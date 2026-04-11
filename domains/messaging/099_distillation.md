# messaging — Domain Distillation

**Status:** APPROVED_BASELINE 2026-04-11  
**Completeness score (Layer 1):** 0.47 (behaviors=[] rules=garbage — source-primary)  
**Evidence source:** `message-wizard/` Angular feature, `SmsSendMethod` OpenAPI enum, `WizardStep` enum  

---

## What this domain is

**Messaging** is the core broadcast authoring and sending domain. It implements the multi-step **message wizard** that guides a user from recipient selection through message composition to transmission confirmation. It also hosts the **broadcasting dashboard** (front page), **single-message shortcuts** (single SMS, single email), and the **limited wizard** for restricted-access scenarios.

---

## Send Methods (SmsSendMethod — 19 values, source-verified)

| Value | Description |
|---|---|
| ByAddress | Address-based recipient lookup + selection |
| ByMap | Geographic map drawing — draws polygon → residents |
| ByLevel | Level/hierarchy tree selection (ByLevel service) |
| ByExcel | Excel/file spreadsheet import |
| BySingleSms | Direct single SMS (not a broadcast) |
| BySingleSmsGroup | Single SMS to existing SMS group |
| ByTestSingleSms | Test SMS (does not count as real delivery) |
| ByTestSingleEmail | Test Email |
| ByWeb | Web message channel |
| ByResend | Resend from existing SmsGroup |
| ByStencil | Create from saved stencil |
| ByStdReceivers | Standard receivers only (recipient list pre-configured) |
| ByWeatherWarning | Weather warning trigger |
| ByWarning | General warning trigger |
| BySmsLogs | Compose from historical SMS log entries |
| ByMessage | Start from existing message copy |
| Systembesked | System message (Danish audience) |
| ByMunicipality | Municipality-based geographic selection |
| Undefined | Unset / default |

---

## Wizard Steps (WizardStep enum — source-verified)

```
1: AddressSelection
2: StdReceivers
3: WriteMessage
4: Confirm
5: Complete
6: SchedulingSetup  (scheduled wizard only)
```

---

## Wizard Variants

### Standard Wizard (`message-wizard`)
Flow: `AddressSelection → [StdReceivers] → WriteMessage → Confirm → Complete`

- StdReceivers step shown only when `canSelectStdReceivers = true` (profile has selectableStdReceivers)
- No scheduling step

### Scheduled Wizard (`message-wizard-scheduled`)
Flow: `AddressSelection → [StdReceivers] → WriteMessage → [SchedulingSetup] → Confirm → Complete`

- For **stencil creation**: SchedulingSetup step is **omitted** (`isCreatingStencil=true` blocks it)
- `canNavigateToConfirmPage` requires `writeMessagePageVisited && scheduledBroadcast != undefined`
- Drafts / stencil URLs → `hideCurrentMessageInDrafts = true`

### Limited Wizard (`message-wizard-limited`)
- Template-only (select from profile templates, fixed text, no sender choice)
- Optional delay checkbox
- Guard (`canActivateLimitedWizardGuardFn`): blocks if SmsGroup already active/sent

---

## Wizard Initialization Logic

1. Subscribe to `currentProfile$` (filter non-null, take 1)
2. Call `initWizardModelAndSmsGroupId(profileId, smsGroupId)`
3. If SmsGroup already `.active` (and not plannedToBeEdited): redirect to `/broadcasting`
4. Set step from `messageMetadata.wizardStep` if present; else derive from URL
5. Fire `wizardInitialized` event → unlocks child component rendering

**Draft/stencil flag:** URLs containing `wizardScheduled` or `wizardStencil` set `hideCurrentMessageInDrafts = true`

---

## Step Navigation Rules

**Next button gates:**
- `nextButtonActive()` signal must be `true` (set by active child component)
- On Confirm step: `writeMessagePageVisited() = true` required
- SchedulingSetup: `scheduledBroadcast != null` required

