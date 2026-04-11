# LOOKUP PIPELINE — SSOT (Layer 1 Extracted Facts)

**Source:** Layer 0 — sms-service source code + SQL  
**Status:** VALIDATED (Wave 1 + Wave 2, approved by Architect)  
**Authority:** INFORMATIONAL — describes WHAT sms-service does, not HOW green-ai should implement  
**Last updated:** 2026-04-12

---

## 1. ARCHITECTURE OVERVIEW

The lookup pipeline is a **command-event engine**, not a sequential pipeline.

```
LookupExecutor
  ├── SortedList<int, LinkedList<ILookupCommand>>   ← priority queues (lower int = higher priority)
  ├── IEnumerable<ILookupCommandProcessor>           ← process commands, emit events
  ├── IEnumerable<ILookupEventListener>              ← handle events, enqueue new commands
  └── ILookupPostProcessor                           ← runs after all queues empty
```

**Entry point:** `CodedLookupService.LookupAsync(smsGroupId)`  
**Seed command:** `LookupSmsGroupCommand(smsGroupId)`  
**Post-processor:** `WriteToDatabasePostProcessor` → writes SmsLog rows

**Execution modes:**
- `LookupAsync` — writes to SmsLogs (production)
- `PrelookupAsync` — uses `TemporaryStoragePostProcessor` (preview, no DB write)
- `GetSmsLogsAsync` — query-mode, `IsQueryLookup=true`, no DB write

**Background processing:** `ISmsLogBackgroundProcessingManager` — if `forWebBackgroundService=true`, SmsLog inserts run in parallel on a Channel while pipeline continues. `CompleteAndWaitAsync()` called after pipeline drains.

---

## 2. FULL COMMAND CHAIN (13 STEPS, END-TO-END)

### Step 0: Entry
```
Seed: LookupSmsGroupCommand(smsGroupId)
```

### Step 1: LookupSmsGroupCommandProcessor → SmsGroupFoundEvent
**File:** `ServiceAlert.Services/Lookup/CodeLookup/CommandProcessors/LookupSmsGroupCommandProcessor.cs`

- `messageService.GetSmsGroupByIdAsync(smsGroupId, true)` — SQL: `SELECT * FROM SmsGroups WHERE Id=@id` (with SmsGroupItems)
- `profileService.GetProfileById(profileId)` — SQL: `SELECT * FROM Profiles WHERE Id=@id` (no cache on entity)
- `permissionService.DoesProfileHaveRole(profileId, ...)` × 12 — SQL (cached 15 days, IMemoryCache per process):
  ```sql
  SELECT pr.* FROM ProfileRoles pr
  INNER JOIN ProfileRoleMappings prm ON pr.Id = prm.ProfileRoleId
  WHERE prm.ProfileId = @profileId
  ```
- `addressService.GetKvhxFromPreloadedAddressesAsync(smsGroupId)`:
  ```sql
  SELECT SmsGroupItemId, Kvhx, Kvh, Name, IsCriticalAddress
  FROM SmsGroupAddresses WHERE SmsGroupId = @id
  ```
- Fires: `SmsGroupFoundEvent` (carries all 12 permissions + preloaded addresses + SmsSendAs + LookupMaxNumbers)

### Step 2: SmsGroupFoundEventListener — fills LookupState + generates per-item commands
**File:** `ServiceAlert.Services/Lookup/CodeLookup/EventListeners/SmsGroupFoundEventListener.cs`

- Fills `LookupState`:
  - `state.ProfileId`, `state.CustomerId`, `state.CountryId`
  - `state.SmsSendAs = SmsGroup.SmsData.SendAs` ← **baked here, not re-read at dispatch**
  - `state.LookupMaxNumbers = profile.LookupMaxNumbers`
  - `state.TestMode`, `state.DateDelayToUtc`
  - All 12 permission flags

