# architectural-decisions.md — CODE-VERIFIED ARCHITECTURAL DECISIONS

**Source:** Wave 5 + Wave 5-A (extracted from temp_history/temp_2026-04-12_wave6-wave7.md, 2026-04-12)  
**Status:** APPROVED — closed decisions, not open questions  
**Authority:** BINDING for green-ai implementation  
**Evidence:** All decisions backed by direct code reads in sms-service  
**Governance:** [ai-safe-rules.md](ai-safe-rules.md) — BINDING

---

## LOCKED DECISIONS (D1–D5 + Correction)

### D1 — Pattern A: `ClaimForDispatch()` ownership protocol

**Decision:** DeliveryTargets are owned by Targeting Engine at creation (`ReadyForDispatch`). Dispatch Service claims via a named atomic API — never by direct write.

**Evidence:** Design + Red Line analysis  
**Contract reference:** [service-contracts.md → CONTRACT 2 + LOCK 1](service-contracts.md)

```
Targeting Engine:   creates DeliveryTargets, owns ReadyForDispatch state
Dispatch Service:   calls ClaimForDispatch(deliveryTargetId) → ClaimResult
                    ONLY legal entry into dispatch lifecycle
                    NO direct read-modify-write on DeliveryTargets rows
```

**Why this matters:** Prevents regression to ROWLOCK SQL patterns, hidden race conditions, multi-claim bugs. `ClaimForDispatch` is not just a method — it is a service boundary.

---

### D2 — 1881 = real-time HTTP + 28-day DB cache. KRR = separate service.

**Decision:** Norway 1881 phone lookup is a real-time HTTP call to `api1881.no`, backed by a 28-day DB cache. KRR (Kontakt- og Reservasjonsregisteret) is a completely separate external dependency.

**Evidence source:** `NorwegianPhoneNumberService.cs`, `PhoneNumberRepository.cs`

```
1881:
  Cache table:  PhoneNumberCachedLookupResults
  Cache key:    (Source=Api1881, Kvhx)
  Cache TTL:    28 days from DateCachedUtc
  On cache hit:  no network call
  On cache miss: real-time HTTP to api1881.no (non-deterministic, may fail)
  Invalidation:  none — TTL only

KRR:
  Separate external API
  Separate lookup trigger conditions
  NOT part of 1881 cache
```

**Contract reference:** [service-contracts.md → CONTRACT 5](service-contracts.md)  
**Non-determinism declared on:** `TelecommunicationContact.CacheStatus` field

---

### D3 — CriticalAddresses = targeting filter. AddressVirtualMarkings = address data quality.

**Decision:** These are two distinct concepts. `CriticalAddresses` is a customer-scoped targeting filter (which addresses to include). `AddressVirtualMarkings` is address data quality (which addresses are real vs. virtual). No new service boundary needed for either — injectable filter predicates.

**Evidence source:** `ICriticalAddressService.cs`, `AddressRepository.cs`

```
CriticalAddresses:
  Scope: per-customer
  Role: targeting filter — "only send to these addresses"
  Applied by: Targeting Engine (AddressRestriction.CriticalAddressesOnly)
  Maintained by: Address Service batch jobs

AddressVirtualMarkings:
  Scope: per-address (Kvhx-keyed)
  Role: data quality flag — "this address is virtual/non-physical"
  Surface: explicit IsVirtual: bool field on AddressRecord
  NOT a hidden SQL filter (was hidden in legacy — corrected in green-ai)
```

**Contract reference:** [service-contracts.md → CONTRACT 4](service-contracts.md), `AddressRecord.IsVirtual`

---

### D4 — StandardReceiver = address bypass path. `Kvhx = null` invariant.

**Decision:** StandardReceiver (fixed recipient) is a completely separate path from geographic targeting. It MUST NOT be folded into the geographic pipeline. `Kvhx` is always `null` on fixed-recipient DeliveryTargets — this is a contract invariant, not a default.

**Evidence source:** `SplitStandardReceiverCommandProcessor.cs`

