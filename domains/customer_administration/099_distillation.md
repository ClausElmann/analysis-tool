# Domain Distillation: customer_administration

**STATUS:** APPROVED_BASELINE  
**Completeness source:** 0.88 (Layer 1 — behaviors EMPTY, entities only) + UI primary evidence  
**UI verified from:** `customer-settings.component.ts`, `customer-create-edit.component.html`  
**Date:** 2026-04-11  
**NOTE:** Layer 1 behaviors and rules are empty/garbage for this domain. Distillation derived primarily from UI source.  

---

## PURPOSE

Customer administration is the self-service settings area that a customer admin uses to view and edit their own organisation's configuration. It is the customer-scoped view of the customer record: identity fields, sender name, broadcast behaviour settings, and (for customers with voice capability) voice call settings. The customer admin cannot change which country they belong to or manage other customers — they can only change the settings that apply to their own organisation.

---

## CORE CONCEPTS

1. **Customer** — the top-level organisation in the system. All profiles, users, and configuration are nested under a customer. Each customer belongs to one country.

2. **Account Data** — basic identity: name, company registration ID (CVR/org number), address. SuperAdmin can also set an Economic ID (billing integration) and a OneFlow document ID (Norwegian e-signature).

3. **Broadcast Settings** — configuration that applies to all outgoing messages from this customer's profiles: default SMS sender name, auto-signature appended to all messages, a configurable window (in days) before draft SMS messages are deleted, and settings controlling how far in advance web messages are published and when they expire.

4. **Voice Settings** — if the customer has voice-enabled profiles: SMS/voice sender number, a forwarding number, and delivery time window (the hours during which voice calls are allowed to be attempted).

5. **Sender name lock** — the SMS sender name can be "locked" so that regular customer admins cannot change it. In the locked state the field shows an informational message and cannot be edited. Only superAdmin can unlock it.

---

## CAPABILITIES

1. View and edit the customer's name (max 200 characters).
2. View and edit the company registration ID.
3. View the display address (readonly for non-superAdmin).
4. Edit the SMS broadcast sender name — subject to min/max character validation; may be locked.
5. Add an auto-signature that is appended to all outgoing SMS messages.
6. Set the number of days before draft SMS messages are automatically deleted (1–9 days).
7. Set how many days before the selected start date web messages should be published.
8. Set how many days after the end date web messages should expire.
9. (If voice-enabled) Select or enter the voice sender number and forwarding number.
10. (If voice-enabled) Set the delivery time window for voice calls (start and end time).
11. (SuperAdmin only) Set the Economic ID for billing integration.
12. (SuperAdmin only) Set the OneFlow document ID for Norwegian customers.
13. (SuperAdmin only) Look up and update the customer's physical address.
14. (SuperAdmin only) Assign a sender admin to manage the sender name.

---

## FLOWS

### 1. Customer Admin Edits Settings
Customer admin navigates to Settings → form loads current customer values → edits one or more fields → saves → customer record updated → changes take effect for all future broadcasts from this customer's profiles.

### 2. SuperAdmin Updates Address
SuperAdmin opens customer settings → clicks Edit on the address field → address search form appears → selects correct address → display address field updated → saved with the rest of the form.

---

## RULES

1. Country cannot be changed after the customer is created — the country selector only appears on the create form, not on edit.
2. SMS sender name has a minimum and maximum character length (enforced at UI and server). The field may be locked — a locked sender name cannot be changed by the customer admin.
3. Days before SMS drafts are deleted must be between 1 and 9.
4. Web message publish-before-days must be between 0 and 100.
5. Voice settings are only shown if the customer has at least one profile with voice capability enabled.
6. If a voice sender number and forwarding number are set to the same value, the form produces a validation error.

---

## GAPS

1. **Layer 1 is largely empty** — behaviors and rules arrays contain no substantive content. This domain requires deeper Layer 0 source reading for a complete picture.
2. **Missing: FTP settings, API keys, contact persons, GDPR, user management** — these are visible in the superAdmin customer detail tabs but are separate concerns not fully captured here. See `customer_management` distillation for superAdmin-level view.


---

## UI-lag: ContactPersonsService (core/services)

**Fil:** `core/services/contact-persons.service.ts`  
**Domain:** customer_administration

Cache: `BehaviorSubject` med last `customerId` — refresher kun ved kunde-skift.

