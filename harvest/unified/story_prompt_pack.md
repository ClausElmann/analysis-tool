# PROMPT PACK — AI Build Instruction for ServiceAlert GreenAI UI

## Instruktioner til AI-agenten

Du er en expert Blazor Server + MudBlazor 8 UI-builder. Du skal bygge et komplet enterprise UI
baseret på 48 user stories fra ServiceAlert.

**Tech stack:** .NET 10, C# 13, Blazor Server, MudBlazor 8, Dapper, MediatR, xUnit v3

**Vigtigste regel:** Ét vertical slice per user story. Hvert slice er selvstændigt og testbart.

---

## Build-sekvens (prioriteret)

Byg i denne rækkefølge:

### P1 (12 stories)

- **US-001** — Manage Messages (Messaging & Communication)
  - Story: Som bruger vil jeg se og søge i beskeder, oprette beskeder og slette beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.
  - Side: `Pages/messaging/MessagesPage.razor`
  - Verbs: DELETE, GET, POST
- **US-002** — Manage Customers (Customer & Enrollment)
  - Story: Som bruger vil jeg se og søge i kunder, oprette kunder, redigere kunder og slette kunder, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
  - Side: `Pages/customers/CustomersPage.razor`
  - Verbs: DELETE, GET, PATCH, POST, PUT
- **US-005** — Manage Senders (Customer & Enrollment)
  - Story: Som bruger vil jeg se og søge i afsendere, oprette afsendere, redigere afsendere og slette afsendere, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
  - Side: `Pages/customers/SendersPage.razor`
  - Verbs: DELETE, GET, PATCH, POST
- **US-009** — Manage Prospects (Customer & Enrollment)
  - Story: Som bruger vil jeg se og søge i salgsmuligheder, oprette salgsmuligheder, redigere salgsmuligheder og slette salgsmuligheder, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
  - Side: `Pages/customers/ProspectsPage.razor`
  - Verbs: DELETE, GET, PATCH, POST
- **US-012** — Manage Operationals (Messaging & Communication)
  - Story: Som bruger vil jeg se og søge i driftsdata, oprette driftsdata, redigere driftsdata og slette driftsdata, så jeg kan kommunikere effektivt med kunder og modtagere.
  - Side: `Pages/messaging/OperationalsPage.razor`
  - Verbs: DELETE, GET, POST, PUT
- **US-016** — Manage Contacts (Customer & Enrollment)
  - Story: Som bruger vil jeg se og søge i kontakter, oprette kontakter, redigere kontakter og slette kontakter, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
  - Side: `Pages/customers/ContactsPage.razor`
  - Verbs: DELETE, GET, POST, PUT
- **US-019** — Manage Enrollments (Customer & Enrollment)
  - Story: Som bruger vil jeg se og søge i tilmeldinger, oprette tilmeldinger og slette tilmeldinger, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
  - Side: `Pages/customers/EnrollmentsPage.razor`
  - Verbs: DELETE, GET, POST
- **US-020** — Manage Dynamics (Messaging & Communication)
  - Story: Som bruger vil jeg se og søge i dynamiske felter, oprette dynamiske felter, redigere dynamiske felter og slette dynamiske felter, så jeg kan kommunikere effektivt med kunder og modtagere.
  - Side: `Pages/messaging/DynamicsPage.razor`
  - Verbs: DELETE, GET, POST, PUT
- **US-023** — Manage Webs (Messaging & Communication)
  - Story: Som bruger vil jeg se og søge i web-beskeder, oprette web-beskeder og slette web-beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.
  - Side: `Pages/messaging/WebsPage.razor`
  - Verbs: DELETE, GET, POST
- **US-032** — Manage Entries (Messaging & Communication)
  - Story: Som bruger vil jeg se og søge i poster, oprette poster og slette poster, så jeg kan kommunikere effektivt med kunder og modtagere.
  - Side: `Pages/messaging/EntriesPage.razor`
  - Verbs: DELETE, GET, POST
- **US-040** — Manage Warnings (Messaging & Communication)
  - Story: Som bruger vil jeg se og søge i advarsler, oprette advarsler og redigere advarsler, så jeg kan kommunikere effektivt med kunder og modtagere.
  - Side: `Pages/messaging/WarningsPage.razor`
  - Verbs: GET, POST, PUT
- **US-041** — Manage Weathers (Messaging & Communication)
  - Story: Som bruger vil jeg se og søge i vejrdata, oprette vejrdata, redigere vejrdata og slette vejrdata, så jeg kan kommunikere effektivt med kunder og modtagere.
  - Side: `Pages/messaging/WeathersPage.razor`
  - Verbs: DELETE, GET, POST, PUT

### P2 (5 stories)

- **US-024** — Manage Sms (Messaging & Communication)
  - Story: Som bruger vil jeg se og søge i SMS-beskeder og slette SMS-beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.
  - Side: `Pages/messaging/SmsPage.razor`
  - Verbs: DELETE, GET
- **US-034** — Manage Archiveds (Messaging & Communication)
  - Story: Som bruger vil jeg se og søge i arkiverede beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.
  - Side: `Pages/messaging/ArchivedsPage.razor`
  - Verbs: GET
- **US-037** — Manage Status (Messaging & Communication)
  - Story: Som bruger vil jeg se og søge i statusoversigt, så jeg kan kommunikere effektivt med kunder og modtagere.
  - Side: `Pages/messaging/StatusPage.razor`
  - Verbs: GET
- **US-043** — Other Messaging Operations (Messaging & Communication)
  - Story: Som bruger vil jeg arbejde med miscer, så jeg kan kommunikere effektivt med kunder og modtagere.
  - Side: `Pages/messaging/MessagingOperationsPage.razor`
  - Verbs: 
- **US-044** — Other Customer Operations (Customer & Enrollment)
  - Story: Som bruger vil jeg arbejde med miscer, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
  - Side: `Pages/customers/CustomerOperationsPage.razor`
  - Verbs: 

### P3 (31 stories)

- **US-003** — Manage Profiles (User & Access Management)
  - Story: Som bruger vil jeg se og søge i profiler, oprette profiler, redigere profiler og slette profiler, så jeg kan styre brugeradgang og sikkerhed i systemet.
  - Side: `Pages/admin/ProfilesPage.razor`
  - Verbs: DELETE, GET, POST, PUT
- **US-004** — Manage Users (User & Access Management)
  - Story: Som bruger vil jeg se og søge i brugere, oprette brugere, redigere brugere og slette brugere, så jeg kan styre brugeradgang og sikkerhed i systemet.
  - Side: `Pages/admin/UsersPage.razor`
  - Verbs: DELETE, GET, PATCH, POST, PUT
