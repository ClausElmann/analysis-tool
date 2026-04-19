# GREEN-AI DOMAIN FACTORY MASTER PLAN
**Version:** 1.0  
**Created:** 2026-04-19  
**Token:** GA-2026-0419-V076-1000  
**Protocol:** DOMAIN FACTORY — resumable, deterministic, governance-gated  

> **RESUME TRIGGER:** "RESUME DOMAIN FACTORY" → load this file → execute SECTION 6 logic  
> **RULE:** 1 domain at a time · no guessing · full gate enforcement · full traceability  

---

## SECTION 1 — DOMAIN REGISTRY

> **NOTE on sub-scores:** 000_meta.json does NOT contain individual entities/behaviors/flows/business_rules scores.  
> Only a single `completeness_score` is tracked. Sub-scores are marked as `N/T` (not tracked).  
> gate_passed uses completeness_score ≥ 0.90 as PROXY until individual scores are available.

| # | domain_name | canonical | wave | live_state | score | gate_passed | gaps | flow_ver_ok | rules_ok | current_status | revisit_trigger | notes |
|---|-------------|-----------|------|-----------|-------|-------------|------|-------------|----------|----------------|----------------|-------|
| 1 | identity_access | ✅ | WAVE_A | DONE 🔒 | 0.98 | ✅ | 1 | UNKNOWN | UNKNOWN | DONE_LOCKED | NONE | Auth + AdminLight + UserSelfService |
| 2 | Email | ✅ | WAVE_A | DONE 🔒 | N/T | ✅ | 0 | UNKNOWN | UNKNOWN | DONE_LOCKED | NONE | status=business_rules_complete |
| 3 | job_management | ✅ | WAVE_A | DONE 🔒 | 0.93 | ✅ | 2 | UNKNOWN | UNKNOWN | DONE_LOCKED | NONE | V035 |
| 4 | localization | ✅ | WAVE_A | DONE 🔒 | 0.92 | ✅ | 2 | UNKNOWN | UNKNOWN | DONE_LOCKED | NONE | 2026-04-13 |
| 5 | activity_log | ✅ | WAVE_A | DONE 🔒 | 0.92 | ✅ | 1 | UNKNOWN | UNKNOWN | DONE_LOCKED | NONE | V037 |
| 6 | logging | ✅ | WAVE_A | N-A | 0.88 | ❌ | 1 | UNKNOWN | UNKNOWN | N-A | NONE | stable_candidate |
| 7 | system_configuration | ✅ | WAVE_A | DONE 🔒 | 0.94 | ✅ | 1 | ✅ 3/3 | ✅ 6/6 | DONE_LOCKED | NONE | N-B complete 2026-04-19. GetSetting + FileTypeValidationService. |
| 8 | customer_administration | ✅ | WAVE_B | N-A | 0.88 | ❌ | 2 | UNKNOWN | UNKNOWN | N-A | PACKAGE_LIVE_DRIFT | GOVERNANCE_REVERT 2026-04-19. N-B invalid: behaviors=0, flows=0, rules=0. NEEDS_FULL_REANALYSIS. Next analysis: minimal scope only (Name edit + User enable/disable). |
| 9 | customer_management | ✅ | WAVE_B | N-A | 0.88 | ❌ | 2 | UNKNOWN | UNKNOWN | N-A | NONE | 0 green-ai code |
| 10 | profile_management | ✅ | WAVE_B | N-A | 0.91 | ✅ | 2 | UNKNOWN | UNKNOWN | READY_FOR_GATE | NONE | stable_candidate |
| 11 | sms | ✅ | WAVE_C | IN PROGRESS | 0.98 | ✅ | N/A | UNKNOWN | UNKNOWN | IN_BUILD | NONE | Wave 8+10 done. REAL blocked on ApiKey. |
| 12 | Delivery | ✅ | WAVE_C | N-A | 0.84 | ❌ | 3 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 13 | eboks_integration | ✅ | WAVE_C | N-A | 0.88 | ❌ | 2 | UNKNOWN | UNKNOWN | N-A | NONE | 0 green-ai code |
| 14 | templates | ✅ | WAVE_C | N-A | 0.37 | ❌ | 5 | UNKNOWN | UNKNOWN | N-A | NONE | Low score — needs extraction |
| 15 | web_messages | ✅ | WAVE_C | N-A | 0.88 | ❌ | 2 | UNKNOWN | UNKNOWN | N-A | NONE | status=stable |
| 16 | Webhook | ✅ | WAVE_C | N-A | 0.37 | ❌ | 5 | UNKNOWN | UNKNOWN | N-A | NONE | Low score — needs extraction |
| 17 | phone_numbers | ✅ | WAVE_C | N-A | 0.69 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 18 | Enrollment | ✅ | WAVE_C | N-A | 0.54 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 19 | data_import | ✅ | WAVE_C | N-A | 0.54 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 20 | standard_receivers | ✅ | WAVE_C | N-A | 0.84 | ❌ | 3 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 21 | positive_list | ✅ | WAVE_C | N-A | 0.48 | ❌ | 5 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 22 | product_scope | ⚠️ | WAVE_C | NOT IN BUILD_STATE | 1.00 | ✅ | 0 | UNKNOWN | UNKNOWN | IGNORED | ARCHITECT_DECISION | IGNORED 2026-04-19. Not in BUILD_STATE. Excluded from analysis pipeline. |
| 23 | address_management | ✅ | WAVE_C | N-A | 0.58 | ❌ | 3 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 24 | messaging | ✅ | WAVE_D | N-A | 0.47 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 25 | subscription | ✅ | WAVE_D | N-A | 0.58 | ❌ | 3 | UNKNOWN | UNKNOWN | N-A | NONE | CANONICAL 2026-04-19. Merged from Subscription (#26). Singular snake_case. |
| 26 | Subscription | ❌ MERGED | WAVE_D | N-A | 0.58 | ❌ | 3 | UNKNOWN | UNKNOWN | REMOVED | MERGED_2026-04-19 | MERGED into subscription (#25). Entry retained for audit trail only. |
| 27 | pipeline_crm | ✅ | WAVE_D | N-A | 0.41 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 28 | pipeline_sales | ✅ | WAVE_D | N-A | 0.41 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 29 | sms_group | ✅ | WAVE_D | N-A | 0.84 | ❌ | 3 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 30 | integrations | ✅ | WAVE_D | N-A | 0.78 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 31 | recipient_management | ✅ | WAVE_D | N-A | 0.52 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 32 | Lookup | ✅ | WAVE_D | N-A | 0.54 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 33 | Finance | ✅ | WAVE_E | N-A | 0.41 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 34 | reporting | ✅ | WAVE_E | N-A | 0.13 | ❌ | 7 | UNKNOWN | UNKNOWN | N-A | NONE | Very low score |
| 35 | Statistics | ✅ | WAVE_E | N-A | 0.35 | ❌ | 6 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 36 | Monitoring | ✅ | WAVE_E | N-A | 0.20 | ❌ | 6 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 37 | Benchmark | ✅ | WAVE_E | N-A | 0.47 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 38 | Conversation | ✅ | WAVE_E | N-A | 0.54 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 39 | Voice | ✅ | WAVE_E | N-A | 0.54 | ❌ | 4 | UNKNOWN | UNKNOWN | N-A | NONE | — |
| 40 | Resten | ❌ NO META | UNCLASSIFIED | N-A | N/T | ❌ | N/T | UNKNOWN | UNKNOWN | ARCHIVED | ARCHITECT_DECISION | ARCHIVED 2026-04-19. No meta, catchall bucket. Excluded from analysis pipeline. |

---

## SECTION 2 — WAVE STRUCTURE

### WAVE_A — FOUNDATION
*Infrastructure, auth, config, jobs, observability*

| Domain | Score | Status |
|--------|-------|--------|
| identity_access | 0.98 | DONE_LOCKED ✅ |
| Email | N/T | DONE_LOCKED ✅ |
| job_management | 0.93 | DONE_LOCKED ✅ |
| localization | 0.92 | DONE_LOCKED ✅ |
| activity_log | 0.92 | DONE_LOCKED ✅ |
| logging | 0.88 | N-A |
| system_configuration | 0.94 | DONE_LOCKED ✅ |

**Wave A progress: 6/7 DONE_LOCKED**

---

### WAVE_B — CORE_DATA
*Customer, profile, user master data*

| Domain | Score | Status |
|--------|-------|--------|
| customer_administration | 0.88 | N-A (GOVERNANCE_REVERT ⚠️) |
| customer_management | 0.88 | N-A |
| profile_management | 0.91 | READY_FOR_GATE |

**Wave B progress: 0/3 DONE_LOCKED**

---

### WAVE_C — CORE_FLOWS
*Primary business operations and delivery*

| Domain | Score | Status |
|--------|-------|--------|
| sms | 0.98 | IN_BUILD |
| eboks_integration | 0.88 | N-A |
| web_messages | 0.88 | N-A |
| standard_receivers | 0.84 | N-A |
| Delivery | 0.84 | N-A |
| phone_numbers | 0.69 | N-A |
| address_management | 0.58 | N-A |
| Enrollment | 0.54 | N-A |
| data_import | 0.54 | N-A |
| templates | 0.37 | N-A |
| Webhook | 0.37 | N-A |
| positive_list | 0.48 | N-A |
| product_scope | 1.00 | IGNORED 🚫 |

**Wave C progress: 0/13 DONE_LOCKED (1 IN_BUILD)**

---

### WAVE_D — ORCHESTRATION
*Messaging, subscriptions, pipelines, integrations*

| Domain | Score | Status |
|--------|-------|--------|
| sms_group | 0.84 | N-A |
| integrations | 0.78 | N-A |
| subscription | 0.58 | N-A (CANONICAL ✅) |
| Lookup | 0.54 | N-A |
| Conversation | — (WAVE_E candidate) | — |
| recipient_management | 0.52 | N-A |
| pipeline_crm | 0.41 | N-A |
| pipeline_sales | 0.41 | N-A |
| messaging | 0.47 | N-A |
| Subscription | — | MERGED → subscription |

**Wave D progress: 0/9 DONE_LOCKED (1 BLOCKED/DUPLICATE)**

---

### WAVE_E — REPORTING
*Analytics, finance, monitoring, statistics*

| Domain | Score | Status |
|--------|-------|--------|
| Conversation | 0.54 | N-A |
| Voice | 0.54 | N-A |
| Benchmark | 0.47 | N-A |
| Finance | 0.41 | N-A |
| Statistics | 0.35 | N-A |
| reporting | 0.13 | N-A |
| Monitoring | 0.20 | N-A |

**Wave E progress: 0/7 DONE_LOCKED**

---

## SECTION 3 — DEPENDENCY MAP

> NOTE: Dependencies derived from domain knowledge + BUILD_STATE. Marked UNKNOWN where not verified from flows.

| Domain | depends_on |
|--------|-----------|
| identity_access | NONE (foundation) |
| Email | NONE (infrastructure) |
| job_management | NONE (infrastructure) |
| logging | NONE (infrastructure) |
| localization | NONE (infrastructure) |
| system_configuration | NONE (infrastructure) |
| activity_log | identity_access |
| customer_administration | identity_access |
| customer_management | identity_access |
| profile_management | identity_access, customer_management |
| sms | identity_access, customer_administration, templates, standard_receivers, positive_list |
| templates | customer_administration |
| standard_receivers | customer_management, profile_management |
| positive_list | profile_management |
| web_messages | templates, standard_receivers |
| Delivery | sms |
| Webhook | sms |
| eboks_integration | sms, Delivery |
| Enrollment | address_management, standard_receivers |
| data_import | customer_administration, profile_management |
| address_management | UNKNOWN |
| phone_numbers | customer_administration |
| product_scope | customer_management (UNKNOWN — needs Architect decision) |
| sms_group | sms, profile_management |
| subscription | customer_administration, profile_management |
| Subscription | MERGED → subscription (2026-04-19) |
| integrations | UNKNOWN (broad coupling) |
| recipient_management | standard_receivers, Lookup |
| Lookup | address_management |
| pipeline_crm | customer_management, UNKNOWN |
| pipeline_sales | customer_management, UNKNOWN |
| messaging | sms, web_messages, Email |
| Finance | customer_management, sms |
| reporting | sms, Finance, Statistics |
| Statistics | sms, Delivery |
| Monitoring | job_management, sms |
| Benchmark | UNKNOWN |
| Conversation | sms, UNKNOWN |
| Voice | sms, phone_numbers |
| Resten | UNKNOWN |

---

## SECTION 4 — ACTIVE PIPELINE STATE

```yaml
active_domain: system_configuration
active_domain_status: READY_FOR_GATE
active_domain_note: "Next domain after governance revert. WAVE_A foundation, no deps, score=0.94."

next_domain: logging
next_domain_rationale: "WAVE_A foundation, no deps, score=0.88, quick win"

analysis_queue:
  - customer_administration # GOVERNANCE_REVERT — NEEDS_FULL_REANALYSIS. Minimal scope only: Name edit + User enable/disable.
  - logging            # 0.88 WAVE_A — N-A, quick win
  - customer_management # 0.88 WAVE_B — direct dependency for profile_management
  - profile_management  # 0.91 WAVE_B — READY_FOR_GATE but depends on customer_management
  - web_messages        # 0.88 WAVE_C — stable
  - eboks_integration   # 0.88 WAVE_C — stable

audit_queue:
  - Warnings            # Feature folder in green-ai (67 files) but not in domain registry

resolved_audit_queue:
  - product_scope       # IGNORED — not in BUILD_STATE, excluded from pipeline
  - Resten              # ARCHIVED — no meta, excluded from pipeline
  - Subscription        # MERGED into subscription (#25)

rebuild_queue: []
```

---

## SECTION 5 — BUILD PRIORITY ENGINE

### HIGH (foundation + gate_passed, no blocked deps)
| # | Domain | Score | Wave | Rationale |
|---|--------|-------|------|-----------|
| 1 | system_configuration | 0.94 | WAVE_A | Foundation, READY_FOR_GATE, no deps |
| 2 | logging | 0.88 | WAVE_A | Foundation, N-A (quick), no deps |

### MEDIUM (depends only on DONE domains)
> ⚠️ NOTE: customer_administration reverted to N-A — domains depending on it (sms, subscriptions, templates, data_import, phone_numbers) cannot promote until customer_administration reaches DONE 🔒
| # | Domain | Score | Wave | Rationale |
|---|--------|-------|------|-----------|
| 3 | customer_management | 0.88 | WAVE_B | Needed by profile_management |
| 4 | profile_management | 0.91 | WAVE_B | READY_FOR_GATE, but depends on customer_management |
| 5 | web_messages | 0.88 | WAVE_C | High score, stable |
| 6 | eboks_integration | 0.88 | WAVE_C | High score |

### LOW (missing analysis, unknown deps, or low score)
All remaining WAVE_C, WAVE_D, WAVE_E domains.

---

## SECTION 6 — RESUMABLE EXECUTION MODEL

### RESUME COMMAND: "RESUME DOMAIN FACTORY"

```
1. Load this file (GREEN_AI_DOMAIN_MASTER_PLAN.md)
2. Read active_domain from ACTIVE PIPELINE STATE section
3. Read active_domain_status

DECISION TREE:

IF active_domain_status = N-A:
   → Read domains/<active_domain>/000_meta.json
   → Run completeness check + flow validation
   → Write N-A report to temp.md
   → STOP — await Architect approval

IF active_domain_status = READY_FOR_GATE:
   → Write GATE REPORT to temp.md
   → STOP — await Architect N-B approval

IF active_domain_status = N-B_APPROVED:
   → Check green-ai for existing implementation
   → Identify gaps
   → Write gap report to temp.md
   → STOP — await Architect scope confirmation

IF active_domain_status = IN_BUILD:
   → Check build progress (files, tests, SQL)
   → Report status to temp.md

IF active_domain_status = DONE_LOCKED:
   → Move to next_domain from analysis_queue
   → Update active_domain + next_domain
   → Start N-A cycle for new active_domain

ELSE:
   → Pick first domain from analysis_queue
   → Set as active_domain
   → Start N-A cycle
```

---

## SECTION 7 — DOMAIN LOOP SPEC (execution rules)

For each active_domain in N-A state:

1. **Existence check** → confirm path `analysis-tool/domains/<domain>/`
2. **Completeness check** → read 000_meta.json → record score, gaps_count, status
3. **Behaviors check** → read 020_behaviors.json → count real behaviors vs garbage
4. **Flows validation** → read 030_flows.json → for each flow: verify file+method+line → mark INVALID if missing
5. **Rules validation** → read 070_rules.json → verify each rule traces to source code
6. **Distillation check** → read 099_distillation.md if exists → use as ground truth

Update registry:
- completeness_score
- unknown_count (garbage entries)
- gate_passed (proxy: score ≥ 0.90 until sub-scores tracked)
- flow_verification_ok
- business_rules_code_verified
- current_status

STOP — do NOT write green-ai code until N-B_APPROVED.

---

## SECTION 8 — AUDIT / REBUILD SYSTEM

### Mismatch detection rules

IF green-ai implementation differs from distillation → REBUILD_CANDIDATE  
IF green-ai missing flows that Layer 1 defines → REBUILD_CANDIDATE  
IF DB schema missing columns that distillation requires → REBUILD_CANDIDATE  
IF Layer 1 behaviors = [] AND distillation not verified from UI → AUDIT_REQUIRED  

### Current REBUILD_CANDIDATES
None. customer_administration was GOVERNANCE_REVERTED to N-A (not a rebuild — domain never reached DONE 🔒).

### Current AUDIT_REQUIRED
- Warnings (feature folder `green-ai/Features/Warnings`, 67 files, RIG PASS — NOT in domain registry)

### Resolved (2026-04-19)
- product_scope → IGNORED (not in BUILD_STATE, excluded from pipeline)
- Resten → ARCHIVED (no meta, catchall bucket, excluded from pipeline)
- Subscription → MERGED into subscription (#25, canonical, singular snake_case)

---

## SECTION 9 — GLOBAL METRICS

```
total_domains:           40  (registry) / 38 active (product_scope IGNORED + Resten ARCHIVED)
domains_done_locked:      5  (Email, identity_access, localization, job_management, activity_log)
domains_in_build:         1  (sms)
domains_nb_approved:      0  (none — customer_administration reverted to N-A 2026-04-19)
domains_ready_for_gate:   2  (system_configuration, profile_management — product_scope IGNORED)
domains_in_na:           28  (includes customer_administration GOVERNANCE_REVERT)
domains_blocked:          0  (Subscription MERGED into subscription 2026-04-19)
domains_audit_required:   1  (Warnings — feature folder exists but not in registry)
domains_ignored:          1  (product_scope)
domains_archived:         1  (Resten)
domains_merged:           1  (Subscription → subscription)
domains_no_meta:          0  (Resten archived)
score_gte_090:            9  (identity_access, Email, job_management, localization, activity_log, system_configuration, profile_management, sms, product_scope)
score_080_089:            4  (logging, customer_administration, customer_management, eboks_integration, web_messages)
score_lt_050:            11  (messaging, Benchmark, positive_list, templates, Webhook, pipeline_crm, pipeline_sales, Finance, Statistics, reporting, Monitoring)

duplicates_detected:      0  (Subscription merged → resolved)
naming_conflicts:         4  (Delivery, Email, Enrollment, Lookup, Benchmark, Finance, Voice, Statistics, Conversation — PascalCase vs snake_case)
```

*product_scope READY_FOR_GATE is flagged — requires HUMAN_DECISION before proceeding.

---

## SECTION 10 — NAMING CONFLICTS (PascalCase vs snake_case)

These domains use PascalCase folder names. canonical_name_confirmed=false until Architect confirms:

| Folder name | Expected canonical | Risk |
|-------------|-------------------|------|
| Delivery | delivery | LOW — likely intentional |
| Email | email | LOW — already DONE_LOCKED |
| Enrollment | enrollment | LOW |
| Lookup | lookup | LOW |
| Benchmark | benchmark | LOW |
| Finance | finance | LOW |
| Voice | voice | LOW |
| Statistics | statistics | LOW |
| Conversation | conversation | LOW |
| Subscription | subscription | HIGH — DUPLICATE with subscriptions |

---

---

## SECTION 11 — RIG SCAN PROTOCOL (Rebuild Integrity Gate)

> **RESUME TRIGGER:** "RUN RIG SCAN `<domain>`" → run command below → update table → write report to temp.md  
> **PURPOSE:** Verify no green-ai code is a structural/behavioral copy of sms-service  
> **TOOL:** `analysis_tool.integrity.run_rig` (heuristic + optional LLM layer)  
> **RULE:** RIG must PASS before any domain is promoted to DONE 🔒  
> **SCOPE:** .cs + .sql only. .razor / .ts / tests/ excluded (Blazor vs Angular = no frontend risk)

### Gate thresholds (Architect-defined, from checker.py)
| Metric | FAIL threshold |
|--------|---------------|
| behavioral_similarity | > 0.75 |
| domain_similarity (GreenAI vocabulary ratio) | < 0.50 (when behavioral > 0.75) |
| Combined gate | behavioral > 0.75 AND domain < 0.50 → GATE FAIL |

### ⚠️ KNOWN LIMITATION (verified 2026-04-19)

Heuristic mode (`--no-llm`) bruger **filnavn-similarity** til at finde legacy-match.  
**Resultat:** En bevidst kopi med et andet filnavn FANGES IKKE af heuristic-mode.

| Scenarie | Heuristic (--no-llm) | LLM-mode |
|----------|----------------------|----------|
| Fil navngivet identisk/ens som legacy | ✅ Fanges | ✅ Fanges |
| Kopieret indhold med NYT filnavn | ❌ Fanges IKKE | ✅ Fanges |

**Proof:** 2026-04-19 test — 3 filer med kopieret sms-service kode (structural/behavioral/domain) planteret i CustomerAdmin → alle scorede 0.00 → LOW → PASS. Heuristic FEJLEDE. LLM-mode påkrævet for indholds-baseret check.

### 🟢 Officiel LLM-metode: VS Code Copilot Chat

**Beslutning (Architect 2026-04-19):** VS Code Copilot Chat er den officielle LLM for RIG.
Ingen ekstern API. Ingen TypeScript. Ingen Ollama.

| Mode | Hvornår | Kommando |
|------|---------|----------|
| Heuristik | Altid (baseline) | `run_rig ... (ingen flag)` |
| Copilot LLM | HIGH/MEDIUM filer, Wave-checkpoints, DONE 🔒 promotion | `run_rig ... --copilot-batch batch.md` |
| Override aktiv | Nær llm_scores_<domain>.json eksisterer | Automatisk — ingen flag nødvendig |

**Fuld LLM-workflow:**
```
1. Kør heuristik:
   python -m analysis_tool.integrity.run_rig \
       --greenai <mappe> --legacy <mappe> --copilot-batch analysis/integrity/batch.md

2. Åbn batch.md → indsæt i VS Code Copilot Chat

3. Copilot returnerer JSON per fil-par. Gem som:
   analysis/integrity/llm_scores_<domain>.json
   (domain = lowercase af greenai folder name, fx CustomerAdmin → customeradmin)

4. Kør RIG igen — override læses automatisk:
   python -m analysis_tool.integrity.run_rig \
       --greenai <mappe> --legacy <mappe> --output domain_scan_<domain>.json
```

**JSON format (llm_scores_<domain>.json):**
```json
{
  "GetUsersEndpoint.cs": {
    "structural_similarity": 0.40,
    "behavioral_similarity": 0.80,
    "domain_similarity": 0.40,
    "flags": ["static Register(IEndpointRouteBuilder) matches legacy KrrEndpoints pattern"],
    "recommendations": ["Rename Register → unique method, use vertical-slice pattern"]
  }
}
```

---

### Run command (heuristic — fast, no LLM tokens)
```powershell
# Single domain
cd C:\Udvikling\analysis-tool
python -m analysis_tool.integrity.run_rig `
    --greenai "c:/Udvikling/green-ai/src/GreenAi.Api/Features/<FeatureFolder>" `
    --legacy  "c:/Udvikling/sms-service" `
    --no-llm `
    --output  "analysis/integrity/domain_scan_<domain>.json"

# With LLM (deeper — use at Wave checkpoint)
python -m analysis_tool.integrity.run_rig `
    --greenai "c:/Udvikling/green-ai/src/GreenAi.Api/Features/<FeatureFolder>" `
    --legacy  "c:/Udvikling/sms-service" `
    --output  "analysis/integrity/domain_scan_<domain>.json"
```

### Resume protocol
```
"RUN RIG SCAN <domain>"
  1. Map domain_name → FeatureFolder (see table below)
  2. Run heuristic scan (--no-llm)
  3. Parse output JSON → gate_status, failed_files, HIGH/MEDIUM/LOW counts
  4. Update RIG STATUS TABLE (below)
  5. If gate_status = FAIL → write RIG FAIL REPORT to temp.md with flags + recommendations
  6. If gate_status = PASS → update table with ✅ PASS + date + medium_risk count
  7. STOP — do not proceed to DONE_LOCKED until RIG PASS confirmed
```

### RIG STATUS TABLE

> Last full scan: **2026-04-18** (all existing feature folders)  
> Source: `analysis-tool/analysis/integrity/domain_scan_*.json`

| Domain (canonical) | FeatureFolder | green-ai files | RIG date | Gate | HIGH | MEDIUM | RIG_json |
|-------------------|---------------|---------------|----------|------|------|--------|---------|
| identity_access | Auth + Identity + AdminLight + UserSelfService | 43+6+24+17=90 | 2026-04-18 | ✅ PASS | 0 | 6+1+3+3=13 | domain_scan_auth/identity/adminlight/userselfservice.json |
| Email | Email | 43 | 2026-04-18 | ✅ PASS | 0 | 14 | domain_scan_email.json |
| job_management | JobManagement | 18 | 2026-04-18 | ✅ PASS | 0 | 6 | domain_scan_jobmanagement.json |
| localization | Localization | 7 | 2026-04-18 | ✅ PASS | 0 | 1 | domain_scan_localization.json |
| activity_log | ActivityLog | 15 | 2026-04-18 | ✅ PASS | 0 | 5 | domain_scan_activitylog.json |
| sms | Sms | 103 | 2026-04-18 | ✅ PASS | 0 | 18 | domain_scan_sms.json |
| customer_administration | CustomerAdmin | 9 | 2026-04-18 | ✅ PASS | 0 | 2 | domain_scan_customeradmin.json |
| system_configuration | System | 8 | 2026-04-18 | ✅ PASS | 0 | 0 | domain_scan_system.json |
| templates | Templates | 21 | 2026-04-18 | ✅ PASS | 0 | 5 | domain_scan_templates.json |
| Lookup | Lookup | 11 | 2026-04-18 | ✅ PASS | 0 | 7 | domain_scan_lookup.json |
| Warnings⚠️ | Warnings | 67 | 2026-04-18 | ✅ PASS | 0 | 6 | domain_scan_warnings.json |
| (infrastructure) | Api | 14 | 2026-04-18 | ✅ PASS | 0 | 0 | domain_scan_api.json |
| (infrastructure) | Operations | 17 | 2026-04-18 | ✅ PASS | 0 | 3 | domain_scan_operations.json |
| logging | — | NOT BUILT YET | — | ⬜ N/A | — | — | — |
| customer_management | — | NOT BUILT YET | — | ⬜ N/A | — | — | — |
| profile_management | — | NOT BUILT YET | — | ⬜ N/A | — | — | — |
| web_messages | — | NOT BUILT YET | — | ⬜ N/A | — | — | — |
| *all other domains* | — | NOT BUILT YET | — | ⬜ N/A | — | — | — |

> ⚠️ **Warnings** — Feature folder exists in green-ai (`Features/Warnings`, 67 files, PASS) but domain is NOT in the 40-domain registry. Requires AUDIT_REQUIRED classification.  
> Add to AUDIT_REQUIRED list alongside product_scope, Resten, Subscription.

### RIG scan history (full baseline)
| Scan run | Date | Scope | Gate | Notes |
|----------|------|-------|------|-------|
| full_baseline_post_fix | 2026-04-18 | All 16 feature folders | ✅ PASS | 0 HIGH, varied MEDIUM |
| warnings_rig_v2 | 2026-04-18 | Warnings only | ✅ PASS | Re-run after fix |

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-04-19 | v1.0 created — initial DOMAIN FACTORY initialization |
| 2026-04-19 | v1.1 — SECTION 11 RIG SCAN PROTOCOL added. Per-domain status table from 2026-04-18 baseline. Warnings domain flagged as unregistered. |
| 2026-04-19 | v1.2 — GOVERNANCE_REVERT: customer_administration reset to N-A. N-B was invalid (behaviors=0, flows=0, rules=0). Active domain → system_configuration. |
| 2026-04-19 | v1.3 — Domain normalization: product_scope→IGNORED, Resten→ARCHIVED, Subscription→MERGED into subscription. RIG: Copilot Chat as official LLM + llm_scores override. GetUsersEndpoint.cs gate violation fixed (Map→Register). customer_administration minimal scope note added. |
