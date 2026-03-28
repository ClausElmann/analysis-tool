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

The system must:

### 3.1 Scan

* Traverse entire solution
* Identify all relevant files
* Ignore irrelevant artifacts

### 3.2 Classify

Each file must be classified as:

* csharp
* sql
* angular
* config
* batch
* unknown

---

### 3.3 Analyze (Per Technology)

Each analyzer extracts signals:

#### CSharpAnalyzer

* classes
* interfaces
* methods
* endpoints (HttpGet/Post/Put/Delete)
* domain keywords (status, type, code, id, date)
* dependencies (using statements)

#### SqlAnalyzer

* tables
* columns
* primary keys
* foreign keys
* stored procedures
* views
* joins
* where conditions

#### AngularAnalyzer

* components
* services
* API calls
* routes
* forms

#### BatchAnalyzer

* jobs
* triggers
* schedules
* data flows

#### ConfigAnalyzer

* connection strings
* feature flags
* environment variables
* integration endpoints

---

### 3.4 Store Results

All analysis must be stored in:

#### FileAnalysis model

Fields:

* metadata
* summary
* key_elements
* domain_signals
* dependencies
* inputs_outputs
* risks_notes
* raw_extract

---

### 3.5 Output

The tool must generate:

#### Per-file:

* Markdown analysis

#### Global:

* JSON index
* Summary reports

---

## 4. Output Purpose

The output is NOT for humans only.

It is specifically designed for:

> **LLM-driven analysis**

Meaning:

* another AI can read this output
* reconstruct domain
* propose new architecture
* generate new system

---

## 5. What We Are Trying to Discover

From the codebase, we want to extract:

### 5.1 Domain Concepts

* entities
* aggregates
* value objects

### 5.2 Business Rules

* validations
* decisions
* workflows

### 5.3 Capabilities

Examples:

* customer management
* order processing
* scheduling
* notifications
* reporting
* integrations

---

### 5.4 System Structure

* dependencies
* layering
* coupling
* boundaries

---

## 6. What Is Already Built

The system currently includes:

### Core

* solution scanner
* file classifier
* pipeline
* output writers

### Analyzers

* CSharpAnalyzer (basic)
* SQL analyzer (basic or partial)
* Angular analyzer (basic or partial)

### Output

* markdown files per source file
* JSON index

---

## 7. What Is Missing / Needs Improvement

The system is NOT complete.

Missing or weak areas:

### 7.1 Deeper SQL Analysis

* relationships
* data flows
* business rules in queries

### 7.2 Capability Extraction

* grouping signals into capabilities
* identifying workflows

### 7.3 Dependency Mapping

* cross-project dependencies
* service relationships

### 7.4 Domain Synthesis

* mapping signals into domain model
* identifying bounded contexts

### 7.5 Noise Reduction

* filtering irrelevant signals
* deduplicating concepts

---

## 8. Rules for Further Development

When extending this system:

### DO:

* keep analyzers simple
* extract signals, not full truth
* write deterministic output
* document everything
* keep modules isolated

### DO NOT:

* attempt full parsing
* over-engineer
* introduce heavy dependencies
* mix responsibilities

---

## 9. Development Strategy

All work must follow:

1. Small incremental steps
2. One module at a time
3. Test output continuously
4. Validate usefulness for domain extraction

---

## 10. End Goal

The final result of this tool is:

A complete **machine-readable description of the system**

Which can be used to:

* design new architecture
* generate new backend
* generate new database
* generate new frontend

---

## 11. Critical Success Criteria

The tool is successful when:

* we can list ALL capabilities of the system
* we understand ALL core workflows
* we can ignore legacy noise
* we can confidently rebuild a "light version"

---

## 12. Instruction for AI Agents (Copilot / GPT)

When working on this project:

* Always follow this document
* Do not guess system behavior
* Extract signals only
* Keep output structured
* Never break existing pipeline
* Extend step-by-step

If uncertain:
→ write "UNKNOWN"

---

## [RESOLUTIONS]

1. **Problem: Ambiguity in "Relevant Files" (Section 3.1 Scan)**
   - Decision: A file is "relevant" if it matches a recognized extension for any supported technology (.cs, .sql, .ts, .js, .json, .yml, .yaml, .config, .xml, .bat, .cmd, .sh) or is referenced in a project/solution file. All others are ignored.
   - Implementation rule: Maintain a configurable list of relevant extensions and parse project/solution files for explicit inclusions.
   - Impact on system: Scanning is deterministic and extensible; no ambiguity in file inclusion.

