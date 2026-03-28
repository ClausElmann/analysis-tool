"""Tests for SqlAnalyzer."""

import pytest

from analyzers.sql_analyzer import SqlAnalyzer
from core.model import FileAnalysis


def make_analysis():
    return FileAnalysis(project="test", path="test.sql", type="sql", technology="sql")


def make_analyzer():
    return SqlAnalyzer()


# 1. Valid SQL file with common objects
def test_sql_valid_tables_and_procedures():
    content = """
CREATE TABLE dbo.Orders (
    id INT,
    status NVARCHAR(50),
    date DATETIME
);

CREATE PROCEDURE dbo.GetOrders
AS
BEGIN
    SELECT * FROM dbo.Orders;
END;
"""
    analyzer = make_analyzer()
    analysis = make_analysis()
    analyzer.analyze("schema.sql", content, analysis)

    assert analysis.summary != ""
    assert "tables_created" in analysis.key_elements
    assert isinstance(analysis.key_elements["tables_created"], list)
    assert "Orders" in analysis.key_elements["tables_created"]
    assert "procedures_created" in analysis.key_elements
    assert isinstance(analysis.key_elements["procedures_created"], list)
    assert "GetOrders" in analysis.key_elements["procedures_created"]
    assert isinstance(analysis.risks_notes, list)


# 2. Partial / syntax-error-like SQL (only references, no creates)
def test_sql_partial_only_references():
    content = """
SELECT * FROM Orders
JOIN Customers ON Orders.id = Customers.order_id
UPDATE Orders SET status = 'done'
"""
    analyzer = make_analyzer()
    analysis = make_analysis()
    analyzer.analyze("query.sql", content, analysis)

    assert "tables_referenced" in analysis.key_elements
    assert isinstance(analysis.key_elements["tables_referenced"], list)
    assert len(analysis.key_elements["tables_referenced"]) > 0
    assert len(analysis.risks_notes) > 0


# 3. Empty / no signals
def test_sql_empty_content():
    content = ""
    analyzer = make_analyzer()
    analysis = make_analysis()
    analyzer.analyze("empty.sql", content, analysis)

    assert analysis.summary != ""
    assert isinstance(analysis.key_elements.get("tables_created", []), list)
    assert isinstance(analysis.key_elements.get("procedures_created", []), list)
    assert isinstance(analysis.domain_signals.get("keywords", []), list)
    assert isinstance(analysis.risks_notes, list)
    assert len(analysis.risks_notes) > 0


# 4. Edge case: view and function definitions
def test_sql_views_and_functions():
    content = """
CREATE VIEW dbo.ActiveOrders AS
SELECT id, status FROM Orders WHERE status = 'active';

CREATE FUNCTION dbo.GetOrderCount()
RETURNS INT
AS
BEGIN
    RETURN (SELECT COUNT(*) FROM Orders);
END;
"""
    analyzer = make_analyzer()
    analysis = make_analysis()
    analyzer.analyze("views.sql", content, analysis)

    assert "views_created" in analysis.key_elements
    assert isinstance(analysis.key_elements["views_created"], list)
    assert "ActiveOrders" in analysis.key_elements["views_created"]
    assert "functions_created" in analysis.key_elements
    assert isinstance(analysis.key_elements["functions_created"], list)
    assert "GetOrderCount" in analysis.key_elements["functions_created"]
    assert isinstance(analysis.dependencies.get("database_objects", []), list)
    assert analysis.raw_extract is not None
