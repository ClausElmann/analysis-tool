"""Tests for system_fusion — SLICE_7 system model fusion."""

import json
import os
import tempfile

import pytest

from core.system_fusion import (
    fuse_system,
    _route_to_module_name,
    _component_to_module_name,
    _name_overlaps,
    _compute_confidence,
)


# ---------------------------------------------------------------------------
# Helpers: write JSON fixture files
# ---------------------------------------------------------------------------

def _write(directory: str, filename: str, data: dict) -> str:
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def _angular(entries):
    return {"entries": entries}


def _api_map(mappings):
    return {"mappings": mappings}


def _db_map(mappings):
    return {"mappings": mappings}


def _work_items(capabilities=None, features=None):
    return {"capabilities": capabilities or [], "features": features or []}


def _wiki(capabilities=None):
    return {"capabilities": capabilities or []}


def _pdf(capabilities=None):
    return {"capabilities": capabilities or []}


def _git(insights=None):
    return {"insights": insights or []}


# Minimal angular entry
def _ae(entry_id, route, component):
    return {"entry_id": entry_id, "route": route, "component": component}


# Minimal api_map mapping
def _am(entry_id, component, urls):
    return {
        "entry_id": entry_id,
        "component": component,
        "apis": [{"url": u, "method": "GET"} for u in urls],
    }


# Minimal db_map mapping
def _dm(api_url, controller, service, tables):
    return {
        "api_url": api_url,
        "controller": controller,
        "service": service,
        "sql": {"tables": tables, "joins": [], "where_conditions": []},
    }


# ---------------------------------------------------------------------------
# Unit tests: helpers
# ---------------------------------------------------------------------------

def test_route_to_module_name_simple():
    assert _route_to_module_name("customers") == "customers"


def test_route_to_module_name_nested():
    assert _route_to_module_name("customers/details") == "customers"


def test_route_to_module_name_leading_slash():
    assert _route_to_module_name("/customers/details") == "customers"


def test_route_to_module_name_empty():
    assert _route_to_module_name("") == ""


def test_component_to_module_name_strips_suffix():
    assert _component_to_module_name("CustomerListComponent") == "customer"


def test_component_to_module_name_module_suffix():
    assert _component_to_module_name("BatchModule") == "batch"


def test_component_to_module_name_plain():
    # No known suffix — lowercased first token after CamelCase split
    assert _component_to_module_name("SmsService") == "sms"


def test_name_overlaps_exact():
    assert _name_overlaps("customer", "customer management rules") is True


def test_name_overlaps_token():
    assert _name_overlaps("sms", "send sms message") is True


def test_name_overlaps_no_match():
    assert _name_overlaps("invoice", "customer management") is False


def test_name_overlaps_empty_module():
    assert _name_overlaps("", "customer") is False


# ---------------------------------------------------------------------------
# Unit tests: _compute_confidence
# ---------------------------------------------------------------------------

def _dummy_module(**kwargs) -> dict:
    base = {
        "routes": [], "apis": [], "tables": [],
        "features": [], "signals": [],
        "components": [], "controllers": [], "services": [],
    }
    base.update(kwargs)
    return base


def test_confidence_zero():
    mod = _dummy_module()
    assert _compute_confidence(mod) == 0.0


def test_confidence_route_only():
    mod = _dummy_module(routes=["/customers"])
    assert _compute_confidence(mod) == 0.20


def test_confidence_route_api():
    mod = _dummy_module(routes=["/customers"], apis=["/api/customers"])
    assert _compute_confidence(mod) == 0.40


def test_confidence_full_chain():
    mod = _dummy_module(
        routes=["/customers"],
        apis=["/api/customers"],
        tables=["Customers"],
        features=["Create customer"],
        signals=["Opret kunde", "git:create customer record"],
    )
    assert _compute_confidence(mod) == 1.00


def test_confidence_clamped_at_one():
    mod = _dummy_module(
        routes=["/x"], apis=["/a"], tables=["T"],
        features=["F"], signals=["wiki_sig", "git:sig"],
    )
    c = _compute_confidence(mod)
    assert 0.0 <= c <= 1.0


