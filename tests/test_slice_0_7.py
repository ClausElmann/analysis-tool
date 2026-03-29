"""Tests for ExecutionEngine — SLICE_0.7 PDF capability extraction."""

import json
import os
import tempfile

import pytest

from core.execution_engine import (
    ExecutionEngine,
    _extract_pdf_toc_capabilities,
    _extract_pdf_operations,
    _group_headings_into_capabilities,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ANALYSIS_TOOL_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
RAW_ROOT = os.path.join(ANALYSIS_TOOL_ROOT, "raw")

_ADMIN_PDF = os.path.join(RAW_ROOT, "Brugervejledning-administration.pdf")
_SA_PDF = os.path.join(RAW_ROOT, "Brugervejledning-til-ServiceAlert.pdf")

_HAS_FITZ = False
try:
    import fitz  # type: ignore[import]  # noqa: F401
    _HAS_FITZ = True
except ImportError:
    pass

requires_fitz = pytest.mark.skipif(not _HAS_FITZ, reason="PyMuPDF not installed")
admin_pdf_present = pytest.mark.skipif(
    not os.path.isfile(_ADMIN_PDF), reason="admin PDF not found"
)
sa_pdf_present = pytest.mark.skipif(
    not os.path.isfile(_SA_PDF), reason="ServiceAlert PDF not found"
)


def _make_engine(tmp_dir: str, state_slice: str = "SLICE_0_7") -> ExecutionEngine:
    protocol_dir = os.path.join(tmp_dir, "protocol")
    data_dir = os.path.join(tmp_dir, "data")
    os.makedirs(protocol_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    state = {
        "current_slice": state_slice,
        "completed_slices": ["SLICE_0", "SLICE_0_5"],
        "status": "READY",
        "last_run": None,
    }
    with open(os.path.join(protocol_dir, "state.json"), "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    return ExecutionEngine(
        solution_root=tmp_dir,
        protocol_root=protocol_dir,
        data_root=data_dir,
        raw_root=tmp_dir,
    )


def _read_result(tmp_dir: str) -> dict:
    path = os.path.join(tmp_dir, "data", "pdf_capabilities.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Unit tests: _extract_pdf_toc_capabilities (pure — no fitz needed)
# ---------------------------------------------------------------------------

def test_extract_pdf_toc_capabilities_level1_extracted():
    toc = [[1, "Velkommen", 1], [1, "Login", 2], [2, "Adgangskode", 2]]
    result = _extract_pdf_toc_capabilities(toc)
    names = [t[1] for t in result]
    assert "Velkommen" in names
    assert "Login" in names


def test_extract_pdf_toc_capabilities_level2_preserved():
    toc = [[1, "Brugerstyring", 1], [2, "Opret bruger", 2], [2, "Slet bruger", 3]]
    result = _extract_pdf_toc_capabilities(toc)
    assert (1, "Brugerstyring") in result
    assert (2, "Opret bruger") in result
    assert (2, "Slet bruger") in result


def test_extract_pdf_toc_capabilities_deduplicates():
    toc = [[1, "Login", 1], [1, "Login", 2]]
    result = _extract_pdf_toc_capabilities(toc)
    assert result.count((1, "Login")) == 1


def test_extract_pdf_toc_capabilities_skips_blank_titles():
    toc = [[1, "", 1], [1, "  ", 2], [2, "Feature", 3]]
    result = _extract_pdf_toc_capabilities(toc)
    titles = [t[1] for t in result]
    assert "" not in titles
    assert "Feature" in titles


def test_extract_pdf_toc_capabilities_empty_toc():
    assert _extract_pdf_toc_capabilities([]) == []


# ---------------------------------------------------------------------------
# Unit tests: _group_headings_into_capabilities (pure — no fitz needed)
# ---------------------------------------------------------------------------

def test_group_headings_level1_becomes_capability():
    headings = [(1, "Brugerstyring"), (2, "Opret bruger")]
    caps = _group_headings_into_capabilities(headings, "test.pdf")
    assert len(caps) == 1
    assert caps[0]["name"] == "Brugerstyring"
    assert caps[0]["source"] == "pdf"
    assert caps[0]["file"] == "test.pdf"


def test_group_headings_level2_becomes_feature():
    headings = [(1, "Brugerstyring"), (2, "Opret bruger"), (2, "Slet bruger")]
    caps = _group_headings_into_capabilities(headings, "test.pdf")
    assert "Opret bruger" in caps[0]["features"]
    assert "Slet bruger" in caps[0]["features"]


def test_group_headings_features_sorted():
    headings = [(1, "Settings"), (2, "Zzz"), (2, "Aaa"), (2, "Mmm")]
    caps = _group_headings_into_capabilities(headings, "test.pdf")
    assert caps[0]["features"] == ["Aaa", "Mmm", "Zzz"]


def test_group_headings_dedup_features():
    headings = [(1, "Settings"), (2, "Same"), (2, "Same")]
    caps = _group_headings_into_capabilities(headings, "test.pdf")
    assert caps[0]["features"].count("Same") == 1


def test_group_headings_dedup_capabilities():
    headings = [(1, "Login"), (2, "Step A"), (1, "Login"), (2, "Step B")]
    caps = _group_headings_into_capabilities(headings, "test.pdf")
    assert sum(1 for c in caps if c["name"] == "Login") == 1
    cap = next(c for c in caps if c["name"] == "Login")
    assert "Step A" in cap["features"]
    assert "Step B" in cap["features"]


def test_group_headings_orphan_level2_skipped():
    """Level-2 headings before any level-1 must not crash."""
    headings = [(2, "Orphan Feature"), (1, "Parent"), (2, "Child")]
    caps = _group_headings_into_capabilities(headings, "test.pdf")
    all_features = [f for c in caps for f in c["features"]]
    assert "Orphan Feature" not in all_features
    assert "Child" in all_features


def test_group_headings_sorted_by_name():
    headings = [(1, "Zulu"), (1, "Alpha"), (1, "Mike")]
    caps = _group_headings_into_capabilities(headings, "test.pdf")
    names = [c["name"] for c in caps]
    assert names == sorted(names)


def test_group_headings_empty_returns_empty():
    assert _group_headings_into_capabilities([], "test.pdf") == []


def test_group_headings_no_nulls():
    headings = [(1, "Cap A"), (2, "Feat 1")]
    caps = _group_headings_into_capabilities(headings, "test.pdf")
    for cap in caps:
        assert cap["name"] is not None
        assert cap["source"] is not None
        assert cap["file"] is not None
        assert isinstance(cap["features"], list)


# ---------------------------------------------------------------------------
# Unit tests: _extract_pdf_operations (pure string — no fitz needed)
# ---------------------------------------------------------------------------

def test_extract_pdf_operations_detects_danish_verbs():
    text = "Klik på Opret ny bruger for at tilføje. Send besked til alle."
    ops = _extract_pdf_operations(text)
    assert any("Opret" in op for op in ops)
    assert any("Send" in op for op in ops)


def test_extract_pdf_operations_returns_sorted():
    text = "Upload fil. Rediger profil. Administrer brugere."
    ops = _extract_pdf_operations(text)
    assert ops == sorted(ops)


def test_extract_pdf_operations_deduplicates():
    text = "Opret bruger. Opret bruger. Opret bruger."
    ops = _extract_pdf_operations(text)
    assert len([op for op in ops if op.startswith("Opret")]) == 1


def test_extract_pdf_operations_empty_text():
    assert _extract_pdf_operations("") == []


def test_extract_pdf_operations_no_false_positives():
    text = "The system automatically creates new records."
    ops = _extract_pdf_operations(text)
    # English "creates" is not in the Danish verb list
    assert ops == []


# ---------------------------------------------------------------------------
# Integration tests: actual PDFs
# ---------------------------------------------------------------------------

@requires_fitz
@admin_pdf_present
def test_admin_pdf_toc_yields_capabilities():
    import fitz
    doc = fitz.open(_ADMIN_PDF)
    toc = doc.get_toc()
    assert len(toc) > 0, "Admin PDF should have an embedded TOC"
    headings = _extract_pdf_toc_capabilities(toc)
    caps = _group_headings_into_capabilities(headings, os.path.basename(_ADMIN_PDF))
    assert len(caps) > 0
    for cap in caps:
        assert cap["name"]
        assert cap["source"] == "pdf"
        assert cap["file"] == os.path.basename(_ADMIN_PDF)


@requires_fitz
@sa_pdf_present
def test_sa_pdf_font_fallback_yields_capabilities():
    import fitz
    from core.execution_engine import _extract_pdf_headings_from_doc
    doc = fitz.open(_SA_PDF)
    toc = doc.get_toc()
    assert len(toc) == 0, "ServiceAlert PDF should have NO embedded TOC"
    headings = _extract_pdf_headings_from_doc(doc)
    assert len(headings) > 0
    caps = _group_headings_into_capabilities(headings, os.path.basename(_SA_PDF))
    assert len(caps) > 0


@requires_fitz
@admin_pdf_present
def test_admin_pdf_operations_extracted():
    import fitz
    doc = fitz.open(_ADMIN_PDF)
    full_text = "\n".join(doc[p].get_text() for p in range(doc.page_count))
    ops = _extract_pdf_operations(full_text)
    assert isinstance(ops, list)
    # Admin manual should have at least a few action verbs
    assert len(ops) >= 1


@requires_fitz
@admin_pdf_present
def test_admin_pdf_deterministic():
    import fitz
    def _run():
        doc = fitz.open(_ADMIN_PDF)
        toc = doc.get_toc()
        headings = _extract_pdf_toc_capabilities(toc)
        caps = _group_headings_into_capabilities(headings, os.path.basename(_ADMIN_PDF))
        return caps

    assert _run() == _run()


@requires_fitz
@sa_pdf_present
def test_sa_pdf_deterministic():
    import fitz
    from core.execution_engine import _extract_pdf_headings_from_doc
    def _run():
        doc = fitz.open(_SA_PDF)
        headings = _extract_pdf_headings_from_doc(doc)
        caps = _group_headings_into_capabilities(headings, os.path.basename(_SA_PDF))
        return caps

    assert _run() == _run()


# ---------------------------------------------------------------------------
# Integration tests: full slice execution
# ---------------------------------------------------------------------------

def test_slice_0_7_no_pdfs_writes_empty_json():
    with tempfile.TemporaryDirectory() as tmp:
        engine = _make_engine(tmp)
        result = engine.execute_next_slice()

        assert result["slice"] == "SLICE_0_7"
        assert result["status"] == "OK"
        data = _read_result(tmp)
        assert data["capabilities"] == []


def test_slice_0_7_advances_state_to_slice_0_8():
    with tempfile.TemporaryDirectory() as tmp:
        engine = _make_engine(tmp)
        engine.execute_next_slice()

        state = engine.load_state()
        assert state["current_slice"] == "SLICE_0_8"
        assert "SLICE_0_7" in state["completed_slices"]


@requires_fitz
@admin_pdf_present
@sa_pdf_present
def test_slice_0_7_with_real_pdfs_end_to_end():
    """Copy both real PDFs into a tmp solution_root and run the slice."""
    import shutil
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        shutil.copy(_ADMIN_PDF, tmp)
        shutil.copy(_SA_PDF, tmp)

        engine = _make_engine(tmp)
        result = engine.execute_next_slice()

        assert result["slice"] == "SLICE_0_7"
        assert result["status"] == "OK"
        assert result["items_found"] > 0

        data = _read_result(tmp)
        caps = data["capabilities"]
        assert len(caps) > 0

        # All required fields present, no nulls
        for cap in caps:
            assert cap.get("name")
            assert cap.get("source") == "pdf"
            assert cap.get("file")
            assert isinstance(cap.get("features"), list)
            assert isinstance(cap.get("operations"), list)

        # Deterministic: no duplicate (file, name) pairs
        keys = [(c["file"], c["name"]) for c in caps]
        assert len(keys) == len(set(keys))

        # Files present in output are only the expected PDFs
        files_in_output = {c["file"] for c in caps}
        assert files_in_output <= {
            os.path.basename(_ADMIN_PDF),
            os.path.basename(_SA_PDF),
        }
