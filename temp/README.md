# temp/ — Arkitekt leveringsmappe

> **Denne fil er PERMANENT. Copilot holder den ajour. Brugeren sletter den ALDRIG.**
> Alle andre filer i `temp/` er flygtige — bruges til levering til Arkitekt, slettes bagefter.

**Sidst opdateret:** 2026-04-23

---

## STATUS

```
mode: BUILD_READY
status: WAVE 1 — UI Foundation afventer implementering
```

---

## NÆSTE HANDLING

**WAVE 1** — Byg UI Foundation (ingen backend-afhængigheder):
1. `Shared/DataGrid/AppDataGrid.razor`
2. `Shared/Dialogs/ConfirmDeleteDialog.razor`
3. `Shared/Dialogs/BaseFormDialog.razor`
4. `NavigationMenu.razor`

Derefter WAVE 2 → GS-001 (Login)

---

## LEVEREDE FILER (klar til afsendelse)

| Fil | Indhold | Permanent original |
|-----|---------|-------------------|
| `architect_decisions_final.md` | LOCKED arkitekt-beslutninger | `harvest/architect-review/` |
| `build_order.md` | WAVE 1-4 rækkefølge (GODKENDT) | `harvest/architect-review/` |
| `backend_ui_contract.md` | Endpoint-mapping per WAVE 2 story | `harvest/architect-review/` |
| `build_rules.md` | Non-plagiarism build-regler | `harvest/architect-review/` |
| `ui_blueprints.md` | Standard UI blueprints (LOCKED) | `harvest/architect-review/` |
| `gateway_protocol.md` | Analysis-tool gateway regler | `harvest/architect-review/` |
| `build_execution_protocol.md` | Deterministisk build protokol | `harvest/architect-review/` |
| `analysis_tool_self_definition.md` | System kernel definition (LOCKED) | `harvest/architect-review/` |
| `MASTER.md` | Alle 69 stories, status, prio | `harvest/stories/` |
| `COPILOT-GREENAI-AND-ANALYSE-TOOL-ONBOARDING.md` | Copilot SSOT | `docs/` |

---

## PROCEDURE

Copilot workflow — i denne rækkefølge:
1. Ret/opret kilde-filer i `harvest/architect-review/` eller `harvest/stories/`
2. Kør generator hvis stories opdateres
3. Kopiér ændrede filer til `temp/` som leveringsbevis

```powershell
cd C:\Udvikling\analysis-tool
Copy-Item harvest/architect-review/architect_decisions_final.md temp/ -Force
Copy-Item harvest/architect-review/build_order.md temp/ -Force
Copy-Item harvest/architect-review/backend_ui_contract.md temp/ -Force
Copy-Item harvest/architect-review/build_rules.md temp/ -Force
Copy-Item harvest/architect-review/ui_blueprints.md temp/ -Force
Copy-Item harvest/architect-review/gateway_protocol.md temp/ -Force
Copy-Item harvest/architect-review/build_execution_protocol.md temp/ -Force
Copy-Item harvest/architect-review/analysis_tool_self_definition.md temp/ -Force
Copy-Item harvest/stories/MASTER.md temp/ -Force
```


# README — Story-katalog

> **Start her** før du åbner andre filer.

**Genereret:** 2026-04-23
**Total stories:** 69 (21 DONE + 48 aktive)

---

## Filer i dette katalog

| Fil | Indhold |
|-----|---------|
| **MASTER.md** | Komplet oversigt — alle stories, status, prio, links |
| **GS-001..021.md** | GreenAI eksisterende funktionalitet (✅ DONE) |
| **US-xxx.md** | Ny UI funktionalitet fra harvest |
| **US-NEW-xx.md** | Manuelt tilføjede stories (arkitekt-besluttet) |

---

## Prioritetsoversigt (harvest stories)

| Prio | Antal |
|------|-------|
| P1 | 7 |
| P2 | 17 |
| P3 | 24 |

---

## Procedure

1. **Arkitekt:** Læs `MASTER.md` → åbn individuelle filer via links
2. **Build:** Se `harvest/architect-review/build_order.md` for WAVE-rækkefølge
3. **Status-opdatering:** Ændr `Status:` i individuel story-fil
4. **Ny story:** Tilføj i `generate_story_files.py` → regenerér
5. **SSOT-regel:** Kilde = denne mappe + generator-script — IKKE temp/

---

*Genereret af `scripts/stories/generate_story_files.py`*

---

## 🔄 RUNTIME STATE (APPEND ONLY)

