# Idle Harvest — Targeted Discovery Prompt
> Domain: Templates | Capability: `create_template` | Gap type: HIGH_GAP | Date: 2026-04-17

## Task

Find ALL code paths in the **sms-service** repository responsible for:

**create_template** — Create a new message template with channel-specific content

This capability is completely absent in the GreenAI rebuild. We need to understand exactly how sms-service implements it before building a green-field equivalent.

## What to find

Search systematically. Start from the HTTP entry point and trace the entire path to the database.

1. **Entry point** — which controller + action handles this? (class name, method name, HTTP verb + route)
2. **Request model** — what parameters/body does the endpoint accept?
3. **Service layer** — which service methods are called? (class name, method name, file path)
4. **Repository layer** — which repository methods? (class name, method name, file path)
5. **SQL** — what SQL operations are executed? (INSERT/UPDATE/DELETE/SELECT, table names)
6. **Validations** — what business rules are enforced BEFORE the DB operation?
7. **Side effects** — are there events, notifications, audit logs, or cascading operations?
8. **Error paths** — what happens if the operation fails? (error codes, rollbacks)

## Search hints

- Look for class/method names containing: `createtemplate`, `CreateTemplate`, `Create`
- SQL table names likely include: `Templates`
- Controllers likely in: `Controllers/`, `Api/`
- Repositories likely in: `Repositories/`, `Data/`

## Required output format

Respond ONLY with this JSON structure (no markdown prose):

```json
{
  "capability_id": "create_template",
  "domain": "Templates",
  "found": true,
  "entry_point": {
    "controller": "ClassName",
    "method": "MethodName",
    "http_verb": "POST",
    "route": "/api/v1/...",
    "file": "path/to/Controller.cs:line"
  },
  "request_model": {
    "class": "RequestClassName",
    "fields": ["field1: type", "field2: type"],
    "file": "path/to/Request.cs:line"
  },
  "service_calls": [
    {"class": "ServiceClass", "method": "MethodName", "file": "path/to/Service.cs:line"}
  ],
  "repository_calls": [
    {"class": "RepoClass", "method": "MethodName", "file": "path/to/Repo.cs:line"}
  ],
  "sql_operations": [
    {"type": "INSERT", "table": "TableName", "file": "path/to/Query.sql:line"}
  ],
  "validations": [
    "Description of validation rule (file:line)"
  ],
  "side_effects": [
    "Description of side effect (file:line)"
  ],
  "error_paths": [
    "Description of error case (file:line)"
  ],
  "confidence": 0.90,
  "notes": "Any observations about edge cases or complexity"
}
```

If the capability cannot be found, set `"found": false` and explain in `"notes"`.