| Metode | Beskrivelse |
|---|---|
| `getAllContactPersonsByCustomerId(customerId, refresh?)` | Alle kontaktpersoner for kunde (cached) |
| `getContactPersonTypes()` | Typer af kontaktpersoner (cached) |
| `addContactPerson(dto)` | Tilføj kontaktperson |
| `deleteContactPerson(id)` | Slet kontaktperson |
| `updateContactPerson(dto)` | Opdater kontaktperson |


---

## UI-lag: features/administration/customer-admin (77 filer)

**Domæne:** customer_management + customer_administration + profile_management + identity_access  
**Modul:** `customer-admin.module.ts`

### CustomerAdminComponent (Containerside)
Header med kundenavn + BiTabs: Brugere / Profiler / Indstillinger.  
Delt service: `CustomerAdminSharedService` (deler kundereferencer med undertabs).

---

### customer-users/ (Brugerstyring)

| Komponent | Rolle |
|---|---|
| `CustomerUsersComponent` | Liste over alle brugere for aktuel kunde. Profilfilter-dropdown. Tabel med navn/email/tlf/sidst logget ind/roller. Navigate til opret/rediger |
| `CreateUserComponent` | Formular til opret ny bruger (email, navn, telefon, roller, profiltilgang). Validering via reaktiv form |
| `EditUserComponent` | Rediger eksisterende bruger. Container-komponent med tabs: Brugerinfo / Profiler / Roller |
| `UserProfilesComponent` | Tab: Liste over brugerens profiltilgange. Tildel/fjern profila |
| `UserRolesComponent` | Tab: Liste over brugerens systemroller (global). Tildel/fjern roller |
| `UserAdminSharedService` | Delt state i edit-flow (current bruger til redigering) |

---

### customer-profiles/ (Profiladministration)

| Komponent | Rolle |
|---|---|
| `CustomerProfilesComponent` | Liste over alle kundens profiler med opret-knap |
| `CreateProfileComponent` | Opret ny profil (navn, type/supplyType, land). `CreateProfileFormValue` model |
| `EditProfileComponent` | Container for profil-redigering med tabs (afhænger af roller/features). `ProfileEditAdminSharedService` deler profil-state |

**EditProfile tabs (tab-children/):**

| Tab-komponent | Indhold |
|---|---|
| `ProfileInfoComponent` | Basinfo: navn, type, land, senderadresse. `ProfileInfoTabFormValue` |
| `ProfileRolesComponent` | Tildel/fjern profilroller (RoleGroups/Packages) |
| `ProfileUsersComponent` | Brugere med adgang til profilen |
| `ProfileAccountComponent` | Fakturakonto (ProfileAccount) til fakturering |
| `ProfileApiKeysComponent` | API-nøgler til profilens API-adgang |
| `ProfileEmailToSmsComponent` | Email-til-SMS opsætning (`email2sms.service.ts` lokalt) |
| `FtpSetupProfileComponent` + `FtpSettingsFormComponent` | FTP-indstillinger for profilen (hostname, port, user, path) |
| `ProfileDistributionNumberAdminComponent` | Distributionsnumre (telefonnumre til reply distribution). `AssignDistributionNumberComponent` + `EditNameAndGroupComponent` |
| `ProfileMapSettingsComponent` | Kortindstillinger (zoom, center, mapLayer) |
| `ProfileSocialMediaComponent` | Social media konti tilknyttet profilen |
| `ProfileReadyReportsComponent` | READY integration rapporter. Sub-rapporter: Messages, Meters, Readings, Warnings, RawData. `KamstrupService` lokal |

---

### customer-settings/
**CustomerSettingsComponent** — Rediger kundeoplysninger via `CustomerCreateEditComponent` (shared).  
Viser: navn, land, voicenumre, brugerroller. Kun super-admin kan redigere alt.

### customer-gdpr-admin/
**CustomerGdprAdminComponent** — GDPR-accept flow for kunden. Extends `GdprAcceptParentBase` (shared).  
Viser GDPR acceptstatus og knap til accept.

### customer-social-media/
**CustomerSocialMediaComponent** — Liste og opret/slet Facebook + Twitter/X konti.
- Facebook: `FB.login()` → OAuth flow → `getSocialMediaAccounts()`
- Twitter/X: OAuth URL → popup → callback via `ConfirmTwitterComponent`
- `ConfirmTwitterComponent`: Håndterer Twitter OAuth callback-parametre (`ITwitterCallbackParams`)