- Per SmsGroupItem routing:
  ```
  IF preloaded addresses exist   → RegisterPreloadedAddressCommand  (skips address DB queries)
  ELIF item.Zip.HasValue         → ExpandAddressFilterCommand
  ELIF item.StandardReceiverId   → SplitStandardReceiverCommand
  ELIF item.StandardReceiverGroupId → ExpandStandardReceiverGroupCommand
  ELSE (explicit phone/email)    → AttachPhoneCommand / AttachEmailCommand
  ```

### Step 3a: ExpandAddressFilterCommandProcessor (BATCHED)
**File:** `ServiceAlert.Services/Lookup/CodeLookup/CommandProcessors/ExpandAddressFilterCommandProcessor.cs`

1. Check `GetKvhxFromPreloadedAddressesAsync(smsGroupId)` — if populated, use cached rows
2. If empty → `AddressLookupService.GetKvhxFromPartialAddressAsync(profileId, countryId, addresses, smsGroupId)`:
   - **Permission decides address filter JOIN (injected into dynamic SQL):**
     ```
     UseMunicipalityPolList → INNER JOIN ProfilePosListMunicipalityCodes pmc 
                                ON pmc.ProfileId=@profileId AND pmc.MunicipalityCode=a.MunicipalityCode
     HaveNoSendRestrictions → (no join — all addresses accessible)
     default                → INNER JOIN ProfilePositiveLists pl 
                                ON pl.ProfileId=@profileId AND pl.Kvhx=a.Kvhx
     ```
   - **Address expansion SQL (dynamically built from criteria flags):**
     ```sql
     SELECT a.Kvhx, a.Kvh, criteria.Name, criteria.Id AS SmsGroupItemId, criteria.ExternalRefId
     FROM Addresses a
     {addressRestriction.GetTableJoins()}    ← PositiveList or Municipality JOIN
     INNER JOIN @criteria criteria ON        ← TVP (SmsGroupItemsType), batched 4000 at a time
       a.CountryId = @countryId
       AND a.DateDeletedUtc IS NULL
       AND a.ZipCode = criteria.Zip
       [AND a.Street = criteria.StreetName]
       [AND a.Number BETWEEN criteria.FromNumber AND criteria.ToNumber]
       [AND (1 - a.Number%2) = criteria.EvenOdd]
       [AND a.Letter = criteria.Letter]
       [AND a.Floor = criteria.Floor]
       [AND a.Door = criteria.Door]
       [AND a.Meters = criteria.Meters]
     ```
3. Save result: `addressRepository.InsertPreloadedAddresses(addresses)` → `INSERT INTO SmsGroupAddresses`
4. Fire `OriginAddressesFoundEvent(smsGroupItemId, name, [kvhx])`

### Step 3b: RegisterPreloadedAddressCommandProcessor
If `SmsGroupAddresses` already populated → fires `OriginAddressesFoundEvent` from cached Kvhxs immediately.

### Step 4: OriginAddressesFoundEventListener
**File:** `ServiceAlert.Services/Lookup/CodeLookup/EventListeners/OriginAddressesFoundEventListener.cs`

- Accumulates: `state.OriginAddresses[smsGroupItemId] += kvhx`
- Routes by country:
  ```
  DK/SE/FI → FindOwnerAddressCommand(kvhx) per address
  NO       → LookupSubscriptionsCommand + LookupEnrollmentsCommand
             + LookupNorwegianAddressResidentsCommand
             + LookupNorwegianAddressOwnersCommand per kvhx
  ```

### Step 5: FindOwnerAddressCommandProcessor (BATCHED, DK/SE/FI only)
**File:** `ServiceAlert.Services/Lookup/CodeLookup/CommandProcessors/FindOwnerAddressCommandProcessor.cs`

Only if `state.SendToOwnerAddress AND countryId != NO`.

