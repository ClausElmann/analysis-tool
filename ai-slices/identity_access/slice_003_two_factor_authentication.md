# SLICE: Two Factor Authentication

## DOMAIN SOURCE

Domain: identity_access
Behavior: BEH_005

## GOAL

2FA flow with 3 delivery methods: SMS pin, email pin, or TOTP authenticator app.

## INPUT

- email
- password

## OUTPUT

- success: operation result

## ENTITIES

- User

## RULES

- See identity_access/070_rules.json

## FLOW

(see domain behaviors for detailed steps)

## ACCEPTANCE CRITERIA

- valid input → successful result

## NOTES

- No infrastructure assumptions. No SQL. No C#.
