# DFEP REPORT — Templates
_Generated: 2026-04-17 23:24 UTC | DFEP v1_

## Coverage

| Metric | Value |
|--------|-------|
| L0 capabilities | 26 |
| GreenAI capabilities | 10 |
| Matched | 22 |
| **Functional coverage** | **27% ❌** |

- 🔥 CRITICAL: 4
- ❗ HIGH: 6
- ⚠️  MEDIUM: 2
- ✅ NONE: 5

## ✅ Matched

- **Create new template** `templates.create_template` ← ServiceAlert.Contracts/Extensions/ServiceCollection/ServiceCollectionExtensions.cs:460 – AddTemplateServices
- **Update existing template** `templates.update_template` ← ServiceAlert.Services/Mails/EmailTemplateService.cs:180 – UpdateTemplatesFromEmbeddedResources

## ❌ Missing — CRITICAL

### Send SMS to recipient
- **ID:** `lookup.send_sms`
- **Action:** 🔨 MUST_BUILD
- **Rationale:** 'Send SMS to recipient' is a core customer capability present in L0 but MISSING in GreenAI.
- **Issues:**
  - Capability 'Send SMS to recipient' exists in L0 but NOT in GreenAI
- **Evidence:** ServiceAlert.Test/Services/Lookup/CodeLookup/CommandProcessors/LookupNorwegianCompany1881DataCommandProcessorTests.cs:304 – Process_WithSendSMSFalse_DoesNotCreateMobileEvents

### Remove template from profile
- **ID:** `templates.remove_template_profile`
- **Action:** 🔨 MUST_BUILD
- **Rationale:** 'Remove template from profile' is a core customer capability present in L0 but MISSING in GreenAI.
- **Issues:**
  - Capability 'Remove template from profile' exists in L0 but NOT in GreenAI
- **Evidence:** ServiceAlert.Api/Controllers/StandardReceiverController.cs:721 – RemoveProfileFromGroup

### Property owner lookup
- **ID:** `templates.owner_lookup`
- **Action:** 🔨 MUST_BUILD
- **Rationale:** 'Property owner lookup' is a core customer capability present in L0 but MISSING in GreenAI.
- **Issues:**
  - Capability 'Property owner lookup' exists in L0 but NOT in GreenAI
- **Evidence:** ServiceAlert.Services/Search/SearchService.cs:234 – GetOwnersOnAddressAsync

### Send Email to recipient
- **ID:** `lookup.send_email`
- **Action:** 🔨 MUST_BUILD
- **Rationale:** 'Send Email to recipient' is a core customer capability present in L0 but MISSING in GreenAI.
- **Issues:**
  - Capability 'Send Email to recipient' exists in L0 but NOT in GreenAI
- **Evidence:** ServiceAlert.Test/Services/Lookup/CodeLookup/CommandProcessors/LookupNorwegianCompany1881DataCommandProcessorTests.cs:366 – Process_WithSendEmailFalse_DoesNotCreateEmailEvents

## ❗ High Severity

### Address lookup
- **ID:** `templates.address_lookup`
- **Match:** ⚡ MISMATCH (score=0.40)
- **Action:** 🔨 MUST_BUILD
- **Rationale:** 'Address lookup' matched but has rule/isolation gaps that must be fixed.
  - ⚡ Missing rule: 'Customer isolation' (present in L0, absent in GreenAI)
- **Evidence:** ServiceAlert.Services/Enrollments/EnrollmentService.cs:393 – GetAddressStatistics, GreenAi.Sources/Dar/DarImporter.cs:1

### Assign template to profile
- **ID:** `profiles.assign_template_profile`
- **Match:** ⚡ MISMATCH (score=0.50)
- **Action:** 🔨 MUST_BUILD
- **Rationale:** 'Assign template to profile' matched but has rule/isolation gaps that must be fixed.
  - ⚡ Missing rule: 'Customer isolation' (present in L0, absent in GreenAI)
- **Evidence:** ServiceAlert.Services/Profiles/ProfileService.cs:54 – AddProfileAccessToUsers, GreenAi.Api/Database/Migrations/V069_MessageTemplates.sql:1

### SMS group management
- **ID:** `templates.sms_group`
- **Match:** ❌ MISSING (score=0.00)
- **Action:** 🔍 REVIEW
- **Rationale:** 'SMS group management' exists in L0 but not in GreenAI — classify as MUST_BUILD or DEFERRED.
  - ⚡ Capability 'SMS group management' exists in L0 but NOT in GreenAI
