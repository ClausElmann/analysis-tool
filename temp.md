PACKAGE_TOKEN: GA-2026-0419-V077-1038

---

> **PACKAGE_TOKEN: GA-2026-0419-V077-1038**
> ChatGPT SKAL citere dette token i sin første sætning som bevis på at den har læst denne ZIP.
> Svar der IKKE starter med token-citering afvises.

## §PIPELINE GOVERNANCE

```
N-A → GATE → N-B BUILD → RIG SCAN → Architect review → DONE 🔒
```

DONE 🔒 kræver: Build ✅ + RIG (0 HIGH) ✅ + Architect GO ✅

### ENFORCEMENT — MANDATORY (NO BYPASS)

1. **BUILD** — Dokumentér: 0 errors, 0 warnings
2. **RIG SCAN** — Kør `python -m analysis_tool.integrity.run_rig ...` — output SKAL i temp.md (files scanned, HIGH, MEDIUM, gate_failed)
3. **VALIDATION** — HIGH > 0 → STOP | gate_failed > 0 → STOP
4. **HOUSEKEEPING** — Slet gamle RIG scans for samme domain. temp.md MAX 150 linjer. Fjern: gamle N-A, gamle audit logs, dubletter.
5. **RESULT** — Alt OK → `READY FOR ARCHITECT REVIEW — RIG PASS` | Fejl → `BLOCKED — RIG FAILURE`

**FORBUDT:** Skrive "RIG PASS" uden at have kørt RIG. Springe housekeeping over.
**STOP CONDITION:** Hvis RIG ikke kan køres → STOP og rapportér.

---

## COPILOT → ARCHITECT — profile_management N-A DONE
**Dato:** 2026-04-20 | **Layer 0:** ProfileController.cs + ProfileService.cs + Profile.cs + ProfileType.cs + ProfileRoleMapping.cs

### ENTITIES (5, code-verified)

| Entity | Type | Source |
|--------|------|--------|
| Profile | aggregate_root | Profile.cs:10 — CustomerId INT FK → Customers.Id |
| ProfileType | enum_lookup | ProfileType.cs:5 — Vand=2, Spildevand=3, Fjernvarme=4, El=5, Renovation=6, Bredbånd=8 |
| ProfileRoleMapping | join_entity | ProfileRoleMapping.cs:6 — (ProfileId, ProfileRoleId) — scoped via Profile.CustomerId |
| ProfileUserMapping | join_entity | ProfileService.cs:43 — (ProfileId, UserId) — access gate |
| ProfileStorageFile | child_entity | ProfileController.cs:218 — blob file per profile |

### BEHAVIORS (5, validated from existing 020_behaviors.json)

| Behavior | Verified |
|----------|----------|
| GetProfilesForUser | ✅ ProfileService.cs:100 — GetProfilesbyUserId |
| CanUserAccessProfile | ✅ ProfileService.cs:49 — ProfileUserMapping != null |
| InsertProfile | ✅ ProfileService.cs:203 — ValidateProfile → CreateProfile |
| SetActiveProfile | ✅ ProfileController.cs:96 — access check → _workContext.CurrentProfile |
| UpdateProfile | ✅ ProfileController.cs:396 — role check → ValidateProfile → UpdateProfile |

### FLOWS (validated — still correct)

| Flow | Steps | Verified |
|------|-------|----------|
| ProfileContextSwitchFlow | 7 steps — CanUserAccessProfile → SetActiveProfile → JWT propagation | ✅ |
| ProfileCreationFlow | 6 steps — validate → InsertProfile → RoleGroup apply | ✅ |
| ProfileRoleGateFlow | 4 steps — DoesProfileHaveRole → 403 | ✅ |

### RULES (8, code-verified)

| ID | Rule | Source |
|----|------|--------|
| RULE_001 | CanUserAccessProfile: ProfileUserMapping row must exist | ProfileService.cs:49 |
| RULE_002 | UpdateProfile: SuperAdmin OR CustomerSetup OR ManageProfiles required | ProfileController.cs:401 |
| RULE_003 | Cross-customer edit: SuperAdmin only | ProfileController.cs:411 |
| RULE_004 | SMSSendAs.Truncate(100), EmailSendAs.Truncate(200) before every save | ProfileService.cs:193 |
| RULE_005 | File upload max 15 MB (sizeKb >= 15360 → BadRequest) | ProfileController.cs:229 |
| RULE_006 | File type validation: FileTypeIdFromExtension = 0 → BadRequest | ProfileController.cs:225 |
| RULE_007 | DateLastUpdatedUtc = DateTime.UtcNow on every UpdateProfile | ProfileService.cs:237 |
| RULE_008 | File access: SuperAdmin OR CanUserAccessProfile before download/delete | ProfileController.cs:168 |

### FILES UPDATED
- 010_entities.json: 5 entities (rewritten fra garbage class-navne)
- 070_rules.json: 8 rules (rewritten fra garbage)
- 000_meta.json: status=gate_ready, score=0.93, iteration=30

**VERDICT: ✅ READY_FOR_GATE**

---

## §DOMAIN FACTORY STATE

| Domain | State | Score |
|--------|-------|-------|
| system_configuration | DONE_LOCKED | 0.94 |
| customer_management | **BUILD ✅ RIG ✅ — Afventer Architect** | 0.91 |
| profile_management | **READY_FOR_GATE** | 0.93 |
| customer_administration | N-A (GOVERNANCE_REVERT) | 0.88 |
| sms | IN_BUILD | -- |

DONE 🔒: Email, identity_access, localization, job_management, activity_log, system_configuration
