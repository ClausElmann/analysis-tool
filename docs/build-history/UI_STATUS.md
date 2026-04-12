# Green AI — UI Status

> **Dato:** 2026-04-05  
> **Fase:** UI Lock Phase — alle UI-sider implementeret med mock backend  
> **Formål:** Aktuelt overblik — arkitektspørgsmål der kræver beslutning

---

## 1. Sider — Status

### Implementeret med real backend

| Side | Route | Backend-features | Status |
|------|-------|-----------------|--------|
| Login | `/login` | Auth/JWT + multi-customer/profile resolution | ✅ Fungerer |
| SelectCustomerPage | `/select-customer` | SelectCustomer (pre-auth JWT) | ✅ Real backend |
| SelectProfilePage | `/select-profile` | SelectProfile (pre-auth JWT) | ✅ Real backend |
| Customer Admin | `/customer-admin` | GetCustomerSettings, GetUsers, GetProfiles | ✅ Real backend |
| Admin: User List | `/admin/users` | CreateUser, AssignRole, AssignProfile | ✅ Real backend |
| Admin: Settings | `/admin/settings` | ListSettings, SaveSetting | ✅ Real backend |
| User Profile | `/user/profile` | ChangeUserEmail, UserSelfService + JWT claims | ✅ Real backend |

### Implementeret med mock-backend (UI-klar, venter på features)

| Side | Route | Hvad er mock | E2E-dækning |
|------|-------|-------------|-------------|

| BroadcastingHubPage | `/broadcasting` | Alt — sendemetoder, scenarier, hurtig-send, godkendelse | ✅ LabelCoverage + Visual |
| SendWizardPage | `/send/wizard?method=X` | Recipient-søgning, Excel-upload, modtagertæl, afsendelse | ✅ LabelCoverage |
| StatusPage | `/status` | Broadcast-historik, tabs: Sendt/Planlagt/Fejlet | ✅ LabelCoverage |
| StatusDetailPage | `/status/{id}` | Leveringsstatus, pr.-modtager rapport, gensend, slet | ✅ LabelCoverage |
| DraftsPage | `/drafts` | Kladdeliste + slet | ✅ LabelCoverage |
| SuperAdminPage | `/admin/super` | Lande, kunder, profiler, brugerliste (alt mock) | ✅ LabelCoverage |

### Deprecated / redirect

| Side | Route | Status |
|------|-------|--------|
| Dashboard | `/dashboard` | ✅ Redirect → `/broadcasting` |
| Home | `/` | ✅ Redirect: autentificeret → `/broadcasting`, uautentificeret → `/login` |

---

## 2. Navigation — Besluttet og implementeret

| Beslutning | Resultat |
|------------|---------|
| Primær entry-point | `/broadcasting` (var `/dashboard`) |
| `/dashboard` | Deprecated redirect → `/broadcasting` |
| OverlayNav struktur | Broadcasting / Status / Kladder / Profil / Kundestyre / Admin |
| Command Palette | Ctrl+K, søger NavCatalog, keyboard-navigerbar |
| SelectCustomer/Profile | EmptyLayout, ingen chrome |

---

## 3. Testoverblik

| Testsuite | Antal tests | Status |
|-----------|-------------|--------|
| Unit + integration (GreenAi.Tests) | 338 | ✅ Alle grønne (2 nye pre-auth assertions) |
| E2E + Visual (GreenAi.E2E) | 43+1 | ✅ 43/43 grønne — inkl. 5 login-flow tests + 1 visual export |
| Label coverage | 12 | ✅ Inkl. SelectCustomer/Profile/StatusTabs (ny) |
| Visual (4 devices) | 12 | ✅ Inkl. Dashboard→Broadcasting visual test (ny) |

**Seneste kørsel:** 2026-04-05 — Unit: seneste build + E2E: 43/43 + Visual: 1/1 — ingen fejl

---

## 4. Arkitektspørgsmål (afventende svar)

### Q1 — Hvad er det rigtige login-flow?

```
Login → JWT token → ???
```

Mulighederne:
- A) `/select-customer` → `/select-profile` → `/broadcasting` (altid)
- B) Spring over hvis kun én kunde/profil → direkte til `/broadcasting`
- C) Customer+profil er bagt ind i token fra start (nuværende JWT-adfærd?)

**Impact:** `ICurrentUser.CustomerId` og `ICurrentUser.ProfileId` bruges overalt.  
Nuværende: token indeholder customer + profil fra login → direkte til `/broadcasting`.  
Select-sider er bygget men aldrig trigget af JWT-flowet endnu.

---

### Q2 — Hvad er relationen mellem Scenarier og Send-wizard?

`BroadcastingHubPage` har scenario-panel (`MockData.Scenarios`).  
`SendWizardPage` har ingen scenarie-integration.

**Uklart:**
- Er et scenarie en genvej der udfylder wizard-steps (metode, modtagere, besked)?
- Er scenarier en separat entitet med egne CRUD-endpoints?
- Hvem kan oprette scenarier? Alle profiler, eller kun admin?

---

### Q3 — Godkendelsesflow — hvem godkender?

`BroadcastingHubPage` viser "Afventer godkendelse"-panel med Godkend/Afvis knapper.

