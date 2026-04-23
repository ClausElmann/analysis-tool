# MASTER — User Stories SSOT

> **DRY/SSOT:** Alle user stories for GreenAI samlet — DONE (eksisterer) + READY/HOLD (skal bygges).
> Arkitekten opdaterer status, prioritet og noter direkte i den individuelle story-fil.

**Sidst genereret:** 2026-04-23
**GreenAI DONE:** 21 stories
**Harvest (ny UI):** 48 stories
**Total:** 69 stories

---

## GreenAI — Eksisterende funktionalitet (DONE)

| ID | Status | Prio | Domain | Titel |
|----|--------|------|--------|-------|
| [GS-001](GS-001.md) | ✅ DONE | P0 | Auth | Login og token-fornyelse |
| [GS-002](GS-002.md) | ✅ DONE | P0 | Auth | Adgangskode-styring |
| [GS-003](GS-003.md) | ✅ DONE | P0 | Auth | Profil- og kundevalg |
| [GS-004](GS-004.md) | ✅ DONE | P1 | UserOnboarding | Bruger onboarding |
| [GS-005](GS-005.md) | ✅ DONE | P1 | AdminLight | Bruger- og rolleadministration |
| [GS-006](GS-006.md) | ✅ DONE | P1 | CustomerAdmin | Kundeadministration (read-side) |
| [GS-007](GS-007.md) | ✅ DONE | P2 | AdminLight | Systemindstillinger |
| [GS-008](GS-008.md) | ✅ DONE | P2 | UserSelfService | Bruger selvbetjening |
| [GS-009](GS-009.md) | ✅ DONE | P2 | ActivityLog | Aktivitetslog |
| [GS-010](GS-010.md) | ✅ DONE | P1 | Email | Email afsendelse og gateway |
| [GS-011](GS-011.md) | ✅ DONE | P1 | Sms/Delivery | SMS afsendelse — outbox og DLR |
| [GS-012](GS-012.md) | ✅ DONE | P2 | Sms/EboksIntegration | e-Boks integration |
| [GS-013](GS-013.md) | ✅ DONE | P1 | Sms/ManageStandardReceiver | Standardmodtagere administration |
| [GS-014](GS-014.md) | ✅ DONE | P2 | Sms/Logging | SMS fejllogning (FatalEmailLogger) |
| [GS-015](GS-015.md) | ✅ DONE | P1 | Conversations | Samtaler — oprettelse og svar |
| [GS-016](GS-016.md) | ✅ DONE | P1 | Conversations | Samtaler — læsning og ulæst-markering |
| [GS-017](GS-017.md) | ✅ DONE | P1 | ConversationDispatch | Samtale-dispatch og status-opdatering |
| [GS-018](GS-018.md) | ✅ DONE | P2 | JobManagement | Job- og task-monitoring |
| [GS-019](GS-019.md) | ✅ DONE | P2 | Localization | Lokalisering og labels |
| [GS-020](GS-020.md) | ✅ DONE | P0 | System | System health og ping |
| [GS-021](GS-021.md) | ✅ DONE | P2 | SharedKernel | Filtype-validering |

---

## Harvest — Ny UI funktionalitet (READY/HOLD)

