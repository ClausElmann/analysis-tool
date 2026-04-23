# US-NEW-06: Søg adresser på kort (kort)

**Status:** 🟡 READY
**Prioritet:** P2
**Domain:** Adresser & Data
**HTTP Verbs:** GET, POST
**Kilde:** Angular harvest → user story

---

## User Story

Som bruger vil jeg søge adresser og se dem på et interaktivt kort, så jeg kan identificere og vælge geografiske modtagere.

---

## Acceptance Criteria

- [ ] Brugeren kan søge adresser via tekstindtastning
- [ ] Resultater vises på kort
- [ ] Brugeren kan vælge område og se modtagere

---

## UI Implementation

| Felt | Værdi |
|------|-------|
| Page | `Pages/address/MapSearchPage.razor` |
| Route | `/address/map` |
| MudBlazor components | `MudTextField`, `MudButton` |
| UI patterns | map-view, address-search |

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

- [VERIFIED] User can search addresses on map *(actor: user)*

---

## Dependencies
- (udfyldes af arkitekt)

## Arkitekt-noter
- (tilføj her)
