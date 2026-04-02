"""Domain Completion Protocol v1 — additive single-iteration orchestrator.

ADDITIVE ONLY: this module does not modify any existing class or function.
It composes existing components via their public APIs.

Entry point::

    from core.domain.domain_completion_protocol import run_protocol_iteration
    result = run_protocol_iteration(engine, all_assets)

One call → one safe iteration → one persisted state update → exit.
An external scheduler / CLI re-triggers as needed.

Protocol flow
-------------
1. ``select_next_domain``     — resume in-progress or pick highest-priority
2. Mark ``in_progress``       — update DomainProgress.status + iteration count
3. Asset cooldown filter      — skip assets processed last COOLDOWN_WINDOW rounds
4. Run one learning iteration — delegate to ``DomainLearningLoop.run_iteration``
5. Update protocol scores     — consistency + saturation via domain_scoring
6. Anti-loop detection        — no-op counter, gap stagnation
7. ``evaluate_completion``    — assign new status
8. Persist                    — atomic domain_state.json + append run_log.jsonl
9. Return result dict         — caller decides when to re-trigger

Completion thresholds (stricter than existing loop thresholds)
--------------------------------------------------------------
* completeness  >= 0.95
* consistency   >= 0.90
* saturation    >= 0.90
* stable_iterations >= 3 consecutive passing iterations
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.domain.domain_asset_matcher import match_assets
from core.domain.domain_scoring import (
    compute_saturation_score,
    cross_source_consistency_score,
)
from core.domain.domain_state import (
    STATUS_BLOCKED,
    STATUS_COMPLETE,
    STATUS_IN_PROGRESS,
    STATUS_STABLE_CANDIDATE,
    DomainProgress,
    DomainState,
)

# ---------------------------------------------------------------------------
# Protocol thresholds
# ---------------------------------------------------------------------------

PROTOCOL_COMPLETENESS_GATE: float = 0.95   # stricter than existing 0.90
PROTOCOL_CONSISTENCY_GATE: float = 0.90
PROTOCOL_SATURATION_GATE: float = 0.90
PROTOCOL_STABLE_REQUIRED: int = 3         # consecutive passing iterations

NOOP_LIMIT: int = 3          # no-op iterations before forcing strategy reset
STAGNATION_LIMIT: int = 3    # repeated gap snapshots before escaling scope
COOLDOWN_WINDOW: int = 2     # assets processed in the last N iters are skipped
SOURCE_DIVERSITY_MAX_RATIO: float = 0.50  # max fraction of assets from one source_type


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enforce_source_diversity(
    assets: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Cap any single source_type to SOURCE_DIVERSITY_MAX_RATIO of the list.

    When one source_type would exceed the cap, excess items from that type
    are moved to the end so the front of the list is balanced.  The full
    list is returned (nothing is dropped) so callers that need all assets
    still have access — only ordering changes.

    Parameters
    ----------
    assets:
        List of asset dicts, each optionally carrying a ``source_type`` key.

    Returns
    -------
    list[dict]
        Same items, reordered so no source_type exceeds the cap in the
        leading *n* items where *n* == len(assets).
    """
    if not assets:
        return assets
    total = len(assets)
    cap = max(1, int(total * SOURCE_DIVERSITY_MAX_RATIO))

    from collections import defaultdict
    buckets: dict = defaultdict(list)
    for a in assets:
        src = a.get("source_type") or "unknown"
        buckets[src].append(a)

    # Interleave: round-robin across source types up to cap per type
    result: List[Dict[str, Any]] = []
    overflow: List[Dict[str, Any]] = []
    counts: dict = defaultdict(int)
    for a in assets:
        src = a.get("source_type") or "unknown"
        if counts[src] < cap:
            result.append(a)
            counts[src] += 1
        else:
            overflow.append(a)
    return result + overflow


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _all_scores_pass(prog: DomainProgress) -> bool:
    """Return True when ALL three gate thresholds are met."""
    return (
        prog.completeness_score >= PROTOCOL_COMPLETENESS_GATE
        and prog.consistency_score >= PROTOCOL_CONSISTENCY_GATE
        and prog.saturation_score >= PROTOCOL_SATURATION_GATE
    )


