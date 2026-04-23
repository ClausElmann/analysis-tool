# BUILD ORDER — FINAL
**Dato:** 2026-04-23
**Status:** GODKENDT
**Kilde:** architect_decisions_02.md

---

## WAVE 1 — FOUNDATION (ingen stories — UI infrastruktur)

| Komponent | Fil |
|-----------|-----|
| DataGrid wrapper | `Shared/DataGrid/AppDataGrid.razor` |
| Slet-bekræftelse dialog | `Shared/Dialogs/ConfirmDeleteDialog.razor` |
| Base formular dialog | `Shared/Dialogs/BaseFormDialog.razor` |
| Navigation menu | `NavigationMenu.razor` |

**Status:** GODKENDT — byg først, ingen backend-afhængigheder

---

## WAVE 2 — CORE (backend DONE)

| ID | Titel | Backend |
|----|-------|---------|
| GS-001 | Login og token-fornyelse | ✅ DONE |
| GS-003 | Profil- og kundevalg | ✅ DONE |
| GS-011 | SMS afsendelse — outbox og DLR | ✅ DONE |
| GS-015 | Samtaler — oprettelse og svar | ✅ DONE |
| GS-016 | Samtaler — læsning og ulæst-markering | ✅ DONE |
| GS-017 | Samtale-dispatch og status-opdatering | ✅ DONE |
| US-038 | Manage Conversations (Messaging) | ✅ DONE |
| US-NEW-01 | Se og sende email-beskeder | ✅ DONE |
| US-NEW-09 | Skift adgangskode (UI) | ✅ DONE |

---

## WAVE 3 — UI CORE (backend TBD)

| ID | Titel | Backend |
|----|-------|---------|
| US-001 | Manage Messages | TBD |
| US-002 | Manage Customers | TBD |
| US-016 | Manage Contacts | TBD |
| US-NEW-07 | Forhåndsvisning af SMS-besked | TBD |

---

## WAVE 4 — EXTENDED (alle resterende P2 + P3)

Alle stories ikke listet i WAVE 1-3 og ikke DROPpet.
Reference: architect_decisions_02.md — P2 (25 stories) + P3 (30 stories).

Prioritér inden WAVE 4 start:
- P2 bygges før P3
- Rækkefølge inden for P2/P3 bestemmes ved WAVE 4 kick-off

---

## DROP

| ID | Årsag |
|----|-------|
| US-043 | Placeholder — ingen behaviors |
| US-044 | Placeholder — ingen behaviors |
| US-045 | Placeholder — ingen behaviors |
| US-046 | Placeholder — ingen behaviors |
| US-047 | Placeholder — ingen behaviors |
| US-048 | Placeholder — ingen behaviors |
| US-NEW-08 | Dækket af GS-004 |

---

## HOLD (afventer verifikation)

| ID | Årsag |
|----|-------|
| US-041 | Domæne uafklaret |

---

## NÆSTE BUILD

**WAVE 1** — start nu

Copilot bygger i rækkefølge:
1. `AppDataGrid.razor`
2. `ConfirmDeleteDialog.razor`
3. `BaseFormDialog.razor`
4. `NavigationMenu.razor`

Når WAVE 1 er DONE → start WAVE 2 (GS-001 først).

---

*Kilde: architect_decisions_02.md | Genereret: 2026-04-23*
