# File Analysis

## Metadata
- Project: output
- Path: C:\Udvikling\analysis-tool\output\report_writer.py
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
"""Writes higher-level summary reports from per-file analyses."""

import collections
import os


class ReportWriter:
    def __init__(self, output_root: str = "output-data") -> None:
        self.output_root = output_root

    def write(self, analyses) -> None:
        os.makedirs(self.output_root, exist_ok=True)
        self._write_solution_overview(analyses)
        self._write_project_catalog(analyses)
        self._write_domain_capabilities(analyses)

    def _write_solution_overview(self, analyses) -> None:
        counts_by_type = collections.Counter(a.type for a in analyses)
        counts_by_project = collections.Counter(a.project for a in analyses)
        lines = ["# Solution Overview", "", f"Total analyzed files: {len(analyses)}", "", "## File Types"]
        for file_type, count in sorted(counts_by_type.items()):
            lines.append(f"- {file_type}: {count}")
        lines.append("")
        lines.append("## Projects")
        for project, count in sorted(counts_by_pr
```
