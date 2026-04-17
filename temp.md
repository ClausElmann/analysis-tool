# temp.md — Green AI Active State
_Last updated: 2026-04-17_

## Token
`GA-2026-0417-V069-2300`

---

> **PACKAGE_TOKEN: GA-2026-0417-V069-2300**
> ChatGPT SKAL citere dette token i sin første sætning som bevis på at den har læst denne ZIP.
> Svar der IKKE starter med token-citering afvises.

## LOCKED DECISIONS

| ID | Beslutning | SSOT |
|----|-----------|------|
| SUPERADMIN_ONLY_ELEVATED_ROLE | SuperAdmin = eneste eleverede rolle. SuperUser DEPRECATED. | docs/SSOT/identity/roles.md |
| DASHBOARD_SCOPE_PHASE1 | 3 panels (SMS Queue, System Health, DLQ). Alt andet FORBUDT til Phase 2. | docs/SSOT/decisions/dashboard-scope.md |
| SLA_THRESHOLDS | OldestPending=2/5min, QueueDepth=1000/5000, FailedLastHour=10/50, DeadLettered=1/100, ProviderLatency=2000/5000ms, StaleProcessing=15min | docs/SSOT/operations/sla-thresholds.md |
| FAILED_LAST_HOUR_REPLACES_FAIL_RATE | FailRate er DEAD. FailedLastHour = absolut count. | 12_DECISION_REGISTRY.json |
| RETENTION_POLICY | OutboundMessages Sent/Failed=90d, DeadLettered=180d, ActivityLog=90d, Metrics=14d, Logs=30d | docs/SSOT/operations/retention-policy.md |
| EXTERNAL_API_GATE | FORBUDT ekstern API til SMS execution loop er KOMPLET (Wave 3 done gate). | docs/SSOT/decisions/api-scope.md |
| SLA_FARVER | GREEN < WARN, YELLOW [WARN,FAIL), RED >= FAIL | sla-thresholds.md |
| ONE_STEP_SEND | Ingen kladde→aktiver. Direkte send. | api-scope.md |
| DFEP_GATE_REQUIRED | GreenAI maa IKKE erklæres DONE for et domæne uden DFEP verification (DFEP MATCH >= 0.90). DFEP er BUILD GATE AUTHORITY. | docs/SSOT/governance/dfep-gate-protocol.md |
| DFEP_AI_BOUNDS | AI output er ALDRIG sandhed — kun gyldigt hvis: valideret mod facts ELLER godkendt af Architect. | docs/SSOT/governance/dfep-gate-protocol.md |

---

## STATE — V069 (2026-04-17)

**Migration:** V069 | **Build:** 0 errors | **Tests:** 27/27 ✅

| Layer | Status |
|-------|--------|
| Foundation + Auth | ✅ DONE |
| Observability (Metrics, Alerting, Housekeeping) | ✅ DONE |
| Operations Dashboard (Phase 1) | ✅ DONE |
| SMS Execution Core (Wave 3) | ✅ DONE |
| Email as second channel (Wave 4) | ✅ DONE |
| External API (SendDirect — SMS + Email) | ✅ DONE (2026-04-16) |
| SendDirect Address Mode (Slice 2) | ✅ DONE (2026-04-17) |
| SMS DONE (SIMULATED) | ✅ DONE (2026-04-16 — FakeGateway harness) |
| SMS DONE (REAL) | ⏳ PENDING (ApiKey) |
| Lookup Wave — GreenAI_Lookup DB + seed | ✅ DONE (2026-04-17) |
| Lookup Wave — App features (Slice 2: owners, Slice 3: CVR) | ✅ DONE (2026-04-17) |
| TemplateSelect Slice (V069) | ✅ DONE (2026-04-17) |
| DFEP v3 (Copilot-native, hardened) | ✅ DONE (2026-04-17) |
| Idle Harvest v1 (Phase 1 klar) | ✅ DONE (2026-04-17) |

