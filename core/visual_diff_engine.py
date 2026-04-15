"""visual_diff_engine.py — WAVE 9: Visual Intelligence Layer.

RULE-VISUAL-DIFF-ENGINE (ARCHITECT DECISION 2026-04-15)
=======================================================
When a cache-miss occurs, the diff engine analyses WHY the image changed.
It does NOT replace the validation decision — it adds intelligence on top.

Core question: "What changed, and is it important?"

Output model
------------
VisualDiffReport captures:
  - change_type:      TEXT | LAYOUT | VISUAL | COMPONENT | UNKNOWN | NONE
  - severity:         none | low | medium | high
  - confidence:       0.0–1.0
  - affected_regions: list of bounding boxes with pixel delta stats
  - requires_attention: True if human review recommended

Classification logic
--------------------
  NONE       → no significant pixel delta (below noise floor)
  TEXT       → semantic_sha256 changed, dependency_sha256 stable
  COMPONENT  → dependency_sha256 changed (code-driven visual change)
  LAYOUT     → large pixel delta (>= LAYOUT_THRESHOLD), no semantic/dep signal
  VISUAL     → small/medium pixel delta, no semantic/dep signal (color/font/spacing)
  UNKNOWN    → unclassifiable (missing data, contradictory signals)

Noise floor
-----------
- Per-pixel: delta < PIXEL_NOISE_THRESHOLD (default 12) → noise
- Per-region: changed_pixel_pct < REGION_NOISE_THRESHOLD (default 0.5%) → noise
  This eliminates font anti-aliasing, subpixel rendering, JPEG artifacts.

Region detection
----------------
1. Compute per-pixel luminance delta
2. Apply noise floor
3. Divide canvas into NxM grid cells
4. For each cell: compute changed_pixel_pct
5. Merge adjacent "hot" cells into bounding boxes (AffectedRegion)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageChops, ImageFilter
    _PIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PIL_AVAILABLE = False

from core.visual_fingerprint import NormalizationConfig, DEFAULT_NORMALIZATION, hash_normalized_image


# ---------------------------------------------------------------------------
# Thresholds — Architect may tune these per project
# ---------------------------------------------------------------------------

#: Per-pixel luminance delta below which a pixel is considered noise.
PIXEL_NOISE_THRESHOLD: int = 12        # out of 255

#: Fraction of changed pixels in a grid cell below which the cell is noise.
REGION_NOISE_THRESHOLD: float = 0.005  # 0.5 %

#: Fraction of total canvas area changed — above this = LAYOUT change.
LAYOUT_THRESHOLD: float = 0.05         # 5 %

#: Fraction of total canvas area changed — above this = HIGH severity.
HIGH_SEVERITY_THRESHOLD: float = 0.20  # 20 %

#: Fraction of total canvas area changed — above this = MEDIUM severity.
MEDIUM_SEVERITY_THRESHOLD: float = 0.03  # 3 %

#: Grid cell dimensions (pixels) for region detection.
GRID_CELL_SIZE: int = 32


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

@dataclass
class AffectedRegion:
    """A bounding box where pixel changes were detected.

    Coordinates are in canvas pixels (post-normalization).
    """
    x: int
    y: int
    width: int
    height: int
    pixel_delta_pct: float  # 0.0–1.0: fraction of pixels changed in this region
    mean_delta: float       # 0–255: average pixel value delta in this region
    label: str = ""         # positional hint: "top-left", "center", etc.

    def area(self) -> int:
        return self.width * self.height

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "pixelDeltaPct": round(self.pixel_delta_pct, 4),
            "meanDelta": round(self.mean_delta, 2),
            "label": self.label,
        }


@dataclass
class VisualDiffReport:
    """Full diff result for one screen comparison.

    Architect interface (WAVE 9):
    {
      "was_cached": false,
      "change_detected": true,
      "change_summary": "...",
      "change_type": "TEXT | LAYOUT | VISUAL | COMPONENT | UNKNOWN | NONE",
      "affected_regions": [...],
      "requires_attention": true/false,
      "severity": "none | low | medium | high",
      "confidence": 0.0–1.0,
    }
    """
    was_cached: bool
    change_detected: bool
    change_type: str          # TEXT | LAYOUT | VISUAL | COMPONENT | UNKNOWN | NONE
    severity: str             # none | low | medium | high
    confidence: float         # 0.0–1.0
    change_summary: str
    affected_regions: list[AffectedRegion]
    requires_attention: bool
    pixel_change_pct: float   # global fraction of canvas changed (0.0–1.0)
    semantic_changed: bool    # semantic_sha256 differed
    dependency_changed: bool  # dependency_sha256 differed

    def to_dict(self) -> dict:
        return {
            "wasCached": self.was_cached,
            "changeDetected": self.change_detected,
            "changeType": self.change_type,
            "severity": self.severity,
            "confidence": round(self.confidence, 3),
            "changeSummary": self.change_summary,
            "affectedRegions": [r.to_dict() for r in self.affected_regions],
            "requiresAttention": self.requires_attention,
            "pixelChangePct": round(self.pixel_change_pct, 4),
            "semanticChanged": self.semantic_changed,
            "dependencyChanged": self.dependency_changed,
        }

    @staticmethod
    def no_change() -> "VisualDiffReport":
        """Convenience factory — no visual change detected."""
        return VisualDiffReport(
            was_cached=True,
            change_detected=False,
            change_type="NONE",
            severity="none",
            confidence=1.0,
            change_summary="No significant visual change detected.",
            affected_regions=[],
            requires_attention=False,
            pixel_change_pct=0.0,
            semantic_changed=False,
            dependency_changed=False,
        )

    @staticmethod
    def unavailable(reason: str) -> "VisualDiffReport":
        """Fallback when diff cannot be computed (e.g. no prior image)."""
        return VisualDiffReport(
            was_cached=False,
            change_detected=True,
            change_type="UNKNOWN",
            severity="low",
            confidence=0.0,
            change_summary=f"Diff unavailable: {reason}",
            affected_regions=[],
            requires_attention=False,
            pixel_change_pct=0.0,
            semantic_changed=False,
            dependency_changed=False,
        )


# ---------------------------------------------------------------------------
# Core diff engine
# ---------------------------------------------------------------------------

class VisualDiffEngine:
    """Compares two screenshots and explains the differences.

    Usage::

        engine = VisualDiffEngine()
        report = engine.compare(
            image_a=path_before,
            image_b=path_after,
            semantic_sha_a="...",
            semantic_sha_b="...",
            dependency_sha_a="...",
            dependency_sha_b="...",
        )
    """

    def __init__(
        self,
        normalization_config: Optional[NormalizationConfig] = None,
        pixel_noise_threshold: int = PIXEL_NOISE_THRESHOLD,
        region_noise_threshold: float = REGION_NOISE_THRESHOLD,
        layout_threshold: float = LAYOUT_THRESHOLD,
        grid_cell_size: int = GRID_CELL_SIZE,
    ) -> None:
        self._config = normalization_config or DEFAULT_NORMALIZATION
        self._pixel_noise = pixel_noise_threshold
        self._region_noise = region_noise_threshold
        self._layout_threshold = layout_threshold
        self._cell_size = grid_cell_size

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compare(
        self,
        image_a: Path,
        image_b: Path,
        *,
        semantic_sha_a: str = "",
        semantic_sha_b: str = "",
        dependency_sha_a: str = "",
        dependency_sha_b: str = "",
    ) -> VisualDiffReport:
        """Compare two screenshots and produce a VisualDiffReport.

        Args:
            image_a: Reference image (prior PASS screenshot).
            image_b: Current image (new screenshot to validate).
            semantic_sha_a/b: SHA256 of DOM/text content — from VisualFingerprint.
            dependency_sha_a/b: SHA256 of dependency manifest — from VisualFingerprint.

        Returns:
            VisualDiffReport with classification, severity, and affected regions.
        """
        if not _PIL_AVAILABLE:
            return VisualDiffReport.unavailable("Pillow not installed")

        semantic_changed = (
            bool(semantic_sha_a) and bool(semantic_sha_b)
            and semantic_sha_a != semantic_sha_b
        )
        dependency_changed = (
            bool(dependency_sha_a) and bool(dependency_sha_b)
            and dependency_sha_a != dependency_sha_b
        )

        try:
            img_a = self._load_normalized(image_a)
            img_b = self._load_normalized(image_b)
        except Exception as exc:
            return VisualDiffReport.unavailable(f"Could not load images: {exc}")

        # Ensure same canvas (should always be true after normalization)
        if img_a.size != img_b.size:
            img_b = img_b.resize(img_a.size, Image.LANCZOS)

        # Pixel-level diff
        diff_img = ImageChops.difference(img_a, img_b)
        gray_diff = diff_img.convert("L")

        pixels = list(gray_diff.tobytes())
        canvas_w, canvas_h = img_a.size
        total_pixels = canvas_w * canvas_h

        # Apply noise floor
        significant = [p for p in pixels if p >= self._pixel_noise]
        pixel_change_pct = len(significant) / total_pixels if total_pixels > 0 else 0.0

        # No significant change
        if pixel_change_pct == 0.0:
            report = VisualDiffReport.no_change()
            report.was_cached = False
            report.semantic_changed = semantic_changed
            report.dependency_changed = dependency_changed
            if dependency_changed:
                report.change_detected = True
                report.change_type = "COMPONENT"
                report.severity = "low"
                report.confidence = 0.85
                report.change_summary = (
                    "Dependency change detected without visible pixel difference. "
                    "Component code changed but visual output appears identical."
                )
                report.requires_attention = True
            return report

        # Detect regions
        regions = self._detect_regions(gray_diff, canvas_w, canvas_h)

        # Classify
        change_type, confidence = self._classify(
            pixel_change_pct=pixel_change_pct,
            semantic_changed=semantic_changed,
            dependency_changed=dependency_changed,
        )

        # Severity
        severity = self._severity(pixel_change_pct)

        # Summary
        summary = self._summarize(change_type, pixel_change_pct, regions, semantic_changed, dependency_changed)

        # requires_attention
        requires_attention = (
            severity in ("high", "medium")
            or semantic_changed
            or (dependency_changed and pixel_change_pct > 0.0)
        )

        return VisualDiffReport(
            was_cached=False,
            change_detected=True,
            change_type=change_type,
            severity=severity,
            confidence=confidence,
            change_summary=summary,
            affected_regions=regions,
            requires_attention=requires_attention,
            pixel_change_pct=pixel_change_pct,
            semantic_changed=semantic_changed,
            dependency_changed=dependency_changed,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_normalized(self, path: Path) -> "Image.Image":
        """Load and normalize to canonical canvas."""
        img = Image.open(path)
        img = img.resize(self._config.canvas_size, Image.LANCZOS)
        img = img.convert("RGB")
        return img

    def _detect_regions(
        self,
        gray_diff: "Image.Image",
        canvas_w: int,
        canvas_h: int,
    ) -> list[AffectedRegion]:
        """Grid-based region detection.

        1. Divide canvas into GRID_CELL_SIZE×GRID_CELL_SIZE cells.
        2. For each cell: compute fraction of pixels above noise floor.
        3. Mark cell as "hot" if fraction > REGION_NOISE_THRESHOLD.
        4. Merge adjacent hot cells into bounding boxes.
        """
        cell = self._cell_size
        cols = (canvas_w + cell - 1) // cell
        rows = (canvas_h + cell - 1) // cell

        hot: list[list[bool]] = [[False] * cols for _ in range(rows)]

        for row in range(rows):
            for col in range(cols):
                x0 = col * cell
                y0 = row * cell
                x1 = min(x0 + cell, canvas_w)
                y1 = min(y0 + cell, canvas_h)

                cell_img = gray_diff.crop((x0, y0, x1, y1))
                cell_pixels = list(cell_img.tobytes())
                cell_total = len(cell_pixels)
                if cell_total == 0:
                    continue

                changed = sum(1 for p in cell_pixels if p >= self._pixel_noise)
                if changed / cell_total > self._region_noise:
                    hot[row][col] = True

        return self._merge_hot_cells(hot, rows, cols, canvas_w, canvas_h, gray_diff)

    def _merge_hot_cells(
        self,
        hot: list[list[bool]],
        rows: int,
        cols: int,
        canvas_w: int,
        canvas_h: int,
        gray_diff: "Image.Image",
    ) -> list[AffectedRegion]:
        """Flood-fill merge of adjacent hot grid cells into AffectedRegion bounding boxes."""
        visited = [[False] * cols for _ in range(rows)]
        regions: list[AffectedRegion] = []
        cell = self._cell_size

        def _flood(start_r: int, start_c: int) -> tuple[int, int, int, int]:
            """BFS flood fill — returns (min_row, min_col, max_row, max_col)."""
            queue = [(start_r, start_c)]
            visited[start_r][start_c] = True
            min_r, min_c, max_r, max_c = start_r, start_c, start_r, start_c

            while queue:
                r, c = queue.pop(0)
                if r < min_r: min_r = r
                if r > max_r: max_r = r
                if c < min_c: min_c = c
                if c > max_c: max_c = c

                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc] and hot[nr][nc]:
                        visited[nr][nc] = True
                        queue.append((nr, nc))

            return min_r, min_c, max_r, max_c

        for row in range(rows):
            for col in range(cols):
                if hot[row][col] and not visited[row][col]:
                    min_r, min_c, max_r, max_c = _flood(row, col)

                    x0 = min_c * cell
                    y0 = min_r * cell
                    x1 = min(max_c * cell + cell, canvas_w)
                    y1 = min(max_r * cell + cell, canvas_h)

                    region_img = gray_diff.crop((x0, y0, x1, y1))
                    region_pixels = list(region_img.tobytes())
                    region_total = len(region_pixels)

                    if region_total == 0:
                        continue

                    above_noise = [p for p in region_pixels if p >= self._pixel_noise]
                    pct = len(above_noise) / region_total
                    mean = sum(above_noise) / len(above_noise) if above_noise else 0.0

                    label = _position_label(x0, y0, x1 - x0, y1 - y0, canvas_w, canvas_h)
                    regions.append(AffectedRegion(
                        x=x0, y=y0,
                        width=x1 - x0,
                        height=y1 - y0,
                        pixel_delta_pct=round(pct, 4),
                        mean_delta=round(mean, 2),
                        label=label,
                    ))

        # Sort by area descending (largest changes first)
        regions.sort(key=lambda r: r.area(), reverse=True)
        return regions

    def _classify(
        self,
        *,
        pixel_change_pct: float,
        semantic_changed: bool,
        dependency_changed: bool,
    ) -> tuple[str, float]:
        """Returns (change_type, confidence)."""

        # TEXT: text/DOM changed, source code stable
        if semantic_changed and not dependency_changed:
            return "TEXT", 0.90

        # COMPONENT: source dependency changed
        if dependency_changed:
            # Dependency changed + visible pixels → confirmed component change
            conf = 0.88 if pixel_change_pct > 0.0 else 0.75
            return "COMPONENT", conf

        # LAYOUT: large structural shift (no semantic/dep signal)
        if pixel_change_pct >= self._layout_threshold:
            return "LAYOUT", 0.80

        # VISUAL: small change (color, font, spacing)
        if pixel_change_pct > 0.0:
            return "VISUAL", 0.75

        return "UNKNOWN", 0.40

    def _severity(self, pixel_change_pct: float) -> str:
        if pixel_change_pct >= HIGH_SEVERITY_THRESHOLD:
            return "high"
        if pixel_change_pct >= MEDIUM_SEVERITY_THRESHOLD:
            return "medium"
        if pixel_change_pct > 0.0:
            return "low"
        return "none"

    def _summarize(
        self,
        change_type: str,
        pixel_change_pct: float,
        regions: list[AffectedRegion],
        semantic_changed: bool,
        dependency_changed: bool,
    ) -> str:
        pct_str = f"{pixel_change_pct * 100:.1f}%"
        region_count = len(regions)

        summaries = {
            "TEXT": (
                f"Text/content change detected ({pct_str} of canvas, "
                f"{region_count} region(s)). DOM/text hash changed; "
                "component source unchanged."
            ),
            "LAYOUT": (
                f"Layout change detected ({pct_str} of canvas, "
                f"{region_count} region(s)). Large structural shift — "
                "elements may have moved or been added/removed."
            ),
            "VISUAL": (
                f"Visual style change detected ({pct_str} of canvas, "
                f"{region_count} region(s)). Color, font, or spacing "
                "change likely."
            ),
            "COMPONENT": (
                f"Component code change detected ({pct_str} of canvas, "
                f"{region_count} region(s)). Dependency hash changed."
            ),
            "UNKNOWN": (
                f"Change detected ({pct_str} of canvas, {region_count} region(s)) "
                "but could not be classified. Manual review recommended."
            ),
        }
        return summaries.get(change_type, f"Change detected: {pct_str}")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _position_label(x: int, y: int, w: int, h: int, canvas_w: int, canvas_h: int) -> str:
    """Assign a positional hint string to a region."""
    cx = x + w / 2
    cy = y + h / 2
    thirds_x = canvas_w / 3
    thirds_y = canvas_h / 3

    v = "top" if cy < thirds_y else ("bottom" if cy > 2 * thirds_y else "center")
    hh = "left" if cx < thirds_x else ("right" if cx > 2 * thirds_x else "middle")

    if v == "center" and hh == "middle":
        return "center"
    if v == "center":
        return hh
    if hh == "middle":
        return v
    return f"{v}-{hh}"
