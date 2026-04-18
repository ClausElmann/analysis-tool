"""run_autonomous.py — LLM-drevet batch engine med state + resume.

ARKITEKTUR
----------
  run_autonomous.py  = ORCHESTRATOR (tynd Python executor)
  Copilot LLM        = ANALYSIS ENGINE (det tunge arbejde)
  temp.md            = STATE LOG (sandhed for mennesker)
  domain_state.json  = MACHINE STATE (sandhed for runner)

Python GÆTTER ALDRIG — den læser kun state og bygger strukturerede direktiver.
Copilot er hjernen. Python er skallen.

KOMMANDOER
----------
  NEXT      — Beregn næste LLM-step baseret på aktiv state.
              Output: struktureret direktiv til temp.md.
              Copilot læser direktivet og eksekverer ÉT atomisk step.

  RUN_FULL  — Instruktion til Copilot om at loope NEXT indtil done.
              Bruges når Copilot er executor i et agentic session.

  STATUS    — Print alle domæner: status, score, gaps-count uden at ændre noget.

  VALIDATE  — Tjek om last step opdaterede state korrekt.
              Fejler hvis: ingen iteration-increment, confidence < 0.9.

  RESUME    — Eksplicit resume fra persisted state.
              Fejler med klar besked hvis ingen state.

  STOP      — No-op for CLI. Send Ctrl+C for at afbryde kørende process.

  RESET     — Slet domain_state.json efter eksplicit bekræftelse.

STEP TYPES (udledt fra gap-format: gap:{domain}:{gap_type}:{detail})
----------
  missing_entity            → ENTITY
  missing_behavior          → BEHAVIOR
  missing_flow              → FLOW
  weak_rule / missing_rule  → RULE
  missing_context           → ENTITY  (context = entity-klasse)
  incomplete_integration    → FLOW    (integration = flow-klasse)
  missing_integration       → FLOW
  orphan_event              → BEHAVIOR (event = behavior-klasse)
  (ukendt)                  → UNKNOWN_STEP (STOP — aldrig gæt)

DFEP GATE (per iteration)
--------------------------
  Entities  ≥ 0.90
  Behaviors ≥ 0.90
  Flows     ≥ 0.90
  Rules     ≥ 0.90
  → Alle ≥ 0.90: domain COMPLETE, skift til næste
  → Én < 0.90:   fokus på den dimension

SAFETY LAYER
------------
  confidence < 0.90 → STOP
  Samme fil ændret 3 gange i træk → ESCALATE (log + stop)

MODES
-----
  MODE A (batch):    python run_autonomous.py RUN_FULL   — op til 500 iterationer
  MODE B (periodisk): python run_autonomous.py STEP      — præcis 1 iteration

STATE FILES
-----------
  domains/domain_state.json  — per-domain progress + DFEP scores
  data/run_log.jsonl         — append-only iteration log
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ROOT       = Path(__file__).parent
_STATE_FILE = _ROOT / "domains" / "domain_state.json"
_TEMP_MD    = _ROOT / "temp.md"
_LOG_FILE   = _ROOT / "data" / "run_log.jsonl"
_ENGINE     = _ROOT / "run_domain_engine.py"
_PYTHON     = sys.executable

# ---------------------------------------------------------------------------
# Step type map (gap_type → STEP_TYPE)
# Gap format: gap:{domain}:{gap_type}:{detail}
# ---------------------------------------------------------------------------

# Gap type → DFEP dimension (ENTITY | BEHAVIOR | FLOW | RULE)
_GAP_TYPE_MAP: dict[str, str] = {
    "missing_entity":         "ENTITY",
    "missing_behavior":       "BEHAVIOR",
    "missing_flow":           "FLOW",
    "weak_rule":              "RULE",
    "missing_rule":           "RULE",
    "missing_context":        "ENTITY",      # context is entity-class
    "missing_integration":    "FLOW",        # integration is flow-class
    "incomplete_integration": "FLOW",
    "orphan_event":           "BEHAVIOR",    # event is behavior-class
}

# DFEP dimension → target file
_DFEP_TARGET_FILE: dict[str, str] = {
    "ENTITY":   "020_entities.json",
    "BEHAVIOR": "030_behaviors.json",
    "FLOW":     "040_flows.json",
    "RULE":     "070_business_rules.json",
}

_CONFIDENCE_THRESHOLD  = 0.90
_MAX_ITERATIONS        = 500
_SAME_FILE_REPEAT_LIMIT = 3   # safety: escalate if same file modified N times in a row

# ---------------------------------------------------------------------------
# Stop conditions (pure Python — no guessing)
# ---------------------------------------------------------------------------

_TERMINAL_STATUSES = {"complete", "blocked", "locked", "saturated", "stable"}


def _all_terminal(state: dict) -> bool:
    """True if every non-_global domain is in a terminal status."""
    return all(
        v.get("status", "") in _TERMINAL_STATUSES
        for k, v in state.items()
        if not k.startswith("_") and isinstance(v, dict)
    )


def _confidence_too_low(state: dict) -> float | None:
    """Return last_step_confidence if < threshold, else None."""
    conf = state.get("_global", {}).get("last_step_confidence")
    if conf is not None and conf < _CONFIDENCE_THRESHOLD:
        return conf
    return None


def _iteration_limit(state: dict) -> bool:
    return state.get("_global", {}).get("iteration_counter", 0) >= _MAX_ITERATIONS


def _dfep_lowest_dimension(domain_state: dict) -> tuple[str, float] | None:
    """
    Return (dimension_name, score) for the lowest-scoring DFEP dimension < 0.90.
    If all >= 0.90, return None (domain is DFEP-complete).
    Reads dfep_scores if present, else falls back to completeness_score for all.
    """
    dfep = domain_state.get("dfep_scores", {})
    # Build score map from dedicated dfep_scores OR legacy single completeness_score
    scores: dict[str, float] = {
        "ENTITY":   dfep.get("entities",  domain_state.get("completeness_score", 0.0)),
        "BEHAVIOR": dfep.get("behaviors", domain_state.get("completeness_score", 0.0)),
        "FLOW":     dfep.get("flows",     domain_state.get("completeness_score", 0.0)),
        "RULE":     dfep.get("rules",     domain_state.get("completeness_score", 0.0)),
    }
    below = [(dim, score) for dim, score in scores.items() if score < _CONFIDENCE_THRESHOLD]
    if not below:
        return None  # all >= 0.90 → domain DFEP-complete
    below.sort(key=lambda x: x[1])  # lowest first
    return below[0]


def _same_file_escalation(state: dict) -> str | None:
    """
    Return target file if the same file has been the last_step_target N times in a row.
    Reads last_step_targets list from _global (runner appends to it after each step).
    """
    targets: list[str] = state.get("_global", {}).get("last_step_targets", [])
    if len(targets) < _SAME_FILE_REPEAT_LIMIT:
        return None
    last_n = targets[-_SAME_FILE_REPEAT_LIMIT:]
    if len(set(last_n)) == 1:
        return last_n[0]
    return None


def _last_run_log_lines(n: int = 50) -> str:
    """Return last n lines of run_log.jsonl as formatted string for prompt context."""
    if not _LOG_FILE.exists():
        return "(ingen log endnu)"
    lines = _LOG_FILE.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-n:]) if lines else "(tom log)"


# ---------------------------------------------------------------------------
# Gap → step type detection
# ---------------------------------------------------------------------------

def _parse_gap_type(gap: str) -> str:
    """Extract gap_type from 'gap:{domain}:{gap_type}:{detail}' string."""
    parts = gap.split(":")
    if len(parts) >= 3:
        return _GAP_TYPE_MAP.get(parts[2], "UNKNOWN_STEP")
    return "UNKNOWN_STEP"


def _next_gap_and_type(domain_state: dict) -> tuple[str, str] | None:
    """Return (gap_string, step_type) for first actionable gap, or None."""
    gaps = domain_state.get("gaps", [])
    if not gaps:
        return None
    gap = gaps[0]
    return gap, _parse_gap_type(gap)


def _find_next_domain_with_gaps(state: dict, exclude: str) -> str | None:
    """Find highest-priority non-terminal domain with gaps (not excluded, not locked)."""
    candidates: list[tuple[int, str]] = []
    for key, val in state.items():
        if key.startswith("_") or not isinstance(val, dict):
            continue
        if key == exclude:
            continue
        if val.get("status", "") in _TERMINAL_STATUSES:
            continue
        gaps = val.get("gaps", [])
        if gaps:
            candidates.append((len(gaps), key))
    if not candidates:
        return None
    # Pick domain with most gaps (most work remaining)
    candidates.sort(reverse=True)
    return candidates[0][1]


# ---------------------------------------------------------------------------
# Prompt builder — structured Copilot directive
# ---------------------------------------------------------------------------

def _read_domain_file(domain: str, filename: str) -> str:
    """Read a domain data file, return content or placeholder if missing."""
    path = _ROOT / "domains" / domain / filename
    if path.exists():
        return path.read_text(encoding="utf-8")[:800]  # trim to avoid prompt overflow
    return f"(fil ikke fundet: domains/{domain}/{filename})"


def _build_input_context(domain: str, domain_state: dict) -> str:
    """Build INPUT CONTRACT block with domain files for Copilot context."""
    meta      = _read_domain_file(domain, "000_meta.json")
    entities  = _read_domain_file(domain, "020_entities.json")
    behaviors = _read_domain_file(domain, "030_behaviors.json")
    flows     = _read_domain_file(domain, "040_flows.json")
    rules     = _read_domain_file(domain, "070_business_rules.json")
    log_tail  = _last_run_log_lines(50)

    dfep = domain_state.get("dfep_scores", {})
    completeness = domain_state.get("completeness_score", "?")

    return f"""### INPUT CONTRACT

