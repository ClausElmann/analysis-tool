# pipeline_sales — Distillation

**Authority Layer:** Layer 1 (Derived Conceptual SSOT)
**Source-primary:** ServiceAlert.Web SuperAdminSalesInfoController + UI components
**Status:** Distilled

---

## 1. Domain Purpose

`pipeline_sales` provides two complementary capabilities for SuperAdmin sales operations:

1. **SalesInfo feature checklist** — A per-customer view showing which product features a customer has/does not have, computed by running admin-defined SQL queries against the customer record.
2. **SalesInfo query management** — An admin-managed library of named SQL queries (`SalesInfoQuery`) that define what feature data to retrieve.

This domain supports the sales pipeline by giving SuperAdmins a fast, configurable dashboard when examining any customer during the sales/support process.

**Note:** The entity list for `pipeline_sales` overlaps heavily with `pipeline_crm` (both reference `ProspectDto`, `SalesforceService`, etc.). The **unique** `pipeline_sales` contribution is the `SalesInfoQuery` / `SalesInfo` subsystem described here.

---

## 2. Core Entities

### SalesInfo
Read-only result entity. Computed by executing a `SalesInfoQuery` against a specific customer.

| Field | Type | Notes |
|---|---|---|
| `featureName` | string | Display name of the feature (from query's nameTranslateKey) |
| `hasFeature` | bool | Whether the customer has this feature |

Rendered via `bi-indicator-icon`: green check = `hasFeature`, red X = not `hasFeature`.

### SalesInfoQuery
Admin-managed named SQL query. Defines one "feature check" that can be run against any customer.

| Field | Type | Notes |
|---|---|---|
| `Id` | int | PK |
| `NameTranslateKey` | string | Translation key used as `featureName` in results |
| `SQL` | string | Raw SQL query executed against the database |

### SalesInfoQueryDto
API transfer object for both read and write operations.

| Field | Type | Notes |
|---|---|---|
| `id` | int | PK (absent on create) |
| `nameTranslateKey` | string | Required |
| `sqlQuery` | string | Required |

---

## 3. SuperAdminSalesInfoController Endpoints

Route: `api/SuperAdminSalesInfo/[action]`  
Auth: Bearer + SuperAdmin

| Endpoint | Method | Parameters | Returns | Notes |
|---|---|---|---|---|
| `SalesInfos` | GET | `customerId` (required, ≠0) | `ICollection<SalesInfo>` | Runs all active queries against the given customer; 400 if `customerId = 0` |
| `SalesInfoQueries` | GET | — | `ICollection<SalesInfoQueryDto>` | Returns all defined query templates |
| `SalesInfoQuery` | POST | `SalesInfoQueryDto` body | `int` (new id) | Creates new query; 400 on service failure |
| `SalesInfoQuery/{id}` | PUT | `SalesInfoQueryDto` body | 200 OK | Updates existing query; 400 on failure |
| `SalesInfoQuery/{id}` | DELETE | `id` path | 200 OK | Deletes query |

---

## 4. UI Components

### `sales-info.component` (SuperAdmin Settings)

**Location:** `super-administration/super-admin-settings/sales-info/`  
**Purpose:** Admin-managed CRUD table for `SalesInfoQueryDto` objects.

| Feature | Detail |
|---|---|
| Table | PrimeNG editable table—inline row editing with cancel support |
| Fields | `nameTranslateKey` (text input) + `sqlQuery` (textarea) |
| Validation | Both fields required; shows toast error if empty |
| Create | Adds a blank row at top; POST on confirm |
| Update | Clone-before-edit pattern; PUT on save, original restored on cancel |
| State | `SalesInfoService` BehaviorSubject state (caches queries across navigations) |

### `sales-infos-dialog-content.component` (Customer Detail Dialog)

**Location:** `super-administration/customers/super-customer-detail/sales-infos-dialog-content/`  
**Purpose:** Shows a per-customer feature checklist dialog.

| Feature | Detail |
|---|---|
| Input | `salesInfos: SalesInfo[]` + `customerName: string` (set by parent) |
| Rendering | List of `bi-indicator-icon` + `featureName` per `SalesInfo` item |
| Icon | green pi-check if `hasFeature`; red pi-times if not |

---

## 5. Service (Angular)

### `SalesInfoService` (BiStore-based)

**State:**
```ts
{
  customer2SalesInfos: { [customerId: number]: SalesInfo[] };  // per-customer cache
  salesInfoQueries: SalesInfoQueryDto[];                        // global cache
}
```

**Cache pattern:**
- `getSalesInfos(customerId)` — returns cached if already loaded, else HTTP GET
- `getSalesInfoQueries()` — returns cached if `length > 0`, else HTTP GET

**Mutations:**
- `createSalesInfoQuery(dto)` → POST, adds to `salesInfoQueries` state, assigns returned `id`
- `updateSalesInfoQuery(dto)` → PUT, patches matching item in `salesInfoQueries` state in-place
- `deleteSalesInfoQuery(id)` → DELETE, removes from `salesInfoQueries` state

---

## 6. Flow

```
CONFIGURE (SuperAdmin Settings → SalesInfo tab)
  GET /SuperAdminSalesInfo/SalesInfoQueries → table of named SQL queries
  Admin creates/edits/deletes queries:
    POST /SuperAdminSalesInfo/SalesInfoQuery → new named SQL check
    PUT /SuperAdminSalesInfo/SalesInfoQuery/{id} → update
    DELETE /SuperAdminSalesInfo/SalesInfoQuery/{id} → remove

CONSUME (Customer Detail → SalesInfo dialog)
  GET /SuperAdminSalesInfo/SalesInfos?customerId={id}
    → Runs all active SQL queries against customer
    → Returns SalesInfo[] (featureName + hasFeature per query)
  Dialog shows feature checklist with green/red indicators
```

---

## 7. Key Rules

1. **SuperAdmin only:** Both `Bearer` + `SuperAdmin` policies required.
2. **Raw SQL queries:** `SalesInfoQuery.SQL` is raw SQL — admin must know the database schema.
3. **Language-sensitive:** `SalesInfos(customerId)` passes `_workContext.CurrentUser.LanguageId` to service — `featureName` respects current localization.
4. **customerId=0 is invalid:** Controller returns 400 Bad Request (guard in endpoint body).
5. **Cache per customer:** Angular service caches `SalesInfo[]` per customerId — no re-fetch on re-open unless service is re-instantiated.
6. **Queries required fields:** Both `nameTranslateKey` and `sqlQuery` must be non-empty — enforced client-side with toast notification.
7. **Overlap with pipeline_crm:** Both domains share ProspectDto and Salesforce entities; `pipeline_sales` uniquely owns the `SalesInfoQuery`/`SalesInfo` subsystem.
