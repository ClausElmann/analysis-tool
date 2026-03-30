"""Tests for core.domain.domain_memory.

Covers:
* load/save round-trip and atomic write
* set_asset_insight / get_asset_insight with hash caching
* set_cross_analysis / get_cross_analysis
* add_gap_snapshot / get_latest_gaps / get_gap_history
* get_all_asset_ids
* get_domain_data
"""

import json
import os

import pytest

from core.domain.domain_memory import DomainMemory


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem(tmp_path):
    """Return a fresh DomainMemory pointing at a temp directory."""
    m = DomainMemory(data_root=str(tmp_path))
    m.load()
    return m


def _insight(signal: float = 0.75) -> dict:
    return {
        "entities":     ["Entity1"],
        "behaviors":    ["method()"],
        "flows":        [],
        "rules":        [],
        "events":       [],
        "batch":        [],
        "integrations": [],
        "pseudocode":   [],
        "rebuild":      [],
        "signal_strength": signal,
    }


def _gaps() -> list:
    return [
        {
            "id": "gap:messaging:missing_entity:user",
            "type": "missing_entity",
            "priority": 1.0,
            "suggested_terms": ["user", "account"],
        }
    ]


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------


class TestDomainMemoryPersistence:
    def test_empty_load_no_crash(self, tmp_path):
        m = DomainMemory(data_root=str(tmp_path))
        m.load()  # file doesn't exist
        # Should initialise to empty structure
        assert m.get_all_asset_ids("messaging") == []

    def test_save_creates_file(self, mem, tmp_path):
        mem.set_asset_insight("messaging", "code:msg:1", _insight(), "abc123")
        mem.save()
        path = os.path.join(str(tmp_path), "domain_memory.json")
        assert os.path.isfile(path)

    def test_round_trip(self, tmp_path):
        m1 = DomainMemory(data_root=str(tmp_path))
        m1.load()
        m1.set_asset_insight("messaging", "code:msg:1", _insight(), "hash1")
        m1.save()

        m2 = DomainMemory(data_root=str(tmp_path))
        m2.load()
        assert "code:msg:1" in m2.get_all_asset_ids("messaging")

    def test_save_is_valid_json(self, mem, tmp_path):
        mem.set_asset_insight("messaging", "code:msg:1", _insight(), "h1")
        mem.save()
        path = os.path.join(str(tmp_path), "domain_memory.json")
        with open(path) as f:
            data = json.load(f)
        assert "domains" in data

    def test_corrupt_file_loads_empty(self, tmp_path):
        path = os.path.join(str(tmp_path), "domain_memory.json")
        with open(path, "w") as f:
            f.write("{invalid json")
        m = DomainMemory(data_root=str(tmp_path))
        m.load()  # should not raise
        assert m.get_all_asset_ids("messaging") == []


# ---------------------------------------------------------------------------
# Asset insights
# ---------------------------------------------------------------------------


class TestAssetInsights:
    def test_set_and_get(self, mem):
        mem.set_asset_insight("messaging", "code:msg:1", _insight(), "h1")
        result = mem.get_asset_insight("messaging", "code:msg:1")
        assert result is not None
        assert "semantic" in result
        assert result["content_hash"] == "h1"

    def test_get_nonexistent_returns_none(self, mem):
        assert mem.get_asset_insight("messaging", "code:missing") is None

    def test_cache_hit_skips_overwrite(self, mem):
        mem.set_asset_insight("messaging", "code:msg:1", _insight(0.5), "same_hash")
        mem.set_asset_insight("messaging", "code:msg:1", _insight(0.9), "same_hash")
        result = mem.get_asset_insight("messaging", "code:msg:1")
        # First write should be retained (0.5 signal_strength)
        assert result["semantic"]["signal_strength"] == 0.5

    def test_changed_hash_overwrites(self, mem):
        mem.set_asset_insight("messaging", "code:msg:1", _insight(0.5), "hash_a")
        mem.set_asset_insight("messaging", "code:msg:1", _insight(0.9), "hash_b")
        result = mem.get_asset_insight("messaging", "code:msg:1")
        assert result["semantic"]["signal_strength"] == 0.9
        assert result["content_hash"] == "hash_b"

    def test_confidence_stored(self, mem):
        mem.set_asset_insight("messaging", "code:msg:1", _insight(0.75), "h1")
        result = mem.get_asset_insight("messaging", "code:msg:1")
        assert result["confidence"] == pytest.approx(0.75)

    def test_get_all_asset_ids_sorted(self, mem):
        mem.set_asset_insight("messaging", "code:msg:b", _insight(), "h2")
        mem.set_asset_insight("messaging", "code:msg:a", _insight(), "h1")
        ids = mem.get_all_asset_ids("messaging")
        assert ids == sorted(ids)

    def test_multiple_domains_isolated(self, mem):
        mem.set_asset_insight("messaging", "code:msg:1", _insight(), "h1")
        mem.set_asset_insight("reporting", "code:rep:1", _insight(), "h2")
        assert "code:msg:1" not in mem.get_all_asset_ids("reporting")
        assert "code:rep:1" not in mem.get_all_asset_ids("messaging")


