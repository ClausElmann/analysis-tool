# ServiceAlert — Komplet Arkitektrapport (30. marts 2026)

> Baseret på dybdegående scanning af hele `c:\Udvikling\sms-service` med særligt fokus på Angular-frontenden.
> Senest opdateret: 30. marts 2026 — DomainEngine v3 tilføjet (sektion 22), testantal opdateret til 762.

---

## 1. Pipeline — Final Status

### Slice-resultater

| Slice | Status | Items | Output-fil | Indhold |
|---|---|---|---|---|
| SLICE_0 | OK | 36 | `solution_structure.json` | Projektklassificering |
| SLICE_0_5 | OK | 3 | `wiki_signals.json` | Wiki-signaler |
| SLICE_0_7 | OK | 41 | `pdf_capabilities.json` | PDF-kapabiliteter |
| SLICE_0_8 | OK | 3395 | `git_insights.json` | Git-historik |
| SLICE_9 | OK | 447 | `db_schema.json` | DB-skema (tabeller, procedures, views, funktioner, typer) |
| SLICE_11 | OK | 115 | `label_map.json` | i18n namespaces |
| SLICE_1 | OK | 69 | `angular_entries.json` | Angular-ruter |
| SLICE_1b | OK | 14 | `angular_apps.json` | iFrame/sub Angular apps (3 sub-apps) |
| SLICE_1c | OK | 63 | `mvc_routes.json` | ServiceAlert.Web REST API controllers |
| SLICE_2 | OK | 4 | `component_api_map.json` | Komponent→API |
| SLICE_3 | OK | **57** | `api_db_map.json` | REST API→DB |
| SLICE_3b | OK | **8** | `webhook_map.json` | Inbound webhooks |
| SLICE_6 | OK | 11622 | `work_item_analysis.json` | Work items |
| SLICE_12 | OK | **11** | `background_services.json` | Background services |
| SLICE_13 | OK | **135** | `batch_jobs.json` | Batch jobs |
| SLICE_14 | OK | **30** | `event_map.json` | MediatR events |
| SLICE_15 | OK | 51 | `integrations.json` | Externe HTTP-integrationer |
| SLICE_16 | OK | **6** | `realtime_map.json` | SSE streams |
| SLICE_17 | OK | 6 | `rabbitmq_topology.json` | RabbitMQ-topologi |
| SLICE_7 | OK | **66** | `system_model.json` | System model (REST) |
| SLICE_8 | OK | **68** | `use-cases.analysis.json` | Use cases |
| SLICE_10 | OK | **5074** | `gap_analysis.json` | Gap-analyse |
| SLICE_7b | OK | **66** | `system_model_extended.json` | Fuldt fusioneret model |

**Total: 23 slices — 23 OK — 0 fejl — final_report.json status: `READY_FOR_AUDIT`**

### Fuld system model — coverage

| Flow-type | Ekstraheret | Koblet til modul |
|---|---|---|
| Batch jobs | 135 | 25 |
| Webhooks | 8 | 2 |
| MediatR events | 30 | 15 |
| Background services | 11 | 1 |
| SSE streams | 6 | 1 |
| **Use cases total** | **137** | — |

> Coverage vurderet som **LOW** — korrekt og forventet. ~70 % af systemets operationelle logik (batch, queue, events) kører uden Angular-modstykke og kan ikke matches mod rute-centrerede modulnavne.

### Use case type-fordeling

| Type | Antal |
|---|---|
| `ui` | 68 |
| `event` | 28 |
| `batch` | 16 |
| `async` | 11 |
| `webhook` | 8 |
| `realtime` | 6 |
| **Total** | **137** |

### Unit-tests

```
platform win32 -- Python 3.11.9, pytest-9.0.2
762 passed in 30.18s
```

### Output-filer (25 filer)

| Fil | Items | Key |
|---|---|---|
| `solution_structure.json` | 36 | projects |
| `wiki_signals.json` | 3 | capabilities |
| `pdf_capabilities.json` | 41 | capabilities |
| `git_insights.json` | 3395 | insights |
| `db_schema.json` | 447 | tables (319) + procedures (99) + views (3) + functions (8) + UDTs (18) |
| `label_map.json` | 115 | namespaces |
| `angular_entries.json` | 69 | entry_points |
| `angular_apps.json` | 3 | apps (3 sub-apps, 14 routes total) |
| `mvc_routes.json` | 63 | mvc_routes |
| `component_api_map.json` | 4 | mappings |
| `api_db_map.json` | 57 | mappings |
| `webhook_map.json` | 8 | webhooks |
| `background_services.json` | 11 | services |
| `batch_jobs.json` | 135 | jobs |
| `event_map.json` | 30 | events |
| `integrations.json` | 51 | integrations |
| `realtime_map.json` | 6 | streams |
| `rabbitmq_topology.json` | 6 | exchanges+queues+bindings+publishers+consumers |
| `work_item_analysis.json` | 11622 | features |
| `system_model.json` | 66 | modules |
| `system_model_extended.json` | 66 | modules |
| `use-cases.analysis.json` | 68 | use_cases |
| `use-cases.selection.json` | 6 | use_cases |
| `gap_analysis.json` | 5074 | gaps |
| `final_report.json` | — | READY_FOR_AUDIT |

---

## 2. Frontend — Angular 20 App (SmsServiceWebApp)

### Tech stack

| Teknologi | Version | Bemærkning |
|---|---|---|
| Angular | **20.0.6** | Standalone components + lazy-loaded modules |
| Angular CDK | 20.0.6 | |
| @azure/msal-angular | 4.0.14 | Azure AD SSO |
| @azure/msal-browser | 4.14.0 | |
| Leaflet + ngx-leaflet | 18.0.1 | Kortvisning |
| @asymmetrik/leaflet-d3 | 6.0.1 | D3 på kort |
| Angular Material | 20.0.x | UI-komponenter |
| Server-Sent Events (SSE) | — | `Lib.AspNetCore.ServerSentEvents` |

#### Andre Angular projekter i same workspace

| Projekt | Startkommando | Formål |
|---|---|---|
| `SmsServiceWebApp` | `ng serve --project SmsServiceWebApp` | Hoved-appen |
| `SubscriptionApp` | port 4201 | Selvstændig tilmeldings-app |
| `iFrameModules` | port 4202 | iFrame-moduler til driftstatus |
| `QuickResponse` | port 4203 | Hurtig-svar app |

---

## 3. Frontend — Komplet Ruteoversigt

### Top-niveau ruter (features-routing.module.ts)

| Rute | Lazy modul / komponent | Guard(s) | Rolle |
|---|---|---|---|
| `/login` | `BiLoginComponent` | — | Alle |
| `/transparent-login` | `TransparentLoginComponent` | — | Alle |
| `/reset-password` | `PasswordResetCreateComponent` | AppCanActivate | Alle |
| `/new-password` | `PasswordResetCreateComponent` | AppCanActivate | Alle |
| `/terms-and-conditions` | `TermsAndConditionsComponent` | — | Alle |
| `/broadcasting` | `BroadcastingModule` | limitedUserGuard(true) | Normale brugere |
| `/broadcasting-limited` | `BroadcastingLimitedComponent` | limitedUserGuard(false) | Begrænsede brugere |
| `/messages/create` | `MessageWizardLimitedComponent` | limitedUser + WizardGuard | Begrænsede brugere |
| `/messages/wizard` | `MessageWizardModule` | ManageMessages + limitedUser | Fuld adgang |
| `/messages/wizard-scheduled` | `MessageWizardScheduledModule` | ManageMessages | Planlagte |
| `/messages/wizard-stencil` | `MessageWizardScheduledModule` | ManageMessages | Skabelon-udsendelse |
| `/my-user` | `my-user.routes` | — | Indlogget bruger |
| `/support` | `SupportComponent` | — | Alle |
| `/status` | `status.routes` | ManageReports | Rapportadgang |
| `/sms-conversations` | `SmsConversationsModule` | ProfileRole: SmsConversations | Profil-rolle |
| `/admin` | `AdministrationModule` | limitedUser(true) | Admins |
| `/pipeline` | `PipelineModule` | SuperAdmin | SuperAdmin |
| `**` | redirect → `/broadcasting` | — | Fallback |

---

## 4. Frontend — Detaljeret Feature-område oversigt

### 4.1 Broadcasting (`/broadcasting`)

Hoved-dashboard for udsendelse. To varianter:
- **Fuld bruger:** `BroadcastingModule` — alle sendemetoder
- **Begrænset bruger:** `BroadcastingLimitedComponent`

Underkomponenter:
- `ScenariosComponent` — vælger sendemetode (SMS, Voice, e-Boks, Web, Facebook, Twitter)
- `SingleSmsEmailComponent` — hurtig enkelt-SMS/email
- `UnapprovedMsgBoxComponent` — venter-på-godkendelse-kasse
- `CustomerSurveyNudgeDialogComponent` — spørgeskema-nudge dialog

**Profil-roller der tjekkes her:**

| Rolle | Effekt |
|---|---|
| `CanSendByVoice` | Voice-kanal synlig |
| `CanSendByEboks` | e-Boks-kanal synlig |
| `CanSendByWeb` | Web-besked synlig |
| `CanSendByWebInternal` | Intern web-kanal synlig |
| `CanPostOnFacebook` | Facebook-kanal synlig |
| `CanTweetOnTwitter` | Twitter/X-kanal synlig |
| `SmsConversations` | Samtale-fane synlig |
| `AlwaysCanReceiveSmsReply` | SMS-svar altid aktiv |
| `AlwaysDelayed` | Altid forsinket udsendelse |
| `DontSendEmail` | Email skjult |

---

### 4.2 Message Wizard (`/messages/wizard`)

Multi-step guide til oprettelse af beskeder.

#### Wizard-trin (child routes):

| Sti | Komponent | Guard/Krav |
|---|---|---|
| `/by-address` | ByAddressComponent | `CanSendByAddressSelection` + ikke SmsLogs-metode |
| `/by-excel` | ByExcelComponent | `CanUploadStreetList` + ikke SmsLogs-metode |
| `/by-map` | ByMapComponent | `CanSendByMap` + ikke SmsLogs-metode |
| `/by-level` | ByLevelComponent | — |
| `/by-municipality` | ByMunicipalityComponent | — |
| `/std-receivers` | StdReceiversComponent | Ikke SmsLogs-metode |
| `/std-receivers-ext` | StdReceiversExtendedComponent | `StdReceiverExtended` |
| `/write-message` | WriteMessageWizardStepComponent | — |
| `/confirm` | ConfirmComponent | — |
| `/complete` | BroadcastCompleteComponent | canDeactivate-guard |

**Confirm-step tjekker yderligere roller:**

| Rolle | Effekt |
|---|---|
| `CanSendByMap` | Kortvisning i bekræftelsestrin |
| `CanSelectStdReceivers` | Standardmodtagere vises |
| `CanSpecifyLookup` | Ejer/adresse-info synlig |
| `CanSelectLookupBusinessOrPrivate` | Erhverv/privat-valg synlig |
| `CanSendToCriticalAddresses` | Kritiske adresser tilladt |

#### Scheduled Wizard (`/messages/wizard-scheduled`):

| Trin | Komponent |
|---|---|
| Skriv besked | `WriteScheduledMessageComponent` |
| Planlæg | `MessageSchedulingSetupComponent` |
| Bekræft | `ConfirmScheduledComponent` |

---

### 4.3 Administration (`/admin`)

meget stor feature-area. Tilgængelig for normale admins (ikke LimitedUser).

#### Sub-features:

| Sub-rute | Modul/Komponent | UserRole-krav |
|---|---|---|
| `/admin/benchmark` | `BenchmarkModule` | `Benchmark` |
| `/admin/scheduled-broadcasts` | ScheduledBroadcastsComponent | `CanCreateScheduledBroadcasts` |
| `/admin/std-receivers-setup` | StdReceiversAdminModule | `StandardReceivers` |
| `/admin/customer` | CustomerAdminModule | `CustomerSetup` |
| `/admin/searching` | SearchingComponent | `Searching` |
| `/admin/message-examples` | MessageExamplesComponent | — |
| `/admin/statstidende` | StatstidendeComponent | `CanSetupStatstidende` |
| `/admin/web-messages` | WebMessagesModule | `WEBMessages` |
| `/admin/subscribe-unsubscribe` | Subscribe/UnsubscribeModule | `SubscriptionModule` |
| `/admin/message-templates` | MessageTemplatesModule | `MessageTemplates` |
| `/admin/critical-addresses` | CriticalAddressesModule | `CanManageCriticalAddresses` |
| `/admin/file-management` | FileManagementComponent | — |

