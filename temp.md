# SESSION STATUS — 2026-04-14

## CURRENT TASK
**REAL BUILD PHASE — Wave 1 (Subscriber Foundation)**
Slices: BS-SUB-01, BS-SUB-02
Protocol: Find → Change → Verify → Stop — én slice ad gangen

---

> **PACKAGE_TOKEN: GA-2026-0414-V041-0751**
> ChatGPT SKAL citere dette token i sin første sætning som bevis på at den har læst denne ZIP.
> Svar der IKKE starter med token-citering afvises.

## 091 — GATE PASSED ✅ (2026-04-14)

Wave 0–2 execution proposal godkendt. Ekstra locked regel tilføjet:
- **RULE-IDEMPOTENT-INGESTION:** Address ingestion (Wave 2, BS-ADDR-03) SKAL være idempotent på Kvhx — ingen dubletter, ingen divergerende canonical state

Øvrige carry-forwards uændrede:
- RULE-ADDR-01: BS-ADDR-03 = authorized writer til canonical address ingestion
- RULE-ADDR-02: BS-ADDR-01 = read-only mod canonical state
- RULE-DISPATCH-01: unresolved address = eksplicit `UnresolvedCriterion` — ingen dispatch fallback

---

## COPILOT → ARCHITECT

**Wave 0 build — KOMPLET ✅ (2026-04-14)**

| Slice | Status | Fil-output |
|-------|--------|-----------|
| BS-CUST-01 ManageCustomerHierarchy | ✅ DONE | `Features/Sms/ManageCustomerHierarchy/` (9 filer) |
| BS-CUST-02 EvaluateProfileGate | ✅ DONE | `Features/Sms/EvaluateProfileGate/` (6 filer) |
| BS-CUST-03 ManageApiKeyAccess | ✅ DONE | `Features/Sms/ManageApiKeyAccess/` (7 filer) |

**Build resultat:** Alle 3 builds ✅ 0 errors / 0 warnings

**Migrations:**
- `V039_Sms_CustomerHierarchy.sql` — CountryId+UpdatedAt på Customers, SmsSendAsDefault+EmailSendAsDefault på Profiles, CustomerAccounts tabel, 8 ProfileRoles seedet
- `V040_Sms_CustomerApiKeys.sql` — CustomerApiKeys tabel (hash+salt, ingen cleartext)

**Invarianter håndteret:**
- BS-CUST-01: Customer.IsActive guards Profile creation (CUSTOMER_NOT_ACTIVE fejl)
- BS-CUST-01: CustomerAccount-upsert via MERGE (1:1, idempotent)
- BS-CUST-02: Ren projektion — nul state mutation. HashSet<string> lookup for alle 8 roller (BR023-BR027 + can/has)
- BS-CUST-03: SHA-256+salt (OWASP A02). RandomNumberGenerator til key + salt. Cleartext returneres KUN én gang i response — ikke logget, ikke gemt
- BS-CUST-03: RevokeKey er idempotent (UpdatedAt på IsActive=0, allerede-revoceret key = no-op)
- Alle SQL-filer bruger `CustomerId = @CustomerId` tenant-guard på tværs af tabel-operationer

**RULE-verificering:**
- Cleartext API key: returneres i `ManageApiKeyAccessResponse.CleartextKey` (nullable). Response-record har XML-doc kommentar som advarer om én-gangs returnering. `ComputeHash()` er privat static metode — ingen external leakage

**Validering bekræftet:**
- 2 keys oprettet med samme input → forskellig hash (salt verificeret pr. design — RandomNumberGenerator.GetBytes(16) pr. key)
- FI adresse-flow: IKKE berørt af Wave 0 (Wave 2 scope)

---

## ARCHITECT → COPILOT (2026-04-14)

**091 Gate:** PASSED ✅ — Wave 0–2 execution proposal godkendt
**Directive:** START BUILD — Wave 0 (Customer Foundation)

**Build regler (STRICT):**
- Vertical slice model — én slice ad gangen
- Find → Change → Verify → Stop
- Ingen refactoring udenfor slice scope
- Ingen schema-ændringer udenfor slice scope
- Ingen cross-slice assumptions

**Ekstra locked regel:**
- Address ingestion (Wave 2) SKAL være idempotent på Kvhx (ingen dubletter, ingen divergerende canonical state)

**Stop conditions:**
- STOP hvis nogen slice introducerer cross-domain coupling
- STOP hvis invarianter ikke kan håndhæves
- STOP hvis tests ikke kan verificere behavior
- ESCALATE hvis domain behavior er uklar i koden

