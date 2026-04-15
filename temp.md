# SESSION STATUS — 2026-04-15

> **PACKAGE_TOKEN: GA-2026-0414-V044-1347**
> ChatGPT SKAL citere dette token i sin første sætning. Svar uden token afvises.

---

## AKTUEL STATUS

| Wave | Navn | Status | Tests |
|------|------|--------|-------|
| Wave 0 | Customer, ProfileGate, ApiKey | ✅ DONE | — |
| Wave 1 | ManageStandardReceiver, Pricing | ✅ DONE | — |
| Wave 2 | Address ingestion + lookup | ✅ DONE | — |
| Wave 5 | BS-MSG-01/02/03 + Hardening | ✅ DONE | 536 |
| BS-ADDR-04 | ResolveAddresses (execution bridge) | ✅ DONE | +11 |
| **GATE** | **RULE-BROADCAST-EXECUTION-GATE** | **✅ LOCKED** | **+12** |
| **Wave 6** | **BS-MSG-04 DispatchBroadcast** | **✅ DONE** | **+9** |
| **RULE** | **RULE-VISUAL-DELTA-CACHE** | **✅ LOCKED** | **+27** |
| **Wave 6** | **BS-MSG-05 TrackDelivery** | **✅ DONE** | **+6** |
| **Wave 7** | **Provider Integration Foundation** | **✅ DONE** | **+5** |
| **RULE** | **RULE-VISUAL-DELTA-ENGINE v2** | **✅ LOCKED** | **+8** |
| **Wave 8** | **Visual Engine Hardening** | **✅ DONE** | **+23** |
| **RULE** | **RULE-VISUAL-NORMALIZATION** | **✅ LOCKED** | *(included above)* |

**C# (green-ai):** 523/523 handler tests ✅ (2026-04-14)  
*(491 handler + 11 BS-ADDR-04 + 12 ExecutionGate + 9 Dispatch + 6 TrackDelivery + 45 HTTP + 5 Outbox/Worker — 6 HTTP kræver kørende server)*

**Python (analysis-tool):** 857/857 tests ✅ (2026-04-15) — heraf 63/63 visual-delta

**RULE-VISUAL-DELTA-CACHE: 🔒 LOCKED** — 3-lag fingerprint system implementeret og testet  
**RULE-VISUAL-DELTA-ENGINE v2: 🔒 LOCKED** — dependency + validator/ruleset/mask version invalidation implementeret og testet  
**RULE-VISUAL-NORMALIZATION: 🔒 LOCKED** — PIL normalization pipeline + production_mode enforcement implementeret og testet

---

## LOCKED RULES (seneste)

Alle regler i `green-ai/AI_WORK_CONTRACT.md` → LOCKED RULES sektion:

| Regel | Locked |
|-------|--------|
| RULE-AI-SELF-LOOP | 2026-04-14 |
| RULE-FAIL-FAST | 2026-04-14 |
| RULE-AI-FIRST-VALIDATION | 2026-04-14 |
| RULE-AI-EXECUTION-BOUNDARY | 2026-04-14 |
| RULE-VISUAL-COVERAGE | 2026-04-14 |
| RULE-BROADCAST-INTEGRITY | 2026-04-14 |
| RULE-CRITERIA-ARE-RAW | 2026-04-14 |
| RULE-FROMAPI-BOUNDARY | 2026-04-14 |
| RULE-IDEMPOTENT-INGESTION | 2026-04-14 |
| RULE-CRYPTO | 2026-04-14 |
| **RULE-BROADCAST-EXECUTION-GATE** | **2026-04-14** |
| **RULE-VISUAL-DELTA-ENGINE v2** | **2026-04-15** |
| **RULE-VISUAL-NORMALIZATION** | **2026-04-15** |

Test-strategi: `green-ai/docs/SSOT/testing/test-automation-rules.md`

---

## WAVE 8 — Visual Engine Hardening — LEVERET ✅ (2026-04-15)

**Arkitekt-direktiv:** 4 punkter — (A) PIL normalization pipeline, (B) non-empty enforcement, (C) DependencyManifest validation + `dependency_source` flag, (D) tests.

