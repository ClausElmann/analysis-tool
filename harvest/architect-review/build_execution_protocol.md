# GreenAI — Build Execution Protocol

**STATUS:** LOCKED — kræver Architect approval for ændringer  
**ROLE:** SYSTEM KERNEL (ikke runtime dokument)  
**Dato:** 2026-04-23

---

## COPILOT → ARCHITECT — BUILD EXECUTION PROTOCOL (2026-04-23)

**Status:** Afventer Architect-direktiv

### 1. OVERORDNET FLOW

```
Story (harvest/stories/XX-xxx.md)
  → Story Resolution   (find domain, behaviors, flows, requirements)
  → Blueprint Binding  (udfyld blueprint med konkrete data)
  → Build              (skriv Razor + code-behind)
  → Runtime Check      (validér mod corpus)
```

---

### 2. STORY RESOLUTION

For story `XX-xxx`:

```
1. Læs: harvest/stories/XX-xxx.md
   → udtræk: domain, feature, description

2. Find domain:
   → domains/{domain}/000_meta.json
   → felt: "name", "status"
   → STOP hvis status != DONE eller UNKNOWN

3. Find behaviors:
   → corpus/ui_behaviors.jsonl
   → filter: domain == story.domain AND feature == story.feature
   → output: liste af { action, constraint, component }
   → STOP hvis 0 resultater

4. Find flows:
   → corpus/flows.jsonl
   → filter: domain == story.domain AND feature == story.feature
   → output: liste af { step, trigger, outcome }
   → STOP hvis 0 resultater

5. Find requirements:
   → corpus/requirements.jsonl
   → filter: domain == story.domain AND feature == story.feature
   → output: liste af { rule, endpoint?, dto? }
   → STOP hvis 0 resultater
```

---

### 3. BLUEPRINT BINDING

Vælg blueprint ud fra story.type:

| story.type | Blueprint |
|-----------|-----------|
| list / crud | LIST PAGE |
| create / edit | FORM PAGE |
| view / detail | DETAILS PAGE |
| messaging | MESSAGING UI |
| auth | AUTH UI |

**LIST PAGE binding:**

```
columns    ← requirements hvor type == "field" → { name, type }
actions    ← behaviors → { action: "edit" | "delete" | "view" }
commands   ← flows → { trigger → endpoint + HTTP method }
state.Items ← requirements → DTO-navn (XxxDto)
```

**FORM PAGE binding:**

```
fields     ← requirements hvor type == "field" → MudTextField per felt
command    ← flows → Command-navn + properties
validation ← requirements hvor type == "rule" → FluentValidation regel
```

**Ukendt felt → STOP. Ingen antagelser om feltnavne, typer eller parametre.**

---

### 4. NO GUESS ENFORCEMENT

| Situation | Handling |
|-----------|---------|
| `field` ikke i requirements | STOP — returnér UNKNOWN |
| `endpoint` ikke i requirements eller backend_ui_contract.md | STOP — returnér UNKNOWN |
| `flow` matcher 0 resultater | STOP — returnér UNKNOWN |
| `domain` status != DONE | STOP — returnér UNKNOWN |
| `DTO`-navn ikke eksplicit angivet | STOP — spørg arkitekt |

**ALDRIG:** Gæt felt-typer, property-navne, HTTP-metoder eller DTO-struktur.

---

### 5. RUNTIME CHECKS

Efter build verificeres:

```
✅ Alle UI actions (edit, delete, create) findes i behaviors
✅ Alle Mediator.Send() kald har matchende requirement (endpoint/rule)
✅ Alle flows fra story er dækket af mindst ét UI element
✅ Ingen state-felt eksisterer uden kilde i requirements
✅ Ingen hardkodede strenge der burde komme fra Loc (ILocalizationContext)
```

Fejl ved check → annotér i RUNTIME STATE + STOP videre build på story.

---

### 6. OUTPUT — DETERMINISTISK BUILD

En story er klar til build når:

```
[ ] domain status = DONE
[ ] behaviors count > 0
[ ] flows count > 0
[ ] requirements count > 0
[ ] blueprint valgt
[ ] alle kolonner/felter mapped til kendte DTOs
[ ] alle commands mapped til kendte endpoints
```

Copilot starter **ikke** build før alle 7 punkter er ✅.  
Copilot **stopper** build ved første UNKNOWN og rapporterer i RUNTIME STATE.
