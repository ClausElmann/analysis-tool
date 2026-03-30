"""
stage_state.py — Per-asset stage tracking with disk persistence.

Each asset moves through four stages in order:
  structured_extraction → semantic_analysis → domain_mapping → refinement

State is persisted to data/stage_state.json after every save() call.
Writes are atomic (.tmp + os.replace).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STAGES = (
    "structured_extraction",
    "semantic_analysis",
    "domain_mapping",
    "refinement",
)


class StageState:
    """
    Tracks which stages have been completed for each asset.

    An asset is considered stale (all stages pending) if its content_hash has
    changed since the last successful run.
    """

    def __init__(self, data_root: str):
        self._path = Path(data_root) / "stage_state.json"
        self._data: dict = {"assets": {}, "last_scan": None}
        self._load()

    # ── I/O ──────────────────────────────────────────────────────────────────

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {"assets": {}, "last_scan": None}

    def save(self):
        """Atomically persist state to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(self._path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self._path)

    # ── Queries ───────────────────────────────────────────────────────────────

    def _entry(self, asset_id: str) -> dict:
        return self._data["assets"].get(asset_id, {})

    def is_stale(self, asset: dict) -> bool:
        """Return True if content_hash has changed → all stages must re-run."""
        return self._entry(asset["id"]).get("content_hash") != asset.get("content_hash")

    def pending_stages(self, asset: dict) -> list:
        """Return ordered list of stages not yet successfully completed."""
        if self.is_stale(asset):
            return list(STAGES)
        stages_done = self._entry(asset["id"]).get("stages", {})
        return [s for s in STAGES if stages_done.get(s, {}).get("status") != "done"]

    def stage_status(self, asset_id: str, stage: str) -> Optional[str]:
        """Return status string for a specific stage, or None if unknown."""
        return self._entry(asset_id).get("stages", {}).get(stage, {}).get("status")

    # ── Mutations ─────────────────────────────────────────────────────────────

    def mark_stage_done(
        self,
        asset_id: str,
        content_hash: str,
        stage: str,
        output_path: Optional[str] = None,
    ):
        self._data["assets"].setdefault(
            asset_id, {"content_hash": content_hash, "stages": {}}
        )
        entry = self._data["assets"][asset_id]
        entry["content_hash"] = content_hash
        entry["stages"][stage] = {
            "status": "done",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "output_path": output_path,
        }

    def mark_stage_failed(
        self,
        asset_id: str,
        content_hash: str,
        stage: str,
        error: str,
    ):
        self._data["assets"].setdefault(
            asset_id, {"content_hash": content_hash, "stages": {}}
        )
        entry = self._data["assets"][asset_id]
        entry["content_hash"] = content_hash
        entry["stages"][stage] = {
            "status": "failed",
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "error": error,
        }

    def reset_asset(self, asset_id: str):
        """Force all stages to re-run for a specific asset."""
        self._data["assets"].pop(asset_id, None)

    def reset_all(self):
        """Force all stages to re-run for every asset."""
        self._data["assets"] = {}

    # ── Reporting ─────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        """Return per-stage counts of done/failed/pending across all tracked assets."""
        counts = {s: {"done": 0, "failed": 0, "pending": 0} for s in STAGES}
        for entry in self._data["assets"].values():
            for stage in STAGES:
                status = entry.get("stages", {}).get(stage, {}).get("status", "pending")
                bucket = status if status in ("done", "failed") else "pending"
                counts[stage][bucket] += 1
        return counts
