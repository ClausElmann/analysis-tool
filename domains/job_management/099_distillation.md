# Domain Distillation — job_management

**Status:** APPROVED_BASELINE  
**Completeness score (Layer 1):** 0.93  
**Evidence:** domains/job_management/010_entities.json, 020_behaviors.json, 030_flows.json + UI (monitoring-jobs, active-job components)

---

## 1. Core Concept

`job_management` is the scheduling, execution, and monitoring layer that coordinates all background work in ServiceAlert. It spans two execution models:

1. **Azure Batch jobs** — heavy, parallelizable jobs submitted to Azure Batch Pool via Quartz.NET cron triggers (address imports, lookup, broadcast delivery, FTP poslist import, archive)
2. **In-process background services (IHostedService)** — lightweight, latency-sensitive or continuous operations running inside the web server process (pin code SMS, voice sends, email via SendGrid, cleanup, statistics, watchdog)

Status of every executed job task is tracked in a three-table schema and pushed live to the admin UI via SSE.

---

## 2. Entities

### `Job`
Lookup table. One row per `ServiceAlertBatchAction` enum value.
- `Id` INT IDENTITY
- `Name` NVARCHAR(50) — matches enum string (`import_dk_addresses`, `gateway_api_bulk`, etc.)

### `JobTask`
Mutable execution record. Created or updated on each job invocation.
- `Id` BIGINT IDENTITY
- `JobId` FK → Jobs
- `AzureJobId` NVARCHAR — populated only for Azure Batch jobs
- `AzureTaskId` NVARCHAR — populated only for Azure Batch jobs
- `StatusCode` INT — latest `JobTaskStatusCode`
- `Parameters` NVARCHAR — JSON or string payload
- `DateCreatedUtc`, `DateUpdatedUtc` DATETIME

### `JobTaskStatus` (append-only log)
- `Id`, `JobTaskId` FK → JobTasks
- `StatusCode` INT — `Queued=0 / Running=100 / Finished=200`
- `Message` NVARCHAR
- `DateCreatedUtc` DATETIME

### `JobTaskStatusCode` Enum
`Queued=0`, `Running=100`, `Finished=200`

---

## 3. ServiceAlertBatchAction — Full Enum

Categorized by purpose:

| Category | Values |
|---|---|
| **subscription** | `subscription_notifications` |
| **address_import** | `import_dk_addresses`, `import_se_addresses`, `import_no_addresses`, `import_no_properties`, `import_dk_owner_addresses`, `import_dk_owner_bfe_lookup`, `import_dk_owner_publish_data`, `recheck_missing_bfes`, `poslist_ftp_import`, `import_robinsons` |
| **lookup_pipeline** | `prelookup`, `lookup` |
| **gateway_delivery** | `gateway_api_bulk`, `gateway_unwire_bulk`, `gateway_emails`, `gateway_voice`, `gateway_webmessages`, `send_emails_sendgrid` |
| **data** | `statstidende` |
| **cleanup** | `cleanup_azure`, `cleanup_azure_profile_storage_files`, `cleanup_messages`, `cleanup_systemlogs`, `cleanup_bisnode_sweden`, `cleanup_deletedsubscriptions`, `cleanup_kamstrup_ready`, `cleanup_duplicate_redundant_logs`, `cleanup_positivelists`, `cleanup_sendertips`, `cleanup_emailmessages`, `cleanup_statstidendedata`, `cleanup_eboksmessages`, `cleanup_requestlogs`, `cleanup_enrollees`, `cleanup_deactivated_users`, `cleanup_deactivated_customers`, `cleanup_deactivated_profiles`, `cleanup_prospects`, `cleanup_smslogsstatuses`, `cleanup_dataimport_files`, `cleanup_dataimportrows`, `cleanup_iframerequests`, `cleanup_clientevents`, `cleanup_maprequest` |
| **statistics** | `statistics_write_emailMessages`, `statistics_write_requestlogs`, `statistics_write_addressdata`, `statistics_write_phonedata` |
| **archive** | `archive_message`, `archive_messages` |
| **watchdog** | `watchdog_databasecheck`, `watchdog_fatalerrors`, `watchdog_version`, `monitoring_address_imports` |

---

## 4. Behaviors

### `LogJobTaskStatus`
- Signature: `LogJobTaskStatusAsync(jobName, statusCode, azureJobId?, azureTaskId?, parameters?)`
- Resolves `Job` by name → upserts `JobTask` → appends `JobTaskStatus` row
- Raises `JobTaskStatusChangedEvent` after each status change

### `GetRecentAndOngoingTasks`
- Returns `IReadOnlyCollection<JobTaskDto>` — recent + ongoing tasks with full status history
- Consumed by admin monitoring UI (initial HTTP load)