---

### 4.4 Benchmark (`/admin/benchmark`)

Komplet ydelsesmålingsmodul. Undersider:

| Rute | Indhold |
|---|---|
| `/index` | Oversigt over alle benchmark-kampagner |
| `/create` | Opret ny benchmark |
| `/edit/:id` | Rediger eksisterende |
| `/statistics` | Statistik og grafer |
| `/kpis` | KPI-visning |
| `/administration` | Årsager og konfiguration |
| `/overview` | Samlet overblik |
| `/settings` | Indstillinger |

---

### 4.5 Standard Receivers (`/admin/std-receivers-setup`)

Håndterer standardmodtagergrupper og abonnements-notifikationer.

| Rute | Indhold |
|---|---|
| `/std-receivers/:receiverId/info` | Modtager-info |
| `/std-receivers/:receiverId/grouping` | Gruppering |
| `/std-receivers/:receiverId/profile-access` | Profiladgang |
| `/receiver-groups/:groupId/info` | Gruppe-info |
| `/receiver-groups/:groupId/members` | Gruppemedlemmer |
| `/receiver-groups/:groupId/profile-access` | Profiladgang |
| `/profile-mapping` | Profil-mapping |
| `/receiver-upload` | Upload modtagere |
| `/subscription-module` | Abonnementsmodul opsætning |
| `/keywords-module` | Keyword-opsætning |
| `/ad-provisioning` | Active Directory provisioning |

---

### 4.6 Customer Admin (`/admin/customer`)

| Rute | Indhold |
|---|---|
| `/settings` | Kundeindstillinger |
| `/users` | Brugerstyring |
| `/users/create` | Opret bruger |
| `/users/:userId/user-profiles` | Bruger→profil-mapping |
| `/users/:userId/user-roles` | Brugerroller |
| `/profiles` | Profilliste |
| `/profiles/create-profile` | Opret profil |
| `/profiles/edit-profile/:id/info` | Profil-info |
| `/profiles/edit-profile/:id/roles` | Profil-roller |
| `/profiles/edit-profile/:id/account` | Konto-indstillinger |
| `/profiles/edit-profile/:id/api-keys` | API-nøgler |
| `/profiles/edit-profile/:id/users` | Tilknyttede brugere |
| `/profiles/edit-profile/:id/map` | Kortadgang |
| `/profiles/edit-profile/:id/social-media` | Sociale medier |
| `/profiles/edit-profile/:id/email2sms` | Email-til-SMS opsætning |
| `/profiles/edit-profile/:id/ready-reports` | Ready-rapporter |
| `/profiles/edit-profile/:id/statstidende` | Statstidende-adgang |
| `/profiles/edit-profile/:id/ftp-setup` | FTP-opsætning |
| `/profiles/edit-profile/:id/distribution` | Distribution til std. modtagergrupper |
| `/social-media` | Kundernes sociale medier |
| `/gdpr` | GDPR-accept administration |
| `/sms-conversations` | SMS-samtale-administration |

---

### 4.7 Web Messages (`/admin/web-messages`)

iFrame-baserede driftstatusmoduler til integration på kundernes egne hjemmesider.

| Rute | Indhold |
|---|---|
| `/messages` | Webbesked-oversigt |
| `/iFrame-driftstatus` | iFrame preview (driftstatus) |
| `/iFrame-driftstatus-map` | iFrame preview (kort) |
| `/iFrame-driftstatus-setup` | iFrame opsætning (driftstatus) |
| `/iFrame-driftstatus-map-setup` | iFrame opsætning (kort) |

---

### 4.8 Message Templates (`/admin/message-templates`)

| Rute | Indhold |
|---|---|
| `/templates` | Beskedskabeloner |
| `/merge-fields` | Merge-felter |
| `/template-access` | Skabelon-adgangsstyring |
| `/weather-warnings` | Vejrvarslings-skabeloner |
| `/warning-templates` | Advarselsskabeloner |
| `/trimble-templates` | Trimble-integration skabeloner |

---

### 4.9 Super Administration (`/admin/super/*`)

Kun tilgængelig for brugere med `SuperAdmin`-rollen.

#### Super-admin under-moduler:

| Rute | Modul | Indhold |
|---|---|---|
| `/admin/super/monitoring` | MonitoringModule | System-sundhed, kort, job-oversigt |
| `/admin/super/enrollment` | EnrollmentModule | Afsendere, statistik, rapporter |
| `/admin/super/hr` | HumanResourceModule | Ansatte, fravær, kørsel, ferie, løn |
| `/admin/super/salesforce` | SalesforceModule | Salgsmuligheder, pipeline, forecast |
| `/admin/super/invoicing` | InvoicingModule | Fakturaer, e-conomic, periodisering |
| `/admin/super/customers` | SuperCustomersModule | Alle kunder, opret, detaljer |
| `/admin/super/prospects` | ProspectsModule | Prospekter/pipeline |
| `/admin/super/pos-lists` | PosListsModule | Positive lister, kommune-opsætning |
| `/admin/super/communication` | CommunicationModule | Operationelle beskeder, nyhedsbreve, DPA |
| `/admin/super/mapLayers` | MapLayersModule | Kortlag og adgangsstyring |
| `/admin/super/users` | UsersModule | Alle brugere på tværs af kunder |
| `/admin/super/settings` | SettingsModule | Pakker, funktioner, salgsinfo |
| `/admin/super/phonenumberproviders` | PhoneProviderModule | SMS-gatewayers og import |
| `/admin/super/translations` | TranslationMgmtComponent | i18n-oversættelser |
| `/admin/super/log` | LogComponent | System-log |
| `/internal-reports` | InternalReportsModule | Virtuelle numre, AD-failures, nudging |

---

### 4.10 Monitoring (`/admin/super/monitoring`)

| Rute | Indhold |
|---|---|
| `/dashboard` | Real-time system-dashboard |
| `/map` | Geografisk jobvisning på kort |
| `/nodeJobs` | Node-job oversigt |

---

### 4.11 Invoicing (`/admin/super/invoicing`)

| Rute | Indhold |
|---|---|
| `/economic-transfer` | e-Conomic overførsel |
| `/framweb-export` | FramWeb-eksport |
| `/load-invoices` | Indlæs fakturaer |
| `/accrual` | Periodisering |
| `/summary` | Opsummering |
| `/budget-follow-up` | Budgetopfølgning |
| `/product-catalog` | Produktkatalog |
| `/mappings` | Mapping-konfiguration |
| `/upload` | Upload fakturaer |

---

### 4.12 Human Resources (`/admin/super/hr`)

| Rute | Indhold |
|---|---|
| `/absences` | Fraværsregistrering |
| `/driving` | Kørselsgodtgørelse |
| `/holidays` | Ferie og fridage |
| `/salary` | Lønopgørelser |
| `/employees` | Medarbejderoversigt |

---

### 4.13 Salesforce (`/admin/super/salesforce`)

| Rute | Indhold |
|---|---|
| `/opportunities/forecast-evaluation` | Forecast-evaluering |
| `/opportunities/pipeline` | Salgspipeline |
| `/opportunities/development` | Salgsprogress |
| `/opportunities/modified` | Senest ændrede muligheder |

---

### 4.14 Positive Lister (`/admin/super/pos-lists`)

| Rute | Indhold |
|---|---|
| `/upload-pos-list` | Upload ny positiv liste |
| `/municipality-setup` | Kommune-opsætning |
| `/uploaded-pos-lists` | Uploadede lister |
| `/positive-lookup` | Positiv opslag |
| `/negative-list` | Negativ liste (opt-out) |
| `/import-corrections` | Import-korrektioner |
| `/import-fof-corrections` | FOF-korrektioner |
| `/additional-import-addresses` | Ekstra import-adresser |
| `/index` | Oversigt |

---

### 4.15 Status (`/status`)

| Rute | Krav | Indhold |
|---|---|---|
| `/:smsGroupId/overview` | ManageReports | Besked-overblik |
| `/:smsGroupId/addresses` | ManageReports | Modtager-adresser |
| `/:smsGroupId/statusReport` | ManageReports | Statusrapport |
| `/:smsGroupId/message-content` | ManageReports | Beskedindhold |

---

### 4.16 SMS Conversations (`/sms-conversations`)

Kræver profil-rolle `SmsConversations`.

- Samtaleoversigt per telefonnummer
- `ConversationItemComponent` — enkelt samtale
- `ConversationMessagesViewComponent` — besked-thread
- `CreateConversationDialogContent` — ny samtale dialog
- SSE-baseret real-time opdatering via `ConversationUnreadStatusChangedListener`
- Groups: `ConversationUnreadStatus/{id}`, `ConversationCreated/{id}`, `ConversationMessageSent/{id}`

---

### 4.17 Pipeline (`/pipeline`)

Kun SuperAdmin. CRM-lignende prospekt- og kundestyring.

| Rute | Indhold |
|---|---|
| `/prospects` | Prospekt-oversigt |
| `/prospects/create` | Opret prospekt |
| `/prospects/:prospectId/edit-info` | Rediger info |
| `/prospects/:prospectId/edit-tasks` | Rediger opgaver |
| `/create-customer` | Opret kunde fra prospekt |
| `/edit-termination` | Opsigelsesflow |
| `/edit-process-tasks` | Procesopgaver |

---

### 4.18 Searching (`/admin/searching`)

| Rute | Indhold |
|---|---|
| `/phone-email` | Søg på telefon/email |
| `/address` | Adressesøgning |
| `/report` | Søgerapport |

---

### 4.19 My User (`/my-user`)

- Personlig brugerinfo-redigering
- Sikkerhedsindstillinger (password, 2FA)

---

### 4.20 Subscribe/Unsubscribe (`/admin/subscribe-unsubscribe`)

| Rute | Indhold |
|---|---|
| `/iFrame-subscription` | iFrame til tilmelding |
| `/iFrame-subscription-setup` | Opsætning af iFrame |
| `/subscription-report` | Tilmeldingsrapport |
| `/subscription-notification` | Notifikationsopsætning |
| `/excel-upload` | Batch-upload via Excel |
| `/enrollment-app` | Tilmeldingsapp |

---

## 5. Frontend — Sikkerhedsmodel

### Garde-hierarki

```
AppCanActivateGuard          — global: er brugeren logget ind?
├── UserRoleGuard             — har brugeren den givne UserRole?
├── ProfileRoleRouteGuard     — har profilen den givne ProfileRole?
├── LimitedUserGuard          — er brugeren "limited user"?
└── CanActivateWizardRoute    — wizard-specifik logik (smsGroupId + URL)
```

### UserRoles (kontostyring)

| Rolle | Adgang til |
|---|---|
| `SuperAdmin` | Alt inkl. pipeline og super-admin |
| `ManageMessages` | Besked-wizard |
| `ManageReports` | Status-sider |
| `ManageCustomer` | Kundeadministration |
| `ManageUsers` | Brugerstyring |
| `ManageProfiles` | Profil-styring |
| `ManageBenchmarks` | Benchmark-modul |
| `ManageRecurringMessages` | Gentagende beskeder |
| `LimitedUser` | Broadcasting-limited only |
| `AlwaysTestMode` | Altid test-tilstand |
| `RequiresApproval` | Besked kræver godkendelse |
| `Benchmark` | Benchmark synlig i admin |
| `Searching` | Søgefunktion synlig |
| `WEBMessages` | Web-beskeder synlig |
| `StandardReceivers` | Std-modtagere synlig |
| `SubscriptionModule` | Abonnementsmodul synlig |
| `MessageTemplates` | Skabeloner synlig |
| `CanSetupStatstidende` | Statstidende synlig |
| `CanCreateScheduledBroadcasts` | Planlagte udsendelser |
| `CanManageCriticalAddresses` | Kritiske adresser |
| `CanSendSingleSmsAndEmail` | Enkelt SMS/email knap |
| `CanManageScenarios` | Scenario-opsætning |
| `WeatherWarning` | Vejrvarslinger |

### ProfileRoles (per-profil rettigheder)

