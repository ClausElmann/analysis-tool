"""Tests for gap_analyzer — SLICE_10 gap analysis."""

import json
import os
import tempfile

from core.gap_analyzer import (
    analyze_gaps,
    _detect_work_items_without_modules,
    _detect_modules_without_features,
    _detect_apis_without_ui,
    _detect_routes_without_api,
    _detect_tables_not_referenced,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(directory: str, filename: str, data: dict) -> str:
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def _module(name, routes=None, components=None, apis=None,
            controllers=None, services=None, tables=None,
            features=None, signals=None, confidence=0.5):
    return {
        "name":        name,
        "routes":      routes or [],
        "components":  components or [],
        "apis":        apis or [],
        "controllers": controllers or [],
        "services":    services or [],
        "tables":      tables or [],
        "features":    features or [],
        "signals":     signals or [],
        "confidence":  confidence,
    }


def _model(modules):
    return {"modules": modules}


def _work_items(features=None, capabilities=None):
    return {"features": features or [], "capabilities": capabilities or []}


def _feature(title, keywords=None, capability="cap"):
    return {"id": "1", "title": title, "capability": capability, "keywords": keywords or []}


def _api_map(mappings=None):
    return {"mappings": mappings or []}


def _mapping(entry_id, component, urls, tables=None):
    return {
        "entry_id": entry_id,
        "component": component,
        "apis": [{"url": u, "method": "GET"} for u in urls],
        "sql": {"tables": tables or [], "joins": [], "where_conditions": []},
    }


def _make_engine(solution_root, data_dir, protocol_dir):
    from core.execution_engine import ExecutionEngine
    engine = ExecutionEngine(
        solution_root=solution_root,
        protocol_root=protocol_dir,
        data_root=data_dir,
    )
    state = {
        "current_slice": "SLICE_10",
        "completed_slices": [
            "SLICE_0", "SLICE_0_5", "SLICE_0_7", "SLICE_0_8",
            "SLICE_1", "SLICE_2", "SLICE_3", "SLICE_6",
            "SLICE_7", "SLICE_8",
        ],
        "status": "READY",
        "last_run": "",
    }
    engine.save_state(state)
    return engine


# ---------------------------------------------------------------------------
# Unit tests — _detect_work_items_without_modules
# ---------------------------------------------------------------------------

def test_work_item_without_module_detected():
    features = [_feature("Export reports", keywords=["export", "reports"])]
    module_names = {"customers"}  # no "reports" or "export" module
    gaps = _detect_work_items_without_modules(features, module_names)
    assert len(gaps) == 1
    assert gaps[0]["type"] == "missing_feature"
    assert "Export reports" in gaps[0]["description"]


def test_work_item_covered_by_module_name_in_title():
    features = [_feature("Create customers list", keywords=["customer", "create"])]
    module_names = {"customers"}
    gaps = _detect_work_items_without_modules(features, module_names)
    assert len(gaps) == 0


def test_work_item_covered_by_module_name_in_keywords():
    features = [_feature("Some task", keywords=["customers", "create"])]
    module_names = {"customers"}
    gaps = _detect_work_items_without_modules(features, module_names)
    assert len(gaps) == 0


def test_empty_features_no_gaps():
    gaps = _detect_work_items_without_modules([], {"customers"})
    assert gaps == []


def test_empty_modules_all_features_are_gaps():
    features = [
        _feature("Feature A", keywords=["aaa"]),
        _feature("Feature B", keywords=["bbb"]),
    ]
    gaps = _detect_work_items_without_modules(features, set())
    assert len(gaps) == 2


def test_duplicate_feature_titles_deduplicated():
    features = [
        _feature("Export reports", keywords=["export"]),
        _feature("Export reports", keywords=["reports"]),
    ]
    gaps = _detect_work_items_without_modules(features, set())
    assert len(gaps) == 1


# ---------------------------------------------------------------------------
# Unit tests — _detect_modules_without_features
# ---------------------------------------------------------------------------

def test_module_without_feature_detected():
    modules = [_module("batch")]
    feature_titles = {"Create customer profile"}  # nothing about batch
    gaps = _detect_modules_without_features(modules, feature_titles)
    assert len(gaps) == 1
    assert gaps[0]["type"] == "missing_requirement"
    assert "batch" in gaps[0]["description"]


def test_module_covered_by_feature_title():
    modules = [_module("customers")]
    feature_titles = {"Create customers list"}
    gaps = _detect_modules_without_features(modules, feature_titles)
    assert len(gaps) == 0


def test_empty_modules_no_gaps():
    gaps = _detect_modules_without_features([], {"some feature"})
    assert gaps == []


def test_empty_features_all_modules_flagged():
    modules = [_module("customers"), _module("orders")]
    gaps = _detect_modules_without_features(modules, set())
    assert len(gaps) == 2


# ---------------------------------------------------------------------------
# Unit tests — _detect_apis_without_ui
# ---------------------------------------------------------------------------

def test_api_without_route_detected():
    modules = [_module("customers", apis=["/api/customers"], routes=[])]
    gaps = _detect_apis_without_ui(modules, set(), set())
    assert len(gaps) == 1
    assert gaps[0]["type"] == "orphan_api"
    assert "/api/customers" in gaps[0]["description"]


def test_api_with_route_not_flagged():
    modules = [_module("customers", apis=["/api/customers"], routes=["customers"])]
    gaps = _detect_apis_without_ui(modules, set(), set())
    assert len(gaps) == 0


def test_no_api_no_gap():
    modules = [_module("customers", apis=[], routes=["customers"])]
    gaps = _detect_apis_without_ui(modules, set(), set())
    assert len(gaps) == 0


def test_multiple_orphan_apis_all_detected():
    modules = [_module("backend", apis=["/api/report", "/api/export"], routes=[])]
    gaps = _detect_apis_without_ui(modules, set(), set())
    assert len(gaps) == 2


# ---------------------------------------------------------------------------
# Unit tests — _detect_routes_without_api
# ---------------------------------------------------------------------------

def test_route_without_api_detected():
    modules = [_module("dashboard", routes=["dashboard"], apis=[])]
    gaps = _detect_routes_without_api(modules)
    assert len(gaps) == 1
    assert gaps[0]["type"] == "dead_route"
    assert "dashboard" in gaps[0]["description"]


def test_route_with_api_not_flagged():
    modules = [_module("customers", routes=["customers"], apis=["/api/customers"])]
    gaps = _detect_routes_without_api(modules)
    assert len(gaps) == 0


def test_no_route_no_dead_route_gap():
    modules = [_module("customers", routes=[], apis=["/api/customers"])]
    gaps = _detect_routes_without_api(modules)
    assert len(gaps) == 0


def test_multiple_dead_routes_all_detected():
    modules = [_module("home", routes=["home", "about"], apis=[])]
    gaps = _detect_routes_without_api(modules)
    assert len(gaps) == 2


# ---------------------------------------------------------------------------
# Unit tests — _detect_tables_not_referenced
# ---------------------------------------------------------------------------

def test_table_not_in_api_module_detected():
    modules = [_module("customers", apis=[], tables=["Customers"])]
    all_tables = {"Customers"}
    gaps = _detect_tables_not_referenced(modules, all_tables, set(), set())
    # Customers is in module but module has no apis → not referenced
    assert len(gaps) == 1
    assert gaps[0]["type"] == "dead_table"
    assert "Customers" in gaps[0]["description"]


def test_table_referenced_by_api_module_not_flagged():
    modules = [_module("customers", apis=["/api/customers"], tables=["Customers"])]
    all_tables = {"Customers"}
    gaps = _detect_tables_not_referenced(modules, all_tables, set(), set())
    assert len(gaps) == 0


def test_no_tables_no_gaps():
    modules = [_module("customers", apis=["/api/customers"])]
    gaps = _detect_tables_not_referenced(modules, set(), set(), set())
    assert len(gaps) == 0


def test_multiple_unreferenced_tables_all_detected():
    modules = [_module("x", apis=[], tables=["TableA", "TableB"])]
    all_tables = {"TableA", "TableB"}
    gaps = _detect_tables_not_referenced(modules, all_tables, set(), set())
    assert len(gaps) == 2


# ---------------------------------------------------------------------------
# Integration tests — analyze_gaps
# ---------------------------------------------------------------------------

def test_empty_inputs_produce_no_gaps():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([]))
        _write(tmp, "work_item_analysis.json", _work_items())
        _write(tmp, "component_api_map.json", _api_map())
        result = analyze_gaps(tmp)
    assert result["gaps"] == []


