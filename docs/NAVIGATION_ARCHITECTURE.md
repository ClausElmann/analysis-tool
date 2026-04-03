# Navigation Architecture — ServiceAlert (Blazor)

**Dato:** 2026-04-02  
**Kilde:** `docs/ANGULAR_ROUTE_TREE.md` + `docs/NAVIGATION_MODEL.json` + `docs/UI_MODEL_SUPER_ADMIN_CONTEXT.json`  
**Formål:** Autoritativ reference for arkitekt og implementering — Blazor routing og navigationsdesign

---

## 1. Fire uafhængige apps

Systemet består af 4 separate Blazor-apps med distinkt auth og bundle-scope:

| App | URL-base | Auth | Formål | Scope |
|-----|----------|------|--------|-------|
| **Main app** | `/` | Krævet (JWT) | Hele den autentificerede oplevelse | ✅ **Aktiv** |
| **Subscription app** | `/` | Anonym | Borger-enrollment (separat deploy) | ⏸ Udsat |
| **Quick Response app** | `/` | Anonym | SMS-respons widget (separat deploy) | ⏸ Udsat |
| **iFrame Modules** | `/iFrame/...` | Anonym | Indlejrerede driftstatus/abonnement-komponenter | ⏸ Udsat |

> **Beslutning 2026-04-02:** Subscription app, Quick Response og iFrame Modules udsættes. Alt arbejde fokuserer på main app.

---

## 2. Main app — 3 navigationsrum

```
App Shell
├── [ROOM 1]  /                   Root — broadcasting, wizards, status, my-user
├── [ROOM 2]  /admin/             Admin — kundens egne admin-sider
└── [ROOM 3]  /admin/super/       Super Admin — administration af alle kunder
```

De tre rum deler **samme app-shell** men har **forskellig layout og kontekst-mekanik**.

---

## 3. Kontekst-modellen (kritisk for routing-design)

### ROOM 1 + 2 — `profile-implicit`

- Brugeren vælger sin **aktive profil** én gang i app-shell dropdownen
- Profil-kontekst er **global og implicit** — vises ikke på de enkelte sider
- Alle sider læser kontekst fra app-state (`ICurrentUser` eller tilsvarende)
- **Ingen kontekst-dropdowns på sider**

### ROOM 3 — `super-admin-explicit`

- Super-admin arbejder **på vegne af en hvilken som helst kunde**
- En **kontekst-selector-bar** vises øverst på alle super-admin sider:

```
[ Land ▾ ]  [ Kunde ▾ ]  [ Profil ▾ ]
```

- Cascade: land → filtrerer kunde-liste → filtrerer profil-liste
- Profil er **valgfri** på kunde-scopede sider, **påkrævet** på profil-scopede sider
- Kontekst persisteres i `SuperAdminContextState` (scoped service) under sessionen
- Blazor: **separat layout** (`SuperAdminLayout.razor`) med **ét delt context-selector komponent**

### Section → mode mapping

| Section | Mode | Kontekst-selector på sider |
|---------|------|---------------------------|
| `root` | `profile-implicit` | Nej |
| `admin` | `profile-implicit` | Nej |
| `admin/super` | `super-admin-explicit` | Ja — land + kunde + profil |

---

## 4. Sidetyper og dybde

| Type | Eksempel | Max dybde |
|------|---------|-----------|
| **simple** | `/support`, `/terms-and-conditions` | 1 |
| **flow** | `/message-wizard`, `/enrollment` | 2 |
| **workspace/tabs** | `/status`, `/admin/benchmark` | 2–3 |
| **workspace/deep** | `/admin/customer`, `/admin/super/customers` | 3–4 |

---

## 5. Deep linking

### Princip

**Alle navigationspositioner skal være direkte adresserbare via URL** — ingen state der kræver forudgående navigation for at nå en bestemt side.

### Room 1 + 2 — profil-kontekst fra app-state, ikke URL

```
/status/1234/addresses             ✅ deep link — sms-gruppe 1234, addresses-tab
/admin/customer/profiles/7/roles   ✅ deep link — profil 7, roles-tab
```

