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
```json
{inputs_outputs}
```

## Risks / Notes
```json
{risks_notes}
```

## Raw Extract
```text
{raw_extract}
```
""".format(
            project=analysis.project,
            path=analysis.path,
            type_=analysis.type,
            technology=analysis.technology,
            summary=analysis.summary,
            key_elements=json.dumps(analysis.key_elements, indent=2, ensure_ascii=False),
            domain_signals=json.dumps(analysis.domain_signals, indent=2, ensure_ascii=False),
            dependencies=json.dumps(analysis.dependencies, indent=2, ensure_ascii=False),
            inputs_outputs=json.dumps(analysis.inputs_outputs, indent=2, ensure_ascii=False),
            risks_notes=json.dumps(analysis.risks_notes, indent=2, ensure_ascii=False),
            raw_extract=analysis.raw_extract,
        )
