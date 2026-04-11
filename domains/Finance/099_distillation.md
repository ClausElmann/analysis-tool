# Domain Distillation — Finance

**Status:** APPROVED_BASELINE  
**Completeness score (Layer 1):** 0.41  
**Evidence:** Source-primary. UI: invoicing.routes, invoicing-main, invoicing-upload, invoicing-load-invoices, invoicing-budget-follow-up, invoicing-product-catalog, Models/*.ts

---

## 1. Core Concept

`Finance` is the SuperAdmin-only invoicing and financial management domain. It integrates with e-conomic (Danish accounting software), Salesforce (CRM/pipeline), and internal accrual accounting. The domain handles monthly invoice generation, transfer to e-conomic per country (DK/SE/FI), budget follow-up, accruals, and financial data file uploads.

---

## 2. Routes (invoicing module — SuperAdmin only)

| Route | Component | Description |
|---|---|---|
| `economicTransfer` | `invoice-export` | Invoice generation + e-conomic transfer (default) |
| `framwebExport` | `invoice-framweb-export` | FramWeb customer invoice export |
| `loadInvoices` | `invoicing-load-invoices` | Pull latest booked invoices from e-conomic |
| `accrual` | `invoicing-accrual` | Accrual management (period-based deferred revenue) |
| `summary` | `invoicing-accrual-summary` | Accrual reconciliation summary |
| `budgetFollowUp` | `invoicing-budget-follow-up` | Budget vs. actual per company/year/month/costCenter |
| `mappings` | `invoicing-budget-follow-up-mapping` | Cost center mapping configuration |
| `productCatalog` | `invoicing-product-catalog` | Billing product catalog CRUD |
| `upload` | `invoicing-upload` | Financial data file uploads |

---

## 3. e-conomic Integration

**Load Invoices (`invoicing-load-invoices`):**
- Fetches latest booked invoices from e-conomic per country: DK, SE, FI
- Shows: `bookedInvoiceNumber` + `date` per country
- "Fetch New Invoices" button triggers pull

**Invoice Transfer (`invoice-export`):**
- Generates `EconomicReportDTO` per customer
- Transfers to e-conomic via `InvoiceEconomicTransferResult`
- `CustomerEconomicReport` model (frontend): customerId, errorCause, accountEntries, economicTransferResult, revenue, selected, invoiceCycle
- `CustomerAccountEntry`: importedSmsCount, sms, smsVoice, email

**Accrual (`invoicing-accrual`):**
- `BookedInvoiceAccrualDtoExt` — accrual entry per booked invoice
- Period-based deferred revenue tracking

---

## 4. Salesforce Integration

**Upload (`invoicing-upload` — Salesforce tab):**
- Salesforce XLSX upload (single file) → parses Salesforce opportunity data
- `SalesforceOpportunityDtoExt` — opportunity record with financial data
- `SalesforceOpportunityHistoryDtoExt` — change history per opportunity

---

## 5. Financial Data Uploads (`invoicing-upload`)

Three upload types on the same screen:

| Upload Type | File | Multiple | Purpose |
|---|---|---|---|
| Salesforce | .xlsx | No | CRM opportunity data |
| DepartmentBalanceSheet | .xlsx | Yes | Department-level balance sheets |
| BalanceSheet | .xlsx | Yes | Company-level balance sheets |

Each upload uses `bi-file-uploader` component with callback on success.

---

## 6. Budget Follow-Up (`invoicing-budget-follow-up`)

**Filters:**
- Economic export type selector (`economicExports`)
- Company/account (`economicAccounts`)
- Year
- Month
- Cost center

**CSV export:** `bi-excel-button` → CSV download

---

## 7. Product Catalog (`invoicing-product-catalog`)

CRUD for billing products (used in invoice line generation).

**Dialog:** `invoicing-product-catalog-dialog` — Create/edit billing product.

---

## 8. Rules

1. Entire Finance domain is SuperAdmin-only — no customer-level access
2. Invoice transfer to e-conomic is per country (DK/SE/FI) — each country has independent booked invoice tracking
3. `CustomerAccountEntry.importedSmsCount` tracks SMS imported from old system (migration legacy)
4. FramWeb exports are separate from main customer invoices (FramWeb has distinct billing arrangement)
5. Accrual entries are keyed to booked invoice numbers — must match e-conomic records exactly