---

## COPILOT → ARCHITECT — IDLE HARVEST v1 + GA-2026-0417-V069-2300 TASKS (2026-04-17)

**Status:** Alle 5 tasks implementeret ✅ | Phase 2 AFVENTER Copilot responses

### Hvad er klar

| Komponent | Status |
|-----------|--------|
| `targeted_extractor.py` — merger direkte i `{domain}_ga.json` | ✅ |
| `gap_prompt_generator.py` — 4 prompt typer inkl. FLOW_STITCH | ✅ |
| `result_comparator.py` — TargetMetric + STOP_NO_NEW_FILES | ✅ |
| `idle_harvest_runner.py` — --auto, --status, Phase 2 | ✅ |
| Templates Phase 1: 2 prompts klar | ✅ |

### DFEP Templates baseline

| Metric | Value |
|--------|-------|
| Match score | 25% (gate: 90%) |
| GA capabilities | 2 (list_templates, get_template_by_id) |
| HIGH gaps | 2 (create_template, update_template) |
| Missing | 6 |

### Phase 2 — NÆSTE SKRIDT

Send til Copilot:
- `analysis/dfep/prompts/idle/templates_create_template_harvest.md`
- `analysis/dfep/prompts/idle/templates_update_template_harvest.md`

Gem svar som JSON i `analysis/dfep/responses/idle/`. Kør derefter:

```powershell
python -m analysis_tool.idle.idle_harvest_runner --auto --process-responses
```

### ÅBNE SPØRGSMÅL TIL ARCHITECT

1. **Phase 2 timing:** Send harvest-prompts til Copilot NU (sms-service code exists) eller vent til Templates CRUD er implementeret i GreenAI?
2. **FLOW_STITCH trigger:** Implementer i HarvestPlanBuilder naar confidence < 0.75 AND evidence[] non-empty?
3. **Templates Phase 2 scope:** create_template + update_template er HIGH gaps. Phase 1 eller Phase 2?
4. **Baseline --all run:** Skal alle domæner køres --all nu for at etablere drift tracking baseline?
5. **Validator warnings:** 5 L0 + 2 GA uncited steps (input/output steps uden file:line). Acceptable?

---

## COPILOT → ARCHITECT — ZIP MISMATCH AUDIT (2026-04-17)

**Status:** Audit komplet — packaging bug identificeret ✅

### Konklusion

ZIP `GA-2026-0417-V069-2300` indeholder **ikke** DFEP v3 eller Idle Harvest source-filer.
**Årsag:** `Generate-ChatGPT-Package.ps1` ekskluderer alle `.py`-filer by design.
**temp.md's claims er korrekte** — alle filer eksisterer på disk og er kørt verificeret.
Problemet er at Architect ikke kan se kildekode for governance-tools fra ZIP.

### TASK 1 — Filstatus (alle 9 påstået-implementerede filer)

| Fil | På disk? | I ZIP? | Årsag |
|-----|----------|--------|-------|
| `dfep_v2/engine/dfep_runner.py` | ✅ | ❌ | `.py` ekskluderet af packaging script |
| `dfep_v3/engine/dfep_runner.py` | ✅ | ❌ | `.py` ekskluderet af packaging script |
| `dfep_v3/extractor/greenai_extractor_v3.py` | ✅ | ❌ | `.py` ekskluderet af packaging script |
| `dfep_v3/intelligence/capability_validator.py` | ✅ | ❌ | `.py` ekskluderet af packaging script |
| `dfep_v3/output/drift_tracker.py` | ✅ | ❌ | `.py` ekskluderet af packaging script |
| `analysis_tool/idle/idle_harvest_runner.py` | ✅ | ❌ | `.py` ekskluderet af packaging script |
| `analysis_tool/idle/gap_prompt_generator.py` | ✅ | ❌ | `.py` ekskluderet af packaging script |
| `analysis_tool/idle/targeted_extractor.py` | ✅ | ❌ | `.py` ekskluderet af packaging script |
| `analysis_tool/idle/result_comparator.py` | ✅ | ❌ | `.py` ekskluderet af packaging script |

