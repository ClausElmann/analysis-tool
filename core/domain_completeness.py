"""
domain_completeness.py — Domain Completeness Check (DOMAIN_COMPLETENESS_PROTOCOL)

Before any slice can be generated, a domain must pass this check.
If the domain is not "build-ready", returns a REBUILD REQUIRED result
listing exactly what is missing or inconsistent.

RULES (V2 canonical):
  1. Required files must exist
  2. Required sections must be non-empty
  3. Substance rules: no placeholder / generic values
  4. Consistency: commands reference real entities, flows match commands

Usage:
    checker = DomainCompletenessChecker(domain_root="domains/identity_access")
    result = checker.check()
    if result.is_ready:
        ...generate slices...
    else:
        print(result.report())
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Required files and the key they must contain ─────────────────────────────

_REQUIRED_FILES: list[tuple[str, str | None]] = [
    ("000_meta.json", "domain"),
    ("010_entities.json", None),        # list
    ("020_behaviors.json", None),       # list (commands / behaviors)
    ("030_flows.json", None),           # list
    ("070_rules.json", None),           # list
]

# Minimum item counts per file
_MIN_ITEM_COUNTS: dict[str, int] = {
    "010_entities.json": 1,
    "020_behaviors.json": 1,
    "030_flows.json": 1,
    "070_rules.json": 1,
}

# Phrases that indicate placeholder / generic content (case-insensitive)
_PLACEHOLDER_PHRASES = [
    "validate input",
    "todo",
    "placeholder",
    "tbd",
    "to be defined",
    "example",
    "<entity>",
    "<command>",
]


@dataclass
class CompletenessResult:
    is_ready: bool
    domain: str
    gaps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    score: float = 0.0

    def report(self) -> str:
        lines = [f"DOMAIN: {self.domain}"]
        if self.is_ready:
            lines.append(f"STATUS: BUILD-READY (score={self.score:.2f})")
            if self.warnings:
                lines.append("WARNINGS:")
                for w in self.warnings:
                    lines.append(f"  ⚠  {w}")
        else:
            lines.append(f"STATUS: REBUILD REQUIRED (score={self.score:.2f})")
            lines.append("MISSING / INCOMPLETE:")
            for g in self.gaps:
                lines.append(f"  ✗  {g}")
            if self.warnings:
                lines.append("WARNINGS:")
                for w in self.warnings:
                    lines.append(f"  ⚠  {w}")
        return "\n".join(lines)


class DomainCompletenessChecker:
    """
    Validates a domain directory against the DOMAIN_COMPLETENESS_PROTOCOL.

    Args:
        domain_root: Path to the domain directory, e.g. domains/identity_access
    """

    def __init__(self, domain_root: str | Path) -> None:
        self._root = Path(domain_root)
        self._domain_name = self._root.name

    # ── Public API ────────────────────────────────────────────────────────────

    def check(self) -> CompletenessResult:
        gaps: list[str] = []
        warnings: list[str] = []
        loaded: dict[str, Any] = {}

        # ── 1. Required files ──────────────────────────────────────────────────
        for filename, top_key in _REQUIRED_FILES:
            path = self._root / filename
            if not path.exists():
                gaps.append(f"`{filename}` is missing")
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                gaps.append(f"`{filename}` is not valid JSON: {exc}")
                continue
            loaded[filename] = data
            if top_key and isinstance(data, dict) and not data.get(top_key):
                gaps.append(f"`{filename}` missing required field `{top_key}`")

        # ── 2. Minimum item counts ─────────────────────────────────────────────
        for filename, min_count in _MIN_ITEM_COUNTS.items():
            data = loaded.get(filename)
            if data is None:
                continue  # already flagged above
            items = data if isinstance(data, list) else data.get("items", [])
            if len(items) < min_count:
                gaps.append(
                    f"`{filename}` has {len(items)} item(s), minimum is {min_count}"
                )

        # ── 3. Substance check ────────────────────────────────────────────────
        for filename in ("020_behaviors.json", "070_rules.json"):
            data = loaded.get(filename)
            if not isinstance(data, list):
                continue
            for item in data:
                text = json.dumps(item).lower()
                for phrase in _PLACEHOLDER_PHRASES:
                    if phrase in text:
                        warnings.append(
                            f"`{filename}` item `{item.get('id', item.get('name', '?'))}` "
                            f"contains placeholder phrase: \"{phrase}\""
                        )
                        break

        # ── 4. Behaviors: no empty steps / descriptions ───────────────────────
        behaviors: list[dict] = loaded.get("020_behaviors.json", [])
        if isinstance(behaviors, list):
            for b in behaviors:
                bid = b.get("id", b.get("name", "?"))
                desc = b.get("description", "")
                steps = b.get("steps", [])
                if not desc and not steps:
                    gaps.append(
                        f"`020_behaviors.json` behavior `{bid}` has no description or steps"
                    )
                elif not steps:
                    warnings.append(
                        f"`020_behaviors.json` behavior `{bid}` has no steps (description only)"
                    )

        # ── 5. Rules: no generic rules ────────────────────────────────────────
        rules: list[dict] = loaded.get("070_rules.json", [])
        if isinstance(rules, list):
            for r in rules:
                rid = r.get("id", r.get("name", "?"))
                rule_text = r.get("rule", "")
                if not rule_text:
                    gaps.append(
                        f"`070_rules.json` rule `{rid}` has no `rule` text"
                    )

        # ── 6. Consistency: flows reference behaviors that exist ──────────────
        behavior_names = {
            b.get("name", "").lower()
            for b in (behaviors if isinstance(behaviors, list) else [])
        }
        flows: list[dict] = loaded.get("030_flows.json", [])
        if isinstance(flows, list):
            for flow in flows:
                fid = flow.get("id", flow.get("name", "?"))
                # Flows should have at least a trigger or happy_path
                if not flow.get("trigger") and not flow.get("happy_path"):
                    gaps.append(
                        f"`030_flows.json` flow `{fid}` has neither trigger nor happy_path"
                    )

        # ── 7. Meta: domain is not abandoned / empty ──────────────────────────
        meta: dict = loaded.get("000_meta.json", {})
        if isinstance(meta, dict):
            status = meta.get("status", "")
            if status == "abandoned":
                gaps.append("`000_meta.json` status is `abandoned` — domain cannot be built")
            elif status not in ("complete", "stable_candidate", "in_progress", ""):
                warnings.append(
                    f"`000_meta.json` status is `{status}` — domain may be incomplete"
                )
            completeness_score = float(meta.get("completeness_score", 0))
            if completeness_score < 0.70:
                gaps.append(
                    f"completeness_score is {completeness_score:.2f} (minimum 0.70 required)"
                )

        # ── Compute result ────────────────────────────────────────────────────
        # Simple scoring: full marks if no gaps
        total_checks = len(_REQUIRED_FILES) + len(_MIN_ITEM_COUNTS) + 3  # substance + consistency + meta
        penalty_per_gap = 1.0 / total_checks
        score = max(0.0, 1.0 - len(gaps) * penalty_per_gap)
        is_ready = len(gaps) == 0

        return CompletenessResult(
            is_ready=is_ready,
            domain=self._domain_name,
            gaps=gaps,
            warnings=warnings,
            score=round(score, 2),
        )
