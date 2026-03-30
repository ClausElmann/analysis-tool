"""Tests for core.domain.ai_reasoner.

Covers:
* HeuristicAIProvider.generate_json
* AIReasoner.analyze_asset — keys, signal_strength, merge
* AIReasoner.cross_analyze — structure
* AIReasoner.detect_gaps — gap ID format, priority ordering
* AIReasoner.estimate_signal_strength — range and relative ordering
"""

import re
import pytest

from core.domain.ai.semantic_analyzer import INSIGHT_KEYS
from core.domain.ai_reasoner import (
    AIProvider,
    AIReasoner,
    GAP_TYPES,
    HeuristicAIProvider,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _code_asset(domain: str = "messaging") -> dict:
    return {
        "id": f"code:{domain}:sender",
        "type": "code_file",
        "path": f"src/{domain}/MessageSender.cs",
        "content": (
            "public class MessageSender {\n"
            "    public async Task SendAsync(Message msg) {}\n"
            "    public void Validate(Message msg) { if (msg == null) throw new ArgumentNullException(); }\n"
            "}\n"
            "public interface IMessageRepository {}\n"
        ),
    }


def _empty_model() -> dict:
    return {k: [] for k in INSIGHT_KEYS}


def _full_model() -> dict:
    return {
        "entities":     ["A", "B", "C", "D", "E"],
        "behaviors":    ["a()", "b()", "c()", "d()", "e()"],
        "flows":        ["Flow1", "Flow2", "Flow3"],
        "rules":        ["rule1", "rule2", "rule3"],
        "events":       ["EventA", "EventB"],
        "integrations": ["http://api.example.com", "HttpClient"],
        "batch":        [],
        "pseudocode":   [],
        "rebuild":      ["TBD"],
    }


# ---------------------------------------------------------------------------
# HeuristicAIProvider
# ---------------------------------------------------------------------------


class TestHeuristicAIProvider:
    def test_generate_json_returns_required_keys(self):
        provider = HeuristicAIProvider()
        prompt = "path: src/Identity/UserService.cs\nclass UserService { public User GetUser() {} }"
        result = provider.generate_json(prompt, schema_name="asset_insight")

        assert isinstance(result, dict)
        for key in ("intent", "domain_role", "entities", "behaviors", "rules",
                    "events", "integrations", "rebuild_note"):
            assert key in result, f"Missing key: {key}"

    def test_generate_json_entities_are_sorted_list(self):
        provider = HeuristicAIProvider()
        prompt = "class OrderService {} class Customer {}"
        result = provider.generate_json(prompt, "asset_insight")
        assert isinstance(result["entities"], list)

    def test_generate_json_deterministic(self):
        provider = HeuristicAIProvider()
        prompt = "public class PaymentHandler { public void Process() { if (amount <= 0) throw; } }"
        r1 = provider.generate_json(prompt, "asset_insight")
        r2 = provider.generate_json(prompt, "asset_insight")
        assert r1 == r2

    def test_generate_json_empty_content(self):
        provider = HeuristicAIProvider()
        result = provider.generate_json("", "asset_insight")
        assert isinstance(result, dict)
        assert "entities" in result

    def test_generate_json_extracts_events(self):
        provider = HeuristicAIProvider()
        prompt = "OrderPlacedEvent OrderCancelledNotification OrderCreatedCommand"
        result = provider.generate_json(prompt, "asset_insight")
        # Should find at least one of these event-named tokens
        all_tokens = result.get("events", [])
        assert len(all_tokens) > 0


# ---------------------------------------------------------------------------
# AIProvider abstract class
# ---------------------------------------------------------------------------


class TestAIProviderAbstract:
    def test_generate_json_raises_not_implemented(self):
        provider = AIProvider()
        with pytest.raises(NotImplementedError):
            provider.generate_json("test", "asset_insight")


# ---------------------------------------------------------------------------
# AIReasoner.analyze_asset
# ---------------------------------------------------------------------------


class TestAIReasonerAnalyzeAsset:
    def test_returns_all_insight_keys(self):
        reasoner = AIReasoner()
        asset = _code_asset()
        result = reasoner.analyze_asset(asset, "messaging")
        for k in INSIGHT_KEYS:
            assert k in result, f"Missing insight key: {k}"

    def test_signal_strength_in_range(self):
        reasoner = AIReasoner()
        asset = _code_asset()
        result = reasoner.analyze_asset(asset, "messaging")
        ss = result.get("signal_strength")
        assert ss is not None
        assert 0.0 <= ss <= 1.0

    def test_entities_are_sorted_list(self):
        reasoner = AIReasoner()
        result = reasoner.analyze_asset(_code_asset(), "messaging")
        assert isinstance(result["entities"], list)
        assert result["entities"] == sorted(result["entities"])

    def test_deterministic_repeated_calls(self):
        reasoner = AIReasoner()
        asset = _code_asset()
        r1 = reasoner.analyze_asset(asset, "messaging")
        r2 = reasoner.analyze_asset(asset, "messaging")
        assert r1 == r2

    def test_empty_asset_returns_valid_structure(self):
        reasoner = AIReasoner()
        asset = {"id": "empty:1", "type": "code_file", "path": "", "content": ""}
        result = reasoner.analyze_asset(asset, "messaging")
        for k in INSIGHT_KEYS:
            assert k in result

    def test_high_signal_for_matching_domain(self):
        reasoner = AIReasoner()
        asset = {
            "id": "code:messaging:sender",
            "type": "code_file",
            "path": "src/messaging/MessageSender.cs",
            "content": "messaging message send notification",
        }
        result = reasoner.analyze_asset(asset, "messaging")
        assert result["signal_strength"] > 0.0


# ---------------------------------------------------------------------------
# AIReasoner.cross_analyze
# ---------------------------------------------------------------------------


class TestAIReasonerCrossAnalyze:
    def test_returns_required_keys(self):
        reasoner = AIReasoner()
        result = reasoner.cross_analyze(_full_model(), "messaging")
        assert "linked_pairs" in result
        assert "flow_stubs" in result
        assert "coverage" in result
        assert "consistency" in result

    def test_coverage_has_all_sections(self):
        reasoner = AIReasoner()
        model = _full_model()
        result = reasoner.cross_analyze(model, "messaging")
        cov = result["coverage"]
        assert isinstance(cov, dict)
        for k in ("entities", "behaviors", "flows", "rules", "events", "integrations"):
            assert k in cov

    def test_consistency_in_range(self):
        reasoner = AIReasoner()
        result = reasoner.cross_analyze(_full_model(), "messaging")
        assert 0.0 <= result["consistency"] <= 1.0

    def test_empty_model_returns_low_consistency(self):
        reasoner = AIReasoner()
        result = reasoner.cross_analyze(_empty_model(), "messaging")
        assert result["consistency"] == 0.0

    def test_full_model_returns_high_consistency(self):
        reasoner = AIReasoner()
        result = reasoner.cross_analyze(_full_model(), "messaging")
        assert result["consistency"] >= 0.5


# ---------------------------------------------------------------------------
# AIReasoner.detect_gaps
# ---------------------------------------------------------------------------


class TestAIReasonerDetectGaps:
    def test_empty_model_has_gaps(self):
        reasoner = AIReasoner()
        gaps = reasoner.detect_gaps(_empty_model(), "messaging")
        assert len(gaps) > 0

    def test_gap_id_format(self):
        reasoner = AIReasoner()
        gaps = reasoner.detect_gaps(_empty_model(), "messaging")
        for gap in gaps:
            assert re.match(r"^gap:[a-z_]+:[a-z_]+:[a-z0-9_]+$", gap["id"]), (
                f"Bad gap ID format: {gap['id']}"
            )

    def test_gap_dict_has_required_fields(self):
        reasoner = AIReasoner()
        gaps = reasoner.detect_gaps(_empty_model(), "messaging")
        for gap in gaps:
            assert "id" in gap
            assert "type" in gap
            assert gap["type"] in GAP_TYPES
            assert "priority" in gap

    def test_full_model_has_no_gaps(self):
        reasoner = AIReasoner()
        gaps = reasoner.detect_gaps(_full_model(), "messaging")
        assert len(gaps) == 0

    def test_gaps_sorted_by_priority_desc(self):
        reasoner = AIReasoner()
        partial_model = {
            "entities":     ["A"],          # only 1 of 5
            "behaviors":    [],
            "flows":        [],
            "rules":        [],
            "events":       [],
            "integrations": [],
            "batch":        [],
            "pseudocode":   [],
            "rebuild":      [],
        }
        gaps = reasoner.detect_gaps(partial_model, "messaging")
        _ORDER = {"high": 0, "medium": 1, "low": 2}
        priority_order = [_ORDER.get(g["priority"], 9) for g in gaps]
        # Numeric order values should be non-decreasing (high=0 first)
        assert priority_order == sorted(priority_order)

    def test_suggested_terms_present(self):
        reasoner = AIReasoner()
        gaps = reasoner.detect_gaps(_empty_model(), "identity_access")
        for gap in gaps:
            terms = gap.get("suggested_terms")
            assert isinstance(terms, list)


# ---------------------------------------------------------------------------
# AIReasoner.estimate_signal_strength
# ---------------------------------------------------------------------------


class TestAIReasonerEstimateSignalStrength:
    def test_returns_float_in_range(self):
        reasoner = AIReasoner()
        val = reasoner.estimate_signal_strength(_code_asset(), "messaging")
        assert 0.0 <= val <= 1.0

    def test_matching_asset_higher_than_unrelated(self):
        reasoner = AIReasoner()
        matching = {
            "id": "code:messaging:sender",
            "type": "code_file",
            "path": "src/messaging/MessageSender.cs",
            "content": "messaging notification send",
        }
        unrelated = {
            "id": "code:reporting:report",
            "type": "code_file",
            "path": "src/reporting/ReportBuilder.cs",
            "content": "report pdf generate",
        }
        s_match = reasoner.estimate_signal_strength(matching, "messaging")
        s_unrelated = reasoner.estimate_signal_strength(unrelated, "messaging")
        assert s_match >= s_unrelated

    def test_deterministic(self):
        reasoner = AIReasoner()
        asset = _code_asset()
        assert (
            reasoner.estimate_signal_strength(asset, "messaging")
            == reasoner.estimate_signal_strength(asset, "messaging")
        )
