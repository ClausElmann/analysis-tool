# messaging — Domain Distillation

**Status:** APPROVED_BASELINE 2026-04-11  
**Completeness score (Layer 1):** 0.47 (behaviors=[] rules=garbage — source-primary)  
**Evidence source:** `message-wizard/` Angular feature, `SmsSendMethod` OpenAPI enum, `WizardStep` enum  

---

## What this domain is

**Messaging** is the core broadcast authoring and sending domain. It implements the multi-step **message wizard** that guides a user from recipient selection through message composition to transmission confirmation. It also hosts the **broadcasting dashboard** (front page), **single-message shortcuts** (single SMS, single email), and the **limited wizard** for restricted-access scenarios.

---

## Send Methods (SmsSendMethod — 19 values, source-verified)

| Value | Description |
|---|---|
| ByAddress | Address-based recipient lookup + selection |
| ByMap | Geographic map drawing — draws polygon → residents |
| ByLevel | Level/hierarchy tree selection (ByLevel service) |
| ByExcel | Excel/file spreadsheet import |
| BySingleSms | Direct single SMS (not a broadcast) |
| BySingleSmsGroup | Single SMS to existing SMS group |
| ByTestSingleSms | Test SMS (does not count as real delivery) |
| ByTestSingleEmail | Test Email |
| ByWeb | Web message channel |
| ByResend | Resend from existing SmsGroup |
| ByStencil | Create from saved stencil |
| ByStdReceivers | Standard receivers only (recipient list pre-configured) |
| ByWeatherWarning | Weather warning trigger |
| ByWarning | General warning trigger |
| BySmsLogs | Compose from historical SMS log entries |
| ByMessage | Start from existing message copy |
| Systembesked | System message (Danish audience) |
| ByMunicipality | Municipality-based geographic selection |
| Undefined | Unset / default |

---

## Wizard Steps (WizardStep enum — source-verified)

```
1: AddressSelection
2: StdReceivers
3: WriteMessage
4: Confirm
5: Complete
6: SchedulingSetup  (scheduled wizard only)
```

---

## Wizard Variants

### Standard Wizard (`message-wizard`)
Flow: `AddressSelection → [StdReceivers] → WriteMessage → Confirm → Complete`

- StdReceivers step shown only when `canSelectStdReceivers = true` (profile has selectableStdReceivers)
- No scheduling step

### Scheduled Wizard (`message-wizard-scheduled`)
Flow: `AddressSelection → [StdReceivers] → WriteMessage → [SchedulingSetup] → Confirm → Complete`

- For **stencil creation**: SchedulingSetup step is **omitted** (`isCreatingStencil=true` blocks it)
- `canNavigateToConfirmPage` requires `writeMessagePageVisited && scheduledBroadcast != undefined`
- Drafts / stencil URLs → `hideCurrentMessageInDrafts = true`

### Limited Wizard (`message-wizard-limited`)
- Template-only (select from profile templates, fixed text, no sender choice)
- Optional delay checkbox
- Guard (`canActivateLimitedWizardGuardFn`): blocks if SmsGroup already active/sent

---

## Wizard Initialization Logic

1. Subscribe to `currentProfile$` (filter non-null, take 1)
2. Call `initWizardModelAndSmsGroupId(profileId, smsGroupId)`
3. If SmsGroup already `.active` (and not plannedToBeEdited): redirect to `/broadcasting`
4. Set step from `messageMetadata.wizardStep` if present; else derive from URL
5. Fire `wizardInitialized` event → unlocks child component rendering

**Draft/stencil flag:** URLs containing `wizardScheduled` or `wizardStencil` set `hideCurrentMessageInDrafts = true`

---

## Step Navigation Rules

**Next button gates:**
- `nextButtonActive()` signal must be `true` (set by active child component)
- On Confirm step: `writeMessagePageVisited() = true` required
- SchedulingSetup: `scheduledBroadcast != null` required

**Step skip rules:**
| Condition | Effect |
|---|---|
| `ByStdReceivers` + `hasStdReceiversExtended` | `hideWizardProgressBar=true`, `skipWriteMessageStep=true` |
| `BySmsLogs` | `hideAddressesStep=true`, `canSelectStdReceivers=false` |
| `ByStdReceivers` (non-extended) | `hideAddressesStep=true` |

**Draft save:** Available at `StdReceivers` step via toolbar Save Draft button

**Back navigation:** Controlled by `canNavigateBackwards()` signal. `AddressSelection` is the floor (no back).

---

## Broadcasting Dashboard (front page)

Components:
- `send-methods-list` — renders available send method tiles based on profile capabilities
- `scenarios` panel — shown when `showScenarios=true` (profile-controlled)
- `bi-tabs` (Sms / E-mail) — single message shortcuts; gated by `CanSendSingleSmsAndEmail` user role
  - `single-sms`: templates, sender name, autosignature, reply numbers, delay default
  - `single-email`: templates, autosignature, delay default