| Rolle | Effekt |
|---|---|
| `CanSendByAddressSelection` | Adressevalg i wizard |
| `CanUploadStreetList` | Excel-upload i wizard |
| `CanSendByMap` | Kortvalg i wizard |
| `CanSendByVoice` | Voice-kanal tilgængelig |
| `CanSendByEboks` | e-Boks-kanal tilgængelig |
| `CanSendByWeb` | Web-besked kanal |
| `CanSendByWebInternal` | Intern web |
| `CanPostOnFacebook` | Facebook-kanal |
| `CanTweetOnTwitter` | Twitter/X-kanal |
| `CanSelectStdReceivers` | Standardmodtagere |
| `CanSendByOnlyStdReceivers` | Kun std. modtagere |
| `StdReceiverExtended` | Udvidet std. modtager |
| `CanSpecifyLookup` | Ejer/adresse opslag |
| `CanSelectLookupBusinessOrPrivate` | Erhverv/privat valg |
| `CanSendToCriticalAddresses` | Kritiske adresser |
| `SmsConversations` | SMS-samtaler synlig |
| `AlwaysCanReceiveSmsReply` | Altid SMS-svar |
| `AlwaysDelayed` | Altid forsinket |
| `CriticalStatusWeb` | Kritisk status-web |
| `CanSendByOnlyStdReceivers` | Kun std. modtagere |

### Autentificering

- **Web-app (ServiceAlert.Web):** SAML2 (Sustainsys.Saml2) + Cookie
- **API (ServiceAlert.Api):** JWT Bearer (RSA-nøgle) + custom ApiKey
- **Azure SSO:** MSAL Angular 4.0 (Azure AD)
- **Frontend interceptorer:** `BiAuthInterceptor` + `BiBearerHeaderInterceptor`

---

## 6. Frontend — Services (core/services)

| Service | Ansvar |
|---|---|
| `address.service.ts` | Adresseopslag og søgning |
| `benchmark.service.ts` | Benchmark-data |
| `bi-local-and-session-storage.service.ts` | Browser storage wrapper |
| `contact-persons.service.ts` | Kontaktpersoner |
| `conversations.service.ts` | SMS-samtaler (SSE) |
| `customer.service.ts` | Kundestamdata |
| `data-import.service.ts` | Data-import |
| `enrollment-admin.service.ts` | Enrollment-administration |
| `file-management.service.ts` | Filhåndtering |
| `invoicing.service.ts` | Fakturering |
| `map-administration.service.ts` | Kortadministration |
| `message.service.ts` | Beskedoprettelse og -styring |
| `operational-messages.service.ts` | Operationelle driftsmeddelelser |
| `outgoing-request-logs.service.ts` | Udgående forespørgselslog |
| `packages.service.ts` | Pakke-opsætning |
| `profile.service.ts` | Profil + profilerol-tjek |
| `smsgroup-approver.service.ts` | Beskedgodkendelse |
| `smsgroup-schedule.service.ts` | Planlagte udsendelser |
| `smsgroup-stencil.service.ts` | Beskedskabeloner (stencils) |
| `social-media.service.ts` | Facebook/Twitter integration |
| `std-receivers.service.ts` | Standardmodtagere |
| `subscribe-module.service.ts` | Abonnementsmodul |
| `support.service.ts` | Support-formular |
| `system-text-merge-fields.service.ts` | Merge-felter |
| `template.service.ts` | Beskedskabeloner |
| `user-nudging.service.ts` | Bruger-nudging |
| `user.service.ts` | Brugerstyring |
| `webmessage.service.ts` | Web-beskeder |

---

## 7. Frontend — Delte UI-komponenter (shared/components)

| Komponent | Formål |
|---|---|
| `bi-desktop-frame` | Hoved-layout frame |
| `bi-menu` | Navigation-menu |
| `bi-tabs` | Tab-navigation |
| `bi-custom-inputs` | Custom input-felter |
| `bi-full-calendar` | Kalender-visning |
| `bi-image-uploader` | Billed-upload |
| `bi-editable-text` | Inline tekst-redigering |
| `bi-text-save-cancel` | Gem/annuller inline |
| `bi-list-box` | Liste-boks |
| `bi-selection-list` | Valgbar liste |
| `bi-indicator-icon` | Status-ikon |
| `bi-phone-frame` | SMS-preview i telefon-ramme |
| `bi-sms-email-counting-box` | Tæl SMS/Email-tegn |
| `bi-show-message-preview` | Besked-forhåndsvisning |
| `bi-email-preview` | Email-forhåndsvisning |
| `bi-eboks-preview` | e-Boks-forhåndsvisning |
| `bi-address-search-input` | Adressesøge-input |
| `advanced-voice-settings` | Voice-indstillinger |
| `bi-error-messages-box` | Fejl-visboks |
| `bi-prospect-tasks-view` | Pipeline-opgavevisning |
| `bi-quick-response-setup-enabler` | Quick Response aktivering |
| `bi-settings-link` | Indstillingslink |
| `benchmark-create-edit` | Benchmark opret/rediger |
| `eboks-create-edit` | e-Boks opret/rediger |
| `file-upload` | Fil-upload |
| `send-methods-list` | Sendemetode-liste |
| `std-receiver-selection` | Vælg standardmodtagere |
| `std-receiver-tree-node` | Træ-node for std. modtagere |
| `country-customer-profile-selection` | Land/Kunde/Profil-vælger |
| `dialog-content` | Dialog-wrapper |
| `iframe-url-param-descriptions` | iFrame URL-parameter docs |
| `individual-msg-settings-display-box` | Individuelle beskedindstillinger |
| `latest-msg-box` | Seneste-besked-boks |
| `send-methods-list` | Sendemetode-liste |
| `box-with-checkboxes` | Checkbox-liste |
| `buttons` | Standard knap-varianter |
| `lists` | Liste-varianter |
| `tables` | Tabel-varianter |

---

## 8. Frontend — Blinde vinkler (status efter SLICE_3b / 12-16)

Oversigt over hvad der oprindeligt manglede i SLICE_1-3 og hvad der siden er kortlagt:

| Sektion | Emne | Status |
|---|---|---|
| 8.1 | Real-time SSE | ✅ Fanget af SLICE_16 |
| 8.2 | iFrame-apps | ✅ SLICE_1b — 14 ruter fra 3 sub-apps |
| 8.3 | Web API-controllers | ✅ SLICE_1c — 63 controllers kortlagt |
| 8.4 | Webhook-controllers | ✅ Fanget af SLICE_3b |
| 8.5 | Batch-jobs | ✅ Fanget af SLICE_13 |
| 8.6 | Background Services | ✅ Fanget af SLICE_12 |
| 8.7 | RabbitMQ-topologi | ✅ SLICE_17 — 1 exchange, 1 queue, 2 publishers, 1 consumer |
| 8.8 | MediatR events | ✅ Fanget af SLICE_14 |
| — | Externe integrationer | ✅ SLICE_15 — 51 AddHttpClient-registreringer |

### 8.1 Real-time kommunikation (SSE) — ✅ Fanget af SLICE_16

Frontenden bruger **Server-Sent Events** (ikke WebSocket) til real-time opdateringer:

| SSE-gruppe | Trigger | Modtager |
|---|---|---|
| `ConversationUnreadStatus/{phoneNumberId}` | Ny ulæst besked | SMS-samtaler |
| `ConversationCreated/{phoneNumberId}` | Ny samtale oprettet | SMS-samtaler |
| `ConversationMessageSent/{phoneNumberId}` | Besked sendt | SMS-samtaler |
| `ClientEvents` | Generelle system-events | Hele appen |

✅ **Fanget af SLICE_16** — 6 SSE-streams kortlagt i `realtime_map.json` med `ServerSentEventType`-enum, endpoint `/sse` og Angular-consumers.

### 8.2 iFrame-apps (3 separate Angular-sub-projekter) — ✅ SLICE_1b

| App | Port | Formål | Ruter |
|---|---|---|---|
| `SubscriptionApp` | 4201 | Selvstændig tilmelding | 8 (paths via TS-konstanter) |
| `iFrameModules` | 4202 | Driftstatus iFrame | 4 (IframeDriftstatus, IframeDriftstatusMap, IframeSubscription, IframeSubscriptionStdReceiver) |
| `QuickResponse` | 4203 | Hurtig svar | 2 (`""`, `":tag"`) |
| `SmsServiceWebApp` | 4200 | Hoved-app | ✅ Kortlagt via SLICE_1 (69 ruter) |

✅ **SLICE_1b — 14 ruter i `angular_apps.json`**. Note: SubscriptionApp bruger TS-konstanter (`RouteNamesEn.xxx`) til path-definitioner — disse kan ikke evalueres via regex-analyse.

### 8.3 ServiceAlert.Web REST API-controllers — ✅ SLICE_1c

`ServiceAlert.Web` er en **ASP.NET Core Web API** der serverer Angular-frontenden. Alle 63 controllers i `Controllers/` er REST API-controllers der extender `BaseController` med `[Route("api/[controller]")]`.

Nøglegrupper:
- `Enrollment/` → tilmeldings-endpoints (EnrollmentController, EnrollmentAdminController)
- `SuperAdmin/` → admin-endpoints (MonitoringController, JobsController, InvoiceController m.fl.)
- `StandardReceivers/` → SCIM-endpoints (ScimUsersController, ScimGroupsController)
- Root: AdminController, ProfileController, QuickResponseController, ReportController m.fl.

✅ **SLICE_1c — 63 controllers i `mvc_routes.json`** med controller-navn, route-prefix, namespace og action-metoder.

### 8.4 Webhook-controllers — ✅ Fanget af SLICE_3b

Backend har dedikerede webhook-controllers der modtager **inbound** kald fra 3. parter:

| Controller | Webhook-kilde | Funktion |
|---|---|---|
| `GatewayApiController` | GatewayAPI | SMS-delivery report + inbound SMS |
| `InfobipWebhookController` | Infobip | Voice-status + inbound SMS |
| `SendgridController` | SendGrid | Email inbound parse + delivery |
| `NineteenNineteenController` | 4519 19 | Inbound SMS til standardmodtagere |
| `StrexController` | Strex | Norsk SMS-delivery report |
| `TrimbleOutageNotificationSoap` | Trimble (SOAP) | Driftstatus-notifikationer |

✅ **Fanget af SLICE_3b** — 8 inbound webhook-controllers kortlagt i `webhook_map.json` (GatewayAPI, Infobip, SendGrid, 1919, Strex m.fl.).

### 8.5 Batch-processor (135 jobs) — ✅ Fanget af SLICE_13

`ServiceAlert.Batch` er en CLI-app med **100+ distinct batch-actions** der kører via Azure-scheduler:

**Adresseimport:**
- `import_dk_addresses` — DAWA (Danmark)
- `import_se_addresses` — Lantmäteriet (Sverige)
- `import_no_addresses` — Kartverket (Norge)
- `import_fi_addresses_map` — AvoinData (Finland)
- `import_no_properties` — Norske ejendomme
- `import_dk_owner_addresses` — Ejerfortegnelsen
- `import_dk_owner_publish_data` — Publiceringsdata

**Beskedlevering:**
- `gateway_api_bulk` — SMS via GatewayAPI
- `gateway_emails` — Email via SMTP
- `send_emails_sendgrid` — Email via SendGrid
- `gateway_voice` — Talesvar
- `gateway_webmessages` — Web-beskeder
- `gateway_eboks` — e-Boks

**Opslag og enrichment:**
- `prelookup` — Pre-opslag
- `lookup` — Ejer/abonnement-opslag
- `import_robinsons` — Robinson-liste (fravalg)
- `import_provider_phonenumbers` — Telefonnummer-import
- `stage_provider_phonenumbers` — Staging
- `swap_provider_phonenumbers` — Swap til aktiv

**Økonomi:**
- `import_economic_customers` — e-Conomic kunder
- `import_economic_invoices` — e-Conomic fakturaer
- `economic_periodize_invoicelines` — Periodisering
- `import_framweb_balance_sheets` — Balancer
- `import_budget` — Budget

**Cleanup (15+ jobs):**
- `cleanup_webhookmessages`, `cleanup_systemlogs`, `cleanup_requestlogs`
- `cleanup_deactivated_users/customers/profiles`
- `cleanup_cached_phonenumbers`, `cleanup_clientevents`
- `cleanup_bisnode_sweden`, `cleanup_enrollees`
- `cleanup_messages`, `cleanup_emailmessages`, `cleanup_eboksmessages`

