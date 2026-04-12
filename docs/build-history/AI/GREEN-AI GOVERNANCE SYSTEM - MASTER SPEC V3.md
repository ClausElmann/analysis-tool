# GREEN-AI GOVERNANCE SYSTEM — MASTER SPEC v3 (PRODUCTION)

> **Status:** Production SSOT
> **Scope:** UI Governance (Phase 1–2) + Autonomous Loop (guarded)
> **Princip:** Deterministic core + non-deterministic AI bounded by contracts

---

# 0. NON-NEGOTIABLE RULES (GLOBAL)

## 0.1 UNKNOWN RULE (CRITICAL)

Copilot MUST:

* STOP on insufficient context
* Output: `UNKNOWN`
* NEVER guess selectors, mappings, or fixes

Violation = **system corruption risk**

---

## 0.2 DETERMINISM RULE

Given identical inputs:

* Runner output MUST be identical
* Scoring MUST be identical
* Delta MUST be identical

AI is non-deterministic → **system compensates with guards**

---

## 0.3 IMMUTABLE CONTRACTS

Copilot MUST NOT:

* change `ruleKey`
* change severity mapping
* change scoring weights
* change thresholds outside config
* modify loop logic

---

# 1. SYSTEM DEFINITION

System = **rule-based quality engine + AI-assisted fix loop**

NOT a test framework.

## 1.1 C# FILES (Governance/ folder)

| File | Role |
|------|------|
| `GovernanceRuleResult.cs` | Canonical data model (sealed record) |
| `UiGovernanceRunner.cs` | Runs all rules, emits `GovernanceRuleResult[]` |
| `GovernanceScorer.cs` | Scoring engine, dimensions, IsMeta guard |
| `RuleDefinition.cs` | Deserialisation model for `rules.json` |
| `RuleEngineValidator.cs` | Validates `rules.json` on load (duplicate keys, unknown ruleIds) |
| `RuleValidator.cs` | Post-run false-positive + engine-fault detection |
| `RuleValidationResult.cs` | Output of `RuleValidator` |
| `UiGovernanceTests.cs` | xUnit entry point `[Trait("Category","UIGovernance")]` |
| `CssTokenComplianceTests.cs` | Static CSS token compliance (no browser, fast) |

## 1.2 RELATED TEST FILES

| File | Purpose |
|------|---------|
| `VisualAnalysis/VisualAnalysisExporter.cs` | Packages screenshots into `analysis-pack.zip` for external AI |
| `VisualAnalysis/ExportVisualAnalysisTests.cs` | Test that triggers the export |
| `ColorSystem/ColorSystemTests.cs` | Color token E2E checks |
| `ColorSystem/TypographySpacingTests.cs` | Typography/spacing E2E checks |
| `Accessibility/AccessibilityTests.cs` | Accessibility rule checks |

---

# 2. ARCHITECTURE

```
Playwright
  ↓
UiGovernanceRunner
  ↓
GovernanceRuleResult[]
  ↓
GovernanceScorer
  ↓
governance-report.json + governance-delta.json
  ↓
┌─────────────────────────────────────────────┐
│ Orchestrator (choose one)                   │
│  run-ui-1click.ps1       ← 2-pause minimal  │
│  run-ui-autofix.ps1      ← semi-auto loop   │
│  run-ui-autoloop.ps1     ← alias for auto   │
│  run-ui-autonomous.ps1   ← full auto        │
└─────────────────────────────────────────────┘
  ↓
build-screenshot-analysis-input.ps1
  ↓  screenshot-analysis-input.json
copilot-analysis.prompt.md  →  Copilot writes screenshot-analysis.json
  ↓
transform-analysis-to-fixes.ps1
  ↓  copilot-fix-input.json
copilot-fix.prompt.md  →  Copilot applies CSS/Razor fix
  ↓
validate-fix.ps1  (git diff — inline styles, line count, new files)
  ↓
iteration loop
```

---

# 3. RULE MODEL (STRICT)

## 3.1 GovernanceRuleResult (canonical)

