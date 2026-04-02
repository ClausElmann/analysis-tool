"""Tests for DomainEngine v2 additions.

Covers:
* AIProvider class hierarchy (HeuristicAIProvider, CompositeAIProvider,
  build_provider_from_env)
* Richer cross_analyze output (confirmed_entities, confirmed_flows,
  confirmed_rules, uncertain_items, contradictions,
  recommended_focus_terms)
* _EVIDENCE_WEIGHTS presence and validity
* ai_prompt_builder — sql_table, sql_procedure, cross_analysis templates
* build_cross_analysis_prompt shape and content
* domain_scoring — compute_consistency_score, compute_saturation_score,
  new threshold constants
* domain_memory — aliases and rejected_hypotheses APIs
* domain_model_store — save_decision_support, 095 file written
* domain_query_engine — gap-type-aware bonus (_GAP_TYPE_PREFERRED_SOURCES)
* domain_state — 4 new DomainProgress fields round-trip
* domain_learning_loop — streak=3, result includes consistency/saturation
"""

import os

import pytest

from core.domain.ai_prompt_builder import build_cross_analysis_prompt, build_prompt
from core.domain.ai_reasoner import (
    AIReasoner,
    CompositeAIProvider,
    HeuristicAIProvider,
    OpenAIJsonProvider,
    _EVIDENCE_WEIGHTS,
    build_provider_from_env,
)
from core.domain.domain_learning_loop import DomainLearningLoop, _REQUIRED_STABLE_STREAK
from core.domain.domain_memory import DomainMemory
from core.domain.domain_model_store import DomainModelStore, _FILE_MAP
from core.domain.domain_gap_types import GAP_SOURCE_ROUTING, GapType
from core.domain.domain_query_engine import (
    DomainQueryEngine,
    _score_asset,
)
from core.domain.domain_scoring import (
    COMPLETENESS_THRESHOLD_V2,
    CONSISTENCY_THRESHOLD,
    SATURATION_THRESHOLD,
    compute_consistency_score,
    compute_saturation_score,
)
from core.domain.domain_state import DomainProgress, DomainState


# ===========================================================================
# AI Provider — class hierarchy
# ===========================================================================


class TestProviderHierarchy:
    def test_heuristic_is_default_when_disabled(self, monkeypatch):
        monkeypatch.setenv("DOMAIN_ENGINE_AI_ENABLED", "false")
        provider = build_provider_from_env()
        assert isinstance(provider, HeuristicAIProvider)

    def test_composite_returned_when_openai(self, monkeypatch):
        monkeypatch.setenv("DOMAIN_ENGINE_AI_ENABLED", "true")
        monkeypatch.setenv("DOMAIN_ENGINE_AI_PROVIDER", "openai")
        provider = build_provider_from_env()
        assert isinstance(provider, CompositeAIProvider)

    def test_heuristic_returned_for_unknown_provider(self, monkeypatch):
        monkeypatch.setenv("DOMAIN_ENGINE_AI_ENABLED", "true")
        monkeypatch.setenv("DOMAIN_ENGINE_AI_PROVIDER", "unknown_llm")
        provider = build_provider_from_env()
        assert isinstance(provider, HeuristicAIProvider)

    def test_composite_falls_back_to_heuristic_on_error(self):
        """CompositeAIProvider swallows errors and falls back to heuristic."""
        class AlwaysFailProvider(HeuristicAIProvider):
            def generate_json(self, prompt, schema_name):
                raise RuntimeError("simulated failure")

        composite = CompositeAIProvider(
            real_provider=AlwaysFailProvider(),
            fallback=HeuristicAIProvider(),
        )
        result = composite.generate_json("test prompt", "asset_insight")
        assert isinstance(result, dict)

    def test_composite_disabled_uses_fallback(self, monkeypatch):
        monkeypatch.setenv("DOMAIN_ENGINE_AI_ENABLED", "false")

        class TrackingProvider(HeuristicAIProvider):
            called = False
            def generate_json(self, prompt, schema_name):
                TrackingProvider.called = True
                return super().generate_json(prompt, schema_name)

        real = TrackingProvider()
        fallback = HeuristicAIProvider()
        composite = CompositeAIProvider(real_provider=real, fallback=fallback)
        composite.generate_json("ignored", "asset_insight")
        assert not TrackingProvider.called

    def test_openai_provider_instantiates(self):
        p = OpenAIJsonProvider()
        assert isinstance(p, OpenAIJsonProvider)

    def test_openai_raises_without_library(self, monkeypatch):
        """OpenAIJsonProvider.generate_json raises RuntimeError when openai missing."""
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("no module named openai")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        p = OpenAIJsonProvider()
        with pytest.raises(RuntimeError, match="openai package"):
            p.generate_json("prompt", "asset_insight")


