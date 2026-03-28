# AI Agent Questions – AI_ANALYSIS_MASTER_SPEC.md

This file is for clarifying questions or uncertainties the AI agent has regarding the master specification for the analysis-tool project. Add new questions below as needed.

---

## [2026-03-28]

- Ingen spørgsmål på nuværende tidspunkt. Specifikationen er læst og forstået. Alle opgaver vil blive løst trin-for-trin, med fokus på signal extraction, domæneforståelse og maskinlæsbar output. Hvis der opstår tvivl, vil spørgsmål blive tilføjet her.

## [CRITICAL REVIEW]

1. **Ambiguity in "Relevant Files" (Section 3.1 Scan):**
   - The spec says "Identify all relevant files" but does not define what makes a file relevant. Is it based on file extension, content, or project inclusion? Clarification is needed on the criteria for relevance, especially for mixed or non-standard files.

2. **Unclear File Classification Boundaries (Section 3.2 Classify):**
   - The categories (csharp, sql, angular, config, batch, unknown) are not precisely defined. For example, how should TypeScript files in Angular, or YAML/JSON config files, be classified? What about files that fit multiple categories?

3. **Domain Keyword List Limitation (Section 3.3 CSharpAnalyzer):**
   - The list of domain keywords (status, type, code, id, date) is hardcoded and limited. Should this be extensible or configurable? How should project-specific domain terms be handled?

4. **Ambiguity in "Endpoints" Extraction (Section 3.3 CSharpAnalyzer):**
   - The spec lists endpoints as HttpGet/Post/Put/Delete, but does not specify how to handle custom attributes, versioned routes, or non-standard HTTP methods. Should these be ignored or flagged?

5. **Lack of SQL Dialect/Platform Guidance (Section 3.3 SqlAnalyzer):**
   - The SQL analyzer requirements do not specify which SQL dialects or platforms are supported. Are only Azure SQL and T-SQL supported, or should MySQL/Postgres syntax be considered if found?

6. **No Definition of "Summary Reports" (Section 3.5 Output):**
   - The spec requires "Summary reports" globally, but does not define their structure, required content, or intended consumers (human vs. LLM). What metrics or aggregations are expected?

7. **Unclear Handling of Partial/Failed Analysis (Section 3.4 Store Results):**
   - If a file cannot be fully analyzed (e.g., due to syntax errors or unsupported constructs), how should this be represented in the FileAnalysis model? Should there be an explicit error or warning field?

8. **Ambiguity in "Noise Reduction" (Section 7.5):**
   - The spec calls for filtering irrelevant signals and deduplication, but does not define what constitutes "noise" or how aggressive filtering should be. Is there a risk of losing weak but important signals?

9. **No Guidance on Cross-File/Project Relationships (Section 7.3 Dependency Mapping):**
   - The spec mentions cross-project dependencies and service relationships, but does not specify how to detect or represent them, especially when dependencies are implicit or dynamic.

10. **Unclear Versioning and Extensibility Strategy (Section 8, Rules for Further Development):**
    - The spec says to "keep analyzers simple" and "write deterministic output," but does not address how to handle future changes in technology stacks, new file types, or evolving domain concepts. Is there a versioning or plugin strategy?

11. **Potential Conflict: "Extract signals, not full truth" vs. "Validate usefulness for domain extraction" (Sections 8 & 9):**
    - There is a tension between extracting only signals (not full parsing) and the need to validate that output is useful for domain extraction. How should this tradeoff be managed, and who decides if the output is "useful enough"?

12. **No Explicit Test or Quality Criteria (Section 9, Development Strategy):**
    - The spec says to "Test output continuously" but does not define what constitutes a "good" or "bad" output, nor how to measure progress or regression. Are there sample outputs or test cases?