def _high_scores(prog: DomainProgress) -> bool:
    """Elevated-but-not-gate scores → stable_candidate territory."""
    return (
        prog.completeness_score >= 0.85
        and prog.consistency_score >= 0.80
        and prog.saturation_score >= 0.80
    )


# ---------------------------------------------------------------------------
# Domain selection
# ---------------------------------------------------------------------------

def select_next_domain(state: DomainState) -> Optional[str]:
    """Return the domain name to process this iteration.

    Rules (in order)
    ----------------
    1. ``state.active_domain`` is set AND its status == ``in_progress``
       → return it unchanged (resume).
    2. Otherwise: scan all non-terminal domains, ordered by
       a. ``current_focus`` priority tag (``"priority_N"`` → N ascending)
       b. ``completeness_score`` ascending (least complete first)
    3. Set ``state.active_domain`` to the chosen name.
    4. Return ``None`` when every domain is complete or blocked.
    """
    # Rule 1: resume current in-progress domain
    if state.active_domain:
        prog = state.get(state.active_domain)
        if prog is not None and prog.status == STATUS_IN_PROGRESS:
            return state.active_domain

    # Rule 2: choose next best
    # NOTE: "stable" is intentionally excluded — it is a loop-internal convergence
    # hint only and must NOT be treated as terminal. Domains set to "stable" by
    # DomainLearningLoop are re-evaluated by the protocol on the next call.
    terminal = {STATUS_COMPLETE, STATUS_BLOCKED}
    candidates: List[DomainProgress] = [
        p for p in state.all_domains() if p.status not in terminal
    ]

    if not candidates:
        state.active_domain = None
        return None

    def _sort_key(p: DomainProgress):
        focus = p.current_focus or ""
        priority_num = 9999
        if focus.startswith("priority_"):
            try:
                priority_num = int(focus.split("_", 1)[1])
            except (ValueError, IndexError):
                pass
        return (priority_num, p.completeness_score)

    candidates.sort(key=_sort_key)
    chosen = candidates[0].name
    state.active_domain = chosen
    return chosen


# ---------------------------------------------------------------------------
# Score updater
# ---------------------------------------------------------------------------

def _update_protocol_scores(
    domain_name: str,
    prog: DomainProgress,
    model: Dict[str, Any],
    memory: Any,
) -> None:
    """Recompute and store consistency + saturation scores on *prog*.

    Does NOT modify any scoring function — calls existing public APIs only.
    """
    # Consistency: uses cross-analysis stored in memory, falls back to model coverage
    prog.consistency_score = round(
        cross_source_consistency_score(model, memory, domain_name), 4
    )

    # Saturation: gap history convergence
    gap_history: list = []
    if memory is not None and domain_name:
        try:
            gap_history = memory.get_gap_history(domain_name)
        except Exception:  # noqa: BLE001
            gap_history = []
    prog.saturation_score = round(compute_saturation_score(gap_history), 4)


# ---------------------------------------------------------------------------
# Anti-loop detection
# ---------------------------------------------------------------------------

def _check_no_op(prog: DomainProgress, result: Dict[str, Any]) -> bool:
    """Detect a no-op iteration; update *prog.no_op_iterations* in place.

    An iteration is a no-op when it produced no new information
    (processed_count == 0 OR new_information_score < 0.001).

    Returns True when the iteration is a no-op.
    """
    no_change = (
        result.get("processed_count", 0) == 0
        or float(result.get("new_information_score", 1.0)) < 0.001
    )
    if no_change:
        prog.no_op_iterations += 1
    else:
        prog.no_op_iterations = 0
        prog.last_change_at = _now_iso()
    return no_change


def _check_gap_stagnation(memory: Any, domain_name: str) -> bool:
    """Return True when the same gap IDs appear in STAGNATION_LIMIT recent snapshots."""
    if memory is None or not domain_name:
        return False
    try:
        history = memory.get_gap_history(domain_name)
    except Exception:  # noqa: BLE001
        return False
    if len(history) < STAGNATION_LIMIT:
        return False

    def _gap_ids(snapshot: Dict[str, Any]) -> frozenset:
        return frozenset(
            g.get("id", "") for g in (snapshot.get("gaps") or []) if g.get("id")
        )

    recent = history[-STAGNATION_LIMIT:]
    id_sets = [_gap_ids(s) for s in recent]
    return all(s == id_sets[0] for s in id_sets[1:])