- **US-006** — Manage Benchmarks (Analytics & Reporting)
  - Story: Som bruger vil jeg se og søge i benchmarks, oprette benchmarks, redigere benchmarks og slette benchmarks, så jeg kan få indsigt i systemaktivitet og performance.
  - Side: `Pages/analytics/BenchmarksPage.razor`
  - Verbs: DELETE, GET, PATCH, POST
- **US-007** — Manage Resets (User & Access Management)
  - Story: Som bruger vil jeg oprette nulstillinger, så jeg kan styre brugeradgang og sikkerhed i systemet.
  - Side: `Pages/admin/ResetsPage.razor`
  - Verbs: POST
- **US-008** — Manage Sales (Finance & Operations)
  - Story: Som bruger vil jeg se og søge i salgsdata, oprette salgsdata, redigere salgsdata og slette salgsdata, så jeg kan holde styr på økonomi og driftsprocesser.
  - Side: `Pages/finance/SalesPage.razor`
  - Verbs: DELETE, GET, POST, PUT
- **US-010** — Manage Salaries (Finance & Operations)
  - Story: Som bruger vil jeg se og søge i lønsedler, så jeg kan holde styr på økonomi og driftsprocesser.
  - Side: `Pages/finance/SalariesPage.razor`
  - Verbs: GET
- **US-011** — Manage Absences (Finance & Operations)
  - Story: Som bruger vil jeg se og søge i fraværsregistreringer, oprette fraværsregistreringer, redigere fraværsregistreringer og slette fraværsregistreringer, så jeg kan holde styr på økonomi og driftsprocesser.
  - Side: `Pages/finance/AbsencesPage.razor`
  - Verbs: DELETE, GET, PATCH, POST
- **US-013** — Manage Groups (Address & Data)
  - Story: Som bruger vil jeg se og søge i grupper, oprette grupper og slette grupper, så jeg kan håndtere og validere adressedata korrekt.
  - Side: `Pages/addresses/GroupsPage.razor`
  - Verbs: DELETE, GET, POST
- **US-014** — Manage Corrections (Address & Data)
  - Story: Som bruger vil jeg oprette korrektioner og slette korrektioner, så jeg kan håndtere og validere adressedata korrekt.
  - Side: `Pages/addresses/CorrectionsPage.razor`
  - Verbs: DELETE, POST
- **US-015** — Manage Receivers (Address & Data)
  - Story: Som bruger vil jeg se og søge i modtagere og oprette modtagere, så jeg kan håndtere og validere adressedata korrekt.
  - Side: `Pages/addresses/ReceiversPage.razor`
  - Verbs: GET, POST
- **US-017** — Manage Roles (User & Access Management)
  - Story: Som bruger vil jeg se og søge i roller, oprette roller og redigere roller, så jeg kan styre brugeradgang og sikkerhed i systemet.
  - Side: `Pages/admin/RolesPage.razor`
  - Verbs: GET, POST, PUT
- **US-018** — Manage Invoices (Finance & Operations)
  - Story: Som bruger vil jeg se og søge i fakturaer, så jeg kan holde styr på økonomi og driftsprocesser.
  - Side: `Pages/finance/InvoicesPage.razor`
  - Verbs: GET
- **US-021** — Manage Gdprs (Address & Data)
  - Story: Som bruger vil jeg se og søge i GDPR-håndtering, oprette GDPR-håndtering, redigere GDPR-håndtering og slette GDPR-håndtering, så jeg kan håndtere og validere adressedata korrekt.
  - Side: `Pages/addresses/GdprsPage.razor`
  - Verbs: DELETE, GET, POST, PUT
- **US-022** — Manage Maps (User & Access Management)
  - Story: Som bruger vil jeg se og søge i kortvisning, oprette kortvisning, redigere kortvisning og slette kortvisning, så jeg kan styre brugeradgang og sikkerhed i systemet.
  - Side: `Pages/admin/MapsPage.razor`
  - Verbs: DELETE, GET, POST, PUT
- **US-025** — Manage Causes (Analytics & Reporting)
  - Story: Som bruger vil jeg oprette årsagskoder, redigere årsagskoder og slette årsagskoder, så jeg kan få indsigt i systemaktivitet og performance.
  - Side: `Pages/analytics/CausesPage.razor`
  - Verbs: DELETE, POST, PUT
- **US-026** — Manage Address (Address & Data)
  - Story: Som bruger vil jeg se og søge i adresser, oprette adresser og redigere adresser, så jeg kan håndtere og validere adressedata korrekt.
  - Side: `Pages/addresses/AddressPage.razor`
  - Verbs: GET, POST, PUT
- **US-027** — Manage Stds (Address & Data)
  - Story: Som bruger vil jeg oprette standardindstillinger og slette standardindstillinger, så jeg kan håndtere og validere adressedata korrekt.
  - Side: `Pages/addresses/StdsPage.razor`
  - Verbs: DELETE, POST
- **US-028** — Manage Localizeds (Address & Data)
  - Story: Som bruger vil jeg oprette sprogoversættelser, så jeg kan håndtere og validere adressedata korrekt.
  - Side: `Pages/addresses/LocalizedsPage.razor`
  - Verbs: POST
- **US-029** — Manage Employees (Finance & Operations)
  - Story: Som bruger vil jeg se og søge i medarbejdere og oprette medarbejdere, så jeg kan holde styr på økonomi og driftsprocesser.
  - Side: `Pages/finance/EmployeesPage.razor`
  - Verbs: GET, POST
- **US-030** — Manage Imports (Address & Data)
  - Story: Som bruger vil jeg se og søge i dataimport, oprette dataimport og slette dataimport, så jeg kan håndtere og validere adressedata korrekt.
  - Side: `Pages/addresses/ImportsPage.razor`
  - Verbs: DELETE, GET, POST
- **US-031** — Manage Customers (User & Access Management)
  - Story: Som bruger vil jeg se og søge i kunder, så jeg kan styre brugeradgang og sikkerhed i systemet.
  - Side: `Pages/admin/CustomersPage.razor`
  - Verbs: GET
- **US-033** — Manage Drives (Finance & Operations)
  - Story: Som bruger vil jeg se og søge i fildrev, oprette fildrev og slette fildrev, så jeg kan holde styr på økonomi og driftsprocesser.
  - Side: `Pages/finance/DrivesPage.razor`
  - Verbs: DELETE, GET, POST
- **US-035** — Manage Receivers (User & Access Management)
  - Story: Som bruger vil jeg oprette modtagere, så jeg kan styre brugeradgang og sikkerhed i systemet.
  - Side: `Pages/admin/ReceiversPage.razor`
  - Verbs: POST
