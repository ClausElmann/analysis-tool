# Delivery — Domain Distillation

**Status:** APPROVED_BASELINE 2026-04-11  
**Completeness score (Layer 1):** 0.84 (behaviors=[] — WIKI + source-primary)  
**Evidence source:** `SMS-service.wiki/DEVELOPMENT/Implementation/Workload-Executor.md`, `SMS-service.wiki/DEVELOPMENT/Implementation/Sms-gateway-Strex.md`, entity list from `010_entities.json`, flows from `030_flows.json`

---

## What this domain is

**Delivery** is the backend domain that physically sends messages through external gateways. It implements a **WorkloadExecutor pattern** that decouples work loading, processing, and status writing. There is no direct user-facing UI — delivery runs as a background service consuming a queue of SmsLogIds and dispatching to channel-specific gateways (SMS, Voice, Email, eBoks). It also processes inbound replies (inbound SMS and email).

---

## WorkloadExecutor Architecture

```
IWorkloadExecutor
  ├── gets IWorkload from → IWorkloadLoader
  ├── passes IWorkload to → IWorkloadProcessor
  └── updates statuses via → IWorkloadStatusWriter
```

**Two executor types:**

| Type | Behavior |
|---|---|
| `WorkloadExecutor` | Loops calling IWorkloadLoader until no more work |
| `SingleChunkWorkloadExecutor` | Calls IWorkloadLoader once per run; used for interlacing multiple executors |

**RoundRobinWorkloadLoader:** Takes a list of IWorkloadLoaders; rotates round-robin between them returning the first loader that has work. Continues from last successful loader on next call. `SetsInitialStatus=true` loaders lock records in DB during loading to prevent double-processing.

---

## SMS Delivery Pipeline

1. `SmsBackgroundService` dequeues `SmsLogIds` from `SingleSmsProcessingChannel`
2. Loads into workload loaders:
   - `SmsWebServerGatewayBulkWorkloadLoader` (primary)
   - `SmsWebServerRetryGatewayBulkWorkloadLoader` (retry)
3. `SmsGatewayRoutingWorkloadProcessor` routes batches:
   - Default → `GatewayApiBulkApiWorkloadProcessor` (GatewayAPI)
   - Norwegian alternative → `StrexSmsWorkloadProcessor`
4. `GatewayApiBulkTestWorkloadProcessor` — test mode (does not call real gateway)

**Interlacing order** (SingleChunkWorkloadExecutor):
1. High-priority executors (one per country)
2. Country executors (normal priority)  
3. Test mode executor

---

## Outbound Gateways

| Gateway | Technology | Key Classes |
|---|---|---|
| **GatewayAPI** | SMS (primary) | `GatewayApiBulkApiWorkloadProcessor`, `MultiSmsMessageDto`, `SmsMessageDto` |
| **Strex** | SMS (NO alternative) | `StrexDeliveryReportDto` |
| **Infobip** | Voice | `InfobipScenarioService`, `InfobipForwardingService`, `InfobipScenarioDto`, `InfobipCustomerVoiceSettingsChangedEventHandler` |
| **SendGrid** | Email | `SendGridBackgroundService`, `ISendGridBackgroundService` |
| **eBoks** | eBoks documents | `EboksService`, `EboksController`, `EboksRepository` |

---

## Delivery Status / Reports

- `DeliveryDto` — general delivery record
- `InfobipDeliveryReportDto` — Infobip (voice) delivery status callback
- `StrexDeliveryReportDto` — Strex (NO SMS) delivery status callback
- Status writers update `SmsLog` / delivery records in DB

---

## Inbound Message Processing

**Inbound SMS (citizen reply):**
- `GatewayApiMobileOriginatedMessageDto` — mobile-originated message from GatewayAPI
- Parsed by `InboundParseEventHandler` equivalent on SMS path
- Routes to quick response handling or conversation system