```sql
SELECT ao.Kvhx, ao.OwnerAddressKvhx AS OwnerKvhx, ao.OwnerName AS Name,
       cr.CompanyRegistrationId, cr.Active AS CompanyActive
FROM AddressOwners ao
LEFT JOIN CompanyRegistrations cr ON cr.CompanyRegistrationId = ao.CompanyRegistrationId
                                   AND cr.CountryId = ao.CountryId AND cr.Active = 1
LEFT JOIN Addresses ad ON ad.Kvhx = ao.OwnerAddressKvhx
                        AND ad.DateDeletedUtc IS NULL
                        AND ao.CompanyRegistrationId IS NULL
WHERE ao.Kvhx IN @kvhxList AND ao.IsDoubled = 0
  AND (ad.Kvhx IS NOT NULL OR cr.CompanyRegistrationId IS NOT NULL)
```

Fires: `OwnerAddressFoundEvent(kvhx, ownerKvhx, ownerName, companyRegistrationId)`

### Step 6: LookupTeledataCommandProcessor (BATCHED)
**File:** `ServiceAlert.Services/Lookup/CodeLookup/CommandProcessors/LookupTeledataCommandProcessor.cs`

Only if `state.SendToAddress AND (state.SendSMS OR state.SendVoice)`.

```sql
-- PhoneNumberRepository.GetPhoneNumbersByKvhxs (TVP NvarcharTableType)
SELECT * FROM PhoneNumbers p
WHERE EXISTS (SELECT NULL FROM @kvhxList k WHERE p.Kvhx = k.NvarcharValue)
```

Filter in C# (not SQL):
```csharp
(state.LookupPrivate && !(p.BusinessIndicator ?? false)) ||
(state.LookupBusiness && (p.BusinessIndicator ?? false))
// AND PhoneNumberType == 1 (PHONE_NORMAL_MOBILE) for SMS path
```

Blocked check:
```csharp
// SQL: SELECT * FROM Subscriptions WHERE CustomerId=@cid AND PhoneNumber IN @phones
_subscriptionRepository.GetBlockedSubscriptionsByPhoneNumbers(state.CustomerId, phoneNumbers)
```

Fires: `TeledataLookedUpEvent` per matching phone (with Blocked=true/false)

### Step 7: CheckRobinsonCommandProcessor (BATCHED)
**File:** `ServiceAlert.Services/Lookup/CodeLookup/CommandProcessors/CheckRobinsonCommandProcessor.cs`

Only if `state.RobinsonCheck`.
- `robinsonService.GetRobinsonEntriesByKvhxs(ownerKvhx ?? kvhx)` — batch DB query
- Name match: `entry.PersonName.Contains(FirstName(cmd.PersonName))` — first name, OrdinalIgnoreCase
- Fires: `PhoneMessageCreatedEvent(robinson=true/false)`

### Step 8: DeterminePhoneNumberTypeCommandProcessor (NOT BATCHED)
**File:** `ServiceAlert.Services/Lookup/CodeLookup/CommandProcessors/DeterminePhoneNumberTypeCommandProcessor.cs`

If `PhoneNumberType is null` (explicit number attached without kvhx lookup):
```sql
SELECT * FROM PhoneNumbers WHERE PhoneCode=@phoneCode AND NumberIdentifier=@phoneNumber
```
Fires: `PhoneNumberTypeDeterminedEvent`

### Step 9: CheckNameMatchCommandProcessor (BATCHED)
**File:** `ServiceAlert.Services/Lookup/CodeLookup/CommandProcessors/CheckNameMatchCommandProcessor.cs`

Three execution modes:
1. `NameMatch AND !HaveNoSendRestrictions AND !UseMunicipalityPositiveList`:
   - Queries `ProfilePositiveLists` for names at these Kvhxs:
     ```sql
     SELECT * FROM ProfilePositiveLists
     WHERE ProfileId=@profileId AND Kvhx IN (SELECT NvarcharValue FROM @kvhxs) -- TVP
     ```
   - `nameFiltered = personFirstName NOT IN poslistNames[kvhx]`  
     AND if nameFromFile present: `personFirstName != firstNameFromFile`
2. `NameMatch AND (HaveNoSendRestrictions OR UseMunicipalityPositiveList)`:
   - No poslist query — pure teledata-vs-file name compare
3. `!NameMatch`: pass-through, `nameFiltered=false`

