## LLM-BESLUTNING (2026-04-21)

**Kun lokal LLM (GitHub Copilot chat) er tilladt.**
- Ekstern LLM, CopilotAIProcessor, GITHUB_TOKEN, OpenAI API, stub fallback og lignende er forbudt i hele repoet.
- Alle AI-analyser og pipelines skal bruge lokal LLM (Copilot chat) — ingen undtagelser.

PACKAGE_TOKEN: GA-2026-0421-V087-1143

> ChatGPT SKAL citere dette token i sin første sætning som bevis på at den har læst denne ZIP.
> Svar der IKKE starter med token-citering afvises.

---

## SYSTEM CONSOLIDATION FREEZE (2026-04-21)

**Authority:** Architect — GA-2026-0421-V087-1143

| Komponent | Status |
|-----------|--------|
| Core pipeline | COMPLETE |
| E2E proof | VERIFIED — 5/5 PASS |
| delivery | DONE |
| logging | DONE |
| eboks_integration | DONE |
| standard_receivers | DONE |
| sms_group | DONE |
| web_messages | OUT_OF_SCOPE |
| Phase 2 Slice 1 — READ SIDE | DONE (GET /api/read/outbound-messages, 5 tests, 0 errors) |

**SYSTEM = STABLE**

---

## SYSTEM-LEVEL INVARIANTS

```
NON_BYPASSABLE_PIPELINE:
  Alle messages SKAL gaa gennem:
  Compose -> Resolve -> Dispatch -> Outbox -> Delivery
  Ingen direkte send. Ingen shortcut til provider.

TENANT_ISOLATION_GLOBAL:
  Ingen cross-tenant access. CustomerId valideres i HVERT repository-kald.
  Violation = BROADCAST_NOT_FOUND (aldrig leak af fejl-type).

STATE_MACHINE_MONOTONIC:
  OutboundMessages: Pending -> Processing -> Sending -> Sent -> Delivered|Failed
  Ingen backward transition. Ingen cross-terminal transition.
  RULE-DELIVERY-01 haandhæves i TrackDeliveryHandler — HARDKODET.

OUTBOX_ENFORCED:
  IMessageProvider kaldes KUN fra OutboxWorker.
  Ingen handler maa kalde provider direkte.

FAIL_OPEN_LOGGING:
  MetricsRepository.RecordAsync er fire-and-observe.
  Exception i metrics maa ALDRIG propagere til caller.
```

---

## CHANGE_POLICY

Aendringer af DONE domain eller invariant: KUN ved runtime failure, CVE, eller Architect Phase 2 GO.

```
FORBUDT:
  - Refactor af handlers
  - Optimering af SQL
  - Nye felter til eksisterende responses
  - Aendring af endpoint URLs
  - Nye features i eksisterende domains
  - UI over core-system (foer Architect GO)
```

---

## ARCHITECT DECISIONS — PHASE 2 (2026-04-21)

### 1. SINGLE SEND = BROADCAST MED 1 MODTAGER
```
FORBUDT: ny SendMessageHandler, bypass af pipeline, shortcut til provider
KRAV: ALL outbound = pipeline. UI adapter loser forskellen.
```
### 2. READ SIDE = PHASE 2 SLICE 1 — DONE
READ SIDE = projection af OutboundMessages. Ingen breaking changes. Minimal slice. Testbar.
### 3. SCHEDULEDAT = GATING PAA DISPATCH
```
Compose -> gem ScheduledAt. Dispatch KUN hvis ScheduledAt <= now.
FORBUDT: Delay i OutboxWorker, retry misuse.
```
### 4. INGEN DynamicMergeFields TABEL
Parse tokens fra Body. Ingen ny tabel.

---

## DOMAIN FOUNDATION — LAASET (2026-04-21)

**Authority:** Architect — GA-2026-0421-V087-1143 — BINDING FOR PHASE 2

```
TOP LEVEL:
  outbound_messaging    (core domain)
  sender_control        (OPERATING AUTHORITY — governance + identity)

SUBDOMAINS under outbound_messaging:
  delivery_timing       (timing constraint paa dispatch)
  message_personalization (indhold i service af afsendelse)
  delivery_monitoring   ("er beskederne gaaet igennem?" — real-time)
  delivery_audit        ("hvad skete der?" — compliance, historik)

PROVISIONAL:
  recipient_reachability (Slice 2 maalrettet paa kontaktdata flows)
```

