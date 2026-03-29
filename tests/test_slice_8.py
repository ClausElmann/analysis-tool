"""Tests for use_case_generator — SLICE_8 use case generation."""

import json
import os
import tempfile

from core.use_case_generator import (
    generate_use_cases,
    build_selection,
    _api_to_name,
    _route_to_name,
    _component_to_name,
    _make_id,
    _compute_confidence,
    _build_flow_steps,
    _build_systems,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(directory: str, filename: str, data: dict) -> str:
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def _model(modules):
    return {"modules": modules}


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


def _make_engine(solution_root, data_dir, protocol_dir):
    """Build an ExecutionEngine pointed at explicit dirs starting at SLICE_8."""
    from core.execution_engine import ExecutionEngine
    engine = ExecutionEngine(
        solution_root=solution_root,
        protocol_root=protocol_dir,
        data_root=data_dir,
    )
    state = {
        "current_slice": "SLICE_8",
        "completed_slices": [
            "SLICE_0", "SLICE_0_5", "SLICE_0_7", "SLICE_0_8",
            "SLICE_1", "SLICE_2", "SLICE_3", "SLICE_6", "SLICE_7",
        ],
        "status": "READY",
        "last_run": "",
    }
    engine.save_state(state)
    return engine


def _read_json(directory: str, filename: str) -> dict:
    with open(os.path.join(directory, filename), encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Unit tests — name helpers
# ---------------------------------------------------------------------------

def test_api_to_name_simple():
    assert _api_to_name("/api/customers") == "Get customers"


def test_api_to_name_nested():
    name = _api_to_name("/api/customers/search")
    assert "customers" in name.lower()
    assert "search" in name.lower()


def test_api_to_name_camel_case():
    name = _api_to_name("/api/workItems")
    assert "work" in name.lower() or "items" in name.lower()


def test_route_to_name_simple():
    assert _route_to_name("customers") == "Open customers page"


def test_route_to_name_nested():
    name = _route_to_name("admin/settings")
    assert "admin" in name.lower()


def test_component_to_name_strips_suffix():
    name = _component_to_name("CustomerListComponent")
    assert "Component" not in name
    assert "customer" in name.lower()


# ---------------------------------------------------------------------------
# Unit tests — ID generation
# ---------------------------------------------------------------------------

def test_make_id_entry_and_api():
    uc_id = _make_id("customers", "/api/customers")
    assert uc_id == "customers__apicustomers"


def test_make_id_no_api():
    uc_id = _make_id("customers", "")
    assert uc_id == "customers"


def test_make_id_stable_same_input():
    assert _make_id("orders", "/api/orders") == _make_id("orders", "/api/orders")


def test_make_id_strips_special_chars():
    uc_id = _make_id("my-module", "/api/my-module")
    assert "-" not in uc_id


# ---------------------------------------------------------------------------
# Unit tests — confidence scoring
# ---------------------------------------------------------------------------

def test_confidence_route_only():
    c = _compute_confidence(["customers"], [], None, [])
    # route(+30) - no api(-20) = 10 → 0.10
    assert c == 0.10


def test_confidence_route_component_api():
    c = _compute_confidence(["customers"], ["CustomerListComponent"], "/api/customers", [])
    # route(+30) + component(+20) + api(+20) = 70 → 0.70
    assert c == 0.70


def test_confidence_full_chain():
    c = _compute_confidence(["customers"], ["CustomerListComponent"], "/api/customers", ["Customers"])
    # route(+30) + component(+20) + api(+20) + db(+20) = 90 → 0.90
    assert c == 0.90


def test_confidence_no_api_penalty():
    # No route, no component, no api → 0 - 20 = 0 (clamped)
    c = _compute_confidence([], [], None, [])
    assert c == 0.0


def test_confidence_clamped_at_one():
    c = _compute_confidence(["r"], ["C"], "/api/x", ["T"])
    assert c <= 1.0


# ---------------------------------------------------------------------------
# Unit tests — flow steps
# ---------------------------------------------------------------------------

def test_flow_steps_full_chain():
    steps = _build_flow_steps(
        routes=["customers"],
        components=["CustomerListComponent"],
        api_url="/api/customers",
        controllers=["CustomerController"],
        services=["CustomerService"],
        tables=["Customers"],
    )
    assert len(steps) == 6
    assert steps[0] == "User opens customers"
    assert "CustomerListComponent" in steps[1]
    assert "/api/customers" in steps[2]
    assert "CustomerController" in steps[3]
    assert "CustomerService" in steps[4]
    assert "Customers" in steps[5]


def test_flow_steps_missing_api_skipped():
    steps = _build_flow_steps(["customers"], ["CustomerListComponent"], None, [], [], [])
    texts = "".join(steps)
    assert "Calls API" not in texts


def test_flow_steps_missing_table_skipped():
    steps = _build_flow_steps(["customers"], ["CustomerListComponent"], "/api/customers", [], [], [])
    texts = "".join(steps)
    assert "Reads/writes" not in texts


# ---------------------------------------------------------------------------
# Unit tests — systems list
# ---------------------------------------------------------------------------

def test_systems_full():
    assert _build_systems(True, True, True) == ["UI", "API", "DB"]


def test_systems_no_db():
    assert _build_systems(True, True, False) == ["UI", "API"]


def test_systems_api_only():
    assert _build_systems(False, True, False) == ["API"]


# ---------------------------------------------------------------------------
# Integration tests — generate_use_cases
# ---------------------------------------------------------------------------

def test_empty_system_model_produces_empty_use_cases():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([]))
        result = generate_use_cases(tmp)
    assert result["use_cases"] == []


def test_missing_system_model_no_crash():
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_use_cases(tmp)
    assert "use_cases" in result


def test_one_api_produces_one_use_case():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module(
                "customers",
                routes=["customers"],
                components=["CustomerListComponent"],
                apis=["/api/customers"],
                controllers=["CustomerController"],
                services=["CustomerService"],
                tables=["Customers"],
            ),
        ]))
        result = generate_use_cases(tmp)
    assert len(result["use_cases"]) == 1


