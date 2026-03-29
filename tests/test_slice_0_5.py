"""Tests for ExecutionEngine — SLICE_0.5 wiki capability signals."""

import json
import os
import tempfile

import pytest

from core.execution_engine import ExecutionEngine, _extract_wiki_signals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(tmp_dir: str, wiki_dir: str = "") -> ExecutionEngine:
    protocol_dir = os.path.join(tmp_dir, "protocol")
    data_dir = os.path.join(tmp_dir, "data")
    os.makedirs(protocol_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    state = {
        "current_slice": "SLICE_0_5",
        "completed_slices": ["SLICE_0"],
        "status": "READY",
        "last_run": None,
    }
    with open(os.path.join(protocol_dir, "state.json"), "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    return ExecutionEngine(
        solution_root=tmp_dir,
        protocol_root=protocol_dir,
        data_root=data_dir,
        wiki_root=wiki_dir,
    )


def _write_md(directory: str, filename: str, content: str) -> str:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _read_result(tmp_dir: str) -> dict:
    path = os.path.join(tmp_dir, "data", "wiki_signals.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Unit tests on _extract_wiki_signals (pure function)
# ---------------------------------------------------------------------------

def test_extract_wiki_signals_heading():
    content = "# Batch Operations\n\nSome text here."
    result = _extract_wiki_signals(content)
    assert "Batch Operations" in result["headings"]


def test_extract_wiki_signals_subheadings():
    content = "# Top\n## Sub One\n### Sub Two\n"
    result = _extract_wiki_signals(content)
    assert "Top" in result["headings"]
    assert "Sub One" in result["headings"]
    assert "Sub Two" in result["headings"]


def test_extract_wiki_signals_bullet_list():
    content = "# Features\n\n- Oprydning\n- Import af telefonnumre\n"
    result = _extract_wiki_signals(content)
    assert "Oprydning" in result["bullets"]
    assert "Import af telefonnumre" in result["bullets"]


def test_extract_wiki_signals_bullet_with_link_extracts_label():
    content = "- [Oprydning](/SMS-Service/Oprydning)\n"
    result = _extract_wiki_signals(content)
    assert "Oprydning" in result["bullets"]


def test_extract_wiki_signals_links():
    content = "[Customer List](/api/customers)\n[Order Management](/api/orders)\n"
    result = _extract_wiki_signals(content)
    assert "Customer List" in result["links"]
    assert "Order Management" in result["links"]


def test_extract_wiki_signals_truncates_to_20_words():
    long_text = " ".join(f"word{i}" for i in range(30))
    content = f"# {long_text}\n"
    result = _extract_wiki_signals(content)
    assert len(result["headings"]) == 1
    assert len(result["headings"][0].split()) == 20


def test_extract_wiki_signals_deduplicates():
    content = "# Batch\n# Batch\n- Oprydning\n- Oprydning\n"
    result = _extract_wiki_signals(content)
    assert result["headings"].count("Batch") == 1
    assert result["bullets"].count("Oprydning") == 1


def test_extract_wiki_signals_sorted():
    content = "# Zebra\n# Apple\n- Mango\n- Banana\n"
    result = _extract_wiki_signals(content)
    assert result["headings"] == sorted(result["headings"])
    assert result["bullets"] == sorted(result["bullets"])


def test_extract_wiki_signals_empty_file():
    result = _extract_wiki_signals("")
    assert result == {"headings": [], "bullets": [], "links": []}


# ---------------------------------------------------------------------------
# Integration tests for _run_slice_0_5
# ---------------------------------------------------------------------------

def test_slice_0_5_heading_extracted():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = os.path.join(tmp, "wiki")
        _write_md(wiki, "ServiceAlert.md",
                  "# Batch Operations\n\n- Oprydning\n- Import af telefonnumre\n")

        engine = _make_engine(tmp, wiki)
        result = engine._run_slice_0_5()

        assert result["status"] == "OK"
        data = _read_result(tmp)
        assert len(data["capabilities"]) == 1
        cap = data["capabilities"][0]
        assert cap["name"] == "Batch Operations"
        assert cap["source"] == "wiki"
        assert cap["file"] == "ServiceAlert.md"


def test_slice_0_5_bullet_signals_extracted():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = os.path.join(tmp, "wiki")
        _write_md(wiki, "Features.md",
                  "# Features\n\n- Alarm Sending\n- Address Lookup\n")

        engine = _make_engine(tmp, wiki)
        engine._run_slice_0_5()

        data = _read_result(tmp)
        signals = data["capabilities"][0]["signals"]
        assert "Alarm Sending" in signals
        assert "Address Lookup" in signals


def test_slice_0_5_links_extracted():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = os.path.join(tmp, "wiki")
        _write_md(wiki, "Domain.md",
                  "# Domain\n\n[Batch Jobs](/batch)\n[Customer Import](/import)\n")

        engine = _make_engine(tmp, wiki)
        engine._run_slice_0_5()

        data = _read_result(tmp)
        signals = data["capabilities"][0]["signals"]
        assert "Batch Jobs" in signals
        assert "Customer Import" in signals


def test_slice_0_5_deterministic():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = os.path.join(tmp, "wiki")
        _write_md(wiki, "ServiceAlert.md",
                  "# Notifications\n\n- SMS\n- Email\n[Settings](/settings)\n")

        engine = _make_engine(tmp, wiki)
        r1 = engine._run_slice_0_5()
        r2 = engine._run_slice_0_5()

        assert r1 == r2
        d1 = _read_result(tmp)

        # Re-run to get second file write
        engine._run_slice_0_5()
        d2 = _read_result(tmp)
        assert d1 == d2


def test_slice_0_5_no_wiki_root_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        engine = _make_engine(tmp, "")
        result = engine._run_slice_0_5()

        assert result["status"] == "OK"
        assert result["items_found"] == 0
        data = _read_result(tmp)
        assert data["capabilities"] == []


def test_slice_0_5_empty_md_file_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = os.path.join(tmp, "wiki")
        _write_md(wiki, "Empty.md", "")
        _write_md(wiki, "Real.md", "# Something\n- feature\n")

        engine = _make_engine(tmp, wiki)
        engine._run_slice_0_5()

        data = _read_result(tmp)
        files = [c["file"] for c in data["capabilities"]]
        assert "Empty.md" not in files
        assert "Real.md" in files


def test_slice_0_5_multiple_files_sorted_by_filename():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = os.path.join(tmp, "wiki")
        _write_md(wiki, "Zebra.md", "# Zebra Feature\n- item\n")
        _write_md(wiki, "Alpha.md", "# Alpha Feature\n- item\n")
        _write_md(wiki, "Middle.md", "# Middle Feature\n- item\n")

        engine = _make_engine(tmp, wiki)
        engine._run_slice_0_5()

        data = _read_result(tmp)
        file_order = [c["file"] for c in data["capabilities"]]
        assert file_order == sorted(file_order)


def test_slice_0_5_no_nulls_in_output():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = os.path.join(tmp, "wiki")
        _write_md(wiki, "ServiceAlert.md",
                  "# Batch Operations\n\n- Oprydning\n[Link](/path)\n")

        engine = _make_engine(tmp, wiki)
        engine._run_slice_0_5()

        data = _read_result(tmp)
        for cap in data["capabilities"]:
            assert cap["name"] is not None and cap["name"] != ""
            assert cap["source"] is not None
            assert cap["file"] is not None
            for s in cap["signals"]:
                assert s is not None and s != ""


def test_slice_0_5_advances_state_to_slice_0_7():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = os.path.join(tmp, "wiki")
        _write_md(wiki, "Ops.md", "# Operations\n- Deploy\n")

        engine = _make_engine(tmp, wiki)
        engine.execute_next_slice()

        state = engine.load_state()
        assert state["current_slice"] == "SLICE_0_7"
        assert "SLICE_0_5" in state["completed_slices"]
