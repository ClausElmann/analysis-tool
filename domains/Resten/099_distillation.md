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
