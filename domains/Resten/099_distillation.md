# Resten — Distillation

**Authority Layer:** Layer 1 (Derived Conceptual SSOT)
**Source-primary:** UI systematisk gennemgang — filer uden klart domænetilhør
**Status:** Under opbygning (systematisk pass)

---

## 1. Formål

Samler UI-komponenter og services der er tværgående infrastruktur og ikke tilhører et specifikt forretningsdomæne.

---

## 2. app-module — App Shell & Navigation

### AppComponent (`app.component.ts` / `.html`)
- Rod-komponent for hele appen
- Håndterer: router-animationer, global SSE-lytter, profil-valg efter login, operationelle beskeder (notification bar), impersonation-mode styling
- Loader bruger + profil ved opstart via `UserService` + `ProfileService`
- Bruger `ProfileService.userHasSomeConversations()` til at bestemme om Conversation-badge skal lyttes på

### AppHeaderComponent (`app-header.component.ts` / `.html`)
- Topbar i alle sider
- **Indhold:**
  - Logo → link til broadcasting
  - Profile dropdown (desktop) — `ProfileSimpleDto[]`, skift profil → trigger `GlobalStateAndEventsService`
  - `UserMenuComponent` (hvis logget ind) ellers Login-knap
  - `BiAppNavigationBarMobileComponent` ved < 768px
- **Test mode:** `host.[class.test-mode]` hvis `testModeEnabled()`
- **Impersonation mode:** `host.[class.impersonation-mode]` hvis `authService.isImpersonating`
- **Country-specifikt logo:** `ServiceAlert_{land}_white_background.svg` udledt af hostname

### UserMenuComponent (`user-menu.component.ts` / `.html`)
- Popover-menu (PrimeNG) åbnet via bruger-ikon i header
- **Links:** My User settings, Terms & Conditions, Logout
- **Test mode toggle:** `bi-switch` + `onToggleTestMode` output
- **Profil-dropdown (mobil):** Vises kun ved `currentProfile()` + lille skærm

### UserHasNoProfileAccessDialogContentComponent
- Simpel dialog: vises når bruger logger ind men ingen profil har adgang
- Tekst: `login.UserHasNoProfileAccess` + OK-knap

### ProfileHasNoAccessDialogContentComponent
- Simpel dialog: vises i navigation context når profil ikke har adgang til conversations
- Tekst: `conversations.ProfileHasNoAccess` + OK-knap

---

## 3. app-module/navigation-bar — Venstre navigationsmenu

### BiAppNavigationBarBaseComponent (abstrakt)
- Abstract base for desktop + mobil navigationsbars
- **Menu-items (betinget):**
  - Broadcasting (altid, dog limiteret bruger → `RouteNames.broadcastingLimited`)
  - Conversations (kun hvis profil har conversations + `listenForConversationMessageCountEvents`)
  - Status (`RouteNames.statusRoutes.main`) — kræver `ManageReports` user-rolle
  - Administration (`RouteNames.adminRoutes.main`)
  - Support (`RouteNames.support`)
  - Pipeline (`RouteNames.pipelineRoutes.main`) — kun SuperAdmin
- **SSE badge:** `unreadConversationMessagesCount` signal opdateres via `ConversationMessagesListenerService`

### BiAppNavigationBarComponent (desktop)
- Extends base; `host.class = "hidden md:block w-6rem"` — vises kun ≥ 768px
- Sidebar lodret layout

### BiAppNavigationBarMobileComponent
- Extends base; slide-in overlay ved `isOpen = true`
- `isOpen = model<boolean>()` — lukkes ved klik på item

### BiAppNavigationbarItemComponent
- Enkelt menu-item: `routerLink` + `icon` (FA) + `label` (i18n) + valgfrit `badgeLabel`
- `isActive` signal sættes via `routerLinkActive`
- `mobileLayout` input skifter layout mellem vertikal (desktop) og horisontal (mobil)

### ConversationMessagesListenerService
- Injectable service (per navigation-bar instans)
- Starter SSE-lytter (`ServerSentEventManagerService`) hvis bruger er logget ind
- Filtrerer `CONVERSATION_UNREAD_STATUS`-events → returnerer `totalUnreadCount` observable
- Stopper SSE ved logout