| Field          | Type      | Init | Default | Note |
|----------------|-----------|------|---------|------|
| `RuleKey`      | string    | ✅   | —       | Immutable API — NEVER change |
| `RuleId`       | string    | ✅   | —       | Binds to runner execution method |
| `RuleName`     | string    | ✅   | —       | Human-readable |
| `Severity`     | string    | ✅   | —       | `critical`\|`major`\|`minor` |
| `Passed`       | bool      | ❌   | true    | |
| `Message`      | string?   | ❌   | null    | |
| `Elements`     | List<string> | ❌ | []   | Offending DOM elements |
| `Selector`     | string?   | ❌   | null    | |
| `SelectorType` | string?   | ❌   | null    | e.g. `"data-testid"` |
| `ExecutionMs`  | int       | ❌   | 0       | |
| `RootCauseId`  | string?   | ❌   | null    | Groups related failures |
| `RootCauseHint`| string?   | ❌   | null    | Fix direction |
| `FixStrategy`  | string?   | ❌   | null    | e.g. `"add-browser-specific-override"` |
| `FlakeRetried` | bool      | ❌   | false   | True = failed even after one retry (persistent failure) |
| `IsMeta`       | bool      | ✅   | false   | True = observability-only, excluded from ALL scoring/coverage/fixes |

---

## 3.2 META ISOLATION (HARD GUARANTEE)

Meta rules:

* `IsMeta = true`
* NEVER included in:

  * scoring
  * coverage
  * rootCauses
  * escalations
  * fixes

**Implementation (MANDATORY):**

```csharp
var scoreable = results.Where(r => !r.IsMeta).ToList();
```

---

## 3.3 RULEKEY IS API

* NEVER change without version bump
* Used across ALL layers
* Breaking = system break

---

# 4. ROOT CAUSE SYSTEM (ENFORCED)

## 4.1 PURPOSE

Many failures → ONE cause

---

## 4.2 HARD RULE

Fix system MUST operate on `rootCauseId`, NOT `ruleKey`.

---

## 4.3 ENFORCEMENT

* One fix per rootCauseId per iteration
* Rules sharing rootCauseId MUST NOT produce multiple fixes
* Copilot MUST ignore rule-level fixes when rootCauseId exists

---

# 5. SCORING SYSTEM

## 5.1 WEIGHTS

| Severity | Weight |
| -------- | ------ |
| critical | 50     |
| major    | 15     |
| minor    | 5      |

---

## 5.2 FORMULA

```
score = earned / max * 100
```

---

## 5.3 DIMENSIONS

Derived from ruleKey prefix:

* layout
* tokens
* typography
* z-index
* component

---

# 6. SELECTOR TRUST MODEL

| selectorType | Copilot Action |
| ------------ | -------------- |
| data-testid  | AUTO-FIX       |
| semantic     | FIX WITH GUARD |
| fallback     | REPORT ONLY    |
| null         | REPORT ONLY    |

---

# 7. FIX SYSTEM (STRICT)

## 7.1 FIX SCOPE RULE

Per iteration:

* ONLY ONE category allowed
* NEVER mix categories

---

## 7.2 FIX CONTRACT (MANDATORY)

```json
{
  "allowedActions": [...],
  "forbiddenActions": [...],
  "tokenOnly": true,
  "maxLinesChanged": 5
}
```

---

## 7.3 CONTRACT ENFORCEMENT (HARD STOP)

Validation MUST run after every fix:

Checks:

* git diff line count ≤ maxLinesChanged
* NO inline styles (`style=`)
* NO new files
* ONLY allowed files modified

Violation → **IMMEDIATE STOP**

---

## 7.4 OWNERSHIP ENFORCEMENT

If no mapping in `component-ownership.json`:

→ `fixStrategy = report-only`
→ Copilot MUST NOT modify code

---

# 8. LOOP SYSTEM

## 8.1 ITERATION FLOW

```
run test
→ report
→ delta
→ fix input
→ Copilot fix
→ validate
→ repeat
```

---

## 8.2 STOP PRIORITY (STRICT ORDER)

1. scoreDelta < 0 → STOP (regression)
2. *(not implemented — Phase 3 backlog: critical persists iteration ≥ 2 → STOP)*
3. no progress ×2 → STOP
4. score ≥ 80 AND scoreDelta ≥ 0 → SUCCESS

---

# 9. FREEZE MODE (PREVENTION LAYER)

## 9.1 ACTIVATION

All four current-run conditions must be true AND last 3 `governance-history.json` entries must each have `score ≥ 80 AND criticalCount = 0`:

```
score ≥ 80  AND  criticalCount = 0  AND  stabilityScore = 1.0  AND  rootCauses = 0
```

---

## 9.2 EFFECT

* Any change REQUIRES re-run
* Blocks regression before commit

---

## 9.3 DEACTIVATION (AUTOMATIC)

Auto-removed if any run produces: score < 80 OR criticalCount > 0 OR rootCauses > 0 OR stabilityScore < 1.0. Re-activation requires 3 consecutive qualifying history entries.

