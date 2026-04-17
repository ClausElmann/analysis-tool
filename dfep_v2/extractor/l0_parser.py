"""
dfep_v2/extractor/l0_parser.py — Layer 1 deterministic extractor for Level 0 (sms-service).

PURPOSE: Extract ONLY verifiable code facts — no interpretation, no guessing.

OUTPUT per file:
{
  "file": "TemplateRepository.cs:121",
  "class": "TemplateRepository",
  "method": "GetTemplatesForSmsAndEmail",
  "params": ["customerId", "profileId"],
  "calls": ["INNER JOIN TemplateProfileMappings", "GetTemplates"],
  "tables": ["Templates", "TemplateProfileMappings", "TemplateSms", "TemplateEmails"],
  "sql_ops": ["SELECT"],
  "filters": ["CustomerId=@customerId", "ProfileId=@profileId"],
  "returns": "IEnumerable<Template>",
  "http_route": null,
  "http_method": null,
  "domain_hint": "Templates"
}

RULE: If uncertain → omit, never invent.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Fact record
# ---------------------------------------------------------------------------

@dataclass
class CodeFact:
    """A single verifiable fact extracted from one method in one file."""
    file: str                               # relative path + line number
    class_name: str
    method: str
    params: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)       # method calls found in body
    tables: list[str] = field(default_factory=list)      # DB tables referenced
    sql_ops: list[str] = field(default_factory=list)     # SELECT/INSERT/UPDATE/DELETE
    filters: list[str] = field(default_factory=list)     # WHERE conditions
    returns: str = ""
    http_route: Optional[str] = None
    http_method: Optional[str] = None
    domain_hint: str = "Unknown"
    raw_snippet: str = ""                                # first 300 chars of method body


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_CLASS_RE = re.compile(
    r"(?:public|internal)\s+(?:sealed\s+|partial\s+|abstract\s+)*class\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)

_METHOD_RE = re.compile(
    r"(?:public|protected|private|internal)\s+"
    r"(?:async\s+)?(?:Task<[^>]+>|IEnumerable<[^>]+>|List<[^>]+>|[A-Za-z_][A-Za-z0-9_<>?,\s]*?)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(?:where\s+\w+\s*:\s*\w+\s*)?(?:\{|=>)",
    re.MULTILINE,
)

_METHOD_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)

_TABLE_RE = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE|DELETE\s+FROM)\s+(?:\[?dbo\]?\.)?\[?([A-Za-z_][A-Za-z0-9_]*)\]?",
    re.IGNORECASE,
)

_SQL_OP_RE = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|MERGE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)

_FILTER_RE = re.compile(
    r"(?:WHERE|AND|OR)\s+((?:\[?\w+\]?\.)?(?:\[?\w+\]?)\s*=\s*@\w+)",
    re.IGNORECASE,
)

_HTTP_MAP_RE = re.compile(
    r'(?:MapGet|MapPost|MapPut|MapDelete|Route|Http(?:Get|Post|Put|Delete))\s*[(\[]'
    r'\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)

# Domain inference from path/content
_DOMAIN_PATH_MAP = [
    (re.compile(r"template",   re.I), "Templates"),
    (re.compile(r"send|outbox|message|smsgroup|smslog", re.I), "Send"),
    (re.compile(r"lookup|address|owner|cvr|property", re.I), "Lookup"),
    (re.compile(r"auth|token|login|user", re.I), "Auth"),
    (re.compile(r"profile", re.I), "Profiles"),
    (re.compile(r"customer", re.I), "Customers"),
]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class L0Parser:
    """
    Walks sms-service source and returns CodeFact objects per method.

    Usage:
        parser = L0Parser(root="C:/Udvikling/sms-service")
        facts = parser.parse_domain("Templates")
        all_facts = parser.parse_all()
    """

    def __init__(self, root: str):
        self.root = root
        self._cache: dict[str, list[CodeFact]] = {}

    # ------------------------------------------------------------------
    def parse_domain(self, domain: str) -> list[CodeFact]:
        if domain in self._cache:
            return self._cache[domain]

        all_facts = self._extract_all()
        domain_facts = [f for f in all_facts if f.domain_hint.lower() == domain.lower()]
        self._cache[domain] = domain_facts
        return domain_facts

    def parse_all(self) -> list[CodeFact]:
        return self._extract_all()

    # ------------------------------------------------------------------
    def _extract_all(self) -> list[CodeFact]:
        facts: list[CodeFact] = []
        for rel_path, content in self._walk():
            facts.extend(self._extract_file(rel_path, content))
        return facts

    # ------------------------------------------------------------------
    def _walk(self):
        extensions = {".cs", ".sql"}
        skip_dirs = {"bin", "obj", ".git", "node_modules"}

        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            rel_dir = os.path.relpath(dirpath, self.root)
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in extensions:
                    continue
                abs_path = os.path.join(dirpath, fname)
                rel_path = os.path.join(rel_dir, fname).replace("\\", "/")
                try:
                    with open(abs_path, encoding="utf-8", errors="ignore") as f:
                        yield rel_path, f.read()
                except OSError:
                    continue

    # ------------------------------------------------------------------
    def _extract_file(self, rel_path: str, content: str) -> list[CodeFact]:
        facts: list[CodeFact] = []
        lines = content.splitlines()
        domain_hint = self._infer_domain(rel_path)

        # Extract classes
        current_class = "Unknown"
        for cm in _CLASS_RE.finditer(content):
            current_class = cm.group(1)
            break  # use first class found

        # Extract HTTP routes
        http_route = None
        http_method_type = None
        for hm in _HTTP_MAP_RE.finditer(content):
            http_route = hm.group(1)
            verb = re.search(r"(Get|Post|Put|Delete)", hm.group(0), re.I)
            if verb:
                http_method_type = verb.group(1).upper()
            break

        # Extract methods
        for mm in _METHOD_RE.finditer(content):
            method_name = mm.group(1)
            params_raw = mm.group(2)

            # Skip constructors, property accessors, common noise
            if method_name in ("get", "set", "add", "remove", "ToString", "GetHashCode", "Equals"):
                continue

            line_no = content[: mm.start()].count("\n") + 1
            file_ref = f"{rel_path}:{line_no}"

            # Extract method body (next 60 lines)
            body_lines = lines[line_no: line_no + 60]
            body = "\n".join(body_lines)

            # Tables
            tables = list(dict.fromkeys(_TABLE_RE.findall(body)))

            # SQL ops
            sql_ops = list(dict.fromkeys(op.upper() for op in _SQL_OP_RE.findall(body)))

            # Filters (WHERE clauses)
            filters = list(dict.fromkeys(_FILTER_RE.findall(body)))

            # Method calls (exclude keywords, common builtins)
            _NOISE = {
                "if", "while", "for", "foreach", "return", "throw", "new", "await",
                "async", "var", "string", "int", "bool", "null", "true", "false",
                method_name, current_class,
            }
            calls = [
                c for c in dict.fromkeys(_METHOD_CALL_RE.findall(body))
                if c not in _NOISE and not c[0].islower() or len(c) > 4
            ][:12]

            # Params
            params = self._parse_params(params_raw)

            # Return type
            ret_match = re.search(
                r"(?:Task<([^>]+)>|IEnumerable<([^>]+)>|([A-Za-z_][A-Za-z0-9_]*))\s+"
                + re.escape(method_name),
                mm.group(0),
            )
            returns = ""
            if ret_match:
                returns = next((g for g in ret_match.groups() if g), "")

            fact = CodeFact(
                file=file_ref,
                class_name=current_class,
                method=method_name,
                params=params,
                calls=calls,
                tables=tables,
                sql_ops=sql_ops,
                filters=filters,
                returns=returns,
                http_route=http_route,
                http_method=http_method_type,
                domain_hint=domain_hint,
                raw_snippet=body[:300],
            )
            facts.append(fact)

        return facts

    # ------------------------------------------------------------------
    def _parse_params(self, params_raw: str) -> list[str]:
        if not params_raw.strip():
            return []
        result = []
        for p in params_raw.split(","):
            p = p.strip()
            tokens = p.split()
            if tokens:
                result.append(tokens[-1].lstrip("@"))
        return result[:8]

    def _infer_domain(self, rel_path: str) -> str:
        for pattern, domain in _DOMAIN_PATH_MAP:
            if pattern.search(rel_path):
                return domain
        return "Unknown"

    # ------------------------------------------------------------------
    def to_dict(self, fact: CodeFact) -> dict:
        """Serialize a CodeFact to a plain dict (for LLM input)."""
        return {
            "file": fact.file,
            "class": fact.class_name,
            "method": fact.method,
            "params": fact.params,
            "calls": fact.calls,
            "tables": fact.tables,
            "sql_ops": fact.sql_ops,
            "filters": fact.filters,
            "returns": fact.returns,
            "http_route": fact.http_route,
            "http_method": fact.http_method,
            "domain_hint": fact.domain_hint,
        }