**Step skip rules:**
| Condition | Effect |
|---|---|
| `ByStdReceivers` + `hasStdReceiversExtended` | `hideWizardProgressBar=true`, `skipWriteMessageStep=true` |
| `BySmsLogs` | `hideAddressesStep=true`, `canSelectStdReceivers=false` |
| `ByStdReceivers` (non-extended) | `hideAddressesStep=true` |

**Draft save:** Available at `StdReceivers` step via toolbar Save Draft button

**Back navigation:** Controlled by `canNavigateBackwards()` signal. `AddressSelection` is the floor (no back).

---

## Broadcasting Dashboard (front page)

Components:
- `send-methods-list` — renders available send method tiles based on profile capabilities
- `scenarios` panel — shown when `showScenarios=true` (profile-controlled)
- `bi-tabs` (Sms / E-mail) — single message shortcuts; gated by `CanSendSingleSmsAndEmail` user role
  - `single-sms`: templates, sender name, autosignature, reply numbers, delay default
  - `single-email`: templates, autosignature, delay default
- `latest-msg-box` (sent messages) — links to status view
- `latest-msg-box` (planned messages) — delete planned message
- SmsGroup approver inbox — shown if `isCurrenUserSmsGroupApprover$`

---

## Approval Workflow

- `userRequiresApproval$` (from `SmsGroupApproverService`) controls the `broadcast-complete` page
- **Approval required:** "Notification sent to admin" message; only FrontPage button shown
- **No approval required:** Receipt email sent notification + links to Front Page, Status view, Create Reminder

---

## Excel/Import Send Path

- `bi-data-import` component with `DataImportPurpose.Broadcast`
- Sample template download button
- `broadcast-import-settings` child: format-specific import settings
- Validation result lifts `nextButtonActive` when valid

---

## Write Message Step

- `bi-write-message` component receives:
  - `existingMessageMetadata` — pre-filled metadata (edit mode)
  - `currentUser`, `currentCustomer`, `currentProfile`
  - `hasStandardReceivers` — affects message channel options
- Emits `onMessageMetadataReady` → updates shared wizard state

---

## Capabilities

1. Multi-step broadcast wizard with 6 possible steps
2. 19 distinct send methods (address, map, level, excel, std, web, stencil, etc.)
3. Step skipping/hiding per send method (no address step for StdReceivers; no WriteMessage for extended StdReceivers)
4. Scheduled broadcast wizard (separate flow with SchedulingSetup step)
5. Stencil creation mode (scheduled wizard, no SchedulingSetup step)
6. Draft saving at StdReceivers step
7. Approval workflow (approval-required branch on broadcast-complete page)
8. Single SMS / Single Email shortcuts on dashboard (role-gated)
9. Limited wizard (template-only, guard-protected)
10. Broadcast dashboard with sent + planned message history boxes
11. Scenarios panel (profile-controlled)
12. SmsGroup approver inbox on dashboard
13. Excel import path for broadcast recipients
14. Wizard state persistence (step saved to `messageMetadata.wizardStep`)
15. Receipt email notification on successful broadcast

---

## Flows

### FLOW_MSG_001: Standard address-based broadcast
1. User navigates to broadcasting → selects ByAddress send method
2. Wizard opens at AddressSelection step
3. Address search → expand tree → select addresses
4. (Optional) StdReceivers step if profile has them
5. WriteMessage step: compose text, select channels, set sender
6. Confirm step: review summary, click Send
7. Complete step: receipt shown; email sent; link to Status view

### FLOW_MSG_002: Scheduled broadcast (future date)
1. User navigates to scheduling → creates new scheduled broadcast
2. Scheduled wizard opens at AddressSelection
3. Steps same as FLOW_MSG_001 except WriteMessage → SchedulingSetup → Confirm
4. SchedulingSetup: set future date/time, recurrence (if applicable)
5. Confirm: save as planned message
6. Complete: planned message created

