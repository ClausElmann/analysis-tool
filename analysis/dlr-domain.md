# DLR Domain (SSOT)

> **EXTRACTION DATE:** 2026-04-12  
> **SOURCE BASIS:** DLR_ANALYSIS_V2 + DLR_GAP_VALIDATION (Wave 10-B)  
> Full archive: `temp_history/wave9-10b_2026-04-12.md`  
> **NO interpretation. NO design. ONLY verified facts.**

---

## 1. State Machine (code-verified)

### GatewayAPI Bulk Path

```
103  → (stored proc GetSmsLogMergeModelForSmsByStatusAndGatewayClass, ROWLOCK) → 202
202  → (GatewayApiBulkApiWorkloadProcessor, sent=true)  → 1211
202  → (GatewayApiBulkApiWorkloadProcessor, sent=false) → 1214
1211 → (GatewayApiCallback DLR, batch job)              → {1,2,3,6,7,9,136,146,149,156}
1214 → (retry send success)                              → 1211
1214 → (retry send failure)                              → 10220 (via GetNextRetryStatus chain)
```

Retry chain (send failures via SharedSmsGatewayTool.GetNextRetryStatus):
```
103  → failure → 1214
1212 → failure → 1213
1213 → failure → 1214
1214 → failure → 10220  (exhausted)
```

Source: `GatewayApiBulkApiWorkloadProcessor.cs`, `SharedSmsGatewayTool.cs`, `GatewayApiBulk.cs`

### Strex Path

```
103  → (stored proc, ROWLOCK, atomically)              → 202
202  → (SmsGatewayBrokerWorkloadProcessor routes to Strex if EnableStrexXX + CountryId match)
202  → (StrexGatewayWorkloadProcessor, sent=true)       → 1311
202  → (StrexGatewayWorkloadProcessor, sent=false, via GetNextRetryStatus) → retry chain → 10220
1311 → (StrexController DLR callback, HMAC validated, batch job) → {1,6,9,136,146,149,156,10220,204,206}
206  → (further Strex DLR callbacks — non-terminal)     → remains updatable by batch job
```

Initial routing condition (SmsGatewayBrokerWorkloadProcessor):
- `_highPriority=true` → always GatewayAPI, never Strex
- `EnableStrexDK/NO/SE/FI AND CountryId matches` → Strex
- Otherwise → GatewayAPI

Source: `SmsGatewayBrokerWorkloadProcessor.cs`, `GatewayApiBulk.cs`, `SmsGatewayBulkWorkloadLoader.cs`,  
`GetSmsLogMergeModelForSmsByStatusAndGatewayClass.sql`

### Legacy States (orphan recovery path)

```
202, 231, 232, 233 → OrphanedSmsLogWorkloadLoader re-queues for re-send
  (_stuckStatuses includes: 202, 231, 232, 233, 10301, 10303, 10305)
  NOTE: 1211, 1212, 1213, 1214, 1311, 1205 are NOT in _stuckStatuses
```

Source: `OrphanedSmsLogWorkloadLoader.cs`

---

## 2. Status Mapping (GatewayAPI + Strex)

### GatewayAPI: `GatewayFunctions.GatewayApiStatusCode(string statusText) → SmsStatusCode`

Source: `GatewayFunctions.cs` lines 32–47

| Gateway string  | SmsStatusCode | IsFinal |
|-----------------|---------------|---------|
| "DELIVERED"     | 1             | YES     |
| "SCHEDULED"     | 1             | YES     |
| "BUFFERED"      | 2             | NO      |
| "ENROUTE"       | 2             | NO      |
| "ACCEPTED"      | 3             | NO      |
| "EXPIRED"       | 6             | YES     |
| "SKIPPED"       | 7             | YES     |
| "DELETED"       | 9             | YES     |
| "UNKNOWN"       | 136           | NO      |
| "REJECTED"      | 146           | YES     |
| "UNDELIVERABLE" | 156           | YES     |
| (default)       | 149           | NO      |

