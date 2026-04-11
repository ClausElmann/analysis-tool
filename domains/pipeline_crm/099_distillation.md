# pipeline_crm — Distillation

**Authority Layer:** Layer 1 (Derived Conceptual SSOT)
**Source-primary:** ServiceAlert.Web PipelineController + SalesforceController
**Status:** Distilled

---

## 1. Domain Purpose

SuperAdmin-only CRM pipeline for managing prospects through their entire sales-to-onboarding lifecycle. A **Prospect** is a pre-customer entity that tracks a potential customer from first contact through Salesforce pipeline management, contract generation, e-conomic customer creation, and final conversion to a live `Customer` record.

**Key rule:** All endpoints in both `PipelineController` and `SalesforceController` are gated behind `[Authorize(UserAuthenticationPolicyNames.SuperAdmin)]`. Hosted in `ServiceAlert.Web`. Route pattern: `api/[controller]/[action]`.

---

## 2. Core Entities

### ProspectDto
Central entity representing a pre-customer during sales/onboarding.

| Field | Type | Notes |
|---|---|---|
| Id | int | PK |
| Name | string | Must be unique; 409 Conflict on duplicate in UpdateProspect |
| CountryId | int | Nordic country filter |
| KvhxAddress | string | Property address identifier |
| DateCreatedUtc | DateTime | Created timestamp |
| DateDeletedUtc | DateTime? | Soft delete marker |
| IsArchived | bool | Archived flag |
| ContactPersons | ProspectContactPersonDto[] | Contact persons (copied to Customer on conversion) |
| Products | ProspectProductDto[] | Products (cloned to Customer via CopyProspectProductsToCustomer) |
| ProcessTasks | ProspectTaskDto[] | Onboarding milestone tasks (type=Implementation) |
| ProspectAccount | ... | Account/billing info |
| ProspectUserRoles | ... | Role access configuration |
| CustomerId | int? | Linked customer Id after conversion |

### ProspectTaskDto
Auto-created from templates when a Prospect is created. Tracks onboarding milestones.

- **TaskType:** Implementation (sales pipeline tasks)
- Each task has a completion state; some are completed programmatically (e.g., `CreateEconomicCustomer` marks the e-conomic task complete)

### UpdateProspectCommand
Partial update payload for `UpdateProspect` — updates mutable fields on an existing prospect.

### UpdateProspectWithCustomerIdCommand
Links a Prospect to a real Customer entity + syncs ContactPersons:
- Sets `CustomerId` on the Prospect
- Copies `ContactPersons` from Prospect to the actual Customer record

### CloneProspectProductsToCustomerCommand
Parameters for `CopyProspectProductsToCustomer`:
- `ProspectId` → source
- `CustomerId` → target
Copies all ProspectProductDto items to the Customer's product configuration.

### CustomerWithTasksDto
Alternative DTO returned by GetProspectsWithTasks — includes the ProcessTasks list alongside the prospect root.

---

## 3. PipelineController Endpoints

Route: `api/Pipeline/[action]`

| Endpoint | Method | Parameters | Returns | Notes |
|---|---|---|---|---|
| `GetProspects` | GET | `countryId`, `inclDeleted`, `inclArchived` | `IEnumerable<ProspectDto>` | Includes Products; no tasks |
| `GetProspectsWithTasks` | GET | `countryId?`, `inclDeleted`, `inclArchived` | `IEnumerable<CustomerWithTasksDto>` | Includes ProcessTasks (type=Implementation) |
| `GetProspect` | GET | `id` | `ProspectDto` | Single by id |
| `GetProspectWithTasks` | GET | `id` | `CustomerWithTasksDto` | Single with tasks |
| `GetProspectCustomerContacts` | GET | `prospectId` | contact list | Customer contact persons for prospect |
| `GetProspectUserRoleAccess` | GET | `prospectId` | `UserRoleAccessModel[]` | Which user roles get access when converted |
| `CreateProspect` | POST | `ProspectDto` body | created entity | Also creates ProcessTasks from templates + contract + user role mappings |
| `UpdateProspect` | POST | `UpdateProspectCommand` body | updated entity | 409 on name conflict |
| `DeleteProspect` | POST | `id` | — | Soft delete (sets DateDeletedUtc) |
| `ArchiveProspect` | POST | `id` | — | Sets IsArchived flag |
| `CreateEconomicCustomer` | POST | `prospectId` | — | Async: creates customer in e-conomic billing system; marks "CreatedInEconomic" process task complete |
| `UpdateProspectWithCustomerIdAndAddContactPersonsToCustomer` | POST | `UpdateProspectWithCustomerIdCommand` | — | Links prospect to real customer; syncs ContactPersons |
| `GetContractWord` | GET | `customerId` | Word DOCX file | Returns F24-template contract as file download |
| `CopyProspectProductsToCustomer` | POST | `CloneProspectProductsToCustomerCommand` | — | Clones prospect products to customer |

