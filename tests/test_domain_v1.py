"""Tests for core/domain/* — DomainEngine v1."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from core.domain.ai.domain_mapper import merge
from core.domain.ai.refiner import refine
from core.domain.ai.semantic_analyzer import INSIGHT_KEYS, analyze
from core.domain.domain_asset_matcher import match_assets
from core.domain.domain_engine import DomainEngine
from core.domain.domain_model_store import DomainModelStore
from core.domain.domain_scoring import (
    COMPLETENESS_THRESHOLD,
    NEW_INFO_THRESHOLD,
    compute_completeness,
    compute_new_information,
    is_stable,
)
from core.domain.domain_selector import pick_next
from core.domain.domain_state import (
    DOMAIN_SEEDS,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    STATUS_STABLE,
    DomainProgress,
    DomainState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(tmp_path, domains=None) -> DomainState:
    state = DomainState(str(tmp_path))
    state.load()
    if domains:
        state.ensure_domains(domains)
    return state


def _full_model() -> Dict[str, Any]:
    """Return a model with enough items to score >= completeness threshold."""
    return {
        "entities": ["A", "B", "C", "D", "E", "F"],
        "behaviors": ["x", "y", "z", "w", "v", "u"],
        "flows": ["f1", "f2", "f3", "f4"],
        "rules": ["r1", "r2", "r3", "r4"],
        "events": ["e1", "e2", "e3"],
        "integrations": ["i1", "i2", "i3"],
        "batch": [],
        "pseudocode": [],
        "rebuild": [],
    }


class _FakeScanner:
    def __init__(self, assets: List[Dict]) -> None:
        self._assets = assets

    def scan_all_assets(self) -> List[Dict]:
        return list(self._assets)


# ---------------------------------------------------------------------------
# TestDomainProgress
# ---------------------------------------------------------------------------


class TestDomainProgress:
    def test_DefaultStatus_IsPending(self):
        p = DomainProgress(name="messaging")
        assert p.status == STATUS_PENDING

    def test_DefaultScores_AreZero(self):
        p = DomainProgress(name="messaging")
        assert p.completeness_score == 0.0
        assert p.new_information_score == 0.0

    def test_ToDict_SortedLists(self):
        p = DomainProgress(name="x", matched_asset_ids=["c", "a", "b"])
        d = p.to_dict()
        assert d["matched_asset_ids"] == ["a", "b", "c"]

    def test_FromDict_RoundTrip(self):
        p = DomainProgress(name="messaging", iteration=3, status=STATUS_STABLE)
        p2 = DomainProgress.from_dict(p.to_dict())
        assert p2.name == "messaging"
        assert p2.iteration == 3
        assert p2.status == STATUS_STABLE

    def test_FromDict_MissingFields_UsesDefaults(self):
        p = DomainProgress.from_dict({"name": "x"})
        assert p.status == STATUS_PENDING
        assert p.iteration == 0
        assert p.matched_asset_ids == []


# ---------------------------------------------------------------------------
# TestDomainState
# ---------------------------------------------------------------------------


class TestDomainState:
    def test_Load_FileNotFound_EmptyState(self, tmp_path):
        state = DomainState(str(tmp_path))
        state.load()
        assert state.all_domains() == []

    def test_EnsureDomains_AddsSeeds(self, tmp_path):
        state = _make_state(tmp_path, ["alpha", "beta"])
        names = [d.name for d in state.all_domains()]
        assert "alpha" in names
        assert "beta" in names

    def test_EnsureDomains_NoDuplicates(self, tmp_path):
        state = _make_state(tmp_path, ["alpha", "alpha"])
        assert len([d for d in state.all_domains() if d.name == "alpha"]) == 1

    def test_Save_CreatesFile(self, tmp_path):
        state = _make_state(tmp_path, ["x"])
        state.save()
        assert (tmp_path / "domain_state.json").exists()

    def test_SaveAndLoad_RoundTrip(self, tmp_path):
        state = _make_state(tmp_path, ["messaging"])
        state.get("messaging").iteration = 5
        state.save()

        state2 = DomainState(str(tmp_path))
        state2.load()
        assert state2.get("messaging").iteration == 5

    def test_Load_ResetsPreviousState(self, tmp_path):
        state = _make_state(tmp_path, ["a"])
        state.save()

        # Load fresh — previous in-memory state from different seeds replaced
        state2 = DomainState(str(tmp_path))
        state2.ensure_domains(["z"])       # z only in memory, not saved
        state2.load()                      # reload clears memory
        assert state2.get("z") is None
        assert state2.get("a") is not None

    def test_Get_UnknownDomain_ReturnsNone(self, tmp_path):
        state = _make_state(tmp_path)
        assert state.get("nonexistent") is None

    def test_DomainSeeds_AllTen(self):
        assert len(DOMAIN_SEEDS) >= 10


# ---------------------------------------------------------------------------
# TestDomainSelector
# ---------------------------------------------------------------------------


class TestDomainSelector:
    def test_PicksInProgress_WhenAvailable(self, tmp_path):
        state = _make_state(tmp_path, ["a", "b"])
        state.get("b").status = STATUS_IN_PROGRESS
        result = pick_next(state)
        assert result.name == "b"

    def test_SetsPending_ToInProgress(self, tmp_path):
        state = _make_state(tmp_path, ["a"])
        domain = pick_next(state)
        assert domain.status == STATUS_IN_PROGRESS

    def test_ReturnsNone_WhenAllStable(self, tmp_path):
        state = _make_state(tmp_path, ["a", "b"])
        state.get("a").status = STATUS_STABLE
        state.get("b").status = STATUS_STABLE
        assert pick_next(state) is None

    def test_PrioritisesInProgress_OverPending(self, tmp_path):
        state = _make_state(tmp_path, ["a", "b"])
        state.get("b").status = STATUS_IN_PROGRESS
        result = pick_next(state)
        assert result.name == "b"

    def test_ReturnsNone_EmptyState(self, tmp_path):
        state = _make_state(tmp_path)
        assert pick_next(state) is None


# ---------------------------------------------------------------------------
# TestDomainAssetMatcher
# ---------------------------------------------------------------------------


class TestDomainAssetMatcher:
    def test_EmptyAssets_ReturnsEmpty(self):
        assert match_assets("messaging", []) == []

    def test_KeywordMatch_IncludesAsset(self):
        assets = [{"id": "code:Sms.cs", "path": "Sms.cs", "content": "send sms message"}]
        result = match_assets("messaging", assets)
        assert "code:Sms.cs" in result

    def test_PathMatch_IncludesAsset(self):
        assets = [{"id": "code:messaging/Handler.cs", "path": "messaging/Handler.cs", "content": ""}]
        result = match_assets("messaging", assets)
        assert "code:messaging/Handler.cs" in result

    def test_NoMatch_ReturnsEmpty(self):
        assets = [{"id": "code:Foo.cs", "path": "Foo.cs", "content": "totally unrelated stuff xyz"}]
        result = match_assets("monitoring", assets)
        assert result == []

    def test_Output_IsSorted(self):
        assets = [
            {"id": "code:z.cs", "path": "", "content": "send sms"},
            {"id": "code:a.cs", "path": "", "content": "message notification"},
        ]
        result = match_assets("messaging", assets)
        assert result == sorted(result)

    def test_Output_NoDuplicates(self):
        # Same asset would match both path and keyword — must appear once
        assets = [{"id": "code:messaging/Send.cs", "path": "messaging/Send.cs", "content": "send message"}]
        result = match_assets("messaging", assets)
        assert len(result) == len(set(result))

    def test_AllSeeds_HaveKeywords(self):
        from core.domain.domain_asset_matcher import _DOMAIN_KEYWORDS
        for seed in DOMAIN_SEEDS:
            assert seed in _DOMAIN_KEYWORDS, f"Missing keywords for {seed}"


# ---------------------------------------------------------------------------
# TestSemanticAnalyzer
# ---------------------------------------------------------------------------


class TestSemanticAnalyzer:
    def test_AllKeys_Present(self):
        result = analyze({"id": "x", "content": ""}, "messaging")
        for key in INSIGHT_KEYS:
            assert key in result

    def test_EmptyAsset_AllListsPresent(self):
        result = analyze({}, "messaging")
        for key in INSIGHT_KEYS:
            assert isinstance(result[key], list)

    def test_ExtractsEntities_FromClassDeclaration(self):
        asset = {"id": "x.cs", "content": "public class MessageService {}"}
        result = analyze(asset, "messaging")
        assert any("MessageService" in e for e in result["entities"])

    def test_ExtractsBehaviors_FromMethod(self):
        asset = {"id": "x.cs", "content": "public void SendMessage(string text) {}"}
        result = analyze(asset, "messaging")
        assert any("SendMessage" in b for b in result["behaviors"])

    def test_PathInPseudocode(self):
        asset = {"id": "code:src/Foo.cs", "path": "src/Foo.cs", "content": ""}
        result = analyze(asset, "messaging")
        assert result["pseudocode"] != []

    def test_ReturnType_IsDict(self):
        result = analyze({"id": "x", "content": "text"}, "monitoring")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# TestDomainMapper
# ---------------------------------------------------------------------------


class TestDomainMapper:
    def test_EmptyInsights_ReturnsOldModel(self):
        old = {"entities": ["A", "B"], "behaviors": [], "flows": [], "rules": [],
               "events": [], "batch": [], "integrations": [], "pseudocode": [], "rebuild": []}
        result = merge(old, [])
        assert result["entities"] == ["A", "B"]

    def test_MergesLists(self):
        old = {"entities": ["A"], "behaviors": [], "flows": [], "rules": [],
               "events": [], "batch": [], "integrations": [], "pseudocode": [], "rebuild": []}
        insight = {k: [] for k in INSIGHT_KEYS}
        insight["entities"] = ["B"]
        result = merge(old, [insight])
        assert "A" in result["entities"]
        assert "B" in result["entities"]

    def test_DeduplicatesItems(self):
        old = {"entities": ["A"], "behaviors": [], "flows": [], "rules": [],
               "events": [], "batch": [], "integrations": [], "pseudocode": [], "rebuild": []}
        insight = {k: [] for k in INSIGHT_KEYS}
        insight["entities"] = ["A", "A", "B"]
        result = merge(old, [insight])
        assert result["entities"].count("A") == 1

    def test_OutputIsSorted(self):
        old = {k: [] for k in INSIGHT_KEYS}
        insight = {k: [] for k in INSIGHT_KEYS}
        insight["entities"] = ["Z", "A", "M"]
        result = merge(old, [insight])
        assert result["entities"] == sorted(result["entities"])

    def test_AllKeysPresent(self):
        result = merge({}, [])
        for key in INSIGHT_KEYS:
            assert key in result


# ---------------------------------------------------------------------------
# TestRefiner
# ---------------------------------------------------------------------------


class TestRefiner:
    def test_AllKeys_InOutput(self):
        result = refine({})
        for key in INSIGHT_KEYS:
            assert key in result

    def test_NullsRemoved(self):
        result = refine({"entities": [None, "", "  ", "A"]})
        assert None not in result["entities"]
        assert "" not in result["entities"]
        assert "A" in result["entities"]

    def test_OutputSorted(self):
        result = refine({"entities": ["Z", "A", "M"]})
        assert result["entities"] == ["A", "M", "Z"]

    def test_Deduplicates(self):
        result = refine({"entities": ["A", "A", "B"]})
        assert result["entities"].count("A") == 1

    def test_EmptyModel_HasAllKeys(self):
        result = refine({})
        assert all(result[k] == [] for k in INSIGHT_KEYS)


# ---------------------------------------------------------------------------
# TestDomainModelStore
# ---------------------------------------------------------------------------


class TestDomainModelStore:
    def test_LoadModel_NoFiles_ReturnsEmpty(self, tmp_path):
        store = DomainModelStore(str(tmp_path))
        model = store.load_model("messaging")
        assert all(model[k] == [] for k in INSIGHT_KEYS)

    def test_SaveAndLoadModel_RoundTrip(self, tmp_path):
        store = DomainModelStore(str(tmp_path))
        model = {k: [] for k in INSIGHT_KEYS}
        model["entities"] = ["UserService", "AccountRepo"]
        store.save_model("messaging", model)
        loaded = store.load_model("messaging")
        assert loaded["entities"] == ["AccountRepo", "UserService"]  # sorted

    def test_SaveModel_WritesMetaFile(self, tmp_path):
        store = DomainModelStore(str(tmp_path))
        store.save_model("messaging", {k: [] for k in INSIGHT_KEYS}, meta={"iteration": 1})
        meta_path = tmp_path / "messaging" / "000_meta.json"
        assert meta_path.exists()
        with open(meta_path) as fh:
            data = json.load(fh)
        assert data["domain"] == "messaging"
        assert data["iteration"] == 1
        assert "saved_utc" in data

    def test_SaveModel_AllSectionFilesCreated(self, tmp_path):
        store = DomainModelStore(str(tmp_path))
        store.save_model("messaging", {k: [] for k in INSIGHT_KEYS})
        domain_dir = tmp_path / "messaging"
        assert (domain_dir / "010_entities.json").exists()
        assert (domain_dir / "040_events.json").exists()
        assert (domain_dir / "090_rebuild.json").exists()

    def test_SaveModel_Atomic_NoTmpFile(self, tmp_path):
        store = DomainModelStore(str(tmp_path))
        store.save_model("messaging", {k: [] for k in INSIGHT_KEYS})
        domain_dir = tmp_path / "messaging"
        tmp_files = list(domain_dir.glob("*.tmp"))
        assert tmp_files == []

    def test_SaveModel_Deduplicates(self, tmp_path):
        store = DomainModelStore(str(tmp_path))
        model = {k: [] for k in INSIGHT_KEYS}
        model["entities"] = ["A", "A", "B"]
        store.save_model("messaging", model)
        loaded = store.load_model("messaging")
        assert loaded["entities"].count("A") == 1


# ---------------------------------------------------------------------------
# TestDomainScoring
# ---------------------------------------------------------------------------


class TestDomainScoring:
    def test_EmptyModel_ScoreZero(self):
        assert compute_completeness({}) == pytest.approx(0.0)

    def test_FullModel_ScoreOne(self):
        assert compute_completeness(_full_model()) == pytest.approx(1.0)

    def test_PartialModel_ScoreBetween(self):
        model = {k: [] for k in INSIGHT_KEYS}
        model["entities"] = ["A", "B", "C", "D", "E"]  # full target
        score = compute_completeness(model)
        assert 0.0 < score < 1.0

    def test_NewInformation_ZeroWhenSame(self):
        model = _full_model()
        assert compute_new_information(model, model) == pytest.approx(0.0)

    def test_NewInformation_NonZeroWhenAdded(self):
        old = {k: [] for k in INSIGHT_KEYS}
        new = {k: [] for k in INSIGHT_KEYS}
        new["entities"] = ["A", "B"]
        assert compute_new_information(old, new) > 0.0

    def test_NewInformation_OldEmptyBaseline(self):
        # When old is empty baseline=0 → denominator=1
        result = compute_new_information({}, {"entities": ["A"]})
        assert result > 0.0

    def test_IsStable_True(self):
        assert is_stable(COMPLETENESS_THRESHOLD, NEW_INFO_THRESHOLD - 0.001)

    def test_IsStable_False_LowCompleteness(self):
        assert not is_stable(COMPLETENESS_THRESHOLD - 0.01, 0.0)

    def test_IsStable_False_HighNewInfo(self):
        assert not is_stable(1.0, NEW_INFO_THRESHOLD + 0.01)

    def test_IsStable_BothMustHold(self):
        # completeness high but new_info too high → not stable
        assert not is_stable(1.0, 0.05)
        # new_info low but completeness too low → not stable
        assert not is_stable(0.5, 0.001)


# ---------------------------------------------------------------------------
# TestDomainEngine
# ---------------------------------------------------------------------------


class TestDomainEngine:
    def _engine(self, tmp_path, assets=None, seeds=None, max_assets=0):
        scanner = _FakeScanner(assets or [])
        return DomainEngine(
            scanner=scanner,
            domains_root=str(tmp_path),
            seed_list=seeds or ["messaging"],
            max_assets_per_domain=max_assets,
            verbose=False,
        )

    def test_RunOnce_AllStable_ReturnsNone(self, tmp_path):
        engine = self._engine(tmp_path)
        # Mark domain stable manually
        state = DomainState(str(tmp_path))
        state.load()
        state.ensure_domains(["messaging"])
        state.get("messaging").status = STATUS_STABLE
        state.save()

        result = engine.run_once()
        assert result is None

    def test_RunOnce_ReturnsDomainName(self, tmp_path):
        engine = self._engine(tmp_path)
        result = engine.run_once()
        assert result is not None
        assert result["domain"] == "messaging"

    def test_RunOnce_ResultContainsRequiredKeys(self, tmp_path):
        engine = self._engine(tmp_path)
        result = engine.run_once()
        for key in ("domain", "status", "iteration", "matched_assets",
                    "processed_this_run", "completeness_score", "new_information_score"):
            assert key in result

    def test_RunOnce_CreatesDomainDirectory(self, tmp_path):
        engine = self._engine(tmp_path)
        engine.run_once()
        assert (tmp_path / "messaging").is_dir()

    def test_RunOnce_PersistsState(self, tmp_path):
        assets = [{"id": "code:Sms.cs", "path": "Sms.cs", "content": "send message"}]
        engine = self._engine(tmp_path, assets=assets)
        engine.run_once()

        state = DomainState(str(tmp_path))
        state.load()
        prog = state.get("messaging")
        assert prog is not None
        assert prog.iteration == 1

    def test_RunOnce_SecondRun_ProcessesZeroAssets(self, tmp_path):
        """Idempotency: second run must find no new assets."""
        assets = [{"id": "code:Sms.cs", "path": "Sms.cs", "content": "send message"}]
        engine = self._engine(tmp_path, assets=assets)
        engine.run_once()
        result2 = engine.run_once()
        # Second run: same domain (in_progress after first run), zero pending
        assert result2 is not None
        assert result2["processed_this_run"] == 0

    def test_RunOnce_MaxAssets_LimitsProcessed(self, tmp_path):
        assets = [
            {"id": f"code:Sms{i}.cs", "path": f"Sms{i}.cs", "content": "send message"}
            for i in range(10)
        ]
        engine = self._engine(tmp_path, assets=assets, max_assets=3)
        result = engine.run_once()
        assert result["processed_this_run"] <= 3

    def test_RunOnce_StableWhenConverged(self, tmp_path):
        """If model is already full (loaded from disk), next run should stabilise."""
        store = DomainModelStore(str(tmp_path))
        store.save_model("messaging", _full_model())

        # Pre-write state showing all assets processed
        state = DomainState(str(tmp_path))
        state.load()
        state.ensure_domains(["messaging"])
        prog = state.get("messaging")
        prog.iteration = 5
        prog.completeness_score = 1.0
        state.save()

        engine = self._engine(tmp_path, assets=[], seeds=["messaging"])
        result = engine.run_once()
        # No new assets → new_info = 0, completeness already high → stable
        assert result is not None
        assert result["status"] == STATUS_STABLE

    def test_RunAll_StopsOnAllStable(self, tmp_path):
        engine = self._engine(tmp_path, assets=[])
        results = engine.run_all()
        # With no assets, domains converge immediately to stable in a few passes
        assert isinstance(results, list)

    def test_RunAll_ReturnsResultsForEachDomain(self, tmp_path):
        engine = self._engine(tmp_path, seeds=["alpha", "beta"], assets=[])
        results = engine.run_all()
        domains = {r["domain"] for r in results}
        # Both domains should appear in results
        assert "alpha" in domains
        assert "beta" in domains
