"""Tests for work_item_analyzer — SLICE_6 work item CSV analysis."""

import json
import os
import tempfile

import pytest

from core.work_item_analyzer import (
    analyze_work_items,
    _detect_delimiter,
    _normalise,
    _extract_keywords,
    _area_to_name,
)


# ---------------------------------------------------------------------------
# CSV builder helper
# ---------------------------------------------------------------------------

_HEADER = "ID,Work Item Type,Title,Assigned To,State,Tags,Description,Acceptance Criteria,Created Date,Changed Date,Area Path,Iteration Path,Parent,Repro Steps"
_HEADER_SEMI = _HEADER.replace(",", ";")


def _write_csv(directory: str, rows: list, delimiter: str = ",") -> str:
    """Write rows (list of dicts) to a CSV file; returns path."""
    path = os.path.join(directory, "data.csv")
    header = _HEADER if delimiter == "," else _HEADER_SEMI
    lines = [header]
    fields = [f.strip() for f in header.split(delimiter)]
    for row in rows:
        values = [str(row.get(f, "")) for f in fields]
        # Quote values that contain the delimiter
        quoted = [
            f'"{v}"' if delimiter in v or "\n" in v else v
            for v in values
        ]
        lines.append(delimiter.join(quoted))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


def _make_row(
    item_id="1001",
    title="Create notification batch job",
    area="SMS-service\\Batch",
    desc="",
    criteria="",
    tags="",
) -> dict:
    return {
        "ID": item_id,
        "Work Item Type": "User Story",
        "Title": title,
        "Assigned To": "",
        "State": "Active",
        "Tags": tags,
        "Description": desc,
        "Acceptance Criteria": criteria,
        "Created Date": "01.01.2025 10.00.00",
        "Changed Date": "02.01.2025 10.00.00",
        "Area Path": area,
        "Iteration Path": "SMS-service\\Sprint 1",
        "Parent": "",
        "Repro Steps": "",
    }


# ---------------------------------------------------------------------------
# Unit tests: helpers
# ---------------------------------------------------------------------------

def test_detect_delimiter_comma():
    header = "ID,Title,Area Path,Description"
    assert _detect_delimiter(header) == ","


def test_detect_delimiter_semicolon():
    header = "ID;Title;Area Path;Description"
    assert _detect_delimiter(header) == ";"


def test_normalise_strips_html():
    result = _normalise("<div>Create <b>batch</b> job</div>")
    assert "<" not in result
    assert "create" in result
    assert "batch" in result


def test_normalise_lowercase():
    assert _normalise("Create Batch Job") == "create batch job"


def test_normalise_removes_punctuation():
    result = _normalise("fix: issue (duplicate), crash!")
    assert ":" not in result
    assert "!" not in result
    assert "(" not in result


def test_normalise_collapses_whitespace():
    assert _normalise("fix   lots  of   spaces") == "fix lots of spaces"


def test_extract_keywords_removes_stopwords():
    kws = _extract_keywords("create the batch and export for the")
    assert "the" not in kws
    assert "and" not in kws
    assert "for" not in kws
    assert "create" in kws
    assert "batch" in kws
    assert "export" in kws


def test_extract_keywords_min_length():
    kws = _extract_keywords("do it run create batch")
    assert "do" not in kws   # len 2
    assert "it" not in kws   # len 2
    # 'run' is 3 chars and not in stopwords
    assert "run" in kws


def test_extract_keywords_deduplicates():
    kws = _extract_keywords("create batch create batch")
    assert kws.count("create") == 1
    assert kws.count("batch") == 1


def test_area_to_name_backslash():
    assert _area_to_name("SMS-service\\General") == "sms_service_general"


def test_area_to_name_slash():
    assert _area_to_name("SMS-service/Batch") == "sms_service_batch"


def test_area_to_name_empty():
    assert _area_to_name("") == "unknown"


# ---------------------------------------------------------------------------
# Integration tests: analyze_work_items
# ---------------------------------------------------------------------------

def test_missing_csv_returns_error():
    result = analyze_work_items("/nonexistent/path/data.csv")
    assert result["capabilities"] == []
    assert result["features"] == []
    assert len(result["errors"]) > 0


