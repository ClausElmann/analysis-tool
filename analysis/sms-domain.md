# SMS DOMAIN — SSOT (Layer 1 Extracted Facts)

**Source:** Layer 0 — sms-service source code + SQL  
**Status:** VALIDATED (Wave 1 + Wave 2, approved by Architect)  
**Authority:** INFORMATIONAL — describes WHAT sms-service does  
**Last updated:** 2026-04-15 (Wave gap-scan — Voice channel, StandardReceivers, Email provider, ByLevel confirmed)

---

## 1. SMS FLOW — OVERVIEW

```
User creates SmsGroup (UI / API)
  → SmsGroupItems (address filters, phone numbers, standard receivers)
  → Lookup pipeline runs (see lookup-pipeline.md)
    → SmsLogs created (StatusCode=103 = ready for dispatch)
  → Batch dispatch (stored procedure claims rows)
    → GatewayAPI / Strex call (SMS gateway) — or Brevo/SendInBlue (email) — or Infobip (voice)
  → DLR callback received
    → SmsLog StatusCode updated
    → SmsLogStatus audit row appended
```

---

## 2. KEY DATABASE TABLES

### SmsGroups
| Field | Type | Notes |
|---|---|---|
| `Id` | INT PK | |
| `ProfileId` | INT FK→Profiles | Owner profile |
| `CountryId` | INT | DK=1, NO=2, SE=3, FI=4 |
| `Active` | BIT | If false: dispatch skips, lookup post-processor skips write |
| `IsLookedUp` | BIT | Set true by `CodedLookupService` after successful lookup |
| `DateLookupTimeUtc` | DATETIME | Set at lookup start (used by missing-lookup recovery) |
| `DateDelayToUtc` | DATETIME? | Delay gate in dispatch SQL |
| `SendSMS` | BIT? | If null → treated as 1 |
| `TestMode` | BIT | If true: dispatch uses `@GatewayClass='test'` |
| `SendMethod` | NVARCHAR | `"ByLevel"` triggers level-based address expansion |

### SmsGroupItems
| Field | Type | Notes |
|---|---|---|
| `Id` | INT PK | |
| `SmsGroupId` | INT FK→SmsGroups | |
| `Zip` | INT? | Present = address filter item |
| `StreetName` | NVARCHAR? | |
| `FromNumber`, `ToNumber` | INT? | Number range |
| `EvenOdd` | INT? | 0=even, 1=odd |
| `Letter`, `Floor`, `Door` | NVARCHAR? | |
| `Meters` | INT? | |
| `Phone`, `PhoneCode` | BIGINT/INT? | Explicit phone number (overrides address lookup) |
| `Email` | NVARCHAR? | Explicit email |
| `StandardReceiverId` | INT? | Points to StandardReceivers table |
| `StandardReceiverGroupId` | INT? | Points to StandardReceiverGroups table |
| `ExternalRefId` | INT? | External reference for merge fields |
| `Name` | NVARCHAR? | Display name for this item |

### SmsGroupSmsData
| Field | Type | Notes |
|---|---|---|
| `SmsGroupId` | INT FK→SmsGroups | |
| `Message` | NVARCHAR | Template with merge tags |
| `SendAs` | NVARCHAR | Sender ID (overrides Profile.SmsSendAs) |
| `UseUCS2` | BIT | Unicode encoding flag |
| `ReceiveSmsReply` | BIT | Two-way SMS flag |

