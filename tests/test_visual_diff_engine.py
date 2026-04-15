"""tests/test_visual_diff_engine.py — WAVE 9: Visual Diff Engine tests.

RULE-VISUAL-DIFF-ENGINE (ARCHITECT DECISION 2026-04-15)
=======================================================
Tests cover all 5 Architect-mandated scenarios:
1. Layout change detected
2. Text change detected
3. No-change → no diff (noise floor)
4. Noise → ignored (subpixel shifts)
5. Dependency change without visual change

Plus:
- Visual (color) change detected
- Component change (dependency + visual)
- UNKNOWN fallback
- Region detection: bounding boxes, labels
- VisualDiffReport.to_dict() serialization
- compare_with_last() integration with VisualDeltaCache
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from core.visual_diff_engine import (
    AffectedRegion,
    VisualDiffEngine,
    VisualDiffReport,
    PIXEL_NOISE_THRESHOLD,
    REGION_NOISE_THRESHOLD,
    LAYOUT_THRESHOLD,
    _position_label,
)
from core.visual_fingerprint import (
    DependencyManifest,
    NormalizationConfig,
    SemanticContext,
    VisualFingerprintBuilder,
    ValidationContext,
    RenderInputs,
)
from core.visual_delta_cache import VisualDeltaCache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _solid_png(tmp_dir: Path, name: str, color: tuple, size=(100, 100)) -> Path:
    """Create a solid-color PNG."""
    from PIL import Image
    img = Image.new("RGB", size, color=color)
    path = tmp_dir / name
    img.save(str(path), format="PNG")
    return path


def _png_with_rect(tmp_dir: Path, name: str, bg=(255, 255, 255),
                   rect_color=(255, 0, 0), rect=(20, 20, 40, 40),
                   size=(100, 100)) -> Path:
    """Create a PNG with a solid background and a rectangle overlay."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", size, color=bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle(rect, fill=rect_color)
    path = tmp_dir / name
    img.save(str(path), format="PNG")
    return path


def _context(screen_key: str = "test-screen") -> ValidationContext:
    return ValidationContext(screen_key=screen_key, device="desktop", locale="da-DK")


def _render() -> RenderInputs:
    return RenderInputs(component_hash="ch-1", css_hash="css-1")


def _fp(tmp_path: Path, png: Path, screen_key: str = "test-screen",
        semantic: SemanticContext | None = None,
        deps: DependencyManifest | None = None):
    return VisualFingerprintBuilder().build(
        png, _context(screen_key), _render(),
        semantic=semantic,
        dependencies=deps,
    )


# ---------------------------------------------------------------------------
# Unit tests — VisualDiffEngine.compare()
# ---------------------------------------------------------------------------

class TestVisualDiffEngineNoChange:
    """Scenario 3: No-change → no diff."""

    def test_identical_images_no_change(self, tmp_path):
        png = _solid_png(tmp_path, "screen.png", (200, 200, 200))
        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(png, png)
        assert report.change_detected is False
        assert report.change_type == "NONE"
        assert report.severity == "none"
        assert report.confidence == 1.0
        assert report.affected_regions == []
        assert report.pixel_change_pct == 0.0

    def test_no_change_requires_no_attention(self, tmp_path):
        png = _solid_png(tmp_path, "screen.png", (100, 100, 100))
        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(png, png)
        assert report.requires_attention is False


class TestVisualDiffEngineNoise:
    """Scenario 4: Noise → ignored (subpixel shifts, anti-aliasing)."""

    def test_tiny_pixel_shift_below_noise_floor(self, tmp_path):
        """Two images differing by only noise-level pixels → NONE."""
        from PIL import Image
        img_a = Image.new("RGB", (64, 64), color=(128, 128, 128))
        img_b = Image.new("RGB", (64, 64), color=(128, 128, 128))
        # Alter exactly one pixel by 5 (below default PIXEL_NOISE_THRESHOLD=12)
        img_b.putpixel((0, 0), (133, 133, 133))

        path_a = tmp_path / "a.png"; img_a.save(str(path_a))
        path_b = tmp_path / "b.png"; img_b.save(str(path_b))

        engine = VisualDiffEngine(
            normalization_config=NormalizationConfig(canvas_size=(64, 64)),
            pixel_noise_threshold=12,
        )
        report = engine.compare(path_a, path_b)
        assert report.change_detected is False
        assert report.change_type == "NONE"


