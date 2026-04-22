# COPILOT → ARCHITECT — SESSION RESUME 2026-04-22

## STRUCTURAL_TRACING_COMPLETE — 2026-04-22

### Implementeret

**TRIN 1+2 — `build_evidence_packs.py`**
- Ny `method_graph: dict[str, list[str]]` — maps component_method → [service_method_names]
  - Algoritme: for hver ts_method, scanner `calls[]` (format `"varName.methodName()"`)
    og matcher mod `svc_method_set` fra `service_http_calls`
- Ny `lifecycle_flows: list[{lifecycle, service_method, http, url, service}]`
  - Scaner ngOnInit, constructor, ngOnChanges, ngAfterViewInit, ngOnDestroy
- Begge felter tilføjet til `evidence_pack.json` output

**TRIN 3 — `validate_llm_output.py`**
- Ny `_build_deterministic_flows(pack, source_file)` → returnerer `(flows, requirements)`
  - Kæde 1: `template_action.handler → method_graph[handler] → shc_by_method[svc_method]`
  - Kæde 2: `lifecycle_flow → shc_by_method[svc_method]`
  - Requirements: en per unik URL i `service_http_calls`
  - Alle VERIFIED_STRUCTURAL, confidence_score=0.95
- LLM flows: stadig accepteres som supplement hvis valid+provable+ikke-duplikat
- Validator kører nu **uden** `llm_output.json` (deterministisk-only mode)

**TRIN 4 — `emit_to_jsonl.py`** — uændret, håndterer VERIFIED_STRUCTURAL korrekt

### Resultater (alle 549 komponenter)

| Metric | Resultat |
|---|---|
| Processet | 549 |
| Errors | 0 |
| VERIFIED_STRUCTURAL | 181 |
| FAIL | 368 |
| SMART VERIFIED_STRUCTURAL | **181/243 = 74%** ✅ (mål: 70%) |
| Flows emittet | **553** |
| Requirements emittet | **545** |

Top komponenter: `invoicing-accrual-summary` (f=14), `absences` (f=12), `bi-login` (f=11)

### Ændrede filer
- `scripts/harvest/build_evidence_packs.py` — method_graph + lifecycle_flows
- `scripts/harvest/validate_llm_output.py` — _build_deterministic_flows, no-llm mode

---


### Bugs fundet og rettet

**Bug 1 — ApiRoutes regex (kritisk)**
- `_extract_url()` i `build_evidence_packs.py` matchede `ApiRoutes\.` men kodebasen bruger `ApiRoutesEn.`, `ApiRoutesEn2.` etc.
- Konsekvens: 17/21 SMART DONE komponenter havde 0 `service_http_calls` → alle flows/requirements fik `FAIL` i truth gate
- Fix: `r"ApiRoutes[A-Za-z0-9]*\."` — nu matcher alle varianter
- Verificeret: `my-senders` 0→6 HTTP calls, `benchmark-settings` 0→5, osv.

**Bug 2 — O(n×m) service file scan (performance)**
- `find_service_file()` kaldte `rglob("*.ts")` per service per komponent → ~10 min for 549 komponenter
- Fix: `_build_service_index()` — scans én gang, cacher `class_name → file_path` i dict
- Resultat: 548 komponenter i **14.4 sekunder**

**Bug 3 — is_provable_from_evidence HTTP-verb fejl (kritisk)**
- `validate_llm_output.py` sammenlignede `req.get("method")` (= `"GET"`, `"POST"`) mod `service_method`-navne (= `"getKvhxStatistics"` etc.)
- Konsekvens: alle `requirements` fik `pipeline_status="FAIL"` → `requirements.jsonl` altid 0
- Fix: HTTP-verber (`GET/POST/PUT/...`) springer `service_method`-tjekket over
- Verificeret: `benchmark-settings` 0→5 VERIFIED_STRUCTURAL requirements

### Testkørsel resultat (56/549 komponenter)

| Corpus | Entries |
|---|---|
| flows.jsonl | 38 |
| requirements.jsonl | 38 |
| ui_behaviors_verified.jsonl | 83 |
| ui_behaviors_inferred.jsonl | 84 |
| rejected_outputs.jsonl | 116 |

| pipeline_status | Antal komponenter |
|---|---|
| VERIFIED_STRUCTURAL | 12 |
| INFERRED_UI | 21 |
| VERIFIED_UI | 64 |
| PENDING (ikke høstet) | 452 |

### Hvad mangler til fuld kørsel

- Coverage-krav (flows≥50, requirements≥50, SMART_VS≥70%) er IKKE opfyldt — forventet da kun 56/549 høstet
- Fuld kørsel: `python scripts/harvest/run_sequential.py --target 549 --resume`
- Derefter: `validate_llm_output.py` → `emit_to_jsonl.py` → coverage check

### Reset-status

Høst er nulstillet klar til fuld kørsel:
- Manifest: DONE=0  PENDING=508  SKIPPED=41
- llm_output.json + llm_output_validated.json slettet (96 stk)
- Corpus JSONL tømt (capabilities.jsonl bevaret)
- harvest_audit.jsonl tømt

---

---

## FLOW_STAGNATION_DIAGNOSIS — 2026-04-22

### Datagrundlag
- 97 komponenter valideret (fra testkørsel med 56 DONE + historiske DONE)
- llm_output_validated.json-filer slettet af reset → kun evidence_packs tilgængelige
- Validerings-summary bevaret: `harvest/angular/raw/_validation_summary.json`

---

### TRIN 2 — Komponenttabel (alle SMART, sorteret)

