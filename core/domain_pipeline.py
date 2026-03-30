"""
domain_pipeline.py — Orchestrates the full multi-stage AI extraction loop.

For each asset returned by the scanner:
  1. Check which stages are still pending (via StageState)
  2. Run each pending stage in order through the AI processor
  3. Save output to disk and persist state after EVERY stage
  4. Log progress continuously

The pipeline is fully restartable: kill it at any point and re-run —
it resumes from exactly where it stopped.

Output files are written to:
  {output_root}/{stage}/{safe_asset_id}.json
"""

import json
import os
from pathlib import Path
from typing import Callable, Optional

from core.stage_state import StageState, STAGES
from core.ai_processor import AIProcessor
from core.prompt_builder import PromptBuilder


class DomainPipeline:
    """
    Drives the scan → filter-stale → multi-stage-AI → persist loop.

    Args:
        scanner:       Any object with scan_all_assets() → list[dict]
        stage_state:   StageState instance (tracks per-stage completion)
        ai_processor:  AIProcessor implementation (or StubAIProcessor)
        output_root:   Directory where JSON results are written
        verbose:       Print [SCAN]/[PROCESS]/[SKIP]/[DONE]/[ERROR] lines
    """

    def __init__(
        self,
        scanner,
        stage_state: StageState,
        ai_processor: AIProcessor,
        output_root: str,
        verbose: bool = False,
    ):
        self._scanner = scanner
        self._state = stage_state
        self._ai = ai_processor
        self._output_root = Path(output_root)
        self._verbose = verbose
        self._prompt_builder = PromptBuilder()
        self._output_root.mkdir(parents=True, exist_ok=True)

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, tag: str, msg: str):
        if self._verbose:
            print(f"[{tag:<10}] {msg}")

    # ── Output paths ──────────────────────────────────────────────────────────

    def _output_path(self, asset_id: str, stage: str) -> Path:
        safe = (
            asset_id
            .replace(":", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )
        return self._output_root / stage / f"{safe}.json"

    def _load_previous(self, asset_id: str, stage: str) -> dict | None:
        path = self._output_path(asset_id, stage)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def _save_result(self, asset_id: str, stage: str, result: dict):
        path = self._output_path(asset_id, stage)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    # ── Stage execution ───────────────────────────────────────────────────────

    def _process_stage(self, asset: dict, stage: str) -> bool:
        """Run one stage for one asset. Persists state. Returns True on success."""
        prev_stage_idx = STAGES.index(stage) - 1
        previous = (
            self._load_previous(asset["id"], STAGES[prev_stage_idx])
            if prev_stage_idx >= 0
            else None
        )

        prompt = self._prompt_builder.build(asset, stage, previous)

        try:
            result = self._ai.process(asset, stage, prompt)
            result["asset_id"] = asset["id"]
            result["stage"] = stage
            self._save_result(asset["id"], stage, result)
            self._state.mark_stage_done(
                asset["id"],
                asset.get("content_hash", ""),
                stage,
                str(self._output_path(asset["id"], stage)),
            )
            self._state.save()
            self._log(
                "DONE",
                f"{asset['type']:<24} {stage:<24} {asset['id']}",
            )
            return True

        except Exception as exc:
            self._state.mark_stage_failed(
                asset["id"],
                asset.get("content_hash", ""),
                stage,
                str(exc),
            )
            self._state.save()
            self._log(
                "ERROR",
                f"{asset['type']:<24} {stage:<24} {asset['id']} — {exc}",
            )
            return False

    # ── Public API ────────────────────────────────────────────────────────────

    def run(
        self,
        max_assets: int | None = None,
        stages: list | None = None,
        asset_filter: "Callable[[dict], bool] | None" = None,
    ) -> dict:
        """
        Run the pipeline.

        Args:
            max_assets:   Stop after processing this many assets (skipped count too).
            stages:       Restrict to a subset of STAGES. Default: all stages.
            asset_filter: Optional callable(asset) → bool.  When provided, only
                          assets for which the callable returns True are processed.
                          Assets that fail the filter are silently excluded (not
                          counted as skipped or processed).

        Returns:
            {"processed": int, "skipped": int, "errors": int, "total": int}
        """
        target_stages = list(stages) if stages else list(STAGES)
        assets = self._scanner.scan_all_assets()

        self._log("SCAN", f"Scanned {len(assets)} assets")

        processed = skipped = errors = 0
        count = 0

        for asset in assets:
            if max_assets is not None and count >= max_assets:
                break

            if asset_filter is not None and not asset_filter(asset):
                continue

            pending = [
                s for s in self._state.pending_stages(asset)
                if s in target_stages
            ]

            if not pending:
                self._log("SKIP", f"{asset['type']:<24} {asset['id']}")
                skipped += 1
                count += 1
                continue

            for stage in pending:
                if self._process_stage(asset, stage):
                    processed += 1
                else:
                    errors += 1

            count += 1

        report = {
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
            "total": len(assets),
        }
        self._log(
            "DONE",
            f"Processed {processed}  Skipped {skipped}  Errors {errors}",
        )
        return report

    def dry_run(self) -> dict:
        """
        Report how many assets/stage-runs are pending without writing anything.

        Returns:
            {"assets": int, "breakdown": {type: {"assets": int, "pending_stages": int}}}
        """
        assets = self._scanner.scan_all_assets()
        breakdown: dict[str, dict[str, int]] = {}

        for asset in assets:
            t = asset["type"]
            pending = self._state.pending_stages(asset)
            breakdown.setdefault(t, {"assets": 0, "pending_stages": 0})
            breakdown[t]["assets"] += 1
            breakdown[t]["pending_stages"] += len(pending)

        return {"assets": len(assets), "breakdown": breakdown}
