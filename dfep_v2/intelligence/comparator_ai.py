"""
dfep_v2/intelligence/comparator_ai.py — AI-powered capability comparator.

Instead of string-matching method names, this asks the LLM:
"Do these two capabilities serve the same customer need?"

RULES:
- Input: Capability from L0 + Capability from GreenAI
- Output: match_verdict with reasoning
- LLM must justify every verdict with evidence
- UNKNOWN is acceptable — hallucination is not

OUTPUT:
{
  "match": true | false | "partial",
  "match_reason": "...",
  "difference": "Template support missing in GreenAI",
  "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE",
  "missing_in_greenai": ["merge field substitution", "profile visibility filter"],
  "extra_in_greenai": [],
  "confidence": 0.91,
  "action": "MUST_BUILD" | "DEFERRED" | "ACCEPTED" | "NO_ACTION" | "REVIEW"
}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

@dataclass
class AIComparisonResult:
    l0_id: str
    greenai_id: str
    match: str              # "true" | "false" | "partial"
    match_reason: str
    difference: str
    severity: str           # CRITICAL / HIGH / MEDIUM / LOW / NONE
    missing_in_greenai: list[str] = field(default_factory=list)
    extra_in_greenai: list[str] = field(default_factory=list)
    confidence: float = 0.0
    action: str = "REVIEW"  # MUST_BUILD / DEFERRED / ACCEPTED / NO_ACTION / REVIEW


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a Functional Equivalence Analyst.

Your job: determine if two software capabilities serve the SAME customer need.

STRICT RULES:
1. Compare INTENT and OUTCOME — not implementation details
2. A different method name does NOT mean different capability
3. A different flow CAN mean different behavior — judge by customer impact
4. If uncertain → set confidence < 0.8 and note it in match_reason
5. Output MUST be valid JSON with exactly the requested keys
6. severity = CRITICAL only if customer CANNOT do the same thing
"""

# NOTE: CopilotAIProcessor has a fixed system message.
# Comparison rules are embedded in the user prompt below.
_USER_PROMPT_TEMPLATE = """STRICT COMPARISON RULES:
- Compare INTENT and OUTCOME, not implementation details
- A different method name does NOT mean different capability
- If uncertain → set confidence < 0.8 and note in match_reason
- Output MUST be valid JSON with exactly the requested keys
- severity = CRITICAL only if customer CANNOT do the same thing


Compare these two capabilities:

## LEVEL 0 (source of truth)
{l0_json}

## GREENAI (implementation target)
{greenai_json}

Question: "Can a customer achieve the same outcome with GreenAI as with Level 0?"

Return JSON:
{{
  "match": "true" | "false" | "partial",
  "match_reason": "one paragraph explaining your verdict",
  "difference": "what is different, or empty string if fully matched",
  "severity": "CRITICAL | HIGH | MEDIUM | LOW | NONE",
  "missing_in_greenai": ["list of things in L0 that GreenAI does not have"],
  "extra_in_greenai": ["list of things GreenAI has that L0 does not"],
  "confidence": 0.0,
  "action": "MUST_BUILD | DEFERRED | ACCEPTED | NO_ACTION | REVIEW"
}}

Severity guide:
- CRITICAL: customer cannot accomplish the same thing at all
- HIGH: customer can do it but behavior differs significantly
- MEDIUM: minor behavioral differences or edge cases
- LOW: implementation/cosmetic difference only
- NONE: functionally equivalent
"""


# ---------------------------------------------------------------------------
# Comparator
# ---------------------------------------------------------------------------