- **US-036** — Manage Configurations (User & Access Management)
  - Story: Som bruger vil jeg se og søge i konfigurationer, oprette konfigurationer og slette konfigurationer, så jeg kan styre brugeradgang og sikkerhed i systemet.
  - Side: `Pages/admin/ConfigurationsPage.razor`
  - Verbs: DELETE, GET, POST
- **US-038** — Manage Conversations (User & Access Management)
  - Story: Som bruger vil jeg se og søge i samtaler og oprette samtaler, så jeg kan styre brugeradgang og sikkerhed i systemet.
  - Side: `Pages/admin/ConversationsPage.razor`
  - Verbs: GET, POST
- **US-039** — Manage Ftps (User & Access Management)
  - Story: Som bruger vil jeg se og søge i FTP-filer, oprette FTP-filer, redigere FTP-filer og slette FTP-filer, så jeg kan styre brugeradgang og sikkerhed i systemet.
  - Side: `Pages/admin/FtpsPage.razor`
  - Verbs: DELETE, GET, POST, PUT
- **US-042** — Manage Statstidendes (Address & Data)
  - Story: Som bruger vil jeg se og søge i statstidendeer, oprette statstidendeer og slette statstidendeer, så jeg kan håndtere og validere adressedata korrekt.
  - Side: `Pages/addresses/StatstidendesPage.razor`
  - Verbs: DELETE, GET, POST
- **US-045** — Other Analytics Operations (Analytics & Reporting)
  - Story: Som bruger vil jeg arbejde med miscer, så jeg kan få indsigt i systemaktivitet og performance.
  - Side: `Pages/analytics/AnalyticsOperationsPage.razor`
  - Verbs: 
- **US-046** — Other Address Operations (Address & Data)
  - Story: Som bruger vil jeg arbejde med miscer, så jeg kan håndtere og validere adressedata korrekt.
  - Side: `Pages/addresses/AddressOperationsPage.razor`
  - Verbs: 
- **US-047** — Other Finance Operations (Finance & Operations)
  - Story: Som bruger vil jeg arbejde med miscer, så jeg kan holde styr på økonomi og driftsprocesser.
  - Side: `Pages/finance/FinanceOperationsPage.razor`
  - Verbs: 
- **US-048** — Other User Operations (User & Access Management)
  - Story: Som bruger vil jeg arbejde med miscer, så jeg kan styre brugeradgang og sikkerhed i systemet.
  - Side: `Pages/admin/UserOperationsPage.razor`
  - Verbs: 

---

## Shared Components (byg FØRST)

Inden du bygger individuelle sider, byg disse delte komponenter:

1. `Shared/DataGrid/AppDataGrid.razor` — wraps MudDataGrid med standard search + paging
2. `Shared/Dialogs/ConfirmDeleteDialog.razor` — standardiseret sletbekræftelse
3. `Shared/Dialogs/BaseFormDialog.razor` — standard create/edit dialog ramme
4. `Shared/Feedback/AppSnackbar.razor` — centraliseret feedback service
5. `Layout/NavMenu.razor` — auto-genereret fra nav-manifest

---

## User Stories (fuld liste)

### US-001 — Manage Messages [P1]

**Domæne:** Beskeder & Kommunikation  
**Story:** Som bruger vil jeg se og søge i beskeder, oprette beskeder og slette beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.  
**Verbs:** DELETE, GET, POST  
**Ressource:** beskeder  

**Acceptkriterier:**
- Brugeren ser en liste over beskeder
- Brugeren kan søge og filtrere beskeder
- Brugeren kan oprette ny/nye beskeder via formular
- Brugeren kan slette beskeder med bekræftelsesdialog

**Blazor side:** `Pages/messaging/MessagesPage.razor`  
**Route:** `/messaging/messages`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove message
- Bruger: User can view and retrieve message
- Bruger: User can create and submit message

---

### US-002 — Manage Customers [P1]

**Domæne:** Kunder & Tilmelding  
**Story:** Som bruger vil jeg se og søge i kunder, oprette kunder, redigere kunder og slette kunder, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.  
**Verbs:** DELETE, GET, PATCH, POST, PUT  
**Ressource:** kunder  

**Acceptkriterier:**
- Brugeren ser en liste over kunder
- Brugeren kan søge og filtrere kunder
- Brugeren kan oprette ny/nye kunder via formular
- Brugeren kan redigere eksisterende kunder
- Brugeren kan slette kunder med bekræftelsesdialog

**Blazor side:** `Pages/customers/CustomersPage.razor`  
**Route:** `/customers/customers`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove customer
- Bruger: User can view and retrieve customer
- Bruger: User can modify customer
- Bruger: User can create and submit customer
- Bruger: User can update customer

---

### US-003 — Manage Profiles [P3]

**Domæne:** Brugere & Adgang  
**Story:** Som bruger vil jeg se og søge i profiler, oprette profiler, redigere profiler og slette profiler, så jeg kan styre brugeradgang og sikkerhed i systemet.  
**Verbs:** DELETE, GET, POST, PUT  
**Ressource:** profiler  

**Acceptkriterier:**
- Brugeren ser en liste over profiler
- Brugeren kan søge og filtrere profiler
- Brugeren kan oprette ny/nye profiler via formular
- Brugeren kan redigere eksisterende profiler
- Brugeren kan slette profiler med bekræftelsesdialog

**Blazor side:** `Pages/admin/ProfilesPage.razor`  
**Route:** `/admin/profiles`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove user profile
- Bruger: User can view and retrieve user profile
- Bruger: User can create and submit user profile
- Bruger: User can update user profile

---

### US-004 — Manage Users [P3]

**Domæne:** Brugere & Adgang  
**Story:** Som bruger vil jeg se og søge i brugere, oprette brugere, redigere brugere og slette brugere, så jeg kan styre brugeradgang og sikkerhed i systemet.  
**Verbs:** DELETE, GET, PATCH, POST, PUT  
**Ressource:** brugere  

**Acceptkriterier:**
- Brugeren ser en liste over brugere
- Brugeren kan søge og filtrere brugere
- Brugeren kan oprette ny/nye brugere via formular
- Brugeren kan redigere eksisterende brugere
- Brugeren kan slette brugere med bekræftelsesdialog

**Blazor side:** `Pages/admin/UsersPage.razor`  
**Route:** `/admin/users`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove user account
- Bruger: User can view and retrieve user account
- Bruger: User can modify user account
- Bruger: User can create and submit user account
- Bruger: User can update user account

