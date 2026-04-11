# DOMAIN DISTILLATION — identity_access

**STATUS:** APPROVED_BASELINE
**Date:** 2026-04-11
**Iteration source:** Layer 1 `domains/identity_access/` — completeness 0.97, iteration 32
**UI validation:** `bi-login.component.ts/html` (STEP 12-C verified)
**Authority:** INFORMATIONAL — guides green-ai implementation, does not bind it

---

## PURPOSE

Controls how users and services prove who they are and what they are allowed to do. Manages the full lifecycle of a user in the system: creation, login, session, profile selection, recovery, and removal. Every other domain depends on a valid authenticated context from this domain.

---

## CORE CONCEPTS

- **User** — a person who can log in. Has credentials, optional two-factor settings, a language and country assignment, and a soft-delete state. Never permanently removed.
- **Session** — a pair of tokens: a short-lived access token (15 minutes) and a longer-lived refresh token (30 minutes, renewed on each use). Represents an active authenticated state.
- **Profile** — the operational context a user acts within. A user may have access to multiple profiles (tenants + roles). Must be selected before any operation can proceed.
- **Authentication method** — the means by which a user proves identity: email + password, Azure AD (per-user), SAML2 (per-customer IdP), or ticket-based SSO (partner system).
- **Two-factor factor** — a second verification step triggered after credential success. Three delivery paths: SMS pin, email pin, or TOTP authenticator app code.
- **Nudge** — a contextual prompt shown to a user suggesting a security improvement or feature. Can be permanently blocked or temporarily postponed per type.
- **Provisioning** — automated creation and management of users and groups from an external identity provider via the SCIM 2.0 protocol.

---

## CAPABILITIES

- Authenticate a user via email and password
- Authenticate a user via Azure AD (Entra ID)
- Authenticate a user via a customer-specific SAML2 identity provider
- Authenticate a user via a partner system ticket (LocationAlert SSO)
- Issue, refresh, and revoke session tokens
- Enforce progressive account lockout after repeated credential failures
- Require and verify a second authentication factor (SMS, email, or authenticator app)
- Reset a forgotten password via a time-limited email link
- Allow a user to set up and confirm a TOTP authenticator app
- Auto-select profile when user has access to exactly one; prompt selection when multiple exist
- Soft-delete users; allow reactivation by admin
- Allow an admin to act as another user (impersonation) while preserving the original identity
- Provision and deprovision users and groups from external identity providers (SCIM 2.0)
- Authenticate internal services to each other (Azure Managed Identity, not for end users)
- Prompt users toward security or feature improvements via nudges; track dismissal

---

## FLOW

### Standard login
1. User submits credentials
2. System checks lockout status — if locked, request is rejected
3. Credentials are verified
4. If two-factor is required: system sends a pin or prompts for authenticator code; user must verify before receiving tokens
5. If user has access to multiple profiles: user must choose one before receiving tokens
6. On success: access token and refresh token are issued

### Token lifecycle
1. Access token used in all subsequent requests
2. When access token nears expiry, client exchanges the refresh token for a new access token
3. Refresh token expiry slides forward on each exchange
4. On logout: server invalidates the refresh token; access token remains valid until its natural expiry

### Password reset
1. User requests reset by providing their email
2. System generates a time-limited token and sends it via email
3. User follows the link, submits a new password meeting complexity requirements
4. System validates the token, applies the new credentials, clears the reset token

### External SSO (SAML2)
1. User navigates via a customer-specific entry URL
2. System reads that customer's identity provider configuration
3. User is redirected to their organization's login page
4. On successful assertion: email is extracted from the configured claim, user is matched or provisioned
5. Tokens issued as with standard login

---

## RULES