### Strex: `GatewayFunctions.StrexStatusCode(StrexDeliveryReportDetailedStatus) → SmsStatusCode`

Source: `GatewayFunctions.cs` lines 49–93. Uses `DetailedStatusCode` ONLY. `StatusCode` field is ignored.

| DetailedStatusCode | SmsStatusCode | IsFinal |
|--------------------|---------------|---------|
| None               | 206           | NO      |
| Sent               | 206           | NO      |
| Delivered          | 1             | YES     |
| Expired            | 6             | YES     |
| Undelivered        | 156           | YES     |
| MissingDeliveryReport | 136        | NO      |
| Failed             | 136           | NO      |
| UnknownError / OtherError | 6      | YES     |
| Rejected / Stopped | 10220         | NO (IsFinal=0 in DB) |
| DuplicateTransaction | 204         | NO (IsInitial=1 — filtered, never writes to SmsLogs) |
| UnknownSubscriber / SubscriberUnavailable | 156 | YES |
| SubscriberBarred / InsufficientFunds / CardPSPError / ConnectionOffline / InvalidCredentials / InvalidOTP / MnoError / RegistrationRequired / UnknownAge / SubscriberLimitExceeded | 146 | YES |
| MaxPinRetry / MissingPreAuth / InvalidAmount / OneTimePasswordExpired / OneTimePasswordFailed / Pending / SubscriberTooYoung / TimeoutError | 149 | NO |
| (default) | 149 | NO |

---

## 3. Correlation Model (int vs long)

| Path       | Field used              | C# parse type | SmsLogs.Id DB type | Risk |
|------------|-------------------------|---------------|--------------------|------|
| GatewayAPI | `userref` then `Reference` | `int.TryParse` | `INT` (32-bit)    | None — types match |
| Strex      | `TransactionId`         | `long.Parse`  | `INT` (32-bit)     | **If TransactionId > 2,147,483,647: SmsLogStatuses row inserted with SmsLogId that has no matching SmsLogs.Id. Batch job silently skips (INNER JOIN miss). SmsLog stays at 1311 forever.** |

`SmsLogs.Id` source: `ServiceAlert.DB/Tables/SmsLogs.sql` line 2: `[Id] INT IDENTITY (1,1) NOT NULL`  
`BaseEntity.Id`: `public int Id { get; set; }` (`ServiceAlert.Core/Infrastructure/BaseEntity.cs`)  
`SmsLogStatuses.SmsLogId`: `BIGINT NOT NULL` (`SmsLogStatuses.sql`)

GatewayAPI parse code: `int.TryParse(callback.userref, out int smsLogId) || int.TryParse(callback.Reference, out smsLogId)` (`MessageService.cs:GatewayApiCallbackAsync`)  
Strex parse code: `long.Parse(status.TransactionId)` (`MessageService.cs:StrexCallbackAsync`)

---

## 4. Two-Table Write Model (SmsLogs vs SmsLogStatuses)

### SEND path (synchronous, immediate)

```
SmsGatewayStatusWriter.SetStatuses():
  Step 1: UpdateStatusesOnSmsLogs
            UPDATE SmsLogs SET StatusCode=@newStatus WHERE StatusCode=@oldStatus AND Id IN @ids
            (CAS-guarded, direct, immediate)
  Step 2: CreateSmsLogStatuses(Imported=TRUE)
            BulkInsert SmsLogStatuses — marks row as already-propagated
            (Batch job skips Imported=1 rows)
```

Source: `SmsGatewayStatusWriter.cs`, `MessageRepository.cs`

### DLR path (deferred via batch job)

