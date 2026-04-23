# ServiceAlert → GreenAI — UI Masterplan

**Genereret:** 2026-04-23  
**Kilde:** 719 engelske behaviors + 593 danske behaviors  
**User stories:** 48  
**Domæner:** 6  

---

## Vision

ServiceAlert UI er et professionelt enterprise-dashboard bygget i **Blazor Server + MudBlazor 8**.
Systemet håndterer bulk-notifikationer (SMS, web-beskeder) til tusindvis af modtagere via et struktureret
admin-interface. Alle sider følger ét konsistent design-sprog med venstre navigation, data-grid layouts
og modal-dialoger for CRUD-operationer.

**Rød tråd:** Desktop-first, data-tæt, keyboard-navigerbar, hurtige svar (<200ms), ingen page reloads.

---


## Tech Stack (LÅST — må ikke ændres)

| Lag | Teknologi |
|-----|-----------|
| Runtime | .NET 10 / C# 13 |
| Arkitektur | Vertical Slice (feature-mappe) |
| Frontend | Blazor Server + MudBlazor 8 |
| Data | Dapper + Z.Dapper.Plus |
| Auth | Custom JWT — ICurrentUser |
| Mediator | MediatR + FluentValidation |
| Tests | xUnit v3 + NSubstitute |
| CSS | design-tokens.css → SSOT |
| Icons | Material Icons via MudBlazor |

---


## Delte UI-mønstre (ALLE sider følger disse)

### 1. List-page pattern
- **MudDataGrid** med server-side paging (default 25 rækker)
- **MudTextField** søgefelt øverst til venstre
- **MudButton** "Opret ny" øverst til højre (kun hvis POST er tilgængeligt)
- Klik på række → åbner detalje-dialog (MudDialog)
- Slet via **MudIconButton** (skraldespand) + bekræftelsesdialog

### 2. Create/Edit dialog pattern
- **MudDialog** i stedet for separate sider
- **MudForm** med **MudTextField**, **MudSelect**, **MudDatePicker** efter behov
- Knapper: "Gem" (primary) og "Annuller" (secondary)
- Validering: FluentValidation-fejl vises inline

### 3. Confirm-delete pattern
- **MudDialog**: "Er du sikker på du vil slette [navn]?"
- Knapper: "Slet" (error color) og "Annuller"
- Efter slet: grid refresh + MudSnackbar "Slettet"

### 4. Navigation
- **MudNavMenu** i venstre sidebar
- Gruperet per domæne med **MudNavGroup** (collapsible)
- Aktiv side markeret med highlight
- Mobile: **MudDrawer** swipe-in

### 5. Feedback pattern
- Success: **MudSnackbar** grøn, 3 sek
- Error: **MudSnackbar** rød, persistent
- Loading: **MudProgressLinear** øverst på siden (ikke spinner)

### 6. Empty state pattern
- Ingen data: **MudAlert** Severity="Info" med opfordringstekst
- "Ingen [ressource] fundet. Opret den første!"

### 7. Auth/Adgang
- Sider kræver **[Authorize]** attribute
- Admin-sider kræver **[Authorize(Roles = "Admin")]**
- UI-elementer der kræver rettigheder: AuthorizeView + Policies

---


## AI Build Regler (ALLE AI-agenter følger disse)

1. **Ét vertical slice per user story** — feature-mappe med Query/Command/Handler/Endpoint
2. **Ingen EF Core** — kun Dapper SQL
3. **Ingen CSS overrides** — brug kun design-tokens.css vars
4. **Ingen inline styles** — brug `.ga-*` utility classes fra portal-skin.css
5. **Tests altid med** — xUnit + NSubstitute, named: `Method_State_Expected`
6. **Labels fra lokalisering** — `ILabelService.Get("KEY")` — ingen hardcoded tekst
7. **Navigation tilføjes** automatisk til `NavMenu.razor` under korrekt domæne-gruppe
8. **MudBlazor components** — se Shared Patterns ovenfor
9. **ICurrentUser** for auth-context — ingen HttpContext direkte
10. **ActivityLog** — alle COMMAND-operationer logger via `IActivityLogService`

## Vedligeholdelse (fremtidig AI)
- Hvert slice er selvstændigt — ændringer påvirker ikke andre slices
- Tilføj ny story: kør `get_story_context.py --story "X"` → får fuld implementeringskontekst
- Opdater harvest: kør `smart_harvester.py --all --overwrite` → genkør pipeline
- UI manifest opdateres automatisk ved ny story via denne pipeline