### FLOW_MSG_003: Stencil creation
1. User creates stencil via scheduled wizard with `isCreatingStencil=true`
2. Steps: AddressSelection → StdReceivers → WriteMessage → Confirm → Complete
3. No SchedulingSetup (skipped in stencil mode)
4. Message saved as stencil template (not active broadcast)

### FLOW_MSG_004: ByStdReceivers extended mode
1. Send method = ByStdReceivers + profile.hasStdReceiversExtended
2. hideWizardProgressBar=true, skipWriteMessageStep=true
3. User sees expanded std-receivers configuration directly
4. Save Draft available at StdReceivers step
5. Next → Confirm → Complete

---

## Rules

| ID | Rule |
|---|---|
| MSG_R001 | Wizard blocks navigation to already-sent (active) SmsGroup; redirects to /broadcasting |
| MSG_R002 | Confirm step requires `writeMessagePageVisited=true` |
| MSG_R003 | SchedulingSetup step requires `scheduledBroadcast != null` to advance to Confirm |
| MSG_R004 | BySmsLogs: canSelectStdReceivers=false; AddressSelection step hidden |
| MSG_R005 | ByStdReceivers: AddressSelection step hidden |
| MSG_R006 | ByStdReceivers + hasStdReceiversExtended: WriteMessage step skipped; progress bar hidden |
| MSG_R007 | Limited wizard guard: SmsGroup must not be active; SmsGroupId must be present in URL |
| MSG_R008 | Approval required → broadcast-complete shows approval-pending state (no status link, no receipt links) |
| MSG_R009 | Draft saves only available at StdReceivers step; not available at WriteMessage or later |
| MSG_R010 | Single SMS / Single Email shortcuts gated by `CanSendSingleSmsAndEmail` user role |

---

## Gaps

| ID | Gap |
|---|---|
| GAP_001 | `message-wizard-limited` format is unclear — unsure whether limited wizard is entirely separate send flow or wraps existing wizard steps |
| GAP_002 | ByMap flow not fully traced — map-tools and polygon-selection behavior not read |
| GAP_003 | ByLevel ("ByLevel" send method) selection component not examined |
| GAP_004 | Scheduled broadcast recurrence (repeat scheduling) — SchedulingSetup component not read; recurrence capability unknown |


---

## UI-lag: MessageService (core/services)

**Fil:** `core/services/message.service.ts`  
**Domain:** messaging / sms_group

Central service for besked-afsendelse og wizard-data. Ingen lokal caching.

| Metode | Beskrivelse |
|---|---|
| `getAllowedSendMethods()` | Tilladte send-metoder for aktuel profil (`SendMethodModel`) |
| `getMessageWizardModel(profileId)` | Wizard-model ved start (`MessageWizardModel`) |
| `getWizardWriteMessageModel(smsGroupId, sendMethod)` | Write-message trin data (merge fields, rolle-afhængig) |
| `getSmsGroup(smsGroupId)` | Hent SmsGroup DTO |
| `createSmsGroup(command)` | Opret nyt SmsGroup |
| `updateSmsGroup(...)` | Opdater SmsGroup |
| `sendBroadcast(smsGroupId)` | Afsend broadcast |
| `getRecipientsAndMetadata(smsGroupId)` | Modtagerantal + metadata |
| `getAddressChanges(smsGroupId)` | Adresseændringer siden sidst broadcast |
| `sendTestSms(model)` | Send test-SMS |
| `sendTestEmail(model)` | Send test-email |
| `sendTestVoice(dto)` | Send test-voice |
| `getSmsGroupsByMunicipalities(cmd)` | SmsGroups oprettet med kommunefiltre |
| `getShortMessage(smsGroupId)` | Hent kort-besked (SMS-tekst) til forhåndsvisning |
| `getEboksPreview(smsGroupId)` | eBoks dokumentforhåndsvisning |
| `getEmailPreview(smsGroupId)` | Email-forhåndsvisning |

---

## UI-lag: features/broadcasting

**Filer:** eatures/broadcasting/ (13 filer), eatures/broadcasting-limited/ (2 filer)
**Domain:** messaging / sms_group