**Monitoring:**
- `monitoring` — Daglig systemrapport
- `monitoring_daily` — Daglig monitoring
- `monitoring_address_imports` — Import-overvågning
- `watchdog_version`
- `send_error_500_report`, `send_error_400_report`

✅ **Fanget af SLICE_13** — 135 batch-jobs kortlagt i `batch_jobs.json` fordelt på 17 kategorier (import, delivery, cleanup, monitoring, statistics, finance m.fl.).

### 8.6 Background Services (altid kørende) — ✅ Fanget af SLICE_12

| Service | Funktion | Host |
|---|---|---|
| `SmsBackgroundService` | SMS-kø-forbruger | ServiceAlert.Api |
| `EmailBackgroundService` | Email-kø-forbruger | ServiceAlert.Api |
| `SendGridBackgroundService` | SendGrid-kø | ServiceAlert.Api |
| `VoiceBackgroundService` | Voice-kø | ServiceAlert.Api |
| `WebhookMessagesBackgroundService` | Webhook-kø | ServiceAlert.Api |
| `EconomicBackgroundService` | e-Conomic synkron | ServiceAlert.Api |
| `ClientEventSyncroBackgroundService` | SSE-event synkron | ServiceAlert.Api |
| `QueueWorker` | RabbitMQ voice-kø | ServiceAlert.Worker.Voice |
| `StatusWatcher` | Voice-status polling | ServiceAlert.Worker.Voice |

✅ **Fanget af SLICE_12** — 11 background services kortlagt i `background_services.json` med type, host og dependencies.

### 8.7 RabbitMQ (messaging infrastructure) — ✅ SLICE_17

| Ressource | Navn | Type | Durable |
|---|---|---|---|
| Connection | `ServiceAlertMQ` | Aspire-managed | — |
| Exchange | `voice_exchange` | Direct | Yes |
| Queue | `voice` | — | Yes |
| Binding | `voice` → `voice_exchange` (routing key: `voice`) | — | — |

**Publishers:**
- `QueueVoiceGatewayStrategy` (ServiceAlert.Services) — voice_exchange/voice
- `EndpointExtensions` (ServiceAlert.Worker.Api) — voice_exchange/voice

**Consumers:**
- `VoiceMessageQueueEventConsumer` : AsyncDefaultBasicConsumer (ServiceAlert.Worker.Voice) — queue `voice`

**Host projects:** ServiceAlert.AppHost (infrastructure), ServiceAlert.Worker.Api (publisher), ServiceAlert.Worker.Voice (consumer + Quartz scheduler)

### 8.8 MediatR events (intern pub/sub) — ✅ Fanget af SLICE_14

Intern hændelseshåndtering via MediatR — 30 events kortlagt i `event_map.json`:

| Event | Publisher | Handler(s) |
|---|---|---|
| `InboundParseEvent` | SendgridController | InboundParseEventHandler (email→SMS) |
| `StandardReceiverGroupMessageReceivedNotification` | GatewayApi/1919Controller | StandardReceiverGroupMessageReceivedEventHandler |
| `VoiceMessageStatusChangedEvent` | InfobipWebhook + StatusWatcher | VoiceMessageStatusChangedEventHandler |
| `UnsubscribeMessageReceivedEvent` | NineteenNineteenController | — |
| `BenchmarkFinishedNotification` | — | BenchmarkFinishedNotificationHandler |
| `ProspectCreatedInEconomicNotification` | — | ProspectCreatedInEconomicNotificationHandler |
| `InboundMessageEvent` | GatewayApiController | — |

---

## 9. Systemlandskab — Eksterne integrationer

| System | Land | Protokol | Funktion |
|---|---|---|---|
| **GatewayAPI** | DK | REST | SMS-afsendelse + DLR |
| **Infobip** | Global | REST | Voice-beskeder + DLR |
| **SendGrid** | Global | REST + Inbound Parse | Email |
| **e-Boks** | DK | REST | Sikker digital post |
| **Strex** | NO | REST | Norsk SMS-delivery |
| **Trimble** | Global | SOAP/WSDL | Driftstatus-notifikationer |
| **DAWA** | DK | REST | Adressedata |
| **Kartverket** | NO | REST | Norske adresser + ejendomme |
| **Lantmäteriet** | SE | REST | Svenske adresser |
| **AvoinData** | FI | REST | Finske adresser |
| **Ejerfortegnelsen** | DK | FTP/SFTP | Ejerskabsdata |
| **FREG** | NO | REST | Norsk personregister |
| **KRR/KoFuVi** | NO | REST | Norske kontaktdata |
| **SwedishBisnode** | SE | — | Svenske virksomhedsdata |
| **Salesforce** | Global | REST | Salgsstyring |
| **e-Conomic** | DK | REST | Fakturering og regnskab |
| **InfoPortal** | DK | REST | El-afbrydelsesregistrering |
| **Statstidende** | DK | Scraper/FTP | Konkurs-notifikationer |
| **Facebook** | Global | REST | Social media-udsendelse |
| **Twitter/X** | Global | REST | Social media-udsendelse |
| **Profinderapi** | — | REST | — |
| **Azure Blob Storage** | — | SDK | Fil-storage |
| **Azure Key Vault** | — | SDK | Hemmeligheder |
| **RabbitMQ** | — | AMQP | Voice-besked-kø |

---

## 10. Deployment — Azure Aspire (ServiceAlert.AppHost)

```
Azure Container Apps Environment: servicealert-aca-env
├── ServiceAlert.Worker.Voice  (Azure Container App, NorwayEast)
│   ├── RabbitMQ reference
│   └── Key Vault reference
├── ServiceAlert.Worker.Api    (Azure Container App, external HTTP)
│   ├── RabbitMQ reference
│   └── /health endpoint
└── ServiceAlert.Test.Fact24TonyEmulator  (kun hvis ENV=true)

RabbitMQ: ServiceAlertMQ (med management-plugin + persistent volume)
Key Vault: eksisterende (AsExisting) 
Managed Identity: ServiceAlertUser (eksisterende)
Region: NorwayEast
```

---

## 11. Hvad pipeline IKKE fanger — Anbefaling til nye slices

| Manglende analyse | Foreslået slice | Prioritet | Status |
|---|---|---|---|
| iFrame-apps (SubscriptionApp, iFrameModules, QuickResponse) | SLICE_1b | Høj | ✅ 14 ruter i `angular_apps.json` |
| ServiceAlert.Web REST API-controllers | SLICE_1c | Høj | ✅ 63 controllers i `mvc_routes.json` |
| Webhook-controllers (inbound flow fra gateways) | SLICE_3b | Høj | ✅ 8 webhooks i `webhook_map.json` |
| Background services + kø-arkitektur | SLICE_12 | Høj | ✅ 11 services i `background_services.json` |
| Batch-job katalog (100+ jobs) | SLICE_13 | Høj | ✅ 135 jobs i `batch_jobs.json` |
| MediatR events (intern pub/sub-model) | SLICE_14 | Medium | ✅ 30 events i `event_map.json` |
| Externe integrationer (HTTP-klienter + contracts) | SLICE_15 | Medium | ✅ 51 registreringer i `integrations.json` |
| SSE-kanaler og real-time events | SLICE_16 | Medium | ✅ 6 streams i `realtime_map.json` |
| Label/i18n namespace mapper | SLICE_11 | Medium | ✅ 115 entries |
| RabbitMQ-kø-topologi | SLICE_17 | Lav | ✅ 6 items i `rabbitmq_topology.json` |

---

## 12. Ressourceinventar — AI vs. Script klassifikation

> Komplet scanning af alle datakilder. Formål: beslutte hvilke slices forbliver script-baserede og hvor AI er påkrævet.

### Kodebase

| Type | Antal | Kompleksitet | Anbefalet behandling |
|---|---|---|---|
| TypeScript-filer (.ts) | **1.698** | HIGH | HYBRID — struktur via script, semantik via AI |
| HTML-templates | **490** | MEDIUM | SCRIPT — binding-mønstre, component-refs |
| SCSS/CSS | **203** | LOW | SCRIPT — fuldt deterministisk |
| Angular components | **548** | HIGH | HYBRID — 69 ruter fanget, ~480 sub-komponenter ukategoriseret |
| Angular services (.service.ts) | **129** | HIGH | HYBRID |
| C# filer (.cs) | **3.193** | HIGH | HYBRID — controllers/repos via script, domænelogik via AI |
| C# Controllers | **83** | MEDIUM | SCRIPT — [Route]/[HttpGet]-attributter, allerede fanget i SLICE_1c + 3b |
| C# Services | **222** | HIGH | HYBRID — dependency graph via script, formål via AI |
| C# Repositories | **174** | MEDIUM | SCRIPT — Dapper/EF query-mønstre |

### Database

| Type | Antal (SQL-filer) | Antal (live schema) | Anbefalet behandling |
|---|---|---|---|
| Tabeller | 319 | 319 | HYBRID — kolonner via script, domænegruppering via AI |
| Stored procedures | 100 | 99 | HYBRID — signaturer via script, forretningslogik via AI |
| Views | 3 | 3 | SCRIPT |
| Funktioner | 9 | 8 | SCRIPT |
| User defined types | 18 | 18 | SCRIPT |
| Test-datafiler | 21 | — | SCRIPT |
| SQL-filer total | **501** | — | — |

### Wiki

| Metric | Værdi |
|---|---|
| .md-filer | **180** |
| Total linjer | **10.175** |
| Gns. linjer/fil | 57 |
| Max linjer (enkeltfil) | 697 |
| Nuværende pipeline-output | **3 signaler** (SLICE_0_5) |
| Anbefalet behandling | **AI** — fri tekst: principper, agendaer, code review guidelines |

> ⚠️ Næsten alt wiki-indhold er uudnyttet. 10.000+ linjer arkitekturbeslutninger og principper fanger ingen pipeline-signaler i dag.

### PDF

| Fil | Sider | Størrelse | Behandling |
|---|---|---|---|
| `example.pdf` | 4 | 49 KB | AI (allerede delvist via SLICE_0_7) |
| `Bootstrap-vs-Material-Design-vs-Prime-vs-Tailwind.pdf` | 19 | 7.781 KB | AI — tech selection dokument med arkitekturrelevans |
| **Total** | **23** | — | — |

### DevOps Work Items

| Metric | Værdi |
|---|---|
| Total items | **11.622** |
| Capabilities (unik) | 6 |
| Gns. keywords/item | 10,5 |
| Raw beskrivelsestekst | ❌ Ikke tilgængelig i `work_item_analysis.json` (pre-processeret) |
| Anbefalet behandling | **AI** — dansk/engelsk naturlig sprog, kapabilitetsmapping er overfladisk |

### Git Insights

| Type | Antal |
|---|---|
| `fix` | 1.780 |
| `feature` | 882 |
| `rule` | 577 |
| `refactor` | 132 |
| `risk` | 24 |
| **Total** | **3.395** |

> Typeklassifikation er allerede script-baseret. `risk`-kategorien (24 items) er høj AI-prioritet trods lille volumen.

### i18n Labels

| Metric | Værdi | Behandling |
|---|---|---|
| Namespaces | **115** | SCRIPT — fuldt fanget af SLICE_11 |
| Estimerede label-nøgler | ~1.725 (115 ns × ~15 keys) | SCRIPT |

---

### AI-belastningsestimering

| Ressource | Items | Tokens/item | Total tokens |
|---|---|---|---|
| Wiki markdown-filer | 180 | 700 | 126.000 |
| PDF-sider | 23 | 600 | 13.800 |
| Work items (pre-processeret) | 11.622 | 80 | **929.760** |
| Work items (rå ADO, hvis tilgængelig) | 11.622 | ~400 | ~4.650.000 |
| Git commit-beskeder | 3.395 | 60 | 203.700 |
| Angular components (semantisk) | 548 | 300 | 164.400 |
| C# services (domæneklassifikation) | 222 | 500 | 111.000 |
| SQL stored procedures (logikanalyse) | 100 | 800 | 80.000 |
| **Minimum AI total** | | | **~1,6M tokens** |
| **Maksimum (rå kilder)** | | | **~8–24M tokens** |

---

### Hotspots — prioriteret