2. **Problem: Unclear File Classification Boundaries (Section 3.2 Classify)**
   - Decision: File classification is based on extension and, if ambiguous, on content heuristics. TypeScript (.ts) and HTML in Angular folders are "angular"; YAML/JSON config files are "config"; files matching multiple categories are classified by a priority order: csharp > sql > angular > batch > config > unknown.
   - Implementation rule: Add a classification priority table and explicit mapping for ambiguous cases.
   - Impact on system: All files are classified unambiguously; multi-category files follow a strict rule.

3. **Problem: Domain Keyword List Limitation (Section 3.3 CSharpAnalyzer)**
   - Decision: Domain keywords are loaded from a project-level configuration file (domain_keywords.json). If not present, use the default list.
   - Implementation rule: Analyzer loads keywords at startup; users can extend or override the list per project.
   - Impact on system: Domain signal extraction is project-adaptable and future-proof.

4. **Problem: Ambiguity in "Endpoints" Extraction (Section 3.3 CSharpAnalyzer)**
   - Decision: All methods with [HttpGet], [HttpPost], [HttpPut], [HttpDelete], or any custom attribute matching pattern [Http*] are extracted. Non-standard or custom HTTP methods are flagged with an "attribute_type: custom" field.
   - Implementation rule: Endpoint extraction regex is extended; output includes attribute_type (standard/custom).
   - Impact on system: All endpoints are captured and flagged for review; no silent omission.

5. **Problem: Lack of SQL Dialect/Platform Guidance (Section 3.3 SqlAnalyzer)**
   - Decision: Only T-SQL (Azure SQL, SQL Server) is supported. If other dialects are detected, analysis proceeds but a warning is added to the FileAnalysis.risks_notes.
   - Implementation rule: Analyzer checks for dialect-specific syntax and flags unsupported dialects.
   - Impact on system: SQL analysis is reliable for T-SQL; other dialects are not silently misinterpreted.

6. **Problem: No Definition of "Summary Reports" (Section 3.5 Output)**
   - Decision: Summary reports are JSON files containing: total files per category, top 20 domain keywords, endpoint counts, cross-file dependency graph, and a list of files with analysis warnings/errors.
   - Implementation rule: Output module generates summary.json with these fields after each run.
   - Impact on system: Stakeholders and LLMs have a clear, structured summary for further processing.

7. **Problem: Unclear Handling of Partial/Failed Analysis (Section 3.4 Store Results)**
   - Decision: FileAnalysis gains two new fields: analysis_status (success/partial/failed) and analysis_warnings (list of strings).
   - Implementation rule: All analyzers must set these fields if any part of analysis fails or is incomplete.
   - Impact on system: Downstream consumers can reliably detect and handle incomplete results.

8. **Problem: Ambiguity in "Noise Reduction" (Section 7.5)**
   - Decision: Noise is defined as signals not matching any domain keyword, not referenced in code, or duplicated across files. Filtering is configurable via noise_filter_rules.json.
   - Implementation rule: Add a noise reduction module that applies these rules post-analysis.
   - Impact on system: Signal extraction is tunable and traceable; risk of losing important signals is minimized by configuration.

9. **Problem: No Guidance on Cross-File/Project Relationships (Section 7.3 Dependency Mapping)**
   - Decision: Cross-file dependencies are detected via import/include/using statements and project references. Service relationships are inferred from API call patterns and config endpoints.
   - Implementation rule: Dependency mapping module parses references and outputs a dependency graph in summary.json.
   - Impact on system: System structure and service boundaries are machine-readable and explicit.

10. **Problem: Unclear Versioning and Extensibility Strategy (Section 8, Rules for Further Development)**
    - Decision: All analyzers and output formats must include a version field. New analyzers or file types are added via a plugin interface.
    - Implementation rule: Add a version property to all output and a plugin loader for analyzers.
    - Impact on system: System is future-proof and extensible without breaking existing pipelines.

11. **Problem: Potential Conflict: "Extract signals, not full truth" vs. "Validate usefulness for domain extraction" (Sections 8 & 9)**
    - Decision: Each analyzer must include a "signal_coverage" metric (percentage of expected signals found) and a "domain_usefulness" flag (manual/AI reviewable).
    - Implementation rule: Output includes these metrics; review process is documented.
    - Impact on system: Tradeoff is explicit and measurable; usefulness is validated per run.