---

## 4. Salesforce Integration (SalesforceController)

Route: `api/Salesforce/[action]`

Salesforce CRM opportunities are synced into the system and exposed via read-only analytics endpoints. All data comes from `ISalesforceService` / `ISalesforceRepository`.

### SalesforceOpportunityDto
Core Salesforce opportunity entity mirrored locally. Has at minimum:
- `opportunityId` (Salesforce Id)
- `countryId`, `closeDateUtc`
- Pipeline/forecast metrics

### SalesforceOpportunityHistoryDto
History/change log for a single Salesforce opportunity (audit trail of stage changes).

### Salesforce Endpoints

| Endpoint | Method | Parameters | Returns | Notes |
|---|---|---|---|---|
| `GetAllSalesforceOpportunities` | GET | `countryId?`, `fromCloseDateUtc?`, `toCloseDateUtc?` | `IEnumerable<SalesforceOpportunityDto>` | Flat list; `inclDeleted=false` |
| `GetAllSalesforceOpportunityHistoriesWithChanges` | GET | `opportunityId` | `IEnumerable<SalesforceOpportunityHistoryDto>` | All history entries with stage changes |
| `GetForecastEvaluationOpportunities` | GET | `forecastMonthDateUtc`, `closeMonthDateUtc`, `countryId?` | `ForecastEvaluationOpportunitiesDto` | Splits into `{Positive, Negative}` lists for a given forecast/close month pair |
| `GetPipelineOpportunities` | GET | `startMonth`, `noOfmonths`, `countryId?` | `ForecastEvaluationOpportunitiesDto` shape | Opportunities closing in a date window starting next month, spanning N months |
| `GetOpportunitiesDevelopment` | GET | `month`, `countryId?` | `DevelopmentOpportunitiesDto` | Splits into `{Created, ClosedLost, ClosedWon}` for given month |
| `GetLastModifiedOpportunities` | GET | `month`, `countryId?` | `IEnumerable<SalesforceOpportunityDto>` | Opportunities last-modified in given month |

### Composite DTOs
- `ForecastEvaluationOpportunitiesDto` = `{ Positive: SalesforceOpportunityDto[], Negative: SalesforceOpportunityDto[] }`
- `DevelopmentOpportunitiesDto` = `{ Created: [], ClosedLost: [], ClosedWon: [] }`

**Month encoding:** Both controllers convert `DateTime` to `yyyyMM` int for service layer queries (`forecastMonth = year × 100 + month`).

---

## 5. Prospect Lifecycle Flow

```
1. SALESFORCE PIPELINE
   Opportunities sync into Salesforce tables (external CRM data)
   SalesforceController exposes pipeline/forecast analytics

2. PROSPECT CREATION
   CreateProspect(ProspectDto)
     → New Prospect record
     → ProcessTasks auto-created from templates (TaskType.Implementation)
     → Contract created
     → UserRole access mappings created

3. ONBOARDING TASKS
   GetProspectWithTasks → shows task completion state
   CreateEconomicCustomer → billing system setup (e-conomic)
     → marks "CreatedInEconomic" process task done

4. CONTRACT
   GetContractWord(customerId) → Word DOCX download (F24 template)

5. CUSTOMER CONVERSION
   UpdateProspectWithCustomerIdAndAddContactPersonsToCustomer
     → Links Prospect.CustomerId = realCustomer.Id
     → Syncs ContactPersons to customer
   CopyProspectProductsToCustomer
     → Clones product configuration to customer

6. ARCHIVE/DELETE
   ArchiveProspect → IsArchived = true
   DeleteProspect → DateDeletedUtc = now (soft delete)
```

---

## 6. Key Rules

- **Auth:** Both controllers are SuperAdmin-only — no customer-facing access.
- **Hosting:** `ServiceAlert.Web` (not BalarmWebApp, not ServiceAlert.Api).
- **Name uniqueness:** `UpdateProspect` returns 409 Conflict on name collision.
- **Soft delete:** `DeleteProspect` never hard-deletes; sets `DateDeletedUtc`.
- **Async e-conomic:** `CreateEconomicCustomer` is async (fire-and-forget background); returns immediately.
- **Salesforce read-only:** No write endpoints for Salesforce — data is synced externally; API only reads.
- **Month encoding:** Service layer uses `yyyyMM` int for month-based queries.

---

## 7. Integration Points

| Integrated System | Direction | How |
|---|---|---|
| Salesforce CRM | Inbound sync | `ISalesforceService/ISalesforceRepository` — external job syncs opportunities |
| e-conomic | Outbound | `CreateEconomicCustomer` → async background task |
| Customer domain | Outbound | `UpdateProspectWithCustomerIdAndAddContactPersonsToCustomer` links to customer record |
| Finance/Subscription domain | Outbound | `CopyProspectProductsToCustomer` seeds customer product config |
| Reporting domain | Read path | `GetContractWord` generates Word contract for sales onboarding |
