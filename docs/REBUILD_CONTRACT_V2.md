# Rebuild Contract V2 — analysis-tool

> **Role:** Principal AI Architect
> **Mode:** Rebuild Contract Design
> **Date:** 2026-04-02
> **Scope:** `090_rebuild.json` and its feeder logic only

---

## 1. Current Rebuild Model Assessment

### What the engine currently produces

`DomainModelStore.build_rebuild_spec()` (Gen 3, `core/domain/domain_model_store.py` lines 177–279) takes the accumulated domain model and converts everything to flat string lists via `_clean()`:

```python
entities     = _clean(model.get("entities"))   # ["User", "UserRefreshToken", ...]
behaviors    = _clean(model.get("behaviors"))  # ["EmailPasswordLogin", ...]
```

All rich structure from `010_entities.json`, `020_behaviors.json`, `030_flows.json`, and `070_rules.json` is **discarded at this step**. What goes in are names-as-strings. What comes out is heuristic inference on those names.

The heuristic produces:

| Key | Method | Example output |
|---|---|---|
| `blazor_pages` | keyword match on "controller", "view", "page" in entity/behavior names | `{ component: "LoginPage", route: "/loginpage", auth_required: true }` |
| `api_contracts` | keyword match on "api", "controller", "get", "post" in behavior names | `{ method: "GET /emailpasswordlogin", source: "inferred" }` |
| `ef_core_entities` | entity names not containing "dto", "service", "view" → appended with `s` | `{ entity: "User", table: "users" }` |
| `blazor_state_model` | `stateful` if rules/events exist, else `stateless` | `{ type: "stateful" }` |
| `authorization_hints` | rules/behaviors containing "auth", "login", "role" | `["PasswordLockout", ...]` |

The manually enriched `domains/identity_access/090_rebuild.json` is far better than what the engine produces — it contains real routes, real API contracts, and real state machine transitions. But it was written by hand, not derived from the domain model files.

### Strengths

- Produces a file that satisfies the file gate (file exists)
- Blazor page stubs provide approximate UI surface coverage
- API contract stubs name behaviors that map to real routes
- `ef_core_entities` gives a starting entity list for SQL scaffolding
- Schema versioning in `_meta` is in place

### Weaknesses

1. **Flat string loss.** `_clean()` converts all structured objects to strings. The `fields`, `type`, `source`, `steps`, `constants`, `lockout_rule` etc. inside `010_entities.json` and `020_behaviors.json` are dropped before the rebuild is computed.

2. **Heuristic route inference.** Routes are derived by stripping suffixes like "Controller" and "Page" from names: `route_name = item.replace("Controller", "").replace("Page", "").lower()`. This guesses `/loginpage` instead of `/login`, `/adminusers` instead of `/admin/users`.

3. **Heuristic table names.** `ef_core_entities` appends `s` to entity names to guess table names. `UserRefreshToken` → `userrefreshtokens`. No FK mapping. No field-to-column mapping.

4. **No aggregates.** No concept of root aggregate, owned entities, or aggregate boundaries. Cannot drive SQL schema without this.

5. **No commands or queries.** Behaviors are named but not typed as commands (write) vs queries (read). No input/output field specification. Cannot generate API endpoint signatures from this.

6. **No authorization boundaries.** `authorization_hints` is a flat list of strings. There is no structure binding "this command requires role X" or "this query is scoped to the authenticated user's CustomerId."

7. **No persistence spec.** No table → entity mapping. No index requirements. No FK constraints. Cannot emit a SQL migration script from this.

8. **No invariants or validation structure.** `validation_rules` is a copy of the flat `rules` string list. Rules in `070_rules.json` contain `constants`, `reset` procedures, `technical_debt` flags — none of it survives into rebuild.

9. **No state transition table.** State transitions are embedded in free-text strings inside `030_flows.json` (`"0 → 1: POST /login returns 428"`). They are not extracted as a machine-readable structure.

10. **No event producer/consumer mapping.** Events are present in `040_events.json` but not structured in the rebuild output as producer → consumer chains.

### Blockers for real rebuild

