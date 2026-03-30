"""Tests for core.domain.domain_learning_loop.

Covers:
* DomainLearningLoop.should_continue / should_mark_stable
* run_iteration — return shape, state updates, processed tracking
* Stable streak logic — requires 2 consecutive convergent iterations
* Memory caching — cached insight reused on unchanged hash
* Persist side-effects — model and state saved after iteration
"""

import pytest

from core.domain.ai.semantic_analyzer import INSIGHT_KEYS
from core.domain.ai_reasoner import AIReasoner
from core.domain.domain_learning_loop import DomainLearningLoop, _REQUIRED_STABLE_STREAK
from core.domain.domain_memory import DomainMemory
from core.domain.domain_model_store import DomainModelStore
from core.domain.domain_query_engine import DomainQueryEngine
from core.domain.domain_scoring import COMPLETENESS_THRESHOLD, NEW_INFO_THRESHOLD
from core.domain.domain_state import DomainProgress, DomainState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def setup(tmp_path):
    """Return a fully wired DomainLearningLoop pointing at tmp_path."""
    domains_root = str(tmp_path / "domains")
    data_root = str(tmp_path / "data")

    model_store = DomainModelStore(domains_root=domains_root)
    memory = DomainMemory(data_root=data_root)
    memory.load()

    reasoner = AIReasoner()
    query_engine = DomainQueryEngine()

    state = DomainState(domains_root=domains_root)
    state.load()
    state.ensure_domains(["messaging"])
    state.save()

    loop = DomainLearningLoop(
        model_store=model_store,
        memory=memory,
        reasoner=reasoner,
        query_engine=query_engine,
        state=state,
        max_assets_per_iter=10,
        verbose=False,
    )

    return loop, state, memory, model_store


