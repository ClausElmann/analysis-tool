# US-NEW-01: Se og sende email-beskeder (email)

**Status:** 🟡 READY
**Prioritet:** P1
**Domain:** Beskeder & Kommunikation
**HTTP Verbs:** GET, POST
**Kilde:** Angular harvest → user story

---

## User Story

Som bruger vil jeg se og sende email-beskeder, så jeg kan kommunikere med kunder via email-kanalen.

---

## Acceptance Criteria

- [ ] Brugeren ser liste over email-beskeder
- [ ] Brugeren kan oprette og sende ny email
- [ ] Leveringsstatus vises på sendte emails

---

## UI Implementation

| Felt | Værdi |
|------|-------|
| Page | `Pages/messaging/EmailPage.razor` |
| Route | `/messaging/email` |
| MudBlazor components | `MudButton`, `MudDataGrid`, `MudDialog`, `MudForm`, `MudTextField` |
| UI patterns | create-dialog, list-with-search, pagination |

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

- [VERIFIED] User can view email messages *(actor: user)*
- [VERIFIED] User can send email message *(actor: user)*

---

## Dependencies
- (udfyldes af arkitekt)

## Arkitekt-noter
- (tilføj her)