### SmsLogs
| Field | Type | Notes |
|---|---|---|
| `Id` | INT PK | |
| `SmsGroupItemId` | INT FK→SmsGroupItems | |
| `ProfileId` | INT FK→Profiles | **HARD dispatch coupling — INNER JOIN** |
| `Kvhx` | NVARCHAR | Origin or owner address (string, NO FK to Addresses) |
| `OwnerAddressKvhx` | NVARCHAR? | Owner's address if owner lookup used |
| `PhoneNumber` | BIGINT | Resolved phone number |
| `PhoneCode` | INT | Country dial code |
| `Name` | NVARCHAR | Subscriber display name (from PhoneNumbers) |
| `SmsSendAs` | NVARCHAR? | Resolved sender ID (from SmsGroup.SmsData.SendAs) |
| `StatusCode` | INT | State machine key (see Section 4) |
| `TestMode` | BIT | From SmsGroup.TestMode |
| `DateGeneratedUtc` | DATETIME | Set at lookup (clock.Now()) |
| `DateDelayToUtc` | DATETIME? | From SmsGroup.DateDelayToUtc |
| `Text` | NVARCHAR? | Pre-resolved text (or null → dispatch uses template) |
| `SupplyNumber` | NVARCHAR? | |
| `SupplyNumberAlias` | NVARCHAR? | |
| `ResponseId` | INT? | Reply campaign link |
| `DisplayAddress` | NVARCHAR? | Pre-formatted address string |
| `GatewayProvider` | NVARCHAR? | Which gateway to use |
| `ExternalRefId` | INT? | External ref (from SmsGroupItem) |

**LookupKey** (dedup identity) = combination of `SmsGroupItemId + PhoneNumber + PhoneCode + Kvhx`

### SmsLogStatuses (append-only audit)
Each StatusCode transition creates a new row. Never updated — append only.

### SmsGroupAddresses (preload/persistent address cache)
```sql
SmsGroupId INT, SmsGroupItemId INT, Kvhx NVARCHAR, Kvh NVARCHAR,
Name NVARCHAR, IsCriticalAddress BIT
```
Written once by address expansion. Read at every lookup start. Cleared on SmsGroup delete or GDPR purge.

---

## 2b. SENDMETHOD = "BYLEVEL" — BUSINESS MEANING

`SmsGroup.SendMethod = "ByLevel"` triggers a **level-based address expansion** instead of the normal Zip-criteria TVP approach.

**What "levels" are:**  
A `ProfilePositiveList` can have up to **5 independent Levels**, each with a `Title` and a list of `Values` (e.g., Level 1 = "Commune", Level 2 = "Zone", etc.).
When `SendMethod=ByLevel`, the user selects combinations of level-values, and the system cross-joins those combinations to produce a set of Kvhxs.

**Flow:**
```
GetSmsGroupAddressesFromLevelsAsync(profileId, smsGroupId, smsGroup)
  → ProfilePositiveListSelectedLevelFilterQuery — reads level selections
  → LevelService.GetLevelCombinationIdsAsync(profileId, levels) — cross-join IDs
  → LevelService.GetLevelCombinationListingsAsync(combinationIds) — Kvhx list
  → AddressRepository.GetByMultipleKvhx(listings) — resolves to Addresses table
```

**Key constraints:**
- Levels are **NOT** a strict address hierarchy (country → region → city). They are customer-defined arbitrary groupings.
- Each Level is independent — selecting values in Level 2 does NOT restrict Level 1 automatically.
- ByLevel bypasses the criteria TVP (`SmsGroupItemsType`) entirely.

**DB tables involved:** `PositiveListLevels`, `PositiveListLevelValues`, `PositiveListLevelCombinations`, `ProfilePositiveListSelectedLevels`

---

## 2c. CHANNELS — CONFIRMED ACTIVE CHANNELS

| Channel | Gateway/Provider | Background Service | Status |
|---------|-----------------|-------------------|--------|
| SMS | GatewayAPI (DK) / Strex (NO) | `SmsBackgroundService` | ✅ Active |
| Email | SendGrid → migrating to Brevo/SendInBlue | `EmailBackgroundService` + `SendGridBackgroundService` | ✅ Active — migration in progress |
| Voice | Infobip | `VoiceBackgroundService` | ✅ Active — Infobip replacement in progress (see WIKI: Implementation/Infobip-replacement.md) |
| Web/Social | Facebook, Twitter | Unknown background service | ⚠️ Scope unknown for green-ai |

