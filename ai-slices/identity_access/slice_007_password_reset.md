# SLICE: Password Reset

## DOMAIN SOURCE

Domain: identity_access
Behavior: BEH_006

## GOAL

User requests password reset via email. Token (Guid) stored on User entity with expiry.

## INPUT

- email
- password

## OUTPUT

- success: access_token + refresh_token

## ENTITIES

- User

## RULES

- PasswordResetToken (Guid) stored on User with DatePasswordResetTokenExpiresUtc. Token validated on /new-password submission. Expired or missing token → rejected.

## FLOW

1. User submits reset email in slide state 3
2. POST /api/user/passwordresetrequest → generates Guid token, sets User.PasswordResetToken + User.DatePasswordResetTokenExpiresUtc
3. Email sent with link containing token
4. User clicks link → GET /new-password?token=<guid>
5. On submit: POST /api/user/newpassword → validates token + expiry, calls SetNewPassword()
6. SetNewPassword(): validates password rules via IsPasswordValid(), generates new salt + hash

## ACCEPTANCE CRITERIA

- valid input → successful result

## NOTES

- No infrastructure assumptions. No SQL. No C#.
