# BACKEND–UI CONTRACT — WAVE 2
**Dato:** 2026-04-23
**Kilde:** GREEN_AI_BUILD_STATE.md + harvest/stories/ (WAVE 2 fra build_order.md)
**Formål:** UI ved præcis hvilke endpoints den skal kalde for hvert WAVE 2 GS-feature

---

## GS-001 — Login og token-fornyelse

UI skal kalde:
- `POST /api/auth/login` — body: `{ email, password }` → returns `{ token, refreshToken }`
- `POST /api/auth/refresh` — body: `{ refreshToken }` → returns ny `token`
- `POST /api/auth/logout` — invaliderer refresh-token
- `GET /api/auth/me` — returnerer aktuel bruger

Bruges af:
- Login page
- App-init (token-check ved opstart)
- AuthService / token-interceptor

---

## GS-003 — Profil- og kundevalg

UI skal kalde:
- `GET /api/auth/profile-context` — returnerer tilgængelige kunder + profiler
- `POST /api/auth/select-customer` — body: `{ customerId }`
- `POST /api/auth/select-profile` — body: `{ profileId }`

Bruges af:
- Customer/Profile selector (post-login flow)
- Navbar kontekst-visning (aktiv kunde/profil)

---

## GS-011 — SMS afsendelse — outbox og DLR

UI skal kalde:
- `GET /api/sms/outbox` — liste over OutboundMessages (status, kanal, modtager)
- `GET /api/sms/outbox/{id}` — detalje på enkelt besked

Status-værdier (vis korrekt i UI):
- `0` = Created, `1` = Queued, `2` = Sent, `3` = Delivered, `4` = Failed

Bruges af:
- US-001 Manage Messages (status-visning)
- US-NEW-07 SMS Preview (forhåndsvisning inden afsendelse)
- Notification log (US-NEW-10)

---

## GS-015 — Samtaler — oprettelse og svar

UI skal kalde:
- `POST /api/conversations` — body: `{ conversationPhoneNumberId, partnerPhoneCode, partnerPhoneNumber, partnerName }` → returnerer `conversationId`
- `POST /api/conversations/{id}/reply` — body: `{ text }` → sender SMS-svar

Bruges af:
- US-038 Manage Conversations (opret + svar)

---

## GS-016 — Samtaler — læsning og ulæst-markering

UI skal kalde:
- `GET /api/conversations` — returnerer liste med `{ id, partnerName, unread, lastMessage }`
- `GET /api/conversations/{id}/messages` — returnerer besked-historik
- `POST /api/conversations/{id}/read` — markerer samtale som læst

Bruges af:
- US-038 Manage Conversations (liste + detalje + read)

---

## GS-017 — Samtale-dispatch og status-opdatering

UI poller status (dispatch er backend-internt):
- `GET /api/conversations/{id}/messages` — poll ConversationMessages.Status (0-4)

Status-værdier:
- `0` = Created, `1` = Queued, `2` = Sent, `3` = Delivered, `4` = Failed

Bruges af:
- US-038 Manage Conversations (statusvisning på beskeder)

---

## US-038 — Manage Conversations (Messaging)

Samler GS-015 + GS-016 + GS-017:

| Handling | Endpoint |
|---------|---------|
| List samtaler | `GET /api/conversations` |
| Åbn samtale | `GET /api/conversations/{id}/messages` |
| Marker læst | `POST /api/conversations/{id}/read` |
| Opret ny samtale | `POST /api/conversations` |
| Send svar | `POST /api/conversations/{id}/reply` |
| Vis status på besked | Poll `GET /api/conversations/{id}/messages` |

---

## US-NEW-01 — Se og sende email-beskeder

Bruger GS-010 (Email). UI skal kalde:
- `GET /api/email/list` — liste over EmailMessages
- `POST /api/email/send` — body: `{ to, subject, body, correlationId? }`
- `POST /api/email/send-system` — systemmail (admin only)
- `GET /api/email/{id}` — detalje + leveringsstatus

Bruges af:
- Email-beskedside under Messaging

---

## US-NEW-09 — Skift adgangskode (UI)

Bruger GS-002 (Auth/ChangePassword). UI skal kalde:
- `POST /api/auth/change-password` — body: `{ currentPassword, newPassword }`

Validering i UI:
- `newPassword` min 8 tegn
- Bekræft-felt matcher `newPassword`
- Vis success/fejl-besked

Bruges af:
- Account-settings page / profil-dropdown

---

## Afhængigheds-oversigt

| WAVE 2 story | Afhænger af GS |
|---|---|
| US-038 | GS-015, GS-016, GS-017 |
| US-NEW-01 | GS-010 |
| US-NEW-09 | GS-002 |

GS-001 og GS-003 er fundament for ALLE UI-sider (auth + kontekst).

---

*Kilde: GREEN_AI_BUILD_STATE.md | WAVE 2 fra harvest/architect-review/build_order.md*