Name comparison: `string.Compare(name1, name2, InvariantCulture, IgnoreCase | IgnoreNonSpace)` — diacritics-aware

Fires: `NameMatchCheckedEvent(nameFiltered=true/false)`

### Step 10: CheckPhoneFiltersCommandProcessor (IN-MEMORY ONLY)
**File:** `ServiceAlert.Services/Lookup/CodeLookup/CommandProcessors/CheckPhoneFiltersCommandProcessor.cs`

No DB calls. Pure in-memory accumulation on `LookupState`:

```csharp
// Duplicate check
bool doubled = state.PhoneNumbersCreated.Contains(
    (DuplicateCheckWithKvhx ? kvhx + "_" : "")
    + PhoneNumberTools.GetPhoneWithPhoneCode(phoneCode, phone)
    + (landline ? "_voice" : "_sms")
);

// Max per address
bool overMax = state.PhoneNumberCounts[ownerKvhx ?? kvhx] >= state.LookupMaxNumbers
    // 14 exempt detail strings that don't count toward max
```

Fires: `PhoneFiltersCheckedEvent`

### Step 11: PhoneFiltersCheckedEventListener — StatusCode assignment (NO DB)
**File:** `ServiceAlert.Services/Lookup/CodeLookup/EventListeners/PhoneFiltersCheckedEventListener.cs`

```
NameFiltered                       → 208  (DiscardedNameCheck)
!OverruleBlockedNumber && Blocked  → 209  (BlockedNumber)
Robinson                           → 207  (DiscardedRobinsonList)
Doubled                            → 204  (Redundant)
OverMax                            → 214  (DiscardMaxPrAddress)
LAND_LINE && SendVoice             → 500  (VoiceReadyForSending)
LAND_LINE && !SendVoice            → 555
MOBILE && !SendSMS                 → 211  (SmsNotIncludedInBroadcast)
DEFAULT                            → 103  ← DISPATCH TARGET (GatewayApiBulkAfventer)
```

### Step 12: WriteToDatabasePostProcessor
**File:** `ServiceAlert.Services/Lookup/CodeLookup/PostProcessors/WriteToDatabasePostProcessor.cs`

```csharp
if (!smsGroup.Active) return;  // race condition: group cancelled during lookup → skip write

// Dedup: load existing SmsLogs for this group, skip rows whose LookupKey already exists
existingLogKeys = messageRepository.GetSmsLogsAsync(smsGroupId).Select(log => log.LookupKey()).ToHashSet();
newLogs = state.SmsLogs.Where(log => !existingLogKeys.Contains(log.LookupKey()));

uow.InsertSmsLogs(newLogs);
uow.ClearSmsLogsNoPhoneAddresses(smsGroupId);
uow.InsertSmsLogsNoPhoneAddresses(noHitKvhxs);  // addresses with no phone found
uow.Commit();
messageService.CreateSmsLogStatuses(newLogs);    // audit rows
```

**SmsLog fields set from lookup state:**

| Field | Source |
|---|---|
| `ProfileId` | `state.ProfileId` — **HARD dispatch coupling** |
| `SmsGroupItemId` | from command chain |
| `Kvhx` | owner kvhx (if owner lookup) or origin kvhx |
| `OwnerAddressKvhx` | from `OwnerAddressFoundEvent` |
| `PhoneNumber` | `NumberIdentifier` from `PhoneNumbers` |
| `PhoneCode` | from `PhoneNumbers` |
| `Name` | `DisplayName` from `PhoneNumbers` |
| `SmsSendAs` | `state.SmsSendAs` (from `SmsGroup.SmsData.SendAs`) |
| `StatusCode` | assigned at step 11 |
| `TestMode` | `state.TestMode` |
| `DateGeneratedUtc` | `_clock.Now()` |
| `DateDelayToUtc` | `state.DateDelayToUtc` |
| `Text` | `SmsGroup.SmsData.Message` (merge tags NOT resolved here — resolved at dispatch) |

