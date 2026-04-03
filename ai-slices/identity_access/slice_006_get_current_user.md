# SLICE: Get Current User

## DOMAIN SOURCE

Domain: identity_access
Behavior: BEH_010

## GOAL

Returns current user data from WorkContext. Two endpoints: full UserDto (GET /user) and lightweight UserInfoDto (GET /user/info).

## OUTPUT

- success: operation result

## ENTITIES

- User
- UserDto
- UserInfoDto

## RULES

- See identity_access/070_rules.json

## FLOW

(see domain behaviors for detailed steps)

## ACCEPTANCE CRITERIA

- valid input → successful result

## NOTES

- No infrastructure assumptions. No SQL. No C#.
