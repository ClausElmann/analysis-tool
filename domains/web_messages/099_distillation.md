# Domain Distillation — web_messages

**Status:** APPROVED_BASELINE  
**Completeness score (Layer 1):** 0.97  
**Evidence:** Layer 1 stable + UI source: web-messages, web-message-part-admin, web-message-part wizard, iFrame driftstatus (standard + map), driftstatus setup (customer + profile), CommonService, WebTypeIdToTypeNamePipe

---

## 1. Core Concept

`web_messages` handles web-published messages and internal messages that accompany SMS broadcasts. A web message is a complementary channel alongside SMS — the message is published on a web portal or internal portal, optionally for Facebook/Twitter, with its own title, text, validity period, and scheduling.

---

## 2. WebMessageType Enum

| Value | Description |
|---|---|
| `Sms2Webs` | Message published to public web portal |
| `Sms2Internals` | Message published to internal portal |
| `Facebook` | Post to Facebook |
| `Twitter` | Post to Twitter/X |

---

## 3. Web Message Entity Fields

| Field | Notes |
|---|---|
| `title` | Header text (max 100 chars) — only for Sms2Webs and Sms2Internals types |
| `text` | Message body (max 10,000 chars) |
| `dateDelayUtc` | ValidFrom — scheduled publish time |
| `dateExpireUtc` | ValidTo — expiry time |
| `typeId` | `WebMessageType` enum value |
| `critical` | Boolean flag — critical message indicator |
| `profileName` | Profile the message belongs to |
| `status` | Current publication status |
| `sendAsap` | If true: publish immediately, no dateFrom required |

---

## 4. Admin UI — `web-messages.component`

**Context:** administration → web-messages

**SuperAdmin features:**
- Country + Customer selector (`bi-country-customer-profile-selection`, customer required)
- Date range query (showMessagesFromDate / showMessagesToDate) — validated for ordering

**Table columns:** Title, Message, ValidFrom (`dateDelayUtc`), ValidTo (`dateExpireUtc`), MessageType (`typeId`), Critical, Profile, Status + [Edit] [Delete] action buttons

**Behaviors:**
- Date range required to load messages
- Create button → `web-message-part-admin` form
- Date validation: fromDate must be before toDate (cross-field validators)

---

## 5. Admin Form — `web-message-part-admin.component`

Used within `bi-accordion` for create/edit of individual web messages. The form is embedded per-message in the list.

**Form fields:**
- `title` — shown only for `Sms2Webs` and `Sms2Internals` types
- `text` — textarea, 10,000 char limit; merge fields hidden in admin context
- `sendAsap` checkbox — shown for Sms2Webs, Sms2Internals, Facebook, Twitter
- `dateFrom` + `timeFrom` — publish start (hidden if sendAsap=true); time required for all types except Facebook/Twitter
- `dateTo` + `timeTo` — publish end

**CopyFromWeb button:** Shown if `canCopyTextFromWeb()` — copies text from the web channel version

---

## 6. Wizard Integration — `web-message-part.component`

Message wizard step for composing a web or internal message alongside the SMS.

**Inputs:**
- `forInternalMessage()` — switches between web title id (`web-title`) and internal title id (`internal-title`)
- `forStdReceivers()` — if true: merge fields hidden in textarea
- `showCopyFromSmsPartButton()` / `showCopyFromEmailPartButton()` — show copy-source buttons

**Form fields:**
- `title` — `sms2WebTitleMaxLength` chars
- `message` — `sms2WebMaxLength` chars; merge fields supported (unless `forStdReceivers`)

**Copy behavior:**
- "Copy from SMS" button: emits `onCopyFromSmsMessagePart` event
- "Copy from Email" button: emits `onCopyFromEmailMessagePart` event
- Merge field validation: `messageCtrl.errors.mergeField` shown if invalid merge field included

---

## 7. Rules

1. Title field only rendered for `Sms2Webs` and `Sms2Internals` message types — not for Facebook/Twitter
2. `sendAsap` checkbox only shown for Sms2Webs, Sms2Internals, Facebook, Twitter (not for eBoks/other types)
3. Time field (`timeFrom`) is required for all types except Facebook and Twitter
4. In admin form: merge fields are always hidden (no manual merge field insertion in admin manage context)
5. In wizard form: merge fields hidden if `forStdReceivers()` (standard receivers context)
6. Facebook/Twitter use `useClearText` option in textarea — resets to empty on clear
7. Date range query required in admin list before messages load (no default "show all")


