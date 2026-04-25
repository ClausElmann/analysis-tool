# Analysis Tool — Self Definition

**STATUS:** LOCKED — kræver Architect approval for ændringer  
**ROLE:** SYSTEM KERNEL (ikke runtime dokument)  
**Dato:** 2026-04-23

---

## COPILOT → ARCHITECT — ANALYSIS TOOL SELF-DEFINITION (2026-04-23)

**Status:** SSOT — ingen arkitekt-svar nødvendigt

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
3. `temp/TEMP.md` — aktuel state + RUNTIME STATE
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