- `latest-msg-box` (sent messages) — links to status view
- `latest-msg-box` (planned messages) — delete planned message
- SmsGroup approver inbox — shown if `isCurrenUserSmsGroupApprover$`

---

## Approval Workflow

- `userRequiresApproval$` (from `SmsGroupApproverService`) controls the `broadcast-complete` page
- **Approval required:** "Notification sent to admin" message; only FrontPage button shown
- **No approval required:** Receipt email sent notification + links to Front Page, Status view, Create Reminder

---

## Excel/Import Send Path

- `bi-data-import` component with `DataImportPurpose.Broadcast`
- Sample template download button
- `broadcast-import-settings` child: format-specific import settings
- Validation result lifts `nextButtonActive` when valid

---

## Write Message Step

- `bi-write-message` component receives:
  - `existingMessageMetadata` — pre-filled metadata (edit mode)
  - `currentUser`, `currentCustomer`, `currentProfile`
  - `hasStandardReceivers` — affects message channel options
- Emits `onMessageMetadataReady` → updates shared wizard state

---

## Capabilities

1. Multi-step broadcast wizard with 6 possible steps
2. 19 distinct send methods (address, map, level, excel, std, web, stencil, etc.)
3. Step skipping/hiding per send method (no address step for StdReceivers; no WriteMessage for extended StdReceivers)
4. Scheduled broadcast wizard (separate flow with SchedulingSetup step)
5. Stencil creation mode (scheduled wizard, no SchedulingSetup step)
6. Draft saving at StdReceivers step
7. Approval workflow (approval-required branch on broadcast-complete page)
8. Single SMS / Single Email shortcuts on dashboard (role-gated)
9. Limited wizard (template-only, guard-protected)
10. Broadcast dashboard with sent + planned message history boxes
11. Scenarios panel (profile-controlled)
12. SmsGroup approver inbox on dashboard
13. Excel import path for broadcast recipients
14. Wizard state persistence (step saved to `messageMetadata.wizardStep`)
15. Receipt email notification on successful broadcast

---

## Flows

### FLOW_MSG_001: Standard address-based broadcast
1. User navigates to broadcasting → selects ByAddress send method
2. Wizard opens at AddressSelection step
3. Address search → expand tree → select addresses
4. (Optional) StdReceivers step if profile has them
5. WriteMessage step: compose text, select channels, set sender
6. Confirm step: review summary, click Send
7. Complete step: receipt shown; email sent; link to Status view

### FLOW_MSG_002: Scheduled broadcast (future date)
1. User navigates to scheduling → creates new scheduled broadcast
2. Scheduled wizard opens at AddressSelection
3. Steps same as FLOW_MSG_001 except WriteMessage → SchedulingSetup → Confirm
4. SchedulingSetup: set future date/time, recurrence (if applicable)
5. Confirm: save as planned message
6. Complete: planned message created

### FLOW_MSG_003: Stencil creation
1. User creates stencil via scheduled wizard with `isCreatingStencil=true`
2. Steps: AddressSelection → StdReceivers → WriteMessage → Confirm → Complete
3. No SchedulingSetup (skipped in stencil mode)
4. Message saved as stencil template (not active broadcast)

### FLOW_MSG_004: ByStdReceivers extended mode
1. Send method = ByStdReceivers + profile.hasStdReceiversExtended
2. hideWizardProgressBar=true, skipWriteMessageStep=true
3. User sees expanded std-receivers configuration directly
4. Save Draft available at StdReceivers step
5. Next → Confirm → Complete

---

## Rules

| ID | Rule |
|---|---|
| MSG_R001 | Wizard blocks navigation to already-sent (active) SmsGroup; redirects to /broadcasting |
| MSG_R002 | Confirm step requires `writeMessagePageVisited=true` |
| MSG_R003 | SchedulingSetup step requires `scheduledBroadcast != null` to advance to Confirm |
| MSG_R004 | BySmsLogs: canSelectStdReceivers=false; AddressSelection step hidden |
| MSG_R005 | ByStdReceivers: AddressSelection step hidden |
| MSG_R006 | ByStdReceivers + hasStdReceiversExtended: WriteMessage step skipped; progress bar hidden |
| MSG_R007 | Limited wizard guard: SmsGroup must not be active; SmsGroupId must be present in URL |
| MSG_R008 | Approval required → broadcast-complete shows approval-pending state (no status link, no receipt links) |
| MSG_R009 | Draft saves only available at StdReceivers step; not available at WriteMessage or later |
| MSG_R010 | Single SMS / Single Email shortcuts gated by `CanSendSingleSmsAndEmail` user role |

---

## Gaps

| ID | Gap |
|---|---|
| GAP_001 | `message-wizard-limited` format is unclear — unsure whether limited wizard is entirely separate send flow or wraps existing wizard steps |
| GAP_002 | ByMap flow not fully traced — map-tools and polygon-selection behavior not read |
| GAP_003 | ByLevel ("ByLevel" send method) selection component not examined |
| GAP_004 | Scheduled broadcast recurrence (repeat scheduling) — SchedulingSetup component not read; recurrence capability unknown |
