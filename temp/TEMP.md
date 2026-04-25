## §STATE SNAPSHOT — 2026-04-25

```
build_state       : SUCCESS — 0 warnings / 0 errors
tests             : 922/922 PASS (exit 0)
requires_chatgpt_refresh : false (upload bekræftet 2026-04-25)

slices_locked:
  MessageWizard                   DONE 🔒
  DispatchPipeline                DONE 🔒
  AccessControl                   DONE 🔒
  GovernanceLayer                 DONE 🔒
  ArchitectureEnforcementLayer    DONE 🔒
  AIArchitectureLayer             DONE 🔒
  UserStories                     DONE 🔒

slices_in_progress : NONE
system_state       : DONE 🔒 — GREENAI CORE COMPLETE
analysis_status    : PARTIALLY VERIFIED
confidence_level   : VERIFIED (file+method level)

known_gaps:
  HIGH-01: UI recovery visibility — ingen auto-refresh/polling, retry kun på detalje-siden
  EP-01:   ENFORCEMENT_PATTERNS.md stale doc (kode er korrekt — ikke runtime-problem)
```

---

## §CHANGE PROOF — seneste (2026-04-25, GOVERNANCE GOLD RULES)

```
files_changed  : 1
  ~ c:\Udvikling\shared\GOVERNANCE.md   (4 sektioner tilføjet: §13-§16)
lines_added    : ~60
build_status   : N/A (doc only)
warnings       : 0
```

---

## §ANALYZE — GET CURRENT USER PROFILE — 2026-04-25

MODE: N-A

```
1. ENTITY
   Interface : src/GreenAi.Api/SharedKernel/Auth/ICurrentUser.cs
               interface ICurrentUser
               fields: UserId, CustomerId, ProfileId, LanguageId, Email,
                       IsImpersonating, OriginalUserId, IsAuthenticated

   Impl      : src/GreenAi.Api/SharedKernel/Auth/HttpContextCurrentUser.cs
               sealed class HttpContextCurrentUser : ICurrentUser
               source: JWT claims via ClaimsPrincipal
               HTTP  → IHttpContextAccessor.HttpContext.User
               Blazor → BlazorPrincipalHolder (set by component before Mediator.Send)

   Response  : src/GreenAi.Api/Features/Auth/Me/MeResponse.cs
               sealed record MeResponse(UserId, CustomerId, ProfileId, LanguageId,
                                        Email, IsImpersonating, OriginalUserId)

2. BEHAVIOR
   file   : src/GreenAi.Api/Features/Auth/Me/MeHandler.cs
   method : MeHandler.Handle(MeQuery, CancellationToken)  line 13
   logic  : reads ICurrentUser properties → maps to MeResponse → Result<MeResponse>.Ok(response)
            NO DB query — pure JWT claim read

   UI:
   file   : src/GreenAi.Api/Components/Pages/UserSelfService/UserProfilePage.razor
   method : OnAfterRenderAsync(bool firstRender)  line ~102
   call   : PrincipalHolder.Set(authState.User) → Mediator.Send(new MeQuery())

3. FLOW
   Endpoint : src/GreenAi.Api/Features/Auth/Me/MeEndpoint.cs
              MeEndpoint.Map  line 10
              GET /api/auth/me — .RequireAuthorization()

   Query    : src/GreenAi.Api/Features/Auth/Me/MeQuery.cs  line 7
              sealed record MeQuery : IRequest<Result<MeResponse>>

   Handler  : src/GreenAi.Api/Features/Auth/Me/MeHandler.cs
              Handle  line 13 → ICurrentUser → Result<MeResponse>.Ok

4. BUSINESS RULES
   RULE 1 : UserId.Value > 0 when IsAuthenticated
            enforced: ICurrentUser.cs (contract) + HttpContextCurrentUser.cs line 47 (throws)
   RULE 2 : CustomerId.Value never 0
            enforced: ICurrentUser.cs (contract) + HttpContextCurrentUser.cs line 52 (throws)
   RULE 3 : ProfileId.Value > 0 for IRequireProfile requests
            enforced: src/GreenAi.Api/SharedKernel/Pipeline/RequireProfileBehavior.cs
   RULE 4 : MeQuery does NOT carry IRequireProfile — only requires IsAuthenticated
            evidence: MeQuery.cs line 7 (no IRequireProfile marker)
   RULE 5 : Blazor must call BlazorPrincipalHolder.Set before Mediator.Send
            enforced: HttpContextCurrentUser.cs line 33-34 (throws if no principal)
   RULE 6 : No DB query for Me read
            evidence: MeHandler.cs — no IDbSession injected
```

---

## §EXISTENCE CHECK — USER PROFILE READ — 2026-04-25

MODE: N-A

