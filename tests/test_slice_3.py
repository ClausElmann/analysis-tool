"""Tests for SLICE_3: API -> Database tracing (Dapper-based)."""

import json
import os
import tempfile

import pytest

from core.execution_engine import ExecutionEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_cs_file(proj_dir: str, filename: str, content: str) -> str:
    os.makedirs(proj_dir, exist_ok=True)
    path = os.path.join(proj_dir, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _build_engine(tmp_dir: str) -> ExecutionEngine:
    protocol_dir = os.path.join(tmp_dir, "protocol")
    data_dir = os.path.join(tmp_dir, "data")
    os.makedirs(protocol_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    state = {
        "current_slice": "SLICE_3",
        "completed_slices": [],
        "status": "READY",
        "last_run": None,
    }
    with open(os.path.join(protocol_dir, "state.json"), "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    return ExecutionEngine(
        solution_root=tmp_dir,
        protocol_root=protocol_dir,
        data_root=data_dir,
    )


def _write_data(root: str, filename: str, data) -> None:
    data_dir = os.path.join(root, "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, filename), "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def _make_solution(proj_path: str) -> dict:
    return {
        "projects": [
            {
                "name": "BackendApi",
                "path": proj_path,
                "type": "api",
                "indicators": ["controllers"],
            }
        ]
    }


def _make_api_map(entry_id: str, url: str) -> dict:
    return {
        "mappings": [
            {
                "entry_id": entry_id,
                "component": "CustomerListComponent",
                "apis": [{"method": "GET", "url": url, "source": "component", "trigger": "init"}],
                "source_file": "app.component.ts",
            }
        ]
    }


# ---------------------------------------------------------------------------
# Test 1: SELECT query → tables extracted
# ---------------------------------------------------------------------------


def test_slice_3_select_query_extracts_tables():
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "api")

        _write_cs_file(
            proj,
            "CustomerController.cs",
            'public class CustomerController { private CustomerService _customerService; }',
        )
        _write_cs_file(
            proj,
            "CustomerService.cs",
            'public class CustomerService {\n'
            '  public IEnumerable<Customer> GetAll() {\n'
            '    return conn.Query<Customer>("SELECT * FROM Customers WHERE Active = 1");\n'
            '  }\n'
            '}',
        )

        engine = _build_engine(tmp)
        _write_data(tmp, "solution_structure.json", _make_solution(proj))
        _write_data(tmp, "component_api_map.json", _make_api_map("route_customers", "/api/customers"))

        result = engine._run_slice_3()

        assert len(result["mappings"]) == 1
        mapping = result["mappings"][0]
        assert "Customers" in mapping["sql"]["tables"]


# ---------------------------------------------------------------------------
# Test 2: JOIN detected in SQL
# ---------------------------------------------------------------------------


def test_slice_3_join_detected():
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "api")

        _write_cs_file(proj, "OrderController.cs",
            'public class OrderController { private OrderService _orderService; }')
        _write_cs_file(
            proj,
            "OrderService.cs",
            'public class OrderService {\n'
            '  public void Get() {\n'
            '    conn.Query("SELECT o.Id, c.Name FROM Orders o INNER JOIN Customers c ON o.CustomerId = c.Id");\n'
            '  }\n'
            '}',
        )

        engine = _build_engine(tmp)
        _write_data(tmp, "solution_structure.json", _make_solution(proj))
        _write_data(tmp, "component_api_map.json", _make_api_map("route_orders", "/api/orders"))

        result = engine._run_slice_3()

        assert len(result["mappings"]) == 1
        mapping = result["mappings"][0]
        assert any("JOIN" in j for j in mapping["sql"]["joins"])
        assert "Customers" in mapping["sql"]["tables"]


# ---------------------------------------------------------------------------
# Test 3: WHERE condition column extracted
# ---------------------------------------------------------------------------


def test_slice_3_where_condition_extracted():
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "api")

        _write_cs_file(proj, "ProductController.cs",
            'public class ProductController { private ProductService _productService; }')
        _write_cs_file(
            proj,
            "ProductService.cs",
            'public class ProductService {\n'
            '  public Product GetById() {\n'
            '    return conn.QueryFirst<Product>("SELECT * FROM Products WHERE Id = @Id");\n'
            '  }\n'
            '}',
        )

        engine = _build_engine(tmp)
        _write_data(tmp, "solution_structure.json", _make_solution(proj))
        _write_data(tmp, "component_api_map.json", _make_api_map("route_products", "/api/products"))

        result = engine._run_slice_3()

        assert len(result["mappings"]) == 1
        mapping = result["mappings"][0]
        assert "Id" in mapping["sql"]["where_conditions"]