```
MessageService.GatewayApiCallbackAsync / StrexCallbackAsync:
  Step 1: CreateSmsLogStatusAsync
            BulkInsert SmsLogStatuses { SmsLogId, StatusCode, Imported=FALSE }
            SmsLogs.StatusCode NOT UPDATED yet — LAG EXISTS

  Step 2 (deferred): ServiceAlertBatchAction.update_smslogs_status (external scheduler)
            MessageService.UpdateStatusOnSmsLogsAsync()
            GetNextSmsLogStatusesChunk(300): SELECT WHERE Imported=0 JOIN SmsStatuses JOIN SmsLogs
            Group by SmsLogId, pick winner (see §5)
            UpdateSmsLogsStatus(winnerIds):
              UPDATE SmsLogs SET StatusCode=st.StatusCode
              WHERE st.Id IN @ids
              AND SmsLogs.StatusCode NOT IN (SELECT Id FROM SmsStatuses WHERE IsFinal=1)
            MarkSmsLogStatusesImported(allStatusIds): UPDATE SmsLogStatuses SET Imported=1
```

Source: `MessageService.cs` lines 2047–2107, `MessageRepository.cs`

**LAG:** SmsLogs.StatusCode does NOT reflect DLR result until the batch job runs. Frequency of batch job is NOT determinable from source (scheduled externally).

---

## 5. Batch Resolution Contract

Exact LINQ from `MessageService.cs` line 2055:

```csharp
var latestStatuses = logsList
    .GroupBy(g => g.SmsLogId)
    .Select(grp => grp
        .OrderBy(s => s.IsFinal ? 3 : s.IsBillable ? 2 : 1)
        .ThenBy(s => s.DateReceivedUtc)
        .Last()
    ).ToList();

var latestStatusIds = latestStatuses.Where(l => !l.IsInitial).Select(s => s.Id).ToList();
_messageRepository.UpdateSmsLogsStatus(latestStatusIds);
```

Priority tiers (from SmsStatuses seed data, `dbo.SmsStatuses.Table.sql`):

| Status | IsFinal | IsBillable | IsInitial | Tier |
|--------|---------|------------|-----------|------|
| 1      | 1       | 1          | 0         | 3    |
| 6      | 1       | 1          | 0         | 3    |
| 7      | 1       | 1          | 0         | 3    |
| 9      | 1       | 1          | 0         | 3    |
| 146    | 1       | 1          | 0         | 3    |
| 156    | 1       | 1          | 0         | 3    |
| 2      | 0       | 1          | 0         | 2    |
| 3      | 0       | 1          | 0         | 2    |
| 136    | 0       | 1          | 0         | 2    |
| 149    | 0       | 1          | 0         | 2    |
| 204    | 0       | 0          | 1         | FILTERED (never writes to SmsLogs) |
| 206    | 0       | 0          | 0         | 1    |
| 10220  | 0       | 0          | 0         | 1    |

Resolution rules:
1. Highest tier wins across all Imported=0 rows for same SmsLogId
2. Within same tier: latest `DateReceivedUtc` wins
3. IsInitial=1: excluded from `UpdateSmsLogsStatus` call entirely
4. SmsLogs guard: if `SmsLogs.StatusCode` is already IsFinal=1, no UPDATE applied

---

## 6. Terminal vs Non-Terminal (IsFinal)

Source: `SmsStatuses` seed data + `UpdateSmsLogsStatus` SQL guard

### Terminal (IsFinal=1) — batch job CANNOT overwrite past these:

| Code | Name |
|------|------|
| 1    | SmsReceived (DELIVERED) |
| 6    | GatewaySendError (EXPIRED) |
| 7    | GatewayUnableToDeliver (SKIPPED) |
| 9    | MessageDeleted (DELETED) |
| 146  | Rejected |
| 156  | Undeliverable |

### Non-terminal DLR-relevant (IsFinal=0) — batch job CAN overwrite:

| Code | Name | Note |
|------|------|------|
| 2    | SmsSendNotReceived | GatewayAPI BUFFERED/ENROUTE |
| 3    | SmsSentAccepted | GatewayAPI ACCEPTED — further DLR can overwrite |
| 136  | Unknown | |
| 149  | SendUnknownGatewayError | default mapping |
| 206  | SmsSentAwaitingStatus | Strex None/Sent — more DLRs expected |
| 10220 | SmsFailedAtGateway | **NOT terminal** — IsFinal=0, guard does not protect |

### Not in SmsStatuses table:

