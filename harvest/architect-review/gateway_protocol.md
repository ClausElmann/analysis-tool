# Analysis Tool — Gateway Protocol

**STATUS:** LOCKED — kræver Architect approval for ændringer  
**ROLE:** SYSTEM KERNEL (ikke runtime dokument)  
**Dato:** 2026-04-23

---

## COPILOT → ARCHITECT — ANALYSIS TOOL AS GATEWAY (2026-04-23)

**Status:** Afventer Architect-direktiv

### 1. FORMÅL

Analysis-tool er den **eneste** lovlige adgangsvej til originalviden under GreenAI build.

- Copilot må **aldrig** åbne `sms-service/` kode, Angular-komponenter eller legacy API direkte under build
- Al viden om originalsystemet er allerede abstraheret og verificeret i `analysis-tool/`
- Direkte brug af Layer 0 risikerer plagiat, stale data og context-drift

---

### 2. GATEWAY PRINCIP

GreenAI build (MODE B) må KUN slå op i:

| Kilde | Sti | Indhold |
|-------|-----|---------|
| Stories | `harvest/stories/` | Hvad der skal bygges |
| Domains | `domains/` | Forretningslogik per domæne |
| Behaviors | `corpus/ui_behaviors.jsonl` | Hvad brugeren må gøre |
| Flows | `corpus/flows.jsonl` | Processeforløb |
| Requirements | `corpus/requirements.jsonl` | Regler og krav |

**ALDRIG:**
- `sms-service/` (Layer 0 kode)
- `harvest/angular/` (gamle Angular-komponenter)
- Direkte endpoint-kald eller legacy SQL

---

### 3. OPSLAGSTYPER

**A. "Hvilket endpoint hører til denne UI handling?"**
- Input: handling-navn / story-id
- Lookup: `corpus/requirements.jsonl` → filter på `type: endpoint`
- Output: endpoint-sti + HTTP-metode + DTO-navn
- Fallback: `backend_ui_contract.md` → UNKNOWN hvis ikke fundet

**B. "Hvilket flow beskriver denne funktion?"**
- Input: feature-navn / story-id
- Lookup: `corpus/flows.jsonl` → filter på `domain` + `feature`
- Output: flow-steps array
- Fallback: UNKNOWN — STOP build

**C. "Hvad må brugeren gøre her?"**
- Input: komponent-navn / domæne
- Lookup: `corpus/ui_behaviors.jsonl` → filter på `component` eller `domain`
- Output: liste af tilladte actions + constraints
- Fallback: UNKNOWN — kræver arkitekt

**D. "Mangler vi noget?"**
- Input: story-id
- Lookup: sammenlign story's scope mod flows + requirements
- Output: liste af manglende flows/requirements (gap)
- Fallback: rapportér gap i RUNTIME STATE

---

### 4. BUILD-TIME WORKFLOW

For hver story i WAVE N:

```
1. Åbn story-fil (harvest/stories/US-xxx.md eller GS-xxx.md)
2. Identificér domæne + feature-navn
3. Lookup behaviors   → corpus/ui_behaviors.jsonl
4. Lookup flows       → corpus/flows.jsonl
5. Lookup requirements → corpus/requirements.jsonl
6. Vælg blueprint     → ui_blueprints.md
7. Map DTO/Command    → backend_ui_contract.md
8. Byg komponent      → kun ud fra ovenstående
9. Validér            → alle state-felter stammer fra kendte DTOs
```

Hvis ét trin returnerer UNKNOWN → **STOP — rapportér til RUNTIME STATE**

---

### 5. ANTI-PLAGIAT GARANTI

Gateway sikrer anti-plagiat ved at:
- Copilot kun ser **abstraheret** viden (behaviors, flows, requirements) — aldrig kode
- Behaviors er verificeret mod original men udtrykker *intent*, ikke implementation
- Flows beskriver *proces*, ikke kode-struktur
- Requirements beskriver *regler*, ikke metoder

Ingen kodelinje fra `sms-service/` må nogensinde kopieres eller parafraseres.

---

### 6. BEGRÆNSNINGER

| Situation | Handling |
|-----------|---------|
| Flow ikke fundet | Returnér UNKNOWN — byg ikke |
| Requirement mangler | STOP — rapportér gap |
| Behavior uklar | Kræv arkitekt-afklaring |
| DTO-felter ukendte | STOP — NO GUESS REGEL |
| Domain er UNKNOWN | STOP — kør ikke videre |

---

### 7. STOP REGLER

Copilot SKAL stoppe og rapportere i RUNTIME STATE hvis:

- `behavior` ikke findes i `ui_behaviors.jsonl`
- `flow` ikke kan matches på domæne + feature
- `endpoint` ikke findes i `backend_ui_contract.md` eller `requirements.jsonl`
- `domain` er `UNKNOWN` i `domains/`
- DTO-felter ikke kan verificeres

→ **Returnér altid UNKNOWN — aldrig gæt**

---

### 8. FREMTID

Mulige gateway-udvidelser:
- **Query API:** Python-script der besvarer opslagstyper A–D programmatisk
- **Coverage scoring:** Hvor stor andel af en story er dækket af corpus
- **Visual mapping:** Story → flows → behaviors som graf