# ---------------------------------------------------------------------------
# Test 4: Entry with no SQL is skipped (not included in output)
# ---------------------------------------------------------------------------


def test_slice_3_no_sql_entry_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "api")

        # Controller with a service reference, but service has no Dapper calls
        _write_cs_file(proj, "EmptyController.cs",
            'public class EmptyController { private EmptyService _emptyService; }')
        _write_cs_file(
            proj,
            "EmptyService.cs",
            'public class EmptyService {\n'
            '  public string Get() { return "hello"; }\n'
            '}',
        )

        engine = _build_engine(tmp)
        _write_data(tmp, "solution_structure.json", _make_solution(proj))
        _write_data(tmp, "component_api_map.json", _make_api_map("route_empty", "/api/empty"))

        result = engine._run_slice_3()

        assert result["mappings"] == []


# ---------------------------------------------------------------------------
# Test 5: Dynamic SQL (no literal string) is skipped
# ---------------------------------------------------------------------------


def test_slice_3_dynamic_sql_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "api")

        _write_cs_file(proj, "ReportController.cs",
            'public class ReportController { private ReportService _reportService; }')
        # Uses string variable, not a literal — _DAPPER_LITERAL_SQL_RE should NOT match
        _write_cs_file(
            proj,
            "ReportService.cs",
            'public class ReportService {\n'
            '  public void Get() {\n'
            '    var sql = "SELECT * FROM Reports WHERE " + filter;\n'
            '    conn.Query(sql);\n'
            '  }\n'
            '}',
        )

        engine = _build_engine(tmp)
        _write_data(tmp, "solution_structure.json", _make_solution(proj))
        _write_data(tmp, "component_api_map.json", _make_api_map("route_reports", "/api/reports"))

        result = engine._run_slice_3()

        assert result["mappings"] == []


# ---------------------------------------------------------------------------
# Test 6: Multiple Dapper queries in one service → all included
# ---------------------------------------------------------------------------


def test_slice_3_multiple_queries_all_included():
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "api")

        _write_cs_file(proj, "InvoiceController.cs",
            'public class InvoiceController { private InvoiceService _invoiceService; }')
        _write_cs_file(
            proj,
            "InvoiceService.cs",
            'public class InvoiceService {\n'
            '  public void GetSummary() {\n'
            '    var headers = conn.Query<Invoice>("SELECT * FROM Invoices WHERE Status = @Status");\n'
            '    var lines = conn.Query<InvoiceLine>("SELECT * FROM InvoiceLines WHERE InvoiceId = @Id");\n'
            '  }\n'
            '}',
        )

        engine = _build_engine(tmp)
        _write_data(tmp, "solution_structure.json", _make_solution(proj))
        _write_data(tmp, "component_api_map.json", _make_api_map("route_invoices", "/api/invoices"))

        result = engine._run_slice_3()

        assert len(result["mappings"]) == 2
        tables_found = {
            t
            for m in result["mappings"]
            for t in m["sql"]["tables"]
        }
        assert "Invoices" in tables_found
        assert "InvoiceLines" in tables_found


# ---------------------------------------------------------------------------
# Test 7: SQL JOIN → relation extracted (e.g. "Orders→Customers")
# ---------------------------------------------------------------------------


def test_slice_3_join_produces_relation():
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "api")

        _write_cs_file(proj, "OrderController.cs",
            'public class OrderController { private OrderService _orderService; }')
        _write_cs_file(
            proj,
            "OrderService.cs",
            'public class OrderService {\n'
            '  public void Get() {\n'
            '    conn.Query("SELECT o.Id, c.Name FROM Orders o INNER JOIN Customers c ON o.CustomerId = c.Id");\n'
            '  }\n'
            '}',
        )

        engine = _build_engine(tmp)
        _write_data(tmp, "solution_structure.json", _make_solution(proj))
        _write_data(tmp, "component_api_map.json", _make_api_map("route_orders", "/api/orders"))

        result = engine._run_slice_3()

        assert len(result["mappings"]) == 1
        relations = result["mappings"][0]["sql"]["relations"]
        assert len(relations) > 0
        assert any("Orders" in r and "Customers" in r for r in relations)


# ---------------------------------------------------------------------------
# Test 8: [Route] + [HttpGet("suffix")] → route-attribute matching
# ---------------------------------------------------------------------------


