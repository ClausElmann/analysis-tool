# LookupImporter — Arkitektur & Design
**Generated:** 2026-04-16  
**Source:** Verificeret mod sms-service kode (Layer 0)  
**Purpose:** Selvstændigt .NET-projekt der henter data fra 3 Datafordeler-kilder, gemmer lokalt og synkroniserer til Simply.com  
**Status:** DESIGN — KLAR TIL IMPLEMENTATION

---

## Oversigt

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LookupImporter (.NET 10)                        │
│                       Console App / Worker Service                     │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │ DarImporter  │  │EjerImporter  │  │ CvrImporter  │                 │
│  │              │  │              │  │              │                 │
│  │ SFTP + ZIP   │  │ SFTP + ZIP   │  │ HTTP + ES    │                 │
│  │ System.Text  │  │ Newtonsoft   │  │ scroll API   │                 │
│  │ .Json        │  │ streaming    │  │              │                 │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                 │
│         │                 │                  │                         │
│         ▼                 ▼                  ▼                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              LocalDB: LookupImport (lokal SQL Server)           │   │
│  │  DarAdresse | DarHusnummer | DarNavngivenVej | DarPostnummer   │   │
│  │  Address_ST_Owners | AddressOwnersST | AddressOwners           │   │
│  │  CompanyRegistrations_Stage                                     │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│  ┌──────────────────────────────▼──────────────────────────────────┐   │
│  │           Build-Lookup Command (distillerings-step)             │   │
│  │  SELECT + JOIN + CAST → GreenAI_Lookup tabeller (lokalt)        │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│  ┌──────────────────────────────▼──────────────────────────────────┐   │
│  │           Sync Command (SqlBulkCopy → Simply.com)               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## De 3 Datafordeler-kilder (verificeret mod sms-service kode)

### Kilde 1: DAR — Danske Adresseregister

| Parameter | Værdi |
|-----------|-------|
| **Transport** | SFTP (SSH private key — ssh.com format!) |
| **Host** | `AppSetting.OwnerDatafordelerHost` (ID 154) — samme server som Ejerfortegnelse |
| **Username** | `AppSetting.OwnerDatafordelerUserName` (ID 155) |
| **SSH nøgle** | ssh.com format — **VIGTIGT**: ikke OpenSSH format. Se: https://github.com/sshnet/SSH.NET/issues/434 |
| **Fil-mønster** | `/DAR_*.zip` |
| **Fil-størrelse** | Baseline >1 GB (fuld), Delta <1 GB (inkrementel) |
| **Format** | ZIP indeholder 1 JSON-fil (ikke Metadata*.json) |
| **Library** | `Renci.SshNet` + `System.Text.Json` |
| **Lokal fallback** | `D:\Temp\DAR\` — hvis denne mappe eksisterer, bruges lokale filer |

**JSON-struktur (DarRootObject):**
```json
{
  "AdresseList":               [...],   // dør + etage, reference til Husnummer UUID
  "HusnummerList":             [...],   // husnummer + vejref + postnrref + koordinat
  "NavngivenVejList":          [...],   // vejnavn (UUID-baseret, ingen vejkode-INT)
  "PostnummerList":            [...],   // postnummer tekst
  "NavngivenVejKommunedelList":[...]    // bridge: vejUUID → kommunekode + vejkode-INT
}
```

**Entities der bruges (→ lokale tabeller):**

| DAR entity | Lokal tabel | Nøgle felter |
|------------|-------------|-------------|
| `NavngivenVejKommunedelList` | `DarNavngivenVejKommunedel` | `NavngivenVejId` (UUID), `KommuneKode`, `Vejkode` |
| `PostnummerList` | `DarPostnummer` | `Nr` (postnummer), `Navn` (by) |
| `HusnummerList` | `DarHusnummer` | `IdLokalId`, `HusnummerTekst`, `NavngivenVejId`, `PostnummerId`, `kommuneinddeling`, koordinater |
| `AdresseList` | `DarAdresse` | `IdLokalId`, `HusnummerId`, `EtageBetegnelse`, `DørBetegnelse`, `Status` |
| `NavngivenVejList` | `DarNavngivenVej` | `IdLokalId`, `Vejnavn` — **ingen vejkode-INT her** |

**Vejkode-INT** kommer fra `NavngivenVejKommunedelList.vejkode` — ikke fra `NavngivenVejList`.

---

### Kilde 2: Ejerfortegnelse — Matrikelregister

| Parameter | Værdi |
|-----------|-------|
| **Transport** | SFTP (SSH private key — samme server + nøgle som DAR) |
| **Fil-mønster** | `AppSetting.OwnerFilePattern` — zip-filer med ejer-JSON |
| **Format** | ZIP → JSON stream (Newtonsoft `JsonTextReader` — ikke System.Text.Json) |
| **Batch-størrelse** | 3000 records pr. BulkMerge |
| **Library** | `Renci.SshNet` + `Newtonsoft.Json` (streaming) |

**JSON-struktur (per ejendom):**
```json
{
  "properties": {
    "status": "gældende",           // filter: kun "gældende"
    "behandlingsID": "uuid",        // NULL → skip
    "faktiskEjerandel_taeller": 1,  // 0 → skip (aktiv ejendom uden ejer)
    "faktiskEjerandel_naevner": 2,
    "bestemtFastEjendomBFENr": 12345,
    "DARadresse": { "id_lokalId": "uuid" },    // reference til DAR
    "ejendePerson": {
      "navn": "Jens Jensen",
      "adresse": { "DARadresse": { "id_lokalId": "uuid" } }
    },
    "ejendeVirksomhed": {
      "attributes": {
        "CVRNummer": "12345678",
        "navn": "Firma A/S",
        "beliggenhedsadresse": { "DARadresse": { "id_lokalId": "uuid" } }
      }
    }
  }
}
```

**Filter (fra `ShouldProcessProperty`):**
- `status == "gældende"` ELLER `virkningFra/registreringFra` < 3 måneder gammel
- `behandlingsID` må ikke være null
- `faktiskEjerandel_taeller != 0` og `_naevner != 0` (for aktive)

**Pipeline:**
```
SFTP ZIP → JSON stream → Address_ST_Owners (batch 3000, BulkMerge)
  → UnionDataAndMoveToAddressOwners() per kommunekode
  → SwapTables(): AddressOwnersST ↔ AddressOwners