# ===========================================================================
# Evidence weights
# ===========================================================================


class TestEvidenceWeights:
    def test_evidence_weights_dict_present(self):
        assert isinstance(_EVIDENCE_WEIGHTS, dict)
        assert len(_EVIDENCE_WEIGHTS) >= 8

    def test_code_file_highest_weight(self):
        assert _EVIDENCE_WEIGHTS["code_file"] == 1.0

    def test_all_weights_in_range(self):
        for key, val in _EVIDENCE_WEIGHTS.items():
            assert 0.0 <= val <= 1.0, f"{key} weight {val} out of range"

    def test_sql_procedure_and_table_present(self):
        assert "sql_procedure" in _EVIDENCE_WEIGHTS
        assert "sql_table" in _EVIDENCE_WEIGHTS


# ===========================================================================
# Cross-analyze — richer output
# ===========================================================================


class TestCrossAnalyzeRicher:
    def _model(self, n_each=3):
        return {
            "entities": [f"UserService{i}" for i in range(n_each)],
            "behaviors": [f"HandleUser{i}" for i in range(n_each)],
            "flows": [f"UserFlow{i}" for i in range(n_each)],
            "rules": [f"UserService{i} must validate input" for i in range(n_each)],
            "events": [f"UserEvent{i}" for i in range(n_each)],
            "integrations": [f"https://api{i}.example.com" for i in range(n_each)],
            "batch": [],
            "pseudocode": [],
            "rebuild": [],
        }

    def test_cross_analyze_returns_new_keys(self):
        reasoner = AIReasoner()
        result = reasoner.cross_analyze(self._model(), "identity_access")
        for key in (
            "confirmed_entities", "confirmed_flows", "confirmed_rules",
            "uncertain_items", "contradictions", "recommended_focus_terms",
        ):
            assert key in result, f"Missing key: {key}"

    def test_cross_analyze_confirmed_entities_are_list(self):
        reasoner = AIReasoner()
        result = reasoner.cross_analyze(self._model(), "identity_access")
        assert isinstance(result["confirmed_entities"], list)

    def test_cross_analyze_recommended_focus_terms_list(self):
        reasoner = AIReasoner()
        # Empty model should have many gaps → many focus terms
        result = reasoner.cross_analyze(
            {k: [] for k in ["entities", "behaviors", "flows", "rules", "events",
                              "integrations", "batch", "pseudocode", "rebuild"]},
            "identity_access",
        )
        assert isinstance(result["recommended_focus_terms"], list)
        assert len(result["recommended_focus_terms"]) > 0

    def test_cross_analyze_backward_compat_keys_still_present(self):
        reasoner = AIReasoner()
        result = reasoner.cross_analyze(self._model(), "identity_access")
        for key in ("linked_pairs", "flow_stubs", "coverage", "consistency"):
            assert key in result, f"Legacy key missing: {key}"


# ===========================================================================
# ai_prompt_builder — new templates
# ===========================================================================