Without fixing the above, the rebuild output cannot:
- Generate a correct SQL migration (no tables, columns, types, FKs, indexes)
- Generate API endpoint stubs (no typed commands/queries with field shapes)
- Generate Blazor page component shells (no routes, no command bindings, no role gates)
- Generate authorization policies (no role → operation mapping)
- Generate background service stubs (no trigger, schedule, or purpose per job)

---

## 2. Rebuild Model V2 Target

### Design goals

1. **Domain-first, not technology-first.** The structure describes what the domain *does* — aggregates, commands, flows, rules. Technology output (SQL, C#, Blazor) is derived from the domain structure, not guessed from technology names.

2. **Synthesis, not duplication.** `090_rebuild.json` receives computed, cross-file synthesis — not copies of other files. Each section maps to a specific set of feeder files with a defined derivation rule.

3. **Fields, not names.** Every entity must carry its typed field list, PKs, FKs, and nullable flags — copied or derived from `010_entities.json`, not inferred from the entity name.

4. **Commands and queries typed.** Every behavior is classified as a command (writes state) or a query (reads state) with explicit input fields, authorization level, and output shape.

5. **Authorization as a first-class dimension.** Each command and query carries a `requires_role` / `requires_profile_permission` specification. A standalone `permission_matrix` maps operations to role requirements.

6. **Additive and backward-compatible.** The existing `blazor_pages` and `api_contracts` sections from the manually enriched v1 are absorbed into the new schema. New sections are added around them, not instead of them.

### Required properties by rebuild target

| Rebuild target | Required in 090 |
|---|---|
| SQL schema | `entities[].fields[]` (typed), `entities[].sql_table`, `entities[].primary_key`, `entities[].foreign_keys[]`, `indexes[]` |
| API | `commands[]` (verb, route, input fields, auth), `queries[]` (route, filters, return shape, auth) |
| Blazor UI | `ui_surfaces[]` (route, component, auth_required, commands_triggered, queries_used) |
| Authorization | `permission_matrix[]` (operation, roles[], scoping rule) |
| Background jobs | `background_processes[]` (trigger, schedule, purpose, commands_issued) |
| Integrations | `integrations[]` (name, protocol, direction, purpose) |
| Domain logic | `aggregates[]`, `state_transitions[]`, `invariants[]`, `validation_rules[]` |
| Events | `events[]` (name, producer, consumers, payload fields) |

---

## 3. Proposed `090_rebuild.json` Structure

This is the canonical V2 schema. All existing manually enriched data for `identity_access` maps into it with zero information loss.

```json
{
  "_meta": {
    "domain": "identity_access",
    "schema_version": "2.0",
    "generated_by": "DomainModelStore.build_rebuild_spec_v2",
    "generated_at": "2026-04-02T00:00:00Z",
    "rebuild_confidence": 0.87,
    "sources_used": ["010_entities.json", "020_behaviors.json", "030_flows.json", "070_rules.json"]
  },

  "aggregates": [
    {
      "id": "AGG_001",
      "name": "UserAccount",
      "root_entity": "User",
      "owned_entities": ["UserRefreshToken", "UserTwoFactorCode"],
      "invariants": ["INV_001", "INV_002"],
      "commands": ["CMD_001", "CMD_002", "CMD_003"],
      "source": "synthesized from 010 + 020"
    }
  ],

  "entities": [
    {
      "id": "ENT_001",
      "name": "User",
      "sql_table": "Users",
      "primary_key": "Id (int, IDENTITY)",
      "fields": [
        { "name": "Id",              "type": "int",       "nullable": false, "pk": true  },
        { "name": "Email",           "type": "nvarchar",  "nullable": false              },
        { "name": "Password",        "type": "nvarchar",  "nullable": false, "note": "SHA256+salt" },
        { "name": "FailedLoginCount","type": "smallint",  "nullable": false              },
        { "name": "IsLockedOut",     "type": "bit",       "nullable": false              },
        { "name": "Deleted",         "type": "bit",       "nullable": false              },
        { "name": "DateDeletedUtc",  "type": "datetime2", "nullable": true               },
        { "name": "CurrentProfileId","type": "int",       "nullable": false, "fk": "Profiles.Id" }
      ],
      "soft_delete": true,
      "technical_debt": ["TD_005: AuthenticatorSecret stored unencrypted"],
      "source": "010_entities.json ENT_User"
    }
  ],

  "value_objects": [
    {
      "id": "VO_001",
      "name": "TokenDto",
      "fields": [
        { "name": "AccessToken",  "type": "string"   },
        { "name": "ExpiresAt",    "type": "DateTime" },
        { "name": "RefreshToken", "type": "string"   }
      ],
      "source": "010_entities.json LoginEmailPasswordDto + TokenDto"
    }
  ],

  "commands": [
    {
      "id": "CMD_001",
      "name": "LoginWithEmailPassword",
      "type": "command",
      "handler": "UserController.Login()",
      "http_verb": "POST",
      "route": "/api/user/login",
      "input_fields": [
        { "name": "Email",    "type": "string", "required": true },
        { "name": "Password", "type": "string", "required": true }
      ],
      "output": "TokenDto",
      "authorization": "AllowAnonymous",
      "error_responses": {
        "401": "Invalid credentials",
        "403": "Account locked",
        "300": "Profile selection required",
        "428": "2FA required"
      },
      "invariants_checked": ["INV_001"],
      "events_emitted": [],
      "source": "020_behaviors.json BEH_001 + 090_api_contracts API_001"
    }
  ],

  "queries": [
    {
      "id": "QRY_001",
      "name": "GetUserInformation",
      "type": "query",
      "handler": "UserController.GetUserInformation()",
      "http_verb": "GET",
      "route": "/api/user/getuserinformation",
      "filters": [],
      "output": "UserInfoDto",
      "authorization": "Authenticated",
      "scoping": "returns data for _workContext.CurrentUser only",
      "source": "090_api_contracts + 020_behaviors.json"
    }
  ],

  "workflows": [
    {
      "id": "WF_001",
      "name": "StandardLogin",
      "trigger": "User submits email + password",
      "steps": [
        "Lookup user by email",
        "Check lockout (RULE_001)",
        "Verify password hash (RULE_004)",
        "Auto-select profile if single (RULE_003)",
        "Issue tokens"
      ],
      "branches": [
        { "condition": "Multiple profiles",     "outcome": "HTTP 300 → profile selector" },
        { "condition": "2FA required (SMS/email)", "outcome": "HTTP 428 → PIN flow" },
        { "condition": "2FA TOTP",              "outcome": "HTTP 428 → TOTP flow" },
        { "condition": "Invalid credentials",   "outcome": "HTTP 401" }
      ],
      "terminal_states": ["authenticated", "locked", "2fa_pending", "profile_selection_pending"],
      "source": "030_flows.json FLOW_001"
    }
  ],

  "state_transitions": [
    {
      "id": "ST_001",
      "entity": "LoginPage",
      "from_state": "slide_0",
      "to_state": "slide_1",
      "trigger": "POST /login returns HTTP 428 (SMS/email 2FA)",
      "guard": "authenticatorApp == false",
      "source": "090_blazor_pages PAGE_LOGIN.state_machine + 030_flows.json FLOW_001"
    },
    {
      "id": "ST_002",
      "entity": "LoginPage",
      "from_state": "slide_0",
      "to_state": "slide_5",
      "trigger": "POST /login returns HTTP 428 (TOTP)",
      "guard": "authenticatorApp == true",
      "source": "090_blazor_pages PAGE_LOGIN.state_machine"
    }
  ],

  "invariants": [
    {
      "id": "INV_001",
      "scope": "User",
      "invariant": "User is locked when IsLockedOut=true OR (FailedLoginCount > 5 AND lockout period not expired)",
      "enforced_by": "UserController.Login() pre-check",
      "source": "070_rules.json RULE_001"
    },
    {
      "id": "INV_002",
      "scope": "User",
      "invariant": "CountryId MUST equal LanguageId at all times (design quirk — DO NOT separate)",
      "enforced_by": "User.UpdateFromForm()",
      "source": "070_rules.json RULE_007"
    }
  ],

  "validation_rules": [
    {
      "id": "VAL_001",
      "name": "PasswordLockout",
      "applies_to": "CMD_001 LoginWithEmailPassword",
      "rule": "FailedLoginCount > 5 AND (UtcNow - DateLastFailedLoginUtc).Minutes < (FailedLoginCount - 5)",
      "constant": "_FAILED_LOCK_COUNT = 5",
      "reset_procedure": "POST /api/user/resetfailedloginandunlock",
      "source": "070_rules.json RULE_001"
    }
  ],

  "permission_matrix": [
    {
      "id": "PERM_001",
      "operation": "CMD_001 LoginWithEmailPassword",
      "requires_role": [],
      "authorization": "AllowAnonymous",
      "scoping": "none"
    },
    {
      "id": "PERM_002",
      "operation": "QRY_GetUsers",
      "requires_role": ["SuperAdmin", "CustomerAdmin"],
      "authorization": "Authenticated",
      "scoping": "customerId from _workContext.CurrentUser.CurrentCustomerId"
    }
  ],

  "persistence": [
    {
      "id": "PERS_001",
      "entity": "User",
      "sql_table": "Users",
      "operations": ["INSERT", "SELECT", "UPDATE"],
      "soft_delete_column": "Deleted",
      "indexes": [
        { "columns": ["Email"], "unique": true },
        { "columns": ["CurrentProfileId"], "unique": false }
      ],
      "source": "010_entities.json ENT_User"
    },
    {
      "id": "PERS_002",
      "entity": "UserRefreshToken",
      "sql_table": "UserRefreshTokens",
      "operations": ["INSERT", "SELECT", "DELETE"],
      "ttl": "30 minutes (sliding on refresh use)",
      "source": "010_entities.json ENT_UserRefreshToken"
    }
  ],

  "background_processes": [
    {
      "id": "BG_001",
      "name": "ExpiredRefreshTokenCleanup",
      "trigger": "scheduled",
      "schedule": "inferred — not explicitly documented",
      "purpose": "Remove expired UserRefreshToken rows from DB",
      "commands_issued": [],
      "confidence": 0.6,
      "source": "050_batch.json (if present)"
    }
  ],

  "integrations": [
    {
      "id": "INT_001",
      "name": "Azure AD / Entra ID (MSAL)",
      "type": "identity_provider",
      "direction": "inbound",
      "protocol": "OIDC / idToken",
      "endpoint": "POST /api/user/loginad",
      "purpose": "Exchange Entra ID idToken for ServiceAlert JWT",
      "source": "060_integrations.json + 020_behaviors.json BEH_004"
    }
  ],

  "events": [
    {
      "id": "EVT_001",
      "name": "UserLoggedIn",
      "producer": "UserController.Login()",
      "consumers": ["GlobalStateAndEventsService.loginEvent"],
      "payload_fields": ["UserModel"],
      "source": "040_events.json + 090_blazor_pages PAGE_LOGIN.events_emitted"
    }
  ],

  "ui_surfaces": [
    {
      "id": "UI_001",
      "route": "/login",
      "component": "LoginPage.razor",
      "auth_required": false,
      "layout": "GuestLayout",
      "commands_triggered": ["CMD_001 LoginWithEmailPassword"],
      "queries_used": [],
      "state_machine": "WF_001 StandardLogin (slides 0–5)",
      "source": "090_blazor_pages PAGE_LOGIN (migrated)"
    }
  ],

  "user_interactions": [
    {
      "id": "UX_001",
      "surface": "UI_001",
      "action": "Submit email + password",
      "triggers_command": "CMD_001",
      "feedback": {
        "success": "Navigate to dashboard",
        "error_401": "Show invalid credentials message",
        "error_403": "Show locked account message",
        "error_428": "Slide to 2FA PIN entry"
      },
      "source": "030_flows.json FLOW_001 + 090_blazor_pages PAGE_LOGIN"
    }
  ]
}
```

---

## 4. Feeder Mapping

Each section of `090_rebuild.json` V2 is synthesized from one or more feeder files. No section is a raw copy — each applies a derivation rule.

| 090 section | Primary feeder | Secondary feeder | Derivation rule |
|---|---|---|---|
| `aggregates` | `020_behaviors.json` (group commands by shared root entity) | `010_entities.json` (owned_entities) | Group commands that mutate the same root entity into one aggregate |
| `entities[].fields` | `010_entities.json` (fields array, verbatim) | — | Copy fields array; parse type/nullable from `"Name (type, flags)"` format |
| `entities[].sql_table` | `010_entities.json` source path (extract table name from C# domain class name) | — | `source` contains class path → infer table; fall back to `name + "s"` only if source absent |
| `value_objects` | `010_entities.json` items where type is "DTO" or name ends in "Dto"/"Model" | — | Filter by type="FACT" + name pattern |
| `commands` | `020_behaviors.json` type="command" OR steps contain mutation verbs (create, update, delete, set, send) | `090_api_contracts` (route + verb) | Match behavior → api_contract on route/name; copy input_fields from api_contract.request_dto |
| `queries` | `020_behaviors.json` type="query" OR steps are GET-only | `090_api_contracts` GET entries | Same cross-reference |
| `workflows` | `030_flows.json` (verbatim, restructured) | `020_behaviors.json` steps | Copy flow steps; resolve branches; link to command IDs |
| `state_transitions` | `090_rebuild.json` v1 `blazor_pages[*].state_machine.transitions` | `030_flows.json` branch conditions | Parse `"A → B: condition"` strings into structured `from_state / to_state / trigger` records |
| `invariants` | `070_rules.json` where rule describes a constraint on an entity field | — | Items with `rule` text containing field equality/comparison operators |
| `validation_rules` | `070_rules.json` all items | `020_behaviors.json` lockout_rule fields | Copy rule text + constants + reset_procedure |
| `permission_matrix` | `020_behaviors.json` (auth field if present) | `090_api_contracts[*].auth` | Authorization column from api_contracts → map to command/query IDs |
| `persistence` | `010_entities.json` (verbatim fields → column defs) | — | Entity fields → columns; infer table name from source path; extract FK hints from field names ending in "Id" |
| `background_processes` | `050_batch.json` | `080_pseudocode.json` | Copy trigger + schedule + purpose; link to any emitted commands |
| `integrations` | `060_integrations.json` | `020_behaviors.json` (AD login, SMS, etc.) | Copy integrations; supplement with behaviors that reference external systems |
| `events` | `040_events.json` | `090_blazor_pages[*].events_emitted` | Merge; resolve producer from behavior source; resolve consumers from Blazor page event handlers |
| `ui_surfaces` | `090_rebuild.json` v1 `blazor_pages` (verbatim → renamed) | — | Rename `blazor_pages` → `ui_surfaces`; add `commands_triggered` + `queries_used` by cross-referencing api_calls vs commands/queries |
| `user_interactions` | `090_rebuild.json` v1 state machine transitions + `030_flows.json` happy path | — | Each user action on a UI surface that triggers a command/query |

### What `090` does NOT duplicate

| Data already in other files | Kept there | In `090` |
|---|---|---|
| Full entity field definitions | `010_entities.json` | Referenced by ID only in `aggregates.owned_entities` |
| Behavior step sequences | `020_behaviors.json` | Workflow steps reference behavior IDs |
| Full flow descriptions | `030_flows.json` | `workflows[].steps` are brief; `030` remains the full narrative |
| Raw rule text | `070_rules.json` | `validation_rules` copies what is needed for rebuild; `070` stays authoritative |

---

## 5. File-Level Implementation Plan

### `core/domain/domain_model_store.py`

**Purpose:** Main writer for `090_rebuild.json`.

**Current problem:** `build_rebuild_spec()` calls `_clean(model.get("entities"))` which converts structured objects to plain strings. Everything below then operates on strings.

**Required change:** Replace `_clean()` consumption of `entities`, `behaviors`, `rules`, `events`, `flows` with direct structured object access:

```python
# Current (WRONG) — loses all structure:
entities = _clean(model.get("entities"))   # ["User", "LoginEmailPasswordDto", ...]

# Required (V2) — preserves structure:
entities = [e for e in (model.get("entities") or []) if isinstance(e, dict)]
behaviors = [b for b in (model.get("behaviors") or []) if isinstance(b, dict)]
```

Then replace `build_rebuild_spec()` with `build_rebuild_spec_v2()` that:
1. Derives `entities` with typed fields from `entities[].fields`
2. Classifies `behaviors` into `commands` vs `queries` via: behavior has no mutation verbs in steps → query; else command
3. Maps `api_contracts` from v1 `090_rebuild.json` blazor enrichment → links to command IDs by route matching
4. Extracts `state_transitions` from `flows[*].branches` and `blazor_pages[].state_machine.transitions`
5. Copies `validation_rules` from `rules` objects (not flattened strings)
6. Maps `persistence` from entities: field name ending in `Id` → FK candidate; source path → table name

**Size estimate:** ~120 lines replacing the current ~100-line heuristic method.

### `core/domain/ai_prompt_builder.py`

**Purpose:** Builds the LLM prompt that extracts domain knowledge from source assets.

**Current problem:** Not verified in this audit, but likely requests entity/behavior/flow data without telling the LLM to preserve field-level detail or classify behaviors as command/query. The resulting `model["entities"]` likely contains flat name strings rather than structured objects.

**Required change:** Update the prompt to instruct the LLM to:
1. Return entities as objects with `name`, `fields[]` (typed), `source`, `sql_table`
2. Return behaviors as objects with `id`, `name`, `type` (`command|query`), `steps[]`, `input_fields[]`, `output`, `authorization`
3. Return rules as objects with `id`, `name`, `rule`, `applies_to`, `constants`

This is a prompt-engineering change, not a schema change — it ensures the model dict contains structured objects that `build_rebuild_spec_v2()` can consume.

### `core/domain/domain_quality_gate.py`

**Purpose:** Guards whether a domain is complete enough to be marked `complete`.

**Current problem:** `090_rebuild.json` passes the gate as long as the file exists. A stub with empty arrays satisfies the gate.

**Required change:** Add a soft V2 check after the file-exists check:

```python
def _rebuild_has_substance(rebuild_path: str) -> bool:
    """True if 090_rebuild.json has at least one non-empty structural section."""
    try:
        with open(rebuild_path, encoding="utf-8") as f:
            rb = json.load(f)
        structural = ["aggregates", "commands", "queries", "entities", "persistence"]
        return any(rb.get(k) for k in structural)
    except (OSError, json.JSONDecodeError, ValueError):
        return False
```

Gate fails if `090_rebuild.json` exists but all structural sections are empty arrays.

### `core/domain/domain_model_store.py` — V1 migration helper

**Purpose:** Migrate the manually enriched `identity_access/090_rebuild.json` v1 to V2 schema without data loss.

**Required change:** Add a one-time migration method:

```python
def migrate_rebuild_v1_to_v2(self, domain_name: str) -> None:
    """Migrate 090_rebuild.json from v1 (blazor_pages/api_contracts) to V2 schema.
    
    - blazor_pages → ui_surfaces
    - api_contracts → commands/queries based on HTTP verb
    - All other v1 keys preserved under '_v1_legacy' for reference
    """
```

This method is called once per domain that has a manually-enriched v1 file. It must be explicitly invoked (not called automatically by the engine) to prevent accidental overwrites.

### No other files require immediate changes

`domain_scoring.py`, `domain_learning_loop.py`, `domain_completion_protocol.py`, and `domain_autonomous_search.py` do not touch `090_rebuild.json` directly. They work from the aggregated model dict and from scores. They do not need changes for Phase 1 of this contract.

---

## 6. Quality Bar for `090_rebuild.json`

### Minimum acceptable (passes file gate)

- File exists and is valid JSON
- `_meta.schema_version` present
- At least one non-empty array among `aggregates`, `commands`, `queries`, `entities`, `persistence`
- No section contains only stub objects (empty `fields: []`, empty `steps: []` for every item)

An engine-produced V2 file with 2 real entities and 3 real commands meets minimum.

### Strong (usable for code generation)

All of the following are true:

- `entities`: every entity has ≥ 1 field with type and nullable flag
- `commands`: every command has `route`, `http_verb`, `authorization`, ≥ 1 `input_fields`
- `queries`: every query has `route`, `authorization`, `output` type
- `persistence`: every entity in `entities` has a matching `persistence` entry with `sql_table`
- `permission_matrix`: every command and query has an entry
- `invariants`: ≥ 1 invariant present
- `state_transitions`: present if domain has multi-step flows (e.g., login wizard, 2FA)

A strong file can generate: SQL CREATE TABLE statements, ASP.NET Core controller stubs with correct routes and auth attributes, Blazor page shells with correct route parameters and role guards.

### Excellent (sufficient for autonomous rebuild)

Strong criteria plus:

- `aggregates`: every aggregate has `root_entity`, `owned_entities[]`, `invariants[]`
- `commands[]`: each has `events_emitted[]` and `invariants_checked[]`
- `state_transitions`: covers all multi-slide/multi-step flows completely
- `user_interactions`: every UI surface action that triggers a command is captured
- `background_processes`: every job has `trigger`, `schedule`, `purpose`
- `integrations`: every external dependency has `protocol` and `direction`
- `rebuild_confidence` score ≥ 0.85 (computed from field fill-rate across sections)

An excellent file can drive: a complete Blazor component tree scaffold, SQL migration with FKs and indexes, an OpenAPI spec draft, and ASP.NET Core authorization policy definitions.

### `rebuild_confidence` formula

```
score = mean([
    entity_field_coverage,     # entities with ≥1 typed field / total entities
    command_route_coverage,    # commands with route+auth / total commands
    query_coverage,            # queries with output+auth / total queries
    persistence_coverage,      # entities with matching persistence entry / total entities
    permission_coverage,       # operations with permission_matrix entry / total operations
])
```

Range: 0.0–1.0. Threshold for "strong": ≥ 0.70. Threshold for "excellent": ≥ 0.85.

---

## 7. Migration Strategy

### Phase 1 — Structural enrichment (additive, zero engine risk)

1. Add `build_rebuild_spec_v2()` to `DomainModelStore` **alongside** the existing `build_rebuild_spec()`. Do not remove the old method.
2. Add `_rebuild_has_substance()` to `domain_quality_gate.py` as an optional soft check (not yet wired into `is_domain_complete()`).
3. Run `migrate_rebuild_v1_to_v2("identity_access")` once manually to produce the first V2 file from the manually enriched v1.
4. Confirm the V2 file passes the quality bar manually before proceeding.

### Phase 2 — Prompt upgrade (requires engine run validation)

5. Update `ai_prompt_builder.py` to request structured entity/behavior/rule objects rather than flat strings.
6. Run the engine on a new domain (not `identity_access`) with the new prompt.
7. Confirm `model["entities"]` contains structured objects, not strings.
8. Switch engine to call `build_rebuild_spec_v2()` instead of `build_rebuild_spec()`.

### Phase 3 — Gate wiring (after two successful V2 domains)

9. Wire `_rebuild_has_substance()` into `is_domain_complete()` as a hard gate.
10. Remove `build_rebuild_spec()` (the old heuristic method).
11. At this point the V2 contract is the only contract.

### Invariant during migration

During Phases 1 and 2, both methods coexist. The engine still calls the old method unless explicitly switched. The manually migrated `identity_access/090_rebuild.json` is written by migration helper, not by the running engine. No engine run can accidentally overwrite it with the heuristic version unless `save_rebuild_spec()` is called.

### What stays the same

- `000–080` file schema: no changes
- `095_decision_support.json`: no changes
- `domain_state.json` and `000_meta.json`: no changes
- `is_domain_complete()` existing checks: no changes until Phase 3

---

## 8. Stop Rule

**Change first:** Phase 1 (add `build_rebuild_spec_v2()`, add `_rebuild_has_substance()`, run migration helper for `identity_access`). All additive.

**Do NOT change yet:**

| File | Reason |
|---|---|
| `core/domain/ai_prompt_builder.py` | Prompt change affects ALL domains in flight. Do validation on a new domain first (Phase 2). |
| `core/domain/domain_quality_gate.py` — gate wiring | Wiring `_rebuild_has_substance()` as a hard gate will fail existing domains with stub rebuild files. Do Phase 3 only after all active domains have V2 files. |
| `core/domain/domain_model_store.py` — remove old method | Keep `build_rebuild_spec()` until the new method is confirmed on at least 2 domains. |
| `domains/identity_access/090_rebuild.json` | The manually enriched v1 is the best rebuild data in the system. Do NOT allow the engine to overwrite it automatically. Migration must be explicit and reviewed. |
| `domain_scoring.py` | Score weights do not change. Rebuild quality is gated at the file gate layer, not the score layer. |
