"""Asset process engine — iterates over grouped assets and dispatches them.

Responsibilities
----------------
- Load all assets via ``AssetScanner.scan_all_assets()``.
- Check ``AssetState`` to skip unchanged assets.
- Log each asset being processed with its type and group size.
- Call the registered handler for each stale asset.
- Persist state after each processed asset.
- Return a structured run report.

Usage
-----
::

    from core.asset_scanner import AssetScanner
    from core.asset_state import AssetState
    from core.asset_processor import AssetProcessor

    def my_handler(asset: dict) -> dict:
        # Call AI, write output, etc.
        # Return any result dict (or empty dict).
        return {}

    scanner = AssetScanner(
        data_root="data",
        wiki_root="C:/wiki",
        raw_root="raw",
        solution_root="C:/sms-service",
    )
    state = AssetState("data")
    processor = AssetProcessor(scanner, state)
    processor.register_handler("pdf_section", my_handler)
    report = processor.run()
    print(report)

Handler contract
----------------
A handler receives one asset dict and returns a result dict.
Exceptions from a handler are caught, logged as errors, and do NOT prevent
remaining assets from being processed.

If no handler is registered for an asset type, the asset is skipped (not
marked as processed).

Logging format (printed to stdout)
-----------------------------------
::

    [SCAN]    Scanning all assets...
    [SCAN]    Scanned 1834 assets (243 stale)
    [PROCESS] pdf_section        "Bootstrap-vs-Material..."  (2 pages)
    [PROCESS] wiki_section       "Architecture.md §3"        (1 section)
    [PROCESS] work_items_batch   batch 0                     (100 items)
    [PROCESS] git_insights_batch batch 34                    (100 items)
    [PROCESS] labels_namespace   "accessibility"             (15 keys)
    [SKIP]    code_file          "code:ServiceAlert.Web/..."  unchanged
    [DONE]    Processed 243 assets  Skipped 1591  Errors 0
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from core.asset_scanner import AssetScanner
from core.asset_state import AssetState


# Type alias for a handler callable
Handler = Callable[[Dict], Dict]

# Human-readable log labels per asset type
_TYPE_LOG_LABELS: Dict[str, str] = {
    "pdf_section":        "pdf_section",
    "wiki_section":       "wiki_section",
    "work_items_batch":   "work_items_batch",
    "git_insights_batch": "git_insights_batch",
    "labels_namespace":   "labels_namespace",
    "code_file":          "code_file",
}


def _format_group_hint(asset: Dict) -> str:
    """Return a compact human-readable description of what's inside the group."""
    atype = asset.get("type", "")
    gs = asset.get("group_size", 1)

    if atype == "pdf_section":
        return f"{gs} page{'s' if gs != 1 else ''}"
    if atype == "wiki_section":
        return "1 section"
    if atype == "work_items_batch":
        return f"{gs} item{'s' if gs != 1 else ''}"
    if atype == "git_insights_batch":
        return f"{gs} item{'s' if gs != 1 else ''}"
    if atype == "labels_namespace":
        return f"{gs} key{'s' if gs != 1 else ''}"
    if atype == "code_file":
        return "1 file"
    return f"{gs} item{'s' if gs != 1 else ''}"


def _format_asset_label(asset: Dict) -> str:
    """Return a short display name for the asset (for log output)."""
    atype = asset.get("type", "")
    if atype == "pdf_section":
        return f"\"{asset.get('file', '')}\" §{asset.get('section_index', 0)}"
    if atype == "wiki_section":
        fname = asset.get("file", "")
        heading = asset.get("heading", "")
        return f"{fname} §{asset.get('section_index', 0)} \"{heading[:40]}\""
    if atype == "work_items_batch":
        return f"batch {asset.get('batch_index', 0)}"
    if atype == "git_insights_batch":
        return f"batch {asset.get('batch_index', 0)}"
    if atype == "labels_namespace":
        return f"\"{asset.get('namespace', '')}\""
    if atype == "code_file":
        return f"\"{asset.get('path', '')}\""
    return asset.get("id", "")