| Code | Note |
|------|------|
| 1311 | `SmsWaitingForStrexCallback` — absent from SmsStatuses seed data. Guard subquery "NOT IN (IsFinal=1)" evaluates to TRUE for 1311 (not in subquery). Rows at 1311 CAN be updated by batch job. |

---

## 7. Failure Modes (stuck states)

| Mode | Trigger | Outcome | Auto-recovery |
|------|---------|---------|---------------|
| GatewayAPI correlation failure | `userref` and `Reference` both non-parseable as int | Fatal log, HTTP 200, SmsLog stays at 1211 forever | NONE |
| Strex correlation failure | `TransactionId` null/empty/non-parseable as long | Fatal log, HTTP 200, SmsLog stays at 1311 forever | NONE |
| Strex DLR never arrives | Network/gateway failure | SmsLog stays at 1311; monitoring fatal log after 28–40 hrs | NONE |
| GatewayAPI DLR never arrives | Network/gateway failure | SmsLog stays at 1211; monitoring fatal log after 12 hrs | NONE |
| Strex unknown DetailedStatusCode | `Enum.TryParse` fails | Fatal log, HTTP 200, SmsLog stays at 1311 | NONE |
| SQL exception in CreateSmsLogStatusAsync (GatewayAPI) | DB error | HTTP 500, gateway may retry depending on gateway policy | Depends on external gateway |
| Strex int overflow | TransactionId > 2,147,483,647 | SmsLogStatuses row inserted, INNER JOIN miss, batch silently skips, SmsLog stays at 1311 | NONE |
| Worker dies mid-processing at 1212/1213/1214 | Process crash | States NOT in _stuckStatuses, not auto-recovered | NONE |

Source: `SmslogService.cs:TrackSmsLogsQueueCounts()`, `OrphanedSmsLogWorkloadLoader.cs`

---

## 8. Critical Risks

| Risk | Classification | Source |
|------|---------------|--------|
| **1311 not in SmsStatuses** | CONFIRMED — IsFinal guard subquery misses 1311 entirely. Rows at 1311 are always updateable. Correct behavior, but creates an invisible dependency on gateway DLR delivery. | `dbo.SmsStatuses.Table.sql`, `UpdateSmsLogsStatus` SQL |
| **10220 is NOT terminal** | CONFIRMED — IsFinal=0. Strex Rejected/Stopped DLR writes 10220 via batch. A subsequent Delivered DLR would overwrite 10220 → 1 with zero structural barriers. | `dbo.SmsStatuses.Table.sql`, `MessageService.cs:UpdateStatusOnSmsLogsAsync` |
| **No FK constraint** | CONFIRMED — No FK from SmsLogStatuses.SmsLogId → SmsLogs.Id in DDL, create script, or Model.xml. Orphaned rows accumulate up to 14 days. Batch job silently skips orphans (INNER JOIN miss). | `SmsLogStatuses.sql`, `ServiceAlert.DB_Create.sql`, `Model.xml` |
| **No automatic recovery** | CONFIRMED — 1311, 1211, 1205, 1212, 1213, 1214 are not in OrphanedSmsLogWorkloadLoader._stuckStatuses. Messages stuck in these states require manual intervention. | `OrphanedSmsLogWorkloadLoader.cs`, `SmslogService.cs` |
| **int vs long correlation mismatch (Strex)** | CONFIRMED — SmsLogs.Id is INT (32-bit); Strex parses TransactionId as long. Silent data loss if value exceeds 2^31. | `SmsLogs.sql`, `MessageService.cs:StrexCallbackAsync` |
| **Batch job non-deterministic lag** | CONFIRMED — DLR-to-status propagation delay is unknown. Scheduler frequency not in source. | `ServiceAlert.Batch/Program.cs`, `ServiceAlertBatchAction` |
| **GatewayAPI DLR endpoint is AllowAnonymous** | CONFIRMED — No auth, no HMAC. Any caller can POST to /Message/GatewayApiCallback. | `MessageController.cs:GatewayApiCallback` |