class TestVisualDiffEngineLayoutChange:
    """Scenario 1: Layout change detected."""

    def test_large_block_change_classified_as_layout(self, tmp_path):
        """White → half-black image → >5% canvas → LAYOUT."""
        from PIL import Image
        img_a = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img_b = Image.new("RGB", (100, 100), color=(255, 255, 255))
        # Fill top half black → 50% change
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img_b)
        draw.rectangle((0, 0, 100, 50), fill=(0, 0, 0))

        path_a = tmp_path / "a.png"; img_a.save(str(path_a))
        path_b = tmp_path / "b.png"; img_b.save(str(path_b))

        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(path_a, path_b)
        assert report.change_detected is True
        assert report.change_type == "LAYOUT"
        assert report.severity in ("medium", "high")
        assert len(report.affected_regions) > 0

    def test_layout_change_requires_attention(self, tmp_path):
        from PIL import Image, ImageDraw
        img_a = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img_b = Image.new("RGB", (100, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img_b)
        draw.rectangle((0, 0, 100, 70), fill=(0, 0, 0))
        path_a = tmp_path / "a.png"; img_a.save(str(path_a))
        path_b = tmp_path / "b.png"; img_b.save(str(path_b))

        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(path_a, path_b)
        assert report.requires_attention is True


class TestVisualDiffEngineTextChange:
    """Scenario 2: Text change detected."""

    def test_text_change_classified_when_semantic_sha_differs(self, tmp_path):
        """Small visual change + semantic_sha differs → TEXT."""
        from PIL import Image, ImageDraw
        img_a = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img_b = img_a.copy()
        draw = ImageDraw.Draw(img_b)
        # Small rectangle (simulates text label change)
        draw.rectangle((10, 10, 30, 20), fill=(50, 50, 50))

        path_a = tmp_path / "a.png"; img_a.save(str(path_a))
        path_b = tmp_path / "b.png"; img_b.save(str(path_b))

        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(
            path_a, path_b,
            semantic_sha_a="sha-old",
            semantic_sha_b="sha-new",
        )
        assert report.change_detected is True
        assert report.change_type == "TEXT"
        assert report.semantic_changed is True
        assert report.dependency_changed is False

    def test_text_change_confidence_high(self, tmp_path):
        from PIL import Image, ImageDraw
        img_a = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img_b = img_a.copy()
        ImageDraw.Draw(img_b).rectangle((5, 5, 25, 15), fill=(30, 30, 30))
        path_a = tmp_path / "a.png"; img_a.save(str(path_a))
        path_b = tmp_path / "b.png"; img_b.save(str(path_b))
        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(path_a, path_b, semantic_sha_a="a", semantic_sha_b="b")
        assert report.confidence >= 0.85


class TestVisualDiffEngineDependencyChange:
    """Scenario 5: Dependency change without visual change."""

    def test_dep_change_no_visual_diff_classified_as_component(self, tmp_path):
        """Identical images + different dependency_sha → COMPONENT, not NONE."""
        png = _solid_png(tmp_path, "screen.png", (200, 200, 200))
        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(
            png, png,
            dependency_sha_a="dep-old",
            dependency_sha_b="dep-new",
        )
        assert report.change_detected is True
        assert report.change_type == "COMPONENT"
        assert report.dependency_changed is True
        assert report.pixel_change_pct == 0.0

    def test_dep_change_no_visual_requires_attention(self, tmp_path):
        png = _solid_png(tmp_path, "screen.png", (200, 200, 200))
        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(png, png, dependency_sha_a="a", dependency_sha_b="b")
        assert report.requires_attention is True

    def test_dep_change_with_visual_diff_classified_as_component(self, tmp_path):
        """Dependency changed AND pixel diff → COMPONENT (code + visual)."""
        from PIL import Image, ImageDraw
        img_a = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img_b = img_a.copy()
        ImageDraw.Draw(img_b).rectangle((0, 0, 100, 30), fill=(200, 200, 200))
        path_a = tmp_path / "a.png"; img_a.save(str(path_a))
        path_b = tmp_path / "b.png"; img_b.save(str(path_b))

        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(path_a, path_b, dependency_sha_a="a", dependency_sha_b="b")
        assert report.change_type == "COMPONENT"
        assert report.dependency_changed is True
        assert report.change_detected is True


class TestVisualDiffEngineVisualChange:
    """Visual (color/spacing) change — no semantic or dep signal."""

    def test_color_change_classified_as_visual(self, tmp_path):
        """Small pixel delta, no semantic/dep signal → VISUAL."""
        from PIL import Image, ImageDraw
        img_a = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img_b = img_a.copy()
        ImageDraw.Draw(img_b).rectangle((40, 40, 60, 60), fill=(230, 230, 230))
        path_a = tmp_path / "a.png"; img_a.save(str(path_a))
        path_b = tmp_path / "b.png"; img_b.save(str(path_b))

        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(path_a, path_b)
        assert report.change_detected is True
        assert report.change_type == "VISUAL"
        assert report.semantic_changed is False
        assert report.dependency_changed is False

    def test_visual_change_low_severity(self, tmp_path):
        from PIL import Image, ImageDraw
        img_a = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img_b = img_a.copy()
        ImageDraw.Draw(img_b).rectangle((45, 45, 55, 55), fill=(200, 200, 200))
        path_a = tmp_path / "a.png"; img_a.save(str(path_a))
        path_b = tmp_path / "b.png"; img_b.save(str(path_b))

        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(path_a, path_b)
        assert report.severity in ("low", "medium")


class TestVisualDiffEngineRegions:
    """Region detection and bounding boxes."""

    def test_change_in_top_left_has_correct_label(self, tmp_path):
        from PIL import Image, ImageDraw
        img_a = Image.new("RGB", (120, 120), color=(255, 255, 255))
        img_b = img_a.copy()
        ImageDraw.Draw(img_b).rectangle((0, 0, 30, 30), fill=(0, 0, 0))
        path_a = tmp_path / "a.png"; img_a.save(str(path_a))
        path_b = tmp_path / "b.png"; img_b.save(str(path_b))

        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(120, 120)))
        report = engine.compare(path_a, path_b)
        assert len(report.affected_regions) >= 1
        assert report.affected_regions[0].label == "top-left"

    def test_two_separate_changes_produce_multiple_regions(self, tmp_path):
        from PIL import Image, ImageDraw
        img_a = Image.new("RGB", (200, 200), color=(255, 255, 255))
        img_b = img_a.copy()
        draw = ImageDraw.Draw(img_b)
        draw.rectangle((0, 0, 40, 40), fill=(0, 0, 0))     # top-left
        draw.rectangle((160, 160, 200, 200), fill=(0, 0, 0))  # bottom-right
        path_a = tmp_path / "a.png"; img_a.save(str(path_a))
        path_b = tmp_path / "b.png"; img_b.save(str(path_b))

        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(200, 200)))
        report = engine.compare(path_a, path_b)
        assert len(report.affected_regions) >= 2

    def test_region_bounding_box_within_canvas(self, tmp_path):
        from PIL import Image, ImageDraw
        size = (100, 100)
        img_a = Image.new("RGB", size, color=(255, 255, 255))
        img_b = img_a.copy()
        ImageDraw.Draw(img_b).rectangle((20, 20, 80, 80), fill=(0, 0, 0))
        path_a = tmp_path / "a.png"; img_a.save(str(path_a))
        path_b = tmp_path / "b.png"; img_b.save(str(path_b))

        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=size))
        report = engine.compare(path_a, path_b)
        for region in report.affected_regions:
            assert region.x >= 0
            assert region.y >= 0
            assert region.x + region.width <= size[0]
            assert region.y + region.height <= size[1]

    def test_affected_region_pixel_delta_pct_nonzero(self, tmp_path):
        from PIL import Image, ImageDraw
        img_a = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img_b = img_a.copy()
        ImageDraw.Draw(img_b).rectangle((10, 10, 50, 50), fill=(0, 0, 0))
        path_a = tmp_path / "a.png"; img_a.save(str(path_a))
        path_b = tmp_path / "b.png"; img_b.save(str(path_b))

        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(path_a, path_b)
        assert all(r.pixel_delta_pct > 0 for r in report.affected_regions)
        assert all(r.mean_delta > 0 for r in report.affected_regions)


