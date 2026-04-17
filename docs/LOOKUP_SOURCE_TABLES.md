# Layer 0 — sms-service Lookup Source Tables
**Generated:** 2026-04-16  
**Source:** `C:\Udvikling\sms-service\ServiceAlert.DB\Tables\*.sql`  
**Purpose:** Fuldt verificeret skema-analyse af alle tabeller der indgår i GreenAI_Lookup distillerings-pipeline  
**Status:** LAYER 0 — PRIMÆR SANDHED — MÅ IKKE GÆTTES, ALTID TRACET HER

---

## Oversigt — Tabel-kategorier

| Kategori | Tabeller | Rolle i pipeline |
|----------|----------|-----------------|
| **Processerede adresser** | `Addresses` | → `AddressLookup_DK` (PRIMÆR KILDE) |
| **Vejkoder** | `AddressStreets`, `AddressStreetCodes` | → `VejkodeLookup_DK` |
| **Postnumre** | `Addresses` (DISTINCT Zipcode/City) | → `PostnummerLookup_DK` |
| **Ejerfortegnelse** | `AddressOwners`, `AddressOwnersST` | → `OwnerLookup_DK` |
| **Ejer staging (rå)** | `Address_ST_Owners` | Mellemtrin — brug IKKE som kilde |
| **CVR register** | `CompanyRegistrations` | → `CvrCompany_DK` |
| **Rå DAR (uprocesseret)** | `DarAdresse`, `DarHusnummer`, `DarNavngivenVej` | Rådata — brug IKKE direkte |
| **Geografi** | `AddressGeographies` | Spatial index → evt. `AddressLookup_DK.Geo` |
| **Beboere (CPR)** | `People` | → evt. `PersonLookup_DK` (fremtidig) |
| **Telefonnumre** | `PhoneNumbers` | → evt. `PhoneLookup_DK` (fremtidig) |
| **Kommuner** | `Municipalities` | Reference/lookup |
| **Lande** | `Countries` | CountryId mapping |
| **BFE-links** | `AddressBfeToLocalIds`, `AddressBfeExclusions` | DAR-match hjælper — niche brug |
| **Virtuelle markringer** | `AddressVirtualMarkings` | Markering af virtuelle adresser |

---

## 1. `Addresses` — PRIMÆR ADRESSEKILDE

**Bruges til:** `AddressLookup_DK` + `PostnummerLookup_DK`  
**Filter for DK:** `WHERE CountryId = 1`  
**Aktive:** `WHERE DateDeletedUtc IS NULL`

```sql
CREATE TABLE [dbo].[Addresses] (
    [Id]                    INT              IDENTITY(1,1) NOT NULL,
    [Kvhx]                  NVARCHAR(36)     COLLATE Danish_Norwegian_CI_AI NOT NULL,  -- PK CLUSTERED
    [Kvh]                   NVARCHAR(36)     COLLATE Danish_Norwegian_CI_AI NULL,
    [Zipcode]               INT              NOT NULL,          -- postnummer som INT (→ CAST til NVARCHAR(4))
    [City]                  NVARCHAR(100)    COLLATE Danish_Norwegian_CI_AI NOT NULL,
    [LocationName]          NVARCHAR(100)    NULL,              -- stednavne (Greve Strand osv.)
    [Street]                NVARCHAR(200)    COLLATE Danish_Norwegian_CI_AI NULL,
    [Number]                INT              NULL,
    [Letter]                NVARCHAR(20)     COLLATE Danish_Norwegian_CI_AI NULL,
    [Floor]                 NVARCHAR(20)     COLLATE Danish_Norwegian_CI_AI NULL,
    [Door]                  NVARCHAR(20)     COLLATE Danish_Norwegian_CI_AI NULL,
    [Meters]                INT              NULL,              -- afstand til vejkante (ubrugt i lookup)
    [MunicipalityCode]      SMALLINT         NOT NULL,          -- kommunekode
    [StreetCode]            INT              NOT NULL,          -- vejkode
    [Latitude]              FLOAT(53)        NULL,
    [Longitude]             FLOAT(53)        NULL,
    [CountryId]             INT              NOT NULL,          -- 1=DK, 2=NO, 3=FI, 4=SE
    [DateLastUpdatedUtc]    DATETIME         NOT NULL,
    [AccessAddressId]       UNIQUEIDENTIFIER NULL,              -- DAR UUID (beholdes ikke i lookup)
    [Zone]                  NVARCHAR(100)    NULL,              -- byzone/sommerhus/landzone
    [DateLastUpdatedGisUtc] DATETIME         NULL,
    [OriginCode]            INT              NULL,
    [Status]                INT              NULL,              -- DAR status (3=aktiv)
    [ExtUUID]               NVARCHAR(36)     NULL,              -- eksternt UUID (ikke brugt i lookup)
    [ExtDetails]            NVARCHAR(30)     NULL,
    [DateDeletedUtc]        DATETIME         NULL,              -- NULL=aktiv, NOT NULL=slettet
    [MunicipalityName]      NVARCHAR(100)    NULL,
    [TaxeringId]            NVARCHAR(20)     NULL,
    [ExtUuidAsGuid]         UNIQUEIDENTIFIER NULL,
    [AddressType]           INT              NULL,
    CONSTRAINT [PkAddresses] PRIMARY KEY CLUSTERED ([Kvhx] ASC)
)
```

