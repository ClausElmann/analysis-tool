"""Domain learning loop — iterative domain refinement driven by gaps and AI reasoning.

``DomainLearningLoop`` orchestrates one refinement iteration:

1. Load current model from store
2. Load domain memory
3. Detect current gaps (via AIReasoner)
4. Snapshot gaps into memory
5. Select best assets for this iteration (via DomainQueryEngine)
6. Analyze selected assets (via AIReasoner), cache in memory
7. Merge + refine combined insights into domain model
8. Run cross-analysis on refined model
9. Compute completeness / new-information scores
10. Update stable-streak counter and persist everything

Stop conditions
---------------
``completeness_score >= 0.90 AND new_information_score < 0.02``
must hold for **2 consecutive iterations** before marking stable
(tracked via ``DomainProgress.consecutive_stable_iterations``).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.domain.ai.domain_mapper import merge
from core.domain.ai.refiner import refine
from core.domain.ai.semantic_analyzer import INSIGHT_KEYS
from core.domain.ai_reasoner import AIReasoner
from core.domain.domain_memory import DomainMemory
from core.domain.domain_model_store import DomainModelStore
from core.domain.domain_query_engine import DomainQueryEngine
from core.domain.domain_scoring import (
    COMPLETENESS_THRESHOLD,
    COMPLETENESS_THRESHOLD_V2,
    CONSISTENCY_THRESHOLD,
    NEW_INFO_THRESHOLD,
    SATURATION_THRESHOLD,
    compute_completeness,
    compute_consistency_score,
    compute_new_information,
    compute_saturation_score,
)
from core.domain.domain_state import DomainState

# How many consecutive stable iterations are required before the domain is
# marked stable and removed from the active processing queue.
_REQUIRED_STABLE_STREAK: int = 3


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _content_hash(asset: Dict[str, Any]) -> str:
    """Return a short SHA-256 hex derived from the asset's content.

    Uses ``asset["content_hash"]`` if already provided, otherwise
    hashes the raw ``content`` string.
    """
    if asset.get("content_hash"):
        return str(asset["content_hash"])
    raw = str(asset.get("content") or "")
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# DomainLearningLoop
# ---------------------------------------------------------------------------


class DomainLearningLoop:
    """Iterative, gap-driven domain refinement engine.

    Parameters
    ----------
    model_store:
        ``DomainModelStore`` instance for reading / writing domain models.
    memory:
        ``DomainMemory`` instance holding AI-derived knowledge.
    reasoner:
        ``AIReasoner`` instance.
    query_engine:
        ``DomainQueryEngine`` instance for asset selection.
    state:
        ``DomainState`` instance — updated after each iteration.
    max_assets_per_iter:
        Maximum assets to process per iteration.  ``0`` = unlimited.
    verbose:
        When *True*, emit progress lines to stdout.
    """

    def __init__(
        self,
        model_store: DomainModelStore,
        memory: DomainMemory,
        reasoner: AIReasoner,
        query_engine: DomainQueryEngine,
        state: DomainState,
        max_assets_per_iter: int = 30,
        verbose: bool = True,
        search_engine: Optional[Any] = None,
    ) -> None:
        self._store = model_store
        self._memory = memory
        self._reasoner = reasoner
        self._query_engine = query_engine
        self._state = state
        self._max_assets = max_assets_per_iter
        self._verbose = verbose
        self._search_engine = search_engine  # DomainAutonomousSearch | None

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        if self._verbose:
            print(msg)

    # ------------------------------------------------------------------
    # Main iteration
    # ------------------------------------------------------------------

    def run_iteration(
        self,
        domain_name: str,
        assets: List[Dict[str, Any]],
        all_assets: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Execute one refinement iteration for *domain_name*.

        Parameters
        ----------
        domain_name:
            The domain being refined.
        assets:
            Candidate assets (typically the full set matched for this
            domain).  The query engine selects the most valuable subset.

        Returns
        -------
        dict
            Summary with keys: ``domain``, ``iteration``,
            ``processed_count``, ``completeness_score``,
            ``new_information_score``, ``gaps_found``, ``stable_streak``,
            ``status``.
        """
        # 1. Load current domain model
        old_model = self._store.load_model(domain_name)

        # 2. Ensure memory is loaded
        self._memory.load()

        # 3. Detect gaps in the current model
        gaps = self._reasoner.detect_gaps(old_model, domain_name)

        # 4. Snapshot gap list into memory (append-only)
        self._memory.add_gap_snapshot(domain_name, gaps)

        # Update domain progress gaps field (store gap IDs only)
        progress = self._state.get(domain_name)
        if progress is not None:
            progress.gaps = sorted({g["id"] for g in gaps})

        # 4b. Autonomous gap-driven search — expand the asset candidate pool
        # Uses the full corpus (all_assets) when provided so the search can
        # surface assets that weren't matched by the keyword matcher.
        if self._search_engine is not None and gaps:
            search_pool = all_assets if all_assets is not None else assets
            extras = self._search_engine.find_assets_for_gaps(
                gaps=gaps,
                domain_name=domain_name,
                assets=search_pool,
                memory=self._memory,
            )
            if extras:
                existing_ids = {a.get("id", "") for a in assets}
                new_assets = [
                    a for a in extras if a.get("id", "") not in existing_ids
                ]
                if new_assets:
                    assets = list(assets) + new_assets
                    self._log(
                        f"[LearningLoop:{domain_name}] "
                        f"search expanded pool by {len(new_assets)} asset(s)"
                    )

        # 5. Select best assets for this iteration
        processed_set: set = set(
            progress.processed_asset_ids if progress is not None else []
        )
        selected = self._query_engine.select_assets_for_iteration(
            domain_name=domain_name,
            assets=assets,
            gaps=gaps,
            processed_ids=processed_set,
            max_assets=self._max_assets,
        )

        # Restrict strictly to unprocessed assets (query engine puts them
        # first but does not guarantee exclusion of all processed ones)
        pending = [a for a in selected if a.get("id", "") not in processed_set]
        if self._max_assets > 0:
            pending = pending[: self._max_assets]

        self._log(
            f"[LearningLoop:{domain_name}] gaps={len(gaps)}  "
            f"pending={len(pending)}  processed_so_far={len(processed_set)}"
        )

        # 6. Analyze each asset and cache results in memory
        insights: List[Dict[str, Any]] = []
        for asset in pending:
            asset_id = asset.get("id", "")
            chash = _content_hash(asset)

            # Use cached insight when content is unchanged
            cached = self._memory.get_asset_insight(domain_name, asset_id)
            if cached and cached.get("content_hash") == chash:
                insight = cached.get("semantic", {})
            else:
                insight = self._reasoner.analyze_asset(asset, domain_name)
                self._memory.set_asset_insight(domain_name, asset_id, insight, chash)

            insights.append(insight)

            # Mark as processed
            if progress is not None and asset_id not in processed_set:
                progress.processed_asset_ids.append(asset_id)
                processed_set.add(asset_id)

        # 7. Merge + refine
        # Strip the extra "signal_strength" key before merging so that
        # domain_mapper only sees the canonical INSIGHT_KEYS
        clean_insights = [
            {k: v for k, v in ins.items() if k in INSIGHT_KEYS}
            for ins in insights
        ]
        merged = merge(old_model, clean_insights)
        refined = refine(merged)

        # 8. Cross-analysis on the refined model
        cross = self._reasoner.cross_analyze(refined, domain_name)
        self._memory.set_cross_analysis(domain_name, cross)

        # 9. Score
        completeness = compute_completeness(refined)
        new_info = compute_new_information(old_model, refined)

        # Compute consistency from the fresh cross-analysis
        consistency = compute_consistency_score(cross)

        # Compute saturation from gap history
        gap_history = self._memory.get_gap_history(domain_name)
        saturation = compute_saturation_score(gap_history)

        # Update stable-streak counter (v2: all 4 conditions)
        is_convergent = (
            completeness >= COMPLETENESS_THRESHOLD_V2
            and consistency >= CONSISTENCY_THRESHOLD
            and saturation >= SATURATION_THRESHOLD
            and new_info < NEW_INFO_THRESHOLD
        )
        prev_streak = (
            progress.consecutive_stable_iterations if progress is not None else 0
        )
        new_streak = (prev_streak + 1) if is_convergent else 0

        # 10. Determine status and update DomainProgress
        status = "in_progress"
        if self.should_mark_stable(
            {
                "completeness_score": completeness,
                "consistency_score": consistency,
                "saturation_score": saturation,
                "new_information_score": new_info,
                "stable_streak": new_streak,
            }
        ):
            status = "stable"
            self._log(
                f"[LearningLoop:{domain_name}] → STABLE  "
                f"completeness={completeness:.4f}  new_info={new_info:.4f}  "
                f"streak={new_streak}"
            )
        else:
            self._log(
                f"[LearningLoop:{domain_name}] completeness={completeness:.4f}  "
                f"new_info={new_info:.4f}  streak={new_streak}"
            )

        if progress is not None:
            progress.iteration += 1
            progress.completeness_score = round(completeness, 4)
            progress.new_information_score = round(new_info, 4)
            progress.consecutive_stable_iterations = new_streak
            progress.last_updated_utc = datetime.now(timezone.utc).isoformat()
            if status == "stable":
                progress.status = status

        # 11. Persist — model → memory → state
        meta: Dict[str, Any] = {
            "iteration": progress.iteration if progress is not None else 1,
            "completeness_score": round(completeness, 4),
            "new_information_score": round(new_info, 4),
            "status": status,
            "gaps_count": len(gaps),
        }
        self._store.save_model(domain_name, refined, meta=meta)
        self._memory.save()
        self._state.save()

        return {
            "domain": domain_name,
            "iteration": progress.iteration if progress is not None else 1,
            "processed_count": len(pending),
            "completeness_score": round(completeness, 4),
            "consistency_score": round(consistency, 4),
            "saturation_score": round(saturation, 4),
            "new_information_score": round(new_info, 4),
            "gaps_found": len(gaps),
            "stable_streak": new_streak,
            "status": status,
        }

    # ------------------------------------------------------------------
    # Stop conditions
    # ------------------------------------------------------------------

    def should_continue(self, domain_state: Dict[str, Any]) -> bool:
        """Return *True* if the domain needs more iterations.

        Stops iterating only when *both* convergence thresholds have been
        met AND the stable streak has reached ``_REQUIRED_STABLE_STREAK``.
        """
        return not self.should_mark_stable(domain_state)

    def should_mark_stable(self, domain_state: Dict[str, Any]) -> bool:
        """Return *True* when the domain has converged sufficiently.

        v2 requires all four conditions:
        * ``completeness_score >= 0.85`` (``COMPLETENESS_THRESHOLD_V2``)
        * ``consistency_score >= 0.80`` (``CONSISTENCY_THRESHOLD``) — default 1.0
        * ``saturation_score >= 0.90`` (``SATURATION_THRESHOLD``) — default 1.0
        * ``new_information_score < 0.02`` (``NEW_INFO_THRESHOLD``)
        * ``stable_streak >= 3`` (``_REQUIRED_STABLE_STREAK``)

        The consistency/saturation keys default to 1.0 so callers that only
        pass the legacy completeness/new_info/streak keys still work.
        """
        completeness = float(domain_state.get("completeness_score", 0.0))
        consistency = float(domain_state.get("consistency_score", 1.0))
        saturation = float(domain_state.get("saturation_score", 1.0))
        new_info = float(domain_state.get("new_information_score", 1.0))
        streak = int(domain_state.get("stable_streak", 0))

        return (
            completeness >= COMPLETENESS_THRESHOLD_V2
            and consistency >= CONSISTENCY_THRESHOLD
            and saturation >= SATURATION_THRESHOLD
            and new_info < NEW_INFO_THRESHOLD
            and streak >= _REQUIRED_STABLE_STREAK
        )