def test_slice_3_controller_route_attribute_matching():
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "api")

        _write_cs_file(
            proj,
            "CustomerController.cs",
            '[Route("api/customers")]\n'
            'public class CustomerController {\n'
            '    private CustomerService _customerService;\n'
            '    [HttpGet]\n'
            '    public async Task<IActionResult> GetAll() {\n'
            '        return Ok(_customerService.GetAll());\n'
            '    }\n'
            '    [HttpGet("search")]\n'
            '    public async Task<IActionResult> Search(string q) {\n'
            '        return Ok(_customerService.Search(q));\n'
            '    }\n'
            '}',
        )
        _write_cs_file(
            proj,
            "CustomerService.cs",
            'public class CustomerService {\n'
            '    public IEnumerable<Customer> GetAll() {\n'
            '        return conn.Query<Customer>("SELECT * FROM Customers");\n'
            '    }\n'
            '    public IEnumerable<Customer> Search(string q) {\n'
            '        return conn.Query<Customer>("SELECT * FROM Customers WHERE Name LIKE @q");\n'
            '    }\n'
            '}',
        )

        engine = _build_engine(tmp)
        _write_data(tmp, "solution_structure.json", _make_solution(proj))
        _write_data(tmp, "component_api_map.json", _make_api_map("route_customers", "/api/customers"))

        result = engine._run_slice_3()

        assert len(result["mappings"]) >= 1
        mapping = result["mappings"][0]
        assert mapping["controller"] == "CustomerController"
        assert "Customers" in mapping["sql"]["tables"]


# ---------------------------------------------------------------------------
# Test 9: IXxxService interface field → resolved to XxxService
# ---------------------------------------------------------------------------


def test_slice_3_interface_resolved_to_implementation():
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "api")

        _write_cs_file(
            proj,
            "InvoiceController.cs",
            'public class InvoiceController {\n'
            '    private readonly IInvoiceService _invoiceService;\n'
            '}',
        )
        _write_cs_file(
            proj,
            "InvoiceService.cs",
            'public class InvoiceService : IInvoiceService {\n'
            '    public void Get() {\n'
            '        conn.Query("SELECT * FROM Invoices WHERE Active = 1");\n'
            '    }\n'
            '}',
        )

        engine = _build_engine(tmp)
        _write_data(tmp, "solution_structure.json", _make_solution(proj))
        _write_data(tmp, "component_api_map.json", _make_api_map("route_invoices", "/api/invoices"))

        result = engine._run_slice_3()

        assert len(result["mappings"]) >= 1
        mapping = result["mappings"][0]
        assert mapping["service"] == "InvoiceService"
        assert "Invoices" in mapping["sql"]["tables"]


# ---------------------------------------------------------------------------
# Test 10: controller_method + service_method traced end-to-end
# ---------------------------------------------------------------------------


def test_slice_3_controller_and_service_method_traced():
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "api")

        _write_cs_file(
            proj,
            "ProductController.cs",
            '[Route("api/products")]\n'
            'public class ProductController {\n'
            '    private readonly IProductService _productService;\n'
            '    [HttpGet]\n'
            '    public async Task<IActionResult> GetAll() {\n'
            '        return Ok(await _productService.GetAll());\n'
            '    }\n'
            '}',
        )
        _write_cs_file(
            proj,
            "ProductService.cs",
            'public class ProductService : IProductService {\n'
            '    public IEnumerable<Product> GetAll() {\n'
            '        return conn.Query<Product>("SELECT * FROM Products WHERE Active = 1");\n'
            '    }\n'
            '}',
        )

        engine = _build_engine(tmp)
        _write_data(tmp, "solution_structure.json", _make_solution(proj))
        _write_data(tmp, "component_api_map.json", _make_api_map("route_products", "/api/products"))

        result = engine._run_slice_3()

        assert len(result["mappings"]) >= 1
        mapping = result["mappings"][0]
        assert mapping["controller_method"] == "GetAll"
        assert mapping["service_method"] == "GetAll"
        assert "Products" in mapping["sql"]["tables"]


# ---------------------------------------------------------------------------
# Test 11: Same input twice → identical output (deterministic)
# ---------------------------------------------------------------------------


def test_slice_3_output_is_deterministic():
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "api")

        _write_cs_file(proj, "CustomerController.cs",
            'public class CustomerController { private CustomerService _customerService; }')
        _write_cs_file(
            proj,
            "CustomerService.cs",
            'public class CustomerService {\n'
            '  public void Get() {\n'
            '    conn.Query("SELECT * FROM Customers WHERE Active = 1");\n'
            '  }\n'
            '}',
        )

        engine = _build_engine(tmp)
        _write_data(tmp, "solution_structure.json", _make_solution(proj))
        _write_data(tmp, "component_api_map.json", _make_api_map("route_customers", "/api/customers"))

        result1 = engine._run_slice_3()
        result2 = engine._run_slice_3()

        assert result1 == result2