**Nøgle-indekser:**
- `PkAddresses` → `Kvhx` (clustered)
- `IX_Addresses_CountryId_Deleted_ZipCode_Number` → `CountryId, DateDeletedUtc, Zipcode, Number` INCLUDE(City, Street, Letter, Floor, Door, Kvh, Kvhx...)

**Distillerings-SQL til `AddressLookup_DK`:**
```sql
SELECT Kvhx, Kvh, MunicipalityCode, StreetCode,
       Number, Letter, Floor, Door,
       CAST(Zipcode AS NVARCHAR(4)) AS PostalCode,
       Latitude AS Lat, Longitude AS Lng,
       CAST(CASE WHEN DateDeletedUtc IS NULL THEN 1 ELSE 0 END AS BIT) AS IsActive
FROM [ServiceAlert].[dbo].[Addresses]
WHERE CountryId = 1
```

**Distillerings-SQL til `PostnummerLookup_DK`:**
```sql
SELECT CAST(Zipcode AS NVARCHAR(4)) AS PostalCode, MAX(City) AS City
FROM [ServiceAlert].[dbo].[Addresses]
WHERE CountryId = 1 AND Zipcode > 0
GROUP BY Zipcode
```

---

## 2. `AddressStreets` + `AddressStreetCodes` — VEJKODEREGISTER

**Bruges til:** `VejkodeLookup_DK`

### `AddressStreets`
```sql
CREATE TABLE [dbo].[AddressStreets] (
    [Id]        INT            IDENTITY(1,1) NOT NULL,  -- PK
    [CountryId] INT            NOT NULL,               -- 1=DK
    [Name]      NVARCHAR(200)  NULL,                   -- vejnavn
    [ZipCode]   INT            NOT NULL,               -- postnummer
    CONSTRAINT [PK_AddressStreets] PRIMARY KEY CLUSTERED ([Id] ASC)
)
-- UX_AddressStreets: UNIQUE(CountryId, ZipCode, Name)
```

### `AddressStreetCodes`
```sql
CREATE TABLE [dbo].[AddressStreetCodes] (
    [Id]               INT  IDENTITY(1,1) NOT NULL,
    [StreetId]         INT  NOT NULL,          -- FK → AddressStreets.Id
    [Streetcode]       INT  NOT NULL,          -- vejkode (SMALLINT i praksis)
    [MunicipalityCode] INT  NOT NULL,          -- kommunekode
    CONSTRAINT [PK_AddressStreetCodes] PRIMARY KEY CLUSTERED ([Id] ASC)
)
-- IX_AddressStreetCodes_MunCode_StreetCode: (MunicipalityCode, Streetcode) INCLUDE(StreetId)
```

**Distillerings-SQL til `VejkodeLookup_DK`:**
```sql
SELECT DISTINCT
    CAST(sc.MunicipalityCode AS SMALLINT) AS KommuneKode,
    sc.Streetcode AS Vejkode,
    s.Name AS Vejnavn
FROM [ServiceAlert].[dbo].[AddressStreetCodes] sc
JOIN [ServiceAlert].[dbo].[AddressStreets] s ON s.Id = sc.StreetId
WHERE s.CountryId = 1 AND s.Name IS NOT NULL
```