| Prioritet | Type | Antal | Årsag |
|---|---|---|---|
| 🔴 HIGH | Work items | 11.622 | Største dataset. NL-titler DK/EN. Kun 6 capability-buckets i dag — alt for groft. |
| 🔴 HIGH | Git insights | 3.395 | `risk`-kategorien er ubehandlet. Arkitekturmønstre på tværs af commits ikke ekstraheret. |
| 🔴 HIGH | C# source | 3.193 | 222 services + 174 repos = 396 filer mangler semantisk domæneklassifikation. |
| 🟡 MEDIUM | Angular components | 548 | ~480 sub-komponenter ikke koblet til business capability. SLICE_1 dækkede kun 69. |
| 🟡 MEDIUM | Wiki markdown | 180 | 10.175 linjer arkitekturviden. Næsten intet udnyttet. Kræver dedikeret AI-slice. |
| 🟡 MEDIUM | SQL stored procedures | 100 | Signaturer er script-analyserede. Forretningslogik og side-effects kræver AI. |
| 🟢 LOW | PDF | 2 | 23 sider total. Bootstrap vs Material er arkitekturrelevant men lavt volumen. |

---

## 13. Kendte arkitektoniske observationer

1. **Dual-app arkitektur:** Systemet har to brugerfrontender — Angular SPA (`ServiceAlert.Web`) og Razor MVC-sider (enrollment, SAML2). Disse deler backend-tjenester men har separate authentication-flows.

2. **Kø-heterogenitet:** SMS/Email bruger SQL-tabelkøer (Background Services), Voice bruger RabbitMQ. Arkitekturdokumentationen noterer dette som et anerkendt teknisk gæld.

3. **Nordisk multi-country:** Adresse-pipelines for 4 lande (DK, NO, SE, FI) kører som separate batch-jobs med separate HTTP-klienter og importers.

4. **3-lags permission-model:** UserRole (system-niveau) + ProfileRole (profil-niveau) + ApiKey (integration-niveau). Alle tre tjekkes uafhængigt.

5. **SAML2 per kunde:** Hver kunde kan have sin egen IdP-konfiguration (`CustomerSamlSettings`), cached i `IMemoryCache`.

6. **Angular 20 — moderne patterns:** Bruger `inject()` DI, standalone components, `loadComponent()` lazy-loading, og signal-baseret state (`set()`, `signal()`).

---

## 14. AI Asset Engine — Adaptiv Chunking

> Implementeret 30. marts 2026. Tre nye moduler i `core/`.

### Formål

Gruppér alle datakilder i meningsfulde enheder (assets) inden AI-behandling — i stedet for at sende rå filer én ad gangen. Muliggør stabil state-tracking, inkrementel genbehandling og præcis token-budgettering.

---

### Nye moduler

| Modul | Fil | Ansvar |
|---|---|---|
| `AssetScanner` | `core/asset_scanner.py` | Scan alle datakilder → returnér flad liste af Asset-dicts |
| `AssetState` | `core/asset_state.py` | Persistér behandlingstilstand i `data/asset_state.json` |
| `AssetProcessor` | `core/asset_processor.py` | Iterer over assets, filtrer uændrede, kald handlers, log |

---

### Grupperingsregler (per type)

| Type | Kilde | Strategi | Gruppe-enhed | ID-mønster |
|---|---|---|---|---|
| `pdf_section` | PDF-filer i `raw/` | TOC hvis tilgængelig → ellers font-størrelse headings | N sider per sektion | `pdf:{fil}:{section_index}` |
| `wiki_section` | Wiki `.md`-filer | Split på `##`+ headings | 1 sektion | `wiki:{fil}:{section_index}` |
| `work_items_batch` | `work_item_analysis.json` | Sorteret på id, vinduer af 100 | 100 items | `work_items:batch:{n}` |
| `git_insights_batch` | `git_insights.json` | Sorteret på id, vinduer af 100 | 100 items | `git_insights:batch:{n}` |
| `labels_namespace` | `label_map.json` | 1 namespace = 1 asset | `key_count` nøgler | `labels:ns:{namespace}` |
| `code_file` | Kildekode i `solution_root` | Uændret — 1 fil = 1 asset | 1 fil | `code:{rel/sti}` |

---

### Live scan-resultater (uden kode-filer)

| Type | Assets | Kilde |
|---|---|---|
| `pdf_section` | **60** | 2+ PDF-filer via TOC-strategi |
| `wiki_section` | **28** | 180 `.md`-filer → 28 sections (samlet wiki er <30 unikke sections pga. lav heading-tæthed) |
| `work_items_batch` | **117** | 11.622 items / 100 per batch |
| `git_insights_batch` | **34** | 3.395 insights / 100 per batch |
| `labels_namespace` | **115** | 1 per namespace |
| **Total** | **354** | — |

---

### State-system

- Persisteret i `data/asset_state.json` (atomisk skrivning via `.tmp` + `os.replace`)
- Et asset er **stale** hvis: id er nyt, ELLER `content_hash` (SHA-256) er ændret
- For batch-typer: ændring i ét item → hele batchen genbehandles
- `reset_asset(id)` tvinger genbehandling af specifikt asset
- `reset_all()` nulstiller komplet state

**Verificeret:** Anden run på uændrede data → 0 processed, 354 skipped.

---

### Logging-format

```
[SCAN]    Scanning all assets...
[SCAN]    Scanned 354 assets (354 stale)
[PROCESS] pdf_section          "manual.pdf" §3                     (2 pages)
[PROCESS] work_items_batch     batch 0                             (100 items)
[PROCESS] wiki_section         Architecture.md §1 "Overview"       (1 section)
[SKIP]    code_file            "code:ServiceAlert.Web/..."          unchanged
[DONE]    Processed 354 assets  Skipped 0  Errors 0
```

---

### Tests

| Testklasse | Tests | Dækker |
|---|---|---|
| `TestWikiSplitSections` | 6 | Heading-split, no-overlap, level-bevaring, tom fil |
| `TestScanWorkItemAssets` | 7 | Batch-størrelse 100, stabile IDs, hash-ændring, ingen duplikering |
| `TestScanGitInsightAssets` | 4 | Batch-størrelse, type-aggregering, ingen duplikering |
| `TestScanLabelAssets` | 4 | 1 asset/namespace, id-format, sortering |
| `TestScanWikiAssets` | 6 | Level-2 split, section_index, no-overlap, tom fil hoppes over |
| `TestScanCodeAssets` | 6 | 1 fil/asset, node_modules skippes, forward-slash IDs |
| `TestAssetState` | 8 | Stale-detektion, disk-persistens, reset, atomisk skrivning |
| `TestAssetProcessor` | 10 | End-to-end run, idempotens, hash-change trigger, fejlhåndtering |
| `TestSha256` | 3 | Determinisme, hex-format |
| **Total nye tests** | **54** | — |

```
374 passed in 28.24s  (+54 asset system, +31 domain pipeline)
```

---

### Hard rules (opfyldt)

| Regel | Status |
|---|---|
| Deterministisk gruppering (samme input → samme output) | ✅ |
| Stabile IDs (aldrig ændret medmindre struktur ændres) | ✅ |
| Ingen duplikering på tværs af grupper | ✅ |
| Ingen overlap (hvert item optræder i præcis én gruppe) | ✅ |
| `group_size` på hvert asset | ✅ |
| `content_hash` på hvert asset | ✅ |

---

## 15. Domain Pipeline — Multi-stage AI Extraction

> Implementeret 30. marts 2026. Fire nye moduler i `core/`.

### Formål

Køre hvert asset igennem fire AI-stadier i rækkefølge, persistere state efter **hvert** stadie, og støtte ubegrænset restart uden tab af data. Output er maskinlæsbare domænefiler — ikke menneskelig dokumentation.

---

### Nye moduler

| Modul | Fil | Ansvar |
|---|---|---|
| `StageState` | `core/stage_state.py` | Tracker per-asset per-stage status i `data/stage_state.json` |
| `AIProcessor` | `core/ai_processor.py` | Abstrakt interface + `StubAIProcessor` (no-op) + `CopilotAIProcessor` (gpt-4.1) |
| `PromptBuilder` | `core/prompt_builder.py` | Bygger stage- og asset-type-specifikke prompts |
| `DomainPipeline` | `core/domain_pipeline.py` | Orchestrerer scan → filter-stale → multi-stage-AI → persist loop |

---

### Stadie-rækkefølge

```
structured_extraction → semantic_analysis → domain_mapping → refinement
```

| Stadie | Opgave |
|---|---|
| `structured_extraction` | Udtræk strukturerede fakta: entitetsnavne, API-signaturer, datastrukturer, eksplicitte relationer |
| `semantic_analysis` | Ansvar og intent: hvad gør komponenten? hvilken business capability? hvem kalder den og hvorfor? |
| `domain_mapping` | Klassificer til domæne-koncepter: entities, behaviors, flows, events, rules, integrations |
| `refinement` | Flet og normaliser. Tilføj pseudokode for komplekse flows. Producér rebuild requirements |

---

### Domæne output-format (per asset per stadie)

```json
{
  "asset_id": "wiki:Architecture.md:3",
  "stage": "domain_mapping",
  "entities": [],
  "behaviors": [],
  "flows": [],
  "events": [],
  "batch_jobs": [],
  "integrations": [],
  "rules": [],
  "pseudocode": [],
  "rebuild_requirements": []
}
```

Output-filer skrives til: `{output_root}/{stage}/{safe_asset_id}.json`

---

### State-system

- Persisteret i `data/stage_state.json` (atomisk via `.tmp` + `os.replace`)
- State gemmes efter **hvert enkelt stadie** — crash-safe
- Et asset er **stale** (alle stadier pending) hvis `content_hash` ændres
- Et failed stadie forbliver pending til det lykkes
- `reset_asset(id)` tvinger genbehandling, `reset_all()` nulstiller komplet

**Verificeret:** Andet run på uændrede data → 0 processed, alle assets skipped.

---

### Pipeline-parametre

| Parameter | Effekt |
|---|---|
| `max_assets=N` | Stop efter N assets (støtter batch-kørsel over dage) |
| `stages=["semantic_analysis"]` | Kør kun ét stadie — restart fra præcis det stadie |
| `dry_run()` | Rapport over pending stadier uden at skrive noget |
| `verbose=True` | Logger `[SCAN]` / `[DONE]` / `[SKIP]` / `[ERROR]` per stadie |

---

### Logging-format

```
[SCAN      ] Scanned 354 assets
[DONE      ] wiki_section             structured_extraction    wiki:Architecture.md:3
[DONE      ] wiki_section             semantic_analysis        wiki:Architecture.md:3
[SKIP      ] code_file                wiki:ServiceAlert.Web/...  (unchanged)
[ERROR     ] pdf_section              domain_mapping           pdf:manual.pdf:5 — AI offline
[DONE      ] Processed 42  Skipped 312  Errors 1
```

---

### Prompt-regler (håndhævet i alle prompts)

| Regel | Status |
|---|---|
| ALDRIG kopier kildekode | ✅ |
| Udtræk altid intent og ansvar | ✅ |
| Normaliser altid navngivning | ✅ |
| Returnér altid strict JSON | ✅ |
| Refinement modtager forrige stadies output som kontekst | ✅ |

---

### AI-implementering — CopilotAIProcessor

| Egenskab | Værdi |
|---|---|
| Endpoint | `https://api.githubcopilot.com` |
| Default model | `gpt-4.1` (fri med GitHub Copilot-abonnement) |
| Auth | `GITHUB_TOKEN` env var |
| Retry | 3 forsøg ved rate-limit (429) og transiente fejl (5xx) |
| JSON-mode | `response_format={"type": "json_object"}` |

**Brug:**
```python
from core.ai_processor import CopilotAIProcessor
processor = CopilotAIProcessor()   # gpt-4.1 via Copilot
pipeline = DomainPipeline(scanner, stage_state, processor, "data/domain_output")
pipeline.run(max_assets=50)
```

**Opsætning:** `pip install openai` + `$env:GITHUB_TOKEN = "ghp_..."`

---

### Tests

| Testklasse | Tests | Dækker |
|---|---|---|
| `TestStageState` | 11 | Pending-beregning, stale-detektion, partial done, disk-persistens, reset, summary |
| `TestStubAIProcessor` | 3 | Alle domain-nøgler returneres, validate_output, stub-markering |
| `TestPromptBuilder` | 5 | Asset-id i prompt, stage-instruktion, previous result, truncation, ingen previous-sektion uden input |
| `TestDomainPipeline` | 12 | End-to-end run, idempotens, hash-change trigger, state-persistens per stadie, fejlhåndtering, max_assets, stage-filter, output-fil, dry_run, restart-resume, refinement modtager context |
| **Total nye tests** | **31** | — |

