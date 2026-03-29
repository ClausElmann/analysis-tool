"""Tests for ExecutionEngine — SLICE_0 solution structure extraction."""

import json
import os

from core.execution_engine import ExecutionEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(solution_root: str, tmp_path) -> ExecutionEngine:
    protocol_root = str(tmp_path / "protocol")
    data_root = str(tmp_path / "data")
    os.makedirs(protocol_root, exist_ok=True)
    os.makedirs(data_root, exist_ok=True)
    state = {
        "current_slice": "SLICE_0",
        "completed_slices": [],
        "status": "READY",
        "last_run": None,
    }
    with open(os.path.join(protocol_root, "state.json"), "w") as fh:
        json.dump(state, fh)
    return ExecutionEngine(
        solution_root=solution_root,
        protocol_root=protocol_root,
        data_root=data_root,
    )


def _write(path: str, content: str = "") -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _structure(data_root: str) -> dict:
    with open(os.path.join(data_root, "solution_structure.json"), encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Test 1 – Detect multiple projects
# ---------------------------------------------------------------------------

def test_slice_0_detects_multiple_projects(tmp_path):
    sol = str(tmp_path / "solution")
    _write(os.path.join(sol, "FrontendApp", "angular.json"))
    _write(os.path.join(sol, "BackendApi", "BackendApi.csproj"))
    _write(os.path.join(sol, "Database", "schema.sql"))

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    data = _structure(str(tmp_path / "data"))
    names = [p["name"] for p in data["projects"]]
    assert "FrontendApp" in names
    assert "BackendApi" in names
    assert "Database" in names


# ---------------------------------------------------------------------------
# Test 2 – Correct project classification
# ---------------------------------------------------------------------------

def test_slice_0_classifies_angular_project(tmp_path):
    sol = str(tmp_path / "solution")
    _write(os.path.join(sol, "WebApp", "angular.json"))
    _write(os.path.join(sol, "WebApp", "src", "app", "app.component.ts"),
           "@Component({ selector: 'app-root' })\nexport class AppComponent {}")

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    data = _structure(str(tmp_path / "data"))
    webapp = next(p for p in data["projects"] if p["name"] == "WebApp")
    assert webapp["type"] == "angular"


def test_slice_0_classifies_api_project(tmp_path):
    sol = str(tmp_path / "solution")
    _write(os.path.join(sol, "MyApi", "MyApi.csproj"))
    _write(
        os.path.join(sol, "MyApi", "Controllers", "CustomerController.cs"),
        "[HttpGet]\npublic IActionResult Get() {}"
    )

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    data = _structure(str(tmp_path / "data"))
    project = next(p for p in data["projects"] if p["name"] == "MyApi")
    assert project["type"] == "api"


def test_slice_0_classifies_database_project(tmp_path):
    sol = str(tmp_path / "solution")
    _write(os.path.join(sol, "Db", "create_tables.sql"), "CREATE TABLE Orders (Id INT);")

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    data = _structure(str(tmp_path / "data"))
    project = next(p for p in data["projects"] if p["name"] == "Db")
    assert project["type"] == "database"


def test_slice_0_classifies_test_project(tmp_path):
    sol = str(tmp_path / "solution")
    _write(
        os.path.join(sol, "MyApi.Test", "CustomerTests.cs"),
        "[Fact]\npublic void Should_Return_Ok() {}"
    )

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    data = _structure(str(tmp_path / "data"))
    project = next(p for p in data["projects"] if p["name"] == "MyApi.Test")
    assert project["type"] == "test"


# ---------------------------------------------------------------------------
# Test 3 – Unknown projects handled gracefully
# ---------------------------------------------------------------------------

def test_slice_0_handles_unknown_project(tmp_path):
    sol = str(tmp_path / "solution")
    _write(os.path.join(sol, "Misc", "readme.md"), "# README")

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    data = _structure(str(tmp_path / "data"))
    misc = next((p for p in data["projects"] if p["name"] == "Misc"), None)
    assert misc is not None
    assert misc["type"] == "unknown"
    assert isinstance(misc["indicators"], list)


# ---------------------------------------------------------------------------
# Test 4 – Deterministic output (same input → same output)
# ---------------------------------------------------------------------------

def test_slice_0_output_is_deterministic(tmp_path):
    sol = str(tmp_path / "solution")
    _write(os.path.join(sol, "Alpha", "Alpha.csproj"))
    _write(os.path.join(sol, "Beta", "Beta.csproj"))

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    data1 = _structure(str(tmp_path / "data"))

    # Reset state and run again in a fresh engine (same solution, same data_root)
    protocol_root = str(tmp_path / "protocol2")
    data_root2 = str(tmp_path / "data2")
    os.makedirs(protocol_root, exist_ok=True)
    os.makedirs(data_root2, exist_ok=True)
    state = {
        "current_slice": "SLICE_0",
        "completed_slices": [],
        "status": "READY",
        "last_run": None,
    }
    with open(os.path.join(protocol_root, "state.json"), "w") as fh:
        json.dump(state, fh)
    engine2 = ExecutionEngine(
        solution_root=sol,
        protocol_root=protocol_root,
        data_root=data_root2,
    )
    engine2.execute_next_slice()
    data2 = _structure(data_root2)

    assert data1["projects"] == data2["projects"]


# ---------------------------------------------------------------------------
# Test 5 – No nulls in output
# ---------------------------------------------------------------------------

def test_slice_0_no_nulls_in_output(tmp_path):
    sol = str(tmp_path / "solution")
    _write(os.path.join(sol, "Api", "Api.csproj"))
    _write(os.path.join(sol, "Web", "angular.json"))

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    data = _structure(str(tmp_path / "data"))
    for project in data["projects"]:
        for key in ("name", "path", "type"):
            assert project.get(key) is not None, f"Field '{key}' is None in {project}"
            assert isinstance(project[key], str), f"Field '{key}' is not a string"
        assert isinstance(project["indicators"], list)
        for ind in project["indicators"]:
            assert ind is not None and isinstance(ind, str)


# ---------------------------------------------------------------------------
# Test 6 – Angular indicators detected
# ---------------------------------------------------------------------------

def test_slice_0_angular_indicators_detected(tmp_path):
    sol = str(tmp_path / "solution")
    _write(os.path.join(sol, "WebApp", "angular.json"))
    _write(os.path.join(sol, "WebApp", "src", "app", "app-routing.module.ts"),
           "export const routes = [];")
    _write(os.path.join(sol, "WebApp", "src", "app", "dashboard.component.ts"),
           "export class DashboardComponent {}")

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    data = _structure(str(tmp_path / "data"))
    webapp = next(p for p in data["projects"] if p["name"] == "WebApp")
    assert "components" in webapp["indicators"]
    assert "routing_files" in webapp["indicators"]
    assert "angular_json" in webapp["indicators"]


# ---------------------------------------------------------------------------
# Test 7 – State advances to SLICE_1 after SLICE_0
# ---------------------------------------------------------------------------

def test_slice_0_advances_state_to_slice_0_5(tmp_path):
    sol = str(tmp_path / "solution")
    _write(os.path.join(sol, "App", "App.csproj"))

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    state = engine.load_state()
    assert state["current_slice"] == "SLICE_0_5"
    assert "SLICE_0" in state["completed_slices"]


# ---------------------------------------------------------------------------
# Test 8 – Empty solution produces empty projects list
# ---------------------------------------------------------------------------

def test_slice_0_empty_solution_produces_empty_projects(tmp_path):
    sol = str(tmp_path / "solution")
    os.makedirs(sol)

    engine = _make_engine(sol, tmp_path)
    summary = engine.execute_next_slice()

    assert summary["status"] == "OK"
    assert summary["items_found"] == 0
    data = _structure(str(tmp_path / "data"))
    assert data["projects"] == []
