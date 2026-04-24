# FIRST_VERTICAL_SLICE

```yaml
id: first_vertical_slice
version: 1.0.0
last_updated: 2026-04-03
ssot_source: docs/SSOT/governance/FIRST_VERTICAL_SLICE.md
target: login → frontpage → customer-admin

rule: Each slice's SSOT files MUST exist before implementation is validated.
rule: done_when criteria are the ONLY acceptance gate — not subjective judgment.

slice:

  - id: slice_1_login
    description: User obtains full JWT (UserId + CustomerId + ProfileId) via 3-step flow.
    status: PARTIALLY_COMPLETE

    ssot_required:
      - docs/SSOT/identity/auth-flow.md          # PENDING sprint_1 — create first
      - docs/SSOT/identity/current-user.md       # PENDING sprint_1 — create first
      - docs/SSOT/backend/patterns/result-pattern.md    # PENDING sprint_1
      - docs/SSOT/backend/patterns/endpoint-pattern.md  # EXISTS

    red_threads:
      - auth_flow
      - result_pattern
      - error_codes
      - strongly_typed_ids

    files:
      existing:
        - src/GreenAi.Api/Features/Auth/Login/LoginCommand.cs
        - src/GreenAi.Api/Features/Auth/Login/LoginHandler.cs
        - src/GreenAi.Api/Features/Auth/Login/LoginValidator.cs
        - src/GreenAi.Api/Features/Auth/Login/LoginResponse.cs
        - src/GreenAi.Api/Features/Auth/Login/LoginEndpoint.cs
        - src/GreenAi.Api/Features/Auth/Login/LoginPage.razor
        - src/GreenAi.Api/Features/Auth/Login/Login.sql
        - src/GreenAi.Api/Features/Auth/SelectCustomer/
        - src/GreenAi.Api/Features/Auth/SelectProfile/
      pending: []

    contracts:
      - name: LoginCommand
        shape: "{ Email: string, Password: string }"
      - name: LoginResponse
        shape: "{ Status: LoginStatus, Token: string? }"
        statuses: [Success, NeedsCustomerSelection, NeedsProfileSelection]
      - name: LoginFailure
        error_codes: [INVALID_CREDENTIALS → 401]

    done_when:
      - POST /auth/login returns JWT with CustomerId+ProfileId for single-profile user
      - POST /auth/login returns NeedsCustomerSelection for multi-membership user
      - POST /auth/login returns 401 INVALID_CREDENTIALS for wrong password
      - LoginPage.razor handles NeedsProfileSelection status (does not silently ignore)
      - E2E: Login_WithValidCredentials_RedirectsToHome → PASS
      - E2E: Login_WithWrongPassword_ShowsError → PASS

  - id: slice_2_frontpage
    description: Authenticated user redirected to home after login. Unauthenticated blocked.
    status: PARTIALLY_COMPLETE

    ssot_required:
      - docs/SSOT/backend/patterns/blazor-page-pattern.md  # PENDING sprint_1
      - docs/SSOT/identity/current-user.md                # PENDING sprint_1

    red_threads:
      - current_user
      - auth_flow

    files:
      existing:
        - src/GreenAi.Api/Components/Pages/Home.razor  # verify redirect target
        - src/GreenAi.Api/Features/Auth/Login/LoginPage.razor
      pending: []

    contracts:
      - name: HomeAccess
        shape: "Requires: valid JWT with CustomerId+ProfileId in Blazor auth state"
      - name: RedirectRule
        shape: "unauthenticated → /login | authenticated → /"

    done_when:
      - Authenticated user lands on / after login flow completes
      - Unauthenticated GET / → redirected to /login
      - E2E: CustomerAdmin_UnauthenticatedAccess_RedirectsToLogin → PASS

  - id: slice_3_customer_admin
    description: Admin sees customer settings, users list, profiles list on /customer-admin.
    status: FAILING — E2E timeout on heading selector

    ssot_required:
      - docs/SSOT/backend/patterns/blazor-page-pattern.md  # PENDING sprint_1 — root cause of failure
      - docs/SSOT/identity/current-user.md                # PENDING sprint_1 — root cause of failure
      - docs/SSOT/backend/patterns/result-pattern.md      # PENDING sprint_1
      - docs/SSOT/backend/patterns/handler-pattern.md     # EXISTS

    red_threads:
      - current_user
      - result_pattern
      - tenant_isolation
      - auth_flow

    files:
      existing:
        - src/GreenAi.Api/Features/CustomerAdmin/GetCustomerSettings/GetCustomerSettingsHandler.cs
        - src/GreenAi.Api/Features/CustomerAdmin/GetUsers/GetUsersHandler.cs
        - src/GreenAi.Api/Features/CustomerAdmin/GetProfiles/GetProfilesHandler.cs
        - src/GreenAi.Api/Components/Pages/CustomerAdmin/Index.razor
      pending: []

    contracts:
      - name: GetCustomerSettingsQuery
        shape: "inputs: [ICurrentUser.CustomerId] | output: Result<CustomerSettingsRow>"
        error_codes: [NO_CUSTOMER → 500]
      - name: GetUsersQuery
        shape: "inputs: [ICurrentUser.CustomerId] | output: Result<List<UserRow>>"
        error_codes: [NO_CUSTOMER → 500]
      - name: GetProfilesQuery
        shape: "inputs: [ICurrentUser.CustomerId] | output: Result<List<ProfileRow>>"
        error_codes: [NO_CUSTOMER → 500]

    known_failure:
      symptom: E2E timeout on [data-testid='customer-admin-heading']
      suspected_causes:
        - PrincipalHolder.Set() not called before Mediator.Send → CustomerId null → NO_CUSTOMER → redirect to /select-customer
        - OnAfterRenderAsync circuit not established before Playwright navigates
      diagnostic_command: >
        Invoke-Sqlcmd -ServerInstance "(localdb)\MSSQLLocalDB22" -Database "GreenAI_DEV"
        -TrustServerCertificate
        -Query "SELECT TOP 15 TimeStamp,Level,Message,Exception FROM Logs ORDER BY TimeStamp DESC"
      fix_protocol: docs/SSOT/testing/debug-protocol.md

    done_when:
      - GET /customer-admin → heading [data-testid='customer-admin-heading'] visible
      - Users tab shows seed users (admin@dev.local + others)
      - Profiles tab shows seed profiles (Nordjylland)
      - Unauthenticated GET /customer-admin → redirect to /login
      - E2E: CustomerAdmin_AfterLogin_ShowsHeading → PASS
      - E2E: CustomerAdmin_UsersTab_ShowsSeedUsers → PASS
      - E2E: CustomerAdmin_ProfilesTab_ShowsSeedProfiles → PASS
      - Integration tests: 112/112 → PASS

slice_completion_order:
  1: slice_1_login          → already 2/2 E2E passing
  2: slice_2_frontpage      → already 1/1 E2E passing
  3: slice_3_customer_admin → 0/3 E2E passing — ACTIVE WORK ITEM

next_action:
  step: resume E2E debugging for slice_3_customer_admin
  command: dotnet test tests/GreenAi.E2E/GreenAi.E2E.csproj --filter "CustomerAdmin_AfterLogin_ShowsHeading"
  protocol: docs/SSOT/testing/debug-protocol.md
  pending_ssot: create docs/SSOT/identity/current-user.md and docs/SSOT/backend/patterns/blazor-page-pattern.md
               as part of fixing + documenting the heading failure root cause
```