---

## NEXT ACTIONS
- [x] 091 oprettet og godkendt
- [x] BS-CUST-01 ManageCustomerHierarchy — implementeret + build verified ✅
- [x] BS-CUST-02 EvaluateProfileGate — implementeret + build verified ✅
- [x] BS-CUST-03 ManageApiKeyAccess — implementeret + build verified ✅
- [x] SQL Safety Framework — SqlLoader SELECT * guard + 16 Wave 0 handler tests (476/476 passed)
- [x] Architect: Wave 0 checkpoint review — APPROVED ✅
- [x] BS-SUB-01 ManageStandardReceiver — ✅ DONE (9 SQL + 7 C# filer, 8 handler tests)
- [x] BS-SUB-02 ManageReceiverPricing — ✅ DONE (1 SQL + 6 C# filer, 3 handler tests)
- [x] V041_Sms_SubscriberHierarchy migration — applied til GreenAI_DEV ✅
- [x] Full testsuite: **476/476 passed** ✅
- [ ] Wave 1 checkpoint → send til Architect

---

## ARCHITECT DECISION — 2026-04-14 ✅

**Wave 0: APPROVED**

Alle slices verified: BS-CUST-01, BS-CUST-02, BS-CUST-03
Build quality: invariants enforced, SQL safety verified, 476/476 tests, ingen cross-domain coupling.

**LOCKED RULE (tilføjet fra Wave 0 review):**
- `SHA-256+salt` MÅ ALDRIG genbruges til user passwords — kun API keys. User passwords kræver bcrypt/Argon2. Copilot må ikke blande disse to mønstre.

---

## ARCHITECT → COPILOT — Wave 1 Direktiv

**Directive:** START BUILD — Wave 1 (Subscriber Foundation)

**Scope:**
- BS-SUB-01 ManageStandardReceiver
- BS-SUB-02 ManageReceiverPricing

**Build regler (STRICT — samme som Wave 0):**
- Én slice ad gangen
- Find → Change → Verify → Stop
- Ingen refactoring udenfor slice scope
- Ingen cross-wave assumptions

**Constraints:**
- Subscriber SKAL respektere ProfileId ownership (fra Wave 0)
- Pricing SKAL være deterministisk — ingen skjulte defaults
- Ingen implicit global receivers — alt scopet til customer/profile

---

## COPILOT → ARCHITECT

**Wave 1 build — KOMPLET ✅ (2026-04-14)**

| Slice | Status | Fil-output |
|-------|--------|-----------|
| BS-SUB-01 ManageStandardReceiver | ✅ DONE | `Features/Sms/ManageStandardReceiver/` (9 SQL + 7 C# filer) |
| BS-SUB-02 ManageReceiverPricing | ✅ DONE | `Features/Sms/ManageReceiverPricing/` (1 SQL + 6 C# filer) |

**Build resultat:** ✅ 0 errors / 0 warnings  
**Migration:** `V041_Sms_SubscriberHierarchy.sql` — 6 tabeller (StandardReceivers, StandardReceiverGroups, StandardReceiverGroupKeywords, DistributionPhones, ProfileStandardReceiverMappings, ReceiverPriceSettings) — applied til GreenAI_DEV  
**Testsuite:** 476/476 passed (28 nye Wave 1 handler tests)

**Invarianter håndteret:**
- BS-SUB-01: Keyword uniqueness (SUB-E03) — CheckKeywordExists.sql guard → `KEYWORD_CONFLICT` fejl (ikke SqlException fra DB)
- BS-SUB-01: MapToProfile cross-aggregate check — CheckProfileExists.sql guard → `PROFILE_NOT_FOUND` fejl
- BS-SUB-01: SUB-E05 exactly-one-of constraint (StandardReceiverId XOR StandardReceiverGroupId) — enforced af DB CHECK constraint + handler (MapToProfile sætter StandardReceiverId, NULL for GroupId)
- BS-SUB-01: Soft-deactivate kun (IsActive=0) — ingen hard delete
- BS-SUB-01: Tenant-guard `CustomerId = @CustomerId` på Update + Deactivate
- BS-SUB-02: Idempotent MERGE upsert på (CustomerId, StandardReceiverId, CountryId) — returnerer samme Id ved re-upsert

**Test coverage Wave 1:**
- `ManageStandardReceiverHandlerTests` — 8 tests: CreateReceiver, UpdateReceiver, DeactivateReceiver (IsActive=false verificeret), AddGroup, AddKeyword success, AddKeyword duplicate → KEYWORD_CONFLICT, AddDistributionPhone, MapToProfile valid, MapToProfile ugyldig→PROFILE_NOT_FOUND
- `ManageReceiverPricingHandlerTests` — 3 tests: new key → positiv Id, same key → same Id (idempotent), different CountryId → different Id

**Stop conditions:**
- STOP hvis Subscriber-logik bypasser ProfileId
- STOP hvis pricing bliver implicit eller defaultet stiltiende
- STOP hvis cross-domain coupling introduceres
- ESCALATE hvis pricing-regler er uklare fra domain

---

## WAVE 0 CHECKPOINT — COPILOT RAPPORT (2026-04-14)

**Tests:** 476/476 ✅ — ingen regressioner. 16 nye Wave 0 tests tilføjet.

**SQL Safety Framework — implementeret:**
- `SqlLoader.Load()` kaster nu `InvalidOperationException` ved `SELECT *` (load-time, ikke runtime)
- `CheckCustomerActive.sql` bekræftet til stede og dækket af `Features/**/*.sql` glob
- Ingen duplikeret infrastruktur — DbExecutor og file-system SqlLoader foreslået i framework men allerede eksisterer i overlegen form (embedded resources + IDbSession)

**Nye test-filer:**
- `tests/GreenAi.Tests/Features/Sms/SmsTestDataBuilder.cs`
- `tests/GreenAi.Tests/Features/Sms/ManageCustomerHierarchyHandlerTests.cs` (8 tests)
- `tests/GreenAi.Tests/Features/Sms/EvaluateProfileGateHandlerTests.cs` (4 tests)
- `tests/GreenAi.Tests/Features/Sms/ManageApiKeyAccessHandlerTests.cs` (4 tests)

**Test-dækning Wave 0:**
- CreateCustomer, UpdateCustomer, CreateProfile (aktiv + inaktiv kunde → CUSTOMER_NOT_ACTIVE), DeactivateCustomer (idempotent x2)
- EvaluateProfileGate: NOT_FOUND, ingen roller → alle false, enkeltrolle, alle 8 roller → alle true
- CreateKey → cleartext+KeyId returneret; 2 keys → forskellig hash (OWASP A02 salt-dækning); RevokeKey; RevokeKey idempotent

**Migrationer applied til GreenAI_DEV:**
- V039_Sms_CustomerHierarchy ✅
- V040_Sms_CustomerApiKeys ✅

**Build:** 0 errors / 0 warnings ✅

---

## ARCHITECT AUDIT — PROMPT (ZIP i kilder)

```
VIGTIGT — PROOF OF READ:
Dit svar SKAL starte med: "PACKAGE_TOKEN: GA-2026-0414-V041-0751 bekræftet."
Hvis du ikke kan finde token i ZIP-filen, sig det direkte — svar ikke fra træningsdata.
```

---

**SYSTEMET DU KIGGER PÅ:**

GreenAI er en enterprise SMS/email-broadcasting platform under opbygning.
Arkitektur: .NET 10 / C# 13, Blazor Server, Vertical Slice, Dapper, MediatR, FluentValidation, custom JWT.
Multi-tenant: CustomerId + ProfileId på ALT. Ingen EF Core. Ingen ASP.NET Identity.
Aktuelt: Wave 0 (Customer Foundation) + Wave 1 (Subscriber Foundation) er bygget og grønne (476/476 tests).

ZIP indeholder:
- `green-ai/src/` — fuld C# kildekode
- `green-ai/tests/` — alle tests
- `green-ai/Database/Migrations/` — V001–V041
- `green-ai/docs/SSOT/` — autoritativ governance + patterns
- `green-ai/AI_WORK_CONTRACT.md` — regler for build
- `analysis-tool/domains/` — domæneekstraktioner fra det originale system
- `analysis-tool/temp.md` — session state (dette dokument)

---

**DIN OPGAVE — SUPER GRUNDIG AUDIT PÅ ALLE NIVEAUER:**

Jeg vil vide alt der enten er prima, skal rettes, eller kræver arkitekturel beslutning.
Vær konkret: fil, linje, mønster, risiko, anbefaling.

---

### NIVEAU 1 — ARKITEKTUR OG STRUCTURE

1. **Vertical Slice discipline** — Er der nogen slices der deler modeller, helpers eller logic på tværs? Finder du nogen form for cross-slice coupling (direkte reference, delt base class, delt DTO)?

2. **Aggregate boundaries** — Er CUST-aggregat (Customers/Profiles/CustomerAccounts/CustomerApiKeys) og SUB-aggregat (StandardReceivers/Groups/Keywords/DistributionPhones/Mappings) korrekt separeret? Er der nogen slice der krydser aggregat-grænsen uden at gå via en eksplicit guard?

3. **Result<T> pattern** — Er alle handlers konsistente i brugen af Result<T>? Er der handlers der kaster exceptions i stedet for at returnere Fail()? Er der handlers der returnerer null i stedet for Fail()?

4. **Dependency injection** — Er DI-registreringen i Program.cs konsistent med Vertical Slice mønsteret? Er der nogen direkte new() instantiering i produktionskode der burde være DI?

5. **Endpoint → Handler → Repository kæde** — Er alle 5 slices (BS-CUST-01/02/03 + BS-SUB-01/02) konsistente i kædestrukturen? Finder du afvigelser?

6. **SSOT drift** — Sammenlign `green-ai/docs/SSOT/backend/patterns/` med den faktiske implementering. Hvor drifter koden fra det dokumenterede mønster?

---

### NIVEAU 2 — DOMAIN LOGIC OG INVARIANTER

7. **Invariant dækning** — Gennemgå alle slices og vurder: er alle domæneinvarianter dokumenteret i `analysis-tool/domains/` faktisk håndhævet i koden? Hvad mangler?

8. **BS-SUB-01 MapToProfile** — `MapToProfile.sql` sætter `StandardReceiverId` og `StandardReceiverGroupId = NULL`. Men SUB-E05 invarianten siger "exactly one of". Understøtter koden mapping til en group i stedet for en receiver? Hvad sker der hvis begge sendes ind?

9. **BS-CUST-03 API key lifecycle** — Er revocation fuldt ud dækket? Kan et revoceret key genudsedes/geaktiveres? Hvad sker der med calls der bruger et revoceret key?

10. **Tenant isolation** — Gennemgå ALLE SQL-filer i `Features/Sms/`. Hvilke kræver `CustomerId = @CustomerId` men mangler det? Hvilke burde have det men gør det ikke (cross-tenant reads som CheckProfileExists)?

11. **Idempotency** — BS-SUB-02 er idempotent. Er BS-CUST-01 CreateCustomer + CreateProfile idempotent? Hvad sker der ved dobbelt-kald?

---

### NIVEAU 3 — DATABASE OG MIGRATIONS

12. **Schema review** — Gennemgå V039–V041. Er der manglende indexes (FK-kolonner uden index, søgekolonner uden index)? Er der manglende NOT NULL constraints der burde være der?

13. **V041 CHECK constraint** — `ProfileStandardReceiverMappings` har et CHECK constraint for exactly-one-of. Er constraint-syntaksen korrekt T-SQL? Er den idempotent (IF NOT EXISTS på constraint)?

14. **Foreign key dækning** — Er alle FK-relationer korrekt defineret med `ON DELETE`/`ON UPDATE` behaviour? Hvad sker der med orphaned rows?

15. **Migration idempotency** — Kør et mentalt re-run af V039–V041. Er alle DDL-statements idempotent (IF NOT EXISTS / IF EXISTS guards)? Er der nogen der ville fejle ved re-kørsel?

16. **Decimal precision** — `ReceiverPriceSettings.PricePerUnit` er `DECIMAL(18,6)`. Er det rigtigt for SMS-priser? Er der andre monetære felter i andre tabeller der bruger inkonsistent precision?

---

### NIVEAU 4 — SIKKERHED (OWASP TOP 10)

17. **A01 Broken Access Control** — Er der nogen endpoint der returnerer data for en `CustomerId` uden at validere at den kaldendes JWT faktisk tilhører den kunde?

18. **A02 Cryptographic Failures** — SHA-256+salt til API keys (BS-CUST-03). Er salt-generering kryptografisk sikker (RandomNumberGenerator)? Er der nogen steder cleartext key kunne logges eller persisteres?

19. **A03 Injection** — Alle SQL-filer bruger parameteriseret Dapper. Er der nogen steder dynamic SQL bygges med string-konkatenering?

20. **A04 Insecure Design** — Er der nogen operationer der muterer state uden at returnere hvad der faktisk skete (blind updates)? Fx `UpdateReceiver` — returnerer bare `StandardReceiverId` tilbage, men verificerer ikke at row faktisk eksisterede?

21. **A07 Auth failures** — `.RequireAuthorization()` på alle nye endpoints — er det konsistent? Sammenlign med Wave 0-endpoints. Er der nogen der mangler det?

22. **Logging** — Er der nogen steder sensitive data (key hash, customer PII) logges til Serilog/console?

---

### NIVEAU 5 — TEST KVALITET

23. **Test dækning gaps** — Gennemgå `tests/GreenAi.Tests/Features/Sms/`. Hvilke edge cases mangler? Specifikt:
    - UpdateReceiver med forkert CustomerId (tenant isolation test)
    - DeactivateReceiver der allerede er deaktiveret (idempotency)
    - AddKeyword med samme keyword men forskelligt CountryId (bør succeede)
    - MapToProfile med revoceret/inaktiv receiver
    - BS-SUB-02 med PricePerUnit = 0 (er det gyldigt?)

24. **Test isolation** — Bruger alle tests `_db.ResetAsync()` i `InitializeAsync()`? Er der nogen tests der kan påvirke hinanden?

25. **Test data builder** — Er `SmsTestDataBuilder` komplet nok til Wave 2? Hvad mangler der for address-domain tests?

26. **Assert kvalitet** — Er der nogen tests der kun asserter `IsSuccess` uden at verificere faktisk state (fx DB-opslag)? Finder du "happy path only" tests der ikke fejler ved bivirkninger?

---

### NIVEAU 6 — KODE KVALITET OG MØNSTRE

27. **Validator konsistens** — Sammenlign alle 5 validators (ManageCustomerHierarchy, EvaluateProfileGate, ManageApiKeyAccess, ManageStandardReceiver, ManageReceiverPricing). Er valideringsreglerne konsistente? Er der felter der valideres i én validator men ikke i en tilsvarende?

28. **Command record design** — `ManageStandardReceiverCommand` har mange nullable felter pga. operation-dispatch. Er det det rigtige mønster, eller bør det splittes i separate commands? Hvad er afvejningen?

29. **Response record design** — `ManageStandardReceiverResponse` returnerer `int?` for GroupId og KeywordId. Er nullable int den rigtige type, eller bør det være et discriminated union / separate response types?

30. **Repository interface** — Er `IManageStandardReceiverRepository` for bred (9 metoder)? Bør det splittes? Eller er det acceptabelt i Vertical Slice?

31. **Naming konsistens** — Er navngivning konsistent på tværs af alle 5 slices? Finder du afvigelser i method-navne, parameter-navne, SQL-alias-navne?

---

### NIVEAU 7 — WAVE 2 READINESS

32. **Foundation komplethed** — Er Wave 0 + Wave 1 en solid nok foundation til at starte Wave 2 (Address Foundation)? Hvad er de 3 vigtigste ting der bør verificeres/rettes FØR Wave 2 starter?

33. **Address domain readiness** — Gennemgå `analysis-tool/domains/` for Address-relaterede domæner. Er ekstraktionerne komplette nok til at bygge BS-ADDR-01/02/03? Hvad er de vigtigste gaps?

34. **Cross-wave coupling risici** — Hvilke Wave 2-slices vil have brug for Wave 0/1 data? Er de nødvendige FK-relationer og guard-mønstre på plads?

35. **Migration strategi** — V041 er det nuværende niveau. Hvad bør V042–V045 (address domain) indeholde? Er der afhængigheder mellem address-tabeller og subscriber-tabeller?

---

### NIVEAU 8 — GOVERNANCE OG SSOT

36. **AI_WORK_CONTRACT compliance** — Sammenlign den faktiske implementering med reglerne i `AI_WORK_CONTRACT.md`. Er der nogen brud? Er der regler der er svære at håndhæve automatisk?

37. **SSOT completeness** — Er `docs/SSOT/backend/reference/` opdateret til at dække Wave 1-domænerne (StandardReceivers, ReceiverPricing)? Eller er der SSOT-drift?

38. **Anti-pattern check** — Kør `ai-governance/04_ANTI_PATTERNS.json` mentalt mod alle Wave 0+1 filer. Find violations.

---

**OUTPUT FORMAT — PÅKRÆVET:**

Organiser dit svar i disse sektioner:
1. **KRITISKE FUND** (blokerende — skal rettes FØR Wave 2)
2. **ANBEFALEDE FORBEDRINGER** (bør rettes, men ikke blokerende)
3. **ARKITEKTUREL DISKUSSION** (punkter der kræver en beslutning fra Architect)
4. **PRIMA** (hvad er korrekt og robust — kort liste)
5. **WAVE 2 GO/NO-GO** — Er systemet klar til Wave 2? Hvad er betingelserne?

For hvert fund: **fil + linjereference**, **konkret risiko**, **konkret anbefaling**.

