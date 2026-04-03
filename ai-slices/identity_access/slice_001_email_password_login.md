# SLICE: Email Password Login

## DOMAIN SOURCE

Domain: identity_access
Behavior: BEH_001

## GOAL

Authenticates user with email + password. Returns JWT access token + refresh token, or HTTP error codes for 2FA/profile-selection flows.

## INPUT

- email
- password
- refresh_token
- profile_id

## OUTPUT

- success: access_token + refresh_token

## ENTITIES

- User
- TokenDto

## RULES

- See identity_access/070_rules.json

## FLOW

1. Lookup user by email via UserService.GetApiUserByEmail()
2. Check lockout: if IsLockedOut=true OR (FailedLoginCount > 5 AND time-based delay not expired) → return HTTP 403
3. Hash submitted password with PasswordSalt using SHA256 → compare to stored Password
4. On match: reset FailedLoginCount=0, IsLockedOut=false, DateLastLoginUtc=now
5. If CurrentProfileId==0 AND user has exactly 1 profile → auto-set CurrentProfileId
6. If CurrentProfileId==0 AND user has multiple profiles → return HTTP 300 (client must show profile selector)
7. Create/extend RefreshToken (30 min), generate AccessToken JWT (15 min)
8. Return TokenDto
9. On mismatch: increment FailedLoginCount, update DateLastFailedLoginUtc → return HTTP 401

## ACCEPTANCE CRITERIA

- valid input → successful result
- locked/forbidden user → failure response
- successful operation resets failure counters
- multiple profiles → selection required response
- invalid credentials → failure response

## NOTES

- No infrastructure assumptions. No SQL. No C#.
