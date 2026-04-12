# Slices 21–30 — Planning Document

> Generated: 2026-04-08  
> Based on: full system scan (filesystem + test inventory + EXECUTION_MEMORY.md)

---

## 1. Current System State

### 1.1 Feature Inventory

| Domain | Features | Backend ✅ | UI Page ✅ | E2E ✅ |
|---|---|---|---|---|
| Auth | Login, Logout, Me, RefreshToken, SelectCustomer, SelectProfile | ✅ | ✅ | ✅ |
| Auth | ChangePassword | ✅ | ✅ | ✅ |
| Auth | GetProfileContext | ✅ | n/a | n/a |
| AdminLight | AssignProfile, AssignRole, CreateUser | ✅ | ✅ | ✅ |
| AdminLight | ListSettings, SaveSetting | ✅ | ✅ | visual only |
| CustomerAdmin | GetCustomerSettings, GetProfiles, GetUsers | ✅ | ✅ | ✅ |
| Identity | ChangeUserEmail | ✅ | ❌ no UI page | ❌ |
| Localization | BatchUpsertLabels, GetLabels | ✅ | n/a | ✅ label-coverage |
| System | Health, Ping | ✅ | n/a | n/a |
| UserSelfService | UpdateUser | ✅ | ✅ (UserProfilePage) | visual only |
| UserSelfService | PasswordReset | ✅ | ❌ no UI page | ❌ |

### 1.2 UI Pages — Coverage Matrix

| Page | Route | Visual ✅ | Functional E2E ✅ | Governance ✅ | Label ✅ | Accessibility ✅ |
|---|---|---|---|---|---|---|
| BroadcastingHubPage | /broadcasting | ✅ | partial | ✅ /broadcasting only | ✅ | ✅ |
| SendWizardPage | /send/wizard | ✅ step1+2 | ❌ no full flow | ❌ | ✅ | ❌ |
| StatusPage (3 tabs) | /status | ✅ | ❌ | ❌ | ✅ | ❌ |
| StatusDetailPage | /status/:id | ✅ | ✅ | ❌ | ✅ | ❌ |
| DraftsPage | /drafts | ✅ | ❌ | ❌ | ✅ | ❌ |
| SelectCustomerPage | /select-customer | ✅ | ✅ (via LoginFlow) | ❌ | ✅ | ❌ |
| SelectProfilePage | /select-profile | ✅ | ✅ (via LoginFlow) | ❌ | ✅ | ❌ |
| CustomerAdminPage | /customer-admin | ✅ | ✅ | ❌ | ✅ | ❌ |
| AdminUserListPage | /admin/users | ✅ | ✅ | ❌ | ✅ | ❌ |
| AdminSettingsPage | /admin/settings | ✅ | ❌ | ❌ | ✅ | ❌ |
| SuperAdminPage | /admin/super | ❌ no visual | ❌ | ❌ | ✅ label only | ❌ |
| UserProfilePage | /user/profile | ✅ | ❌ no edit test | ❌ | ✅ | ✅ |
| DashboardPage | /dashboard | ✅ (redirects) | ❌ | ❌ | ✅ | ❌ |
| UIShowcase | /ui-showcase | ✅ | n/a | ❌ | partial | ❌ |

### 1.3 E2E Test Suite — Inventory

| File | Category | Test Count | Coverage |
|---|---|---|---|
| Accessibility/AccessibilityTests.cs | Accessibility | 5 | BroadcastingHub, CustomerAdmin, AdminSettings, UserProfile, Login |
| ColorSystem/ColorSystemTests.cs | ColorSystem | 7 | Computed CSS token assertions (all on /broadcasting) |
| ColorSystem/TypographySpacingTests.cs | ColorSystem | 7 | Typography + spacing token assertions |
| CustomerAdminE2ETests.cs | Functional | 9 | CustomerAdmin tabs + CRUD operations |
| DetailPageE2ETests.cs | Functional | 6 | StatusDetail stat cards + resend dialog |
| LabelCoverageE2ETests.cs | Labels | 12 | All pages — no missing labels |
| LoginFlowE2ETests.cs | Functional | 5 | Full login → SelectCustomer → SelectProfile |
| Demo/DemoFlowTests.cs | Demo | 1 | Full flow video (login → select → wizard → send) |
| Governance/CssTokenComplianceTests.cs | Governance | 3–5 | Static scan: no hardcoded colours/spacing in CSS |
| Governance/UiGovernanceTests.cs | Governance | 1 | 3 rules, /broadcasting ONLY, Desktop viewport |
| Visual/NavigationVisualTests.cs | Visual | 11 | Shell: topbar, overlay-nav, command-palette, resize |
| Visual/PageVisualTests.cs | Visual | 14 | 13 page scenarios × 4 devices (where applicable) |
| Visual/ShowcaseVisualTests.cs | Visual | 7 | UIShowcase components |
| VisualAnalysis/ExportVisualAnalysisTests.cs | Analysis | 1 | Screenshot export for AI analysis |

