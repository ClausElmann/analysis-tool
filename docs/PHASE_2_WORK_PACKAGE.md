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
  - Set analysis_status to 'partial', populate analysis_warnings with specific issues (e.g., syntax errors, unsupported constructs).
- **Acceptance criteria:**
  - All required signals are extracted and present in output for valid .cs files; failures and partials are correctly flagged.
- **Test cases to create:**
  - Valid C# file with all signal types
  - File with syntax errors
  - File with custom [Http*] attributes
  - File with no extractable signals

### 2. SqlAnalyzer
- **Purpose:** Extract schema and logic signals from SQL files (T-SQL only).
- **Input file types:** .sql
- **Signals to extract:**
  - tables
  - columns
  - primary keys
  - foreign keys
  - stored procedures
  - views
  - joins
  - where conditions
- **Output fields to populate in FileAnalysis:**
  - key_elements (all above signals)
  - domain_signals
  - dependencies
  - raw_extract (first 1000 chars)
  - analysis_status
  - analysis_warnings
  - risks_notes (if non-T-SQL dialect detected)
- **Failure behavior:**
  - Set analysis_status to 'failed', populate analysis_warnings, output empty key_elements.
- **Warnings behavior:**
  - Set analysis_status to 'partial', populate analysis_warnings (e.g., partial parse, dialect mismatch).
- **Acceptance criteria:**
  - All required signals are extracted for T-SQL; dialect issues are flagged; failures/partials are handled.
- **Test cases to create:**
  - Valid T-SQL file with all signal types
  - File with MySQL/Postgres syntax
  - File with syntax errors
  - File with no extractable signals

### 3. AngularAnalyzer
- **Purpose:** Extract structural and API signals from Angular codebase files.
- **Input file types:** .ts, .html, .js (in Angular folders)
- **Signals to extract:**
  - components
  - services
  - API calls
  - routes
  - forms
- **Output fields to populate in FileAnalysis:**
  - key_elements (all above signals)
  - domain_signals
  - dependencies
  - raw_extract (first 1000 chars)
  - analysis_status
  - analysis_warnings
- **Failure behavior:**
  - Set analysis_status to 'failed', populate analysis_warnings, output empty key_elements.
- **Warnings behavior:**
  - Set analysis_status to 'partial', populate analysis_warnings (e.g., partial parse, unsupported constructs).
- **Acceptance criteria:**
  - All required signals are extracted for valid Angular files; failures/partials are handled.
- **Test cases to create:**
  - Valid Angular component/service file
  - File with syntax errors
  - File with no extractable signals

### 4. ConfigAnalyzer
- **Purpose:** Extract configuration and integration signals from config files.
- **Input file types:** .json, .yml, .yaml, .config, .xml
- **Signals to extract:**
  - connection strings
  - feature flags
  - environment variables
  - integration endpoints
- **Output fields to populate in FileAnalysis:**
  - key_elements (all above signals)
  - domain_signals
  - dependencies
  - raw_extract (first 1000 chars)
  - analysis_status
  - analysis_warnings
- **Failure behavior:**
  - Set analysis_status to 'failed', populate analysis_warnings, output empty key_elements.
- **Warnings behavior:**
  - Set analysis_status to 'partial', populate analysis_warnings (e.g., partial parse, unsupported format).
- **Acceptance criteria:**
  - All required signals are extracted for valid config files; failures/partials are handled.
- **Test cases to create:**
  - Valid config file with all signal types
  - File with syntax errors
  - File with no extractable signals

### 5. BatchAnalyzer
- **Purpose:** Extract job and scheduling signals from batch files.
- **Input file types:** .bat, .cmd, .sh
- **Signals to extract:**
  - jobs
  - triggers
  - schedules
  - data flows
- **Output fields to populate in FileAnalysis:**
  - key_elements (all above signals)
  - domain_signals
  - dependencies
  - raw_extract (first 1000 chars)
  - analysis_status
  - analysis_warnings
- **Failure behavior:**
  - Set analysis_status to 'failed', populate analysis_warnings, output empty key_elements.
- **Warnings behavior:**
  - Set analysis_status to 'partial', populate analysis_warnings (e.g., partial parse, unsupported constructs).
- **Acceptance criteria:**
  - All required signals are extracted for valid batch files; failures/partials are handled.
- **Test cases to create:**
  - Valid batch file with all signal types
  - File with syntax errors
  - File with no extractable signals

---

## Shared Analyzer Contract

- **Required analyzer interface:**
  - analyze(file_path: str, content: str, analysis: FileAnalysis) -> None
- **Expected inputs:**
  - file_path: absolute path to the file
  - content: full file content as string
  - analysis: FileAnalysis object to mutate
- **Expected mutations on FileAnalysis:**
  - Populate key_elements, domain_signals, dependencies, raw_extract, analysis_status, analysis_warnings
- **Required status handling:**
  - Set analysis_status to one of: 'success', 'partial', 'failed'
  - 'success': all required signals extracted
  - 'partial': some signals missing or parse incomplete
  - 'failed': no signals extracted, analysis_warnings populated
- **Required warnings handling:**
  - All parse or extraction issues must be appended to analysis_warnings (list of strings)
- **raw_extract rules:**
  - Always set to the first 1000 characters of the file content (UTF-8)
- **Deterministic output rules:**
  - Given the same input, output must be byte-for-byte identical; no random or time-dependent fields

---

## Phase 2 Definition of Done

- **Modules/files that must exist:**
  - analyzers/csharp_analyzer.py
  - analyzers/sql_analyzer.py
  - analyzers/angular_analyzer.py
  - analyzers/config_analyzer.py
  - analyzers/batch_analyzer.py
  - tests/test_csharp_analyzer.py
  - tests/test_sql_analyzer.py
  - tests/test_angular_analyzer.py
  - tests/test_config_analyzer.py
  - tests/test_batch_analyzer.py
- **Tests that must exist:**
  - At least 4 test cases per analyzer as specified above
- **Output fields that must be populated:**
  - key_elements, domain_signals, dependencies, raw_extract, analysis_status, analysis_warnings (and risks_notes for SQL)
- **Sample files that must be analyzable:**
  - At least one valid and one invalid sample for each supported file type

---

## Phase 2 Exclusions

- No cross-file or dependency mapping (Phase 3)
- No capability extraction or domain synthesis (Phase 4)
- No noise reduction or performance tuning (Phase 5)
- No plugin or extensibility features
- No UI or visualization components
- No support for file types outside those listed
- No support for SQL dialects other than T-SQL
- No output formats other than Markdown and JSON
- No integration with external systems or databases