12. **Problem: No Explicit Test or Quality Criteria (Section 9, Development Strategy)**
    - Decision: A test suite with sample inputs/outputs and regression checks is mandatory. "Good" output is defined by 95%+ signal coverage and zero critical errors in summary.json.
    - Implementation rule: Add tests and output validation scripts; document criteria in README.
    - Impact on system: Quality is measurable and regressions are caught early.

---

## [BUILD PLAN]

### Phase 1 – Foundation

**Goal:** Establish the core infrastructure for scanning, classifying, processing, and outputting analysis results.

**Modules to implement:**
- SolutionScanner
- FileClassifier
- Pipeline
- OutputWriters (Markdown, JSON)

**Exact tasks:**
1. Implement SolutionScanner
   - Description: Traverse the root directory and project/solution files to enumerate all files.
   - Input: Root path
   - Output: List of file paths
   - Acceptance criteria: All files matching relevant extensions or referenced in project/solution files are listed.
2. Implement FileClassifier
   - Description: Classify each file by extension and content heuristics using the priority table.
   - Input: List of file paths
   - Output: List of (file path, category)
   - Acceptance criteria: Every file is assigned exactly one category; ambiguous cases resolved by priority.
3. Implement Pipeline
   - Description: Orchestrate the flow: scan → classify → analyze → output.
   - Input: Root path
   - Output: Triggers all downstream modules; manages process state
   - Acceptance criteria: Pipeline runs end-to-end and produces output for all files.
4. Implement OutputWriters
   - Description: Write per-file Markdown and global JSON index.
   - Input: Analysis results
   - Output: Markdown files, JSON index
   - Acceptance criteria: All analyzed files have Markdown output; global index is valid JSON.

**Dependencies:** None (foundation phase)
**Expected output artifacts:**
- List of all relevant files
- File classification report
- Per-file Markdown
- Global JSON index

---

### Phase 2 – Core Analyzers

**Goal:** Extract structural and domain signals for each supported technology.

**Modules to implement:**
- CSharpAnalyzer
- SqlAnalyzer
- AngularAnalyzer
- ConfigAnalyzer
- BatchAnalyzer

**Exact tasks:**
1. Implement CSharpAnalyzer
   - Description: Extract classes, interfaces, methods, endpoints, domain keywords, dependencies from .cs files.
   - Input: .cs file content
   - Output: Structured analysis dict
   - Acceptance criteria: All required signals are extracted and present in output.
2. Implement SqlAnalyzer
   - Description: Extract tables, columns, keys, procedures, views, joins, where conditions from .sql files.
   - Input: .sql file content
   - Output: Structured analysis dict
   - Acceptance criteria: All required SQL signals are extracted; unsupported dialects flagged.
3. Implement AngularAnalyzer
   - Description: Extract components, services, API calls, routes, forms from Angular files.
   - Input: .ts, .html, .js files in Angular folders
   - Output: Structured analysis dict
   - Acceptance criteria: All required Angular signals are extracted.
4. Implement ConfigAnalyzer
   - Description: Extract connection strings, feature flags, env variables, integration endpoints from config files.
   - Input: .json, .yml, .yaml, .config, .xml files
   - Output: Structured analysis dict
   - Acceptance criteria: All required config signals are extracted.
5. Implement BatchAnalyzer
   - Description: Extract jobs, triggers, schedules, data flows from batch files.
   - Input: .bat, .cmd, .sh files
   - Output: Structured analysis dict
   - Acceptance criteria: All required batch signals are extracted.

**Dependencies:** Foundation phase complete
**Expected output artifacts:**
- Per-file analysis JSON/Markdown with all required signals
- Analysis warnings/errors for unsupported or partial files

---

### Phase 3 – Cross-Analysis

**Goal:** Map dependencies and generate global summary reports.

**Modules to implement:**
- DependencyMapping
- SummaryReportGenerator

**Exact tasks:**
1. Implement DependencyMapping
   - Description: Parse import/include/using statements and project references to build a dependency graph.
   - Input: All per-file analysis results
   - Output: Dependency graph (JSON)
   - Acceptance criteria: All cross-file and service dependencies are represented in the graph.
2. Implement SummaryReportGenerator
   - Description: Aggregate statistics (file counts, top domain keywords, endpoint counts, warnings/errors) into summary.json.
   - Input: All per-file analysis results
   - Output: summary.json
   - Acceptance criteria: Summary report contains all required fields and matches the spec.

**Dependencies:** Core analyzers complete
**Expected output artifacts:**
- Dependency graph (JSON)
- summary.json with all required metrics

---

### Phase 4 – Domain Intelligence