**Total E2E: ~89 tests** (unit tests: 337 in GreenAi.Tests)

### 1.4 Governance Rules — Current State

```json
{
  "rules": [
    { "ruleKey": "layout.no_horizontal_overflow",   "severity": "major",    "pages": ["/broadcasting"] },
    { "ruleKey": "tokens.primary_color",            "severity": "critical", "pages": ["/broadcasting"] },
    { "ruleKey": "typography.no_text_overflow",     "severity": "minor",    "pages": ["/broadcasting"] },
    { "ruleKey": "layout.topbar_not_clipping",      "severity": "major",    "pages": ["/broadcasting"] },
    { "ruleKey": "z-index.no_overlapping_clickable","severity": "unknown",  "pages": ["/broadcasting"] },
    { "ruleKey": "layout.spacing_scale",            "severity": "unknown",  "pages": ["/broadcasting"] },
    { "ruleKey": "typography.font_scale",           "severity": "unknown",  "pages": ["/broadcasting"] }
  ],
  "gap": "All 7 rules run ONLY against /broadcasting. 12 other pages have ZERO governance coverage."
}
```

### 1.5 Demo Engine — Current State

| Script | Status | Notes |
|---|---|---|
| scripts/demo/test-voice.ps1 | ✅ works | da-DK-ChristelNeural, confirmed |
| scripts/demo/merge-test.ps1 | ✅ fixed | VP8→H264 fix applied (KI-010) |
| scripts/demo/generate-audio.ps1 | ❓ not smoke-tested | TTS pipeline script |
| scripts/demo/generate-script.ps1 | ❓ not smoke-tested | Narration generation |
| scripts/demo/generate-voice.ps1 | ❓ not smoke-tested | Voice synthesis |
| scripts/demo/build-demo.ps1 | ❓ not smoke-tested | Full pipeline orchestrator |
| Demo/DemoFlowTests.cs | ✅ 1/1 PASSING | MP4 produced, pacing 3–4 s highlights |

### 1.6 Autonomous Loop — Current State

| Script | Mode | Gap |
|---|---|---|
| scripts/run-ui-autonomous.ps1 | "Autonomous" | Requires manual Copilot interaction at analysis step |
| scripts/run-ui-1click.ps1 | Semi-autonomous | 7-step, pauses for human Copilot |
| scripts/run-ui-autofix.ps1 | Autofix | Not read — scope unclear |
| scripts/run-ui-autoloop.ps1 | Loop | Not read — scope unclear |
| scripts/ai/build-screenshot-analysis-input.ps1 | Input builder | ✅ |
| scripts/ai/transform-analysis-to-fixes.ps1 | Transformer | ✅ |
| scripts/ai/validate-fix.ps1 | Validator | ✅ |

---

## 2. Slices 1–20 Validation

| Slice Range | Description | Status |
|---|---|---|
| 1–3 | Governance foundation: rules.json, rule engine, CssTokenComplianceTests, UiGovernanceTests | ✅ complete |
| 4–6 | Auth E2E + LoginFlow functional tests: login, SelectCustomer, SelectProfile, ChangePassword | ✅ complete |
| 7–9 | Color system tests: ColorSystemTests, TypographySpacingTests, token validation | ✅ complete |
| 10–12 | Visual test infrastructure: VisualTestBase, DeviceProfile, 4-device matrix, baselines | ✅ complete |
| 13 | CustomerAdmin E2E: functional tests for tabs + CRUD | ✅ complete |
| 14 | LabelCoverageE2ETests: all pages, no missing labels | ✅ complete |
| 15 | AccessibilityTests: WCAG assertions (5 pages) | ✅ complete |
| 16–18 | Demo Engine V2: test-voice, merge-test, DemoFlowTests (1/1), KI-007–KI-011 fixed | ✅ complete |
| 19 | Enterprise UI Polish Batches A–D: 42/42 visual tests, 0 warnings | ✅ complete |
| 20 | SSOT documentation: known-issues KI-007–KI-011, e2e-demo-pattern.md updated | ✅ complete |

