# SLICE: Refresh Access Token

## DOMAIN SOURCE

Domain: identity_access
Behavior: BEH_002

## GOAL

Exchanges a valid refresh token for a new access token. Extends refresh token expiry on use.

## INPUT

- refresh_token

## OUTPUT

- success: access_token + refresh_token

## ENTITIES

- User
- UserRefreshToken
- TokenDto

## RULES

- See identity_access/070_rules.json

## FLOW

1. GET /api/user/refreshaccesstoken?refreshToken=<token>
2. Lookup UserRefreshToken by token string (only non-expired)
3. If not found or expired → HTTP 401
4. Load User by token.UserId
5. Generate new AccessToken JWT (15 min)
6. ExtendRefreshToken (sliding window, 30 min from now)
7. Return new TokenDto (same RefreshTokenModel, new AccessToken)

## ACCEPTANCE CRITERIA

- valid input → successful result
- invalid credentials → failure response

## NOTES

- No infrastructure assumptions. No SQL. No C#.
