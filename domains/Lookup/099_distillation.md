# Lookup — Distillation

**Authority Layer:** Layer 1 (Derived Conceptual SSOT)
**Source-primary:** LookupService.cs + CodedLookupService.cs + entity/command inventory
**Status:** Distilled

---

## 1. Domain Purpose

The Lookup domain is the **core recipient resolution engine** of ServiceAlert. When a broadcast (`SmsGroup`) is created, the Lookup pipeline expands address-based inputs into individual recipients and resolves their contact data (phone number, email, eBoks identity, physical address) via external and internal data sources.

Lookup runs **before delivery** — it transforms a broadcast's target definition (addresses, level filters, standard receivers, supply numbers) into a set of `SmsLog` records (one per resolved contact). Delivery consumes these records.

**Two execution modes:**
1. **Prelookup (preview):** Dry-run that returns estimated recipient counts by type, without writing to the database.
2. **Lookup (full):** Actual resolution — writes resolved `SmsLog` records to the database and streams progress via SSE.

---

## 2. Architecture Overview

```
LookupService
  ├── GetSmsLogsFromKvhxsAsync(...)  ← One-off lookup for specific KVHx addresses
  ├── RunPrelookupAsync(smsGroupId)  ← Prelookup: preview counts (via CodedLookupService)
  └── RunLookupAsync(smsGroupId)     ← Full lookup (via CodedLookupService)

CodedLookupService
  ├── PrelookupAsync(userId, smsGroupId)
  │     → LookupExecutor + TemporaryStoragePostProcessor
  │     → Returns LookupProgressCountDto[] per type
  └── LookupAsync(smsGroupId)
        → LookupExecutor + SequentialPostProcessor(ProgressWatcher, WriteToDatabasePostProcessor)
        → Writes SmsLog records to DB

LookupExecutor
  ├── Receives: IEnumerable<ILookupCommandProcessor> (DI-injected)
  ├── Input: [LookupSmsGroupCommand(smsGroupId)] entry-point command
  ├── Execution: Commands run in PriorityOrder; each processor handles its matching command
  └── Output: Passes resolved SmsLog list to PostProcessor
```

---

## 3. Command Pipeline — Categories

Commands are `ILookupCommand` implementations, each with a `PriorityOrder` int. The `LookupExecutor` dispatches to matching `ILookupCommandProcessor<TCommand>` implementations (DI-registered). Commands run sequentially in priority order.

### A. Entry Point
| Command | Notes |
|---|---|
| `LookupSmsGroupCommand(smsGroupId)` | Top-level trigger; wraps smsGroupId; PriorityOrder=1000 |
| `RunBatchedCommandsCommand` | Run batched sub-commands in a single pass |

### B. Expansion — Target → Individual Addresses
| Command | Notes |
|---|---|
| `ExpandAddressFilterCommand` | Address-based filters → individual address records |
| `ExpandLevelFiltersCommand` | Level-based address filters → addresses |
| `LoadLevelFiltersCommand` | Load level filter configuration before expansion |
| `ExpandRecipientMunicipalityAddressesCommand` | Municipality-scoped address expansion |
| `ExpandStandardReceiverGroupCommand` | Expand StandardReceiverGroup → individual receivers |
| `SplitStandardReceiverCommand` | Split a standard receiver into components |
| `RegisterPreloadedAddressCommand` | Register an already-resolved address into pipeline |

### C. Norwegian-Specific Lookups
All commands named `LookupNorwegian*` are Norway-country-specific.

| Command | Data Source | Notes |
|---|---|---|
| `LookupNorwegianAddressOwnersCommand` | Property registry | Gets property owners at address |
| `LookupNorwegianAddressResidentsCommand` | Population registry | Gets residents at address |
| `LookupNorwegianPropertyOwnersCommand` | Property registry | Gets owners for property |
| `LookupNorwegianPropertyResidentsCommand` | Population registry | Gets residents for property |
| `LookupNorwegianPropertyPublicContactsCommand` | KRR | Public contacts for property |
| `LookupNorwegianPublicContactsCommand` | KRR | Public contact lookup (KRR = Kontakt- og Reservasjonsregisteret) |
| `LookupNorwegianOwnersCommand` | Property registry | General owner lookup |
| `LookupNorwegianCompaniesCommand` | Brønnøysund/CVR | Norwegian company lookup |
| `LookupNorwegianCompany1881DataCommand` | 1881 | Company contact data via 1881 service |
| `LookupNorwegianCompanyContactDataCommand` | 1881 | Company contact details |
| `LookupNorwegianPerson1881DataCommand` | 1881 | Person phone data via 1881 |
| `LookupNorwegianPersonContactDataCommand` | 1881 | Person contact details |
| `LookupNorwegianTeledataCommand` | Teledata | Norwegian teledata / directory |

