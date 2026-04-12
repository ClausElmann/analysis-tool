# DLR Design Boundary

> **EXTRACTION DATE:** 2026-04-12  
> **PURPOSE:** Defines Wave 10 design scope before any DLR architecture work begins.  
> **This document defines WHAT MAY be designed, WHAT MUST NOT change, and WHAT REMAINS UNKNOWN.**  
> Source basis: `dlr-domain.md` + `dlr-invariants.md`.

---

## What We Are Allowed to Design in Wave 10

### 1. DLR Ingestion Abstraction

Current state: `GatewayApiCallbackAsync` and `StrexCallbackAsync` are two unrelated methods in `MessageService`. Both call `CreateSmsLogStatusAsync` directly.

Design scope:
- An abstraction layer that accepts a DLR signal regardless of gateway source
- Normalization of the correlation step (int vs long type mismatch may be addressed here)
- Validation boundary for incoming DLR payloads before they touch the database

### 2. Status Propagation Replacement

Current state: DLR writes to `SmsLogStatuses` (Imported=0) and waits for an external batch job. SmsLogs.StatusCode has undefined lag.

Design scope:
- A replacement or supplement to the deferred two-table write model
- A mechanism that reduces or eliminates the non-deterministic lag
- A strategy that respects the IsFinal guard and IsInitial filter invariants
- Note: Any replacement must still produce the correct winner selection behavior (see §5 of dlr-domain.md)

### 3. Recovery Strategy

Current state: No automated recovery exists for stuck DLR-awaiting states (1311, 1211, 1205, 1212, 1213, 1214). Monitoring emits fatal logs only.

Design scope:
- A recovery mechanism for DLR-awaiting states that have exceeded their expected wait window
- Explicit definition of what "stuck" means per status (time threshold per gateway)
- A transition target for recovered stuck states (must be a valid SmsStatusCode with IsFinal=1 or explicit monitoring)

---

## What We Must NOT Change

### 1. Existing SmsStatusCode values

The numeric values of `SmsStatusCode` (1, 2, 3, 6, 7, 9, 136, 146, 149, 156, 204, 206, 1211, 1311, 10220, etc.) must not be renumbered, removed, or redefined. They are embedded in:
- Database seed data (`dbo.SmsStatuses`)
- Batch job SQL (`UpdateSmsLogsStatus` guard subquery)
- API response models (`MessageStatusResponseDto.SuccessStatusCodes`, `PendingStatusCodes`)
- Stored procedures and indices on `SmsLogs.StatusCode`

### 2. External gateway contracts

The following are defined by external parties and must not be changed:
- GatewayAPI DLR payload shape: `GatewayApiCallBackItem` fields (`userref`, `Reference`, `status`, `code`, `Error`)
- Strex DLR payload shape: `StrexDeliveryReportDto` fields (`TransactionId`, `DetailedStatusCode`, `StatusCode`, `Delivered`, etc.)
- Strex HMAC signature scheme: `?signature=<HMAC>` in query string, validated by `_hashSignatureService`
- GatewayAPI `AllowAnonymous` endpoint (gateway cannot be reconfigured from this codebase)

### 3. Existing mapping logic (GatewayFunctions)

`GatewayFunctions.GatewayApiStatusCode` and `GatewayFunctions.StrexStatusCode` implement the authoritative translation from gateway strings to `SmsStatusCode`. These mappings correspond to live production gateway behavior:
- The 11-entry GatewayAPI status map must not be altered
- The 33-value Strex DetailedStatusCode map must not be altered
- The decision to use `DetailedStatusCode` (not `StatusCode`) for Strex must not be changed

---

## Unknowns (Must Remain Untouched Until Clarified)

### U-1: Batch scheduler frequency

`ServiceAlertBatchAction.update_smslogs_status` is triggered by an external scheduler. Its execution interval (seconds? minutes?) is not in this repository. Any design that depends on "the batch runs every X seconds" is making an assumption.

**Constraint:** Wave 10 design MUST NOT assume a specific batch frequency.

### U-2: External gateway retry behavior

Whether Strex sends multiple DLR callbacks for the same `TransactionId` (e.g., `Rejected` followed by `Delivered`) is Strex platform behavior. Whether GatewayAPI retries DLR delivery on HTTP 500 responses is GatewayAPI platform behavior.

**Constraint:** Wave 10 design MUST NOT assume that a single DLR per send is guaranteed. Designs must handle multiple DLR callbacks for the same SmsLog.

### U-3: GatewayAPI callback URL configuration

Where the GatewayAPI is configured to deliver DLR callbacks (account settings, per-request, environment variable) is not visible in source. The endpoint is `/Message/GatewayApiCallback` but the registration point is external.

**Constraint:** No change to callback URL registration can be designed from this codebase alone.

### U-4: Whether 10220 is intentionally non-terminal

`SmsFailedAtGateway10220` has `IsFinal=0`. Whether this is intentional (to allow recovery) or an error (should be IsFinal=1 to protect from accidental overwrite) is not determinable from source. Changing this would affect the IsFinal guard behavior for all future DLR processing.

**Constraint:** Wave 10 design MUST NOT change the IsFinal value of 10220 without explicit Architect decision.
