# File Analysis

## Metadata
- Project: analyzers
- Path: C:\Udvikling\analysis-tool\analyzers\batch_analyzer.py
- Type: batch
- Technology: Batch / Scheduler

## Summary
Batch or scheduler related file analyzed for operational signals.

## Key Elements
```json
{
  "job_names": [
    "Job",
    "Loader",
    "Scheduler",
    "Task",
    "Worker"
  ],
  "schedule_expressions": []
}
```

## Domain Signals
```json
{
  "commands": [
    "execute",
    "resume",
    "retry",
    "run",
    "start",
    "stop"
  ]
}
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
"""Batch and scheduler signal extraction analyzer."""

import re

from analyzers.base_analyzer import BaseAnalyzer


class BatchAnalyzer(BaseAnalyzer):
    def analyze(self, file_path: str, content: str, analysis):
        cron_like = re.findall(r"\b(?:\*|\d+|/|-|,){5,}\b", content)
        job_names = re.findall(r"\b(\w*(?:Job|Worker|Scheduler|Task|Loader))\b", content)
        commands = re.findall(r"\b(start|run|execute|retry|resume|stop)\b", content, re.IGNORECASE)

        analysis.summary = "Batch or scheduler related file analyzed for operational signals."
        analysis.key_elements["job_names"] = sorted(set(job_names))
        analysis.key_elements["schedule_expressions"] = sorted(set(cron_like))
        analysis.domain_signals["commands"] = [cmd.lower() for cmd in sorted(set(commands))]
        analysis.raw_extract = content[:1000]

        if not job_names and not cron_like:
            analysis.risks_notes.append("Batch file classification matched but no explicit job or s
```
