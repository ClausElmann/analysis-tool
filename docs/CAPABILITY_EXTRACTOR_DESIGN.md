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
- **description:** See Section 4

---

### 1.2 From C# Methods (non-endpoint)

- **Source:** `key_elements.methods` in FileAnalysis for files with `type = "csharp"`, excluding methods already captured as endpoints
- **One function per method name (per file).**
- **Name:** method name verbatim
- **Type:** `"API"` if the file contains any endpoint; otherwise `"API"` (C# methods are always type API in this model)
- **Inputs:** `[]` (method signature not parsed beyond name at this stage)
- **Outputs:** `[]`
- **source_files:** `[file_path]`
- **dependencies:** `key_elements.dependencies.namespaces` from the same file
- **description:** See Section 4

---

### 1.3 From SQL Procedures

- **Source:** `key_elements.procedures` in FileAnalysis for files with `type = "sql"`
- **One function per procedure name.**
- **Name:** procedure name verbatim
- **Type:** `"DB"`
- **Inputs:**
  - Extract `@ParamName` tokens from the stored procedure definition using regex: `@(\w+)`
  - If not extractable: `[]`
- **Outputs:** `[]` (SQL result sets are not parsed)
- **source_files:** `[file_path]`
- **dependencies:** `key_elements.tables` from the same file (sorted)
- **description:** See Section 4

---

### 1.4 From Angular Services

- **Source:** `key_elements.services` in FileAnalysis for files with `type = "angular"`
- **One function per service name.**
- **Name:** service name verbatim
- **Type:** `"UI"`
- **Inputs:** `[]`
- **Outputs:** `[]`
- **source_files:** `[file_path]`
- **dependencies:** `key_elements.dependencies.files` from the same file (sorted)
- **description:** See Section 4

---

### 1.5 From Batch Jobs

- **Source:** `key_elements.jobs` in FileAnalysis for files with `type = "batch"`
- **One function per job name.**
- **Name:** job name verbatim
- **Type:** `"Batch"`
- **Inputs:** `[]`
- **Outputs:** `[]`
- **source_files:** `[file_path]`
- **dependencies:** `key_elements.dependencies.files` from the same file (sorted)
- **description:** See Section 4

---

### 1.6 Naming Rules

- Names are taken verbatim from extracted signal — no transformation.
- Names are never generated, inferred, or abbreviated.
- If a name is empty string: skip this entry and add warning to extraction log.

---

## 2. Module Grouping Algorithm

### 2.1 Overview

Each function is scored against every existing module candidate. The function is assigned to the module with the highest score above the threshold. If no module qualifies, a new module candidate is started for that function. If no candidate ever qualifies, the function is assigned to "Uncategorized".

All operations are deterministic: functions are processed in sorted order by name.

---

### 2.2 Scoring System

When comparing function F to module candidate M, compute a score in range [0, 100]:

| Signal | Score contribution |
|---|---|
| Namespace overlap | +30 per shared namespace (capped at 60) |
| Filename prefix match | +20 if source file path shares a directory with any function in M |
| Domain keyword overlap | +15 per shared domain keyword (capped at 30) |
| Dependency overlap | +10 per shared dependency (capped at 20) |
| Name prefix match (first word of CamelCase) | +20 if matches dominant prefix of M |

**Score computation rules:**
- Namespace overlap: count namespaces in F.dependencies that also appear in any function in M.dependencies; multiply by 30, cap at 60
- Filename prefix: extract directory path from F.source_files[0]; compare to directory of any source file in M; if equal → +20
- Domain keyword overlap: count keywords in F.domain_signals that also appear in any function in M.domain_signals; multiply by 15, cap at 30
- Dependency overlap: count F.dependencies items that appear in any function in M.dependencies; multiply by 10, cap at 20
- Name prefix: split F.name by CamelCase → first token; compare to dominant prefix of M (mode of first tokens of all M functions); if match → +20

---

### 2.3 Threshold Rules

- Score **≥ 40**: function is assigned to module M
- Score **< 40**: function does not belong to M
- If multiple modules tie on score: assign to module whose name is lexicographically first
- If function scores ≥ 40 against no existing module: create a new module candidate seeded with that function

---

### 2.4 Fallback

- After all functions are processed, any module containing exactly one function that was never joined by another function at ≥ 40 score is merged into "Uncategorized".
- "Uncategorized" always exists in modules.json, even if empty.

---

## 3. Module Naming Strategy

### 3.1 Name Generation

1. Collect the first CamelCase token from each function name in the module (e.g., `GetCustomer` → `Customer`).
2. Find the most frequent token (mode). If tie: use lexicographically first.
3. Module name = that token, as-is (no further transformation).
4. Exception: if all tokens are generic (`Get`, `Set`, `Update`, `Delete`, `Create`, `Handle`, `Process`) with no differentiating noun, use the most common domain keyword from the module's functions. If still not deterministic, use "Uncategorized".

### 3.2 Avoiding Duplicates

- Module names are unique. If two module candidates generate the same name, suffix the second with `_2`, the third with `_3`, etc.
- Suffixes are numeric, starting at `_2`.

### 3.3 Normalizing Names

- Remove leading/trailing whitespace.
- Replace spaces with underscores.
- Remove non-alphanumeric characters except underscores.
- Preserve original casing (no lowercasing).

---

## 4. Description Generation

### 4.1 Rules

- Max 20 words.
- Written for a non-developer audience (no technical jargon).
- Deterministic: same input → same description.
- If not inferrable: use the string `"UNKNOWN"` exactly.

### 4.2 Generation Algorithm

**For functions:**

1. Take the function name and split by CamelCase → list of words (e.g., `GetCustomerOrders` → `["Get", "Customer", "Orders"]`)
2. Remove generic verbs: `Get`, `Set`, `Post`, `Put`, `Delete`, `Handle`, `Process`, `Create`, `Update`, `Run`, `Execute`
3. Remaining tokens form the subject (e.g., `["Customer", "Orders"]`)
4. If type is API: prefix with "Retrieves", "Creates", "Updates", or "Deletes" based on method attribute (`HttpGet`→`Retrieves`, `HttpPost`→`Creates`, `HttpPut`→`Updates`, `HttpDelete`→`Deletes`); for others: "Handles"
5. If type is DB: prefix with "Database operation for"
6. If type is UI: prefix with "User interface feature for"
7. If type is Batch: prefix with "Scheduled job for"
8. Concatenate prefix + subject tokens joined by spaces
9. If result is empty (no subject tokens): return `"UNKNOWN"`
10. Truncate to 20 words if needed

**For modules:**

1. Collect all function descriptions in the module
2. Extract the subject tokens from step 3 above, across all functions
3. Find the most frequent subject token (mode; if tie: lexicographically first)
4. Description = `"Handles all {module_name}-related operations in the system."`
5. If module_name is "Uncategorized": description = `"Contains functions that could not be grouped into a specific module."`

---

## 5. Output Structure

### 5.1 capabilities.json

```json
{
  "functions": [
    {
      "name": "GetCustomer",
      "type": "API",
      "inputs": ["id"],
      "outputs": ["CustomerDto"],
      "source_files": ["ServiceAlert.Api/Controllers/CustomerController.cs"],
      "dependencies": ["MyApp.Models", "MyApp.Services"],
      "description": "Retrieves Customer information."
    }
  ]
}
```

- `functions` is sorted by `name` lexicographically.
- All fields always present; no nulls; empty lists if not applicable; empty string if description not inferrable.
- Merged entries: if two files contain a function with the same name, they are merged into one entry with combined `source_files` (sorted) and union of `dependencies` (sorted).

---

### 5.2 modules.json

```json
{
  "modules": [
    {
      "name": "Customer",
      "description": "Handles all Customer-related operations in the system.",
      "functions": ["GetCustomer", "UpdateCustomer"],
      "dependencies": ["MyApp.Models", "MyApp.Services"],
      "used_by": []
    },
    {
      "name": "Uncategorized",
      "description": "Contains functions that could not be grouped into a specific module.",
      "functions": [],
      "dependencies": [],
      "used_by": []
    }
  ]
}
```

- `modules` sorted by `name` lexicographically; "Uncategorized" always last.
- `functions`, `dependencies`, `used_by` arrays are sorted lexicographically.
- All fields always present; no nulls.

---

### 5.3 v2-selection.json

```json
{
  "modules": [
    {
      "name": "Customer",
      "keep": true,
      "reason": ""
    }
  ],
  "functions": [
    {
      "name": "GetCustomer",
      "keep": true,
      "reason": ""
    }
  ]
}
```

- `modules` sorted by `name` lexicographically.
- `functions` sorted by `name` lexicographically.
- All fields always present; no nulls.
- `keep` defaults to `true` for all entries on first generation.
- `reason` defaults to `""` on first generation.
- **This file is NEVER overwritten if it already exists.** The extractor checks for existence before generating; if found, it skips generation entirely.

---

## 6. Edge Cases

### 6.1 Duplicate Functions

- Two functions with the same `name` from different files: merged into one entry.
- Merge rule: `source_files` = sorted union; `dependencies` = sorted union; `inputs` = union (deduplicated, sorted); `outputs` = union (deduplicated, sorted); `description` = description of first occurrence (sorted by source_file path).
- Merge is applied after all files are processed.

### 6.2 Missing Data

- If `key_elements.methods` is empty: no functions extracted from that file; no error.
- If `key_elements.procedures` is empty: no DB functions extracted; no error.
- If a function name is empty string: skip entry; log warning `"Skipped function with empty name in {file_path}"`.
- If `domain_signals.keywords` is empty for a function: keyword overlap = 0 in scoring.

### 6.3 Conflicting Groupings

- A function can only belong to one module. First-assignment wins (functions processed in sorted name order; modules scored in sorted name order).
- No function appears in two modules.

### 6.4 Empty Modules

- A module with zero functions after merging is removed from modules.json.
- Exception: "Uncategorized" is always present, even if its `functions` list is empty.

---

## 7. Determinism Rules

The following rules guarantee same input → same output on every run:

1. **Sort all inputs before processing.** Functions are processed in lexicographic order by `name`. Module candidates are scored in lexicographic order by `name`.
2. **Tie-breaking is always lexicographic.** Any tie in score, frequency, or naming is broken by choosing the lexicographically smallest value.
3. **No random or time-dependent values.** No UUIDs, timestamps, or random seeds anywhere in the pipeline.
4. **File order is normalized.** Source files are sorted before processing; directory traversal order does not affect output.
5. **Merge order is deterministic.** When merging duplicate functions, the merge processes files in sorted path order.
6. **v2-selection.json write-once.** If the file exists, it is not regenerated; output is stable across re-runs.
7. **Description generation is rule-based.** No LLM calls; no probabilistic steps; all derivation is regex + token counting + lexicographic tie-breaking.