**Bemærk:** `AddressStreets.ZipCode` er INT — vejnavne kan have samme navn i flere postnumre/kommuner. `VejkodeLookup_DK` bruger kun `KommuneKode+Vejkode` som nøgle (composite PK), ikke postnummer.

---

## 3. `AddressOwners` — EJERFORTEGNELSE (PRODUKTIONS-TABEL)

**Bruges til:** `OwnerLookup_DK`  
**Filter for DK:** `WHERE CountryId = 1`  
**Note:** Denne tabel er **resultatet** af staging/swap — det er den aktive produktionstabel.

```sql
CREATE TABLE [dbo].[AddressOwners] (
    [Id]                    INT            IDENTITY(1,1) NOT NULL,  -- PK (ikke brugt i lookup)
    [EsrPropertyId]         INT            NOT NULL,          -- ESR ejendomsnummer (historisk)
    [PropertyOwnersId]      INT            NOT NULL,          -- intern ID
    [OwnerName]             NVARCHAR(300)  NOT NULL,          -- ejerens navn
    [OwnerStatus]           INT            NULL,              -- ejerstatus (int kode)
    [OwnerStatusText]       NVARCHAR(100)  NULL,              -- ejerstatus tekst
    [OwnerPartPercent]      FLOAT(53)      NULL,              -- ejerandel i procent
    [DateLastUpdatedUtc]    DATETIME       NULL,
    [Kvhx]                  NVARCHAR(36)   COLLATE Danish_Norwegian_CI_AI NULL,  -- ejendommens adresse
    [OwnerAddressKvhx]      NVARCHAR(36)   COLLATE Danish_Norwegian_CI_AI NULL,  -- ejerens bopæls-adresse
    [CountryId]             INT            NOT NULL,
    [MunicipalityCode]      SMALLINT       NOT NULL,
    [OwnerPart]             NVARCHAR(30)   NULL,              -- ejerandel som brøk ("1/2")
    [CompanyRegistrationId] NVARCHAR(50)   NULL,              -- CVR-nummer (NULL = privat ejer)
    [IsDoubled]             BIT            DEFAULT((0)) NOT NULL,  -- dublet-flag
    CONSTRAINT [PK_AddressOwners] PRIMARY KEY CLUSTERED ([Id] ASC)
)
-- IX_AddressOwners_Cvr: (CompanyRegistrationId)
-- SearchOwnersOnAddress_Index: (Kvhx) INCLUDE(OwnerName, OwnerAddressKvhx)
-- SearchOwnersOnAddress_Index2: (OwnerAddressKvhx) INCLUDE(OwnerName, Kvhx)
```

**Distillerings-SQL til `OwnerLookup_DK`:**
```sql
SELECT
    ao.Kvhx,
    ao.OwnerName,
    ao.CompanyRegistrationId         AS OwnerCvr,       -- NULL = privat ejer
    ao.OwnerAddressKvhx,
    ao.CompanyRegistrationId         AS CompanyRegistrationId,
    ISNULL(cr.Active, 0)             AS CompanyActive
FROM [ServiceAlert].[dbo].[AddressOwners] ao
LEFT JOIN [ServiceAlert].[dbo].[CompanyRegistrations] cr
    ON cr.CompanyRegistrationId = ao.CompanyRegistrationId
    AND cr.CountryId = 1
WHERE ao.CountryId = 1
  AND ao.IsDoubled = 0
```

**Vigtige observationer:**
- `CompanyRegistrationId = NULL` → privat ejer (person)
- `IsDoubled = 1` → dublet-post, skal filtreres fra
- Én ejendom (`Kvhx`) kan have **multiple ejere** — PK er `Id`, ikke `Kvhx`
- `OwnerAddressKvhx` → ejerens bopæl (FK til `Addresses`) → bruges til telefon-opslag

---

## 4. `AddressOwnersST` — STAGING TABEL (swap-target)

**Bruges IKKE som direkte kilde** — er swap-partner til `AddressOwners`.  
Identisk struktur som `AddressOwners`. Swap-processen: `AddressOwners → temp → AddressOwnersST → AddressOwners`.

---

## 5. `Address_ST_Owners` — RÅ EJER-STAGING (fra Ejerfortegnelse ZIP)

**Bruges IKKE som kilde** — er mellemtrin under import, populeres fra Datafordeler SFTP.  
Indeholder BFE-nummer-baserede rå data inkl. `OwnerCvr INT` (CVR som INT).

