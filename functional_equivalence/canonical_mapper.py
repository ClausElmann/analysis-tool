"""
canonical_mapper.py — Normalize L0 and GreenAI capabilities to a shared canonical model.

The canonical model is the neutral comparison layer:
{
    "capability": "Send SMS from template",
    "inputs": ["TemplateId", "Recipient"],
    "outputs": ["Delivered SMS"],
    "side_effects": ["OutboundMessages row"],
    "rules": ["Customer isolation", "Profile visibility"],
    "flow": ["Load template", "Resolve content", "Send"],
    "source": "L0" | "GreenAI",
    "evidence": ["file.cs:123 – MethodName"],
    "domain": "Templates",
    "id": "templates.send_sms_from_template",
    "http_route": null,
}

Both L0 and GreenAI capabilities are mapped to this format for comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from functional_equivalence.capability_extractor_l0 import CapabilityL0
from functional_equivalence.capability_extractor_greenai import CapabilityGreenAI


# ---------------------------------------------------------------------------
# Canonical data model
# ---------------------------------------------------------------------------

@dataclass
class CanonicalCapability:
    id: str
    name: str
    domain: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    flow: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    source: str = "Unknown"             # "L0" or "GreenAI"
    http_route: Optional[str] = None


# ---------------------------------------------------------------------------
# Mapper
# ---------------------------------------------------------------------------

class CanonicalMapper:
    """
    Converts L0 and GreenAI capabilities to CanonicalCapability instances.

    Usage:
        mapper = CanonicalMapper()
        canonical_l0 = mapper.from_l0(caps_l0)
        canonical_greenai = mapper.from_greenai(caps_greenai)
    """

    def from_l0(self, caps: list[CapabilityL0]) -> list[CanonicalCapability]:
        result = []
        for c in caps:
            result.append(CanonicalCapability(
                id=c.id,
                name=c.name,
                domain=c.domain,
                inputs=list(c.inputs),
                outputs=list(c.outputs),
                side_effects=list(c.side_effects),
                rules=list(c.rules),
                flow=list(c.flow),
                evidence=list(c.evidence),
                source="L0",
                http_route=None,
            ))
        return result

    def from_greenai(self, caps: list[CapabilityGreenAI]) -> list[CanonicalCapability]:
        result = []
        for c in caps:
            result.append(CanonicalCapability(
                id=c.id,
                name=c.name,
                domain=c.domain,
                inputs=list(c.inputs),
                outputs=list(c.outputs),
                side_effects=list(c.side_effects),
                rules=list(c.rules),
                flow=list(c.flow),
                evidence=list(c.evidence),
                source="GreenAI",
                http_route=c.http_route,
            ))
        return result

    def merge(
        self,
        l0_caps: list[CanonicalCapability],
        greenai_caps: list[CanonicalCapability],
    ) -> list[CanonicalCapability]:
        """Return combined list (no deduplication — used by comparator)."""
        return l0_caps + greenai_caps

    # ------------------------------------------------------------------
    def normalize_id(self, cap_id: str) -> str:
        """
        Normalize a capability id for comparison.
        Strips domain prefix and lowercases.
        e.g. "templates.list_templates" → "list_templates"
        """
        if "." in cap_id:
            return cap_id.split(".", 1)[1].lower()
        return cap_id.lower()