def test_confidence_git_only_signals():
    mod = _dummy_module(signals=["git:fix crash"])
    assert _compute_confidence(mod) == 0.10


def test_confidence_non_git_signals_only():
    mod = _dummy_module(signals=["some wiki signal"])
    assert _compute_confidence(mod) == 0.10


# ---------------------------------------------------------------------------
# Integration tests: fuse_system
# ---------------------------------------------------------------------------

def test_empty_inputs_return_empty_modules():
    with tempfile.TemporaryDirectory() as tmp:
        result = fuse_system(tmp)
    assert result["modules"] == []


def test_missing_files_no_crash():
    with tempfile.TemporaryDirectory() as tmp:
        # Write only one file; others missing
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_customers", "customers", "CustomerListComponent"),
        ]))
        result = fuse_system(tmp)
    # Should produce a module (has route) without crashing
    assert isinstance(result["modules"], list)


def test_simple_full_chain_route_api_db():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_customers", "customers", "CustomerListComponent"),
        ]))
        _write(tmp, "component_api_map.json", _api_map([
            _am("r_customers", "CustomerListComponent", ["/api/customers"]),
        ]))
        _write(tmp, "api_db_map.json", _db_map([
            _dm("/api/customers", "CustomerController", "CustomerService", ["Customers"]),
        ]))

        result = fuse_system(tmp)

    mods = result["modules"]
    assert len(mods) == 1
    m = mods[0]
    assert m["name"] == "customers"
    assert "customers" in m["routes"]
    assert "/api/customers" in m["apis"]
    assert "CustomerController" in m["controllers"]
    assert "CustomerService" in m["services"]
    assert "Customers" in m["tables"]


def test_missing_api_still_creates_module():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_customers", "customers", "CustomerListComponent"),
        ]))
        # No component_api_map, no api_db_map
        result = fuse_system(tmp)

    mods = result["modules"]
    assert any(m["name"] == "customers" for m in mods)
    m = next(m for m in mods if m["name"] == "customers")
    assert m["apis"] == []
    assert m["tables"] == []


def test_missing_db_still_creates_module():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_orders", "orders", "OrderListComponent"),
        ]))
        _write(tmp, "component_api_map.json", _api_map([
            _am("r_orders", "OrderListComponent", ["/api/orders"]),
        ]))
        # No api_db_map
        result = fuse_system(tmp)

    mods = result["modules"]
    m = next(m for m in mods if m["name"] == "orders")
    assert "/api/orders" in m["apis"]
    assert m["tables"] == []


def test_feature_matching_by_capability():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_customers", "customers", "CustomerListComponent"),
        ]))
        _write(tmp, "work_item_analysis.json", _work_items(
            capabilities=[{
                "name": "sms_service_customers",
                "area": "SMS-service\\Customers",
                "keywords": ["customer", "create", "update"],
                "item_count": 10,
            }],
            features=[{
                "id": "1001",
                "title": "Create customer profile",
                "capability": "sms_service_customers",
                "keywords": ["customer", "create", "profile"],
            }],
        ))
        result = fuse_system(tmp)

    mods = result["modules"]
    m = next((m for m in mods if m["name"] == "customers"), None)
    assert m is not None
    assert "Create customer profile" in m["features"]


def test_feature_matching_by_keyword_overlap():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_batch", "batch", "BatchListComponent"),
        ]))
        _write(tmp, "work_item_analysis.json", _work_items(
            features=[{
                "id": "2001",
                "title": "Schedule batch import",
                "capability": "unrelated_area",
                "keywords": ["batch", "schedule", "import"],
            }],
        ))
        result = fuse_system(tmp)

    mods = result["modules"]
    m = next((m for m in mods if m["name"] == "batch"), None)
    assert m is not None
    assert "Schedule batch import" in m["features"]


def test_wiki_signals_attached():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_batch", "batch", "BatchListComponent"),
        ]))
        _write(tmp, "wiki_signals.json", _wiki(capabilities=[{
            "name": "Batch opgaver",
            "source": "wiki",
            "file": "Batch.md",
            "signals": ["Import af data", "Batch kørsel"],
        }]))
        result = fuse_system(tmp)

    mods = result["modules"]
    m = next((m for m in mods if m["name"] == "batch"), None)
    assert m is not None
    assert any("Import" in s or "Batch" in s for s in m["signals"])