---

## 3b. models/ — Frontend datamodeller

Udvidede DTO'er og frontend-specifikke modeller (ikke openapi-genererede).

| Fil | Indhold |
|---|---|
| `models/common/ClientSentEvent.ts` | `{eventType: ServerSentEventType, payload: string}` — SSE event wrapper |
| `models/common/IdAndValueGeneric.ts` | `{id: number, value: T}` — generisk patch-payload |
| `models/conversations/ConversationPhoneNumberModel.ts` | Extends `ConversationPhoneNumberDto` + `getSenderNumberValue()` static helper |
| `models/message/LookupProgressDto.ts` | `{smsGroupId, message, counts: {type,count}[]}` — prelookup progress |
| `models/message/MessageTypeEnum.ts` | `MessageType` enum: SMS, WEB, e-Boks, Internal, Benchmark, InfoPortal, Facebook, X, Voice, Email |
| `models/message-template/MessageTemplateModelExt.ts` | Extends `MessageTemplateDto` + `templateBenchmark` + `dynamicMergefields` |
| `models/message-template/TemplateMergeFieldDtoExt.ts` | Extends `TemplateMergeFieldDto` + `isDynamic`, `selected`, `isFromDate` |
| `models/message-template/TemplateBenchmarkModelExt.ts` | Benchmark-template extension |
| `models/profile/ProfileTypeExt.ts` | Extends `ProfileTypeModel` + `translationKey` + `isSupplyType` |
| `models/std-receiver/StdReceiverGroupWithGroupInfo.ts` | StdReceiver med gruppe-info (id, name, isManaged, hasKeyword, ftpFilePath) |
| `models/CompanyInfo.ts` | Land-specifik firmainfo (navn, adresse, tlf, email) — DK/SE/FI/NO specificeret via switch |
| `models/customer/ICustomerFtpSetting.ts` | FTP-indstillinger for kunde |

**Note om `MessageType` enum:** Dette er den kanoniske liste over alle kanaltyper i systemet. Bruges til at klassificere SmsGroup-beskeder.

---

## 3c. core/ — Infrastruktur

### HTTP Interceptors
- **`BiAuthInterceptor`:** 401 handler — refresher access token automatisk, kø'er ventende requests, 403 → logout
- **`BiBearerHeaderInterceptor`:** Tilføjer `Authorization: Bearer {token}` header på alle requests (undtagen refresh-endpoint)

### Routing Guards
- **`AppCanActivateGuard`:** Global auth-guard — ikke-logget bruger → `/login`; gemmer `routeAfterLogin` i state
- **`ProfileRoleRouteGuard`:** Check af `ProfileRoleNames` på current profile; afviser adgang hvis profil mangler rolle
- **`limitedUserGuardFunc`:** Functional guard — blokerer LimitedUser fra normale routes eller omvendt
- **`user-role.guard`:** UserRole-baseret guard (parallel til profile-role)
- **`app-can-deactivate.guard`:** CanDeactivate guard (unsaved changes warning)
- **`BiCustomRouteReuseStrategy`:** Custom reuse — ruter med `data.reuseComponent: true` genbruges; `clearReusedComponents` rydder cachen

### Security
- **`TokenAuthenticationService`:** Interface (InjectionToken) — definerer login/logout/2FA/QR-metoder; implementeret som `AuthenticationService`
- **`authentication.service.ts`:** Konkret implementation (JWT storage, refresh-token timer, impersonation)

### SSE Infrastruktur (ServerSentEventManagerService)
Singleton SSE-forbindelsesstyrer. Events dispatches til typed handlers:

