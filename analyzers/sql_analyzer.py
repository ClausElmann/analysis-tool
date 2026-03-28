"""SQL signal extraction analyzer.

This analyzer extracts table, procedure, view, and query-like signals from SQL
scripts. It does not attempt full SQL parsing across all dialect variations.
"""

import re

from analyzers.base_analyzer import BaseAnalyzer


class SqlAnalyzer(BaseAnalyzer):
    def analyze(self, file_path: str, content: str, analysis):
        tables = re.findall(r"\bcreate\s+table\s+(?:\[?\w+\]?\.)?\[?(\w+)\]?", content, re.IGNORECASE)
        views = re.findall(r"\bcreate\s+view\s+(?:\[?\w+\]?\.)?\[?(\w+)\]?", content, re.IGNORECASE)
        procedures = re.findall(r"\bcreate\s+(?:proc|procedure)\s+(?:\[?\w+\]?\.)?\[?(\w+)\]?", content, re.IGNORECASE)
        functions = re.findall(r"\bcreate\s+function\s+(?:\[?\w+\]?\.)?\[?(\w+)\]?", content, re.IGNORECASE)
        referenced_tables = re.findall(r"\b(?:from|join|into|update)\s+(?:\[?\w+\]?\.)?\[?(\w+)\]?", content, re.IGNORECASE)
        columns = re.findall(r"\[?(\w+)\]?\s+(?:int|bigint|nvarchar|varchar|datetime|bit|decimal|uniqueidentifier)", content, re.IGNORECASE)

        keywords = []
        for keyword in ["status", "type", "code", "id", "date"]:
            if re.search(rf"\b{keyword}\b", content, re.IGNORECASE):
                keywords.append(keyword)

        analysis.summary = "SQL file analyzed for database object signals."
        analysis.key_elements["tables_created"] = sorted(set(tables))
        analysis.key_elements["views_created"] = sorted(set(views))
        analysis.key_elements["procedures_created"] = sorted(set(procedures))
        analysis.key_elements["functions_created"] = sorted(set(functions))
        analysis.key_elements["tables_referenced"] = sorted(set(referenced_tables))
        analysis.domain_signals["keywords"] = keywords
        analysis.domain_signals["columns_detected"] = sorted(set(columns))[:100]
        analysis.dependencies["database_objects"] = sorted(set(referenced_tables + tables + views + procedures + functions))
        analysis.raw_extract = content[:1000]

        if not any([tables, views, procedures, functions]):
            analysis.risks_notes.append("SQL file contains queries or scripts but no created objects were detected")