---

## Navigationsstruktur

```
App
├── Dashboard (/)          ← overblik, KPI-widgets
├── Beskeder & Kommunikation (/messaging)
│   ├── Beskeder (/messaging/messages)
│   ├── Driftsdata (/messaging/operationals)
│   ├── Dynamiske felter (/messaging/dynamics)
│   ├── Web-beskeder (/messaging/webs)
│   ├── Poster (/messaging/entrys)
│   ├── Sms-beskeder (/messaging/smss)
│   └── ... +5 mere
├── Kunder & Tilmelding (/customers)
│   ├── Kunder (/customers/customers)
│   ├── Afsendere (/customers/senders)
│   ├── Salgsmuligheder (/customers/prospects)
│   ├── Kontakter (/customers/contacts)
│   ├── Tilmeldinger (/customers/enrollments)
│   ├── Miscer (/customers/miscs)
├── Brugere & Adgang (/admin)
│   ├── Profiler (/admin/profiles)
│   ├── Brugere (/admin/users)
│   ├── Nulstillinger (/admin/resets)
│   ├── Roller (/admin/roles)
│   ├── Kortvisning (/admin/maps)
│   ├── Kunder (/admin/customers)
│   └── ... +5 mere
├── Adresser & Data (/addresses)
│   ├── Grupper (/addresses/groups)
│   ├── Korrektioner (/addresses/corrections)
│   ├── Modtagere (/addresses/receivers)
│   ├── Gdpr-håndtering (/addresses/gdprs)
│   ├── Adresser (/addresses/addresss)
│   ├── Standardindstillinger (/addresses/stds)
│   └── ... +4 mere
├── Økonomi & Drift (/finance)
│   ├── Salgsdata (/finance/sales)
│   ├── Lønsedler (/finance/salarys)
│   ├── Fraværsregistreringer (/finance/absences)
│   ├── Fakturaer (/finance/invoices)
│   ├── Medarbejdere (/finance/employees)
│   ├── Fildrev (/finance/drives)
│   └── ... +1 mere
├── Analyse & Rapportering (/analytics)
│   ├── Benchmarks (/analytics/benchmarks)
│   ├── Årsagskoder (/analytics/causes)
│   ├── Miscer (/analytics/miscs)
└── Indstillinger (/settings)
```

---

## Sider per domæne

### Beskeder & Kommunikation `/messaging` (icon: Message)

**P1 — Kritisk:**

#### [US-001] Manage Messages
- **Story:** Som bruger vil jeg se og søge i beskeder, oprette beskeder og slette beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.
- **Side:** `Pages/messaging/MessagesPage.razor`
- **Route:** `/messaging/messages`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over beskeder
  - Brugeren kan søge og filtrere beskeder
  - Brugeren kan oprette ny/nye beskeder via formular
  - Brugeren kan slette beskeder med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove message
  - [INFERRED] Bruger: User can view and retrieve message
  - [INFERRED] Bruger: User can create and submit message

#### [US-012] Manage Operationals
- **Story:** Som bruger vil jeg se og søge i driftsdata, oprette driftsdata, redigere driftsdata og slette driftsdata, så jeg kan kommunikere effektivt med kunder og modtagere.
- **Side:** `Pages/messaging/OperationalsPage.razor`
- **Route:** `/messaging/operationals`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over driftsdata
  - Brugeren kan søge og filtrere driftsdata
  - Brugeren kan oprette ny/nye driftsdata via formular
  - Brugeren kan redigere eksisterende driftsdata
  - Brugeren kan slette driftsdata med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove operational notification
  - [INFERRED] Bruger: User can view and retrieve operational notification
  - [INFERRED] Bruger: User can create and submit operational notification
  - [INFERRED] Bruger: User can update operational notification

#### [US-020] Manage Dynamics
- **Story:** Som bruger vil jeg se og søge i dynamiske felter, oprette dynamiske felter, redigere dynamiske felter og slette dynamiske felter, så jeg kan kommunikere effektivt med kunder og modtagere.
- **Side:** `Pages/messaging/DynamicsPage.razor`
- **Route:** `/messaging/dynamics`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over dynamiske felter
  - Brugeren kan søge og filtrere dynamiske felter
  - Brugeren kan oprette ny/nye dynamiske felter via formular
  - Brugeren kan redigere eksisterende dynamiske felter
  - Brugeren kan slette dynamiske felter med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove dynamic notification
  - [INFERRED] Bruger: User can view and retrieve dynamic notification
  - [INFERRED] Bruger: User can create and submit dynamic notification
  - [INFERRED] Bruger: User can update dynamic notification

