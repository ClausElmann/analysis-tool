# SLICE: Azure ADLogin

## DOMAIN SOURCE

Domain: identity_access
Behavior: BEH_004

## GOAL

Azure AD / Entra ID login via MSAL. Extracts idToken from MSAL result and exchanges for ServiceAlert JWT.

## INPUT

- email
- profile_id
- customer_id (optional)

## OUTPUT

- success: access_token + refresh_token

## ENTITIES

- User

## RULES

- See identity_access/070_rules.json

## FLOW

1. MsalBroadcastService emits LOGIN_SUCCESS or ACQUIRE_TOKEN_SUCCESS
2. Extract idToken from AuthenticationResult
3. POST /api/user/loginad { token: idToken, smsGroupId? }
4. On success: store adLogin='1' in localStorage for silent SSO on next load
5. On HTTP 300: show profile selector (slideContainerValue=2)
6. On HTTP 428 + authenticatorApp=true: show TOTP input (slideContainerValue=5)
7. On HTTP 428 + authenticatorApp=false: send pin code by email
8. On subsequent loads: attempt ssoSilent() first; if fails, remove adLogin flag

## ACCEPTANCE CRITERIA

- valid input → successful result

## NOTES

- No infrastructure assumptions. No SQL. No C#.
