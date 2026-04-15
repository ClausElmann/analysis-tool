"""tests/test_visual_intelligence_reporter.py — Wave 10 prep: Layer 2.5 stats generator.

Tests for core/visual_intelligence_reporter.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.visual_intelligence_reporter import (
    generate_visual_intelligence,
    _sanitize_entry,
    _load_registry,
    _build_component_stability,
    _build_failure_patterns,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_registry(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _make_entry(
    screen_key: str = "Home",
    result: str = "PASS",
    wave: str = "Wave9",
    device: str = "desktop",
    ts: str = "2026-04-15T10:00:00+00:00",
) -> dict:
    return {
        "screenKey": screen_key,
        "device": device,
        "imageSha256": "aaa",
        "normalizedImageSha256": "bbb",
        "validationContextSha256": "ccc",
        "renderInputSha256": "ddd",
        "validationFingerprintSha256": "eee",
        "policyVersion": "v1",
        "result": result,
        "wave": wave,
        "validatedAtUtc": ts,
        "artifacts": {
            "screenshotPath": "C:\\secret\\path\\home.png",
            "failuresPath": None,
        },
    }


# ---------------------------------------------------------------------------
# _sanitize_entry
# ---------------------------------------------------------------------------

class TestSanitizeEntry:
    def test_artifacts_stripped(self):
        entry = _make_entry()
        safe = _sanitize_entry(entry)
        assert "artifacts" not in safe

    def test_hashes_kept(self):
        entry = _make_entry()
        safe = _sanitize_entry(entry)
        assert safe["imageSha256"] == "aaa"
        assert safe["normalizedImageSha256"] == "bbb"

    def test_screen_key_kept(self):
        entry = _make_entry(screen_key="Dashboard")
        safe = _sanitize_entry(entry)
        assert safe["screenKey"] == "Dashboard"

    def test_original_not_mutated(self):
        entry = _make_entry()
        _sanitize_entry(entry)
        assert "artifacts" in entry


# ---------------------------------------------------------------------------
# _load_registry
# ---------------------------------------------------------------------------

class TestLoadRegistry:
    def test_missing_file_returns_empty(self, tmp_path):
        result = _load_registry(tmp_path / "nonexistent.jsonl")
        assert result == []

    def test_loads_valid_entries(self, tmp_path):
        reg = tmp_path / "reg.jsonl"
        _write_registry(reg, [_make_entry("A"), _make_entry("B")])
        entries = _load_registry(reg)
        assert len(entries) == 2

    def test_skips_corrupt_lines(self, tmp_path):
        reg = tmp_path / "reg.jsonl"
        with open(reg, "w") as f:
            f.write('{"screenKey":"OK","result":"PASS"}\n')
            f.write("NOT_JSON\n")
            f.write('{"screenKey":"OK2","result":"FAIL"}\n')
        entries = _load_registry(reg)
        assert len(entries) == 2

    def test_empty_file_returns_empty(self, tmp_path):
        reg = tmp_path / "reg.jsonl"
        reg.write_text("")
        assert _load_registry(reg) == []

    def test_blank_lines_ignored(self, tmp_path):
        reg = tmp_path / "reg.jsonl"
        with open(reg, "w") as f:
            f.write("\n")
            f.write('{"screenKey":"X","result":"PASS"}\n')
            f.write("\n")
        entries = _load_registry(reg)
        assert len(entries) == 1


# ---------------------------------------------------------------------------
# _build_component_stability
# ---------------------------------------------------------------------------

class TestBuildComponentStability:
    def test_empty_entries_produces_empty_screens(self):
        result = _build_component_stability([])
        assert result["totalScreens"] == 0
        assert result["stableScreens"] == 0
        assert result["unstableScreens"] == 0
        assert result["screens"] == []

    def test_all_pass_stable(self):
        entries = [_make_entry("Home", "PASS")] * 10
        result = _build_component_stability(entries)
        assert result["totalScreens"] == 1
        assert result["stableScreens"] == 1
        screen = result["screens"][0]
        assert screen["passRate"] == 1.0
        assert screen["stable"] is True

    def test_all_fail_unstable(self):
        entries = [_make_entry("Broken", "FAIL")] * 5
        result = _build_component_stability(entries)
        screen = result["screens"][0]
        assert screen["passRate"] == 0.0
        assert screen["stable"] is False

    def test_90_percent_is_stable(self):
        entries = [_make_entry("X", "PASS")] * 9 + [_make_entry("X", "FAIL")]
        result = _build_component_stability(entries)
        screen = result["screens"][0]
        assert screen["passRate"] == 0.9
        assert screen["stable"] is True

    def test_89_percent_is_unstable(self):
        entries = [_make_entry("X", "PASS")] * 89 + [_make_entry("X", "FAIL")] * 11
        result = _build_component_stability(entries)
        screen = result["screens"][0]
        assert screen["stable"] is False

    def test_least_stable_first(self):
        entries = (
            [_make_entry("Stable", "PASS")] * 10
            + [_make_entry("Unstable", "PASS")] * 3
            + [_make_entry("Unstable", "FAIL")] * 7
        )
        result = _build_component_stability(entries)
        keys = [s["screenKey"] for s in result["screens"]]
        assert keys[0] == "Unstable"
        assert keys[1] == "Stable"

    def test_multiple_screens(self):
        entries = [
            _make_entry("A", "PASS"),
            _make_entry("A", "FAIL"),
            _make_entry("B", "PASS"),
        ]
        result = _build_component_stability(entries)
        assert result["totalScreens"] == 2

    def test_last_result_tracking(self):
        entries = [
            _make_entry("X", "PASS", ts="2026-04-15T08:00:00+00:00"),
            _make_entry("X", "FAIL", ts="2026-04-15T10:00:00+00:00"),
        ]
        result = _build_component_stability(entries)
        screen = result["screens"][0]
        assert screen["lastResult"] == "FAIL"
        assert "10:00" in screen["lastSeen"]

    def test_generated_at_present(self):
        result = _build_component_stability([])
        assert "generatedAt" in result
        assert "2026" in result["generatedAt"]


# ---------------------------------------------------------------------------
# _build_failure_patterns
# ---------------------------------------------------------------------------

class TestBuildFailurePatterns:
    def test_empty_entries(self):
        result = _build_failure_patterns([])
        assert result["summary"]["totalValidations"] == 0
        assert result["summary"]["totalFail"] == 0
        assert result["summary"]["overallPassRate"] == 0.0

    def test_all_pass(self):
        entries = [_make_entry("X", "PASS")] * 5
        result = _build_failure_patterns(entries)
        assert result["summary"]["totalPass"] == 5
        assert result["summary"]["totalFail"] == 0
        assert result["summary"]["overallPassRate"] == 1.0

    def test_failures_by_wave(self):
        entries = [
            _make_entry(wave="Wave8", result="FAIL"),
            _make_entry(wave="Wave8", result="FAIL"),
            _make_entry(wave="Wave9", result="FAIL"),
        ]
        result = _build_failure_patterns(entries)
        assert result["failuresByWave"]["Wave8"] == 2
        assert result["failuresByWave"]["Wave9"] == 1

    def test_failures_by_device(self):
        entries = [
            _make_entry(device="mobile", result="FAIL"),
            _make_entry(device="desktop", result="FAIL"),
            _make_entry(device="mobile", result="FAIL"),
        ]
        result = _build_failure_patterns(entries)
        assert result["failuresByDevice"]["mobile"] == 2
        assert result["failuresByDevice"]["desktop"] == 1

    def test_top_failing_screens_sorted(self):
        entries = (
            [_make_entry("Buggy", result="FAIL")] * 5
            + [_make_entry("Flaky", result="FAIL")] * 2
            + [_make_entry("Ok", result="PASS")] * 3
        )
        result = _build_failure_patterns(entries)
        top = result["topFailingScreens"]
        assert top[0]["screenKey"] == "Buggy"
        assert top[0]["failCount"] == 5
        assert top[1]["screenKey"] == "Flaky"

    def test_top_failing_max_10(self):
        entries = [_make_entry(f"Screen{i}", result="FAIL") for i in range(20)]
        result = _build_failure_patterns(entries)
        assert len(result["topFailingScreens"]) == 10

    def test_pass_entries_not_in_failure_counts(self):
        entries = [_make_entry("Good", "PASS"), _make_entry("Bad", "FAIL")]
        result = _build_failure_patterns(entries)
        screen_keys = [t["screenKey"] for t in result["topFailingScreens"]]
        assert "Good" not in screen_keys

    def test_overall_pass_rate(self):
        entries = [_make_entry("X", "PASS")] * 3 + [_make_entry("X", "FAIL")]
        result = _build_failure_patterns(entries)
        assert result["summary"]["overallPassRate"] == 0.75


# ---------------------------------------------------------------------------
# generate_visual_intelligence (integration)
# ---------------------------------------------------------------------------

class TestGenerateVisualIntelligence:
    def test_creates_output_dir(self, tmp_path):
        registry = tmp_path / "reg.jsonl"
        out = tmp_path / "vi-output"
        generate_visual_intelligence(registry, out)
        assert out.exists()

    def test_creates_stats_dir(self, tmp_path):
        registry = tmp_path / "reg.jsonl"
        out = tmp_path / "vi-output"
        generate_visual_intelligence(registry, out)
        assert (out / "stats").exists()

    def test_creates_cache_index(self, tmp_path):
        registry = tmp_path / "reg.jsonl"
        out = tmp_path / "vi-output"
        generate_visual_intelligence(registry, out)
        assert (out / "cache_index.jsonl").exists()

    def test_creates_component_stability(self, tmp_path):
        registry = tmp_path / "reg.jsonl"
        out = tmp_path / "vi-output"
        generate_visual_intelligence(registry, out)
        assert (out / "stats" / "component_stability.json").exists()

    def test_creates_failure_patterns(self, tmp_path):
        registry = tmp_path / "reg.jsonl"
        out = tmp_path / "vi-output"
        generate_visual_intelligence(registry, out)
        assert (out / "stats" / "failure_patterns.json").exists()

    def test_missing_registry_produces_empty_output(self, tmp_path):
        out = tmp_path / "vi-output"
        result = generate_visual_intelligence(tmp_path / "nonexistent.jsonl", out)
        assert result["entries"] == 0
        assert result["screens"] == 0
        assert result["fail_entries"] == 0

    def test_cache_index_has_no_file_paths(self, tmp_path):
        reg = tmp_path / "reg.jsonl"
        _write_registry(reg, [_make_entry("Home", "PASS")])
        out = tmp_path / "vi-output"
        generate_visual_intelligence(reg, out)

        with open(out / "cache_index.jsonl") as f:
            entry = json.loads(f.read().strip())
        assert "artifacts" not in entry
        assert "screenshotPath" not in str(entry)

    def test_cache_index_hashes_preserved(self, tmp_path):
        reg = tmp_path / "reg.jsonl"
        _write_registry(reg, [_make_entry("Home", "PASS")])
        out = tmp_path / "vi-output"
        generate_visual_intelligence(reg, out)

        with open(out / "cache_index.jsonl") as f:
            entry = json.loads(f.read().strip())
        assert entry["imageSha256"] == "aaa"

    def test_return_value_counts(self, tmp_path):
        reg = tmp_path / "reg.jsonl"
        _write_registry(reg, [
            _make_entry("A", "PASS"),
            _make_entry("B", "FAIL"),
            _make_entry("A", "FAIL"),
        ])
        out = tmp_path / "vi-output"
        result = generate_visual_intelligence(reg, out)
        assert result["entries"] == 3
        assert result["screens"] == 2
        assert result["fail_entries"] == 2

    def test_stability_json_valid(self, tmp_path):
        reg = tmp_path / "reg.jsonl"
        _write_registry(reg, [_make_entry("Home", "PASS")])
        out = tmp_path / "vi-output"
        generate_visual_intelligence(reg, out)

        data = json.loads((out / "stats" / "component_stability.json").read_text())
        assert "screens" in data
        assert data["totalScreens"] == 1

    def test_failure_patterns_json_valid(self, tmp_path):
        reg = tmp_path / "reg.jsonl"
        _write_registry(reg, [_make_entry("Home", "FAIL", wave="W9")])
        out = tmp_path / "vi-output"
        generate_visual_intelligence(reg, out)

        data = json.loads((out / "stats" / "failure_patterns.json").read_text())
        assert data["summary"]["totalFail"] == 1
        assert data["failuresByWave"]["W9"] == 1

    def test_idempotent_overwrite(self, tmp_path):
        reg = tmp_path / "reg.jsonl"
        _write_registry(reg, [_make_entry("A", "PASS")])
        out = tmp_path / "vi-output"
        generate_visual_intelligence(reg, out)
        # second run with different data — should overwrite cleanly
        _write_registry(reg, [_make_entry("B", "FAIL"), _make_entry("B", "FAIL")])
        result = generate_visual_intelligence(reg, out)
        assert result["entries"] == 2
        data = json.loads((out / "stats" / "component_stability.json").read_text())
        assert data["screens"][0]["screenKey"] == "B"
