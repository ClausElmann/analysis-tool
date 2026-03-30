"""
domain_engine.py — Autonomous domain analysis engine.

Discovers domains from a seed list AND/OR an existing domains/ directory,
then drives iterative AI extraction per domain until convergence:

    STOP when BOTH conditions hold:
        new_information_score < NEW_INFO_THRESHOLD  (0.02)
        AND completeness_score > COMPLETENESS_THRESHOLD (0.90)

    OR when max_iterations is reached → status = "saturated".

Key differences from DomainLoopEngine:
    ┌──────────────────────────┬─────────────────────────────────────────────┐
    │ DomainLoopEngine         │ DomainEngine                                │
    ├──────────────────────────┼─────────────────────────────────────────────┤
    │ Asset selection: path    │ Path/name + keyword relevance scoring        │
    │ Stop: score ≥ 0.80       │ new_info < 0.02 AND completeness > 0.90     │
    │ Discovery: domains/ dir  │ Seed list + dir + optional dynamic discovery │
    │ new_information_score: — │ Tracked every iteration                     │
    └──────────────────────────┴─────────────────────────────────────────────┘

Usage:
    engine = DomainEngine(scanner, stage_state, ai, "data", "domains")

    # Default seeds + everything in domains/
    engine.run()

    # Custom seed list with keyword overrides
    engine.run(
        seed_list=["messaging", "billing"],
        keywords_map={"billing": ["invoice", "stripe", "payment"]},
    )

    # Single domain
    engine.run_domain("messaging")

Environment:
    GITHUB_TOKEN    Required by CopilotAIProcessor in the outer pipeline

Paths written:
    domains/{name}/domain_state.json  — per-domain state (status, scores, gaps)
    domains/{name}/010_entities.json  — merged AI output per iteration
    ...                               — (all 7 model files refreshed each iter)
    data/domain_output/               — raw per-asset AI stage outputs
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Callable, Optional

from core.domain_builder import _domain_token
from core.domain_information import (
    compute_new_information,
    compute_completeness,
    load_domain_snapshot,
    NEW_INFO_THRESHOLD,
    COMPLETENESS_THRESHOLD,
    TRACKED_KEYS,
)
from core.domain_loop_engine import _asset_matches_domain, _deduplicate
from core.domain_state import (
    DomainState,
    STATUS_COMPLETE,
    STATUS_SATURATED,
    STATUS_IN_PROGRESS,
)
from core.domain_pipeline import DomainPipeline
from core.stage_state import StageState


# ── Default seeds and keyword map ─────────────────────────────────────────────

DEFAULT_SEEDS: list[str] = [
    "identity",
    "messaging",
    "billing",
    "subscriptions",
    "monitoring",
]

# Domain name → list of keywords to score asset relevance.
# Checked case-insensitively against asset ID + content.
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "identity":      ["identity", "auth", "login", "user", "account", "password",
                      "token", "claim", "role", "permission", "principal", "session"],
    "messaging":     ["message", "sms", "email", "send", "notify", "notification",
                      "inbox", "recipient", "template", "deliver", "outbox"],
    "billing":       ["invoice", "billing", "payment", "charge", "price",
                      "credit", "debit", "transaction", "receipt", "fee"],
    "subscriptions": ["subscription", "subscribe", "unsubscribe", "plan", "tier",
                      "renewal", "cancel", "active", "expire", "trial"],
    "monitoring":    ["monitor", "health", "alert", "log", "metric", "dashboard",
                      "status", "ping", "trace", "diagnostic", "uptime"],
}

_DEFAULT_MAX_ITERATIONS = 15
_DEFAULT_MAX_ASSETS     = 50
_RELEVANCE_THRESHOLD    = 0.05   # keyword score at which an asset is included


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _safe_id(asset_id: str) -> str:
    return asset_id.replace(":", "_").replace("/", "_").replace("\\", "_")


def _load_json_file(path: Path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return default


def _write_json_atomic(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ── Keyword relevance ─────────────────────────────────────────────────────────

def keyword_relevance(asset: dict, keywords: list[str]) -> float:
    """
    Score 0.0-1.0 how relevant an asset is to a list of keywords.

    Checks the asset ID and any 'content' field for keyword occurrences.
    Returns the fraction of keywords that appear at least once.

    Returns 0.0 if keywords is empty.
    """
    if not keywords:
        return 0.0
    text = (asset.get("id", "") + " " + asset.get("content", "")).lower()
    if not text.strip():
        return 0.0
    hits = sum(1 for kw in keywords if kw.lower() in text)
    return hits / len(keywords)


def get_keywords_for_domain(domain_name: str) -> list[str]:
    """
    Return keyword list for a domain.

    Looks up DOMAIN_KEYWORDS by lowercased domain_name.
    Falls back to splitting the domain name into camelCase tokens.
    """
    key = domain_name.lower()
    if key in DOMAIN_KEYWORDS:
        return DOMAIN_KEYWORDS[key]
    tokens = re.findall(r"[a-z]+", _normalise(domain_name))
    return tokens if tokens else [key]


# ── AI output aggregator ──────────────────────────────────────────────────────

def _aggregate_ai_outputs(
    domain_name: str,
    domain_assets: list[dict],
    output_root: Path,
    domains_root: Path,
) -> dict:
    """
    Read domain_mapping AI outputs for domain_assets and merge them into
    the domain model files (010–090).

    Returns a summary dict: {"merged": N, "entities": N, "behaviors": N, ...}
    """
    mapping_dir = output_root / "domain_mapping"
    if not mapping_dir.exists():
        return {"merged": 0}

    merged: dict[str, list] = {k: [] for k in TRACKED_KEYS}
    asset_ids = {a["id"] for a in domain_assets}
    count = 0

    for asset_id in asset_ids:
        path = mapping_dir / f"{_safe_id(asset_id)}.json"
        data = _load_json_file(path, None)
        if not data:
            continue
        count += 1
        for key in merged:
            # Handle both canonical key and "rebuild_requirements"
            val = data.get(key, [])
            if isinstance(val, list):
                merged[key].extend(val)

    if count == 0:
        return {"merged": 0}

    for key in merged:
        merged[key] = _deduplicate(merged[key])

    domain_dir = domains_root / domain_name
    _write_json_atomic(domain_dir / "010_entities.json",
                       {"domain": domain_name, "entities": merged["entities"]})
    _write_json_atomic(domain_dir / "020_behaviors.json",
                       {"domain": domain_name, "behaviors": merged["behaviors"]})
    _write_json_atomic(domain_dir / "030_flows.json",
                       {"domain": domain_name, "flows": merged["flows"]})
    _write_json_atomic(domain_dir / "040_events.json",
                       {"domain": domain_name, "events": merged["events"]})
    _write_json_atomic(domain_dir / "070_rules.json",
                       {"domain": domain_name, "rules": merged["rules"]})
    _write_json_atomic(domain_dir / "080_pseudocode.json",
                       {"domain": domain_name, "pseudocode": merged["pseudocode"]})
    _write_json_atomic(domain_dir / "090_rebuild.json",
                       {"domain": domain_name,
                        "rebuild_requirements": merged["rebuild_requirements"]})

    return {
        "merged":    count,
        "entities":  len(merged["entities"]),
        "behaviors": len(merged["behaviors"]),
        "flows":     len(merged["flows"]),
    }


# ── DomainEngine ──────────────────────────────────────────────────────────────

class DomainEngine:
    """
    Autonomous domain analysis engine.

    Discovers domains, selects relevant assets via keyword + path heuristics,
    and drives iterative AI extraction until each domain converges.

    Stop condition (BOTH must hold):
        new_information_score < NEW_INFO_THRESHOLD   (0.02)
        AND completeness_score > COMPLETENESS_THRESHOLD (0.90)

    Fallback: status = "saturated" after max_iterations.

    Args:
        scanner:         AssetScanner instance
        stage_state:     StageState instance
        ai_processor:    AIProcessor implementation
        data_root:       Path to data/ directory
        domains_root:    Path to domains/ directory
        max_iterations:  Hard cap per domain (default 15)
        max_assets:      Max assets to pass to the pipeline per iteration (50)
        verbose:         Print progress to stdout
    """

    def __init__(
        self,
        scanner,
        stage_state: StageState,
        ai_processor,
        data_root: str,
        domains_root: str,
        max_iterations: int = _DEFAULT_MAX_ITERATIONS,
        max_assets: int = _DEFAULT_MAX_ASSETS,
        verbose: bool = True,
    ):
        self._scanner = scanner
        self._stage_state = stage_state
        self._ai = ai_processor
        self._data_root = Path(data_root)
        self._domains_root = Path(domains_root)
        self._max_iterations = max_iterations
        self._max_assets = max_assets
        self._verbose = verbose
        self._output_root = self._data_root / "domain_output"
        self._all_assets: Optional[list[dict]] = None

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, tag: str, msg: str):
        if self._verbose:
            print(f"[{tag:<12}] {msg}")

    # ── Asset access ──────────────────────────────────────────────────────────

    def _get_all_assets(self) -> list[dict]:
        if self._all_assets is None:
            self._all_assets = self._scanner.scan_all_assets()
            self._log("SCAN", f"Scanned {len(self._all_assets)} assets")
        return self._all_assets

    # ── Asset selection ───────────────────────────────────────────────────────

    def select_assets(
        self,
        domain_name: str,
        keywords: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Select assets relevant to a domain.

        Combines two signals:
            1. Path/name matching  (from domain_loop_engine._asset_matches_domain)
            2. Keyword relevance   (keyword_relevance against the provided list)

        Assets that pass neither signal with sufficient score are excluded.
        Remaining assets are sorted by combined relevance score descending and
        capped at max_assets.

        Global asset types (work_items_batch, git_insights_batch) are always
        included, regardless of keyword score.
        """
        kw = keywords or get_keywords_for_domain(domain_name)
        all_assets = self._get_all_assets()

        scored: list[tuple[float, dict]] = []
        seen_ids: set[str] = set()

        for asset in all_assets:
            if asset["id"] in seen_ids:
                continue

            path_match = _asset_matches_domain(asset, domain_name)
            kw_score   = keyword_relevance(asset, kw)

            if path_match or kw_score > _RELEVANCE_THRESHOLD:
                combined = (1.0 if path_match else 0.0) + kw_score
                scored.append((combined, asset))
                seen_ids.add(asset["id"])

        scored.sort(key=lambda x: -x[0])
        return [a for _, a in scored[: self._max_assets]]

    # ── Domain discovery ──────────────────────────────────────────────────────

    def discover_domains(
        self,
        seed_list: Optional[list[str]] = None,
        discover_from_dir: bool = True,
    ) -> list[str]:
        """
        Build the ordered list of domains to process.

        Priority:
            1. seed_list entries (if given), else DEFAULT_SEEDS
            2. Existing domains/ subdirectory names (if discover_from_dir)

        Ordering: roi_score descending (from 000_meta.json).
        """
        names: list[str] = list(seed_list if seed_list is not None else DEFAULT_SEEDS)
        seen: set[str] = {n.lower() for n in names}

        if discover_from_dir and self._domains_root.exists():
            for d in sorted(self._domains_root.iterdir()):
                if d.is_dir() and d.name.lower() not in seen:
                    names.append(d.name)
                    seen.add(d.name.lower())

        # Sort by roi_score from 000_meta.json, falling back to 0
        def _roi(name: str) -> int:
            return _load_json_file(
                self._domains_root / name / "000_meta.json", {}
            ).get("roi_score", 0)

        names.sort(key=_roi, reverse=True)
        return names

    # ── Domain dir bootstrap ──────────────────────────────────────────────────

    def _ensure_domain_dir(self, domain_name: str):
        """Create domain directory structure with stub files if absent."""
        domain_dir = self._domains_root / domain_name
        domain_dir.mkdir(parents=True, exist_ok=True)
        stubs = {
            "000_meta.json":     {"domain": domain_name, "coverage": {}, "roi_score": 0},
            "010_entities.json": {"domain": domain_name, "entities": []},
            "020_behaviors.json": {"domain": domain_name, "behaviors": []},
            "030_flows.json":    {"domain": domain_name, "flows": []},
            "040_events.json":   {"domain": domain_name, "events": []},
            "070_rules.json":    {"domain": domain_name, "rules": []},
            "080_pseudocode.json": {"domain": domain_name, "pseudocode": []},
            "090_rebuild.json":  {"domain": domain_name, "rebuild_requirements": []},
        }
        for filename, data in stubs.items():
            path = domain_dir / filename
            if not path.exists():
                _write_json_atomic(path, data)

    # ── AI stage runner ───────────────────────────────────────────────────────

    def _run_ai_stages(self, domain_assets: list[dict]) -> int:
        """Run pending AI stages for domain_assets only. Returns processed count."""
        asset_ids = {a["id"] for a in domain_assets}
        pipeline = DomainPipeline(
            scanner=self._scanner,
            stage_state=self._stage_state,
            ai_processor=self._ai,
            output_root=str(self._output_root),
            verbose=self._verbose,
        )
        report = pipeline.run(
            max_assets=len(domain_assets),
            asset_filter=lambda a: a["id"] in asset_ids,
        )
        return report["processed"]

    # ── Single domain loop ────────────────────────────────────────────────────

    def run_domain(
        self,
        domain_name: str,
        keywords: Optional[list[str]] = None,
    ) -> dict:
        """
        Run the autonomous analysis loop for a single domain.

        Each iteration:
            1. Snapshot domain model BEFORE
            2. Run pending AI stages on domain-relevant assets
            3. Aggregate AI outputs into domain model files
            4. Snapshot domain model AFTER
            5. Compute new_information_score  (old → new delta)
            6. Compute completeness_score     (section coverage)
            7. Persist domain_state.json
            8. Check stop condition

        Stop condition: new_info < 0.02 AND completeness > 0.90
        Fallback stop:  max_iterations reached → "saturated"
        Early exit:     processed == 0 after first iteration → "idle"

        Returns:
            {
                "domain":                str,
                "status":                str,
                "completeness_score":    float,
                "new_information_score": float,
                "iterations":            int,
            }
        """
        state = DomainState.load(self._domains_root, domain_name)

        if state.is_done:
            self._log("SKIP", f"{domain_name} already {state.status}")
            return {
                "domain":                domain_name,
                "status":                state.status,
                "completeness_score":    state.score,
                "new_information_score": state.new_information_score,
                "iterations":            state.iterations,
            }

        self._ensure_domain_dir(domain_name)
        state.mark_in_progress()
        state.save()

        kw = keywords or get_keywords_for_domain(domain_name)
        domain_assets = self.select_assets(domain_name, kw)
        self._log(
            "DOMAIN",
            f"'{domain_name}'  assets={len(domain_assets)}  "
            f"keywords={kw[:3]}{'...' if len(kw) > 3 else ''}",
        )

        completeness = 0.0
        new_info = 1.0    # first iteration: all info is new by definition
        domain_dir = self._domains_root / domain_name

        for iteration in range(1, self._max_iterations + 1):
            state.iterations = iteration

            # ── Snapshot before ───────────────────────────────────────────────
            old_snapshot = load_domain_snapshot(domain_dir)

            # ── AI stages ─────────────────────────────────────────────────────
            processed = self._run_ai_stages(domain_assets)

            # ── Aggregate AI outputs into model files ─────────────────────────
            agg = _aggregate_ai_outputs(
                domain_name, domain_assets,
                self._output_root, self._domains_root,
            )

            # ── Snapshot after ────────────────────────────────────────────────
            new_snapshot = load_domain_snapshot(domain_dir)

            # ── Score this iteration ──────────────────────────────────────────
            new_info     = compute_new_information(old_snapshot, new_snapshot)
            completeness = compute_completeness(new_snapshot)

            state.update_new_information_score(new_info)
            state.update_score(completeness, {"completeness": completeness})
            state.save()

            self._log(
                "ITER",
                f"{domain_name}  iter={iteration}/{self._max_iterations}  "
                f"processed={processed}  "
                f"completeness={completeness:.3f}  new_info={new_info:.4f}  "
                f"entities={agg.get('entities', 0)}  "
                f"behaviors={agg.get('behaviors', 0)}",
            )

            # ── Stop condition (convergence) ───────────────────────────────────
            if new_info < NEW_INFO_THRESHOLD and completeness > COMPLETENESS_THRESHOLD:
                state.mark_complete()
                state.save()
                self._log(
                    "COMPLETE",
                    f"{domain_name}  converged  "
                    f"completeness={completeness:.3f}  new_info={new_info:.4f}",
                )
                break

            # ── Early exit (no AI progress after first iteration) ─────────────
            if processed == 0 and iteration > 1:
                self._log("IDLE", f"{domain_name}  no AI progress; ending loop")
                break

        else:
            # Exhausted all iterations without converging
            state.mark_saturated()
            state.save()
            self._log(
                "SATURATED",
                f"{domain_name}  max_iterations reached  "
                f"completeness={completeness:.3f}  new_info={new_info:.4f}",
            )

        return {
            "domain":                domain_name,
            "status":                state.status,
            "completeness_score":    completeness,
            "new_information_score": new_info,
            "iterations":            state.iterations,
        }

    # ── Multi-domain run ──────────────────────────────────────────────────────

    def run(
        self,
        seed_list: Optional[list[str]] = None,
        discover_from_dir: bool = True,
        max_domains: Optional[int] = None,
        keywords_map: Optional[dict[str, list[str]]] = None,
    ) -> list[dict]:
        """
        Run the domain analysis engine across all discovered/seeded domains.

        Processing order: roi_score descending (highest-value domains first).

        Args:
            seed_list:        Domain names to process (default: DEFAULT_SEEDS).
            discover_from_dir: Also process existing domains/ subdirectories.
            max_domains:      Hard cap on the number of domains to process.
            keywords_map:     Per-domain keyword overrides {name: [kw, ...]}.

        Returns:
            List of per-domain result dicts.
        """
        domains = self.discover_domains(
            seed_list=seed_list,
            discover_from_dir=discover_from_dir,
        )
        if max_domains is not None:
            domains = domains[:max_domains]

        self._log("ENGINE", f"Processing {len(domains)} domain(s)")
        results: list[dict] = []

        for domain_name in domains:
            kw = (keywords_map or {}).get(domain_name)
            result = self.run_domain(domain_name, keywords=kw)
            results.append(result)

        complete  = sum(1 for r in results if r["status"] == STATUS_COMPLETE)
        saturated = sum(1 for r in results if r["status"] == STATUS_SATURATED)
        self._log(
            "SUMMARY",
            f"processed={len(results)}  complete={complete}  saturated={saturated}",
        )
        return results