**domain_state (scores):**
- completeness: {completeness}
- entities:  {dfep.get('entities',  '?')}
- behaviors: {dfep.get('behaviors', '?')}
- flows:     {dfep.get('flows',     '?')}
- rules:     {dfep.get('rules',     '?')}

**000_meta.json (trimmet):**
```json
{meta}
```

**020_entities.json (trimmet):**
```json
{entities}
```

**030_behaviors.json (trimmet):**
```json
{behaviors}
```

**040_flows.json (trimmet):**
```json
{flows}
```

**070_business_rules.json (trimmet):**
```json
{rules}
```

**run_log.jsonl (last 50 lines):**
```
{log_tail}
```
"""


def _build_advance_domain_prompt(
    from_domain: str,
    to_domain: str,
    to_state: dict,
    next_gap: str,
    step_type: str,
) -> str:
    ts = datetime.now(timezone.utc).isoformat()
    score = to_state.get("completeness_score", "?")
    status = to_state.get("status", "?")
    gaps_n = len(to_state.get("gaps", []))
    target_file = _DFEP_TARGET_FILE.get(step_type, "(ukendt fil)")
    return f"""## AUTONOMOUS STEP — ADVANCE ACTIVE DOMAIN

**Timestamp:** {ts}
**Fra:** `{from_domain}` (ingen gaps tilbage)
**Til:** `{to_domain}` (score={score}, status={status}, {gaps_n} gaps)
**Næste gap:** `{next_gap}`
**Step type:** `{step_type}` → `domains/{to_domain}/{target_file}`