**Goal:** Extract higher-level domain and capability information from signals.

**Modules to implement:**
- CapabilityExtractor
- DomainSynthesizer

**Exact tasks:**
1. Implement CapabilityExtractor
   - Description: Group signals into business capabilities and workflows using rules and domain keywords.
   - Input: All per-file analysis results
   - Output: Capabilities report (JSON)
   - Acceptance criteria: All major system capabilities are identified and mapped.
2. Implement DomainSynthesizer
   - Description: Map signals into domain model concepts (entities, aggregates, value objects, bounded contexts).
   - Input: All per-file analysis results
   - Output: Domain model report (JSON)
   - Acceptance criteria: All core domain concepts are represented; bounded contexts are identified.

**Dependencies:** Cross-analysis complete
**Expected output artifacts:**
- Capabilities report (JSON)
- Domain model report (JSON)

---

### Phase 5 – Optimization

**Goal:** Refine analysis quality, reduce noise, and optimize performance.

**Modules to implement:**
- NoiseReductionModule
- PerformanceTuning
- TestSuite & Validation

**Exact tasks:**
1. Implement NoiseReductionModule
   - Description: Filter irrelevant or duplicate signals using noise_filter_rules.json.
   - Input: All analysis results
   - Output: Cleaned analysis results
   - Acceptance criteria: All noise is filtered as per config; no required signals are lost.
2. Implement PerformanceTuning
   - Description: Profile and optimize scanning, analysis, and output for large codebases.
   - Input: Full system
   - Output: Optimized runtime and resource usage
   - Acceptance criteria: System processes large codebases within target time/memory limits.
3. Implement TestSuite & Validation
   - Description: Add regression tests, sample input/output, and output validation scripts.
   - Input: All modules
   - Output: Test results, validation logs
   - Acceptance criteria: 95%+ signal coverage, zero critical errors, all tests pass.

**Dependencies:** All previous phases complete
**Expected output artifacts:**
- Cleaned, validated analysis results
- Performance benchmarks
- Test/validation reports

## [OUTPUT CONTRACT]

### 1. analysis-index.json Structure

Each file entry MUST have the following structure (all fields required, no nulls, deterministic order):

{
  "path": string,                        // Absolute or workspace-relative file path
  "type": string,                        // File type (e.g., "csharp", "sql", "angular", "config", "batch", "unknown")
  "technology": string,                  // Technology label (e.g., "CSharp", "TSQL", "Angular", "Config", "Batch")
  "analysis_status": "success" | "partial" | "failed",
  "analysis_warnings": [string],         // List of warning messages (empty if none)
  "key_elements": {
    "classes": [string],                 // Sorted
    "interfaces": [string],              // Sorted
    "methods": [string],                 // Sorted
    "endpoints": [
      {
        "method": string,                // Method name
        "attribute_type": "standard" | "custom"
      }
    ],
    "tables": [string],                  // Sorted
    "columns": [string],                 // Sorted
    "procedures": [string],              // Sorted
    // ...other technology-specific arrays, always present, empty if not used
  },
  "domain_signals": {
    "keywords": [string]                 // Sorted
  },
  "dependencies": {
    "namespaces": [string],              // Sorted
    "files": [string]                    // Sorted
  },
  "inputs_outputs": {},                  // Always present, empty object if not used
  "risks_notes": [string],               // List of risk/warning notes (empty if none)
  "raw_extract": string                  // First 1000 chars of file (UTF-8, may be empty)
}

- All arrays must be present and sorted lexicographically.
- All objects must have all fields, even if empty.
- No nulls allowed.
- Order of fields must match above.

---

### 2. summary.json Structure

{
  "total_files": number,                                 // Total number of files analyzed
  "files_by_type": { string: number },                  // Map: file type → count
  "top_domain_keywords": [
    { "keyword": string, "count": number }              // Sorted by count desc, then keyword asc
  ],
  "endpoint_count": number,                             // Total number of endpoints found
  "warnings_count": number,                             // Total number of warnings across all files
  "failed_files": [string]                              // Sorted list of file paths with status 'failed'
}

- All fields required, no nulls.
- Arrays sorted as specified.
- files_by_type keys sorted lexicographically.

---

### 3. dependency-graph.json Structure

{
  "nodes": [
    { "id": string, "type": string }                   // id = file path or unique identifier
  ],
  "edges": [
    { "from": string, "to": string, "type": string }   // type = dependency type (e.g., "import", "call")
  ]
}

- All fields required, no nulls.
- Arrays sorted by id (nodes) and from+to+type (edges).

