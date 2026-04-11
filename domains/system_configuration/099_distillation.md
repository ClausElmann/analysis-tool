# Domain Distillation: system_configuration

**STATUS:** APPROVED_BASELINE  
**Completeness source:** 0.94 (Layer 1) + UI verification  
**UI verified from:** `super-admin-settings.component.ts`, `packages-setup.component.html`, `super-admin-functions.component.html`  
**Date:** 2026-04-11  

---

## PURPOSE

This domain provides two things: a central runtime configuration store for the entire application, and a superAdmin control panel for operational management. All credentials, feature flags, delivery provider keys, and system behaviour toggles are stored in one place and accessed through a single read-through cache. The control panel exposes the ability to change any of these values live, clear server caches, trigger administrative operations, and configure which capabilities are available per country.

---

## CORE CONCEPTS

1. **Application Setting** — a named key-value pair stored in the database. Every configurable behaviour, credential, threshold, and feature flag is represented as one of these. Values are strings; the system interprets them as booleans, numbers, or lists depending on context.

2. **AppSetting key** — a hard-coded identifier (defined in code as an enum, with the enum's numeric value matching the row ID in the database). You cannot add or rename keys at runtime — they are defined in code and auto-provisioned at startup.

3. **Read-through cache** — all settings are loaded into memory as a single block on the first read. Every subsequent read in that server instance is served from memory. The cache is invalidated (fully cleared) whenever any single setting is saved.

4. **Emergency kill-switches** — two settings that, when enabled, immediately stop all outgoing message delivery system-wide: one for broadcasts, one for system-generated messages. These are the highest-priority operational controls.

5. **File type registry** — a separate lookup table listing every allowed file extension with its MIME type and icon. Any file upload across the system is validated against this allowlist. An unrecognised extension = rejected upload.

6. **Identifier types** — a country-level configuration defining what kind of owner identifier is used per country (e.g. Norwegian organisation number, Danish CVR number, Finnish Y-number). Used in address/owner lookup flows.

7. **Azure infrastructure config** — blob storage containers and Key Vault are part of the system configuration landscape. Each container has a dedicated purpose (logs, batch executable, certificates, import files, profile storage, error logs).

---

## CAPABILITIES

1. Read any configuration value at runtime via the cached accessor (used throughout the system on every request).
2. Read a configuration value bypassing the cache (used in the admin UI to show the live database value).
3. Save a configuration value — updates the database and immediately invalidates the full in-memory cache.
4. Auto-provision all expected settings on startup — any setting not yet in the database is inserted with a safe default value. Safe to run repeatedly; never overwrites existing values.
5. View and edit all application settings grouped in the superAdmin Settings panel (packages tab).
6. Configure which capability packages (ProfileRoleGroups) are available per country — select country, select package, assign roles via grouped checkboxes.
7. Configure which ProfileRoles are available per country (ProfileRoleCountryMapping tab).
8. Configure which UserRoles are available per country (UserRoleCountryMapping tab).
9. View and edit sales information (SalesInfo tab).
10. Clear the in-memory cache of the main app server (immediate effect on next request).
11. Clear the in-memory cache of the API server separately.
12. Trigger instant recalculation of SMS statistics for a specific period.
13. Delete all standard receivers on a selected customer (irreversible admin-level operation).
14. Toggle the global broadcast kill-switch on/off (DisableAllBroadcasts) — UI panel turns red when active.
15. Validate uploaded files against the file type allowlist.

---

## FLOWS

### 1. Application Startup
Application starts → `CreateDefault()` runs → any AppSetting key not yet in the database gets a row inserted with a safe default → first request that reads a setting loads ALL settings at once into the memory cache → all subsequent reads are served from cache.

### 2. Admin Changes a Setting
SuperAdmin navigates to Settings UI → each field calls `GetUncached()` to show the current live database value (not stale cache) → admin edits a value and saves → `Save(key, value)` called → database row updated → entire cache invalidated → next read reloads all settings from database.

### 3. File Upload Validation
A file upload arrives (profile storage, data import, etc.) → extension extracted from filename → `FileTypeIdFromExtension(ext)` called → if the extension is in the allowlist, the associated FileType ID is returned and stored with the file metadata → if not in the allowlist, the file is rejected immediately.

### 4. Kill-Switch Toggle
SuperAdmin opens the Functions panel → the `DisableAllBroadcasts` setting is loaded and displayed as a toggle switch → admin flips the toggle → `Save(DisableAllBroadcasts, true/false)` called → cache cleared → all broadcast delivery code checks this setting before dispatching any message → if true, no messages leave the system.

---

## RULES

1. All credentials (API keys, delivery provider tokens, batch account details, SMTP keys) are stored as AppSettings only — never hardcoded anywhere in the codebase.
2. The AppSetting enum (in code) defines the full set of valid keys. The enum's numeric value IS the row ID. You cannot add free-text keys at runtime.
3. `CreateDefault()` is idempotent — safe to run on every application start. It only inserts missing rows; it never overwrites values already set.
4. The cache loads all settings at once (one cache entry for the entire table). Saving one setting invalidates all of them together.
5. Admin UI must use `GetUncached()` — reading via the cached accessor in admin UI would show potentially stale values and mislead operators.
6. `DisableAllBroadcasts` and `DisableAllSystemMessages` are checked before any message delivery path. If either is true, nothing sends — no exceptions.
7. File extension matching is case-insensitive. Unknown extension = upload rejected, no fallback.
8. IdentifierTypes are country-specific — the allowed identifier format for property/owner lookups depends on which country the profile is in.
9. Database conventions: table names plural PascalCase, column names camelCase, no FK constraints, no cascading deletes, all timestamps UTC.
10. Azure Blob Storage containers have fixed, purpose-specific names. `profilestorage` = user file uploads. `profileimports`/`customerimports`/`importedfiles` = data import routing. `errorlogs` = Dapper and SendGrid error captures.

---

## EDGE CASES

1. If a setting key is added to the enum in code but the application is not restarted, `CreateDefault()` won't have run — the row won't exist, and `Get()` will return the `defaultSetting` fallback passed by the caller.
2. Clearing the cache on the APP server does not clear the API server's cache — they are independent. The UI provides separate buttons for each.
3. The kill-switch panel turns visually red in the UI when broadcasts are disabled — this is a visual safety signal to prevent leaving it on by accident.
4. Deleting all standard receivers on a customer from the Functions panel is irreversible — no confirmation step is visible in the UI beyond the button label.
5. Package-to-country assignment affects which packages are offered when creating new profiles in that country — changing this does not retroactively change existing profiles.

---

## GAPS

1. **AppSetting enum is incomplete in Layer 1** — only ~22 notable keys are captured; the actual enum has 50+ keys. Non-captured keys include all gateway-specific settings, country-specific feature flags, and notification throttling parameters.
2. **No UI for file type management** — `FileTypes` table exists and is used for upload validation, but there is no visible admin UI to add or remove allowed file types. This may be database-only, or the UI may be in a location not yet mapped.


---

## UI-lag: features/administration/super-administration (269 filer)

**Domæne(r):** system_configuration + Finance + customer_management + Enrollment + Monitoring + positive_list + integrations  
**Kun tilgængeligt for: Super Admin brugere**  
**Modul:** `super-administration.module.ts`

### Overordnet struktur (17 under-sections)

---

### bi-log/ (3 filer)
**BiLogComponent** — Viser system-logfiler (events, fejl) til super-admin debugging.

---

### communication/ (21 filer)
- **CommunicationComponent** — Container. Tabs: Driftsmeddelelser / Email-nyhedsbrev / Webinarer
- **OperationalMessagesComponent** — CRUD driftsmeddelelser (`OperationalMessagesService`)
- **EmailNewsletterComponent** — Compose og send nyhedsbrev til kunder via email
- **CreateNewsletterComponent** — Opret ny newsletter (emne, indhold, modtagere)
- **ViewNewsletterComponent** — Forhåndsvisning af newsletter

---

### customers/ (57 filer)
Den største sektion. Fuld kundeoversigt + detaljehåndtering.

- **SuperCustomersMainComponent** — Liste over alle kunder (alle lande, filter, søg, opret ny)
- **SuperCustomersDetailComponent** — Detaljer for én kunde med tabs:
   - `SuperCustomerSettingsComponent` — Rediger kundeindstillinger
   - `SuperCustomerInvoiceDataComponent` / `SuperCustomerInvoicesComponent` — Fakturaoplysninger
   - `SuperCustomerApiKeysComponent` + `CreateApiKeyDialogComponent` — API-nøgler
   - `SuperCustomerFtpSettingsComponent` — FTP-indstillinger
   - `SuperCustomerGdprAcceptComponent` — GDPR-accept status
   - `SuperCustomerContactPersonsComponent` + `SuperCustomerContactPersonsTableComponent` + `ContactPersonsCreateEditComponent` — Kontaktpersoner
   - `SuperCustomerAdminLogsComponent` — Admin-log for kunden
   - `CustomerNotesComponent` + `CustomerNotesTableComponent` — Interne noter
   - `CustomerDataOverviewComponent` — Dataoversigtfor kunden (priser, forbrugstæller mv.)
   - `SuperProfilesComponent` + `SuperProfilesSelectionComponent` — Profiler for kunden
   - `PackagesSetupComponent` — Pakke-/rettigheds-opsætning for kunden
   - `ProfileRoleCountryMappingComponent` + `UserRoleCountryMappingComponent` — Land-specifikke rolle-mappings
   - `CustomerKrrRequestsComponent` + `KrrKofuviStatisticsComponent` — KRR (norsk kontaktregister) forespørgsler og statistik
   - `MunicipalitySetupComponent` — Kommuneopsætning for kunden
   - `DataImportConfigurationsTableComponent` + `DataImportConfigurationColumnMappingsComponent` — Import-konfigurationer admin
- **CreateCustomerComponent** — Opret ny kunde
- **CustomersMapComponent** — Geokort med alle kunder (Leaflet)
- **SuperAdminFunctionsComponent** — Diverse super-admin funktioner (cache-reset, test-mode etc.)
- **CreateEditDataProcessorAgreementComponent** + **DataProcessorAgreementsComponent** — GDPR databehandleraftaler

---

### enrollment/ (11 filer)
- **EnrollmentMainComponent** — Container. Tabs: Statistik / Rapporter / Senders
- **EnrollmentStatisticsComponent** — Enrollment statistik (grafisk + tabel)
- **EnrollmentReportsComponent** — Download enrollment rapporter
- **SendersMainComponent** / **CreateEditSenderComponent** — CRUD over senderenheder (afsendere) til enrollment

---

### humanresource/ (19 filer)
Intern HR-modul (kun tilgængeligt for interne medarbejdere).
- **HumanresourceMainComponent** — Tabs: Medarbejdere / Kørsel / Fravær / Ferier / Lønoversigt
- **EmployeesComponent** — Medarbejderliste
- **DrivingsComponent** — Kørselsgodtgørelser
- **AbsencesComponent** — Fraværsregistrering
- **HolidaysComponent** — Ferieoversigt
- **SalaryOverviewComponent** + **SalaryPeriodInfoDialogComponent** — Lønoversigt og lønperioder

---

### inbound-call-redirect/ (1 fil)
**InboundCallRedirectComponent** — Opsætning af indgående opkald-viderestilling.

---

### internal-reports/ (18 filer)
- **InternalReportsMainComponent** — Tabs: Nudging rapport / Webinar rapport
- **NudgingReportComponent** — Rapport over bruger nudging-svar
- **WebinarReportComponent** — Rapport over webinar-deltagelse

---

### invoicing/ (31 filer)
Fakturering og økonomi (`InvoicingService`).
- **InvoicingMainComponent** — Container med tabs
- **InvoicingLoadInvoicesComponent** — Hent fakturaer fra e-conomic
- **InvoicingAccrualComponent** + **InvoicingAccrualSummaryComponent** + **InvoicingEditAccrualComponent** — Periodisering
- **InvoicingBudgetFollowUpComponent** + **InvoicingBudgetFollowUpMappingComponent** — Budgetopfølgning
- **InvoiceExportComponent** + **InvoiceFramwebExportComponent** — Export til e-conomic / Framweb
- **InvoicingProductCatalogComponent** + **InvoicingProductCatalogDialogComponent** — Produktkatalog
- **InvoicingUploadComponent** — Upload fakturadata
- **SuperCustomerInvoicesComponent** — Kunderegnskab overblik

---

### map-layers/ (9 filer)
- **MapLayersMainComponent** — Liste over alle kort-lag
- **MapLayersDetailComponent** — Detaljer og tilpasning af et kort-lag
- **MapLayersAccessComponent** + **MapLayersAddAccessComponent** — Profiladgang til kort-lag (`MapAdministrationService`)

---

### monitoring/ (20 filer)
- **MonitoringDashboardComponent** — Live dashboard: job-status, køer, server-helse
- **MonitoringJobsComponent** + **ActiveJobComponent** + **TaskDetailsDialogContentComponent** — Job-oversigt og detaljer
- **MonitoringGraphComponent** — Tidsseriegraf over systemperformance
- **MonitoringMapComponent** — Geodistribution af aktivitet

---

### phonenumber-import/ (10 filer)
- **PhonenumberProviderMainComponent** — Tabs: Provider-liste / Import-liste
- **PhonenumberProviderListComponent** + **VirtualPhoneNumbersComponent** — Telefonnummer-udbydere og virtuelle numre
- **PhonenumberImportListComponent** — Import-historik og status

---

### pos-lists/ (23 filer)
Positive List super-admin (`PosListService`).
- **PosListsComponent** — Liste over profiler med positive lister
- **PoslistDataImportComponent** + **PoslistDataImportSettingsComponent** — Import af positive lister
- **UploadedPosListsComponent** + **PosList_FtpUploadsComponent** — Upload og FTP-filer
- **AdditionalImportAddressesComponent** — Manuelle tillægsadresser
- **ImportCorrectionsComponent** + **ImportFofCorrectionsComponent** — Import-korrektioner (standard + FoF-format)
- **LookupSwedishSkipListComponent** — Svensk udeladelses-liste opslag
- **NegativeListComponent** — Negativ liste (adresser der udelades)
- **PositiveLookupComponent** — Opslag i positiv liste
- **ProfilePositiveListFtpSettingsTableComponent** + **StdReceiverGroupFtpSettingsTableComponent** — FTP-indstillinger for profiler og grupper
- **DifiCodeStatisticsComponent** — DIFI-kode statistik (norsk)

---

### salesforce/ (17 filer)
CRM-integration med Salesforce.
- **SalesforceMainComponent** — Tabs: Development / Forecast / Modified / Pipeline / Opportunities + SalesInfo
- **SalesforceDevelopmentComponent** — Udviklingsvisning af Salesforce-data
- **SalesforceForecastEvaluationComponent** — Forecast evaluering
- **SalesforceModifiedComponent** — Nyligt ændrede records
- **SalesforcePipelineComponent** — Pipeline grafik
- **SalesforceOpportunitiesComponent** + **SalesforceOpportunitiesTableComponent** — Kundeopportuniteter
- **SalesInfoComponent** + **SalesInfosDialogContentComponent** — Sales-info panel

---

### super-admin-settings/ (13 filer)
- **SuperAdminSettingsComponent** — Global system-indstillinger
- **FailedAdLoginsComponent** — Log over fejlede AD-logins
- **ProfileRoleCountryMappingComponent** — Lande-specifikke profilrolle-mappings (global)

---

### translation-management/ (3 filer)
**TranslationManagementComponent** — Super-admin oversættelses-administration (oversæt UI tekster per sprog).

---

### users/ (10 filer)
- **SuperUsersMainComponent** — Container: Tabs: Brugere / Roller
- **SuperUsersComponent** — Liste over ALLE brugere i systemet (på tværs af kunder)
- **SuperUsersIndexComponent** — Indeks/søgeside for brugere
- **UserRoleCountryMappingComponent** — Country-based user-rolle mappings


---

## UI-lag: features/administration/super-administration (269 filer)

**Domæne(r):** system_configuration + Finance + customer_management + Enrollment + Monitoring + positive_list + integrations  
**Kun tilgængeligt for: Super Admin brugere**  

### Overordnet struktur (17 under-sections)

- **bi-log/** — System log visning
- **communication/** (21) — Driftsmeddelelser, Email-nyhedsbreve, webinarer
- **customers/** (57) — Fuld kundeoversigt + detaljer: settings, fakturaer, API-nøgler, FTP, GDPR, kontaktpersoner, noter, dataoversigt, profiler, pakker, KRR, kommuner, dataImport-konfigurationer, kundeaftalear, kortvisning
- **enrollment/** (11) — Enrollment statistik, rapporter, senders CRUD
- **humanresource/** (19) — Intern HR: medarbejdere, kørsel, fravær, ferier, lønoversigt
- **inbound-call-redirect/** (1) — Viderestilling af indgående opkald
- **internal-reports/** (18) — Nudging-rapport, webinar-rapport
- **invoicing/** (31) — Fakturering: e-conomic, periodisering, budgetopfølgning, produktkatalog, export
- **map-layers/** (9) — Kortlag admin og profiladgang
- **monitoring/** (20) — Live dashboard, job-oversigt, performance graf, geo-kort
- **phonenumber-import/** (10) — Telefon-nummer udbydere + import
- **pos-lists/** (23) — Positiv liste admin: import, FTP-upload, korrektioner, lookup, negativ liste
- **salesforce/** (17) — Salesforce CRM: pipeline, forecast, opportunities, sales-info
- **shared/** (1) — Delt komponent
- **super-admin-settings/** (13) — Globale systemindstillinger, fejlede AD-logins, landekortlægning
- **translation-management/** (3) — UI-oversættelses-administration
- **users/** (10) — Alle brugere i systemet, super-user-roller

Detaljeret komponent-liste: Se kodereferencerne ovenfor.