```
1. ENTITIES

   ICurrentUser (interface)
     file : src/GreenAi.Api/SharedKernel/Auth/ICurrentUser.cs
     fields: UserId, CustomerId, ProfileId, LanguageId, Email,
             IsImpersonating, OriginalUserId, IsAuthenticated

   HttpContextCurrentUser (implementation)
     file : src/GreenAi.Api/SharedKernel/Auth/HttpContextCurrentUser.cs
     type : sealed class HttpContextCurrentUser : ICurrentUser
     source: JWT ClaimsPrincipal (HTTP: IHttpContextAccessor / Blazor: BlazorPrincipalHolder)

   MeResponse (read model)
     file : src/GreenAi.Api/Features/Auth/Me/MeResponse.cs
     type : sealed record MeResponse(UserId, CustomerId, ProfileId, LanguageId,
                                     Email, IsImpersonating, OriginalUserId)

   ProfileSummary (profile list item)
     file : src/GreenAi.Api/SharedKernel/Auth/ProfileSummary.cs
     type : sealed record ProfileSummary(int ProfileId, string DisplayName)

   ProfileRecord (auth / select profile)
     file : src/GreenAi.Api/Features/Auth/SelectProfile/SelectProfileRepository.cs  line 13
     used in: SelectProfileRepository.GetAvailableProfilesAsync

   DB tables: [dbo].[Profiles], [dbo].[ProfileUserMappings], [dbo].[UserCustomerMemberships]

2. BEHAVIORS

   Me read (current user identity from JWT — NO DB)
     file   : src/GreenAi.Api/Features/Auth/Me/MeHandler.cs
     method : MeHandler.Handle  line 13
     source : ICurrentUser → MeResponse

   Update user display name
     file   : src/GreenAi.Api/Features/UserSelfService/UpdateUser/UpdateUserHandler.cs
     method : UpdateUserHandler.Handle  line 19
     sql    : UpdateUserDisplayName.sql → UPDATE [dbo].[Profiles] SET DisplayName WHERE Id = @ProfileId

   Update user language
     file   : src/GreenAi.Api/Features/UserSelfService/UpdateUser/UpdateUserHandler.cs
     method : UpdateUserHandler.Handle  line 23
     sql    : UpdateUserLanguage.sql → UPDATE [dbo].[UserCustomerMemberships] SET LanguageId

   Select profile (auth flow)
     file   : src/GreenAi.Api/Features/Auth/SelectProfile/SelectProfileHandler.cs
     method : SelectProfileHandler.Handle  line 25
     repo   : SelectProfileRepository.GetAvailableProfilesAsync
     sql    : GetAvailableProfiles.sql → SELECT FROM Profiles JOIN ProfileUserMappings
              WHERE UserId = @UserId AND CustomerId = @CustomerId

3. FLOWS

   GET /api/auth/me (read identity)
     file   : src/GreenAi.Api/Features/Auth/Me/MeEndpoint.cs  line 10
     query  : MeQuery → MeHandler.Handle → Result<MeResponse>.Ok
     auth   : .RequireAuthorization()

   PUT /api/user/update (write display name / language)
     file   : src/GreenAi.Api/Features/UserSelfService/UpdateUser/UpdateUserEndpoint.cs  line 10
     command: UpdateUserCommand → UpdateUserHandler.Handle → DB
     auth   : .RequireAuthorization() + IRequireProfile (pipeline enforced)

   Blazor UI load (UserProfilePage)
     file   : src/GreenAi.Api/Components/Pages/UserSelfService/UserProfilePage.razor
     method : OnAfterRenderAsync  line ~102
     flow   : PrincipalHolder.Set → MeQuery → _email
              JWT claims fallback for _displayName, _role, _memberSince
     save   : SaveAsync → UpdateUserCommand(_displayName, null)

4. AUTH / CONTEXT

   HttpContextCurrentUser reads from:
     HTTP   : IHttpContextAccessor.HttpContext.User (Bearer token claims)
     Blazor : BlazorPrincipalHolder.Current (set by component before Mediator.Send)
     file   : src/GreenAi.Api/SharedKernel/Auth/HttpContextCurrentUser.cs  line 33-34

   Claims used:
     GreenAiClaims.Sub          → UserId           line 47
     GreenAiClaims.CustomerId   → CustomerId        line 52
     GreenAiClaims.ProfileId    → ProfileId         line 57
     GreenAiClaims.LanguageId   → LanguageId        line 62
     GreenAiClaims.Email        → Email             line 67
     GreenAiClaims.ImpersonatedUserId → IsImpersonating / OriginalUserId  line 72-79

   Pipeline enforcement:
     IRequireProfile → RequireProfileBehavior
       file: src/GreenAi.Api/SharedKernel/Pipeline/RequireProfileBehavior.cs
     IRequireAuthentication → AuthorizationBehavior
       file: src/GreenAi.Api/SharedKernel/Pipeline/AuthorizationBehavior.cs
```

---

## §COPILOT → ARCHITECT — Åbne spørgsmål

*Ingen åbne spørgsmål pt.*

---
