# File Analysis

## Metadata
- Project: docs
- Path: C:\Udvikling\analysis-tool\docs\ANALYSIS_ENGINE.md
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
# Analysis Engine

## Purpose

The tool creates a structured textual inventory of a large legacy solution. It is built to support later domain analysis, capability mapping, and redesign work.

## What signal extraction means

Signal extraction means the tool looks for useful patterns rather than attempting perfect semantic understanding. This is deliberate. Large mixed-codebase solutions contain many technologies, generated files, and inconsistent coding styles. A lightweight approach is more robust in the first discovery phase.

## Why full parsing is not used

Full parsing for every technology would make the tool slower, more fragile, and much harder to evolve. The first goal is breadth and repeatability, not compiler-grade precision.

## FileAnalysis model

Every analyzer writes into the same normalized model. This makes it possible to compare C#, SQL, Angular, config, and batch files using one shared schema.

## Analyzer overview

- CSharpAnalyzer: classes, interfaces, methods, HTT
```