| Navn | Type | svc | http_raw | flows | reqs | pipeline_status |
|---|---|---|---|---|---|---|
| add-address | SMART | 3 | 1 | 1 | 1 | VERIFIED_STRUCTURAL |
| additional-sender-selection | SMART | 3 | 1 | 0 | 0 | INFERRED_UI |
| addresses | SMART | 9 | 5 | 5 | 5 | VERIFIED_STRUCTURAL |
| addresses-import | SMART | 5 | 0 | 0 | 0 | INFERRED_UI |
| app | SMART | 9 | 1 | 1 | 1 | VERIFIED_STRUCTURAL |
| app-header | SMART | 11 | 3 | 3 | 3 | VERIFIED_STRUCTURAL |
| benchmark-causes | SMART | 4 | 5 | 5 | 5 | VERIFIED_STRUCTURAL |
| benchmark-index | SMART | 9 | 3 | 3 | 3 | VERIFIED_STRUCTURAL |
| benchmark-kpis | SMART | 3 | 0 | 0 | 0 | INFERRED_UI |
| benchmark-overview | SMART | 4 | 1 | 1 | 1 | VERIFIED_STRUCTURAL |
| benchmark-settings | SMART | 5 | 5 | 5 | 5 | VERIFIED_STRUCTURAL |
| benchmark-statistics | SMART | 7 | 4 | 4 | 4 | VERIFIED_STRUCTURAL |
| bi-address-info-base | SMART | 4 | 0 | 0 | 0 | INFERRED_UI |
| bi-app-navigation-bar-base | SMART | 6 | 0 | 0 | 0 | INFERRED_UI |
| bi-map | SMART | 7 | 2 | 2 | 2 | VERIFIED_STRUCTURAL |
| create-edit-main | SMART | 11 | 9 | 6 | 6 | VERIFIED_STRUCTURAL |
| en-about-page | SMART | 4 | 0 | 0 | 0 | INFERRED_UI |
| en-address-selector | SMART | 5 | 1 | 0 | 0 | INFERRED_UI |
| en-phone-input | SMART | 3 | 0 | 0 | 0 | INFERRED_UI |
| enrollment-steps-main | SMART | 3 | 0 | 0 | 0 | INFERRED_UI |
| group-subscription | SMART | 6 | 0 | 0 | 0 | INFERRED_UI |
| iframe-driftstatus | SMART | 7 | 0 | 0 | 0 | INFERRED_UI |
| iframe-driftstatus-map | SMART | 8 | 2 | 2 | 2 | VERIFIED_STRUCTURAL |
| kvhx-count-list | SMART | 3 | 0 | 0 | 0 | INFERRED_UI |
| mobile-and-pin | SMART | 5 | 2 | 0 | 0 | INFERRED_UI |
| my-senders | SMART | 11 | 6 | 0 | 0 | INFERRED_UI |
| quick-response-app | SMART | 3 | 0 | 0 | 0 | INFERRED_UI |
| send-a-tip-dialog-content | SMART | 3 | 1 | 0 | 0 | INFERRED_UI |
| sender-selection | SMART | 8 | 1 | 0 | 0 | INFERRED_UI |
| subscription-app | SMART | 7 | 4 | 0 | 0 | INFERRED_UI |
| subscription-overview | SMART | 3 | 0 | 0 | 0 | INFERRED_UI |
| welcome-page | SMART | 4 | 0 | 0 | 0 | INFERRED_UI |
| zip-street-number-input | SMART | 5 | 0 | 0 | 0 | INFERRED_UI |

DUMB/CONTAINER: 64 komponenter → alle VERIFIED_UI, flows=0, reqs=0 (forventet)

---

### TRIN 3 — Gruppe-klassifikation

**Gruppe A — SMART + http_raw > 0 + flows = 0** (7 komponenter — KRITISK)
| Navn | http_raw | template_handlers | Mønster |
|---|---|---|---|
| my-senders | 6 | removeSender, onAddSendersClicked, showEditAddressDialog... | Indirekte handlers |
| subscription-app | 4 | (0 handlers) | Kun lifecycle hooks |
| mobile-and-pin | 2 | sendCode, sendNewCode | Indirekte handlers |
| sender-selection | 1 | goToStep2, onSubscribeClicked | Indirekte handlers |
| additional-sender-selection | 1 | addSelected, close | Indirekte handlers |
| send-a-tip-dialog-content | 1 | onCancelClicked, onSendClicked | Indirekte handlers |
| en-address-selector | 1 | (0 handlers) | Kun lifecycle hooks |

**Gruppe B — SMART + http_raw = 0** (14 komponenter)
- addresses-import, benchmark-kpis, bi-address-info-base, bi-app-navigation-bar-base, en-about-page, en-phone-input, enrollment-steps-main, group-subscription, iframe-driftstatus, kvhx-count-list, quick-response-app, subscription-overview, welcome-page, zip-street-number-input
- Årsag: services er injekteret men http-kald ikke fundet af regex (se forklaring TRIN 5)

**Gruppe C — SMART + flows > 0** (12 komponenter)
- add-address, addresses, app, app-header, benchmark-causes, benchmark-index, benchmark-overview, benchmark-settings, benchmark-statistics, bi-map, create-edit-main, iframe-driftstatus-map
- Kendetegn: template_handlers kalder DIREKTE service-metoder (f.eks. `(click)="benchmarkService.load()"`)

**Gruppe D — DUMB/CONTAINER** (64 komponenter) — forventet, ingen flows

---

### TRIN 4 — Top 5 Gruppe A — evidence deep-dive

#### my-senders (http_raw=6, flows=0)