def test_small_csv_correct_parsing():
    with tempfile.TemporaryDirectory() as tmp:
        _write_csv(tmp, [
            _make_row("1001", "Create notification batch job", "SMS-service\\Batch"),
            _make_row("1002", "Send SMS to subscribers", "SMS-service\\SMS"),
        ])
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    assert len(result["features"]) == 2
    ids = [f["id"] for f in result["features"]]
    assert "1001" in ids
    assert "1002" in ids


def test_delimiter_detection_semicolon():
    with tempfile.TemporaryDirectory() as tmp:
        _write_csv(tmp, [
            _make_row("2001", "Create batch export process"),
        ], delimiter=";")
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    assert len(result["features"]) == 1
    assert result["features"][0]["id"] == "2001"


def test_empty_rows_ignored():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "data.csv")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(_HEADER + "\n")
            fh.write("1001,,Create notification,,Active,,,,,,,,,\n")
            fh.write(",,,,,,,,,,,,,\n")   # fully blank row
            fh.write("1002,,Send alerts,,Active,,,,,,,,,\n")
        result = analyze_work_items(path)

    ids = [f["id"] for f in result["features"]]
    assert "" not in ids  # blank row not included
    assert "1001" in ids
    assert "1002" in ids


def test_keyword_extraction_from_title():
    with tempfile.TemporaryDirectory() as tmp:
        _write_csv(tmp, [
            _make_row("3001", "prevent duplicate SMS notifications", "SMS-service\\SMS"),
        ])
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    feat = result["features"][0]
    assert "prevent" in feat["keywords"]
    assert "duplicate" in feat["keywords"]


def test_keyword_extraction_includes_description():
    with tempfile.TemporaryDirectory() as tmp:
        _write_csv(tmp, [
            _make_row(
                "4001",
                "SMS gateway",
                desc="validate phone numbers before sending",
            ),
        ])
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    feat = result["features"][0]
    assert "validate" in feat["keywords"]
    assert "phone" in feat["keywords"]


def test_keyword_extraction_includes_acceptance_criteria():
    with tempfile.TemporaryDirectory() as tmp:
        _write_csv(tmp, [
            _make_row(
                "5001",
                "User login",
                criteria="must validate password length minimum eight chars",
            ),
        ])
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    feat = result["features"][0]
    assert "validate" in feat["keywords"] or "password" in feat["keywords"]


def test_capability_grouping_by_area():
    with tempfile.TemporaryDirectory() as tmp:
        _write_csv(tmp, [
            _make_row("6001", "Create batch job", area="SMS-service\\Batch"),
            _make_row("6002", "Schedule batch run", area="SMS-service\\Batch"),
            _make_row("6003", "Send SMS alert", area="SMS-service\\SMS"),
        ])
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    cap_names = [c["name"] for c in result["capabilities"]]
    assert "sms_service_batch" in cap_names
    assert "sms_service_sms" in cap_names

    batch_cap = next(c for c in result["capabilities"] if c["name"] == "sms_service_batch")
    assert batch_cap["item_count"] == 2


def test_capability_item_count():
    with tempfile.TemporaryDirectory() as tmp:
        rows = [_make_row(str(i), f"Create feature {i}", area="SMS-service\\Core") for i in range(5)]
        _write_csv(tmp, rows)
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    cap = next(c for c in result["capabilities"] if c["name"] == "sms_service_core")
    assert cap["item_count"] == 5


def test_capability_top_keywords_present():
    with tempfile.TemporaryDirectory() as tmp:
        # Create many items with the same keyword so it dominates
        rows = [_make_row(str(i), "validate notification rules process", area="SMS-service\\Core")
                for i in range(10)]
        _write_csv(tmp, rows)
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    cap = next(c for c in result["capabilities"] if c["name"] == "sms_service_core")
    assert "validate" in cap["keywords"]


def test_capabilities_sorted_lexicographically():
    with tempfile.TemporaryDirectory() as tmp:
        _write_csv(tmp, [
            _make_row("1", "item", area="SMS-service\\Zzz"),
            _make_row("2", "item", area="SMS-service\\Aaa"),
            _make_row("3", "item", area="SMS-service\\Mmm"),
        ])
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    names = [c["name"] for c in result["capabilities"]]
    assert names == sorted(names)