---

## UI-lag: WebMessageService (core/services)

**Fil:** `core/services/webmessage.service.ts`  
**Extends:** `BiWebMessageBaseService`  
**Domain:** web_messages

| Metode | Beskrivelse |
|---|---|
| `createWebMessages(messages[])` | Opret webbesked(er) — returnerer `WebMessageCreateResultModel` |
| `getWebMessage(id)` | Hent enkelt webbesked |
| `updateWebMessage(model)` | Opdater webbesked |
| `setWebMessageClosedStatus(id, toEnd)` | Åbn/luk en webbesked |
| `deleteWebMessage(id)` | Slet webbesked |

## UI-lag: SocialMediaService (core/services)

**Fil:** `core/services/social-media.service.ts`  
**Domain:** web_messages (sociale medier er kanal i web-beskeder)

Cache: `cachedSocialMediaTokenStatus` (BehaviorSubject) pr. profil+kunde.

| Metode | Beskrivelse |
|---|---|
| `getSocialMediaAccounts(profileId?)` | Alle social media konti — evt. filtreret pr. profil |
| `removeSocialMediaAccount(id)` | Fjern social media konto |
| `addSocialMediaAccount(account)` | Tilføj social media konto |
| `getSocialMediaTokenStatus(profileId, customerId)` | Check om token er gyldigt (cached) |
| `getTwitterAuthUrl()` | Hent Twitter OAuth URL |
| `confirmTwitterCallback(params)` | Bekræft Twitter OAuth callback |

---

## 8. iFrame Driftstatus — Oversigt

`web_messages` rummer et dedikeret **iFrame Driftstatus-undersystem** til at eksponere operationelle beskeder via embeddable iFrames på kundernes egne websites. Findes i to udgaver:

| Variant | Route-base | Beskrivelse |
|---|---|---|
| Standard | `SharedRouteNames.iFrameRoutes.driftstatus` | Liste-visning af aktive driftsbeskeder |
| Kort | `SharedRouteNames.iFrameRoutes.driftstatusMap` | Kortbaseret visning med geografiske markeringer |

Begge varianter har to views pr. variant:

| View | Komponent | Formål |
|---|---|---|
| Admin | `IframeDriftstatusAdminComponent` / `IframeDriftstatusMapAdminComponent` | Viser genereret iFrame HTML-kode og live preview for kunde/profil |
| Setup | `IframeDriftstatusSetupComponent` / `IframeDriftstatusMapSetupComponent` | Konfigurerer Driftsmodul-indstillinger pr. kunde og profil |

---

## 9. iFrame Driftstatus — Admin-view (`iframe-driftstatus-admin.base.ts`)

**Base-klasse:** `IFrameDriftstatusAdminBase`

**Funktioner:**
- SuperAdmin kan skifte kunde via `bi-country-customer-profile-selection`
- Genererer iFrame URL (DomSanitizer SafeResourceUrl) til live preview
- Genererer fuld iFrame HTML-kode til kunde (standard `<iframe>` tag)
- Pr.-profil HTML-kode: `profileIdsToIFrameHtml[profile.id]` (accordion per profil)
- Styling/layout-parametre: `featureParams`, `stylingParams`, `layoutParams` — vises via `bi-iframe-url-param-descriptions`
- Dynamisk/fast højde (radio-knapper): `showDynamicHeight` toggle

**Standard-variant ekstra:**
- Lytter på `window.addEventListener("message")` for `HeightChanged`-events → dynamisk iFrame-højde
- Ekstern iFrame script: `${origin}/StaticFiles/iFrameScript.js`

**Kort-variant HTML-output:**
```
<iframe src="{base}?customerId={publicId}" frameborder="0" width="100%" height="900px"></iframe>
// pr. profil:
<iframe src="{base}?customerId={publicId}&profileIds={ids}" frameborder="0" width="100%" height="900px"></iframe>
```

---

## 10. iFrame Driftstatus Standard — Customer-indstillinger

