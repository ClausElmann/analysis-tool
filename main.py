"""CLI entry point for the analysis tool."""

import os
import sys

from core.solution_scanner import SolutionScanner
from core.pipeline import Pipeline
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

    print(f"[1/4] Scanning: {root_path}")
    scanner = SolutionScanner()
    files = scanner.scan(root_path)
    print(f"Found {len(files)} candidate files")

    print("[2/4] Analyzing files")
    pipeline = Pipeline(root_path=root_path)
    analyses = pipeline.run(files)
    print(f"Analyzed {len(analyses)} files")

    print("[3/4] Writing detailed outputs")
    MarkdownWriter(output_root="output-data").write(analyses)
    JsonWriter(output_root="output-data").write(analyses)

    print("[4/4] Writing summary reports")
    ReportWriter(output_root="output-data").write(analyses)

    print("Done. Output written to output-data/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
