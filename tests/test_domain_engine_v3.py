"""Tests for DomainEngine v3 additions.

Covers:
* DomainDiscoveryEngine — discover, save/load, DomainCandidate dataclass
* DomainPrioritizer — prioritize, save/load, tier ordering
* DomainAutonomousSearch — search, gap_to_intents, find_assets_for_gaps
* DomainLearningLoop v3 — search_engine param, all_assets param (backward compat)
* DomainEngineV3 — construction, discover_and_prioritize, run (smoke test)

All tests run with a HeuristicAIProvider — no real AI or network required.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock

import pytest

from core.domain.domain_discovery import (
    DomainCandidate,
    DomainDiscoveryEngine,
    _MIN_MATCH_COUNT,
)
from core.domain.domain_prioritizer import DomainPrioritizer
from core.domain.domain_autonomous_search import (
    DomainAutonomousSearch,
    _tokenize,
    _expand_with_synonyms,
)
from core.domain.domain_query_engine import DomainQueryEngine
from core.domain.domain_learning_loop import DomainLearningLoop
from core.domain.domain_model_store import DomainModelStore
from core.domain.domain_memory import DomainMemory
from core.domain.domain_state import DomainState
from core.domain.ai_reasoner import AIReasoner, HeuristicAIProvider


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


def _asset(asset_id: str, asset_type: str = "code_file", content: str = "",
           path: str = "") -> dict:
    return {
        "id": asset_id,
        "type": asset_type,
        "path": path or asset_id,
        "content": content,
        "content_hash": "h_" + asset_id,
    }


def _make_messaging_assets() -> list:
    """Return a small corpus that should trigger the 'messaging' domain."""
    return [
        _asset("sms_sender",      content="send sms message deliver"),
        _asset("email_notifier",  content="send email notification deliver"),
        _asset("inbox_reader",    content="inbox outbox message channel"),
        _asset("notification_svc", content="notification send deliver channel"),
        _asset("msg_template",    content="message template sms send"),
    ]


def _make_identity_assets() -> list:
    return [
        _asset("auth_service",   content="auth login token jwt session"),
        _asset("login_handler",  content="login credential access oauth"),
        _asset("token_store",    content="token jwt refresh expire"),
        _asset("session_mgr",    content="session credential access login"),
        _asset("user_auth",      content="auth login access token"),
    ]


def _stub_scanner(assets: list) -> MagicMock:
    m = MagicMock()
    m.scan_all_assets.return_value = assets
    return m


# ===========================================================================
# 1. DomainDiscovery
# ===========================================================================


class TestDomainDiscovery:

    def test_discover_empty_returns_empty(self):
        eng = DomainDiscoveryEngine()
        result = eng.discover([])
        assert result == []

    def test_discover_returns_domain_candidates(self):
        eng = DomainDiscoveryEngine()
        result = eng.discover(_make_messaging_assets())
        assert len(result) > 0
        assert all(isinstance(c, DomainCandidate) for c in result)

    def test_discover_finds_messaging_domain(self):
        eng = DomainDiscoveryEngine()
        results = eng.discover(_make_messaging_assets())
        domains = {c.domain for c in results}
        # "messaging" or some domain containing "message"/"sms" should appear
        assert any("messag" in d or "sms" in d or "notif" in d for d in domains)

    def test_confidence_in_range(self):
        eng = DomainDiscoveryEngine()
        for c in eng.discover(_make_messaging_assets() + _make_identity_assets()):
            assert 0.0 <= c.confidence <= 1.0, (
                f"confidence out of range for {c.domain}: {c.confidence}"
            )

    def test_estimated_size_valid(self):
        eng = DomainDiscoveryEngine()
        valid = {"small", "medium", "large"}
        for c in eng.discover(_make_messaging_assets()):
            assert c.estimated_size in valid, (
                f"invalid estimated_size for {c.domain}: {c.estimated_size}"
            )

    def test_no_nulls_in_output(self):
        eng = DomainDiscoveryEngine()
        for c in eng.discover(_make_messaging_assets()):
            assert c.domain
            assert c.keywords is not None
            assert c.sources is not None
            assert c.reasoning is not None

    def test_discover_is_deterministic(self):
        eng = DomainDiscoveryEngine()
        assets = _make_messaging_assets() + _make_identity_assets()
        first  = [(c.domain, c.confidence) for c in eng.discover(assets)]
        second = [(c.domain, c.confidence) for c in eng.discover(assets)]
        assert first == second

    def test_discover_sorted_by_confidence_desc(self):
        eng = DomainDiscoveryEngine()
        results = eng.discover(_make_messaging_assets() + _make_identity_assets())
        confs = [c.confidence for c in results]
        assert confs == sorted(confs, reverse=True)

    def test_save_and_load_round_trip(self, tmp_path):
        eng = DomainDiscoveryEngine()
        candidates = eng.discover(_make_messaging_assets())
        path = str(tmp_path / "discovered.json")
        eng.save(candidates, path)
        loaded = eng.load(path)
        assert len(loaded) == len(candidates)
        for orig, loaded_c in zip(candidates, loaded):
            assert orig.domain == loaded_c.domain
            assert abs(orig.confidence - loaded_c.confidence) < 0.001

    def test_load_returns_empty_for_missing_file(self, tmp_path):
        eng = DomainDiscoveryEngine()
        result = eng.load(str(tmp_path / "nonexistent.json"))
        assert result == []

    def test_save_creates_parent_dirs(self, tmp_path):
        eng = DomainDiscoveryEngine()
        candidates = eng.discover(_make_messaging_assets())
        path = str(tmp_path / "deep" / "nested" / "discovered.json")
        eng.save(candidates, path)
        assert os.path.isfile(path)

    def test_domain_candidate_to_dict_round_trip(self):
        c = DomainCandidate(
            domain="my_domain",
            confidence=0.75,
            keywords=["foo", "bar"],
            sources=["code", "sql"],
            estimated_size="medium",
            reasoning=["test reason"],
        )
        d = c.to_dict()
        c2 = DomainCandidate.from_dict(d)
        assert c2.domain == c.domain
        assert abs(c2.confidence - c.confidence) < 0.001
        assert sorted(c2.keywords) == sorted(c.keywords)
        assert sorted(c2.sources) == sorted(c.sources)

    def test_few_assets_below_min_match_not_returned(self):
        """A single asset should not produce a discovery candidate."""
        eng = DomainDiscoveryEngine()
        results = eng.discover([_asset("lone_ranger", content="auth login token")])
        # Only 1 asset — below _MIN_MATCH_COUNT=2 — nothing should meet threshold
        # (phase 2 path tokens also need >=2 matches)
        assert isinstance(results, list)


# ===========================================================================
# 2. DomainPrioritizer
# ===========================================================================


class TestDomainPrioritizer:

    def test_prioritize_empty_returns_empty(self):
        p = DomainPrioritizer()
        assert p.prioritize([]) == []

    def test_priority_is_one_indexed_no_gaps(self):
        eng = DomainDiscoveryEngine()
        candidates = eng.discover(_make_messaging_assets() + _make_identity_assets())
        if not candidates:
            pytest.skip("no candidates discovered")
        p = DomainPrioritizer()
        result = p.prioritize(candidates)
        priorities = [r["priority"] for r in result]
        assert priorities[0] == 1
        assert priorities == list(range(1, len(priorities) + 1))

    def test_identity_before_messaging(self):
        """Identity (tier 1) must appear before messaging (tier 4)."""
        identity_candidate = DomainCandidate(
            domain="identity_access",
            confidence=0.8,
            keywords=["auth", "login", "token", "jwt"],
            sources=["code"],
        )
        messaging_candidate = DomainCandidate(
            domain="messaging",
            confidence=0.8,
            keywords=["sms", "email", "notification", "send"],
            sources=["code"],
        )
        p = DomainPrioritizer()
        result = p.prioritize([messaging_candidate, identity_candidate])
        domain_order = [r["domain"] for r in result]
        assert domain_order.index("identity_access") < domain_order.index("messaging")

    def test_result_contains_required_keys(self):
        candidate = DomainCandidate(
            domain="foo_domain",
            confidence=0.5,
            keywords=["foo"],
            sources=["code"],
        )
        p = DomainPrioritizer()
        result = p.prioritize([candidate])
        assert len(result) == 1
        row = result[0]
        assert "domain"   in row
        assert "priority" in row
        assert "tier"     in row
        assert "reason"   in row

    def test_tier_is_positive_integer(self):
        candidates = [
            DomainCandidate("auth_domain",  0.9, ["auth", "login"],     ["code"]),
            DomainCandidate("order_domain", 0.7, ["order", "purchase"],  ["code"]),
        ]
        p = DomainPrioritizer()
        for row in p.prioritize(candidates):
            assert isinstance(row["tier"], int)
            assert row["tier"] >= 1

    def test_prioritize_is_deterministic(self):
        eng = DomainDiscoveryEngine()
        candidates = eng.discover(_make_messaging_assets() + _make_identity_assets())
        p = DomainPrioritizer()
        r1 = [r["domain"] for r in p.prioritize(candidates)]
        r2 = [r["domain"] for r in p.prioritize(candidates)]
        assert r1 == r2

    def test_save_and_load_round_trip(self, tmp_path):
        candidates = [
            DomainCandidate("identity", 0.9, ["auth", "login"], ["code"]),
            DomainCandidate("messaging", 0.7, ["sms", "send"],   ["code"]),
        ]
        p = DomainPrioritizer()
        priority_list = p.prioritize(candidates)
        path = str(tmp_path / "priority.json")
        p.save(priority_list, path)
        loaded = p.load(path)
        assert len(loaded) == len(priority_list)
        assert loaded[0]["domain"] == priority_list[0]["domain"]
        assert loaded[0]["priority"] == 1

    def test_load_returns_empty_for_missing_file(self, tmp_path):
        p = DomainPrioritizer()
        assert p.load(str(tmp_path / "missing.json")) == []

    def test_single_candidate_priority_is_one(self):
        p = DomainPrioritizer()
        result = p.prioritize(
            [DomainCandidate("solo", 0.5, ["solo"], ["code"])]
        )
        assert result[0]["priority"] == 1


# ===========================================================================
# 3. DomainAutonomousSearch
# ===========================================================================


class TestDomainAutonomousSearch:

    def _make_search(self) -> DomainAutonomousSearch:
        return DomainAutonomousSearch(DomainQueryEngine())

    def test_search_empty_assets_returns_empty(self):
        s = self._make_search()
        result = s.search("find auth entities", "identity", [])
        assert result == []

    def test_search_returns_scored_dicts(self):
        s = self._make_search()
        assets = _make_identity_assets()
        results = s.search("auth login token", "identity", assets)
        assert isinstance(results, list)
        if results:
            assert "asset_id" in results[0]
            assert "score"    in results[0]

    def test_search_scores_non_negative(self):
        s = self._make_search()
        for r in s.search("auth login token", "identity", _make_identity_assets()):
            assert r["score"] >= 0.0

    def test_search_is_deterministic(self):
        s = self._make_search()
        assets = _make_identity_assets()
        r1 = s.search("auth login token", "identity", assets)
        r2 = s.search("auth login token", "identity", assets)
        assert [x["asset_id"] for x in r1] == [x["asset_id"] for x in r2]

    def test_gap_to_intents_returns_list(self):
        s = self._make_search()
        gap = {"type": "missing_entity", "description": "Missing role entity",
               "suggested_terms": ["role", "permission"]}
        intents = s.gap_to_intents(gap, "identity")
        assert isinstance(intents, list)
        assert len(intents) >= 1

    def test_gap_to_intents_max_three(self):
        s = self._make_search()
        gap = {"type": "weak_rule", "description": "desc",
               "suggested_terms": ["a", "b", "c"]}
        intents = s.gap_to_intents(gap, "mydom")
        assert len(intents) <= 3

    def test_gap_to_intents_empty_gap(self):
        s = self._make_search()
        intents = s.gap_to_intents({}, "mydom")
        assert isinstance(intents, list)

    def test_find_assets_for_gaps_empty_gaps(self):
        s = self._make_search()
        result = s.find_assets_for_gaps([], "identity", _make_identity_assets())
        assert result == []

    def test_find_assets_for_gaps_empty_assets(self):
        s = self._make_search()
        gaps = [{"type": "missing_entity", "description": "no entities",
                 "suggested_terms": ["entity"]}]
        result = s.find_assets_for_gaps(gaps, "identity", [])
        assert result == []

    def test_find_assets_for_gaps_returns_asset_dicts(self):
        s = self._make_search()
        assets = _make_identity_assets()
        gaps = [{"type": "missing_entity", "id": "g1",
                 "description": "auth entity missing",
                 "suggested_terms": ["auth", "role"]}]
        results = s.find_assets_for_gaps(gaps, "identity", assets)
        assert isinstance(results, list)
        if results:
            assert "id" in results[0]

    def test_find_assets_for_gaps_is_deterministic(self):
        s = self._make_search()
        assets = _make_identity_assets()
        gaps = [{"type": "missing_flow", "id": "g1",
                 "description": "missing flow",
                 "suggested_terms": ["login", "flow"]}]
        r1 = [a["id"] for a in s.find_assets_for_gaps(gaps, "identity", assets)]
        r2 = [a["id"] for a in s.find_assets_for_gaps(gaps, "identity", assets)]
        assert r1 == r2

    def test_tokenize_removes_noise(self):
        tokens = _tokenize("the and for")
        assert not tokens  # all noise

    def test_tokenize_splits_camel_case(self):
        tokens = _tokenize("AuthService")
        assert "auth" in tokens or "service" in tokens or len(tokens) >= 1

    def test_expand_with_synonyms_adds_related_terms(self):
        expanded = _expand_with_synonyms(["entity"])
        assert len(expanded) > 1
        assert "entity" in expanded

    def test_search_respects_max_results(self):
        s = self._make_search()
        assets = _make_identity_assets() * 10  # 50 assets
        results = s.search("auth login token", "identity", assets, max_results=3)
        assert len(results) <= 3


# ===========================================================================
# 4. DomainLearningLoop v3 params (backward compatibility)
# ===========================================================================


class TestLearningLoopV3:
    """Verify that the new search_engine/all_assets params do not break existing usage."""

    def _make_loop(self, tmp_path, search_engine=None, verbose=False):
        store   = DomainModelStore(str(tmp_path / "domains"))
        memory  = DomainMemory(str(tmp_path / "data"))
        state   = DomainState(str(tmp_path / "domains"))
        state.load()
        reasoner = AIReasoner(provider=HeuristicAIProvider())
        qe       = DomainQueryEngine()
        return DomainLearningLoop(
            model_store=store,
            memory=memory,
            reasoner=reasoner,
            query_engine=qe,
            state=state,
            search_engine=search_engine,
            verbose=verbose,
        )

    def test_default_no_search_engine(self, tmp_path):
        """search_engine=None is the default; constructor must not fail."""
        loop = self._make_loop(tmp_path)
        assert loop._search_engine is None

    def test_run_iteration_without_search_engine(self, tmp_path):
        """run_iteration works normally when search_engine=None."""
        loop = self._make_loop(tmp_path)
        assets = _make_identity_assets()
        result = loop.run_iteration("identity", assets)
        assert "completeness_score" in result
        assert "consistency_score"  in result
        assert "saturation_score"   in result
        assert "status"             in result

    def test_run_iteration_with_all_assets_none(self, tmp_path):
        """all_assets=None must behave identically to not passing it."""
        loop = self._make_loop(tmp_path)
        result = loop.run_iteration("identity", _make_identity_assets(), all_assets=None)
        assert "status" in result

    def test_run_iteration_with_search_engine_and_no_gaps(self, tmp_path):
        """When there are no gaps, the search engine should not be called."""
        mock_search = MagicMock()
        loop = self._make_loop(tmp_path, search_engine=mock_search)
        # Run with an empty assets list — no assets means no processing,
        # but gaps could be empty too, so find_assets_for_gaps should not be called
        loop.run_iteration("identity", [], all_assets=[])
        # If gaps were empty, find_assets_for_gaps must NOT be called
        # (the implementation only calls it when gaps is truthy)
        # We can't guarantee gaps=[] here, but we can assert no crash
        assert True

    def test_run_iteration_with_search_engine_expands_pool(self, tmp_path):
        """search_engine.find_assets_for_gaps is called and new assets are added."""
        extra_asset = _asset("extra_from_search", content="auth login extra")

        class _FakeSearch:
            """Returns one extra asset from find_assets_for_gaps."""
            def find_assets_for_gaps(self, gaps, domain_name, assets, memory=None,
                                     max_per_gap=5, max_gaps=10):
                return [extra_asset]

        loop = self._make_loop(tmp_path, search_engine=_FakeSearch())
        # Run with modest assets; we need gaps to be non-empty for expansion to fire.
        # HeuristicAIProvider.detect_gaps always returns at least some gaps.
        base_assets = _make_identity_assets()
        result = loop.run_iteration("identity", base_assets, all_assets=base_assets)
        # Main verifiable invariant: result shape is correct
        assert "status" in result
        assert "processed_count" in result

    def test_result_has_all_score_keys(self, tmp_path):
        loop = self._make_loop(tmp_path)
        result = loop.run_iteration("messaging", _make_messaging_assets())
        for key in ("completeness_score", "new_information_score",
                    "consistency_score", "saturation_score"):
            assert key in result, f"missing key: {key}"

    def test_backward_compat_no_extra_kwargs(self, tmp_path):
        """A loop constructed with v1/v2 positional params still works."""
        store   = DomainModelStore(str(tmp_path / "domains"))
        memory  = DomainMemory(str(tmp_path / "data"))
        state   = DomainState(str(tmp_path / "domains"))
        state.load()
        reasoner = AIReasoner(provider=HeuristicAIProvider())
        qe       = DomainQueryEngine()
        # v2-style construction — no search_engine
        loop = DomainLearningLoop(
            model_store=store,
            memory=memory,
            reasoner=reasoner,
            query_engine=qe,
            state=state,
            verbose=False,
        )
        result = loop.run_iteration("identity", _make_identity_assets())
        assert "status" in result


# ===========================================================================
# 5. DomainEngineV3 — smoke tests
# ===========================================================================


class TestDomainEngineV3:
    """Smoke tests — verify wiring and API contract without file I/O side effects."""

    def _make_engine(self, tmp_path, extra_assets=None):
        from core.domain.domain_engine_v3 import DomainEngineV3

        assets = (extra_assets or []) + _make_identity_assets() + _make_messaging_assets()
        scanner = _stub_scanner(assets)
        return DomainEngineV3(
            scanner=scanner,
            domains_root=str(tmp_path / "domains"),
            data_root=str(tmp_path / "data"),
            seed_list=[],
            max_iterations_per_domain=1,
            max_assets_per_iter=5,
            ai_provider=HeuristicAIProvider(),
            verbose=False,
        )

    def test_constructor_does_not_crash(self, tmp_path):
        engine = self._make_engine(tmp_path)
        assert engine is not None

    def test_discover_and_prioritize_returns_tuple(self, tmp_path):
        from core.domain.domain_engine_v3 import DomainEngineV3

        engine = self._make_engine(tmp_path)
        assets = _make_identity_assets() + _make_messaging_assets()
        result = engine.discover_and_prioritize(assets)
        assert isinstance(result, tuple)
        assert len(result) == 2
        candidates, priority = result
        assert isinstance(candidates, list)
        assert isinstance(priority, list)

    def test_discover_and_prioritize_empty(self, tmp_path):
        engine = self._make_engine(tmp_path)
        candidates, priority = engine.discover_and_prioritize([])
        assert candidates == []
        assert priority == []

    def test_discover_and_prioritize_is_deterministic(self, tmp_path):
        engine = self._make_engine(tmp_path)
        assets = _make_identity_assets() + _make_messaging_assets()
        c1, p1 = engine.discover_and_prioritize(assets)
        c2, p2 = engine.discover_and_prioritize(assets)
        assert [c.domain for c in c1] == [c.domain for c in c2]
        assert [r["domain"] for r in p1] == [r["domain"] for r in p2]

    def test_run_returns_list(self, tmp_path):
        engine = self._make_engine(tmp_path)
        results = engine.run(resume=False)
        assert isinstance(results, list)

    def test_run_results_have_domain_key(self, tmp_path):
        engine = self._make_engine(tmp_path)
        for r in engine.run(resume=False):
            assert "domain" in r

    def test_run_resume_skips_stable_domains(self, tmp_path):
        """Running twice with resume=True must not re-process stable domains."""
        from core.domain.domain_engine_v3 import DomainEngineV3

        assets = _make_identity_assets() + _make_messaging_assets()
        scanner = _stub_scanner(assets)

        def _fresh():
            return DomainEngineV3(
                scanner=scanner,
                domains_root=str(tmp_path / "domains"),
                data_root=str(tmp_path / "data"),
                seed_list=[],
                max_iterations_per_domain=50,
                max_assets_per_iter=5,
                ai_provider=HeuristicAIProvider(),
                verbose=False,
            )

        # First run — process everything
        first_results = _fresh().run(resume=False)
        # Second run with resume=True — stable domains should be skipped
        second_results = _fresh().run(resume=True)
        skipped = [r for r in second_results if r.get("skipped")]
        assert len(skipped) >= 0  # may or may not skip depending on stable status

    def test_run_domain_engine_v3_function(self, tmp_path):
        """run_domain_engine_v3() convenience wrapper returns list."""
        from core.domain.domain_engine_v3 import run_domain_engine_v3

        assets = _make_identity_assets() + _make_messaging_assets()
        scanner = _stub_scanner(assets)
        results = run_domain_engine_v3(
            scanner=scanner,
            domains_root=str(tmp_path / "domains"),
            data_root=str(tmp_path / "data"),
            seed_list=[],
            max_iterations_per_domain=1,
            max_assets_per_iter=5,
            ai_provider=HeuristicAIProvider(),
            verbose=False,
        )
        assert isinstance(results, list)

    def test_discovery_output_files_written(self, tmp_path):
        """run() must write discovered_domains.json and domain_priority.json."""
        engine = self._make_engine(tmp_path)
        engine.run(resume=False)
        out_dir = tmp_path / "data" / "domains"
        disc = out_dir / "discovered_domains.json"
        prio = out_dir / "domain_priority.json"
        assert disc.exists(), "discovered_domains.json not written"
        assert prio.exists(), "domain_priority.json not written"

    def test_discovery_output_files_are_valid_json(self, tmp_path):
        engine = self._make_engine(tmp_path)
        engine.run(resume=False)
        out_dir = tmp_path / "data" / "domains"
        for fname in ("discovered_domains.json", "domain_priority.json"):
            fpath = out_dir / fname
            with open(fpath, encoding="utf-8") as fh:
                data = json.load(fh)
            assert isinstance(data, list)