```sql
[BFENr]              INT              -- fast ejendoms nummer
[Kvhx]               NVARCHAR(36)     -- matchematch til Addresses
[OwnerName]          NVARCHAR(300)
[OwnerAddressKvhx]   NVARCHAR(36)
[OwnerCvr]           INT              -- CVR-nummer som INT (→ CompanyRegistrations via CAST)
[Status]             NVARCHAR(50)     -- "gældende" = aktiv
[ProcessingId]       UNIQUEIDENTIFIER -- batch-kørsel ID
```

---

## 6. `CompanyRegistrations` — CVR REGISTER

**Bruges til:** `CvrCompany_DK`  
**Filter:** `WHERE CountryId = 1 AND Active = 1 AND Discarded = 0`

```sql
CREATE TABLE [dbo].[CompanyRegistrations] (
    [Id]                          INT            IDENTITY(1,1) NOT NULL,
    [CountryId]                   INT            NOT NULL,
    [Kvhx]                        NVARCHAR(36)   COLLATE Danish_Norwegian_CI_AI NULL,  -- virksomhedens adresse
    [Name]                        NVARCHAR(300)  NOT NULL,          -- virksomhedsnavn
    [Address]                     NVARCHAR(300)  NOT NULL,          -- adresse som tekststreng (denorm)
    [Zipcode]                     INT            NOT NULL,
    [DateLastUpdatedUtc]          DATETIME       NOT NULL,
    [CompanyRegistrationId]       NVARCHAR(50)   NOT NULL,          -- CVR-nummer (PK i praksis)
    [AddressId]                   NVARCHAR(50)   NOT NULL,          -- ekstern adresse-ID
    [Active]                      BIT            NOT NULL,          -- 1 = aktiv virksomhed
    [AddressValid]                BIT            NULL,              -- adresse matchet til Kvhx
    [FromDate]                    DATE           NULL,
    [ToDate]                      DATE           NULL,
    [Status]                      NVARCHAR(100)  NOT NULL,          -- "NORMAL", "OPHOERT" osv.
    [IndustryCode]                NVARCHAR(50)   NULL,              -- branchekode (DB07)
    [IndustryText]                NVARCHAR(200)  NULL,              -- branchetekst
    [AnnualEmployment]            INT            NULL,              -- antal ansatte
    [Discarded]                   BIT            NOT NULL,          -- 1 = kasseret (doublet/fejl)
    [IndustryCodeId]              INT            NULL,              -- FK til IndustryCodes
    [IsDirty]                     BIT            NULL,              -- markeret til re-import
    [ReMatch]                     BIT            NULL,              -- markeret til re-match
    [AdvertisingProtected]        BIT            NULL,              -- reklamebeskyttelse
    [LatestContactInformation]    NVARCHAR(MAX)  NULL,              -- JSON blob (seneste kontakt)
    [ParentCompanyRegistrationId] NVARCHAR(50)   NULL,              -- moderselskabs CVR
    CONSTRAINT [PK_CompanyRegistrations] PRIMARY KEY CLUSTERED ([Id] ASC)
)
-- IX_CompanyRegistrations_CountryId_Active_CompanyRegistrationId: (CountryId,Active,CompanyRegistrationId) INCLUDE(Name)
-- IX_CompanyRegistrations_CountryId_Active_Kvhx: (CountryId,Active,Kvhx) INCLUDE(Name,CompanyRegistrationId)
-- IX_CompanyRegistrations_CountryId_Discarded_AddressValid_IndustryCode
-- IX_CompanyRegistrations_CountryId_Kvhx_IndustryCodeId: (CountryId,Kvhx,IndustryCodeId) INCLUDE(Name,CompanyRegistrationId)
-- IX_CompanyRegistrations_Kvhx: (Active,Kvhx) INCLUDE(Name,CompanyRegistrationId)
```

**Distillerings-SQL til `CvrCompany_DK`:**
```sql
SELECT
    CompanyRegistrationId   AS CvrNumber,
    Name                    AS CompanyName,
    Kvhx                    AS AddressKvhx,       -- NULL hvis adresse ikke matchet
    CompanyRegistrationId   AS CompanyRegistrationId,
    IndustryCode,           -- valgfrit: med eller uden
    AnnualEmployment,       -- valgfrit: med eller uden
    AdvertisingProtected    -- valgfrit: med eller uden
FROM [ServiceAlert].[dbo].[CompanyRegistrations]
WHERE CountryId = 1
  AND Active = 1
  AND Discarded = 0
```

