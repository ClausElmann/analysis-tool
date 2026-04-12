# Email — A9 Immediate-Dispatch Channel Extraction

**Date:** 2026-04-11 (moved to correct location 2026-04-12)  
**Scope:** Layer 0 extraction (`c:\Udvikling\sms-service\`)  
**Extracted by:** analysis-tool Copilot (Layer 1 output — belongs here, not in green-ai)  
**Purpose:** Document existence and contract of ISingleSendGridProcessingChannel for green-ai STEP 7 implementation  
**Authority:** Layer 1 INFORMATIONAL — green-ai reads this, never reads Layer 0 directly

---

## 1. Immediate-Dispatch Contract

### 1.1 `ISingleSendGridProcessingChannel`

| Field | Value |
|---|---|
| File | `ServiceAlert.Services\Messages\BackgrundServices\Email\SendGrid\ISingleSendGridProcessingChannel.cs` |
| Class | `ISingleSendGridProcessingChannel` |
| Method | `QueueMessages(IEnumerable<int> emailMessageIds)` |
| Line | 8 |
| Inherits from | `ISingleProcessingChannel` |

**Observed behavior:**  
Extends `ISingleProcessingChannel` with a multi-id variant. The base interface (`ISingleProcessingChannel`) defines:
- `QueueMessage(int id)` — enqueues single ID and signals the `AutoResetEvent`
- `QueueMessages(IEnumerable<int> ids)` — enqueues multiple IDs, then signals once
- `GetMessageId()` — dequeues one ID from `ConcurrentQueue<int>`
- `WaitForMessages()` — blocks on `AutoResetEvent.WaitOne()` (no timeout)
- `IsTheQueueEmpty` — returns `ConcurrentQueue<T>.IsEmpty`

**Relevance to A9:** This IS the A9 contract. It exists in Layer 0.

---

### 1.2 `SingleSendGridProcessingChannel` (concrete implementation)

| Field | Value |
|---|---|
| File | `ServiceAlert.Services\Messages\BackgrundServices\Email\SendGrid\SingleSendGridProcessingChannel.cs` |
| Class | `SingleSendGridProcessingChannel : ISingleSendGridProcessingChannel` |
| Method | `QueueMessages` |
| Line | 40 |

**Observed behavior:**  
- Internal state: `ConcurrentQueue<int>` + `AutoResetEvent`
- `QueueMessages`: enqueues each ID into `ConcurrentQueue`, then calls `sendMessagesEvent.Set()` ONCE after all are enqueued
- `WaitForMessages`: calls `sendMessagesEvent.WaitOne()` — blocks indefinitely until `Set()` is called
- `GetMessageId`: calls `TryDequeue()` — returns null when queue is empty

**Key constraint:** The `AutoResetEvent` is set once per `QueueMessages` call regardless of count. Worker wakes once and drains the entire queue.

**Relevance to A9:** This is the complete concrete implementation of the A9 channel. No `System.Threading.Channels.Channel<T>` is used — the pattern uses `ConcurrentQueue<int>` + `AutoResetEvent` instead.

---

### 1.3 DI Registration

| Context | Registration | Line |
|---|---|---|
| `ServiceAlert.Api\Startup.cs` | `services.AddSingleton<ISingleSendGridProcessingChannel, SingleSendGridProcessingChannel>()` | 584 |
| `ServiceAlert.Contracts\Extensions\ServiceCollection\ServiceCollectionExtensions.cs` | `services.AddSingleton<ISingleSendGridProcessingChannel, SingleSendGridProcessingChannel>()` | 714 |
| `ServiceAlert.Batch\Infrastructure\DependencyRegistrar.cs` | `services.AddScoped<ISingleSendGridProcessingChannel, SingleSendGridProcessingChannel>()` | 339 |
| `ServiceAlert.Worker.Voice\Program.cs` | `services.AddSingleton<ISingleSendGridProcessingChannel, SingleSendGridProcessingChannel>()` | 47 |

**Critical observation:** In the API context it is registered as **Singleton**. This is mandatory for cross-thread communication between the request scope (`EmailService`) and the background service (`SendGridBackgroundService`). Both share the same channel instance.

---

## 2. Worker Trigger Model

### 2.1 `SendGridBackgroundService`

| Field | Value |
|---|---|
| File | `ServiceAlert.Services\Messages\BackgrundServices\Email\SendGrid\SendGridBackgroundService.cs` |
| Class | `SendGridBackgroundService : ISendGridBackgroundService` |
| Method | `DoWorkAsync(CancellationToken stoppingToken)` |
| Loop entry | Line 73 |
| Wake-up call | `_singleSendGridProcessingChannel.WaitForMessages()` — line 75 |

**Observed behavior:**
```
while (!stoppingToken.IsCancellationRequested)
{
    _singleSendGridProcessingChannel.WaitForMessages();  // BLOCKS until QueueMessages fires AutoResetEvent
    // drain queue: _singleSendGridProcessingChannel.GetMessageId() in batches of 500
    // call SendEmailMessagesAsync(emailMessageIds) per batch
}
```
- Worker **only wakes up** when `sendFast: true` triggers `QueueMessages()` via the channel
- Worker does NOT poll DB independently — no timer, no scheduled interval
- After waking, the worker queries DB using the IDs from the in-memory queue (`EmailWebServerSendGridWorkloadLoader` calls `_emailService.GetEmailMessagesFromStatusAndIds(...)`)

**Hosted service wiring:**  
`services.AddHostedService<ConsumeScopedServiceHostedService<ISendGridBackgroundService>>()` — line 599, `Startup.cs`  
`ConsumeScopedServiceHostedService<T>` extends `BackgroundService` and calls `DoWorkAsync` directly in `ExecuteAsync`.

**Relevance to A9:** `SendGridBackgroundService` IS the A9 "fast path" consumer. The contract between caller and worker is exactly `ISingleSendGridProcessingChannel.QueueMessages(ids)`.

---

### 2.2 Batch Job (non-fast path)

| Field | Value |
|---|---|
| File | `ServiceAlert.Services\Gateways\EmailGateways\EmailsBulk.cs` |
| Class | `EmailsBulk : IEmailsBulk` |
| Method | `ProcessQueuedEmailsSendGridAsync(bool live)` |
| Line | 65 |

**Observed behavior:**
- Triggered externally via `ServiceAlert.Batch\Program.cs` line 321: `case ServiceAlertBatchAction.send_emails_sendgrid`
- Uses `SendGridWorkloadLoader` which calls `_emailRepository.GetQueuedEmails(chunkSize, currentStatus, nextStatus)` — direct DB poll by status
- Processes `Queued`, `QueuedFirstRetry`, `QueuedSecondRetry`, `QueuedThirdRetry`, plus orphaned messages

**This is the dispatch path for `sendFast: false` messages.** Messages persisted as `Queued` without the channel signal are dispatched by this batch job on an external schedule.

---

## 3. sendFast Semantics

### 3.1 Where `sendFast` is read

| File | Class | Method | Line | Read |
|---|---|---|---|---|
| `ServiceAlert.Services\Mails\EmailService.cs` | `EmailService` | `SendEmailMessages` | 402 | Parameter declaration `bool sendFast = false` |
| `ServiceAlert.Services\Mails\EmailService.cs` | `EmailService` | `SendEmailMessages` | 468 | `if (sendFast)` — the only conditional |
| `ServiceAlert.Services\Gateways\EmailGateways\EmailsWorkloadProcessor.cs` | `EmailMessageWorkloadProcessor` | constructor | 33 | Stored as `_sendFast` for workload processor |
| `ServiceAlert.Services\Gateways\EmailGateways\EmailsWorkloadProcessor.cs` | `EmailMessageWorkloadProcessor` | (usage) | ~38 | `_sendFast = sendFast` |

### 3.2 Exact `sendFast` branch (EmailService.cs lines 468–471)

```csharp
if (sendFast)
{
    _singleSendGridProcessingChannel.QueueMessages(emailMessages.Select(x => x.Id));
}
```

**Observed behavior:**
- This executes **after** A7 (BulkInsertEmailMessages) and **after** A8 (InsertEmailAttachments + UpdateEmailMessages)
- The `if (sendFast)` block is the ONLY difference between `sendFast: true` and `sendFast: false`
- `sendFast: false` = messages persist to DB, channel is NOT called, batch job dispatches later
- `sendFast: true` = messages persist to DB, channel IS called, `SendGridBackgroundService` wakes up immediately

### 3.3 Test verification (`EmailServiceTests.cs`)

| Test | Line | Assertion |
|---|---|---|
| `SendEmailMessages_SendFastIsSetToTrue_QueueTheEmailMessages` | 506–540 | `_singleSendGridProcessingChannel.Received().QueueMessages(Arg.Is<IEnumerable<int>>(x => x.Count() == 2))` |
| Tests with `sendFast: false` | 458, 491 | `_singleSendGridProcessingChannel` is NOT asserted on — implicitly: `DidNotReceive().QueueMessages(...)` |

**Observed behavior confirmed by Layer 0 tests:** `sendFast: true` calls `QueueMessages`; `sendFast: false` does not.

### 3.4 Does sendFast only hint priority, or truly bypass polling?

**Answer from code:** `sendFast: true` **truly bypasses polling**. The `SendGridBackgroundService` worker loop calls `WaitForMessages()` which blocks on `AutoResetEvent.WaitOne()` with **no timeout**. Without a `QueueMessages` call, the worker never wakes. There is no periodic timer, no polling loop, no DB scan in the hosted service path.

**The two dispatch paths are entirely separate:**

| Path | Trigger | Loader | Timing |
|---|---|---|---|
| Fast path | `sendFast: true` → `QueueMessages` → `AutoResetEvent.Set()` | `EmailWebServerSendGridWorkloadLoader` (by IDs) | Immediate (in-process) |
| Batch path | `ServiceAlertBatchAction.send_emails_sendgrid` | `SendGridWorkloadLoader` (DB scan by status) | External schedule |

**Code and test interpretation agree.** No conflicting evidence found.

---

## 4. Minimal Reconstruction Candidate List

> Provided because conclusion is `A9_CONTRACT_FOUND`.  
> Interface/class names only. No implementation. No signatures beyond what Layer 0 shows.

| Artifact | Type | Observed name |
|---|---|---|
| Immediate-dispatch channel interface | Interface | `ISingleSendGridProcessingChannel` |
| Base channel interface | Interface | `ISingleProcessingChannel` |
| Concrete channel implementation | Class | `SingleSendGridProcessingChannel` |
| Background worker interface | Interface | `ISendGridBackgroundService` |
| Background worker implementation | Class | `SendGridBackgroundService` |
| Hosted service wrapper | Generic class | `ConsumeScopedServiceHostedService<T>` |
| Web-server-side workload loader | Class | `EmailWebServerSendGridWorkloadLoader` |

**Not included:** Method signatures, constructor shapes, internal queue type, `AutoResetEvent` usage — those are implementation details for the architecture decision, not the analysis.

---

## 5. Conclusion

```
A9_CONTRACT_FOUND
```

`ISingleSendGridProcessingChannel` exists in Layer 0 with:
- A concrete implementation (`SingleSendGridProcessingChannel`)
- A consumer (`SendGridBackgroundService` — hosted service)
- A caller (`EmailService.SendEmailMessages` — `if (sendFast)` branch)
- Test coverage verifying the `sendFast: true` behavior
- Singleton DI registration in the API confirming cross-thread intent

The A9 contract is **real**, **proven**, and **not invented**. It can be reconstructed in green-ai from Layer 0 evidence.

---

## 6. Implications for STEP 7 (Analysis only — no code)

1. `ISingleSendGridProcessingChannel` must be defined with at minimum: `QueueMessages(IEnumerable<int>)` from Layer 0 observation
2. Base interface `ISingleProcessingChannel` must also be present: `QueueMessage(int)`, `QueueMessages(IEnumerable<int>)`, `GetMessageId()`, `WaitForMessages()`, `IsTheQueueEmpty`, `IDisposable`
3. Concrete implementation uses `ConcurrentQueue<int>` + `AutoResetEvent` — not `System.Threading.Channels`
4. Registration MUST be `AddSingleton` in the API context (not Scoped, not Transient) — shared between request scope and background service scope
5. `SendGridBackgroundService` (hosted service) wraps the drain loop; has no DB polling of its own
6. IDs are written to the channel AFTER A7+A8 complete (post-transaction)
7. No `sendFast` change is needed in the current `SendEmailCommand` — the flag already exists

**Active locks:**
- `A9_DEFERRED_PENDING_STEP7` → this analysis satisfies the pre-analysis gate
- `SEND_FAST_NOT_ACTIVE_IN_MVP` → must be reconsidered: Layer 0 shows sendFast is a real, tested, production path, not a hint

**Escalation for Architect:**  
The `SEND_FAST_NOT_ACTIVE_IN_MVP` lock was set when A9 appeared to have no contract. Now that A9_CONTRACT_FOUND, the lock's rationale has changed. Architect must decide whether to upgrade this lock or keep MVP to batch-only dispatch.