class TestVisualDiffReportModel:
    """VisualDiffReport data model and serialization."""

    def test_to_dict_keys_present(self, tmp_path):
        png = _solid_png(tmp_path, "s.png", (100, 100, 100))
        engine = VisualDiffEngine(normalization_config=NormalizationConfig(canvas_size=(100, 100)))
        report = engine.compare(png, png)
        d = report.to_dict()
        expected_keys = {
            "wasCached", "changeDetected", "changeType", "severity",
            "confidence", "changeSummary", "affectedRegions",
            "requiresAttention", "pixelChangePct", "semanticChanged", "dependencyChanged",
        }
        assert expected_keys <= d.keys()

    def test_no_change_factory(self):
        r = VisualDiffReport.no_change()
        assert r.change_detected is False
        assert r.change_type == "NONE"
        assert r.was_cached is True
        assert r.confidence == 1.0

    def test_unavailable_factory(self):
        r = VisualDiffReport.unavailable("no prior image")
        assert r.change_type == "UNKNOWN"
        assert r.confidence == 0.0
        assert "no prior image" in r.change_summary

    def test_affected_region_to_dict(self):
        region = AffectedRegion(x=10, y=20, width=50, height=30,
                                pixel_delta_pct=0.45, mean_delta=120.5, label="center")
        d = region.to_dict()
        assert d["x"] == 10
        assert d["y"] == 20
        assert d["width"] == 50
        assert d["height"] == 30
        assert d["pixelDeltaPct"] == 0.45
        assert d["meanDelta"] == 120.5
        assert d["label"] == "center"


