# Domain Distillation: logging

**STATUS:** APPROVED_BASELINE  
**Completeness source:** 0.88 (Layer 1) — well-populated  
**UI verified from:** N/A — logging is a server-side concern with no dedicated UI management component  
**Date:** 2026-04-11  

---

## PURPOSE

Logging is the system's observability infrastructure. Three parallel logging pipelines capture different categories of events: general application errors and events go to the database and Azure Application Insights; critical failures trigger an immediate email alert; every incoming HTTP request can optionally be recorded; every outbound HTTP call to external systems is automatically captured; Norwegian API calls are captured separately for billing compliance; map tile requests are metered per profile; and every superAdmin impersonation is audited. Old logs are purged by scheduled batch jobs to prevent unbounded database growth.

---

## CORE CONCEPTS

1. **ISystemLogger** — the single interface for all application-level logging. Three implementations are registered simultaneously: database logger, Azure Application Insights logger, and a fatal-error email notifier. All three receive every log call (composite pattern).

2. **Log levels** — the standard severity scale: Information, Warning, Error, Fatal. Fatal events trigger the email notifier in addition to the database write.

3. **RequestLog** — a record of an inbound HTTP request: the path, method, query string, request body, response body, status code, and duration. Only captured when `RequestLogLevel` app setting enables it — performance-sensitive, should not be enabled at "All" in production.

4. **OutgoingRequestLog** — a record of an outbound HTTP call made by the system to external APIs (SendGrid, GatewayAPI, Infobip, KRR, KoFuVi, Datafordeler, etc.). Captured automatically for every registered HttpClient via a delegating handler — services do not write these themselves.

5. **NorwegianRequestLog** — a dedicated log for outbound calls to Norwegian APIs (KRR, KoFuVi) required for billing and compliance reporting. Separate table from general outbound logs.

6. **MapRequestLog** — per-request record of map tile renders per profile. Used to quantify and bill map API usage per customer.

7. **ImpersonationLog** — audit trail entry created every time a superAdmin begins impersonating another user. Records both the admin's ID and the target user's ID.

8. **Azure Blob errorlogs** — a safety net for the three failure types that cannot use the database logger: Dapper cannot connect to the database, Dapper license is invalid, SendGrid email send failure. Written directly to blob storage, bypassing all other logging infrastructure.

---

## CAPABILITIES

1. Log application events, errors, and exceptions at any log level — routed to database and Azure Application Insights simultaneously.
2. Receive an email alert when a Fatal-level event is logged.
3. Capture full inbound HTTP request/response pairs — controlled by the RequestLogLevel system setting (off / errors only / all requests).
4. Automatically capture every outbound HTTP call without requiring services to write log code.
5. Record Norwegian API calls separately for billing compliance.
6. Record map tile requests per profile for usage billing.
7. Audit superAdmin impersonation events.
8. Capture three categories of infrastructure-level failures to Azure Blob when the database logger itself is unavailable.
9. Purge old application logs and request logs via scheduled cleanup jobs.

---

## FLOWS

### 1. Application Error Logging
Code catches an exception (or a service operation records a notable event) → calls `ISystemLogger.InsertLog(level, message, fullMessage, user, module, data)` → all three logger implementations receive the call → DB logger writes to `Logs` table (ShortMessage truncated at 1500 chars, FullMessage unbounded) → AppInsights logger sends telemetry → if Fatal: FinalEmailLogger sends email to the configured admin address.

### 2. HTTP Request Logging
Inbound request arrives → middleware checks `AppSetting(RequestLogLevel)` → if "off": skip → if "Error": only log if response status ≥ 400 → if "All": always log → write `RequestLogs` row with path, body, response body, status code, duration.

### 3. Outbound HTTP Logging
Service makes an HTTP call via a DI-registered HttpClient → the `OutgoingHttpClientLoggingHandler` delegating handler intercepts the call transparently → before the call: captures request URL, method, body → after the call: captures response body, status code, duration → writes `OutgoingRequestLogs` row.

### 4. Log Cleanup
Scheduled batch jobs `cleanup_systemlogs` and `cleanup_requestlogs` run periodically → delete log rows older than a configured retention threshold → prevents unbounded storage growth.

---

## RULES

1. All three logger implementations (DB, AppInsights, Email) receive every log call. There is no branching by destination — all three always fire.
2. Fatal-level events trigger an immediate email in addition to the standard DB/AppInsights write.
3. ShorMessage is truncated at 1500 characters. FullMessage (stack traces) is unlimited.
4. HTTP request logging is gated by `AppSetting(RequestLogLevel=160)`. "All" mode has significant performance impact and must not be left on in production.
5. Outbound HTTP logging is transparent — it is injected via a DelegatingHandler. Services do not call log methods for external API calls.
6. KRR/KoFuVi Norwegian API calls are written to a separate `NorwegianOutgoingRequestLogs` table, not the general outbound log, for billing compliance separation.
7. Infrastructure failures that prevent the DB logger from working (no DB connection, Dapper license issue, SendGrid send failure) are written to the Azure Blob `errorlogs` container as a last-resort fallback.
8. Cleanup jobs prevent unbounded log table growth. Retention threshold is a system configuration value.

---

## GAPS

1. **No admin UI for log viewing** — logs are queryable only via database tools or Azure Application Insights. There may be a superAdmin log viewer component not yet mapped (Log domain entity list includes `LogController`).
2. **Retention thresholds not captured** — the specific retention duration for each log type is not documented in Layer 1.


---

## UI-lag: OutgoingRequestLogsService (core/services)

**Fil:** `core/services/outgoing-request-logs.service.ts`  
**Domain:** logging

| Metode | Beskrivelse |
|---|---|
| `getNorwegianRequestLogsStatistics()` | Statistik over udgående requests til norske API'er (`NorwegianRequestLogStatisticsReadModel`) |

*Minimal service — kun én metode. Benyttes til norsk stats-rapport i super-admin.*