def test_two_apis_produce_two_use_cases():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module(
                "customers",
                routes=["customers"],
                apis=["/api/customers", "/api/customers/search"],
            ),
        ]))
        result = generate_use_cases(tmp)
    assert len(result["use_cases"]) == 2


def test_no_api_module_produces_one_use_case_from_route():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("customers", routes=["customers"], components=["CustomerListComponent"]),
        ]))
        result = generate_use_cases(tmp)
    assert len(result["use_cases"]) == 1
    uc = result["use_cases"][0]
    assert "customers" in uc["name"].lower() or "Open" in uc["name"]


def test_use_case_has_all_required_fields():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("customers", routes=["customers"], apis=["/api/customers"]),
        ]))
        result = generate_use_cases(tmp)
    uc = result["use_cases"][0]
    assert "id" in uc
    assert "name" in uc
    assert "entry_point" in uc
    assert "flow_steps" in uc
    assert "systems" in uc
    assert "confidence" in uc


def test_id_stable_across_runs():
    with tempfile.TemporaryDirectory() as tmp:
        model = _model([
            _module("customers", routes=["customers"], apis=["/api/customers"]),
        ])
        _write(tmp, "system_model.json", model)
        r1 = generate_use_cases(tmp)
        r2 = generate_use_cases(tmp)
    assert r1["use_cases"][0]["id"] == r2["use_cases"][0]["id"]


def test_use_cases_sorted_by_id():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("zebra", routes=["zebra"], apis=["/api/zebra"]),
            _module("alpha", routes=["alpha"], apis=["/api/alpha"]),
        ]))
        result = generate_use_cases(tmp)
    ids = [uc["id"] for uc in result["use_cases"]]
    assert ids == sorted(ids)


def test_no_nulls_in_output():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("customers", routes=["customers"], apis=["/api/customers"],
                    components=["CustomerListComponent"],
                    controllers=["CustomerController"], services=["CustomerService"],
                    tables=["Customers"]),
        ]))
        result = generate_use_cases(tmp)
    for uc in result["use_cases"]:
        assert uc.get("id") is not None
        assert uc.get("name") is not None
        assert uc.get("entry_point") is not None
        assert isinstance(uc.get("flow_steps"), list)
        assert isinstance(uc.get("systems"), list)
        assert uc.get("confidence") is not None


def test_deterministic_output():
    with tempfile.TemporaryDirectory() as tmp:
        model = _model([
            _module("customers", routes=["customers"], apis=["/api/customers"]),
            _module("orders",    routes=["orders"],    apis=["/api/orders"]),
        ])
        _write(tmp, "system_model.json", model)
        r1 = generate_use_cases(tmp)
        r2 = generate_use_cases(tmp)
    assert r1 == r2


def test_missing_api_use_case_has_no_api_flow_step():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("customers", routes=["customers"], components=["CustomerListComponent"]),
        ]))
        result = generate_use_cases(tmp)
    uc = result["use_cases"][0]
    assert not any("Calls API" in s for s in uc["flow_steps"])


def test_systems_ui_api_db_present_for_full_chain():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("customers",
                    routes=["customers"],
                    apis=["/api/customers"],
                    tables=["Customers"]),
        ]))
        result = generate_use_cases(tmp)
    systems = result["use_cases"][0]["systems"]
    assert "UI" in systems
    assert "API" in systems
    assert "DB" in systems


