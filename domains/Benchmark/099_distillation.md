# Domain Distillation — Benchmark

**Status:** APPROVED_BASELINE  
**Completeness score (Layer 1):** 0.4667  
**Evidence:** Layer 1 partial + full UI source (benchmark-create-edit, benchmark-index, benchmark-overview, benchmark-kpis, benchmark-statistics, benchmark-causes, benchmark-settings, benchmark-message-part, benchmark-routing)

---

## 1. Core Concept

`Benchmark` is the domain for tracking and analyzing supply interruption events (outages). Each benchmark record captures a real-world supply outage with classification data (supply type, category, cause), timing, and project references. The domain provides KPI dashboards, period comparison statistics with map view, and a message wizard integration for notifying about outages.

---

## 2. Domain Model

### `BenchmarkModel` — Core Record
| Field | Type | Notes |
|---|---|---|
| `id` | number | |
| `supplyType` | `BenchmarkSupplyType` | Required — electricity, water, gas, etc. |
| `category` | `BenchmarkCategory` | Required if supply type selected; filtered by supply type |
| `cause` | `BenchmarkCauseModel` | Optional; not shown in InfoPortal mode |
| `fromDate` + `fromTime` | string | Start of outage |
| `estToDate` + `estToTime` | string | Estimated end of outage |
| `projectId` | string | max 50 chars; supports merge fields inserted via cursor |
| `note` | string | Free text |

### `BenchmarkMetadataModel`
Status and metadata for a benchmark record (e.g. active/finished state, year, municipality).

### `BenchmarkInfoportalEntry`
Variant model for InfoPortal benchmarks — replaces `cause` with `infoPortalCause` (string) and `infoPortalComment` (string). Uses same `benchmark-create-edit` component but in InfoPortal mode.

### Reference Lists
- `BenchmarkSupplyType[]` — available supply types (filterable)
- `BenchmarkCategory[]` — categories filtered by supply type via `supplyTypeFilter` pipe
- `BenchmarkCauseModel[]` — causes filtered by supply type via `supplyTypeFilter` pipe

---

## 3. Routes (benchmark module)

| Route | Component | Notes |
|---|---|---|
| `index` | `BenchmarkIndexComponent` | List with date filter + active count warning |
| `createMain` | `BenchmarkCreateEditMainComponent` | Create new benchmark |
| `editMain/:id` | `BenchmarkCreateEditMainComponent` | Edit existing benchmark |
| `statistics` | `BenchmarkStatisticsComponent` | Two-period comparison (lazy-loaded) |
| `kpis` | `BenchmarkKpisComponent` | KPI tables + charts (lazy-loaded) |
| `causes` | `BenchmarkCausesComponent` | Cause management (lazy-loaded) |
| `overview` | `BenchmarkOverviewComponent` | Aggregated table/chart view |
| `settings` | `BenchmarkSettingsComponent` | Configuration (lazy-loaded) |

---

## 4. Component Behaviors

### `benchmark-index` — Benchmark List
- Date range filter (fromDate / toDate)
- Radio toggle: Show Unfinished / Show Finished benchmarks
- Active benchmarks warning: if incomplete benchmarks exist since year start → shows count + `ShowAll` shortcut
- Row actions: navigate to edit
- `finish-benchmark-dialog` — marks benchmark as finished (changes active → finished)

### `benchmark-create-edit` — Shared Create/Edit Form
Shared component used in wizard and standalone create/edit contexts.

**Form fields:**
- SupplyType (dropdown, required; drives category/cause options)
- Category (dropdown, required if supply type set; filtered by `supplyTypeFilter` pipe)
- Cause (dropdown, optional; NOT shown in InfoPortal mode)
- InfoPortal mode only: `infoPortalCause` (text), `infoPortalComment` (text)
- ProjectId (text, max 50; supports merge field insertion)
- Note (textarea)
- FromDate + FromTime (required)
- EstToDate + EstToTime (required)

