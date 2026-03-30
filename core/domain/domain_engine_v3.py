"""DomainEngine v3 — fully autonomous, discovery-first domain analysis.

Flow
----
1. **Scan** — collect all assets via ``AssetScanner``
2. **Discover** — infer business domains from assets
   (``DomainDiscoveryEngine``)
3. **Prioritize** — compute optimal build order
   (``DomainPrioritizer``)
4. **Analyze** — for each domain in priority order, run the gap-driven
   learning loop until stable or ``max_iterations_per_domain`` is reached
   (``DomainLearningLoop`` + ``DomainAutonomousSearch``)
5. **Persist** — all results written atomically after every iteration;
   the run is fully resumable (``--resume``)

Config surface (environment)
----------------------------
* ``DOMAIN_ENGINE_AI_ENABLED``  — ``false`` disables live LLM
* ``DOMAIN_ENGINE_AI_PROVIDER`` — ``openai`` (default) or other
* ``DOMAIN_ENGINE_AI_MODEL``    — model name (default: ``gpt-4o-mini``)

Entrypoint
----------
Use ``run_domain_engine_v3()`` for programmatic invocation, or subclass
``DomainEngineV3`` to customise any component.

Output tree::

    domains/
        domain_state.json               ← progress tracking
        {domain}/
            000_meta.json
            010_entities.json
            ...
            090_rebuild.json
            095_decision_support.json

    data/domains/
        discovered_domains.json         ← discovery output
        domain_priority.json            ← priority output
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.domain.ai_reasoner import AIProvider, AIReasoner, build_provider_from_env
from core.domain.domain_asset_matcher import match_assets
from core.domain.domain_autonomous_search import DomainAutonomousSearch
from core.domain.domain_discovery import DomainCandidate, DomainDiscoveryEngine
from core.domain.domain_learning_loop import DomainLearningLoop
from core.domain.domain_memory import DomainMemory
from core.domain.domain_model_store import DomainModelStore
from core.domain.domain_prioritizer import DomainPrioritizer
from core.domain.domain_query_engine import DomainQueryEngine
from core.domain.domain_state import DOMAIN_SEEDS, DomainState

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_MAX_ITERATIONS: int = 50
_DEFAULT_MAX_ASSETS: int = 30
_DEFAULT_DOMAINS_ROOT: str = "domains"
_DEFAULT_DATA_ROOT: str = "data"


# ---------------------------------------------------------------------------
# DomainEngineV3
# ---------------------------------------------------------------------------


class DomainEngineV3:
    """Autonomous, discovery-first domain analysis engine.

    Parameters
    ----------
    scanner:
        Any object with a ``scan_all_assets() -> List[dict]`` method.
    domains_root:
        Directory for domain state and model section files.
    data_root:
        Directory for discovery/priority JSON outputs and memory.
    seed_list:
        Explicit seed domain names appended after discovered domains.
        Pass ``[]`` (empty) to rely entirely on discovery.
    max_iterations_per_domain:
        Hard cap on iterations per domain.
    max_assets_per_iter:
        Maximum assets to analyse per iteration.
    ai_provider:
        Override AI provider.  ``None`` → ``build_provider_from_env()``.
    verbose:
        Print progress to stdout.
    """

    def __init__(
        self,
        scanner: Any,
        domains_root: str = _DEFAULT_DOMAINS_ROOT,
        data_root: str = _DEFAULT_DATA_ROOT,
        seed_list: Optional[List[str]] = None,
        max_iterations_per_domain: int = _DEFAULT_MAX_ITERATIONS,
        max_assets_per_iter: int = _DEFAULT_MAX_ASSETS,
        ai_provider: Optional[AIProvider] = None,
        verbose: bool = True,
    ) -> None:
        self._scanner  = scanner
        self._domains_root = os.path.abspath(domains_root)
        self._data_root    = os.path.abspath(data_root)
        self._seed_list    = list(seed_list) if seed_list is not None else list(DOMAIN_SEEDS)
        self._max_iters    = max_iterations_per_domain
        self._max_assets   = max_assets_per_iter
        self._verbose      = verbose

        # Core components
        provider       = ai_provider or build_provider_from_env()
        self._state    = DomainState(self._domains_root)
        self._store    = DomainModelStore(self._domains_root)
        self._memory   = DomainMemory(self._data_root)
        self._reasoner = AIReasoner(provider=provider)
        self._qe       = DomainQueryEngine()
        self._search   = DomainAutonomousSearch(self._qe)
        self._discovery = DomainDiscoveryEngine()
        self._prioritizer = DomainPrioritizer()

        self._loop = DomainLearningLoop(
            model_store=self._store,
            memory=self._memory,
            reasoner=self._reasoner,
            query_engine=self._qe,
            state=self._state,
            search_engine=self._search,
            max_assets_per_iter=max_assets_per_iter,
            verbose=verbose,
        )

    # ------------------------------------------------------------------
    # Logging

    def _log(self, msg: str) -> None:
        if self._verbose:
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            print(f"[DomainEngineV3 {ts}] {msg}")

    # ------------------------------------------------------------------
    # Public: discovery + prioritization

    def discover_and_prioritize(
        self,
        assets: List[Dict[str, Any]],
    ) -> tuple:  # (List[DomainCandidate], List[Dict])
        """Run discovery and prioritization over *assets*.

        Returns
        -------
        tuple
            ``(candidates, priority_list)`` where *candidates* is a list of
            ``DomainCandidate`` and *priority_list* is a list of dicts with
            ``domain``, ``priority``, ``tier``, ``reason``.
        """
        candidates    = self._discovery.discover(assets)
        priority_list = self._prioritizer.prioritize(candidates)
        return candidates, priority_list

    # ------------------------------------------------------------------
    # Public: main run

    def run(
        self,
        resume: bool = True,
    ) -> List[Dict[str, Any]]:
        """Execute the full autonomous v3 pipeline.

        Parameters
        ----------
        resume:
            When *True* (default), skip domains already marked ``stable``.
            When *False*, reset all domain state before analysis.

        Returns
        -------
        list[dict]
            Per-domain result summaries.
        """
        self._log("scanning assets …")
        all_assets = self._scanner.scan_all_assets()
        self._log(f"scanned {len(all_assets)} assets")

        # Discovery + prioritization
        self._log("discovering domains …")
        candidates, priority_list = self.discover_and_prioritize(all_assets)
        self._log(f"discovered {len(candidates)} domain(s), "
                  f"{len(priority_list)} prioritised")

        # Persist discovery outputs
        out_dir = os.path.join(self._data_root, "domains")
        self._discovery.save(
            candidates, os.path.join(out_dir, "discovered_domains.json")
        )
        self._prioritizer.save(
            priority_list, os.path.join(out_dir, "domain_priority.json")
        )

        # Build ordered domain name list (priority order → then seeds)
        ordered: List[str] = [p["domain"] for p in priority_list]
        for seed in self._seed_list:
            if seed not in ordered:
                ordered.append(seed)

        # Load / reset state
        self._state.load()
        if not resume:
            # Wipe progress (clear processed IDs, not files)
            for name in ordered:
                prog = self._state.get(name)
                if prog is not None:
                    from core.domain.domain_state import STATUS_PENDING
                    prog.status = STATUS_PENDING
                    prog.iteration = 0
                    prog.processed_asset_ids = []
                    prog.consecutive_stable_iterations = 0

        self._state.ensure_domains(ordered)
        self._memory.load()

        # Tag each domain with its priority position
        for i, name in enumerate(ordered):
            prog = self._state.get(name)
            if prog is not None:
                prog.current_focus = f"priority_{i + 1}"

        self._state.save()
        self._log(f"{len(ordered)} domain(s) enqueued")

        # Analyse each domain in priority order
        results: List[Dict[str, Any]] = []
        for domain_name in ordered:
            prog = self._state.get(domain_name)
            if prog is not None and prog.status == "stable" and resume:
                self._log(f"{domain_name} ← already stable, skipping")
                results.append({"domain": domain_name, "status": "stable", "skipped": True})
                continue

            result = self._run_domain_to_saturation(domain_name, all_assets)
            results.append(result)

        self._log("run complete")
        return results

    def _run_domain_to_saturation(
        self, domain_name: str, all_assets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Iterate *domain_name* until stable or ``_max_iters`` reached."""
        # Match domain assets from the full corpus
        matched_ids   = match_assets(domain_name, all_assets)
        assets_by_id  = {a.get("id", ""): a for a in all_assets}
        domain_assets = [
            assets_by_id[aid] for aid in matched_ids if aid in assets_by_id
        ]

        self._log(
            f"{domain_name} → matched {len(domain_assets)} assets, "
            f"starting analysis"
        )

        last_result: Dict[str, Any] = {
            "domain": domain_name,
            "status": "no_assets",
            "iterations_run": 0,
        }

        for iteration in range(self._max_iters):
            result = self._loop.run_iteration(
                domain_name=domain_name,
                assets=domain_assets,
                all_assets=all_assets,
            )
            last_result = result
            last_result["iterations_run"] = iteration + 1

            if result["status"] == "stable":
                self._log(
                    f"{domain_name} → STABLE after {iteration + 1} iteration(s)  "
                    f"completeness={result.get('completeness_score', 0):.4f}"
                )
                break

            if result.get("processed_count", 0) == 0 and iteration > 0:
                self._log(
                    f"{domain_name} → no new assets, stopping at "
                    f"iteration {iteration + 1}"
                )
                break

        return last_result


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def run_domain_engine_v3(
    scanner: Any,
    domains_root: str = _DEFAULT_DOMAINS_ROOT,
    data_root: str = _DEFAULT_DATA_ROOT,
    seed_list: Optional[List[str]] = None,
    max_iterations_per_domain: int = _DEFAULT_MAX_ITERATIONS,
    max_assets_per_iter: int = _DEFAULT_MAX_ASSETS,
    ai_provider: Optional[AIProvider] = None,
    verbose: bool = True,
    resume: bool = True,
) -> List[Dict[str, Any]]:
    """Construct and run a ``DomainEngineV3`` in one call.

    Parameters
    ----------
    scanner:
        Any object with ``scan_all_assets() -> List[dict]``.
    domains_root:
        Root for domain state and files (default: ``"domains"``).
    data_root:
        Root for memory and discovery outputs (default: ``"data"``).
    seed_list:
        Extra domain names to process after discovery.
    max_iterations_per_domain:
        Hard iteration cap per domain (default: 50).
    max_assets_per_iter:
        Assets processed per iteration (default: 30).
    ai_provider:
        Override provider. ``None`` → ``build_provider_from_env()``.
    verbose:
        Print progress to stdout.
    resume:
        Skip already-stable domains when *True*.

    Returns
    -------
    list[dict]
        Per-domain result summaries.
    """
    engine = DomainEngineV3(
        scanner=scanner,
        domains_root=domains_root,
        data_root=data_root,
        seed_list=seed_list,
        max_iterations_per_domain=max_iterations_per_domain,
        max_assets_per_iter=max_assets_per_iter,
        ai_provider=ai_provider,
        verbose=verbose,
    )
    return engine.run(resume=resume)
