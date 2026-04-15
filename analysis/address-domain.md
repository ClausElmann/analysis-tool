# ADDRESS DOMAIN — SSOT (Layer 1 Extracted Facts)

**Source:** Layer 0 — sms-service source code + SQL  
**Status:** VALIDATED (Wave 2, approved by Architect)  
**Authority:** INFORMATIONAL — describes WHAT sms-service does  
**Last updated:** 2026-04-15 (Wave gap-scan — NO/SE/FI import sources confirmed)

---

## 1. DATA MODEL

### Addresses (master address register — local DB copy)
```sql
CREATE TABLE dbo.Addresses (
    Kvhx            NVARCHAR(36)  NOT NULL,  -- compound key: floor+door+letter uniqueness
    Kvh             NVARCHAR(36)  NOT NULL,  -- base key: no floor/door
    CountryId       INT           NOT NULL,  -- DK=1, NO=2, SE=3, FI=4
    ZipCode         INT           NOT NULL,
    City            NVARCHAR,
    Street          NVARCHAR,
    Number          INT           NULL,
    Letter          NVARCHAR,
    Floor           NVARCHAR,
    Door            NVARCHAR,
    Meters          INT           NULL,      -- parcel identifier (DK: matrikelnummer context)
    MunicipalityCode INT,
    Latitude        FLOAT         NULL,
    Longitude       FLOAT         NULL,
    DateDeletedUtc  DATETIME      NULL,      -- soft delete (NULL = active)
    ExtUUID         NVARCHAR      NULL
)
```

**KVHX FORMAT (country-specific):**
- DK example: `07402045__28_______` — encodes zip+street+number+letter+floor+door
- NO: different format (not verified in code)
- Kvhx is padded to a fixed-width string — exact format defined during import

**`Addresses` is a local copy** of national registers:
- DK: DAWA (Danmarks Adressers Web API) — batch import via `DanishAddressImporter` (HTTP client)
- DK: DAR file download — `DarFileDownloadImporter` (HTTP client)
- NO/SE/FI: source UNKNOWN (import clients not read in this wave)

There is NO real-time address lookup during the SMS lookup pipeline. All address resolution uses this local table.

### AddressOwners (property ownership register — local DB copy)
```sql
CREATE TABLE dbo.AddressOwners (
    Kvhx                  NVARCHAR  NOT NULL,  -- property being looked up (NO FK to Addresses)
    OwnerAddressKvhx      NVARCHAR  NULL,       -- owner's home/mailing address
    OwnerName             NVARCHAR,
    CompanyRegistrationId NVARCHAR  NULL,       -- if company owner (FK→CompanyRegistrations)
    CountryId             INT,
    IsDoubled             BIT       NOT NULL    -- import dedup flag (1=duplicate, excluded from queries)
)
```

**Source:** BBR (DK), equivalent owner registers (NO/SE/FI). Updated by batch import.  
**Key property:** `IsDoubled=0` filter excludes duplicate ownership rows. Set at import time.  
**No FK** to `Addresses` — string join on Kvhx.  
**External source:** `IEjerfortegnelseAppService` (HTTP client in Batch) — DK owner register.

### CompanyRegistrations (business register — local DB copy)
```sql
CREATE TABLE dbo.CompanyRegistrations (
    CompanyRegistrationId NVARCHAR NOT NULL,
    CountryId             INT,
    Active                BIT,
    -- other fields...
)
```

Used in owner lookup JOIN to verify company is still active.

### ProfilePositiveLists (profile address whitelist)
```sql
CREATE TABLE dbo.ProfilePositiveLists (
    ProfileId INT NOT NULL,
    Kvhx      NVARCHAR NOT NULL
    -- Name field present (used in name-match queries)
)
```

**Purpose:** Restricts which addresses a profile can send to (default mode for most profiles).  
**Managed via:** UI (operator adds/removes addresses per profile) or import.  
**Used in TWO separate ways:**
1. Address filter JOIN: `INNER JOIN ProfilePositiveLists pl ON pl.ProfileId=@profileId AND pl.Kvhx=a.Kvhx`
2. Name match query: `SELECT Name FROM ProfilePositiveLists WHERE ProfileId=@profileId AND Kvhx IN @kvhxs`

