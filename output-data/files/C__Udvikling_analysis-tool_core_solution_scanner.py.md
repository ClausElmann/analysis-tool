# File Analysis

## Metadata
- Project: core
- Path: C:\Udvikling\analysis-tool\core\solution_scanner.py
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
"""Directory scanner for collecting candidate files."""

import os
from typing import List


class SolutionScanner:
    def __init__(self) -> None:
        self.ignore_dirs = {
            "bin",
            "obj",
            "node_modules",
            "dist",
            ".git",
            ".angular",
            ".vs",
            ".idea",
            "coverage",
            "TestResults",
            "packages",
        }
        self.ignore_ext = {".dll", ".exe", ".pdb", ".cache", ".zip"}

    def scan(self, root_path: str) -> List[str]:
        results: List[str] = []
        for root, dirs, files in os.walk(root_path):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            for file_name in files:
                _, ext = os.path.splitext(file_name)
                if ext.lower() in self.ignore_ext:
                    continue
                results.append(os.path.join(root, file_name))
        return results

```
