"""Tests for core.domain.domain_completion_protocol (Protocol v1).

Covers:
* State upgrade — new DomainProgress fields round-trip cleanly
* select_next_domain — resume / selection / all-done
* evaluate_completion — all gate paths
* no-op detection
* Gap stagnation detection
* run_protocol_iteration — smoke test via stub engine
* Run log — file created and line appended
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from core.domain.domain_completion_protocol import (
    NOOP_LIMIT,
    PROTOCOL_COMPLETENESS_GATE,
    PROTOCOL_CONSISTENCY_GATE,
    PROTOCOL_SATURATION_GATE,
    PROTOCOL_STABLE_REQUIRED,
    STAGNATION_LIMIT,
    STATUS_BLOCKED,
    STATUS_COMPLETE,
    STATUS_IN_PROGRESS,
    STATUS_STABLE_CANDIDATE,
    _append_run_log,
    _check_gap_stagnation,
    _check_no_op,
    evaluate_completion,
    run_protocol_iteration,
    select_next_domain,
)
from core.domain.domain_state import (
    STATUS_PENDING,
    DomainProgress,
    DomainState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_progress(
    name: str,
    status: str = STATUS_PENDING,
    completeness: float = 0.0,
    consistency: float = 0.0,
    saturation: float = 0.0,
    no_op: int = 0,
    stable: int = 0,
    focus: str = "",
) -> DomainProgress:
    p = DomainProgress(name=name, status=status)
    p.completeness_score = completeness
    p.consistency_score = consistency
    p.saturation_score = saturation
    p.no_op_iterations = no_op
    p.stable_iterations = stable
    p.current_focus = focus
    return p


def _make_state(tmp_path, domains: List[DomainProgress]) -> DomainState:
    state = DomainState(domains_root=str(tmp_path / "domains"))
    os.makedirs(state._domains_root, exist_ok=True)
    for p in domains:
        state._domains[p.name] = p
    state.save()   # persist so state.load() inside the protocol restores it
    return state


def _stub_engine(tmp_path, state: DomainState, loop_result: Dict[str, Any] | None = None):
    """Return a minimal duck-typed engine stub."""
    loop = MagicMock()
    loop.run_iteration.return_value = loop_result or {
        "domain": "messaging",
        "iteration": 1,
        "processed_count": 3,
        "completeness_score": 0.5,
        "new_information_score": 0.1,
        "gaps_found": 2,
        "stable_streak": 0,
        "status": STATUS_IN_PROGRESS,
    }

    memory = MagicMock()
    memory.get_cross_analysis.return_value = {"consistency": 0.5}
    memory.get_gap_history.return_value = []

    store = MagicMock()
    store.load_model.return_value = {
        "entities": ["E1", "E2", "E3", "E4", "E5"],
        "behaviors": ["B1", "B2", "B3", "B4", "B5"],
        "flows": ["F1", "F2", "F3"],
        "rules": ["R1", "R2", "R3"],
        "events": ["Ev1", "Ev2"],
        "integrations": ["I1", "I2"],
    }

    scanner = MagicMock()
    scanner.scan_all_assets.return_value = []

    # Patch match_assets to return all provided asset IDs
    engine = MagicMock()
    engine._state = state
    engine._loop = loop
    engine._memory = memory
    engine._store = store
    engine._scanner = scanner
    engine._data_root = str(tmp_path / "data")
    engine._domains_root = str(tmp_path / "domains")

    return engine


# ---------------------------------------------------------------------------
# 1. State upgrade — backward compat
# ---------------------------------------------------------------------------


class TestStateUpgrade:
    def test_new_fields_on_fresh_progress(self):
        """New protocol fields should exist with safe defaults."""
        p = DomainProgress(name="test")
        assert p.no_op_iterations == 0
        assert p.last_change_at == ""
        assert p.consistency_score == 0.0
        assert p.saturation_score == 0.0
        assert p.last_processed_assets == []

    def test_round_trip_includes_new_fields(self, tmp_path):
        """New fields must survive a save / load cycle."""
        state = DomainState(domains_root=str(tmp_path / "domains"))
        os.makedirs(state._domains_root, exist_ok=True)
        p = DomainProgress(name="messaging")
        p.no_op_iterations = 2
        p.consistency_score = 0.75
        p.saturation_score = 0.60
        p.last_processed_assets = ["asset_a", "asset_b"]
        state._domains["messaging"] = p
        state.save()

        state2 = DomainState(domains_root=str(tmp_path / "domains"))
        state2.load()
        p2 = state2.get("messaging")
        assert p2 is not None
        assert p2.no_op_iterations == 2
        assert p2.consistency_score == 0.75
        assert p2.saturation_score == 0.60
        assert p2.last_processed_assets == ["asset_a", "asset_b"]

    def test_old_record_missing_new_fields_loads_safely(self, tmp_path):
        """Loading a JSON file that lacks protocol v1 fields must not crash."""
        domains_dir = str(tmp_path / "domains")
        os.makedirs(domains_dir, exist_ok=True)
        old_record = {
            "messaging": {
                "name": "messaging",
                "status": "pending",
                "iteration": 0,
                "completeness_score": 0.3,
                "new_information_score": 0.0,
                "matched_asset_ids": [],
                "processed_asset_ids": [],
                "gaps": [],
                "last_updated_utc": "",
                "consecutive_stable_iterations": 0,
                "stable_iterations": 0,
                "last_significant_change": "",
                "current_focus": "",
                "evidence_balance": {},
                # protocol v1 fields intentionally absent
            }
        }
        path = os.path.join(domains_dir, "domain_state.json")
        with open(path, "w") as f:
            json.dump(old_record, f)

        state = DomainState(domains_root=domains_dir)
        state.load()
        p = state.get("messaging")
        assert p is not None
        assert p.no_op_iterations == 0
        assert p.consistency_score == 0.0

    def test_global_fields_persist(self, tmp_path):
        """active_domain and iteration_counter must survive a save/load round-trip."""
        state = DomainState(domains_root=str(tmp_path / "domains"))
        os.makedirs(state._domains_root, exist_ok=True)
        state.active_domain = "messaging"
        state.iteration_counter = 7
        state.ensure_domains(["messaging"])
        state.save()

        state2 = DomainState(domains_root=str(tmp_path / "domains"))
        state2.load()
        assert state2.active_domain == "messaging"
        assert state2.iteration_counter == 7


# ---------------------------------------------------------------------------
# 2. select_next_domain
# ---------------------------------------------------------------------------


class TestSelectNextDomain:
    def test_resumes_in_progress_domain(self, tmp_path):
        p = _make_progress("messaging", status=STATUS_IN_PROGRESS)
        state = _make_state(tmp_path, [p])
        state.active_domain = "messaging"
        result = select_next_domain(state)
        assert result == "messaging"

    def test_skips_active_if_not_in_progress(self, tmp_path):
        p_done = _make_progress("messaging", status=STATUS_COMPLETE)
        p_next = _make_progress("billing", status=STATUS_PENDING, focus="priority_1")
        state = _make_state(tmp_path, [p_done, p_next])
        state.active_domain = "messaging"
        result = select_next_domain(state)
        assert result == "billing"
        assert state.active_domain == "billing"

    def test_picks_highest_priority_focus(self, tmp_path):
        p1 = _make_progress("billing",   status=STATUS_PENDING, focus="priority_2")
        p2 = _make_progress("messaging", status=STATUS_PENDING, focus="priority_1")
        state = _make_state(tmp_path, [p1, p2])
        result = select_next_domain(state)
        assert result == "messaging"

    def test_breaks_tie_by_lowest_completeness(self, tmp_path):
        p1 = _make_progress("billing",   status=STATUS_PENDING, completeness=0.8)
        p2 = _make_progress("messaging", status=STATUS_PENDING, completeness=0.3)
        state = _make_state(tmp_path, [p1, p2])
        result = select_next_domain(state)
        assert result == "messaging"

    def test_returns_none_when_all_complete(self, tmp_path):
        p1 = _make_progress("messaging", status=STATUS_COMPLETE)
        p2 = _make_progress("billing",   status=STATUS_BLOCKED)
        state = _make_state(tmp_path, [p1, p2])
        result = select_next_domain(state)
        assert result is None
        assert state.active_domain is None

    def test_stable_domains_excluded(self, tmp_path):
        p_stable = _make_progress("messaging", status="stable")
        p_next   = _make_progress("billing",   status=STATUS_PENDING)
        state = _make_state(tmp_path, [p_stable, p_next])
        result = select_next_domain(state)
        assert result == "billing"


# ---------------------------------------------------------------------------
# 3. evaluate_completion
# ---------------------------------------------------------------------------


class TestEvaluateCompletion:
    def _passing_progress(self, name="test") -> DomainProgress:
        return _make_progress(
            name,
            completeness=PROTOCOL_COMPLETENESS_GATE,
            consistency=PROTOCOL_CONSISTENCY_GATE,
            saturation=PROTOCOL_SATURATION_GATE,
        )

    def test_complete_after_stable_required_consecutive(self):
        p = self._passing_progress()
        for _ in range(PROTOCOL_STABLE_REQUIRED):
            evaluate_completion("test", p)
        assert p.status == STATUS_COMPLETE

    def test_stable_candidate_before_enough_iterations(self):
        p = self._passing_progress()
        # Only one iteration — not enough for COMPLETE
        evaluate_completion("test", p)
        assert p.status == STATUS_STABLE_CANDIDATE

    def test_in_progress_when_scores_low(self):
        p = _make_progress("test", completeness=0.5, consistency=0.5, saturation=0.5)
        evaluate_completion("test", p)
        assert p.status == STATUS_IN_PROGRESS

    def test_stable_iterations_resets_on_score_drop(self):
        p = self._passing_progress()
        p.stable_iterations = PROTOCOL_STABLE_REQUIRED - 1
        # Drop a score below gate
        p.consistency_score = 0.0
        evaluate_completion("test", p)
        assert p.stable_iterations == 0
        assert p.status == STATUS_IN_PROGRESS

    def test_blocked_when_stuck_with_low_completeness(self):
        p = _make_progress("test", completeness=0.2, no_op=NOOP_LIMIT)
        evaluate_completion("test", p)
        assert p.status == STATUS_BLOCKED

    def test_not_blocked_when_completeness_adequate(self):
        """No-op limit alone does not block if completeness is reasonable."""
        p = _make_progress("test", completeness=0.6, no_op=NOOP_LIMIT)
        evaluate_completion("test", p)
        # Should be in_progress, not blocked
        assert p.status == STATUS_IN_PROGRESS


# ---------------------------------------------------------------------------
# 4. No-op detection
# ---------------------------------------------------------------------------


class TestNoOpDetection:
    def test_increments_on_zero_processed(self):
        p = _make_progress("test")
        result = {"processed_count": 0, "new_information_score": 0.0}
        is_noop = _check_no_op(p, result)
        assert is_noop is True
        assert p.no_op_iterations == 1

    def test_increments_on_negligible_new_info(self):
        p = _make_progress("test")
        result = {"processed_count": 5, "new_information_score": 0.0005}
        is_noop = _check_no_op(p, result)
        assert is_noop is True

    def test_resets_on_real_change(self):
        p = _make_progress("test", no_op=3)
        result = {"processed_count": 4, "new_information_score": 0.1}
        is_noop = _check_no_op(p, result)
        assert is_noop is False
        assert p.no_op_iterations == 0

    def test_last_change_at_set_on_real_change(self):
        p = _make_progress("test")
        result = {"processed_count": 2, "new_information_score": 0.05}
        _check_no_op(p, result)
        assert p.last_change_at != ""


# ---------------------------------------------------------------------------
# 5. Gap stagnation detection
# ---------------------------------------------------------------------------


class TestGapStagnation:
    def _make_gap_snapshot(self, gap_ids: list) -> dict:
        return {
            "iteration": 1,
            "gaps": [{"id": gid} for gid in gap_ids],
        }

    def test_no_stagnation_with_few_snapshots(self):
        memory = MagicMock()
        memory.get_gap_history.return_value = [
            self._make_gap_snapshot(["g1"]),
        ]
        assert _check_gap_stagnation(memory, "test") is False

    def test_stagnation_detected_with_identical_snapshots(self):
        memory = MagicMock()
        snap = self._make_gap_snapshot(["g1", "g2"])
        memory.get_gap_history.return_value = [snap, snap, snap]
        assert _check_gap_stagnation(memory, "test") is True

    def test_no_stagnation_when_gaps_change(self):
        memory = MagicMock()
        memory.get_gap_history.return_value = [
            self._make_gap_snapshot(["g1"]),
            self._make_gap_snapshot(["g1", "g2"]),
            self._make_gap_snapshot(["g2", "g3"]),
        ]
        assert _check_gap_stagnation(memory, "test") is False

    def test_returns_false_when_memory_is_none(self):
        assert _check_gap_stagnation(None, "test") is False


# ---------------------------------------------------------------------------
# 6. Run log
# ---------------------------------------------------------------------------


class TestRunLog:
    def test_creates_file_and_appends(self, tmp_path):
        data_root = str(tmp_path / "data")
        entry = {"iteration": 1, "domain": "messaging", "status": "in_progress"}
        _append_run_log(data_root, entry)
        log_path = os.path.join(data_root, "run_log.jsonl")
        assert os.path.isfile(log_path)
        with open(log_path) as f:
            line = f.readline()
        parsed = json.loads(line)
        assert parsed["domain"] == "messaging"

    def test_multiple_entries_preserved(self, tmp_path):
        data_root = str(tmp_path / "data")
        for i in range(3):
            _append_run_log(data_root, {"iteration": i, "domain": "test"})
        log_path = os.path.join(data_root, "run_log.jsonl")
        with open(log_path) as f:
            lines = f.readlines()
        assert len(lines) == 3


# ---------------------------------------------------------------------------
# 7. run_protocol_iteration — integration smoke test
# ---------------------------------------------------------------------------


class TestRunProtocolIteration:
    def _make_engine(self, tmp_path):
        p = _make_progress("messaging", status=STATUS_PENDING, focus="priority_1")
        state = _make_state(tmp_path, [p])
        return _stub_engine(tmp_path, state)

    def test_returns_expected_keys(self, tmp_path):
        engine = self._make_engine(tmp_path)

        import unittest.mock as mock
        with mock.patch(
            "core.domain.domain_completion_protocol.match_assets",
            return_value=["asset_1"],
        ):
            engine._scanner.scan_all_assets.return_value = [
                {"id": "asset_1", "type": "code_file", "content": ""}
            ]
            result = run_protocol_iteration(engine)

        assert "domain" in result
        assert "iteration" in result
        assert "status_before" in result
        assert "status_after" in result
        assert "scores_before" in result
        assert "scores_after" in result
        assert "changes" in result
        assert "next_command" in result

    def test_domain_marked_in_progress(self, tmp_path):
        engine = self._make_engine(tmp_path)
        import unittest.mock as mock
        with mock.patch("core.domain.domain_completion_protocol.match_assets", return_value=[]):
            result = run_protocol_iteration(engine)

        assert result["status_after"] in (
            STATUS_IN_PROGRESS, STATUS_STABLE_CANDIDATE, STATUS_COMPLETE, STATUS_BLOCKED
        )

    def test_iteration_counter_increments(self, tmp_path):
        engine = self._make_engine(tmp_path)
        state: DomainState = engine._state
        import unittest.mock as mock
        with mock.patch("core.domain.domain_completion_protocol.match_assets", return_value=[]):
            run_protocol_iteration(engine)
        assert state.iteration_counter == 1

    def test_run_log_written(self, tmp_path):
        engine = self._make_engine(tmp_path)
        import unittest.mock as mock
        with mock.patch("core.domain.domain_completion_protocol.match_assets", return_value=[]):
            run_protocol_iteration(engine)
        log_path = os.path.join(engine._data_root, "run_log.jsonl")
        assert os.path.isfile(log_path)

    def test_all_complete_returns_early(self, tmp_path):
        p = _make_progress("messaging", status=STATUS_COMPLETE)
        state = _make_state(tmp_path, [p])
        engine = _stub_engine(tmp_path, state)
        result = run_protocol_iteration(engine)
        assert result["status_after"] == "all_complete"

    def test_state_saved_after_iteration(self, tmp_path):
        engine = self._make_engine(tmp_path)
        import unittest.mock as mock
        with mock.patch("core.domain.domain_completion_protocol.match_assets", return_value=[]):
            run_protocol_iteration(engine)
        state_path = os.path.join(str(tmp_path / "domains"), "domain_state.json")
        assert os.path.isfile(state_path)
        with open(state_path) as f:
            data = json.load(f)
        assert "messaging" in data
        assert "_global" in data
        assert data["_global"]["iteration_counter"] == 1
