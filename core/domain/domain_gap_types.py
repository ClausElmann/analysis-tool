"""Canonical gap type system for the Gen 3 domain engine.

Single source of truth for gap type constants, legacy normalization,
source routing, and priority. Import this instead of any local gap dict.
"""
from __future__ import annotations
from typing import Dict, List


class GapType:
    MISSING_ENTITY      = "MISSING_ENTITY"
    MISSING_FLOW        = "MISSING_FLOW"
    MISSING_RULE        = "MISSING_RULE"
    MISSING_INTEGRATION = "MISSING_INTEGRATION"
    ORPHAN_EVENT        = "ORPHAN_EVENT"
    ORPHAN_BATCH        = "ORPHAN_BATCH"
    UI_BACKEND_MISMATCH = "UI_BACKEND_MISMATCH"
    CONTRADICTION       = "CONTRADICTION"
    WEAK_REBUILD        = "WEAK_REBUILD"
    MISSING_CONTEXT     = "MISSING_CONTEXT"

    ALL: frozenset = frozenset({
        "MISSING_ENTITY", "MISSING_FLOW", "MISSING_RULE", "MISSING_INTEGRATION",
        "ORPHAN_EVENT", "ORPHAN_BATCH", "UI_BACKEND_MISMATCH", "CONTRADICTION",
        "WEAK_REBUILD", "MISSING_CONTEXT",
    })

    @classmethod
    def normalize(cls, raw: str) -> str:
        return _LEGACY_MAP.get(raw.upper().strip(), cls.MISSING_CONTEXT)


_LEGACY_MAP: Dict[str, str] = {
    "MISSING_ENTITY":         GapType.MISSING_ENTITY,
    "PARTIAL_ENTITY":         GapType.MISSING_ENTITY,
    "MISSING_FLOW":           GapType.MISSING_FLOW,
    "MISSING_RULE":           GapType.MISSING_RULE,
    "WEAK_RULE":              GapType.MISSING_RULE,
    "MISSING_INTEGRATION":    GapType.MISSING_INTEGRATION,
    "INCOMPLETE_INTEGRATION": GapType.MISSING_INTEGRATION,
    "MISSING_INTEG":          GapType.MISSING_INTEGRATION,
    "ORPHAN_EVENT":           GapType.ORPHAN_EVENT,
    "UNLINKED_EVENT":         GapType.ORPHAN_EVENT,
    "ORPHAN_BATCH":           GapType.ORPHAN_BATCH,
    "UI_BACKEND_MISMATCH":    GapType.UI_BACKEND_MISMATCH,
    "UI_WITHOUT_BACKEND":     GapType.UI_BACKEND_MISMATCH,
    "BACKEND_WITHOUT_UI":     GapType.UI_BACKEND_MISMATCH,
    "CONTRADICTION":          GapType.CONTRADICTION,
    "WEAK_REBUILD":           GapType.WEAK_REBUILD,
    "MISSING_CONTEXT":        GapType.MISSING_CONTEXT,
}

# Gap type → preferred asset source_type values (for autonomous search)
GAP_SOURCE_ROUTING: Dict[str, List[str]] = {
    GapType.MISSING_ENTITY:      ["sql_table", "sql_procedure", "code_file"],
    GapType.MISSING_FLOW:        ["angular", "code_file", "wiki_section"],
    GapType.MISSING_RULE:        ["wiki_section", "work_items_batch", "code_file"],
    GapType.MISSING_INTEGRATION: ["code_file", "config_file", "wiki_section"],
    GapType.ORPHAN_EVENT:        ["event", "webhook", "code_file"],
    GapType.ORPHAN_BATCH:        ["background", "batch", "code_file"],
    GapType.UI_BACKEND_MISMATCH: ["angular", "code_file"],
    GapType.CONTRADICTION:       [],   # use the two conflicting source IDs directly
    GapType.WEAK_REBUILD:        [],   # synthesize from existing 010/020/030/070
    GapType.MISSING_CONTEXT:     ["wiki_section", "work_items_batch"],
}

# Lower number = higher priority (process first)
GAP_PRIORITY: Dict[str, int] = {
    GapType.CONTRADICTION:       1,
    GapType.WEAK_REBUILD:        2,
    GapType.MISSING_ENTITY:      3,
    GapType.MISSING_FLOW:        4,
    GapType.MISSING_RULE:        4,
    GapType.MISSING_INTEGRATION: 5,
    GapType.ORPHAN_EVENT:        5,
    GapType.ORPHAN_BATCH:        5,
    GapType.UI_BACKEND_MISMATCH: 6,
    GapType.MISSING_CONTEXT:     7,
}