**Overvej om grønne skema skal inkludere:**
| Felt | Formål | Anbefaling |
|------|--------|-----------|
| `IndustryCode` | Branchefiltrering (segmentering) | ✅ Med — nyttig til SMS-målretning |
| `AnnualEmployment` | Virksomhedsstørrelse | ⚠️ Valgfri |
| `AdvertisingProtected` | Reklamebeskyttelse | ✅ Med — lovkrav |
| `ParentCompanyRegistrationId` | Koncernstruktur | ❌ Udelad til demo |

---

## 7. Rå DAR-tabeller (bruges IKKE direkte i distillering)

Disse tabeller populeres af `DarFileDownloadImporter` fra Datafordeler SFTP.  
`Addresses`-tabellen er allerede de-normaliseret herfra. **Brug `Addresses`, ikke disse.**

### `DarAdresse`
```sql
[IdLokalId]           UNIQUEIDENTIFIER PK  -- DAR UUID for lejlighed/dør
[HusnummerId]         UNIQUEIDENTIFIER     -- FK → DarHusnummer
[AdresseBetegnelse]   NVARCHAR(500)        -- "Østergade 12, 2. th"
[EtageBetegnelse]     NVARCHAR(10)         -- "2", "st", "kl"
[DørBetegnelse]       NVARCHAR(10)         -- "th", "tv", "1"
[Status]              INT                  -- 3=aktiv
[VirkningTil]         DATETIME2            -- NULL=aktiv
```

### `DarHusnummer`
```sql
[IdLokalId]                UNIQUEIDENTIFIER PK
[HusnummerTekst]           NVARCHAR(10)        -- "12", "12A"
[NavngivenVejId]           UNIQUEIDENTIFIER    -- FK → DarNavngivenVej
[PostnummerId]             UNIQUEIDENTIFIER    -- FK (ikke direkte til postnr-tekst)
[AdgangspunktId]           UNIQUEIDENTIFIER    -- koordinat-reference
[AdgangsadresseBetegnelse] NVARCHAR(500)       -- "Østergade 12"
[Status]                   INT                 -- 3=aktiv
[VirkningTil]              DATETIME2           -- NULL=aktiv
```

### `DarNavngivenVej`
```sql
[IdLokalId]        UNIQUEIDENTIFIER PK   -- UUID (ingen vejkode-INT her!)
[Vejnavn]          NVARCHAR(255)
[Adresseringsnavn] NVARCHAR(255)         -- forkortet vejnavn
[Status]           INT
[VirkningTil]      DATETIME2             -- NULL=aktiv
```

**Vigtig:** `DarNavngivenVej` har **ingen vejkode** — det er UUID-baseret.  
Vejkoder (`MunicipalityCode + StreetCode`) kommer fra `AddressStreetCodes + AddressStreets`.

---

## 8. `People` — BEBOERREGISTER (CPR-baseret)

**Ikke i første pipeline** — fremtidig `PersonLookup_DK`.

```sql
[PersonNumber]   NVARCHAR(36)   -- CPR-lignende (hash eller pseudonym)
[Name]           NVARCHAR(100)
[BirthYear]      INT
[Kvhx]           NVARCHAR(36)   -- bopæl → FK Addresses
[MunicipalityCode] INT
[BirthDate]      DATE
```

---

## 9. `PhoneNumbers` — TELEFONNUMMERREGISTER

**Ikke i første pipeline** — fremtidig `PhoneLookup_DK`.

```sql
[SubscriberId]      INT         -- abonnent-ID
[NumberIdentifier]  BIGINT      -- telefonnummer (8 cifre DK)
[DisplayName]       NVARCHAR(100)
[PhoneNumberType]   INT         -- 1=fastnet, 2=mobil
[BusinessIndicator] BIT         -- 1=erhvervsnummer
[Kvhx]             NVARCHAR(36) -- adresse-match
[Kvh]              NVARCHAR(36)
[CountryId]         INT
[MunicipalityCode]  SMALLINT
```

---

## 10. `Municipalities` — KOMMUNEREGISTER

