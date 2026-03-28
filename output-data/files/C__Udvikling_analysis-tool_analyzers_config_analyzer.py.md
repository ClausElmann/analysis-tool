# File Analysis

## Metadata
- Project: analyzers
- Path: C:\Udvikling\analysis-tool\analyzers\config_analyzer.py
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
"""Configuration signal extraction analyzer."""

import re

from analyzers.base_analyzer import BaseAnalyzer


class ConfigAnalyzer(BaseAnalyzer):
    def analyze(self, file_path: str, content: str, analysis):
        json_like_keys = re.findall(r'''"([A-Za-z0-9_\-\.]+)"\s*:''', content)
        yaml_like_keys = re.findall(r'''^\s*([A-Za-z0-9_\-\.]+)\s*:''', content, re.MULTILINE)
        urls = re.findall(r'''https?://[^\s"']+''', content)
        integration_hints = []
        for key in json_like_keys + yaml_like_keys:
            lower_key = key.lower()
            if "connection" in lower_key or "endpoint" in lower_key or "url" in lower_key:
                integration_hints.append(key)

        analysis.summary = "Configuration file analyzed for keys and integration hints."
        analysis.key_elements["keys"] = sorted(set(json_like_keys + yaml_like_keys))[:200]
        analysis.domain_signals["integration_hints"] = sorted(set(integration_hints))
        analysis.dependencies["u
```