**Behaviors:**
- Category and cause options load only after supply type is selected (`@if (supplyTypeCtrl.value?.id)`)
- `FinishBenchmarkDialogComponent` launched from within on finish action
- Merge field insertion available in ProjectId field

### `benchmark-overview` — Aggregated Overview

**View controls:**
- Time mode: Monthly / Yearly (radio)
- Data mode: Table / Graph (selectButton)
- Municipality filter (optional dropdown)

**Table mode:**
- Dynamic columns, global filter
- Excel export (client-side)
- Fields: year, monthName, supplyTypeName, categoryName, groupCount, interruptionTimePerBBR

**Graph mode:**
- Supply type selector + year selector (for monthly mode)
- Bar chart rendered via `p-chart`
- Download chart as image via `bi-download-chart-button`

### `benchmark-kpis` — KPI Dashboard

Two tables: Yearly KPIs + Monthly KPIs (using shared `tableTemplate`)

KPI table columns: year, month, supplyTypeName, avgDurationAcute, avgDurationPlanned, percentInterruptionsAcute, percentInterruptionsPlanned

**Charts:**
1. Average Duration chart — year + supply type selectors → bar chart → downloadable
2. Over-max Duration chart — bar chart showing count over threshold → downloadable
3. `maxDurationString()` used in labels (configurable threshold)

### `benchmark-statistics` — Period Comparison

**Layout:** Two `bi-accordion` panels — Primary period and Comparison period

Each panel:
- `bi-benchmark-statistics-criteria` — filter criteria (supply type, category, cause, date range)
- Results table: `BenchmarkStatisticsDtoExt[]` with expandable rows
- View mode toggle: Map / Data

**Loading states:** `StatisticTarget.LEFTSTAT` / `RIGHTSTAT` / `ADDRESSES`

**Map view:** `BenchmarkMapStatisticsComponent` with `BiMapComponent` (Leaflet) showing `BiMapMarker[]` at address locations

**Table view:** `BenchmarkStatisticAddressExt[]` in expandable rows — drill down to individual addresses

**Excel export:** Available per statistics panel

---

## 5. Wizard Integration

**`benchmark-message-part`** — Used within the message wizard (`write-message` step) as a wizard step variant:
- Embeds `BenchmarkCreateEditComponent` in non-InfoPortal mode
- Inputs: `profileTypeId` (pre-selects supply type if profile has one), `isInfoPortal`
- Outputs: `showCopyFromEmailTextButton` signal
- Part of `MessagePartComponentBase<IBenchmarkMessagePartData>`
- Pre-populates from `existingData()` when editing an existing benchmark message

---

## 6. Rules

1. Category and cause dropdowns are hidden until a supply type is selected — supply type drives filtering
2. In InfoPortal mode: `cause` field removed; `infoPortalCause` and `infoPortalComment` shown instead
3. Active benchmarks warning uses year-start-to-now window — incomplete benchmarks from prior years not shown
4. KPI `maxDurationString` is a configurable threshold shown in chart titles
5. Overview graph mode requires supply type selection; for monthly mode also requires year selection
6. Statistics map/data toggle is per-panel (left/right independently controlled)
7. Merge fields insertable into ProjectId field via cursor


---

## UI-lag: BenchmarkService (core/services)

**Fil:** `core/services/benchmark.service.ts`  
**Extends:** `BiStore<BenchmarkState>`  
**Domain:** Benchmark

 Indeholder caching via BiStore (categories, causes, supplyTypes, benchmarks, settings, numberOfActiveBenchmarks).

| Metode | Beskrivelse |
|---|---|
| `getCategories()` | Benchmark-kategorier (med profil-type mapping), cached |
| `getCauses()` | Benchmark-årsager, cached |
| `getSupplyTypes()` | Supply types til benchmark, cached |
| `getBenchmarks()` | Alle benchmarks, cached |
| `getSettings()` | Kundens benchmark-indstillinger |
| `getNumberOfActiveBenchmarks()` | Tid-begrænset cache (moment) af antal aktive benchmarks |
| `getOverview(filter)` | Benchmark oversigt med `BenchmarkStatisticsFilter` |
| `getStatistics(...)` | Statistik-data inkl. adresser og KPI'er |
| CRUD for benchmarks, causes, categories, supplyTypes | Standard opret/opdater/slet |