class ComparatorAI:
    """
    AI-powered capability comparator.

    Usage:
        comp = ComparatorAI(ai_processor)
        result = comp.compare(l0_cap, greenai_cap)
        results = comp.compare_many(l0_caps, greenai_caps)
    """

    def __init__(self, ai_processor):
        self._ai = ai_processor  # Skal være lokal LLM (Copilot chat)

    # ------------------------------------------------------------------
    def compare(self, l0_cap: Any, greenai_cap: Any) -> AIComparisonResult:
        """Compare one L0 capability against one GreenAI capability."""
        l0_dict = self._cap_to_dict(l0_cap)
        ga_dict = self._cap_to_dict(greenai_cap)

        prompt = _USER_PROMPT_TEMPLATE.format(
            l0_json=json.dumps(l0_dict, indent=2, ensure_ascii=False)[:3000],
            greenai_json=json.dumps(ga_dict, indent=2, ensure_ascii=False)[:3000],
        )

        raw = self._ai.process(
            asset={"id": f"compare_{l0_cap.capability_id}_vs_{greenai_cap.capability_id}", "type": "comparison"},
            stage="capability_comparison",
            prompt=prompt,
        )

        return self._parse(raw, l0_cap.capability_id, greenai_cap.capability_id)

    # ------------------------------------------------------------------
    def compare_missing(self, l0_cap: Any) -> AIComparisonResult:
        """Assess a capability that exists in L0 but is completely absent in GreenAI."""
        l0_dict = self._cap_to_dict(l0_cap)

        prompt = f"""
The following capability exists in Level 0 but is COMPLETELY ABSENT in GreenAI.

## LEVEL 0 CAPABILITY
{json.dumps(l0_dict, indent=2, ensure_ascii=False)[:3000]}

Assess the impact:
- What can a customer NOT do because this is missing?
- What is the severity?
- What action should be taken?

Return JSON:
{{
  "match": "false",
  "match_reason": "capability is absent in GreenAI",
  "difference": "describe what customer cannot do",
  "severity": "CRITICAL | HIGH | MEDIUM | LOW | NONE",
  "missing_in_greenai": ["full list of absent functionality"],
  "extra_in_greenai": [],
  "confidence": 0.0,
  "action": "MUST_BUILD | DEFERRED | ACCEPTED | REVIEW"
}}
"""
        raw = self._ai.process(
            asset={"id": f"missing_{l0_cap.capability_id}", "type": "missing_analysis"},
            stage="gap_analysis",
            prompt=prompt,
        )
        return self._parse(raw, l0_cap.capability_id, "MISSING")

    # ------------------------------------------------------------------
    def compare_many(
        self,
        l0_caps: list,
        greenai_caps: list,
        missing_l0: list | None = None,
    ) -> list[AIComparisonResult]:
        results: list[AIComparisonResult] = []

        # Build lookup by normalized id
        ga_by_id = {c.capability_id.split(".", 1)[-1].lower(): c for c in greenai_caps}

        for l0_cap in l0_caps:
            l0_key = l0_cap.capability_id.split(".", 1)[-1].lower()
            if l0_key in ga_by_id:
                results.append(self.compare(l0_cap, ga_by_id[l0_key]))
            else:
                results.append(self.compare_missing(l0_cap))

        # Extra GreenAI-only capabilities
        l0_keys = {c.capability_id.split(".", 1)[-1].lower() for c in l0_caps}
        for ga_cap in greenai_caps:
            ga_key = ga_cap.capability_id.split(".", 1)[-1].lower()
            if ga_key not in l0_keys:
                results.append(AIComparisonResult(
                    l0_id="N/A",
                    greenai_id=ga_cap.capability_id,
                    match="extra",
                    match_reason="Exists in GreenAI but not in Level 0",
                    difference="",
                    severity="NONE",
                    extra_in_greenai=[ga_cap.capability_name],
                    confidence=1.0,
                    action="ACCEPTED",
                ))

        return results

    # ------------------------------------------------------------------
    def _cap_to_dict(self, cap) -> dict:
        if hasattr(cap, "__dict__"):
            return {k: v for k, v in cap.__dict__.items() if v is not None}
        return dict(cap)

    def _parse(self, raw: dict, l0_id: str, greenai_id: str) -> AIComparisonResult:
        confidence = 0.5
        try:
            confidence = float(raw.get("confidence", 0.5))
        except (ValueError, TypeError):
            pass

        match_val = str(raw.get("match", "false")).lower()
        if match_val not in ("true", "false", "partial", "extra"):
            match_val = "false"

        return AIComparisonResult(
            l0_id=l0_id,
            greenai_id=greenai_id,
            match=match_val,
            match_reason=str(raw.get("match_reason", "")),
            difference=str(raw.get("difference", "")),
            severity=str(raw.get("severity", "HIGH")).upper(),
            missing_in_greenai=[str(x) for x in raw.get("missing_in_greenai", [])],
            extra_in_greenai=[str(x) for x in raw.get("extra_in_greenai", [])],
            confidence=confidence,
            action=str(raw.get("action", "REVIEW")).upper(),
        )