### D. eBoks Lookups
| Command | Notes |
|---|---|
| `LookupEboksAmplifyCommand` | eBoks Amplify — citizen lookup by name/address |
| `LookupEboksAmplifyOwnerCommand` | Owner eBoks Amplify lookup |
| `LookupEboksCvrCommand` | eBoks CVR — company registration lookup |
| `LookupEboksCvrOwnerCommand` | Owner CVR lookup |

### E. Teledata (General / Denmark/Finland/Sweden)
| Command | Notes |
|---|---|
| `LookupTeledataCommand` | General teledata directory lookup |
| `CompleteTeledataCommand` | Finalise/merge teledata results |
| `LookupOwnerTeledataCommand` | Teledata for property owner |
| `FindOwnerAddressCommand` | Resolve owner's physical address |

### F. Subscriptions & Enrollments
| Command | Notes |
|---|---|
| `LookupEnrollmentsCommand` | Citizen enrollment data |
| `LookupOwnerEnrollmentsCommand` | Owner enrollment data |
| `LookupSubscriptionsCommand` | General subscription data |
| `LookupOwnerSubscriptionsCommand` | Owner subscription data |
| `LookupSupplyNumbersSubscriptionsCommand` | Subscriptions via supply numbers |
| `CompleteSubscribersCommand` | Finalise subscriber records |

### G. Deduplication & Filter Checks
| Command | Notes |
|---|---|
| `CheckRobinsonCommand` | Robinson no-contact list filter — removes opted-out contacts |
| `CheckPhoneFiltersCommand` | Customer-defined number filters |
| `CheckEmailForDoublesCommand` | Email deduplication |
| `CheckNameMatchCommand` | Name-match validation (confirm identity) |
| `CheckEboksAmplifyForDoublesCommand` | eBoks Amplify dedup |
| `CheckEboksAmplifyOwnerForDoublesCommand` | eBoks Amplify owner dedup |
| `CheckEboksCvrForDoublesCommand` | eBoks CVR dedup |
| `CheckEboksCvrNameMatchCommand` | eBoks CVR name-match check |

### H. Attach — Write Resolved Contact to SmsLog
| Command | Notes |
|---|---|
| `AttachPhoneCommand` | Attach resolved phone number to recipient |
| `AttachEmailCommand` | Attach resolved email to recipient |
| `AttachAddressCommand` | Attach resolved physical address |
| `AttachEboksAddressCommand` | Attach eBoks Amplify address |
| `AttachEboksCvrCommand` | Attach eBoks CVR identifier |

### I. Misc / Infrastructure
| Command | Notes |
|---|---|
| `DeterminePhoneNumberTypeCommand` | Classify phone as mobile vs landline |
| `CreateSmsLogCommand` | Create a new SmsLog record in pipeline state |
| `CreateSmsLogResponseCommand` | Create SmsLog response record |

---

## 4. Post-Processors

| Post-Processor | Used In | Behaviour |
|---|---|---|
| `TemporaryStoragePostProcessor` | Prelookup | Collects results in memory; no DB write |
| `WriteToDatabasePostProcessor` | Full lookup | Writes resolved SmsLog records to DB |
| `SequentialPostProcessor` | Full lookup | Chains: `ProgressWatcher` → `WriteToDatabasePostProcessor` |
| `WriteToConsolePostProcessor` | Debug | Writes to console (dev only) |

---

## 5. LookupSmsLogsQuery — Configuration Object

| Field | Type | Notes |
|---|---|---|
| `CustomerId` | int | |
| `ProfileId` | int | |
| `CountryId` | int | |
| `SendSMS` | bool | |
| `SendEmail` | bool | |
| `SendVoice` | bool | |
| `SendToAddress` | bool | Send to addresses |
| `SendToOwnerAddress` | bool | Send to owner's address |
| `LookupBusiness` | bool | Include business/company lookups |
| `LookupPrivate` | bool | Include private person lookups |
| `LookupNorwegianKRR` | bool | Derived from `ProfileRoleNames.NorwayKRRLookup` permission |
| `DontLookupTeledata` | bool | Derived from `ProfileRoleNames.DontLookUpNumbers` permission |
| `AllAddrTable` | `IEnumerable<LookupKvhx>` | Input KVHx address identifiers |
| `SmsGroupId` | long? | Broadcast SmsGroup id |
| `SendEboksStrategy` | enum | eBoks delivery strategy |
| `EboksMessage` | string | eBoks message text |
| `UseEboksAmplify` | bool | Default true |
| `DisableDuplicateControl` | bool | Skip dedup checks |

