# DLR Invariants (SSOT)

> **EXTRACTION DATE:** 2026-04-12  
> **SOURCE BASIS:** DLR_ANALYSIS_V2 + DLR_GAP_VALIDATION (Wave 10-B)  
> **These are hard rules observed from source. NO interpretation. NO design.**  
> Violation of any invariant means the system deviates from current production behavior.

---

## Hard Invariants

### I-1: DLR never writes to SmsLogs directly

DLR callbacks (`GatewayApiCallbackAsync`, `StrexCallbackAsync`) call `CreateSmsLogStatusAsync` which inserts a row into `SmsLogStatuses` with `Imported=0`. They do NOT call `UpdateStatusesOnSmsLogs` or any direct `UPDATE SmsLogs` statement.

Source: `MessageService.cs:GatewayApiCallbackAsync`, `MessageService.cs:StrexCallbackAsync`

---

### I-2: Batch job is REQUIRED for DLR propagation to SmsLogs

`SmsLogs.StatusCode` does not reflect a DLR result until `ServiceAlertBatchAction.update_smslogs_status` runs and calls `MessageService.UpdateStatusOnSmsLogsAsync()`. This job is triggered externally. It is not self-scheduling. No in-process trigger exists.

Source: `ServiceAlert.Batch/Program.cs:731`, `MessageService.cs:UpdateStatusOnSmsLogsAsync`

---

### I-3: IsFinal=1 blocks SmsLogs overwrite

Once `SmsLogs.StatusCode` is set to a status with `IsFinal=1 in SmsStatuses`, the `UpdateSmsLogsStatus` SQL guard prevents any further update.

```sql
AND SmsLogs.StatusCode NOT IN (SELECT Id FROM SmsStatuses WHERE IsFinal = 1)
```

The guard fires on `SmsLogs.StatusCode`, not on the incoming status. If a prior batch already wrote an IsFinal status, all future batches are blocked for that row.

Source: `MessageRepository.cs:UpdateSmsLogsStatus`

---

### I-4: 1311 is not in SmsStatuses

`SmsWaitingForStrexCallback1311` has no row in `dbo.SmsStatuses`. The IsFinal=1 subquery in the guard returns no row for 1311. Rows with `SmsLogs.StatusCode=1311` are therefore ALWAYS updateable by the batch job. This is required — 1311 must be overwritable when the DLR arrives.

Source: `dbo.SmsStatuses.Table.sql`, `UpdateSmsLogsStatus` SQL

---

### I-5: 10220 is NOT terminal

`SmsFailedAtGateway10220` has `IsFinal=0` in `SmsStatuses`. The batch job guard does NOT protect rows at 10220. A subsequent DLR callback can overwrite 10220 with any higher-tier status.

Source: `ServiceAlert.Test.Shared/Database/Generated/dbo.SmsStatuses.Table.sql`, `UpdateSmsLogsStatus` SQL

---

### I-6: No automatic recovery exists for DLR-awaiting stuck states

Statuses `1311, 1211, 1205, 1212, 1213, 1214` are not in `OrphanedSmsLogWorkloadLoader._stuckStatuses`. If the DLR never arrives, these SmsLogs remain in their awaiting state indefinitely. The monitoring job (`SmslogService.TrackSmsLogsQueueCounts`) emits fatal logs only — no state transition is triggered.

Source: `OrphanedSmsLogWorkloadLoader.cs`, `SmslogService.cs:TrackSmsLogsQueueCounts`

---

### I-7: FK does NOT exist from SmsLogStatuses to SmsLogs

No `FOREIGN KEY` constraint exists from `SmsLogStatuses.SmsLogId` to `SmsLogs.Id`. Orphaned `SmsLogStatuses` rows (with no matching `SmsLogs` row) are possible and accumulate until the 14-day time-based purge (`SmsLogStatusesDelete` stored procedure).

Source: `SmsLogStatuses.sql`, `ServiceAlert.DB_Create.sql`, `Model.xml`, `SmsLogStatusesDelete.sql`

---

### I-8: GatewayAPI correlation uses int; Strex uses long; SmsLogs.Id is INT

`GatewayApiCallbackAsync` parses `smsLogId` as `int`. `StrexCallbackAsync` parses `TransactionId` as `long`. `SmsLogs.Id` is `INT` (32-bit) in the database. The Strex path silently fails for values > 2,147,483,647 (INNER JOIN miss in batch job).

Source: `SmsLogs.sql`, `MessageService.cs:GatewayApiCallbackAsync`, `MessageService.cs:StrexCallbackAsync`

---

### I-9: IsInitial=1 rows never write to SmsLogs.StatusCode

Before calling `UpdateSmsLogsStatus`, the batch job filters out all entries where `IsInitial=1`:

```csharp
var latestStatusIds = latestStatuses.Where(l => !l.IsInitial).Select(s => s.Id).ToList();
```

Status 204 (DuplicateTransaction) has `IsInitial=1`. It is never promoted to `SmsLogs.StatusCode`.

Source: `MessageService.cs:2063`, `dbo.SmsStatuses.Table.sql`

---

### I-10: Strex DLR mapping uses DetailedStatusCode exclusively

`GatewayFunctions.StrexStatusCode` takes `StrexDeliveryReportDetailedStatus` (33-value enum). The top-level `StatusCode` field (Queued/Sent/Failed/Ok/Reversed) is never passed to any mapping function. It is not used in determining the resulting `SmsStatusCode`.

Source: `GatewayFunctions.cs:49–93`, `MessageService.cs:StrexCallbackAsync`

---

### I-11: Strex DLR endpoint has HMAC auth; GatewayAPI DLR endpoint has none

`StrexController.DeliveryReport`: validates `_hashSignatureService.ValidateSignature(transactionId, signature)` before processing.  
`MessageController.GatewayApiCallback`: marked `[AllowAnonymous]`. No signature or token check.

Source: `StrexController.cs`, `MessageController.cs:GatewayApiCallback`

---

### I-12: Multiple DLR callbacks for the same SmsLog are cumulative

Every DLR call inserts a new `SmsLogStatuses` row (no upsert, no replace). The batch job processes ALL `Imported=0` rows for a given `SmsLogId` together and selects a single winner. Multiple non-terminal callbacks (e.g., two `206` rows from Strex) are handled correctly by the ordering logic.

Source: `MessageService.cs:CreateSmsLogStatusAsync`, `MessageService.cs:UpdateStatusOnSmsLogsAsync`