> **Regler:**
> - Denne sektion erstatter den tidligere `temp.md` / `temp/temp.md`
> - Copilot må KUN skrive i denne sektion — ikke i resten af README.md
> - Append-only — ingen overskrivning af tidligere entries
> - Format: `## COPILOT → ARCHITECT — [EMNE] ([YYYY-MM-DD])`

---

## COPILOT → ARCHITECT — Opsætning (2026-04-23)

**Status:** DONE ✅

### 🎯 Completed
- `harvest/architect-review/ui_blueprints.md` — 5 standard UI blueprints defineret (LIST, FORM, DETAILS, MESSAGING, AUTH)
- `temp/README.md` konverteret til hybrid: statisk SSOT + append-only RUNTIME STATE
- Alle `temp/temp.md` og `temp.md` referencer opdateret til `temp/README.md` i alle SSOT-filer
- `.github/copilot-instructions.md` opdateret: README.md er PERMANENT undtagelse i temp/

### ❓ Decisions Needed
- `ui_blueprints.md` er DRAFT — Arkitekt bedes godkende eller korrigere blueprints inden WAVE 1 start

---

## COPILOT → ARCHITECT — ANALYSIS TOOL AS GATEWAY (2026-04-23)

> **PERMANENT SSOT — se:** `harvest/architect-review/gateway_protocol.md` (LOCKED)

---

## COPILOT → ARCHITECT — BUILD EXECUTION PROTOCOL (2026-04-23)

> **PERMANENT SSOT — se:** `harvest/architect-review/build_execution_protocol.md` (LOCKED)

---

## ANALYSIS TOOL SELF-DEFINITION

> **PERMANENT SSOT — se:** `harvest/architect-review/analysis_tool_self_definition.md`
> STATUS: LOCKED — kræver Architect approval for ændringer

### 1. IDENTITET

**analysis-tool ER:**
- Mining engine for Layer 0 (sms-service)
- Gateway til extracted viden under GreenAI build
- SSOT for behaviors, flows, requirements, stories
- Anti-plagiat garanti

**analysis-tool ER IKKE:**
- Et produktionssystem
- En del af GreenAI runtime
- En erstatning for Architect-beslutninger

**Roller:**
| Rolle | Aktør | Ansvar |
|-------|-------|--------|
| Architect | ChatGPT | Strategi, godkendelse, regler, build-direktiver |
| Builder | Copilot | Mining, ekstraktion, implementering, rapportering |
| Relay | User | Videresender beskeder mellem Architect og Copilot |

---

### 2. ANSVARSOMRÅDE (ABSOLUT)

Analysis-tool er **eneste** ansvarlige for:
- Mining af Layer 0 (`sms-service/`, wiki)
- Ekstraktion til `corpus/ui_behaviors.jsonl`, `flows.jsonl`, `requirements.jsonl`
- Truth gate: intet bygges uden evidens i corpus
- Anti-plagiat: ingen Layer 0 kode i output
- SSOT for al extracted data som GreenAI bygger på

---

### 3. FORBUD (HÅRDE REGLER)

Copilot må **ALDRIG**:
- Bygge GreenAI UI uden eksplicit Architect-direktiv
- Skrive produktionskode uden "N-B APPROVED" fra Architect
- Kopiere eller parafrasere Layer 0 kode
- Antage flows, requirements eller DTOs der ikke er i corpus
- Bruge eksterne LLM, API-kald eller Internet-søgning

---

### 4. OUTPUT KONTRAKT

Analysis-tool producerer **kun** disse filtyper:

| Output | Sti | Indhold |
|--------|-----|---------|
| Behaviors | `corpus/ui_behaviors.jsonl` | Bruger-actions per komponent |
| Flows | `corpus/flows.jsonl` | Procesforløb |
| Requirements | `corpus/requirements.jsonl` | Regler, endpoints, felter |
| Stories | `harvest/stories/` | GS-/US-filer + MASTER.md |
| Architect review | `harvest/architect-review/` | Gaps, decisions, contracts |

Alt output er:
- Evidensbaseret (kilde-reference påkrævet)
- Fri for implementation details (ingen kode, ingen SQL)
- Verificeret (`behaviors_verified` flag i jsonl)

---

### 5. GATEWAY ROLLE (UNDER BUILD)

Under GreenAI build (MODE B):
- `corpus/` er eneste lovlige kilde til domain-viden
- `harvest/stories/` er eneste lovlige kilde til scope
- `harvest/architect-review/backend_ui_contract.md` er eneste lovlige kilde til endpoints
- Direkte opslag i `sms-service/` = **VIOLATION**

