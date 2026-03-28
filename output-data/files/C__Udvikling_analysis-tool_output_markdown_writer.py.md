# File Analysis

## Metadata
- Project: output
- Path: C:\Udvikling\analysis-tool\output\markdown_writer.py
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
"""Detailed markdown output writer."""

import json
import os

from utils.file_utils import safe_filename


class MarkdownWriter:
    def __init__(self, output_root: str = "output-data") -> None:
        self.output_root = output_root

    def write(self, analyses) -> None:
        files_dir = os.path.join(self.output_root, "files")
        os.makedirs(files_dir, exist_ok=True)
        for analysis in analyses:
            file_name = safe_filename(analysis.path) + ".md"
            target = os.path.join(files_dir, file_name)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(self._render(analysis))

    def _render(self, analysis) -> str:
        return """# File Analysis

## Metadata
- Project: {project}
- Path: {path}
- Type: {type_}
- Technology: {technology}

## Summary
{summary}

## Key Elements
```json
{key_elements}
```

## Domain Signals
```json
{domain_signals}
```

## Dependencies
```json
{dependencies}
```

## Inputs and Outputs
```
```