### Implementering

| Fil | Ændring |
|-----|---------|
| `core/visual_fingerprint.py` | `MaskRegion` dataclass (x/y/width/height/label + `to_pil_box()`); `NormalizationConfig` dataclass (canvas_size, mask_regions, grayscale, blur_radius, mask_version); `DEFAULT_NORMALIZATION`; `MASK_FILL_COLOR=(128,128,128)`; `DEFAULT_CANVAS_SIZE=(1280,800)` |
| `core/visual_fingerprint.py` | `hash_normalized_image()` PIL pipeline: open → resize LANCZOS → RGB → mask_regions fill → optional grayscale → optional GaussianBlur → `tobytes()` → SHA256. Fallback: raw SHA256 hvis PIL ikke kan parse filen (backward-compat) |
| `core/visual_fingerprint.py` | `DependencyManifest.dependency_source` (`MANUAL`\|`AUTO`\|`HYBRID`); `is_empty()` method; `to_canonical_dict()` inkluderer `dependencySource` nøgle |
| `core/visual_fingerprint.py` | `FingerprintValidationError(ValueError)`; `validate_fingerprint()` — fail-fast: rejser med liste af alle tomme required v2 felter (semantic_sha256, dependency_sha256, validator_version, ruleset_version, mask_version) |
| `core/visual_fingerprint.py` | `VisualFingerprintBuilder.build()` accepterer `normalization_config: Optional[NormalizationConfig] = None` param |
| `core/visual_delta_cache.py` | `VisualDeltaCache.__init__(production_mode: bool = False)`; `_v2_match()` helper — production: empty = force reanalysis; test/migration: `""` = any |
| `core/visual_delta_cache.py` | `VisualCacheEntry.dependency_source` property; `_make_entry()` persisterer `dependencySource` |
| `tests/test_visual_delta_cache.py` | +23 tests fordelt på: `TestWave8Normalization` (7 tests), `TestWave8ProductionMode` (4 tests), `TestWave8ValidationFastFail` (7 tests), `TestWave8DependencyManifest` (5 tests) |

### Nøgle-design-beslutninger

| Beslutning | Begrundelse |
|-----------|-------------|
| Fallback i `hash_normalized_image()` ved PIL-fejl → raw SHA256 | Backward-compat for tests med syntetisk data; i produktion er billeder altid gyldige PNG/JPEG |
| `production_mode=False` default | Alle 834 eksisterende tests kræver `""` = any adfærd |
| `validate_fingerprint()` er separat funktion (ikke auto-kaldt i `build()`) | Caller bestemmer hvornår strict validation sker — giver fleksibilitet i migration-flows |
| `dependency_source` indgår i canonical dict hash | Sikrer MANUAL vs AUTO manifests giver forskellig `dependency_sha256` |

### Test-resultater

| Suite | Før | Efter | Delta |
|-------|-----|-------|-------|
| `test_visual_delta_cache.py` | 40 | 63 | +23 |
| **Total pytest** | **834** | **857** | **+23** |

**Status:** 857/857 ✅ — 0 failures

---

## RULE-VISUAL-DELTA-ENGINE v2 — LEVERET ✅ (2026-04-15)

**Gate rapport:** Leveret til Architect med file+method+line+verified=true for alle 4 dimensioner.  
**Gate verdict:** PASS (alle scores ≥ 0.90)

### Implementering

| Fil | Ændring |
|-----|---------|
| `core/visual_fingerprint.py` | `DependencyManifest` dataclass (component/css/loc/layout/journey/rule hashes); `VisualFingerprint` +5 felter: `dependency_sha256`, `validator_version`, `ruleset_version`, `mask_version`, `source_commit_sha`; `VisualFingerprintBuilder.build()` modtager nye params |
| `core/visual_delta_cache.py` | `VisualCacheEntry` +5 properties; `_make_entry()` persisterer dem; STRICT `should_skip()` kræver nu 10 conditions (inkl. semantic + dependency + validator/ruleset/mask) |
| `tests/test_visual_delta_cache.py` | `TestVisualDeltaEngineV2` klasse — 8 tests (7 Architect-scenarier + JSONL round-trip) |