### `ActiveJobsClientEventPush`
- Triggered by `JobTaskStatusChangedEvent`
- Pushes SSE event of type `ACTIVEJOBS` to connected admin clients
- UI merges by `jobTaskId`; auto-removes Finished tasks older than 15 minutes

### `QuartzSchedulerRegistration`
- All recurring jobs registered at app startup with cron expressions
- Each `IJob` implementation either submits to Azure Batch SDK or triggers in-process services

### Background Services (IHostedService)

| Service | Purpose | Key Rules |
|---|---|---|
| `SmsBackgroundService` | Dequeues SmsLog items → SMS gateway (GatewayAPI) | Per-server queue; only time-sensitive single sends (not bulk broadcasts); bulk goes via Azure Batch |
| `VoiceBackgroundService` | Dequeues voice messages → Infobip | Same per-server isolation as SMS |
| `EmailBackgroundService` | Converts SmsLog → EmailMessage records | Feeds into SendGridBackgroundService |
| `SendGridBackgroundService` | Sends EmailMessage queue via SendGrid | Can queue emails without SmsLogId (supports system emails: password reset, welcome) |
| `ClientEventBackgroundService` | Polls `ClientEvents` table → SSE push | Uses `Lib.AspNetCore.ServerSentEvents`; tracks last-seen Id per server; pushes to subscription groups |

**Why background services (not Azure Batch) for pin codes:**  
Azure Batch startup latency was too slow for time-sensitive single sends. 100 simultaneous pin code requests would coalesce into 1 delayed batch task. Background services send directly from web server, eliminating that delay.

---

## 5. Flows

### Azure Batch Job Execution Flow
1. Quartz fires cron trigger
2. `IJob.Execute()` called in web server
3. `LogJobTaskStatusAsync(jobName, Queued)` → inserts `JobTask`
4. Azure Batch SDK submits job+task to `BatchPool`
5. Batch app (separate process) executes `ServiceAlertBatchAction`
6. Batch app calls back: `LogJobTaskStatusAsync(jobName, Running, azureJobId, azureTaskId)`
7. Batch app completes: `LogJobTaskStatusAsync(jobName, Finished)`
8. `JobTaskStatusChangedEvent` → SSE push to admin UI

**Used for:** address imports, owner imports, robinson import, prelookup/lookup, poslist FTP import, subscription notifications, archive

### In-Process Background Service Execution Flow
1. `IHostedService.ExecuteAsync()` runs on timer or continuously
2. Service performs work (email dispatch, SMS gateway, cleanup, statistics)
3. `LogJobTaskStatusAsync` called for named operations
4. No Azure Batch — runs entirely inside API process

**Used for:** send_emails_sendgrid, gateway_api_bulk (small volume), cleanup_*, statistics_write_*, watchdog_*

### Cleanup Job Pattern
1. Quartz fires daily or weekly
2. `SELECT` rows WHERE `DateDeletedUtc < NOW()-threshold` OR `DateCreatedUtc < NOW()-retention`
3. `DELETE` in batches
4. Log count to `JobTaskStatuses`

---

## 6. Admin UI — monitoring-jobs

**Component:** `monitoring-jobs.component` (super-administration → monitoring)  
**Route context:** Admin-only; super-administration section

**Table columns:**
- Status (translated: Queued / Running / Finished)
- DateCreated (UTC, formatted)
- Seconds (execution time, right-aligned)
- Name (ServiceAlertBatchAction string)
- Parameters

**Behavior:**
- On load: `JobService.getRecentAndOngoingTasks()` → populates table
- SSE subscription (`ServerSentEventType.ACTIVEJOBS`): merges new/updated `JobTaskDto` by `jobTaskId`; removes Finished tasks after 15-minute grace period
- Global filter on `currentStatus`, `name`, `parameters`
- Multi-select filter on status available 
- Row click → `TaskDetailsDialogContentComponent` (shows full status history)
- Sorted by status (Queued first, then Running, then Finished by recency)

**`active-job` component:** Compact indicator used in dashboard/header area — shows currently running jobs inline.

---

## 7. Rules

1. `Job.Name` is the canonical string form of `ServiceAlertBatchAction` — matches must be exact
2. `JobTaskStatuses` is append-only — status history is never updated, only new rows added
3. Azure Batch jobs hold `AzureJobId`/`AzureTaskId` references for correlation; in-process jobs leave these null
4. Per-server queue isolation: web server 1 cannot enqueue into web server 2's `SmsBackgroundService` queue
5. Finished tasks are visible in monitoring UI for 15 minutes post-completion, then auto-removed from live view
6. Each `ClientEventBackgroundService` instance tracks its own last-seen `ClientEvents.Id` — no central cursor
7. `SendGridBackgroundService` accepts `EmailMessage` records without a `SmsLogId` — system emails (password reset, account activation) bypass the SmsLog pipeline
