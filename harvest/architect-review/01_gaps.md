# Gaps — Beslutninger krævet inden build

**Instruktioner:** Sæt `GO` / `HOLD` / `SPLIT` / `MERGE` / `DROP` / `RENAME` ud for hvert punkt.

---

## GAP-A: 6 tomme "Other X Operations" stories

Auto-harvest fandt aktivitet der ikke passede i capability-grupper. Placeholders uden verbs/resource.

| Story | Domæne | Beslutning |
|-------|--------|------------|
| US-043 Other Messaging Operations | Messaging & Communication | `[ ]` |
| US-044 Other Customer Operations | Customer & Enrollment | `[ ]` |
| US-045 Other Analytics Operations | Analytics & Reporting | `[ ]` |
| US-046 Other Address Operations | Address & Data | `[ ]` |
| US-047 Other Finance Operations | Finance & Operations | `[ ]` |
| US-048 Other User Operations | User & Access Management | `[ ]` |

**Muligheder:** DROP alle / Uddyb hvad de skal indeholde og tilføj som rigtige stories

---

## GAP-B: Dubletter — samme ressource i to domæner

| Ressource | Story 1 | Story 2 | Beslutning |
|-----------|---------|---------|------------|
| `customer` | US-002 Manage Customers (Customer & Enrollment, fuld CRUD) | US-031 Manage Customers (User & Access Mgmt, GET only) | `[ ]` |
| `receiver` | US-015 Manage Receivers (Address & Data, GET+POST) | US-035 Manage Receivers (User & Access Mgmt, POST only) | `[ ]` |

**Muligheder per linje:** `GO begge` / `MERGE` / `RENAME den ene`

Bemærk: US-031 er sandsynligvis en SuperAdmin-liste. US-035 kan være "tildel bruger til modtagergruppe".

---

## GAP-C: Features i GreenAI-backend uden user story

Disse er fuldt implementeret i backend men mangler UI-story:

| Feature | Backend status | Har story? | Anbefaling |
|---------|---------------|------------|------------|
| Email (send, draft, list) | ✅ DONE — `/email/create`, `/email/list` | ❌ | Tilføj US-NEW-01 |
| Conversations (list, get, mark-read) | ✅ DONE | US-038 P3 (fejlplaceret) | RENAME + P1 |
| Warnings (create, list, process) | ✅ DONE | US-040 P1 ✅ | — |
| JobManagement (monitor, SSE) | ✅ DONE | ❌ | Tilføj US-NEW-02 |

**Beslutning:**
- US-038 Conversations flyttes til Messaging + P1: `[ ]` JA / `[ ]` NEJ
- Email US-NEW-01 tilføjes: `[ ]` JA / `[ ]` NEJ
- Jobs US-NEW-02 tilføjes: `[ ]` JA / `[ ]` NEJ

---

## GAP-D: Sandsynlig forkert domæneplacering

| Story | Nuværende domæne | Sandsynligt korrekt | Beslutning |
|-------|-----------------|---------------------|------------|
| US-022 Manage Maps | User & Access Management | Address & Data | `[ ]` |
| US-041 Manage Weathers | Messaging P1 | Operations / Analytics | `[ ]` |

---

## GAP-E: Prioritetsfordeling er skæv

65% af alle stories er P3 — auto-logikken satte alt uden Messaging/Customer+POST til P3.

| Prioritet | Antal nu |
|-----------|----------|
| P1 | 12 |
| P2 | 5 |
| P3 | 31 |

**Se `02_all_stories.md` og markér hvad der reelt er P2 i kolonnen "Ny prio".**