class TestPromptBuilderV2:
    def _asset(self, asset_type, path="src/Payments.cs"):
        return {"id": f"{asset_type}:1", "type": asset_type, "path": path}

    def test_sql_table_template_used(self):
        asset = self._asset("sql_table", "db/tables/Orders.sql")
        prompt = build_prompt(asset, "payments")
        assert "table" in prompt.lower()
        assert "payments" in prompt

    def test_sql_procedure_template_used(self):
        asset = self._asset("sql_procedure", "db/procs/CreateOrder.sql")
        prompt = build_prompt(asset, "payments")
        assert "procedure" in prompt.lower()
        assert "payments" in prompt

    def test_schema_includes_confidence_field(self):
        asset = self._asset("code_file")
        prompt = build_prompt(asset, "messaging")
        assert "confidence" in prompt

    def test_schema_includes_domain_relevance_field(self):
        asset = self._asset("code_file")
        prompt = build_prompt(asset, "messaging")
        assert "domain_relevance" in prompt

    def test_build_cross_analysis_prompt_shape(self):
        model = {
            "entities": ["UserService", "UserRepo"],
            "behaviors": ["HandleLogin"],
            "flows": ["AuthFlow"],
            "rules": ["Must validate token"],
            "events": ["LoginEvent"],
            "integrations": ["https://api.example.com"],
            "batch": [],
            "pseudocode": [],
            "rebuild": [],
        }
        prompt = build_cross_analysis_prompt(model, "identity_access")
        assert "identity_access" in prompt
        assert "confirmed_entities" in prompt
        assert "uncertain_items" in prompt

    def test_build_cross_analysis_prompt_includes_counts(self):
        model = {
            "entities": ["A", "B", "C"],
            "behaviors": ["DoX"],
            "flows": [],
            "rules": [],
            "events": [],
            "integrations": [],
            "batch": [],
            "pseudocode": [],
            "rebuild": [],
        }
        prompt = build_cross_analysis_prompt(model, "billing")
        assert "3" in prompt  # entity count


# ===========================================================================
# domain_scoring — new functions
# ===========================================================================


class TestComputeConsistencyScore:
    def test_empty_cross_analysis_returns_zero(self):
        assert compute_consistency_score({}) == 0.0

    def test_uses_consistency_key_when_present(self):
        result = compute_consistency_score({"consistency": 0.75})
        assert result == 0.75

    def test_clamps_consistency_key_to_range(self):
        assert compute_consistency_score({"consistency": 2.0}) == 1.0
        assert compute_consistency_score({"consistency": -1.0}) == 0.0

    def test_derives_from_confirmed_uncertain(self):
        cross = {
            "confirmed_entities": ["A", "B", "C"],
            "confirmed_flows": ["F1"],
            "confirmed_rules": ["R1"],
            "uncertain_items": ["X"],
        }
        score = compute_consistency_score(cross)
        # 5 confirmed / 6 total = 0.8333
        assert 0.8 <= score <= 0.9

    def test_all_confirmed_returns_one(self):
        cross = {
            "confirmed_entities": ["A"],
            "confirmed_flows": [],
            "confirmed_rules": [],
            "uncertain_items": [],
        }
        assert compute_consistency_score(cross) == 1.0


class TestComputeSaturationScore:
    def _snap(self, gap_ids):
        return {"gaps": [{"id": gid} for gid in gap_ids]}

    def test_less_than_two_snapshots_returns_zero(self):
        assert compute_saturation_score([]) == 0.0
        assert compute_saturation_score([self._snap(["g1"])]) == 0.0

    def test_identical_snapshots_high_saturation(self):
        history = [self._snap(["g1", "g2"]), self._snap(["g1", "g2"])]
        score = compute_saturation_score(history)
        assert score >= 0.8

    def test_no_gaps_in_both_returns_one(self):
        history = [self._snap([]), self._snap([])]
        assert compute_saturation_score(history) == 1.0

    def test_decreasing_gaps_increases_saturation(self):
        history = [
            self._snap(["g1", "g2", "g3", "g4", "g5"]),
            self._snap(["g1"]),
        ]
        score = compute_saturation_score(history)
        assert 0.0 <= score <= 1.0


class TestNewThresholdConstants:
    def test_completeness_threshold_v2_lowered(self):
        assert COMPLETENESS_THRESHOLD_V2 < 0.90
        assert COMPLETENESS_THRESHOLD_V2 == 0.85

    def test_consistency_threshold_value(self):
        assert CONSISTENCY_THRESHOLD == 0.80

    def test_saturation_threshold_value(self):
        assert SATURATION_THRESHOLD == 0.90


# ===========================================================================
# domain_memory — aliases + rejected_hypotheses
# ===========================================================================