def test_pdf_signals_attached():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_customers", "customers", "CustomerListComponent"),
        ]))
        _write(tmp, "pdf_capabilities.json", _pdf(capabilities=[{
            "name": "Kundehåndtering",
            "source": "pdf",
            "file": "manual.pdf",
            "features": ["Opret kunde", "Slet customer"],
            "operations": [],
        }]))
        result = fuse_system(tmp)

    mods = result["modules"]
    m = next((m for m in mods if m["name"] == "customers"), None)
    assert m is not None
    # "customer" overlaps with "Slet customer"
    assert any("customer" in s.lower() or "kunde" in s.lower() for s in m["signals"])


def test_git_signals_attached():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_customers", "customers", "CustomerListComponent"),
        ]))
        _write(tmp, "git_insights.json", _git(insights=[
            {"id": "git_0001", "type": "rule", "text": "prevent duplicate customer records",
             "confidence": 0.9, "files": []},
        ]))
        result = fuse_system(tmp)

    mods = result["modules"]
    m = next((m for m in mods if m["name"] == "customers"), None)
    assert m is not None
    assert any("customer" in s for s in m["signals"])


def test_git_signals_prefixed_with_git():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_batch", "batch", "BatchListComponent"),
        ]))
        _write(tmp, "git_insights.json", _git(insights=[
            {"id": "git_0001", "type": "feature", "text": "create batch scheduler",
             "confidence": 0.8, "files": []},
        ]))
        result = fuse_system(tmp)

    mods = result["modules"]
    m = next((m for m in mods if m["name"] == "batch"), None)
    assert m is not None
    assert any(s.startswith("git:") for s in m["signals"])


def test_all_arrays_sorted():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_customers", "customers", "CustomerListComponent"),
        ]))
        _write(tmp, "component_api_map.json", _api_map([
            _am("r_customers", "CustomerListComponent", ["/api/cz", "/api/aa", "/api/mm"]),
        ]))
        result = fuse_system(tmp)

    m = result["modules"][0]
    assert m["apis"] == sorted(m["apis"])
    assert m["routes"] == sorted(m["routes"])
    assert m["features"] == sorted(m["features"])
    assert m["signals"] == sorted(m["signals"])


def test_no_nulls_in_output():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_customers", "customers", "CustomerListComponent"),
        ]))
        _write(tmp, "component_api_map.json", _api_map([
            _am("r_customers", "CustomerListComponent", ["/api/customers"]),
        ]))
        result = fuse_system(tmp)

    for m in result["modules"]:
        assert m.get("name") is not None
        assert isinstance(m.get("routes"), list)
        assert isinstance(m.get("apis"), list)
        assert isinstance(m.get("tables"), list)
        assert isinstance(m.get("features"), list)
        assert isinstance(m.get("signals"), list)
        assert m.get("confidence") is not None


def test_modules_sorted_by_name():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_z", "zebra", "ZebraComponent"),
            _ae("r_a", "alpha", "AlphaComponent"),
            _ae("r_m", "management", "ManagementComponent"),
        ]))
        _write(tmp, "component_api_map.json", _api_map([
            _am("r_z", "ZebraComponent",      ["/api/zebra"]),
            _am("r_a", "AlphaComponent",      ["/api/alpha"]),
            _am("r_m", "ManagementComponent", ["/api/management"]),
        ]))
        result = fuse_system(tmp)

    names = [m["name"] for m in result["modules"]]
    assert names == sorted(names)


def test_filter_removes_modules_with_no_route_api_feature():
    """Modules that have no routes, no apis, and no features must be dropped."""
    with tempfile.TemporaryDirectory() as tmp:
        # Work item that references "phantom" — no angular entry for it
        _write(tmp, "work_item_analysis.json", _work_items(
            features=[{
                "id": "9001",
                "title": "phantom feature",
                "capability": "phantom",
                "keywords": ["phantom"],
            }],
        ))
        result = fuse_system(tmp)

    # "phantom" module candidate has no route/api — must be filtered
    names = [m["name"] for m in result["modules"]]
    assert "phantom" not in names


