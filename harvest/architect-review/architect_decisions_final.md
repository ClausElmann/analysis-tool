# ARCHITECT DECISION BASELINE — FINAL (LOCKED)
**Dato:** 2026-04-23
**Status:** LOCKED — arkitekt-godkendt

---

## 1. GAP DECISIONS (FINAL)

### GAP-A: "Other X" placeholders
| Story | Beslutning |
|-------|-----------|
| US-043 | DROP |
| US-044 | DROP |
| US-045 | DROP |
| US-046 | DROP |
| US-047 | DROP |
| US-048 | DROP |

### GAP-B: Dubletter
| Par | Beslutning |
|-----|-----------|
| US-002 vs US-031 | KEEP BOTH — US-031 RENAME → "SuperAdmin: Kundeliste (read-only)" |
| US-015 vs US-035 | KEEP BOTH — US-035 RENAME → "Assign receiver to user/group" |

### GAP-C: Backend uden UI-story
| Feature | Beslutning |
|---------|-----------|
| Email UI | ADD → US-NEW-01, P1 |
| JobManagement UI | ADD → US-NEW-02, P2 |
| US-038 Conversations | RENAME + FLYT → Messaging & Communication, P1 |

### GAP-D: Forkert domæne
| Story | Korrekt domæne |
|-------|---------------|
| US-022 Manage Maps | Address & Data |
| US-041 Manage Weathers | HOLD — domæne uafklaret, kræver verifikation |

---

## 2. MISSING STORIES DECISIONS (FINAL)

| ID | Titel | Beslutning | Prioritet |
|----|-------|-----------|---------|
| US-NEW-01 | Se og sende email-beskeder | ADD | P1 |
| US-NEW-02 | Overvåg igangværende baggrundsjobs | ADD | P2 |
| US-NEW-03 | Vis samtalehistorik per kontakt | HOLD | — |
| US-NEW-04 | Eksportér liste til Excel/CSV | HOLD | — |
| US-NEW-05 | Bulk-handlinger på valgte rækker | HOLD | — |
| US-NEW-06 | Søg adresser på kort | ADD | P2 |
| US-NEW-07 | Forhåndsvisning af SMS-besked | ADD | P1 |
| US-NEW-08 | Opret ny bruger (onboarding) | DROP — dækket af GS-004 | — |
| US-NEW-09 | Skift adgangskode (UI) | ADD | P1 |
| US-NEW-10 | Notifikations-log | ADD | P2 |

---

## 3. FINAL STORY SET

| Kilde | Antal |
|-------|-------|
| GreenAI DONE (GS) | 21 |
| Harvest (US) — efter DROP af 6 placeholders | 42 |
| US-NEW tilføjet (01,02,06,07,09,10) | 6 |
| **TOTAL AKTIVE** | **69** |

| Status | Antal |
|--------|-------|
| DONE (GS) | 21 |
| P1 READY | 13 |
| P2 READY | 25 |
| P3 READY | 30 |
| HOLD | 1 (US-041) |
| DROP | 8 (6×GAP-A + US-NEW-08) |

---

## 4. FINAL P1 / P2 / P3 LISTS

### P1 (13 stories)
| ID | Titel | Backend |
|----|-------|---------|
| GS-001 | Login og token-fornyelse | ✅ DONE |
| GS-003 | Profil- og kundevalg | ✅ DONE |
| GS-011 | SMS afsendelse — outbox og DLR | ✅ DONE |
| GS-015 | Samtaler — oprettelse og svar | ✅ DONE |
| GS-016 | Samtaler — læsning og ulæst-markering | ✅ DONE |
| GS-017 | Samtale-dispatch og status-opdatering | ✅ DONE |
| US-001 | Manage Messages | TBD |
| US-002 | Manage Customers | TBD |
| US-016 | Manage Contacts | TBD |
| US-038 | Manage Conversations (→ Messaging) | ✅ DONE |
| US-NEW-01 | Se og sende email-beskeder | ✅ DONE |
| US-NEW-07 | Forhåndsvisning af SMS-besked | TBD |
| US-NEW-09 | Skift adgangskode (UI) | ✅ DONE |

### P2 (25 stories)
| ID | Titel |
|----|-------|
| GS-002 | Adgangskode-styring |
| GS-004 | Bruger onboarding |
| GS-005 | Bruger- og rolleadministration |
| GS-006 | Kundeadministration (read-side) |
| GS-007 | Systemindstillinger |
| GS-008 | Bruger selvbetjening |
| GS-009 | Aktivitetslog |
| GS-010 | Email afsendelse og gateway |
| GS-012 | e-Boks integration |
| GS-013 | Standardmodtagere administration |
| GS-018 | Job- og task-monitoring |
| US-003 | Manage Profiles |
| US-004 | Manage Users |
| US-005 | Manage Senders (↓ fra P1) |
| US-009 | Manage Prospects (↓ fra P1) |
| US-012 | Manage Operationals (↓ fra P1) |
| US-013 | Manage Groups |
| US-019 | Manage Enrollments (↓ fra P1) |
| US-020 | Manage Dynamics (↓ fra P1) |
| US-023 | Manage Webs (↓ fra P1) |
| US-032 | Manage Entries (↓ fra P1) |
| US-040 | Manage Warnings (↓ fra P1) |
| US-NEW-02 | Overvåg baggrundsjobs (UI) |
| US-NEW-06 | Søg adresser på kort |
| US-NEW-10 | Notifikations-log |

### P3 (30 stories)
GS-014, GS-019, GS-020, GS-021,
US-006, US-007, US-008, US-010, US-011, US-014, US-015, US-017, US-018,
US-021, US-022, US-024, US-025, US-026, US-027, US-028, US-029, US-030,
US-031, US-033, US-034, US-035, US-036, US-037, US-039, US-042

### HOLD
US-041 — domæne uafklaret

---

## 5. BUILD READINESS: JA

WAVE 1 næste — se build_order.md

---

*Kilde: architect_decisions_01.md + arkitekt-korrektioner 2026-04-23*
