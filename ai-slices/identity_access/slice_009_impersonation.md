# SLICE: Impersonation

## DOMAIN SOURCE

Domain: identity_access
Behavior: BEH_008

## GOAL

Admin can impersonate another user. Original user identity preserved in JWT claim.

## OUTPUT

- success: access_token + refresh_token

## ENTITIES

- User

## RULES

- See identity_access/070_rules.json

## FLOW

(see domain behaviors for detailed steps)

## ACCEPTANCE CRITERIA

- valid input → successful result

## NOTES

- INFERRED: Super admin feature. Original user session must be restored on exit.
- No infrastructure assumptions. No SQL. No C#.