### Step 13: Dispatch (stored procedure)
**File:** `ServiceAlert.DB/Stored Procedures/GetSmsLogMergeModelForSmsByStatusAndGatewayClass.sql`

See [sms-domain.md](sms-domain.md) — Section 3: Dispatch SQL.

---

## 3. BATCHPROCESSOR PATTERN

Processors implementing `ILookupBatchCommandProcessor`:
- `ExpandAddressFilterCommandProcessor` — batches ExpandAddressFilterCommands
- `FindOwnerAddressCommandProcessor` — batches FindOwnerAddressCommands
- `LookupTeledataCommandProcessor` — batches LookupTeledataCommands
- `CheckRobinsonCommandProcessor` — batches CheckRobinsonCommands
- `CheckNameMatchCommandProcessor` — batches CheckNameMatchCommands

Batch mechanism: when `ShouldBatch(state)=true`, commands accumulate in `state.BatchedCommands[typeName]`. A `RunBatchedCommandsCommand` is inserted (front or back of queue) to flush the batch as one call.

---

## 4. LOOKUPSTATE FIELDS (KEY SUBSET)

```csharp
// Identity
int ProfileId, CustomerId, CountryId, SmsGroupId

// Channel flags
bool SendSMS, SendEmail, SendVoice, SendToAddress, SendToOwnerAddress
bool LookupPrivate, LookupBusiness, TestMode

// Permissions (resolved at step 1, baked in for whole run)
bool RobinsonCheck, NameMatch, DuplicateCheckWithKvhx, OverruleBlockedNumber
bool DontLookUpNumbers, HaveNoSendRestrictions, CanSendToCriticalAddresses
bool UseMunicipalityPositiveList, NorwayKRRLookup, Norway1881Lookup
bool VarsleMegLookup, GenerateSmsLogResponses

// Content
string SmsSendAs, Content
bool UseUCS2
int LookupMaxNumbers
DateTime? DateDelayToUtc

// Accumulators (in-memory, not persisted)
IDictionary<int, IEnumerable<string>> OriginAddresses    // SmsGroupItemId → [kvhxs]
ICollection<SmsLogState> SmsLogs                          // pipeline results
ICollection<string> PhoneNumbersCreated                   // dedup HashSet
IDictionary<string, int> PhoneNumberCounts                // max counter per kvhx
IDictionary<string, List<ILookupCommand>> BatchedCommands // pending batch

// Flags
bool IsQueryLookup, ForWebBackgroundService, DisableDuplicateControl
```

---

## 5. RETRY + RECOVERY

**Missing lookup detection** (`LookupRepository.GetMissingLookups`):
```sql
SELECT * FROM SmsGroups
WHERE Active=1 AND IsLookedUp=0
  AND DateLookupTimeUtc < DATEADD(minute, -40, GETUTCDATE())
  AND DateUpdatedUtc < DATEADD(minute, -10, GETUTCDATE())
```

**Retry behaviour:**
- Retry re-runs the FULL pipeline from scratch (no partial state replay — `LookupState` is not persisted)
- `WriteToDatabasePostProcessor` dedup (via `LookupKey`) prevents duplicate SmsLogs on retry
- `SmsGroupLookupRetries` table records each retry attempt
- Max retry count: UNKNOWN (LookupRetryPolicy.cs not read)

---

## 6. OPEN UNKNOWNS

| ID | What | Impact |
|---|---|---|
| UNKNOWN-5 | Norway KRR, Norway 1881, VarsleMeg processors — real-time external API or local? | HIGH for Norway |
| UNKNOWN-4 | `LookupRetryPolicy` max retry count + backoff | MEDIUM |
| UNKNOWN-6 | `ISmsLogBackgroundProcessingManager.CanRunInBackground()` exact condition | LOW |
| UNKNOWN-7 | Norwegian address residents + property owners processors (local or external API?) | MEDIUM |

---

*Source archive: [/temp_history/temp_2026-04-12_wave1-wave2.md](/temp_history/temp_2026-04-12_wave1-wave2.md)*