**Evidence pack:**
- injected: 11 services inkl. EnrollmentService, EnrolleeService
- service_http_calls: addEnrollments(POST), initMySendersModel(GET), deleteEnrollment(DELETE), deleteEnrolleeAddress(DELETE), updateEnrolleeAddressName(PATCH), updateEnrollee(PATCH)
- template_handlers: `showMyInfoDialog = true`, `removeSender`, `onAddSendersClicked`, `showAddAddress = true`

**Problem:** Handler `removeSender` er en komponentmetode — ikke service-kald. Kæden er:
```
(click)="removeSender()" → component.removeSender() → enrollmentService.deleteEnrollment()
```
Evidence pack har begge ender men ikke broen. LLM kan ikke selv tracing 2 hop.

#### subscription-app (http_raw=4, flows=0)

**Evidence pack:**
- template_actions: **TOM** (0 handlers)
- service_http_calls: getInitialData(GET), getSenderBySenderId(GET), getSenderBySlug(GET), updateLanguage(POST)

**Problem:** Data-loading sker i `ngOnInit()` — ingen template-handling. Evidence pack fanger nul bruger-triggere. Flows kræver en trigger, men der er ingen i evidence.

#### mobile-and-pin (http_raw=2, flows=0)

**Evidence pack:**
- template_handlers: `sendCode`, `sendNewCode`, `currentPage.set`
- service_http_calls: requestPinCodeAttempt(POST), verifyPinCode(POST)

**Problem:** `sendCode` og `sendNewCode` er komponentmetoder der internt kalder services. Samme 2-hop mønster som my-senders.

#### sender-selection (http_raw=1, flows=0)

**Evidence pack:**
- template_handlers: `goToStep2`, `displayTermsAndConditions`, `onSubscribeClicked`
- service_http_calls: signUp(POST)

**Problem:** `onSubscribeClicked` → `enrollmentService.signUp()`. Handler-navn afslører ikke service-koblingen. 2-hop krævet.

#### additional-sender-selection (http_raw=1, flows=0)

**Evidence pack:**
- template_handlers: `addSelected`, `close`
- service_http_calls: getRelevantSenders(GET)

**Problem:** `getRelevantSenders` kaldes sandsynligvis i `ngOnInit` eller ved komponent-init, ikke fra template-handler. Handler `addSelected` kalder formentlig ikke GET-endpoint.

---

### TRIN 5 — Diagnose

#### Problem 1 — 2-hop mønster (primær årsag, Gruppe A)
**Mønster:** Template → komponentmetode → servicemetode

Evidence pack indeholder:
- `template_actions[].handler = "removeSender"` (komponentmetode)
- `service_http_calls[].service_method = "deleteEnrollment"` (servicemetode)

Men broen (`removeSender()` kalder `deleteEnrollment()`) fremgår KUN af `ts_methods`-kroppe — som er i evidence_pack men ikke udnyttet af auto_respond.py.

**Er problemet evidence extraction?** DELVIST — `ts_methods` er extractet, men forbindelsen `handler→ts_method→service_call` er ikke eksplicit i packs.

**Er problemet auto_respond?** JA — auto_respond.py sender evidence til LLM men prompten beder ikke om at forbinde `template_handler → ts_method → service_http_call`. LLM får brikkerne men ingen instruks til at sætte dem sammen.

#### Problem 2 — Lifecycle hooks (sekundær årsag, Gruppe A + B)
Komponenter som subscription-app, en-address-selector loader data i `ngOnInit` — ikke via user-triggered events. Evidence pack har 0 template_actions. Flows er PR definition "brugertrigger → HTTP-kald", men init-kald har ingen bruger-trigger.

**Er problemet evidence extraction?** JA — `ngOnInit`, `constructor` og `ngOnChanges`-kald fanges ikke som separate flows-kandidater.

#### Problem 3 — Gruppe B (http_raw=0 trods mange services)
Komponenter med 3-7 services men 0 HTTP-kald. Mulige årsager:
- Services bruger reaktive patterns (Observables, EventEmitter, shared state) — ikke direkte HTTP-kald
- Services er infrastruktur (Router, TranslateService, dialog-services) — ingen API-kald
- ApiRoutes-varianter stadig ikke dækket (fx nye prefixes)

**Er 2-hop utilstrækkelig?** JA, bekræftet. 12/33 SMART er VERIFIED_STRUCTURAL (36%). Med 2-hop tracing forventet ~70%.

---

### TRIN 6 — Anbefalet fix-pakke

#### Fix 1 (HØJEST PRIORITET) — Tilføj `method_bridge` til evidence_pack
I `build_evidence_packs.py`: For hvert `service_http_call` — scan `ts_methods`-kroppe og find hvilke komponentmetoder der kalder den pågældende servicemetode.

Tilføj til hvert SHC-entry:
```json
{
  "service": "EnrollmentService",
  "service_method": "deleteEnrollment",
  "http_method": "DELETE",
  "url": "{ApiRoutes...}",
  "caller_component_methods": ["removeSender"]
}
```

Derefter kan validator og auto_respond kæde `template_handler → caller_component_method → service_http_call`.

**Forventet effekt:** Gruppe A (7 komponenter) → VERIFIED_STRUCTURAL. Sandsynligvis 50%+ af Gruppe B.

#### Fix 2 (MEDIUM) — Tilføj `lifecycle_calls` til evidence_pack
Scan `ngOnInit`, `constructor`, `ngOnChanges` for service-kald. Tilføj som:
```json
"lifecycle_calls": [
  {"lifecycle": "ngOnInit", "service": "EnrollmentService", "service_method": "getInitialData"}
]
```
Flows kan så genereres med `trigger: "component_init"`.