---

## 6. Progress Tracking

### Prelookup Progress
- `ILookupProgressIndicator.SetProgressAsync(userId, smsGroupId, message, counts?)`
- Stages: `"Started"` → `"Finished"` (or `"Failed|{message}"`)
- `LookupProgressDto = {SmsGroupId, Message, Counts: LookupProgressCountDto[]}`
  - `LookupProgressCountDto = {LookupType, Count}` — one per resolved recipient type

### Full Lookup Progress
- `ProgressWatcher($"Lookup {smsGroupId}", $"status/{smsGroupId}", clientEventRepository)` — SSE stream for live dashboard
- Activity log entries on start; `UpdateSmsGroupForLookup(smsGroupId)` marks broadcast as "in lookup"

---

## 7. SmsLog Background Processing

- `SmsLogBackgroundProcessingManager` / `SmsLogBackgroundService` — writes `SmsLog` records to DB asynchronously via a background channel (pattern identical to WebhookMessagesBackgroundService)
- Decouples high-concurrency lookup write load from the main lookup thread

---

## 8. Missed Lookup Recovery

`CheckForMissedLookupsAsync()` is called by `RunLookupAsync()` when no `smsGroupId` is supplied:
1. Queries `ILookupRepository.GetMissingLookups()` — finds SmsGroups that should have been looked up but weren't
2. For each: applies `LookupRetryPolicy.GetRetryAction(smsGroupId)` — `Retry` or skip
3. Re-queues via `IBatchAppService.CreateLookupAzureTaskAsync()` — Azure Batch task
4. Logs retry to ActivityLog

---

## 9. Key Rules

1. **Prelookup before send:** Users see estimated recipient counts (by type) from prelookup before confirming the broadcast.
2. **Priority-ordered commands:** `LookupExecutor` dispatches commands in ascending `PriorityOrder`; lower = earlier.
3. **Permission-gated steps:** `LookupNorwegianKRR=true` requires `ProfileRoleNames.NorwayKRRLookup`; `DontLookupTeledata=true` derives from `ProfileRoleNames.DontLookUpNumbers`.
4. **Robinson always applied:** `CheckRobinsonCommand` removes opted-out contacts before any attach step.
5. **eBoks requires strategy:** `SendEboksStrategy` must be set; `UseEboksAmplify` defaults to true for citizen (Amplify) lookup.
6. **Dedup default on:** `DisableDuplicateControl` is false by default — duplicate phone/email is filtered per broadcast.
7. **Missed lookup recovery:** A scheduled job calls `RunLookupAsync(null)` to pick up any broadcasts that silently failed during lookup.
8. **Country drives command set:** Norway activates 1881 + KRR commands; DK/SE/FI use Teledata + eBoks CVR paths.

---

## 10. Integration Points

| Integrated System | Direction | Command |
|---|---|---|
| Norwegian property registry | Inbound | `LookupNorwegianPropertyOwnersCommand`, `LookupNorwegianAddressOwnersCommand` |
| Norwegian KRR (Kontakt-/Reservasjonsregisteret) | Inbound | `LookupNorwegianPublicContactsCommand`, `LookupNorwegianPropertyPublicContactsCommand` |
| 1881 (Norway phone directory) | Inbound | `LookupNorwegian*1881*Command` |
| Teledata (DK/SE/FI directory) | Inbound | `LookupTeledataCommand`, `CompleteTeledataCommand` |
| eBoks Amplify | Inbound | `LookupEboksAmplifyCommand`, `CheckEboksAmplifyForDoublesCommand` |
| eBoks CVR | Inbound | `LookupEboksCvrCommand`, `CheckEboksCvrForDoublesCommand` |
| Azure Batch | Outbound | `IBatchAppService.CreateLookupAzureTaskAsync()` for retry |
| Delivery domain | Downstream | Writes `SmsLog` records consumed by Delivery pipeline |
| Monitoring domain | Side-channel | `ProgressWatcher` → SSE for monitoring dashboard |
| ActivityLog domain | Side-channel | Logs lookup start + retry events |