**State reset:** sker automatisk ved `customerChanged$` event.


---

## UI-lag: features/administration/benchmark (6 sider, 29 filer)

**Domæne:** Benchmark  
**Modul:** `benchmark.module.ts` med lazy-loaded routing

### BenchmarkMainComponent (benchmark-main.component.ts)
Container med BiTabs. 6 faner: Rapportering, Statistik, Oversigt, KPI'er, Årsager, Indstillinger.
Badge på "Rapportering" med antal aktive benchmarks (farve: danger).

### Benchmark Index (index/)
**BenchmarkIndexComponent** — Primær liste-visning af benchmarks.
- Fritekst-søgning + dato-filter med `searchForm`
- Tabel over benchmarks med inline opret/rediger flow (`create-edit-main/`)
- "Afslut alle" knap via `extraTableButtonConfigs`
- State husket i `BenchmarkIndexSharedService` (lastFromDate/lastToDate/showFinished)

**BenchmarkIndexSharedService** — Delt state for index-søgeparametre (ingen HTTP, kun in-memory).

**create-edit-main/CreateEditMainComponent** — Inline opret/rediger benchmark-formular:
- Vælg profil, type (SupplyType), årsag (Cause), startdato, varighed
- Opret + gem i `BenchmarkService`

### Benchmark Statistics (statistics/)
**BenchmarkStatisticsComponent** — Statistikvisning med kort og tabel.
- Filter: `BenchmarkStatisticsFilter` (supplyType, category, datointerval)
- 3 loading-states: LEFTSTAT, RIGHTSTAT, ADDRESSES
- Visnings-mode: Map / Data (`ViewModeType`)
- Map: Leaflet-baseret med `BiMapComponent`

**BenchmarkStatisticsCriteriaComponent** — Filterformular til statistik (vælg benchmark + datointerval).

**BenchmarkMapStatisticsComponent** — Ligeledeles statistik men specifikt til kort-visning (adresse-pins + cluster).

**Ext-klasser:**
- `BenchmarkStatisticAddressExt` — frontend extension af statistik-adresse (beregnet felt)
- `BenchmarkStatisticsDtoExt` — extension med beregnet total
- `BenchmarkStatisticsFilter` — interface for filter-kriterier: `{supplyTypeId?, categoryId?, from, to}`

### Benchmark Overview (overview/)
**BenchmarkOverviewComponent** — Graf og tabel over benchmark-oversigt pr. kategori.
- Toggle: månedlig / årlig visning (`TimeViewMode`)
- Toggle: tabel / graf (`DataViewMode`)
- Graf via `ChartModule` (Chart.js)

**BenchmarkOverviewDtoExt** — DTO extension med beregnet kategorinavn inkl. supply type.

### Benchmark KPIs (kpis/)
**BenchmarkKpisComponent** — Viser KPI-data for benchmark (e.g. svarprocenter).
- SupplyType-filter + graf
- `BenchmarkKeyPerformanceIndicatorExt` — extension med supplerende beregnet felt

### Benchmark Causes (causes/)
**BenchmarkCausesComponent** — CRUD over benchmark-årsager (causes).
- Tabel + inline opret/rediger med `InputTextModule` + supply type dropdown
- Viser supply type som `SelectItem<number>`

### Benchmark Settings (settings/)
**BenchmarkSettingsComponent** — Benchmark-indstillinger for kunden.
- `maxDuration` (int) + `closeMessageTemplateId` (select af skabeloner)
- Viser KVHX-statistik via `KvhxCountListComponent`

**KvhxCountListComponent** — Sub-komponent der viser KVHX-tælle-statistik (`BenchmarkKvhxStatisticsDto[]`) som tabel.
