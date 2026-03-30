"""
tests/test_domain_engine.py — Tests for:
    core/domain_information.py    (compute_new_information, compute_completeness, load_domain_snapshot)
    core/domain_engine.py         (keyword_relevance, get_keywords_for_domain,
                                   DomainEngine.select_assets, discover_domains,
                                   run_domain, run)
    core/domain_state.py          (new_information_score field)

Naming convention: test_MethodOrBehavior_StateUnderTest_ExpectedBehavior
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from core.domain_information import (
    compute_new_information,
    compute_completeness,
    load_domain_snapshot,
    TRACKED_KEYS,
    SECTION_WEIGHTS,
    NEW_INFO_THRESHOLD,
    COMPLETENESS_THRESHOLD,
)
from core.domain_engine import (
    DomainEngine,
    keyword_relevance,
    get_keywords_for_domain,
    DEFAULT_SEEDS,
    DOMAIN_KEYWORDS,
)
from core.domain_state import DomainState, STATUS_COMPLETE, STATUS_SATURATED, STATUS_IN_PROGRESS
from core.ai_processor import StubAIProcessor


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _stub_asset(asset_id: str, asset_type: str = "code_file", content: str = "") -> dict:
    return {"id": asset_id, "type": asset_type, "content_hash": "h", "content": content}


def _stub_scanner(assets: list):
    m = MagicMock()
    m.scan_all_assets.return_value = assets
    return m


def _make_domain_dir(tmp_path: Path, name: str, **model_overrides) -> Path:
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    defaults = {
        "000_meta.json":      {"domain": name, "coverage": {}, "roi_score": 5},
        "010_entities.json":  {"domain": name, "entities": []},
        "020_behaviors.json": {"domain": name, "behaviors": []},
        "030_flows.json":     {"domain": name, "flows": []},
        "040_events.json":    {"domain": name, "events": []},
        "070_rules.json":     {"domain": name, "rules": []},
        "080_pseudocode.json":{"domain": name, "pseudocode": []},
        "090_rebuild.json":   {"domain": name, "rebuild_requirements": []},
    }
    defaults.update(model_overrides)
    for fname, data in defaults.items():
        _write_json(d / fname, data)
    return d


def _make_engine(tmp_path: Path, domains_root: Path, assets: list,
                  max_iterations: int = 3) -> DomainEngine:
    stage_state = MagicMock()
    stage_state.pending_stages.return_value = []   # all stages already done
    return DomainEngine(
        scanner=_stub_scanner(assets),
        stage_state=stage_state,
        ai_processor=StubAIProcessor(),
        data_root=str(tmp_path / "data"),
        domains_root=str(domains_root),
        max_iterations=max_iterations,
        max_assets=20,
        verbose=False,
    )


def _full_snapshot() -> dict:
    """A snapshot that satisfies all section targets."""
    return {
        "entities":             [{"name": f"Entity{i}"} for i in range(5)],
        "behaviors":            [{"name": f"Behavior{i}"} for i in range(5)],
        "flows":                [{"name": f"Flow{i}"} for i in range(3)],
        "events":               [{"name": f"Event{i}"} for i in range(2)],
        "rules":                [{"rule": f"Rule{i}"} for i in range(3)],
        "pseudocode":           [{"pseudocode": f"code{i}"} for i in range(2)],
        "rebuild_requirements": [{"requirement": f"REQ-{i}"} for i in range(4)],
    }


# ═════════════════════════════════════════════════════════════════════════════
# TestComputeNewInformation
# ═════════════════════════════════════════════════════════════════════════════

class TestComputeNewInformation:
    def test_BothEmpty_ReturnsZero(self):
        assert compute_new_information({}, {}) == 0.0

    def test_OldEmpty_NewHasItems_ReturnsOne(self):
        new = {"entities": [{"name": "User"}, {"name": "Order"}]}
        assert compute_new_information({}, new) == 1.0

    def test_SameContent_ReturnsZero(self):
        snap = _full_snapshot()
        assert compute_new_information(snap, snap) == 0.0

    def test_PartiallyNewContent_ReturnsCorrectFraction(self):
        old = {"entities": [{"name": "User"}, {"name": "Order"}]}
        new = {"entities": [{"name": "User"}, {"name": "Order"}, {"name": "Invoice"}]}
        # 1 new out of 2 baseline = 0.5
        result = compute_new_information(old, new)
        assert result == pytest.approx(0.5)

    def test_AllNewInSecondSection_CountedCorrectly(self):
        old = {"entities": [{"name": "User"}]}
        new = {
            "entities": [{"name": "User"}],
            "behaviors": [{"name": "CreateUser"}, {"name": "DeleteUser"}],
        }
        # 0 new entities + 2 new behaviors out of 1 baseline entity = 2/1 → capped to 1.0
        result = compute_new_information(old, new)
        assert result == pytest.approx(1.0)

    def test_NormalisedDuplicates_CountedOnce(self):
        old = {"entities": [{"name": "User"}]}
        new = {"entities": [{"name": "User"}, {"name": "user "}]}  # same after normalise
        # "user" already in old_keys, " user" normalises same → 0 new
        result = compute_new_information(old, new)
        assert result == 0.0

    def test_ScoreAboveThreshold_GenuinelyNew(self):
        old = {"entities": [{"name": "A"}]}
        new = {"entities": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}
        result = compute_new_information(old, new)
        assert result > NEW_INFO_THRESHOLD

    def test_SameSnapshotTwice_ScoreBelowThreshold(self):
        snap = _full_snapshot()
        result = compute_new_information(snap, snap)
        assert result < NEW_INFO_THRESHOLD


# ═════════════════════════════════════════════════════════════════════════════
# TestComputeCompleteness
# ═════════════════════════════════════════════════════════════════════════════

class TestComputeCompleteness:
    def test_EmptySnapshot_ReturnsZero(self):
        assert compute_completeness({}) == 0.0

    def test_FullSnapshot_ScoreAboveThreshold(self):
        result = compute_completeness(_full_snapshot())
        assert result >= COMPLETENESS_THRESHOLD

    def test_PartialSnapshot_ScoreBelowThreshold(self):
        partial = {"entities": [{"name": "X"}]}   # only 1/5 entities, nothing else
        result = compute_completeness(partial)
        assert result < COMPLETENESS_THRESHOLD

    def test_SectionWeightsSumToOne(self):
        assert abs(sum(SECTION_WEIGHTS.values()) - 1.0) < 1e-9

    def test_AllTrackedKeysHaveWeights(self):
        for key in TRACKED_KEYS:
            assert key in SECTION_WEIGHTS

    def test_ResultIsClamped_NeverExceedsOne(self):
        huge = {"entities": [{"name": f"E{i}"} for i in range(100)]}
        result = compute_completeness(huge)
        assert result <= 1.0


# ═════════════════════════════════════════════════════════════════════════════
# TestLoadDomainSnapshot
# ═════════════════════════════════════════════════════════════════════════════

class TestLoadDomainSnapshot:
    def test_EmptyDir_ReturnsEmptyLists(self, tmp_path):
        (tmp_path / "Dom").mkdir()
        snap = load_domain_snapshot(tmp_path / "Dom")
        for key in TRACKED_KEYS:
            assert snap[key] == []

    def test_LoadsEntitiesFromFile(self, tmp_path):
        d = tmp_path / "Dom"
        d.mkdir()
        _write_json(d / "010_entities.json", {"entities": [{"name": "Order"}]})
        snap = load_domain_snapshot(d)
        assert snap["entities"] == [{"name": "Order"}]

    def test_LoadsAllSectionFiles(self, tmp_path):
        d = _make_domain_dir(tmp_path, "Dom",
            **{"010_entities.json": {"domain": "Dom", "entities": [{"name": "E1"}]},
               "070_rules.json": {"domain": "Dom", "rules": [{"rule": "R1"}]}})
        snap = load_domain_snapshot(d)
        assert len(snap["entities"]) == 1
        assert len(snap["rules"]) == 1


# ═════════════════════════════════════════════════════════════════════════════
# TestKeywordRelevance
# ═════════════════════════════════════════════════════════════════════════════

class TestKeywordRelevance:
    def test_NoKeywords_ReturnsZero(self):
        asset = {"id": "code:MessageService.cs", "content": "sends messages"}
        assert keyword_relevance(asset, []) == 0.0

    def test_AllKeywordsMatch_ReturnsOne(self):
        asset = {"id": "code:x.cs", "content": "message send notify"}
        result = keyword_relevance(asset, ["message", "send", "notify"])
        assert result == pytest.approx(1.0)

    def test_PartialMatch_ReturnsCorrectFraction(self):
        asset = {"id": "code:x.cs", "content": "only message here"}
        result = keyword_relevance(asset, ["message", "invoice", "billing"])
        assert result == pytest.approx(1 / 3)

    def test_NoMatch_ReturnsZero(self):
        asset = {"id": "code:Foo.cs", "content": "some unrelated content"}
        result = keyword_relevance(asset, ["invoice", "billing", "payment"])
        assert result == 0.0

    def test_MatchInAssetId_Counted(self):
        asset = {"id": "code:MessageService.cs", "content": ""}
        result = keyword_relevance(asset, ["message"])
        assert result == pytest.approx(1.0)

    def test_EmptyAsset_ReturnsZero(self):
        asset = {"id": "", "content": ""}
        result = keyword_relevance(asset, ["message", "send"])
        assert result == 0.0


# ═════════════════════════════════════════════════════════════════════════════
# TestGetKeywordsForDomain
# ═════════════════════════════════════════════════════════════════════════════

class TestGetKeywordsForDomain:
    def test_KnownDomain_ReturnsKeywords(self):
        kw = get_keywords_for_domain("messaging")
        assert "message" in kw
        assert "send" in kw

    def test_KnownDomainCaseInsensitive_ReturnsKeywords(self):
        kw = get_keywords_for_domain("Messaging")
        assert "message" in kw

    def test_UnknownDomain_ReturnsFallbackTokens(self):
        kw = get_keywords_for_domain("CustomAlerts")
        assert len(kw) > 0

    def test_AllSeeds_HaveKeywordEntries(self):
        for seed in DEFAULT_SEEDS:
            assert seed in DOMAIN_KEYWORDS, f"Missing keywords for seed '{seed}'"


# ═════════════════════════════════════════════════════════════════════════════
# TestDomainEngineSelectAssets
# ═════════════════════════════════════════════════════════════════════════════

class TestDomainEngineSelectAssets:
    def _engine(self, tmp_path, domains_root, assets):
        return _make_engine(tmp_path, domains_root, assets)

    def test_GlobalAssets_AlwaysIncluded(self, tmp_path):
        domains = tmp_path / "domains"
        assets = [
            _stub_asset("work_items:batch:0", "work_items_batch"),
            _stub_asset("git_insights:batch:0", "git_insights_batch"),
            _stub_asset("code:Unrelated/Foo.cs", "code_file"),
        ]
        engine = self._engine(tmp_path, domains, assets)
        selected = engine.select_assets("messaging")
        selected_ids = {a["id"] for a in selected}
        assert "work_items:batch:0" in selected_ids
        assert "git_insights:batch:0" in selected_ids

    def test_KeywordMatch_IncludesAsset(self, tmp_path):
        domains = tmp_path / "domains"
        assets = [
            _stub_asset("code:Whatever.cs", "code_file",
                        content="sends message to notify recipient"),
        ]
        engine = self._engine(tmp_path, domains, assets)
        selected = engine.select_assets("messaging")
        assert len(selected) == 1

    def test_NoKeywordNoPathMatch_ExcludesAsset(self, tmp_path):
        domains = tmp_path / "domains"
        assets = [_stub_asset("code:BillingService.cs", "code_file",
                               content="invoice payment credit")]
        engine = self._engine(tmp_path, domains, assets)
        # Messaging domain should not pick up billing code
        selected = engine.select_assets("messaging", keywords=["message", "sms"])
        assert len(selected) == 0

    def test_MaxAssets_LimitsOutput(self, tmp_path):
        domains = tmp_path / "domains"
        assets = [
            _stub_asset(f"code:Messaging/File{i}.cs", "code_file")
            for i in range(100)
        ]
        engine = DomainEngine(
            scanner=_stub_scanner(assets),
            stage_state=MagicMock(),
            ai_processor=StubAIProcessor(),
            data_root=str(tmp_path / "data"),
            domains_root=str(domains),
            max_assets=10,
            verbose=False,
        )
        selected = engine.select_assets("Messaging")
        assert len(selected) <= 10

    def test_PathMatchPrioritisedOverKeywordOnly(self, tmp_path):
        domains = tmp_path / "domains"
        path_asset = _stub_asset("code:Sms/SmsService.cs", "code_file")
        keyword_asset = _stub_asset("code:Other/Misc.cs", "code_file",
                                    content="sms message send")
        assets = [keyword_asset, path_asset]
        engine = self._engine(tmp_path, domains, assets)
        selected = engine.select_assets("Sms")
        # Both included; path_asset should be first (higher score)
        assert selected[0]["id"] == path_asset["id"]


# ═════════════════════════════════════════════════════════════════════════════
# TestDomainEngineDiscoverDomains
# ═════════════════════════════════════════════════════════════════════════════

class TestDomainEngineDiscoverDomains:
    def test_DefaultSeeds_ReturnedWhenNoDomainDir(self, tmp_path):
        domains = tmp_path / "domains"
        engine = _make_engine(tmp_path, domains, [])
        names = engine.discover_domains(discover_from_dir=False)
        assert set(names) == set(DEFAULT_SEEDS)

    def test_CustomSeedList_Returned(self, tmp_path):
        domains = tmp_path / "domains"
        engine = _make_engine(tmp_path, domains, [])
        names = engine.discover_domains(seed_list=["alpha", "beta"], discover_from_dir=False)
        assert "alpha" in names
        assert "beta" in names

    def test_ExistingDirDomains_AppendedToSeeds(self, tmp_path):
        domains = tmp_path / "domains"
        _make_domain_dir(domains, "Billing")
        _make_domain_dir(domains, "Sms")
        engine = _make_engine(tmp_path, domains, [])
        names = engine.discover_domains(seed_list=[], discover_from_dir=True)
        assert "Billing" in names
        assert "Sms" in names

    def test_NoDuplicates_WhenSeedMatchesDir(self, tmp_path):
        domains = tmp_path / "domains"
        _make_domain_dir(domains, "messaging")
        engine = _make_engine(tmp_path, domains, [])
        names = engine.discover_domains(seed_list=["messaging"], discover_from_dir=True)
        assert names.count("messaging") == 1

    def test_SortedByRoiScore(self, tmp_path):
        domains = tmp_path / "domains"
        _make_domain_dir(domains, "LowRoi",  **{"000_meta.json": {"roi_score": 1, "coverage": {}}})
        _make_domain_dir(domains, "HighRoi", **{"000_meta.json": {"roi_score": 9, "coverage": {}}})
        engine = _make_engine(tmp_path, domains, [])
        names = engine.discover_domains(seed_list=[], discover_from_dir=True)
        high_idx = names.index("HighRoi")
        low_idx  = names.index("LowRoi")
        assert high_idx < low_idx


# ═════════════════════════════════════════════════════════════════════════════
# TestDomainEngineRunDomain
# ═════════════════════════════════════════════════════════════════════════════

class TestDomainEngineRunDomain:
    def test_AlreadyComplete_SkipsProcessing(self, tmp_path):
        domains = tmp_path / "domains"
        _make_domain_dir(domains, "Sms")
        state = DomainState.load(domains, "Sms")
        state.mark_complete()
        state.save()

        engine = _make_engine(tmp_path, domains, [])
        result = engine.run_domain("Sms")
        assert result["status"] == STATUS_COMPLETE
        assert result["iterations"] == 0   # no iterations run

    def test_NewDomain_CreatesDirectoryAndStateFile(self, tmp_path):
        domains = tmp_path / "domains"
        engine = _make_engine(tmp_path, domains, [])
        engine.run_domain("NewDomain")
        assert (domains / "NewDomain").is_dir()
        assert (domains / "NewDomain" / "domain_state.json").exists()

    def test_Result_ContainsRequiredKeys(self, tmp_path):
        domains = tmp_path / "domains"
        engine = _make_engine(tmp_path, domains, [])
        result = engine.run_domain("TestDomain")
        assert "domain" in result
        assert "status" in result
        assert "completeness_score" in result
        assert "new_information_score" in result
        assert "iterations" in result

    def test_IdleExit_WhenNoAssetsAndNotFirstIteration(self, tmp_path):
        """
        With no assets and stub AI, processed=0 from iteration 2 onward.
        The engine should exit the loop early rather than spinning all iterations.
        """
        domains = tmp_path / "domains"
        engine = _make_engine(tmp_path, domains, [], max_iterations=10)
        result = engine.run_domain("EmptyDomain")
        # Should exit well before 10 iterations due to idle check
        assert result["iterations"] <= 3

    def test_MaxIterations_MarksAsSaturated(self, tmp_path):
        """
        Engine forced to run with max_iterations=1 and no convergence.
        Because after iter 1 processed=0 triggers idle exit first,
        we use max_iterations=1 specifically to hit the `else` branch.
        """
        domains = tmp_path / "domains"
        # Build a domain with barely-populated model so completeness stays low
        # and new_info=0 (no real AI outputs).  With max_iterations=1 the
        # for-else `else` branch fires.
        engine = DomainEngine(
            scanner=_stub_scanner([]),
            stage_state=MagicMock(),
            ai_processor=StubAIProcessor(),
            data_root=str(tmp_path / "data"),
            domains_root=str(domains),
            max_iterations=1,
            max_assets=5,
            verbose=False,
        )
        result = engine.run_domain("Limited")
        # Only 1 iteration then saturated (for…else fires)
        assert result["status"] == STATUS_SATURATED
        assert result["iterations"] == 1

    def test_DomainStateNewInfoScore_Persisted(self, tmp_path):
        domains = tmp_path / "domains"
        engine = _make_engine(tmp_path, domains, [])
        engine.run_domain("Track")
        state = DomainState.load(domains, "Track")
        # new_information_score should be a float (was persisted)
        assert isinstance(state.new_information_score, float)


# ═════════════════════════════════════════════════════════════════════════════
# TestDomainEngineRun (multi-domain)
# ═════════════════════════════════════════════════════════════════════════════

class TestDomainEngineRun:
    def test_RunWithSeeds_ProcessesEach(self, tmp_path):
        domains = tmp_path / "domains"
        engine = _make_engine(tmp_path, domains, [])
        results = engine.run(seed_list=["alpha", "beta"], discover_from_dir=False)
        names = {r["domain"] for r in results}
        assert "alpha" in names
        assert "beta" in names

    def test_MaxDomains_LimitsCount(self, tmp_path):
        domains = tmp_path / "domains"
        engine = _make_engine(tmp_path, domains, [])
        results = engine.run(
            seed_list=["a", "b", "c", "d"],
            discover_from_dir=False,
            max_domains=2,
        )
        assert len(results) == 2

    def test_KeywordsMap_PassedToDomain(self, tmp_path):
        """Engine accepts keywords_map without error."""
        domains = tmp_path / "domains"
        engine = _make_engine(tmp_path, domains, [])
        results = engine.run(
            seed_list=["billing"],
            discover_from_dir=False,
            keywords_map={"billing": ["invoice", "payment"]},
        )
        assert len(results) == 1

    def test_AllResultsHaveStatus(self, tmp_path):
        domains = tmp_path / "domains"
        engine = _make_engine(tmp_path, domains, [])
        results = engine.run(seed_list=["x", "y"], discover_from_dir=False)
        for r in results:
            assert r["status"] in (
                "not_started", "in_progress", "complete", "saturated"
            )


# ═════════════════════════════════════════════════════════════════════════════
# TestDomainStateNewInfoScore
# ═════════════════════════════════════════════════════════════════════════════

class TestDomainStateNewInfoScore:
    def test_DefaultValue_IsZero(self, tmp_path):
        (tmp_path / "X").mkdir()
        state = DomainState.load(tmp_path, "X")
        assert state.new_information_score == 0.0

    def test_UpdateMethod_SetsValue(self, tmp_path):
        (tmp_path / "X").mkdir()
        state = DomainState.load(tmp_path, "X")
        state.update_new_information_score(0.314)
        assert state.new_information_score == pytest.approx(0.314)

    def test_SaveAndReload_PreservesValue(self, tmp_path):
        (tmp_path / "X").mkdir()
        state = DomainState.load(tmp_path, "X")
        state.update_new_information_score(0.078)
        state.save()
        loaded = DomainState.load(tmp_path, "X")
        assert loaded.new_information_score == pytest.approx(0.078)

    def test_UpdateMethod_RoundsToFourDecimals(self, tmp_path):
        (tmp_path / "X").mkdir()
        state = DomainState.load(tmp_path, "X")
        state.update_new_information_score(0.123456789)
        assert state.new_information_score == pytest.approx(0.1235, abs=1e-4)