---

### US-005 — Manage Senders [P1]

**Domæne:** Kunder & Tilmelding  
**Story:** Som bruger vil jeg se og søge i afsendere, oprette afsendere, redigere afsendere og slette afsendere, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.  
**Verbs:** DELETE, GET, PATCH, POST  
**Ressource:** afsendere  

**Acceptkriterier:**
- Brugeren ser en liste over afsendere
- Brugeren kan søge og filtrere afsendere
- Brugeren kan oprette ny/nye afsendere via formular
- Brugeren kan redigere eksisterende afsendere
- Brugeren kan slette afsendere med bekræftelsesdialog

**Blazor side:** `Pages/customers/SendersPage.razor`  
**Route:** `/customers/senders`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove message sender
- Bruger: User can view and retrieve message sender
- Bruger: User can modify message sender
- Bruger: User can create and submit message sender

---

### US-006 — Manage Benchmarks [P3]

**Domæne:** Analyse & Rapportering  
**Story:** Som bruger vil jeg se og søge i benchmarks, oprette benchmarks, redigere benchmarks og slette benchmarks, så jeg kan få indsigt i systemaktivitet og performance.  
**Verbs:** DELETE, GET, PATCH, POST  
**Ressource:** benchmarks  

**Acceptkriterier:**
- Brugeren ser en liste over benchmarks
- Brugeren kan søge og filtrere benchmarks
- Brugeren kan oprette ny/nye benchmarks via formular
- Brugeren kan redigere eksisterende benchmarks
- Brugeren kan slette benchmarks med bekræftelsesdialog

**Blazor side:** `Pages/analytics/BenchmarksPage.razor`  
**Route:** `/analytics/benchmarks`  
**MudBlazor:** MudButton, MudCard, MudChart, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination, stats-cards  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove performance benchmark
- Bruger: User can view and retrieve performance benchmark
- Bruger: User can modify performance benchmark
- Bruger: User can create and submit performance benchmark

---

### US-007 — Manage Resets [P3]

**Domæne:** Brugere & Adgang  
**Story:** Som bruger vil jeg oprette nulstillinger, så jeg kan styre brugeradgang og sikkerhed i systemet.  
**Verbs:** POST  
**Ressource:** nulstillinger  

**Acceptkriterier:**
- Brugeren kan oprette ny/nye nulstillinger via formular

**Blazor side:** `Pages/admin/ResetsPage.razor`  
**Route:** `/admin/resets`  
**MudBlazor:** MudButton, MudDialog, MudForm  
**Patterns:** create-dialog  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can create and submit password reset request

---

### US-008 — Manage Sales [P3]

**Domæne:** Økonomi & Drift  
**Story:** Som bruger vil jeg se og søge i salgsdata, oprette salgsdata, redigere salgsdata og slette salgsdata, så jeg kan holde styr på økonomi og driftsprocesser.  
**Verbs:** DELETE, GET, POST, PUT  
**Ressource:** salgsdata  

**Acceptkriterier:**
- Brugeren ser en liste over salgsdata
- Brugeren kan søge og filtrere salgsdata
- Brugeren kan oprette ny/nye salgsdata via formular
- Brugeren kan redigere eksisterende salgsdata
- Brugeren kan slette salgsdata med bekræftelsesdialog

**Blazor side:** `Pages/finance/SalesPage.razor`  
**Route:** `/finance/sales`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove sales record
- Bruger: User can view and retrieve sales record
- Bruger: User can create and submit sales record
- Bruger: User can update sales record

---

### US-009 — Manage Prospects [P1]

**Domæne:** Kunder & Tilmelding  
**Story:** Som bruger vil jeg se og søge i salgsmuligheder, oprette salgsmuligheder, redigere salgsmuligheder og slette salgsmuligheder, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.  
**Verbs:** DELETE, GET, PATCH, POST  
**Ressource:** salgsmuligheder  

**Acceptkriterier:**
- Brugeren ser en liste over salgsmuligheder
- Brugeren kan søge og filtrere salgsmuligheder
- Brugeren kan oprette ny/nye salgsmuligheder via formular
- Brugeren kan redigere eksisterende salgsmuligheder
- Brugeren kan slette salgsmuligheder med bekræftelsesdialog

**Blazor side:** `Pages/customers/ProspectsPage.razor`  
**Route:** `/customers/prospects`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove potential customer
- Bruger: User can view and retrieve potential customer
- Bruger: User can modify potential customer
- Bruger: User can create and submit potential customer

---

### US-010 — Manage Salaries [P3]

**Domæne:** Økonomi & Drift  
**Story:** Som bruger vil jeg se og søge i lønsedler, så jeg kan holde styr på økonomi og driftsprocesser.  
**Verbs:** GET  
**Ressource:** lønsedler  

**Acceptkriterier:**
- Brugeren ser en liste over lønsedler
- Brugeren kan søge og filtrere lønsedler

**Blazor side:** `Pages/finance/SalariesPage.razor`  
**Route:** `/finance/salarys`  
**MudBlazor:** MudDataGrid, MudTextField  
**Patterns:** list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can view and retrieve payroll period

---

### US-011 — Manage Absences [P3]

**Domæne:** Økonomi & Drift  
**Story:** Som bruger vil jeg se og søge i fraværsregistreringer, oprette fraværsregistreringer, redigere fraværsregistreringer og slette fraværsregistreringer, så jeg kan holde styr på økonomi og driftsprocesser.  
**Verbs:** DELETE, GET, PATCH, POST  
**Ressource:** fraværsregistreringer  

**Acceptkriterier:**
- Brugeren ser en liste over fraværsregistreringer
- Brugeren kan søge og filtrere fraværsregistreringer
- Brugeren kan oprette ny/nye fraværsregistreringer via formular
- Brugeren kan redigere eksisterende fraværsregistreringer
- Brugeren kan slette fraværsregistreringer med bekræftelsesdialog

**Blazor side:** `Pages/finance/AbsencesPage.razor`  
**Route:** `/finance/absences`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove employee absence
- Bruger: User can view and retrieve employee absence
- Bruger: User can modify employee absence
- Bruger: User can create and submit employee absence

---

### US-012 — Manage Operationals [P1]

**Domæne:** Beskeder & Kommunikation  
**Story:** Som bruger vil jeg se og søge i driftsdata, oprette driftsdata, redigere driftsdata og slette driftsdata, så jeg kan kommunikere effektivt med kunder og modtagere.  
**Verbs:** DELETE, GET, POST, PUT  
**Ressource:** driftsdata  