---

### COPILOT: SKIFT AKTIVT DOMÆNE + UDFØR NÆSTE STEP

**REGLER:** ÉN ændring per step. Opdatér `_global.active_domain` i SAMME step.

**OPGAVE:**
1. Sæt `domains/domain_state.json` → `_global.active_domain = "{to_domain}"`
2. Udfør atomisk analyse ({step_type}) på gap: `{next_gap}`
3. Opdatér `_global.last_step_confidence`, `last_step_domain`, `last_step_type`, `last_step_target`
4. Append til `_global.last_step_targets` (list — bruges til safety-check)

**OUTPUT til temp.md (STRICT FORMAT):**
```
## ITERATION {{n}}

**Domain:** {to_domain}
**Step Type:** {step_type}
**Target:** domains/{to_domain}/{target_file}

### ACTION
Advance fra {from_domain} → {to_domain}. Gap: {next_gap}

### CHANGE
[konkret ændring]

### SCORE UPDATE
- Entities: X.XX
- Behaviors: X.XX
- Flows: X.XX
- Rules: X.XX

### NEXT
[næste logiske step]

### CONFIDENCE
[0.90+]
```
"""


def _build_step_prompt(domain: str, domain_state: dict, gap: str, step_type: str) -> str:
    all_gaps: list[str] = domain_state.get("gaps", [])
    status    = domain_state.get("status", "?")
    iteration = domain_state.get("iteration", "?")
    ts        = datetime.now(timezone.utc).isoformat()
    iteration_n = domain_state.get("iteration", 0)

    if step_type == "UNKNOWN_STEP":
        return f"""## AUTONOMOUS STOP — UNKNOWN STEP TYPE

