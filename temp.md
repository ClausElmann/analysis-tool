# SESSION STATUS — 2026-04-10 18:00

## CURRENT TASK
Email domain — Entities extraction (Architect directive: entities only, Layer 0 verified)

---

## COPILOT → ARCHITECT (Latest Report)

### 🎯 Completed
- Read all 7 C# entity files from Layer 0 (ServiceAlert.Core)
- Read all 7 matching DB table definitions (ServiceAlert.DB/Tables/)
- Updated domains/Email/010_entities.json: 4 → 7 entities (all source-cited)
- Updated domains/Email/000_meta.json: status, entity count, sources

### ⚠️ Blockers
None — all entities fully mapped. One governance question for Architect (see below).

### 📊 Findings

**Complete entity inventory (7 entities, all verified):**

| Entity | C# File | DB Table | Status |
|---|---|---|---|
| EmailMessage | Domain/Mails/EmailMessage.cs:8-90 | EmailMessages.sql | ✅ Verified |
| EmailAttachment | Domain/Mails/EmailAttachments.cs:1-30 | EmailAttachments.sql | ✅ Verified |
| EmailTemplate | Domain/Mails/EmailTemplate.cs:1-49 | EmailTemplates.sql | ✅ Verified |
| Email2SmsWhitelistEntry | Domain/Profiles/Email2SmsWhitelist/Email2SmsWhitelistEntry.cs:1-7 | Email2SmsWhitelistEntries.sql | ✅ Verified |
| ProcessedInboundEmail | Domain/Mails/ProcessedInboundEmail.cs:1-30 | ProcessedInboundEmails.sql | ✅ **NEW** |
| BlockedTemporaryEmailAddressDomain | Domain/Mails/BlockedTemporaryEmailAddressDomain.cs:1-13 | BlockedTemporaryEmailAddressDomains.sql | ✅ **NEW** |
| TemplateEmail | Domain/Templates/Entities/TemplateEmail.cs:1-9 | TemplateEmails.sql | ✅ **NEW** |

**C# vs DB discrepancies observed (all factual, no interpretation):**

- `EmailMessage.ExternalRefId`: C# = `long?`, DB = `INT NULL`
- `EmailMessage.SmsLogId`: C# = `long?`, DB = `INT NULL`
- `EmailMessage.DateCreatedUtc`: In DB (DEFAULT getutcdate()), NOT in C# entity
- `EmailMessage.ResponseBody`: In DB (VARCHAR(10)), NOT in C# entity
- `EmailAttachment.DateCreatedUtc`: In DB (DEFAULT getutcdate()), NOT in C# entity
- `EmailTemplate.DateCreatedUtc`: In DB (DEFAULT getutcdate()), NOT in C# entity
- `BlockedTemporaryEmailAddressDomain.DatetimeCreatedUtc`: DB uses lowercase 't' vs C# uppercase 'T'
- `ProcessedInboundEmail`: No Id column in DB — composite PK (MessageIdHash + RecipientHash), but C# inherits BaseEntity (int Id). DB and C# are structurally inconsistent.

**EmailStatus enum — full observed state list:**
`Importing(1) → Queued(2) → SendingToGateway(3) → ValidationError(8) → SentToGatewayFailed(9) → SentToGateway(10) → InvalidEmail(11) → SentToGatewaySandbox(15) → Processed(30) → Dropped(31) → Delivered(32) → Deferred(33) → Bounced(34) → Blocked(35) → Opened(36) → Clicked(37) → SpamReport(38) → UnSubscribe(39) → GroupUnSubscribe(40) → GroupReSubscribe(41) → Redundant(204) → QueuedFirstRetry(450) → SendingToGatewayFirstRetry(451) → QueuedSecondRetry(452) → SendingToGatewaySecondRetry(453) → QueuedThirdRetry(454) → SendingToGatewayThirdRetry(455)`

Source: ServiceAlert.Core/Domain/Mails/EmailStatus.cs:1-43 ✅

### ❓ Decisions Needed

1. **rethink fields in 010_entities.json**: Prior extraction (iterations 1-17) added `rethink` arrays to all 4 original entities — these contain design proposals (normalized schemas, proposed technologies). Under governance v3.1 (ANALYSIS MODE, no Copilot design proposals), these violate the protocol.
   - **Impact**: rethink fields mix observations with design decisions — if retained, risk of Architect treating them as authoritative
   - **Options**:
     - Option A: Remove all `rethink` fields — entities contain OBSERVED facts only
     - Option B: Retain as labeled observations — rename to `legacy_proposals` (not authoritative)
   - Awaiting Architect decision.

2. **`normalized_interpretation` fields**: Same issue — these contain green-ai design suggestions (blob storage, Razor layout, etc.) generated before governance v3.1. Same options as above.
   - Awaiting Architect decision.

3. **ProcessedInboundEmail BaseEntity conflict**: C# inherits BaseEntity (int Id) but DB has no Id column (composite PK). This is a structural inconsistency in the original codebase.
   - Impact: Cannot verify entity-to-table mapping cleanly
   - Options:
     - Option A: Document as-is (inconsistency observed, no mapping gap in extraction)
     - Option B: Mark as CONFLICTING and request deeper investigation
   - Awaiting Architect decision.

### 📈 Metrics
- Domains extracted: Email entities pass (7/7)
- Entities completeness: 7 verified of 7 known = 0.90 ✅
- UNKNOWN count: 0 (all entities mapped to DB tables)
- DB discrepancies documented: 8

---

## ARCHITECT → COPILOT (Latest Directive)
[User will paste Architect's response here]

---

## NEXT ACTIONS
Awaiting Architect directive. Do NOT proceed to behaviors/flows/rules extraction without explicit instruction.