#### [US-023] Manage Webs
- **Story:** Som bruger vil jeg se og søge i web-beskeder, oprette web-beskeder og slette web-beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.
- **Side:** `Pages/messaging/WebsPage.razor`
- **Route:** `/messaging/webs`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over web-beskeder
  - Brugeren kan søge og filtrere web-beskeder
  - Brugeren kan oprette ny/nye web-beskeder via formular
  - Brugeren kan slette web-beskeder med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove web notification channel
  - [INFERRED] Bruger: User can view and retrieve web notification channel
  - [INFERRED] Bruger: User can create and submit web notification channel

#### [US-032] Manage Entries
- **Story:** Som bruger vil jeg se og søge i poster, oprette poster og slette poster, så jeg kan kommunikere effektivt med kunder og modtagere.
- **Side:** `Pages/messaging/EntriesPage.razor`
- **Route:** `/messaging/entrys`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over poster
  - Brugeren kan søge og filtrere poster
  - Brugeren kan oprette ny/nye poster via formular
  - Brugeren kan slette poster med bekræftelsesdialog

#### [US-040] Manage Warnings
- **Story:** Som bruger vil jeg se og søge i advarsler, oprette advarsler og redigere advarsler, så jeg kan kommunikere effektivt med kunder og modtagere.
- **Side:** `Pages/messaging/WarningsPage.razor`
- **Route:** `/messaging/warnings`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over advarsler
  - Brugeren kan søge og filtrere advarsler
  - Brugeren kan oprette ny/nye advarsler via formular
  - Brugeren kan redigere eksisterende advarsler

#### [US-041] Manage Weathers
- **Story:** Som bruger vil jeg se og søge i vejrdata, oprette vejrdata, redigere vejrdata og slette vejrdata, så jeg kan kommunikere effektivt med kunder og modtagere.
- **Side:** `Pages/messaging/WeathersPage.razor`
- **Route:** `/messaging/weathers`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over vejrdata
  - Brugeren kan søge og filtrere vejrdata
  - Brugeren kan oprette ny/nye vejrdata via formular
  - Brugeren kan redigere eksisterende vejrdata
  - Brugeren kan slette vejrdata med bekræftelsesdialog

**P2 — Vigtig:**

#### [US-024] Manage Sms
- **Story:** Som bruger vil jeg se og søge i SMS-beskeder og slette SMS-beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.
- **Side:** `Pages/messaging/SmsPage.razor`
- **Route:** `/messaging/smss`
- **Components:** MudDataGrid, MudDialog, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over SMS-beskeder
  - Brugeren kan søge og filtrere SMS-beskeder
  - Brugeren kan slette SMS-beskeder med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove sms notification channel
  - [INFERRED] Bruger: User can view and retrieve sms notification channel

#### [US-034] Manage Archiveds
- **Story:** Som bruger vil jeg se og søge i arkiverede beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.
- **Side:** `Pages/messaging/ArchivedsPage.razor`
- **Route:** `/messaging/archiveds`
- **Components:** MudDataGrid, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over arkiverede beskeder
  - Brugeren kan søge og filtrere arkiverede beskeder

#### [US-037] Manage Status
- **Story:** Som bruger vil jeg se og søge i statusoversigt, så jeg kan kommunikere effektivt med kunder og modtagere.
- **Side:** `Pages/messaging/StatusPage.razor`
- **Route:** `/messaging/statuss`
- **Components:** MudDataGrid, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over statusoversigt
  - Brugeren kan søge og filtrere statusoversigt

#### [US-043] Other Messaging Operations
- **Story:** Som bruger vil jeg arbejde med miscer, så jeg kan kommunikere effektivt med kunder og modtagere.
- **Side:** `Pages/messaging/MessagingOperationsPage.razor`
- **Route:** `/messaging/miscs`
- **Components:** 
- **Acceptkriterier:**

### Kunder & Tilmelding `/customers` (icon: People)

**P1 — Kritisk:**