### BroadcastingComponent (broadcasting.component.ts/.html)
**Primære sendeflade** — entry point for alle brugere med messaging-adgang.

| Funktion | Beskrivelse |
|---|---|
| Fanebjælke (send-methods-list) | <send-methods-list> — viser tilladte kanaler/metoder; klik ruter til wizard |
| Scenarios-panel | <scenarios> — vises kun hvis bruger har CanManageScenarios-rolle; list af stencil-baserede scenarier |
| Single-SMS tab | <single-sms> — direkte afsendelse af enkelt SMS med template-valg, sendernavn, reply-nummer, delay |
| Single-Email tab | <single-email> — direkte afsendelse af enkelt email med template-valg, autosignatur, delay |
| Sent messages boks | <latest-msg-box titleKey="broadcasting.SentMessages"> — de seneste afsendte beskeder |
| Planned messages boks | <latest-msg-box titleKey="broadcasting.PlannedMessages"> — planlagte/forsinkede beskeder med delete-mulighed |
| Unapproved messages boks | <unapproved-msg-box> — vises kun for godkendere (isCurrenUserSmsGroupApprover$); godkend/afvis faneindhold |
| Unfinished messages boks | <latest-msg-box> — ufærdige beskeder fra wizard |
| Survey nudge | CustomerSurveyNudgeDialogComponent — pop-up dialog på login til brugertilfredshedsundersøgelse (Office Forms) |

**Roller brugt:** ManageMessages, ManageReports, CanManageScenarios, CanSendSingleSmsAndEmail, SuperAdmin, LimitedUser

### ScenariosComponent (scenarios/scenarios.component.ts/.html)
**Scenarieliste** — viser tiljadte SMS Group Stencils som scenarier.

| Funktion | Beskrivelse |
|---|---|
| Liste visning | <bi-list-box> med sms-gruppe-stencils; bruger kan klikke for at starte wizard |
| Opret besked fra stencil | Kalder MessageService.createSmsGroup() baseret på stencil → ruter til wizard |
| Merge fields dialog | <bi-merge-field-dialog-content> — udfyld skabelonfelter før afsendelse |
| Broadcast-dialog | <create-broadcast-dialog> — bekræft og send direkte broadcast |
| Roller | CanManageScenarios — kan administrere; alle med stencils kan sende |

### SingleSmsComponent (single-sms-email/single-sms.component.ts/.html)
**Enkelt SMS formular** til direkte afsendelse.

| Felt | Beskrivelse |
|---|---|
| Telefonnummer | <bi-phone-input> med validators |
| Besked-tekst | Multi-line med GSM/Unicode-detektion, tegnoptælling (smsMaxLength/smsUnicodeMaxLength) |
| Afsendernavn | Input begrænset til smsSendAsMinLength–smsSendAsMaxLength tegn |
| Template valg | Dropdown med MessageTemplateModelExt[]; auto-udfylder tekst |
| Merge fields | Dialog via BiMergefieldDialogContentComponent |
| Reply-nummer | Dropdown ConversationPhoneNumberModel[] |
| Delay (dato/tid) | Optional forsinkelse |
| Forhåndsvisning | <bi-message-preview> |

### SingleEmailComponent (single-sms-email/single-email.component.ts/.html)
**Enkelt Email formular** til direkte afsendelse.

| Felt | Beskrivelse |
|---|---|
| Email-adresse | Input med Validators.email |
| Emne | Subject-felt |
| Besked | Rich textarea med autosignatur |
| Template valg | Dropdown med email-templates (TemplateEmailDto) |
| Merge fields | Dialog-integration |
| Delay | Optional forsinkelse |

### UnapprovedMsgBoxComponent (unapproved-msg-box/)
**Unapproved beskeder boks** til godkendere.

| Funktion | Beskrivelse |
|---|---|
| Liste | <bi-list-box> med SmsGroupApprovalRequestDto[] |
| Filtrering | Søg-input med debounce |
| Udvid/sammenfold | Paginering med limitForMessageList = 3 |
| Godkend | Output event onApproveRequest → parent kalder API |
| Afvis | Output event onRejectRequest → parent kalder API |
| Activity log | Dialog ActivityLogDialogContentComponent |

