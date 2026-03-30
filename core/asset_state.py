"""Asset processing state — tracks which grouped assets have been processed.

State file: data/asset_state.json

Format::

    {
      "processed": {
        "<asset_id>": {
          "content_hash": "<sha256_hex>",
          "processed_at": "<iso_utc_timestamp>"
        }
      },
      "last_scan": "<iso_utc_timestamp>"
    }

Reprocessing trigger
--------------------
An asset is considered stale (needs reprocessing) when:
  - Its id is not in the ``processed`` map (new asset).
  - Its ``content_hash`` has changed since last processing.

For *batch* asset types (work_items_batch, git_insights_batch) this means any
change to any item in the batch triggers reprocessing of the entire batch — no
partial updates.

Guarantees
----------
- State is written atomically (write to .tmp, then os.replace).
- IDs are stored verbatim — the same id always maps to the same asset.
- Removing an id from the processed map forces reprocessing on the next run.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional


class AssetState:
    """Read/write asset processing state from ``data/asset_state.json``.

    Parameters
    ----------
    data_root:
        Same ``data_root`` passed to ``AssetScanner`` and ``AssetProcessor``.
    """

    _FILENAME = "asset_state.json"

    def __init__(self, data_root: str) -> None:
        self.data_root = os.path.abspath(data_root)
        self._state_path = os.path.join(self.data_root, self._FILENAME)
        self._state: Dict = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_stale(self, asset: Dict) -> bool:
        """Return True if *asset* needs (re)processing.

        An asset is stale when:
          - It has never been processed (id absent from processed map).
          - Its ``content_hash`` differs from the stored hash.
        """
        asset_id = asset["id"]
        stored = self._state["processed"].get(asset_id)
        if stored is None:
            return True
        return stored.get("content_hash") != asset.get("content_hash")

    def mark_processed(self, asset: Dict) -> None:
        """Record *asset* as successfully processed at the current UTC time."""
        self._state["processed"][asset["id"]] = {
            "content_hash": asset.get("content_hash", ""),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

    def mark_scan(self) -> None:
        """Update the ``last_scan`` timestamp (call after each full scan)."""
        self._state["last_scan"] = datetime.now(timezone.utc).isoformat()

    def save(self) -> None:
        """Persist state to disk atomically."""
        os.makedirs(self.data_root, exist_ok=True)
        tmp = self._state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._state, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, self._state_path)

    def stale_assets(self, assets: List[Dict]) -> List[Dict]:
        """Filter *assets* to those that need processing."""
        return [a for a in assets if self.is_stale(a)]

    def summary(self) -> Dict:
        """Return a snapshot of state statistics."""
        processed = self._state["processed"]
        return {
            "total_processed": len(processed),
            "last_scan": self._state.get("last_scan", ""),
        }

    def reset_asset(self, asset_id: str) -> None:
        """Remove *asset_id* from the processed map, forcing reprocessing."""
        self._state["processed"].pop(asset_id, None)

    def reset_all(self) -> None:
        """Clear all processed state, forcing full reprocessing on next run."""
        self._state["processed"] = {}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> Dict:
        """Load state from disk; return a fresh empty state if unavailable."""
        if os.path.isfile(self._state_path):
            try:
                with open(self._state_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict) and isinstance(data.get("processed"), dict):
                    return data
            except (OSError, json.JSONDecodeError):
                pass
        return {"processed": {}, "last_scan": ""}