#### [US-002] Manage Customers
- **Story:** Som bruger vil jeg se og søge i kunder, oprette kunder, redigere kunder og slette kunder, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
- **Side:** `Pages/customers/CustomersPage.razor`
- **Route:** `/customers/customers`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over kunder
  - Brugeren kan søge og filtrere kunder
  - Brugeren kan oprette ny/nye kunder via formular
  - Brugeren kan redigere eksisterende kunder
  - Brugeren kan slette kunder med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove customer
  - [INFERRED] Bruger: User can view and retrieve customer
  - [INFERRED] Bruger: User can modify customer
  - [INFERRED] Bruger: User can create and submit customer

#### [US-005] Manage Senders
- **Story:** Som bruger vil jeg se og søge i afsendere, oprette afsendere, redigere afsendere og slette afsendere, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
- **Side:** `Pages/customers/SendersPage.razor`
- **Route:** `/customers/senders`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over afsendere
  - Brugeren kan søge og filtrere afsendere
  - Brugeren kan oprette ny/nye afsendere via formular
  - Brugeren kan redigere eksisterende afsendere
  - Brugeren kan slette afsendere med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove message sender
  - [INFERRED] Bruger: User can view and retrieve message sender
  - [INFERRED] Bruger: User can modify message sender
  - [INFERRED] Bruger: User can create and submit message sender

#### [US-009] Manage Prospects
- **Story:** Som bruger vil jeg se og søge i salgsmuligheder, oprette salgsmuligheder, redigere salgsmuligheder og slette salgsmuligheder, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
- **Side:** `Pages/customers/ProspectsPage.razor`
- **Route:** `/customers/prospects`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over salgsmuligheder
  - Brugeren kan søge og filtrere salgsmuligheder
  - Brugeren kan oprette ny/nye salgsmuligheder via formular
  - Brugeren kan redigere eksisterende salgsmuligheder
  - Brugeren kan slette salgsmuligheder med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove potential customer
  - [INFERRED] Bruger: User can view and retrieve potential customer
  - [INFERRED] Bruger: User can modify potential customer
  - [INFERRED] Bruger: User can create and submit potential customer

#### [US-016] Manage Contacts
- **Story:** Som bruger vil jeg se og søge i kontakter, oprette kontakter, redigere kontakter og slette kontakter, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
- **Side:** `Pages/customers/ContactsPage.razor`
- **Route:** `/customers/contacts`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over kontakter
  - Brugeren kan søge og filtrere kontakter
  - Brugeren kan oprette ny/nye kontakter via formular
  - Brugeren kan redigere eksisterende kontakter
  - Brugeren kan slette kontakter med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove contact person
  - [INFERRED] Bruger: User can view and retrieve contact person
  - [INFERRED] Bruger: User can create and submit contact person
  - [INFERRED] Bruger: User can update contact person

#### [US-019] Manage Enrollments
- **Story:** Som bruger vil jeg se og søge i tilmeldinger, oprette tilmeldinger og slette tilmeldinger, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
- **Side:** `Pages/customers/EnrollmentsPage.razor`
- **Route:** `/customers/enrollments`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over tilmeldinger
  - Brugeren kan søge og filtrere tilmeldinger
  - Brugeren kan oprette ny/nye tilmeldinger via formular
  - Brugeren kan slette tilmeldinger med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove subscription
  - [INFERRED] Bruger: User can view and retrieve subscription
  - [INFERRED] Bruger: User can create and submit subscription

**P2 — Vigtig:**

#### [US-044] Other Customer Operations
- **Story:** Som bruger vil jeg arbejde med miscer, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
- **Side:** `Pages/customers/CustomerOperationsPage.razor`
- **Route:** `/customers/miscs`
- **Components:** 
- **Acceptkriterier:**

### Brugere & Adgang `/admin` (icon: AdminPanelSettings)

**P3 — Nice-to-have:**

#### [US-003] Manage Profiles
- **Story:** Som bruger vil jeg se og søge i profiler, oprette profiler, redigere profiler og slette profiler, så jeg kan styre brugeradgang og sikkerhed i systemet.
- **Side:** `Pages/admin/ProfilesPage.razor`
- **Route:** `/admin/profiles`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over profiler
  - Brugeren kan søge og filtrere profiler
  - Brugeren kan oprette ny/nye profiler via formular
  - Brugeren kan redigere eksisterende profiler
  - Brugeren kan slette profiler med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove user profile
  - [INFERRED] Bruger: User can view and retrieve user profile
  - [INFERRED] Bruger: User can create and submit user profile
  - [INFERRED] Bruger: User can update user profile

