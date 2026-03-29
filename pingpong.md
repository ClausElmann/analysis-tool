# ServiceAlert — Komplet Arkitektrapport (29. marts 2026)

> Baseret på dybdegående scanning af hele `c:\Udvikling\sms-service` med særligt fokus på Angular-frontenden.

---

## 1. Pipeline — Final Status

### Slice-resultater

| Slice | Status | Items | Output-fil | Indhold |
|---|---|---|---|---|
| SLICE_0 | OK | 36 | `solution_structure.json` | Projektklassificering |
| SLICE_0_5 | OK | 3 | `wiki_signals.json` | Wiki-signaler |
| SLICE_0_7 | OK | 41 | `pdf_capabilities.json` | PDF-kapabiliteter |
| SLICE_0_8 | OK | 3395 | `git_insights.json` | Git-historik |
| SLICE_9 | OK | 319 | `db_schema.json` | DB-tabeller |
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
289 passed in 43.21s
```

### Output-filer (24 filer)

| Fil | Items | Key |
|---|---|---|
| `solution_structure.json` | 36 | projects |
| `wiki_signals.json` | 3 | capabilities |
| `pdf_capabilities.json` | 41 | capabilities |
| `git_insights.json` | 3395 | insights |
| `db_schema.json` | 319 | tables |
| `label_map.json` | 115 | namespaces |
| `angular_entries.json` | 69 | entry_points |
| `angular_apps.json` | 14 | apps (routes across 3 sub-apps) |
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

## 12. Kendte arkitektoniske observationer

1. **Dual-app arkitektur:** Systemet har to brugerfrontender — Angular SPA (`ServiceAlert.Web`) og Razor MVC-sider (enrollment, SAML2). Disse deler backend-tjenester men har separate authentication-flows.

2. **Kø-heterogenitet:** SMS/Email bruger SQL-tabelkøer (Background Services), Voice bruger RabbitMQ. Arkitekturdokumentationen noterer dette som et anerkendt teknisk gæld.

3. **Nordisk multi-country:** Adresse-pipelines for 4 lande (DK, NO, SE, FI) kører som separate batch-jobs med separate HTTP-klienter og importers.

4. **3-lags permission-model:** UserRole (system-niveau) + ProfileRole (profil-niveau) + ApiKey (integration-niveau). Alle tre tjekkes uafhængigt.

5. **SAML2 per kunde:** Hver kunde kan have sin egen IdP-konfiguration (`CustomerSamlSettings`), cached i `IMemoryCache`.

6. **Angular 20 — moderne patterns:** Bruger `inject()` DI, standalone components, `loadComponent()` lazy-loading, og signal-baseret state (`set()`, `signal()`).