class TestPositionLabel:
    """_position_label helper."""

    def test_top_left(self):
        assert _position_label(0, 0, 30, 30, 120, 120) == "top-left"

    def test_bottom_right(self):
        assert _position_label(90, 90, 30, 30, 120, 120) == "bottom-right"

    def test_center(self):
        assert _position_label(45, 45, 30, 30, 120, 120) == "center"

    def test_top(self):
        assert _position_label(45, 0, 30, 20, 120, 120) == "top"

    def test_left(self):
        assert _position_label(0, 45, 20, 30, 120, 120) == "left"


class TestVisualDiffCacheIntegration:
    """compare_with_last() integration with VisualDeltaCache."""

    def test_compare_with_last_no_prior_returns_unavailable(self, tmp_path):
        """No prior PASS → unavailable report."""
        png = _solid_png(tmp_path, "screen.png", (200, 200, 200))
        fp = _fp(tmp_path, png)
        cache = VisualDeltaCache(tmp_path)
        report = cache.compare_with_last(fp, png)
        assert report.change_type == "UNKNOWN"
        assert report.confidence == 0.0
        assert "No prior PASS" in report.change_summary

    def test_compare_with_last_no_screenshot_on_disk_uses_signals(self, tmp_path):
        """Prior PASS exists but screenshot path not on disk → signal-based diff."""
        png = _solid_png(tmp_path, "screen.png", (200, 200, 200))
        sem_a = SemanticContext(texts=["Hello"])
        fp_a = VisualFingerprintBuilder().build(
            png, _context(), _render(), semantic=sem_a
        )
        cache = VisualDeltaCache(tmp_path)
        cache.record_pass(fp_a)

        sem_b = SemanticContext(texts=["World"])
        fp_b = VisualFingerprintBuilder().build(
            png, _context(), _render(), semantic=sem_b
        )
        report = cache.compare_with_last(fp_b, png)
        # Semantic changed → TEXT (signal-based)
        assert report.change_type == "TEXT"
        assert report.semantic_changed is True

    def test_compare_with_last_identical_signals_no_change(self, tmp_path):
        """Same fingerprint → no change report."""
        png = _solid_png(tmp_path, "screen.png", (200, 200, 200))
        sem = SemanticContext(texts=["Hello"])
        fp = VisualFingerprintBuilder().build(png, _context(), _render(), semantic=sem)
        cache = VisualDeltaCache(tmp_path)
        cache.record_pass(fp)

        report = cache.compare_with_last(fp, png)
        assert report.change_detected is False

    def test_compare_with_last_dep_change_no_screenshot(self, tmp_path):
        """Dependency changed, no screenshot path → COMPONENT inferred."""
        png = _solid_png(tmp_path, "screen.png", (200, 200, 200))
        deps_a = DependencyManifest(component_hashes={"A.razor": "v1"})
        fp_a = VisualFingerprintBuilder().build(
            png, _context(), _render(), dependencies=deps_a
        )
        cache = VisualDeltaCache(tmp_path)
        cache.record_pass(fp_a)

        deps_b = DependencyManifest(component_hashes={"A.razor": "v2"})
        fp_b = VisualFingerprintBuilder().build(
            png, _context(), _render(), dependencies=deps_b
        )
        report = cache.compare_with_last(fp_b, png)
        assert report.change_type == "COMPONENT"
        assert report.dependency_changed is True