class TestDomainMemoryAliases:
    @pytest.fixture()
    def mem(self, tmp_path):
        m = DomainMemory(data_root=str(tmp_path))
        m.load()
        return m

    def test_add_and_get_alias(self, mem):
        mem.add_alias("messaging", "login_user", "authenticate_user")
        aliases = mem.get_aliases("messaging")
        assert {"from": "login_user", "to": "authenticate_user"} in aliases

    def test_duplicate_alias_not_added(self, mem):
        mem.add_alias("messaging", "a", "b")
        mem.add_alias("messaging", "a", "b")
        assert len(mem.get_aliases("messaging")) == 1

    def test_aliases_empty_by_default(self, mem):
        assert mem.get_aliases("identity") == []

    def test_aliases_persisted_on_save(self, tmp_path):
        m1 = DomainMemory(data_root=str(tmp_path))
        m1.load()
        m1.add_alias("messaging", "x", "y")
        m1.save()

        m2 = DomainMemory(data_root=str(tmp_path))
        m2.load()
        assert {"from": "x", "to": "y"} in m2.get_aliases("messaging")


class TestDomainMemoryRejectedHypotheses:
    @pytest.fixture()
    def mem(self, tmp_path):
        m = DomainMemory(data_root=str(tmp_path))
        m.load()
        return m

    def test_add_and_get_rejected_hypothesis(self, mem):
        mem.add_rejected_hypothesis("billing", "shipping", "no payment refs found")
        items = mem.get_rejected_hypotheses("billing")
        assert {"candidate": "shipping", "reason": "no payment refs found"} in items

    def test_duplicate_rejected_not_added(self, mem):
        mem.add_rejected_hypothesis("billing", "x", "reason1")
        mem.add_rejected_hypothesis("billing", "x", "different reason")
        assert len(mem.get_rejected_hypotheses("billing")) == 1

    def test_rejected_empty_by_default(self, mem):
        assert mem.get_rejected_hypotheses("messaging") == []

    def test_rejected_persisted(self, tmp_path):
        m1 = DomainMemory(data_root=str(tmp_path))
        m1.load()
        m1.add_rejected_hypothesis("messaging", "cand", "why not")
        m1.save()

        m2 = DomainMemory(data_root=str(tmp_path))
        m2.load()
        assert len(m2.get_rejected_hypotheses("messaging")) == 1


class TestDomainMemoryBackfillKeys:
    def test_existing_domain_gets_aliases_backfilled(self, tmp_path):
        """Old memory files without aliases key are back-filled on load."""
        import json
        path = tmp_path / "domain_memory.json"
        old_data = {
            "domains": {
                "messaging": {
                    "assets": {},
                    "cross_analysis": {},
                    "gap_history": [],
                    # No aliases or rejected_hypotheses — simulates old format
                }
            }
        }
        path.write_text(json.dumps(old_data))

        m = DomainMemory(data_root=str(tmp_path))
        m.load()
        assert m.get_aliases("messaging") == []
        assert m.get_rejected_hypotheses("messaging") == []


# ===========================================================================
# domain_model_store — decision support
# ===========================================================================


class TestDomainModelStoreV2:
    def test_095_in_file_map(self):
        assert "decision_support" in _FILE_MAP
        assert _FILE_MAP["decision_support"] == "095_decision_support.json"

    def test_save_decision_support_creates_file(self, tmp_path):
        store = DomainModelStore(domains_root=str(tmp_path))
        data = {
            "business_value": "high",
            "complexity": "medium",
            "rebuild_priority": 1,
            "reasoning": "Core auth domain",
        }
        store.save_decision_support("identity_access", data)
        expected = tmp_path / "identity_access" / "095_decision_support.json"
        assert expected.is_file()

    def test_save_decision_support_includes_domain_and_timestamp(self, tmp_path):
        import json
        store = DomainModelStore(domains_root=str(tmp_path))
        store.save_decision_support("messaging", {"rebuild_priority": 2})
        path = tmp_path / "messaging" / "095_decision_support.json"
        data = json.loads(path.read_text())
        assert data["domain"] == "messaging"
        assert "saved_utc" in data

    def test_save_decision_support_is_atomic(self, tmp_path):
        """No .tmp file left after write."""
        store = DomainModelStore(domains_root=str(tmp_path))
        store.save_decision_support("billing", {"x": 1})
        tmp_file = tmp_path / "billing" / "095_decision_support.json.tmp"
        assert not tmp_file.exists()

    def test_save_model_does_not_create_095_file(self, tmp_path):
        """save_model should NOT write decision_support — that's save_decision_support."""
        from core.domain.ai.semantic_analyzer import INSIGHT_KEYS
        store = DomainModelStore(domains_root=str(tmp_path))
        model = {k: [] for k in INSIGHT_KEYS}
        store.save_model("billing", model)
        path = tmp_path / "billing" / "095_decision_support.json"
        assert not path.exists()