| SSE EventType | Handler | Payload |
|---|---|---|
| `CONVERSATION_UNREAD_STATUS` | `ConversationUnreadStatusSSEHandler` | `{totalUnreadCount, conversationId?, unread}` — akkumulerer tæller |
| `CONVERSATION_CREATED` | `ConversationCreatedHandler` | Ny conversation oprettet |
| `CONVERSATION_MSG_SENT` | `ConversationMessageSentHandler` | Besked sendt i conversation |
| `LOOKUP_PROGRESS` | `LookupProgressHandler` | `LookupProgressDto {smsGroupId, message, counts[]}` |
| `PROGRESSWATCHERINFO` | `ProgressWatcherInfoHandler` | `{job, currentTask, progress, complete}` — job-monitoring |
| `ACTIVEJOBS` | `ActiveJobsHandler` | `JobTaskDto` — live job-tabel opdatering |

- Auto-reconnect ved disconnect
- Stopper ved logout (`globalStatesAndEvents.loggedOut`)

### Utility Interfaces
- `ICustomerAccountFields`: `{showPricePerEboks, showPricePerAddressLookup, showInvoiceContact, showInvoiceReference}` — betingede felter i kundeoprettelse
- `FromAndToDatesAndTimes` / `FromAndToDateTimes`: Date-range interfaces brugt i søgeformularer
- `AddressColumns`: Kolonnenavne for adresse-imports

### GlobalStateAndEventsService
BiStore-baseret global applikationsstate:
- `countries[]` — liste af lande med id + navn (indlæst ved translation-ready)
- `routeAfterLogin` — gemt rute til brug efter login-redirect
- Subject-baserede events: `loggedOut`, `profileChanged`, `notificationEvent`

### TemplateToolsService
Service til merge-field håndtering i skabeloner:
- Indsæt/fjern merge fields i beskedtekst
- Dynamiske merge fields (dato-parametre)
- Validering af merge field-input

---

## 4. Infrastruktur-noter

- **Route-animationer:** `app-router-transitions.animation.ts` — slide/fade transitions ved route-skift
- **Scroll-handler:** `app-routing-scroll-handler.function.ts` — restore scroll position ved navigation
- **App shell:** `app.config.ts` — Angular application config (providers, bootstrapping)

---

## 5. Filer i dette domæne

| Fil | Funktion |
|---|---|
| `app-module/app-header/app-header.component.*` | Topbar med logo, profil-skift, user-menu |
| `app-module/app-header/user-has-no-profile-access-dialog-content.component.ts` | Dialog: ingen profil-adgang |
| `app-module/app-header/user-menu/user-menu.component.*` | Popover user-menu |
| `app-module/app-router-transitions.animation.ts` | Route-animationer |
| `app-module/app-routing-scroll-handler.function.ts` | Scroll restore |
| `app-module/app.component.*` | Rod-komponent |
| `app-module/app.config.ts` | Angular app config |
| `app-module/navigation-bar/bi-app-navigation-bar-base.component.ts` | Abstract navigationsmenu base |
| `app-module/navigation-bar/bi-app-navigation-bar-item/*` | Enkelt menu-item komponent |
| `app-module/navigation-bar/bi-app-navigation-bar-mobile.component.ts` | Mobil slide-in menu |
| `app-module/navigation-bar/bi-app-navigation-bar.component.*` | Desktop sidemenu |
| `app-module/navigation-bar/conversation-messages-listener.service.ts` | SSE unread-badge lytter |
| `app-module/navigation-bar/profile-has-no-access-dialog-content.component.ts` | Dialog: profil ingen adgang |


---

## 5. core/services — Infrastruktur-services (ingen specifik domænebinding)

### BiLocalAndSessionStorageService
**Fil:** `core/services/bi-local-and-session-storage.service.ts`

Abstraktion over browser `localStorage` og `sessionStorage`. Alle get/set operationer JSON-serialiseret.
- `setItem / getItem` (localStorage)
- `setSessionItem / getSessionItem` (sessionStorage)  
- `removeItem`, `removeSessionItem`, `clearLocal`

### FileManagementService
**Fil:** `core/services/file-management.service.ts`  
**Extends:** `BiStore<FileManagementServiceState>`

Profil-filopbevaring (uploadede filer til brug i broadcast-beskeder).
- `getAllFiles(profileId)` — cached pr. profil
- `downloadFile(fileId)` — ArrayBuffer download
- `deleteStorageFile(fileId)` — slet + opdater cache
- `uploadFile(formData, profileId)` — upload fil

