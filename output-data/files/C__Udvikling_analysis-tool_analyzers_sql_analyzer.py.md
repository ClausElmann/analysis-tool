# File Analysis

## Metadata
- Project: analyzers
- Path: C:\Udvikling\analysis-tool\analyzers\sql_analyzer.py
- Type: unknown
- Technology: Unknown

## Summary
No specialized analyzer assigned.

## Key Elements
```json
{}
```

## Domain Signals
```json
{}
```

## Dependencies
```json
{}
```

## Inputs and Outputs
```json
{}
```

## Risks / Notes
```json
[]
```

## Raw Extract
```text
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
        columns = re.findall(r"\[?(\w+)\]?\s+(?:int|bigint|nvarchar|varchar|datetime|bi
```