| Domain | Capability | execution_mode |
|--------|-----------|----------------|
| outbound_messaging | reach_recipients | manual_or_automated |
| outbound_messaging | verify_before_dispatch | manual_only |
| delivery_timing | control_when_messages_arrive | manual_or_scheduled |
| message_personalization | personalize_with_recipient_data | system_only |
| message_personalization | maintain_reusable_content | manual_only |
| delivery_monitoring | track_delivery_outcomes | manual_or_automated |
| delivery_audit | audit_dispatch_history | system_generated_manual_access |
| sender_control | control_who_can_send | manual_only |
| sender_control | manage_sender_identity | manual_only |
| recipient_reachability | ensure_contact_reachability | manual_or_automated |

---

## ARCHITECT DECISIONS — USER MODEL (2026-04-21)

**Authority:** Architect — GA-2026-0421-V087-1143

### GreenAI = COMMUNICATION OPERATING SYSTEM
UI maa ALDRIG starte i "send besked" — starte i "hvad er situationen?"

### Flow model (bindende)
```
URGENT:      reach_recipients + verify_before_dispatch
PLANNED:     reach_recipients + control_when_messages_arrive + verify_before_dispatch
INVESTIGATE: track_delivery_outcomes + audit_dispatch_history
SETUP:       maintain_reusable_content + manage_sender_identity + control_who_can_send
```

### verify_before_dispatch = CONTROL POINT
Den eneste menneskelige sikkerhedsventil. MAAT altid vises. Maa ALDRIG bypasses. Maa IKKE gemmes vaek i UI.

### Entry points — LAASET (4 stk)

| Entry point | Brugerens mentale tilstand | Flow |
|-------------|---------------------------|------|
| "Send noget nu" | Handling, urgency | URGENT |
| "Planlæg en besked" | Kontrol, plan | PLANNED |
| "Se hvad der skete" | Tryghed, verifikation | INVESTIGATE |
| "Indstillinger" | Systemkontrol | SETUP |

---

## FLOWS — LAASET (2026-04-21, ACCEPTED med tweaks)

### FLOW 1: "Send noget nu" (URGENT)

| Step | Bruger-handling | System-respons | Capability |
|------|----------------|----------------|------------|
| 1 | Klikker "Send noget nu" | Viser modtager-vaelger | reach_recipients |
| 2 | Vaelger hvem der skal modtage | Bekraefter antal modtagere | reach_recipients |
| 3 | Skriver eller vaelger indhold | Viser preview med personaliserede vaerdier | message_personalization |
| 4 | ⚠️ CONTROL POINT — ser hvem + hvad | Blokerer videre uden eksplicit bekraeftelse | verify_before_dispatch |
| 5 | Godkender udsendelsen | Besked frigives til pipeline | reach_recipients (dispatch) |
| 6 | Ser bekraeftelse | Viser antal modtagere + live status + link til INVESTIGATE | delivery_monitoring |

**CONTROL POINT (step 4): kan IKKE springes over. Ingen timeout-auto-accept.**

### FLOW 2: "Planlæg en besked" (PLANNED)

| Step | Bruger-handling | System-respons | Capability |
|------|----------------|----------------|------------|
| 1 | Klikker "Planlæg en besked" | Viser modtager-vaelger | reach_recipients |
| 2 | Vaelger hvem der skal modtage | Bekraefter antal modtagere | reach_recipients |
| 3 | Skriver eller vaelger indhold | Viser preview med personaliserede vaerdier | message_personalization |
| 4 | Vaelger tidspunkt for udsendelse | System viser "planlagt til [tidspunkt]" | delivery_timing |
| 5 | ⚠️ CONTROL POINT — ser hvem + hvad + hvornaar | Blokerer videre uden eksplicit bekraeftelse | verify_before_dispatch |
| 6 | Godkender — eller aendrer tidspunkt | Besked gemmes som planlagt / annulleres | delivery_timing |

### FLOW 3: "Se hvad der skete" (INVESTIGATE)

**DEFAULT = delivery_monitoring** (brugeren lander altid i "er den gaaet igennem?")