Profil/kunde-kontekst opløses fra JWT-claims eller app-state ved load. URL bærer kun den indholdsmæssige identitet (entity-id + tab).

### Room 3 — kontekst SKAL kodes i URL

Super-admin deep links bærer kontekst som **query parameters**:

```
/admin/super/users?countryId=1&customerId=42&profileId=7
/admin/super/customers/42/contact-persons?countryId=1
/admin/super/benchmark?countryId=1&customerId=42&profileId=7
```

Ved direkte navigation: URL-params → seed `SuperAdminContextState` → indlæs kontekst-dropdowns i korrekt tilstand → indlæs side-data.

### Wizards — step som URL-segment

```
/message-wizard/by-address       Trin 1 (valg af modtager-metode)
/message-wizard/write-message    Trin 2
/message-wizard/confirm          Trin 3
/message-wizard/complete         Trin 4
```

Direkte link til `/message-wizard/confirm` uden gyldig wizard-state → redirect til `/broadcasting`.  
Wizard-data (valgte modtagere, besked-draft) lever **ikke** i URL — server-side eller session-state.

### iFrame Modules — ingen legacy deep linking

iFrame-appen i Angular bruger imperativ path-matching ved startup — ingen router-baseret deep linking inden i komponenter. **Blazor-versionen skal bruge standard `@page`-routing** — dette er en forbedring i forhold til legacy.

---

## 6. Blazor Routing Skelet

```
[AppLayout — alle rum]
  /                              → FrontPage
  /login                         → Login
  /transparent-login             → TransparentLogin
  /reset-password                → PasswordReset
  /new-password                  → PasswordReset (step 2)
  /terms-and-conditions          → TermsAndConditions
  /support                       → Support
  /unavailable                   → Unavailable

[MainLayout — Room 1, kræver auth]
  /broadcasting                             → Broadcasting (primær post-login hub — UNKNOWN intern struktur)
  /broadcasting-limited                     → BroadcastingLimited
  /create-message                           → MessageWizardLimited
  /message-wizard/{step}                    → MessageWizard flow
  /message-wizard-scheduled/{step}          → MessageWizardScheduled flow
  /message-wizard-stencil/{step}            → MessageWizardStencil flow (same UI, isCreatingStencil=true)
  /status                                   → StatusList
  /status/{smsGroupId}                      → StatusDetail (default tab: overview)
  /status/{smsGroupId}/{tab}                → StatusDetail tab (overview|addresses|statusReport|message-content)
  /my-user/{tab}                            → MyUser (user-infoEdit|security)
  /sms-conversations                        → SmsConversations
  /pipeline                                 → PipelineDashboard (SuperAdmin only)
  /pipeline/prospects                       → ProspectList
  /pipeline/prospects/{prospectId}/{tab}    → ProspectDetail (edit-info|edit-tasks)
  /pipeline/create-customer/{prospectId}    → CreateCustomerByProspect
  /pipeline/edit-termination/{customerId}   → EditTermination
  /pipeline/edit-process-tasks/{processType}/{customerId} → EditProcessTasks

[AdminLayout — Room 2, kræver auth + admin-rolle]
  /admin/customer                            → CustomerAdmin (tab: settings)
  /admin/customer/{tab}                      → CustomerAdmin tab (settings|users|profiles|social-media|gdpr|sms-conversations)
  /admin/customer/users/create               → CreateUser form
  /admin/customer/users/{userId}/{tab}       → UserDetail (user-profiles|user-roles)
  /admin/customer/profiles/create            → CreateProfile form
  /admin/customer/profiles/{profileId}/{tab} → ProfileDetail (info|roles|account|api-keys|users|map|social-media|email2sms|ready-reports|statstidende|ftp-setup|distribution)
  /admin/benchmark/{tab}                     → Benchmark
  /admin/benchmark/edit/{id}                 → BenchmarkEdit
  /admin/std-receivers-setup/{tab}           → StdReceiversSetup
  /admin/message-templates/{tab}             → MessageTemplates
  /admin/message-examples                    → MessageExamples
  /admin/searching/{tab}                     → Searching
  /admin/statstidende/{tab}                  → Statstidende
  /admin/web-messages/{tab}                  → WebMessages
  /admin/subscribe-unsubscribe/{tab}         → SubscribeUnsubscribe
  /admin/scheduled-broadcasts/{tab}          → ScheduledBroadcasts
  /admin/critical-addresses/{tab}            → CriticalAddresses
  /admin/file-management/{tab}               → FileManagement
  /admin/internal-reports/{tab}              → InternalReports (SuperAdmin only — anomali: ingen super/-prefix)

[SuperAdminLayout — Room 3, kræver auth + SuperAdmin-rolle]
  Alle sider har context selector: ?countryId=&customerId=&profileId=

  /admin/super/translations                          → Translations
  /admin/super/log                                   → Log
  /admin/super/communication/{tab}                   → Communication
  /admin/super/pos-lists/{tab}                       → PosLists
  /admin/super/customers                             → CustomerList
  /admin/super/customers/create                      → CreateCustomer form
  /admin/super/customers/{id}/{tab}                  → CustomerDetail (profiles|users|settings|admin|ftpSettings|api-keys|gdpr|contact-persons)
  /admin/super/customers/{id}/contact-persons/create → CreateContactPerson
  /admin/super/customers/{id}/contact-persons/{contactId} → EditContactPerson
  /admin/super/users                                 → UserList
  /admin/super/users/{id}/{tab}                      → UserDetail (data|subscriptions)
  /admin/super/settings/{tab}                        → Settings
  /admin/super/invoicing/{tab}                       → Invoicing
  /admin/super/phonenumberproviders/{tab}             → PhoneNumberProviders
  /admin/super/phonenumberproviders/providers/create  → CreateProvider
  /admin/super/phonenumberproviders/providers/{id}    → ProviderDetail
  /admin/super/monitoring/{tab}                      → Monitoring
  /admin/super/enrollment/{tab}                      → EnrollmentManagement
  /admin/super/enrollment/senders/create             → CreateSender
  /admin/super/enrollment/senders/{id}               → EditSender
  /admin/super/hr/{tab}                              → HumanResources
  /admin/super/salesforce/{tab}                      → Salesforce
  /admin/super/inboundCall/{phone}                   → InboundCallRedirect
  /admin/super/mapLayers                             → MapLayerList
  /admin/super/mapLayers/{id}/access                 → MapLayerAccess

[iFrame apps — ⏸ UDSAT]
[Subscription app — ⏸ UDSAT]
[Quick Response app — ⏸ UDSAT]

  Se docs/ANGULAR_ROUTE_TREE.md for komplet routes når disse apps sættes i gang.
```

