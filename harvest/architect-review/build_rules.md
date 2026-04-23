# BUILD RULES — GreenAI UI
**Dato:** 2026-04-23
**Status:** GÆLDENDE — alle WAVE 1-4 builds

---

## 1. FORBUDT

- Ingen kopiering af Angular kode fra sms-service
- Ingen kopiering af komponent-struktur fra Angular
- Ingen genbrug af variabelnavne fra legacy UI
- Ingen direkte mapping fra `component.ts` → Blazor
- Ingen import af Angular-mønstre (services, pipes, modules, decorators)

---

## 2. TILLADT

- Samme endpoints (backend er GreenAI — uændret)
- Samme user flows (defineret i US/GS story-filer)
- Samme business logic
- Samme funktionalitet

---

## 3. UI PRINCIPPER (Blazor-native)

- Brug MudBlazor komponenter (MudDataGrid, MudDialog, MudForm m.m.)
- Brug Razor patterns — IKKE Angular patterns
- State styres via C# (ikke frontend state frameworks)
- Navigation via Blazor routing (`@page "/route"`)
- CSS via `design-tokens.css` + `portal-skin.css` — ingen inline styles

---

## 4. IMPLEMENTATION RULE — per feature

```
INPUT:
  - Story-fil (US-xxx.md eller GS-xxx.md)
  - Backend endpoint (backend_ui_contract.md)

OUTPUT:
  - Ny Blazor Razor-komponent
  - Ingen reference til Angular-kode

ALDRIG:
  - "Dette svarer til Angular-komponenten X"
  - Copy-paste fra sms-service/
```

---

## 5. VERIFICATION — efter hver komponent

| Check | Krav |
|-------|------|
| Kan spores til en story? | **JA** — angiv ID |
| Kan spores til Angular-kode? | **NEJ** |
| Bruger MudBlazor? | **JA** |
| Bruger design-tokens? | **JA** |
| Har test? | **JA** — minimum happy-path |

---

## 6. GOAL

GreenAI UI skal være:
- **Funktionelt identisk** med sms-service Angular UI
- **Teknisk ny** — Blazor Server, C#, MudBlazor 8
- **Arkitekturmæssigt bedre** — Vertical Slice, ingen legacy-kode

---

*Gælder alle builds fra WAVE 1 og frem*
