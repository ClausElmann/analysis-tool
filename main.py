# LEGACY — DO NOT RUN
# This script is superseded by run_domain_engine.py (Gen 3 canonical entrypoint).
# Retained for reference only. Running this file may corrupt domain state.
"""CLI entry point for the analysis tool."""

import os
import sys

from core.solution_scanner import SolutionScanner
from core.pipeline import Pipeline
from core.coverage_analyzer import CoverageAnalyzer
from core.data_model_extractor import DataModelExtractor
from output.markdown_writer import MarkdownWriter
from output.json_writer import JsonWriter
from output.report_writer import ReportWriter


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python main.py <root_path>")
        return 1

    root_path = os.path.abspath(sys.argv[1])
    if not os.path.isdir(root_path):
        print(f"Input folder does not exist: {root_path}")
        return 1

    print(f"[1/6] Scanning: {root_path}")
    scanner = SolutionScanner()
    files = scanner.scan(root_path)
    print(f"Found {len(files)} candidate files")

    print("[2/6] Analyzing files")
    pipeline = Pipeline(root_path=root_path)
    analyses = pipeline.run(files)
    print(f"Analyzed {len(analyses)} files")

    print("[3/6] Writing detailed outputs")
    MarkdownWriter(output_root="output-data").write(analyses)
    JsonWriter(output_root="output-data").write(analyses)

    print("[4/6] Writing summary reports")
    ReportWriter(output_root="output-data").write(analyses)

    print("[5/6] Extracting data model")
    data_model = DataModelExtractor(output_root="output-data").extract()
    print(f"Data model: {len(data_model['tables'])} tables")

    print("[6/6] Computing coverage")
    coverage = CoverageAnalyzer(output_root="output-data").analyze()
    print(
        f"Coverage — UI: {coverage['ui']['covered']}/{coverage['ui']['total']}  "
        f"API: {coverage['api']['used']}/{coverage['api']['total']}  "
        f"SQL: {coverage['sql']['used']}/{coverage['sql']['total']}"
    )

    print("Done. Output written to output-data/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