```

---

### Kilde 3: CVR — Virksomhedsregister

| Parameter | Værdi |
|-----------|-------|
| **Transport** | HTTP Elasticsearch scroll API |
| **Host** | `http://distribution.virk.dk` |
| **Auth** | Basic Authentication |
| **Index** | `cvr-permanent` |
| **Type** | `virksomhed` |
| **Scroll** | `"2m"` timeout, 500 records per batch |
| **Library** | `NEST` (Elasticsearch .NET client) |
| **Delta-strategi** | `sidstIndlaest >= DateLastUpdated` fra DB |

**Felter der hentes:**
```
cvrNummer                                    → CvrNumber
reklamebeskyttet                             → AdvertisingProtected  
virksomhedMetadata.nyesteNavn.navn           → CompanyName
virksomhedMetadata.nyesteBeliggenhedsadresse → adresse → Kvhx-opslag
virksomhedMetadata.sammensatStatus           → Status (NORMAL/OPHOERT)
virksomhedMetadata.nyesteHovedbranche        → IndustryCode + IndustryText
virksomhedMetadata.nyesteAarsbeskaeftigelse  → AnnualEmployment
virksomhedMetadata.nyesteKontaktoplysninger  → LatestContactInformation (JSON)
```

**Filter:** `nyesteBeliggenhedsadresse != null && nyesteNavn != null && kommune != null`

---

## Projekt-struktur (forslag)

```
c:\Udvikling\lookup-importer\
  LookupImporter.sln
  src/
    LookupImporter.Console/        ← entry point (Console App, .NET 10)
      Program.cs                   ← Commands: import-dar | import-ejere | import-cvr | build-lookup | sync
      appsettings.json
      appsettings.Development.json ← ikke i git
    LookupImporter.Core/           ← domain + interfaces
      Importers/
        IDarImporter.cs
        IEjerImporter.cs
        ICvrImporter.cs
      Distiller/
        ILookupDistiller.cs
      Sync/
        ILookupSyncer.cs
    LookupImporter.Infrastructure/  ← implementations
      Sftp/
        SftpDownloader.cs            ← Renci.SshNet wrapper
      Dar/
        DarImporter.cs               ← DAR JSON → lokal DB
        ReadModels/                  ← DarAdresse, DarHusnummer, etc.
      Ejere/
        EjerImporter.cs              ← Ejerfortegnelse JSON → lokal DB
        ReadModels/                  ← EjerfortegnelseProperties, etc.
      Cvr/
        CvrImporter.cs               ← Elasticsearch scroll → lokal DB
        ReadModels/                  ← Company, Vrvirksomhed, etc.
      Distiller/
        LookupDistiller.cs           ← SELECT+JOIN → GreenAI_Lookup tabeller
      Sync/
        LookupSyncer.cs              ← SqlBulkCopy → Simply.com
  tests/
    LookupImporter.Tests/
  scripts/
    Run-DarImport.ps1               ← kør DAR import
    Run-EjerImport.ps1              ← kør Ejer import
    Run-CvrImport.ps1               ← kør CVR import
    Build-LookupTables.ps1          ← distillér til GreenAI_Lookup
    Sync-ToSimply.ps1               ← push til Simply.com
```