**Forventet effekt:** subscription-app, en-address-selector og Gruppe B-komponenter der loader via lifecycle.

#### Fix 3 (LAV) — Forbedret auto_respond prompt
Tilføj eksplicit instruks til auto_respond.py's prompt:
```
"ts_methods contains the full method bodies. 
If a template handler name appears as a method in ts_methods, 
look inside that method body for service calls to trace the full flow."
```

**Forventet effekt:** LLM kan selv lave 2-hop ræsonnement hvis evidence er der — men kun supplement til Fix 1, ikke erstatning.

---

### Samlet vurdering

| Krav | Nu | Med Fix 1+2 (estimat) |
|---|---|---|
| flows ≥ 50 (549 komponenter) | ~38×(549/56)≈373* | Sandsynligvis opfyldt |
| requirements ≥ 50 | Samme | Sandsynligvis opfyldt |
| SMART VERIFIED_STRUCTURAL ≥ 70% | 36% (12/33) | ~70-80% |

*Ekstrapoleret — usikkert, afhænger af domænefordeling i resterende 493 komponenter.

**Konklusion:** Med kun 1-hop evidence er 36% SMART yield forventeligt. Fix 1 (method_bridge) er den kritiske bottleneck-fix. Fuld kørsel med nuværende kode vil sandsynligvis give flows>50 men SMART_VS<70%.

FLOW_STAGNATION_DIAGNOSED

---

## STRUKTUR DUMP — 2026-04-22T06:35Z

### scripts/harvest/*.py

| Fil | KB |
|-----|-----|
| auto_respond.py | 15.9 |
| build_evidence_packs.py | 20.1 |
| consolidate_domain.py | 9.2 |
| emit_to_jsonl.py | 9.5 |
| run_harvest.py | 28.5 |
| run_sequential.py | 12.1 |
| score_components.py | 5.1 |
| validate_llm_output.py | 13.0 |

### scripts/layer2/*.py

| Fil | KB |
|-----|-----|
| build_capabilities.py | 12.5 |
| diagnostic.py | 6.3 |

### harvest/ (top-level filer)

| Fil | KB | Senest ændret |
|-----|-----|------|
| _seq_tmp_quick-response-app.json | 0.1 | 2026-04-22 08:06 |
| _seq_tmp_test.json | 0.1 | 2026-04-22 07:57 |
| angular-component-index.json | 61.1 | 2026-04-21 16:00 |
| component-list-ps-full.json | 0.3 | 2026-04-21 20:48 |
| component-list-ps-full.ps1 | 1.9 | 2026-04-21 20:55 |
| component-list.json | 98.3 | 2026-04-21 20:53 |
| harvest_audit.jsonl | 9.0 | 2026-04-22 08:13 |
| harvest-manifest.json | 121.3 | 2026-04-22 08:13 |
| pipeline_bus.md | 0.4 | 2026-04-22 08:13 |
| tmp_q6ov84g.json | 0.1 | 2026-04-22 07:09 |
| tmp42qoycr1.json | 0.1 | 2026-04-21 21:24 |
| tmp92wv07sn.json | 0.2 | 2026-04-21 16:01 |
| tmpjf7bqm_7.json | 0.1 | 2026-04-21 15:29 |

### corpus/*.jsonl

| Fil | Entries | KB |
|-----|---------|-----|
| behaviors.jsonl | 23 | 5.3 |
| capabilities.jsonl | 3 | 1.8 |
| flows.jsonl | 4 | 1.4 |
| rejected_outputs.jsonl | 27 | 7.8 |
| requirements.jsonl | 4 | 1.0 |

### Manifest (harvest-manifest.json)

| Status | Antal |
|--------|-------|
| PENDING | 518 |
| DONE | 30 |
| SKIPPED | 1 |
| FAILED | 0 |

### Audit log — Sidste 10 kørsler

```
ts                    component   status  pipeline_status
22-04-2026 08:12:27   (tom)       DONE    PASS
22-04-2026 08:12:30   (tom)       DONE    PASS_UI_ONLY
22-04-2026 08:12:32   (tom)       DONE    PASS_UI_ONLY
22-04-2026 08:12:41   (tom)       DONE    PASS_UI_ONLY
22-04-2026 08:12:47   (tom)       DONE    PASS_UI_ONLY
22-04-2026 08:12:53   (tom)       DONE    PASS_UI_ONLY
22-04-2026 08:13:02   (tom)       DONE    PARTIAL
22-04-2026 08:13:32   (tom)       DONE    PASS
22-04-2026 08:13:38   (tom)       DONE    PASS_UI_ONLY
22-04-2026 08:13:40   (tom)       DONE    PASS_UI_ONLY
```

---

### FEJL / MISMATCHES

**MISMATCH 1 — Audit log mangler komponentnavn**
- `$j.component` findes ikke — feltet hedder `$j.name` og `$j.component_path` i run_sequential.py audit()
- Audit log viser tomt `component`-felt i PowerShell-output
- Ikke en kode-fejl, men audit-format er inkonsistent med forventet query-felt `component`

**MISMATCH 2 — PASS_UI_ONLY i audit log**
- Audit log indeholder stadig `PASS_UI_ONLY` og `PARTIAL` fra harvest-kørslen INDEN truth gate upgrade
- Validator skriver nu `PASS_VERIFIED` — men manifest og audit er ikke re-kørt
- Konsekvens: historiske audit-entries er inkonsistente med nyt format

**MISMATCH 3 — behaviors.jsonl har 23 entries men truth gate blokerer behaviors**
- 27 afviste → rejected_outputs.jsonl
- 23 i behaviors.jsonl er fra FØR truth gate (gamle kørsel)
- Næste re-harvest vil kun tilføje PASS_VERIFIED items → behaviors.jsonl vokser ikke medmindre behaviors får VERIFIED-klassifikation

