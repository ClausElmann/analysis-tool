# Feature Template

## Feature structure

```
Features/[Domain]/[Feature]/
```

## Required files

- Command.cs
- Handler.cs
- Validator.cs
- Response.cs
- Endpoint.cs
- Page.razor
- [Feature].sql

## Rules

- Handler contains ALL logic
- SQL is NEVER inline
- Use IDbSession for all DB operations
- Use ICurrentUser for identity
- Return Result<T>
- Do NOT throw for business errors
- All queries MUST include CustomerId filtering