```
437 passed in 23.79s  (+31 domain pipeline)
```

---

## 16. Domain Extraction Platform — Full Architecture

> Implementeret 30. marts 2026. Komplet AI-drevet reverse engineering platform.

### Formål

Transformere alle rådata fra de 23 deterministiske slices til struktureret domæneviden, sufficient til at genopbygge hele systemet fra bunden — uden at kopiere kode.

---

### Ny fil- og mappestruktur

```
prompts/
  code_semantic.txt       — udtræk ansvar og intent fra kildekode
  code_domain.txt         — kortlæg kildekode til domæne-koncepter
  sql_semantic.txt        — udtræk forretningsbetydning af SQL-objekter
  wiki_semantic.txt       — udtræk arkitekturbeslutninger fra wiki
  workitem_semantic.txt   — udtræk kapabiliteter fra work item-batches
  refinement.txt          — flet, normaliser, tilføj pseudokode + rebuild krav

core/ai/
  __init__.py
  semantic_analyzer.py    — kører semantic_analysis med type-specifik prompt
  domain_mapper.py        — kører domain_mapping med semantisk resultat som kontekst
  refiner.py              — kører refinement per asset + per domain-cluster

core/
  domain_builder.py       — deterministisk gruppering af slice-output til domæner

domains/
  {DomainName}/
    000_meta.json         — confidence, coverage, complexity_score, roi_score
    010_entities.json     — domæneentiteter (AI-udfyldt)
    020_behaviors.json    — handlinger og processer (AI-udfyldt)
    030_flows.json        — end-to-end flows (AI-udfyldt)
    040_events.json       — MediatR events (fra slice + AI-beriget)
    050_batch.json        — batch jobs (fra slice + AI-beriget)
    060_integrations.json — integrationer, webhooks, background services
    070_rules.json        — forretningsregler (AI-udfyldt)
    080_pseudocode.json   — pseudokode for komplekse flows (AI-udfyldt)
    090_rebuild.json      — rebuild requirements, prioriteret og ordnet

run_domain_pipeline.py    — CLI entry point
```

---

### Domain Builder — deterministisk gruppering

Læser 6 slice-filer og grupperer på tværs via navn-tokenisering (ingen AI):

| Input-fil | Kilde | Gruppering |
|---|---|---|
| `api_db_map.json` | Controller-navn | `BenchmarkController` → `Benchmark` |
| `batch_jobs.json` | Job-kategori | `import` → `Import` |
| `event_map.json` | Event-navn | `BenchmarkFinishedNotification` → `Benchmark` |
| `webhook_map.json` | Source-system | `GatewayAPI` → `GatewayAPI` |
| `integrations.json` | Interface-navn | `IEboksService` → `Eboks` (AI normaliser) |
| `background_services.json` | Service-navn | `SmsBackgroundService` → `Sms` |

**Live scan-resultat (kørte mod rigtige data):**

| Metrik | Værdi |
|---|---|
| Domains oprettet | **51** |
| Største domæne | `Import` (37 items) |
| Højest confidence | `Benchmark` (0.5 — API + events) |
| Filer skrevet | 51 × 10 = **510 JSON-filer** |

> ⚠️ Heuristisk første pass — `I` og `Human` er kendte artefakter fra interface-navne og modul-navne. AI refinement-stadiet normaliserer disse til korrekte domænenavne.

---

### AI-stadier og prompt-strategi

| Stadie | Prompt-fil | Indhold |
|---|---|---|
| `semantic_analysis` | `code_semantic.txt` / `wiki_semantic.txt` / `workitem_semantic.txt` | Hvad gør filen? Ansvar, intent, side-effects |
| `domain_mapping` | `code_domain.txt` | Hvilken domæne? Bounded context? Aggregate root? |
| `refinement` | `refinement.txt` | Flet duplikater, normaliser navne, pseudokode, rebuild requirements |

**Alle prompts håndhæver:**
- Kopier aldrig kildekode
- Udtræk intent og ansvar
- Normaliser navngivning
- Returnér strict JSON

---

### Quality scoring (per domæne)

```json
{
  "domain": "Benchmark",
  "confidence": 0.5,
  "coverage": {
    "api_endpoints": 15,
    "batch_jobs": 0,
    "events": 1,
    "webhooks": 0,
    "integrations": 9,
    "background_services": 0
  },
  "complexity_score": 5,
  "roi_score": 6
}
```

---

### run_domain_pipeline.py — CLI

```bash
# Første kørsel — byg domæner + kør AI på 50 assets
python run_domain_pipeline.py --max-assets 50

# Kun semantisk analyse
python run_domain_pipeline.py --stages semantic_analysis --max-assets 100

# Se hvad der er pending — ingen AI-kald
python run_domain_pipeline.py --dry-run

# Nulstil specifikt asset og genprocess
python run_domain_pipeline.py --reset wiki:Architecture.md:3

# Test pipeline-kabling uden token-forbrug
python run_domain_pipeline.py --stub --max-assets 5
```

---

### Tests

| Testklasse | Tests | Dækker |
|---|---|---|
| `TestDomainToken` | 6 | CamelCase-split, suffix-stripping, fallback til "Core" |
| `TestDomainClusterMetrics` | 5 | confidence, complexity_score, roi_score beregning |
| `TestDomainBuilder` | 7 | Gruppering pr. kilde, manglende filer, atomisk skrivning, pre-udfyldte events |
| `TestSemanticAnalyzer` | 4 | Alle domain-nøgler, prompt-valg pr. type, truncation, manglende prompt-fil |
| `TestDomainMapper` | 2 | Alle domain-nøgler, forrige resultat injiceret i prompt |
| `TestRefiner` | 3 | Alle domain-nøgler, syntetisk asset ved cluster-refinement, domain-navn i prompt |
| **Total nye tests** | **27** | — |

```
437 passed in 23.79s  (+27 domain extraction platform)
```

---

## 17. Autonomous Domain Loop Engine

> Implementeret 30. marts 2026. Domain-first, selvstyrende loop pr. domæne.

### Formål

Systemet bestemmer selv hvornår et domæne er *tilstrækkeligt forstået* til at kunne genopbygges — uden menneskelig indgriben.

---

### Nye moduler

| Fil | Klasse | Ansvar |
|---|---|---|
| `core/domain_state.py` | `DomainState` | Persisterer status, score, gaps, saturation pr. domæne til `domains/{name}/domain_state.json` |
| `core/domain_gap_detector.py` | `DomainGapDetector` | Opdager: `missing_entity`, `orphan_event`, `api_without_flow`, `missing_trigger`, `unowned_batch_job`, `integration_no_behavior` |
| `core/domain_scorer.py` | `DomainScorer` | Beregner 7-dimensionel score: `coverage_code (0.30)`, `coverage_events (0.15)`, `coverage_batch (0.10)`, `coverage_webhooks (0.05)`, `coverage_ui (0.10)`, `consistency (0.15)`, `confidence (0.15)` |
| `core/domain_loop_engine.py` | `DomainLoopEngine` | Kører domain-loop: asset-mapping → AI stages → aggregering → scoring → gap-detektion → saturation-check |

---

### Domain-loop (for hvert domæne)

```
while not domain.is_complete:
    assets ← get_domain_assets(domain)           # path/name heuristik
    run_ai_stages(assets)                          # DomainPipeline med asset_filter
    aggregate_ai_outputs(domain, assets)           # merge domain_mapping outputs
    score  ← DomainScorer.score(domain_files)
    gaps   ← DomainGapDetector.detect(domain_files)
    update domain_state.json

    if score >= 0.80:   mark_complete()
    elif saturated:     mark_saturated()
    elif processed==0:  exit early (idle)
```

---

### Scoringssystem

| Dimension | Vægt | Kilde |
|---|---|---|
| `coverage_code` | 0.30 | entities + behaviors + flows mod API-count |
| `coverage_events` | 0.15 | events med producer/consumer info |
| `coverage_batch` | 0.10 | batch jobs mappet |
| `coverage_webhooks` | 0.05 | integrationer/webhooks |
| `coverage_ui` | 0.10 | behaviors med UI-trigger nøgleord |
| `consistency` | 0.15 | ingen ALLCAPS, ingen duplikater |
| `confidence` | 0.15 | rules + pseudocode + rebuild |

**Tærskel: score ≥ 0.80 → COMPLETE**

---

### Saturation-detektion

Hvis `entity_count`, `flow_count` og `behavior_count` ikke ændrer sig over 3 på hinanden følgende iterationer → `STATUS_SATURATED`.

---

### Asset → domæne mapping

| Asset-type | Strategi |
|---|---|
| `code_file` | Path-segment normaliseret + `_domain_token()` matcher domænenavn |
| `wiki_section` | Domænenavn i asset-ID |
| `labels_namespace` | Namespace-præfiks indeholder domænenavn |
| `work_items_batch` | Global kontekst — tildeles alle domæner |
| `git_insights_batch` | Global kontekst — tildeles alle domæner |

---

### Domæne-tilstandsfil

```json
{
  "domain": "Messaging",
  "status": "in_progress",
  "iterations": 5,
  "score": 0.76,
  "score_breakdown": { "coverage_code": 0.85, "coverage_events": 0.67, ... },
  "last_improvement": "coverage_events",
  "gaps": [
    { "type": "orphan_event", "priority": "medium", "description": "..." }
  ],
  "saturation": { "stable_iterations": 1, ... }
}
```

---

### CLI-integration

```bash
# Kør domain-loop for alle domæner
python run_domain_pipeline.py --loop

# Kun ét domæne
python run_domain_pipeline.py --loop --domain Messaging

# Begræns iterationer og assets
python run_domain_pipeline.py --loop --max-iterations 5 --max-assets-per-iter 10 --stub
```

---

### Tests (nye: 36)

| Klasse | Tests | Dækker |
|---|---|---|
| `TestDomainState` | 8 | Load/save/reload, saturation, completion |
| `TestDomainGapDetector` | 7 | Alle 6 gap-typer + sorteret output |
| `TestDomainScorer` | 6 | Fuld score, tom score, alle dimensioner, vægte |
| `TestAssetMatchesDomain` | 5 | Global, code-file, wiki, prefix-match |
| `TestDeduplicate` | 4 | Dicts, strings, tom liste |
| `TestDomainLoopEngine` | 6 | Skip-complete, filter, max-domains, saturation |
| **Total nye tests** | **36** | — |

```
437 passed in 23.79s  (+36 autonomous loop engine)
```

---

## 18. DomainEngine — Convergence-baseret stop (30. marts 2026)

### Formål

Ny `DomainEngine` der driver det autonome domain-loop med et matematisk konvergenskriterium fremfor simpel score-tærskel. Stop-betingelse: **begge** skal gælde samtidigt:

- `new_information_score < 0.02` (ny info pr. iteration under 2 %)
- `completeness_score > 0.90` (væstet dækning over 90 %)

Adskiller sig fra `DomainLoopEngine` (stopper ved score ≥ 0.80 **eller** saturation).

---

### Nye filer

#### `core/domain_information.py`
Pure scoring-funktioner — ingen fil-I/O undtagen `load_domain_snapshot()`.

| Konstant | Værdi |
|---|---|
| `NEW_INFO_THRESHOLD` | `0.02` |
| `COMPLETENESS_THRESHOLD` | `0.90` |
| `TRACKED_KEYS` | `("entities", "behaviors", "flows", "events", "rules", "pseudocode", "rebuild_requirements")` |

**`SECTION_WEIGHTS`** (summer til præcis 1.0):

| Sektion | Vægt | Mål (min items) |
|---|---|---|
| entities | 0.20 | 5 |
| behaviors | 0.20 | 5 |
| flows | 0.20 | 3 |
| events | 0.15 | 2 |
| rules | 0.10 | 3 |
| pseudocode | 0.05 | 2 |
| rebuild_requirements | 0.10 | 4 |

**Funktioner:**
- `compute_new_information(old_snapshot, new_snapshot) -> float` — `added / baseline`-ratio over alle 7 sektioner
- `compute_completeness(snapshot) -> float` — vægtet `min(count/target, 1.0)` pr. sektion, clamped til [0, 1]
- `load_domain_snapshot(domain_dir) -> dict` — læser alle 7 model-JSON-filer

#### `core/domain_engine.py`

