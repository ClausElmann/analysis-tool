"""
dfep_v2/extractor/greenai_parser.py — Layer 1 deterministic extractor for GreenAI.

Same structure as l0_parser but tuned for GreenAI vertical slice patterns:
- Features/**/*Handler.cs
- Features/**/*Endpoint.cs
- Features/**/*Repository.cs
- Features/**/*.sql

OUTPUT: list[CodeFact] — pure verifiable facts, no interpretation.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

# Reuse the CodeFact model from l0_parser
from dfep_v2.extractor.l0_parser import CodeFact, _TABLE_RE, _SQL_OP_RE, _FILTER_RE


# ---------------------------------------------------------------------------
# GreenAI-specific patterns
# ---------------------------------------------------------------------------

_HANDLER_HANDLE_RE = re.compile(
    r"public\s+(?:async\s+)?Task<[^>]+>\s+Handle\s*\(\s*([^,)]+),",
    re.MULTILINE,
)

_ENDPOINT_MAP_RE = re.compile(
    r"app\.(MapGet|MapPost|MapPut|MapDelete)\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

_DI_REGISTRATION_RE = re.compile(
    r"(?:AddScoped|AddTransient|AddSingleton)<([^,>]+),\s*([^>]+)>",
    re.IGNORECASE,
)

_RESULT_RE = re.compile(r"Result<([^>]+)>")

_METHOD_RE = re.compile(
    r"(?:public|private|protected|internal)\s+"
    r"(?:async\s+)?(?:Task<[^>]+>|[A-Za-z_][A-Za-z0-9_<>?,\s]*?)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(?:\{|=>)",
    re.MULTILINE,
)

_CLASS_RE = re.compile(
    r"(?:public|internal)\s+(?:sealed\s+|partial\s+|abstract\s+)*class\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)

_DOMAIN_PATH_MAP = [
    (re.compile(r"/templates?/",       re.I), "Templates"),
    (re.compile(r"/senddirect|/send/",  re.I), "Send"),
    (re.compile(r"/outbox|outboxworker", re.I), "Send"),
    (re.compile(r"/lookup|/address|/owner|/cvr", re.I), "Lookup"),
    (re.compile(r"/auth",               re.I), "Auth"),
    (re.compile(r"/profile",            re.I), "Profiles"),
]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class GreenAIParser:
    """
    Walks green-ai/src and returns CodeFact objects per method/handler/endpoint.

    Usage:
        parser = GreenAIParser(root="C:/Udvikling/green-ai/src")
        facts = parser.parse_domain("Templates")
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
        skip_dirs = {"bin", "obj", ".git", "TestResults", "Migrations"}

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

        # Current class
        current_class = "Unknown"
        for cm in _CLASS_RE.finditer(content):
            current_class = cm.group(1)
            break

        # HTTP endpoint detection
        http_route = None
        http_method_type = None
        for em in _ENDPOINT_MAP_RE.finditer(content):
            verb = em.group(1).replace("Map", "").upper()
            http_method_type = verb
            http_route = em.group(2)
            break

        # Process methods
        for mm in _METHOD_RE.finditer(content):
            method_name = mm.group(1)
            params_raw = mm.group(2)

            skip_names = {"get", "set", "ToString", "GetHashCode", "Equals", "Dispose"}
            if method_name in skip_names:
                continue

            line_no = content[: mm.start()].count("\n") + 1
            file_ref = f"{rel_path}:{line_no}"
            body_lines = lines[line_no: line_no + 60]
            body = "\n".join(body_lines)

            tables = list(dict.fromkeys(_TABLE_RE.findall(body)))
            sql_ops = list(dict.fromkeys(op.upper() for op in _SQL_OP_RE.findall(body)))
            filters = list(dict.fromkeys(_FILTER_RE.findall(body)))

            # Calls: method invocations in body
            call_re = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]+)\s*\(", re.MULTILINE)
            _NOISE = {"if", "while", "for", "foreach", "return", "throw", "new", "await",
                      "var", "string", "int", "bool", method_name}
            calls = [
                c for c in dict.fromkeys(call_re.findall(body))
                if c not in _NOISE
            ][:12]

            # Params
            params = self._parse_params(params_raw)

            # Returns
            result_types = _RESULT_RE.findall(content[:500] + mm.group(0))
            returns = result_types[0] if result_types else ""

            # ICurrentUser usage
            uses_current_user = bool(re.search(r"_currentUser|ICurrentUser", body))
            if uses_current_user and "JWT identity" not in filters:
                filters.append("ICurrentUser (JWT claims)")

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

    def to_dict(self, fact: CodeFact) -> dict:
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
