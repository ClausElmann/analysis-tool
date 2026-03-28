# File Analysis

## Metadata
- Project: core
- Path: C:\Udvikling\analysis-tool\core\pipeline.py
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
"""Pipeline orchestration for the analysis engine.

Flow:
1. Classify each file.
2. Create a normalized FileAnalysis object.
3. Read content safely.
4. Route the file to a matching analyzer.
5. Return a uniform list of results for reporting.
"""

from analyzers.angular_analyzer import AngularAnalyzer
from analyzers.batch_analyzer import BatchAnalyzer
from analyzers.config_analyzer import ConfigAnalyzer
from analyzers.csharp_analyzer import CSharpAnalyzer
from analyzers.sql_analyzer import SqlAnalyzer
from core.file_classifier import FileClassifier
from core.model import FileAnalysis
from utils.file_utils import detect_project_name


class Pipeline:
    def __init__(self, root_path: str) -> None:
        self.root_path = root_path
        self.classifier = FileClassifier()
        self.csharp_analyzer = CSharpAnalyzer()
        self.sql_analyzer = SqlAnalyzer()
        self.angular_analyzer = AngularAnalyzer()
        self.config_analyzer = ConfigAnalyzer()
        self.batch_analyzer =
```
