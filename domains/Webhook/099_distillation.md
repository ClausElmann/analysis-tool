# DOMAIN DISTILLATION — Webhook
**Status:** APPROVED_BASELINE 2026-04-11
**Source:** Source-primary (Layer 1 score 0.37 — source code primary)
**Authority:** INFORMATIONAL (Layer 1)

---

## 1. DOMAIN ROLE

Webhook is a **dual-direction integration layer**:

1. **Outbound webhooks** — ServiceAlert notifies registered customer systems when events occur (web message viewed, message delivery status changed). Managed via `ServiceAlert.Api` REST API.
2. **Inbound gateway webhooks** — External delivery gateways (GatewayAPI, Infobip, SendGrid, Strex, 1919) POST callbacks to ServiceAlert when delivery status changes or inbound messages arrive.

No Angular UI found for webhook management — the outbound webhook registration API is used directly.

---

## 2. KEY ENTITIES

### 2a. Outbound webhooks

| Entity | Fields | Purpose |
|---|---|---|
| `WebhookRegistrationDto` | `Id: Guid`, `EventType: EventType`, `CallbackUrl: string`, `Secret: string`, `AlarmEmails: string` | Represents a registered outbound webhook |
| `RegisterWebhookCommand` | `EventType`, `CallbackUrl`, `Secret`, `AlarmEmails` | Create/update command |
| `WebhookEventTypeDto` | `EventType` | Describes an available event type |
| `WebhookRegistration` | (domain entity, same fields as above + `CustomerId: int`) | Persisted registration entity |
| `IWebhookService` / `WebhookService` | — | Outbound webhook crud + send |
| `IWebhooksRepository` / `WebhooksRepository` | — | Persistence layer |
| `WebhookMessagesBackgroundService` | — | Background drain loop; reads from `WebhookMessagesProcessingChannel` |
| `WebhookMessagesProcessingChannel` | — | .NET Channel buffer between producers and the background dispatcher |

### 2b. Gateway inbound controllers (receive callbacks)

| Controller | Purpose | Provider |
|---|---|---|
| `GatewayApiController` | Inbound SMS + quick-reply events from GatewayAPI | GatewayAPI |
| `InfobipWebhookController` | Delivery status + voice status callbacks | Infobip |
| `NineteenNineteenController` | 1919 SMS keyword-based unsubscribe/terminate | 1919 (DK/NO infrastructure) |
| `SendgridController` | Email delivery event callbacks (delivered, bounced, spam) | SendGrid |
| `StrexController` | Delivery + reply callbacks from Strex | Strex (Norwegian carrier) |

---

## 3. BEHAVIORS

### 3a. Outbound webhook registration (`ServiceAlert.Api`, `/WebHooks`)
- `GET /WebHooks` → returns `WebhookEventTypeDto[]` — available event types: `EventType.Webmessage`, `EventType.MessageStatus`
- `GET /WebHooks/Registrations/all` → `WebhookRegistrationDto[]` — all registrations for current customer
- `GET /WebHooks/Registrations/{registrationId}` → single `WebhookRegistrationDto`
- `POST /WebHooks/Registrations(RegisterWebhookCommand)` → creates new registration, returns 302 redirect; **idempotent** — if a registration already exists with same `callbackUrl` for this customer, returns redirect to existing (no duplicate created)
- `PUT /WebHooks/Registrations/{registrationId}(RegisterWebhookCommand)` → create-or-update (upsert by Id), returns 204
- `DELETE /WebHooks/Registrations/{registrationId}` → deletes if owned by customer, returns 204

Registration is per-customer, per-eventType. `Secret` is used for HMAC signing of outbound payloads. `AlarmEmails` defines alert notification addresses.

### 3b. Outbound webhook dispatch
- When a triggering event occurs (e.g. web message viewed, delivery status changed), the system writes a message to `WebhookMessagesProcessingChannel`.
- `WebhookMessagesBackgroundService` reads asynchronously from the channel and calls `IWebhookService.SendWebhookMessageAsync(webhookMessage)`.
- Runs as a persistent `BackgroundService` (IHostedService). Errors handled: `SqlException`, `TimeoutException`, `TaskCanceledException` → Fatal log, continue. `OperationCanceledException` / `ChannelClosedException` → stop.