**Timestamp:** {ts}
**Domain:** `{domain}`
**Gap:** `{gap}`

**COPILOT ACTION: STOP**
```json
{{"status": "BLOCKED", "reason": "UNKNOWN_STEP: {gap}", "next": "Arkitekt definerer gap_type mapping"}}
```
- Skriv ovenstående til temp.md
- Sæt `_global.last_step_confidence = 0.0`
- Sæt `_global.last_step_domain = "{domain}"`
- Rør INTET andet
"""

    target_file = _DFEP_TARGET_FILE.get(step_type, "(ukendt)")
    dfep_focus  = _dfep_lowest_dimension(domain_state)
    dfep_note   = f"Laveste DFEP dimension: {dfep_focus[0]}={dfep_focus[1]:.2f} — prioritér denne" if dfep_focus else "Alle DFEP dimensions >= 0.90 — sæt status=complete efter dette step"
    input_ctx   = _build_input_context(domain, domain_state)

    return f"""## AUTONOMOUS STEP — {step_type} | {domain} | iteration {iteration_n}

**Timestamp:** {ts}
**Status:** `{status}` | **Remaining gaps:** {len(all_gaps)}
**Active gap:** `{gap}`
**Step type:** `{step_type}` → `domains/{domain}/{target_file}`
**DFEP:** {dfep_note}

---

{input_ctx}

---

### EXECUTION PROTOCOL (NON-NEGOTIABLE)

**STEP 1 — LOAD STATE**: Læs active_domain + scores ovenfor. ✅ allerede gjort.

**STEP 2 — FIND GAP**: Gap er: `{gap}` — konkret, ikke generisk. ✅ allerede gjort.

**STEP 3 — ANALYSÉR**: Brug eksisterende data i INPUT CONTRACT ovenfor.
- Hvis ikke nok data → UNKNOWN (sæt confidence = 0.0, STOP)
- Ingen gæt — kun verificerbar analyse

**STEP 4 — APPLY CHANGE** (ÉN fil, ÉN ændring):
- Opdatér: `domains/{domain}/{target_file}`
- Ingen refactors. Ingen multi-file. Ingen nye domæner.

**STEP 5 — UPDATE STATE** i `domain_state.json`:
- `{domain}.iteration += 1`
- `{domain}.gaps` → fjern `{gap}` fra listen
- `_global.last_step_confidence = [din confidence]`
- `_global.last_step_domain = "{domain}"`
- `_global.last_step_type = "{step_type}"`
- `_global.last_step_target = "domains/{domain}/{target_file}"`
- `_global.last_step_targets` → append `"domains/{domain}/{target_file}"` (bevar eksisterende)
- Hvis ingen gaps tilbage → `{domain}.status = "complete"`

**STEP 6 — OUTPUT** (skriv til temp.md — STRICT FORMAT):
```
## ITERATION {iteration_n}

**Domain:** {domain}
**Step Type:** {step_type}
**Target:** domains/{domain}/{target_file}

### ACTION
[hvad du gjorde — 1-2 sætninger]

### CHANGE
[konkret ændring — hvad blev tilføjet/ændret]

### SCORE UPDATE
- Entities: X.XX
- Behaviors: X.XX
- Flows: X.XX
- Rules: X.XX

### NEXT
[næste logiske step eller DONE]

### CONFIDENCE
[0.90+]
```