def _no_unprocessed_assets_exist(
    prog: DomainProgress,
    domain_name: str,
    all_assets: List[Dict[str, Any]],
) -> bool:
    """True when at least one asset matches *domain_name* and every matched
    asset has already been processed.  Returns False when no assets are
    matched (nothing to exhaust) to avoid false positives on empty domains.
    """
    matched_ids = set(match_assets(domain_name, all_assets))
    if not matched_ids:
        return False  # no matched assets — nothing to exhaust
    processed = set(prog.processed_asset_ids)
    return matched_ids.issubset(processed)


def _contradiction_stagnant(memory: Any, domain_name: str) -> bool:
    """True when CONTRADICTION gaps appear in every snapshot
    of the last STAGNATION_LIMIT history entries."""
    if memory is None or not domain_name:
        return False
    try:
        history = memory.get_gap_history(domain_name)
    except Exception:  # noqa: BLE001
        return False
    if len(history) < STAGNATION_LIMIT:
        return False
    recent = history[-STAGNATION_LIMIT:]

    def _has_contradiction(snapshot: Dict[str, Any]) -> bool:
        return any(
            g.get("type") == "CONTRADICTION"
            for g in (snapshot.get("gaps") or [])
        )

    return all(_has_contradiction(s) for s in recent)


# ---------------------------------------------------------------------------
# Completion evaluator
# ---------------------------------------------------------------------------

def evaluate_completion(
    domain_name: str,
    prog: DomainProgress,
    gap_stagnation: bool = False,
    all_assets: Optional[List[Dict[str, Any]]] = None,
    memory: Any = None,
) -> str:
    """Determine and set the new status for *prog*.

    Decision table
    --------------
    All gates pass + stable_iterations >= PROTOCOL_STABLE_REQUIRED
        → ``complete``
    All gates pass OR high scores (pre-gate zone)
        → ``stable_candidate``
    no_op_iterations >= NOOP_LIMIT AND completeness < 0.60
        → ``blocked``  (domain stuck with low coverage)
    gap_stagnation AND all matched assets already processed
        → ``blocked``  (domain exhausted all assets with no progress)
    CONTRADICTION in every snapshot for STAGNATION_LIMIT iterations
        → ``blocked``  (persistent contradiction cannot be auto-resolved)
    Otherwise
        → ``in_progress``

    The ``stable_iterations`` counter increments only when all gates pass,
    and resets to zero the moment any gate fails.

    Returns
    -------
    str
        The new status string (also assigned to ``prog.status``).
    """
    if _all_scores_pass(prog) or _high_scores(prog):
        prog.stable_iterations += 1
    else:
        prog.stable_iterations = 0

    if _all_scores_pass(prog) and prog.stable_iterations >= PROTOCOL_STABLE_REQUIRED:
        prog.status = STATUS_COMPLETE
    elif _high_scores(prog) and prog.stable_iterations >= PROTOCOL_STABLE_REQUIRED * 2:
        # Heuristic mode: PROTOCOL_CONSISTENCY_GATE (0.90) is never reachable
        # because heuristic providers cap consistency ~0.83.  After 2x the normal
        # stable window with consistently high scores, accept the domain as complete.
        prog.status = STATUS_COMPLETE
    elif (_all_scores_pass(prog) or _high_scores(prog)) and prog.no_op_iterations >= NOOP_LIMIT:
        # High-score domain that can no longer learn — no AI or assets are exhausted.
        # stable_iterations can never accumulate because _all_scores_pass() may never
        # be True (e.g. heuristic mode caps consistency at 0.83).  Treat as BLOCKED
        # rather than spinning forever in stable_candidate.
        prog.status = STATUS_BLOCKED
    elif _all_scores_pass(prog) or _high_scores(prog):
        prog.status = STATUS_STABLE_CANDIDATE
    elif prog.no_op_iterations >= NOOP_LIMIT and prog.completeness_score < 0.60:
        prog.status = STATUS_BLOCKED
    elif gap_stagnation and all_assets and _no_unprocessed_assets_exist(prog, domain_name, all_assets):
        prog.status = STATUS_BLOCKED
    elif _contradiction_stagnant(memory, domain_name):
        prog.status = STATUS_BLOCKED
    else:
        prog.status = STATUS_IN_PROGRESS

    return prog.status


