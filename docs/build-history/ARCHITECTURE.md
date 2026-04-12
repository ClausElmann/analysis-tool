# GreenAi — SSOT

## Stack
- .NET 10 / C# 13
- Blazor Server (same-host som Web API)
- Dapper (ingen EF Core, ingen ORM)
- SQL Server
- Custom JWT (ingen ASP.NET Identity)
- MediatR + FluentValidation + Scrutor
- xUnit + NSubstitute

## Projekter
| Projekt | Formål |
|---|---|
| `src/GreenAi.Api` | Blazor Server + Web API + SharedKernel + Features |
| `tests/GreenAi.Tests` | Unit tests (én fil per handler) |

## Mappestruktur (konvention)
```
src/GreenAi.Api/
  Features/
    [Domain]/
      [Feature]/
        [Feature]Command.cs      ← record : IRequest<Result<T>>
        [Feature]Handler.cs      ← IRequestHandler<TCmd, Result<T>>
        [Feature]Validator.cs    ← AbstractValidator<TCmd>
        [Feature]Response.cs     ← output record
        [Feature]Endpoint.cs     ← minimal API mapping
        [Feature]Page.razor      ← Blazor page (co-located)
        [Feature].sql            ← ÉN sql-fil per operation
  SharedKernel/
    Auth/    → ICurrentUser
    Db/      → IDbSession, DbSession, SqlLoader
    Ids/     → UserId, CustomerId, ProfileId
    Results/ → Result<T>, Error
    Tenant/  → ITenantContext
    Pipeline/→ ValidationBehavior (ordered)
tests/GreenAi.Tests/
  Features/[Domain]/[Feature]/
    [Feature]HandlerTests.cs
```

## Ikke-accepterede mønstre
- Inline SQL strings
- HttpContext i handlers
- EF Core (selv til migrering — brug GreenAi.DB SSDT Schema Compare)
- ASP.NET Identity
- Generic base repositories (shared across features)
- Implicit tenant-filtrering

## Repository-konvention (Retning A)
Feature-lokale repositories som tynde SQL-adaptere er **tilladt og foretrukket**.
De ene formål er at isolere SQL-filindlæsning og Dapper-kald fra handler-logik.

```
[Feature]Repository.cs      ← interface + impl, Dapper via IDbSession, SqlLoader
I[Feature]Repository.cs     ← interface-kontrakt (til NSubstitute i tests)
[Feature].sql               ← én sql-fil per operation (embedded resource)
```

Forbudt:
- Generic repository\<T\> på tværs af features
- Repository med forretningslogik
- Direkte `IDbSession` i handlers (undtagen admin-only batch-operationer)

## Governance
AI-governance regler lever i `ai-governance/` i dette projekt og er autoriteten for prompt-regler, anti-patterns og stack-analyse.

> **Note:** `analysis-tool/ai-governance/` er et BUILD-TIME redskab (Builder-Architect protokol under byggeriet). Det er ikke en permanent del af green-ai. Når byggeriet er færdigt kan analysis-tool slettes.
