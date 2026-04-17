"""
dfep_v3/parser/response_parser.py

Parses Copilot's JSON responses into structured Python objects.

Copilot responds to the capability/comparison prompts with JSON.
This parser converts that JSON into typed objects the pipeline can use.

Handles:
- Markdown fences (```json ... ```) that Copilot may wrap around output
- Missing/malformed fields (graceful defaults)
- Validation: flags capabilities with confidence < 0.80 as LOW_CONFIDENCE
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass
class ParsedCapability:
    id: str
    intent: str
    business_value: str
    flow: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    is_unknown: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "intent": self.intent,
            "business_value": self.business_value,
            "flow": self.flow,
            "constraints": self.constraints,
            "rules": self.rules,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "is_unknown": self.is_unknown,
        }


# Canonical semantic match types (TASK D)
# Backwards-compatible with legacy "true" | "partial" | "false"
MATCH_EXACT = "MATCH_EXACT"               # Functionally identical (same customer outcome, same constraints)
MATCH_CLEAN_REBUILD = "MATCH_CLEAN_REBUILD" # Same outcome, different architecture (clean rebuild, accepted)
MATCH_PARTIAL = "MATCH_PARTIAL"           # Exists but reduced scope or different constraints
MISSING = "MISSING"                       # Absent in GreenAI
INTENT_DRIFT = "INTENT_DRIFT"             # Implemented but different intent/scope than L0
EXTRA_NON_EQUIVALENT = "EXTRA_NON_EQUIVALENT"  # GreenAI has extra not mapping to any L0 cap

# Legacy values for backward compatibility
_LEGACY_MATCH_MAP = {
    "true": MATCH_EXACT,
    "partial": MATCH_PARTIAL,
    "false": MISSING,
}

# Groups for match_score calculation
_MATCHED_TYPES = {MATCH_EXACT, MATCH_CLEAN_REBUILD, "true"}
_PARTIAL_TYPES = {MATCH_PARTIAL, "partial"}
_MISSING_TYPES = {MISSING, INTENT_DRIFT, "false"}
# EXTRA_NON_EQUIVALENT is not counted in L0 comparison totals

_ALL_MATCH_TYPES = {
    MATCH_EXACT, MATCH_CLEAN_REBUILD, MATCH_PARTIAL,
    MISSING, INTENT_DRIFT, EXTRA_NON_EQUIVALENT,
    "true", "partial", "false",  # legacy accepted
}


@dataclass
class ParsedComparison:
    l0_capability_id: str
    ga_capability_id: str | None
    match: str          # semantic type — see constants above
    severity: str       # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    difference: str
    impact: str
    action: str

    def to_dict(self) -> dict:
        return {
            "l0_capability_id": self.l0_capability_id,
            "ga_capability_id": self.ga_capability_id,
            "match": self.match,
            "severity": self.severity,
            "difference": self.difference,
            "impact": self.impact,
            "action": self.action,
        }


@dataclass
class CapabilityParseResult:
    domain: str
    source: str
    capabilities: list[ParsedCapability] = field(default_factory=list)
    unknown_hints: list[str] = field(default_factory=list)
    low_confidence: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)


@dataclass
class ComparisonParseResult:
    domain: str
    comparisons: list[ParsedComparison] = field(default_factory=list)
    coverage_score: float = 0.0   # deprecated alias — use match_score
    match_score: float = 0.0      # (matched + partial) / total_l0
    total_l0_count: int = 0
    matched_count: int = 0        # match == "true"
    partial_count: int = 0        # match == "partial"
    missing_count: int = 0        # match == "false"
    critical_count: int = 0
    high_count: int = 0
    summary: str = ""
    parse_errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class ResponseParser:
    """
    Parses Copilot's JSON response from capability or comparison prompts.

    Usage:
        parser = ResponseParser()
        cap_result = parser.parse_capabilities(json_text)
        cmp_result = parser.parse_comparisons(json_text)
    """

    def parse_capabilities(self, raw_text: str) -> CapabilityParseResult:
        """Parse Copilot's capability extraction response."""
        data, error = self._parse_json(raw_text)
        if error:
            return CapabilityParseResult(
                domain="UNKNOWN",
                source="UNKNOWN",
                parse_errors=[f"JSON parse failed: {error}"],
            )

        result = CapabilityParseResult(
            domain=data.get("domain", "UNKNOWN"),
            source=data.get("source", "UNKNOWN"),
            unknown_hints=data.get("unknown_hints", []),
        )

        for raw_cap in data.get("capabilities", []):
            try:
                confidence = float(raw_cap.get("confidence", 0.0))
                cap = ParsedCapability(
                    id=str(raw_cap.get("id", "UNKNOWN")),
                    intent=str(raw_cap.get("intent", "")),
                    business_value=str(raw_cap.get("business_value", "")),
                    flow=list(raw_cap.get("flow", [])),
                    constraints=list(raw_cap.get("constraints", [])),
                    rules=list(raw_cap.get("rules", [])),
                    evidence=list(raw_cap.get("evidence", [])),
                    confidence=confidence,
                    is_unknown=confidence < 0.80,
                )
                if cap.is_unknown:
                    result.low_confidence.append(cap.id)
                result.capabilities.append(cap)
            except Exception as e:
                result.parse_errors.append(f"Skipped capability: {e} — raw: {str(raw_cap)[:80]}")

        return result

    def parse_comparisons(self, raw_text: str) -> ComparisonParseResult:
        """Parse Copilot's comparison response."""
        data, error = self._parse_json(raw_text)
        if error:
            return ComparisonParseResult(
                domain="UNKNOWN",
                parse_errors=[f"JSON parse failed: {error}"],
            )

        result = ComparisonParseResult(
            domain=data.get("domain", "UNKNOWN"),
            coverage_score=float(data.get("coverage_score", 0.0)),
            critical_count=int(data.get("critical_count", 0)),
            high_count=int(data.get("high_count", 0)),
            summary=str(data.get("summary", "")),
        )

        for raw_cmp in data.get("comparisons", []):
            try:
                raw_match = str(raw_cmp.get("match", "false"))
                match = raw_match.lower()
                severity = str(raw_cmp.get("severity", "LOW")).upper()

                # Normalise legacy match values to canonical types
                if match in _LEGACY_MATCH_MAP:
                    match = _LEGACY_MATCH_MAP[match]
                elif raw_match in _ALL_MATCH_TYPES:
                    match = raw_match  # preserve original case for semantic types
                elif raw_match.upper() in _ALL_MATCH_TYPES:
                    match = raw_match.upper()
                if match not in _ALL_MATCH_TYPES:
                    match = MISSING  # unknown value treated as missing
                if severity not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
                    severity = "MEDIUM"

                cmp = ParsedComparison(
                    l0_capability_id=str(raw_cmp.get("l0_capability_id", "UNKNOWN")),
                    ga_capability_id=raw_cmp.get("ga_capability_id"),
                    match=match,
                    severity=severity,
                    difference=str(raw_cmp.get("difference", "")),
                    impact=str(raw_cmp.get("impact", "")),
                    action=str(raw_cmp.get("action", "")),
                )
                result.comparisons.append(cmp)
            except Exception as e:
                result.parse_errors.append(f"Skipped comparison: {e} — raw: {str(raw_cmp)[:80]}")

        # Recount from parsed data using semantic match types
        # EXTRA_NON_EQUIVALENT not counted in L0 total (it's additive)
        l0_comparisons = [c for c in result.comparisons if c.match != EXTRA_NON_EQUIVALENT]
        result.critical_count = sum(1 for c in l0_comparisons if c.severity == "CRITICAL" and c.match not in _MATCHED_TYPES)
        result.high_count = sum(1 for c in l0_comparisons if c.severity == "HIGH" and c.match not in _MATCHED_TYPES)
        total = len(l0_comparisons)
        result.total_l0_count = total
        result.matched_count = sum(1 for c in l0_comparisons if c.match in _MATCHED_TYPES)
        result.partial_count = sum(1 for c in l0_comparisons if c.match in _PARTIAL_TYPES)
        result.missing_count = sum(1 for c in l0_comparisons if c.match in _MISSING_TYPES)
        matched = result.matched_count + result.partial_count
        result.match_score = matched / total if total else 0.0
        result.coverage_score = result.match_score  # alias kept for backwards compat

        return result

    # ------------------------------------------------------------------
    def _parse_json(self, raw_text: str) -> tuple[dict, str | None]:
        """Extract and parse JSON from raw text (handles markdown fences)."""
        raw = raw_text.strip()

        # Strip markdown code fences
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if fence:
            raw = fence.group(1)
        else:
            # Find first { ... } block
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                raw = m.group()

        try:
            return json.loads(raw), None
        except json.JSONDecodeError as e:
            return {}, str(e)
