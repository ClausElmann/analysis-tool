"""Tests for git_analyzer — SLICE_0.8 git intelligence extraction."""

import json
import os
import subprocess
import tempfile

import pytest

from core.git_analyzer import (
    analyze_git,
    _classify,
    _normalise,
    _should_ignore,
    _fetch_commits,
)


# ---------------------------------------------------------------------------
# Helpers: build a real local git repo in a temp directory
# ---------------------------------------------------------------------------

def _git(args, cwd):
    """Run a git command; raise on failure."""
    subprocess.check_call(
        ["git"] + args,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _make_git_repo(tmp_dir: str) -> str:
    """Initialise a minimal git repo with a handful of commits.

    Returns the path to the repo root.
    """
    _git(["init"], tmp_dir)
    _git(["config", "user.email", "ci@test.local"], tmp_dir)
    _git(["config", "user.name", "CI Test"], tmp_dir)

    def _commit(message: str, filename: str, content: str = "x"):
        fpath = os.path.join(tmp_dir, filename)
        with open(fpath, "w", encoding="utf-8") as fh:
            fh.write(content)
        _git(["add", filename], tmp_dir)
        _git(["commit", "-m", message], tmp_dir)

    _commit("prevent duplicate sms to same number", "SmsService.cs")
    _commit("fix crash when phone number is null", "PhoneValidator.cs")
    _commit("create scheduled batch job for imports", "BatchJob.cs")
    _commit("workaround for missing provider ID", "ProviderMapper.cs")
    _commit("refactor notification pipeline", "Pipeline.cs")
    _commit("fix", "noise.txt")               # noise — too short / exact match
    _commit("update", "noise2.txt")           # noise — exact match
    _commit("x", "noise3.txt")               # noise — too short
    return tmp_dir


# ---------------------------------------------------------------------------
# Unit tests: _classify
# ---------------------------------------------------------------------------

def test_classify_rule():
    assert _classify("prevent duplicate sms to the same recipient") == "rule"


def test_classify_rule_must():
    assert _classify("must validate phone numbers before sending") == "rule"


def test_classify_fix():
    assert _classify("fix crash when recipient list is empty") == "fix"


def test_classify_fix_bug():
    assert _classify("bug in import parser causes index error") == "fix"


def test_classify_feature():
    assert _classify("create new batch export for norway") == "feature"


def test_classify_feature_send():
    assert _classify("send sms via new gateway integration") == "feature"


def test_classify_risk():
    assert _classify("workaround for missing provider id") == "risk"


def test_classify_risk_hack():
    assert _classify("hack to bypass validation temporarily") == "risk"


def test_classify_risk_quick_fix():
    assert _classify("quick fix for deployment issue") == "risk"


def test_classify_refactor():
    assert _classify("refactor notification pipeline") == "refactor"


def test_classify_unknown():
    assert _classify("misc change to readme") == "unknown"


# ---------------------------------------------------------------------------
# Unit tests: _should_ignore
# ---------------------------------------------------------------------------

def test_ignore_too_short():
    assert _should_ignore("fix") is True
    assert _should_ignore("x") is True
    assert _should_ignore("abc") is True


def test_ignore_noise_exact():
    assert _should_ignore("update") is True
    assert _should_ignore("test") is True
    assert _should_ignore("minor") is True


def test_ignore_no_keywords():
    assert _should_ignore("misc change to readme file") is True


def test_not_ignored_rule():
    assert _should_ignore("prevent duplicate sms to same number") is False


def test_not_ignored_fix():
    assert _should_ignore("fix crash when phone number is null") is False


# ---------------------------------------------------------------------------
# Unit tests: _normalise
# ---------------------------------------------------------------------------

def test_normalise_lowercases():
    assert _normalise("Fix CRASH in PhoneValidator") == "fix crash in phonevalidator"


def test_normalise_trims():
    assert _normalise("  fix crash  ") == "fix crash"


def test_normalise_collapses_whitespace():
    assert _normalise("fix  multiple   spaces") == "fix multiple spaces"


# ---------------------------------------------------------------------------
# Integration tests: analyze_git on a real local repo
# ---------------------------------------------------------------------------

def test_analyze_git_no_git_dir():
    with tempfile.TemporaryDirectory() as tmp:
        result = analyze_git(tmp)
        assert result["insights"] == []
        assert len(result["errors"]) > 0


def test_analyze_git_extracts_rule_commit():
    with tempfile.TemporaryDirectory() as tmp:
        _make_git_repo(tmp)
        result = analyze_git(tmp)
        texts = [i["text"] for i in result["insights"]]
        assert any("prevent" in t for t in texts)


def test_analyze_git_extracts_fix_commit():
    with tempfile.TemporaryDirectory() as tmp:
        _make_git_repo(tmp)
        result = analyze_git(tmp)
        types = {i["text"]: i["type"] for i in result["insights"]}
        fix_entries = [t for t, tp in types.items() if tp == "fix"]
        assert len(fix_entries) >= 1


def test_analyze_git_ignores_noise_commits():
    with tempfile.TemporaryDirectory() as tmp:
        _make_git_repo(tmp)
        result = analyze_git(tmp)
        texts = [i["text"] for i in result["insights"]]
        # "fix", "update", "x" must all be absent
        assert "fix" not in texts
        assert "update" not in texts
        assert "x" not in texts


def test_analyze_git_file_list_extracted():
    with tempfile.TemporaryDirectory() as tmp:
        _make_git_repo(tmp)
        result = analyze_git(tmp)
        # At least some insights must carry a non-empty file list
        files_found = [i for i in result["insights"] if i["files"]]
        assert len(files_found) > 0


def test_analyze_git_files_capped_at_five():
    with tempfile.TemporaryDirectory() as tmp:
        _git(["init"], tmp)
        _git(["config", "user.email", "ci@test.local"], tmp)
        _git(["config", "user.name", "CI Test"], tmp)
        # Commit with 8 files — should be capped to 5
        fnames = [f"f{i}.cs" for i in range(8)]
        for fn in fnames:
            open(os.path.join(tmp, fn), "w").close()
            _git(["add", fn], tmp)
        _git(["commit", "-m", "create many services for batch processing"], tmp)
        result = analyze_git(tmp)
        for insight in result["insights"]:
            assert len(insight["files"]) <= 5


def test_analyze_git_deterministic():
    with tempfile.TemporaryDirectory() as tmp:
        _make_git_repo(tmp)
        r1 = analyze_git(tmp)
        r2 = analyze_git(tmp)
        assert r1["insights"] == r2["insights"]


def test_analyze_git_sorted_by_text():
    with tempfile.TemporaryDirectory() as tmp:
        _make_git_repo(tmp)
        result = analyze_git(tmp)
        texts = [i["text"] for i in result["insights"]]
        assert texts == sorted(texts)


def test_analyze_git_ids_sequential():
    with tempfile.TemporaryDirectory() as tmp:
        _make_git_repo(tmp)
        result = analyze_git(tmp)
        for expected_idx, insight in enumerate(result["insights"], start=1):
            assert insight["id"] == f"git_{expected_idx:04d}"


def test_analyze_git_no_nulls():
    with tempfile.TemporaryDirectory() as tmp:
        _make_git_repo(tmp)
        result = analyze_git(tmp)
        for i in result["insights"]:
            assert i.get("id") is not None
            assert i.get("type") is not None
            assert i.get("text") is not None
            assert i.get("confidence") is not None
            assert isinstance(i.get("files"), list)


def test_analyze_git_confidence_values():
    with tempfile.TemporaryDirectory() as tmp:
        _make_git_repo(tmp)
        result = analyze_git(tmp)
        valid_confidences = {0.9, 0.8, 0.7, 0.6, 0.5, 0.4}
        for i in result["insights"]:
            assert i["confidence"] in valid_confidences


def test_analyze_git_no_remote_usage(monkeypatch):
    """Ensure no subprocess call contains 'fetch' or 'pull'."""
    calls = []
    original_run = subprocess.run

    def _spy_run(cmd, **kwargs):
        calls.append(cmd)
        return original_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", _spy_run)

    with tempfile.TemporaryDirectory() as tmp:
        _make_git_repo(tmp)
        analyze_git(tmp)

    for cmd in calls:
        cmd_str = " ".join(str(c) for c in cmd)
        assert "fetch" not in cmd_str, f"Remote call detected: {cmd_str}"
        assert "pull" not in cmd_str, f"Remote call detected: {cmd_str}"


def test_analyze_git_deduplicates_same_message():
    with tempfile.TemporaryDirectory() as tmp:
        _git(["init"], tmp)
        _git(["config", "user.email", "ci@test.local"], tmp)
        _git(["config", "user.name", "CI Test"], tmp)

        for fname in ("a.cs", "b.cs"):
            open(os.path.join(tmp, fname), "w").close()
            _git(["add", fname], tmp)
            _git(["commit", "-m", "prevent duplicate entries in database"], tmp)

        result = analyze_git(tmp)
        texts = [i["text"] for i in result["insights"]]
        # Same message → only one insight
        assert texts.count("prevent duplicate entries in database") == 1


def test_analyze_git_dedup_merges_files():
    with tempfile.TemporaryDirectory() as tmp:
        _git(["init"], tmp)
        _git(["config", "user.email", "ci@test.local"], tmp)
        _git(["config", "user.name", "CI Test"], tmp)

        for fname in ("svc.cs", "repo.cs"):
            open(os.path.join(tmp, fname), "w").close()
            _git(["add", fname], tmp)
            _git(["commit", "-m", "prevent duplicate sms to same recipient"], tmp)

        result = analyze_git(tmp)
        entry = next(
            i for i in result["insights"]
            if "prevent duplicate sms" in i["text"]
        )
        # Both files should appear in the merged list
        assert "svc.cs" in entry["files"]
        assert "repo.cs" in entry["files"]


# ---------------------------------------------------------------------------
# Integration test: full SLICE_0.8 via execution engine
# ---------------------------------------------------------------------------

def test_slice_0_8_via_engine():
    from core.execution_engine import ExecutionEngine

    with tempfile.TemporaryDirectory() as tmp:
        _make_git_repo(tmp)

        protocol_dir = os.path.join(tmp, "protocol")
        data_dir = os.path.join(tmp, "data")
        os.makedirs(protocol_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        state = {
            "current_slice": "SLICE_0_8",
            "completed_slices": ["SLICE_0", "SLICE_0_5", "SLICE_0_7"],
            "status": "READY",
            "last_run": None,
        }
        with open(os.path.join(protocol_dir, "state.json"), "w", encoding="utf-8") as fh:
            json.dump(state, fh)

        engine = ExecutionEngine(
            solution_root=tmp,
            protocol_root=protocol_dir,
            data_root=data_dir,
        )
        result = engine.execute_next_slice()

        assert result["slice"] == "SLICE_0_8"
        assert result["status"] == "OK"

        out_path = os.path.join(data_dir, "git_insights.json")
        assert os.path.isfile(out_path)
        with open(out_path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert "insights" in data

        new_state = engine.load_state()
        assert new_state["current_slice"] == "SLICE_9"
        assert "SLICE_0_8" in new_state["completed_slices"]