---

### 4. Markdown Format (Per File)

# File Analysis

## Metadata

* Path: <file path>
* Type: <file type>
* Status: <analysis_status>

## Key Elements

(classes, interfaces, methods, endpoints, tables, columns, etc. – all present, empty if none)

## Domain Signals

(keywords – always present, empty if none)

## Dependencies

(namespaces, files – always present, empty if none)

## Warnings

(List of warnings – always present, empty if none)

## Raw Extract

(First 1000 chars of file, always present, may be empty)

---

### 5. Output Rules

- ALL fields must always exist, even if empty.
- No null values anywhere; use empty list [], empty object {}, or empty string "" as appropriate.
- Order of fields in all outputs must be deterministic and match the contract above.
- Arrays must be sorted lexicographically unless otherwise specified.
- Output must be fully machine-readable and consistent across runs for the same input.

## [PHASE 4 – CAPABILITY MODEL]

**Goal:** Transform extracted signals from Phases 1–3 into a product-level understanding of the system.

The output of this phase is NOT technical documentation. It is a product-level model that a non-technical product owner can read and act on.

---

### 4.1 Function Model

A **Function** represents a single named operation in the system.

Each function must have the following fields (all required, no nulls):

```json
{
  "name": string,
  "type": "API" | "DB" | "UI" | "Batch",
  "inputs": [string],
  "outputs": [string],
  "source_files": [string],
  "dependencies": [string],
  "description": string
}
```

**Derivation rules:**

* type = "API" — derived from endpoints (HttpGet/Post/Put/Delete/Http*) in C# files
* type = "DB" — derived from stored procedures and views in SQL files
* type = "UI" — derived from Angular services and components
* type = "Batch" — derived from batch jobs, triggers, and schedules
* `name` = method name or procedure name, verbatim
* `inputs` = inferred from method parameters or SQL parameters (if extractable, else [])
* `outputs` = inferred from return types or SQL result sets (if extractable, else [])
* `source_files` = sorted list of files where the function was found
* `dependencies` = sorted list of namespaces, services, or tables referenced
* `description` = short plain-language description inferred from name and domain keywords; if not inferrable, use "UNKNOWN"

---

### 4.2 Module Model

A **Module** represents a named group of related functions forming a business capability.

Each module must have the following fields (all required, no nulls):

```json
{
  "name": string,
  "description": string,
  "functions": [string],
  "dependencies": [string],
  "used_by": [string]
}
```

**Derivation rules:**

* Modules are formed by grouping functions that share:
  * two or more domain keywords
  * common dependency namespaces or file paths
  * common naming prefix (e.g., "Order", "Customer", "Schedule")
* `name` = inferred from dominant shared keyword or naming prefix; plain language
* `description` = one sentence describing the module's purpose; if not inferrable, use "UNKNOWN"
* `functions` = sorted list of function names belonging to this module
* `dependencies` = sorted union of all function dependencies in the module
* `used_by` = sorted list of other module names that call or depend on this module

---

### 4.3 V2 Decision Model

Every function and every module must include a V2 decision entry. This is the product owner's selection model.

**Per function entry:**

```json
{
  "name": string,
  "keep": boolean,
  "reason": string
}
```

**Per module entry:**

```json
{
  "name": string,
  "keep": boolean,
  "reason": string
}
```

**Default values:**

* `keep` = true (default; product owner explicitly sets to false to exclude)
* `reason` = "" (empty string if not set; product owner fills this in)

---

### 4.4 Output Files

Three new output files must be generated:

#### capabilities.json

List of all functions derived from the codebase.

```json
{
  "functions": [
    {
      "name": string,
      "type": "API" | "DB" | "UI" | "Batch",
      "inputs": [string],
      "outputs": [string],
      "source_files": [string],
      "dependencies": [string],
      "description": string
    }
  ]
}
```

#### modules.json

List of all modules derived by grouping functions.

```json
{
  "modules": [
    {
      "name": string,
      "description": string,
      "functions": [string],
      "dependencies": [string],
      "used_by": [string]
    }
  ]
}
```

#### v2-selection.json

Product owner's decision model. Pre-populated from modules.json and capabilities.json with `keep: true` for all entries.

```json
{
  "modules": [
    {
      "name": string,
      "keep": boolean,
      "reason": string
    }
  ],
  "functions": [
    {
      "name": string,
      "keep": boolean,
      "reason": string
    }
  ]
}
```

---

### 4.5 Rules

