# US-NEW-10: Notifikations-log (notifikationslog)

**Status:** 🟡 READY
**Prioritet:** P2
**Domain:** Beskeder & Kommunikation
**HTTP Verbs:** GET
**Kilde:** Angular harvest → user story

---

## User Story

Som administrator vil jeg se en komplet log over hvad der er sendt til hvem, så jeg kan eftervise leverancer og opfylde compliance-krav.

---

## Acceptance Criteria

- [ ] Administrator ser log med afsender, modtager, kanal, status, tidspunkt
- [ ] Søg og filtrer på periode og status
- [ ] Eksport til CSV

---

## UI Implementation

| Felt | Værdi |
|------|-------|
| Page | `Pages/messaging/NotificationLogPage.razor` |
| Route | `/messaging/notification-log` |
| MudBlazor components | `MudDataGrid`, `MudDateRangePicker`, `MudButton` |
| UI patterns | list-with-search, pagination |

---

## Backend (udfyldes af arkitekt)

| Felt | Værdi |
|------|-------|
| Endpoints | TBD |
| Handler(s) | TBD |
| SQL filer | TBD |
| DB Tabeller | TBD |

---

## Source Behaviors (fra harvest)

- [INFERRED] Administrator can view notification delivery log *(actor: user)*

---

## Dependencies
- (udfyldes af arkitekt)

## Arkitekt-noter
- (tilføj her)