**Acceptkriterier:**
- Brugeren ser en liste over driftsdata
- Brugeren kan søge og filtrere driftsdata
- Brugeren kan oprette ny/nye driftsdata via formular
- Brugeren kan redigere eksisterende driftsdata
- Brugeren kan slette driftsdata med bekræftelsesdialog

**Blazor side:** `Pages/messaging/OperationalsPage.razor`  
**Route:** `/messaging/operationals`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove operational notification
- Bruger: User can view and retrieve operational notification
- Bruger: User can create and submit operational notification
- Bruger: User can update operational notification

---

### US-013 — Manage Groups [P3]

**Domæne:** Adresser & Data  
**Story:** Som bruger vil jeg se og søge i grupper, oprette grupper og slette grupper, så jeg kan håndtere og validere adressedata korrekt.  
**Verbs:** DELETE, GET, POST  
**Ressource:** grupper  

**Acceptkriterier:**
- Brugeren ser en liste over grupper
- Brugeren kan søge og filtrere grupper
- Brugeren kan oprette ny/nye grupper via formular
- Brugeren kan slette grupper med bekræftelsesdialog

**Blazor side:** `Pages/addresses/GroupsPage.razor`  
**Route:** `/addresses/groups`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove recipient group
- Bruger: User can view and retrieve recipient group
- Bruger: User can create and submit recipient group

---

### US-014 — Manage Corrections [P3]

**Domæne:** Adresser & Data  
**Story:** Som bruger vil jeg oprette korrektioner og slette korrektioner, så jeg kan håndtere og validere adressedata korrekt.  
**Verbs:** DELETE, POST  
**Ressource:** korrektioner  

**Acceptkriterier:**
- Brugeren kan oprette ny/nye korrektioner via formular
- Brugeren kan slette korrektioner med bekræftelsesdialog

**Blazor side:** `Pages/addresses/CorrectionsPage.razor`  
**Route:** `/addresses/corrections`  
**MudBlazor:** MudButton, MudDialog, MudForm, MudIconButton  
**Patterns:** confirm-delete-dialog, create-dialog  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove address correction
- Bruger: User can create and submit address correction

---

### US-015 — Manage Receivers [P3]

**Domæne:** Adresser & Data  
**Story:** Som bruger vil jeg se og søge i modtagere og oprette modtagere, så jeg kan håndtere og validere adressedata korrekt.  
**Verbs:** GET, POST  
**Ressource:** modtagere  

**Acceptkriterier:**
- Brugeren ser en liste over modtagere
- Brugeren kan søge og filtrere modtagere
- Brugeren kan oprette ny/nye modtagere via formular

**Blazor side:** `Pages/addresses/ReceiversPage.razor`  
**Route:** `/addresses/receivers`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudTextField  
**Patterns:** create-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can view and retrieve notification recipient
- Bruger: User can create and submit notification recipient

---

### US-016 — Manage Contacts [P1]

**Domæne:** Kunder & Tilmelding  
**Story:** Som bruger vil jeg se og søge i kontakter, oprette kontakter, redigere kontakter og slette kontakter, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.  
**Verbs:** DELETE, GET, POST, PUT  
**Ressource:** kontakter  

**Acceptkriterier:**
- Brugeren ser en liste over kontakter
- Brugeren kan søge og filtrere kontakter
- Brugeren kan oprette ny/nye kontakter via formular
- Brugeren kan redigere eksisterende kontakter
- Brugeren kan slette kontakter med bekræftelsesdialog

**Blazor side:** `Pages/customers/ContactsPage.razor`  
**Route:** `/customers/contacts`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove contact person
- Bruger: User can view and retrieve contact person
- Bruger: User can create and submit contact person
- Bruger: User can update contact person

---

### US-017 — Manage Roles [P3]

**Domæne:** Brugere & Adgang  
**Story:** Som bruger vil jeg se og søge i roller, oprette roller og redigere roller, så jeg kan styre brugeradgang og sikkerhed i systemet.  
**Verbs:** GET, POST, PUT  
**Ressource:** roller  

**Acceptkriterier:**
- Brugeren ser en liste over roller
- Brugeren kan søge og filtrere roller
- Brugeren kan oprette ny/nye roller via formular
- Brugeren kan redigere eksisterende roller

**Blazor side:** `Pages/admin/RolesPage.razor`  
**Route:** `/admin/roles`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** create-dialog, edit-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can view and retrieve user role
- Bruger: User can create and submit user role
- Bruger: User can update user role

---

### US-018 — Manage Invoices [P3]

**Domæne:** Økonomi & Drift  
**Story:** Som bruger vil jeg se og søge i fakturaer, så jeg kan holde styr på økonomi og driftsprocesser.  
**Verbs:** GET  
**Ressource:** fakturaer  

**Acceptkriterier:**
- Brugeren ser en liste over fakturaer
- Brugeren kan søge og filtrere fakturaer

**Blazor side:** `Pages/finance/InvoicesPage.razor`  
**Route:** `/finance/invoices`  
**MudBlazor:** MudDataGrid, MudTextField  
**Patterns:** list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can view and retrieve invoice

---

### US-019 — Manage Enrollments [P1]

**Domæne:** Kunder & Tilmelding  
**Story:** Som bruger vil jeg se og søge i tilmeldinger, oprette tilmeldinger og slette tilmeldinger, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.  
**Verbs:** DELETE, GET, POST  
**Ressource:** tilmeldinger  

**Acceptkriterier:**
- Brugeren ser en liste over tilmeldinger
- Brugeren kan søge og filtrere tilmeldinger
- Brugeren kan oprette ny/nye tilmeldinger via formular
- Brugeren kan slette tilmeldinger med bekræftelsesdialog

**Blazor side:** `Pages/customers/EnrollmentsPage.razor`  
**Route:** `/customers/enrollments`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove subscription
- Bruger: User can view and retrieve subscription
- Bruger: User can create and submit subscription

---

### US-020 — Manage Dynamics [P1]

**Domæne:** Beskeder & Kommunikation  
**Story:** Som bruger vil jeg se og søge i dynamiske felter, oprette dynamiske felter, redigere dynamiske felter og slette dynamiske felter, så jeg kan kommunikere effektivt med kunder og modtagere.  
**Verbs:** DELETE, GET, POST, PUT  
**Ressource:** dynamiske felter  

**Acceptkriterier:**
- Brugeren ser en liste over dynamiske felter
- Brugeren kan søge og filtrere dynamiske felter
- Brugeren kan oprette ny/nye dynamiske felter via formular
- Brugeren kan redigere eksisterende dynamiske felter
- Brugeren kan slette dynamiske felter med bekræftelsesdialog

