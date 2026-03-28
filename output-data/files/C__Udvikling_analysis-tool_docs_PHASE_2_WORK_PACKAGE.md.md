# File Analysis

## Metadata
- Project: docs
- Path: C:\Udvikling\analysis-tool\docs\PHASE_2_WORK_PACKAGE.md
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
# Phase 2 – Core Analyzers: Work Package

## Ordered Implementation Tasks

1. CSharpAnalyzer
2. SqlAnalyzer
3. AngularAnalyzer
4. ConfigAnalyzer
5. BatchAnalyzer

---

## Analyzer Specifications

### 1. CSharpAnalyzer
- **Purpose:** Extract structural and domain signals from C# source files.
- **Input file types:** .cs
- **Signals to extract:**
  - classes
  - interfaces
  - methods
  - endpoints ([HttpGet], [HttpPost], [HttpPut], [HttpDelete], [Http*] custom)
  - domain keywords (from domain_keywords.json or default)
  - dependencies (using statements)
- **Output fields to populate in FileAnalysis:**
  - key_elements (all above signals)
  - domain_signals
  - dependencies
  - raw_extract (first 1000 chars)
  - analysis_status
  - analysis_warnings
- **Failure behavior:**
  - Set analysis_status to 'failed', populate analysis_warnings with error details, output empty key_elements.
- **Warnings behavior:**
  - Set analysis_status to 'partial', populate analysis_warnings with specific is
```
