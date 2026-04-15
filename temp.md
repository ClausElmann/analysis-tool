# SESSION STATUS — 2026-04-15

> **PACKAGE_TOKEN: GA-2026-0415-V050-1316**
> ChatGPT SKAL citere dette token i sin første sætning. Svar uden token afvises.

---

## COPILOT → ARCHITECT — Ekstern API Analyse (Layer 1 udtræk) — 2026-04-15

**Formål:** Kortlægning af den eksisterende eksterne API's forretningsmæssige capabilities — udledt af Layer 0-analyse. Ingen Layer 0 kode er inkluderet her. Alt er omskrevet til krav.

---

### Domæne 1: Beskedafsendelse

**Capability: Send besked til enkelt modtager (telefonnummer og/eller e-mail)**
- Angiv telefonnummer og/eller e-mail direkte — ingen adresseopslag
- Vælg profil der afsender
- Angiv beskedtekst (SMS og/eller e-mail separat)
- Mulighed for øjeblikkelig afsendelse eller planlagt afsendelse
- Returnerer ID på oprettet afsendelsespost

**Capability: Send besked til adresse (opslag på beboere/ejere)**
- Angiv adresse → systemet slår telefonnumre/emails op automatisk
- Vælg om der sendes til beboer, ejer eller begge
- Optionelt: angiv specifikt telefonnummer/e-mail som tillæg til opslaget
- Returnerer ID på oprettet afsendelsespost

**Capability: Opret besked som kladde (batch — adresseliste)**
- Send liste af adresser → systemet opretter kladde med alle modtagere
- Besked sendes IKKE ved oprettelse — kræver separat aktivering
- Understøtter merge-felter per adresse (personalisering)
- Understøtter afsendelse til beboer og/eller ejer
- Returnerer ID på oprettet kladde

**Capability: Opret besked som kladde (hierarkisk filtrering)**
- Vælg modtagere via op til 5 niveauer af et geografisk/organisatorisk hierarki
- Besked sendes IKKE ved oprettelse — kræver separat aktivering
- Returnerer ID på oprettet kladde

**Capability: Hent beskeddetaljer**
- Hent alle data for én besked inkl. optionel modtagerliste
- Adgangskontrol: bruger må kun se beskeder under egne profiler

**Capability: Deaktiver planlagt besked**
- Tilbagekald planlagt (forsinket) besked inden afsendelse — returnerer til kladde-tilstand
- Kun mulig inden afsendelsestidspunktet

**Capability: Slet besked**
- Slet besked der endnu ikke er aktiveret/sendt

---

### Domæne 2: Leveringsstatus og rapportering

**Capability: Hent status-koder**
- Returnerer system-definerede statuskoder med beskrivelser (leveret, afsendt, afvist, afventer, m.fl.)
- Sprogtilpasset til kundens land

**Capability: Hent statusrapport for beskeder**
- Filtrer på profil, besked-ID og datointerval (UTC)
- Returnerer per-modtager status: adresse, navn, e-mail, statuskode, tidsstempel
- Adgangskontrol: bruger ser kun egne profilers beskeder

**Capability: Søg beskeder sendt til adresse**
- Søg hvilke beskeder der er sendt til en specifik adresse i et datointerval
- Bruges til at vise historik for en adresse

---

### Domæne 3: Adresseopslag og modtagerantal

**Capability: Tæl modtagere for én adresse**
- Angiv adressefelter → returnerer antal telefonnumre/emails fundet
- Bruges til forhåndsvisning inden afsendelse

**Capability: Tæl modtagere for liste af adresser**
- Send liste af adresser → returnerer per-adresse antal (beboere + ejere separat)
- Understøtter tomme adresser i listen

---

### Domæne 4: Abonnementer (opt-in/opt-out)

**Capability: Opret abonnement (via adressenøgle)**
- Tilknyt telefonnummer (mobil og/eller fastnet) og/eller e-mail til en adresse via unik nøgle
- Validerer telefonnumre inkl. internationale formater

**Capability: Opret abonnement (via adressefelter)**
- Som ovenstående, men adresse angives som strukturerede felter i stedet for nøgle

**Capability: Hent abonnementer**
- Filtrer på telefonnummer, e-mail og/eller adresse
- Returnerer liste med abonnement-ID, adresse, kontaktoplysninger

**Capability: Slet abonnement**
- Fjern et abonnement via ID

---

### Domæne 5: Standardmodtagere (faste modtagere)

**Capability: Hent alle standardmodtagere**
- Returnerer liste over faste modtagere under aktuel kunde

**Capability: Hent enkelt standardmodtager**
- Hent detaljer inkl. tilknyttede telefonnumre for én standardmodtager

**Capability: Opret standardmodtager**
- Angiv navn, telefon(er), e-mail — opretter fast modtager

**Capability: Opdater standardmodtager**
- Rediger navn, kontaktoplysninger

**Capability: Slet standardmodtager**

---

### Domæne 6: Beskedskabeloner

**Capability: Hent skabeloner for profil**
- Returnerer liste af skabeloner (SMS, e-mail, web-besked m.fl.) tilgængeligt for en profil
- Inkluderer dynamiske merge-felter

---

### Domæne 7: Webhooks (udgående notifikationer)

**Capability: Hent understøttede webhook-event-typer**
- Pt. to typer: leveringsstatus-opdateringer og web-besked-events

**Capability: Administrer webhook-registreringer (CRUD)**
- Opret, hent, opdater, slet registreringer med callback-URL og hemmelighed
- Kun tilgængeligt med Bearer-token

---

### Domæne 8: Profiler og brugerkontekst

**Capability: Hent profiler tilgængelige for bruger**
- Filtrer efter navn
- Understøtter skift af aktiv profil i sessionen

---