### CustomerSurveyNudgeDialogComponent (customer-survey-nudge-dialog/)
Survey nudge-dialog: viser Office Forms-link afhængigt af brugerens sprog (DK/NO/etc). Gemmer svar via UserNudgingService.

### BroadcastingLimitedComponent (broadcasting-limited/)
**Stencil-bruger interface** for LimitedUser-rolle — viser kun stencils og planlagte beskeder.

| Funktion | Beskrivelse |
|---|---|
| Stencil-liste | <bi-list-box> med SmsGroupSimpleDto[]; klik → confirm → wizard |
| Planlagte beskeder | <latest-msg-box> med delete |


---

## UI-lag: features/broadcasting

**Filer:** `features/broadcasting/` (13 filer), `features/broadcasting-limited/` (2 filer)
**Domain:** messaging / sms_group

### BroadcastingComponent
Primære sendeflade. Tabs: Single SMS / Single Email (krav: CanSendSingleSmsAndEmail). Viser Scenarios-panel (krav: CanManageScenarios eller stencils). Bokse: SentMessages, PlannedMessages (med delete), UnapprovedMessages (godkendere), UnfinishedMessages. Survey nudge-dialog ved login.

### ScenariosComponent
Viser SMS Group Stencils som klikbare scenarier. Klik starter wizard eller afsender direkte via CreateBroadcastDialogComponent. Understøtter merge fields dialog.

### SingleSmsComponent
Enkelt SMS-formular: telefonnummer (bi-phone-input), tekst med GSM/Unicode-detektion og tegnoptælling, afsendernavn (min/max validators), template-valg, merge fields, reply-nummer, forsinkelse (dato/tid), forhåndsvisning.

### SingleEmailComponent
Enkelt email-formular: email-adresse, emne, besked med autosignatur, template-valg, merge fields, forsinkelse.

### UnapprovedMsgBoxComponent
Godkender-boks: liste af SmsGroupApprovalRequestDto, søgefilter med debounce, paginering (3 pr. side), Godkend/Afvis output events, activity log-dialog.

### CustomerSurveyNudgeDialogComponent
Survey nudge-dialog ved login. Office Forms-link afhænger af bruger-sprog. Gemmer svar via UserNudgingService.

### BroadcastingLimitedComponent
LimitedUser-interface: stencil-liste + planlagte beskeder. Ingen wizard-adgang direkte.
---

## UI-lag: features/message-wizard-limited

### MessageWizardLimitedComponent (features/message-wizard-limited/)
Simplificeret wizard for LimitedUser uden fuld wizard-adgang. Bruger vælger template, udfylder evt. merge fields, angiver delay-dato/tid og sender broadcast. Afsendelse sker via MessageService. Dialog MessageSentDialogComponent bekræfter afsendelse. Guard message-wizard-limited.guard.ts sikrer kun LimitedUser kan tilgå ruten.
---

## UI-lag: features/message-wizard (FULL WIZARD)

**Filer:** `features/message-wizard/` (173 filer)
**Domain:** messaging (primært) / address_management / sms_group / standard_receivers / recipient_management

### Wizard Flow (WizardStep enum)
Trinbaseret flow: **AddressSelection → StdReceivers → WriteMessage → Confirm → Complete**. Eller for scheduled: ekstra trin SchedulingSetup.

### Base Component Classes
- **MessageWizardBaseComponent** — abstrakt base for alle wizard-varianter. Styrer: currentStep$ (BehaviorSubject), pageLoading, canSelectStdReceivers, hideAddressesStep, skipWriteMessageStep. Init: WizardSharedService.initWizardModelAndSmsGroupId().
- **WriteMessageBaseComponent** — base for write-message trin.
- **ConfirmBaseComponent** — base for confirm-trin.
- **StdReceiversBaseComponent** — base for std-receivers trin.
- **WriteMessageWizardStepBaseComponent** — base for wizard-steps med message-skriving.