---

## Commands (CLI interface)

```bash
# Importer alle 3 kilder (fuld baseline — første gang)
LookupImporter.Console import-dar --baseline
LookupImporter.Console import-ejere
LookupImporter.Console import-cvr

# Delta-opdatering (dagligt/ugentligt)
LookupImporter.Console import-dar --delta
LookupImporter.Console import-ejere --delta
LookupImporter.Console import-cvr --delta

# Distillér til GreenAI_Lookup lokalt
LookupImporter.Console build-lookup --country DK

# Sync til Simply.com
LookupImporter.Console sync --country DK

# Alt i ét (vedligehold)
LookupImporter.Console update-all --country DK
```

---

## Konfiguration (`appsettings.json`)

```json
{
  "Datafordeler": {
    "SftpHost": "",              ← fra sms-service AppSetting.OwnerDatafordelerHost
    "SftpUsername": "",          ← fra sms-service AppSetting.OwnerDatafordelerUserName
    "SshKeyPath": "",            ← lokal sti til .pem fil (ssh.com format!)
    "DarFilePattern": "DAR_",
    "EjerFilePattern": ""        ← fra sms-service AppSetting.OwnerFilePattern
  },
  "Virk": {
    "BaseUrl": "http://distribution.virk.dk",
    "Username": "",              ← credentials fra sms-service
    "Password": "",
    "CvrIndex": "cvr-permanent",
    "ScrollTimeout": "2m",
    "BatchSize": 500
  },
  "ConnectionStrings": {
    "LocalImport":  "Server=(localdb)\\MSSQLLocalDB;Database=LookupImport;...",
    "LocalLookup":  "Server=(localdb)\\MSSQLLocalDB;Database=GreenAI_Lookup;...",
    "SimplyLookup": ""           ← Simply.com connection string (user secrets)
  },
  "DebugMode": false,            ← true = max 1000 records per type
  "DebugMaxRecords": 1000
}
```

**Credentials i User Secrets (aldrig i git):**
```powershell
dotnet user-secrets set "Datafordeler:SftpHost" "<host>"
dotnet user-secrets set "Datafordeler:SftpUsername" "<user>"
dotnet user-secrets set "Virk:Username" "<user>"
dotnet user-secrets set "Virk:Password" "<password>"
dotnet user-secrets set "ConnectionStrings:SimplyLookup" "<connstr>"
```

---

## Lokale DB-tabeller (LookupImport)

Spejling af sms-service tabeller — kun de felter vi bruger:

```sql
-- Rå DAR (importeres direkte fra ZIP)
DarNavngivenVej           (IdLokalId PK, Vejnavn, Status, VirkningTil)
DarNavngivenVejKommunedel (IdLokalId PK, NavngivenVejId, KommuneKode, Vejkode, VirkningTil)
DarPostnummer             (IdLokalId PK, Nr, Navn, VirkningTil)
DarHusnummer              (IdLokalId PK, HusnummerTekst, NavngivenVejId, PostnummerId, 
                           KommuneinddelingId, AdgangspunktId, Status, VirkningTil)
DarAdresse                (IdLokalId PK, HusnummerId, EtageBetegnelse, DørBetegnelse, 
                           Status, VirkningTil)

-- Kommunekode-lookup (bygges af DarNavngivenVejKommunedel)
MunicipalityCodeLookup    (KommuneinddelingId PK, KommuneKode SMALLINT)

-- Ejer staging (populeres af EjerImporter)
Address_ST_Owners         (Id PK, BFENr, Kvhx, OwnerName, OwnerCvr, 
                           OwnerAddressKvhx, Status, ProcessingId)

-- Ejer produktions-tabel (efter swap)
AddressOwners             (Id PK, Kvhx, OwnerName, CompanyRegistrationId, 
                           OwnerAddressKvhx, CountryId, IsDoubled)

-- CVR
CompanyRegistrations      (Id PK, CountryId, Kvhx, Name, CompanyRegistrationId,
                           Active, Discarded, Status, IndustryCode, 
                           AnnualEmployment, AdvertisingProtected)
```