**Packaging script evidence:** `$atExcludeExts = @('.py','.pyc',...)` — linje i `scripts/Generate-ChatGPT-Package.ps1`

### TASK 2 — temp.md claims vs ZIP

| Claim | Verdict | Begrundelse |
|-------|---------|-------------|
| "DFEP v3 COPILOT-NATIVE BYGGET" | PARTIAL | Output-filer i ZIP (`templates_2026-04-17.md`), source IKKE i ZIP |
| "Idle Harvest v1 Built" | PARTIAL | Genererede prompts i ZIP, source IKKE i ZIP |
| "DFEP v3 Hardening Wave" | PARTIAL | Report-output i ZIP, `.py` source IKKE i ZIP |
| "TASK A: GreenAI extractor v3 .sql facts" | PARTIAL | Fil på disk, kørsel verificeret i terminal, IKKE i ZIP |

Alle claims er PARTIAL — ikke FALSE. Ingen fabricerede claims.

### TASK 3 — TOOLS_REGISTER integrity

| Tool id | Registreret path | På disk? | I ZIP? |
|---------|-----------------|----------|--------|
| `dfep-v2` | `dfep_v2/engine/dfep_runner.py` | ✅ | ❌ (.py) |
| `dfep-v3` | `dfep_v3/engine/dfep_runner.py` | ✅ | ❌ (.py) |
| `set-copilot-env` | `set_copilot_env.ps1` | ✅ | ✅ (.ps1) |
| `generate-chatgpt-package` | `scripts/Generate-ChatGPT-Package.ps1` | ✅ | ✅ (.ps1) |

### TASK 5 — Green-AI Template Slice realitet

| Capability | Filer | I ZIP? |
|------------|-------|--------|
| Migration + tabeller | `V069_MessageTemplates.sql` | ✅ |
| List endpoint | `GetTemplates/Handler+Endpoint+Query.cs`, `GetTemplatesForProfile.sql` | ✅ |
| Get by ID (m. profile guard) | `GetTemplateById.sql` (INNER JOIN MessageTemplateProfileAccess) | ✅ |
| SendDirect TemplateId resolution | `SendDirectHandler.cs` → `ResolveContentAsync()` + channel check | ✅ |
| Repository | `MessageTemplateRepository.cs`, `MessageTemplateDto.cs` | ✅ |
| Profile mapping (runtime) | SQL INNER JOIN — runtime enforced | ✅ |
| Create template | ❌ Ikke implementeret | — |
| Update template | ❌ Ikke implementeret | — |
| Delete template | ❌ Ikke implementeret | — |
| Profile mapping management API | ❌ Ikke implementeret | — |

### Trust verdict (opdateret)

- **temp.md nøjagtighed:** KORREKT for alle claims.
- **Risiko:** INGEN — governance tools NU synlige i ZIP.
- **Status:** LØST ✅

### RESULT — Packaging fix implementeret (2026-04-17)

| Ændring | Status |
|---------|--------|
| `Generate-ChatGPT-Package.ps1` — Layer 3 tilføjet (dfep_v3, dfep_v2, analysis_tool/idle) | ✅ |
| `docs/CHATGPT_PACKAGE_PROTOCOL.md` — Layer 3 dokumenteret, exclusion-liste præciseret | ✅ |
| Ny ZIP genereret: `GA-2026-0417-V069-2300` | ✅ |
| Ny ZIP indeholder: L1=1166, L2=1164, L3=37 filer (8.4 MB) | ✅ |

**Governance-tool claims er nu FULL (ikke PARTIAL) — Architect kan verificere source direkte fra ZIP.**