def test_features_sorted_by_id():
    with tempfile.TemporaryDirectory() as tmp:
        _write_csv(tmp, [
            _make_row("3001", "Third feature"),
            _make_row("1001", "First feature"),
            _make_row("2001", "Second feature"),
        ])
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    ids = [f["id"] for f in result["features"]]
    assert ids == sorted(ids)


def test_feature_keywords_sorted():
    with tempfile.TemporaryDirectory() as tmp:
        _write_csv(tmp, [
            _make_row("7001", "zebra alpaca mango create batch validate process"),
        ])
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    feat = result["features"][0]
    assert feat["keywords"] == sorted(feat["keywords"])


def test_deterministic_output():
    with tempfile.TemporaryDirectory() as tmp:
        rows = [
            _make_row("1001", "Create batch job", area="SMS-service\\Batch"),
            _make_row("1002", "Send notifications", area="SMS-service\\SMS"),
            _make_row("1003", "Validate phone numbers", area="SMS-service\\SMS"),
        ]
        _write_csv(tmp, rows)
        csv_path = os.path.join(tmp, "data.csv")
        r1 = analyze_work_items(csv_path)
        r2 = analyze_work_items(csv_path)

    assert r1["capabilities"] == r2["capabilities"]
    assert r1["features"] == r2["features"]


def test_no_nulls_in_output():
    with tempfile.TemporaryDirectory() as tmp:
        _write_csv(tmp, [
            _make_row("8001", "Create batch export", area="SMS-service\\Batch"),
        ])
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    for cap in result["capabilities"]:
        assert cap.get("name") is not None
        assert cap.get("area") is not None
        assert isinstance(cap.get("keywords"), list)
        assert isinstance(cap.get("item_count"), int)

    for feat in result["features"]:
        assert feat.get("id") is not None
        assert feat.get("title") is not None
        assert feat.get("capability") is not None
        assert isinstance(feat.get("keywords"), list)


def test_html_stripped_from_description():
    with tempfile.TemporaryDirectory() as tmp:
        _write_csv(tmp, [
            _make_row(
                "9001",
                "Web message",
                desc="<div><b>validate</b> phone numbers <br/> before sending</div>",
            ),
        ])
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    feat = result["features"][0]
    # HTML tags must not appear as keywords
    assert all("<" not in kw for kw in feat["keywords"])
    assert "validate" in feat["keywords"]


def test_empty_csv_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "data.csv")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(_HEADER + "\n")
        result = analyze_work_items(path)

    assert result["capabilities"] == []
    assert result["features"] == []


def test_capability_keywords_capped_at_ten():
    with tempfile.TemporaryDirectory() as tmp:
        # Each item introduces unique keywords; cap the list at 10
        rows = [
            _make_row(str(i), f"feature{i} alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu",
                      area="SMS-service\\Core")
            for i in range(5)
        ]
        _write_csv(tmp, rows)
        result = analyze_work_items(os.path.join(tmp, "data.csv"))

    cap = next(c for c in result["capabilities"] if "core" in c["name"])
    assert len(cap["keywords"]) <= 10


# ---------------------------------------------------------------------------
# Slice execution test
# ---------------------------------------------------------------------------

def test_slice_6_via_engine():
    from core.execution_engine import ExecutionEngine

    with tempfile.TemporaryDirectory() as tmp:
        protocol_dir = os.path.join(tmp, "protocol")
        data_dir = os.path.join(tmp, "data")
        os.makedirs(protocol_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        # Write the CSV into data_root (where _run_slice_6 looks for it)
        rows = [
            _make_row("1001", "Create batch job", area="SMS-service\\Batch"),
            _make_row("1002", "Send SMS notification", area="SMS-service\\SMS"),
        ]
        _write_csv(data_dir, rows)

        state = {
            "current_slice": "SLICE_6",
            "completed_slices": ["SLICE_0", "SLICE_1", "SLICE_2", "SLICE_3"],
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

        assert result["slice"] == "SLICE_6"
        assert result["status"] == "OK"
        assert result["items_found"] == 2

        out_path = os.path.join(data_dir, "work_item_analysis.json")
        assert os.path.isfile(out_path)
        with open(out_path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert len(data["features"]) == 2
        assert len(data["capabilities"]) == 2

        new_state = engine.load_state()
        assert new_state["current_slice"] == "SLICE_12"
        assert "SLICE_6" in new_state["completed_slices"]