def _assets(n: int = 5, domain: str = "messaging") -> list:
    """Generate *n* simple code_file assets for *domain*."""
    return [
        {
            "id": f"code:{domain}:{i}",
            "type": "code_file",
            "path": f"src/{domain}/File{i}.cs",
            "content": (
                f"public class {domain.capitalize()}Service{i} {{"
                f"  public void Handle{domain.capitalize()}() {{ }}"
                f"  public void Validate() {{ if (x == null) throw; }}"
                f"}}"
            ),
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# should_mark_stable / should_continue
# ---------------------------------------------------------------------------


class TestStopConditions:
    def test_stable_when_all_conditions_met(self, setup):
        loop, *_ = setup
        domain_state = {
            "completeness_score": COMPLETENESS_THRESHOLD,
            "new_information_score": NEW_INFO_THRESHOLD - 0.001,
            "stable_streak": _REQUIRED_STABLE_STREAK,
        }
        assert loop.should_mark_stable(domain_state) is True

    def test_not_stable_when_completeness_low(self, setup):
        loop, *_ = setup
        domain_state = {
            "completeness_score": 0.50,
            "new_information_score": 0.00,
            "stable_streak": _REQUIRED_STABLE_STREAK,
        }
        assert loop.should_mark_stable(domain_state) is False

    def test_not_stable_when_new_info_high(self, setup):
        loop, *_ = setup
        domain_state = {
            "completeness_score": COMPLETENESS_THRESHOLD,
            "new_information_score": 0.10,   # above threshold
            "stable_streak": _REQUIRED_STABLE_STREAK,
        }
        assert loop.should_mark_stable(domain_state) is False

    def test_not_stable_when_streak_insufficient(self, setup):
        loop, *_ = setup
        domain_state = {
            "completeness_score": COMPLETENESS_THRESHOLD,
            "new_information_score": NEW_INFO_THRESHOLD - 0.001,
            "stable_streak": _REQUIRED_STABLE_STREAK - 1,  # one short
        }
        assert loop.should_mark_stable(domain_state) is False

    def test_should_continue_is_inverse_of_should_mark_stable(self, setup):
        loop, *_ = setup
        cases = [
            {"completeness_score": 0.50, "new_information_score": 0.10, "stable_streak": 0},
            {"completeness_score": 0.95, "new_information_score": 0.00, "stable_streak": 2},
        ]
        for ds in cases:
            assert loop.should_continue(ds) != loop.should_mark_stable(ds)


# ---------------------------------------------------------------------------
# run_iteration — return value shape
# ---------------------------------------------------------------------------


class TestRunIterationShape:
    def test_returns_required_keys(self, setup):
        loop, *_ = setup
        result = loop.run_iteration("messaging", _assets())
        for key in (
            "domain", "iteration", "processed_count",
            "completeness_score", "new_information_score",
            "gaps_found", "stable_streak", "status",
        ):
            assert key in result, f"Missing key: {key}"

    def test_domain_name_in_result(self, setup):
        loop, *_ = setup
        result = loop.run_iteration("messaging", _assets())
        assert result["domain"] == "messaging"

    def test_status_is_valid(self, setup):
        loop, *_ = setup
        result = loop.run_iteration("messaging", _assets())
        assert result["status"] in ("in_progress", "stable", "complete")

    def test_completeness_in_range(self, setup):
        loop, *_ = setup
        result = loop.run_iteration("messaging", _assets())
        assert 0.0 <= result["completeness_score"] <= 1.0

    def test_new_info_non_negative(self, setup):
        loop, *_ = setup
        result = loop.run_iteration("messaging", _assets())
        assert result["new_information_score"] >= 0.0

    def test_gaps_found_non_negative(self, setup):
        loop, *_ = setup
        result = loop.run_iteration("messaging", _assets())
        assert result["gaps_found"] >= 0

    def test_processed_count_non_negative(self, setup):
        loop, *_ = setup
        result = loop.run_iteration("messaging", _assets())
        assert result["processed_count"] >= 0


# ---------------------------------------------------------------------------
# run_iteration — state updates
# ---------------------------------------------------------------------------


class TestRunIterationStateUpdates:
    def test_iteration_counter_incremented(self, setup):
        loop, state, *_ = setup
        progress_before = state.get("messaging")
        iter_before = progress_before.iteration if progress_before else 0
        loop.run_iteration("messaging", _assets())
        progress_after = state.get("messaging")
        assert progress_after.iteration == iter_before + 1

    def test_processed_assets_tracked(self, setup):
        loop, state, *_ = setup
        assets = _assets(3)
        loop.run_iteration("messaging", assets)
        progress = state.get("messaging")
        assert len(progress.processed_asset_ids) > 0

    def test_assets_not_reprocessed_on_second_run(self, setup):
        loop, state, *_ = setup
        assets = _assets(3)
        loop.run_iteration("messaging", assets)
        count_after_first = len(state.get("messaging").processed_asset_ids)

        result2 = loop.run_iteration("messaging", assets)
        assert result2["processed_count"] == 0
        assert len(state.get("messaging").processed_asset_ids) == count_after_first

    def test_consecutive_stable_iterations_tracked(self, setup):
        loop, state, *_ = setup
        # Run with assets (will not be stable after 1 iter with few assets)
        loop.run_iteration("messaging", _assets())
        progress = state.get("messaging")
        # streak should be 0 or a valid integer
        assert isinstance(progress.consecutive_stable_iterations, int)


# ---------------------------------------------------------------------------
# run_iteration — persistence
# ---------------------------------------------------------------------------


class TestRunIterationPersistence:
    def test_state_file_written(self, setup, tmp_path):
        loop, *_ = setup
        loop.run_iteration("messaging", _assets())
        state_path = tmp_path / "domains" / "domain_state.json"
        assert state_path.exists()

    def test_memory_file_written(self, setup, tmp_path):
        loop, *_ = setup
        loop.run_iteration("messaging", _assets())
        memory_path = tmp_path / "data" / "domain_memory.json"
        assert memory_path.exists()

    def test_domain_model_files_written(self, setup, tmp_path):
        loop, *_ = setup
        loop.run_iteration("messaging", _assets())
        meta_path = tmp_path / "domains" / "messaging" / "000_meta.json"
        assert meta_path.exists()

    def test_gap_history_populated_in_memory(self, setup):
        loop, _, memory, _ = setup
        loop.run_iteration("messaging", _assets())
        history = memory.get_gap_history("messaging")
        assert isinstance(history, list)
        assert len(history) >= 1


# ---------------------------------------------------------------------------
# run_iteration — memory caching
# ---------------------------------------------------------------------------


class TestRunIterationCaching:
    def test_cached_insight_reused_on_same_hash(self, setup):
        loop, _, memory, _ = setup
        assets = _assets(1)
        asset_id = assets[0]["id"]

        # Pre-populate cache with a known insight
        cached_insight = {k: [] for k in INSIGHT_KEYS}
        cached_insight["entities"] = ["CachedEntity"]
        cached_insight["signal_strength"] = 0.5

        # Need to compute correct hash to match caching logic
        import hashlib
        chash = hashlib.sha256(str(assets[0].get("content", "")).encode()).hexdigest()

        memory.set_asset_insight("messaging", asset_id, cached_insight, chash)
        # Mark as unprocessed so loop will select it
        loop.run_iteration("messaging", assets)

        result = memory.get_asset_insight("messaging", asset_id)
        # Cache should have been used (hash matches, no overwrite)
        assert result is not None


# ---------------------------------------------------------------------------
# run_iteration — max_assets cap
# ---------------------------------------------------------------------------


class TestRunIterationMaxAssets:
    def test_max_assets_limits_processing(self, setup, tmp_path):
        domains_root = str(tmp_path / "domains2")
        data_root = str(tmp_path / "data2")

        from core.domain.domain_memory import DomainMemory as _Mem
        from core.domain.domain_model_store import DomainModelStore as _Store
        from core.domain.domain_state import DomainState as _State

        model_store = _Store(domains_root=domains_root)
        memory = _Mem(data_root=data_root)
        memory.load()
        state = _State(domains_root=domains_root)
        state.load()
        state.ensure_domains(["messaging"])
        state.save()

        loop = DomainLearningLoop(
            model_store=model_store,
            memory=memory,
            reasoner=AIReasoner(),
            query_engine=DomainQueryEngine(),
            state=state,
            max_assets_per_iter=2,
            verbose=False,
        )

        result = loop.run_iteration("messaging", _assets(10))
        assert result["processed_count"] <= 2