---

## Distillering til GreenAI_Lookup

Når lokale import-tabeller er populerede, kører `build-lookup` kommandoen:

```sql
-- 1. PostnummerLookup_DK — fra DarPostnummer
INSERT INTO [GreenAI_Lookup].[dbo].[PostnummerLookup_DK] (PostalCode, City)
SELECT Nr, Navn FROM [LookupImport].[dbo].[DarPostnummer]
WHERE VirkningTil IS NULL

-- 2. VejkodeLookup_DK — join via kommunedel-bridge
INSERT INTO [GreenAI_Lookup].[dbo].[VejkodeLookup_DK] (KommuneKode, Vejkode, Vejnavn)
SELECT DISTINCT kd.KommuneKode, kd.Vejkode, v.Vejnavn
FROM [LookupImport].[dbo].[DarNavngivenVejKommunedel] kd
JOIN [LookupImport].[dbo].[DarNavngivenVej] v ON v.IdLokalId = kd.NavngivenVejId
WHERE kd.VirkningTil IS NULL AND v.VirkningTil IS NULL

-- 3. AddressLookup_DK — join HusnummerList + AdresseList
INSERT INTO [GreenAI_Lookup].[dbo].[AddressLookup_DK]
    (Kvhx, Kvh, KommuneKode, Vejkode, Number, Letter, Floor, Door, PostalCode, Lat, Lng, IsActive)
SELECT
    dbo.BuildKvhx(mc.KommuneKode, kd.Vejkode, h.HusnummerTekst, a.EtageBetegnelse, a.DørBetegnelse) AS Kvhx,
    dbo.BuildKvh(mc.KommuneKode, kd.Vejkode, h.HusnummerTekst)                                      AS Kvh,
    mc.KommuneKode, kd.Vejkode,
    dbo.ExtractNumber(h.HusnummerTekst), dbo.ExtractLetter(h.HusnummerTekst),
    a.EtageBetegnelse, a.DørBetegnelse,
    p.Nr AS PostalCode,
    dbo.ExtractLat(h.AdgangspunktId), dbo.ExtractLng(h.AdgangspunktId),
    CAST(CASE WHEN a.Status = 3 THEN 1 ELSE 0 END AS BIT)
FROM [LookupImport].[dbo].[DarAdresse] a
JOIN [LookupImport].[dbo].[DarHusnummer] h ON h.IdLokalId = a.HusnummerId
JOIN [LookupImport].[dbo].[MunicipalityCodeLookup] mc ON mc.KommuneinddelingId = h.KommuneinddelingId
JOIN [LookupImport].[dbo].[DarNavngivenVejKommunedel] kd ON kd.NavngivenVejId = h.NavngivenVejId 
    AND kd.KommuneKode = mc.KommuneKode
JOIN [LookupImport].[dbo].[DarPostnummer] p ON p.IdLokalId = h.PostnummerId
WHERE a.VirkningTil IS NULL AND h.VirkningTil IS NULL

-- 4. OwnerLookup_DK
INSERT INTO [GreenAI_Lookup].[dbo].[OwnerLookup_DK]
    (Kvhx, OwnerName, OwnerCvr, OwnerAddressKvhx, CompanyRegistrationId, CompanyActive)
SELECT ao.Kvhx, ao.OwnerName, ao.CompanyRegistrationId,
       ao.OwnerAddressKvhx, ao.CompanyRegistrationId,
       ISNULL(cr.Active, 0)
FROM [LookupImport].[dbo].[AddressOwners] ao
LEFT JOIN [LookupImport].[dbo].[CompanyRegistrations] cr
    ON cr.CompanyRegistrationId = ao.CompanyRegistrationId
WHERE ao.IsDoubled = 0

-- 5. CvrCompany_DK
INSERT INTO [GreenAI_Lookup].[dbo].[CvrCompany_DK]
    (CvrNumber, CompanyName, AddressKvhx, CompanyRegistrationId, 
     IndustryCode, AdvertisingProtected)
SELECT CompanyRegistrationId, Name, Kvhx, CompanyRegistrationId,
       IndustryCode, AdvertisingProtected
FROM [LookupImport].[dbo].[CompanyRegistrations]
WHERE Active = 1 AND Discarded = 0
```

