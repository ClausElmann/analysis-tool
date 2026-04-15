"""visual_delta_export.py — Delta exporter for external AI analysis.

RULE-VISUAL-DELTA-CACHE (ARCHITECT DECISION 2026-04-14)
========================================================
Pipeline:
  1. Run screenshots
  2. Calculate fingerprints
  3. Compare with validated registry
  4. Export ONLY unseen / invalidated fingerprints
  5. External AI analyses only the delta
  6. Merge PASS / FAIL results back into registry

This module handles steps 4-6.

Usage example::

    from pathlib import Path
    from core.visual_fingerprint import VisualFingerprintBuilder, ValidationContext
    from core.visual_delta_cache import VisualDeltaCache, DeltaMode
    from core.visual_delta_export import VisualDeltaExporter

    cache = VisualDeltaCache(data_root="data")
    exporter = VisualDeltaExporter(cache, output_dir="output/visual-delta")

    # Build fingerprints for this run's screenshots
    builder = VisualFingerprintBuilder()
    fingerprints = [
        builder.build(
            screenshot_path=path,
            context=ValidationContext(screen_key=key, device="desktop", locale="da-DK"),
        )
        for key, path in screenshots.items()
    ]

    # Export only the delta
    manifest = exporter.export(fingerprints, mode="STRICT", build_id="GA-2026-...")

    # ... send manifest["zip_path"] to external AI ...

    # Merge results back
    exporter.merge_results(manifest["manifest_path"], results_jsonl_path="ai_results.jsonl")
"""

from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from core.visual_delta_cache import DeltaMode, VisualDeltaCache
from core.visual_fingerprint import VisualFingerprint


class VisualDeltaExporter:
    """Builds delta ZIP packages for external AI analysis and merges results.

    Parameters
    ----------
    cache:
        The VisualDeltaCache instance to query for prior PASSes.
    output_dir:
        Directory where export ZIPs and manifests will be written.
    """

    def __init__(self, cache: VisualDeltaCache, output_dir: str | Path = "output/visual-delta") -> None:
        self._cache = cache
        self._output_dir = Path(output_dir)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(
        self,
        fingerprints: List[VisualFingerprint],
        *,
        screenshot_paths: Optional[Dict[str, str]] = None,
        mode: DeltaMode = "STRICT",
        build_id: str = "",
        wave: str = "",
    ) -> dict:
        """Export a ZIP of screenshots that need (re)analysis.

        Parameters
        ----------
        fingerprints:
            All fingerprints for the current run (not pre-filtered).
        screenshot_paths:
            Optional mapping of screen_key → file path.
            If provided, matching PNG files are bundled in the ZIP.
        mode:
            FAST or STRICT delta mode.
        build_id:
            Stamped in the manifest for traceability.
        wave:
            Stamped in the manifest for traceability.

        Returns
        -------
        dict with keys:
            ``zip_path``        — path to the generated ZIP (or None if nothing to export)
            ``manifest_path``   — path to the manifest JSONL
            ``delta_count``     — number of fingerprints in the delta
            ``total_count``     — total input fingerprints
            ``skipped_count``   — fingerprints skipped (prior PASS matches)
        """
        screenshot_paths = screenshot_paths or {}

        # Determine delta
        delta = self._cache.get_unseen_or_invalidated(fingerprints, mode=mode)
        skipped = [fp for fp in fingerprints if fp not in delta]

        self._output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        # Build manifest
        manifest_entries = []
        for fp in delta:
            manifest_entries.append({
                "screenKey":                   fp.screen_key,
                "imageSha256":                 fp.image_sha256,
                "normalizedImageSha256":       fp.normalized_image_sha256,
                "validationContextSha256":     fp.validation_context_sha256,
                "renderInputSha256":           fp.render_input_sha256,
                "validationFingerprintSha256": fp.validation_fingerprint_sha256,
                "policyVersion":               fp.policy_version,
                "screenshotFile":              screenshot_paths.get(fp.screen_key, ""),
                "exportedAtUtc":               datetime.now(timezone.utc).isoformat(),
                "buildId":                     build_id,
                "wave":                        wave,
            })

        manifest_path = self._output_dir / f"delta_manifest_{timestamp}.jsonl"
        with open(manifest_path, "w", encoding="utf-8") as fh:
            for entry in manifest_entries:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Build ZIP if there are screenshots to bundle
        zip_path = None
        if delta and screenshot_paths:
            zip_path = self._output_dir / f"delta_{timestamp}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Manifest inside zip
                zf.writestr("manifest.jsonl", manifest_path.read_text(encoding="utf-8"))
                # Screenshots
                for fp in delta:
                    src = screenshot_paths.get(fp.screen_key)
                    if src and Path(src).is_file():
                        zf.write(src, arcname=f"screenshots/{fp.screen_key}{Path(src).suffix}")

        return {
            "zip_path":      str(zip_path) if zip_path else None,
            "manifest_path": str(manifest_path),
            "delta_count":   len(delta),
            "total_count":   len(fingerprints),
            "skipped_count": len(skipped),
            "skipped_keys":  [fp.screen_key for fp in skipped],
        }

    # ------------------------------------------------------------------
    # Merge results
    # ------------------------------------------------------------------

    def merge_results(
        self,
        results_source: str | Path | List[dict],
        *,
        fingerprints_by_key: Optional[Dict[str, VisualFingerprint]] = None,
        validated_by: str = "ai-visual-loop",
        wave: str = "",
        build_id: str = "",
    ) -> dict:
        """Merge AI analysis results back into the registry.

        Parameters
        ----------
        results_source:
            Either a path to a JSONL file containing result dicts,
            or a plain list of result dicts.
            Each dict must have:
              ``screenKey``  (str)
              ``result``     ("PASS" or "FAIL")
            Optional:
              ``screenshotPath``, ``failuresPath``, ``analysisZipPath``
        fingerprints_by_key:
            Mapping of screen_key → VisualFingerprint from the current run.
            Required if the result records don't carry full hash fields.
        validated_by:
            Label recorded in the registry (e.g. "ai-visual-loop", "manual").
        wave:
            Wave label.
        build_id:
            Build / session token for traceability.

        Returns
        -------
        dict with ``pass_count``, ``fail_count``, ``unknown_count``
        """
        fingerprints_by_key = fingerprints_by_key or {}
        results = self._load_results(results_source)

        pass_count = fail_count = unknown_count = 0

        for r in results:
            screen_key = r.get("screenKey", "")
            result_val = r.get("result", "").upper()
            fp = fingerprints_by_key.get(screen_key)

            if fp is None or result_val not in ("PASS", "FAIL"):
                unknown_count += 1
                continue

            kwargs = dict(
                validated_by=validated_by,
                wave=wave,
                build_id=build_id,
                screenshot_path=r.get("screenshotPath", ""),
                device=r.get("device", ""),
            )

            if result_val == "PASS":
                self._cache.record_pass(fp, analysis_zip_path=r.get("analysisZipPath"), **kwargs)
                pass_count += 1
            else:
                self._cache.record_fail(fp, failures_path=r.get("failuresPath"), **kwargs)
                fail_count += 1

        return {
            "pass_count":    pass_count,
            "fail_count":    fail_count,
            "unknown_count": unknown_count,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_results(source: str | Path | List[dict]) -> List[dict]:
        if isinstance(source, list):
            return source
        path = Path(source)
        results: List[dict] = []
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return results