---

# 10. OBSERVABILITY (NON-SCORING)

## 10.1 visualConsistency

Tracks UI variance (meta only)

## 10.2 performance

Tracks timing + CLS (meta only)

## 10.3 stability

Tracks flakiness

---

# 11. RULE ENGINE

## 11.1 rules.json

Defines per rule: `ruleKey`, `ruleId`, `severity`, `confidence`, `enabled`

Deserialized into `RuleDefinition`. Validated on load by `RuleEngineValidator`.

---

## 11.2 VALIDATION (`RuleEngineValidator`)

MUST throw on:

* duplicate ruleKey
* unknown ruleId (not in `UiGovernanceRunner.KnownRuleIds`)
* invalid severity

---

## 11.3 POST-RUN VALIDATION (`RuleValidator`)

Runs after every test run. Does NOT affect scoring. Detects:

| Status | Condition |
|--------|-----------|
| `broken` | Failed rule has no Message (engine fault) |
| `suspicious` | Failed layout rule whose Message contains `'0px'` (measurement glitch), OR failed routing rule whose Message contains `'outside'` (path mismatch) |
| `valid` | Result passes all checks — no anomaly detected |
| `meta` | `IsMeta = true` — skipped from all validation |

> `FlakeRetried = true` means the rule **failed on both attempts**. If the retry succeeds the field stays false and `Passed = true`. `stabilityScore` counts only persistent failures.

Output: `List<RuleValidationResult>` — written to `governance-report.json` under `"validations"`

---

# 12. THRESHOLD SYSTEM

## 12.1 rule-thresholds.json

* All thresholds configurable
* MUST NOT be loosened (anti-abuse)

**Required `_governance` block:**

```json
{
  "_governance": {
    "version": "1.0.0",
    "reviewedBy": "threshold-review",
    "note": "DO NOT increase thresholds to achieve a green build. Each change requires a comment explaining the intentional design decision."
  },
  "layout.no_horizontal_overflow": { "thresholdPx": 2 },
  "typography.no_text_overflow":   { "thresholdPx": 4 },
  "layout.topbar_not_clipping":    { "thresholdPx": 4 }
}
```

**Defaults (if key missing):** overflow=2, textOverflow=4, topBar=4

Console audit trail emitted on startup: `[GovernanceThresholds] version=1.0.0 — overflow=2px, textOverflow=4px, topBar=4px`

---

# 13. AUTONOMOUS MODE (REALISTIC)

## 13.1 DEFINITION

Autonomous mode is:

> **Best-effort orchestration — NOT guaranteed execution**

---

## 13.2 LIMITATIONS

Copilot:

* is NOT deterministic
* cannot be forced to write files
* cannot run as a worker

**Practical implication — human trigger required:**
`run-ui-autonomous.ps1` opens prompt files with `code $promptFile`. This does NOT trigger Copilot to run. A human must invoke the agent prompt each iteration. Without action, `Wait-ForFile` exits after `$WaitTimeout` seconds. True zero-human-input execution is not possible with current VS Code tooling.

---

## 13.3 SYSTEM REQUIREMENTS

All loops MUST:

* use timeouts
* tolerate missing outputs
* fail safely

---

## 13.4 SCRIPTS (current implementation)

**Orchestrators (choose one per session):**

| Script | Mode | Pauses |
|--------|------|--------|
| `scripts/run-ui-1click.ps1` | Minimal — one iteration, two Read-Host pauses | 2× (after analysis, after fix) |
| `scripts/run-ui-autofix.ps1` | Semi-auto loop — score-gated, git baseline tracking | 1× per iteration |
| `scripts/run-ui-autoloop.ps1` | Auto-loop — thin wrapper over `run-ui-autonomous.ps1` | 0 |
| `scripts/run-ui-autonomous.ps1` | Full autonomous — Wait-ForFile + git diff polling, stop conditions | 0 |

**Pipeline scripts (called by orchestrators):**

| Script | Purpose |
|--------|---------|
| `scripts/ai/build-screenshot-analysis-input.ps1` | Scans Visual/ → `screenshot-analysis-input.json` |
| `scripts/ai/transform-analysis-to-fixes.ps1` | `screenshot-analysis.json` → `copilot-fix-input.json` |
| `scripts/ai/validate-fix.ps1` | git diff contract check (inline styles, line count, new files) |

## 13.7 WHEN TO USE WHICH ORCHESTRATOR