| Konstant | Værdi |
|---|---|
| `DEFAULT_SEEDS` | `["identity", "messaging", "billing", "subscriptions", "monitoring"]` |
| `_DEFAULT_MAX_ITERATIONS` | `15` |
| `_DEFAULT_MAX_ASSETS` | `50` |
| `_RELEVANCE_THRESHOLD` | `0.05` |

`DOMAIN_KEYWORDS` — 5 entries, 10-13 keywords per seed-domæne.

**Pure functions:**
- `keyword_relevance(asset, keywords) -> float` — brøkdel af keywords fundet i `id + content`
- `get_keywords_for_domain(domain_name) -> list[str]` — opslag i `DOMAIN_KEYWORDS` eller camelCase-split fallback

**`DomainEngine`-metoder:**
- `select_assets(domain_name, keywords)` — path-score (0/1) + kw_score, capped ved max_assets
- `discover_domains(seed_list, discover_from_dir)` — seeds + domains/-mappe + roi_score-sortering
- `run_domain(domain_name, keywords) -> dict` — fuldt loop med snapshot-sammenligning og konvergensstop
- `run(seed_list, discover_from_dir, max_domains, keywords_map) -> list[dict]` — multi-domain orkestrering

**Return per domæne:** `{domain, status, completeness_score, new_information_score, iterations}`

---

### Opdaterede filer

#### `core/domain_state.py`
- Nyt felt: `new_information_score: float = 0.0` (backward-kompatibel, defaulter til 0.0 ved load)
- Ny metode: `update_new_information_score(score: float)` — runder til 4 decimaler

#### `run_domain_pipeline.py`
- Nye CLI-flag: `--engine`, `--seeds NAME [NAME...]`
- Branch `5a` for `DomainEngine` indsat før eksisterende `5b` (`DomainLoopEngine`)

```bash
# Convergence-baseret engine (ny)
python run_domain_pipeline.py --engine --stub
python run_domain_pipeline.py --engine --seeds messaging billing --max-domains 2
python run_domain_pipeline.py --engine --max-iterations 15 --max-assets-per-iter 50

# Domain-loop (eksisterende)
python run_domain_pipeline.py --loop --domain Messaging
```

---

### Tests (nye: 51)

| Klasse | Tests | Dækker |
|---|---|---|
| `TestComputeNewInformation` | 8 | Tom/fuld/delvis/normaliseret/threshold |
| `TestComputeCompleteness` | 6 | Tom, fuld, delvis, vægte sum, keys, clamping |
| `TestLoadDomainSnapshot` | 3 | Tom dir, entities, alle sektioner |
| `TestKeywordRelevance` | 6 | Ingen keywords, alle match, delvis, ingen match, id-match, tom asset |
| `TestGetKeywordsForDomain` | 4 | Kendt, case-insensitiv, ukendt fallback, alle seeds |
| `TestDomainEngineSelectAssets` | 5 | Global assets, keyword-match, ingen match, max_assets, rækkefølge |
| `TestDomainEngineDiscoverDomains` | 5 | Default seeds, custom seeds, dir-tilføjelse, ingen dubletter, roi-sort |
| `TestDomainEngineRunDomain` | 6 | Allerede complete, opretter dir, result keys, idle exit, saturated, new_info persisteret |
| `TestDomainEngineRun` | 4 | Processer seeds, max_domains, keywords_map, alle har status |
| `TestDomainStateNewInfoScore` | 4 | Default, update, save+reload, afrunding |
| **Total nye tests** | **51** | — |

```
488 passed in 27.11s  (+51 convergence domain engine)
```

---

## 19. DomainEngine v1 — Autonom domenepakke (30. marts 2026)

### Formål

Ny separat pakke `core/domain/` med en fuldt selvstændig autonomous domain-loop. Kører én iteration ad gangen (`run_once()`), eller til alle domæner er stabile (`run_all()`). Integreres i `ExecutionEngine` via den nye `run_domain_engine()`-metode.

**Adskiller sig fra `core/domain_engine.py`** (Section 18):
- Egen state-fil (`domains/domain_state.json`) med `DomainProgress`-records per domæne
- Separate model-filer per sektion (nummererede JSON-filer)
- Stub semantic analyzer (regex, ingen LLM endnu)
- Fuldt afkoblet fra `DomainLoopEngine`/`DomainPipeline`

---

### Filstruktur

```
core/domain/
    __init__.py
    domain_engine.py          ← DomainEngine: run_once() / run_all()
    domain_selector.py        ← pick_next(): in_progress → pending → None
    domain_asset_matcher.py   ← match_assets(): keyword + path heuristics
    domain_state.py           ← DomainProgress + DomainState
    domain_model_store.py     ← DomainModelStore: 10 nummererede section-filer
    domain_scoring.py         ← compute_completeness / compute_new_information / is_stable

core/domain/ai/
    __init__.py
    semantic_analyzer.py      ← analyze(): 9 insight keys, regex heuristics
    domain_mapper.py          ← merge(): dedup + sort lists
    refiner.py                ← refine(): normaliser, fjern nulls/blanks
```

---

### Domain seeds (10 stk.)

```python
DOMAIN_SEEDS = [
    "identity_access", "customer_administration", "messaging",
    "recipient_management", "subscriptions", "reporting",
    "monitoring", "benchmark", "pipeline_sales", "integrations",
]
```

---

### `domain_state.py` — `DomainProgress`

| Felt | Type | Default |
|---|---|---|
| `name` | str | — |
| `status` | str | `"pending"` |
| `iteration` | int | 0 |
| `completeness_score` | float | 0.0 |
| `new_information_score` | float | 0.0 |
| `matched_asset_ids` | List[str] | [] |
| `processed_asset_ids` | List[str] | [] |
| `gaps` | List[str] | [] |
| `last_updated_utc` | str | "" |

`DomainState`: `load()`, `save()` (atomisk), `ensure_domains(seed_list)`, `get(name)`, `all_domains()`.

---

### `domain_model_store.py` — sectionfiler

```
domains/{domain}/
    000_meta.json
    010_entities.json
    020_behaviors.json
    030_flows.json
    040_events.json
    050_batch.json
    060_integrations.json
    070_rules.json
    080_pseudocode.json
    090_rebuild.json
```

Alle skrivninger atomisk (`path.tmp` → `os.replace`). `sort_keys=True` på al JSON-output.

---

### `domain_scoring.py`

| Konstant | Værdi |
|---|---|
| `COMPLETENESS_THRESHOLD` | `0.90` |
| `NEW_INFO_THRESHOLD` | `0.02` |

Scorede sektioner: `entities`, `behaviors`, `flows`, `rules`, `events`, `integrations` (mål: 5/5/3/3/2/2).
`is_stable()`: begge betingelser skal gælde simultant.

---

### `DomainEngine`

| Metode | Beskrivelse |
|---|---|
| `run_once()` | Vælger næste domæne, matcher assets, analyserer, merger, gemmer |
| `run_all()` | Kører til alle domæner er stabile; per-domæne idle-guard (2 runs → force-stable) |

**Resumability**: state genindlæses fra disk ved hvert `run_once()`-kald.  
**Idempotency**: anden kørsel processerer 0 assets (allerede i `processed_asset_ids`).

---

### `ExecutionEngine.run_domain_engine()` (ny metode)

```python
engine.run_domain_engine(
    domains_root="domains",
    seed_list=None,           # None → DOMAIN_SEEDS
    max_assets_per_domain=0,  # 0 = unlimited
    verbose=True,
)
```

Returnerer result-dict eller `{"status": "all_stable", "domain": None}`.

---

### HOW TO RUN

```bash
# Én iteration (næste pending/in_progress domæne)
python -c "
from core.execution_engine import ExecutionEngine
e = ExecutionEngine(solution_root='C:/Udvikling/sms-service')
print(e.run_domain_engine(domains_root='domains'))
"

# Kør alle domæner til konvergens
python -c "
from core.asset_scanner import AssetScanner
from core.domain.domain_engine import DomainEngine
scanner = AssetScanner(data_root='data', solution_root='C:/Udvikling/sms-service')
engine = DomainEngine(scanner=scanner, domains_root='domains', verbose=True)
for r in engine.run_all():
    print(r)
"
```

---

### Tests (nye: 67)

| Klasse | Tests | Dækker |
|---|---|---|
| `TestDomainProgress` | 5 | Default status/scores, to_dict sort, from_dict roundtrip, manglende felter |
| `TestDomainState` | 7 | Load/save, ensure_domains, dedup, roundtrip, reset ved reload, unknown domain |
| `TestDomainSelector` | 5 | in_progress prioritet, pending→in_progress, alle stable→None, tom state |
| `TestDomainAssetMatcher` | 7 | Keyword-match, path-match, ingen match, sorteret, ingen dubletter, alle seeds har keywords |
| `TestSemanticAnalyzer` | 6 | Alle keys, tom asset, entities fra class, behaviors fra metode, path i pseudocode |
| `TestDomainMapper` | 5 | Tom insight, merge lists, dedup, sorteret output, alle keys |
| `TestRefiner` | 5 | Alle keys, nulls fjernet, sorteret, dedup, tom model |
| `TestDomainModelStore` | 6 | Load tom, save+load roundtrip, meta-fil, alle sectionfiler, ingen .tmp-filer, dedup |
| `TestDomainScoring` | 10 | Tom model, fuld model, delvis, ny info=0/!=0/tom baseline, is_stable alle kombinationer |
| `TestDomainEngine` | 11 | Alle stable→None, domain navn, required keys, opretter dir, persist state, idempotency, max_assets, stable ved konvergens, run_all stop, run_all alle domæner |
| **Total nye tests** | **67** | — |

```
555 passed in 23.62s  (+67 DomainEngine v1)
```

---

## 21. DomainEngine v2 — AI Reasoning Layer (30. marts 2026)

### Formål

Opgrader DomainEngine v1 med en gap-drevet, memory-backed AI reasoning layer. Additive kun — ingen breaking changes. V1 `run_once()` er uændret.

**Stop-betingelse (skærpet):** Begge konvergensbetingelser skal gælde i **2 på hinanden følgende iterationer** (v1 kræver kun 1):
- `completeness_score >= 0.90`
- `new_information_score < 0.02`

---

### Nye filer

| Fil | Klasse/Funktion | Ansvar |
|---|---|---|
| `core/domain/ai_prompt_builder.py` | `build_prompt()` | Type-specifik prompt per asset (7 typer) |
| `core/domain/ai_reasoner.py` | `AIProvider`, `HeuristicAIProvider`, `AIReasoner` | Provider-abstraktion + heuristisk implementation + reasoning-metoder |
| `core/domain/domain_memory.py` | `DomainMemory` | Persistér AI-afledt viden i `data/domain_memory.json` |
| `core/domain/domain_query_engine.py` | `DomainQueryEngine` | Gap-drevet asset-ranking og -selektion |
| `core/domain/domain_learning_loop.py` | `DomainLearningLoop` | 10-trins iterationsorkestrator |

---

### `ai_prompt_builder.py`

Bygger type-afhængige prompts for: `code_file`, `sql`, `wiki_section`, `work_items_batch`, `git_insights_batch`, `labels_namespace`, `pdf_section` + fallback.

Fælles JSON-schema der efterspørges: `intent`, `domain_role`, `entities`, `behaviors`, `rules`, `flow_relevance`, `events`, `integrations`, `rebuild_note`.

---

### `ai_reasoner.py`

| Klasse | Beskrivelse |
|---|---|
| `AIProvider` | Abstrakt interface — `generate_json(prompt, schema_name) -> dict` |
| `HeuristicAIProvider` | Regex-baseret stub. Deterministisk. Ingen LLM. Erstattelig med GPT/Copilot |
| `AIReasoner` | High-level reasoning-metoder |

**`AIReasoner`-metoder:**

| Metode | Returnerer |
|---|---|
| `analyze_asset(asset, domain_name)` | Alle INSIGHT_KEYS + `signal_strength` float |
| `cross_analyze(domain_model, domain_name)` | `{linked_pairs, flow_stubs, coverage, consistency}` |
| `detect_gaps(domain_model, domain_name)` | `list[dict]` med gap-records, sorteret høj→lav prioritet |
| `estimate_signal_strength(asset, domain_name)` | Float i [0.0, 1.0] |

**Gap ID-format:** `gap:<domain>:<type>:<slug>`

**Gap-typer:** `missing_entity`, `missing_flow`, `orphan_event`, `weak_rule`, `incomplete_integration`, `missing_context`