#### [US-004] Manage Users
- **Story:** Som bruger vil jeg se og søge i brugere, oprette brugere, redigere brugere og slette brugere, så jeg kan styre brugeradgang og sikkerhed i systemet.
- **Side:** `Pages/admin/UsersPage.razor`
- **Route:** `/admin/users`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over brugere
  - Brugeren kan søge og filtrere brugere
  - Brugeren kan oprette ny/nye brugere via formular
  - Brugeren kan redigere eksisterende brugere
  - Brugeren kan slette brugere med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove user account
  - [INFERRED] Bruger: User can view and retrieve user account
  - [INFERRED] Bruger: User can modify user account
  - [INFERRED] Bruger: User can create and submit user account

#### [US-007] Manage Resets
- **Story:** Som bruger vil jeg oprette nulstillinger, så jeg kan styre brugeradgang og sikkerhed i systemet.
- **Side:** `Pages/admin/ResetsPage.razor`
- **Route:** `/admin/resets`
- **Components:** MudButton, MudDialog, MudForm
- **Acceptkriterier:**
  - Brugeren kan oprette ny/nye nulstillinger via formular
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can create and submit password reset request

#### [US-017] Manage Roles
- **Story:** Som bruger vil jeg se og søge i roller, oprette roller og redigere roller, så jeg kan styre brugeradgang og sikkerhed i systemet.
- **Side:** `Pages/admin/RolesPage.razor`
- **Route:** `/admin/roles`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over roller
  - Brugeren kan søge og filtrere roller
  - Brugeren kan oprette ny/nye roller via formular
  - Brugeren kan redigere eksisterende roller
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can view and retrieve user role
  - [INFERRED] Bruger: User can create and submit user role
  - [INFERRED] Bruger: User can update user role

#### [US-022] Manage Maps
- **Story:** Som bruger vil jeg se og søge i kortvisning, oprette kortvisning, redigere kortvisning og slette kortvisning, så jeg kan styre brugeradgang og sikkerhed i systemet.
- **Side:** `Pages/admin/MapsPage.razor`
- **Route:** `/admin/maps`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudPaper, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over kortvisning
  - Brugeren kan søge og filtrere kortvisning
  - Brugeren kan oprette ny/nye kortvisning via formular
  - Brugeren kan redigere eksisterende kortvisning
  - Brugeren kan slette kortvisning med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove geographic map
  - [INFERRED] Bruger: User can view and retrieve geographic map
  - [INFERRED] Bruger: User can create and submit geographic map
  - [INFERRED] Bruger: User can update geographic map

#### [US-031] Manage Customers
- **Story:** Som bruger vil jeg se og søge i kunder, så jeg kan styre brugeradgang og sikkerhed i systemet.
- **Side:** `Pages/admin/CustomersPage.razor`
- **Route:** `/admin/customers`
- **Components:** MudDataGrid, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over kunder
  - Brugeren kan søge og filtrere kunder

#### [US-035] Manage Receivers
- **Story:** Som bruger vil jeg oprette modtagere, så jeg kan styre brugeradgang og sikkerhed i systemet.
- **Side:** `Pages/admin/ReceiversPage.razor`
- **Route:** `/admin/receivers`
- **Components:** MudButton, MudDialog, MudForm
- **Acceptkriterier:**
  - Brugeren kan oprette ny/nye modtagere via formular

#### [US-036] Manage Configurations
- **Story:** Som bruger vil jeg se og søge i konfigurationer, oprette konfigurationer og slette konfigurationer, så jeg kan styre brugeradgang og sikkerhed i systemet.
- **Side:** `Pages/admin/ConfigurationsPage.razor`
- **Route:** `/admin/configurations`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over konfigurationer
  - Brugeren kan søge og filtrere konfigurationer
  - Brugeren kan oprette ny/nye konfigurationer via formular
  - Brugeren kan slette konfigurationer med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove system configuration
  - [INFERRED] Bruger: User can view and retrieve system configuration
  - [INFERRED] Bruger: User can create and submit system configuration

