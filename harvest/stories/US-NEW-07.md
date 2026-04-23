# US-NEW-07: Forhåndsvisning af SMS-besked (SMS-forhåndsvisning)

**Status:** 🟡 READY
**Prioritet:** P1
**Domain:** Beskeder & Kommunikation
**HTTP Verbs:** GET
**Kilde:** Angular harvest → user story

---

## User Story

Som bruger vil jeg se en forhåndsvisning af SMS-beskeden før afsendelse, så jeg kan verificere indhold og format.

---

## Acceptance Criteria

- [ ] Forhåndsvisning vises som mobil-visning
- [ ] Tegntæller vises
- [ ] Besked-segmentering vises

---

## UI Implementation

| Felt | Værdi |
|------|-------|
| Page | `Shared/SmsPreview/SmsPreviewComponent.razor` |
| Route | `(komponent)` |
| MudBlazor components | `MudPaper`, `MudText` |
| UI patterns | preview-panel |

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

- [VERIFIED] User can preview SMS message before sending *(actor: user)*

---

## Dependencies
- (udfyldes af arkitekt)

## Arkitekt-noter
- (tilføj her)