- **Evidence:** ServiceAlert.Services/Benchmarks/BenchmarkService.cs:265 – GetSmsGroupsForBenchmark

### List templates for profile
- **ID:** `templates.list_templates`
- **Match:** ⚡ MISMATCH (score=0.50)
- **Action:** 🔨 MUST_BUILD
- **Rationale:** 'List templates for profile' matched but has rule/isolation gaps that must be fixed.
  - ⚡ Missing rule: 'Customer isolation' (present in L0, absent in GreenAI)
  - ⚡ Missing rule: 'Profile visibility filter' (present in L0, absent in GreenAI)
  - ⚡ Missing rule: 'Validation / error handling' (present in L0, absent in GreenAI)
- **Evidence:** ServiceAlert.Services/Templates/TemplateService.cs:32 – GetTemplatesForSmsAndEmail, GreenAi.Api/Features/Templates/GetTemplates/GetTemplatesEndpoint.cs:1

### Get single template by ID
- **ID:** `templates.get_template_by_id`
- **Match:** ⚡ MISMATCH (score=0.40)
- **Action:** 🔨 MUST_BUILD
- **Rationale:** 'Get single template by ID' matched but has rule/isolation gaps that must be fixed.
  - ⚡ Missing rule: 'Validation / error handling' (present in L0, absent in GreenAI)
- **Evidence:** ServiceAlert.Services/Templates/TemplateService.cs:45 – GetTemplateById, GreenAi.Api/Features/Templates/GetTemplateById.sql:1

### Delete template
- **ID:** `templates.delete_template`
- **Match:** ⚡ MISMATCH (score=0.40)
- **Action:** 🔨 MUST_BUILD
- **Rationale:** 'Delete template' matched but has rule/isolation gaps that must be fixed.
  - ⚡ Missing rule: 'Customer isolation' (present in L0, absent in GreenAI)
  - ⚡ Missing rule: 'Validation / error handling' (present in L0, absent in GreenAI)
- **Evidence:** ServiceAlert.Services/Templates/TemplateService.cs:100 – DeleteTemplateResponseOptionsAsync, GreenAi.Api/Features/Templates/UpdateTemplate/DeleteTemplateProfileAccess.sql:1

## ⚠️ Mismatches / Medium Gaps

- **Merge field token substitution** `customers.merge_fields`
  - Match: ❌ MISSING | Action: ⏳ DEFERRED
  - 'Merge field token substitution' is a deferred/legacy feature (voice/social/merge) — intentionally out of scope for current phase.
  - ⚡ Capability 'Merge field token substitution' exists in L0 but NOT in GreenAI
  - Evidence: ServiceAlert.Services/Subscriptions/Models/CustomerSubscriptionNotification.cs:20 – HandleMergeFields
- **Manage customer dynamic merge fields** `templates.dynamic_merge_fields`
  - Match: ❌ MISSING | Action: ⏳ DEFERRED
  - 'Manage customer dynamic merge fields' is a deferred/legacy feature (voice/social/merge) — intentionally out of scope for current phase.
  - ⚡ Capability 'Manage customer dynamic merge fields' exists in L0 but NOT in GreenAI
  - Evidence: ServiceAlert.Core/Domain/MergeFields/MergeFields.cs:461 – GetDynamicMergeFieldNames

## ➕ Extra (GreenAI-only — not in L0)

- **Track delivery status** `templates.track_delivery`
  - 'Track delivery status' is a GreenAI addition not present in L0 — document as intentional.
  - Evidence: GreenAi.Api/Database/Migrations/V047_Sms_DispatchAttempts.sql:1
- **Outbox message processing** `templates.outbox_send`
  - 'Outbox message processing' is a GreenAI addition not present in L0 — document as intentional.
  - Evidence: GreenAi.Api/Database/Migrations/V054_RetryDeadLetter.sql:1
- **Send direct message** `templates.send_direct`
  - 'Send direct message' is a GreenAI addition not present in L0 — document as intentional.
  - Evidence: GreenAi.Api/Features/Templates/MessageTemplateDto.cs:1

## 🔨 Action Plan