# ===========================================================================
# domain_query_engine — gap-type-aware bonus
# ===========================================================================


class TestGapTypeAwareScoring:
    def test_gap_source_routing_dict_present(self):
        assert isinstance(GAP_SOURCE_ROUTING, dict)
        assert GapType.MISSING_ENTITY in GAP_SOURCE_ROUTING

    def test_preferred_source_gets_bonus(self):
        asset_preferred = {"id": "sql1", "type": "sql_table", "path": "db/table.sql", "content": ""}
        asset_other = {"id": "git1", "type": "git_insights_batch", "path": "git.json", "content": ""}
        gaps = [{"type": "missing_entity"}]

        score_preferred = _score_asset(
            asset_preferred, "identity_access", [], set(), ["missing_entity"]
        )
        score_other = _score_asset(
            asset_other, "identity_access", [], set(), ["missing_entity"]
        )
        assert score_preferred > score_other

    def test_orphan_event_favors_event_type(self):
        # "event" type (not in _TYPE_PRIORITY → base score 0) gets gap-type bonus 0.3
        # "pdf_section" (priority 1) → type score 0.1, no gap-type bonus
        # event total ≈ 2.3  vs  pdf_section total ≈ 2.1
        asset_event = {"id": "ev1", "type": "event", "path": "events/", "content": ""}
        asset_pdf = {"id": "pdf1", "type": "pdf_section", "path": "docs/", "content": ""}
        score_event = _score_asset(asset_event, "messaging", [], set(), ["orphan_event"])
        score_pdf = _score_asset(asset_pdf, "messaging", [], set(), ["orphan_event"])
        assert score_event > score_pdf

    def test_no_gap_types_no_crash(self):
        asset = {"id": "x", "type": "code_file", "path": "src/X.cs", "content": ""}
        score = _score_asset(asset, "messaging", [], set(), None)
        assert score >= 0.0

    def test_select_assets_passes_gap_types(self):
        """select_assets_for_iteration should prefer sql_table over git_insights for missing_entity."""
        engine = DomainQueryEngine()
        assets = [
            {"id": "sql:tbl", "type": "sql_table", "path": "db/Users.sql", "content": "Users"},
            {"id": "git:log", "type": "git_insights_batch", "path": "git.json", "content": ""},
        ]
        gaps = [{"id": "g1", "type": "missing_entity", "suggested_terms": ["user"]}]
        selected = engine.select_assets_for_iteration(
            domain_name="identity_access",
            assets=assets,
            gaps=gaps,
            processed_ids=set(),
            max_assets=5,
        )
        assert selected[0]["id"] == "sql:tbl"


# ===========================================================================
# domain_state — 4 new fields
# ===========================================================================


class TestDomainProgressV2Fields:
    def test_new_fields_have_defaults(self):
        p = DomainProgress(name="test_domain")
        assert p.stable_iterations == 0
        assert p.last_significant_change == ""
        assert p.current_focus == ""
        assert p.evidence_balance == {}

    def test_to_dict_includes_new_fields(self):
        p = DomainProgress(
            name="billing",
            stable_iterations=2,
            last_significant_change="2025-01-01T00:00:00",
            current_focus="entities",
            evidence_balance={"code_file": 10, "sql": 3},
        )
        d = p.to_dict()
        assert d["stable_iterations"] == 2
        assert d["last_significant_change"] == "2025-01-01T00:00:00"
        assert d["current_focus"] == "entities"
        assert d["evidence_balance"] == {"code_file": 10, "sql": 3}

    def test_from_dict_restores_new_fields(self):
        d = {
            "name": "billing",
            "stable_iterations": 3,
            "last_significant_change": "ts",
            "current_focus": "flows",
            "evidence_balance": {"code_file": 5},
        }
        p = DomainProgress.from_dict(d)
        assert p.stable_iterations == 3
        assert p.current_focus == "flows"
        assert p.evidence_balance == {"code_file": 5}

    def test_from_dict_missing_new_fields_use_defaults(self):
        """Old state files without new fields load without error."""
        p = DomainProgress.from_dict({"name": "legacy_domain"})
        assert p.stable_iterations == 0
        assert p.evidence_balance == {}

    def test_domain_state_round_trip_with_new_fields(self, tmp_path):
        state = DomainState(domains_root=str(tmp_path))
        state.load()
        state.ensure_domains(["billing"])
        progress = state.get("billing")
        progress.stable_iterations = 2
        progress.current_focus = "rules"
        state.save()

        state2 = DomainState(domains_root=str(tmp_path))
        state2.load()
        p2 = state2.get("billing")
        assert p2.stable_iterations == 2
        assert p2.current_focus == "rules"