**Assessment:** Slices 1–20 are fully delivered. No known regressions.

---

## 3. Gap Analysis

```json
{
  "critical_gaps": [
    {
      "gap": "UiGovernanceTests only covers /broadcasting",
      "impact": "12 pages have zero browser-based governance validation",
      "risk": "high — layout regressions invisible outside broadcasting"
    },
    {
      "gap": "PasswordReset has backend feature but no UI page and no E2E",
      "impact": "Feature is unreachable by users",
      "risk": "high — functional dead code"
    },
    {
      "gap": "ChangeUserEmail has backend feature but no UI page",
      "impact": "Identity feature unreachable",
      "risk": "medium"
    }
  ],
  "high_gaps": [
    {
      "gap": "SendWizard has no full-flow E2E (only step 1–2 visual)",
      "impact": "Core business flow untested functionally",
      "risk": "high"
    },
    {
      "gap": "SuperAdminPage has no visual and no functional E2E (label-only)",
      "impact": "Page appearance and function unvalidated",
      "risk": "medium"
    },
    {
      "gap": "200+ baseline screenshots exist but no pixel-diff comparison implemented",
      "impact": "Visual regressions not caught automatically",
      "risk": "medium"
    }
  ],
  "medium_gaps": [
    {
      "gap": "Demo engine full pipeline (generate-script → build-demo) not smoke-tested",
      "impact": "Pipeline failure would be silent until demo production attempt",
      "risk": "medium"
    },
    {
      "gap": "CssTokenCompliance scans only .css files, not Razor style= attributes",
      "impact": "Inline styles in .razor files bypass governance",
      "risk": "low-medium"
    },
    {
      "gap": "AccessibilityTests covers 2 of 12 pages",
      "impact": "Accessibility regressions invisible on 10 pages",
      "risk": "medium"
    },
    {
      "gap": "DashboardPage shows mock data — no real DB connection",
      "impact": "Dashboard is decorative, not informative",
      "risk": "product"
    }
  ]
}
```

---

## 4. Slices 21–30 — Proposals

---

### Slice 21 — Multi-Page Governance Sweep

```yaml
id: slice_21
name: Multi-Page Governance Sweep
goal: Extend UiGovernanceTests to run all 7 rules against every major page (not just /broadcasting)
why: |
  7 governance rules exist but only execute on /broadcasting.
  12 pages are invisible to governance. A typography regression on /status
  or a z-index bug on /customer-admin would not be caught.
deliverables:
  - UiGovernanceTests: parameterized test or additional [Fact] per page
  - Pages covered: /broadcasting, /status, /drafts, /send/wizard, /status/1,
                   /customer-admin, /admin/users, /admin/settings, /admin/super,
                   /user/profile, /select-customer, /select-profile
  - governance-report.json updated to include per-page results
  - All 7 rules run on all pages (currently only 3 verified to pass all pages)
depends_on: []
complexity: medium
risk: low — adding test coverage, not changing production code
priority: 1
business_value: Prevents silent layout regressions on any page, not just broadcasting
```

---

### Slice 22 — Password Reset UI + E2E

```yaml
id: slice_22
name: Password Reset — UI Page + Functional E2E
goal: Build the missing PasswordReset UI page and end-to-end test for the full reset flow
why: |
  PasswordReset backend feature (UserSelfService/PasswordReset/) fully exists.
  No UI page exists → feature is dead code. Users who forget their password
  have no recovery path.
deliverables:
  - src/GreenAi.Api/Components/Pages/Auth/PasswordResetPage.razor (new)
  - Route: /auth/reset-password?token=&email=
  - UI: new password input + confirm + submit → success message
  - E2E test: LoginFlowE2ETests or PasswordResetE2ETests.cs
    - request reset, receive token, navigate to page, set new password, verify login
  - Label coverage: page.passwordReset.* labels
  - Visual test: PageVisualTests adds PasswordResetPage_AllDevices
depends_on: []
complexity: medium
risk: low — backend already implemented
priority: 2
business_value: Closes a critical user-facing gap — users can recover access
```

---

