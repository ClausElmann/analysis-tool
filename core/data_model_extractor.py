"""Phase 4.2 – Data Model Extraction.

Builds a table-centric data model by fusing two signal sources:

1. **SQL files** (SqlAnalyzer)  — DDL: table definitions, columns, procedures.
2. **C# files** (CSharpAnalyzer) — DML: SQL strings embedded in Dapper calls.

For each table the extractor records:

* columns discovered from DDL (``CREATE TABLE``) or column-type patterns.
* inferred relationships from ``JOIN … ON`` clauses in any SQL (DDL or
  embedded).
* which C# methods use the table (``used_in_functions``).
* how many distinct queries reference the table (``usage_count``).

Output file: ``data-model.json``

Input files (read from ``output_root``):
    ``analysis-index.json``       — pipeline output (all file analyses)
    ``use-cases.analysis.json``   — use case records (optional; used for
                                    table → use case mapping)

Determinism guarantees
----------------------
* All collections are sorted before output.
* Files and methods are processed in lexicographic path order.
* Tie-breaking is always lexicographic.
* No random values, no timestamps.
"""

import collections
import json
import os
import re
from typing import Any, Dict, List, Set


# ---------------------------------------------------------------------------
# Column extraction from DDL fragments stored in SqlAnalyzer output
# ---------------------------------------------------------------------------
# Pattern: column name followed by a SQL type declaration.
_COL_PATTERN = re.compile(
    r"\[?(\w+)\]?\s+"
    r"(?:int|bigint|smallint|tinyint|decimal|numeric|float|real|bit|money|"
    r"nvarchar|varchar|nchar|char|text|ntext|datetime|datetime2|date|time|"
    r"uniqueidentifier|varbinary|binary|image|xml)\b",
    re.IGNORECASE,
)

# Noise tokens that appear as column names in raw_extract but aren't columns.
_COL_NOISE: frozenset = frozenset({
    "constraint", "primary", "foreign", "references", "default",
    "index", "create", "table", "not", "null", "identity",
})


def _extract_columns_from_raw(raw: str) -> List[str]:
    """Extract column names from a raw DDL snippet."""
    found = []
    for m in _COL_PATTERN.finditer(raw):
        name = m.group(1).lower()
        if name not in _COL_NOISE:
            found.append(name)
    return sorted(set(found))