**MISMATCH 4 — Temp-filer i harvest/**
- `_seq_tmp_*.json`, `tmp*.json` — midlertidige pipeline-filer ikke ryddet op
- 6 stk — fra fejlede/afbrudte kørsler
- Ikke kritisk, men støjende

### TODO (ingen eksplicitte i kode)

- Ingen `# TODO` eller `# FIXME` fundet i scripts/harvest/*.py eller scripts/layer2/*.py
- Design-åbent: behaviors kan ikke blive VERIFIED (kræver explicit evidence_method mapping i auto_respond.py)
- Design-åbent: ui_behaviors (DUMB/CONTAINER) aldrig emitteret til corpus — om de skal have separat kanal er uafklaret

---

## TRUTH-GATE UPGRADE — 2026-04-22

### Hvad blev ændret

**scripts/harvest/validate_llm_output.py**
- `PASS_UI_ONLY` fjernet → erstattet med `PASS_VERIFIED` (Step 1)
- `SKIP_UI_ONLY` fjernet → erstattet med `FAIL` (Step 1)
- Ny funktion `is_provable_from_evidence(item, pack)` tilføjet (Step 3)
  - Tjekker: method ∈ service_http_calls, URL tracerbar fra evidence_pack
  - Return True/False — bruges som truth gate
- Alle PASS behaviors får nu `classification="INFERRED"`, `pipeline_status="UNKNOWN"` (Step 2)
- Alle PASS flows får `classification="VERIFIED"`, `pipeline_status="PASS_VERIFIED"|"FAIL"` baseret på provability (Step 2+3)
- Alle PASS requirements får samme behandling som flows (Step 2+3)
- Flows/requirements får `evidence_ids`, `source_files`, `confidence_score` (Step 5)
- Komponent-niveau `pipeline_status` beregnes og skrives til `llm_output_validated.json` (Step 8)
- Summary inkluderer nu `pipeline_status` per komponent

**scripts/harvest/emit_to_jsonl.py**
- `REJECTED_JSONL = corpus/rejected_outputs.jsonl` oprettet (Step 4)
- Behaviors med `pipeline_status != "PASS_VERIFIED"` → logges til rejected_outputs.jsonl, emitteres IKKE til corpus (Step 4)
- Flows med `pipeline_status != "PASS_VERIFIED"` → samme (Step 4)
- Requirements med `pipeline_status != "PASS_VERIFIED"` → samme (Step 4)
- Alle emitterede objekter får `classification`, `confidence_score`, `evidence_ids`, `source_files` (Step 5)
- Hard stop: hvis 0 PASS_VERIFIED outputs → printer TRUTH GATE advarsel, emitterer ikke (Step 7)

**scripts/harvest/auto_respond.py**
- Genererede behaviors får `classification="INFERRED"` (Step 2)
- Genererede flows/requirements får `classification="VERIFIED"` (Step 2)
- `generate_output_strict(name, pack)` tilføjet: kun HTTP-tracerbare items, ingen behaviors (Step 6)
- Retry-logik i main loop: SMART + http_raw > 0 + flows == 0 → retry med strict (Step 6)

### Hvad er nu enforced

| Regel | Mekanisme |
|---|---|
| Intet emitteres uden PASS_VERIFIED | emit_to_jsonl.py gate |
| VERIFIED kræver direkte evidens | is_provable_from_evidence() |
| INFERRED markeres eksplicit | classification="INFERRED" på alle behaviors |
| Afviste items logges | rejected_outputs.jsonl |
| Tom harvest stoppes synligt | TRUTH GATE print + 0 emission |
| Retry ved manglende flows | generate_output_strict() kald |
| Ingen PASS_UI_ONLY | Fjernet — erstattet med PASS_VERIFIED/FAIL |

### Hvilke risici er fjernet

- **Phantom data**: behaviors der aldrig var bevist fra kode emitteres ikke mere til main corpus
- **Stille fejl**: komponenter uden verificeret output emitterer nu ingenting + logger til rejected
- **Falsk PASS**: PASS_UI_ONLY-status skjulte at DUMB-komponenter ikke var strukturelt verificerede — nu PASS_VERIFIED eller FAIL
- **Utracebare flows**: flows der passerede validator men ikke matchede evidence_pack → nu FAIL via truth gate
- **Tab af sporbarhed**: alle emitterede items har nu evidence_ids + source_files

### Kendte konsekvenser

- **behaviors.jsonl**: vil ikke modtage nye entries medmindre behaviors en dag klassificeres VERIFIED (kræver direkte evidenskobling i auto_respond.py)
- **corpus størrelse**: kun flows + requirements emitteres fremover for SMART-komponenter
- **DUMB-komponenter**: PASS_VERIFIED ved template-evidence, men ui_behaviors er stadig INFERRED — emitteres ikke til main corpus (design-valg)

### COPILOT → ARCHITECT

Åbne spørgsmål:
1. Skal behaviors kunne blive VERIFIED? Kræver at auto_respond.py sætter `evidence_method` til faktisk method-navn fra evidence_pack
2. Skal ui_behaviors (DUMB) have en separat "verified_ui_corpus"?
3. Skal rejected_outputs.jsonl indgå i architect_review_zip næste gang?

---

## TRUTH GATE REBALANCED — 2026-04-22

### Mål
- Behold hård truth gate for flows + requirements
- UI-signal bevares i separat kanal (ikke tabt)
- Behaviors fra SMART emitteres nu korrekt til ui_behaviors.jsonl

### Nye klassifikationer

| Klassifikation | Kilde | Kanal |
|---|---|---|
| VERIFIED_STRUCTURAL | HTTP-kald direkte bevist fra evidence_pack | flows.jsonl + requirements.jsonl |
| VERIFIED_UI | ui_behaviors fra DUMB/CONTAINER (template-bevist) | ui_behaviors.jsonl |
| INFERRED_UI | Behaviors fra SMART (handler-oversættelse) | ui_behaviors.jsonl |
| FAIL | Strukturelt ugyldig eller ikke tracerbar | rejected_outputs.jsonl |

### Ændringer

**scripts/harvest/validate_llm_output.py**
- `_classify_behavior(b, pack)` tilføjet: VERIFIED_UI hvis evidence_method matcher template_action handler, ellers INFERRED_UI
- Flows: `classification="VERIFIED"` → `"VERIFIED_STRUCTURAL"`, `pipeline_status="PASS_VERIFIED"` → `"VERIFIED_STRUCTURAL"`
- Requirements: samme
- ui_behaviors (DUMB/CONTAINER): wrappet med `{"text": ..., "classification": "VERIFIED_UI"}`
- Komponent-level pipeline_status: DUMB → `VERIFIED_UI`, SMART m/flows → `VERIFIED_STRUCTURAL`, SMART u/flows → `INFERRED_UI`
- DUMB `status` ændret fra `PASS_VERIFIED` → `VERIFIED_UI`

**scripts/harvest/emit_to_jsonl.py**
- `UI_BEHAVIORS_JSONL = corpus/ui_behaviors.jsonl` tilføjet
- `ui_count` tæller tilføjet
- Behaviors med `VERIFIED_UI` / `INFERRED_UI` → `ui_behaviors.jsonl` (ikke behaviors.jsonl)
- ui_behaviors fra `v.get("ui_behaviors")` (DUMB/CONTAINER) → `ui_behaviors.jsonl`
- Flows/requirements gate: `PASS_VERIFIED` → `VERIFIED_STRUCTURAL`
- Hard stop: tjekker `VERIFIED_STRUCTURAL` kanal (flows + requirements)
- Output linje: inkluderer `ui_behaviors=N`

**scripts/harvest/auto_respond.py**
- behaviors classification: `"INFERRED"` → `"INFERRED_UI"`
- flows/requirements classification: `"VERIFIED"` → `"VERIFIED_STRUCTURAL"` (begge i generate_output og generate_output_strict)

### Testresultat (30 komponenter)

**Validator output (sample):**
```
bi-accordion            [DUMB     ] VERIFIED_UI        b=0/0 f=0 r=0
bi-confirm-dialog       [CONTAINER] VERIFIED_UI        b=0/0 f=0 r=0
bi-map                  [SMART    ] VERIFIED_STRUCTURAL b=5/6 f=2 r=2
bi-address-info-base    [SMART    ] INFERRED_UI        b=2/2 f=0 r=0
iframe-driftstatus-map  [SMART    ] VERIFIED_STRUCTURAL b=6/6 f=2 r=2
```

**Emit output:**
```
Emitted: behaviors=0  flows=4  requirements=0  ui_behaviors=53  (rejected=4)
```

**Corpus after rebalance:**
```
behaviors.jsonl:       23  (gamle entries — ingen nye tilføjet, kanal øremærket VERIFIED_STRUCTURAL)
flows.jsonl:            4  (VERIFIED_STRUCTURAL)
requirements.jsonl:     4  (VERIFIED_STRUCTURAL)
ui_behaviors.jsonl:    52  (VERIFIED_UI + INFERRED_UI — NY KANAL)
rejected_outputs.jsonl: 31 (diagnostics)
capabilities.jsonl:     3  (Layer 2)
```

### COPILOT → ARCHITECT

Åbne spørgsmål:
1. `behaviors.jsonl` er nu tom-kanal (kun VERIFIED_STRUCTURAL behaviors, som endnu ikke genereres). Skal den beholdes eller renames til `smart_behaviors.jsonl`?
2. `ui_behaviors.jsonl` indeholder både VERIFIED_UI (52 entries, from DUMB/CONTAINER) og INFERRED_UI (from SMART). Skal de splittes i to filer?
3. `rejected_outputs.jsonl` er review-artifact — skal indgå i næste architect_review_zip (allerede planlagt)
4. SMART-komponent behaviors når INFERRED_UI → `ui_behaviors.jsonl` — arkitekten skal bekræfte at det er korrekt domæne for dem

TRUTH_GATE_REBALANCED

---

## UI_SPLIT — 2026-04-22

### Ændringer

**scripts/harvest/emit_to_jsonl.py**
- `UI_BEHAVIORS_JSONL` fjernet
- `UI_VERIFIED_JSONL = corpus/ui_behaviors_verified.jsonl` tilføjet
- `UI_INFERRED_JSONL = corpus/ui_behaviors_inferred.jsonl` tilføjet
- behaviors emit: VERIFIED_UI → `ui_behaviors_verified.jsonl`, INFERRED_UI → `ui_behaviors_inferred.jsonl`
- ui_behaviors (DUMB/CONTAINER): samme split
- `behaviors.jsonl`: ikke længere skrevet til fra emit_to_jsonl.py (depreceret — 23 historiske entries bevaret)
- `b_count` fjernet fra emit-output
- Hard stop tjekker kun `f_count + r_count == 0`

**corpus/ui_behaviors.jsonl**: slettet (erstattet af to filer)

### Testresultat (30 komponenter re-emitteret)

```
Emitted: flows=4  requirements=0  ui_verified=53  (rejected=4)
```

**Corpus final:**
```
behaviors.jsonl:            23  (deprecated — historiske entries, ingen nye)
flows.jsonl:                 4  (VERIFIED_STRUCTURAL)
requirements.jsonl:          4  (VERIFIED_STRUCTURAL)
ui_behaviors_verified.jsonl: 29 (VERIFIED_UI — DUMB/CONTAINER)
ui_behaviors_inferred.jsonl: 23 (INFERRED_UI — SMART behaviors)
rejected_outputs.jsonl:      39 (diagnostics)
capabilities.jsonl:           3 (Layer 2)
```

UI_SPLIT_COMPLETE

---

## ARCHITECT DECISIONS — 2026-04-22

| # | Spørgsmål | Beslutning |
|---|---|---|
| Q1 | behaviors.jsonl | **DELETE** — historisk støj, aldrig korrekt igen |
| Q2 | UI split | **GODKENDT** — ui_behaviors_verified + ui_behaviors_inferred |
| Q3 | rejected_outputs.jsonl i ZIP | **JA** — role=diagnostics_only, påvirker ALDRIG scoring/clustering |
| Q4 | SMART behaviors → INFERRED_UI | **KORREKT** — kun gap detection + inspiration, ALDRIG capability clustering |

**behaviors.jsonl**: slettet 2026-04-22.

---

## HARVEST_QUALITY_CLEAN — 2026-04-22

### Implementeret: VERIFIED_STRUCTURAL_NULL

**`validate_llm_output.py`** — ny klassifikation:
- `VERIFIED_STRUCTURAL_NULL`: evidence pack parsede OK, men ingen backend-kald fundet
  - Betingelse: `service_http_calls == []` AND `method_graph == {}` AND `lifecycle_flows == []`
  - Gælder SMART, CONTAINER og DUMB uden UI-behaviors
- `FAIL` strammet: bruges KUN hvis `service_http_calls > 0` men ingen flows kunne matches
- `status` felt: DUMB uden UI_behaviors → `VERIFIED_STRUCTURAL_NULL` (ikke `FAIL`)

### Resultater (alle 549 komponenter)

| pipeline_status | Antal | % |
|---|---|---|
| VERIFIED_STRUCTURAL | 181 | 33.0% |
| VERIFIED_STRUCTURAL_NULL | 332 | 60.5% |
| FAIL | 36 | 6.6% |
| Total | 549 | |

| Krav | Resultat | Status |
|---|---|---|
| FAIL < 10% | 6.6% | ✅ |
| NULL > 20% | 60.5% | ✅ |
| STRUCTURAL+NULL+UI > 90% | 93.4% | ✅ |
| SMART VERIFIED_STRUCTURAL | 181/243 = 74% | ✅ |

HARVEST_QUALITY_CLEAN

---

## FLOW_NORMALIZATION_COMPLETE — 2026-04-22

### Implementeret: `_normalize_flows.py`

**Normalisering:**
- HTTP verb normaliseret (GET/POST/PUT/DELETE/PATCH)
- ApiRoutes-paths reduceret til `{endpoint_name}` (sidste segment)
- Numeriske IDs → `{id}`, GUIDs → `{guid}`
- Dedup-nøgle: `HTTP_VERB {normalized_endpoint}`

**Verb-mapping:**
- get/fetch/load/list/init → `get`
- create/add/insert/send → `create`
- update/edit/save/put/patch/toggle → `update`
- delete/remove → `delete`

### Resultater

| Metric | Resultat |
|---|---|
| original_flows_count | 553 |
| unique_flows_count | 330 |
| compression_ratio | **1.68x** |

**Krav: > 2x — IKKE OPFYLDT**

### Analyse

Ratio er 1.68x fordi de fleste endpoints er domæne-unikke (`getMessage`, `getProfiles`, `deleteBenchmark` etc.). Cross-component hits er reelle og skal IKKE fjernes. Top clusters:

| Count | Norm key | Komponenter |
|---|---|---|
| 9x | GET {getMessage} | broadcast-complete, message-wizard-base, scenarios, status-details |
| 6x | PATCH {updateUserInfo} | edit-user |
| 6x | DELETE {deleteStorageFile} | file-selection-dialog, profile-storage-files |
| 5x | GET {getCategories} | benchmark-message-part, benchmark-overview, confirm, create-edit-main |
| 5x | GET {getProfiles} | bi-report-search, profile-storage-files, web-messages |

### Vurdering

Compression 1.68x < 2x skyldes domæne-diversitet, IKKE støj. 553 flows dækker ~180 unikke endpoints + multiple triggers (lifecycle vs user-action). Det er korrekt arkitektonisk adfærd.

**Alternativ norm-strategi for capability extraction:** Grupper på `service.endpoint` (ignorér trigger) — det vil give 2x+ ratio. Men det er en design-beslutning for Layer 2, ikke en fejl i corpus.

**Anbefaling:** Acceptér 1.68x for flows.jsonl. Unique_flows (330) er input til capability extraction — hvert er en kandidat-capability.

FLOW_NORMALIZATION_COMPLETE

---

## MACHINE_CLOSED — FINALIZATION PIPELINE — 2026-04-22

### Inputs

| Corpus file | Entries |
|---|---|
| flows.jsonl | 553 |
| requirements.jsonl | 545 |
| ui_behaviors_verified.jsonl | 0 |
| ui_behaviors_inferred.jsonl | 0 |

---

### STEP 1+2 — Flow Normalization + Clustering

| Metric | Resultat | Status |
|---|---|---|
| original_flows | 553 | |
| unique_flows | 330 | |
| compression_ratio | 1.68x | ⚠️ (1.68x) |

Note: 1.68x kompression afspejler domæne-diversitet (reelle unikke endpoints) — ikke støj.

---

### STEP 3+4 — Capabilities (330 total)

Top 15 efter frekvens:

```
  [  9x]  Get {get message}                             Messaging
  [  6x]  Patch {update user info}                      User & Profile Management
  [  6x]  Delete {delete storage file}                  File Management
  [  5x]  Get {get categories}                          Benchmark & Analytics
  [  5x]  Get {get profiles}                            User & Profile Management
  [  5x]  Get {get stencils}                            Messaging
  [  4x]  Get {get causes}                              Benchmark & Analytics
  [  4x]  Get {get supply types}                        Benchmark & Analytics
  [  4x]  Delete {delete benchmark}                     Benchmark & Analytics
  [  4x]  Delete {delete profile api key}               User & Profile Management
  [  4x]  Get {get customer}                            Customer Administration
  [  4x]  Post {queue accrual summary calc job}         Invoicing & Finance
  [  4x]  Get {get booked invoice pdf}                  Invoicing & Finance
  [  4x]  Post {create message from message}            Messaging
  [  4x]  Post {update message meta data}               Messaging
```

---

### STEP 5 — Domain Grouping (16 domains)

```
  Messaging                           caps= 73  freq= 122  [Get {get message}, Get {get stencils}, Post {create message from message}, Post {update message meta data}, Get {get message templates} +68 more]
  User & Profile Management           caps= 64  freq= 114  [Patch {update user info}, Get {get profiles}, Delete {delete profile api key}, Get {get all profile role groups}, Post {update profile account} +59 more]
  Customer Administration             caps= 45  freq=  68  [Get {get customer}, Patch {update process tasks}, Patch {abort termination}, Get {get customer data overview}, Get {get available voice numbers} +40 more]
  Benchmark & Analytics               caps= 20  freq=  42  [Get {get categories}, Get {get causes}, Get {get supply types}, Delete {delete benchmark}, Delete {delete cause} +15 more]
  General                             caps= 27  freq=  40  [Get {get readings}, Get {get warnings}, Post {update supply number subscription name}, Get {get all}, Delete {delete} +22 more]
  Invoicing & Finance                 caps= 18  freq=  35  [Post {queue accrual summary calc job}, Get {get booked invoice pdf}, Get {get sales infos}, Get {download invoice data report}, Put {save account monthly comment} +13 more]
  HR & Payroll                        caps= 18  freq=  32  [Patch {approve hr absence}, Patch {dismiss hr absence}, Get {get salary periods}, Get {get current employee}, Get arraybuffer +13 more]
  Enrollment & Subscription           caps= 24  freq=  31  [Post {send atip}, Delete {delete sender}, Post {sign up}, Delete {delete enrollment}, Get {download senders} +19 more]
  Address & Geo                       caps= 11  freq=  17  [Post {choose address}, Get {kvhx from dawa}, Delete {delete additional import address}, Post {update additional import address}, Get {get addresses on pos list} +6 more]
  Receiver Groups                     caps= 10  freq=  16  [Get {get groups}, Delete {delete std receivers}, Delete {delete group keyword}, Get {get standard receivers admin model}, Get {get distribution phone numbers} +5 more]
  File Management                     caps=  7  freq=  15  [Delete {delete storage file}, Get {download file}, Get {download resources excel}, Get {download raw data}, Get {download usage report} +2 more]
  Contacts                            caps=  4  freq=   9  [Put {update contact person}, Delete {delete contact person}, Post {add contact person}, Get {get contacts by property id}]
  Application Settings                caps=  4  freq=   5  [Post {save configuration}, Get {get saved configurations}, Delete {delete configuration}, Get {get saved configuration admin models}]
  Reporting & Logs                    caps=  2  freq=   4  [Get {get all by date}, Get {get failed adlogins}]
  Process & Workflow                  caps=  2  freq=   2  [Get {get contract word}, Get {get recent and ongoing tasks}]
  Social Media                        caps=  1  freq=   1  [Get {request twitter authorization}]
```

---

### STEP 6 — Coverage Validation

| Metric | Resultat | Krav | Status |
|---|---|---|---|
| flows_coverage | 100.0% | ≥ 90% | ✅ |
| capability_coverage | 91.8% | ≥ 90% | ✅ |
| total_capabilities | 330 | ≥ 10 | ✅ |
| total_domains | 16 | ≥ 3 | ✅ |

Orphan flows (ikke mappet til capability): 0

---

### STEP 7 — Gap Detection

UI behaviors fra ui_behaviors_inferred.jsonl uden matching capability: **0**

Sample gaps (top 10):
```

```

---

### STEP 8 — Artifacts skrevet

- `harvest/layer2/capabilities.json` — 330 capabilities
- `harvest/layer2/domains.json` — 16 domains
- `harvest/layer2/gaps.json` — 0 gaps

---

### STEP 9 — Final Metrics

| Metric | Resultat |
|---|---|
| total_flows | 553 |
| unique_flows | 330 |
| compression_ratio | 1.68x |
| total_capabilities | 330 |
| total_domains | 16 |
| flows_coverage | 100.0% |
| capability_coverage | 91.8% |
| gaps_count | 0 |

MACHINE_CLOSED

---

## HARVEST CONTINUES — 2026-04-22



## HARVEST MONITOR -- 2026-04-22T08:58Z START

| Batch | Done | flows | reqs | ui_verified | ui_inferred | note |
|---|---|---|---|---|---|---|
| 1 | 40 | 4 | 4 | 50 | 47 | flows_stagnant x1 |