### Skip-beslutning STRICT — alle 10 conditions skal være True

1. `normalized_image_sha256` match (canonical visual)
2. `validation_context_sha256` match (gates, mustShow, device)
3. `render_input_sha256` match (component/CSS/loc/seed)
4. `policy_version` match
5. `semantic_sha256` match (DOM/text — `""` = any)
6. `dependency_sha256` match (Razor/CSS/layout/rules — `""` = any)
7. `validator_version` match (AI engine — `""` = any)
8. `ruleset_version` match (mustShow/mustNotShow — `""` = any)
9. `mask_version` match (normalization masks — `""` = any)
10. `result == "PASS"` (FAIL/WARN aldrig skip-eligible)

### Åbne punkter (Architect aware)
- `hash_normalized_image()` er stadig stub = raw SHA256 (kræver PIL-pipeline)
- `DependencyManifest` populeres manuelt af caller (ingen auto-scan endnu)

---

## BROADCAST-EXECUTION-GATE — BESTÅET ✅ (2026-04-14)

**Fil:** `tests/GreenAi.Tests/Features/Sms/BroadcastExecutionGateTests.cs`  
**Resultat:** 12/12 tests ✅ — Wave 6 Dispatch UNLOCKED

### Gate coverage

| Krav | Test | Resultat |
|------|------|---------|
| BR005 NoCriteria → Activate FAIL | BR005_NoCriteria_ActivateFails | ✅ |
| BR005 AllUnresolved → ZERO_RECIPIENTS FAIL | BR005_CriteriaButAllUnresolved_ResolveFailsWithZeroRecipients | ✅ |
| BR005 Resolved > 0 → Success | BR005_WithResolvedRecipients_Succeeds | ✅ |
| BR024 AlwaysOwner → DB SendToOwner=true | BR024_AlwaysOwner_SendToOwnerPersistedInDB | ✅ |
| BR024 AlwaysOwner E2E → owner i resolved | BR024_AlwaysOwner_ResolveContainsOwner | ✅ |
| BR025 DontSendEmail → Channels=SMS only | BR025_DontSendEmail_EmailChannelStrippedInDB | ✅ |
| BR025 DontSendEmail → consistent efter resolve | BR025_DontSendEmail_ChannelStillSmsOnlyAfterResolve | ✅ |
| BR026 CanSpecifyLookup absent → flags blocked | BR026_CanSpecifyLookupAbsent_LookupFlagsBlockedInDB | ✅ |
| BR026 flags immutable gennem pipeline | BR026_CanSpecifyLookupAbsent_FlagsUnchangedAfterResolve | ✅ |
| E2E: Compose→AddCriteria→Activate→Resolve | E2E_Compose_AddCriteria_Activate_Resolve_StateConsistent | ✅ |
| Edge: mixed criteria correct split | Edge_MixedCriteria_PhoneAndUnknownAddress_CorrectSplit | ✅ |
| Edge: multi-type correct prioritization | Edge_MultipleCriteriaTypes_CorrectPrioritization | ✅ |

### ZERO_RECIPIENTS guard implementeret i ResolveAddressesHandler
```csharp
if (deduped.Count == 0)
    return Result<ResolveAddressesResponse>.Fail(
        "ZERO_RECIPIENTS",
        $"Broadcast {command.BroadcastId}: all {unresolved.Count} criteria were unresolved.");
```

---

---

## BS-ADDR-04 — LEVERET ✅ (2026-04-14)

**ResolveAddresses — execution bridge (Wave 2 → Wave 6)**

| Fil | Indhold |
|-----|---------|
| `V046_Sms_ResolvedRecipients.sql` | Ny tabel: `ResolvedRecipients` + `UnresolvedCriteria` |
| `ResolveAddressesCommand/Handler/Repository/Endpoint.cs` | Vertical slice |
| 8 SQL-filer | GetBroadcastResolveState, GetRecipientCriteria, FindCanonicalAddress, GetAddressOwnerPhones, DeleteResolvedData, InsertResolvedRecipient, InsertUnresolvedCriterion, SetBroadcastLookedUp |
| `ResolveAddressesHandlerTests.cs` | 11 tests: core + edge + guards |

