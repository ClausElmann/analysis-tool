## STEP 12-D — IDENTITY_ACCESS COMPLETE

**Status:** CLOSED. All corrections applied. Indexes updated.

**Corrections applied:**
- BEH_005 slide_states: states 1/3 were swapped; state 4 was "forgot password confirmation" → corrected to Authenticator App QR setup. All 6 states now verified from UI source.
- BEH_001 HTTP 300: was "multiple profiles → profile selector". Actual (UserController.cs:482): user has BOTH phone AND email → show 2FA delivery choice. Profile selection is server-side (`FindProfileIdInProfileList()`).
- `099_distillation.md` created: APPROVED_BASELINE.
- `UI_FILE_INDEX.md` created: 26 identity_access files tracked.
- `_distillation_index.md` created: 38 domains tracked.

**Proceeding to: profile_management STEP A — UI file discovery**

---

## COPILOT → ARCHITECT: STEP 12-C — SLIDE STATE MAPPING VERIFIED

**Protocol:** Micro-analysis only. NO code. Source read: `bi-login.component.ts` + `bi-login.component.html`.

---

### SLIDE_STATE_MAPPING_VERIFIED (from UI source code — HTML + TypeScript)

```
state 0 = Email + Password login form
          (email input, password input, "Forgot password" link → state 1, Login button, AD Login button)

state 1 = Forgot password — enter email
          (email input for reset request, "Reset password" submit, Cancel → state 0)
          TRIGGER: user clicks "Forgot pass" button → slideContainerValue = 1

state 2 = Choose 2FA delivery method
          (two buttons: "Send PIN by email", "Send PIN by SMS")
          TRIGGER: HTTP 300 from login or loginAD → slideContainerValue = 2
          HTML comment: "2Factor Pincode DeliveryMethod" / i18n key: "login.ChoosePincodeDeliveryMethod"

state 3 = Enter PIN code (SMS or email)
          (text input for 6-digit PIN, Login button, Cancel button)
          TRIGGER: sendPinCodeByEmail() success → slideContainerValue = 3
                   sendPinCodeBySms()  success → slideContainerValue = 3
          twoFactorMethodUsed = "email" | "sms" sets label text

state 4 = Set up Authenticator App (first-time enrollment)
          (QR code display, TOTP confirmation input, "Save" button, "Don't ask again", "Ask next time")
          TRIGGER: after successful PIN 2FA login (onTwoFactorLogin) + nudge NOT permanently blocked
                   + authenticatorQRImage returned from getAuthenticatorSecretQR()
          HTML comment: "2Factor Authenticator App secret" / i18n key: "login.AuthenticatorAppOffer"

state 5 = Enter Authenticator App TOTP code (existing users)
          (TOTP input, "Lost authenticator" link, Login button, Cancel button)
          TRIGGER: HTTP 428 + authenticatorApp=true flag from login or loginAD → slideContainerValue = 5
```

---

### ADDITIONAL FINDING — Profile Selection

Profile selection after multiple-profile login is NOT a slide state.
It is handled by a SEPARATE dialog component:
`src/shared/components/dialog-content/bi-profile-selection-dialog-content/bi-profile-selection-dialog-content.component.ts`

HTTP 300 in the login component always maps to **state 2 (Choose 2FA delivery method)**.
The domain artifact's claim that HTTP 300 = "profile selector" applies to the BACKEND behavior
(UserController returns 300 when user has multiple profiles) — but in the frontend, HTTP 300 from
the login component routes to 2FA delivery method choice. Profile selection must be
triggered differently (separate route or dialog, not this slide machine). This requires
clarification with backend endpoint semantics.

---

### COMPARISON WITH DOMAIN ARTIFACT (020_behaviors.json — BEH_005)

| State | Domain artifact (BEH_005) | Actual UI source | Match |
|---|---|---|---|
| 0 | "Email + Password form" | Email + Password login form | ✅ CORRECT |
| 1 | "Enter SMS/email PIN" | Forgot password — enter email | ❌ WRONG |
| 2 | "Choose delivery method (SMS vs Email)" | Choose 2FA delivery method | ✅ CORRECT |
| 3 | "Forgot password — enter email" | Enter PIN code (SMS or email) | ❌ WRONG |
| 4 | "Forgot password — confirmation" | Set up Authenticator App (QR + confirm) | ❌ WRONG |
| 5 | "Enter TOTP authenticator app code" | Enter Authenticator App TOTP code | ✅ CORRECT |

---

```
DRIFT: YES

SOURCE OF TRUTH: UI (bi-login.component.html + bi-login.component.ts)

ERRORS IN DOMAIN ARTIFACT (020_behaviors.json BEH_005):
  - States 1 and 3 are SWAPPED
  - State 4 is COMPLETELY WRONG (forgot password confirmation does not exist as a slide state)
  - State 4 is actually: Authenticator App first-time QR setup screen

NOTE: 099_distillation.md is NOT affected by this drift.
  The distillation describes behavior in conceptual terms without referencing state numbers.

RECOMMENDED ACTION:
  Update 020_behaviors.json BEH_005 slide_states with verified mapping above.
  This is a Layer 1 correction, not a green-ai code change.
  Awaiting Architect directive before modifying domain artifact.
```

---

**System locks:**
- `STEP_12C_SLIDE_STATE_MAPPING_COMPLETE` 🔒
- `BEH005_SLIDE_STATE_CORRECTION_PENDING_APPROVAL` 🔒

**Artifacts created this session:**
- `UI_FILE_INDEX.md` ✅ (root of analysis-tool)
- `domains/_distillation_index.md` ✅
- `domains/identity_access/099_distillation.md` ✅ (STATUS: APPROVED_BASELINE)

**STOP** — awaiting Architect directive for next domain selection.
