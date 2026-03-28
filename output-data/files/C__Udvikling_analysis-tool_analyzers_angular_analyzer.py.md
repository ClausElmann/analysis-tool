# File Analysis

## Metadata
- Project: analyzers
- Path: C:\Udvikling\analysis-tool\analyzers\angular_analyzer.py
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
"""Angular signal extraction analyzer.

This analyzer extracts lightweight signals from Angular-related files such as
components, services, routes, selectors, templates, and HTTP calls.
"""

import os
import re

from analyzers.base_analyzer import BaseAnalyzer


class AngularAnalyzer(BaseAnalyzer):
    def analyze(self, file_path: str, content: str, analysis):
        file_name = os.path.basename(file_path).lower()
        classes = re.findall(r"\bexport\s+class\s+(\w+)", content)
        selectors = re.findall(r'''selector\s*:\s*["']([^"']+)["']''', content)
        templates = re.findall(r'''templateUrl\s*:\s*["']([^"']+)["']''', content)
        routes = re.findall(r'''path\s*:\s*["']([^"']+)["']''', content)
        http_calls = re.findall(r"\.\s*(get|post|put|delete|patch)\s*\(", content, re.IGNORECASE)
        forms = re.findall(r"\b(FormGroup|FormControl|Validators)\b", content)

        roles = []
        if ".component." in file_name:
            roles.append("component")
    
```