class AssetProcessor:
    """Drives the full scan → filter stale → process → persist-state loop.

    Parameters
    ----------
    scanner:
        Configured ``AssetScanner`` instance.
    state:
        ``AssetState`` instance backed by ``data/asset_state.json``.
    verbose:
        When True, print a [SKIP] line for every unchanged asset.
        When False (default), only log processed and error assets.
    """

    def __init__(
        self,
        scanner: AssetScanner,
        state: AssetState,
        verbose: bool = False,
    ) -> None:
        self._scanner = scanner
        self._state = state
        self._verbose = verbose
        self._handlers: Dict[str, Handler] = {}

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handler(self, asset_type: str, handler: Handler) -> None:
        """Register *handler* for *asset_type*.

        Only one handler per type is supported; a second call overwrites.
        Raises ``ValueError`` if *asset_type* is not a known asset type.
        """
        from core.asset_scanner import ASSET_TYPES
        if asset_type not in ASSET_TYPES:
            raise ValueError(
                f"Unknown asset type {asset_type!r}. "
                f"Valid types: {sorted(ASSET_TYPES)}"
            )
        self._handlers[asset_type] = handler

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> Dict:
        """Execute the full scan-and-process loop.

        Returns
        -------
        dict with keys:
            scanned      : total assets found
            stale        : assets that needed processing
            processed    : assets successfully processed
            skipped      : assets skipped (unchanged or no handler)
            errors       : list of {id, error} dicts
            started_at   : ISO UTC timestamp
            finished_at  : ISO UTC timestamp
        """
        started_at = datetime.now(timezone.utc).isoformat()
        errors: List[Dict] = []
        processed_count = 0
        skipped_count = 0

        # STEP 1 — Scan
        print("[SCAN]    Scanning all assets...")
        all_assets = self._scanner.scan_all_assets()
        self._state.mark_scan()

        stale = self._state.stale_assets(all_assets)
        print(
            f"[SCAN]    Scanned {len(all_assets)} assets "
            f"({len(stale)} stale)"
        )

        # STEP 4 — Process loop (unchanged iteration, grouped content)
        for asset in all_assets:
            asset_type = asset.get("type", "")
            asset_id = asset.get("id", "")
            handler = self._handlers.get(asset_type)

            is_stale = self._state.is_stale(asset)

            if not is_stale:
                skipped_count += 1
                if self._verbose:
                    label = _format_asset_label(asset)
                    type_label = _TYPE_LOG_LABELS.get(asset_type, asset_type)
                    print(
                        f"[SKIP]    {type_label:<20} {label:<50}  unchanged"
                    )
                continue

            if handler is None:
                skipped_count += 1
                continue

            # STEP 5 — Logging
            label = _format_asset_label(asset)
            type_label = _TYPE_LOG_LABELS.get(asset_type, asset_type)
            hint = _format_group_hint(asset)
            print(
                f"[PROCESS] {type_label:<20} {label:<50}  ({hint})"
            )

            try:
                handler(asset)
                self._state.mark_processed(asset)
                self._state.save()
                processed_count += 1
            except Exception as exc:  # noqa: BLE001
                errors.append({"id": asset_id, "error": str(exc)})
                print(f"[ERROR]   {asset_id}: {exc}")

        finished_at = datetime.now(timezone.utc).isoformat()

        report = {
            "scanned": len(all_assets),
            "stale": len(stale),
            "processed": processed_count,
            "skipped": skipped_count,
            "errors": errors,
            "started_at": started_at,
            "finished_at": finished_at,
        }

        print(
            f"[DONE]    Processed {processed_count} assets  "
            f"Skipped {skipped_count}  "
            f"Errors {len(errors)}"
        )

        return report

    # ------------------------------------------------------------------
    # Convenience: dry-run (scan only, no processing)
    # ------------------------------------------------------------------

    def dry_run(self) -> Dict:
        """Scan assets and report what would be processed, without calling handlers."""
        print("[DRY-RUN] Scanning all assets...")
        all_assets = self._scanner.scan_all_assets()
        stale = self._state.stale_assets(all_assets)

        by_type: Dict[str, int] = {}
        for asset in stale:
            atype = asset.get("type", "unknown")
            by_type[atype] = by_type.get(atype, 0) + 1

        print(f"[DRY-RUN] Total assets : {len(all_assets)}")
        print(f"[DRY-RUN] Stale assets : {len(stale)}")
        for atype, count in sorted(by_type.items()):
            print(f"[DRY-RUN]   {atype:<25} {count}")

        return {
            "scanned": len(all_assets),
            "stale": len(stale),
            "stale_by_type": by_type,
        }