### Slice 23 — Send Wizard Full-Flow Functional E2E

```yaml
id: slice_23
name: Send Wizard — Full 4-Step Functional E2E
goal: Write a functional end-to-end test covering all 4 wizard steps through to send confirmation
why: |
  SendWizard visual tests only cover steps 1–2 (method selection + recipients).
  Steps 3 (confirm) and 4 (send result/success) are untested.
  The core business flow — selecting recipients, configuring, and sending a message —
  has no functional E2E validation. DemoFlowTests covers the happy path visually
  but does not assert business logic (recipient count, message preview, etc.).
deliverables:
  - WizardE2ETests.cs (new) or extend DetailPageE2ETests
  - Test: WizardFlow_ByAddress_CompletesSuccessfully
    Step 1: select By Address method
    Step 2: enter and validate recipient address
    Step 3: review confirm screen — assert recipient count, message text
    Step 4: send → assert success or queued status
  - data-testid coverage gaps filled as needed
  - Wizard step 3+4 Razor pages: verify [data-testid] attributes present
depends_on: []
complexity: high — wizard state machine is complex
risk: medium — may require mock recipients or seeded test data
priority: 3
business_value: Validates the primary business action of the entire product
```

---

### Slice 24 — SuperAdminPage Visual + Functional E2E

```yaml
id: slice_24
name: SuperAdminPage — Visual + Functional E2E
goal: Add visual (4 devices) and functional E2E coverage for SuperAdminPage
why: |
  SuperAdminPage (/admin/super) has only one E2E fact: label coverage check.
  No screenshot exists. No functional actions tested. SuperAdmins manage
  global system settings — any regression here is invisible.
deliverables:
  - PageVisualTests: SuperAdminPage_AllDevices() ← new Fact
  - SuperAdminE2ETests.cs (new) or extend CustomerAdminE2ETests:
    - loads without error
    - lists global settings
    - toggles/saves a setting (if safe to do in E2E)
  - Governance: SuperAdminPage added to Slice 21 governance sweep
  - AccessibilityTests: SuperAdmin_NoWcagViolations() ← new Fact
depends_on: [slice_21]
complexity: low-medium
risk: low
priority: 4
business_value: Prevents admin UX regressions for the highest-privilege users
```

---

### Slice 25 — Screenshot Pixel-Diff Comparison

```yaml
id: slice_25
name: Pixel-Diff Baseline Comparison (Visual Regression Gate)
goal: Implement actual pixel-diff comparison against the existing 200+ baseline screenshots
why: |
  NavigationVisualTests + PageVisualTests capture screenshots and save baselines,
  but the diff step is explicitly deferred ("visual-regression.md: deferred until UI is stable").
  UI is now stable (Batches A–D complete, 0 warnings). Baselines are ready.
  Without diff comparison, visual tests only check layout assertions, not appearance.
  A colour change or element displacement would not be caught.
deliverables:
  - Choose comparison strategy: ImageSharp (pixel count) or SkiaSharp MSE threshold
  - VisualTestBase.AssertMatchesBaselineAsync(page, device, scenarioName) implement
  - Threshold config: VisualTestBase reads from rules.json or separate diff-config.json
    (e.g. maxAllowedDiffPercent: 0.5)
  - Baseline update workflow documented (GREENAI_UPDATE_BASELINE env var already exists)
  - SSOT: docs/SSOT/testing/patterns/visual-baseline-diff.md (new)
depends_on: []
complexity: medium-high
risk: medium — pixel thresholds need tuning; flaky tests possible on subpixel rendering
priority: 5
business_value: Catches appearance regressions that layout assertions miss (colour, font-weight, icon changes)
```

---

### Slice 26 — Governance Rule: Inline-Style Ban (Razor Scan)

```yaml
id: slice_26
name: Governance Rule — Inline Style Ban in Razor Files
goal: Extend CssTokenComplianceTests to detect style= attributes in .razor files
why: |
  CssTokenComplianceTests currently scans .css files for hardcoded values.
  Razor files can bypass this with inline style= attributes (e.g. style="color: #2563EB").
  This is a known governance gap — no test catches it.
  Enterprise Polish Batch work may have introduced some inline styles as quick fixes.
deliverables:
  - CssTokenComplianceTests: new [Fact] AllRazorFiles_HaveNoInlineStyles()
    - Regex: style\s*=\s*"[^"]*(?:#[0-9a-fA-F]{3,6}|px|rem|em)[^"]*"
    - Exclude: deliberately allowed exceptions via comment marker // governance-allow-inline
    - Reports filename + line number on failure
  - Scan result: run once to find existing violations, fix them in same PR
  - Add to docs/SSOT/ui/color-system.md: inline-style prohibition rule
depends_on: []
complexity: low
risk: low
priority: 6
business_value: Closes a governance gap — enforces design token usage across all Razor
```