**DTO:** `CustomerDriftsStatusModuleSettingsDto`  
**Komponent:** `IframeDriftstatusSetupComponent`

| Felt (CustomerFormValue) | Beskrivelse |
|---|---|
| `defaultTextNoMessages` | Tekst der vises når ingen aktive driftsbeskeder |
| `groupMessagesByProfile` | Boolean: gruppér beskeder pr. profil |
| `titleForWebModule` | Titel vist i web-modulet |
| `webModulePageTitle` | Browser-sidetitel for iFrame-siden |
| `canSeeFromArchive` | Tillad visning af arkiverede beskeder |
| `numOfDaysBackArchive` | Antal dage tilbage i arkiv |

**Profil-configuration (`WebMessageModuleProfile` / `WebMessageModuleProfileExt`):**
- `isSelected` (ext.) — om profilen er valgt til modulet
- Profil-rækkefølge kan ændres via drag-and-drop (`TableRowReorderEvent`)
- Delvist udvalgte profiler: `isPartiallySelected`, `isChecked` (computed signals)
- Sub-profiler understøttes: `hasSubProfiles`

**Profile-settings dialog (`ProfileIframeDriftstatusSettings`):**

| Felt | Beskrivelse |
|---|---|
| `profiles` | Tilgængelige profiler at vælge |
| `title` | Titel for profilen i Driftstatus-modulet |
| `profilesForPublish` | Liste af profil-IDs hvis beskeder publiceres under samme profil |

---

## 11. iFrame Driftstatus Kort — Customer-indstillinger

**DTO:** `WebMessageMapModuleCustomerSettingsModel`  
**Setup-komponent:** `IframeDriftstatusMapSetupComponent`  
**Profil-model:** `WebMessageMapModuleProfileModel`

| Felt (CustomerFormValue) | Beskrivelse |
|---|---|
| `mapLayerId` | Kortlag-ID |
| `zoomLevel` | Standard zoom-niveau |
| `centerCoords` | Centreringskoordinater (LatLng) |
| `hasSearchInput` | Vis søgefelt i kort-modulet |
| `showLegend` | Vis legende |
| `showPolygons` | Vis polygoner |
| `useAreaCircles` | Brug areal-cirkler i stedet for polygoner |
| `addressAndInfoDisplayType` | `HOVER` (1) eller `CLICK` (2) — hvornår adresse/besked vises |
| `showArchiveDays` | Antal dage arkiv vist |

**Kortlag:**  `BiLayer = { mapLayerId, layerName }` — tilgængelige kortlag

**Icons:** `CommonService.getWebMessageMapModuleIcons(customerId?)` returnerer `IconModel[]` — ikoner til kortmarkører

---

## 12. WebTypeIdToTypeNamePipe

**Pipe:** `webTypeName` — konverterer numerisk typeId til visningsnavn

| typeId | Output |
|---|---|
| 1 | `shared.Web` |
| 2 | `sms2InternalDisplayName` (custom) eller `shared.InternalMessage` |
| 3 | `"Facebook"` (hardcoded) |
| 4 | `shared.XTitle` (X/Twitter) |
| default | `shared.Web` |

---

## 13. Rules (opdateret)

1. Title field kun for `Sms2Webs` og `Sms2Internals` — ikke Facebook/Twitter
2. `sendAsap` kun for Sms2Webs, Sms2Internals, Facebook, Twitter
3. `timeFrom` påkrævet for alle typer undtagen Facebook og Twitter
4. I admin-form: merge fields altid skjult
5. I wizard-form: merge fields skjult hvis `forStdReceivers()`
6. Facebook/Twitter bruger `useClearText`
7. Dato-range krævet i admin-liste før beskeder loades
8. iFrame Driftstatus standard: dynamisk/fast højde valgbar — dynamisk kræver `iFrameScript.js` på kundens side
9. iFrame Driftstatus kort: adresse+besked-visning styres af `addressAndInfoDisplayType` (HOVER=1 / CLICK=2)
10. Profil-rækkefølge i standard Driftstatus-modul kan sorteres via drag-and-drop
11. `ProfilesForPublish` i profil-indstillinger: bestemmer hvilke profilers beskeder vises samlet under ét profil-view
