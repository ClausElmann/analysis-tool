# US-NEW-09: Skift adgangskode (adgangskode)

**Status:** 🟡 READY
**Prioritet:** P1
**Domain:** Brugere & Adgang
**HTTP Verbs:** POST
**Kilde:** Angular harvest → user story

---

## User Story

Som bruger vil jeg kunne skifte min adgangskode, så jeg kan vedligeholde sikkerheden på min konto.

---

## Acceptance Criteria

- [ ] Brugeren kan indtaste nuværende + ny adgangskode
- [ ] Validering: ny kode opfylder krav
- [ ] Bekræftelse ved succesfuld ændring

---

## UI Implementation

| Felt | Værdi |
|------|-------|
| Page | `Pages/account/ChangePasswordPage.razor` |
| Route | `/account/change-password` |
| MudBlazor components | `MudForm`, `MudTextField`, `MudButton` |
| UI patterns | form-page |

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

- [VERIFIED] User can change own password *(actor: user)*

---

## Dependencies
- (udfyldes af arkitekt)

## Arkitekt-noter
- (tilføj her)