* All fields in all output files must always exist; no nulls; empty string or empty list if not applicable.
* All arrays are sorted lexicographically.
* Functions with the same name from different files are merged into one entry; source_files lists all origins.
* Modules must not overlap; each function belongs to exactly one module.
* If a function cannot be assigned to any module, it goes into a module named "Uncategorized".
* Descriptions must be plain language, max 20 words, written for a non-developer audience.
* v2-selection.json is only generated once per run; if it already exists, it is NOT overwritten (to preserve product owner edits).

---

### 4.6 Phase 4 Dependencies

Phase 4 requires:
* Phase 2 (Core Analyzers) complete
* Phase 3 (Cross-Analysis) complete — specifically dependency graph and summary report

---

### 4.7 Phase 4 Definition of Done

* capabilities.json exists and contains at least one function per endpoint/procedure/service found
* modules.json exists and all functions are assigned to a module
* v2-selection.json exists with keep: true for all entries (initial state)
* No null values in any output field
* All arrays are sorted
* Descriptions are present for all functions and modules (or "UNKNOWN" if not inferrable)

## [PHASE 4.5 – USE CASE EXTRACTION]

**Goal:** Derive real user-facing flows by tracing paths from Angular entry points through the backend to the database. Output is designed for non-technical product owners to understand what the system actually does for its users.

---

### 4.5.1 Use Case Models

Use case data is split across two output files with separate lifecycles. A use case is identified by its `id` field, which is the stable join key between the two files. `name` is display-only and may change between runs.

#### Analysis Record (use-cases.analysis.json)

Always regenerated. Contains volatile analysis data.

```json
{
  "id": string,
  "name": string,
  "entry_point": string,
  "flow_steps": [
    { "type": "UI" | "API" | "Service" | "DB", "name": string }
  ],
  "functions": [string],
  "module": string,
  "description": string,
  "confidence": number
}
```

**Field rules:**

* `id` — stable deterministic identifier. Computed per Section 4.5.1.1. Never changes unless the use case disappears completely. Join key.
* `name` — plain-language display name derived from the entry point (see Section 4.5.5). Max 5 words. Display-only; may change between runs.
* `entry_point` — the Angular component name or route that initiates the flow. Verbatim from AngularAnalyzer output.
* `flow_steps` — ordered list of steps traced from entry point to termination. Each step has:
  * `type` — one of: `"UI"`, `"API"`, `"Service"`, `"DB"`
  * `name` — the component, endpoint, service, or procedure name. Verbatim. Never invented.
* `functions` — sorted list of function names (from capabilities.json) involved in this use case.
* `module` — the module name (from modules.json) that this use case primarily belongs to. If ambiguous, use the module of the first API step. If unresolvable, use `"Uncategorized"`.
* `description` — plain-language description of the user action. Max 20 words. Not technical. If not inferrable, use `"UNKNOWN"`.
* `confidence` — integer from 0 to 100 representing trace completeness. Computed automatically per Section 4.5.4. Never set manually.

#### Selection Record (use-cases.selection.json)

Write-once. Contains persistent product owner decisions.

```json
{
  "id": string,
  "name": string,
  "keep": boolean,
  "reason": string
}
```

**Field rules:**

* `id` — must match the corresponding analysis record id exactly. Join key. Stable across runs.
* `name` — copied from the analysis record at time of first generation. Informational only; not updated on subsequent runs.
* `keep` — defaults to `true` on first generation. Product owner sets to `false` to exclude from V2.
* `reason` — defaults to `""`. Product owner fills this in to explain the decision.

---

### 4.5.1.1 ID Generation Rules

The `id` is a deterministic string derived from the use case's structural identity, not its display name.

**Algorithm:**

1. Take `entry_point` (verbatim from AngularAnalyzer output)
2. Take the `name` of the first API step in `flow_steps` (the primary endpoint). If no API step exists, use `"none"`.
3. Normalize each: lowercase, remove all non-alphanumeric characters, trim whitespace
4. Concatenate: `<normalized_entry_point>__<normalized_primary_endpoint>`
5. `id` = the concatenated string

**Examples:**

* `entry_point = "CustomerDetailComponent"`, first API = `"GetCustomer"` → `id = "customerdetailcomponent__getcustomer"`
* `entry_point = "OrderListComponent"`, no API step → `id = "orderlistcomponent__none"`
* `entry_point = "/customer/edit"`, first API = `"UpdateCustomer"` → `id = "customeredit__updatecustomer"`

**Stability rules:**