Lookup-rækkefølge:
```
story → domain → behaviors → flows → requirements → blueprint → build
```
Ethvert UNKNOWN i kæden = STOP.

---

### 6. BUILD CONTROL

Analysis-tool kan validere story-readiness:
```
✅ domain i domains/ med status=DONE
✅ behaviors count > 0 i ui_behaviors.jsonl
✅ flows count > 0 i flows.jsonl
✅ requirements count > 0 i requirements.jsonl
✅ alle DTO-felter navngivet eksplicit
✅ alle endpoints i backend_ui_contract.md
```
Mangler ét punkt → rapportér gap → STOP build på den story.

---

### 7. ONBOARDING (CRITICAL)

Hvis session-hukommelse ryger, læs i denne rækkefølge:
1. `docs/COPILOT-GREENAI-AND-ANALYSE-TOOL-ONBOARDING.md` — roller, regler, modes
2. `docs/GREEN_AI_BUILD_STATE.md` — projekt-status
3. `temp/README.md` (denne fil) — aktuel state + RUNTIME STATE
4. `harvest/architect-review/build_order.md` — WAVE-rækkefølge
5. `harvest/architect-review/ui_blueprints.md` — execution patterns

Efter læsning: du kender corpus-struktur, gateway-regler, build-protokol og aktuel WAVE.

---

### 8. DECOUPLING (SLUTTILSTAND)

Når GreenAI er feature-complete:
- `analysis-tool/` kan arkiveres eller fjernes
- GreenAI afhænger **ikke** af analysis-tool runtime
- GreenAI har egne DTOs, APIs, tests — ingen reference til `corpus/`
- Stories er "consumed" — ikke "linked"

---

### 9. ARCHITECT CONTROL

**Kun Architect (ChatGPT) må:**
- Ændre regler, pipeline eller build-strategi
- Godkende stories til build (N-B APPROVED)
- Omdefinere scope eller domæner
- Sætte WAVE-grænser

**Copilot må kun:**
- Udføre direktiver
- Rapportere findings og gaps
- Stoppe ved uklarhed
- Aldrig tage strategiske beslutninger alene

---

### 10. ENDELIG REGEL

```
HVIS tvivl → RETURNER UNKNOWN → STOP → VENT på Architect
ALDRIG GÆT
ALDRIG ANTAG
ALDRIG FORTSÆT MED INCOMPLETE DATA
```

---

## COPILOT → ARCHITECT — KERNEL SYNC AUDIT (2026-04-23)

**Status:** DONE ✅ — alle conflicts løst

---

## COPILOT → ARCHITECT — KERNEL GOVERNANCE LOCK (2026-04-23)

**Status:** DONE ✅

### Udført

1. ✅ `harvest/architect-review/gateway_protocol.md` oprettet (LOCKED)
2. ✅ `harvest/architect-review/build_execution_protocol.md` oprettet (LOCKED)
3. ✅ `harvest/architect-review/analysis_tool_self_definition.md` oprettet (LOCKED)
4. ✅ GATEWAY-sektion i README erstattet med reference → kernel-fil
5. ✅ BUILD EXECUTION PROTOCOL-sektion i README erstattet med reference → kernel-fil
6. ✅ LEVEREDE FILER tabel opdateret (3 nye filer + ui_blueprints REVIEW)
7. ✅ PROCEDURE-blok opdateret (3 nye Copy-Item linjer)
8. ✅ Alle 3 kernel-filer kopieret til `temp/`

### Kernel-filer (LOCKED)

| Fil | SSOT for |
|-----|---------|
| `gateway_protocol.md` | Analysis-tool gateway regler |
| `build_execution_protocol.md` | Deterministisk build protokol |
| `analysis_tool_self_definition.md` | System kernel self-definition |

**Alle ændringer til disse filer kræver Architect approval.**

---

## COPILOT → ARCHITECT — UI BLUEPRINTS LOCKED (2026-04-23)

**Status:** DONE ✅ — UI BLUEPRINTS LOCKED — BUILD SAFE

- `harvest/architect-review/ui_blueprints.md` STATUS: LOCKED — Architect approved
- KERNEL header tilføjet (ingen afvigelser tilladt under build)
- LEVEREDE FILER tabel opdateret: REVIEW → LOCKED

---

## SSOT CONFLICT RESOLVED — UI BLUEPRINTS LOCKED (2026-04-23)

**Status:** KERNEL SYNC OK ✅

- Verificeret: ingen DRAFT-status i filhoved
- Verificeret: KERNEL header på plads
- Verificeret: "DRAFT" i linje 219/372 er domæneindhold (beskedstatus 0=Draft) — ikke konflikt