| Situation | Use |
|-----------|-----|
| First time / getting started | `run-ui-1click.ps1` |
| Daily loop, want score tracking | `run-ui-autofix.ps1` |
| Want full auto with no pauses | `run-ui-autoloop.ps1` or `run-ui-autonomous.ps1` |
| Debugging a specific issue | `run-ui-1click.ps1` (most visibility) |

## 13.5 PROMPT FILES (`mode: agent`)

| File | Role |
|------|------|
| `scripts/ai/copilot-analysis.prompt.md` | Batch screenshot → `screenshot-analysis.json` |
| `scripts/ai/copilot-fix.prompt.md` | Fix one root cause → CSS changes |
| `scripts/ai/SCREENSHOT-ANALYSIS-PROMPT.md` | Manual reference (semi-auto mode) |

## 13.6 `Wait-ForFile` RULE

Delete stale output file BEFORE waiting. Wait key = `LastWriteTime > $since`.
Never use `Test-Path` alone — leftover files cause false positives.

---

# 14. CROSS-BROWSER SYSTEM

* Chromium = baseline (only browser tested in Phase 1–2)
* Firefox/WebKit = validation only, **not yet implemented** — Phase 3 backlog
* `UiGovernanceTests.cs` reads `governance-report-firefox.json` / `governance-report-webkit.json` if they exist (forward-compatible), but nothing in the repo produces them yet
* flaky results ignored

---

# 15. EXPORT SYSTEM

**Per-run output files:**

| File | Content |
|------|---------|
| `governance-report.json` | score, dimensions, rootCauses, coverage, visualConsistency, performance, stability, validations, rules, runSignature |
| `governance-delta.json` | previousScore, currentScore, scoreDelta, isRegression |
| `governance-escalations.json` | Rules with null/fallback selectorType — each: ruleKey + suggestedAction |
| `governance-report-chromium.json` | Browser-specific copy of governance-report.json |
| `governance-freeze.json` | Exists only while freeze active: frozenAt, frozenSince, envMode |
| `governance-cross-browser.json` | Emitted only when Firefox/WebKit reports exist with inconsistencies vs Chromium |
| `governance-history.json` | Append-only run history (see Section 16) |

**`GREENAI_GOVERNANCE_MODE`** env var — sets `envMode` in report, runSignature, freeze. Default: `"full"`.

**`analysis-pack.zip`** — `VisualAnalysisExporter`: packages `TestResults/Visual/current/{device}/*.png` with `instructions.json` for external AI. Device folders: desktop, laptop, tablet, mobile.

---

# 16. HISTORY SYSTEM

Append-only. Fields per entry: `run`, `timestamp`, `score`, `criticalCount`, `majorCount`, `minorCount`, `flakyCount`, `stabilityScore`.

**Stability formula:**

```
flakyCount     = results.Count(r => r.FlakeRetried)  // FAILED even after retry
stabilityScore = results.Count == 0 ? 1.0 : Round(1.0 - flakyCount / results.Count, 2)
```

**Freeze gate:** `stabilityScore == 1.0` required at activation. Used for: freeze gate, trend analysis, regression detection.

---

# 17. SYSTEM INVARIANTS

Copilot MUST NEVER:

* modify governance logic
* bypass contract
* guess missing data
* fix outside ownership

---

# 18. PHASE ROADMAP

## Phase 1–2 (DONE)

* UI governance
* scoring
* loop
* root cause
* freeze
* config system

## Phase 3 (NEXT)

* API governance
* integration governance
* E2E flow rules
* global score

---

# 19. FINAL PRINCIPLE

System = deterministic
AI = non-deterministic

Therefore:

> **System MUST control AI — never the opposite**

---

---

# PHASE STATUS

| Phase | Status | Date |
|-------|--------|------|
| Phase 1 — Foundation (rules, scoring, CLI, history) | ✅ Complete | 2026-04-06 |
| Phase 2 — Advanced (cross-browser, IsMeta, autonomous) | ✅ Complete | 2026-04-07 |
| Phase 3 — Production (freeze gate, CI, alerts) | 🔲 Planned | — |

Audit cross-reference: `docs/AI/UI_GOVERNANCE_AUDIT_PHASE2.md` — W1–W5 status

## VISUAL AI INTEGRATION

* ✅ Auto batch screenshot scan (`build-screenshot-analysis-input.ps1`)
* ✅ Screenshot → AI analysis → fix pipeline
* ✅ Before/after comparison via git diff + validate-fix
* 🔲 Auto visual regression gate in CI

# END OF SPEC v3