* `id` does NOT depend on `name`, `description`, `module`, `confidence`, or `flow_steps` beyond the first API step.
* If `entry_point` is renamed in Angular code, the `id` changes — this is expected; the use case has structurally changed.
* If only the display `name` changes (e.g., due to naming rule updates), the `id` is unaffected.
* If two use cases produce the same `id`, suffix the second with `__2`, third with `__3`, etc. (lexicographic order of entry_point determines which is first).

---

### 4.5.2 Extraction Rules

Use case extraction MUST start from Angular only. No use cases are invented from backend code alone.

**Start from:**
1. Angular components (from `key_elements.components` in AngularAnalyzer output)
2. Angular routes (from `key_elements.routes`)
3. Inferred user actions from component names using the pattern keywords: `view`, `list`, `create`, `edit`, `update`, `delete`, `submit`, `search`, `load`, `upload`, `download`, `login`, `logout`

**For each Angular starting point:**
1. Find all API calls made by that component or its associated service (from `key_elements.api_calls`)
2. Match each API call to a backend endpoint in capabilities.json by URL pattern or method name similarity
3. From each matched endpoint, find the associated service/repository calls (from `key_elements.methods` and `dependencies`)
4. From each service, find associated SQL procedures, tables, or views (from SqlAnalyzer output)
5. Stop tracing when reaching: a DB operation, an external API call (URL not in the solution), or a batch trigger

**If a step cannot be resolved:** record it as a partial step with `name` = `"UNKNOWN"` and continue.

---

### 4.5.3 Flow Tracing Rules

* Trace is strictly layer-by-layer: UI → API → Service → DB. No skipping layers.
* Each step in `flow_steps` must be traceable to a real signal in the analysis output. No invented steps.
* Circular references (A calls B calls A) are broken at the second occurrence; the repeated step is recorded as `"[CIRCULAR]"` and tracing stops for that branch.
* A use case with zero API steps is recorded as partial (only UI layer traced).
* A use case with zero DB steps is still valid if the API layer is complete.
* Maximum depth: 10 steps. If tracing exceeds 10 steps, record the last step as `"[DEPTH LIMIT]"` and stop.

---

### 4.5.4 Confidence Scoring

Every use case receives a `confidence` score computed deterministically from its traced flow.

**Scoring rules (additive):**

| Condition | Points |
|---|---|
| Angular entry point exists (non-empty `entry_point`) | +30 |
| At least one API step found in `flow_steps` | +20 |
| At least one Service step found in `flow_steps` | +20 |
| At least one DB step found in `flow_steps` | +20 |
| Any step has `name = "UNKNOWN"` | −20 |
| Any step has `name = "[CIRCULAR]"` | −30 |

**Calculation rules:**

* Start at 0.
* Apply all matching conditions; conditions are independent and non-exclusive.
* Multiple `"UNKNOWN"` steps still deduct only −20 (penalty applied once).
* Multiple `"[CIRCULAR]"` steps still deduct only −30 (penalty applied once).
* Clamp final result: `confidence = max(0, min(100, raw_score))`.
* Result is always an integer.

**Examples:**

* Full trace (entry + API + Service + DB, no unknowns): 30+20+20+20 = **90**
* Entry + API only: 30+20 = **50**
* Entry + API + UNKNOWN step: 30+20−20 = **30**
* Entry only (no API found): 30 = **30**
* Entry + CIRCULAR: 30−30 = **0**
* No entry point: 0 (before any penalties)

**Determinism requirement:** Given the same `entry_point` and `flow_steps`, the score is always identical. Score computation has no external inputs.

---

### 4.5.5 Naming Rules

Use case names are derived in this order of priority:

1. If a route exists: use the route path, convert to Title Case, remove slashes and IDs (e.g., `/customer/edit/:id` → `Edit Customer`)
2. If no route: use the component name, split by CamelCase, remove generic words (`Component`, `View`, `Page`, `Container`), title case the rest (e.g., `CustomerEditComponent` → `Edit Customer`)
3. If still ambiguous: use the primary API endpoint name, split by CamelCase, prefix with action verb inferred from HTTP method (`HttpGet`→`View`, `HttpPost`→`Create`, `HttpPut`→`Update`, `HttpDelete`→`Delete`)
4. If all above fail: name = `"UNKNOWN"`

**Deduplication:** If two use cases generate the same name, suffix the second with ` (2)`, third with ` (3)`, etc.

---

### 4.5.6 Output Files

#### use-cases.analysis.json

Always recomputed on every run. Never preserved between runs.