# ---------------------------------------------------------------------------
# Cross-analysis
# ---------------------------------------------------------------------------


class TestCrossAnalysis:
    def test_set_and_get(self, mem):
        analysis = {"linked_pairs": [["A", "B"]], "consistency": 0.8}
        mem.set_cross_analysis("messaging", analysis)
        result = mem.get_cross_analysis("messaging")
        assert result["consistency"] == 0.8

    def test_get_returns_empty_dict_initially(self, mem):
        result = mem.get_cross_analysis("messaging")
        assert isinstance(result, dict)

    def test_overwrite_replaces(self, mem):
        mem.set_cross_analysis("messaging", {"consistency": 0.5})
        mem.set_cross_analysis("messaging", {"consistency": 0.9})
        assert mem.get_cross_analysis("messaging")["consistency"] == 0.9

    def test_returns_copy(self, mem):
        analysis = {"consistency": 0.7}
        mem.set_cross_analysis("messaging", analysis)
        result = mem.get_cross_analysis("messaging")
        result["consistency"] = 0.0  # mutate returned value
        # Original should be unchanged
        assert mem.get_cross_analysis("messaging")["consistency"] == 0.7


# ---------------------------------------------------------------------------
# Gap history
# ---------------------------------------------------------------------------


class TestGapHistory:
    def test_add_and_get_latest(self, mem):
        mem.add_gap_snapshot("messaging", _gaps())
        latest = mem.get_latest_gaps("messaging")
        assert len(latest) == 1
        assert latest[0]["id"] == "gap:messaging:missing_entity:user"

    def test_get_latest_empty_domain(self, mem):
        assert mem.get_latest_gaps("messaging") == []

    def test_history_is_append_only(self, mem):
        mem.add_gap_snapshot("messaging", _gaps())
        mem.add_gap_snapshot("messaging", [])
        history = mem.get_gap_history("messaging")
        assert len(history) == 2
        assert history[0]["iteration"] == 1
        assert history[1]["iteration"] == 2

    def test_get_latest_returns_last_snapshot(self, mem):
        mem.add_gap_snapshot("messaging", _gaps())
        mem.add_gap_snapshot("messaging", [])  # second snapshot is empty
        assert mem.get_latest_gaps("messaging") == []

    def test_gap_history_persisted(self, tmp_path):
        m1 = DomainMemory(data_root=str(tmp_path))
        m1.load()
        m1.add_gap_snapshot("messaging", _gaps())
        m1.save()

        m2 = DomainMemory(data_root=str(tmp_path))
        m2.load()
        history = m2.get_gap_history("messaging")
        assert len(history) == 1


# ---------------------------------------------------------------------------
# get_domain_data
# ---------------------------------------------------------------------------


class TestGetDomainData:
    def test_returns_dict_for_new_domain(self, mem):
        data = mem.get_domain_data("messaging")
        assert isinstance(data, dict)

    def test_contains_expected_keys(self, mem):
        data = mem.get_domain_data("messaging")
        assert "assets" in data
        assert "cross_analysis" in data
        assert "gap_history" in data
