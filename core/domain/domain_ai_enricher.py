"""domain_ai_enricher.py — Post-heuristic AI enrichment pass per domain.

The heuristic engine processes assets using file paths only (no content), so
behaviors, rules, and pseudocode are systematically under-populated.  This
module runs a second pass that reads actual source file content and asks an
LLM to extract what the heuristic missed.

Workflow
--------
1. Scan ``solution_root`` for files relevant to ``domain_name`` using
   ``domain_asset_matcher.match_assets``.
2. Read each file's content from disk (max ``MAX_FILE_CHARS`` chars per file).
3. Group files into token-safe batches (``BATCH_SIZE`` files × content).
4. For each batch, call ``provider.generate_json`` with a content-aware prompt
   asking for behaviors, rules, pseudocode, events, integrations.
5. Merge results additively into the existing domain JSON files via
   ``DomainModelStore.save_model``.  No manually enriched data is overwritten.

Usage
-----
    from core.domain.domain_ai_enricher import DomainAIEnricher
    enricher = DomainAIEnricher(solution_root="C:/Udvikling/sms-service")
    enricher.enrich("identity_access", dry_run=False)

Or from CLI::

    python run_ai_enrichment.py --domain identity_access
    python run_ai_enrichment.py --all
    python run_ai_enrichment.py --domain identity_access --dry-run
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from core.asset_scanner import AssetScanner
from core.domain.ai_reasoner import AIProvider, HeuristicAIProvider, build_provider_from_env
from core.domain.domain_asset_matcher import match_assets
from core.domain.domain_model_store import DomainModelStore
from core.domain.domain_state import DOMAIN_SEEDS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Max characters read per source file (≈ 2 000 tokens at 3 chars/token)
MAX_FILE_CHARS: int = 6_000

# Files grouped into batches of this size for each LLM call
BATCH_SIZE: int = 4

# File extensions to include
_CODE_EXTENSIONS: Set[str] = {
    ".cs", ".ts", ".tsx", ".js", ".py",
    ".sql", ".json", ".yaml", ".yml", ".xml",
}

# Paths to skip during content reading
_SKIP_PATH_FRAGMENTS: List[str] = [
    "/obj/", "/bin/", "/node_modules/", "/.angular/",
    ".designer.cs", ".g.cs", ".generated.",
    "migrations/", "wwwroot/",
    "test.integration", "test.ui",
]

# Minimum file size (bytes) — smaller files are usually auto-generated stubs
_MIN_FILE_SIZE: int = 150

# LLM prompt template — asks specifically for what the heuristic misses
_ENRICHMENT_PROMPT = """\
You are extracting domain knowledge from source files in the "{domain}" domain
of a .NET / Angular application.

IMPORTANT rules:
- Extract INTENT and RESPONSIBILITY only.  Never quote source code.
- Use plain English verb phrases for behaviors (e.g. "validates user credentials").
- Use plain English constraints for rules (e.g. "user locked after 5 failed logins").
- Keep each list item ≤ 80 characters.
- If a section has nothing meaningful, return an empty list [].

Source files (truncated):
{files_block}

