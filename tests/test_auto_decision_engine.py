"""Tests for core.auto_decision_engine — IGNORE / WARN / FAIL decision matrix.

RULE-AUTO-DECISION-ENGINE (Wave 12) — verified by these tests.
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass, field

from core.auto_decision_engine import (
    AutoDecisionEngine,
    Decision,
    DecisionPolicy,
    DecisionResult,
)


# ---------------------------------------------------------------------------
# Minimal VisualDiffReport stub for unit tests
# ---------------------------------------------------------------------------

@dataclass
class _Report:
    change_type: str
    severity: str
    confidence: float
    summary: str = ""


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _decide(
    change_type: str,
    severity: str,
    confidence: float,
    policy: DecisionPolicy | None = None,
) -> Decision:
    engine = AutoDecisionEngine(policy=policy)
    report = _Report(change_type=change_type, severity=severity, confidence=confidence)
    result = engine.decide(report)  # type: ignore[arg-type]
    return result.decision


# ===========================================================================
# NONE — no change
# ===========================================================================

class TestNoneChange:
    def test_none_change_type_is_ignore(self):
        assert _decide("NONE", "none", 0.99) == Decision.IGNORE

    def test_none_lowercase_is_ignore(self):
        assert _decide("none", "none", 0.99) == Decision.IGNORE


# ===========================================================================
# TEXT
# ===========================================================================

class TestTextDecision:
    def test_text_medium_is_fail(self):
        assert _decide("TEXT", "medium", 0.90) == Decision.FAIL

    def test_text_high_is_fail(self):
        assert _decide("TEXT", "high", 0.95) == Decision.FAIL

    def test_text_low_high_confidence_is_warn(self):
        # low severity + confidence >= threshold → WARN
        assert _decide("TEXT", "low", 0.90) == Decision.WARN

    def test_text_low_low_confidence_is_ignore(self):
        # low severity + low confidence → IGNORE (not enough signal)
        assert _decide("TEXT", "low", 0.50) == Decision.IGNORE

    def test_text_low_at_threshold_is_warn(self):
        # Exactly at threshold (0.85) → WARN
        assert _decide("TEXT", "low", 0.85) == Decision.WARN

    def test_text_low_just_below_threshold_is_ignore(self):
        assert _decide("TEXT", "low", 0.84) == Decision.IGNORE


# ===========================================================================
# LAYOUT
# ===========================================================================

class TestLayoutDecision:
    def test_layout_high_confidence_is_fail(self):
        assert _decide("LAYOUT", "low", 0.90) == Decision.FAIL

    def test_layout_any_severity_high_confidence_is_fail(self):
        for sev in ("none", "low", "medium", "high"):
            assert _decide("LAYOUT", sev, 0.80) == Decision.FAIL

    def test_layout_low_confidence_is_warn(self):
        # confidence below layout_fail_confidence → WARN
        assert _decide("LAYOUT", "high", 0.50) == Decision.WARN

    def test_layout_at_confidence_threshold_is_fail(self):
        assert _decide("LAYOUT", "medium", 0.75) == Decision.FAIL

    def test_layout_just_below_confidence_is_warn(self):
        assert _decide("LAYOUT", "medium", 0.74) == Decision.WARN


# ===========================================================================
# VISUAL
# ===========================================================================

class TestVisualDecision:
    def test_visual_low_is_warn(self):
        assert _decide("VISUAL", "low", 0.80) == Decision.WARN

    def test_visual_medium_is_fail(self):
        assert _decide("VISUAL", "medium", 0.80) == Decision.FAIL

    def test_visual_high_is_fail(self):
        assert _decide("VISUAL", "high", 0.95) == Decision.FAIL

    def test_visual_none_severity_is_warn(self):
        # "none" severity = below "low" in ordering → WARN
        assert _decide("VISUAL", "none", 0.80) == Decision.WARN


# ===========================================================================
# COMPONENT
# ===========================================================================

class TestComponentDecision:
    def test_component_low_is_fail(self):
        assert _decide("COMPONENT", "low", 0.50) == Decision.FAIL

    def test_component_medium_is_fail(self):
        assert _decide("COMPONENT", "medium", 0.70) == Decision.FAIL

    def test_component_high_is_fail(self):
        assert _decide("COMPONENT", "high", 0.99) == Decision.FAIL

    def test_component_none_severity_is_still_fail(self):
        # "none" severity should still FAIL (code changed = suspect)
        assert _decide("COMPONENT", "none", 0.10) == Decision.FAIL

    def test_component_always_fail_false_falls_through(self):
        # Disable component_always_fail → falls through to UNKNOWN rules
        policy = DecisionPolicy(component_always_fail=False)
        result = _decide("COMPONENT", "low", 0.40, policy=policy)
        # low severity + low confidence → IGNORE under UNKNOWN rules
        assert result == Decision.IGNORE


# ===========================================================================
# UNKNOWN
# ===========================================================================

class TestUnknownDecision:
    def test_unknown_low_low_confidence_is_ignore(self):
        assert _decide("UNKNOWN", "low", 0.40) == Decision.IGNORE

    def test_unknown_low_at_threshold_is_warn(self):
        # confidence == threshold → WARN (not below threshold)
        assert _decide("UNKNOWN", "low", 0.60) == Decision.WARN

    def test_unknown_medium_is_warn(self):
        assert _decide("UNKNOWN", "medium", 0.50) == Decision.WARN

    def test_unknown_high_confidence_is_warn(self):
        assert _decide("UNKNOWN", "high", 0.95) == Decision.WARN

    def test_unrecognised_change_type_treated_as_unknown(self):
        # Future-proof: unknown change type treated same as UNKNOWN
        result = _decide("FUTURE_TYPE", "low", 0.30)
        assert result == Decision.IGNORE


# ===========================================================================
# Policy overrides
# ===========================================================================

class TestPolicyOverride:
    def test_custom_text_warn_threshold(self):
        # Raise the confidence threshold to 0.95 — low+0.90 should IGNORE
        policy = DecisionPolicy(text_warn_confidence=0.95)
        assert _decide("TEXT", "low", 0.90, policy=policy) == Decision.IGNORE

    def test_custom_layout_fail_threshold(self):
        # Lower threshold to 0.50 — confidence=0.60 should now FAIL
        policy = DecisionPolicy(layout_fail_confidence=0.50)
        assert _decide("LAYOUT", "low", 0.60, policy=policy) == Decision.FAIL

    def test_custom_unknown_ignore_threshold(self):
        # Raise ignore threshold — confidence=0.55 used to be IGNORE, now WARN
        policy = DecisionPolicy(unknown_ignore_confidence=0.70)
        assert _decide("UNKNOWN", "low", 0.55, policy=policy) == Decision.IGNORE
        assert _decide("UNKNOWN", "low", 0.70, policy=policy) == Decision.WARN


# ===========================================================================
# DecisionResult structure
# ===========================================================================

class TestDecisionResult:
    def test_result_has_reason(self):
        engine = AutoDecisionEngine()
        report = _Report("TEXT", "high", 0.95)
        result = engine.decide(report)  # type: ignore[arg-type]
        assert isinstance(result.reason, str)
        assert len(result.reason) > 0

    def test_result_to_dict_structure(self):
        engine = AutoDecisionEngine()
        report = _Report("VISUAL", "medium", 0.80)
        result = engine.decide(report)  # type: ignore[arg-type]
        d = result.to_dict()
        assert d["decision"] == "FAIL"
        assert d["changeType"] == "VISUAL"
        assert d["severity"] == "medium"
        assert 0.0 <= d["confidence"] <= 1.0

    def test_result_report_reference(self):
        engine = AutoDecisionEngine()
        report = _Report("NONE", "none", 0.0)
        result = engine.decide(report)  # type: ignore[arg-type]
        assert result.report is report


# ===========================================================================
# CacheMetrics (imported from auto_decision_engine for convenience)
# ===========================================================================

class TestCacheMetricsStandaloneImport:
    def test_import_from_auto_decision_engine_is_not_present(self):
        """CacheMetrics lives in visual_delta_cache, not auto_decision_engine."""
        import importlib, sys
        # auto_decision_engine should NOT export CacheMetrics
        import core.auto_decision_engine as ade
        assert not hasattr(ade, "CacheMetrics")