---

## Kvhx-beregning (fra sms-service `AddressHelper.CreateDawaKvhx`)

```csharp
// Format: {muni:d4}{street:d4}{nr padded 4}{floor padded 3}{door padded 4}
// Eksempel: "01010100__41__2__th"
// 
// HusnummerTekst = "12A" → number=12, letter="A"
// EtageBetegnelse = "2" → floor="2"
// DørBetegnelse = "th" → door="th"
//
// Padding-tegn: '_' (underscore) — ikke mellemrum
// Kommunekode: 4 cifre, zero-padded ("0101" for København)
// Vejkode: 4 cifre, zero-padded ("0100")
// Nummer: 4 tegn, left-padded med '_' ("__12")
// Etage: 3 tegn, left-padded med '_' ("__2")
// Dør: 4 tegn, left-padded med '_' ("__th")
```

---

## NuGet-afhængigheder

```xml
<PackageReference Include="Renci.SshNet" Version="2024.*" />
<PackageReference Include="Newtonsoft.Json" Version="13.*" />       <!-- Ejer streaming -->
<PackageReference Include="NEST" Version="7.*" />                   <!-- CVR Elasticsearch -->
<PackageReference Include="Microsoft.Data.SqlClient" Version="5.*" />
<PackageReference Include="Dapper" Version="2.*" />
<PackageReference Include="System.CommandLine" Version="2.*" />     <!-- CLI commands -->
```

---

## Vigtige fund fra sms-service kode

| Fund | Konsekvens |
|------|-----------|
| SSH nøgle SKAL være ssh.com format | OpenSSH format virker IKKE med Renci.SshNet — se issue #434 |
| DAR og Ejerfortegnelse bruger SAMME SFTP-server og SSH-nøgle | Én konfiguration dækker begge |
| Lokal fallback: `D:\Temp\DAR\` | Understøt lokal mappe — nyttig ved test |
| `DEBUG_MODE_LIMIT_RECORDS = 1000` | Implementér samme konstant til test |
| Ejer: Newtonsoft `JsonTextReader` streaming | System.Text.Json er IKKE brugt her — Newtonsoft nødvendig |
| CVR: Elasticsearch scroll med `sidstIndlaest` filter | Delta-import er billig — kør dagligt |
| Ejer batch: 3000 records pr. BulkMerge | Brug SqlBulkCopy med batchSize=3000 |
| DAR filstørrelse: baseline >1 GB, delta <1 GB | Size-based selektion — ikke filnavn-baseret |
| `EtageBetegnelse` / `DørBetegnelse` fra DarAdresse | Etage og dør kommer IKKE fra DarHusnummer |

---

## Sync til Simply.com

`LookupSyncer` kører SqlBulkCopy tabel for tabel:

```csharp
// Per tabel: TRUNCATE destination → SqlBulkCopy fra lokal GreenAI_Lookup
// Rækkefølge: PostnummerLookup → VejkodeLookup → AddressLookup → OwnerLookup → CvrCompany
// AddressLookup (~3.8M rækker) = størst — estimeret tid: 2-5 min ved 1 Gbit
// Kør manuelt eller via scheduled task ugentligt
```

---

## Åbne spørgsmål til Arkitekten

1. **Credentials:** Skal `lookup-importer` bruge sms-service's Datafordeler-credentials direkte, eller oprette eget abonnement på Datafordeler?
2. **SSH-nøgle format:** Nøglen i sms-service er i ssh.com format (gemt i Azure Blob). Hvor opbevares nøglen til lookup-importer? Lokal fil?
3. **CVR credentials:** Sms-service har hardkodede virk.dk credentials (`Blue_Idea_CVR_I_SKYEN`). Bruger vi samme, eller henter vi dem fra dig?
4. **Separat repo:** Skal `lookup-importer` ligge i sit eget git-repo (`c:\Udvikling\lookup-importer\`)?
5. **Sync-frekvens:** DAR dagligt, Ejer ugentligt, CVR dagligt — eller alt ugentligt til demo?

---

*Sidst opdateret: 2026-04-16 — verificeret mod DarFileDownloadImporter.cs + EjerfortegnelseAppService.cs + DanishCompanyRegistrationImporterService.cs*