---

### Slice 27 — ChangeUserEmail — UI Page + E2E

```yaml
id: slice_27
name: ChangeUserEmail — UI Page + Functional E2E
goal: Build the UI surface for the existing ChangeUserEmail backend feature
why: |
  Identity/ChangeUserEmail/ backend feature exists (endpoint, handler, validator, SQL).
  No UI page exposes it. UserProfilePage is the natural place — add an "Change Email"
  section or link to a separate /user/change-email page.
deliverables:
  - Option A: Add ChangeEmail section to UserProfilePage.razor (preferred — fewer routes)
    - Email field + current password confirmation + submit
    - On success: re-login flow (JWT invalidated, redirected to Login)
  - Option B: Separate /user/change-email route
  - E2E test: UserProfileE2ETests.cs (new)
    - Navigate to change email section
    - Submit valid current password + new email
    - Assert redirect to login (JWT cleared)
  - Label coverage: labels for new UI text
  - Visual: update PageVisualTests or NavigationVisualTests for UserProfile
depends_on: []
complexity: medium
risk: medium — JWT invalidation must be tested carefully; race condition possible
priority: 7
business_value: Enables users to manage their own identity — core self-service capability
```

---

### Slice 28 — Demo Engine Full Pipeline Smoke Test

```yaml
id: slice_28
name: Demo Engine — Full Pipeline Smoke Test
goal: Create a script that exercises the complete demo production pipeline end-to-end
why: |
  demo/DemoFlowTests.cs (1/1 passing) validates the browser recording.
  The narration pipeline (generate-script → generate-voice/generate-audio → build-demo)
  has never been smoke-tested as a whole. A broken Azure TTS key, changed API response
  format, or ffmpeg codec issue would only be discovered when trying to produce a demo.
  merge-test.ps1 works, but the full orchestration via build-demo.ps1 is untested.
deliverables:
  - scripts/demo/smoke-test-pipeline.ps1 (new, inline — NOT committed as permanent)
    Actually: extend build-demo.ps1 with a -SmokeTest flag:
    - Runs generate-script.ps1 with a 2-sentence script
    - Runs generate-voice.ps1 for 1 audio file
    - Merges 1 clip → 1 MP4
    - Asserts MP4 exists, duration > 0, file size > 10 KB
  - Document: docs/SSOT/testing/known-issues.md — add demo pipeline smoke-test procedure
  - Verify: da-DK-ChristelNeural still the default voice
depends_on: []
complexity: medium
risk: medium — requires Azure TTS key and ffmpeg present
priority: 8
business_value: Prevents demo pipeline from silently breaking between demo sessions
```

---

### Slice 29 — Dashboard Real Data Connection

```yaml
id: slice_29
name: Dashboard — Real DB Data (Sent/Scheduled Counts)
goal: Connect BroadcastingHubPage stats to real database counts instead of mock data
why: |
  DashboardPage (/dashboard) redirects to /broadcasting.
  BroadcastingHubPage displays send-method cards and likely shows stats/counts.
  If these are hardcoded or always empty, the page provides no operational value.
  Connecting to real sent/scheduled message counts makes the dashboard actionable.
deliverables:
  - New feature: Features/Broadcasting/GetDashboardStats/ (if not exists)
    - Returns: sent_today, scheduled_today, failed_today, total_this_month
    - Scoped by CustomerId (tenant-isolated)
    - SQL: one .sql file per convention
  - BroadcastingHubPage.razor: displays counts in stat cards
  - Unit tests: GetDashboardStatsHandler tests (GreenAi.Tests)
  - E2E: NavigationVisualTests.Dashboard_AllDevices asserts stat cards visible
  - No mock data left in Razor after this slice
depends_on: []
complexity: medium
risk: low — read-only query, no write operations
priority: 9
business_value: Transforms dashboard from decorative to operational for users
```

---

### Slice 30 — Accessibility Scorecard Expansion