**Blazor side:** `Pages/messaging/DynamicsPage.razor`  
**Route:** `/messaging/dynamics`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove dynamic notification
- Bruger: User can view and retrieve dynamic notification
- Bruger: User can create and submit dynamic notification
- Bruger: User can update dynamic notification

---

### US-021 — Manage Gdprs [P3]

**Domæne:** Adresser & Data  
**Story:** Som bruger vil jeg se og søge i GDPR-håndtering, oprette GDPR-håndtering, redigere GDPR-håndtering og slette GDPR-håndtering, så jeg kan håndtere og validere adressedata korrekt.  
**Verbs:** DELETE, GET, POST, PUT  
**Ressource:** GDPR-håndtering  

**Acceptkriterier:**
- Brugeren ser en liste over GDPR-håndtering
- Brugeren kan søge og filtrere GDPR-håndtering
- Brugeren kan oprette ny/nye GDPR-håndtering via formular
- Brugeren kan redigere eksisterende GDPR-håndtering
- Brugeren kan slette GDPR-håndtering med bekræftelsesdialog

**Blazor side:** `Pages/addresses/GdprsPage.razor`  
**Route:** `/addresses/gdprs`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove privacy consent record
- Bruger: User can view and retrieve privacy consent record
- Bruger: User can create and submit privacy consent record
- Bruger: User can update privacy consent record

---

### US-022 — Manage Maps [P3]

**Domæne:** Brugere & Adgang  
**Story:** Som bruger vil jeg se og søge i kortvisning, oprette kortvisning, redigere kortvisning og slette kortvisning, så jeg kan styre brugeradgang og sikkerhed i systemet.  
**Verbs:** DELETE, GET, POST, PUT  
**Ressource:** kortvisning  

**Acceptkriterier:**
- Brugeren ser en liste over kortvisning
- Brugeren kan søge og filtrere kortvisning
- Brugeren kan oprette ny/nye kortvisning via formular
- Brugeren kan redigere eksisterende kortvisning
- Brugeren kan slette kortvisning med bekræftelsesdialog

**Blazor side:** `Pages/admin/MapsPage.razor`  
**Route:** `/admin/maps`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudPaper, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, map-view, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove geographic map
- Bruger: User can view and retrieve geographic map
- Bruger: User can create and submit geographic map
- Bruger: User can update geographic map

---

### US-023 — Manage Webs [P1]

**Domæne:** Beskeder & Kommunikation  
**Story:** Som bruger vil jeg se og søge i web-beskeder, oprette web-beskeder og slette web-beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.  
**Verbs:** DELETE, GET, POST  
**Ressource:** web-beskeder  

**Acceptkriterier:**
- Brugeren ser en liste over web-beskeder
- Brugeren kan søge og filtrere web-beskeder
- Brugeren kan oprette ny/nye web-beskeder via formular
- Brugeren kan slette web-beskeder med bekræftelsesdialog

**Blazor side:** `Pages/messaging/WebsPage.razor`  
**Route:** `/messaging/webs`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove web notification channel
- Bruger: User can view and retrieve web notification channel
- Bruger: User can create and submit web notification channel

---

### US-024 — Manage Sms [P2]

**Domæne:** Beskeder & Kommunikation  
**Story:** Som bruger vil jeg se og søge i SMS-beskeder og slette SMS-beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.  
**Verbs:** DELETE, GET  
**Ressource:** SMS-beskeder  

**Acceptkriterier:**
- Brugeren ser en liste over SMS-beskeder
- Brugeren kan søge og filtrere SMS-beskeder
- Brugeren kan slette SMS-beskeder med bekræftelsesdialog

**Blazor side:** `Pages/messaging/SmsPage.razor`  
**Route:** `/messaging/smss`  
**MudBlazor:** MudDataGrid, MudDialog, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove sms notification channel
- Bruger: User can view and retrieve sms notification channel

---

### US-025 — Manage Causes [P3]

**Domæne:** Analyse & Rapportering  
**Story:** Som bruger vil jeg oprette årsagskoder, redigere årsagskoder og slette årsagskoder, så jeg kan få indsigt i systemaktivitet og performance.  
**Verbs:** DELETE, POST, PUT  
**Ressource:** årsagskoder  

**Acceptkriterier:**
- Brugeren kan oprette ny/nye årsagskoder via formular
- Brugeren kan redigere eksisterende årsagskoder
- Brugeren kan slette årsagskoder med bekræftelsesdialog

**Blazor side:** `Pages/analytics/CausesPage.razor`  
**Route:** `/analytics/causes`  
**MudBlazor:** MudButton, MudDialog, MudForm, MudIconButton  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove benchmark cause
- Bruger: User can create and submit benchmark cause
- Bruger: User can update benchmark cause

---

### US-026 — Manage Address [P3]

**Domæne:** Adresser & Data  
**Story:** Som bruger vil jeg se og søge i adresser, oprette adresser og redigere adresser, så jeg kan håndtere og validere adressedata korrekt.  
**Verbs:** GET, POST, PUT  
**Ressource:** adresser  

**Acceptkriterier:**
- Brugeren ser en liste over adresser
- Brugeren kan søge og filtrere adresser
- Brugeren kan oprette ny/nye adresser via formular
- Brugeren kan redigere eksisterende adresser

**Blazor side:** `Pages/addresses/AddressPage.razor`  
**Route:** `/addresses/addresss`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudPaper, MudTextField  
**Patterns:** create-dialog, edit-dialog, list-with-search, map-view, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can view and retrieve address
- Bruger: User can create and submit address
- Bruger: User can update address

---

### US-027 — Manage Stds [P3]

**Domæne:** Adresser & Data  
**Story:** Som bruger vil jeg oprette standardindstillinger og slette standardindstillinger, så jeg kan håndtere og validere adressedata korrekt.  
**Verbs:** DELETE, POST  
**Ressource:** standardindstillinger  

**Acceptkriterier:**
- Brugeren kan oprette ny/nye standardindstillinger via formular
- Brugeren kan slette standardindstillinger med bekræftelsesdialog

**Blazor side:** `Pages/addresses/StdsPage.razor`  
**Route:** `/addresses/stds`  
**MudBlazor:** MudButton, MudDialog, MudForm, MudIconButton  
**Patterns:** confirm-delete-dialog, create-dialog  


---

### US-028 — Manage Localizeds [P3]

**Domæne:** Adresser & Data  
**Story:** Som bruger vil jeg oprette sprogoversættelser, så jeg kan håndtere og validere adressedata korrekt.  
**Verbs:** POST  
**Ressource:** sprogoversættelser  

