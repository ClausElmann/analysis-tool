# File Analysis

## Metadata
- Project: core
- Path: C:\Udvikling\analysis-tool\core\file_classifier.py
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
"""File classification logic used before analyzer selection."""

import os


class FileClassifier:
    def classify(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        name = os.path.basename(file_path).lower()

        if ext == ".cs":
            return "csharp"
        if ext == ".sql":
            return "sql"
        if ext in {".ts", ".html", ".scss"}:
            return "angular"
        if ext in {".json", ".yaml", ".yml", ".xml", ".config"}:
            return "config"
        if "batch" in name or "scheduler" in name or "job" in name or ext in {".ps1", ".cmd", ".bat"}:
            return "batch"
        return "unknown"

    def technology_for_type(self, file_type: str) -> str:
        mapping = {
            "csharp": ".NET / C#",
            "sql": "SQL",
            "angular": "Angular / Web",
            "config": "Configuration",
            "batch": "Batch / Scheduler",
            "unknown": "Unknown",
        }
        return map
```
