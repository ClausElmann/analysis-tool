"""Tests for ExecutionEngine — SLICE_2 component API extraction and UI coverage."""

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
        "current_slice": "SLICE_2",
        "completed_slices": ["SLICE_1"],
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


def _write(path: str, content: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _write_entries(data_root: str, entry_points: list) -> None:
    os.makedirs(data_root, exist_ok=True)
    with open(os.path.join(data_root, "angular_entries.json"), "w") as fh:
        json.dump({"entry_points": entry_points}, fh)


def _write_observed(data_root: str, menus: list) -> None:
    os.makedirs(data_root, exist_ok=True)
    with open(os.path.join(data_root, "ui_observed_structure.json"), "w") as fh:
        json.dump({"menus": menus}, fh)


def _ep(route_path: str, component: str, source_file: str) -> dict:
    """Build a minimal entry_point dict with deterministic id."""
    import re
    safe = re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", route_path.lower())).strip("_")
    ep_id = f"route_{safe}" if safe else "route_wildcard"
    return {
        "id": ep_id,
        "type": "route",
        "path": route_path,
        "component": component,
        "parent": "",
        "depth": 0,
        "source_file": source_file,
    }


def _api_map(data_root: str) -> dict:
    with open(os.path.join(data_root, "component_api_map.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _coverage(data_root: str) -> dict:
    with open(os.path.join(data_root, "ui_coverage_report.json"), encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Test 1 – API in ngOnInit → trigger = "init"
# ---------------------------------------------------------------------------

def test_slice_2_ngoninit_trigger_is_init(tmp_path):
    sol = str(tmp_path / "solution")
    os.makedirs(sol)
    comp_file = _write(
        os.path.join(sol, "customer-list.component.ts"),
        """
@Component({ selector: 'app-customer-list', template: '' })
export class CustomerListComponent {
  constructor(private http: HttpClient) {}
  ngOnInit() {
    this.http.get('/api/customers');
  }
}
""",
    )
    engine = _make_engine(sol, tmp_path)
    _write_entries(str(tmp_path / "data"), [_ep("customers", "CustomerListComponent", comp_file)])
    engine.execute_next_slice()

    data = _api_map(str(tmp_path / "data"))
    assert len(data["mappings"]) == 1
    api = data["mappings"][0]["apis"][0]
    assert api["method"] == "GET"
    assert api["url"] == "/api/customers"
    assert api["trigger"] == "init"
    assert api["source"] == "component"


# ---------------------------------------------------------------------------
# Test 2 – API in (click) handler → trigger = "click"
# ---------------------------------------------------------------------------

def test_slice_2_click_handler_trigger_is_click(tmp_path):
    sol = str(tmp_path / "solution")
    os.makedirs(sol)
    comp_file = _write(
        os.path.join(sol, "order-list.component.ts"),
        """
@Component({
  selector: 'app-order-list',
  template: `<button (click)="loadOrders()">Load</button>`
})
export class OrderListComponent {
  constructor(private http: HttpClient) {}
  loadOrders() {
    this.http.get('/api/orders');
  }
}
""",
    )
    engine = _make_engine(sol, tmp_path)
    _write_entries(str(tmp_path / "data"), [_ep("orders", "OrderListComponent", comp_file)])
    engine.execute_next_slice()

    data = _api_map(str(tmp_path / "data"))
    api = data["mappings"][0]["apis"][0]
    assert api["trigger"] == "click"
    assert api["url"] == "/api/orders"
    assert api["source"] == "component"


# ---------------------------------------------------------------------------
# Test 3 – Service call resolved one level
# ---------------------------------------------------------------------------

def test_slice_2_service_call_resolved(tmp_path):
    sol = str(tmp_path / "solution")
    os.makedirs(sol)
    _write(
        os.path.join(sol, "product.service.ts"),
        """
export class ProductService {
  constructor(private http: HttpClient) {}
  getAll() {
    this.http.get('/api/products');
  }
}
""",
    )
    comp_file = _write(
        os.path.join(sol, "product.component.ts"),
        """
@Component({ selector: 'app-product', template: '' })
export class ProductComponent {
  constructor(private productService: ProductService) {}
  ngOnInit() {
    this.productService.getAll();
  }
}
""",
    )
    engine = _make_engine(sol, tmp_path)
    _write_entries(str(tmp_path / "data"), [_ep("products", "ProductComponent", comp_file)])
    engine.execute_next_slice()

    data = _api_map(str(tmp_path / "data"))
    assert len(data["mappings"]) == 1
    api = data["mappings"][0]["apis"][0]
    assert api["url"] == "/api/products"
    assert api["source"] == "service"
    assert api["trigger"] == "init"


# ---------------------------------------------------------------------------
# Test 4 – Multiple APIs per component (init + click)
# ---------------------------------------------------------------------------

def test_slice_2_multiple_apis_per_component(tmp_path):
    sol = str(tmp_path / "solution")
    os.makedirs(sol)
    comp_file = _write(
        os.path.join(sol, "dashboard.component.ts"),
        """
@Component({
  selector: 'app-dashboard',
  template: `<button (click)="create()">New</button>`
})
export class DashboardComponent {
  constructor(private http: HttpClient) {}
  ngOnInit() {
    this.http.get('/api/stats');
  }
  create() {
    this.http.post('/api/items', {});
  }
}
""",
    )
    engine = _make_engine(sol, tmp_path)
    _write_entries(str(tmp_path / "data"), [_ep("dashboard", "DashboardComponent", comp_file)])
    engine.execute_next_slice()

    data = _api_map(str(tmp_path / "data"))
    apis = data["mappings"][0]["apis"]
    assert len(apis) == 2
    methods = {a["method"] for a in apis}
    assert methods == {"GET", "POST"}
    triggers = {a["trigger"] for a in apis}
    assert triggers == {"init", "click"}


# ---------------------------------------------------------------------------
# Test 5 – Component with no API → skipped from mappings
# ---------------------------------------------------------------------------

def test_slice_2_component_with_no_api_is_skipped(tmp_path):
    sol = str(tmp_path / "solution")
    os.makedirs(sol)
    comp_file = _write(
        os.path.join(sol, "profile.component.ts"),
        """
@Component({ selector: 'app-profile', template: '' })
export class ProfileComponent {
  ngOnInit() {
    console.log('no http here');
  }
}
""",
    )
    engine = _make_engine(sol, tmp_path)
    _write_entries(str(tmp_path / "data"), [_ep("profile", "ProfileComponent", comp_file)])
    summary = engine.execute_next_slice()

    assert summary["items_found"] == 0
    data = _api_map(str(tmp_path / "data"))
    assert data["mappings"] == []


# ---------------------------------------------------------------------------
# Test 6 – Route exists but no API → coverage = "no_api_detected"
# ---------------------------------------------------------------------------

def test_slice_2_coverage_no_api_detected(tmp_path):
    sol = str(tmp_path / "solution")
    os.makedirs(sol)
    comp_file = _write(
        os.path.join(sol, "orders.component.ts"),
        """
@Component({ selector: 'app-orders', template: '' })
export class OrdersComponent {
  ngOnInit() { console.log('orders'); }
}
""",
    )
    data_root = str(tmp_path / "data")
    _write_entries(data_root, [_ep("orders", "OrdersComponent", comp_file)])
    _write_observed(data_root, [{"name": "Orders", "route": "orders", "observed_features": []}])

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    report = _coverage(data_root)
    assert len(report["menus"]) == 1
    assert report["menus"][0]["coverage_status"] == "no_api_detected"


# ---------------------------------------------------------------------------
# Test 7 – Route missing entirely → coverage = "missing_route"
# ---------------------------------------------------------------------------

def test_slice_2_coverage_missing_route(tmp_path):
    sol = str(tmp_path / "solution")
    os.makedirs(sol)
    data_root = str(tmp_path / "data")
    # angular_entries has only "customers", observed has "settings"
    _write_entries(data_root, [])
    _write_observed(data_root, [{"name": "Settings", "route": "settings", "observed_features": []}])

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    report = _coverage(data_root)
    assert report["menus"][0]["coverage_status"] == "missing_route"


# ---------------------------------------------------------------------------
# Test 8 – Feature not found → appears in missing_features
# ---------------------------------------------------------------------------

def test_slice_2_coverage_feature_not_found_is_missing(tmp_path):
    sol = str(tmp_path / "solution")
    os.makedirs(sol)
    comp_file = _write(
        os.path.join(sol, "customer-list.component.ts"),
        """
@Component({ selector: 'app-customer-list', template: '' })
export class CustomerListComponent {
  constructor(private http: HttpClient) {}
  ngOnInit() {
    this.http.get('/api/customers');
  }
}
""",
    )
    data_root = str(tmp_path / "data")
    _write_entries(data_root, [_ep("customers", "CustomerListComponent", comp_file)])
    _write_observed(
        data_root,
        [{"name": "Customers", "route": "customers", "observed_features": ["export", "customers"]}],
    )

    engine = _make_engine(sol, tmp_path)
    engine.execute_next_slice()

    report = _coverage(data_root)
    menu = report["menus"][0]
    assert menu["coverage_status"] == "covered"
    assert "export" in menu["missing_features"]
    assert "customers" not in menu["missing_features"]  # "customers" is in the URL


# ---------------------------------------------------------------------------
# Test 9 – ngOnInit API includes method_name = "ngOnInit"
# ---------------------------------------------------------------------------

def test_slice_2_ngoninit_api_has_method_name(tmp_path):
    sol = str(tmp_path / "solution")
    os.makedirs(sol)
    comp_file = _write(
        os.path.join(sol, "report.component.ts"),
        """
@Component({ selector: 'app-report', template: '' })
export class ReportComponent {
  constructor(private http: HttpClient) {}
  ngOnInit() {
    this.http.get('/api/reports');
  }
}
""",
    )
    engine = _make_engine(sol, tmp_path)
    _write_entries(str(tmp_path / "data"), [_ep("reports", "ReportComponent", comp_file)])
    engine.execute_next_slice()

    data = _api_map(str(tmp_path / "data"))
    api = data["mappings"][0]["apis"][0]
    assert api["method_name"] == "ngOnInit"


# ---------------------------------------------------------------------------
# Test 10 – (click) handler API includes method_name = handler function name
# ---------------------------------------------------------------------------

def test_slice_2_click_handler_api_has_method_name(tmp_path):
    sol = str(tmp_path / "solution")
    os.makedirs(sol)
    comp_file = _write(
        os.path.join(sol, "invoice.component.ts"),
        """
@Component({
  selector: 'app-invoice',
  template: `<button (click)="submitInvoice()">Submit</button>`
})
export class InvoiceComponent {
  constructor(private http: HttpClient) {}
  submitInvoice() {
    this.http.post('/api/invoices', {});
  }
}
""",
    )
    engine = _make_engine(sol, tmp_path)
    _write_entries(str(tmp_path / "data"), [_ep("invoices", "InvoiceComponent", comp_file)])
    engine.execute_next_slice()

    data = _api_map(str(tmp_path / "data"))
    api = data["mappings"][0]["apis"][0]
    assert api["method_name"] == "submitInvoice"
