# subscriptions — Domain Distillation

**Status:** APPROVED_BASELINE 2026-04-11
**Source:** Layer 0 primary — BalarmWebApp `SmsServiceWebApp.Controllers.SubscribeModuleController` (ApiEndpoints.json)
**Authority:** INFORMATIONAL

---

## DOMAIN IDENTITY

`subscriptions` is the **BalarmWebApp citizen-facing iFrame API layer** — the public-facing ASP.NET application (`BalarmWebApp` project, `SmsServiceWebApp` namespace) that serves the embedded self-subscription widget to end citizens.

**DISTINCT FROM `Subscription` domain:**
- `Subscription` = ServiceAlert admin UI for configuring the subscription module (iFrame setup, Excel import, report, notification settings)
- `subscriptions` = The actual BalarmWebApp HTTP API (`SubscribeModuleController`) that citizens interact with through the iFrame widget

These are **complementary**: `Subscription` (admin) configures what `subscriptions` (BalarmWebApp) serves.

---

## CORE API — SubscribeModuleController

**Base path:** `api/SubscribeModule/`
**Namespace:** `SmsServiceWebApp.Controllers.SubscribeModuleController`

### Widget Bootstrap
- `GetSubscriptionModuleModel(customerPublicId: Guid, languageId?)` → `SubscriptionModuleModel`
  - Entry point keyed by customer **public GUID** (never internal integer ID)
  - Returns widget configuration: allowed subscription types, language, customer branding

### PIN Authentication Flow
1. `RequestPinCodeAttempt(PinCodeRequestDto)` — sends SMS/email PIN to citizen
2. `VerifyPinCode(VerifyPinCodeRequestDto)` → `AnonymousTokenModel` — returns short-lived access token
3. `RequestAndSavePinCode()` — legacy no-arg GET variant

### Subscription Reads
- `GetSubscriptions(accessToken, phoneNumber, email, customerId, onlyBusiness?, onlyPrivate?, phoneVoice?, noOperatorLookup?)` → `SubscriptionDto[]`
  - `noOperatorLookup` skips Norwegian/Swedish mobile operator number resolution

### Subscription Mutations (citizen)
- `SubscribeAddress(SubscribeAddressCommand)` — add address KVHX subscription
- `SubscribeSupplyNumber(SubscribeSupplyNumberCommand)` — add supply number subscription
- `UnsubscribeAddress(UnsubscribeAddressCommand)` — remove address subscription
- `UnsubscribeSupplyNumber(UnsubscribeSupplyNumberCommand)` — remove supply subscription
- `UnsubscribeEnrollmentById(enrollmentId)` — remove by enrollment ID
- `UpdateAddressSubscriptionName(UpdateAddressSubscriptionNameCommand)` — rename address sub
- `UpdateSupplyNumberSubscriptionName(UpdateSupplyNumberSubscriptionNameCommand)` — rename supply sub
- `UpdateNotificationInfo(SubscriptionNotificationDTO)` — update notification preferences

### Admin API (same controller, authenticated session)
- `GetNotificationInfo(customerId)` → `CustomerSubscriptionSetting` — read notification config
- `GetSubscriptionsIndex(customerId, state?)` → `SubscriptionIndexItemDto[]` — admin subscription list
- `DownloadSubscriptions(customerId, countryId?, state?)` → file export
- `SubscribeFromCsv(UploadFromCSVDTO)` — bulk CSV load

---

## KEY ENTITIES

| Entity | Description |
|---|---|
| `SubscriptionModuleModel` | Widget config returned at bootstrap (Balarm.Web.Framework.Models.Subscribe) |
| `SubscriptionDto` | Individual subscription record (address or supply number) |
| `AnonymousTokenModel` | Short-lived citizen session token from PIN verification |
| `PinCodeRequestDto` | PIN request: phone number or email |
| `VerifyPinCodeRequestDto` | PIN verification payload |
| `CustomerSubscriptionSetting` | Notification frequency + active flag + merge fields (admin read) |
| `SubscriptionNotificationDTO` | Notification update command |
| `SubscribeAddressCommand` | {kvhx, accessToken, customerId, ...} |
| `SubscribeSupplyNumberCommand` | {supplyNumber, accessToken, customerId, ...} |
| `UploadFromCSVDTO` | Bulk CSV upload payload (admin) |
| `SubscriptionIndexItemDto` | Admin list item with subscription state |

---

## AUTHENTICATION MODEL

```
[Anonymous] → GetSubscriptionModuleModel(customerPublicId)
                         ↓
[Anonymous] → RequestPinCodeAttempt({phoneNumber/email})
                         ↓ SMS/email PIN delivery
[Anonymous] → VerifyPinCode({phoneNumber, pinCode})
                         ↓
             AnonymousTokenModel (access token)
                         ↓
[Token] → GetSubscriptions(accessToken, ...)
[Token] → SubscribeAddress(accessToken + command)
[Token] → UnsubscribeAddress(accessToken + command)
```

---

## FLOWS

### Flow 1: Citizen Widget Subscription
1. iFrame loads → `GetSubscriptionModuleModel(customerPublicId)` → widget config
2. Citizen enters phone/email → `RequestPinCodeAttempt` → PIN SMS/email sent
3. Citizen enters PIN → `VerifyPinCode` → `AnonymousTokenModel`
4. Load current subscriptions → `GetSubscriptions(accessToken, ...)`
5. Citizen subscribes/unsubscribes → address or supply number commands
6. Optional: update notification prefs → `UpdateNotificationInfo`

### Flow 2: Admin Bulk Import
1. Admin uploads CSV file → `SubscribeFromCsv(UploadFromCSVDTO)` → batch subscriptions created
2. View results → `GetSubscriptionsIndex(customerId, state)` → admin list
3. Export → `DownloadSubscriptions(customerId, countryId, state)` → file

---

## RULES

1. **Public GUID only** — Widget entry uses customer `publicId` (GUID), never internal integer `customerId` — prevents customer enumeration
2. **PIN-gated access** — Citizens must verify phone/email via PIN before read/write; `AnonymousTokenModel` gates all subscription mutations
3. **Dual subscription types** — Subscriptions are either address (KVHX-based) or supply number; separate commands for each
4. **Operator lookup flag** — `noOperatorLookup=true` on `GetSubscriptions` skips mobile operator resolution (performance vs accuracy tradeoff)
5. **Admin vs citizen split** — `GetSubscriptionsIndex`, `DownloadSubscriptions`, `SubscribeFromCsv` require authenticated admin session; citizen flow is anonymous+token
6. **BalarmWebApp app boundary** — This controller runs in the legacy BalarmWebApp ASP.NET project (separate deployment from ServiceAlert.Api); shares Balarm service libraries but is a separate API host
7. **`InvoiceErrorDto` / `SuperAdminInvoiceController`** — Domain extraction artifact; these billing entities do not belong to the subscription citizen flow (likely co-extracted due to shared service assembly)