### ProfilePosListMunicipalityCodes (municipality whitelist — alternative to address-level)
```sql
CREATE TABLE dbo.ProfilePosListMunicipalityCodes (
    ProfileId        INT NOT NULL,
    MunicipalityCode INT NOT NULL
)
```

Used when profile has role `UseMunicipalityPolList`. Joins on `Addresses.MunicipalityCode` instead of per-address Kvhx.

### SmsGroupAddresses (persistent address preload cache)
```sql
CREATE TABLE dbo.SmsGroupAddresses (
    SmsGroupId      INT      NOT NULL,
    SmsGroupItemId  INT      NOT NULL,
    Kvhx            NVARCHAR NOT NULL,
    Kvh             NVARCHAR,
    Name            NVARCHAR,
    IsCriticalAddress BIT    NULL
)
```

**Written by:** `AddressRepository.InsertPreloadedAddresses()` after first address expansion  
**Read by:** `GetKvhxFromPreloadedAddressesAsync(smsGroupId)` at every lookup start  
**Cache hit:** If rows exist → `ExpandAddressFilterCommandProcessor` skips all address queries  
**Cache miss:** Address expansion SQL runs, result saved here  
**Cleared by:** SmsGroup delete / GDPR purge  
**Staleness risk:** If address register changes AFTER preload → addresses not refreshed until SmsGroup is deleted

### PhoneNumbers (teledata — local DB copy)
```sql
CREATE TABLE dbo.PhoneNumbers (
    Kvhx              NVARCHAR(36) NOT NULL,  -- address key (NO FK to Addresses)
    NumberIdentifier  BIGINT       NOT NULL,   -- phone number (without country code)
    PhoneCode         INT          NOT NULL,   -- country dial code (+45, +47, etc.)
    PhoneNumberType   INT          NOT NULL,   -- 1=mobile, 2=landline
    BusinessIndicator BIT          NULL,       -- true=business subscriber
    DisplayName       NVARCHAR,
    PersonGivenName   NVARCHAR,
    CountryId         INT,
    MunicipalityCode  INT,
    DateUpdatedUtc    DATETIME
)
```

**Source:** External teledata provider — imported via batch jobs (schedule UNKNOWN).  
**No FK** to `Addresses` — string join on Kvhx.  
**Primary query:** `GetPhoneNumbersByKvhxs(kvhxs)` → TVP batch:
```sql
SELECT * FROM PhoneNumbers p
WHERE EXISTS (SELECT NULL FROM @kvhxList k WHERE p.Kvhx = k.NvarcharValue)
```

**Secondary (fallback):** `GetPhoneNumber(phoneCode, phoneNumber)`:
```sql
SELECT * FROM PhoneNumbers WHERE PhoneCode=@phoneCode AND NumberIdentifier=@phoneNumber
```

**PhoneNumberCachedLookupResults** — separate table for external API results (Norway KRR). Has `Source` column, `CleanupOldCachedLookupResults()` job purges expired entries.

---

## 2. KVHX — ROLE OF THE STRING KEY

### What Kvhx represents
A **compound address identifier** encoding: country-specific register key + address components.  
Example: DK Kvhx `07402045__28_______` encodes zip=0740, address block 2045, number 28.

### How Kvhx flows through the system

```
Addresses.Kvhx
    ↓ (string join — no FK)
PhoneNumbers.Kvhx      → resolves phone at this address
AddressOwners.Kvhx     → resolves owner at this address (citizen or company)
AddressOwners.OwnerAddressKvhx → owner's own mailing address (→ used for LookupTeledata)
SmsGroupAddresses.Kvhx → persistent preload cache
SmsLogs.Kvhx           → records which address generated this SmsLog
    ↓ (LEFT JOIN in dispatch SQL — can return NULL if Addresses row deleted)
Addresses.Kvhx         → address fields (Street, City, Number) in dispatch merge model
ProfilePositiveLists.Kvhx → positive list membership test
RobinsonEntries.Kvhx   → opt-out check
```

### Kvhx integrity
- **No FK constraints** anywhere in this chain
- `DateDeletedUtc IS NULL` check on `Addresses` prevents deleted addresses from being targeted in new lookups
- Existing `SmsLogs.Kvhx` referencing a deleted `Addresses.Kvhx` → dispatch returns NULL address fields (LEFT JOIN). SMS still sends.
- Format is country-specific — a DK Kvhx cannot accidentally match a NO Kvhx (different format + CountryId separation)