---

## 7. Nøgle-designbeslutninger

| # | Beslutning | Begrundelse |
|---|-----------|-------------|
| 1 | **Tab-navigation = URL-segment** | Back-knap og deep links virker uden ekstra state |
| 2 | **SuperAdminContextState er scoped service** | Persister under session, URL seeder state ved reload (ikke URL-only) |
| 3 | **Same capability, two contexts = ét komponent** | Fx "users" er ét Blazor-komponent der modtager `customerId` som parameter. Layout (AdminLayout vs SuperAdminLayout) bestemmer kilden — ikke komponentet |
| 4 | **Wizard-state = server-side eller session** | Steps har URL, men data (valgte modtagere, besked-draft) lever ikke i URL |
| 5 | **iFrame Modules → standard `@page` routing** | Legacy Angular-versionen har ingen router — Blazor-versionen forbedrer dette og muliggør deep linking |
| 6 | **Super-admin deep links bærer context som query params** | `?countryId=X&customerId=Y&profileId=Z` — bookmarkable og shareable |
| 7 | **`/admin/internal-reports` uden `super/`-prefix** | Bevaret som anomali fra legacy — kan rettes til `/admin/super/internal-reports` i Blazor |

---

## 8. Afklaret — tidligere UNKNOWN

### `/broadcasting` — intern struktur (AFKLARET)

3-kolonne layout (flex-row på large screens):

```
[ send-methods-list ]  [ scenarios ]  [ bi-tabs: single-sms / single-email ]
```

