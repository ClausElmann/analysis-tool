"""
tests/test_domain_pipeline.py — Tests for stage_state, ai_processor,
prompt_builder, and domain_pipeline.

Naming convention: test_MethodOrBehavior_StateUnderTest_ExpectedBehavior
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from core.stage_state import StageState, STAGES
from core.ai_processor import AIProcessor, StubAIProcessor, DOMAIN_OUTPUT_KEYS
from core.prompt_builder import PromptBuilder
from core.domain_pipeline import DomainPipeline


# ── Helpers ───────────────────────────────────────────────────────────────────


def _asset(
    asset_id="wiki:doc.md:0",
    asset_type="wiki_section",
    content_hash="abc123",
    content="hello world",
):
    return {
        "id": asset_id,
        "type": asset_type,
        "content_hash": content_hash,
        "content": content,
        "group_size": 1,
    }


def _scanner(assets):
    s = MagicMock()
    s.scan_all_assets.return_value = assets
    return s


def _pipeline(tmp_path, assets, ai_proc=None, verbose=False):
    scanner = _scanner(assets)
    state = StageState(str(tmp_path / "state"))
    processor = ai_proc or StubAIProcessor()
    pipeline = DomainPipeline(
        scanner=scanner,
        stage_state=state,
        ai_processor=processor,
        output_root=str(tmp_path / "output"),
        verbose=verbose,
    )
    return pipeline, state


# ── TestStageState ────────────────────────────────────────────────────────────


class TestStageState:
    def test_pending_stages_NewAsset_ReturnsAllStages(self, tmp_path):
        state = StageState(str(tmp_path))
        assert state.pending_stages(_asset()) == list(STAGES)

    def test_pending_stages_AllDone_ReturnsEmptyList(self, tmp_path):
        state = StageState(str(tmp_path))
        a = _asset()
        for stage in STAGES:
            state.mark_stage_done(a["id"], a["content_hash"], stage)
        assert state.pending_stages(a) == []

    def test_pending_stages_PartialDone_ReturnsMissingStages(self, tmp_path):
        state = StageState(str(tmp_path))
        a = _asset()
        state.mark_stage_done(a["id"], a["content_hash"], "structured_extraction")
        state.mark_stage_done(a["id"], a["content_hash"], "semantic_analysis")
        assert state.pending_stages(a) == ["domain_mapping", "refinement"]

    def test_is_stale_HashChanged_ReturnsTrue(self, tmp_path):
        state = StageState(str(tmp_path))
        a = _asset(content_hash="v1")
        for stage in STAGES:
            state.mark_stage_done(a["id"], a["content_hash"], stage)
        updated = _asset(content_hash="v2")
        assert state.is_stale(updated) is True

    def test_pending_stages_HashChanged_ReturnsAllStages(self, tmp_path):
        state = StageState(str(tmp_path))
        a = _asset(content_hash="v1")
        for stage in STAGES:
            state.mark_stage_done(a["id"], a["content_hash"], stage)
        updated = _asset(content_hash="v2")
        assert state.pending_stages(updated) == list(STAGES)

    def test_mark_stage_failed_StageStillPending(self, tmp_path):
        state = StageState(str(tmp_path))
        a = _asset()
        state.mark_stage_failed(a["id"], a["content_hash"], "structured_extraction", "boom")
        assert "structured_extraction" in state.pending_stages(a)

    def test_save_and_load_PersistsCompletedStage(self, tmp_path):
        state = StageState(str(tmp_path))
        a = _asset()
        state.mark_stage_done(a["id"], a["content_hash"], "structured_extraction")
        state.save()
        reloaded = StageState(str(tmp_path))
        pending = reloaded.pending_stages(a)
        assert "structured_extraction" not in pending
        assert "semantic_analysis" in pending

    def test_save_AtomicWrite_LeavesNoTempFile(self, tmp_path):
        state = StageState(str(tmp_path))
        state.save()
        assert not (tmp_path / "stage_state.json.tmp").exists()

    def test_reset_asset_ClearsAllStages(self, tmp_path):
        state = StageState(str(tmp_path))
        a = _asset()
        for stage in STAGES:
            state.mark_stage_done(a["id"], a["content_hash"], stage)
        state.reset_asset(a["id"])
        assert state.pending_stages(a) == list(STAGES)

    def test_reset_all_ClearsEveryAsset(self, tmp_path):
        state = StageState(str(tmp_path))
        for i in range(3):
            a = _asset(asset_id=f"wiki:doc.md:{i}")
            state.mark_stage_done(a["id"], a["content_hash"], "structured_extraction")
        state.reset_all()
        assert state.pending_stages(_asset(asset_id="wiki:doc.md:0")) == list(STAGES)

    def test_summary_CountsCorrectly(self, tmp_path):
        state = StageState(str(tmp_path))
        a = _asset()
        state.mark_stage_done(a["id"], a["content_hash"], "structured_extraction")
        state.mark_stage_failed(a["id"], a["content_hash"], "semantic_analysis", "err")
        summary = state.summary()
        assert summary["structured_extraction"]["done"] == 1
        assert summary["semantic_analysis"]["failed"] == 1
        assert summary["domain_mapping"]["pending"] == 1  # asset is tracked; unstarted stages count as pending


# ── TestStubAIProcessor ───────────────────────────────────────────────────────


class TestStubAIProcessor:
    # TestStubAIProcessor er fjernet — kun lokal LLM (Copilot chat) er tilladt


# ── TestPromptBuilder ─────────────────────────────────────────────────────────


class TestPromptBuilder:
    def test_build_ContainsAssetId(self):
        pb = PromptBuilder()
        a = _asset(asset_id="wiki:Architecture.md:2")
        assert "wiki:Architecture.md:2" in pb.build(a, "semantic_analysis")

    def test_build_ContainsStageInstruction(self):
        pb = PromptBuilder()
        prompt = pb.build(_asset(), "domain_mapping")
        assert "domain" in prompt.lower()

    def test_build_WithPreviousResult_IncludesPreviousSection(self):
        pb = PromptBuilder()
        previous = {"entities": [{"name": "Customer"}], "behaviors": []}
        prompt = pb.build(_asset(), "refinement", previous_result=previous)
        assert "PREVIOUS RESULT" in prompt
        assert "Customer" in prompt

    def test_build_LongContent_IsTruncated(self):
        pb = PromptBuilder()
        a = _asset(content="x" * 20_000)
        prompt = pb.build(a, "semantic_analysis")
        # 8000-char cap + surrounding prompt text — well below 25000
        assert len(prompt) < 25_000

    def test_build_NoPreviousResult_NoPreviousSection(self):
        pb = PromptBuilder()
        prompt = pb.build(_asset(), "structured_extraction")
        assert "PREVIOUS RESULT" not in prompt


# ── TestDomainPipeline ────────────────────────────────────────────────────────


class TestDomainPipeline:
    def test_run_SingleAsset_ProcessesAllStages(self, tmp_path):
        pipeline, _ = _pipeline(tmp_path, [_asset()])
        report = pipeline.run()
        assert report["processed"] == len(STAGES)
        assert report["errors"] == 0

    def test_run_SecondRun_SkipsAlreadyCompletedAsset(self, tmp_path):
        pipeline, _ = _pipeline(tmp_path, [_asset()])
        pipeline.run()
        report2 = pipeline.run()
        assert report2["processed"] == 0
        assert report2["skipped"] == 1

    def test_run_HashChanged_ReprocessesAllStages(self, tmp_path):
        pipeline, _ = _pipeline(tmp_path, [_asset(content_hash="v1")])
        pipeline.run()
        pipeline._scanner = _scanner([_asset(content_hash="v2")])
        report2 = pipeline.run()
        assert report2["processed"] == len(STAGES)

    def test_run_PersistsStateAfterEachStage(self, tmp_path):
        pipeline, state = _pipeline(tmp_path, [_asset()])
        save_calls = []
        original_save = state.save

        def tracking_save():
            save_calls.append(True)
            original_save()

        state.save = tracking_save
        pipeline.run()
        assert len(save_calls) == len(STAGES)

    def test_run_AIError_MarksFailedAndContinues(self, tmp_path):
        class FailingAI(AIProcessor):
            def process(self, asset, stage, prompt):
                raise RuntimeError("AI offline")

        pipeline, _ = _pipeline(tmp_path, [_asset()], ai_proc=FailingAI())
        report = pipeline.run()
        assert report["errors"] == len(STAGES)
        assert report["processed"] == 0

    def test_run_MaxAssets_LimitsProcessing(self, tmp_path):
        assets = [_asset(asset_id=f"wiki:doc.md:{i}") for i in range(5)]
        pipeline, _ = _pipeline(tmp_path, assets)
        report = pipeline.run(max_assets=2)
        assert report["total"] == 5
        assert report["processed"] == 2 * len(STAGES)

    def test_run_StagesFilter_OnlyRunsRequestedStages(self, tmp_path):
        assets = [_asset()]
        pipeline, state = _pipeline(tmp_path, assets)
        report = pipeline.run(stages=["structured_extraction", "semantic_analysis"])
        assert report["processed"] == 2
        pending = state.pending_stages(assets[0])
        assert "domain_mapping" in pending
        assert "refinement" in pending

    def test_run_SavesOutputFileWithCorrectContent(self, tmp_path):
        assets = [_asset(asset_id="wiki:doc.md:0")]
        pipeline, _ = _pipeline(tmp_path, assets)
        pipeline.run(stages=["structured_extraction"])
        output_file = tmp_path / "output" / "structured_extraction" / "wiki_doc.md_0.json"
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["asset_id"] == "wiki:doc.md:0"
        assert data["stage"] == "structured_extraction"

    def test_dry_run_ReturnsBreakdownByType(self, tmp_path):
        assets = [
            _asset(asset_id="wiki:a:0", asset_type="wiki_section"),
            _asset(asset_id="wiki:b:0", asset_type="wiki_section"),
            _asset(asset_id="work_items:batch:0", asset_type="work_items_batch"),
        ]
        pipeline, _ = _pipeline(tmp_path, assets)
        report = pipeline.dry_run()
        assert report["assets"] == 3
        assert report["breakdown"]["wiki_section"]["assets"] == 2
        assert report["breakdown"]["work_items_batch"]["assets"] == 1

    def test_dry_run_DoesNotWriteStateFile(self, tmp_path):
        pipeline, _ = _pipeline(tmp_path, [_asset()])
        pipeline.dry_run()
        assert not (tmp_path / "state" / "stage_state.json").exists()

    def test_run_StageRestart_ResumesFromCorrectStage(self, tmp_path):
        assets = [_asset()]
        pipeline, state = _pipeline(tmp_path, assets)
        pipeline.run(stages=["structured_extraction"])
        pipeline.run(stages=["semantic_analysis"])
        pending = state.pending_stages(assets[0])
        assert "structured_extraction" not in pending
        assert "semantic_analysis" not in pending
        assert "domain_mapping" in pending

    def test_run_RefinementStage_LoadsPreviousDomainMappingResult(self, tmp_path):
        """Verify refinement receives domain_mapping output as context."""
        prompts_seen = []

        class CapturingAI(AIProcessor):
            def process(self, asset, stage, prompt):
                prompts_seen.append((stage, prompt))
                return StubAIProcessor().process(asset, stage, prompt)

        assets = [_asset()]
        pipeline, _ = _pipeline(tmp_path, assets, ai_proc=CapturingAI())
        pipeline.run()
        refinement_prompt = next(p for s, p in prompts_seen if s == "refinement")
        # domain_mapping result (_stub: true) should appear in refinement prompt
        assert "PREVIOUS RESULT" in refinement_prompt