#### [US-038] Manage Conversations
- **Story:** Som bruger vil jeg se og søge i samtaler og oprette samtaler, så jeg kan styre brugeradgang og sikkerhed i systemet.
- **Side:** `Pages/admin/ConversationsPage.razor`
- **Route:** `/admin/conversations`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over samtaler
  - Brugeren kan søge og filtrere samtaler
  - Brugeren kan oprette ny/nye samtaler via formular

#### [US-039] Manage Ftps
- **Story:** Som bruger vil jeg se og søge i FTP-filer, oprette FTP-filer, redigere FTP-filer og slette FTP-filer, så jeg kan styre brugeradgang og sikkerhed i systemet.
- **Side:** `Pages/admin/FtpsPage.razor`
- **Route:** `/admin/ftps`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over FTP-filer
  - Brugeren kan søge og filtrere FTP-filer
  - Brugeren kan oprette ny/nye FTP-filer via formular
  - Brugeren kan redigere eksisterende FTP-filer
  - Brugeren kan slette FTP-filer med bekræftelsesdialog

#### [US-048] Other User Operations
- **Story:** Som bruger vil jeg arbejde med miscer, så jeg kan styre brugeradgang og sikkerhed i systemet.
- **Side:** `Pages/admin/UserOperationsPage.razor`
- **Route:** `/admin/miscs`
- **Components:** 
- **Acceptkriterier:**

### Adresser & Data `/addresses` (icon: LocationOn)

**P3 — Nice-to-have:**

#### [US-013] Manage Groups
- **Story:** Som bruger vil jeg se og søge i grupper, oprette grupper og slette grupper, så jeg kan håndtere og validere adressedata korrekt.
- **Side:** `Pages/addresses/GroupsPage.razor`
- **Route:** `/addresses/groups`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over grupper
  - Brugeren kan søge og filtrere grupper
  - Brugeren kan oprette ny/nye grupper via formular
  - Brugeren kan slette grupper med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove recipient group
  - [INFERRED] Bruger: User can view and retrieve recipient group
  - [INFERRED] Bruger: User can create and submit recipient group

#### [US-014] Manage Corrections
- **Story:** Som bruger vil jeg oprette korrektioner og slette korrektioner, så jeg kan håndtere og validere adressedata korrekt.
- **Side:** `Pages/addresses/CorrectionsPage.razor`
- **Route:** `/addresses/corrections`
- **Components:** MudButton, MudDialog, MudForm, MudIconButton
- **Acceptkriterier:**
  - Brugeren kan oprette ny/nye korrektioner via formular
  - Brugeren kan slette korrektioner med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove address correction
  - [INFERRED] Bruger: User can create and submit address correction

#### [US-015] Manage Receivers
- **Story:** Som bruger vil jeg se og søge i modtagere og oprette modtagere, så jeg kan håndtere og validere adressedata korrekt.
- **Side:** `Pages/addresses/ReceiversPage.razor`
- **Route:** `/addresses/receivers`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over modtagere
  - Brugeren kan søge og filtrere modtagere
  - Brugeren kan oprette ny/nye modtagere via formular
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can view and retrieve notification recipient
  - [INFERRED] Bruger: User can create and submit notification recipient

#### [US-021] Manage Gdprs
- **Story:** Som bruger vil jeg se og søge i GDPR-håndtering, oprette GDPR-håndtering, redigere GDPR-håndtering og slette GDPR-håndtering, så jeg kan håndtere og validere adressedata korrekt.
- **Side:** `Pages/addresses/GdprsPage.razor`
- **Route:** `/addresses/gdprs`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over GDPR-håndtering
  - Brugeren kan søge og filtrere GDPR-håndtering
  - Brugeren kan oprette ny/nye GDPR-håndtering via formular
  - Brugeren kan redigere eksisterende GDPR-håndtering
  - Brugeren kan slette GDPR-håndtering med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove privacy consent record
  - [INFERRED] Bruger: User can view and retrieve privacy consent record
  - [INFERRED] Bruger: User can create and submit privacy consent record
  - [INFERRED] Bruger: User can update privacy consent record

#### [US-026] Manage Address
- **Story:** Som bruger vil jeg se og søge i adresser, oprette adresser og redigere adresser, så jeg kan håndtere og validere adressedata korrekt.
- **Side:** `Pages/addresses/AddressPage.razor`
- **Route:** `/addresses/addresss`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudPaper, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over adresser
  - Brugeren kan søge og filtrere adresser
  - Brugeren kan oprette ny/nye adresser via formular
  - Brugeren kan redigere eksisterende adresser
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can view and retrieve address
  - [INFERRED] Bruger: User can create and submit address
  - [INFERRED] Bruger: User can update address