def test_missing_files_no_crash():
    with tempfile.TemporaryDirectory() as tmp:
        result = analyze_gaps(tmp)
    assert "gaps" in result


def test_missing_feature_detected_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("customers", routes=["customers"], apis=["/api/customers"]),
        ]))
        _write(tmp, "work_item_analysis.json", _work_items(features=[
            _feature("Export all invoices", keywords=["export", "invoices"]),
        ]))
        _write(tmp, "component_api_map.json", _api_map())
        result = analyze_gaps(tmp)
    types = [g["type"] for g in result["gaps"]]
    assert "missing_feature" in types


def test_missing_requirement_detected_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("batch", routes=["batch"], apis=["/api/batch"]),
        ]))
        _write(tmp, "work_item_analysis.json", _work_items(features=[
            _feature("Create customer profile", keywords=["customer"]),
        ]))
        _write(tmp, "component_api_map.json", _api_map())
        result = analyze_gaps(tmp)
    types = [g["type"] for g in result["gaps"]]
    assert "missing_requirement" in types


def test_orphan_api_detected_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("reports", routes=[], apis=["/api/reports"]),
        ]))
        _write(tmp, "work_item_analysis.json", _work_items())
        _write(tmp, "component_api_map.json", _api_map())
        result = analyze_gaps(tmp)
    types = [g["type"] for g in result["gaps"]]
    assert "orphan_api" in types


