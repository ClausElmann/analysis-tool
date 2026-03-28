# File Analysis

## Metadata
- Project: utils
- Path: C:\Udvikling\analysis-tool\utils\file_utils.py
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
"""File utility helpers."""

import os
import re


def safe_filename(path: str) -> str:
    safe = path.replace(":", "_")
    return re.sub(r"[^a-zA-Z0-9._-]", "_", safe)


def detect_project_name(file_path: str, root_path: str) -> str:
    relative_path = os.path.relpath(file_path, root_path)
    parts = relative_path.split(os.sep)
    return parts[0] if parts else "root"

```