```json
{
  "use_cases": [
    {
      "id": "customerdetailcomponent__getcustomer",
      "name": "View Customer",
      "entry_point": "CustomerDetailComponent",
      "flow_steps": [
        { "type": "UI", "name": "CustomerDetailComponent" },
        { "type": "API", "name": "GetCustomer" },
        { "type": "Service", "name": "CustomerService" },
        { "type": "DB", "name": "sp_GetCustomer" }
      ],
      "functions": ["GetCustomer", "sp_GetCustomer"],
      "module": "Customer",
      "description": "Displays the details of a single customer record.",
      "confidence": 90
    }
  ]
}
```

#### use-cases.selection.json

Write-once. Generated on first run only. Never overwritten.

```json
{
  "use_cases": [
    {
      "id": "customerdetailcomponent__getcustomer",
      "name": "View Customer",
      "keep": true,
      "reason": ""
    }
  ]
}
```

**Output rules:**

* Both files have `use_cases` array sorted by `id` lexicographically.
* `flow_steps` in analysis file ordered as traced (not sorted).
* `functions` sorted lexicographically.
* All fields always present; no nulls; empty list or empty string if not applicable.
* `id` exists in BOTH files and is the primary join key.
* `confidence` exists ONLY in use-cases.analysis.json. Never in selection file.
* `keep` and `reason` exist ONLY in use-cases.selection.json. Never in analysis file.
* **use-cases.analysis.json is always overwritten on each run.**
* **use-cases.selection.json is NEVER overwritten** once created (to preserve product owner edits).
* On first run, use-cases.selection.json is generated with `keep: true`, `reason: ""`, and `name` copied from the analysis record for all entries.
* When presenting merged data, consumers must join the two files on the `id` field. `name` is display-only and must not be used as a join key.

---

### 4.5.7 Determinism Rules

* Angular components and routes are processed in lexicographic order.
* API call matching uses exact string match first; if no exact match, use longest common substring match; if still ambiguous, use lexicographically first match.
* All tie-breaking is lexicographic.
* No random values, no timestamps, no UUIDs anywhere in the extraction pipeline.
* Partial use cases (where some steps are `"UNKNOWN"`) are included in output — they are NOT discarded.
* Partial use cases are flagged by having at least one `flow_steps` entry with `name = "UNKNOWN"`.

**File lifecycle rules:**

* use-cases.analysis.json: always regenerated. Previous content is always replaced.
* use-cases.selection.json: generated once. If the file exists, it is never modified by the tool.
* When use-cases.selection.json already exists and new use cases appear in use-cases.analysis.json, the tool does NOT add them to the selection file automatically. A separate migration step is required.
* The join key between the two files is always the `id` field. `name` is display-only and must not be used for joining.
* If names change between runs, the selection file remains valid as long as `id` values are stable.
* If `id` values change (e.g., due to an `entry_point` rename in the Angular code), the selection file becomes partially stale — this is expected and is the product owner's responsibility to reconcile.

---

### 4.5.8 Phase 4.5 Dependencies

* Phase 2 complete (CSharpAnalyzer, SqlAnalyzer, AngularAnalyzer)
* Phase 4 Capability Model complete (capabilities.json, modules.json must exist)

---

### 4.5.9 Phase 4.5 Definition of Done

**use-cases.analysis.json:**
* File exists and is regenerated on every run
* At least one use case is derived per Angular component found
* Every use case has a non-empty `id` computed per Section 4.5.1.1
* Every use case has a non-empty `entry_point`
* Every use case has at least one `flow_steps` entry
* Every use case is assigned to a module
* No null values in any field
* `functions` array references only names present in capabilities.json
* `module` references only names present in modules.json (or `"Uncategorized"`)
* Every use case has a `confidence` value that is an integer in the range 0–100
* `confidence` is computed deterministically from `entry_point` and `flow_steps` per Section 4.5.4
* `keep` and `reason` fields are NOT present in this file
* `use_cases` array is sorted by `id` lexicographically

**use-cases.selection.json:**
* File exists after first run
* Contains one entry per use case in use-cases.analysis.json (on first generation)
* Every entry has `id`, `name`, `keep`, and `reason`
* `id` matches the corresponding analysis record exactly
* `keep` defaults to `true`; `reason` defaults to `""`
* `confidence`, `entry_point`, `flow_steps`, `functions`, `module`, and `description` fields are NOT present in this file
* File is never overwritten once created
* `id` values are stable across runs unless the underlying `entry_point` or primary endpoint changes
