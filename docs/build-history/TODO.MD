Rangering: Impact vs Arbejdstid

## Status
Opdateret: 2026-04-04
Legend: ✅ Færdig | 🔄 Delvist | ⬜ Ikke startet

---

⚡ S-TIER — Gøres nu (høj impact, lille arbejde)
Rank	#	Task	Impact	Tid	Status
1	50	Tilføj "Verify med SQL FØR du antager noget" til AI_WORK_CONTRACT.md	AI stopper med at gætte DB-state	10 min	✅ Gjort — VERIFY-FØR-ANTAG sektion tilføjet
2	28	[ServiceName] prefix i ALLE log-beskeder — [UserService] Creating...	Dramatisk nemmere grep i Serilog	30 min	✅ Gjort — LoggingBehavior logger allerede [MediatR] {RequestName} for alle handlers
3	45/46	Exit-code kontrakt i PS-scripts — exit 1 ved fejl, aldrig soft-failure	Fejl opdages garanteret	30 min	✅ Gjort — $ErrorActionPreference = "Stop" tilføjet til 3 scripts
4	36	[Collection("GreenAI")] på ALLE test-klasser	Stopper parallel DB-corruption nu	15 min	✅ Gjort — audit viste at alle DB-tests allerede har [Collection], unit tests skal ikke
5	22	OnParametersSetAsync + StateHasChanged() i alle Blazor-komponenter (audit)	E2E stabilitet, stop race conditions	1 time	✅ Gjort — alle sider bruger OnAfterRenderAsync korrekt, ingen violations

🥇 A-TIER — Gøres denne uge (høj impact, moderat arbejde)
Rank	#	Task	Impact	Tid	Status
6	18/19	data-testid audit — tilføj manglende på ALLE interaktive elementer + {entity}-row-{id}	E2E tests kan skrive stabile selectors	2 timer	✅ Gjort — open/delete IconButtons i UserList+ProfileList, tables+chip i UserDetail
7	11–13	Drawer-pattern SSOT skrives til patterns — PatternC, clamp() bredde, row-click	AI ved hvad den skal gøre ved næste drawer	1 time	✅ Gjort — detail_navigation_architecture tilføjet til mudblazor-conventions.md
8	27	Correlation ID i fejl-svar — Guid.NewGuid() i alle 500-svar	Debug på prod uden Serilog-research	1 time	✅ Gjort — errorId i ToHttpResult 500-case + UseExceptionHandler med JSON+errorId
9	24/25/26	IsLoading + drawer-loading-indicator + ErrorMessage pattern i ALLE Blazor-komponenter	Stabile E2E, ingen flaky timing-fejl	2 timer	🔄 I gang — Index.razor + UserDetail.razor rettet; ProfileDetail + AdminSettings OK
10	29/30	DTO-navngivning audit — CreateRequest, Response, FilterDto konsekvent	AI laver rigtige navne første gang	1 time	✅ Gjort — PingCommand→PingQuery; to-tier XxxRow/XxxResponse konvention dokumenteret i handler-pattern.md
11	37/38	Minimum 5 test-scenarier per endpoint — 404, 400, 403, 500 FK, happy path	API-bugs fanges INDEN E2E kører	3 timer	✅ Gjort — alle endpoints har 5+ scenarier; DatabaseMigrator-fejl rettet (DB project er master)
12	43	AssertNoMissingLabelsAsync i ALLE resterende sider og features	Ingen rå label-keys når projektet vokser	1 time	✅ Gjort — LabelCoverageE2ETests.cs: UserProfile, AdminUsers, AdminSettings

🥇 A-TIER EKSTRA — Tooling adopteret fra NeeoBovisWeb
Rank	#	Task	Status
A1	—	Backend.psm1 — Start/Stop/Build/Wait backend	✅ Gjort — scripts/modules/Backend.psm1
A2	—	Http.psm1 — Auth + GET/POST/PUT/DELETE wrappers	✅ Gjort — scripts/modules/Http.psm1
A3	—	Database.psm1 — Invoke-DatabaseQuery/NonQuery	✅ Gjort — scripts/modules/Database.psm1
A4	—	Output.psm1 — Write-Header/Success/Failure/Step	✅ Gjort — scripts/modules/Output.psm1
A5	—	Test-SqlStatement.ps1 — SQL pre-validering (10x hurtigere)	✅ Gjort — scripts/debug/Test-SqlStatement.ps1
A6	—	tool-registry.yaml — autoritativ tool-oversigt	✅ Gjort — ai-governance/tool-registry.yaml

