# Forslag til manglende stories

Disse features eksisterer i sms-service men blev ikke fanget i harvest,
eller de eksisterer allerede som backend i GreenAI uden tilhørende UI-story.

**Instruktioner:** Marker med `ADD` / `DROP` / `HOLD`

---

## Fra eksisterende GreenAI-backend (ingen UI-story endnu)

| Forslag ID | Titel | Backend-fil | Beslutning |
|------------|-------|-------------|------------|
| US-NEW-01 | Se og sende email-beskeder | `Features/Email/` | `[ ]` |
| US-NEW-02 | Overvåg igangværende baggrundsjobs | `Features/JobManagement/` (SSE) | `[ ]` |
| US-NEW-03 | Vis samtalehistorik per kontakt | `Features/Conversations/` | `[ ]` |

---

## Fra sms-service Angular — ikke i harvest

| Forslag ID | Titel | Kilde | Beslutning |
|------------|-------|-------|------------|
| US-NEW-04 | Eksportér liste til Excel/CSV | Alle lister har eksport-knap i sms-service | `[ ]` |
| US-NEW-05 | Bulk-handlinger på valgte rækker | Mange lister har batch-select | `[ ]` |
| US-NEW-06 | Søg adresser på kort (map-view) | bi-map + bi-address-search komponenter | `[ ]` |
| US-NEW-07 | Forhåndsvisning af SMS-besked før afsendelse | SMS-preview komponent i sms-service | `[ ]` |

---

## Fra domæne-analyse — logiske huller

| Forslag ID | Titel | Reasoning | Beslutning |
|------------|-------|-----------|------------|
| US-NEW-08 | Opret ny bruger (self-service onboarding) | UserOnboarding feature er i backend, ingen story | `[ ]` |
| US-NEW-09 | Skift adgangskode | ChangePassword feature er i backend | `[ ]` |
| US-NEW-10 | Notifikations-log (hvad er sendt til hvem) | Mangler i harvest — kritisk for compliance | `[ ]` |

---

## Noter fra arkitekten

*(fri tekst)*