### 3c. Inbound gateway callbacks

**GatewayAPI — inbound SMS:**
- `POST Callback([FromBody] GatewayApiMobileOriginatedMessageDto)` — `[AllowAnonymous]`
- Publishes `StandardReceiverGroupMessageReceivedNotification(message, receiver, msisdn)`

**GatewayAPI — quick reply:**
- `POST Reply([FromBody] GatewayApiMobileOriginatedMessageDto)` — `[AllowAnonymous]`
- Publishes `InboundMessageEvent(message, receiver, sender, GatewayProvider.GatewayApi)`

**Infobip:**
- Handles Infobip delivery status events + voice call status callbacks
- Routes to appropriate status processing via `VoiceMessageStatusChangedEventHandler`

**Strex:**
- `StrexController` → processes `StrexReplyDto` for Strex-specific SMS reply/status events

**1919 (NineteenNineteenController):**
- Processes SMS keyword unsubscribe / termination events from Danish/Norwegian 1919 SMS infrastructure

**SendGrid:**
- Processes email event callbacks (delivered, bounced, opened, spam, etc.)

---

## 4. FLOWS

### Flow A — Customer registers an outbound webhook
1. Customer calls `POST /WebHooks/Registrations` with `{eventType, callbackUrl, secret, alarmEmails}`.
2. System checks idempotency: if registration with same `callbackUrl` exists for this customer → returns 302 to existing.
3. Otherwise creates new `WebhookRegistration` with `Id = Guid.NewGuid()` → returns 302 to new registration URL.
4. Customer verifies via `GET /WebHooks/Registrations/{id}`.

### Flow B — ServiceAlert dispatches outbound webhook event
1. Event occurs (e.g. delivery status changes).
2. System produces message to `WebhookMessagesProcessingChannel`.
3. `WebhookMessagesBackgroundService` drains channel → calls `IWebhookService.SendWebhookMessageAsync`.
4. Service fetches registrations matching `(customerId, eventType)`.
5. POSTs payload to each `callbackUrl` with `Secret`-signed header.
6. Logs result; on transient failure → logs Fatal and continues processing next message.

### Flow C — Inbound SMS from GatewayAPI
1. GatewayAPI POSTs to `Callback` (or `Reply`) endpoint — anonymous allowed.
2. Controller publishes `InboundMessageEvent` via MediatR.
3. Handler routes to keyword matching → standard receiver group or quick-response capture.

---

## 5. RULES

1. **Dual direction**: Webhook domain has two independent sub-features: customer-facing outbound webhook registration/dispatch (API) and inbound gateway callback receivers. These share the domain but are functionally separate.

2. **No UI**: Outbound webhook registration has no Angular frontend. Management is via the `ServiceAlert.Api` REST API only. The `integrations` domain notes this as a REST API surface.

3. **Idempotent registration**: `POST /WebHooks/Registrations` does not duplicate. If `callbackUrl` matches an existing registration for the same customer, returns 302 to the existing one.

4. **Customer-scoped registrations**: All outbound webhook registrations are scoped to `WorkContext.CurrentCustomerId`. A customer cannot access or modify another customer's registrations (enforced by ownership check; returns 403/404).

5. **Inbound callbacks are anonymous**: All inbound gateway webhook endpoints are `[AllowAnonymous]`. Authentication relies on the specific provider's signature or secret mechanisms, not JWT.

6. **Channel-based dispatch**: Outbound webhook delivery is decoupled from the event trigger via `WebhookMessagesProcessingChannel` (System.Threading.Channels). This prevents blocking the main request pipeline during outbound HTTP calls.

7. **Available event types**: Only two outbound event types currently exist — `EventType.Webmessage` and `EventType.MessageStatus`. Additional types would require code changes.
