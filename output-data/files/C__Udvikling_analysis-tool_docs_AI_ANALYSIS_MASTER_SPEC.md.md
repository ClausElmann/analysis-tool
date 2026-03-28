# File Analysis

## Metadata
- Project: docs
- Path: C:\Udvikling\analysis-tool\docs\AI_ANALYSIS_MASTER_SPEC.md
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
# AI Analysis Tool – Master Specification

## 1. Purpose

This project builds a **codebase analysis engine** designed to reverse engineer a large legacy system.

The system consists of:

* .NET Web API (C#)
* Azure SQL database
* Batch/scheduler applications
* Angular frontend

The goal is NOT to refactor the system directly.

The goal is to:

1. Extract ALL meaningful signals from the codebase
2. Build a complete **domain understanding**
3. Identify **capabilities and business logic**
4. Enable a future rebuild:

   * new architecture
   * new database model
   * new backend
   * Blazor frontend

---

## 2. Core Principle: Signal Extraction

This tool does NOT attempt full parsing or full correctness.

Instead, it performs:

> **Signal Extraction**

Meaning:

* Detect patterns
* Extract structural elements
* Identify domain indicators
* Collect hints about behavior

This approach is:

* fast
* robust
* scalable
* sufficient for domain reconstruction

---

## 3. What This Tool Must Do

```