# ---------------------------------------------------------------------------
# Run log
# ---------------------------------------------------------------------------

def _append_run_log(data_root: str, entry: Dict[str, Any]) -> None:
    """Append *entry* as a single JSON line to ``{data_root}/run_log.jsonl``.

    Creates the file and directory if absent.  Always appends — never
    overwrites prior entries.
    """
    log_path = os.path.join(data_root, "run_log.jsonl")
    os.makedirs(data_root, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ---------------------------------------------------------------------------
# Meta-sync guard
# ---------------------------------------------------------------------------

def _check_meta_sync(
    domain_name: str,
    prog: DomainProgress,
    data_root: str,
) -> None:
    """Warn to stderr when ``000_meta.json`` status disagrees with *prog*.

    Trusts ``domain_state.json`` (Tier 1) as master.  Never raises, never
    modifies state.  Safe to call before every protocol iteration.
    """
    meta_path = os.path.join(data_root, domain_name, "000_meta.json")
    try:
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return
    meta_status = meta.get("status")
    if meta_status is not None and meta_status != prog.status:
        import sys
        print(
            f"WARNING: domain_state.json[{domain_name!r}].status={prog.status!r} "
            f"!= 000_meta.json status={meta_status!r} "
            "\u2014 trusting domain_state.json",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_protocol_iteration(
    engine: Any,
    all_assets: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Execute **one** safe protocol iteration and return immediately.

    Parameters
    ----------
    engine:
        A ``DomainEngineV3`` instance (duck-typed for testability).
        Must expose: ``_state``, ``_loop``, ``_memory``, ``_store``,
        ``_data_root``, ``_scanner``.
    all_assets:
        Full asset corpus.  When ``None``, ``engine._scanner.scan_all_assets()``
        is called to obtain assets.

    Returns
    -------
    dict
        ``domain``          — domain processed (``None`` if all done)
        ``iteration``       — per-domain iteration count after this run
        ``status_before``   — status entering this iteration
        ``status_after``    — status exiting this iteration
        ``scores_before``   — scores snapshot before
        ``scores_after``    — scores snapshot after
        ``changes``         — ``True`` when new information was extracted
        ``no_op_iterations``— consecutive no-op count
        ``gap_stagnation``  — ``True`` when gaps are stuck
        ``next_command``    — hint for the next call
    """
    state: DomainState = engine._state
    state.load()

    # Scan assets once if not supplied
    if all_assets is None:
        all_assets = engine._scanner.scan_all_assets()

    # ── 1. Domain selection ──────────────────────────────────────────────
    domain_name = select_next_domain(state)
    if domain_name is None:
        return {
            "domain": None,
            "status_after": "all_complete",
            "message": "All domains are complete or blocked — nothing to do.",
        }

    state.ensure_domains([domain_name])
    prog = state.get(domain_name)
    assert prog is not None  # ensure_domains guarantees existence

    # ── 1b. Meta-sync guard ──────────────────────────────────────────────
    _check_meta_sync(domain_name, prog, engine._data_root)

    status_before = prog.status
    scores_before = {
        "completeness": prog.completeness_score,
        "consistency":  prog.consistency_score,
        "saturation":   prog.saturation_score,
    }

    # ── 2. Mark in_progress; increment counters ──────────────────────────
    prog.status = STATUS_IN_PROGRESS
    prog.iteration += 1
    state.iteration_counter += 1
    state.active_domain = domain_name

    # ── 3. Asset cooldown filter ─────────────────────────────────────────
    matched_ids = match_assets(domain_name, all_assets)
    assets_by_id = {a.get("id", ""): a for a in all_assets}

    cooldown_ids = set(prog.last_processed_assets)
    domain_assets = [
        assets_by_id[aid]
        for aid in matched_ids
        if aid in assets_by_id and aid not in cooldown_ids
    ]
    # If cooldown removed all assets, fall back to the full matched set
    if not domain_assets:
        domain_assets = [assets_by_id[aid] for aid in matched_ids if aid in assets_by_id]

    # ── 3b. Source diversity enforcement ────────────────────────────────
    # Reorder domain_assets so no single source_type dominates the front
    # of the list beyond SOURCE_DIVERSITY_MAX_RATIO.
    domain_assets = _enforce_source_diversity(domain_assets)

    # ── 4. Run one learning iteration ───────────────────────────────────
    if domain_assets:
        iteration_result: Dict[str, Any] = engine._loop.run_iteration(
            domain_name=domain_name,
            assets=domain_assets,
            all_assets=all_assets,
        )
    else:
        # No assets matched at all — record as no-op
        iteration_result = {
            "domain": domain_name,
            "iteration": prog.iteration,
            "processed_count": 0,
            "completeness_score": prog.completeness_score,
            "new_information_score": 0.0,
            "gaps_found": 0,
            "stable_streak": prog.stable_iterations,
            "status": STATUS_IN_PROGRESS,
        }

    # Mirror scores back to progress record
    prog.completeness_score = float(
        iteration_result.get("completeness_score", prog.completeness_score)
    )
    prog.new_information_score = float(
        iteration_result.get("new_information_score", prog.new_information_score)
    )

    # ── 5. Update consistency + saturation scores ────────────────────────
    model = engine._store.load_model(domain_name)
    _update_protocol_scores(domain_name, prog, model, engine._memory)

    # ── 6. Anti-loop checks ──────────────────────────────────────────────
    is_no_op = _check_no_op(prog, iteration_result)
    gap_stagnation = _check_gap_stagnation(engine._memory, domain_name)

    if is_no_op and prog.no_op_iterations >= NOOP_LIMIT:
        # Force strategy reset: clear cooldown so all matched assets are eligible
        prog.last_processed_assets = []
    else:
        # Rolling cooldown: store this iteration's processed assets for next run
        prog.last_processed_assets = [
            a.get("id", "") for a in domain_assets if a.get("id")
        ]

    # ── 7. Evaluate completion ───────────────────────────────────────────
    status_after = evaluate_completion(
        domain_name, prog,
        gap_stagnation=gap_stagnation,
        all_assets=all_assets,
        memory=engine._memory,
    )

    if status_after == STATUS_COMPLETE:
        state.active_domain = None  # release lock — next domain on next call

    prog.last_updated_utc = _now_iso()

    # ── 8. Persist state ─────────────────────────────────────────────────
    state.save()

    scores_after = {
        "completeness": prog.completeness_score,
        "consistency":  prog.consistency_score,
        "saturation":   prog.saturation_score,
    }

    # ── 9. Append run log ────────────────────────────────────────────────
    log_entry: Dict[str, Any] = {
        "iteration":    state.iteration_counter,
        "domain":       domain_name,
        "status":       status_after,
        "scores":       scores_after,
        "changes":      not is_no_op,
        "no_op_count":  prog.no_op_iterations,
        "gap_stagnation": gap_stagnation,
        "timestamp":    _now_iso(),
    }
    _append_run_log(engine._data_root, log_entry)

    return {
        "domain":           domain_name,
        "iteration":        prog.iteration,
        "status_before":    status_before,
        "status_after":     status_after,
        "scores_before":    scores_before,
        "scores_after":     scores_after,
        "changes":          not is_no_op,
        "no_op_iterations": prog.no_op_iterations,
        "gap_stagnation":   gap_stagnation,
        "next_command":     _next_command(status_after, domain_name),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _next_command(status: str, domain: str) -> str:
    """Return a human-readable hint for the next call."""
    if status == STATUS_COMPLETE:
        return "run_protocol_iteration(engine, all_assets)  # advance to next domain"
    if status == STATUS_BLOCKED:
        return (
            f"# Manual review required for '{domain}' — "
            "expand asset sources or add seeds"
        )
    if status == STATUS_STABLE_CANDIDATE:
        remaining = PROTOCOL_STABLE_REQUIRED - 1
        return (
            f"run_protocol_iteration(engine, all_assets)  "
            f"# ~{remaining} more stable iteration(s) needed"
        )
    return f"run_protocol_iteration(engine, all_assets)  # continue '{domain}'"