class DataModelExtractor:
    """Derives a table-centric data model from analysis-index.json signals.

    Parameters
    ----------
    output_root:
        Directory that contains ``analysis-index.json`` and where
        ``data-model.json`` will be written.
    """

    def __init__(self, output_root: str = "output-data") -> None:
        self.output_root = output_root

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self) -> Dict:
        """Compute the data model and write ``data-model.json``.

        Returns the written dict.
        """
        index: List[Dict] = self._load_json("analysis-index.json", default=[])
        use_cases: List[Dict] = self._load_json(
            "use-cases.analysis.json", default={}
        ).get("use_cases", [])

        # ---- Phase 1: build table registry from SQL DDL ----------------
        # table_name → { columns, source_files }
        tables: Dict[str, Dict] = {}
        for entry in sorted(index, key=lambda e: e.get("path", "")):
            if entry.get("type") != "sql":
                continue
            ke = entry.get("key_elements", {})
            path = entry.get("path", "")
            for tname in ke.get("tables_created", []):
                key = tname.lower()
                if key not in tables:
                    tables[key] = {
                        "name": tname,
                        "columns": [],
                        "relationships": [],
                        "used_in_functions": [],
                        "used_in_use_cases": [],
                        "usage_count": 0,
                        "_source_files": [],
                        "_col_set": set(),
                        "_rel_set": set(),
                        "_fn_set": set(),
                        "_uc_set": set(),
                    }
                tables[key]["_source_files"].append(path)
                # Columns from sql_analyzer domain_signals
                for col in ke.get("columns_detected", []) + entry.get("domain_signals", {}).get("columns_detected", []):
                    cname = col.lower()
                    if cname not in _COL_NOISE:
                        tables[key]["_col_set"].add(cname)
                # Columns from raw_extract DDL
                for col in _extract_columns_from_raw(entry.get("raw_extract", "")):
                    tables[key]["_col_set"].add(col)

        # Also register tables referenced but not created (from any SQL file)
        for entry in sorted(index, key=lambda e: e.get("path", "")):
            if entry.get("type") != "sql":
                continue
            ke = entry.get("key_elements", {})
            for tname in ke.get("tables_referenced", []):
                key = tname.lower()
                if key not in tables:
                    tables[key] = {
                        "name": tname,
                        "columns": [],
                        "relationships": [],
                        "used_in_functions": [],
                        "used_in_use_cases": [],
                        "usage_count": 0,
                        "_source_files": [],
                        "_col_set": set(),
                        "_rel_set": set(),
                        "_fn_set": set(),
                        "_uc_set": set(),
                    }

        # ---- Phase 2: enrich from embedded SQL in C# files -------------
        for entry in sorted(index, key=lambda e: e.get("path", "")):
            if entry.get("type") != "csharp":
                continue
            ke = entry.get("key_elements", {})
            methods: List[str] = ke.get("methods", [])
            queries: List[Dict] = ke.get("embedded_sql", [])

            for query in queries:
                for tname in query.get("tables", []):
                    key = tname.lower()
                    if key not in tables:
                        tables[key] = {
                            "name": tname,
                            "columns": [],
                            "relationships": [],
                            "used_in_functions": [],
                            "used_in_use_cases": [],
                            "usage_count": 0,
                            "_source_files": [],
                            "_col_set": set(),
                            "_rel_set": set(),
                            "_fn_set": set(),
                            "_uc_set": set(),
                        }
                    tables[key]["usage_count"] += 1
                    # Map table → methods that are in the same C# file
                    for method in methods:
                        tables[key]["_fn_set"].add(method)
                    # Infer relationships from JOIN…ON
                    for j in query.get("joins", []):
                        right = j.get("right_table", "").lower()
                        if right and right != key:
                            rel_key = (key, right)
                            if rel_key not in tables[key]["_rel_set"]:
                                tables[key]["_rel_set"].add(rel_key)
                            # Register reverse too
                            if right in tables:
                                rev_key = (right, key)
                                tables[right]["_rel_set"].add(rev_key)

        # ---- Phase 3: map tables → use cases ---------------------------
        # Build: table_name → set of use case names that reference it via DB
        # flow steps.
        for uc in use_cases:
            uc_name = uc.get("name", "") or uc.get("id", "")
            for step in uc.get("flow_steps", []):
                if step.get("type") == "DB":
                    step_name = step.get("name", "").lower()
                    # step_name might be a procedure; also check if it
                    # contains a table substring.
                    for key in list(tables.keys()):
                        if key in step_name or step_name in key:
                            tables[key]["_uc_set"].add(uc_name)
            # Also check functions list in use case against table usage
            for fn in uc.get("functions", []):
                fn_lower = fn.lower()
                for key in list(tables.keys()):
                    if key in fn_lower:
                        tables[key]["_uc_set"].add(uc_name)

        # ---- Phase 4: serialise ----------------------------------------
        output_tables = []
        for key in sorted(tables.keys()):
            t = tables[key]
            rels = sorted(
                {"related_table": r[1]} for r in t["_rel_set"]
            ) if t["_rel_set"] else []
            # Deduplicate rels by related_table
            seen_rels: set = set()
            dedup_rels = []
            for r in sorted(t["_rel_set"], key=lambda x: x[1]):
                if r[1] not in seen_rels:
                    seen_rels.add(r[1])
                    dedup_rels.append({"related_table": r[1]})

            output_tables.append({
                "name": t["name"],
                "columns": sorted(t["_col_set"]),
                "relationships": dedup_rels,
                "used_in_functions": sorted(t["_fn_set"]),
                "used_in_use_cases": sorted(t["_uc_set"]),
                "usage_count": t["usage_count"],
            })

        report: Dict = {"tables": output_tables}
        self._write_json("data-model.json", report)
        return report

    # ------------------------------------------------------------------
    # I/O helpers
    # ------------------------------------------------------------------

    def _load_json(self, filename: str, default: Any) -> Any:
        path = os.path.join(self.output_root, filename)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError):
            return default

    def _write_json(self, filename: str, data: Any) -> None:
        os.makedirs(self.output_root, exist_ok=True)
        path = os.path.join(self.output_root, filename)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
