# DOMAIN DISTILLATION — Voice
**Status:** APPROVED_BASELINE 2026-04-11
**Source:** Source-primary (Layer 1 score 0.54 — empty behaviors/flows; UI + entities used)
**Authority:** INFORMATIONAL (Layer 1)

---

## 1. DOMAIN ROLE

Voice is a **send channel** within the messaging system, not a standalone application domain. It delivers TTS (text-to-speech) phone calls via the **Infobip gateway**. Voice is embedded in the messaging wizard and operates as a parallel channel alongside SMS/Email/eBoks.

Voice has no dedicated HTTP controller — all commands enter through `MessageController.CreateSingleVoice`.

---

## 2. KEY ENTITIES

| Entity | Type | Purpose |
|---|---|---|
| `SingleVoiceDto` | Input DTO | Data for a single voice message send (user-initiated) |
| `VoiceMessageDto` | Model | Voice message (openapi model) |
| `SmsGroupVoiceData` | Embedded model | Voice channel data within a broadcast (`SmsGroup`) |
| `TemplateVoiceDto` | DTO | Template-based voice message configuration |
| `IAdvancedVoiceSettings` | Interface | `{language: int, attempts: int, interval: int}` — TTS language, retry count, retry interval |
| `VoiceGatewaySendMessageCommand` | Command | Internal command sent to Infobip delivery gateway |
| `VoiceMessageUpdateCommand` | Command | Status update command applied after gateway callback |
| `InfobipScenarioDto` | External config | Infobip scenario object for TTS voice delivery |
| `InfobipCustomerVoiceSettingsChangedEventHandler` | Event handler | Reacts to per-customer Infobip voice setting changes |
| `VoiceMessageStatusChangedEventHandler` | Event handler | Reacts to delivery status callbacks from Infobip (call answered, failed, timeout) |
| `IVoiceBackgroundService` / `VoiceBackgroundService` | Service | Background processing for voice delivery queue |
| `IInfobipForwardingService` / `InfobipForwardingService` | Service | Call forwarding via Infobip (number-to-number) |
| `IInfobipScenarioService` / `InfobipScenarioService` | Service | Infobip scenario management (TTS config) |
| `IVoiceNumbersService` / `VoiceNumbersService` | Service | Virtual phone number assignment for voice calls |

---

## 3. BEHAVIORS

### 3a. Single voice message send
- Entry point: `POST api/Message/CreateSingleVoice(SingleVoiceDto)` → returns `int` (smsGroupId on success) or `400`.
- `SingleVoiceDto` carries: destination phone, message text, voice channel settings.
- Backend constructs `VoiceGatewaySendMessageCommand` and dispatches to `IVoiceBackgroundService`.
- `VoiceBackgroundService` queues delivery to Infobip using the per-customer `InfobipScenarioDto`.

### 3b. Broadcast with voice channel (wizard)
- In the messaging wizard, `voice-message-part.component.ts` is rendered as one of the message parts.
- The voice part form accepts:
  - Message text (TTS content)
  - `callForwardingNumber` — optional forwarding number if call is answered
  - `advancedVoiceSettings`: language (BiLanguageId), attempts (≥1), interval (5–45 min in 5-min steps)
  - Test message via `SendSmsOrVoiceTestMessageComponent`
- When user completes wizard, voice data is stored as `SmsGroupVoiceData` on the broadcast entity.

### 3c. Advanced voice settings
- `AdvancedVoiceSettingsComponent` exposes: language selector, attempts input, interval slider.
- Interval enforced to nearest 5-min multiple; min 5, max 45.
- Default values: attempts = 3, interval = 15, language = customer country language.
- Settings displayed as inline summary text after save.

### 3d. Voice nudging dialog
- `VoiceNudgingComponent` (`bi-voice-nudging`) — popup dialog shown when a broadcast is about to be sent without voice enabled.
- User can choose: "Yes, also send to voice" or dismiss.
- "Do not show again" checkbox available — preference persisted per user.
- Returns `VoiceNudgingDialogResult { sendToVoice: boolean, doNotShowAgain: boolean }`.

### 3e. Delivery status callback
- Infobip calls back to ServiceAlert webhook when call is answered / failed / timed out.
- `VoiceMessageStatusChangedEventHandler` processes the callback.
- Determines final delivery status; updates internal record via `VoiceMessageUpdateCommand`.

### 3f. Call forwarding
- `IInfobipForwardingService` configures per-number call forwarding rules in Infobip.
- If a call is answered, Infobip can optionally forward the call to a real phone number.
- `callForwardingNumber` on the voice message part sets this target number.

### 3g. Virtual phone number management
- `IVoiceNumbersService` manages which Infobip virtual phone numbers are available per customer.
- Numbers listed via `GET api/VirtualPhoneNumbers/GetVoiceInfoBipNumbers` (in phone_numbers domain).
- Per-customer assignment handled in `InfobipCustomerVoiceSettingsChangedEventHandler`.

---

## 4. FLOWS

### Flow A — User sends a single voice test/broadcast
1. User navigates to messaging wizard, selects Voice channel.
2. `voice-message-part` renders text field + advanced settings.
3. User optionally configures language, attempts (default 3), interval (default 15 min).
4. User optionally enters `callForwardingNumber`.
5. On wizard completion → `POST api/Message/CreateSingleVoice(SingleVoiceDto)`.
6. `VoiceBackgroundService` queues TTS call to Infobip via `VoiceGatewaySendMessageCommand`.
7. Infobip dials recipient; if no answer → retries up to `attempts` times with `interval` spacing.
8. Infobip calls back when final outcome known → `VoiceMessageStatusChangedEventHandler` updates status.

### Flow B — Voice nudging prompt
1. User is about to send a broadcast without voice configured.
2. System opens `VoiceNudgingComponent` dialog.
3. If user selects "Yes, also send to voice" → wizard adds voice channel to the broadcast.
4. If "Do not show again" checked → preference stored; nudge suppressed on future sends.

---

## 5. RULES

1. **No dedicated VoiceController**: All voice send commands enter through `MessageController.CreateSingleVoice`. There is no `api/Voice/` route group.

2. **Infobip only**: Voice delivery is exclusively via the Infobip gateway. No other voice gateway exists in the current architecture.

3. **Infobip scenario = TTS config**: Each voice delivery uses an `InfobipScenarioDto` — this defines TTS engine, language, and other call parameters. Configured per customer via `IInfobipScenarioService`.

4. **Retry logic is gateway-side**: `IAdvancedVoiceSettings.attempts` and `.interval` control retries. These are passed to Infobip; the gateway handles the retry loop.

5. **Call forwarding is conditional**: `callForwardingNumber` is optional. If set and the called party answers, Infobip patches the call through to the forwarding number.

6. **Complexity high, rebuild priority 6**: Layer 1 decision support marks Voice as high complexity (#6 rebuild priority). The Infobip integration and TTS scenario management are non-trivial external dependencies.

7. **Virtual phone numbers managed in phone_numbers domain**: `GetVoiceInfoBipNumbers` lives on `VirtualPhoneNumbers` controller — managed in the `phone_numbers` domain, not Voice.
