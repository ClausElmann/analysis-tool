"""
dfep_v3/intelligence/capability_validator.py

Validates AI-generated capabilities against deterministically extracted code facts.

GOVERNANCE RULE (DFEP_AI_BOUNDS):
  "AI output is NEVER truth — only valid if validated against facts OR approved by Architect."

Validation modes:
  DEFAULT MODE:
    - INVALID: capability has phantom refs (cited file:line not in extracted facts) → REJECTED
    - WARNING: step has no file:line ref at all → accepted with warning
  STRICT MODE (strict_mode=True):
    - INVALID: phantom refs (same as default)
    - INVALID: uncited non-trivial steps (no ref AND step appears to describe implementation)
    - WARNING: uncited trivial steps only (entry-point/exit descriptions)

Step classification:
  - Trivial: first step, or contains "receives/accepts/called/request" language
  - Non-trivial: describes DB ops, method calls, validations, persistence → must cite evidence

Evidence detection:
  1. Explicit (evidence: file.cs:NNN) markers
  2. Any file.ext:NNN pattern in step text
  3. Checked against known_refs set built from CodeFact.file values

Usage:
    validator = CapabilityValidator(facts=l0_facts, strict_mode=False)
    report = validator.validate_all(capabilities)
    valid = report.accepted  # only these go to comparison
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from dfep_v3.extractor.extractor_bridge import CodeFact
from dfep_v3.parser.response_parser import ParsedCapability


# Matches patterns like: ServiceAlert.Services/Foo/Bar.cs:42
# Also handles: GreenAi.Api/Features/Foo.sql:1
_FILE_LINE_RE = re.compile(
    r"[\w/\\.\-]+\.\w{2,4}:\d+",
    re.IGNORECASE,
)

# Explicit (evidence: ...) or evidence: ... markers
_EVIDENCE_MARKER_RE = re.compile(
    r"\(evidence:\s*([^)]+)\)",
    re.IGNORECASE,
)

# Non-trivial step keywords — these steps MUST have evidence in strict mode
_NONTRIVIAL_KEYWORDS = (
    "select", "insert", "update", "delete", "query", "queries",
    "repository", "handler", "validates", "validation", "calls",
    "returns", "fetches", "executes", "persists", "reads from",
    "writes to", "joins", "filters", "loads", "saves", "maps",
    "resolves", "invokes", ".sql", ".cs:", "async", "await",
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class FlowStepCheck:
    """Validation result for a single flow step in a capability."""
    step_index: int
    step_text: str
    cited_refs: list[str]           # all file:line refs found in step text
    verified_refs: list[str]        # refs that exist in the fact set
    phantom_refs: list[str]         # refs NOT in the fact set → INVALID
    has_any_ref: bool               # True if step cited at least one file:line
    is_trivial: bool                # True = entry/exit step, no evidence required


@dataclass
class CapabilityValidationResult:
    """Validation result for a single capability."""
    capability_id: str
    valid: bool                     # False = REJECTED
    errors: list[str] = field(default_factory=list)     # INVALID — phantom refs or strict uncited
    warnings: list[str] = field(default_factory=list)   # WARNING — uncited trivial steps
    step_checks: list[FlowStepCheck] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Aggregated validation report for a batch of capabilities."""
    accepted: list[ParsedCapability]
    rejected: list[ParsedCapability]
    results: list[CapabilityValidationResult]
    fact_count: int

    @property
    def accepted_ids(self) -> list[str]:
        return [c.id for c in self.accepted]

    @property
    def rejected_ids(self) -> list[str]:
        return [c.id for c in self.rejected]

    def summary_lines(self) -> list[str]:
        lines = [
            f"Validated {len(self.accepted) + len(self.rejected)} capabilities "
            f"against {self.fact_count} facts",
            f"  Accepted: {len(self.accepted)} | Rejected: {len(self.rejected)}",
        ]
        for r in self.results:
            if not r.valid:
                lines.append(f"  REJECTED: {r.capability_id}")
                for e in r.errors:
                    lines.append(f"    ERROR: {e}")
            elif r.warnings:
                lines.append(f"  WARN: {r.capability_id} — {len(r.warnings)} uncited step(s)")
        return lines


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class CapabilityValidator:
    """
    Validates AI-generated capabilities against extracted code facts.

    Args:
        facts:       Extracted CodeFact list to build the known-refs set from.
        strict_mode: If True, uncited non-trivial steps also cause INVALID rejection.
                     If False (default), uncited steps produce WARNING only.
    """

    def __init__(self, facts: list[CodeFact], strict_mode: bool = False):
        self._fact_keys = self._build_fact_keys(facts)
        self._fact_count = len(facts)
        self._strict_mode = strict_mode

    # ------------------------------------------------------------------
    def validate_all(
        self,
        capabilities: list[ParsedCapability],
    ) -> ValidationReport:
        """
        Validate all capabilities. Returns ValidationReport with accepted/rejected split.
        """
        accepted: list[ParsedCapability] = []
        rejected: list[ParsedCapability] = []
        results: list[CapabilityValidationResult] = []

        for cap in capabilities:
            result = self._validate_capability(cap)
            results.append(result)
            if result.valid:
                accepted.append(cap)
            else:
                rejected.append(cap)

        return ValidationReport(
            accepted=accepted,
            rejected=rejected,
            results=results,
            fact_count=self._fact_count,
        )

    # ------------------------------------------------------------------
    def _validate_capability(self, cap: ParsedCapability) -> CapabilityValidationResult:
        """Validate a single capability against the fact set."""
        result = CapabilityValidationResult(capability_id=cap.id, valid=True)

        for idx, step_text in enumerate(cap.flow):
            step_check = self._check_step(idx, step_text)
            result.step_checks.append(step_check)

            if step_check.phantom_refs:
                # INVALID: cited a ref that is NOT in extracted facts → phantom hallucination
                result.valid = False
                for phantom in step_check.phantom_refs:
                    result.errors.append(
                        f"INVALID — Step {idx + 1}: phantom ref '{phantom}' "
                        f"not found in extracted facts"
                    )

            elif not step_check.has_any_ref:
                if self._strict_mode and not step_check.is_trivial:
                    # INVALID (strict): non-trivial step with no evidence at all
                    result.valid = False
                    result.errors.append(
                        f"INVALID (strict) — Step {idx + 1}: no evidence ref for "
                        f"non-trivial step: '{step_text[:80]}'"
                    )
                else:
                    # WARNING: high-level or trivial step — acceptable without evidence
                    result.warnings.append(
                        f"WARNING — Step {idx + 1}: no file:line reference "
                        f"(trivial={step_check.is_trivial}): '{step_text[:60]}'"
                    )

        return result

    # ------------------------------------------------------------------
    def _check_step(self, idx: int, step_text: str) -> FlowStepCheck:
        """Extract and verify all file:line refs in a flow step."""
        cited = self._extract_refs(step_text)

        verified = [r for r in cited if self._is_known(r)]
        phantom = [r for r in cited if not self._is_known(r)]

        return FlowStepCheck(
            step_index=idx,
            step_text=step_text,
            cited_refs=cited,
            verified_refs=verified,
            phantom_refs=phantom,
            has_any_ref=bool(cited),
            is_trivial=self._is_trivial_step(idx, step_text),
        )

    # ------------------------------------------------------------------
    def _extract_refs(self, text: str) -> list[str]:
        """
        Extract all file:line refs from text.
        Normalises path separators, strips surrounding parens/brackets.
        """
        refs: set[str] = set()

        # Primary: explicit (evidence: ...) markers
        for m in _EVIDENCE_MARKER_RE.finditer(text):
            inner = m.group(1).strip()
            for ref in _FILE_LINE_RE.findall(inner):
                refs.add(self._normalise(ref))

        # Secondary: any file:line pattern in the step text
        for ref in _FILE_LINE_RE.findall(text):
            refs.add(self._normalise(ref))

        return sorted(refs)

    # ------------------------------------------------------------------
    def _is_known(self, ref: str) -> bool:
        """Check if a normalised file:line ref exists in the fact set."""
        if ref in self._fact_keys:
            return True
        # Also check by filename:line suffix only (handles path prefix differences)
        _, _, suffix = ref.rpartition("/")
        return any(k.endswith(suffix) for k in self._fact_keys)

    # ------------------------------------------------------------------
    @staticmethod
    def _is_trivial_step(idx: int, step_text: str) -> bool:
        """
        Returns True if step is a high-level entry/exit description that
        cannot reasonably be expected to cite a source file:line ref.

        Rule:
          - Step 0 (first step) is always trivial — it describes the incoming request
          - Steps containing only entry-point/exit language are trivial
          - Steps containing SQL/method/code language are non-trivial
        """
        if idx == 0:
            return True  # First step = entry point, no code evidence expected

        lower = step_text.lower()

        # Explicit trivial markers (entry/exit descriptions)
        trivial_markers = (
            "receives", "accepts", "called", "request arrives",
            "caller sends", "user calls", "endpoint called",
            "handler is invoked", "input:", "api receives",
            "returns response", "returns result", "returns error",
            "response is sent", "sends back",
        )
        if any(m in lower for m in trivial_markers):
            return True

        # If the step contains non-trivial implementation keywords → not trivial
        if any(k in lower for k in _NONTRIVIAL_KEYWORDS):
            return False

        # Short high-level steps with no implementation language = trivial
        return len(step_text) < 60

    # ------------------------------------------------------------------
    @staticmethod
    def _build_fact_keys(facts: list[CodeFact]) -> set[str]:
        """
        Build a normalised set of all fact file:line keys.
        CodeFact.file is already in "relative/path.cs:line" format.
        """
        keys: set[str] = set()
        for fact in facts:
            keys.add(CapabilityValidator._normalise(fact.file))
        return keys

    @staticmethod
    def _normalise(ref: str) -> str:
        """Normalise path separators to forward slash, strip whitespace."""
        return ref.replace("\\", "/").strip()


    @staticmethod
    def _normalise(ref: str) -> str:
        """Normalise path separators to forward slash, strip whitespace."""
        return ref.replace("\\", "/").strip()
