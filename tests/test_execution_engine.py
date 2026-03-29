"""Tests for ExecutionEngine — SLICE_1 Angular route entry detection."""

import json
import os
import tempfile

import pytest

from core.execution_engine import ExecutionEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(solution_root: str, tmp_path) -> ExecutionEngine:
    protocol_root = str(tmp_path / "protocol")
    data_root = str(tmp_path / "data")
    os.makedirs(protocol_root, exist_ok=True)
    state = {
        "current_slice": "SLICE_1",
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


def _write_ts_file(directory: str, filename: str, content: str) -> str:
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# load_state / save_state
# ---------------------------------------------------------------------------

def test_load_state_returns_dict(tmp_path):
    engine = _make_engine(str(tmp_path), tmp_path)
    state = engine.load_state()
    assert state["current_slice"] == "SLICE_1"
    assert state["completed_slices"] == []
    assert state["status"] == "READY"
    assert state["last_run"] is None


def test_save_state_persists(tmp_path):
    engine = _make_engine(str(tmp_path), tmp_path)
    new_state = {
        "current_slice": "SLICE_2",
        "completed_slices": ["SLICE_1"],
        "status": "READY",
        "last_run": "2026-03-29T12:00:00+00:00",
    }
    engine.save_state(new_state)
    reloaded = engine.load_state()
    assert reloaded["current_slice"] == "SLICE_2"
    assert reloaded["completed_slices"] == ["SLICE_1"]


# ---------------------------------------------------------------------------
# SLICE_1 — output file and entry_points structure
# ---------------------------------------------------------------------------

def test_slice_1_writes_angular_entries_json(tmp_path):
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    _write_ts_file(
        solution_dir,
        "app-routing.module.ts",
        "export const ROUTES = [{ path: 'home', component: HomeComponent }];",
    )
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    output_file = os.path.join(str(tmp_path / "data"), "angular_entries.json")
    assert os.path.isfile(output_file), "angular_entries.json was not written"
    with open(output_file, encoding="utf-8") as fh:
        data = json.load(fh)
    assert "entry_points" in data


def test_slice_1_only_includes_routes(tmp_path):
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    _write_ts_file(
        solution_dir,
        "app-routing.module.ts",
        "export const ROUTES = [{ path: 'customers', component: CustomerListComponent }];",
    )
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    output_file = os.path.join(str(tmp_path / "data"), "angular_entries.json")
    with open(output_file, encoding="utf-8") as fh:
        data = json.load(fh)

    entry_points = data["entry_points"]
    assert len(entry_points) == 1
    ep = entry_points[0]
    assert ep["id"] == "route_customers"
    assert ep["type"] == "route"
    assert ep["path"] == "customers"
    assert ep["component"] == "CustomerListComponent"
    assert ep["source_file"].endswith("app-routing.module.ts")
    assert ep["parent"] == ""


def test_slice_1_excludes_shared_components(tmp_path):
    """A .component.ts file without any routing declaration must be excluded."""
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    _write_ts_file(
        solution_dir,
        "dashboard.component.ts",
        """
@Component({ selector: 'app-dashboard' })
export class DashboardComponent {}
""",
    )
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    output_file = os.path.join(str(tmp_path / "data"), "angular_entries.json")
    with open(output_file, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["entry_points"] == []


def test_slice_1_deterministic_output(tmp_path):
    """Entry points must be sorted by id regardless of declaration order."""
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    # Declare routes in reverse alphabetical order
    _write_ts_file(
        solution_dir,
        "app-routing.module.ts",
        """
export const ROUTES = [
  { path: 'zebra', component: ZebraComponent },
  { path: 'alpha', component: AlphaComponent },
  { path: 'mango', component: MangoComponent },
];
""",
    )
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    output_file = os.path.join(str(tmp_path / "data"), "angular_entries.json")
    with open(output_file, encoding="utf-8") as fh:
        data = json.load(fh)

    ids = [ep["id"] for ep in data["entry_points"]]
    assert ids == sorted(ids), f"Entry points are not sorted: {ids}"


def test_slice_1_no_duplicates(tmp_path):
    """The same route path declared twice must produce exactly one entry."""
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    _write_ts_file(
        solution_dir,
        "app.routes.ts",
        """
export const ROUTES = [
  { path: 'orders', component: OrdersComponent },
  { path: 'orders', component: OrdersComponent },
];
""",
    )
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    output_file = os.path.join(str(tmp_path / "data"), "angular_entries.json")
    with open(output_file, encoding="utf-8") as fh:
        data = json.load(fh)
    assert len(data["entry_points"]) == 1


def test_slice_1_entry_has_no_nulls(tmp_path):
    """All fields in every entry_point must be non-null strings."""
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    _write_ts_file(
        solution_dir,
        "app-routing.module.ts",
        "export const ROUTES = [{ path: 'profile', component: ProfileComponent }];",
    )
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    output_file = os.path.join(str(tmp_path / "data"), "angular_entries.json")
    with open(output_file, encoding="utf-8") as fh:
        data = json.load(fh)

    for ep in data["entry_points"]:
        for key in ("id", "type", "path", "component", "parent", "source_file"):
            assert ep.get(key) is not None, f"Field '{key}' is None in {ep}"
            assert isinstance(ep[key], str), f"Field '{key}' is not a string in {ep}"
        assert isinstance(ep.get("depth"), int), f"Field 'depth' is not an int in {ep}"


def test_slice_1_skips_non_routing_files(tmp_path):
    """A plain .ts file that is not a routing file must be ignored."""
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    _write_ts_file(solution_dir, "service.cs", "public class MyService {}")
    _write_ts_file(solution_dir, "shared.service.ts", "export class SharedService {}")
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    output_file = os.path.join(str(tmp_path / "data"), "angular_entries.json")
    with open(output_file, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["entry_points"] == []


# ---------------------------------------------------------------------------
# SLICE_1 — nested routes, empty path, lazy module
# ---------------------------------------------------------------------------

def test_slice_1_nested_routes(tmp_path):
    """Child routes get the fully combined path and the parent's id in 'parent'."""
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    _write_ts_file(
        solution_dir,
        "app-routing.module.ts",
        """
export const ROUTES = [
  {
    path: 'customers',
    component: CustomerListComponent,
    children: [
      { path: 'details/:id', component: CustomerDetailComponent }
    ]
  }
];
""",
    )
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    output_file = os.path.join(str(tmp_path / "data"), "angular_entries.json")
    with open(output_file, encoding="utf-8") as fh:
        data = json.load(fh)

    entry_points = data["entry_points"]
    assert len(entry_points) == 2

    parent = next(ep for ep in entry_points if ep["path"] == "customers")
    assert parent["id"] == "route_customers"
    assert parent["parent"] == ""
    assert parent["component"] == "CustomerListComponent"
    assert parent["depth"] == 0

    child = next(ep for ep in entry_points if "details" in ep["path"])
    assert child["path"] == "customers/details/:id"
    assert child["id"] == "route_customers_details_id"
    assert child["parent"] == "route_customers"
    assert child["component"] == "CustomerDetailComponent"
    assert child["depth"] == 1


def test_slice_1_empty_path_generates_id_from_component(tmp_path):
    """A route with path='' uses the component name to build the id."""
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    _write_ts_file(
        solution_dir,
        "app-routing.module.ts",
        "export const ROUTES = [{ path: '', component: DashboardComponent }];",
    )
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    output_file = os.path.join(str(tmp_path / "data"), "angular_entries.json")
    with open(output_file, encoding="utf-8") as fh:
        data = json.load(fh)

    entry_points = data["entry_points"]
    assert len(entry_points) == 1
    ep = entry_points[0]
    assert ep["id"] == "route_root_dashboard"
    assert ep["path"] == ""
    assert ep["component"] == "DashboardComponent"
    assert ep["parent"] == ""
    assert ep["depth"] == 0


def test_slice_1_lazy_module_entry(tmp_path):
    """A loadChildren route has type 'lazy-module' and a derived component name."""
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    _write_ts_file(
        solution_dir,
        "app.routes.ts",
        """
export const ROUTES = [
  {
    path: 'admin',
    loadChildren: () => import('./admin/admin.module').then(m => m.AdminModule)
  }
];
""",
    )
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    output_file = os.path.join(str(tmp_path / "data"), "angular_entries.json")
    with open(output_file, encoding="utf-8") as fh:
        data = json.load(fh)

    entry_points = data["entry_points"]
    assert len(entry_points) == 1
    ep = entry_points[0]
    assert ep["id"] == "route_admin"
    assert ep["type"] == "lazy-module"
    assert ep["path"] == "admin"
    assert ep["component"] == "AdminModule"
    assert ep["parent"] == ""


def test_slice_1_path_normalization(tmp_path):
    """Paths with duplicate slashes, whitespace, or trailing slash must be normalized."""
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    _write_ts_file(
        solution_dir,
        "app-routing.module.ts",
        """
export const ROUTES = [
  { path: 'customers/', component: CustomersComponent },
  { path: '  orders  ', component: OrdersComponent },
];
""",
    )
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    output_file = os.path.join(str(tmp_path / "data"), "angular_entries.json")
    with open(output_file, encoding="utf-8") as fh:
        data = json.load(fh)

    paths = {ep["path"] for ep in data["entry_points"]}
    assert "customers" in paths, "Trailing slash not removed"
    assert "orders" in paths, "Whitespace not stripped"


def test_slice_1_empty_solution_produces_empty_entry_points(tmp_path):
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    engine = _make_engine(solution_dir, tmp_path)
    summary = engine.execute_next_slice()
    assert summary["status"] == "OK"
    assert summary["items_found"] == 0


# ---------------------------------------------------------------------------
# State advance after SLICE_1
# ---------------------------------------------------------------------------

def test_slice_1_advances_state_to_slice_2(tmp_path):
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    state = engine.load_state()
    assert state["current_slice"] == "SLICE_1b"
    assert "SLICE_1" in state["completed_slices"]
    assert state["status"] == "READY"
    assert state["last_run"] is not None


def test_slice_1_does_not_duplicate_in_completed(tmp_path):
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()
    state = engine.load_state()
    assert state["completed_slices"].count("SLICE_1") == 1


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def test_slice_1_writes_log_file(tmp_path):
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    logs_dir = os.path.join(str(tmp_path / "protocol"), "logs")
    log_files = [f for f in os.listdir(logs_dir) if f.endswith(".md")]
    assert len(log_files) == 1


def test_log_file_contains_slice_name(tmp_path):
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    engine = _make_engine(solution_dir, tmp_path)
    engine.execute_next_slice()

    logs_dir = os.path.join(str(tmp_path / "protocol"), "logs")
    log_file = next(
        f for f in os.listdir(logs_dir) if f.endswith(".md")
    )
    with open(os.path.join(logs_dir, log_file), encoding="utf-8") as fh:
        content = fh.read()
    assert "SLICE_1" in content


# ---------------------------------------------------------------------------
# Unknown slice
# ---------------------------------------------------------------------------

def test_unknown_slice_is_skipped(tmp_path):
    solution_dir = str(tmp_path / "solution")
    os.makedirs(solution_dir)
    engine = _make_engine(solution_dir, tmp_path)
    # Manually set an unknown slice
    state = engine.load_state()
    state["current_slice"] = "SLICE_99"
    engine.save_state(state)

    summary = engine.execute_next_slice()
    assert summary["status"] == "SKIPPED"


