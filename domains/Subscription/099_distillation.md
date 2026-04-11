# Domain Distillation — Subscription

**Status:** APPROVED_BASELINE  
**Completeness score (Layer 1):** 0.58  
**Evidence:** Layer 1 entities + UI source (subscribe-unsubscribe tabs, subscription-notification, subscription-import, iFrame-subscription components)

---

## 1. Core Concept

`Subscription` is the citizen self-subscription domain — citizens subscribe to receive alerts for specific addresses or supply numbers via the web iFrame widget, Excel import, or FTP. This is distinct from `Enrollment` (app registration) and `standard_receivers` (staff alert targeting).

---

## 2. Subscription Types

| Type | Commands |
|---|---|
| Address subscription | `SubscribeAddressCommand`, `UnsubscribeAddressCommand`, `AddressSubscriptionDto`, `SubscribedAddressDto` |
| Supply number subscription | `SubscribeSupplyNumberCommand`, `UnsubscribeSupplyNumberCommand`, `SupplyNumberSubscriptionDto` |
| Zip code (by country) | `ZipCodeAddressSubscriptionDKDto`, `ZipCodeAddressSubscriptionFIDto`, `ZipCodeAddressSubscriptionNODto`, `ZipCodeAddressSubscriptionSEDto` |
| Standard receiver group | `StandardReceiverGroupSubscriptionDto/ReadModel` |
| FTP delivery | `FtpSubscriptionDataModel`, `FtpSubscriptionSupplyNumberDataModel` |

---

## 3. Entities

| Entity | Description |
|---|---|
| `SubscriptionDto` / `SubscriptionReadModel` | Core subscription record |
| `SubscriptionExtendedReadModel` | Extended detail view |
| `SubscriptionIndexItemDto/ReadModel` | List item for subscription index |
| `SubscriptionsCountReadModel/Dto` | Aggregate counts |
| `CustomerSubscriptionModuleSettingsDto` | Per-customer module configuration |
| `SubscriptionModuleModel` | Module state |
| `SubscriptionImportSettingsDto` | Import configuration |
| `SubscriptionReportReadModel` | Report output data |
| `StandardReceiverGroupActivationModel` | Subscription group activation record |
| `StandardReceiverSubscriptionDto` | Standard receiver subscription |
| `StandardReceiverSubscriptionModuleDto` | Subscription module per standard receiver |
| `SupplyNumberSubscriptionNotificationReadModel` | Notification state per supply number subscription |

---

## 4. Lookup Commands

| Command | Description |
|---|---|
| `LookupSubscriptionsCommand` | Look up all subscriptions for an address |
| `LookupOwnerSubscriptionsCommand` | Look up subscriptions for a property owner |
| `LookupSupplyNumbersSubscriptionsCommand` | Look up subscriptions by supply number |

---

## 5. Events

| Handler | Trigger |
|---|---|
| `UnsubscribeMessageReceivedEventHandler` | Raised when SMS unsubscribe keyword received (from 1919 controller or enrollment) |
| `EnrollmentCreatedEventHandler` | Raised when new enrollment subscription is created |

---

## 6. Admin UI — subscribe-unsubscribe Module

**Tabs** (in order):

| Tab | Route | Notes |
|---|---|---|
| Subscription Module | iFrameSubscription | Displays the iframe subscription widget preview |
| Setup | iFrameSubscriptionSetup | Configure iframe widget (text, sender selection, HTML generation) |
| Subscription Report | subscriptionReport | Export subscription data (see reporting domain) |
| Excel Upload | excelUpload | Import subscriptions via Excel |
| Notify | notification | Subscription notification settings (guarded by role or SuperAdmin) |
| Enrollment App | enrollmentApp | Link to enrollment app (guarded by `registerApplication` flag or SuperAdmin) |

---

### Subscription Notification (`subscription-notification`)

Configures periodic reminder SMS to subscribers.

**Form:**
- Frequency selector (from API; SuperAdmin-editable only)
- Active toggle (binary checkbox)
- Notification text: SMS textarea with merge fields, char counter, msg counter, SMS length limit
- SuperAdmin: country + customer selector

**Behavior:** Save → `updateNotificationInfo()` — disabled if form invalid or pristine.

---

### Subscription Import (`subscription-import`)

Import address subscriptions from Excel.

**Flow:**
1. Download sample template (`bi-excel-button`)
2. `bi-data-import` component with `DataImportPurpose.Subscriptions`
3. Column mapping + validation → confirm → `confirmSubscriptionImport()`
4. SuperAdmin: `overrideCustomerId` parameter
5. Save configuration button available

---

## 7. Rules

1. Frequency selector disabled for non-SuperAdmin on notification screen — only SuperAdmin changes cadence
2. `Notify` tab only visible for users with subscription notification role OR SuperAdmin
3. `Enrollment App` tab only visible if customer has `registerApplication = true` OR SuperAdmin
4. Supply number subscriptions and address subscriptions are distinct — separate subscribe/unsubscribe commands
5. Zip code subscriptions are country-specific DTOs (DK/FI/NO/SE) — no unified model
6. FTP subscription delivery uses `FtpSubscriptionDataModel` for automated batch delivery
