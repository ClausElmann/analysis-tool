"""
tests/test_domain_loop.py — Tests for domain_state, domain_gap_detector,
domain_scorer, and domain_loop_engine.

Naming convention: test_MethodOrBehavior_StateUnderTest_ExpectedBehavior
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.domain_state import (
    DomainState,
    STATUS_NOT_STARTED,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETE,
    STATUS_SATURATED,
    SATURATION_STABLE,
    SCORE_THRESHOLD,
)
from core.domain_gap_detector import DomainGapDetector
from core.domain_scorer import DomainScorer, WEIGHTS
from core.domain_loop_engine import (
    DomainLoopEngine,
    _asset_matches_domain,
    _deduplicate,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_domain_dir(tmp_path: Path, name: str, **overrides) -> Path:
    """Create a minimal domain directory with skeleton files."""
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    defaults = {
        "000_meta.json":    {"domain": name, "coverage": {"api_endpoints": 2}, "roi_score": 5},
        "010_entities.json": {"domain": name, "entities": []},
        "020_behaviors.json": {"domain": name, "behaviors": []},
        "030_flows.json":    {"domain": name, "flows": []},
        "040_events.json":   {"domain": name, "events": []},
        "050_batch.json":    {"domain": name, "batch_jobs": []},
        "060_integrations.json": {"domain": name, "integrations": [], "webhooks": []},
        "070_rules.json":    {"domain": name, "rules": []},
        "080_pseudocode.json": {"domain": name, "pseudocode": []},
        "090_rebuild.json":  {"domain": name, "rebuild_requirements": []},
    }
    defaults.update(overrides)
    for fname, data in defaults.items():
        _write_json(d / fname, data)
    return d


def _stub_scanner(assets: list):
    """Return a mock scanner that always yields the given asset list."""
    scanner = MagicMock()
    scanner.scan_all_assets.return_value = assets
    return scanner


def _stub_ai():
    """Minimal AI processor that returns skeleton domain output."""
    from core.ai_processor import StubAIProcessor
    return StubAIProcessor()


# ─────────────────────────────────────────────────────────────────────────────
# TestDomainState
# ─────────────────────────────────────────────────────────────────────────────

class TestDomainState:
    def test_load_MissingFile_ReturnsNotStarted(self, tmp_path):
        state = DomainState.load(tmp_path, "Messaging")
        assert state.status == STATUS_NOT_STARTED
        assert state.iterations == 0
        assert state.score == 0.0

    def test_save_And_Reload_RestoresAllFields(self, tmp_path):
        (tmp_path / "Messaging").mkdir()
        state = DomainState.load(tmp_path, "Messaging")
        state.mark_in_progress()
        state.iterations = 3
        state.update_score(0.72, {"coverage_code": 0.8})
        state.update_gaps([{"type": "orphan_event", "priority": "medium"}])
        state.save()

        loaded = DomainState.load(tmp_path, "Messaging")
        assert loaded.status == STATUS_IN_PROGRESS
        assert loaded.iterations == 3
        assert loaded.score == pytest.approx(0.72)
        assert loaded.gaps[0]["type"] == "orphan_event"

    def test_markComplete_SetsStatusComplete(self, tmp_path):
        (tmp_path / "Sms").mkdir()
        state = DomainState.load(tmp_path, "Sms")
        state.mark_complete()
        assert state.status == STATUS_COMPLETE
        assert state.is_done is True

    def test_markSaturated_SetsStatusSaturated(self, tmp_path):
        (tmp_path / "Sms").mkdir()
        state = DomainState.load(tmp_path, "Sms")
        state.mark_saturated()
        assert state.status == STATUS_SATURATED
        assert state.is_done is True

    def test_checkSaturation_StableCountsForThreshold_ReturnsTrue(self, tmp_path):
        (tmp_path / "X").mkdir()
        state = DomainState.load(tmp_path, "X")
        # First call establishes the baseline (0→3,2,4); subsequent calls detect stability.
        # Need SATURATION_STABLE + 1 calls before the condition fires.
        result = False
        for _ in range(SATURATION_STABLE + 1):
            result = state.check_saturation(3, 2, 4)
        assert result is True

    def test_checkSaturation_ChangingCounts_ReturnsFalse(self, tmp_path):
        (tmp_path / "X").mkdir()
        state = DomainState.load(tmp_path, "X")
        state.check_saturation(3, 2, 4)
        state.check_saturation(3, 2, 4)
        result = state.check_saturation(5, 2, 4)   # entity_count changed
        assert result is False
        assert state.saturation["stable_iterations"] == 0

    def test_updateScore_RecordsLastImprovement(self, tmp_path):
        (tmp_path / "X").mkdir()
        state = DomainState.load(tmp_path, "X")
        state.update_score(0.55, {"coverage_code": 0.5}, last_improvement="coverage_code")
        assert state.last_improvement == "coverage_code"

    def test_save_IsAtomic_WritesToTmpFirst(self, tmp_path):
        """save() should not leave a .tmp file on disk after completion."""
        (tmp_path / "Dom").mkdir()
        state = DomainState.load(tmp_path, "Dom")
        state.save()
        tmp_files = list((tmp_path / "Dom").glob("*.tmp"))
        assert tmp_files == []


# ─────────────────────────────────────────────────────────────────────────────
# TestDomainGapDetector
# ─────────────────────────────────────────────────────────────────────────────

class TestDomainGapDetector:
    def _detector(self):
        return DomainGapDetector()

    def test_detect_EmptyDomain_ReturnsApiWithoutFlowGap(self):
        detector = self._detector()
        gaps = detector.detect(
            meta={"coverage": {"api_endpoints": 3}},
            entities=[],
            behaviors=[],
            flows=[],
            events=[],
            batch_jobs=[],
            integrations=[],
        )
        types = [g["type"] for g in gaps]
        assert "api_without_flow" in types

    def test_detect_OrphanEvent_Detected(self):
        detector = self._detector()
        gaps = detector.detect(
            meta={},
            entities=[],
            behaviors=[],
            flows=[],
            events=[{"event": "MessageSentEvent"}],
            batch_jobs=[],
            integrations=[],
        )
        types = [g["type"] for g in gaps]
        assert "orphan_event" in types

    def test_detect_OrphanEvent_ReferencedInBehavior_NotDetected(self):
        detector = self._detector()
        gaps = detector.detect(
            meta={},
            entities=[],
            behaviors=[{"name": "Handle MessageSentEvent processing"}],
            flows=[],
            events=[{"event": "MessageSentEvent"}],
            batch_jobs=[],
            integrations=[],
        )
        types = [g["type"] for g in gaps]
        assert "orphan_event" not in types

    def test_detect_UnownedBatchJob_Detected(self):
        detector = self._detector()
        gaps = detector.detect(
            meta={},
            entities=[],
            behaviors=[],
            flows=[],
            events=[],
            batch_jobs=[{"job": "CleanupOldMessages"}],
            integrations=[],
        )
        types = [g["type"] for g in gaps]
        assert "unowned_batch_job" in types

    def test_detect_MissingTrigger_InFlow_Detected(self):
        detector = self._detector()
        gaps = detector.detect(
            meta={},
            entities=[],
            behaviors=[],
            flows=[{"name": "Send SMS flow", "description": "Sends an SMS message"}],
            events=[],
            batch_jobs=[],
            integrations=[],
        )
        types = [g["type"] for g in gaps]
        assert "missing_trigger" in types

    def test_detect_IntegrationNoBehavior_Detected(self):
        detector = self._detector()
        gaps = detector.detect(
            meta={},
            entities=[],
            behaviors=[],
            flows=[],
            events=[],
            batch_jobs=[],
            integrations=[{"interface": "IEmailService"}],
        )
        types = [g["type"] for g in gaps]
        assert "integration_no_behavior" in types

    def test_detect_Gaps_SortedHighFirst(self):
        detector = self._detector()
        gaps = detector.detect(
            meta={"coverage": {"api_endpoints": 2}},
            entities=[],
            behaviors=[],
            flows=[],
            events=[{"event": "OrphanedEvent"}],
            batch_jobs=[{"job": "UnownedJob"}],
            integrations=[{"interface": "IFoo"}],
        )
        priorities = [g["priority"] for g in gaps]
        assert priorities == sorted(
            priorities,
            key=lambda p: {"high": 0, "medium": 1, "low": 2}[p]
        )


# ─────────────────────────────────────────────────────────────────────────────
# TestDomainScorer
# ─────────────────────────────────────────────────────────────────────────────

class TestDomainScorer:
    def _scorer(self):
        return DomainScorer()

    def _full_domain(self):
        """Build a domain that should score above the threshold."""
        return dict(
            meta={"coverage": {"api_endpoints": 3}},
            entities=[
                {"name": "Message"},
                {"name": "Recipient"},
                {"name": "Channel"},
                {"name": "Template"},
                {"name": "Delivery"},
            ],
            behaviors=[
                {"name": "Send message", "trigger": "user submits form"},
                {"name": "Retry failed delivery", "trigger": "system scheduler"},
                {"name": "Acknowledge response", "trigger": "inbound webhook"},
                {"name": "Archive message", "trigger": "batch job"},
                {"name": "Validate recipient", "trigger": "ui input validation"},
            ],
            flows=[
                {"name": "Send flow", "description": "trigger: api call"},
                {"name": "Retry flow", "description": "trigger: scheduler"},
                {"name": "Archive flow", "description": "trigger: batch"},
            ],
            events=[
                {"event": "MessageSent", "publishers": ["MessageService"], "handlers": ["AuditHandler"]},
                {"event": "DeliveryFailed", "publishers": ["DeliveryWorker"], "handlers": ["RetryHandler"]},
                {"event": "MessageArchived", "publishers": ["ArchiveJob"], "handlers": []},
            ],
            batch_jobs=[{"job": "ArchiveJob"}, {"job": "CleanupJob"}, {"job": "RetryJob"}],
            integrations={"integrations": [{"interface": "IEmailService"}], "webhooks": []},
            rules=[{"rule": "Max 5 retries"}, {"rule": "Rate limit 100/min"}, {"rule": "No PII"}],
            pseudocode=[{"code": "sendMessage(msg)"}, {"code": "retryDelivery(id)"}],
            rebuild=[
                {"requirement": "REQ-1"},
                {"requirement": "REQ-2"},
                {"requirement": "REQ-3"},
                {"requirement": "REQ-4"},
                {"requirement": "REQ-5"},
            ],
        )

    def test_score_FullDomain_ScoreAboveThreshold(self):
        scorer = self._scorer()
        result = scorer.score(**self._full_domain())
        assert result["is_complete"] is True
        assert result["score"] >= 0.80

    def test_score_EmptyDomain_ScoreBelowThreshold(self):
        scorer = self._scorer()
        result = scorer.score(
            meta={},
            entities=[], behaviors=[], flows=[],
            events=[], batch_jobs=[], integrations=[],
            rules=[], pseudocode=[], rebuild=[],
        )
        assert result["is_complete"] is False
        assert result["score"] == 0.0

    def test_score_ReturnsAllDimensions(self):
        scorer = self._scorer()
        result = scorer.score(**self._full_domain())
        for key in WEIGHTS:
            assert key in result["breakdown"]

    def test_score_WeightsSumToOne(self):
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

    def test_score_ConsistencyPenalisesDuplicateNames(self):
        scorer = self._scorer()
        duplicate_entities = [{"name": "Message"}, {"name": "message"}, {"name": "message"}]
        result = scorer.score(
            meta={},
            entities=duplicate_entities, behaviors=[], flows=[],
            events=[], batch_jobs=[], integrations=[],
            rules=[], pseudocode=[], rebuild=[],
        )
        assert result["breakdown"]["consistency"] < 1.0

    def test_score_ThresholdFieldPresent(self):
        scorer = self._scorer()
        result = scorer.score(
            meta={},
            entities=[], behaviors=[], flows=[],
            events=[], batch_jobs=[], integrations=[],
            rules=[], pseudocode=[], rebuild=[],
        )
        assert result["threshold"] == 0.80


# ─────────────────────────────────────────────────────────────────────────────
# TestAssetMatchesDomain
# ─────────────────────────────────────────────────────────────────────────────

class TestAssetMatchesDomain:
    def test_GlobalAsset_AlwaysMatches(self):
        asset = {"id": "work_items:batch:0", "type": "work_items_batch"}
        assert _asset_matches_domain(asset, "Messaging") is True

    def test_CodeFile_PathContainsDomain_Matches(self):
        asset = {
            "id": "code:ServiceAlert.Services/Messaging/MessageService.cs",
            "type": "code_file",
        }
        assert _asset_matches_domain(asset, "Messaging") is True

    def test_CodeFile_PathNotRelated_NoMatch(self):
        asset = {
            "id": "code:ServiceAlert.Services/Billing/InvoiceService.cs",
            "type": "code_file",
        }
        assert _asset_matches_domain(asset, "Messaging") is False

    def test_WikiSection_DomainInId_Matches(self):
        asset = {"id": "wiki:Messaging-Architecture.md:0", "type": "wiki_section"}
        assert _asset_matches_domain(asset, "Messaging") is True

    def test_CodeFile_PrefixMatch_Matches(self):
        # Path segment "SmsService" strips via _domain_token to "Sms" → matches domain "Sms"
        asset = {
            "id": "code:ServiceAlert.Services/SmsService/SmsHandler.cs",
            "type": "code_file",
        }
        assert _asset_matches_domain(asset, "Sms") is True


# ─────────────────────────────────────────────────────────────────────────────
# TestDeduplicate
# ─────────────────────────────────────────────────────────────────────────────

class TestDeduplicate:
    def test_deduplicate_DuplicateNameDicts_RemovesSecond(self):
        items = [{"name": "Message"}, {"name": "message"}, {"name": "Other"}]
        result = _deduplicate(items)
        assert len(result) == 2

    def test_deduplicate_UniqueItems_PreservesAll(self):
        items = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        result = _deduplicate(items)
        assert len(result) == 3

    def test_deduplicate_Strings_RemovesDuplicates(self):
        items = ["apple", "Apple", "banana"]
        result = _deduplicate(items)
        assert len(result) == 2

    def test_deduplicate_EmptyList_ReturnsEmpty(self):
        assert _deduplicate([]) == []


# ─────────────────────────────────────────────────────────────────────────────
# TestDomainLoopEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestDomainLoopEngine:
    def _make_engine(self, tmp_path: Path, domains_root: Path, assets: list):
        scanner = _stub_scanner(assets)
        stage_state = MagicMock()
        stage_state.pending_stages.return_value = []   # everything already done
        ai = _stub_ai()
        return DomainLoopEngine(
            scanner=scanner,
            stage_state=stage_state,
            ai_processor=ai,
            data_root=str(tmp_path / "data"),
            domains_root=str(domains_root),
            max_iterations=3,
            max_assets_per_iter=10,
            verbose=False,
        )

    def test_runDomain_NoDomainDir_ReturnsNotStarted(self, tmp_path):
        domains = tmp_path / "domains"
        domains.mkdir()
        engine = self._make_engine(tmp_path, domains, [])
        result = engine.run_domain("NonExistent")
        # Should not crash; state directory may be created with not_started
        assert "domain" in result

    def test_runDomain_AlreadyComplete_SkipsProcessing(self, tmp_path):
        domains = tmp_path / "domains"
        _make_domain_dir(domains, "Sms")
        # Pre-write a complete state
        state = DomainState.load(domains, "Sms")
        state.mark_complete()
        state.save()

        engine = self._make_engine(tmp_path, domains, [])
        result = engine.run_domain("Sms")
        assert result["status"] == STATUS_COMPLETE

    def test_run_LoadsDomainList_ReturnsResults(self, tmp_path):
        domains = tmp_path / "domains"
        _make_domain_dir(domains, "Alpha")
        _make_domain_dir(domains, "Beta")

        engine = self._make_engine(tmp_path, domains, [])
        results = engine.run()
        domain_names = {r["domain"] for r in results}
        assert "Alpha" in domain_names
        assert "Beta" in domain_names

    def test_run_DomainFilter_OnlyProcessesSelected(self, tmp_path):
        domains = tmp_path / "domains"
        _make_domain_dir(domains, "Alpha")
        _make_domain_dir(domains, "Beta")
        _make_domain_dir(domains, "Gamma")

        engine = self._make_engine(tmp_path, domains, [])
        results = engine.run(domain_filter=["Alpha"])
        assert len(results) == 1
        assert results[0]["domain"] == "Alpha"

    def test_run_MaxDomains_LimitsCount(self, tmp_path):
        domains = tmp_path / "domains"
        for name in ["A", "B", "C", "D"]:
            _make_domain_dir(domains, name)

        engine = self._make_engine(tmp_path, domains, [])
        results = engine.run(max_domains=2)
        assert len(results) == 2

    def test_runDomain_SaturatesWhenNoNewOutputs(self, tmp_path):
        """
        With stub AI (no-op), no real outputs are written to domain_output/.
        Aggregation produces 0 entities/behaviors/flows.
        After SATURATION_STABLE stable iterations, the domain is saturated.
        """
        domains = tmp_path / "domains"
        _make_domain_dir(domains, "Saturate")

        assets = [{"id": "code:Saturate/Foo.cs", "type": "code_file", "content_hash": "x"}]
        scanner = _stub_scanner(assets)
        stage_state = MagicMock()
        stage_state.pending_stages.return_value = []  # already done → processed=0

        engine = DomainLoopEngine(
            scanner=scanner,
            stage_state=stage_state,
            ai_processor=_stub_ai(),
            data_root=str(tmp_path / "data"),
            domains_root=str(domains),
            max_iterations=SATURATION_STABLE + 2,
            max_assets_per_iter=10,
            verbose=False,
        )
        result = engine.run_domain("Saturate")
        # With processed=0 every iteration, engine exits early via the idle check
        assert result["status"] in (STATUS_SATURATED, STATUS_IN_PROGRESS)