| Blok | Komponent | Indhold | Synlighed |
|------|-----------|---------|-----------|
| **Send-metoder** | `SendMethodsListComponent` | Icon-grid: afsendelsesmetoder (ByAddress, ByMap, ByExcel, ByLevel, ByMunicipality, ByStdReceivers) — hvert klik åbner wizard på den tilsvarende step | Altid (konfigureret pr. profil-roller) |
| **Scenarios** | `ScenariosComponent` | Liste af gemte besked-skabeloner — klik starter wizard med pre-fill | Kun hvis `showScenarios` |
| **Enkelt-send** | `BiTabsComponent` → `SingleSmsComponent` / `SingleEmailComponent` | Hurtig afsendelse uden wizard, tab-switch (Sms / E-mail) | Kræver rolle `CanSendSingleSmsAndEmail` + `customerAutosignature != null` |

**Under 3-kolonne layout** — besked-historik boks:

| Panel | Data | Synlighed |
|-------|------|-----------|
| Sendte beskeder | `broadcastingMessages.sentMessages` | Altid |
| Planlagte beskeder | `broadcastingMessages.plannedMessages` | Altid |
| Godkendelseskø | `broadcastingMessages.unapprovedMessages` | Kun hvis bruger er `SmsGroupApprover` |
| Ufærdige beskeder | `broadcastingMessages.unfinishedMessages` | Altid |

Broadcasting reagerer på `profileChanged$` event og gen-initialiserer rettigheder og tabs.

---

### Wizard-state persistens (AFKLARET)

**State lever i `WizardSharedService` (Angular in-memory service, modul-scopet)**

- Holds: `smsGroupId`, `currentSendMethod`, `currentMessage$`, `scheduledBroadcast`, `messageNameControl`, adressevalg, mv.
- State er **ikke** server-side og **ikke** localStorage (undtagelse: map-layers-siden bruger localStorage til sit eget land-valg)
- State forsvinder ved navigation væk eller page refresh
- Direkte deep link til et step ≠ trin 1:
  - `complete`-stepet har `canMatch` guard: kun tilgængeligt hvis forrige URL var `/confirm`
  - Andre trin: guard tjekker om URL er eksakt wizard-root → redirect til `/broadcasting`  
  - Undtagelse: `?smsGroupId=X` query param → wizard indlæser eksisterende besked fra server (server-state som seed)

**Blazor-implikation:** Wizard-state implementeres som scoped/transient Blazor-service. Ingen URL-state bortset fra step-segment og evt. `?smsGroupId`. Direkte access til step > 1 → `NavigationManager.NavigateTo("/broadcasting")`.

---

### Super-admin kontekst-selector (AFKLARET — vigtig korrektion)

**Angular-virkelighed:** Der er INGEN global kontekst-bar i layoutet.  
`BiCountryCustomerProfileSelectionComponent` er en **delt komponent der embeddes per side**, ikke i et fælles super-admin layout.

```csharp
// Komponent-interface:
showCountrySelection: input<boolean>   // default: true
showCustomerSelection: input<boolean>  // default: true
showProfileSelection: input<boolean>   // default: true
profileRequired: input<boolean>
customerRequired: input<boolean>
requireCountry: input(true)
```

**Scope pr. super-admin side:**

| Side | Land | Kunde | Profil |
|------|------|-------|--------|
| `users` | ✅ | ✅ | ✅ |
| `settings` | ✅ | ✅ | ✅ |
| `salesforce` | ✅ | ✅ | ✅ |
| `hr/holidays` | ✅ | ✅ | ✅ |
| `pos-lists/data-import` | ✅ | ✅ | ✅ |
| `pos-lists/municipality-setup` | ✅ | ✅ | ✅ |
| `map-layers/access` | ✅ | ✅ | ✅ |
| `map-layers` (liste) | ✅ | ❌ | ❌ |
| `customers` | ✅ (global state) | ✅ (global state) | ❌ |

**Persistens i Angular:** Ingen delt cross-page state. Map-layers gemmer land i `localStorage("mapLayersSelectedCountry")`. Alle andre sider nulstiller kontekst ved navigation.

**Blazor-design-beslutning (afvigelse fra legacy — forbedring):**  
Centralisér som `SuperAdminContextState` (scoped service) med layout-niveau kontekst-bar i `SuperAdminLayout.razor`. Dette er en **architectural improvement** — Angular-versionen har inkonsistent state fordi der ingen central koordinering er. URL-encoding som query params giver deep-link og browser-back support.