```yaml
id: slice_30
name: Accessibility — Full-Suite WCAG 2.1 AA Coverage
goal: Expand AccessibilityTests from 5 pages to all major pages
why: |
  AccessibilityTests covers 5 pages: BroadcastingHub, CustomerAdmin, AdminSettings,
  UserProfile, Login. 9 major pages have no accessibility assertions.
  WCAG 2.1 AA is a legal requirement in several markets (Denmark/EU).
  Expanding coverage now is cheaper than retrofitting after a user complaint.
deliverables:
  - AccessibilityTests: add [Fact] for each uncovered page:
    - Status, StatusDetail, Drafts, SendWizard, SelectCustomer, SelectProfile,
      AdminUserList, SuperAdmin (+ PasswordReset from slice_22)
  - Each test: navigate → run axe-core assertions (same pattern as existing 5)
  - Consolidate: AccessibilityTestBase.AssertWcagAsync() if not already extracted
  - Report: docs/SSOT/testing/accessibility-coverage.md (baseline scores per page)
  - Fix: any violations discovered in the sweep (likely <5 based on existing track record)
depends_on: [slice_22, slice_24]
complexity: medium
risk: low — read-only test additions
priority: 10
business_value: Legal compliance + better UX for all users, especially screen-reader users
```

---

## 5. Priority Order Summary

| # | Slice | Priority | Complexity | Risk | Value |
|---|---|---|---|---|---|
| 1 | Slice 21 — Multi-Page Governance Sweep | ⭐⭐⭐ | medium | low | Prevents silent regressions across 12 pages |
| 2 | Slice 22 — Password Reset UI + E2E | ⭐⭐⭐ | medium | low | Closes critical user-facing gap |
| 3 | Slice 23 — Send Wizard Full-Flow E2E | ⭐⭐⭐ | high | medium | Core business flow validated |
| 4 | Slice 24 — SuperAdminPage Visual + Functional | ⭐⭐ | low | low | Admin page coverage complete |
| 5 | Slice 25 — Pixel-Diff Baseline Comparison | ⭐⭐ | high | medium | True appearance regression gate |
| 6 | Slice 26 — Governance: Inline-Style Ban | ⭐⭐ | low | low | Closes CSS governance gap |
| 7 | Slice 27 — ChangeUserEmail UI + E2E | ⭐⭐ | medium | medium | Self-service identity complete |
| 8 | Slice 28 — Demo Pipeline Smoke Test | ⭐ | medium | medium | Demo production reliability |
| 9 | Slice 29 — Dashboard Real Data | ⭐⭐ | medium | low | Operational dashboard |
| 10 | Slice 30 — Accessibility Full Suite | ⭐⭐ | medium | low | Legal compliance |

---

## 6. Recommended Execution Order

```
Week 1: Slice 21 (governance) + Slice 26 (inline-style ban)
         → Both are test-only, 0 production code risk, yield broad safety net

Week 2: Slice 22 (PasswordReset UI) + Slice 24 (SuperAdminPage)
         → Fill known dead-code gaps, complete admin coverage

Week 3: Slice 23 (Wizard full flow)
         → Complex, needs full session — core business validator

Week 4: Slice 27 (ChangeUserEmail) + Slice 29 (Dashboard data)
         → Self-service features complete, dashboard becomes useful

Week 5: Slice 25 (Pixel-diff) + Slice 30 (Accessibility)
         → Infrastructure investment with long-term payoff

Anytime: Slice 28 (Demo pipeline smoke test)
         → Run before any demo production session
```

---

## 7. What Would Come After Slice 30?

The next logical phase (Slices 31–40) would focus on:

1. **Real notification sending** — connect to SMS gateway (mock is in place)
2. **Scheduling** — send at a future time, CRON-based recurring
3. **Template system** — reusable message templates with variable substitution
4. **Recipient list management** — upload CSV, manage groups
5. **Audit trail** — full send history with delivery receipts (webhook inbound)
6. **Multi-language UI** — current localization is Danish only
7. **Customer onboarding flow** — new customer self-registration
8. **Reporting** — export sent reports as PDF/Excel
9. **API key management** — external integrations
10. **Mobile app or PWA** — offline-capable send from field

---

*SSOT source: `docs/SSOT/_system/SLICES_21_30_PLANNING.md`*  
*Related: `docs/SSOT/governance/EXECUTION_MEMORY.md`*
