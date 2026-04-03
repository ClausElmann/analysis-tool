# SLICE: User Nudging

## DOMAIN SOURCE

Domain: identity_access
Behavior: BEH_007

## GOAL

System prompts users with contextual suggestions. Users can dismiss permanently (neverAgain=true) or postpone.

## OUTPUT

- success: operation result

## ENTITIES

- User
- UserNudgingBlocksDto

## RULES

- A nudge is shown if UserNudgingBlocksDto.broadcastBlocks[NudgeType] = false. User can block permanently (neverAgain=true) or postpone (Survey: 1 hour, stored in localStorage). AuthenticatorApp nudge is specific to identity_access domain.

## FLOW

(see domain behaviors for detailed steps)

## ACCEPTANCE CRITERIA

- valid input → successful result

## NOTES

- No infrastructure assumptions. No SQL. No C#.