**Reference-tabel** — mapper `MunicipalityCode` til `MunicipalityName`.

```sql
[MunicipalityCode] SMALLINT      -- kommunekode (fx 101=København)
[CountryId]        INT
[Region]           NVARCHAR(50)  -- region (fx "Region Hovedstaden")
[MunicipalityName] NVARCHAR(50)
```

---

## 11. `Countries` — LANDE-MAPPING

**Reference** — `CountryId` værdier:

```sql
-- Verificér med: SELECT Id, TwoLetterIsoCode, Name FROM Countries
-- Forventet: 1=DK, 2=NO, 3=FI, 4=SE (skal verificeres mod faktisk data)
[Id]                 INT
[TwoLetterIsoCode]   NVARCHAR(2)   -- "DK", "NO", "FI", "SE"
[ThreeLetterIsoCode] NVARCHAR(3)
[NumericIsoCode]     SMALLINT
[PhoneCode]          INT           -- +45, +47, +358, +46
```

---

## 12. `AddressGeographies` — SPATIAL GEOMETRI

**Bruges IKKE i første pipeline** — spatial index til radius-søgning.

```sql
[Kvhx] NVARCHAR(36)    -- FK → Addresses (CASCADE)
[Geo]  geography       -- SQL Server geometry type (WGS84)
-- SIX_AddressGeographies_Geo: SPATIAL INDEX
```

**Alternativ:** `Addresses.Latitude + Longitude` dækker det meste uden spatial type.

---

## 13. `AddressVirtualMarkings` — VIRTUELLE ADRESSER

**Niche** — virtuelle adresser (fx postadressen for en bygning uden egentlig lejlighed).

```sql
[Kvhx]       NVARCHAR(36)
[CountryId]  INT
```

---

## 14. `AddressBfeToLocalIds` — BFE → DAR UUID MAPPING

**Intern hjælper** — bridge mellem `Address_ST_Owners.BFENr` og DAR `IdLokalId`.

```sql
[BfeNr]                  INT              PK   -- fast ejendoms nr
[LocationId]             UNIQUEIDENTIFIER      -- DAR adresse UUID
[HousenumberLocationId]  UNIQUEIDENTIFIER      -- DAR husnummer UUID
[NoResult]               BIT                   -- ingen match fundet
[BygningPaaFremmedGrund] BIT                   -- særlig ejendomstype
```

---

## Pipeline Beslutningsmatrix — Hvad bruges hvornår

```
DISTILLERING TIL GreenAI_Lookup_DK:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PostnummerLookup_DK   ←  Addresses (DISTINCT Zipcode/City, CountryId=1)
VejkodeLookup_DK      ←  AddressStreetCodes JOIN AddressStreets (CountryId=1)
AddressLookup_DK      ←  Addresses (CountryId=1, alle rækker inkl. slettet)
OwnerLookup_DK        ←  AddressOwners JOIN CompanyRegistrations (CountryId=1, IsDoubled=0)
CvrCompany_DK         ←  CompanyRegistrations (CountryId=1, Active=1, Discarded=0)

FREMTIDIG (ikke nu):
PersonLookup_DK       ←  People (CountryId=1)
PhoneLookup_DK        ←  PhoneNumbers (CountryId=1)

BRUGES ALDRIG SOM DIREKTE KILDE:
❌  DarAdresse           (rå, UUID-baseret, allerede processeret ind i Addresses)
❌  DarHusnummer         (rå, UUID-baseret)
❌  DarNavngivenVej      (rå, ingen vejkode-INT, UUID-baseret)
❌  Address_ST_Owners    (staging under import)
❌  AddressOwnersST      (swap-staging)
❌  AddressBfeToLocalIds (kun bro under DAR-match)
```

---

## CountryId Mapping (skal verificeres ved første kørsel)

```sql
-- Kør mod sms-service LocalDB for at verificere:
SELECT Id, TwoLetterIsoCode, Name FROM [ServiceAlert].[dbo].[Countries] ORDER BY Id
```

Forventet (men verificér!):

| Id | IsoCode | Land |
|----|---------|------|
| 1 | DK | Danmark |
| 2 | NO | Norge |
| 3 | FI | Finland |
| 4 | SE | Sverige |

---

*Sidst opdateret: 2026-04-16 — verificeret mod faktiske .sql filer i `ServiceAlert.DB/Tables/`*
