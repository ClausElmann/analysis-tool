"""
SQL-specific analysis for the Rebuild Integrity Gate (RIG).

SQL files are treated as PRIMARY (equal weight to .cs) because
in Dapper-based architecture, SQL = behavior.

Four checks:
1. sql_behavior_signature  — ordered SQL operation tokens (flow fingerprint)
2. sql_structural_similarity — table/column name overlap
3. sql_naming_guard         — identical column aliases, table names, WHERE patterns
4. sql_schema_guard         — DDL-specific: CREATE TABLE names, column names, constraint names
                              SCHEMA IS THE HIGHEST-RISK AREA — table/column names are persistent
                              identifiers that define the data model and are hardest to change later.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher


# SQL operation tokens for behavior fingerprint
_SQL_OP_PATTERNS: list[tuple[str, str]] = [
    ("SELECT_COUNT",    r'\bSELECT\s+COUNT\b'),
    ("SELECT_EXISTS",   r'\bSELECT\s+(?:TOP\s+1|1)\b'),
    ("SELECT_HEADER",   r'\bSELECT\b(?!.*COUNT)'),
    ("INSERT_OUTPUT",   r'\bOUTPUT\s+INSERTED\b'),
    ("INSERT",          r'\bINSERT\s+INTO\b'),
    ("UPDATE",          r'\bUPDATE\b'),
    ("DELETE",          r'\bDELETE\s+FROM\b'),
    ("WHERE_PROFILE",   r'\bWHERE\b.*\bProfileId\s*='),
    ("WHERE_TENANT",    r'\bWHERE\b.*\bCustomerId\s*='),
    ("WHERE_PARAM",     r'\bWHERE\b.*@\w+'),
    ("JOIN",            r'\bJOIN\b'),
    ("TRANSACTION",     r'\bBEGIN\s+TRAN(?:SACTION)?\b'),
    ("ORDER_BY",        r'\bORDER\s+BY\b'),
    ("PARAM",           r'@\w+'),
]


def sql_behavior_signature(sql_source: str) -> list[str]:
    """
    Return ordered SQL operation tokens — the flow fingerprint of the SQL file.
    Each token appears at most once, in order of first occurrence.
    """
    seen: list[str] = []
    seen_set: set[str] = set()
    for token, pattern in _SQL_OP_PATTERNS:
        if re.search(pattern, sql_source, re.IGNORECASE | re.DOTALL):
            if token not in seen_set:
                seen.append(token)
                seen_set.add(token)
    return seen


def _extract_sql_table_names(sql_source: str) -> list[str]:
    """Extract table names from FROM, JOIN, INSERT INTO, UPDATE, DELETE FROM."""
    patterns = [
        r'\bFROM\s+\[?(\w+)\]?',
        r'\bJOIN\s+\[?(\w+)\]?',
        r'\bINSERT\s+INTO\s+\[?(\w+)\]?',
        r'\bUPDATE\s+\[?(\w+)\]?',
        r'\bDELETE\s+FROM\s+\[?(\w+)\]?',
    ]
    names: list[str] = []
    for p in patterns:
        names.extend(re.findall(p, sql_source, re.IGNORECASE))
    return [n.lower() for n in names]


def _extract_sql_column_aliases(sql_source: str) -> list[str]:
    """Extract column aliases: SELECT x AS alias or SELECT x alias."""
    aliases: list[str] = []
    # Pattern: word/expression AS identifier
    for m in re.finditer(r'\bAS\s+(\w+)', sql_source, re.IGNORECASE):
        aliases.append(m.group(1).lower())
    return aliases


def _extract_sql_param_names(sql_source: str) -> list[str]:
    """Extract all @ParameterName usages."""
    return [m.lower() for m in re.findall(r'@(\w+)', sql_source)]


def sql_structural_similarity(greenai_sql: str, legacy_sql: str) -> tuple[float, list[str]]:
    """
    Structural comparison for SQL files: table names + column aliases.
    Returns (score, flags).
    """
    ga_tables   = set(_extract_sql_table_names(greenai_sql))
    leg_tables  = set(_extract_sql_table_names(legacy_sql))
    ga_aliases  = set(_extract_sql_column_aliases(greenai_sql))
    leg_aliases = set(_extract_sql_column_aliases(legacy_sql))

    all_ga  = ga_tables | ga_aliases
    all_leg = leg_tables | leg_aliases

    if not all_ga:
        return 0.0, []

    shared = all_ga & all_leg
    score  = len(shared) / len(all_ga)

    flags: list[str] = []
    for name in sorted(shared)[:5]:
        flags.append(f"SQL identifier '{name}' is identical in both codebases")

    return round(score, 3), flags


def sql_naming_guard(greenai_sql: str, legacy_sql: str) -> list[str]:
    """
    Flag identical column aliases, table names, and parameter names between
    the GreenAI SQL and legacy SQL.
    Returns a list of flag strings.
    """
    flags: list[str] = []

    # Column aliases
    ga_aliases  = set(_extract_sql_column_aliases(greenai_sql))
    leg_aliases = set(_extract_sql_column_aliases(legacy_sql))
    shared_aliases = ga_aliases & leg_aliases
    for alias in sorted(shared_aliases):
        flags.append(f"SQL column alias '{alias}' identical to legacy — consider renaming")

    # Table names
    ga_tables  = set(_extract_sql_table_names(greenai_sql))
    leg_tables = set(_extract_sql_table_names(legacy_sql))
    # Table names are expected to be identical (same DB) — only flag if combined with alias match
    if shared_aliases and ga_tables & leg_tables:
        shared_tables = ga_tables & leg_tables
        flags.append(
            f"SQL query pattern mirrors legacy: shared tables {sorted(shared_tables)[:3]} "
            f"AND shared aliases {sorted(shared_aliases)[:3]}"
        )

    # Parameter names — exact match signals copy/paste
    ga_params  = set(_extract_sql_param_names(greenai_sql))
    leg_params = set(_extract_sql_param_names(legacy_sql))
    shared_params = ga_params & leg_params
    if len(shared_params) > 2:
        flags.append(
            f"SQL parameter names overlap significantly with legacy: "
            f"{sorted(shared_params)[:5]} — verify these are GreenAI-native"
        )

    return flags


def is_schema_file(sql_source: str) -> bool:
    """Return True if the SQL file is a DDL/migration file (contains CREATE TABLE)."""
    return bool(re.search(r'\bCREATE\s+TABLE\b', sql_source, re.IGNORECASE))


def _extract_create_table_names(sql_source: str) -> list[str]:
    """Extract table names from CREATE TABLE statements."""
    return [
        m.lower()
        for m in re.findall(r'\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\[?(\w+)\]?', sql_source, re.IGNORECASE)
    ]


def _extract_column_definitions(sql_source: str) -> list[str]:
    """
    Extract column names from CREATE TABLE bodies.
    Matches lines like: [ColumnName] INT NOT NULL or ColumnName NVARCHAR(255)
    """
    columns: list[str] = []
    # Find CREATE TABLE blocks
    for block_match in re.finditer(
        r'\bCREATE\s+TABLE\b.*?\((.+?)\)',
        sql_source,
        re.IGNORECASE | re.DOTALL,
    ):
        body = block_match.group(1)
        for line in body.splitlines():
            line = line.strip().lstrip('[')
            # Column definition starts with an identifier followed by a type keyword
            m = re.match(r'^(\w+)\]?\s+(?:INT|BIGINT|NVARCHAR|VARCHAR|DATETIME|BIT|DECIMAL|FLOAT|UNIQUEIDENTIFIER|TEXT)', line, re.IGNORECASE)
            if m:
                col = m.group(1).lower()
                # Skip SQL keywords
                if col not in {'constraint', 'primary', 'foreign', 'unique', 'index', 'key', 'check'}:
                    columns.append(col)
    return columns


def _extract_constraint_names(sql_source: str) -> list[str]:
    """Extract CONSTRAINT names from DDL."""
    return [
        m.lower()
        for m in re.findall(r'\bCONSTRAINT\s+\[?(\w+)\]?', sql_source, re.IGNORECASE)
    ]


def _extract_index_names(sql_source: str) -> list[str]:
    """Extract CREATE INDEX names from DDL."""
    return [
        m.lower()
        for m in re.findall(r'\bCREATE\s+(?:UNIQUE\s+)?(?:NONCLUSTERED\s+|CLUSTERED\s+)?INDEX\s+\[?(\w+)\]?', sql_source, re.IGNORECASE)
    ]


def _load_ignored_table_names() -> frozenset[str]:
    """Load schema_guard.ignored_table_names from config.json."""
    import json as _json
    config_path = _Path(__file__).parent.parent / "config.json"
    try:
        cfg = _json.loads(config_path.read_text(encoding="utf-8"))
        return frozenset(n.lower() for n in cfg.get("schema_guard", {}).get("ignored_table_names", []))
    except Exception:
        return frozenset()


from pathlib import Path as _Path


def sql_schema_guard(greenai_schema: str, legacy_schema: str) -> tuple[float, list[str]]:
    """
    Schema guard for DDL/migration files (CREATE TABLE).
    This is the HIGHEST-RISK area: table names, column names, constraint names, index names
    are persistent identifiers that define the data model.

    Returns (risk_score, flags).
    risk_score: 0.0–1.0 — fraction of GreenAI schema identifiers matching legacy.
    flags: specific matches that signal copy risk.

    Risk levels:
    - Table names identical:    HIGH RISK — rename or justify
    - Column names identical:   MEDIUM RISK — common names (Id, Name) are expected; flag clusters
    - Constraint/index names:   HIGH RISK — these are almost always copy if identical
    """
    flags: list[str] = []
    _ignored_tables = _load_ignored_table_names()

    # Table names (filter schema prefixes like 'dbo' which are SQL Server defaults, not design choices)
    ga_tables  = set(t for t in _extract_create_table_names(greenai_schema) if t not in _ignored_tables)
    leg_tables = set(t for t in _extract_create_table_names(legacy_schema)  if t not in _ignored_tables)
    shared_tables = ga_tables & leg_tables
    for t in sorted(shared_tables):
        flags.append(f"SCHEMA HIGH RISK: table name '{t}' identical to legacy — rename or justify")

    # Column names — flag clusters (>3 identical columns in same table context = copy signal)
    ga_cols  = _extract_column_definitions(greenai_schema)
    leg_cols = set(_extract_column_definitions(legacy_schema))
    # Exclude trivially universal column names
    _universal = {'id', 'name', 'description', 'createdat', 'updatedat', 'isactive',
                  'isdeleted', 'createdutc', 'modifiedutc', 'status', 'value'}
    shared_cols = [c for c in ga_cols if c in leg_cols and c not in _universal]
    if len(shared_cols) > 3:
        flags.append(
            f"SCHEMA MEDIUM RISK: {len(shared_cols)} non-trivial column names shared with legacy: "
            f"{sorted(set(shared_cols))[:6]} — verify these reflect GreenAI domain model"
        )
    elif shared_cols:
        flags.append(
            f"SCHEMA LOW RISK: column names also in legacy: {sorted(set(shared_cols))[:4]}"
        )

    # Constraint names — almost never coincidentally identical
    ga_constraints  = set(_extract_constraint_names(greenai_schema))
    leg_constraints = set(_extract_constraint_names(legacy_schema))
    shared_constraints = ga_constraints & leg_constraints
    for c in sorted(shared_constraints):
        flags.append(f"SCHEMA HIGH RISK: constraint name '{c}' identical to legacy — strong copy signal")

    # Index names
    ga_indexes  = set(_extract_index_names(greenai_schema))
    leg_indexes = set(_extract_index_names(legacy_schema))
    shared_indexes = ga_indexes & leg_indexes
    for i in sorted(shared_indexes):
        flags.append(f"SCHEMA HIGH RISK: index name '{i}' identical to legacy — strong copy signal")

    # Risk score: weighted by severity
    total_ga = len(ga_tables) + len(set(ga_cols)) + len(ga_constraints) + len(ga_indexes)
    if total_ga == 0:
        return 0.0, flags

    weighted_matches = (
        len(shared_tables) * 3 +          # table names: highest weight
        len(shared_cols) * 1 +            # column names: low weight (many are universal)
        len(shared_constraints) * 3 +     # constraint names: highest weight
        len(shared_indexes) * 3           # index names: highest weight
    )
    max_possible = total_ga * 3
    risk_score = min(weighted_matches / max_possible, 1.0)

    return round(risk_score, 3), flags