**Acceptkriterier:**
- Brugeren kan oprette ny/nye sprogoversættelser via formular

**Blazor side:** `Pages/addresses/LocalizedsPage.razor`  
**Route:** `/addresses/localizeds`  
**MudBlazor:** MudButton, MudDialog, MudForm  
**Patterns:** create-dialog  


---

### US-029 — Manage Employees [P3]

**Domæne:** Økonomi & Drift  
**Story:** Som bruger vil jeg se og søge i medarbejdere og oprette medarbejdere, så jeg kan holde styr på økonomi og driftsprocesser.  
**Verbs:** GET, POST  
**Ressource:** medarbejdere  

**Acceptkriterier:**
- Brugeren ser en liste over medarbejdere
- Brugeren kan søge og filtrere medarbejdere
- Brugeren kan oprette ny/nye medarbejdere via formular

**Blazor side:** `Pages/finance/EmployeesPage.razor`  
**Route:** `/finance/employees`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudTextField  
**Patterns:** create-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can view and retrieve employee
- Bruger: User can create and submit employee

---

### US-030 — Manage Imports [P3]

**Domæne:** Adresser & Data  
**Story:** Som bruger vil jeg se og søge i dataimport, oprette dataimport og slette dataimport, så jeg kan håndtere og validere adressedata korrekt.  
**Verbs:** DELETE, GET, POST  
**Ressource:** dataimport  

**Acceptkriterier:**
- Brugeren ser en liste over dataimport
- Brugeren kan søge og filtrere dataimport
- Brugeren kan oprette ny/nye dataimport via formular
- Brugeren kan slette dataimport med bekræftelsesdialog

**Blazor side:** `Pages/addresses/ImportsPage.razor`  
**Route:** `/addresses/imports`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  


---

### US-031 — Manage Customers [P3]

**Domæne:** Brugere & Adgang  
**Story:** Som bruger vil jeg se og søge i kunder, så jeg kan styre brugeradgang og sikkerhed i systemet.  
**Verbs:** GET  
**Ressource:** kunder  

**Acceptkriterier:**
- Brugeren ser en liste over kunder
- Brugeren kan søge og filtrere kunder

**Blazor side:** `Pages/admin/CustomersPage.razor`  
**Route:** `/admin/customers`  
**MudBlazor:** MudDataGrid, MudTextField  
**Patterns:** list-with-search, pagination  


---

### US-032 — Manage Entries [P1]

**Domæne:** Beskeder & Kommunikation  
**Story:** Som bruger vil jeg se og søge i poster, oprette poster og slette poster, så jeg kan kommunikere effektivt med kunder og modtagere.  
**Verbs:** DELETE, GET, POST  
**Ressource:** poster  

**Acceptkriterier:**
- Brugeren ser en liste over poster
- Brugeren kan søge og filtrere poster
- Brugeren kan oprette ny/nye poster via formular
- Brugeren kan slette poster med bekræftelsesdialog

**Blazor side:** `Pages/messaging/EntriesPage.razor`  
**Route:** `/messaging/entrys`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  


---

### US-033 — Manage Drives [P3]

**Domæne:** Økonomi & Drift  
**Story:** Som bruger vil jeg se og søge i fildrev, oprette fildrev og slette fildrev, så jeg kan holde styr på økonomi og driftsprocesser.  
**Verbs:** DELETE, GET, POST  
**Ressource:** fildrev  

**Acceptkriterier:**
- Brugeren ser en liste over fildrev
- Brugeren kan søge og filtrere fildrev
- Brugeren kan oprette ny/nye fildrev via formular
- Brugeren kan slette fildrev med bekræftelsesdialog

**Blazor side:** `Pages/finance/DrivesPage.razor`  
**Route:** `/finance/drives`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  


---

### US-034 — Manage Archiveds [P2]

**Domæne:** Beskeder & Kommunikation  
**Story:** Som bruger vil jeg se og søge i arkiverede beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.  
**Verbs:** GET  
**Ressource:** arkiverede beskeder  

**Acceptkriterier:**
- Brugeren ser en liste over arkiverede beskeder
- Brugeren kan søge og filtrere arkiverede beskeder

**Blazor side:** `Pages/messaging/ArchivedsPage.razor`  
**Route:** `/messaging/archiveds`  
**MudBlazor:** MudDataGrid, MudTextField  
**Patterns:** list-with-search, pagination  


---

### US-035 — Manage Receivers [P3]

**Domæne:** Brugere & Adgang  
**Story:** Som bruger vil jeg oprette modtagere, så jeg kan styre brugeradgang og sikkerhed i systemet.  
**Verbs:** POST  
**Ressource:** modtagere  

**Acceptkriterier:**
- Brugeren kan oprette ny/nye modtagere via formular

**Blazor side:** `Pages/admin/ReceiversPage.razor`  
**Route:** `/admin/receivers`  
**MudBlazor:** MudButton, MudDialog, MudForm  
**Patterns:** create-dialog  


---

### US-036 — Manage Configurations [P3]

**Domæne:** Brugere & Adgang  
**Story:** Som bruger vil jeg se og søge i konfigurationer, oprette konfigurationer og slette konfigurationer, så jeg kan styre brugeradgang og sikkerhed i systemet.  
**Verbs:** DELETE, GET, POST  
**Ressource:** konfigurationer  

**Acceptkriterier:**
- Brugeren ser en liste over konfigurationer
- Brugeren kan søge og filtrere konfigurationer
- Brugeren kan oprette ny/nye konfigurationer via formular
- Brugeren kan slette konfigurationer med bekræftelsesdialog

**Blazor side:** `Pages/admin/ConfigurationsPage.razor`  
**Route:** `/admin/configurations`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

**Context fra sms-service (implementeringsinspirasjon):**
- Bruger: User can remove system configuration
- Bruger: User can view and retrieve system configuration
- Bruger: User can create and submit system configuration

---

### US-037 — Manage Status [P2]

**Domæne:** Beskeder & Kommunikation  
**Story:** Som bruger vil jeg se og søge i statusoversigt, så jeg kan kommunikere effektivt med kunder og modtagere.  
**Verbs:** GET  
**Ressource:** statusoversigt  

**Acceptkriterier:**
- Brugeren ser en liste over statusoversigt
- Brugeren kan søge og filtrere statusoversigt

**Blazor side:** `Pages/messaging/StatusPage.razor`  
**Route:** `/messaging/statuss`  
**MudBlazor:** MudDataGrid, MudTextField  
**Patterns:** list-with-search, pagination  


---

### US-038 — Manage Conversations [P3]

