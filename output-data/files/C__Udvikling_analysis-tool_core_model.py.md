# File Analysis

## Metadata
- Project: core
- Path: C:\Udvikling\analysis-tool\core\model.py
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
"""Shared data model used by the analysis pipeline."""

from dataclasses import asdict, dataclass, field
from typing import Dict, List


@dataclass
class FileAnalysis:
    """Represents a normalized analysis result for a single file."""

    project: str = ""
    path: str = ""
    type: str = ""
    technology: str = ""
    summary: str = ""
    key_elements: Dict[str, List[str]] = field(default_factory=dict)
    domain_signals: Dict[str, List[str]] = field(default_factory=dict)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    inputs_outputs: Dict[str, List[str]] = field(default_factory=dict)
    risks_notes: List[str] = field(default_factory=list)
    raw_extract: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

```