---

### Stadig uafklaret

4. **`/enrollment-dashboard`** — refereret i kode, ingen route fundet
5. **Subscription-app `/login` og `/unsubscribe-sender`** — intern struktur ukendt
6. **Profil-dropdown og super-admin kontekst** — kan super-admin arbejde med sin egen kundes profil og undgå konflikt med global profil-dropdown?

---

## 9. App Shell / Chrome

Dokumenterer den faktiske synlige navigationsstruktur — hvad Blazor-layoutet skal implementere.

### Header (top-bar, alle layouts)

```
[ ≡ (mobile) ]  [ LOGO → /broadcasting ]  [ Profil-dropdown (desktop) ]  [ Bruger-ikon ▾ ]
```

| Element | Synlighed | Funktion |
|---------|-----------|----------|
| Hamburger `≡` | Mobile only | Åbner slide-in left-nav |
| Logo | Altid | Navigerer til `/broadcasting` |
| Profil-dropdown | Desktop only, kun hvis profil eksisterer | Skifter aktiv profil → opdaterer alle Room 1+2 sider |
| Bruger-ikon | Altid (logget ind) | Åbner popover med user-menu |
| Login-knap | Kun ulogget | Åbner login-flow |

**User-menu popover indhold:**
1. Brugernavn (display only)
2. Link → `/my-user` (Min bruger)
3. Test-mode toggle (kun hvis tilladt)
4. Link → `/terms-and-conditions`
5. Profil-dropdown (mobile only — spejl af header-dropdown)
6. Logout

### Venstre navigationslinje (main app, desktop)

Vertikal bar, 6rem bred, icon + label pr. item:

| Item | Icon | Route | Synlighed |
|------|------|-------|-----------|
| Broadcasting | `fa-envelope` | `/broadcasting` eller `/broadcasting-limited` | Altid (wenn profil eksisterer) |
| SMS-samtaler | `fa-comments` | `/sms-conversations` | Kun hvis `userHasAProfileWithConversations` |
| Status | `fa-chart-column` | `/status` | Kræver rolle: `ManageReports` |
| Administration | `fa-wrench` | `/admin/customer` | Skjult for `LimitedUser` |
| Support | `fa-headset` | `/support` | Altid |
| Pipeline | `fa-archive` | `/pipeline` | Kræver rolle: `SuperAdmin` |

**`LimitedUser`-rolle skjuler:** SMS-samtaler, Status, Administration, Pipeline.

**SMS-samtaler badge:** Viser antal ulæste beskeder (live-opdateret via SSE).

### Intern workspace-navigation (`bi-menu` komponent)

Bruges inde i workspaces (Room 2+3) til at navigere mellem sektioner. 2-niveau hierarki:

```
[ Header-item ]
  ├── [ Child item — clickCommand ]
  ├── [ Child item — clickCommand ]
  └── [ Child item — clickCommand ]
```

`BiMenuItem` interface: `label`, `icon`, `isHeader`, `childItems[]`, `clickCommand`.  
Tab-tekst max 40 tegn (truncated i UI). Dette er **ikke** router-navigation — det er komponent-state/tab-skift.

### Mobile adaptation

| Element | Desktop | Mobile |
|---------|---------|--------|
| Venstre nav | Altid synlig (6rem) | Skjult bag hamburger |
| Profil-dropdown | I header | I user-menu popover |
| Navigation-bar animation | slideInFromLeft | slideInFromLeft (slide-in overlay) |

---

## 10. Relaterede filer

| Fil | Indhold |
|-----|---------|
| `docs/ANGULAR_ROUTE_TREE.md` | Komplet udtrukket Angular route-struktur (kilde) |
| `docs/NAVIGATION_MODEL.json` | Domæne-navigationmodel inkl. `context_model` |
| `docs/UI_MODEL_SUPER_ADMIN_CONTEXT.json` | Detaljeret super-admin kontekst-selector model |
| `docs/UI_MODEL_CUSTOMER_ADMIN.json` | Full + light UI model for customer-admin capability |