**Email DLR:** via webhooks (Brevo delivers event callbacks — same pattern as SMS DLR).

**NOTE FOR GREEN-AI:** `Broadcasts.Channels` enum currently has SMS=1, Email=2. Voice=3 is missing. Architect decision required before adding Voice.

---

## 2d. STANDARDRECEIVERS — BUSINESS CONTEXT

**What they are:** Pre-defined recipient lists maintained per Customer (NOT global). Used for recipients who should always receive messages from that customer regardless of address lookup (e.g., key personnel, emergency contacts).

**Structure:**
- `StandardReceivers` — individual recipients (PhoneCode + PhoneNumber, optional Name)
- `StandardReceiverGroups` — named collections of StandardReceivers per Customer
- `SmsGroupItems.StandardReceiverId` — direct reference to one receiver
- `SmsGroupItems.StandardReceiverGroupId` — reference to a group (expanded in pipeline Step 2)

**Key property:** Customer-specific. A StandardReceiver belongs to exactly one Customer.

**Active feature:** PR #12114 (sms group StandardReceiver admin), PR #12139 (StandardReceiver admin UI) — confirmed actively developed as of 2026-Q1.

**File:** `ServiceAlert.DB/Stored Procedures/GetSmsLogMergeModelForSmsByStatusAndGatewayClass.sql`  
**Called by:** Azure Batch dispatch job  
**Parameters:** `@StatusCode, @GatewayClass, @CountryId, @Top=1000, @HighPriority=0`

### Emergency kill switch
```sql
IF EXISTS (SELECT NULL FROM ApplicationSettings WHERE ApplicationSettingTypeId = 184 AND Setting = '1')
BEGIN
    SELECT null AS Id WHERE 1 = 0  -- returns empty result set, suspends all dispatch
END
```

### StatusCode transition map (dispatch)
```
103  → 202   (BulkAfventer → BulkKlarTilAfsendelse — ready for gateway, normal)
1212 → 231   (ready for 1st retry)
1213 → 232   (ready for 2nd retry)
1214 → 233   (ready for 3rd retry)
```

### Dispatch UPDATE (claim rows, ROWLOCK)
```sql
UPDATE TOP (@Top) SmsLogs WITH (ROWLOCK)
    SET StatusCode = @NextStatusCode
    OUTPUT inserted.Id INTO #ids
    FROM dbo.SmsLogs sl
      INNER JOIN dbo.SmsGroupItems sgi ON sl.SmsGroupItemId = sgi.Id
      INNER JOIN dbo.SmsGroups sg ON sgi.SmsGroupId = sg.Id
      INNER JOIN dbo.Profiles p ON p.Id = sl.ProfileId
      LEFT OUTER JOIN dbo.ProfileRoleMappings pr ON pr.ProfileId = p.Id AND pr.ProfileRoleId = 69
    WHERE sl.StatusCode = @StatusCode
      AND (sg.DateDelayToUtc IS NULL OR sg.DateDelayToUtc < GETUTCDATE())
      AND sg.Active = 1
      AND ISNULL(sg.SendSMS, 1) = 1
      AND ((@GatewayClass = 'test' AND sl.TestMode = 1) OR (sg.CountryId = @CountryId AND sl.TestMode = 0))
      AND ((@HighPriority = 0 AND pr.Id IS NULL) OR (@HighPriority = 1 AND pr.Id IS NOT NULL))
```