### MUST_BUILD
- [ ] **Address lookup** (❗ HIGH)
- [ ] **Send SMS to recipient** (🔥 CRITICAL)
- [ ] **Assign template to profile** (❗ HIGH)
- [ ] **Remove template from profile** (🔥 CRITICAL)
- [ ] **Property owner lookup** (🔥 CRITICAL)
- [ ] **Send Email to recipient** (🔥 CRITICAL)
- [ ] **List templates for profile** (❗ HIGH)
- [ ] **Get single template by ID** (❗ HIGH)
- [ ] **Delete template** (❗ HIGH)

### DEFERRED
- ~~Merge field token substitution~~ — 'Merge field token substitution' is a deferred/legacy feature (voice/social/merge)
- ~~Manage customer dynamic merge fields~~ — 'Manage customer dynamic merge fields' is a deferred/legacy feature (voice/social/merge)

### REVIEW
- 🔍 **SMS group management** — 'SMS group management' exists in L0 but not in GreenAI — classify as MUST_BUILD 

## 📎 Evidence Index

| Capability | L0 Evidence | GreenAI Evidence |
|-----------|------------|-----------------|
| Address lookup | `ServiceAlert.Services/Enrollments/EnrollmentService.cs:393 – GetAddressStatistics` | `GreenAi.Sources/Dar/DarImporter.cs:1` |
| Send SMS to recipient | `ServiceAlert.Test/Services/Lookup/CodeLookup/CommandProcessors/LookupNorwegianCompany1881DataCommandProcessorTests.cs:304 – Process_WithSendSMSFalse_DoesNotCreateMobileEvents` | `—` |
| Assign template to profile | `ServiceAlert.Services/Profiles/ProfileService.cs:54 – AddProfileAccessToUsers` | `GreenAi.Api/Database/Migrations/V069_MessageTemplates.sql:1` |
| Remove template from profile | `ServiceAlert.Api/Controllers/StandardReceiverController.cs:721 – RemoveProfileFromGroup` | `—` |
| SMS group management | `ServiceAlert.Services/Benchmarks/BenchmarkService.cs:265 – GetSmsGroupsForBenchmark` | `—` |
| Merge field token substitution | `ServiceAlert.Services/Subscriptions/Models/CustomerSubscriptionNotification.cs:20 – HandleMergeFields` | `—` |
| Create new template | `ServiceAlert.Contracts/Extensions/ServiceCollection/ServiceCollectionExtensions.cs:460 – AddTemplateServices` | `GreenAi.Api/Program.cs:1` |
| Manage customer dynamic merge fields | `ServiceAlert.Core/Domain/MergeFields/MergeFields.cs:461 – GetDynamicMergeFieldNames` | `—` |
| Property owner lookup | `ServiceAlert.Services/Search/SearchService.cs:234 – GetOwnersOnAddressAsync` | `—` |
| Send Email to recipient | `ServiceAlert.Test/Services/Lookup/CodeLookup/CommandProcessors/LookupNorwegianCompany1881DataCommandProcessorTests.cs:366 – Process_WithSendEmailFalse_DoesNotCreateEmailEvents` | `—` |
| Update existing template | `ServiceAlert.Services/Mails/EmailTemplateService.cs:180 – UpdateTemplatesFromEmbeddedResources` | `GreenAi.Api/Features/Templates/UpdateTemplate/UpdateTemplate.sql:1` |
| List templates for profile | `ServiceAlert.Services/Templates/TemplateService.cs:32 – GetTemplatesForSmsAndEmail` | `GreenAi.Api/Features/Templates/GetTemplates/GetTemplatesEndpoint.cs:1` |
| Get single template by ID | `ServiceAlert.Services/Templates/TemplateService.cs:45 – GetTemplateById` | `GreenAi.Api/Features/Templates/GetTemplateById.sql:1` |
| Delete template | `ServiceAlert.Services/Templates/TemplateService.cs:100 – DeleteTemplateResponseOptionsAsync` | `GreenAi.Api/Features/Templates/UpdateTemplate/DeleteTemplateProfileAccess.sql:1` |
| Track delivery status | `—` | `GreenAi.Api/Database/Migrations/V047_Sms_DispatchAttempts.sql:1` |
| Outbox message processing | `—` | `GreenAi.Api/Database/Migrations/V054_RetryDeadLetter.sql:1` |
| Send direct message | `—` | `GreenAi.Api/Features/Templates/MessageTemplateDto.cs:1` |

---
_DFEP v1 | Domain: Templates | L0 source: sms-service | GreenAI source: green-ai/src_
_Re-run: `python run_dfep.py --domain Templates`_