### `GetByMultipleKvhx` (reverse lookup)
**File:** `ServiceAlert.Services/Addresses/Repository/AddressRepository.cs` line 152

```sql
SELECT * FROM dbo.Addresses
WHERE Kvhx IN @KvhxList AND CountryId = @CountryId
  AND (@IncludeDeleted = 1 OR DateDeletedUtc IS NULL)
```

Chunked at 2000 items per query (Dapper IN-clause limit protection).  
Used by: `MessageService.GetCityAndStreetNames()`, `SmsGroupAddressFetcher`, `SmsGroupItemFactory`, `WebMessageService`

---

## 3. ADDRESS EXPANSION FLOW

### Entry path (full detail)

```
SmsGroupItem.Zip (required) + optional: Street, FromNumber, ToNumber, EvenOdd, Letter, Floor, Door, Meters
    ↓
AddressLookupService.GetKvhxFromPartialAddressAsync(profileId, countryId, addresses, smsGroupId)
    ↓
GetSmsGroupAddressesFromPartialAddressesAsync(profileId, ...)
    ↓
PERMISSION CHECK → selects IAddressRestriction:
    UseMunicipalityPolList  → MunicipalityPositiveListAddressRestriction (JOIN ProfilePosListMunicipalityCodes)
    HaveNoSendRestrictions  → NoAddressRestriction (no join — all addresses in Addresses table accessible)
    default                 → PositiveListAddressRestriction (JOIN ProfilePositiveLists ON Kvhx)
    ↓
AddressRepository.GetAddressesFromPartialAddressesAsync(smsGroupId, countryId, addressQuery, restriction)
    ↓
Grouped by criteria shape (which optional fields are present)
Per group, batched at 4000 items (TVP SmsGroupItemsType)
    ↓
GetAddressesFromSimplifiedPartialAddressesAsync → dynamic SQL built from criteria flags
Returns: IReadOnlyCollection<SmsGroupAddressReadModel> {Kvhx, Kvh, SmsGroupItemId, ExternalRefId, Name, HasPhoneOrEmail}
    ↓
IF CanSendToCriticalAddresses: CriticalAddressService.CheckCriticalAddresses(customerId, entries)
    ↓
AddressRepository.InsertPreloadedAddresses(addresses) → INSERT INTO SmsGroupAddresses
```

### Special case: ByLevel
```
SmsGroup.SendMethod == "ByLevel"
    ↓
GetSmsGroupAddressesFromLevelsAsync(profileId, smsGroupId, smsGroup)
    ↓
ProfilePositiveListSelectedLevelFilterQuery → gets level selections
LevelService.GetLevelCombinationIdsAsync(profileId, levels) → combination IDs
LevelService.GetLevelCombinationListingsAsync(combinationIds) → list of Kvhxs
AddressRepository.GetByMultipleKvhx(listings, countryId, false) → ADDRESSES table
```

Level-based lookup bypasses the criteria TVP entirely and uses Kvhx-by-level instead.

---

## 4. ADDRESS RESTRICTION PATTERN

Three strategies (*Strategy Pattern*):

### `PositiveListAddressRestriction` (default)
```sql
INNER JOIN dbo.ProfilePositiveLists pl ON pl.ProfileId = @profileId AND pl.Kvhx = a.Kvhx
```
- ProfileId injected as SQL parameter
- Restricts to only addresses the profile has been granted access to
- No access granted = no rows returned from address query

### `MunicipalityPositiveListAddressRestriction` (UseMunicipalityPolList role)
```sql
INNER JOIN dbo.ProfilePosListMunicipalityCodes pmc 
    ON pmc.ProfileId = @profileId AND pmc.MunicipalityCode = a.MunicipalityCode
```
- Broader than address-level restriction
- Grants access to all addresses in approved municipalities

### `NoAddressRestriction` (HaveNoSendRestrictions role or profileId == 0)
- No JOIN added
- All addresses in `Addresses` table accessible to the profile
- Used for system profiles or emergency broadcast profiles

**Key fact:** The restriction is chosen in `AddressLookupService.GetSmsGroupAddressesFromPartialAddressesAsync` reading from `PermissionService` (cached 15 days). The choice is made ONCE per lookup call — not per address.

---

## 5. CRITICAL ADDRESS FLAG