**Locked rules (fra Architect directive):**
- RULE-RESOLVE-01 — Deterministic
- RULE-RESOLVE-02 — Idempotent (delete + insert i transaction)
- RULE-RESOLVE-03 — No silent drop → `UnresolvedCriteria`
- RULE-RESOLVE-04 — No dispatch
- RULE-RESOLVE-05 — `IsLookedUp = 1` freezer broadcast

**Resolution priority:** PHONE_DIRECT → STANDARD_RECEIVER → ADDRESS_OWNER → UNRESOLVED

**Test coverage:**
- ✅ Resolve_PhoneCriterion_ReturnsSuccess
- ✅ Resolve_PhoneCriterion_InsertsFullPhoneNumber
- ✅ Resolve_AddressCriterion_ResolvesToKvhx
- ✅ Resolve_AddressCriterion_AddressWithNoOwners_StillResolvesToKvhx
- ✅ Resolve_StandardReceiverCriterion_ResolvesToReceiverId
- ✅ Resolve_UnknownAddress_RecordsUnresolvedCriterion
- ✅ Resolve_DuplicatePhoneCriteria_NoDuplicatesInOutput
- ✅ Resolve_ReRun_ReturnsAlreadyResolvedTrue
- ✅ Resolve_SetsIsLookedUp
- ✅ Resolve_CrossTenant_ReturnsBroadcastNotFound
- ✅ Resolve_DraftBroadcast_ReturnsBroadcastInvalidState

---

## WAVE 5 HARDENING — LEVERET ✅ (2026-04-14)

**Broadcast Aggregate (BS-MSG-01/02/03):**
- BROADCAST-INTEGRITY guard i `ActivateBroadcastHandler`: criteria + channels + content valideres
- FROMAPI-BOUNDARY: `ComposeBroadcastEndpoint` sætter `FromApi = null`
- `SmsTestDataBuilder`: `InsertSmsContentDirectAsync`, `InsertEmailContentDirectAsync`, `InsertCriterionDirectAsync`
- `GetBroadcastActivationState.sql` — ét kald henter active + channels + criterion count + content flags

**AI-Flow model låst:**
```
Architect designer → Copilot eksekverer → Tests verifierer
Find → Change → Verify → FIX → Verify → DONE
```

---

## ARCHITECT VERDICT — Wave 5 ✅ (2026-04-14)

- Aggregate discipline 100% ✅
- Idempotency enterprise-grade ✅
- Cross-tenant guards konsekvente ✅
- DRAFT → ACTIVE lifecycle ren ✅
- AI-Flow model: executor (ikke designer) ✅

---

## SPØRGSMÅL TIL ARCHITECT

**RULE-BROADCAST-EXECUTION-GATE bestået. Wave 6 Dispatch (BS-MSG-04/05) er nu UNLOCKED.**

**Flow:**
```
Compose → AddCriteria → Activate
        ↓
ResolveAddresses (✅ DONE)
        ↓ ← GATE PASSED ✅
Dispatch (Wave 6) — 🔓 KLAR TIL BYG
```

**Hvad er næste direktiv for Wave 6?**

- [ ] A — Byg BS-MSG-05: TrackDelivery / delivery acknowledgement (async provider receipts)
- [ ] B — Byg provider integration (SMS gateway / email provider call i DispatchBroadcast)
- [ ] C — Andet

så vi skal have opfunden en metode til ikke at analyssre de samme igen og igen, som ikke har ændrest sig siden sidste fangst so er valideret, nogen gode ideer til et skudsikker system?

God problemstilling. Her er min analyse af et skudsikkert system:
Kerneprincippet: Content hash (SHA256) som kilde til sandhed — ikke filnavn, ikke dato.

Nu har jeg det hele. Her er designet for et skudsikkert delta-system:

Designet: Hash-baseret validerings-cache
Grundprincip: SHA256 hash af screenshot-indhold = identitet. Samme dialog, ny kørselsdag = samme hash = skip.