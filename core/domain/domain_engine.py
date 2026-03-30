"""DomainEngine v1 — autonomous domain analysis loop.

Processes ONE domain per ``run_once()`` call.  Designed to run for hours
or days by calling ``run_once()`` or ``run_all()`` in a loop.

Guarantees
----------
* Resumable: state is reloaded from disk at the start of each ``run_once()``.
* Idempotent: running twice processes zero assets the second time (all
  already in ``processed_asset_ids``).
* Atomic: all state and model writes use ``path.tmp`` → ``os.replace``.
* Deterministic: asset selection and ordering are sorted.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.asset_scanner import AssetScanner
from core.domain.ai.domain_mapper import merge
from core.domain.ai.refiner import refine
from core.domain.ai.semantic_analyzer import analyze
from core.domain.domain_asset_matcher import match_assets
from core.domain.domain_model_store import DomainModelStore
from core.domain.domain_scoring import compute_completeness, compute_new_information, is_stable
from core.domain.domain_selector import pick_next
from core.domain.domain_state import DOMAIN_SEEDS, DomainProgress, DomainState


class DomainEngine:
    """Autonomous domain analysis engine.

    Parameters
    ----------
    scanner:
        Configured ``AssetScanner`` instance.
    domains_root:
        Root directory for domain state and model files.
        Defaults to ``domains/`` relative to cwd.
    seed_list:
        Domain names to bootstrap.  Defaults to ``DOMAIN_SEEDS``.
    max_assets_per_domain:
        Maximum unprocessed assets to handle per ``run_once()`` call.
        ``0`` means unlimited.
    verbose:
        Whether to print progress messages to stdout.
    """

    def __init__(
        self,
        scanner: AssetScanner,
        domains_root: str = "domains",
        seed_list: Optional[List[str]] = None,
        max_assets_per_domain: int = 0,
        verbose: bool = True,
    ) -> None:
        self._scanner = scanner
        self._domains_root = os.path.abspath(domains_root)
        self._seed_list = seed_list if seed_list is not None else list(DOMAIN_SEEDS)
        self._max_assets = max_assets_per_domain
        self._verbose = verbose
        self._state = DomainState(self._domains_root)
        self._store = DomainModelStore(self._domains_root)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        if self._verbose:
            print(msg)

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def _bootstrap(self) -> None:
        """Reload state from disk and ensure seed domains are present."""
        self._state.load()
        self._state.ensure_domains(self._seed_list)

    # ------------------------------------------------------------------
    # Asset helpers
    # ------------------------------------------------------------------

    def _load_all_assets(self) -> List[Dict]:
        return self._scanner.scan_all_assets()

    def _assets_by_id(self, assets: List[Dict]) -> Dict[str, Dict]:
        return {a.get("id", ""): a for a in assets}

    # ------------------------------------------------------------------
    # Main entry points
    # ------------------------------------------------------------------

    def run_once(self) -> Optional[Dict[str, Any]]:
        """Execute one domain iteration.

        Returns
        -------
        dict
            Result summary with keys: domain, status, iteration,
            matched_assets, processed_this_run, completeness_score,
            new_information_score.
        None
            When all domains are stable (nothing left to do).
        """
        self._bootstrap()

        domain: Optional[DomainProgress] = pick_next(self._state)
        if domain is None:
            self._log("[DomainEngine] All domains stable.")
            return None

        self._log(
            f"[DomainEngine] Processing domain: {domain.name}  "
            f"(iteration {domain.iteration + 1})"
        )

        # Scan and match assets
        all_assets = self._load_all_assets()
        matched_ids = match_assets(domain.name, all_assets)
        domain.matched_asset_ids = matched_ids

        assets_by_id = self._assets_by_id(all_assets)
        processed_set = set(domain.processed_asset_ids)
        pending = [aid for aid in matched_ids if aid not in processed_set]
        if self._max_assets > 0:
            pending = pending[: self._max_assets]

        self._log(
            f"[DomainEngine]   matched={len(matched_ids)}  "
            f"pending={len(pending)}  already_done={len(processed_set)}"
        )

        # Snapshot before
        old_model = self._store.load_model(domain.name)

        # Collect insights from each pending asset
        insights: List[Dict[str, Any]] = []
        for asset_id in pending:
            asset = assets_by_id.get(asset_id)
            if asset is None:
                continue
            insight = analyze(asset, domain.name)
            insights.append(insight)
            domain.processed_asset_ids.append(asset_id)

        # Merge + refine
        merged = merge(old_model, insights)
        refined = refine(merged)

        # Score
        completeness = compute_completeness(refined)
        new_info = compute_new_information(old_model, refined)

        # Update progress
        domain.iteration += 1
        domain.completeness_score = round(completeness, 4)
        domain.new_information_score = round(new_info, 4)
        domain.last_updated_utc = datetime.now(timezone.utc).isoformat()

        if is_stable(completeness, new_info):
            domain.status = "stable"
            self._log(
                f"[DomainEngine]   → STABLE  "
                f"completeness={completeness:.4f}  new_info={new_info:.4f}"
            )
        else:
            self._log(
                f"[DomainEngine]   completeness={completeness:.4f}  "
                f"new_info={new_info:.4f}  (continuing)"
            )

        # Persist — model first, then state
        meta = {
            "iteration": domain.iteration,
            "completeness_score": domain.completeness_score,
            "new_information_score": domain.new_information_score,
            "status": domain.status,
        }
        self._store.save_model(domain.name, refined, meta=meta)
        self._state.save()

        return {
            "domain": domain.name,
            "status": domain.status,
            "iteration": domain.iteration,
            "matched_assets": len(matched_ids),
            "processed_this_run": len(pending),
            "completeness_score": domain.completeness_score,
            "new_information_score": domain.new_information_score,
        }

    def run_once_v2(
        self,
        data_root: str = "data",
    ) -> Optional[Dict[str, Any]]:
        """Execute one v2 domain iteration using ``DomainLearningLoop``.

        Uses gap-driven asset selection and AI-backed reasoning.  The
        v1 ``run_once()`` method is unchanged; call this variant to opt
        into the v2 stack.

        Parameters
        ----------
        data_root:
            Root directory for ``data/domain_memory.json``.

        Returns
        -------
        dict
            Iteration summary (same shape as ``DomainLearningLoop.run_iteration``).
        None
            When all domains are stable (nothing left to do).
        """
        from core.domain.ai_reasoner import AIReasoner
        from core.domain.domain_learning_loop import DomainLearningLoop
        from core.domain.domain_memory import DomainMemory
        from core.domain.domain_query_engine import DomainQueryEngine

        self._bootstrap()

        domain: Optional[DomainProgress] = pick_next(self._state)
        if domain is None:
            self._log("[DomainEngine v2] All domains stable.")
            return None

        self._log(
            f"[DomainEngine v2] Processing domain: {domain.name}  "
            f"(iteration {domain.iteration + 1})"
        )

        # Scan and pre-filter assets for this domain
        all_assets = self._load_all_assets()
        matched_ids = match_assets(domain.name, all_assets)
        domain.matched_asset_ids = matched_ids

        id_set = set(matched_ids)
        matched_assets = [a for a in all_assets if a.get("id", "") in id_set]

        # Build v2 stack
        memory = DomainMemory(data_root=os.path.abspath(data_root))
        memory.load()
        reasoner = AIReasoner()
        query_engine = DomainQueryEngine()
        loop = DomainLearningLoop(
            model_store=self._store,
            memory=memory,
            reasoner=reasoner,
            query_engine=query_engine,
            state=self._state,
            max_assets_per_iter=self._max_assets,
            verbose=self._verbose,
        )

        return loop.run_iteration(domain.name, matched_assets)

    def run_all(self) -> List[Dict[str, Any]]:
        """Run until all domains are stable or no assets remain to process.

        Designed for autonomous long-running operation.  Each domain is
        allowed up to 2 consecutive idle runs (zero new assets processed).
        After that it is force-advanced to ``stable`` so that later domains
        can be picked by ``pick_next``.
        """
        results: List[Dict[str, Any]] = []
        domain_idle: Dict[str, int] = {}

        while True:
            result = self.run_once()
            if result is None:
                break
            results.append(result)
            domain = result["domain"]

            if result["processed_this_run"] == 0:
                domain_idle[domain] = domain_idle.get(domain, 0) + 1
            else:
                domain_idle[domain] = 0

            # If a domain has been idle for 2 runs and is not yet stable,
            # force it stable so pick_next can advance to the next domain.
            if domain_idle.get(domain, 0) >= 2 and result["status"] != "stable":
                self._bootstrap()
                prog = self._state.get(domain)
                if prog and prog.status != "stable":
                    prog.status = "stable"
                    self._state.save()
                    self._log(
                        f"[DomainEngine] {domain} force-advanced to stable "
                        f"after consecutive idle runs."
                    )

        return results