| Step | Bruger-handling | System-respons | Capability |
|------|----------------|----------------|------------|
| 1 | Klikker "Se hvad der skete" | Viser DEFAULT: leveringsstatus-liste | delivery_monitoring |
| 2a [levering] | Vaelger udsendelse | Viser status per modtager (real-time) | delivery_monitoring |
| 3a [levering] | Identificerer fejlede modtagere | Viser kanaler der fejlede + tidspunkt | delivery_monitoring |
| 2b [historik] | Skifter til historik-soegning | Soeger paa afsender / dato / modtager | delivery_audit |
| 3b [historik] | Ser detaljer om specifik udsendelse | Viser komplet audit-record | delivery_audit |
| 4b [historik] | Eksporterer dokumentation | Data eksporteret til fil / API | delivery_audit |

### FLOW 4: "Indstillinger" (SETUP)

| Step | Bruger-handling | System-respons | Capability |
|------|----------------|----------------|------------|
| 1 | Klikker "Indstillinger" | Viser 3 omraader: Adgang / Afsender / Indhold | — |
| 2a [adgang] | Se / tilfoej / fjern personer med afsendelsesret | System opdaterer adgangsliste | control_who_can_send |
| 2b [afsender] | Opdater navn eller nummer modtagere ser | System gemmer ny afsenderidentitet | manage_sender_identity |
| 2c [indhold] | Opret / opdater / slet indholdsudkast | System gemmer skabelon med felter | maintain_reusable_content |
| 3 | Konfigurerer indholdsfelter | Systemet viser automatisk hvad der kan indsaettes i beskeder | personalize_with_recipient_data |

---

## COPILOT → ARCHITECT — HARVEST RESULTAT (2026-04-21)

### GITIGNORE — DONE (Architect beslutning implementeret)
```
harvest/angular/raw/    ← IGNORERET (.gitignore opdateret)
corpus/                 ← COMMIT (akkumuleret SSOT — behaviors/flows/requirements.jsonl)
harvest/domains/        ← COMMIT (Architect truth)
__pycache__/ .venv/     ← IGNORERET
```

### BATCH 1 — DONE (pass_rate=0.75, requirements_emitted=0 — FIXET i batch 2)

### BATCH 2 — DONE (2026-04-21)

**Komponenter:** message-wizard (DUMB), single-sms (SMART), scheduled-broadcasts (SMART)

```
VERDICT: ACCEPTED  pass_rate=1.0
pass=2  partial=0  fail=0  pass_ui_only=1
behaviors_emitted: +8   (total: 34)
flows_emitted:     +4   (total: 11)
requirements_emitted: 4  ← PIPELINE FIX VERIFIED ✅
```

**Backend-koblinger verificeret:**
| Komponent | Endpoint | Method |
|-----------|----------|--------|
| single-sms | `{ApiRoutes.messageRoutes.create.createSingleSMS}` | POST |
| scheduled-broadcasts | `{ApiRoutes.smsGroupScheduleRoutes.cancelScheduledBroadcastEvent}` | POST |
| scheduled-broadcasts | `{ApiRoutes.smsGroupScheduleRoutes.postponeScheduledBroadcastEvent}` | POST |
| scheduled-broadcasts | `{ApiRoutes.smsGroupScheduleRoutes.resetScheduledBroadcastEvent}` | POST |

**Pipeline-fix:** `requirements` kræver `"status": "PASS"` i llm_output.json — pattern etableret for alle fremtidige batches.

---

## CLEANUP RESULT (2026-04-21)

```
raw_files_deleted: 0 (allerede tom — gitignore forhindrer tracking)
pycache_deleted:   0 (ingen udenfor .venv)
venv_deleted:      no (.venv bevaret)
```

### REMAINING STRUCTURE

```
corpus/
  behaviors.jsonl     (34 behaviors)
  flows.jsonl         (11 flows)
  requirements.jsonl  (4 requirements)

harvest/domains/
  delivery_audit/
  delivery_monitoring/
  insights/
  operators/
  outbound_messaging/
  recipients/
  scheduling/
  template_management/
```

### WARNINGS

- `harvest/angular/raw/` mapper eksisterer på disk men er tomme — git ignorerer dem korrekt
- `.venv/` er bevaret (påkrævet for pipeline-kørsler)

