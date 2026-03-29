"""C# signal extraction analyzer.

This analyzer extracts lightweight structural signals from C# source files.
It is not a full parser and does not guarantee semantic correctness.
It is designed for large-solution inventory work where speed and broad coverage
matter more than perfect understanding of every file.
"""

import re

from analyzers.base_analyzer import BaseAnalyzer


# ---------------------------------------------------------------------------
# SQL string extraction helpers (reused by DataModelExtractor)
# ---------------------------------------------------------------------------

# Matches string literals that look like SQL.  We look for multiline verbatim
# strings (@"...") and regular double-quoted strings and capture the body.
# A string is considered SQL if it starts (after optional whitespace) with
# one of the DML/query keywords.
_SQL_VERBATIM = re.compile(r'@"(.*?)"', re.DOTALL)
_SQL_REGULAR = re.compile(r'"((?:[^"\\]|\\.)*)"')
_SQL_KEYWORD_START = re.compile(
    r"^\s*(?:SELECT|INSERT|UPDATE|DELETE|WITH|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)

# Per-query signal patterns
_SELECT_COLS = re.compile(r"\bSELECT\b(.*?)\bFROM\b", re.IGNORECASE | re.DOTALL)
_FROM_TABLE = re.compile(
    r"\bFROM\s+(?:\[?\w+\]?\.)?\[?(\w+)\]?\b", re.IGNORECASE
)
_JOIN_TABLE = re.compile(
    r"\bJOIN\s+(?:\[?\w+\]?\.)?\[?(\w+)\]?\b", re.IGNORECASE
)
_INSERT_TABLE = re.compile(
    r"\bINSERT\s+INTO\s+(?:\[?\w+\]?\.)?\[?(\w+)\]?\b", re.IGNORECASE
)
_UPDATE_TABLE = re.compile(
    r"\bUPDATE\s+(?:\[?\w+\]?\.)?\[?(\w+)\]?\b", re.IGNORECASE
)
_DELETE_TABLE = re.compile(
    r"\bDELETE\s+FROM\s+(?:\[?\w+\]?\.)?\[?(\w+)\]?\b", re.IGNORECASE
)
# JOIN relationship: "JOIN <right> ON <left>.<col> = <right>.<col>"
_JOIN_REL = re.compile(
    r"\bJOIN\s+(?:\[?\w+\]?\.)?\[?(\w+)\]?\s+(?:\w+\s+)?ON\s+"
    r"(?:\[?\w+\]?\.)?\[?(\w+)\]?\s*=\s*(?:\[?\w+\]?\.)?\[?(\w+)\]?",
    re.IGNORECASE,
)


def extract_embedded_sql(content: str) -> list:
    """Return a list of SQL query dicts extracted from a C# source string.

    Each dict has:
        ``raw``        — the raw SQL text (stripped)
        ``operations`` — sorted list of DML verbs present (SELECT/INSERT/…)
        ``tables``     — sorted list of table names referenced
        ``joins``      — list of {left, right} relationship dicts (source order)
    """
    candidates = []
    for m in _SQL_VERBATIM.finditer(content):
        candidates.append(m.group(1))
    for m in _SQL_REGULAR.finditer(content):
        candidates.append(m.group(1).replace('\\"', '"'))

    results = []
    for text in candidates:
        if not _SQL_KEYWORD_START.match(text):
            continue
        raw = text.strip()
        ops = sorted({
            v for v in ("SELECT", "INSERT", "UPDATE", "DELETE")
            if re.search(rf"\b{v}\b", raw, re.IGNORECASE)
        })
        tables: set = set()
        tables.update(m.lower() for m in _FROM_TABLE.findall(raw))
        tables.update(m.lower() for m in _JOIN_TABLE.findall(raw))
        tables.update(m.lower() for m in _INSERT_TABLE.findall(raw))
        tables.update(m.lower() for m in _UPDATE_TABLE.findall(raw))
        tables.update(m.lower() for m in _DELETE_TABLE.findall(raw))
        # Filter out common SQL noise tokens that are not table names
        _NOISE = frozenset({"where", "set", "values", "select", "on", ""})
        tables -= _NOISE

        joins = []
        for m in _JOIN_REL.finditer(raw):
            right_table = m.group(1).lower()
            left_col = m.group(2).lower()
            right_col = m.group(3).lower()
            joins.append({"left_column": left_col, "right_table": right_table, "right_column": right_col})

        if ops or tables:
            results.append({
                "raw": raw[:500],
                "operations": ops,
                "tables": sorted(tables),
                "joins": joins,
            })
    return results


class CSharpAnalyzer(BaseAnalyzer):
    def analyze(self, file_path: str, content: str, analysis):
        classes = re.findall(r"\bclass\s+(\w+)", content)
        interfaces = re.findall(r"\binterface\s+(\w+)", content)
        method_pattern = re.compile(
            r"\b(?:public|private|protected|internal)\s+(?:async\s+)?[\w<>,\[\]?]+\s+(\w+)\s*\(",
            re.MULTILINE,
        )
        methods = method_pattern.findall(content)
        endpoint_pattern = re.compile(r"\[(HttpGet|HttpPost|HttpPut|HttpDelete|Route)\b[^\]]*\]", re.MULTILINE)
        endpoints = endpoint_pattern.findall(content)

        keywords = []
        for keyword in ["status", "type", "code", "id", "date"]:
            if re.search(rf"\b{keyword}\b", content, re.IGNORECASE):
                keywords.append(keyword)

        namespaces = re.findall(r"^\s*using\s+([\w\.]+)\s*;", content, re.MULTILINE)
        injected_dependencies = re.findall(r"private\s+readonly\s+[\w<>,\.\[\]?]+\s+_(\w+)\s*;", content)

        analysis.summary = "C# file analyzed for structural signals."
        analysis.key_elements["classes"] = sorted(set(classes))
        analysis.key_elements["interfaces"] = sorted(set(interfaces))
        analysis.key_elements["methods"] = sorted(set(methods))
        analysis.key_elements["endpoints"] = endpoints
        analysis.key_elements["embedded_sql"] = extract_embedded_sql(content)
        analysis.domain_signals["keywords"] = keywords
        analysis.dependencies["namespaces"] = sorted(set(namespaces))
        analysis.dependencies["injected_fields"] = sorted(set(injected_dependencies))
        analysis.inputs_outputs["possible_http_attributes"] = endpoints
        analysis.raw_extract = content[:1000]

        if not classes and not interfaces and not methods:
            analysis.risks_notes.append("Low structural signal density in C# file")