### green-ai: Hvad er IKKE bygget endnu

| Capability-gruppe | green-ai status |
|---|---|
| Send enkelt besked (telefon/email direkte) | ❌ ikke bygget |
| Send besked til adresse (opslag) | ❌ ikke bygget |
| Opret besked som kladde (adresseliste/hierarki) | ❌ ikke bygget |
| Deaktiver / slet besked | ❌ ikke bygget |
| Leveringsstatus og rapportering | ❌ ikke bygget |
| Adresseopslag og modtagerantal | ❌ ikke bygget |
| Abonnementer (opt-in/opt-out) | ❌ ikke bygget |
| Standardmodtagere | ❌ ikke bygget |
| Skabeloner | ❌ ikke bygget |
| Webhooks (udgående) | ❌ ikke bygget |
| Auth token (JWT) | ✅ BYGGET (`POST /api/v1/auth/token`) |

---

### Spørgsmål til Architect

1. **Scope for parallel bygning:** Hvilke af ovenstående domæner skal ind i green-ai's eksterne API — og i hvilken prioriteret rækkefølge?
2. **Besked-model:** Den eksisterende API skelner mellem "kladde → aktiver" og "send direkte" — skal green-ai følge samme to-trins model, eller bygger vi simpel én-trins-afsendelse i MVP?
3. **Hierarki-filtrering (niveau 1–5):** Er dette en grøn-ai-specifik feature eller hentes niveauerne fra sms-service-data? Skal det med i første iteration?
4. **Webhooks:** Udgående notifikationer til kundesystemer — MVP eller post-MVP?

---

> **PACKAGE_TOKEN: GA-2026-0415-V050-1316**
> ChatGPT SKAL citere dette token i sin første sætning som bevis på at den har læst denne ZIP.
> Svar der IKKE starter med token-citering afvises.

---

## COPILOT → ARCHITECT — Direktiver modtaget + implementeringsplan — 2026-04-15

**Token:** GA-2026-0415-V050-1316
**Status:** Alle direktiver læst og forstået. Opdeler i: låser nu / action-liste / afklaringsspørgsmål.

---

### Låser nu (ingen yderligere afklaring nødvendig)

| Lock | Regel |
|------|-------|
| LOCK-1: Modul-root | `Features/[Modul]/[Feature]/` — ingen shared service layer drift |
| LOCK-2: Soft delete | Kun Users. Broadcasts/OutboundMessages/ActivityLog/JobTaskStatuses = append-only/status |
| LOCK-3: API versionering | `/api/v1/` indføres nu — tilføjes til GREEN_AI_BUILD_STATE.md |
| LOCK-4: DispatchAttempts | Død model bekræftet — PLAN-2 allerede implementeret |
| LOCK-5: Ingen Redis | Deferred til målt problem |
| LOCK-6: Read-model | Dedikerede read SQL-filer — ikke separat fysisk model |
| LOCK-7: MediatR | Bevares — ingen direct-call migration |
| LOCK-8: Blazor Server | Bevares — SignalR kun på specifikke flows ved behov |

Disse skrives ind i `ai-governance/12_DECISION_REGISTRY.json` som del af implementeringen.

---

### Action-liste (prioriteret)

| # | Action | Severity | Blokeret af |
|---|--------|----------|-------------|
| 1 | Index-migration (alle Architect-specificerede indices) | KRITISK | Intet — kan starte nu |
| 2 | Correlation ID (middleware + Serilog enricher + scope-propagation) | KRITISK | Intet — kan starte nu |
| 3 | ExecutionHealth v2 (udvidet med alle nye metrics) | HØJ | Intet — kan starte nu |
| 4 | Decision Registry opdatering | HØJ | Intet — kan starte nu |
| 5 | GREEN_AI_BUILD_STATE.md: modul-root + `/api/v1/` + soft-delete locks | HØJ | Intet — kan starte nu |
| 6 | Wave 13: `run_signature_sha256` i VisualDeltaCache | MEDIUM | Architect-signal |
| 7 | Feature flags per tenant (simpel tabel + `IFeatureFlagService`) | MEDIUM | Q4 afklaring |
| 8 | DEV seed pipeline | MEDIUM | Intet — kan planlægges |
| 9 | SMS DONE 🔒 manglende del (provider send, DLR, retry, min. UI) | KRITISK | SMS-scope bekræftelse |

---

### Spørgsmål inden build (blokerer specifikke actions)

**Q1 — SLA tærskler (blokerer: monitoring alarmer)**
Architect definerede niveauerne men ikke konkrete tal:
- Oldest pending age WARN: X minutter?
- Oldest pending age FAIL: X minutter?
- Queue depth WARN/FAIL: over N rækker?
- Processing stale timeout: allerede 15 min — behold eller juster?

**Q2 — Retention strategi "på papir" (blokerer: arkiverings-SSOT)**
Copilot opretter dokument i `docs/DECISIONS.md` eller selvstændig fil?
Architect-forslag til retention-perioder:
- OutboundMessages, ActivityLogEntries, Logs, JobTaskStatuses: X måneder online?

**Q3 — Layer 1 gaps (blokerer: lookup/SMS-udvidelse)**
GAP-002/003/004/006/007/009 kræver hands-on domain-ekspert input — kan ikke løses fra kodeanalyse.
Er der plan for at indhente disse svar? (fx bruger interviewer sms-service teamet?)

**Q4 — Ekstern API første slice (blokerer: `SendDirect` feature)**
Architect prioriterede "Send enkelt besked direkte" som #1.
Skal dette bygges nu, eller afventer vi at SMS execution-loop (provider send + DLR) er komplet først?
(Dvs.: bygger vi API-overfladen over et endnu-ikke-fuldt-funktionelt SMS-domæne?)