---

## DEPRECATION RESULT (2026-04-21)

```
renamed: yes — harvest/domains/insights/ → harvest/domains/_deprecated_insights/
DEPRECATED.md: oprettet med authority GA-2026-0421-V087-1143
```

### REFERENCES FOUND — KRÆVER MANUEL VURDERING (må IKKE auto-fixes)

Disse filer bruger `"insights"` som begreb — IKKE nødvendigvis domain-refs — men rapporteres:

```
core/asset_scanner.py
core/execution_engine.py
core/git_analyzer.py
core/system_fusion.py
data/git_insights.json
data/work_item_analysis.json
tests/test_asset_system.py
tests/test_git_analyzer.py
tests/test_slice_7.py
run_pipeline.py
```

**VURDERING (Copilot):** Disse er del af analysis-tool core pipeline (git analysis, work items) — IKKE harvest domain pipeline. `"insights"` her refererer sandsynligvis til `git_insights` / analyse-artefakter, IKKE `harvest/domains/insights/`. Architect bekræfter om disse kræver handling.

### DOMAIN STRUCTURE EFTER DEPRECATION

```
harvest/domains/
  _deprecated_insights/    ← DEPRECATED (DEPRECATED.md tilføjet)
  delivery_audit/
  delivery_monitoring/
  operators/
  outbound_messaging/
  recipients/
  scheduling/
  template_management/
```

---

## VERIFICATION RESULT (2026-04-21)

```
domain_usage_found: false
blockers: 0
```

### ALLE FUND — KLASSIFICERET

| File | Line | Pattern | Type |
|------|------|---------|------|
| core/asset_scanner.py | 26-544 | `git_insights_batch`, `git_insights.json`, `insights[]` | PIPELINE_METADATA |
| core/execution_engine.py | 1254-1264 | `git_insights.json`, `{"insights": insights}` | PIPELINE_METADATA |
| core/git_analyzer.py | 9-254 | `{"insights": [...]}` return value fra git log analyse | PIPELINE_METADATA |
| core/system_fusion.py | 128-353 | `git_insights.json`, `git_data.get("insights", [])` | PIPELINE_METADATA |
| data/git_insights.json | — | indeholder `"insights"` array fra git log | PIPELINE_METADATA |
| data/work_item_analysis.json | — | `"insights"` nøgle i work item analyse | PIPELINE_METADATA |
| tests/test_asset_system.py | — | tester git_insights_batch asset | PIPELINE_METADATA |
| tests/test_git_analyzer.py | — | tester git_analyzer output `{"insights": [...]}` | PIPELINE_METADATA |
| tests/test_slice_7.py | — | tester pipeline slice med git_insights | PIPELINE_METADATA |
| run_pipeline.py | 32 | `"git_insights.json": "insights"` — filnavn-mapping | PIPELINE_METADATA |

**KONKLUSION:** Ingen af de 10 filer loader fra `harvest/domains/insights/`.
`"insights"` refererer udelukkende til `git_insights` — et separat data-format i analysis-tool core pipeline.
`_deprecated_insights` domain er 100% isoleret fra aktiv kode.

---

## HARVEST CLI — DONE (2026-04-21)

```
scripts/harvest/run_harvest.py — BYGGET
```

**Kørsel:**
```powershell
.venv\Scripts\python.exe scripts/harvest/run_harvest.py --batch-size 10 --auto-mark-done
.venv\Scripts\python.exe scripts/harvest/run_harvest.py --status
```

**Manifest:** `harvest/harvest-manifest.json` — status per komponent (DONE/FAILED/PENDING)

**Pipeline per komponent:**
```
1. build_evidence_packs.py  — strukturel ekstraktion
2. LLM (Copilot API)        — copilot_prompt.md → llm_output.json (reuses existing)
3. validate_llm_output.py   — validering mod evidence_pack
4. emit_to_jsonl.py         — append til corpus/ (PASS/PASS_UI_ONLY)
5. manifest update          — DONE | FAILED | PENDING_REVIEW
```

**DONE-regel (håndhævet i kode):**
```
DONE sættes KUN hvis pipeline_status IN (PASS, PASS_UI_ONLY) + --auto-mark-done
DONE sættes ALDRIG manuelt
```
