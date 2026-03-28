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
        for project, count in sorted(counts_by_project.items()):
            lines.append(f"- {project}: {count}")
        self._write_file("00_solution_overview.md", "\n".join(lines))

    def _write_project_catalog(self, analyses) -> None:
        by_project = collections.defaultdict(list)
        for analysis in analyses:
            by_project[analysis.project].append(analysis)
        lines = ["# Project Catalog", ""]
        for project in sorted(by_project):
            lines.append(f"## {project}")
            lines.append("")
            for analysis in sorted(by_project[project], key=lambda item: item.path):
                lines.append(f"- `{analysis.type}` {analysis.path}")
            lines.append("")
        self._write_file("01_project_catalog.md", "\n".join(lines))

    def _write_domain_capabilities(self, analyses) -> None:
        keyword_counter = collections.Counter()
        routes = []
        tables = []
        for analysis in analyses:
            for keyword in analysis.domain_signals.get("keywords", []):
                keyword_counter[keyword] += 1
            routes.extend(analysis.key_elements.get("routes", []))
            tables.extend(analysis.key_elements.get("tables_created", []))
            tables.extend(analysis.key_elements.get("tables_referenced", []))
        lines = [
            "# Domain Capability Signals",
            "",
            "This report is heuristic. It highlights repeated technical and domain clues that can later be grouped into business capabilities.",
            "",
            "## Frequent Domain Keywords",
        ]
        for keyword, count in keyword_counter.most_common():
            lines.append(f"- {keyword}: {count}")
        lines.append("")
        lines.append("## Routes Detected")
        for route in sorted(set(routes))[:200]:
            lines.append(f"- {route}")
        lines.append("")
        lines.append("## Database Objects Detected")
        for table in sorted(set(tables))[:200]:
            lines.append(f"- {table}")
        self._write_file("08_domain_capabilities.md", "\n".join(lines))

    def _write_file(self, name: str, content: str) -> None:
        with open(os.path.join(self.output_root, name), "w", encoding="utf-8") as handle:
            handle.write(content)