`SmsGroupAddresses.IsCriticalAddress` — set when:
1. Profile has role `CanSendToCriticalAddresses`
2. `ICriticalAddressService.CheckCriticalAddresses(customerId, entries)` is called after address expansion
3. Marks addresses identified as critical (e.g. hospitals, emergency services) in a separate `CriticalAddresses` / `AddressVirtualMarkings` data set

Usage in lookup:
```csharp
where (!state.SendToCriticalAddressesOnly || (address.IsCriticalAddress ?? false))
```
If `SendToCriticalAddressesOnly=true` AND address is not marked critical → excluded from broadcast.

**Staleness risk:** Critical address status is saved at preload time. If an address is newly marked critical AFTER the SmsGroup's address preload → not picked up until SmsGroup is deleted and re-looked-up.

---

## 6. EXTERNAL DEPENDENCIES (ADDRESS DOMAIN)

| Service | Type | Used For | Called When |
|---|---|---|---|
| `DanishAddressImporter` | HTTP client (DAWA API) | Import DK addresses into `Addresses` table | BATCH JOB only |
| `DarFileDownloadImporter` | HTTP client (DAR file) | Import DK address file | BATCH JOB only |
| `IEjerfortegnelseAppService` | HTTP client | Import DK property owners into `AddressOwners` | BATCH JOB only |
| `IStatstidendeService` | HTTP client | Import DK corporate announcements (company status) | BATCH JOB only |
| `EndringslogsService` + `StoreService` (Kartverket) | HTTP client (Kartverket API) | Import NO addresses | BATCH JOB only |
| `LantmaterietImporter` (Lantmäteriet) | HTTP client (weekly API) | Import SE addresses — day-after-fetch lag | BATCH JOB only |
| AvoinData (Finland) | HTTP client | Import FI addresses | ⚠️ **CLOSED February 2025** — new FI source UNKNOWN |

**Finding:** ALL external address/owner API calls are import-time batch jobs. The SMS lookup pipeline makes ZERO external HTTP calls for address resolution in the DK/SE/FI path. Norway KRR/1881 are the ONLY potential real-time external lookups (not verified — see UNKNOWNS).

---

## 7. BLOCKING CALLS (FAILURE POINT)

**Found in `MessageService.cs` (lines 332, 345):**
```csharp
// GetCityAndStreetNames (line 332)
var kvhxs = _addressLookupService.GetKvhxFromPartialAddressAsync(
    profileId, countryId, new List<LookupAddress>(), smsGroupId, true)
    .GetAwaiter().GetResult();   // ← BLOCKING

// GetCityNames (line 345) — same pattern
var kvhxs = _addressLookupService.GetKvhxFromPartialAddressAsync(...)
    .GetAwaiter().GetResult();   // ← BLOCKING
```

These methods are called during SMS message template merge-field resolution (building city/street name strings for `{by}`, `{gade}` merge tags). The address lookup is async but is called synchronously. Risk: deadlock in ASP.NET thread pool under high concurrency.

**Found in address matchers:**
- `DanishAddressMatcher.cs` line 123
- `NorwegianAddressMatcher.cs` line 105
- `SwedishAddressMatcher.cs` line 116

All call `GetAllStreetsByZipAsync().GetAwaiter().GetResult()` in synchronous validation contexts.

---

## 8. OPEN UNKNOWNS

| ID | What | Impact |
|---|---|---|
| UNKNOWN-5 | Norway KRR, Norway 1881 processors — real-time external API or local cache? | HIGH for Norway scope |
| UNKNOWN-7 | Norwegian address residents + property owners processors (local vs external?) | MEDIUM |
| UNKNOWN-8 | PhoneNumbers import schedule — how frequent? How stale can teledata be? | HIGH for data quality |
| UNKNOWN-9 | `MunicipalityPositiveListAddressRestriction.GetTableJoins()` exact SQL (symmetric to PositiveList — inferred but not read) | LOW |
| UNKNOWN-NO | ~~NO/SE/FI address register import sources~~ CLOSED: NO=Kartverket, SE=Lantmäteriet. FI=AvoinData ⚠️ source CLOSED Feb 2025 — new FI import source unknown | HIGH — FI addresses may be stale/broken in production |

---

*Source archive: [/temp_history/temp_2026-04-12_wave1-wave2.md](/temp_history/temp_2026-04-12_wave1-wave2.md)*  
*See also: [sms-domain.md](sms-domain.md) · [lookup-pipeline.md](lookup-pipeline.md)*
