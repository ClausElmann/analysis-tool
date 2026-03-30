"""
domain_loop_engine.py — Autonomous domain-first extraction loop.

For each domain, the engine:
  1. Collects related assets (path/name heuristics)
  2. Runs pending AI stages on those assets (via DomainPipeline)
  3. Aggregates per-asset AI outputs into domain model files
  4. Scores the domain (DomainScorer)
  5. Detects knowledge gaps (DomainGapDetector)
  6. Decides whether to continue, mark complete, or mark saturated
  7. Persists domain_state.json after every iteration

Completion criteria (score >= 0.80 OR saturation detected):
    domains/{name}/domain_state.json  → "status": "complete" | "saturated"

Domain processing order: roi_score descending (highest-value domains first).

Asset → domain mapping strategy:
    code_file           — any path segment normalises to domain name prefix
    wiki_section        — domain name appears in file or section heading
    labels_namespace    — namespace prefix contains domain name
    work_items_batch    — global context; assigned to ALL domains
    git_insights_batch  — global context; assigned to ALL domains
    pdf_section         — domain name appears in section title or file name
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Callable, Optional

from core.domain_builder import DomainBuilder, _domain_token
from core.domain_state import (
    DomainState,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETE,
    STATUS_SATURATED,
    SCORE_THRESHOLD,
)
from core.domain_gap_detector import DomainGapDetector
from core.domain_scorer import DomainScorer
from core.domain_pipeline import DomainPipeline
from core.stage_state import StageState, STAGES


# ── Constants ─────────────────────────────────────────────────────────────────

# Asset types that are global context and go to every domain
_GLOBAL_ASSET_TYPES = frozenset({
    "work_items_batch",
    "git_insights_batch",
})

_DEFAULT_MAX_ITERATIONS = 10
_DEFAULT_MAX_ASSETS_PER_ITER = 30


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_id(asset_id: str) -> str:
    return asset_id.replace(":", "_").replace("/", "_").replace("\\", "_")


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


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


def _deduplicate(items: list) -> list:
    """
    Remove duplicate items from a list of dicts or strings.
    Equality is determined by the 'name' key (lowercase) for dicts,
    or the string value itself.
    """
    seen: set[str] = set()
    result = []
    for item in items:
        if isinstance(item, dict):
            key = _normalise(item.get("name", "") or item.get("description", "") or str(item))
        else:
            key = _normalise(str(item))
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


# ── Asset → domain affinity ───────────────────────────────────────────────────

def _asset_matches_domain(asset: dict, domain_name: str) -> bool:
    """
    Return True if this asset is relevant to the given domain.

    Strategy:
      - Global asset types (work items, git) → always match
      - code_file: check if any path segment normalises to domain prefix
      - wiki_section, pdf_section: domain name in asset ID path
      - labels_namespace: namespace prefix contains domain name
    """
    asset_type = asset.get("type", "")

    if asset_type in _GLOBAL_ASSET_TYPES:
        return True

    asset_id = asset.get("id", "")
    domain_norm = _normalise(domain_name)
    domain_token = _normalise(_domain_token(domain_name))

    if asset_type == "code_file":
        # id = "code:ServiceAlert.Services/Messaging/MessageService.cs"
        path_part = asset_id.split(":", 1)[-1] if ":" in asset_id else asset_id
        segments = re.split(r"[/\\.]", path_part)
        for seg in segments:
            seg_norm  = _normalise(seg)
            seg_token = _normalise(_domain_token(seg))   # strip Controller/Service/etc.
            if (
                seg_norm == domain_norm
                or seg_token == domain_norm
                or seg_norm == domain_token
                or seg_token == domain_token
                or (len(seg_norm) > 3 and (
                    seg_norm.startswith(domain_norm)
                    or domain_norm.startswith(seg_norm)
                ))
            ):
                return True
        return False

    if asset_type in ("wiki_section", "pdf_section"):
        id_norm = _normalise(asset_id)
        return domain_norm in id_norm

    if asset_type == "labels_namespace":
        ns = asset.get("namespace", asset_id.split(":")[-1])
        return domain_norm in _normalise(ns)

    return False


# ── Domain data loader ────────────────────────────────────────────────────────

def _load_domain_files(domain_dir: Path) -> dict:
    """Load all model JSON files for a domain into a single dict."""
    files = {
        "meta":       "000_meta.json",
        "entities":   "010_entities.json",
        "behaviors":  "020_behaviors.json",
        "flows":      "030_flows.json",
        "events":     "040_events.json",
        "batch":      "050_batch.json",
        "integrations": "060_integrations.json",
        "rules":      "070_rules.json",
        "pseudocode": "080_pseudocode.json",
        "rebuild":    "090_rebuild.json",
    }
    return {key: _load_json_file(domain_dir / fname, {}) for key, fname in files.items()}


# ── AI output aggregator ──────────────────────────────────────────────────────

class _DomainAggregator:
    """
    Reads per-asset AI outputs from domain_output/{stage}/ and merges
    them into the domain model files (010–090).

    For each domain_mapping output that belongs to the domain:
      - entities    → 010_entities.json
      - behaviors   → 020_behaviors.json
      - flows       → 030_flows.json
      - rules       → 070_rules.json
      - pseudocode  → 080_pseudocode.json
      - rebuild_requirements → 090_rebuild.json

    Pre-populated files (040, 050, 060) are left intact.
    """

    def __init__(self, output_root: Path, domains_root: Path):
        self._output_root = output_root
        self._domains_root = domains_root

    def aggregate(self, domain_name: str, domain_assets: list[dict]) -> dict:
        """
        Merge domain_mapping AI outputs for domain_assets into the domain's
        model files.  Returns a summary dict describing what changed.
        """
        mapping_dir = self._output_root / "domain_mapping"
        if not mapping_dir.exists():
            return {"merged": 0}

        merged: dict[str, list] = {
            "entities":            [],
            "behaviors":           [],
            "flows":               [],
            "rules":               [],
            "pseudocode":          [],
            "rebuild_requirements": [],
        }

        asset_ids = {a["id"] for a in domain_assets}
        merged_count = 0

        for asset_id in asset_ids:
            path = mapping_dir / f"{_safe_id(asset_id)}.json"
            data = _load_json_file(path, None)
            if not data:
                continue
            merged_count += 1
            for key in merged:
                val = data.get(key, [])
                if isinstance(val, list):
                    merged[key].extend(val)

        if merged_count == 0:
            return {"merged": 0}

        # Deduplicate each list
        for key in merged:
            merged[key] = _deduplicate(merged[key])

        domain_dir = self._domains_root / domain_name
        _write_json_atomic(domain_dir / "010_entities.json",
                           {"domain": domain_name, "entities": merged["entities"]})
        _write_json_atomic(domain_dir / "020_behaviors.json",
                           {"domain": domain_name, "behaviors": merged["behaviors"]})
        _write_json_atomic(domain_dir / "030_flows.json",
                           {"domain": domain_name, "flows": merged["flows"]})
        _write_json_atomic(domain_dir / "070_rules.json",
                           {"domain": domain_name, "rules": merged["rules"]})
        _write_json_atomic(domain_dir / "080_pseudocode.json",
                           {"domain": domain_name, "pseudocode": merged["pseudocode"]})
        _write_json_atomic(domain_dir / "090_rebuild.json",
                           {"domain": domain_name,
                            "rebuild_requirements": merged["rebuild_requirements"]})

        return {
            "merged": merged_count,
            "entities":   len(merged["entities"]),
            "behaviors":  len(merged["behaviors"]),
            "flows":      len(merged["flows"]),
        }


# ── DomainLoopEngine ──────────────────────────────────────────────────────────

class DomainLoopEngine:
    """
    Autonomous domain-first extraction loop.

    Args:
        scanner:              AssetScanner instance
        stage_state:          StageState instance
        ai_processor:         AIProcessor implementation
        data_root:            Path to data/ (stage_state, domain_output/)
        domains_root:         Path to domains/
        max_iterations:       Maximum loop iterations per domain
        max_assets_per_iter:  Cap on assets processed per iteration
        score_threshold:      Quality threshold to mark a domain complete
        verbose:              Print progress lines

    Usage:
        engine = DomainLoopEngine(scanner, stage_state, ai, "data", "domains")
        engine.run()                        # all domains
        engine.run(domain_filter=["Sms"])   # selected domains only
        engine.run_domain("Messaging")      # single domain
    """

    def __init__(
        self,
        scanner,
        stage_state: StageState,
        ai_processor,
        data_root: str,
        domains_root: str,
        max_iterations: int = _DEFAULT_MAX_ITERATIONS,
        max_assets_per_iter: int = _DEFAULT_MAX_ASSETS_PER_ITER,
        score_threshold: float = SCORE_THRESHOLD,
        verbose: bool = True,
    ):
        self._scanner = scanner
        self._stage_state = stage_state
        self._ai = ai_processor
        self._data_root = Path(data_root)
        self._domains_root = Path(domains_root)
        self._max_iterations = max_iterations
        self._max_assets_per_iter = max_assets_per_iter
        self._score_threshold = score_threshold
        self._verbose = verbose

        self._output_root = self._data_root / "domain_output"
        self._scorer = DomainScorer()
        self._detector = DomainGapDetector()
        self._aggregator = _DomainAggregator(self._output_root, self._domains_root)

        # Cache all assets for the run (scanned once)
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

    def _get_domain_assets(self, domain_name: str) -> list[dict]:
        """Return assets relevant to this domain."""
        return [
            a for a in self._get_all_assets()
            if _asset_matches_domain(a, domain_name)
        ]

    # ── Domain list ───────────────────────────────────────────────────────────

    def _load_domain_list(self, domain_filter: Optional[list[str]] = None) -> list[str]:
        """
        Return domain names sorted by roi_score desc.
        If domain_filter given, return only those names (in roi order).
        """
        if not self._domains_root.exists():
            return []

        roi_map: list[tuple[int, str]] = []
        for d in self._domains_root.iterdir():
            if not d.is_dir():
                continue
            name = d.name
            meta = _load_json_file(d / "000_meta.json", {})
            roi = meta.get("roi_score", 0)
            roi_map.append((roi, name))

        roi_map.sort(key=lambda x: -x[0])
        names = [name for _, name in roi_map]

        if domain_filter:
            filter_set = {_normalise(n) for n in domain_filter}
            names = [n for n in names if _normalise(n) in filter_set]

        return names

    # ── Pipeline runner ───────────────────────────────────────────────────────

    def _run_ai_stages(self, domain_name: str, domain_assets: list[dict]) -> dict:
        """Run pending AI stages for domain_assets only."""
        asset_ids = {a["id"] for a in domain_assets}

        pipeline = DomainPipeline(
            scanner=self._scanner,
            stage_state=self._stage_state,
            ai_processor=self._ai,
            output_root=str(self._output_root),
            verbose=self._verbose,
        )
        return pipeline.run(
            max_assets=self._max_assets_per_iter,
            asset_filter=lambda a: a["id"] in asset_ids,
        )

    # ── Scoring and gap detection ─────────────────────────────────────────────

    def _evaluate(self, domain_name: str, state: DomainState) -> dict:
        """Score the domain and detect gaps. Updates state in place."""
        domain_dir = self._domains_root / domain_name
        d = _load_domain_files(domain_dir)

        entities   = d["entities"].get("entities", [])
        behaviors  = d["behaviors"].get("behaviors", [])
        flows      = d["flows"].get("flows", [])
        events     = d["events"].get("events", [])
        batch_jobs = d["batch"].get("batch_jobs", [])
        integr     = d["integrations"]
        rules      = d["rules"].get("rules", [])
        pseudocode = d["pseudocode"].get("pseudocode", [])
        rebuild    = d["rebuild"].get("rebuild_requirements", [])
        meta       = d["meta"]

        score_result = self._scorer.score(
            meta=meta,
            entities=entities,
            behaviors=behaviors,
            flows=flows,
            events=events,
            batch_jobs=batch_jobs,
            integrations=integr,
            rules=rules,
            pseudocode=pseudocode,
            rebuild=rebuild,
        )

        gaps = self._detector.detect(
            meta=meta,
            entities=entities,
            behaviors=behaviors,
            flows=flows,
            events=events,
            batch_jobs=batch_jobs,
            integrations=integr,
        )

        # Determine what improved
        prev_breakdown = state.score_breakdown
        last_improvement = None
        for dim, val in score_result["breakdown"].items():
            if val > prev_breakdown.get(dim, 0.0):
                last_improvement = dim
                break

        state.update_score(
            score_result["score"],
            score_result["breakdown"],
            last_improvement,
        )
        state.update_gaps(gaps)
        state.save()

        return {
            "score":        score_result["score"],
            "is_complete":  score_result["is_complete"],
            "gaps":         len(gaps),
            "entities":     len(entities),
            "behaviors":    len(behaviors),
            "flows":        len(flows),
        }

    # ── Single domain loop ────────────────────────────────────────────────────

    def run_domain(self, domain_name: str) -> dict:
        """
        Run the autonomous loop for a single domain.

        Returns:
            Final domain state summary dict.
        """
        state = DomainState.load(self._domains_root, domain_name)

        if state.is_done:
            self._log("SKIP", f"{domain_name} already {state.status}")
            return {"domain": domain_name, "status": state.status, "score": state.score}

        state.mark_in_progress()
        state.save()
        self._log("DOMAIN", f"Starting '{domain_name}'  (score={state.score})")

        domain_assets = self._get_domain_assets(domain_name)
        self._log("ASSETS", f"{domain_name}: {len(domain_assets)} related assets")

        for iteration in range(1, self._max_iterations + 1):
            state.iterations = iteration
            self._log("ITER", f"{domain_name}  iteration {iteration}/{self._max_iterations}")

            # Run AI stages for domain assets
            run_report = self._run_ai_stages(domain_name, domain_assets)
            self._log(
                "AI",
                f"{domain_name}  processed={run_report['processed']}  "
                f"skipped={run_report['skipped']}  errors={run_report['errors']}",
            )

            # Aggregate AI outputs into domain model files
            agg = self._aggregator.aggregate(domain_name, domain_assets)
            self._log(
                "AGGREGATE",
                f"{domain_name}  merged={agg['merged']}  "
                f"entities={agg.get('entities', 0)}  "
                f"behaviors={agg.get('behaviors', 0)}  "
                f"flows={agg.get('flows', 0)}",
            )

            # Score and detect gaps
            eval_result = self._evaluate(domain_name, state)
            self._log(
                "SCORE",
                f"{domain_name}  score={eval_result['score']:.3f}  "
                f"gaps={eval_result['gaps']}  "
                f"entities={eval_result['entities']}  "
                f"flows={eval_result['flows']}",
            )

            # Check completion
            if eval_result["is_complete"]:
                state.mark_complete()
                state.save()
                self._log(
                    "COMPLETE",
                    f"{domain_name}  score={eval_result['score']:.3f} >= {self._score_threshold}",
                )
                break

            # Check saturation
            saturated = state.check_saturation(
                entity_count=eval_result["entities"],
                flow_count=eval_result["flows"],
                behavior_count=eval_result["behaviors"],
            )
            state.save()

            if saturated:
                state.mark_saturated()
                state.save()
                self._log(
                    "SATURATED",
                    f"{domain_name}  stable {state.saturation['stable_iterations']} iters "
                    f"score={eval_result['score']:.3f}",
                )
                break

            # If all AI stages already done and nothing new to process, exit early
            if run_report["processed"] == 0 and iteration > 1:
                self._log("IDLE", f"{domain_name}  no new AI outputs; exiting loop")
                break

        return {
            "domain":     domain_name,
            "status":     state.status,
            "score":      state.score,
            "iterations": state.iterations,
            "gaps":       len(state.gaps),
        }

    # ── Multi-domain run ──────────────────────────────────────────────────────

    def run(
        self,
        domain_filter: Optional[list[str]] = None,
        max_domains: Optional[int] = None,
    ) -> list[dict]:
        """
        Run the domain loop across all (or selected) domains.

        Args:
            domain_filter: List of domain names to restrict to.
            max_domains:   Stop after this many domains.

        Returns:
            List of per-domain summary dicts.
        """
        domains = self._load_domain_list(domain_filter)
        if max_domains is not None:
            domains = domains[:max_domains]

        self._log("ENGINE", f"Running {len(domains)} domains")
        results = []

        for domain_name in domains:
            result = self.run_domain(domain_name)
            results.append(result)

        # Print summary
        complete  = sum(1 for r in results if r["status"] == "complete")
        saturated = sum(1 for r in results if r["status"] == "saturated")
        self._log(
            "SUMMARY",
            f"Domains processed={len(results)}  "
            f"complete={complete}  saturated={saturated}",
        )
        return results