**Inbound Email (via SendGrid webhook):**
- `InboundParseEventHandler` — processes SendGrid inbound parse webhook events
- `ProcessedInboundEmailRepository` — tracks processed events to prevent duplicate handling
- `IProcessedInboundEmailRepository` — interface

---

## Infobip Voice Scenarios

- `InfobipScenarioDto` — scenario definition (voice call flow)
- `InfobipScenarioService` / `IInfobipScenarioService` — manages voice scenarios in Infobip
- `InfobipForwardingService` / `IInfobipForwardingService` — voice forwarding configuration
- `InfobipCustomerVoiceSettingsChangedEventHandler` — reacts to voice settings changes per customer

---

## Capabilities

1. Queue-based SMS dispatch via WorkloadExecutor pattern
2. Gateway routing: GatewayAPI (primary) + Strex (NO alternative)
3. High-priority interlaced sending (country-per-executor, then test mode)
4. Test mode delivery (GatewayApiBulkTestWorkloadProcessor — no real send)
5. Retry path for failed SMS deliveries
6. Voice delivery via Infobip (scenario-based call flows)
7. Email delivery via SendGrid
8. eBoks document delivery
9. Delivery status callback processing (Infobip, Strex)
10. Inbound SMS processing (GatewayAPI mobile-originated)
11. Inbound email processing (SendGrid parse webhook, deduplication)
12. RoundRobinWorkloadLoader for multi-source queue balancing
13. DB-lock record prevention (SetsInitialStatus) on workload loading

---

## Flows

### FLOW_DEL_001: Outbound SMS delivery
1. `SmsBackgroundService` picks SmsLogIds from `SingleSmsProcessingChannel`
2. Loads into SmsWebServer workload loaders (primary + retry)
3. `SmsGatewayRoutingWorkloadProcessor` routes to GatewayApi or Strex per country/config
4. `GatewayApiBulkApiWorkloadProcessor.ProcessWorkAsync()` calls `GatewayApiClient.SendMultiAsync()`
5. Delivery status written back to DB via IWorkloadStatusWriter
6. On failure: retry batch picked up by `SmsWebServerRetryGatewayBulkWorkloadLoader`

### FLOW_DEL_002: Inbound SMS (citizen reply)
1. GatewayAPI receives reply SMS → calls webhook
2. `GatewayApiMobileOriginatedMessageDto` parsed
3. Match against active broadcast with quick response options
4. Response recorded → `QuickResponseRecipientRespondentDto` created
5. Stats updated on broadcast

### FLOW_DEL_003: Inbound email
1. SendGrid receives email → calls inbound parse webhook
2. `InboundParseEventHandler` checks `ProcessedInboundEmailRepository`
3. If not duplicate: processes as email reply (routes to conversation or quick response)

### FLOW_DEL_004: Voice delivery
1. Broadcast with voice channel → `InfobipScenarioService` resolves scenario
2. Voice call initiated to recipient via Infobip
3. `InfobipDeliveryReportDto` received on callback → status updated

---

## Rules

| ID | Rule |
|---|---|
| DEL_R001 | Gateway selection is per-country; Norwegian profiles may route to Strex |
| DEL_R002 | Test mode uses `GatewayApiBulkTestWorkloadProcessor` — no real send; logs status as sent |
| DEL_R003 | Inbound email must check `ProcessedInboundEmailRepository` to prevent duplicate handling |
| DEL_R004 | `SetsInitialStatus=true` workload loaders lock DB records during load to prevent double-pick |
| DEL_R005 | SingleChunkWorkloadExecutor interlaces: high-priority → country executors → test mode |

---

## Gaps

| ID | Gap |
|---|---|
| GAP_001 | `InfobipForwardingService` call flow not traced — voice forwarding behavior unknown |
| GAP_002 | Retry exhaustion behavior (give-up threshold) not confirmed from source |
| GAP_003 | Social media delivery (Facebook/Twitter) gateway not in entity list — relationship to SocialMediaGatewayWorkloadLoader unknown |