### MessageWizardComponent (root)
Konkret wizard. Implementerer getNextStep/getPreviousStep — routing mellem trin afhænger af bruger-rettigheder. Provider: ByAddressService.

### Shared Services
- **WizardSharedService** — central state og HTTP-kald for wizard. initWizardModelAndSmsGroupId() henter MessageWizardModel (sender-konfig, tilladte metoder, modtager-info). Holder hele MessageModel (SmsGroup) under editing.
- **WizardSharedEventsService** — RxJS Subjects for events på tværs af wizard-trin: stepChanged, startWizardLoading, stopWizardLoading, draftSaved.

### Adresse-valg trin (childComponents/)
Wizard trin 1: AddressSelection. Brugeren vælger "send-metode" (by-address, by-level, by-map, by-municipality, by-excel, std-receivers):

**ByAddressComponent** (childComponents/by-address)
- Adresse-søgning via <bi-address-search-input> (postnummer/gadenavne)
- Resultat: BiTreeNode-hierarki (zip → gade → husnumre) i "searched" og "selected" visninger
- ByAddressService — lokal event-bus (Subjects) for søgede/valgte adresser
- BiAddressTreeNodeManager — håndterer tree-node opbygning og selektion
- Understøtter interval-søgning (fra-til husnumre, lige/ulige)

**ByLevelComponent** (childComponents/by-level)
- Hierarkisk niveau-filter: kolonner af LevelValueItem-lister (niveau 1 → 2 → 3)
- ByLevelService + ByLevelSharedService — HTTP og lokal state
- ByLevelSelectionAndSearchComponent — interaktivt søge/vælg per niveau-kolonne
- LevelItemsFilterPipe — lokal filtrering af niveau-items

**ByExcelComponent** (childComponents/by-excel)
- Excel/CSV import via <bi-data-import> (DataImportPurpose.Broadcast)
- BroadcastImportSettingsComponent — send-format og telefonnummer-kolonne indstillinger
- BroadcastDataImportResult — resultat-model

**ByMapComponent** (childComponents/by-map) — 13 filer
- Kortbaseret modtager-valg (Leaflet/OpenLayers polygon-tegning)
- Brugeren tegner polygon på kort → backend finder adresser inden for

**ByMunicipalityComponent** (childComponents/by-municipality) — 15 filer
- Kommune/amt-baseret valg
- Multi-level hierarki (land → region → kommune)

**ConfirmComponent** (childComponents/confirm) — 6 filer
- Opsummering af alle modtagere og besked-indhold inden afsendelse
- Viser statistik: antal modtagere pr. kanal
- "Send nu" / "Gem kladde" / "Planlæg"

**BroadcastCompleteComponent** (childComponents/broadcast-complete)
- Bekræftelses-side efter afsendelse. Viser besked-navn og delay-dato hvis planlagt.
- "Tilbage til broadcasting"-knap.

**StdReceiversComponent** (childComponents/std-receivers) — 3 filer
**StdReceiversExtendedComponent** (childComponents/std-receivers-extended) — 6 filer
- Trin 2: valg af standard-modtagere (grupper, filtre)
- Extended: udvidet med ekstra filtre

**WriteMessageComponent** (childComponents/write-message) — 2 filer
- Thin wrapper → delegerer til shared/write-message komponenter

### Scheduled Wizard (message-wizard-scheduled) — 21 filer
- Alternativ wizard for planlagte og gentagne udsendelser
- SchedulingSetup-trin med dato/tid valg og gentagelses-konfiguration

### Nudging Dialogs
- **EboksNudgingComponent** (eboks-nudging) — opfordrer bruger til at aktivere eBoks-kanal
- **OwnersNudgingComponent** (owners-nudging) — opfordrer til at sende til ejere
- **VoiceNudgingComponent** (voice-nudging) — opfordrer til at aktivere voice-kanal