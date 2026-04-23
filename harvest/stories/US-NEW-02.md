# US-NEW-02: Overvåg igangværende baggrundsjobs (baggrundsjobs)

**Status:** 🟡 READY
**Prioritet:** P2
**Domain:** System & Drift
**HTTP Verbs:** GET
**Kilde:** Angular harvest → user story

---

## User Story

Som administrator vil jeg se igangværende og seneste baggrundsjobs i realtid, så jeg kan overvåge systemets driftstilstand.

---

## Acceptance Criteria

- [ ] Administrator ser liste over aktive og seneste jobs
- [ ] Live-opdateringer via SSE uden reload
- [ ] Fejlede jobs markeres tydeligt

---

## UI Implementation

| Felt | Værdi |
|------|-------|
| Page | `Pages/system/JobsPage.razor` |
| Route | `/system/jobs` |
| MudBlazor components | `MudDataGrid`, `MudChip`, `MudProgressLinear` |
| UI patterns | sse-live-update, list-with-search |

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

- [VERIFIED] System streams active job status via SSE *(actor: system)*

---

## Dependencies
- (udfyldes af arkitekt)

## Arkitekt-noter
- (tilføj her)