**Dispatch gates enforced in SQL (not C#):**
| Condition | Enforced by |
|---|---|
| StatusCode must match | `WHERE sl.StatusCode = @StatusCode` |
| No future delay | `sg.DateDelayToUtc IS NULL OR sg.DateDelayToUtc < GETUTCDATE()` |
| Group must be active | `sg.Active = 1` |
| SMS channel enabled | `ISNULL(sg.SendSMS, 1) = 1` |
| Country or test mode | `sg.CountryId = @CountryId` or `sl.TestMode=1` |
| HighPriority routing | `ProfileRoleMappings.ProfileRoleId = 69` hardcoded |

### Dispatch SELECT (build merge model for gateway)
```sql
SELECT
    sl.Id, sl.PhoneCode, sl.PhoneNumber,
    c.Id AS CustomerId,
    c.ForwardingNumber,                             -- silent phone override
    ISNULL(sl.Text, smsData.Message) AS [Text],     -- merge template fallback
    sgimf.GroupItemId,
    a.Street, a.City, a.Number, a.Letter, a.Meters, -- address fields (LEFT JOIN, can be NULL)
    sl.Name,
    sgimf.MergeFieldName1..5, sgimf.MergeFieldValue1..5,
    ISNULL(sl.SmsSendAs, smsData.SendAs) AS SmsSendAs,
    sg.Id AS SmsGroupId, sg.CountryId,
    ISNULL(smsData.ReceiveSmsReply, 0) AS RecieveSmsReply,
    ISNULL(smsData.UseUCS2, 0) AS UseUCS2,
    sl.Email, c.Name AS Company,
    sl.TestMode, sl.StatusCode,
    sgi.StandardReceiverId, sgi.StandardReceiverGroupId,
    sl.ProfileId, p.Hidden AS ProfileIsHidden,
    sl.SupplyNumber, sl.SupplyNumberAlias, sl.ResponseId,
    sl.DisplayAddress, sl.GatewayProvider
FROM dbo.SmsLogs sl
    LEFT JOIN dbo.Addresses a ON sl.Kvhx = a.Kvhx             -- string join, nullable
    INNER JOIN dbo.SmsGroupItems sgi ON sl.SmsGroupItemId = sgi.Id
    INNER JOIN dbo.SmsGroups sg ON sgi.SmsGroupId = sg.Id
    LEFT JOIN dbo.SmsGroupSmsData smsData ON smsData.SmsGroupId = sg.Id
    LEFT JOIN dbo.SmsGroupItemMergeFields sgimf ON sgimf.GroupItemId = sgi.Id
    INNER JOIN dbo.Profiles p ON p.Id = sl.ProfileId
    INNER JOIN dbo.Customers c ON c.Id = p.CustomerId
WHERE sl.Id IN (SELECT Id FROM #ids)
```

**Key observations from dispatch SELECT:**
- `c.ForwardingNumber` — if NOT NULL, delivery goes to this number, not `sl.PhoneNumber`. SmsLog is NOT updated. Invisible in audit trail.
- `Addresses` is LEFT JOIN — if Kvhx is deleted from Addresses after lookup, Street/City/Number return NULL. SMS still sends.
- Merge field text (`sgimf.MergeFieldValue1..5`) is resolved at dispatch time, not lookup time.
- `ISNULL(sl.Text, smsData.Message)` — if `sl.Text` was set at lookup (pre-resolved text), template is ignored.

---

## 4. STATUSCODE STATE MACHINE

### Lookup-time assignments (set by PhoneFiltersCheckedEventListener)
| Code | Name | Meaning |
|---|---|---|
| 103 | GatewayApiBulkAfventer | Ready for batch dispatch — the DISPATCH TARGET |
| 204 | Redundant | Duplicate number |
| 207 | DiscardedRobinsonList | Opt-out (Robinson register) |
| 208 | DiscardedNameCheck | Name match filter rejected |
| 209 | BlockedNumber | Blocked subscription |
| 211 | SmsNotIncludedInBroadcast | Mobile number but SMS channel not enabled |
| 214 | DiscardMaxPrAddress | Exceeded max-per-address limit |
| 500 | VoiceReadyForSending | Landline, voice channel enabled |
| 555 | (landline, no voice) | Discarded — landline, voice not enabled |

### Dispatch-time transitions (from stored proc)
| From | To | Meaning |
|---|---|---|
| 103 | 202 | Claimed by batch, awaiting gateway send |
| 1212 | 231 | Claimed for 1st retry |
| 1213 | 232 | Claimed for 2nd retry |
| 1214 | 233 | Claimed for 3rd retry |

### Post-send / DLR transitions (partial — full list UNKNOWN)
| Code | Meaning |
|---|---|
| 200 | Delivered (DLR confirmed) |
| 201 | Undelivered (DLR failed) |
| 202 | Sent to gateway (awaiting DLR) |
| 231/232/233 | Retry in progress |

Full DLR status string→code mapping: **UNKNOWN** (UNKNOWN-3)

---

## 5. PROFILE + CUSTOMER COUPLING

### Profiles table (fields relevant to SMS)
| Field | Type | Usage |
|---|---|---|
| `Id` | INT PK | FK target in SmsLogs.ProfileId, dispatch JOIN |
| `CustomerId` | INT FK→Customers | Navigated in dispatch (ForwardingNumber, blocked subscriptions) |
| `SmsSendAs` | NVARCHAR | Default sender ID (overridden by SmsGroup.SmsData.SendAs) |
| `LookupMaxNumbers` | INT | Max phone numbers per address (0=unlimited, 999=special-case) |
| `Hidden` | BIT | Returned in dispatch SELECT (used for UI display suppression only) |

### ProfileRoleMappings (dispatch-time coupling)
```sql
-- Only this one role is checked at dispatch time:
LEFT JOIN ProfileRoleMappings pr ON pr.ProfileId = p.Id AND pr.ProfileRoleId = 69
-- ProfileRoleId = 69 = HighPrioritySender (hardcoded literal in stored proc)
```

All other 61 ProfileRoles are resolved at LOOKUP TIME → baked into LookupState → baked into SmsLog.StatusCode.

### Customers table (fields relevant to SMS)
| Field | Type | Usage |
|---|---|---|
| `Id` | INT PK | |
| `ForwardingNumber` | BIGINT? | Silent phone override at dispatch. NULL = use SmsLog.PhoneNumber |
| `MonthToDeleteMessages` | INT | GDPR: auto-delete SmsLogs after N months |
| `Name` | NVARCHAR | Company name returned in dispatch SELECT |

### ProfileRoles — full set (62 total, lookup-time gates)
Permission flags resolved once per lookup from `ProfileRoleMappings`. Full list in `ProfileRoleNames.cs`.

Key subset (lookup-relevant):

| Role | Effect |
|---|---|
| `HighPrioritySender` | Controls dispatch priority via SQL gate (RoleId=69 hardcoded) |
| `UseMunicipalityPolList` | Address expansion uses municipality positive list JOIN |
| `HaveNoSendRestrictions` | Address expansion uses no positive list restriction |
| `DontLookUpNumbers` | Skip teledata lookup entirely |
| `RobinsonCheck` | Enforce Robinson opt-out list |
| `NameMatch` | Name-match filter against positive list names |
| `DuplicateCheckWithKvhx` | Dedup prefix includes Kvhx (per-address dedup) |
| `CanSendToCriticalAddresses` | Allow sending to IsCriticalAddress=true addresses |
| `OverruleBlockedNumber` | Send even to blocked subscription numbers |
| `NorwayKRRLookup` | Norway KRR register lookup (external API — unconfirmed) |
| `Norway1881Lookup` | Norway 1881 directory lookup |
| `SendToVarsleMeg` | VarsleMeg app subscription lookup |
| `QuickResponse` | Generate SmsLogResponse rows for two-way SMS |

### Permission cache
```
Cache key: "sms.profile.roles.by.id.{profileId}"
TTL:       21600 minutes (15 DAYS)
Store:     IMemoryCache — PER PROCESS (NOT distributed)
Invalidation: _cacheManager.Remove(...) on profile edit — current process ONLY
```

**Risk:** Role change in web UI only invalidates web server cache. Azure Batch has separate memory — reads fresh from DB. Other web instances retain stale cache up to 15 days.

---

## 6. COUPLING MAP

| Component | Depends On | Type | Evidence |
|---|---|---|---|
| Dispatch SQL status gate | `SmsLogs.StatusCode` | **HARD** | `WHERE sl.StatusCode = @StatusCode` |
| Dispatch SQL | `SmsLogs.ProfileId` → `Profiles` | **HARD** | `INNER JOIN Profiles p ON p.Id = sl.ProfileId` |
| Dispatch SQL priority | `ProfileRoleMappings.ProfileRoleId=69` | **HARD** | Literal `69` hardcoded in stored proc |
| Dispatch SQL delay gate | `SmsGroups.DateDelayToUtc` + `Active` | **HARD** | `sg.DateDelayToUtc < GETUTCDATE() AND sg.Active=1` |
| Dispatch SQL forwarding | `Customers.ForwardingNumber` | **HARD** | `c.ForwardingNumber` from `INNER JOIN Customers` |
| Dispatch SQL merge fields | `SmsGroupItemMergeFields` | **HARD** | `LEFT JOIN SmsGroupItemMergeFields` — resolved at dispatch |
| Address expansion | `Addresses` table | **HARD** | Dynamic SQL joins Addresses with criteria TVP |
| Address expansion | `ProfilePositiveLists` or `ProfilePosListMunicipalityCodes` | **HARD** | INNER JOIN injected at query build time; no ProfileId = no rows |
| Phone resolution | `PhoneNumbers` table | **SOFT** | Local import table, string Kvhx, TVP batch. No FK to dispatch tables. |
| Owner resolution | `AddressOwners` table | **SOFT** | Local import table, string Kvhx. No FK. |
| Robinson check | `RobinsonEntries` table | **SOFT** | Batch Kvhx query, result baked into StatusCode. No dispatch coupling. |
| Blocked opt-outs | `Subscriptions` table | **SOFT** | Per-customer, per-phone. Result baked into StatusCode=209. |
| Name match | `ProfilePositiveLists` (names) | **SOFT** | Separate query at lookup time. Result baked into StatusCode=208. |
| SmsSendAs | `SmsGroup.SmsData.SendAs` → `SmsLog.SmsSendAs` | **SOFT** | Baked into SmsLog at INSERT. Dispatch reads `ISNULL(sl.SmsSendAs, smsData.SendAs)`. |
| Permissions (12 flags) | `ProfileRoleMappings` → `LookupState` | **SOFT** | Resolved at step 1, cached 15 days. All baked into StatusCode or SmsLog — except HighPriority. |
| Kvhx address key | STRING join across Addresses/PhoneNumbers/SmsLogs/AddressOwners | **SOFT** | No FK. String equality. Cross-table identity is by convention. |
| Dedup control | In-memory `HashSet<string>` | **PURE** | `state.PhoneNumbersCreated` — not persisted |
| Max per address | In-memory `Dictionary<string,int>` | **PURE** | `state.PhoneNumberCounts` — not persisted |

---

## 7. ISOLATION CLASSIFICATION (A/B/C)

### A — HARD COUPLED (redesign required)

| Component | Reason |
|---|---|
| `SmsLogs.ProfileId` FK | Dispatch SQL INNER JOIN. Cannot remove without stored proc rewrite. |
| `ProfileRoleMappings.RoleId=69` in stored proc | Hardcoded literal. No referential guard. Stored proc must be rewritten. |
| `SmsGroups.Active` + JOIN chain | Dispatch gate — every UPDATE and SELECT passes through `SmsGroupItems → SmsGroups`. |
| `Customers.ForwardingNumber` | Returned by dispatch. Silent override. Cannot be isolated without adding SmsLog field or separate resolution step. |
| `SmsGroupItemMergeFields` at dispatch time | Merge resolution happens in dispatch SELECT. Moving dispatch requires moving merge resolution. |
| `ProfilePositiveLists` join in address SQL | ProfileId is embedded in address expansion SQL as INNER JOIN. Inseparable from profileId parameter. |
| `SmsGroupAddresses` write in same transaction domain | `InsertPreloadedAddresses` writes to core DB during lookup. Cannot be moved to a separate service without transactional boundary. |

### B — SOFT COUPLED (abstraction possible)

| Component | How to abstract |
|---|---|
| `PhoneNumbers` table | Pure read-only import table. Wrap as `IPhoneNumberResolver(kvhxs) → [{kvhx, phone, type}]`. |
| `AddressOwners` table | Same pattern. `IOwnerResolver(kvhxs) → [{kvhx, ownerKvhx, name}]`. |
| `RobinsonEntries` query | Read-only by Kvhx. Could be external service call. |
| `Subscriptions` (opt-outs) | Read-only per CustomerId+Phone. `IOptOutService.IsBlocked(customerId, phone)`. |
| `PermissionService` (12 flags) | Pure read against `ProfileRoleMappings`. Stateless `IPermissionResolver(profileId) → PermissionSet`. |
| `ProfilePositiveLists` (name match only) | Separate from address filter query. `INameMatchService(profileId, kvhxs)`. |
| `SmsSendAs` resolution | Already baked into `SmsLog.SmsSendAs`. Dispatch fallback is redundant if always written. |

### C — PURE CORE (no data coupling to dispatch tables)

| Component | Why pure |
|---|---|
| `LookupExecutor` engine | No DB access. Pure command-event dispatch engine given injected processors. |
| `LookupState` | Pure RAM. All fields computed during run. No DB representation. |
| `CheckPhoneFiltersCommandProcessor` | 100% in-memory dedup + max logic. |
| `PhoneFiltersCheckedEventListener` (StatusCode table) | Pure flag → int mapping. |
| `PositiveListAddressRestriction` strategy | Pure SQL fragment injection. |
| `DeterminePhoneNumberTypeCommandProcessor` fallback | Single-row read from `PhoneNumbers`. No coupling to dispatch. |
| Name comparison logic (`StringExtensions.FirstName`, diacritics-aware compare) | Pure string. Zero dependencies. |

---

## 8. FAILURE POINTS

| ID | Description | Risk Level |
|---|---|---|
| F1 | Blocking `.GetAwaiter().GetResult()` in `MessageService` (lines 332, 345) — address lookup called synchronously inside merge-field resolution | HIGH — deadlock risk under load |
| F2 | String Kvhx without FK — deleted Addresses row → NULL address fields in dispatch SELECT (SMS still sends, address is blank) | MEDIUM — silent data quality degradation |
| F3 | `ProfileRoleId=69` hardcoded in dispatch SQL — role ID change breaks priority routing silently | HIGH — no compile-time check |
| F4 | Permission cache inconsistency across processes (IMemoryCache, 15-day TTL, no cross-instance invalidation) | MEDIUM — role changes take different effect per process |
| F5 | `smsGroup.Active` checked AFTER full pipeline run — race condition if group cancelled during long lookup | LOW — compute wasted, no incorrect SMS |
| F6 | Missing-lookup retry re-runs FULL pipeline from scratch — no partial replay | MEDIUM — expensive for large broadcasts |
| F7 | `Matcher.cs` also calls `.GetAwaiter().GetResult()` (line 131) during address autocomplete | MEDIUM — same deadlock risk pattern |

---

*Source archive: [/temp_history/temp_2026-04-12_wave1-wave2.md](/temp_history/temp_2026-04-12_wave1-wave2.md)*  
*See also: [lookup-pipeline.md](lookup-pipeline.md) · [address-domain.md](address-domain.md)*