---

### `domain_memory.py`

Persisteret i `data/domain_memory.json` — atomisk skrivning.

**Struktur:**
```json
{
  "domains": {
    "<domain>": {
      "assets": { "<id>": { "semantic": {...}, "confidence": 0.8, "content_hash": "abc" } },
      "cross_analysis": {...},
      "gap_history": [ { "iteration": 1, "gaps": [...] } ]
    }
  }
}
```

**Caching:** `set_asset_insight()` springer over skrivning hvis `content_hash` er uændret → idempotent.

---

### `domain_query_engine.py`

Asset-score = `unprocessed_bonus(+2.0)` + `type_priority(0–0.7)` + `gap_score(0–1.0)` + `path_score(0–0.5)`

**Type-prioriteter:** `code_file=7`, `sql=6`, `wiki_section=5`, `work_items_batch=4`, `git_insights_batch=3`, `labels_namespace=2`, `pdf_section=1`

| Metode | Beskrivelse |
|---|---|
| `rank_assets_for_domain(domain_name, assets, memory, processed_ids)` | Fuld rangering, deterministisk tie-breaking på asset_id |
| `select_assets_for_iteration(domain_name, assets, gaps, processed_ids, max_assets=30)` | Uprocesserede gaps-orienterede assets først, capped |
| `expand_search_terms(domain_name, gaps)` | Domæne-tokens + gap `suggested_terms`, sorteret + deduped |

---

### `domain_learning_loop.py`

**10-trins iteration:**
1. Load domænemodel
2. Load memory
3. Detect gaps → snapshot i memory
4. Sæt gap-IDs på `DomainProgress.gaps`
5. Vælg assets via `DomainQueryEngine`
6. Analyser hvert asset (`AIReasoner`), cache i `DomainMemory`
7. Merge + refine
8. Cross-analyse
9. Beregn scores + opdater `consecutive_stable_iterations`
10. Persist model → memory → state

**Stop-betingelse:**
```python
def should_mark_stable(domain_state):
    return (
        completeness >= 0.90
        and new_info < 0.02
        and stable_streak >= 2   # _REQUIRED_STABLE_STREAK
    )
```

---

### Opdaterede filer

| Fil | Ændring |
|---|---|
| `core/domain/domain_state.py` | Nyt felt: `consecutive_stable_iterations: int = 0` (backward-kompatibel) |
| `core/domain/domain_scoring.py` | Ny funktion: `cross_source_consistency_score(model, memory, domain_name) -> float` |
| `core/domain/domain_engine.py` | Ny metode: `run_once_v2(data_root="data")` — bruger `DomainLearningLoop`; `run_once()` uændret |
| `core/execution_engine.py` | Ny metode: `run_domain_engine_v2(...)` — `run_domain_engine()` uændret |

---

### `DomainProgress` — opdateret feltliste

| Felt | Type | Default |
|---|---|---|
| `name` | str | — |
| `status` | str | `"pending"` |
| `iteration` | int | 0 |
| `completeness_score` | float | 0.0 |
| `new_information_score` | float | 0.0 |
| `matched_asset_ids` | List[str] | [] |
| `processed_asset_ids` | List[str] | [] |
| `gaps` | List[str] | [] |
| `last_updated_utc` | str | "" |
| `consecutive_stable_iterations` | int | 0 | ← **NY (v2)** |

---

### HOW TO RUN (v2)

```bash
# Én v2-iteration (næste pending/in_progress domæne)
python -c "
from core.execution_engine import ExecutionEngine
e = ExecutionEngine(solution_root='C:/Udvikling/sms-service')
print(e.run_domain_engine_v2(domains_root='domains'))
"

# Direkte via DomainEngine
python -c "
from core.asset_scanner import AssetScanner
from core.domain.domain_engine import DomainEngine
scanner = AssetScanner(data_root='data', solution_root='C:/Udvikling/sms-service')
engine = DomainEngine(scanner=scanner, domains_root='domains', verbose=True)
print(engine.run_once_v2(data_root='data'))
"
```

---

### Tests (nye: 89)

| Fil | Tests | Dækker |
|---|---|---|
| `tests/test_ai_reasoner.py` | 26 | `HeuristicAIProvider`, `AIProvider`, `AIReasoner.analyze_asset`, `.cross_analyze`, `.detect_gaps`, `.estimate_signal_strength` |
| `tests/test_domain_memory.py` | 22 | Persistens, roundtrip, asset-caching, cross-analysis, gap-historik, `get_domain_data` |
| `tests/test_domain_query_engine.py` | 18 | `expand_search_terms`, `rank_assets_for_domain`, `select_assets_for_iteration` |
| `tests/test_domain_learning_loop.py` | 23 | Stop-betingelser, iteration-shape, state-opdateringer, persistens, memory-caching, `max_assets`-cap |
| **Total nye tests** | **89** | — |

```
644 passed in 26.34s  (+89 DomainEngine v2)
```

---

## 20. run_domain_engine.py — CLI runner (30. marts 2026)

### Formål

Standalone CLI entry point for `DomainEngine v1` (`core/domain/`).

### Kommandooversigt

```bash
# Vis status for alle domæner (ingen processering)
python run_domain_engine.py --dry-run

# Én iteration (næste pending/in_progress domæne)
python run_domain_engine.py --once

# Én iteration, maks 50 assets
python run_domain_engine.py --once --max-assets 50

# Kør alle domæner til konvergens
python run_domain_engine.py

# Kun specifikke domæner
python run_domain_engine.py --seeds messaging monitoring

# Nulstil al domain-state
python run_domain_engine.py --reset-all

# Tilpasset domains-mappe
python run_domain_engine.py --domains-root my_domains/

# Undertrykker progress-output
python run_domain_engine.py --quiet
```

### Første kørsel (verificeret)

```
identity_access: matched=135  pending=10  completeness=0.25  new_info=0.00
```

Alle 10 domæner starter som `pending`. Scanner matcher automatisk assets via `domain_asset_matcher.py`.

---

## 22. DomainEngine v3 — Discovery + Autonomous Search (30. marts 2026)

### Formål

Fuldautomatisk, discovery-first pipeline. Ingen seed-liste nødvendig. Systemet finder selv domænerne, sorterer dem i rækkefølge og kører hvert domæne til konvergens med gap-drevet corpus-udvidelse.

**Ny flowsekvens:**
1. **Scan** — alle assets via `AssetScanner`
2. **Discover** — `DomainDiscoveryEngine` identificerer domæner via vokabular-match + sti-token-clustering
3. **Prioritize** — `DomainPrioritizer` beregner build-rækkefølge (foundation-tier-regler + coupling-score)
4. **Analyze** — `DomainLearningLoop` + `DomainAutonomousSearch` kører hvert domæne til stable
5. **Persist** — `discovered_domains.json` + `domain_priority.json` + alle v1/v2 model-filer

---

### Nye filer

| Fil | Klasse | Ansvar |
|---|---|---|
| `core/domain/domain_discovery.py` | `DomainDiscoveryEngine`, `DomainCandidate` | Opdager forretningsdomæner fra assets (vokabular + sti-tokens) |
| `core/domain/domain_prioritizer.py` | `DomainPrioritizer` | Beregner build-rækkefølge (13 foundation-tier-regler + coupling) |
| `core/domain/domain_autonomous_search.py` | `DomainAutonomousSearch` | Konverterer gap-records til ranked asset-selektion fra hele corpus |
| `core/domain/domain_engine_v3.py` | `DomainEngineV3`, `run_domain_engine_v3()` | V3 orkestrerings-entrypoint |

---

### `domain_discovery.py`

**To faser:**
- **Fase 1 — Vokabular-match:** scorer `_DOMAIN_KEYWORDS` mod asset-indhold
- **Fase 2 — Sti-token-clustering:** grupperer assets på delte namespace-tokens

**`DomainCandidate`-felter:** `domain`, `confidence`, `keywords`, `sources`, `estimated_size` (`small`/`medium`/`large`), `reasoning`

**Confidence-formel:** `asset_score(0–0.70)` + `diversity(0–0.15)` + `kw_depth(0–0.10)`

**Output:** sorteret confidence desc → domain name asc (deterministisk)

**JSON-output:** `data/domains/discovered_domains.json`

---

### `domain_prioritizer.py`

**13 foundation-tier-regler** (lavest matchende tier vinder):

| Tier | Domænetyper |
|---|---|
| 1 | identity, auth, login, token, jwt, oauth |
| 2 | user, customer, account, profile, tenant |
| 3 | permission, role, policy, privilege |
| 4 | message, sms, email, notification, send, deliver |
| 5 | recipient, contact, subscriber, distribution |
| 6 | subscription, billing, payment, invoice |
| … | … |
| 50 | sales, crm, lead, opportunity |

**Sorteringsnøgle:** `(tier asc, -coupling asc, domain asc)` — fuldt deterministisk

**JSON-output:** `data/domains/domain_priority.json`

---

### `domain_autonomous_search.py`

**`DomainAutonomousSearch(query_engine)`-metoder:**

| Metode | Returnerer |
|---|---|
| `search(intent, domain, assets, gap_types, max_results)` | `[{"asset_id": str, "score": float}]` |
| `gap_to_intents(gap, domain)` | `list[str]` — max 3 intents per gap |
| `find_assets_for_gaps(gaps, domain, assets, memory, max_per_gap, max_gaps)` | `list[dict]` — faktiske asset-dicts sorteret efter score |

**Intent-udvidelse:** CamelCase-split → noise-fjernelse → synonym-udvidelse (12 entries)

**Synonym-eksempler:** `entity → [entity, object, model, record]`, `flow → [flow, process, pipeline, step]`

---

### Opdaterede filer

| Fil | Ændring |
|---|---|
| `core/domain/domain_learning_loop.py` | Ny param `search_engine: Optional[Any] = None` + `all_assets: Optional[List[Dict]] = None` i `run_iteration()` + trin 4b: gap-drevet pool-udvidelse |

**Trin 4b (nyt):** Hvis `search_engine` er sat og der er gaps, kalder `find_assets_for_gaps()` på hele corpus (`all_assets`). Nye asset-IDs appendes til kandidat-puljen.

**Bagudkompatibel:** `search_engine=None` (default) → ingen ændring i eksisterende adfærd.

---

### `DomainProgress` — opdateret feltliste (v3)

| Felt | Type | Default | Version |
|---|---|---|---|
| `consecutive_stable_iterations` | int | 0 | v2 |
| `last_significant_change` | str | "" | v2 |
| `current_focus` | str | "" | v2 |
| `evidence_balance` | dict | {} | v2 |

---

### HOW TO RUN (v3)

```python
from core.domain.domain_engine_v3 import run_domain_engine_v3
from core.asset_scanner import AssetScanner

scanner = AssetScanner(data_root='data', solution_root='C:/Udvikling/sms-service')
results = run_domain_engine_v3(
    scanner=scanner,
    domains_root='domains',
    data_root='data',
    seed_list=[],          # tomt = kun discovery
    max_iterations_per_domain=50,
    verbose=True,
)
```

---

### Tests (nye: 54)

| Testklasse | Tests | Dækker |
|---|---|---|
| `TestDomainDiscovery` | 13 | discover([])→[], finder messaging, confidence i [0,1], estimated_size valid, ingen nulls, deterministisk, sorteret desc, save/load round-trip, to_dict/from_dict, min_match_count |
| `TestDomainPrioritizer` | 8 | prioritize([])→[], 1-indekseret, identity før messaging, required keys, tier > 0, deterministisk, save/load round-trip, enkelt kandidat |
| `TestDomainAutonomousSearch` | 12 | search([])→[], scored dicts, scores ≥ 0, deterministisk, gap_to_intents, max 3 intents, find_assets_for_gaps([])→[], asset dicts returneret, deterministisk, tokenize, synonymer, max_results |
| `TestLearningLoopV3` | 7 | search_engine=None default, run_iteration uden search_engine, all_assets=None, med search_engine uden gaps, pool-expansion, alle score-keys, bagudkompatibilitet |
| `TestDomainEngineV3` | 9 | constructor, discover_and_prioritize tuple, tom discover, deterministisk, run returnerer list, domain key, resume, convenience-funktion, output-filer skrevet |
| **Total** | **54** | — |

### Samlet testantal

```
platform win32 -- Python 3.11.9, pytest-9.0.2
762 passed in 30.18s  (+54 DomainEngine v3)
```