#### [US-027] Manage Stds
- **Story:** Som bruger vil jeg oprette standardindstillinger og slette standardindstillinger, så jeg kan håndtere og validere adressedata korrekt.
- **Side:** `Pages/addresses/StdsPage.razor`
- **Route:** `/addresses/stds`
- **Components:** MudButton, MudDialog, MudForm, MudIconButton
- **Acceptkriterier:**
  - Brugeren kan oprette ny/nye standardindstillinger via formular
  - Brugeren kan slette standardindstillinger med bekræftelsesdialog

#### [US-028] Manage Localizeds
- **Story:** Som bruger vil jeg oprette sprogoversættelser, så jeg kan håndtere og validere adressedata korrekt.
- **Side:** `Pages/addresses/LocalizedsPage.razor`
- **Route:** `/addresses/localizeds`
- **Components:** MudButton, MudDialog, MudForm
- **Acceptkriterier:**
  - Brugeren kan oprette ny/nye sprogoversættelser via formular

#### [US-030] Manage Imports
- **Story:** Som bruger vil jeg se og søge i dataimport, oprette dataimport og slette dataimport, så jeg kan håndtere og validere adressedata korrekt.
- **Side:** `Pages/addresses/ImportsPage.razor`
- **Route:** `/addresses/imports`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over dataimport
  - Brugeren kan søge og filtrere dataimport
  - Brugeren kan oprette ny/nye dataimport via formular
  - Brugeren kan slette dataimport med bekræftelsesdialog

#### [US-042] Manage Statstidendes
- **Story:** Som bruger vil jeg se og søge i statstidendeer, oprette statstidendeer og slette statstidendeer, så jeg kan håndtere og validere adressedata korrekt.
- **Side:** `Pages/addresses/StatstidendesPage.razor`
- **Route:** `/addresses/statstidendes`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over statstidendeer
  - Brugeren kan søge og filtrere statstidendeer
  - Brugeren kan oprette ny/nye statstidendeer via formular
  - Brugeren kan slette statstidendeer med bekræftelsesdialog

#### [US-046] Other Address Operations
- **Story:** Som bruger vil jeg arbejde med miscer, så jeg kan håndtere og validere adressedata korrekt.
- **Side:** `Pages/addresses/AddressOperationsPage.razor`
- **Route:** `/addresses/miscs`
- **Components:** 
- **Acceptkriterier:**

### Økonomi & Drift `/finance` (icon: AccountBalance)

**P3 — Nice-to-have:**

#### [US-008] Manage Sales
- **Story:** Som bruger vil jeg se og søge i salgsdata, oprette salgsdata, redigere salgsdata og slette salgsdata, så jeg kan holde styr på økonomi og driftsprocesser.
- **Side:** `Pages/finance/SalesPage.razor`
- **Route:** `/finance/sales`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over salgsdata
  - Brugeren kan søge og filtrere salgsdata
  - Brugeren kan oprette ny/nye salgsdata via formular
  - Brugeren kan redigere eksisterende salgsdata
  - Brugeren kan slette salgsdata med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove sales record
  - [INFERRED] Bruger: User can view and retrieve sales record
  - [INFERRED] Bruger: User can create and submit sales record
  - [INFERRED] Bruger: User can update sales record

#### [US-010] Manage Salaries
- **Story:** Som bruger vil jeg se og søge i lønsedler, så jeg kan holde styr på økonomi og driftsprocesser.
- **Side:** `Pages/finance/SalariesPage.razor`
- **Route:** `/finance/salarys`
- **Components:** MudDataGrid, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over lønsedler
  - Brugeren kan søge og filtrere lønsedler
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can view and retrieve payroll period

#### [US-011] Manage Absences
- **Story:** Som bruger vil jeg se og søge i fraværsregistreringer, oprette fraværsregistreringer, redigere fraværsregistreringer og slette fraværsregistreringer, så jeg kan holde styr på økonomi og driftsprocesser.
- **Side:** `Pages/finance/AbsencesPage.razor`
- **Route:** `/finance/absences`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over fraværsregistreringer
  - Brugeren kan søge og filtrere fraværsregistreringer
  - Brugeren kan oprette ny/nye fraværsregistreringer via formular
  - Brugeren kan redigere eksisterende fraværsregistreringer
  - Brugeren kan slette fraværsregistreringer med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove employee absence
  - [INFERRED] Bruger: User can view and retrieve employee absence
  - [INFERRED] Bruger: User can modify employee absence
  - [INFERRED] Bruger: User can create and submit employee absence