### SupportService
**Fil:** `core/services/support.service.ts`

| Metode | Beskrivelse |
|---|---|
| `sendSupportCase(model)` | Send supportsag (FormData: navn, email, tekst, version) |
| `getWebinars()` | Henter liste over webinarer (`WebinarDto[]`) |
| `getWebinarLink(id)` | Henter unik webinar-link-URL |
| `downloadWebinarLogsReport()` | Download webinar-deltagelsesrapport |

### UserNudgingService
**Fil:** `core/services/user-nudging.service.ts`  
**Extends:** `BiStore<UserNudgingState>`

Kontrollerer om brugeren skal "nudges" (f.eks. til en NPS-undersøgelse).
- `getUserNudgingBlocks(smsGroupId?)` — check om blokering gælder
- `saveUserNudgingResponse(type, neverAgain, response, smsGroupId?)` — gem brugers svar
- `saveCustomerSurveyNudgingResponse(response)` — gem survey-svar (opdaterer lokal state + postpone-timestamp)
- `isSurveyNudgingEnabled()` — Observable af survey-status

### MapAdministrationService
**Fil:** `core/services/map-administration.service.ts`

Admin af kort-lag (til super-admin kort-opsætning):
- `getMapLayers()` — alle kort-lag
- `getMapLayer(id)` — enkelt lag
- `updateMapLayer(cmd)` — opdater lag
- `getMapLayerMappings(mapLayerId)` — mappings (kunde/profil til lag)
- `createMapLayerMapping(cmd)` / `updateMapLayerMapping(cmd)` — CRUD mappings
- `deleteMapLayerMapping(mapLayerId, customerId, profileId?)` — slet mapping

---

## UI-lag: features/support

**Filer:** `features/support/` (6 filer)
**Domain:** Resten (support / customer-service)

### SupportComponent (support.component.ts/.html)
Support-side med:
- Supportformular <support-case-form> med reCAPTCHA (
g-recaptcha-2) og indsend via SupportService
- Webinar-liste <webinars-list> med kommende webinarer
- Hosted for offentlig adgang (ingen login krav til formular, men auto-udfylder bruger-info hvis logget ind)
- Sprog bestemmes af hostnavn → korrekt land-URL

### SupportCaseFormComponent (support-case-form/)
Formular: navn, email, emne, besked. Kalder SupportService.createSupportCase().

### WebinarsListComponent (webinars-list/)
Viser liste af kommende webinarer hentet via SupportService.getWebinars().
---

## UI-lag: features-shared (diverse)

### SmsConversationsAdminComponent (features-shared/sms-conversations-admin/)
Admin-interface for SMS-samtale-numre. Kan tilgås fra Customer-admin og Super-admin. Viser ConversationPhoneNumberWithProfileIdsDto[]. Sub-komponenter: AssignConversationNumberComponent (tildel nummer til profiler), EditNameAndProfileMappingsComponent (redigér navn og profil-mapping). Detekterer context (super vs customer) via router URL.

### SmsStatisticsTableComponent (features-shared/sms-statistics-table/) — 3 filer
Genbrugelig tabel der viser SMS-statistik (antal sendt, leveret, fejl) pr. periode. Bruges i Benchmark og andre statistik-visninger.

### BiDataImportComponent (features-shared/bi-data-import/) — se data_import domain

### BiFooterComponent (features-shared/bi-footer/) — 2 filer
Sidefod med copyright, version, links.

### CustomerContactPersonFormComponent (features-shared/customer-contact-person-form/) — 2 filer
Genbrugelig formular til kontaktperson (navn, stilling, email, telefon). Bruges i customer-admin og pipeline.

### CustomerCreateEditComponent (features-shared/customer-create-edit/) — 3 filer
Genbrugelig formular til opret/redigér kunde-stamdata (navn, adresse, CVR etc.). Bruges fra super-admin og customer-admin.

### CustomerGdprAcceptComponent (features-shared/customer-gdpr-accept/) — 4 filer
GDPR data-behandleraftale accept-formular. Viser aftaletekst (PDF), kontaktperson-felt, accept-checkbox. Bruger BiPdfService til PDF-visning.