```
Fixed Recipient path:
  Input:    StandardReceiverId / StandardReceiverGroupId
  Output:   DeliveryTarget with Kvhx=null, sourceType=FixedRecipient
  Uses:     NO Address Service
  Uses:     NO Teledata Service
  Uses:     NO geographic pipeline steps

Geographic path:
  Input:    GeographicFilter + countryId
  Output:   DeliveryTarget with Kvhx=<address kvhx>, sourceType=GeographicAddress
```

**Contract reference:** [service-contracts.md → CONTRACT 7](service-contracts.md)  
**Stop condition:** Any implementation merging these two paths is a red-line violation.

---

### D5 — Profile cache = 15 days, in-process, no invalidation API. HARD DEFECT.

**Decision:** The legacy profile role cache has a 15-day TTL with no invalidation mechanism. This is a hard defect that MUST NOT carry forward. green-ai MUST implement `InvalidateProfileRolesCache(profileId)` and call it from any operation that modifies profile roles.

**Evidence source:** `CacheTimeout.cs` (`VeryLong = 21600` minutes = 15 days), `PermissionService.cs`

```
Legacy (sms-service):
  Cache TTL:    21600 minutes = 15 days = CacheTimeout.VeryLong
  Invalidation: NONE — no API exists
  Defect:       role changes take up to 15 days to take effect

green-ai requirement:
  InvalidateProfileRolesCache(profileId: int) → void  [NEW — does not exist yet]
  MUST be called by: any admin operation modifying profile roles
  Effect: removes cached set; next GetPermissionSet fetches from DB
```

**Contract reference:** [service-contracts.md → CONTRACT 6](service-contracts.md)  
**Build-time requirement:** Any service modifying roles without calling `InvalidateProfileRolesCache` is a defect.

---

### Correction — `Customer.ForwardingNumber` = VOICE-ONLY. Removed from SMS reasoning.

**Decision:** `Customer.ForwardingNumber` is exclusively a voice/Infobip configuration field. It has no role in SMS dispatch, SMS targeting, or any SMS boundary. All previous SMS architectural reasoning referencing this field is invalidated.

**Evidence source:** `Customer.cs`, `InfobipCustomerVoiceSettingsChangedEventHandler.cs` — all codebase usages verified

```
Customer.ForwardingNumber:
  Used by:  Infobip voice configuration only
  Purpose:  voice call forwarding setup
  SMS role: NONE
  Impact:   remove from all SMS boundary diagrams, contracts, and rules
```

**Stop condition:** If `ForwardingNumber` appears in any future SMS architectural reasoning, require new code evidence before accepting.

---

## SUMMARY TABLE

| Decision | Code evidence | Impact |
|---|---|---|
| D1: Pattern A — `ClaimForDispatch()` | Design + Red Line analysis | Targeting Engine owns DeliveryTargets creation; Dispatch claims via named gate |
| D2: 1881 = real-time HTTP + 28-day DB cache; KRR separate | `NorwegianPhoneNumberService.cs`, `PhoneNumberRepository.cs` | Declared as explicit external dep with cache contract + `CacheStatus` field |
| D3: CriticalAddresses = targeting filter; AddressVirtualMarkings = quality | `ICriticalAddressService.cs`, `AddressRepository.cs` | No new service boundary; `IsVirtual` surfaced on `AddressRecord`; not hidden SQL |
| D4: StandardReceiver = address bypass; `Kvhx=null` | `SplitStandardReceiverCommandProcessor.cs` | Separate Contract 7; MUST NOT merge into geographic pipeline |
| D5: Profile cache = 15 days, no invalidation — HARD DEFECT | `CacheTimeout.cs`, `PermissionService.cs` | `InvalidateProfileRolesCache(profileId)` required as new method in green-ai |
| Correction: `ForwardingNumber` = VOICE-ONLY | All codebase usages verified | Removed from all SMS reasoning |

---

**Last updated:** Wave 5-A (2026-04-12)  
**Next spec:** [service-contracts.md](service-contracts.md) — contract definitions derived from these decisions
