# SLICE: Logout

## DOMAIN SOURCE

Domain: identity_access
Behavior: BEH_003

## GOAL

Invalidates user session server-side. GAP_001 was wrong — logout IS implemented.

## INPUT

- (authenticated session)

## OUTPUT

- success: confirmation (HTTP 200)

## ENTITIES

- User

## RULES

- See identity_access/070_rules.json

## FLOW

1. POST /api/user/logout (authorized)
2. Check _workContext.IsLoggedIn
3. Call _authenticationService.Logout(_workContext.CurrentUser.Id)
4. Return HTTP 200

## ACCEPTANCE CRITERIA

- valid input → successful result

## NOTES

- Logout invalidates refresh token server-side. Access token remains valid until 15-min TTL expires (by design — short-lived JWT).
- No infrastructure assumptions. No SQL. No C#.