### FilesourceEditorComponent (features-shared/filesource-editor/) — 2 filer
Editor til filkilde-konfiguration (FTP/SFTP/HTTP-filimport opsætning). Bruges i data-import admin.

### StatstidendeMainComponent (features-shared/statstidende/) — 7 filer
Statstidende-integration. Container med faner. StatstidendeService — HTTP service til statstidende-modtagere. StatstidendeReceiversComponent — tabel af statstidende-modtagere med CRUD.

### SendTestMessageBaseComponent (features-shared/send-test-message/) — 5 filer
Base-klasse + concrete implementations for Send Test SMS (SendSmsOrVoiceTestMessageComponent) og Send Test Email (SendEmailTestMessageComponent). Bruges i wizard write-message trin.
---

## UI-lag: shared/

**Filer:** `shared/` (253 filer) — fælles UI-bibliotek
**Domain:** Resten (primært) / messaging / address_management

### shared/classes/
- **ApiRoutes** — centrale API endpoint-konstanter for alle HTTP-kald
- **RouteNames** — centrale route-sti-konstanter for Angular Router
- **BiCustomValidators** — custom Angular FormValidators (min/maks SMS-længde, telefonnummer, datoer, adgangskode-match)
- **EmailValidator** — email-validerings-helper
- **StdReceiversDataManager** — hjælpeklasse til standard-modtager-datastyring
- **StylingAndLayoutUrlParams** — URL-parameter konstanter til layout/styling
- **sse-subscription.factory** — factory til SSE (Server-Sent Events) abonnementer
- **BICustomAnimations** — ekstra Angular-animationer

### shared/interfaces-and-enums/
- **UserRoleEnum** — alle brugerroller i systemet
- **ServerSentEventType** — SSE event-typer (ConversationMessageReceived, BroadcastStatusUpdated etc.)
- **BiTreeNode** — genbrugelig tree-node interface til hierarkiske datastrukturer
- **BiWizardStep** — interface for wizard-trin
- **SubscriptionTypes** — abonnements-type enum
- **SocialMediaStatus** — social medie-status enum
- **QuickResponseSetupDto** — QuickResponse opsætnings-model

### shared/pipes/ — 11 filer
- **BiSlicePipe** — array slice til templates
- **BiSortPipe** — generisk sortering
- **BiMsgCountPipe** — SMS-karakter-optælling
- **BiAreStringsEqualPipe** — sammenligning af strings i templates
- **CountryIdToTranslateKeyPipe** — country ID → i18n nøgle
- **HighlightTextPipe** — HTML-highlight af søgetekst
- **LanguageIdFormatPipe** — sprog-ID formattering
- **NumberToArrayPipe** — konverter tal til array (til *ngFor loops)
- **SupplytypeFilterPipe** — filtrering af supply-typer
- **UsedForToImportPurposePipe** — konvertering til import-formål
- **BiPipesModule** — samler alle pipes i et modul

### shared/directives/ — 5 filer
- **BiRequireRolesDirective** — structural directive til rolle-baseret UI-skjul (*biRequireRoles)
- **BiDisableControlDirective** — disable reactive form controls
- **DebouncedClickerDirective** — click-debouncing directive
- **StickySecondaryElementDirective** — sticky positionering
- **BiPTemplateDirective** — PrimeNG template adapter

### shared/variables-and-functions/ — 5 filer
- **helper-functions.ts** — generelle hjælpefunktioner (string-checks, isNullOrEmpty, scrollTo, uniqueID etc.)
- **general-variables.ts** — konstanter (smsMaxLength=160, smsUnicodeMaxLength, smsSendAsMinLength etc.)
- **LocalStorageItemNames.ts** — localStorage nøgle-konstanter
- **WindowSessionStorageNames.ts** — sessionStorage nøgle-konstanter
- **primeNg-utilities.ts** — PrimeNG-specifikke hjælpefunktioner

### shared/components/ — 209 filer (STORE KATEGORIER)