- Account locks after 5 failed login attempts; lockout duration scales with failure count (more failures = longer wait); only admin can manually unlock
- Access token lifetime is 15 minutes; refresh token lifetime is 30 minutes (sliding)
- If a user has exactly one accessible profile, it is selected automatically; if multiple, the user must choose explicitly
- Users are never hard-deleted; deletion sets a deleted flag and a timestamp; deleted users are excluded from normal operations but can be reactivated
- Passwords must meet minimum complexity: at least 8 characters, one digit, one lowercase letter, one uppercase letter, one special character
- A user's country and language are always the same value — they are set together when the user is created and must not be treated as independent fields
- New users inherit language, country, and timezone from the customer they belong to
- 2FA via SMS is only available if a phone number is configured on the user; 2FA via TOTP is only available if an authenticator secret has been confirmed; email 2FA is always available as a fallback
- SAML2 is scoped per customer — each customer can configure a different identity provider; the email claim name must match what the customer's IdP actually sends
- SCIM endpoints are authenticated per customer using a dedicated bearer token stored on the customer record

---

## EDGE CASES

- A session that expires while the user is actively working causes the login dialog to appear mid-application, not on a separate login page
- Azure AD users who have previously signed in will have silent SSO attempted automatically on the next page load; if silent SSO fails, the login form appears normally
- An access token issued just before logout remains usable for up to 15 minutes after logout — there is no server-side mechanism to revoke it before its natural expiry
- When multiple parallel API requests are made near token expiry, all may simultaneously attempt a token refresh — without a concurrency guard this produces duplicate sessions
- A SAML2 user logging in for the first time is automatically provisioned and notified by email; misconfiguration of the email claim silently prevents login for the entire customer
- A user who loses their authenticator device has no self-service recovery path — an admin must clear the authenticator secret manually
- An admin impersonating a user carries the original user's identity in the session token throughout the impersonation; downstream operations record the impersonated identity
- The subscription app (citizen-facing) uses a separate login component but calls the same authentication API

---

## INTEGRATIONS

- **Azure AD / Entra ID** — outbound, per-user; users authenticate via MSAL; admin consent required once per organization
- **SAML2 Identity Provider** — outbound, per-customer; each customer configures their own IdP; SAML certificate requires annual manual renewal
- **SCIM 2.0** — inbound, per-customer; external IdPs push user/group changes; authenticated via per-customer bearer token
- **Email** — outbound; used for password reset links, 2FA pin delivery, and new SAML user notification; must route through the email pipeline domain
- **SMS gateway** — outbound; used for 2FA SMS pin delivery; the SMS domain does not yet exist — this path is currently blocked
- **TOTP / RFC 6238** — local; authenticator app code verification uses the secret stored on the user record
- **LocationAlert** — ticket-based SSO with 1-minute ticket expiry and 8-hour session; requires a heartbeat call to keep the session alive; logout must be coordinated across both systems
- **Azure Managed Identity** — inbound; internal Azure-hosted services authenticate to the API using managed identity tokens; not visible to end users

---

## GAPS

- **GAP_004 (open):** No explicit MFA recovery codes — if a user loses their authenticator device, no self-service recovery exists; admin manual reset is the only path. This gap exists in Layer 0 as well; it is a known limitation, not a rebuild error.
- **2FA SMS blocked:** The SMS pin delivery path cannot be implemented until the SMS domain is built. 2FA via email and TOTP can proceed independently.
- **Access token revocation:** There is no mechanism to invalidate an access token before it expires. This is an intentional design (TTL-based), but means a logged-out user retains API access for up to 15 minutes.
- **SAML certificate renewal:** The annual certificate renewal process is manual and critical. No automation is documented; a missed renewal silently locks out all customers using that IdP.
- **Slide state mapping:** Domain artifact `020_behaviors.json` (BEH_005) contains incorrect state numbering. Verified correct mapping documented in STEP 12-C. See `temp.md` for correction details. This distillation does NOT reference state numbers and is therefore unaffected.

---

## NOTES

- This distillation contains NO class names, method names, frameworks, or implementation details
- All content is derived exclusively from Layer 1 (`domains/identity_access/`) with secondary UI validation
- The login UI is a 6-state slide machine (states 0–5). Profile selection uses a separate dialog mechanism, not a slide state.
- Technical debt items (SHA256, TTL hardcoding, token refresh concurrency) are tracked in `095_decision_support.json` and STEP 12-B compliance reports — not repeated here
