"""
tests/test_domain_system.py — Tests for domain_builder, semantic_analyzer,
domain_mapper, and refiner.

Naming convention: test_MethodOrBehavior_StateUnderTest_ExpectedBehavior
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from core.domain_builder import DomainBuilder, DomainCluster, _domain_token
from core.ai_processor import StubAIProcessor, DOMAIN_OUTPUT_KEYS
from core.ai.semantic_analyzer import SemanticAnalyzer
from core.ai.domain_mapper import DomainMapper
from core.ai.refiner import Refiner


# ── Helpers ───────────────────────────────────────────────────────────────────

def _asset(asset_id="code:MyService.cs", asset_type="code_file"):
    return {
        "id": asset_id,
        "type": asset_type,
        "content_hash": "abc123",
        "content": "public class MessageService { ... }",
        "group_size": 1,
    }


def _write_slice(tmp_path: Path, filename: str, data: dict):
    (tmp_path / filename).write_text(json.dumps(data), encoding="utf-8")


def _write_prompt(tmp_path: Path, filename: str, content: str = "Extract domain."):
    (tmp_path / filename).write_text(content, encoding="utf-8")


# ── TestDomainToken ───────────────────────────────────────────────────────────

class TestDomainToken:
    def test_StripController_ReturnsDomainWord(self):
        assert _domain_token("BenchmarkController") == "Benchmark"

    def test_StripService_ReturnsDomainWord(self):
        assert _domain_token("MessageService") == "Message"

    def test_StripRepository_ReturnsDomainWord(self):
        assert _domain_token("AddressRepository") == "Address"

    def test_MultiWordCamel_ReturnsFirstWord(self):
        assert _domain_token("SmsGroupService") == "Sms"

    def test_EmptyString_ReturnsFallback(self):
        assert _domain_token("") == "Core"

    def test_NoSuffix_ReturnsFullWord(self):
        assert _domain_token("Benchmark") == "Benchmark"


# ── TestDomainClusterMetrics ──────────────────────────────────────────────────

class TestDomainClusterMetrics:
    def _cluster_with(self, **kwargs):
        c = DomainCluster(name="Test")
        for k, v in kwargs.items():
            setattr(c, k, v)
        return c

    def test_confidence_FullCoverage_ReturnsOne(self):
        c = self._cluster_with(
            apis=[1], batch_jobs=[1], events=[1],
            webhooks=[1], integrations=[1], background_services=[1],
        )
        assert c.confidence == 1.0

    def test_confidence_NoCoverage_ReturnsZero(self):
        c = DomainCluster(name="Empty")
        assert c.confidence == 0.0

    def test_confidence_PartialCoverage_IsBetweenZeroAndOne(self):
        c = self._cluster_with(apis=[1, 2], events=[1])
        assert 0.0 < c.confidence < 1.0

    def test_complexity_score_InRange(self):
        c = self._cluster_with(apis=list(range(30)))
        assert 1 <= c.complexity_score <= 10

    def test_roi_score_InRange(self):
        c = self._cluster_with(apis=[1], events=[1])
        assert 1 <= c.roi_score <= 10


# ── TestDomainBuilder ─────────────────────────────────────────────────────────

class TestDomainBuilder:
    def test_build_GroupsApisByControllerPrefix(self, tmp_path):
        _write_slice(tmp_path, "api_db_map.json", {
            "mappings": [
                {"controller": "BenchmarkController", "controller_method": "Get", "api_url": "/api/Benchmark"},
                {"controller": "BenchmarkController", "controller_method": "Create", "api_url": "/api/Benchmark"},
                {"controller": "MessageController", "controller_method": "Send", "api_url": "/api/Message"},
            ]
        })
        _write_slice(tmp_path, "batch_jobs.json", {"jobs": []})
        _write_slice(tmp_path, "event_map.json", {"events": []})
        _write_slice(tmp_path, "webhook_map.json", {"webhooks": []})
        _write_slice(tmp_path, "integrations.json", {"integrations": []})
        _write_slice(tmp_path, "background_services.json", {"services": []})

        builder = DomainBuilder(str(tmp_path), str(tmp_path / "domains"))
        clusters = builder.build()

        assert "Benchmark" in clusters
        assert len(clusters["Benchmark"].apis) == 2
        assert "Message" in clusters

    def test_build_GroupsBatchJobsByCategory(self, tmp_path):
        _write_slice(tmp_path, "api_db_map.json", {"mappings": []})
        _write_slice(tmp_path, "batch_jobs.json", {
            "jobs": [
                {"job": "import_dk_addresses", "category": "import"},
                {"job": "import_se_addresses", "category": "import"},
                {"job": "gateway_email", "category": "delivery"},
            ]
        })
        _write_slice(tmp_path, "event_map.json", {"events": []})
        _write_slice(tmp_path, "webhook_map.json", {"webhooks": []})
        _write_slice(tmp_path, "integrations.json", {"integrations": []})
        _write_slice(tmp_path, "background_services.json", {"services": []})

        builder = DomainBuilder(str(tmp_path), str(tmp_path / "domains"))
        clusters = builder.build()

        assert "Import" in clusters
        assert len(clusters["Import"].batch_jobs) == 2

    def test_build_MissingSliceFile_DoesNotCrash(self, tmp_path):
        # No slice files — all missing
        builder = DomainBuilder(str(tmp_path), str(tmp_path / "domains"))
        clusters = builder.build()
        assert isinstance(clusters, dict)

    def test_write_CreatesMetaFile(self, tmp_path):
        _write_slice(tmp_path, "api_db_map.json", {
            "mappings": [{"controller": "BenchmarkController", "controller_method": "Get", "api_url": "/api/Benchmark"}]
        })
        _write_slice(tmp_path, "batch_jobs.json", {"jobs": []})
        _write_slice(tmp_path, "event_map.json", {"events": []})
        _write_slice(tmp_path, "webhook_map.json", {"webhooks": []})
        _write_slice(tmp_path, "integrations.json", {"integrations": []})
        _write_slice(tmp_path, "background_services.json", {"services": []})

        builder = DomainBuilder(str(tmp_path), str(tmp_path / "domains"))
        builder.build_and_write()

        meta = tmp_path / "domains" / "Benchmark" / "000_meta.json"
        assert meta.exists()
        data = json.loads(meta.read_text())
        assert data["domain"] == "Benchmark"
        assert "confidence" in data
        assert "coverage" in data

    def test_write_CreatesAllNineFiles(self, tmp_path):
        _write_slice(tmp_path, "api_db_map.json", {
            "mappings": [{"controller": "MessageController", "controller_method": "Send", "api_url": "/api/Message"}]
        })
        _write_slice(tmp_path, "batch_jobs.json", {"jobs": []})
        _write_slice(tmp_path, "event_map.json", {"events": []})
        _write_slice(tmp_path, "webhook_map.json", {"webhooks": []})
        _write_slice(tmp_path, "integrations.json", {"integrations": []})
        _write_slice(tmp_path, "background_services.json", {"services": []})

        builder = DomainBuilder(str(tmp_path), str(tmp_path / "domains"))
        builder.build_and_write()

        domain_dir = tmp_path / "domains" / "Message"
        expected = [
            "000_meta.json", "010_entities.json", "020_behaviors.json",
            "030_flows.json", "040_events.json", "050_batch.json",
            "060_integrations.json", "070_rules.json", "080_pseudocode.json",
            "090_rebuild.json",
        ]
        for fname in expected:
            assert (domain_dir / fname).exists(), f"Missing {fname}"

    def test_write_Atomic_NoTempFiles(self, tmp_path):
        _write_slice(tmp_path, "api_db_map.json", {
            "mappings": [{"controller": "TestController", "controller_method": "X", "api_url": "/api/Test"}]
        })
        for f in ["batch_jobs.json", "event_map.json", "webhook_map.json", "integrations.json", "background_services.json"]:
            _write_slice(tmp_path, f, {"jobs": [], "events": [], "webhooks": [], "integrations": [], "services": []})

        builder = DomainBuilder(str(tmp_path), str(tmp_path / "domains"))
        builder.build_and_write()

        tmp_files = list((tmp_path / "domains").rglob("*.tmp"))
        assert tmp_files == []

    def test_write_EventsPrepopulated(self, tmp_path):
        _write_slice(tmp_path, "api_db_map.json", {"mappings": []})
        _write_slice(tmp_path, "batch_jobs.json", {"jobs": []})
        _write_slice(tmp_path, "event_map.json", {
            "events": [{"event": "BenchmarkFinishedNotification", "publishers": ["X"], "handlers": ["Y"]}]
        })
        _write_slice(tmp_path, "webhook_map.json", {"webhooks": []})
        _write_slice(tmp_path, "integrations.json", {"integrations": []})
        _write_slice(tmp_path, "background_services.json", {"services": []})

        builder = DomainBuilder(str(tmp_path), str(tmp_path / "domains"))
        builder.build_and_write()

        events_file = tmp_path / "domains" / "Benchmark" / "040_events.json"
        data = json.loads(events_file.read_text())
        assert len(data["events"]) == 1
        assert data["events"][0]["event"] == "BenchmarkFinishedNotification"


# ── TestSemanticAnalyzer ──────────────────────────────────────────────────────

class TestSemanticAnalyzer:
    def test_analyze_ReturnsAllDomainKeys(self, tmp_path):
        _write_prompt(tmp_path, "code_semantic.txt")
        analyzer = SemanticAnalyzer(StubAIProcessor(), str(tmp_path))
        result = analyzer.analyze(_asset(), "content here")
        for key in DOMAIN_OUTPUT_KEYS:
            assert key in result

    def test_analyze_WikiSection_UsesWikiPrompt(self, tmp_path):
        _write_prompt(tmp_path, "wiki_semantic.txt", "Wiki extraction prompt")
        _write_prompt(tmp_path, "code_semantic.txt", "Code extraction prompt")

        prompts_seen = []

        class CapturingAI(StubAIProcessor):
            def process(self, asset, stage, prompt):
                prompts_seen.append(prompt)
                return super().process(asset, stage, prompt)

        analyzer = SemanticAnalyzer(CapturingAI(), str(tmp_path))
        a = _asset(asset_type="wiki_section")
        analyzer.analyze(a, "wiki content")
        assert "Wiki extraction prompt" in prompts_seen[0]

    def test_analyze_MissingPromptFile_DoesNotCrash(self, tmp_path):
        # No prompt files in tmp_path
        analyzer = SemanticAnalyzer(StubAIProcessor(), str(tmp_path))
        result = analyzer.analyze(_asset(), "content")
        assert isinstance(result, dict)

    def test_analyze_ContentTruncatedAt8000Chars(self, tmp_path):
        _write_prompt(tmp_path, "code_semantic.txt")
        prompts_seen = []

        class CapturingAI(StubAIProcessor):
            def process(self, asset, stage, prompt):
                prompts_seen.append(prompt)
                return super().process(asset, stage, prompt)

        analyzer = SemanticAnalyzer(CapturingAI(), str(tmp_path))
        analyzer.analyze(_asset(), "x" * 20_000)
        assert len(prompts_seen[0]) < 25_000


# ── TestDomainMapper ──────────────────────────────────────────────────────────

class TestDomainMapper:
    def test_map_ReturnsAllDomainKeys(self, tmp_path):
        _write_prompt(tmp_path, "code_domain.txt")
        mapper = DomainMapper(StubAIProcessor(), str(tmp_path))
        result = mapper.map(_asset(), {"entities": [], "behaviors": []})
        for key in DOMAIN_OUTPUT_KEYS:
            assert key in result

    def test_map_InjectsPreviousResultIntoPrompt(self, tmp_path):
        _write_prompt(tmp_path, "code_domain.txt", "DOMAIN MAPPING PROMPT")
        prompts_seen = []

        class CapturingAI(StubAIProcessor):
            def process(self, asset, stage, prompt):
                prompts_seen.append(prompt)
                return super().process(asset, stage, prompt)

        mapper = DomainMapper(CapturingAI(), str(tmp_path))
        mapper.map(_asset(), {"entities": [{"name": "Customer"}], "behaviors": []})
        assert "Customer" in prompts_seen[0]


# ── TestRefiner ───────────────────────────────────────────────────────────────

class TestRefiner:
    def test_refine_ReturnsAllDomainKeys(self, tmp_path):
        _write_prompt(tmp_path, "refinement.txt")
        refiner = Refiner(StubAIProcessor(), str(tmp_path))
        result = refiner.refine(_asset(), {"entities": [], "behaviors": []})
        for key in DOMAIN_OUTPUT_KEYS:
            assert key in result

    def test_refine_cluster_UsesSyntheticAsset(self, tmp_path):
        _write_prompt(tmp_path, "refinement.txt")
        asset_ids_seen = []

        class CapturingAI(StubAIProcessor):
            def process(self, asset, stage, prompt):
                asset_ids_seen.append(asset["id"])
                return super().process(asset, stage, prompt)

        refiner = Refiner(CapturingAI(), str(tmp_path))
        refiner.refine_cluster("Messaging", {"entities": [], "behaviors": []})
        assert asset_ids_seen[0] == "domain:Messaging"

    def test_refine_cluster_InjectsDomainNameInPrompt(self, tmp_path):
        _write_prompt(tmp_path, "refinement.txt", "REFINEMENT PROMPT")
        prompts_seen = []

        class CapturingAI(StubAIProcessor):
            def process(self, asset, stage, prompt):
                prompts_seen.append(prompt)
                return super().process(asset, stage, prompt)

        refiner = Refiner(CapturingAI(), str(tmp_path))
        refiner.refine_cluster("AddressManagement", {"entities": [], "behaviors": []})
        assert "AddressManagement" in prompts_seen[0]
