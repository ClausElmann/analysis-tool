"""
dfep_v2/intelligence/capability_builder.py — Layer 2 Intelligence.

Takes a GROUP of CodeFacts (related methods from same domain) and asks the LLM:
"What is the functional capability these code facts collectively implement?"

STRICT RULES:
- LLM ONLY uses facts provided — no invention
- If uncertain → mark field as "UNKNOWN"
- Output must be strict JSON
- All flows/entities in output must trace back to provided facts

OUTPUT per capability:
{
  "capability_id": "templates.list_for_profile",
  "capability_name": "List templates for profile",
  "intent": "...",
  "business_value": "...",
  "inputs": ["customerId", "profileId"],
  "outputs": ["List<Template>"],
  "side_effects": [],
  "rules": ["Customer isolation", "Profile visibility filter"],
  "flow": ["Read ProfileId from JWT", "Query MessageTemplates JOIN Access", "Return list"],
  "constraints": ["RequireAuthorization", "CustomerId must match JWT"],
  "confidence": 0.95,
  "unknowns": [],
  "evidence": ["file.cs:121 – GetTemplatesForSmsAndEmail"]
}
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Capability:
    capability_id: str
    capability_name: str
    domain: str
    intent: str = ""
    business_value: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    flow: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    confidence: float = 0.0
    unknowns: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    source: str = "Unknown"   # "L0" | "GreenAI"
    http_route: Optional[str] = None


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a Functional Capability Extractor — a domain analysis engine.

STRICT RULES:
1. ONLY use the code facts provided to you — never invent flows, entities, or rules
2. If you cannot determine something from the facts → use "UNKNOWN" as the value
3. Focus on WHAT the code does for the customer, not HOW it does it
4. Output MUST be valid JSON with exactly the requested keys
5. Every item in "flow" must be traceable to a provided fact
6. "confidence" is your certainty that the output reflects the facts (0.0–1.0)
"""

# NOTE: CopilotAIProcessor has a fixed system message.
# Anti-hallucination rules are embedded in the user prompt below.
_USER_PROMPT_TEMPLATE = """STRICT EXTRACTION RULES:
- Use ONLY the code facts provided — never invent flows, entities, or rules
- If uncertain about any field → use "UNKNOWN"
- confidence = 1.0 only if ALL fields are fully determined from facts
- confidence < 0.8 if more than 2 unknowns
- Every item in "flow" must be traceable to a provided fact


Domain: {domain}
Source: {source}

I have extracted the following code facts from {file_count} file(s):

{facts_json}

Based ONLY on these facts, extract the functional capability.

Return JSON with exactly these keys:
{{
  "capability_id": "{domain_lower}.{suggested_id}",
  "capability_name": "short human label",
  "intent": "one sentence: what does this capability let a customer DO?",
  "business_value": "one sentence: why does this matter?",
  "inputs": ["list of input parameters"],
  "outputs": ["list of return values"],
  "side_effects": ["DB inserts/updates that happen as a result"],
  "rules": ["business/security rules enforced"],
  "flow": ["ordered steps the code executes"],
  "constraints": ["authorization, validation, limits"],
  "confidence": 0.0,
  "unknowns": ["things you could not determine from the facts"],
  "evidence": ["{evidence_list}"]
}}

IMPORTANT:
- If facts show no HTTP endpoint → leave http_route out
- If facts show no SQL → leave side_effects empty
- confidence = 1.0 only if ALL fields are fully determined from facts
- confidence < 0.8 if more than 2 unknowns
"""


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class CapabilityBuilder:
    """
    Groups related CodeFacts and asks the LLM to synthesize a Capability.

    Usage:
        builder = CapabilityBuilder(ai_processor)
        cap = builder.build_from_facts(facts, domain="Templates", source="L0")
    """

    MIN_CONFIDENCE = 0.65  # Below this → capability is marked LOW_CONFIDENCE

    def __init__(self, ai_processor):
        """
        ai_processor: CopilotAIProcessor or StubAIProcessor from core/ai_processor.py
        """
        self._ai = ai_processor

    def build_from_facts(
        self,
        facts: list[Any],  # list[CodeFact]
        domain: str,
        source: str,
        suggested_id: str = "unknown_capability",
    ) -> Capability:
        """
        Build a single Capability from a list of related CodeFacts.
        """
        if not facts:
            return Capability(
                capability_id=f"{domain.lower()}.empty",
                capability_name="No facts provided",
                domain=domain,
                confidence=0.0,
                unknowns=["No code facts were extracted"],
                source=source,
            )

        # Serialize facts for LLM
        facts_dicts = [self._fact_to_dict(f) for f in facts]
        evidence_list = [f"{f.file} – {f.method}" for f in facts if hasattr(f, "file")]

        prompt = _USER_PROMPT_TEMPLATE.format(
            domain=domain,
            source=source,
            file_count=len(facts),
            facts_json=json.dumps(facts_dicts, indent=2, ensure_ascii=False)[:6000],
            domain_lower=domain.lower(),
            suggested_id=suggested_id,
            evidence_list=", ".join(evidence_list[:5]),
        )

        raw = self._ai.process(
            asset={"id": f"dfep_{domain}_{suggested_id}", "type": "capability"},
            stage="capability_extraction",
            prompt=prompt,
        )

        return self._parse_capability(raw, domain, source, evidence_list)

    def build_many(
        self,
        grouped_facts: dict[str, list],  # {cap_id_hint: [CodeFact, ...]}
        domain: str,
        source: str,
    ) -> list[Capability]:
        """
        Build capabilities for multiple fact groups.
        """
        caps: list[Capability] = []
        for suggested_id, facts in grouped_facts.items():
            cap = self.build_from_facts(facts, domain, source, suggested_id)
            caps.append(cap)
        return caps

    # ------------------------------------------------------------------
    def _fact_to_dict(self, fact) -> dict:
        if hasattr(fact, "__dict__"):
            d = {k: v for k, v in fact.__dict__.items() if v and k != "raw_snippet"}
            return d
        return dict(fact)

    def _parse_capability(
        self, raw: dict, domain: str, source: str, evidence: list[str]
    ) -> Capability:
        # raw may have extra keys from validate_output — focus on our keys
        confidence = float(raw.get("confidence", 0.5))
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except ValueError:
                confidence = 0.5

        cap = Capability(
            capability_id=raw.get("capability_id", f"{domain.lower()}.unknown"),
            capability_name=raw.get("capability_name", "Unknown"),
            domain=domain,
            intent=raw.get("intent", ""),
            business_value=raw.get("business_value", ""),
            inputs=self._to_list(raw.get("inputs", [])),
            outputs=self._to_list(raw.get("outputs", [])),
            side_effects=self._to_list(raw.get("side_effects", [])),
            rules=self._to_list(raw.get("rules", [])),
            flow=self._to_list(raw.get("flow", [])),
            constraints=self._to_list(raw.get("constraints", [])),
            confidence=confidence,
            unknowns=self._to_list(raw.get("unknowns", [])),
            evidence=self._to_list(raw.get("evidence", evidence)),
            source=source,
            http_route=raw.get("http_route"),
        )

        if cap.confidence < self.MIN_CONFIDENCE:
            cap.unknowns.append(f"LOW_CONFIDENCE: {cap.confidence:.2f} — review manually")

        return cap

    @staticmethod
    def _to_list(val) -> list:
        if isinstance(val, list):
            return [str(v) for v in val if v]
        if val:
            return [str(val)]
        return []