#### [US-018] Manage Invoices
- **Story:** Som bruger vil jeg se og søge i fakturaer, så jeg kan holde styr på økonomi og driftsprocesser.
- **Side:** `Pages/finance/InvoicesPage.razor`
- **Route:** `/finance/invoices`
- **Components:** MudDataGrid, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over fakturaer
  - Brugeren kan søge og filtrere fakturaer
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can view and retrieve invoice

#### [US-029] Manage Employees
- **Story:** Som bruger vil jeg se og søge i medarbejdere og oprette medarbejdere, så jeg kan holde styr på økonomi og driftsprocesser.
- **Side:** `Pages/finance/EmployeesPage.razor`
- **Route:** `/finance/employees`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over medarbejdere
  - Brugeren kan søge og filtrere medarbejdere
  - Brugeren kan oprette ny/nye medarbejdere via formular
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can view and retrieve employee
  - [INFERRED] Bruger: User can create and submit employee

#### [US-033] Manage Drives
- **Story:** Som bruger vil jeg se og søge i fildrev, oprette fildrev og slette fildrev, så jeg kan holde styr på økonomi og driftsprocesser.
- **Side:** `Pages/finance/DrivesPage.razor`
- **Route:** `/finance/drives`
- **Components:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over fildrev
  - Brugeren kan søge og filtrere fildrev
  - Brugeren kan oprette ny/nye fildrev via formular
  - Brugeren kan slette fildrev med bekræftelsesdialog

#### [US-047] Other Finance Operations
- **Story:** Som bruger vil jeg arbejde med miscer, så jeg kan holde styr på økonomi og driftsprocesser.
- **Side:** `Pages/finance/FinanceOperationsPage.razor`
- **Route:** `/finance/miscs`
- **Components:** 
- **Acceptkriterier:**

### Analyse & Rapportering `/analytics` (icon: Analytics)

**P3 — Nice-to-have:**

#### [US-006] Manage Benchmarks
- **Story:** Som bruger vil jeg se og søge i benchmarks, oprette benchmarks, redigere benchmarks og slette benchmarks, så jeg kan få indsigt i systemaktivitet og performance.
- **Side:** `Pages/analytics/BenchmarksPage.razor`
- **Route:** `/analytics/benchmarks`
- **Components:** MudButton, MudCard, MudChart, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField
- **Acceptkriterier:**
  - Brugeren ser en liste over benchmarks
  - Brugeren kan søge og filtrere benchmarks
  - Brugeren kan oprette ny/nye benchmarks via formular
  - Brugeren kan redigere eksisterende benchmarks
  - Brugeren kan slette benchmarks med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove performance benchmark
  - [INFERRED] Bruger: User can view and retrieve performance benchmark
  - [INFERRED] Bruger: User can modify performance benchmark
  - [INFERRED] Bruger: User can create and submit performance benchmark

#### [US-025] Manage Causes
- **Story:** Som bruger vil jeg oprette årsagskoder, redigere årsagskoder og slette årsagskoder, så jeg kan få indsigt i systemaktivitet og performance.
- **Side:** `Pages/analytics/CausesPage.razor`
- **Route:** `/analytics/causes`
- **Components:** MudButton, MudDialog, MudForm, MudIconButton
- **Acceptkriterier:**
  - Brugeren kan oprette ny/nye årsagskoder via formular
  - Brugeren kan redigere eksisterende årsagskoder
  - Brugeren kan slette årsagskoder med bekræftelsesdialog
- **Behaviors fra sms-service:**
  - [INFERRED] Bruger: User can remove benchmark cause
  - [INFERRED] Bruger: User can create and submit benchmark cause
  - [INFERRED] Bruger: User can update benchmark cause

#### [US-045] Other Analytics Operations
- **Story:** Som bruger vil jeg arbejde med miscer, så jeg kan få indsigt i systemaktivitet og performance.
- **Side:** `Pages/analytics/AnalyticsOperationsPage.razor`
- **Route:** `/analytics/miscs`
- **Components:** 
- **Acceptkriterier:**

