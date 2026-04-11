# Domain Distillation — integrations

**Status:** APPROVED_BASELINE  
**Completeness score (Layer 1):** 0.7833  
**Evidence:** Layer 1 entity list + backend controller source (FramWebController, NineteenNineteenController, webhook controllers)

---

## 1. Core Concept

`integrations` covers all external integration points of ServiceAlert — both inbound (external systems calling ServiceAlert) and outbound (ServiceAlert calling external systems). This includes third-party GIS tools, telco SMS keyword services, delivery gateway callbacks, AD/SCIM provisioning, and customer-facing REST API + webhook subscriptions.

---

## 2. Inbound Integrations

### FramWeb — Norwegian GIS Integration

**Controller:** `FramWebController` (`[AllowAnonymous]`, API key authenticated)

**Endpoint:** `POST GetPropertiesByShape`
- Auth: `api_key` query parameter validated against `AppSetting.FramwebApiKey`
- Input: `GetPropertiesByShapeRequest` — `WellKnownTextGeometri` (WKT geometry), `BufferRadius`, `SRS` (default 4326)
- Output: `GetPropertiesByShapeResult` — Norwegian properties within the WKT shape
- Returns `OwnerDto` / `PersonDto` / `PlotDto` / `PlotWrapperDto` / `PropertyIdDto` / `OwnershipCodeDto`
- Error: returns 500 with JSON `{SRS, ResponseStatus: {ErrorCode, Message, Errors}}`
- Hidden from Swagger (`[SwaggerIgnore]`)

**Purpose:** FramWeb (external Norwegian digital map tool) queries ServiceAlert for properties within a drawn polygon, then initiates mass notifications to those property owners.

---

### 1919 SMS Keyword Service

**Controller:** `NineteenNineteenController` (hidden from API explorer: `[ApiExplorerSettings(IgnoreApi = true)]`, `[AllowAnonymous]`)

**Endpoints:**
- `GET Callback(message, sender)` — inbound keyword SMS from telco:
  - Publishes `StandardReceiverGroupMessageReceivedNotification(message, 451919, sender)`
  - Returns XML terminate action: `<action><type>terminate</type></action>`
- `GET Unsubscribe(message, sender)` — unsubscribe keyword:
  - Publishes `UnsubscribeMessageReceivedEvent(message, 451919, sender)`
  - Returns XML terminate action

**Purpose:** Citizens send SMS to 451919 to subscribe/unsubscribe from a standard receiver group by keyword.

---

### Delivery Gateway Webhooks

All delivery gateway callbacks are via dedicated controllers:

| Controller | Gateway | Events |
|---|---|---|
| `GatewayApiController` | GatewayAPI | Inbound SMS (`GatewayApiMobileOriginatedMessageDto`), delivery reports |
| `InfobipWebhookController` | Infobip | Delivery reports (`InfobipDeliveryReportDto`), smart responses (`InfobipSmartResponseDto`) |
| `SendgridController` | SendGrid | Inbound email parse events |
| `StrexController` | Strex | Delivery reports (`StrexReplyDto`) |

See Delivery domain for full gateway details.

---

### SCIM 2.0 — AD Provisioning

**Controller:** `ScimGroupsController`

**Purpose:** Enterprise customers provision their Active Directory groups to ServiceAlert standard receiver groups. Users provisioned via SCIM automatically become standard receivers.

See standard_receivers domain for full details.

---

## 3. Outbound Integrations

### Customer Webhook Subscriptions

**Controller:** `WebhooksController`

- Customers register webhooks (`RegisterWebhookCommand`) to receive events
- `WebhookRegistrationDto` — registered webhook configuration
- `WebhookEventTypeDto` — event type selection

See Webhook domain for full details.

---

### `IntegrationBatchAppService`

Service for inter-process communication between the Azure Batch app and the web server. The Batch app calls back via this service to report job progress (used in `job_management` domain via `LogJobTaskStatusAsync`).

---

## 4. External API — HTTP REST

ServiceAlert exposes a REST API for external clients (municipalities, utilities).

**Key external-facing controllers:**
- `MessageController` — lookup, create, send SmsGroups
- `StatusController` — query broadcast status
- `SubscriptionController` — manage address/supply number subscriptions
- `StandardReceiverController` — manage standard receivers
- `TemplateController` — manage templates
- `BenchmarkController` — manage benchmark events
- `AddressController` — query address data
- `ProfileController` — profile management

**Auth:** Standard JWT bearer token auth (`LoginEmailPasswordDto → TokenDto`)

---

## 5. Rules

1. FramWeb authentication uses API key validated server-side against `AppSetting.FramwebApiKey` — not JWT
2. NineteenNineteenController is hidden from Swagger (`IgnoreApi=true`) — not documented for API consumers
3. 1919 callbacks return XML terminate response (telco protocol requirement)
4. SCIM provisioning integrates with AD groups — provisioned users map to standard receiver profiles automatically
5. `IntegrationBatchAppService` is the only allowed path for Azure Batch → web server callback; web server → Batch is via Azure Batch SDK