# ===========================================================================
# domain_learning_loop — streak=3, result includes new scores
# ===========================================================================


def _assets(n=5, domain="messaging"):
    return [
        {
            "id": f"code:{domain}:{i}",
            "type": "code_file",
            "path": f"src/{domain}/File{i}.cs",
            "content": (
                f"public class {domain.capitalize()}Service{i} {{"
                f"  public void Handle{domain.capitalize()}() {{ }}"
                f"  public void Validate() {{ if (x == null) throw; }}"
                f"}}"
            ),
        }
        for i in range(n)
    ]


@pytest.fixture()
def loop_setup(tmp_path):
    domains_root = str(tmp_path / "domains")
    data_root = str(tmp_path / "data")
    model_store = DomainModelStore(domains_root=domains_root)
    memory = DomainMemory(data_root=data_root)
    memory.load()
    reasoner = AIReasoner()
    query_engine = DomainQueryEngine()
    state = DomainState(domains_root=domains_root)
    state.load()
    state.ensure_domains(["messaging"])
    state.save()
    loop = DomainLearningLoop(
        model_store=model_store,
        memory=memory,
        reasoner=reasoner,
        query_engine=query_engine,
        state=state,
        max_assets_per_iter=10,
        verbose=False,
    )
    return loop, state, memory, model_store


class TestLearningLoopV2:
    def test_required_stable_streak_is_3(self):
        assert _REQUIRED_STABLE_STREAK == 3

    def test_run_iteration_returns_consistency_score(self, loop_setup):
        loop, *_ = loop_setup
        result = loop.run_iteration("messaging", _assets())
        assert "consistency_score" in result
        assert 0.0 <= result["consistency_score"] <= 1.0

    def test_run_iteration_returns_saturation_score(self, loop_setup):
        loop, *_ = loop_setup
        result = loop.run_iteration("messaging", _assets())
        assert "saturation_score" in result
        assert 0.0 <= result["saturation_score"] <= 1.0

    def test_should_mark_stable_requires_streak_3(self, loop_setup):
        loop, *_ = loop_setup
        # Streak 2 should NOT be stable
        assert not loop.should_mark_stable({
            "completeness_score": 0.95,
            "consistency_score": 1.0,
            "saturation_score": 1.0,
            "new_information_score": 0.0,
            "stable_streak": 2,
        })
        # Streak 3 should be stable
        assert loop.should_mark_stable({
            "completeness_score": 0.95,
            "consistency_score": 1.0,
            "saturation_score": 1.0,
            "new_information_score": 0.0,
            "stable_streak": 3,
        })

    def test_should_mark_stable_requires_consistency(self, loop_setup):
        loop, *_ = loop_setup
        assert not loop.should_mark_stable({
            "completeness_score": 0.95,
            "consistency_score": 0.5,   # below threshold
            "saturation_score": 1.0,
            "new_information_score": 0.0,
            "stable_streak": 3,
        })

    def test_should_mark_stable_requires_saturation(self, loop_setup):
        loop, *_ = loop_setup
        assert not loop.should_mark_stable({
            "completeness_score": 0.95,
            "consistency_score": 1.0,
            "saturation_score": 0.5,   # below threshold
            "new_information_score": 0.0,
            "stable_streak": 3,
        })

    def test_legacy_dict_without_new_keys_still_evaluable(self, loop_setup):
        """Old callers that pass only completeness/new_info/streak still work."""
        loop, *_ = loop_setup
        # Should not raise — uses default 1.0 for consistency/saturation
        result = loop.should_mark_stable({
            "completeness_score": 0.95,
            "new_information_score": 0.0,
            "stable_streak": 3,
        })
        assert isinstance(result, bool)
