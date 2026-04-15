"""visual_delta_cache.py — PASS-only validation registry.

RULE-VISUAL-DELTA-CACHE (ARCHITECT DECISION 2026-04-14)
========================================================
Registry for validated visual screenshots.  Only PASS results are cacheable.
FAIL results are NEVER used to skip analysis.

Storage
-------
Append-only JSONL file: ``data/visual_validation_registry.jsonl``
Each line is one complete validation record (see VisualCacheEntry).

Skip rules
----------
FAST mode (daily runs):
  skip = image_sha256 matches prior PASS
       AND validation_context_sha256 matches prior PASS

STRICT mode (wave checkpoints / releases / audits):
  skip = image_sha256 matches prior PASS
       AND validation_context_sha256 matches prior PASS
       AND render_input_sha256 matches prior PASS
       AND policy_version matches prior PASS

A FAIL entry with an identical fingerprint is NEVER a skip — it forces re-run.

Invalidation
------------
Any of the following changes forces re-analysis:
  - quality gates changed
  - mustShow / mustNotShow changed
  - device matrix changed
  - localization resources changed
  - CSS / design tokens changed
  - seed scenario changed
  - auth role / scenario changed
  - VISUAL_VALIDATION_POLICY_VERSION bumped

These are encoded in validation_context_sha256 and render_input_sha256,
so the composite fingerprint changes automatically.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional

from core.visual_fingerprint import (
    DependencyManifest,
    FingerprintValidationError,
    VisualFingerprint,
    VISUAL_VALIDATION_POLICY_VERSION,
    phash_similarity,
    validate_fingerprint,
)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

ValidationType = Literal["PASS", "FAIL", "PENDING"]
DeltaMode = Literal["FAST", "STRICT"]


# ---------------------------------------------------------------------------
# Cache entry
# ---------------------------------------------------------------------------

class VisualCacheEntry:
    """One row in the validation registry."""

    def __init__(self, data: dict) -> None:
        self._d = data

    # --- identity ---
    @property
    def screen_key(self) -> str:                      return self._d["screenKey"]
    @property
    def device(self) -> str:                          return self._d.get("device", "")
    @property
    def image_sha256(self) -> str:                    return self._d["imageSha256"]
    @property
    def normalized_image_sha256(self) -> str:         return self._d["normalizedImageSha256"]
    @property
    def validation_context_sha256(self) -> str:       return self._d["validationContextSha256"]
    @property
    def render_input_sha256(self) -> str:             return self._d["renderInputSha256"]
    @property
    def validation_fingerprint_sha256(self) -> str:   return self._d["validationFingerprintSha256"]
    @property
    def policy_version(self) -> str:                  return self._d.get("policyVersion", "")

    # --- result ---
    @property
    def result(self) -> ValidationType:               return self._d["result"]
    @property
    def is_pass(self) -> bool:                        return self.result == "PASS"

    # --- 3-layer fields ---
    @property
    def perceptual_hash(self) -> str:                 return self._d.get("perceptualHash", "")
    @property
    def semantic_sha256(self) -> str:                 return self._d.get("semanticSha256", "")

    # --- RULE-VISUAL-DELTA-ENGINE v2 ---
    @property
    def dependency_sha256(self) -> str:               return self._d.get("dependencySha256", "")
    @property
    def validator_version(self) -> str:               return self._d.get("validatorVersion", "")
    @property
    def ruleset_version(self) -> str:                 return self._d.get("ruleSetVersion", "")
    @property
    def mask_version(self) -> str:                    return self._d.get("maskVersion", "")
    @property
    def source_commit_sha(self) -> str:               return self._d.get("sourceCommitSha", "")
    @property
    def dependency_source(self) -> str:               return self._d.get("dependencySource", "MANUAL")

    # --- metadata ---
    @property
    def validated_at_utc(self) -> str:                return self._d.get("validatedAtUtc", "")
    @property
    def validated_by(self) -> str:                    return self._d.get("validatedBy", "")
    @property
    def wave(self) -> str:                            return self._d.get("wave", "")
    @property
    def build_id(self) -> str:                        return self._d.get("buildId", "")
    @property
    def artifacts(self) -> dict:                      return self._d.get("artifacts", {})

    def to_dict(self) -> dict:
        return dict(self._d)


def _make_entry(
    fingerprint: VisualFingerprint,
    result: ValidationType,
    *,
    validated_by: str = "ai-visual-loop",
    wave: str = "",
    build_id: str = "",
    screenshot_path: str = "",
    failures_path: Optional[str] = None,
    analysis_zip_path: Optional[str] = None,
    device: str = "",
) -> VisualCacheEntry:
    """Create a new VisualCacheEntry from a fingerprint + result."""
    return VisualCacheEntry({
        "screenKey":                   fingerprint.screen_key,
        "device":                      device,
        "imageSha256":                 fingerprint.image_sha256,
        "normalizedImageSha256":       fingerprint.normalized_image_sha256,
        "validationContextSha256":     fingerprint.validation_context_sha256,
        "renderInputSha256":           fingerprint.render_input_sha256,
        "validationFingerprintSha256": fingerprint.validation_fingerprint_sha256,
        "policyVersion":               fingerprint.policy_version,
        "perceptualHash":              fingerprint.perceptual_hash,
        "semanticSha256":              fingerprint.semantic_sha256,
        # RULE-VISUAL-DELTA-ENGINE v2
        "dependencySha256":            fingerprint.dependency_sha256,
        "validatorVersion":            fingerprint.validator_version,
        "ruleSetVersion":              fingerprint.ruleset_version,
        "maskVersion":                 fingerprint.mask_version,
        "sourceCommitSha":             fingerprint.source_commit_sha,
        "dependencySource":            "MANUAL",
        "validatedAtUtc":              datetime.now(timezone.utc).isoformat(),
        "validatedBy":                 validated_by,
        "result":                      result,
        "wave":                        wave,
        "buildId":                     build_id,
        "artifacts": {
            "screenshotPath":   screenshot_path,
            "failuresPath":     failures_path,
            "analysisZipPath":  analysis_zip_path,
        },
    })


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class VisualDeltaCache:
    """Read/write the visual validation registry (append-only JSONL).

    Parameters
    ----------
    data_root:
        Directory that contains (or will contain) the JSONL registry file.
    filename:
        Override the default registry filename.
    """

    _FILENAME = "visual_validation_registry.jsonl"

    def __init__(
        self,
        data_root: str | Path,
        filename: Optional[str] = None,
        production_mode: bool = False,
    ) -> None:
        """Initialise the registry.

        Parameters
        ----------
        production_mode:
            When True, empty v2 fields (semantic/dependency/validator/ruleset/mask)
            in a fingerprint are treated as MISSING and ALWAYS force re-analysis
            (no "\"\" = any" relaxation).  This prevents silent skips in production.
            When False (default / test / migration), empty fields are skipped-over
            for backward compatibility.
        """
        self._data_root = Path(data_root)
        self._path = self._data_root / (filename or self._FILENAME)
        self._production_mode = production_mode
        self._entries: List[VisualCacheEntry] = self._load()

    # ------------------------------------------------------------------
    # Core skip logic
    # ------------------------------------------------------------------

    def should_skip(
        self,
        fingerprint: VisualFingerprint,
        mode: DeltaMode = "FAST",
    ) -> bool:
        """3-layer Decision Engine — RULE-VISUAL-DELTA-01/02/03.

        RULE-VISUAL-DELTA-01 (EXACT SKIP):
            Same image_sha256 + context_sha256 as a prior PASS:
            - FAST mode  → skip immediately (render inputs not checked).
            - STRICT mode → fall through to render-input check.

        RULE-VISUAL-DELTA-03 (STRUCTURAL CHANGE):
            Image/context differs AND semantic content changed vs. prior PASS
            → always re-analyze (overrides pHash similarity).
            Only activates when both fingerprints carry non-empty semantic data.

        RULE-VISUAL-DELTA-02 (SEMANTIC STABILITY):
            Image/context differs AND pHash similarity >= 95% AND semantic
            content unchanged → skip.
            Only activates when both fingerprints carry perceptual + semantic data.

        STRICT fallback:
            normalized_image + context + render_inputs + policy_version all match.

        A prior FAIL is NEVER used to skip analysis.
        """
        prior_pass = self._find_pass(fingerprint.screen_key, fingerprint.validation_context_sha256)
        if prior_pass is None:
            return False

        exact_image   = prior_pass.image_sha256 == fingerprint.image_sha256
        exact_context = prior_pass.validation_context_sha256 == fingerprint.validation_context_sha256

        # RULE-VISUAL-DELTA-01: Exact image + context match.
        if exact_image and exact_context:
            if mode == "FAST":
                return True
            # STRICT: fall through to render-input check below.
        else:
            # Image or context differs — evaluate pHash path.

            # RULE-VISUAL-DELTA-03: Semantic change → always re-analyze.
            # Requires non-empty semantic data on both to activate.
            if fingerprint.semantic_sha256 and prior_pass.semantic_sha256:
                if fingerprint.semantic_sha256 != prior_pass.semantic_sha256:
                    return False

            # RULE-VISUAL-DELTA-02: High pHash + same semantic → skip.
            # Requires non-empty perceptual + semantic data on both to activate.
            if (fingerprint.perceptual_hash and prior_pass.perceptual_hash
                    and fingerprint.semantic_sha256 and prior_pass.semantic_sha256):
                similarity = phash_similarity(
                    fingerprint.perceptual_hash, prior_pass.perceptual_hash
                )
                if similarity >= 0.95:
                    return True

            # pHash path did not cover this case.
            # FAST: image or context changed with no pHash coverage → re-analyze.
            if mode == "FAST":
                return False

        # STRICT fallback — RULE-VISUAL-DELTA-ENGINE v2:
        # ALL conditions must be true to skip.
        #
        # production_mode=True  ("": ARCHITECT RULE) — empty field = MISSING = force reanalysis
        # production_mode=False (default/test/migration) — empty = "any" (backward-compat)
        canonical_visual_match = (
            prior_pass.normalized_image_sha256 == fingerprint.normalized_image_sha256
        )
        context_match = (
            prior_pass.validation_context_sha256 == fingerprint.validation_context_sha256
        )
        render_match = (
            prior_pass.render_input_sha256 == fingerprint.render_input_sha256
        )
        policy_match = prior_pass.policy_version == fingerprint.policy_version

        def _v2_match(fp_val: str, prior_val: str) -> bool:
            if self._production_mode:
                # Empty = missing = force reanalysis
                if not fp_val:
                    return False
                return prior_val == fp_val
            # Test/migration mode: empty = any
            return not fp_val or prior_val == fp_val

        semantic_match    = _v2_match(fingerprint.semantic_sha256,    prior_pass.semantic_sha256)
        dependency_match  = _v2_match(fingerprint.dependency_sha256,  prior_pass.dependency_sha256)
        validator_match   = _v2_match(fingerprint.validator_version,  prior_pass.validator_version)
        ruleset_match     = _v2_match(fingerprint.ruleset_version,    prior_pass.ruleset_version)
        mask_match        = _v2_match(fingerprint.mask_version,       prior_pass.mask_version)

        return (
            canonical_visual_match
            and context_match
            and render_match
            and policy_match
            and semantic_match
            and dependency_match
            and validator_match
            and ruleset_match
            and mask_match
        )

    def should_skip_strict(self, fingerprint: VisualFingerprint) -> bool:
        """Convenience wrapper for STRICT mode."""
        return self.should_skip(fingerprint, mode="STRICT")

    # ------------------------------------------------------------------
    # Recording results
    # ------------------------------------------------------------------

    def record_pass(
        self,
        fingerprint: VisualFingerprint,
        *,
        validated_by: str = "ai-visual-loop",
        wave: str = "",
        build_id: str = "",
        screenshot_path: str = "",
        analysis_zip_path: Optional[str] = None,
        device: str = "",
    ) -> VisualCacheEntry:
        """Record a PASS result and persist to registry."""
        entry = _make_entry(
            fingerprint,
            "PASS",
            validated_by=validated_by,
            wave=wave,
            build_id=build_id,
            screenshot_path=screenshot_path,
            analysis_zip_path=analysis_zip_path,
            device=device,
        )
        self._append(entry)
        return entry

    def record_fail(
        self,
        fingerprint: VisualFingerprint,
        *,
        validated_by: str = "ai-visual-loop",
        wave: str = "",
        build_id: str = "",
        screenshot_path: str = "",
        failures_path: Optional[str] = None,
        device: str = "",
    ) -> VisualCacheEntry:
        """Record a FAIL result.

        FAIL entries are written to the registry for audit purposes
        but NEVER used to skip analysis.
        """
        entry = _make_entry(
            fingerprint,
            "FAIL",
            validated_by=validated_by,
            wave=wave,
            build_id=build_id,
            screenshot_path=screenshot_path,
            failures_path=failures_path,
            device=device,
        )
        self._append(entry)
        return entry

    # ------------------------------------------------------------------
    # Delta query — for external AI analysis export
    # ------------------------------------------------------------------

    def get_unseen_or_invalidated(
        self,
        candidates: List[VisualFingerprint],
        mode: DeltaMode = "STRICT",
    ) -> List[VisualFingerprint]:
        """Return fingerprints from *candidates* that need (re)analysis.

        A candidate needs analysis if:
          - it has never been validated (no matching PASS in registry), OR
          - its fingerprint does not match any prior PASS (hash mismatch), OR
          - the prior PASS was under a different policy version (STRICT).
        """
        return [fp for fp in candidates if not self.should_skip(fp, mode=mode)]

    # ------------------------------------------------------------------
    # Summary / introspection
    # ------------------------------------------------------------------

    def pass_count(self) -> int:
        return sum(1 for e in self._entries if e.is_pass)

    def fail_count(self) -> int:
        return sum(1 for e in self._entries if e.result == "FAIL")

    def total_count(self) -> int:
        return len(self._entries)

    def entries_for_screen(self, screen_key: str) -> List[VisualCacheEntry]:
        return [e for e in self._entries if e.screen_key == screen_key]

    def latest_pass_for_screen(self, screen_key: str) -> Optional[VisualCacheEntry]:
        """Return the most recently recorded PASS for *screen_key*, or None."""
        passes = [e for e in self._entries if e.screen_key == screen_key and e.is_pass]
        return passes[-1] if passes else None

    def summary(self) -> dict:
        return {
            "total": self.total_count(),
            "pass":  self.pass_count(),
            "fail":  self.fail_count(),
            "registry_path": str(self._path),
        }

    # ------------------------------------------------------------------
    # Invalidation
    # ------------------------------------------------------------------

    def invalidate_screen(self, screen_key: str) -> int:
        """Remove all entries for *screen_key* from the in-memory cache.

        Does NOT rewrite the JSONL file — the removed entries stay in the
        append-only log for audit purposes.  On next load, if you need them
        gone, use ``rebuild_from_entries`` after filtering.

        Returns the number of entries removed from the live index.
        """
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.screen_key != screen_key]
        return before - len(self._entries)

    def rebuild_registry(self, keep_only_latest_pass: bool = False) -> None:
        """Rewrite the JSONL file from the current in-memory entries.

        Use when you need to compact the log or remove invalidated entries.
        If *keep_only_latest_pass* is True, only the most recent PASS per
        screen_key + context_hash pair is retained.
        """
        entries = self._entries
        if keep_only_latest_pass:
            seen: Dict[str, VisualCacheEntry] = {}
            for e in entries:
                if e.is_pass:
                    key = e.screen_key + "|" + e.validation_context_sha256
                    seen[key] = e  # last writer wins (entries are chronological)
            entries = list(seen.values())
            self._entries = entries

        self._data_root.mkdir(parents=True, exist_ok=True)
        tmp = str(self._path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            for entry in entries:
                fh.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        os.replace(tmp, str(self._path))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _find_pass_by_image_sha256(
        self,
        image_sha256: str,
    ) -> Optional[VisualCacheEntry]:
        """RULE-VISUAL-DELTA-01: Find any PASS with exact image SHA256."""
        for entry in reversed(self._entries):
            if entry.is_pass and entry.image_sha256 == image_sha256:
                return entry
        return None

    def _find_pass(
        self,
        screen_key: str,
        context_sha256: str,
    ) -> Optional[VisualCacheEntry]:
        """Return the most recent PASS for this screen + context, or None."""
        result = None
        for e in self._entries:
            if e.screen_key == screen_key and e.is_pass:
                result = e  # keep last (most recent)
        return result

    def _append(self, entry: VisualCacheEntry) -> None:
        """Add to in-memory list and persist one line to the JSONL file."""
        self._entries.append(entry)
        self._data_root.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    def _load(self) -> List[VisualCacheEntry]:
        if not self._path.is_file():
            return []
        entries: List[VisualCacheEntry] = []
        with open(self._path, "r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(VisualCacheEntry(json.loads(line)))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"FAIL FAST: Corrupted visual validation registry "
                        f"at line {line_no}: {exc}"
                    ) from exc
        return entries