| ID | Status | Prio | Domain | Capability | Route | Verbs |
|----|--------|------|--------|-----------|-------|-------|
| **Beskeder & Kommunikation** | | | | | | |
| [US-001](US-001.md) | 🟡 READY | P1 | Beskeder & Kommunikation | Manage Messages | `/messaging/messages` | DELETE, GET, POST |
| [US-012](US-012.md) | 🟡 READY | P2 | Beskeder & Kommunikation | Manage Operationals | `/messaging/operationals` | DELETE, GET, POST, PUT |
| [US-020](US-020.md) | 🟡 READY | P2 | Beskeder & Kommunikation | Manage Dynamics | `/messaging/dynamics` | DELETE, GET, POST, PUT |
| [US-023](US-023.md) | 🟡 READY | P2 | Beskeder & Kommunikation | Manage Webs | `/messaging/webs` | DELETE, GET, POST |
| [US-024](US-024.md) | 🟡 READY | P2 | Beskeder & Kommunikation | Manage Sms | `/messaging/smss` | DELETE, GET |
| [US-032](US-032.md) | 🟡 READY | P2 | Beskeder & Kommunikation | Manage Entries | `/messaging/entrys` | DELETE, GET, POST |
| [US-034](US-034.md) | 🟡 READY | P2 | Beskeder & Kommunikation | Manage Archiveds | `/messaging/archiveds` | GET |
| [US-037](US-037.md) | 🟡 READY | P2 | Beskeder & Kommunikation | Manage Status | `/messaging/statuss` | GET |
| [US-038](US-038.md) | ⏸️ HOLD | P3 | Beskeder & Kommunikation | Manage Conversations | `/admin/conversations` | GET, POST |
| [US-040](US-040.md) | 🟡 READY | P2 | Beskeder & Kommunikation | Manage Warnings | `/messaging/warnings` | GET, POST, PUT |
| [US-041](US-041.md) | 🟡 READY | P1 | Beskeder & Kommunikation | Manage Weathers | `/messaging/weathers` | DELETE, GET, POST, PUT |
| [US-NEW-01](US-NEW-01.md) | 🟡 READY | P1 | Beskeder & Kommunikation | Se og sende email-beskeder | `/messaging/email` | GET, POST |
| [US-NEW-07](US-NEW-07.md) | 🟡 READY | P1 | Beskeder & Kommunikation | Forhåndsvisning af SMS-besked | `(komponent)` | GET |
| [US-NEW-10](US-NEW-10.md) | 🟡 READY | P2 | Beskeder & Kommunikation | Notifikations-log | `/messaging/notification-log` | GET |
| **Kunder & Tilmelding** | | | | | | |
| [US-002](US-002.md) | 🟡 READY | P1 | Kunder & Tilmelding | Manage Customers | `/customers/customers` | DELETE, GET, PATCH, POST, PUT |
| [US-005](US-005.md) | 🟡 READY | P2 | Kunder & Tilmelding | Manage Senders | `/customers/senders` | DELETE, GET, PATCH, POST |
| [US-009](US-009.md) | 🟡 READY | P2 | Kunder & Tilmelding | Manage Prospects | `/customers/prospects` | DELETE, GET, PATCH, POST |
| [US-016](US-016.md) | 🟡 READY | P1 | Kunder & Tilmelding | Manage Contacts | `/customers/contacts` | DELETE, GET, POST, PUT |
| [US-019](US-019.md) | 🟡 READY | P2 | Kunder & Tilmelding | Manage Enrollments | `/customers/enrollments` | DELETE, GET, POST |
| **Brugere & Adgang** | | | | | | |
| [US-003](US-003.md) | 🟡 READY | P2 | Brugere & Adgang | Manage Profiles | `/admin/profiles` | DELETE, GET, POST, PUT |
| [US-004](US-004.md) | 🟡 READY | P2 | Brugere & Adgang | Manage Users | `/admin/users` | DELETE, GET, PATCH, POST, PUT |
| [US-007](US-007.md) | ⏸️ HOLD | P3 | Brugere & Adgang | Manage Resets | `/admin/resets` | POST |
| [US-017](US-017.md) | ⏸️ HOLD | P3 | Brugere & Adgang | Manage Roles | `/admin/roles` | GET, POST, PUT |
| [US-031](US-031.md) | ⏸️ HOLD | P3 | Brugere & Adgang | SuperAdmin: Kundeliste (read-only) | `/admin/customers` | GET |
| [US-035](US-035.md) | ⏸️ HOLD | P3 | Brugere & Adgang | Assign receiver to user/group | `/admin/receivers` | POST |
| [US-036](US-036.md) | ⏸️ HOLD | P3 | Brugere & Adgang | Manage Configurations | `/admin/configurations` | DELETE, GET, POST |
| [US-039](US-039.md) | ⏸️ HOLD | P3 | Brugere & Adgang | Manage Ftps | `/admin/ftps` | DELETE, GET, POST, PUT |
| [US-NEW-09](US-NEW-09.md) | 🟡 READY | P1 | Brugere & Adgang | Skift adgangskode | `/account/change-password` | POST |
| **Analyse & Rapportering** | | | | | | |
| [US-006](US-006.md) | ⏸️ HOLD | P3 | Analyse & Rapportering | Manage Benchmarks | `/analytics/benchmarks` | DELETE, GET, PATCH, POST |
| [US-025](US-025.md) | ⏸️ HOLD | P3 | Analyse & Rapportering | Manage Causes | `/analytics/causes` | DELETE, POST, PUT |
| **Økonomi & Drift** | | | | | | |
| [US-008](US-008.md) | ⏸️ HOLD | P3 | Økonomi & Drift | Manage Sales | `/finance/sales` | DELETE, GET, POST, PUT |
| [US-010](US-010.md) | ⏸️ HOLD | P3 | Økonomi & Drift | Manage Salaries | `/finance/salarys` | GET |
| [US-011](US-011.md) | ⏸️ HOLD | P3 | Økonomi & Drift | Manage Absences | `/finance/absences` | DELETE, GET, PATCH, POST |
| [US-018](US-018.md) | ⏸️ HOLD | P3 | Økonomi & Drift | Manage Invoices | `/finance/invoices` | GET |
| [US-029](US-029.md) | ⏸️ HOLD | P3 | Økonomi & Drift | Manage Employees | `/finance/employees` | GET, POST |
| [US-033](US-033.md) | ⏸️ HOLD | P3 | Økonomi & Drift | Manage Drives | `/finance/drives` | DELETE, GET, POST |
| **Adresser & Data** | | | | | | |
| [US-013](US-013.md) | 🟡 READY | P2 | Adresser & Data | Manage Groups | `/addresses/groups` | DELETE, GET, POST |
| [US-014](US-014.md) | ⏸️ HOLD | P3 | Adresser & Data | Manage Corrections | `/addresses/corrections` | DELETE, POST |
| [US-015](US-015.md) | ⏸️ HOLD | P3 | Adresser & Data | Manage Receivers | `/addresses/receivers` | GET, POST |
| [US-021](US-021.md) | ⏸️ HOLD | P3 | Adresser & Data | Manage Gdprs | `/addresses/gdprs` | DELETE, GET, POST, PUT |
| [US-026](US-026.md) | ⏸️ HOLD | P3 | Adresser & Data | Manage Address | `/addresses/addresss` | GET, POST, PUT |
| [US-027](US-027.md) | ⏸️ HOLD | P3 | Adresser & Data | Manage Stds | `/addresses/stds` | DELETE, POST |
| [US-028](US-028.md) | ⏸️ HOLD | P3 | Adresser & Data | Manage Localizeds | `/addresses/localizeds` | POST |
| [US-030](US-030.md) | ⏸️ HOLD | P3 | Adresser & Data | Manage Imports | `/addresses/imports` | DELETE, GET, POST |
| [US-042](US-042.md) | ⏸️ HOLD | P3 | Adresser & Data | Manage Statstidendes | `/addresses/statstidendes` | DELETE, GET, POST |
| [US-NEW-06](US-NEW-06.md) | 🟡 READY | P2 | Adresser & Data | Søg adresser på kort | `/address/map` | GET, POST |
| **Address & Data** | | | | | | |
| [US-022](US-022.md) | ⏸️ HOLD | P3 | Address & Data | Manage Maps | `/admin/maps` | DELETE, GET, POST, PUT |
| **System & Drift** | | | | | | |
| [US-NEW-02](US-NEW-02.md) | 🟡 READY | P2 | System & Drift | Overvåg igangværende baggrundsjobs | `/system/jobs` | GET |

---

## Prioritets-oversigt

| Prio | GreenAI DONE | Harvest READY | Harvest HOLD |
|------|-------------|--------------|-------------|
| P0 | 4 | 0 | 0 |
| P1 | 9 | 7 | 0 |
| P2 | 8 | 17 | 0 |
| P3 | 0 | 0 | 24 |

---

## Sådan bruges dette dokument

1. **Arkitekt:** Åbn individuelle story-filer (GS-*/US-*) for detaljer
2. **Byg-ordre:** Udfyld `harvest/architect-review/04_build_order.md` med WAVE 1-4 baseret på prioritet
3. **Status-opdatering:** Ændr `Status:` i individuel story-fil når feature bygges/afsluttes
4. **Ny story:** Tilføj ny `.md`-fil i dette katalog + tilføj række i denne MASTER
5. **SSOT-regel:** Arkitektur-beslutninger skrives i story-filen — IKKE i chat

---

*Genereret af `scripts/stories/generate_story_files.py`*
