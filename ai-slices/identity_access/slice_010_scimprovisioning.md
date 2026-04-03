# SLICE: SCIMProvisioning

## DOMAIN SOURCE

Domain: identity_access
Behavior: BEH_009

## GOAL

SCIM 2.0 inbound user/group provisioning from external IdPs (e.g., Azure AD, Okta).

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