def test_systems_no_db_when_no_tables():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("customers", routes=["customers"], apis=["/api/customers"]),
        ]))
        result = generate_use_cases(tmp)
    systems = result["use_cases"][0]["systems"]
    assert "DB" not in systems


def test_multiple_modules_multiple_use_cases():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "system_model.json", _model([
            _module("customers", routes=["customers"], apis=["/api/customers"]),
            _module("orders",    routes=["orders"],    apis=["/api/orders"]),
            _module("reports",   routes=["reports"],   apis=["/api/reports"]),
        ]))
        result = generate_use_cases(tmp)
    assert len(result["use_cases"]) == 3


# ---------------------------------------------------------------------------
# Integration tests — build_selection
# ---------------------------------------------------------------------------

def test_build_selection_has_correct_shape():
    analysis = {"use_cases": [
        {"id": "customers__apicustomers", "name": "Get customers",
         "entry_point": "customers", "flow_steps": [], "systems": [], "confidence": 0.7},
    ]}
    sel = build_selection(analysis)
    assert "use_cases" in sel
    uc = sel["use_cases"][0]
    assert uc["id"] == "customers__apicustomers"
    assert uc["name"] == "Get customers"
    assert uc["keep"] is True
    assert uc["reason"] == ""


def test_build_selection_keep_defaults_true():
    analysis = {"use_cases": [
        {"id": "a__b", "name": "X", "entry_point": "a",
         "flow_steps": [], "systems": [], "confidence": 0.5},
        {"id": "c__d", "name": "Y", "entry_point": "c",
         "flow_steps": [], "systems": [], "confidence": 0.5},
    ]}
    sel = build_selection(analysis)
    assert all(uc["keep"] is True for uc in sel["use_cases"])


def test_build_selection_empty_analysis():
    sel = build_selection({"use_cases": []})
    assert sel["use_cases"] == []


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------

def test_slice_8_writes_analysis_file():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir     = os.path.join(tmp, "data")
        protocol_dir = os.path.join(tmp, "protocol")
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(protocol_dir, exist_ok=True)

        _write(data_dir, "system_model.json", _model([
            _module("customers", routes=["customers"], apis=["/api/customers"]),
        ]))
        engine = _make_engine(tmp, data_dir, protocol_dir)
        result = engine.execute_next_slice()

        assert result["slice"] == "SLICE_8"
        assert result["status"] == "OK"
        assert result["items_found"] >= 1
        assert os.path.isfile(os.path.join(data_dir, "use-cases.analysis.json"))


def test_slice_8_writes_selection_file_on_first_run():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir     = os.path.join(tmp, "data")
        protocol_dir = os.path.join(tmp, "protocol")
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(protocol_dir, exist_ok=True)

        _write(data_dir, "system_model.json", _model([
            _module("customers", routes=["customers"], apis=["/api/customers"]),
        ]))
        engine = _make_engine(tmp, data_dir, protocol_dir)
        engine.execute_next_slice()

        assert os.path.isfile(os.path.join(data_dir, "use-cases.selection.json"))
        sel = _read_json(data_dir, "use-cases.selection.json")
        assert "use_cases" in sel
        assert sel["use_cases"][0]["keep"] is True
        sel_path = os.path.join(data_dir, "use-cases.selection.json")

        # Manually mark one use case as keep=False
        with open(sel_path, encoding="utf-8") as fh:
            sel_before = json.load(fh)
        sel_before["use_cases"][0]["keep"] = False
        with open(sel_path, "w", encoding="utf-8") as fh:
            json.dump(sel_before, fh)

        # Re-run SLICE_8 (new engine instance, reset state)
        engine2 = _make_engine(tmp, data_dir, protocol_dir)
        engine2.execute_next_slice()

        with open(sel_path, encoding="utf-8") as fh:
            sel_after = json.load(fh)

        # Manual edit must be preserved
        assert sel_after["use_cases"][0]["keep"] is False


def test_slice_8_advances_state_to_slice_4():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir     = os.path.join(tmp, "data")
        protocol_dir = os.path.join(tmp, "protocol")
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(protocol_dir, exist_ok=True)

        _write(data_dir, "system_model.json", _model([
            _module("customers", routes=["customers"], apis=["/api/customers"]),
        ]))
        engine = _make_engine(tmp, data_dir, protocol_dir)
        engine.execute_next_slice()
        new_state = engine.load_state()

        assert new_state["current_slice"] == "SLICE_10"
        assert "SLICE_8" in new_state["completed_slices"]