**Dialog-content (30 filer):**
- ctivity-log-dialog-content — aktivitets-log dialog
- i-create-new-pass-error-dialog-content — fejlbesked ved password-oprettelse
- i-dialog-spinner — loading-spinner dialog
- i-merge-field-dialog-content — udfyld merge fields dialog
- i-mergefield-conflict-dialog-content — merge field konflikthåndtering
- i-profile-selection-dialog-content — profilvalg dialog
- create-broadcast-dialog — beknr. og afsend broadcast dialog
- dialog-with-text-input — simpel text-input dialog
- conomic-report-dialog-content — e-conomic rapport dialog
- dit-smsGroupSchedule-dialog — redigér SMS-planlagte udsendelser
- manage-product-dialog — produkt/pakke administrations-dialog
- map-coords-dialog — kort koordinat-dialog
- 	ext-template-overwrite-or-append-dialog — vælg overskrivning/tilføjelse af template

**Tabeller (29 filer):**
- i-p-table — generisk PrimeNG-wrapper tabel med sortering/filtrering
- i-p-table-with-checkboxes — tabel med multi-vælg checkboxes
- i-item-indicator-table — tabel med farve-indikatorer

**Send Methods (11 filer):**
- SendMethodsListComponent — viser tilladte send-metoder som klikkbare knapper (by-address, by-level, by-map, by-municipality, by-excel)
- BiMessageResendDialogContentComponent — dialog til resend af besked
- BiMessageResendSimpleDialogContentComponent — simpel resend dialog

**Input Components (22 filer — bi-custom-inputs/):**
- BiDateAndTimeInputModule, BiDateInput, BiTimeInput
- BiPasswordInputComponent — password input med vis/skjul
- BiTextAreaModule
- Øvrige custom inputs

**eBoks Preview (13 filer):**
- EboksDesktopPreviewComponent — eBoks besked forhåndsvisning (desktop)
- EboksMobilePreviewComponent — mobil forhåndsvisning
- Tilhørende stilkomponenter

**Email Preview (8 filer):**
- BiEmailPreviewComponent + tilhørende sub-komponenter

**Quick Response Setup (10 filer):**
- BiQuickResponseSetupEnablerComponent — aktivér/konfigurér QuickResponse på besked

**File Upload (10 filer):**
- BiFileUploaderComponent — generisk fil-upload med validering
- Sub-komponenter til status og fejlvisning

**Std Receiver Tree (8 filer):**
- StdReceiverTreeNodeComponent + sub-nodes — hierarkisk modtager-træ

**De øvrige komponenter (enkelt-filer):**
- BiAddressSearchInputComponent — adressesøgnings-input
- BiDesktopFrameComponent — desktop-frame wrapper
- BiEditableTextComponent — inline edit
- BenchmarkCreateEditComponent — benchmark CRUD
- AdvancedVoiceSettingsComponent — avancerede voice-indstillinger
- BiListBoxComponent — genbrugelig listeboks
- BiMenuComponent — menu-komponent
- BiPhoneFrameComponent — telefon-frame wrapper
- BiProspectTasksViewComponent — pipeline prospect opgave-visning
- BiSelectionListComponent — multi-select liste
- BiSettingsLinkComponent — link til indstillinger
- BiSmsEmailCountingBoxComponent — SMS/email tegn-tæller-boks
- BiTabsComponent — generisk fane-komponent
- BiTextSaveCancelComponent — inline edit med gem/annuller
- BoxWithCheckboxesComponent — checkbox-gruppe
- CountryCustomerProfileSelectionComponent — land/kunde/profil-selector
- IframeUrlParamDescriptionsComponent — IFrame URL parameter beskrivelse
- IndividualMsgSettingsDisplayBoxComponent — vis individuelle besked-indstillinger
- LatestMsgBoxComponent — boks med seneste beskeder (broadcasting)
- ListsComponent — diverse liste-visninger
- BiIndicatorIconComponent — farve-indikator ikon
- BiFullCalendarComponent — kalender-visning
- BiImageUploaderComponent — billede-upload
- BiShowMessagePreviewComponent — standard besked-forhåndsvisning
- BiQuickResponseSetupEnablerComponent — quickresponse setup