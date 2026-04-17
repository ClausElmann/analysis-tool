"""
dfep_v3/extractor/greenai_extractor_v3.py

DFEP v3 — Extended GreenAI extractor with SQL first-class fact support.

Extends v2 GreenAIParser. For .sql files, extracts a CodeFact per file
containing table refs, SQL ops, filters, and @Parameters. This ensures
that capabilities citing GetTemplateById.sql:1 etc. are validated correctly
by CapabilityValidator and not falsely rejected as phantom refs.

Design principle (TASK A):
  - .cs files: inherited behavior from v2 GreenAIParser (methods, handlers, endpoints)
  - .sql files: one CodeFact per file at line 1 — table, ops, filters, @params
  - Override only _extract_file; all other v2 behavior unchanged
"""

from __future__ import annotations

import os
import re

from dfep_v2.extractor.greenai_parser import GreenAIParser
from dfep_v2.extractor.l0_parser import CodeFact, _TABLE_RE, _SQL_OP_RE, _FILTER_RE


# Matches @ParameterName in SQL (e.g. @ProfileId, @CustomerId)
_SQL_PARAM_RE = re.compile(r"@([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)


class GreenAIExtractorV3(GreenAIParser):
    """
    V3 GreenAI extractor: .sql files become first-class CodeFact entries.

    When the CapabilityValidator checks `GetTemplateById.sql:1`, it will now find
    a fact with that key, preventing false phantom-ref rejections.

    Facts from SQL files include:
      - file ref = "relative/path/to/File.sql:1"
      - class_name = "SQL"
      - method = filename without extension (e.g. "GetTemplateById")
      - params = list of @ParameterNames found in SQL
      - tables = table names referenced (FROM/JOIN/UPDATE/INSERT)
      - sql_ops = SQL verbs (SELECT, INSERT, UPDATE, DELETE)
      - filters = WHERE-clause column names + @params
      - raw_snippet = first 300 chars of content
    """

    def _extract_file(self, rel_path: str, content: str) -> list[CodeFact]:
        ext = os.path.splitext(rel_path)[1].lower()
        if ext == ".sql":
            return self._extract_sql_file(rel_path, content)
        return super()._extract_file(rel_path, content)

    def _extract_sql_file(self, rel_path: str, content: str) -> list[CodeFact]:
        """
        Extract a single CodeFact from a GreenAI SQL file.
        One fact per SQL file at line 1 — this is the canonical evidence anchor
        that allows CapabilityValidator to verify references like File.sql:1.
        """
        domain_hint = self._infer_domain(rel_path)
        filename_no_ext = os.path.splitext(os.path.basename(rel_path))[0]

        tables = list(dict.fromkeys(_TABLE_RE.findall(content)))
        sql_ops = list(dict.fromkeys(op.upper() for op in _SQL_OP_RE.findall(content)))
        filters = list(dict.fromkeys(_FILTER_RE.findall(content)))

        # Extract @Parameter names as additional filter evidence
        sql_params = list(dict.fromkeys(_SQL_PARAM_RE.findall(content)))[:12]
        for p in sql_params:
            hint = f"@{p}"
            if hint not in filters:
                filters.append(hint)

        fact = CodeFact(
            file=f"{rel_path}:1",
            class_name="SQL",
            method=filename_no_ext,
            params=sql_params[:8],
            calls=[],
            tables=tables,
            sql_ops=sql_ops,
            filters=filters,
            returns="",
            http_route=None,
            http_method=None,
            domain_hint=domain_hint,
            raw_snippet=content[:300],
        )
        return [fact]