**Domæne:** Brugere & Adgang  
**Story:** Som bruger vil jeg se og søge i samtaler og oprette samtaler, så jeg kan styre brugeradgang og sikkerhed i systemet.  
**Verbs:** GET, POST  
**Ressource:** samtaler  

**Acceptkriterier:**
- Brugeren ser en liste over samtaler
- Brugeren kan søge og filtrere samtaler
- Brugeren kan oprette ny/nye samtaler via formular

**Blazor side:** `Pages/admin/ConversationsPage.razor`  
**Route:** `/admin/conversations`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudTextField  
**Patterns:** create-dialog, list-with-search, pagination  


---

### US-039 — Manage Ftps [P3]

**Domæne:** Brugere & Adgang  
**Story:** Som bruger vil jeg se og søge i FTP-filer, oprette FTP-filer, redigere FTP-filer og slette FTP-filer, så jeg kan styre brugeradgang og sikkerhed i systemet.  
**Verbs:** DELETE, GET, POST, PUT  
**Ressource:** FTP-filer  

**Acceptkriterier:**
- Brugeren ser en liste over FTP-filer
- Brugeren kan søge og filtrere FTP-filer
- Brugeren kan oprette ny/nye FTP-filer via formular
- Brugeren kan redigere eksisterende FTP-filer
- Brugeren kan slette FTP-filer med bekræftelsesdialog

**Blazor side:** `Pages/admin/FtpsPage.razor`  
**Route:** `/admin/ftps`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  


---

### US-040 — Manage Warnings [P1]

**Domæne:** Beskeder & Kommunikation  
**Story:** Som bruger vil jeg se og søge i advarsler, oprette advarsler og redigere advarsler, så jeg kan kommunikere effektivt med kunder og modtagere.  
**Verbs:** GET, POST, PUT  
**Ressource:** advarsler  

**Acceptkriterier:**
- Brugeren ser en liste over advarsler
- Brugeren kan søge og filtrere advarsler
- Brugeren kan oprette ny/nye advarsler via formular
- Brugeren kan redigere eksisterende advarsler

**Blazor side:** `Pages/messaging/WarningsPage.razor`  
**Route:** `/messaging/warnings`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** create-dialog, edit-dialog, list-with-search, pagination  


---

### US-041 — Manage Weathers [P1]

**Domæne:** Beskeder & Kommunikation  
**Story:** Som bruger vil jeg se og søge i vejrdata, oprette vejrdata, redigere vejrdata og slette vejrdata, så jeg kan kommunikere effektivt med kunder og modtagere.  
**Verbs:** DELETE, GET, POST, PUT  
**Ressource:** vejrdata  

**Acceptkriterier:**
- Brugeren ser en liste over vejrdata
- Brugeren kan søge og filtrere vejrdata
- Brugeren kan oprette ny/nye vejrdata via formular
- Brugeren kan redigere eksisterende vejrdata
- Brugeren kan slette vejrdata med bekræftelsesdialog

**Blazor side:** `Pages/messaging/WeathersPage.razor`  
**Route:** `/messaging/weathers`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  


---

### US-042 — Manage Statstidendes [P3]

**Domæne:** Adresser & Data  
**Story:** Som bruger vil jeg se og søge i statstidendeer, oprette statstidendeer og slette statstidendeer, så jeg kan håndtere og validere adressedata korrekt.  
**Verbs:** DELETE, GET, POST  
**Ressource:** statstidendeer  

**Acceptkriterier:**
- Brugeren ser en liste over statstidendeer
- Brugeren kan søge og filtrere statstidendeer
- Brugeren kan oprette ny/nye statstidendeer via formular
- Brugeren kan slette statstidendeer med bekræftelsesdialog

**Blazor side:** `Pages/addresses/StatstidendesPage.razor`  
**Route:** `/addresses/statstidendes`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  


---

### US-043 — Other Messaging Operations [P2]

**Domæne:** Beskeder & Kommunikation  
**Story:** Som bruger vil jeg arbejde med miscer, så jeg kan kommunikere effektivt med kunder og modtagere.  
**Verbs:**   
**Ressource:** miscer  

**Acceptkriterier:**

**Blazor side:** `Pages/messaging/MessagingOperationsPage.razor`  
**Route:** `/messaging/miscs`  
**MudBlazor:**   
**Patterns:**   


---

### US-044 — Other Customer Operations [P2]

**Domæne:** Kunder & Tilmelding  
**Story:** Som bruger vil jeg arbejde med miscer, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.  
**Verbs:**   
**Ressource:** miscer  

**Acceptkriterier:**

**Blazor side:** `Pages/customers/CustomerOperationsPage.razor`  
**Route:** `/customers/miscs`  
**MudBlazor:**   
**Patterns:**   


---

### US-045 — Other Analytics Operations [P3]

**Domæne:** Analyse & Rapportering  
**Story:** Som bruger vil jeg arbejde med miscer, så jeg kan få indsigt i systemaktivitet og performance.  
**Verbs:**   
**Ressource:** miscer  

**Acceptkriterier:**

**Blazor side:** `Pages/analytics/AnalyticsOperationsPage.razor`  
**Route:** `/analytics/miscs`  
**MudBlazor:**   
**Patterns:**   


---

### US-046 — Other Address Operations [P3]

**Domæne:** Adresser & Data  
**Story:** Som bruger vil jeg arbejde med miscer, så jeg kan håndtere og validere adressedata korrekt.  
**Verbs:**   
**Ressource:** miscer  

**Acceptkriterier:**

**Blazor side:** `Pages/addresses/AddressOperationsPage.razor`  
**Route:** `/addresses/miscs`  
**MudBlazor:**   
**Patterns:**   


---

### US-047 — Other Finance Operations [P3]

**Domæne:** Økonomi & Drift  
**Story:** Som bruger vil jeg arbejde med miscer, så jeg kan holde styr på økonomi og driftsprocesser.  
**Verbs:**   
**Ressource:** miscer  

**Acceptkriterier:**

**Blazor side:** `Pages/finance/FinanceOperationsPage.razor`  
**Route:** `/finance/miscs`  
**MudBlazor:**   
**Patterns:**   


---

### US-048 — Other User Operations [P3]

**Domæne:** Brugere & Adgang  
**Story:** Som bruger vil jeg arbejde med miscer, så jeg kan styre brugeradgang og sikkerhed i systemet.  
**Verbs:**   
**Ressource:** miscer  

**Acceptkriterier:**

**Blazor side:** `Pages/admin/UserOperationsPage.razor`  
**Route:** `/admin/miscs`  
**MudBlazor:**   
**Patterns:**   


---