def test_deterministic_output():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_customers", "customers", "CustomerListComponent"),
            _ae("r_orders", "orders", "OrderListComponent"),
        ]))
        _write(tmp, "component_api_map.json", _api_map([
            _am("r_customers", "CustomerListComponent", ["/api/customers"]),
            _am("r_orders", "OrderListComponent", ["/api/orders"]),
        ]))
        _write(tmp, "api_db_map.json", _db_map([
            _dm("/api/customers", "CustomerController", "CustomerService", ["Customers"]),
            _dm("/api/orders", "OrderController", "OrderService", ["Orders"]),
        ]))
        _write(tmp, "work_item_analysis.json", _work_items(
            features=[
                {"id": "1", "title": "Create customer", "capability": "x", "keywords": ["customer"]},
                {"id": "2", "title": "List orders", "capability": "x", "keywords": ["orders"]},
            ],
        ))
        r1 = fuse_system(tmp)
        r2 = fuse_system(tmp)

    assert r1["modules"] == r2["modules"]


def test_confidence_calculation_correct():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_customers", "customers", "CustomerListComponent"),
        ]))
        _write(tmp, "component_api_map.json", _api_map([
            _am("r_customers", "CustomerListComponent", ["/api/customers"]),
        ]))
        _write(tmp, "api_db_map.json", _db_map([
            _dm("/api/customers", "CustomerController", "CustomerService", ["Customers"]),
        ]))
        _write(tmp, "work_item_analysis.json", _work_items(
            features=[{
                "id": "1", "title": "Create customer",
                "capability": "x", "keywords": ["customer"],
            }],
        ))
        result = fuse_system(tmp)

    m = next(m for m in result["modules"] if m["name"] == "customers")
    # route(+20) + api(+20) + tables(+20) + features(+20) = 80 → 0.80
    assert m["confidence"] == 0.80


def test_duplicate_entries_deduplicated():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, "angular_entries.json", _angular([
            _ae("r_customers", "customers", "CustomerListComponent"),
        ]))
        # Same URL twice in api_map
        _write(tmp, "component_api_map.json", {"mappings": [
            {
                "entry_id": "r_customers",
                "component": "CustomerListComponent",
                "apis": [
                    {"url": "/api/customers", "method": "GET"},
                    {"url": "/api/customers", "method": "GET"},
                ],
            }
        ]})
        result = fuse_system(tmp)

    m = next(m for m in result["modules"] if m["name"] == "customers")
    assert m["apis"].count("/api/customers") == 1


# ---------------------------------------------------------------------------
# Slice execution test
# ---------------------------------------------------------------------------

def test_slice_7_via_engine():
    from core.execution_engine import ExecutionEngine

    with tempfile.TemporaryDirectory() as tmp:
        protocol_dir = os.path.join(tmp, "protocol")
        data_dir     = os.path.join(tmp, "data")
        os.makedirs(protocol_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        _write(data_dir, "angular_entries.json", _angular([
            _ae("r_customers", "customers", "CustomerListComponent"),
        ]))
        _write(data_dir, "component_api_map.json", _api_map([
            _am("r_customers", "CustomerListComponent", ["/api/customers"]),
        ]))
        _write(data_dir, "api_db_map.json", _db_map([
            _dm("/api/customers", "CustomerController", "CustomerService", ["Customers"]),
        ]))

        state = {
            "current_slice": "SLICE_7",
            "completed_slices": ["SLICE_0", "SLICE_1", "SLICE_2", "SLICE_3", "SLICE_6"],
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

        assert result["slice"] == "SLICE_7"
        assert result["status"] == "OK"
        assert result["items_found"] >= 1

        out_path = os.path.join(data_dir, "system_model.json")
        assert os.path.isfile(out_path)
        with open(out_path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert "modules" in data
        assert len(data["modules"]) >= 1

        new_state = engine.load_state()
        assert new_state["current_slice"] == "SLICE_8"
        assert "SLICE_7" in new_state["completed_slices"]