**Uklart:**
- Hvad er `Unapproved`-statussen? Er det separat status i broadcast-tabellen?
- Hvem har rollen til at godkende? Er det en ny rolle (`ApproveBroadcast`)?
- Hvad sker der ved afvisning — slettes broadcast, eller sættes til `Rejected`?
- Skal godkender modtage en notifikation?

---

### Q4 — Adresse-søgning — hvilken API?

`SendWizardPage` (by-address) søger adresser.

- Hvilket API? (DAR, DAWA, intern geo-service?)
- Returnerer det ejerdata direkte, eller to-trins kald?
- Radius/zone-parameter?

---

### Q5 — Excel-upload — format og validering

`SendWizardPage` (by-excel) viser file-upload.

- Kolonneformat? (Telefon, navn, adresse?)
- Server-side eller kun client-side validering?
- Øvre grænse på antal rækker?
- Gemmes filen eller kun in-memory?

---

### Q6 — Standard-modtagere (`StdReceivers`) — hvem administrerer dem?

`MockData.StdReceivers` viser 6 grupper.

- Statiske (konfiguration) eller dynamiske (DB-tabeller)?
- Hvem opretter/redigerer? SuperAdmin? Kunde-admin?
- Per-kunde, per-profil, eller globale?

---

### Q7 — Kort-integration (by-map)

`SendWizardPage` (by-map) viser placeholder.

- Kortleverandør? (Leaflet, Google Maps, Azure Maps, DAWA?)
- Polygon-udtræk til modtagerliste?
- I scope for nuværende fase?

---

## 5. Manglende features i `Features/` for at erstatte mock

| Side / Funktion | Manglende feature |
|-----------------|------------------|
| BroadcastingHubPage | `GetBroadcasts`, `GetScheduled`, `GetUnapproved` |
| BroadcastingHubPage | `ApproveBroadcast`, `RejectBroadcast` |
| BroadcastingHubPage | `QuickSendSms`, `QuickSendEmail` |
| BroadcastingHubPage | `GetScenarios`, `CreateScenario` |
| SendWizardPage | `SearchAddresses`, `LookupOwners` |
| SendWizardPage | `UploadRecipientFile` (Excel parsing) |
| SendWizardPage | `CreateBroadcast` / `ScheduleBroadcast` |
| StatusPage + StatusDetailPage | `GetBroadcastHistory` (filtreret) |
| StatusDetailPage | `GetStatusReport` (pr.-modtager) |
| StatusDetailPage | `ResendBroadcast`, `DeleteBroadcast` |
| DraftsPage + Wizard | `SaveDraft`, `GetDrafts`, `DeleteDraft` |
| DraftsPage + Wizard | Auto-save trigger on step_change / route_away |
| SuperAdminPage | `GetCountries`, `GetAllCustomers`, `GetAllProfiles` |
| SuperAdminPage | `GetCustomerUsers` (SuperAdmin scope) |
| ~~Login-flow~~ | ~~`SelectCustomer`, `SelectProfile` (trigger fra JWT)~~ | ✅ Implementeret |

---

## 6. Arkitekt-review — Visuelle fund (2026-04-05)

Findings fra ekstern analyse af architect-audit-2026-04-05.zip.  
Prioriteret: **critical** → **major** → **minor**

### Critical (blokerer go-live)

| # | Område | Problem | Handling |
|---|--------|---------|---------|
| C1 | Raw label keys | `shared.Save`, `nav.*` vises direkte i UI | Fail hard + fallback formatter — aldrig vis key |
| C2 | Visuel konsistens | Spacing, font-size, komponenter varierer på tværs | Indfør design tokens (spacing scale, font scale, color tokens) |
| C3 | Kontrast (WCAG) | Ikke konsekvent — risiko for AA-brud | Min. 4.5:1 tekst / 3:1 UI-elementer |
| C4 | Fokus-states | Mangler på alle interaktive elementer | Implementér `:focus-visible` med tydelig outline |

### Major (skal rettes inden første brugertest)

| # | Område | Problem | Handling |
|---|--------|---------|---------|
| M1 | Login-sider | Mangler visuelt hierarki — form, titel, handlinger flyder | Card-layout max-width 480px, 24px spacing, klar primary button |
| M2 | BroadcastingHubPage | For meget whitespace — ser ufærdig ud | Grid-system + max-width container + card/tabel content density |
| M3 | Overlay navigation | Ingen affordance — trigger ikke synlig | Tydelig trigger (ikon + label) + hover/focus states |
| M4 | UserProfile (mobil) | Formfelter for tæt på kanter | Min. 16px padding + input height min. 44px |
| M5 | TopBar | Kan klippe/overflyde på small devices | Responsive collapse — skjul tekst, behold ikon |
| M6 | Buttons / actions | Primary vs. secondary ikke differentieret | Én primary farve + sekundær outlined variant |
| M7 | Tabeller / lister | Mangler densitet og alignment | Compact table mode + tydelige column headers + zebra rows |
| M8 | Overlay + palette | z-index / klik-zoner kan konflikte | Standardisér overlay stack: backdrop → panel → modal |
| M9 | Dashboard / hub | Generisk/ufærdig visuel identitet | System-wide color palette + typografi + spacing system |

### Minor

| # | Område | Problem | Handling |
|---|--------|---------|---------|
| m1 | Command palette | Lav visuel dybde (shadow for svag) | Øg elevation + backdrop blur |

---

*Fil: `docs/UI_STATUS.md` — opdateres løbende. Arkitektspørgsmål fjernes når besvaret.*