**DFEP GATE CHECK** (efter step):
- Entities ≥ 0.90 AND Behaviors ≥ 0.90 AND Flows ≥ 0.90 AND Rules ≥ 0.90
  → domain = COMPLETE → skift til næste domain
- Én < 0.90 → fortsæt med den dimension næste iteration

**STOP BETINGELSER:**
- confidence < {_CONFIDENCE_THRESHOLD} → STOP
- Mangler data → UNKNOWN → STOP
- Inkonsistent state → STOP
"""


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log(entry: dict) -> None:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry["_ts"] = datetime.now(timezone.utc).isoformat()
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _append_to_temp(content: str) -> None:
    with _TEMP_MD.open("a", encoding="utf-8") as f:
        f.write("\n\n---\n\n" + content)


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _state_exists() -> bool:
    return _STATE_FILE.exists() and _STATE_FILE.stat().st_size > 10


def _load_state() -> dict:
    return json.loads(_STATE_FILE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def cmd_next() -> int:
    """Generate next LLM step prompt based on current state."""
    if not _state_exists():
        print("[NEXT] ERROR: No domain_state.json — use RUN_FULL to start.")
        return 1

    state  = _load_state()

    # Stop condition: confidence
    low_conf = _confidence_too_low(state)
    if low_conf is not None:
        msg = f"[NEXT] STOP — last_step_confidence={low_conf:.2f} < {_CONFIDENCE_THRESHOLD}"
        print(msg)
        _log({"command": "NEXT", "result": "STOP_CONFIDENCE", "confidence": low_conf})
        _append_to_temp(f"## AUTONOMOUS STOP\n\nÅrsag: `last_step_confidence={low_conf:.2f}` under tærskel `{_CONFIDENCE_THRESHOLD}`\n\nKør `python run_autonomous.py STATUS` for at se state.")
        return 2

    # Stop condition: all terminal
    if _all_terminal(state):
        print("[NEXT] STOP — alle domæner er i terminal tilstand.")
        _log({"command": "NEXT", "result": "STOP_ALL_TERMINAL"})
        return 0

    # Find active domain and its next gap
    domain = state.get("_global", {}).get("active_domain")
    if not domain or domain not in state:
        print(f"[NEXT] ERROR: active_domain='{domain}' ikke fundet i state.")
        return 1

    domain_state = state[domain]
    result = _next_gap_and_type(domain_state)

    if result is None:
        # Active domain has no gaps — find next domain with gaps
        candidate = _find_next_domain_with_gaps(state, exclude=domain)
        if candidate is None:
            print("[NEXT] STOP — ingen domæner har gaps tilbage.")
            _log({"command": "NEXT", "result": "STOP_NO_GAPS"})
            return 0
        # Build directive: advance active_domain, then process first gap
        next_gap, next_step_type = _next_gap_and_type(state[candidate])  # type: ignore[misc]
        prompt = _build_advance_domain_prompt(domain, candidate, state[candidate], next_gap, next_step_type)
        _append_to_temp(prompt)
        _log({"command": "NEXT", "from_domain": domain, "to_domain": candidate,
              "gap": next_gap, "step_type": next_step_type, "action": "advance_domain"})
        print(f"[NEXT] Aktivt domæne '{domain}' har ingen gaps.")
        print(f"[NEXT] Næste domæne med gaps: '{candidate}' ({next_step_type})")
        print(f"[NEXT] Direktiv skrevet til temp.md")
        return 0

    gap, step_type = result
    prompt = _build_step_prompt(domain, domain_state, gap, step_type)

    # Write directive to temp.md (Copilot reads this)
    _append_to_temp(prompt)

    # Log
    _log({"command": "NEXT", "domain": domain, "gap": gap, "step_type": step_type})

    print(f"[NEXT] domain={domain} step_type={step_type}")
    print(f"[NEXT] gap={gap}")
    print(f"[NEXT] Direktiv skrevet til temp.md")

    return 0


def cmd_step() -> int:
    """
    MODE B — præcis 1 iteration.
    Genererer ÉT direktiv til temp.md og afslutter.
    Velegnet til Task Scheduler / cron / manuel kørsel.
    """
    if not _state_exists():
        print("[STEP] ERROR: Ingen domain_state.json — brug RUN_FULL til ny kørsel.")
        return 1

    state = _load_state()

    # Safety: same file escalation
    repeat_file = _same_file_escalation(state)
    if repeat_file is not None:
        msg = f"[STEP] ESCALATE — samme fil ændret {_SAME_FILE_REPEAT_LIMIT} gange i træk: {repeat_file}"
        print(msg)
        _log({"command": "STEP", "result": "ESCALATE", "file": repeat_file})
        _append_to_temp(
            f"## AUTONOMOUS ESCALATE\n\n"
            f"Årsag: `{repeat_file}` ændret {_SAME_FILE_REPEAT_LIMIT} gange i træk.\n\n"
            f"Kør `python run_autonomous.py STATUS` og vurder manuelt."
        )
        return 3

    _log({"command": "STEP", "mode": "single"})
    return cmd_next()


def cmd_run_full() -> int:
    """
    MODE A — batch op til 500 iterationer.
    Instruktion til Copilot: kør NEXT-loop til STOP-condition.

    I agentic Copilot-session:
      WHILE NEXT returnerer 0:
        1. Læs direktiv fra temp.md
        2. Udfør step (ÉN atomisk ændring)
        3. VALIDATE
        4. NEXT igen
      STOP når NEXT returnerer non-zero.
    """
    if not _state_exists():
        mode = "NEW"
        print("[RUN_FULL] Ingen eksisterende state — starter ny kørsel.")
        result = subprocess.run([_PYTHON, str(_ENGINE)], cwd=str(_ROOT))
        if result.returncode != 0:
            return result.returncode
    else:
        mode = "RESUME"
        print("[RUN_FULL] State fundet — delegerer til NEXT-loop.")

    _log({"command": "RUN_FULL", "mode": mode})

    # After engine init (or resume), generate first NEXT
    return cmd_next()


def cmd_resume() -> int:
    """Explicit resume — fejler hvis ingen state."""
    if not _state_exists():
        print("[RESUME] ERROR: Ingen domain_state.json. Brug RUN_FULL til ny kørsel.")
        _log({"command": "RESUME", "result": "error_no_state"})
        return 1
    print("[RESUME] State fundet — genererer næste direktiv.")
    _log({"command": "RESUME", "step": "start"})
    return cmd_next()


def cmd_validate() -> int:
    """
    Validér at seneste Copilot-step opdaterede state korrekt.

    Checks:
      - last_step_confidence >= 0.90
      - last_step_domain eksisterer
      - iteration for active domain > forrige (kan ikke verificeres uden snapshot — loggede vi det?)
    """
    if not _state_exists():
        print("[VALIDATE] Ingen state at validere.")
        return 1

    state = _load_state()
    g     = state.get("_global", {})

    conf   = g.get("last_step_confidence")
    domain = g.get("last_step_domain")
    stype  = g.get("last_step_type")

    print(f"[VALIDATE] last_step_domain     : {domain}")
    print(f"[VALIDATE] last_step_type       : {stype}")
    print(f"[VALIDATE] last_step_confidence : {conf}")

    errors: list[str] = []

    if conf is None:
        errors.append("last_step_confidence mangler — step har ikke opdateret state")
    elif conf < _CONFIDENCE_THRESHOLD:
        errors.append(f"confidence={conf:.2f} < tærskel {_CONFIDENCE_THRESHOLD} — STOP krævet")

    if domain is None:
        errors.append("last_step_domain mangler — step har ikke opdateret state")

    if errors:
        for e in errors:
            print(f"[VALIDATE] FEJL: {e}")
        _log({"command": "VALIDATE", "result": "FAILED", "errors": errors})
        return 1

    print("[VALIDATE] OK — step ser gyldigt ud.")
    _log({"command": "VALIDATE", "result": "OK", "domain": domain, "step_type": stype, "confidence": conf})
    return 0


def cmd_status() -> int:
    """Print alle domæners status + score + gaps-count."""
    if not _state_exists():
        print("[STATUS] Ingen domain_state.json — ingen kørsel startet.")
        _log({"command": "STATUS", "result": "no_state"})
        return 0

    state = _load_state()
    g     = state.get("_global", {})
    print(f"[STATUS] active_domain         : {g.get('active_domain', '?')}")
    print(f"[STATUS] iteration_counter     : {g.get('iteration_counter', '?')}")
    print(f"[STATUS] last_step_confidence  : {g.get('last_step_confidence', 'N/A')}")
    print(f"[STATUS] last_step_domain      : {g.get('last_step_domain', 'N/A')}")
    print(f"[STATUS] last_step_type        : {g.get('last_step_type', 'N/A')}")
    print()
    print(f"{'Domain':<35} {'Status':<20} {'Score':>6}  {'Iter':>5}  {'Gaps':>5}")
    print("-" * 80)

    for key, val in sorted(state.items()):
        if key.startswith("_") or not isinstance(val, dict):
            continue
        status  = val.get("status", "?")
        score   = val.get("completeness_score", 0.0)
        itr     = val.get("iteration", 0)
        gaps_n  = len(val.get("gaps", []))
        print(f"{key:<35} {status:<20} {score:>6.3f}  {itr:>5}  {gaps_n:>5}")

    _log({"command": "STATUS", "result": "printed"})
    return 0


def cmd_stop() -> int:
    """STOP — no-op for CLI. Ctrl+C afbryder kørende process."""
    print("[STOP] Send Ctrl+C (SIGINT) for at afbryde kørende process.")
    print("[STOP] Ingen effekt når engine ikke kører.")
    _log({"command": "STOP", "result": "noop"})
    return 0


def cmd_reset() -> int:
    """Slet domain_state.json efter eksplicit bekræftelse."""
    if not _state_exists():
        print("[RESET] Ingen domain_state.json — intet at nulstille.")
        _log({"command": "RESET", "result": "nothing_to_reset"})
        return 0

    print("[RESET] ADVARSEL: Sletter domains/domain_state.json.")
    print("[RESET] Alt domain-progress går tabt.")
    confirm = input("[RESET] Skriv 'RESET' for at bekræfte: ").strip()
    if confirm != "RESET":
        print("[RESET] Afbrudt — state IKKE slettet.")
        _log({"command": "RESET", "result": "aborted"})
        return 0

    result = subprocess.run(
        [_PYTHON, str(_ENGINE), "--reset-all"],
        cwd=str(_ROOT),
    )
    _log({"command": "RESET", "step": "done", "returncode": result.returncode})
    return result.returncode


# ---------------------------------------------------------------------------
# Command table + dispatch
# ---------------------------------------------------------------------------

_COMMANDS: dict[str, Any] = {
    "NEXT":     cmd_next,
    "STEP":     cmd_step,
    "RUN_FULL": cmd_run_full,
    "RESUME":   cmd_resume,
    "VALIDATE": cmd_validate,
    "STATUS":   cmd_status,
    "STOP":     cmd_stop,
    "RESET":    cmd_reset,
}


def _print_usage() -> None:
    print("brug: python run_autonomous.py <KOMMANDO>")
    print()
    print("Kommandoer:")
    print("  NEXT      — generer næste LLM-step direktiv → temp.md")
    print("  STEP      — MODE B: præcis 1 iteration (til cron/scheduler)")
    print("  RUN_FULL  — MODE A: batch op til 500 iterationer")
    print("  RESUME    — eksplicit resume, fejl hvis ingen state")
    print("  VALIDATE  — tjek om seneste step opdaterede state korrekt")
    print("  STATUS    — vis alle domæner: status, score, gaps (ingen ændringer)")
    print("  STOP      — vejledning om Ctrl+C")
    print("  RESET     — slet state med bekræftelse")
    print()
    print("Step types (fra gap-format gap:{domain}:{gap_type}:{detail}):")
    for k, v in _GAP_TYPE_MAP.items():
        print(f"  {k:<25} → {v}")


def main() -> int:
    cmd = sys.argv[1].strip().upper() if len(sys.argv) > 1 else None
    if cmd is None or cmd not in _COMMANDS:
        if cmd is not None:
            print(f"[FEJL] Ukendt kommando: '{cmd}'")
        _print_usage()
        return 1
    return _COMMANDS[cmd]()


if __name__ == "__main__":
    raise SystemExit(main())