def test_dead_route_detected_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("dashboard", routes=["dashboard"], apis=[]),
        ]))
        _write(tmp, "work_item_analysis.json", _work_items())
        _write(tmp, "component_api_map.json", _api_map())
        result = analyze_gaps(tmp)
    types = [g["type"] for g in result["gaps"]]
    assert "dead_route" in types


def test_dead_table_detected_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("archive", routes=[], apis=[], tables=["ArchiveLog"]),
        ]))
        _write(tmp, "work_item_analysis.json", _work_items())
        _write(tmp, "component_api_map.json", _api_map())
        result = analyze_gaps(tmp)
    types = [g["type"] for g in result["gaps"]]
    assert "dead_table" in types


def test_gaps_sorted_deterministically():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("z_module", routes=["z_module"], apis=["/api/z"]),
            _module("a_module", routes=["a_module"], apis=["/api/a"]),
        ]))
        _write(tmp, "work_item_analysis.json", _work_items(features=[
            _feature("Zebra task", keywords=["zebra"]),
            _feature("Alpha task", keywords=["alpha"]),
        ]))
        _write(tmp, "component_api_map.json", _api_map())
        r1 = analyze_gaps(tmp)
        r2 = analyze_gaps(tmp)
    assert r1["gaps"] == r2["gaps"]


def test_output_has_type_and_description():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("orphan_backend", routes=[], apis=["/api/orphan"]),
        ]))
        _write(tmp, "work_item_analysis.json", _work_items())
        _write(tmp, "component_api_map.json", _api_map())
        result = analyze_gaps(tmp)
    for gap in result["gaps"]:
        assert "type" in gap
        assert "description" in gap
        assert gap["type"]
        assert gap["description"]


def test_clean_system_has_no_gaps():
    """A module with route, api, table, and matching feature → no gaps."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("customers",
                    routes=["customers"],
                    apis=["/api/customers"],
                    tables=["Customers"]),
        ]))
        _write(tmp, "work_item_analysis.json", _work_items(features=[
            _feature("Manage customers", keywords=["customer", "manage"]),
        ]))
        _write(tmp, "component_api_map.json", _api_map([
            _mapping("r_customers", "CustomerListComponent",
                     ["/api/customers"], tables=["Customers"]),
        ]))
        result = analyze_gaps(tmp)
    types = [g["type"] for g in result["gaps"]]
    assert "orphan_api" not in types
    assert "dead_route" not in types
    assert "dead_table" not in types


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------

def test_slice_10_writes_gap_analysis_file():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir     = os.path.join(tmp, "data")
        protocol_dir = os.path.join(tmp, "protocol")
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(protocol_dir, exist_ok=True)

        _write(data_dir, "system_model.json", _model([
            _module("customers", routes=["customers"], apis=["/api/customers"]),
        ]))
        _write(data_dir, "work_item_analysis.json", _work_items())
        _write(data_dir, "component_api_map.json", _api_map())

        engine = _make_engine(tmp, data_dir, protocol_dir)
        result = engine.execute_next_slice()

        assert result["slice"] == "SLICE_10"
        assert result["status"] == "OK"
        assert os.path.isfile(os.path.join(data_dir, "gap_analysis.json"))


def test_slice_10_advances_state_to_slice_4():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir     = os.path.join(tmp, "data")
        protocol_dir = os.path.join(tmp, "protocol")
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(protocol_dir, exist_ok=True)

        _write(data_dir, "system_model.json", _model([
            _module("customers", routes=["customers"], apis=["/api/customers"]),
        ]))
        _write(data_dir, "work_item_analysis.json", _work_items())
        _write(data_dir, "component_api_map.json", _api_map())

        engine = _make_engine(tmp, data_dir, protocol_dir)
        engine.execute_next_slice()
        new_state = engine.load_state()

        assert new_state["current_slice"] == "SLICE_7b"
        assert "SLICE_10" in new_state["completed_slices"]