Return ONLY valid JSON:
{{
  "behaviors":    ["<verb phrase>", ...],
  "rules":        ["<business constraint or invariant>", ...],
  "pseudocode":   ["<numbered step in main flow, e.g. 1. receive login request>", ...],
  "events":       ["<EventName — only domain events, not technical noise>", ...],
  "integrations": ["<ExternalSystem or API name>", ...]
}}
"""

# Noise words to strip from heuristic-generated junk rules
_RULE_NOISE: re.Pattern = re.compile(
    r"^(must|should|guard|if truly|return only|all strings|keep each|omit a key|no code)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_skippable(path: str) -> bool:
    lc = path.lower().replace("\\", "/")
    return any(frag in lc for frag in _SKIP_PATH_FRAGMENTS)


def _read_source_file(abs_path: str) -> Optional[str]:
    """Read a source file, returning up to MAX_FILE_CHARS characters."""
    try:
        size = os.path.getsize(abs_path)
        if size < _MIN_FILE_SIZE:
            return None
        with open(abs_path, encoding="utf-8", errors="ignore") as fh:
            return fh.read(MAX_FILE_CHARS)
    except OSError:
        return None


def _clean_rules(rules: List[str]) -> List[str]:
    """Remove junk rules coming from schema description text in the prompt."""
    cleaned = []
    for r in rules:
        r = r.strip()
        if not r or len(r) < 10:
            continue
        if _RULE_NOISE.match(r):
            continue
        # Skip items that look like file paths or code identifiers
        if r.startswith("//") or r.startswith("/*") or "/" in r[:5]:
            continue
        cleaned.append(r)
    return cleaned


def _merge_lists(existing: List[str], new_items: List[str]) -> List[str]:
    """Additive set-union merge, deduped and sorted."""
    merged = set(str(x) for x in existing if x)
    for item in new_items:
        item = str(item).strip()
        if item and len(item) >= 5:
            merged.add(item)
    return sorted(merged)


def _build_files_block(file_contents: List[tuple]) -> str:
    """Format (path, content) pairs into the prompt's files_block."""
    parts = []
    for rel_path, content in file_contents:
        # Trim and add a clear separator
        trimmed = content[:MAX_FILE_CHARS]
        parts.append(f"=== {rel_path} ===\n{trimmed}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# DomainAIEnricher
# ---------------------------------------------------------------------------

class DomainAIEnricher:
    """Runs a content-aware AI enrichment pass for a single domain.

    Parameters
    ----------
    solution_root:
        Root directory of the .NET / Angular solution to scan.
    domains_root:
        Root directory where domain JSON files live.  Defaults to
        ``<repo_root>/domains``.
    provider:
        AI provider to use.  Defaults to ``build_provider_from_env()``.
    verbose:
        Print progress to stdout.
    """

    def __init__(
        self,
        solution_root: str,
        domains_root: Optional[str] = None,
        provider: Optional[AIProvider] = None,
        verbose: bool = True,
    ) -> None:
        self._solution_root = Path(solution_root)
        _repo_root = Path(__file__).parent.parent.parent
        self._domains_root = Path(domains_root) if domains_root else _repo_root / "domains"
        self._provider = provider or build_provider_from_env()
        self._verbose = verbose
        self._store = DomainModelStore(str(self._domains_root))

    def _log(self, msg: str) -> None:
        if self._verbose:
            print(msg)

    # ------------------------------------------------------------------
    # Asset discovery
    # ------------------------------------------------------------------

    def _discover_domain_files(self, domain_name: str) -> List[tuple]:
        """Return (rel_path, content) for all files matching *domain_name*.

        Reads from ``solution_root`` directly.  Uses ``match_assets`` to
        identify which files belong to this domain, then reads their content.
        """
        # Build lightweight asset list from file paths (no content needed for matching)
        path_assets = []
        for abs_path in self._solution_root.rglob("*"):
            if not abs_path.is_file():
                continue
            if abs_path.suffix.lower() not in _CODE_EXTENSIONS:
                continue
            rel = abs_path.relative_to(self._solution_root).as_posix()
            if _is_skippable(rel):
                continue
            path_assets.append({
                "id": f"code:{rel}",
                "path": rel,
                "content": "",   # empty — matching uses path/id only
            })

        matched_ids: Set[str] = set(match_assets(domain_name, path_assets))
        self._log(f"  [{domain_name}] matched {len(matched_ids)} files via asset matcher")

        # Now read actual content for matched files
        results = []
        for asset in path_assets:
            if asset["id"] not in matched_ids:
                continue
            abs_path = self._solution_root / asset["path"]
            content = _read_source_file(str(abs_path))
            if content:
                results.append((asset["path"], content))

        # Sort by path for determinism
        results.sort(key=lambda t: t[0])
        self._log(f"  [{domain_name}] {len(results)} files readable")
        return results

    # ------------------------------------------------------------------
    # Batching + LLM calls
    # ------------------------------------------------------------------

    def _call_provider_for_batch(
        self, domain_name: str, file_contents: List[tuple]
    ) -> Dict[str, Any]:
        """Send one batch of files to the provider, return raw JSON dict."""
        files_block = _build_files_block(file_contents)
        prompt = _ENRICHMENT_PROMPT.format(
            domain=domain_name,
            files_block=files_block,
        )
        try:
            result = self._provider.generate_json(prompt, schema_name="domain_enrichment")
        except Exception as exc:
            self._log(f"    WARNING: provider error: {exc}")
            result = {}
        return result if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def enrich(self, domain_name: str, dry_run: bool = False) -> Dict[str, Any]:
        """Run AI enrichment for *domain_name*.

        Returns
        -------
        dict
            Summary with keys ``behaviors_added``, ``rules_added``,
            ``pseudocode_lines``, ``events_added``, ``integrations_added``.
        """
        self._log(f"\n=== AI Enrichment: {domain_name} ===")

        # Load existing model
        model = self._store.load_model(domain_name)
        existing_behaviors = list(model.get("behaviors") or [])
        existing_rules     = list(model.get("rules") or [])
        existing_pseudocode= list(model.get("pseudocode") or [])
        existing_events    = list(model.get("events") or [])
        existing_integ     = list(model.get("integrations") or [])

        # Clean junk from existing rules (heuristic noise)
        model["rules"] = _clean_rules(existing_rules)

        # Discover files
        file_list = self._discover_domain_files(domain_name)
        if not file_list:
            self._log("  No files found — skipping")
            return {"behaviors_added": 0, "rules_added": 0}

        # Process in batches
        all_behaviors:    List[str] = list(existing_behaviors)
        all_rules:        List[str] = list(model["rules"])
        all_pseudocode:   List[str] = list(existing_pseudocode)
        all_events:       List[str] = list(existing_events)
        all_integrations: List[str] = list(existing_integ)

        total_batches = (len(file_list) + BATCH_SIZE - 1) // BATCH_SIZE
        for i in range(0, len(file_list), BATCH_SIZE):
            batch = file_list[i: i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            self._log(f"  Batch {batch_num}/{total_batches}: {[b[0].split('/')[-1] for b in batch]}")

            result = self._call_provider_for_batch(domain_name, batch)

            new_behaviors    = result.get("behaviors") or []
            new_rules        = result.get("rules") or []
            new_pseudocode   = result.get("pseudocode") or []
            new_events       = result.get("events") or []
            new_integrations = result.get("integrations") or []

            # Clean rules before merging
            new_rules = _clean_rules(new_rules if isinstance(new_rules, list) else [])

            if isinstance(new_behaviors, list):
                all_behaviors = _merge_lists(all_behaviors, new_behaviors)
            if isinstance(new_rules, list):
                all_rules = _merge_lists(all_rules, new_rules)
            if isinstance(new_pseudocode, list):
                all_pseudocode = _merge_lists(all_pseudocode, new_pseudocode)
            if isinstance(new_events, list):
                all_events = _merge_lists(all_events, new_events)
            if isinstance(new_integrations, list):
                all_integrations = _merge_lists(all_integrations, new_integrations)

        # Summary
        behaviors_added    = len(all_behaviors) - len(existing_behaviors)
        rules_added        = len(all_rules) - len(model["rules"])
        pseudocode_lines   = len(all_pseudocode)
        events_added       = len(all_events) - len(existing_events)
        integrations_added = len(all_integrations) - len(existing_integ)

        self._log(
            f"  Results: +{behaviors_added} behaviors, +{rules_added} rules, "
            f"{pseudocode_lines} pseudocode lines, +{events_added} events, "
            f"+{integrations_added} integrations"
        )

        if dry_run:
            self._log("  [DRY RUN] — no files written")
            # Still show a preview
            if all_behaviors:
                self._log(f"  Behaviors preview: {all_behaviors[:5]}")
            if all_rules:
                self._log(f"  Rules preview: {all_rules[:5]}")
            return {
                "behaviors_added": behaviors_added,
                "rules_added": rules_added,
                "pseudocode_lines": pseudocode_lines,
                "events_added": events_added,
                "integrations_added": integrations_added,
                "dry_run": True,
            }

        # Persist enriched model
        model["behaviors"]    = all_behaviors
        model["rules"]        = all_rules
        model["pseudocode"]   = all_pseudocode
        model["events"]       = all_events
        model["integrations"] = all_integrations

        self._store.save_model(
            domain_name,
            model,
            meta={"enriched_by": "DomainAIEnricher", "enrichment_pass": True},
        )
        self._log(f"  Saved enriched model to domains/{domain_name}/")

        return {
            "behaviors_added": behaviors_added,
            "rules_added": rules_added,
            "pseudocode_lines": pseudocode_lines,
            "events_added": events_added,
            "integrations_added": integrations_added,
        }
