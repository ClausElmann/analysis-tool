# File Analysis

## Metadata
- Project: analyzers
- Path: C:\Udvikling\analysis-tool\analyzers\csharp_analyzer.py
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
"""C# signal extraction analyzer.

This analyzer extracts lightweight structural signals from C# source files.
It is not a full parser and does not guarantee semantic correctness.
It is designed for large-solution inventory work where speed and broad coverage
matter more than perfect understanding of every file.
"""

import re

from analyzers.base_analyzer import BaseAnalyzer


class CSharpAnalyzer(BaseAnalyzer):
    def analyze(self, file_path: str, content: str, analysis):
        classes = re.findall(r"\bclass\s+(\w+)", content)
        interfaces = re.findall(r"\binterface\s+(\w+)", content)
        method_pattern = re.compile(
            r"\b(?:public|private|protected|internal)\s+(?:async\s+)?[\w<>,\[\]?]+\s+(\w+)\s*\(",
            re.MULTILINE,
        )
        methods = method_pattern.findall(content)
        endpoint_pattern = re.compile(r"\[(HttpGet|HttpPost|HttpPut|HttpDelete|Route)\b[^\]]*\]", re.MULTILINE)
        endpoints = endpoint_pattern.findall(content)

        k
```
