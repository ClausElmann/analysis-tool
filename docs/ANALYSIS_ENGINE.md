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

- CSharpAnalyzer: classes, interfaces, methods, HTTP attributes, namespaces, basic domain keywords.
- SqlAnalyzer: tables, procedures, views, functions, referenced tables, column-like names, domain keywords.
- AngularAnalyzer: components, selectors, routes, template references, HTTP calls, forms.
- ConfigAnalyzer: keys, URL hints, integration hints.
- BatchAnalyzer: job names, commands, schedule-like expressions.

## How output can be used later

- Build a domain glossary from repeated keywords, routes, tables, and class names.
- Map capabilities by combining backend endpoints, frontend routes, and database objects.
- Identify legacy hotspots by looking at dense dependencies and repeated keywords.
- Create a candidate list for a new lightweight system.

## Limitations

- Results are heuristic.
- Regex-based extraction may miss complex syntax.
- A file may be classified correctly but still contain weak signals.
- The output is intended for human review plus LLM-assisted synthesis.

## Extension approach

1. Add a new analyzer in `analyzers/`.
2. Populate the shared `FileAnalysis` model.
3. Register the analyzer in `core/pipeline.py`.
4. Optionally extend summary reports in `output/report_writer.py`.
