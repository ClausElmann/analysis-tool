# File Analysis

## Metadata
- Project: docs
- Path: C:\Udvikling\analysis-tool\docs\CAPABILITY_EXTRACTOR_DESIGN.md
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
# CapabilityExtractor – Detailed Design

Source of truth: AI_ANALYSIS_MASTER_SPEC.md, Section [PHASE 4 – CAPABILITY MODEL]

---

## 1. Function Extraction Rules

### 1.1 From C# Endpoints

- **Source:** `key_elements.endpoints` in FileAnalysis for files with `type = "csharp"`
- **One function per endpoint entry.**
- **Name:** `endpoint.method` verbatim (e.g., `GetCustomer`)
- **Type:** `"API"`
- **Inputs:**
  - Extract parameter names from the method signature regex: `\w+\s+(\w+)` inside `(\s*...\s*)` following the method name
  - If not extractable: `[]`
- **Outputs:**
  - Extract return type from the method signature regex: `(public|private|protected|internal)\s+([\w<>\[\]]+)\s+MethodName`
  - If return type is `void`, `Task`, or `IActionResult` → `[]`
  - If return type is a concrete type → `[return_type]`
  - If not extractable: `[]`
- **source_files:** `[file_path]` of the file where found
- **dependencies:** `key_elements.dependencies.namespaces` from the same file
- **descriptio
```