🥈 B-TIER — Gøres næste sprint (medium impact, moderat arbejde)
Rank	#	Task	Impact	Tid	Status
13	5	Audit trail kolonner på alle main-tables — CreatedAt, UpdatedAt, DeletedAt	Retrospektiv debugging mulig	2 timer	🔄 Delvist — CreatedAt allerede overalt; UpdatedAt på ApplicationSettings+EmailTemplates allerede der; DeletedAt kræver soft-delete design-beslutning — udskudt til feature-behov
14	3/4	SQL-indeks på alle FK-kolonner + soft-delete kolonner	Query-performance — mærkes når data vokser	2 timer	✅ Gjort — V027_FkIndexes.sql: 7 indeks på de mest brugte FK-kolonner (Profiles, UserCustomerMemberships, UserRefreshTokens, PasswordResetTokens, ProfileUserMappings, AuditLog)
15	14/15	Delete-knap disabled under redigering + ShowMessageBox confirmation	Accidental-delete prevention	1 time	⬜ — Lav AI-autonomi-værdi; implementeres når konkret delete-feature bygges
16	16/17	Color system enforced (Success=Gem, Error=Slet) + Drawer vs Dialog tabel	Konsistent brugeroplevelse	1 time	⬜ — Allerede brugt korrekt i kodebasen; pattern-doc kan vente til næste UI-feature
17	32	FilterDto med pagination + ShowDeleted på alle list-endpoints	Kræves når brugerlister vokser	2 timer	⬜ — Ingen lister er lange nok endnu; implementeres ved første real-data behov
18	35	Enum SSOT — alle enums ét sted, alle test-projekter refererer dertil	Forhindrer SQL CHECK-constraint fejl	1 time	⬜ — Kun AppSetting enum eksisterer; dækket af governance-memory mod sms-service copy-paste — Kun 1 enum (AppSetting) eksisterer; fil er allerede ren; reglen mod copy-paste er i memory
19	48/49	Filstørrelsesregel + index README per SSOT-area	AI finder docs på første forsøg	2 timer	✅ Gjort — README per area eksisterer; schema-overview.md opdateret til V026 (manglede ApplicationSettings+PasswordResetTokens+EmailTemplates)

🥉 C-TIER — Gøres når funktioner kræver det
Rank	#	Task	Impact	Tid	Status
20	1	DATETIME over DATETIME2 — audit nuværende migrationer	Konsistens-issue, ingen runtime-fejl	1 time	⬜
21	6/7	Boolean-prefix (Is*, Has*) + Utc suffix audit	Kun relevant ved nye kolonner	1 time	⬜
22	33	N+1 query audit	Kun mærkbart ved 100+ rækker	3 timer	⬜
23	31	ApiResponseDto<T> wrapper på alle endpoints	Blazor-klienten håndterer det allerede	2 timer	⬜
24	40/41	E2E timeout-hierarki + ingen text-based selectors	Fejltracking, ikke ny funktionalitet	1 time	⬜
25	44	E2E coverage matrix	Syns-overhead, lav direkte kodningsgevinst	2 timer	⬜

🗂️ D-TIER — Gøres kun når projektet er meget større
Rank	#	Task	Årsag	Status
26+	2	sp_addextendedproperty på kolonner	Kun relevant ved mange udviklere + SSMS-brug	⬜
27+	8/9	NVARCHAR/DECIMAL audit	Green-ai er allerede NVARCHAR, ikke et reelt problem	⬜
28+	51	common-mistakes.md for green-ai	God idé, men output af naturlig session-læring	⬜
29+	47	-WhatIf på destructive scripts	Meget lidt at vinde i lille projekt	⬜
30+	10	Full DB conventions SSOT-dokument	Nyttigt men ikke akut	⬜