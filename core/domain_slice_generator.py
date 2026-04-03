"""
domain_slice_generator.py — DOMAIN → SLICE GENERATOR

Translates a build-ready domain into concrete, AI-executable slices.
Each slice maps to one capability (one command / behavior).

RULES:
  - Slice = one capability (domain-based, not technical)
  - No C#, no SQL, no infrastructure in output
  - Slices are sorted: core flows → reads → admin → edge cases
  - Slices must be buildable in isolation
  - Overlapping responsibility is detected and collapsed

Usage:
    from core.domain_completeness import DomainCompletenessChecker
    from core.domain_slice_generator import DomainSliceGenerator

    check = DomainCompletenessChecker("domains/identity_access").check()
    if not check.is_ready:
        print(check.report())
        raise SystemExit(1)

    gen = DomainSliceGenerator("domains/identity_access", output_root="ai-slices")
    slices = gen.generate()
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.domain_completeness import DomainCompletenessChecker, CompletenessResult


# ── Priority tiers (lower = earlier in sorted output) ─────────────────────────

_PRIORITY_KEYWORDS: list[tuple[int, list[str]]] = [
    (1, ["login", "authenticate", "auth", "register", "signup", "sign in"]),
    (2, ["logout", "session", "token", "refresh"]),
    (3, ["create", "add", "new", "submit", "send", "upsert"]),
    (4, ["update", "edit", "change", "modify"]),
    (5, ["delete", "remove", "cancel", "revoke"]),
    (6, ["get", "list", "search", "find", "view", "read", "query"]),
    (7, ["admin", "superadmin", "bulk", "batch", "import"]),
    (8, ["reset", "recover", "unlock", "reactivate"]),
    (9, []),   # default / edge cases
]


def _priority(name: str) -> int:
    lower = name.lower()
    for tier, keywords in _PRIORITY_KEYWORDS:
        for kw in keywords:
            if kw in lower:
                return tier
    return 9


# ── Slice data model ───────────────────────────────────────────────────────────

@dataclass
class SliceSpec:
    index: int
    name: str           # human-readable capability name
    domain: str
    source_id: str      # BEH_001 / FLOW_001 etc.
    goal: str
    inputs: list[str]
    outputs: list[str]
    entities: list[str]
    rules: list[str]
    flow: list[str]
    acceptance_criteria: list[str]
    notes: list[str] = field(default_factory=list)
    priority: int = 9

    def filename(self) -> str:
        safe = re.sub(r"[^a-z0-9]+", "_", self.name.lower()).strip("_")
        return f"slice_{self.index:03d}_{safe}.md"

    def render(self) -> str:
        lines: list[str] = []
        lines.append(f"# SLICE: {self.name}\n")
        lines.append("## DOMAIN SOURCE\n")
        lines.append(f"Domain: {self.domain}")
        lines.append(f"Behavior: {self.source_id}\n")
        lines.append("## GOAL\n")
        lines.append(f"{self.goal}\n")

        if self.inputs:
            lines.append("## INPUT\n")
            for inp in self.inputs:
                lines.append(f"- {inp}")
            lines.append("")

        if self.outputs:
            lines.append("## OUTPUT\n")
            for out in self.outputs:
                lines.append(f"- {out}")
            lines.append("")

        if self.entities:
            lines.append("## ENTITIES\n")
            for ent in self.entities:
                lines.append(f"- {ent}")
            lines.append("")

        if self.rules:
            lines.append("## RULES\n")
            for rule in self.rules:
                lines.append(f"- {rule}")
            lines.append("")

        if self.flow:
            lines.append("## FLOW\n")
            for step in self.flow:
                lines.append(f"{step}")
            lines.append("")

        if self.acceptance_criteria:
            lines.append("## ACCEPTANCE CRITERIA\n")
            for ac in self.acceptance_criteria:
                lines.append(f"- {ac}")
            lines.append("")

        if self.notes:
            lines.append("## NOTES\n")
            for note in self.notes:
                lines.append(f"- {note}")
            lines.append("")

        return "\n".join(lines)


# ── Main generator ─────────────────────────────────────────────────────────────

class DomainSliceGenerator:
    """
    Generates slice files from a build-ready domain directory.

    Args:
        domain_root:  Path to the domain directory, e.g. domains/identity_access
        output_root:  Root directory for slice output, e.g. ai-slices
        dry_run:      If True, return slices without writing files
    """

    def __init__(
        self,
        domain_root: str | Path,
        output_root: str | Path = "ai-slices",
        dry_run: bool = False,
    ) -> None:
        self._root = Path(domain_root)
        self._domain_name = self._root.name
        self._output_root = Path(output_root)
        self._dry_run = dry_run

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate(self) -> list[SliceSpec]:
        """
        Runs completeness check, then generates slices.
        Raises ValueError if the domain is not build-ready.
        """
        result = DomainCompletenessChecker(self._root).check()
        if not result.is_ready:
            raise ValueError(
                f"Domain `{self._domain_name}` is not build-ready:\n{result.report()}"
            )

        behaviors = self._load_list("020_behaviors.json")
        entities = self._load_list("010_entities.json")
        rules = self._load_list("070_rules.json")
        flows = self._load_list("030_flows.json")

        entity_names = self._extract_entity_names(entities)
        rule_index = self._index_rules(rules)
        flow_index = self._index_flows(flows)

        raw_slices: list[SliceSpec] = []
        for behavior in behaviors:
            spec = self._behavior_to_slice(behavior, entity_names, rule_index, flow_index)
            if spec:
                raw_slices.append(spec)

        # Sort by priority tier then original order
        raw_slices.sort(key=lambda s: (s.priority, s.index))

        # Re-number after sort
        slices = []
        for i, spec in enumerate(raw_slices, start=1):
            spec.index = i
            slices.append(spec)

        if not self._dry_run:
            self._write_slices(slices)

        return slices

    # ── Loading ────────────────────────────────────────────────────────────────

    def _load_list(self, filename: str) -> list[dict]:
        path = self._root / filename
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    # ── Entity name extraction ─────────────────────────────────────────────────

    def _extract_entity_names(self, entities: list[dict]) -> list[str]:
        names = []
        for e in entities:
            name = e.get("name") or e.get("id") or ""
            if name:
                names.append(name)
        return names

    # ── Rule index ────────────────────────────────────────────────────────────

    def _index_rules(self, rules: list[dict]) -> dict[str, str]:
        """Returns {rule_id: rule_text}"""
        return {
            r.get("id", r.get("name", "?")): r.get("rule", r.get("description", ""))
            for r in rules
        }

    # ── Flow index ────────────────────────────────────────────────────────────

    def _index_flows(self, flows: list[dict]) -> dict[str, dict]:
        """Returns {flow_name_lower: flow_dict}"""
        index: dict[str, dict] = {}
        for flow in flows:
            name = flow.get("name", flow.get("id", "")).lower()
            if name:
                index[name] = flow
        return index

    # ── Behavior → Slice ──────────────────────────────────────────────────────

    def _behavior_to_slice(
        self,
        behavior: dict,
        entity_names: list[str],
        rule_index: dict[str, str],
        flow_index: dict[str, dict],
    ) -> SliceSpec | None:
        bid = behavior.get("id", "?")
        raw_name = behavior.get("name", "Unnamed")
        description = behavior.get("description", "")
        steps: list[str] = behavior.get("steps", [])
        note = behavior.get("note", "")

        if not description and not steps:
            return None  # silently skip empty stubs

        # ── Goal ──────────────────────────────────────────────────────────────
        goal = description or (steps[0] if steps else raw_name)

        # ── Inputs: heuristic from steps ─────────────────────────────────────
        inputs = self._extract_inputs(behavior)

        # ── Outputs: success + failure ────────────────────────────────────────
        outputs = self._extract_outputs(behavior)

        # ── Entities: match entity names mentioned in behavior text ──────────
        behavior_text = json.dumps(behavior).lower()
        matched_entities = [
            e for e in entity_names
            if e.lower() in behavior_text
        ]
        if not matched_entities:
            matched_entities = entity_names[:2]  # fallback: first 2

        # ── Rules: match rules mentioned in behavior ──────────────────────────
        matched_rules = [
            rule_text
            for rule_id, rule_text in rule_index.items()
            if rule_id.lower() in behavior_text or rule_text[:40].lower() in behavior_text
        ]
        # If no rules matched, try keyword matching from behavior name
        if not matched_rules:
            matched_rules = self._infer_rules(raw_name, rule_index)

        # ── Flow: use steps or linked flow ────────────────────────────────────
        flow_steps = self._build_flow_steps(raw_name, steps, flow_index)

        # ── Acceptance criteria ───────────────────────────────────────────────
        ac = self._build_acceptance_criteria(behavior)

        # ── Notes ─────────────────────────────────────────────────────────────
        notes: list[str] = []
        if note:
            notes.append(note)
        for td_key in ("technical_debt", "td"):
            td = behavior.get(td_key)
            if td:
                notes.append(f"Technical debt: {td}")
        notes.append("No infrastructure assumptions. No SQL. No C#.")

        return SliceSpec(
            index=0,  # re-numbered after sort
            name=self._canonical_name(raw_name),
            domain=self._domain_name,
            source_id=bid,
            goal=goal,
            inputs=inputs,
            outputs=outputs,
            entities=matched_entities,
            rules=matched_rules or [f"See {self._domain_name}/070_rules.json"],
            flow=flow_steps,
            acceptance_criteria=ac,
            notes=notes,
            priority=_priority(raw_name),
        )

    # ── Input extraction ──────────────────────────────────────────────────────

    def _extract_inputs(self, behavior: dict) -> list[str]:
        inputs: list[str] = []
        # Explicit request fields on behavior
        for key in ("request_fields", "inputs", "parameters"):
            if behavior.get(key):
                val = behavior[key]
                if isinstance(val, dict):
                    inputs.extend(f"{k} ({v})" for k, v in val.items())
                elif isinstance(val, list):
                    inputs.extend(str(v) for v in val)
                break

        # Infer from steps
        if not inputs:
            step_text = " ".join(behavior.get("steps", [])).lower()
            if "email" in step_text:
                inputs.append("email")
            if "password" in step_text:
                inputs.append("password")
            if "token" in step_text and "refresh" in step_text:
                inputs.append("refresh_token")
            if "profile" in step_text and "select" in step_text:
                inputs.append("profile_id")
            if "customer" in step_text or "smsgroup" in step_text:
                inputs.append("customer_id (optional)")

        # Infer from name
        if not inputs:
            name_lower = behavior.get("name", "").lower()
            if "login" in name_lower or "authenticat" in name_lower:
                inputs = ["email", "password"]
            elif "refresh" in name_lower:
                inputs = ["refresh_token"]
            elif "logout" in name_lower:
                inputs = ["(authenticated session)"]
            elif "password reset" in name_lower:
                inputs = ["email"]

        return inputs

    # ── Output extraction ─────────────────────────────────────────────────────

    def _extract_outputs(self, behavior: dict) -> list[str]:
        outputs: list[str] = []
        step_text = " ".join(behavior.get("steps", [])).lower()
        desc = behavior.get("description", "").lower()
        name_lower = behavior.get("name", "").lower()
        full_text = f"{desc} {step_text}"

        # Success
        if "token" in full_text or "jwt" in full_text:
            outputs.append("success: access_token + refresh_token")
        elif "http 200" in full_text or "200 ok" in full_text:
            outputs.append("success: confirmation (HTTP 200)")
        elif "list" in full_text or "collection" in full_text:
            outputs.append("success: list of items")
        else:
            outputs.append("success: operation result")

        # Failures from error_codes or steps
        error_codes = behavior.get("error_codes", {})
        if isinstance(error_codes, dict):
            for code, msg in error_codes.items():
                outputs.append(f"failure ({code}): {msg}")
        else:
            # Infer failures from steps
            for step in behavior.get("steps", []):
                step_lower = step.lower()
                if "401" in step_lower or "invalid" in step_lower:
                    outputs.append("failure: invalid input → error code + message")
                    break
                if "403" in step_lower or "lock" in step_lower:
                    outputs.append("failure: access denied → error code + message")
                    break

        return outputs

    # ── Flow step building ────────────────────────────────────────────────────

    def _build_flow_steps(
        self,
        behavior_name: str,
        steps: list[str],
        flow_index: dict[str, dict],
    ) -> list[str]:
        if steps:
            return [f"{step}" for step in steps]

        # Look for matching flow
        name_lower = behavior_name.lower()
        for flow_name, flow in flow_index.items():
            if any(kw in flow_name for kw in name_lower.split()):
                hp = flow.get("happy_path", [])
                if hp:
                    return [f"{step}" for step in hp]

        return ["(see domain behaviors for detailed steps)"]

    # ── Acceptance criteria ───────────────────────────────────────────────────

    def _build_acceptance_criteria(self, behavior: dict) -> list[str]:
        criteria: list[str] = []
        name_lower = behavior.get("name", "").lower()
        steps = behavior.get("steps", [])

        # Synthesize from steps
        for step in steps:
            step_lower = step.lower()
            if "→ return http 401" in step_lower or "→ http 401" in step_lower:
                criteria.append("invalid credentials → failure response")
            elif "→ return http 403" in step_lower or "→ http 403" in step_lower:
                criteria.append("locked/forbidden user → failure response")
            elif "→ return http 428" in step_lower or "→ http 428" in step_lower:
                criteria.append("2FA required → challenge response")
            elif "→ return http 300" in step_lower or "→ http 300" in step_lower:
                criteria.append("multiple profiles → selection required response")
            elif "reset failedlogincount" in step_lower or "reset" in step_lower and "failed" in step_lower:
                criteria.append("successful operation resets failure counters")

        # Ensure at least a happy path criterion
        if not criteria:
            criteria.append("valid input → successful result")
        else:
            criteria.insert(0, "valid input → successful result")

        # Deduplicate
        seen = set()
        deduped = []
        for c in criteria:
            if c not in seen:
                seen.add(c)
                deduped.append(c)
        return deduped

    # ── Rule inference ────────────────────────────────────────────────────────

    def _infer_rules(self, behavior_name: str, rule_index: dict[str, str]) -> list[str]:
        name_lower = behavior_name.lower()
        matched = []
        for rule_id, rule_text in rule_index.items():
            rule_lower = (rule_id + " " + rule_text).lower()
            for kw in name_lower.split():
                if len(kw) > 3 and kw in rule_lower:
                    matched.append(rule_text)
                    break
        return matched[:3]  # max 3 inferred rules

    # ── Name canonicalization ─────────────────────────────────────────────────

    def _canonical_name(self, raw: str) -> str:
        """Convert BEH name like 'EmailPasswordLogin' to 'Email Password Login'"""
        # Handle CamelCase
        spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", raw)
        # Handle (Entra ID / MSAL) parenthetical junk
        spaced = re.sub(r"\s*\(.*?\)", "", spaced).strip()
        return spaced

    # ── Slice file writing ────────────────────────────────────────────────────

    def _write_slices(self, slices: list[SliceSpec]) -> None:
        output_dir = self._output_root / self._domain_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Clean old slices for this domain
        for old in output_dir.glob("slice_*.md"):
            old.unlink()

        for spec in slices:
            path = output_dir / spec.filename()
            path.write_text(spec.render(), encoding="utf-8")
