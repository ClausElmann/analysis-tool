"""Tests for core.visual_fingerprint, core.visual_delta_cache, core.visual_delta_export.

RULE-VISUAL-DELTA-CACHE — verified by these tests.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import pytest

from core.visual_fingerprint import (
    VISUAL_VALIDATION_POLICY_VERSION,
    DEFAULT_NORMALIZATION,
    DependencyManifest,
    FingerprintValidationError,
    MaskRegion,
    NormalizationConfig,
    RenderInputs,
    SemanticContext,
    ValidationContext,
    VisualFingerprintBuilder,
    _sha256_dict,
    compute_phash,
    hash_image_file,
    hash_normalized_image,
    phash_similarity,
    validate_fingerprint,
)
from core.visual_delta_cache import VisualDeltaCache
from core.visual_delta_export import VisualDeltaExporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _png(tmp_dir: Path, name: str = "screen.png", content: bytes = b"PNG_FAKE_DATA") -> Path:
    p = tmp_dir / name
    p.write_bytes(content)
    return p


def _context(screen_key: str = "test-screen", **kwargs) -> ValidationContext:
    return ValidationContext(
        screen_key=screen_key,
        device=kwargs.get("device", "desktop"),
        locale=kwargs.get("locale", "da-DK"),
        must_show=kwargs.get("must_show", ["Brugere"]),
        must_not_show=kwargs.get("must_not_show", ["shared."]),
    )


def _render(component: str = "abc") -> RenderInputs:
    return RenderInputs(component_hash=component, css_hash="css1")


# ---------------------------------------------------------------------------
# VisualFingerprintBuilder
# ---------------------------------------------------------------------------

class TestVisualFingerprintBuilder:

    def test_build_returns_fingerprint_with_all_hashes(self, tmp_path):
        png = _png(tmp_path)
        builder = VisualFingerprintBuilder()
        fp = builder.build(png, _context(), _render())

        assert fp.screen_key == "test-screen"
        assert len(fp.image_sha256) == 64
        assert len(fp.normalized_image_sha256) == 64
        assert len(fp.validation_context_sha256) == 64
        assert len(fp.render_input_sha256) == 64
        assert len(fp.validation_fingerprint_sha256) == 64
        assert fp.policy_version == VISUAL_VALIDATION_POLICY_VERSION

    def test_same_image_same_context_produces_identical_fingerprint(self, tmp_path):
        png = _png(tmp_path)
        builder = VisualFingerprintBuilder()
        ctx = _context()
        fp1 = builder.build(png, ctx, _render())
        fp2 = builder.build(png, ctx, _render())
        assert fp1.validation_fingerprint_sha256 == fp2.validation_fingerprint_sha256

    def test_different_image_produces_different_fingerprint(self, tmp_path):
        png_a = _png(tmp_path, "a.png", b"IMAGE_A")
        png_b = _png(tmp_path, "b.png", b"IMAGE_B")
        builder = VisualFingerprintBuilder()
        ctx = _context()
        fp_a = builder.build(png_a, ctx, _render())
        fp_b = builder.build(png_b, ctx, _render())
        assert fp_a.validation_fingerprint_sha256 != fp_b.validation_fingerprint_sha256

    def test_different_context_produces_different_fingerprint(self, tmp_path):
        png = _png(tmp_path)
        builder = VisualFingerprintBuilder()
        ctx_a = _context(must_show=["Brugere"])
        ctx_b = _context(must_show=["Brugere", "Ny bruger"])
        fp_a = builder.build(png, ctx_a, _render())
        fp_b = builder.build(png, ctx_b, _render())
        assert fp_a.validation_context_sha256 != fp_b.validation_context_sha256
        assert fp_a.validation_fingerprint_sha256 != fp_b.validation_fingerprint_sha256

    def test_different_render_inputs_produces_different_fingerprint(self, tmp_path):
        png = _png(tmp_path)
        builder = VisualFingerprintBuilder()
        ctx = _context()
        fp_a = builder.build(png, ctx, RenderInputs(component_hash="v1"))
        fp_b = builder.build(png, ctx, RenderInputs(component_hash="v2"))
        assert fp_a.render_input_sha256 != fp_b.render_input_sha256
        assert fp_a.validation_fingerprint_sha256 != fp_b.validation_fingerprint_sha256

    def test_context_hash_is_order_independent(self):
        ctx_a = ValidationContext(
            screen_key="s", device="desktop", locale="da-DK",
            must_show=["A", "B"], must_not_show=["X"]
        )
        ctx_b = ValidationContext(
            screen_key="s", device="desktop", locale="da-DK",
            must_show=["B", "A"], must_not_show=["X"]  # reversed order
        )
        assert _sha256_dict(ctx_a.to_canonical_dict()) == _sha256_dict(ctx_b.to_canonical_dict())

    def test_filename_does_not_affect_fingerprint(self, tmp_path):
        """Same bytes, different filename → identical fingerprint."""
        bytes_ = b"SAME_CONTENT"
        png_a = _png(tmp_path, "screenshot_run1.png", bytes_)
        png_b = _png(tmp_path, "screenshot_run999.png", bytes_)
        builder = VisualFingerprintBuilder()
        ctx = _context()
        fp_a = builder.build(png_a, ctx, _render())
        fp_b = builder.build(png_b, ctx, _render())
        assert fp_a.validation_fingerprint_sha256 == fp_b.validation_fingerprint_sha256

    def test_policy_version_stamped_on_fingerprint(self, tmp_path):
        png = _png(tmp_path)
        fp = VisualFingerprintBuilder().build(png, _context(), _render())
        assert fp.policy_version == VISUAL_VALIDATION_POLICY_VERSION


# ---------------------------------------------------------------------------
# VisualDeltaCache — skip logic
# ---------------------------------------------------------------------------

class TestVisualDeltaCacheSkipLogic:

    def _cache(self, tmp_path: Path) -> VisualDeltaCache:
        return VisualDeltaCache(data_root=tmp_path)

    def test_unseen_fingerprint_is_not_skipped(self, tmp_path):
        cache = self._cache(tmp_path)
        png = _png(tmp_path)
        fp = VisualFingerprintBuilder().build(png, _context(), _render())
        assert cache.should_skip(fp, mode="FAST") is False
        assert cache.should_skip(fp, mode="STRICT") is False

    def test_prior_pass_enables_fast_skip(self, tmp_path):
        cache = self._cache(tmp_path)
        png = _png(tmp_path)
        fp = VisualFingerprintBuilder().build(png, _context(), _render())
        cache.record_pass(fp)
        assert cache.should_skip(fp, mode="FAST") is True

    def test_prior_pass_enables_strict_skip(self, tmp_path):
        cache = self._cache(tmp_path)
        png = _png(tmp_path)
        fp = VisualFingerprintBuilder().build(png, _context(), _render())
        cache.record_pass(fp)
        assert cache.should_skip(fp, mode="STRICT") is True

    def test_prior_fail_never_enables_skip(self, tmp_path):
        cache = self._cache(tmp_path)
        png = _png(tmp_path)
        fp = VisualFingerprintBuilder().build(png, _context(), _render())
        cache.record_fail(fp)
        assert cache.should_skip(fp, mode="FAST") is False
        assert cache.should_skip(fp, mode="STRICT") is False

    def test_changed_image_breaks_fast_skip(self, tmp_path):
        cache = self._cache(tmp_path)
        png_old = _png(tmp_path, "old.png", b"OLD")
        png_new = _png(tmp_path, "new.png", b"NEW")
        ctx = _context()
        render = _render()
        fp_old = VisualFingerprintBuilder().build(png_old, ctx, render)
        fp_new = VisualFingerprintBuilder().build(png_new, ctx, render)
        cache.record_pass(fp_old)
        assert cache.should_skip(fp_new, mode="FAST") is False

    def test_changed_context_breaks_skip(self, tmp_path):
        cache = self._cache(tmp_path)
        png = _png(tmp_path)
        ctx_v1 = _context(must_show=["Brugere"])
        ctx_v2 = _context(must_show=["Brugere", "Ny knap"])  # gates changed
        fp_v1 = VisualFingerprintBuilder().build(png, ctx_v1, _render())
        fp_v2 = VisualFingerprintBuilder().build(png, ctx_v2, _render())
        cache.record_pass(fp_v1)
        assert cache.should_skip(fp_v2, mode="FAST") is False
        assert cache.should_skip(fp_v2, mode="STRICT") is False

    def test_changed_render_inputs_breaks_strict_but_not_fast(self, tmp_path):
        """FAST skips on image+context match even if render inputs changed."""
        cache = self._cache(tmp_path)
        png = _png(tmp_path)
        ctx = _context()
        fp_v1 = VisualFingerprintBuilder().build(png, ctx, RenderInputs(component_hash="v1"))
        fp_v2 = VisualFingerprintBuilder().build(png, ctx, RenderInputs(component_hash="v2"))
        cache.record_pass(fp_v1)
        # FAST: same image + same context → skip (render inputs not checked)
        assert cache.should_skip(fp_v2, mode="FAST") is True
        # STRICT: render input differs → do NOT skip
        assert cache.should_skip(fp_v2, mode="STRICT") is False

    def test_registry_persisted_across_instances(self, tmp_path):
        png = _png(tmp_path)
        fp = VisualFingerprintBuilder().build(png, _context(), _render())

        cache_a = VisualDeltaCache(data_root=tmp_path)
        cache_a.record_pass(fp)

        cache_b = VisualDeltaCache(data_root=tmp_path)  # fresh load from disk
        assert cache_b.should_skip(fp, mode="STRICT") is True

    def test_fail_written_to_registry_but_does_not_enable_skip(self, tmp_path):
        png = _png(tmp_path)
        fp = VisualFingerprintBuilder().build(png, _context(), _render())
        cache = VisualDeltaCache(data_root=tmp_path)
        cache.record_fail(fp)

        # Reload
        cache2 = VisualDeltaCache(data_root=tmp_path)
        assert cache2.fail_count() == 1
        assert cache2.should_skip(fp, mode="FAST") is False

    def test_pass_count_and_fail_count(self, tmp_path):
        cache = self._cache(tmp_path)
        png_a = _png(tmp_path, "a.png", b"A")
        png_b = _png(tmp_path, "b.png", b"B")
        fp_a = VisualFingerprintBuilder().build(png_a, _context("screen-a"), _render())
        fp_b = VisualFingerprintBuilder().build(png_b, _context("screen-b"), _render())
        cache.record_pass(fp_a)
        cache.record_fail(fp_b)
        assert cache.pass_count() == 1
        assert cache.fail_count() == 1
        assert cache.total_count() == 2

    def test_latest_pass_for_screen(self, tmp_path):
        cache = self._cache(tmp_path)
        png_v1 = _png(tmp_path, "v1.png", b"V1")
        png_v2 = _png(tmp_path, "v2.png", b"V2")
        builder = VisualFingerprintBuilder()
        ctx = _context("my-screen")
        fp1 = builder.build(png_v1, ctx, _render())
        fp2 = builder.build(png_v2, ctx, _render())
        cache.record_pass(fp1, build_id="build-1")
        cache.record_pass(fp2, build_id="build-2")
        latest = cache.latest_pass_for_screen("my-screen")
        assert latest is not None
        assert latest.build_id == "build-2"

    def test_get_unseen_or_invalidated_returns_delta(self, tmp_path):
        cache = self._cache(tmp_path)
        png_known = _png(tmp_path, "known.png", b"KNOWN")
        png_new   = _png(tmp_path, "new.png",   b"NEW")
        builder = VisualFingerprintBuilder()
        ctx_known = _context("screen-known")
        ctx_new   = _context("screen-new")
        fp_known = builder.build(png_known, ctx_known, _render())
        fp_new   = builder.build(png_new,   ctx_new,   _render())

        cache.record_pass(fp_known)

        candidates = [fp_known, fp_new]
        delta = cache.get_unseen_or_invalidated(candidates, mode="STRICT")
        assert delta == [fp_new]

    def test_rebuild_registry_keeps_only_latest_pass(self, tmp_path):
        cache = self._cache(tmp_path)
        png_v1 = _png(tmp_path, "v1.png", b"V1")
        png_v2 = _png(tmp_path, "v2.png", b"V2")
        ctx = _context("my-screen")
        fp1 = VisualFingerprintBuilder().build(png_v1, ctx, _render())
        fp2 = VisualFingerprintBuilder().build(png_v2, ctx, _render())
        cache.record_pass(fp1)
        cache.record_pass(fp2)
        cache.rebuild_registry(keep_only_latest_pass=True)
        reloaded = VisualDeltaCache(data_root=tmp_path)
        assert reloaded.total_count() == 1  # only latest pass kept


# ---------------------------------------------------------------------------
# VisualDeltaExporter
# ---------------------------------------------------------------------------

class TestVisualDeltaExporter:

    def test_export_only_unseen_fingerprints(self, tmp_path):
        cache = VisualDeltaCache(data_root=tmp_path / "data")
        exporter = VisualDeltaExporter(cache, output_dir=tmp_path / "exports")

        png_known = _png(tmp_path, "known.png", b"KNOWN")
        png_new   = _png(tmp_path, "new.png",   b"NEW")
        builder = VisualFingerprintBuilder()
        fp_known = builder.build(png_known, _context("screen-known"), _render())
        fp_new   = builder.build(png_new,   _context("screen-new"),   _render())

        cache.record_pass(fp_known)

        result = exporter.export(
            [fp_known, fp_new],
            screenshot_paths={"screen-known": str(png_known), "screen-new": str(png_new)},
            mode="STRICT",
            build_id="TEST-BUILD",
        )

        assert result["delta_count"] == 1
        assert result["skipped_count"] == 1
        assert "screen-known" in result["skipped_keys"]
        assert Path(result["manifest_path"]).is_file()

    def test_export_all_when_registry_empty(self, tmp_path):
        cache = VisualDeltaCache(data_root=tmp_path / "data")
        exporter = VisualDeltaExporter(cache, output_dir=tmp_path / "exports")

        pngs = [_png(tmp_path, f"s{i}.png", f"IMG{i}".encode()) for i in range(3)]
        builder = VisualFingerprintBuilder()
        fps = [builder.build(p, _context(f"screen-{i}"), _render()) for i, p in enumerate(pngs)]

        result = exporter.export(fps, mode="STRICT")
        assert result["delta_count"] == 3
        assert result["skipped_count"] == 0

    def test_zip_contains_screenshots_and_manifest(self, tmp_path):
        cache = VisualDeltaCache(data_root=tmp_path / "data")
        exporter = VisualDeltaExporter(cache, output_dir=tmp_path / "exports")

        png = _png(tmp_path, "screen.png", b"CONTENT")
        fp = VisualFingerprintBuilder().build(png, _context("my-screen"), _render())

        result = exporter.export(
            [fp],
            screenshot_paths={"my-screen": str(png)},
            mode="STRICT",
        )

        assert result["zip_path"] is not None
        import zipfile
        with zipfile.ZipFile(result["zip_path"]) as zf:
            names = zf.namelist()
        assert "manifest.jsonl" in names
        assert any("my-screen" in n for n in names)

    def test_merge_results_records_pass_and_fail(self, tmp_path):
        cache = VisualDeltaCache(data_root=tmp_path / "data")
        exporter = VisualDeltaExporter(cache, output_dir=tmp_path / "exports")

        png_a = _png(tmp_path, "a.png", b"A")
        png_b = _png(tmp_path, "b.png", b"B")
        builder = VisualFingerprintBuilder()
        fp_a = builder.build(png_a, _context("screen-a"), _render())
        fp_b = builder.build(png_b, _context("screen-b"), _render())

        results = [
            {"screenKey": "screen-a", "result": "PASS"},
            {"screenKey": "screen-b", "result": "FAIL"},
        ]

        summary = exporter.merge_results(
            results,
            fingerprints_by_key={"screen-a": fp_a, "screen-b": fp_b},
            build_id="BUILD-X",
        )

        assert summary["pass_count"] == 1
        assert summary["fail_count"] == 1
        assert cache.pass_count() == 1
        assert cache.fail_count() == 1

    def test_merge_results_pass_enables_subsequent_skip(self, tmp_path):
        cache = VisualDeltaCache(data_root=tmp_path / "data")
        exporter = VisualDeltaExporter(cache, output_dir=tmp_path / "exports")

        png = _png(tmp_path, "screen.png", b"IMG")
        fp = VisualFingerprintBuilder().build(png, _context("screen-x"), _render())

        exporter.merge_results(
            [{"screenKey": "screen-x", "result": "PASS"}],
            fingerprints_by_key={"screen-x": fp},
        )

        assert cache.should_skip(fp, mode="STRICT") is True

    def test_merge_fail_does_not_enable_skip(self, tmp_path):
        cache = VisualDeltaCache(data_root=tmp_path / "data")
        exporter = VisualDeltaExporter(cache, output_dir=tmp_path / "exports")

        png = _png(tmp_path, "screen.png", b"IMG")
        fp = VisualFingerprintBuilder().build(png, _context("screen-x"), _render())

        exporter.merge_results(
            [{"screenKey": "screen-x", "result": "FAIL"}],
            fingerprints_by_key={"screen-x": fp},
        )

        assert cache.should_skip(fp, mode="FAST") is False
        assert cache.should_skip(fp, mode="STRICT") is False


# ---------------------------------------------------------------------------
# Decision Engine — RULE-VISUAL-DELTA-01/02/03 + edge cases
# ---------------------------------------------------------------------------

class TestDecisionEngine:
    """RULE-VISUAL-DELTA-01 through RULE-VISUAL-DELTA-03.

    01 — Same SHA256 → SKIP unconditionally (new timestamp, same image)
    02 — pHash >= 95% + same semantic → SKIP (small pixel diff)
    03 — Semantic changed → ANALYZE (text change overrides visual similarity)
    04 — No prior PASS → ANALYZE
    05 — Corrupted cache → FAIL FAST
    """

    # Two images that differ by one byte in the interior.
    # Using > 64 bytes so the dHash sampler spans the byte array properly.
    _BASE = b"PNG_VISUAL_CONTENT_ABCDEFGHIJ" * 20   # 580 bytes

    def _image_pair(self, tmp_path: Path, change_offset: int = 290):
        """Return (imageA, imageB) where B has one byte changed at *change_offset*."""
        imageA = tmp_path / "imageA.png"
        imageB = tmp_path / "imageB.png"
        imageA.write_bytes(self._BASE)
        modified = bytearray(self._BASE)
        modified[change_offset] = (modified[change_offset] + 7) % 256
        imageB.write_bytes(bytes(modified))
        return imageA, imageB

    def test_same_image_new_timestamp_skips(self, tmp_path):
        """RULE-VISUAL-DELTA-01: Exact SHA256 → SKIP (timestamp irrelevant)."""
        png = _png(tmp_path, content=self._BASE)
        builder = VisualFingerprintBuilder()
        ctx = _context()
        cache = VisualDeltaCache(tmp_path)

        fp = builder.build(png, ctx)
        cache.record_pass(fp, screenshot_path=str(png))

        # Second "run" — same image bytes → same sha256 → SKIP
        fp2 = builder.build(png, ctx)
        assert cache.should_skip(fp2) is True

    def test_small_pixel_diff_high_phash_skips(self, tmp_path):
        """RULE-VISUAL-DELTA-02: pHash >= 95% + same semantic → SKIP."""
        imageA, imageB = self._image_pair(tmp_path)
        builder = VisualFingerprintBuilder()
        ctx = _context()
        semantic = SemanticContext(texts=["Gem", "Annuller"])
        cache = VisualDeltaCache(tmp_path)

        fpA = builder.build(imageA, ctx, semantic=semantic)
        cache.record_pass(fpA, screenshot_path=str(imageA))

        fpB = builder.build(imageB, ctx, semantic=semantic)
        assert fpA.image_sha256 != fpB.image_sha256, "images must differ for this test"
        assert phash_similarity(fpA.perceptual_hash, fpB.perceptual_hash) >= 0.95
        assert cache.should_skip(fpB) is True

    def test_text_change_forces_reanalysis(self, tmp_path):
        """RULE-VISUAL-DELTA-03: Semantic change → ANALYZE even with pHash >= 95%."""
        imageA, imageB = self._image_pair(tmp_path)
        builder = VisualFingerprintBuilder()
        ctx = _context()
        semantic_old = SemanticContext(texts=["Gem", "Annuller"])
        semantic_new = SemanticContext(texts=["Gem", "Annuller", "Slet"])
        cache = VisualDeltaCache(tmp_path)

        fpA = builder.build(imageA, ctx, semantic=semantic_old)
        cache.record_pass(fpA, screenshot_path=str(imageA))

        fpB = builder.build(imageB, ctx, semantic=semantic_new)
        # Verify pHash would allow skip — semantic change must override it
        assert phash_similarity(fpA.perceptual_hash, fpB.perceptual_hash) >= 0.95
        assert fpA.semantic_sha256 != fpB.semantic_sha256
        assert cache.should_skip(fpB) is False

    def test_new_ui_forces_analysis(self, tmp_path):
        """No prior PASS → always ANALYZE."""
        png = _png(tmp_path, content=b"BRAND_NEW_UI_NEVER_SEEN_BEFORE" * 10)
        ctx = _context(screen_key="brand-new-screen")
        cache = VisualDeltaCache(tmp_path)  # empty cache

        fp = VisualFingerprintBuilder().build(png, ctx)
        assert cache.should_skip(fp) is False

    def test_corrupted_cache_fails_fast(self, tmp_path):
        """FAIL FAST: corrupted JSONL line raises ValueError on load."""
        registry = tmp_path / "visual_validation_registry.jsonl"
        registry.write_text(
            '{"screenKey":"s","result":"PASS"}\n{CORRUPTED JSON\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="FAIL FAST"):
            VisualDeltaCache(tmp_path)


# ---------------------------------------------------------------------------
# RULE-VISUAL-DELTA-ENGINE v2 — 7 Architect-required scenarios
# ---------------------------------------------------------------------------

def _deps(component: str = "comp-v1") -> DependencyManifest:
    return DependencyManifest(
        component_hashes={"MainPage.razor": component},
        css_hashes={"app.css": "css1"},
    )


class TestVisualDeltaEngineV2:
    """RULE-VISUAL-DELTA-ENGINE v2 (ARCHITECT DECISION 2026-04-15).

    All 7 required scenarios:
    1. same binary + same semantic + same dependency + PASS  => skip
    2. same binary but different semantic                    => reanalyze
    3. same canonical visual but different dependency        => reanalyze
    4. same hashes but previous FAIL                        => no skip
    5. validator_version change                              => reanalyze
    6. ruleset_version change                               => reanalyze
    7. mask_version change                                  => reanalyze
    """

    def test_scenario_1_all_match_pass_enables_skip(self, tmp_path):
        """Scenario 1: same binary + semantic + dependency + PASS => skip."""
        png = _png(tmp_path, content=b"UI_CONTENT_V1" * 20)
        ctx = _context()
        semantic = SemanticContext(texts=["Brugere", "Ny bruger"])
        deps = _deps("comp-v1")
        builder = VisualFingerprintBuilder()

        fp = builder.build(
            png, ctx, _render(), semantic=semantic,
            dependencies=deps,
            validator_version="va-1.0",
            ruleset_version="rs-1.0",
            mask_version="mask-1.0",
        )
        cache = VisualDeltaCache(tmp_path)
        cache.record_pass(fp)

        # Rebuild same fingerprint — everything matches
        fp2 = builder.build(
            png, ctx, _render(), semantic=semantic,
            dependencies=deps,
            validator_version="va-1.0",
            ruleset_version="rs-1.0",
            mask_version="mask-1.0",
        )
        assert cache.should_skip(fp2, mode="STRICT") is True

    def test_scenario_2_different_semantic_forces_reanalyze(self, tmp_path):
        """Scenario 2: same binary hash but semantic changed => reanalyze."""
        png = _png(tmp_path, content=b"UI_CONTENT_V1" * 20)
        ctx = _context()
        semantic_old = SemanticContext(texts=["Brugere"])
        semantic_new = SemanticContext(texts=["Brugere", "Slet bruger"])
        deps = _deps("comp-v1")
        builder = VisualFingerprintBuilder()

        fp_old = builder.build(png, ctx, _render(), semantic=semantic_old, dependencies=deps)
        cache = VisualDeltaCache(tmp_path)
        cache.record_pass(fp_old)

        fp_new = builder.build(png, ctx, _render(), semantic=semantic_new, dependencies=deps)
        assert fp_old.image_sha256 == fp_new.image_sha256, "binary hash must be identical"
        assert fp_old.semantic_sha256 != fp_new.semantic_sha256
        assert cache.should_skip(fp_new, mode="STRICT") is False

    def test_scenario_3_dependency_change_forces_reanalyze(self, tmp_path):
        """Scenario 3: same canonical visual but dependency changed => reanalyze."""
        png = _png(tmp_path, content=b"UI_CONTENT_V1" * 20)
        ctx = _context()
        semantic = SemanticContext(texts=["Brugere"])
        deps_old = _deps("comp-v1")
        deps_new = _deps("comp-v2")   # component source changed
        builder = VisualFingerprintBuilder()

        fp_old = builder.build(png, ctx, _render(), semantic=semantic, dependencies=deps_old)
        cache = VisualDeltaCache(tmp_path)
        cache.record_pass(fp_old)

        fp_new = builder.build(png, ctx, _render(), semantic=semantic, dependencies=deps_new)
        # Visual output is identical — but Razor component changed
        assert fp_old.normalized_image_sha256 == fp_new.normalized_image_sha256
        assert fp_old.dependency_sha256 != fp_new.dependency_sha256
        assert cache.should_skip(fp_new, mode="STRICT") is False

    def test_scenario_4_prior_fail_never_enables_skip(self, tmp_path):
        """Scenario 4: same hashes but previous result was FAIL => no skip."""
        png = _png(tmp_path, content=b"UI_CONTENT_V1" * 20)
        ctx = _context()
        deps = _deps()
        fp = VisualFingerprintBuilder().build(
            png, ctx, _render(), dependencies=deps,
            validator_version="va-1.0", ruleset_version="rs-1.0",
        )
        cache = VisualDeltaCache(tmp_path)
        cache.record_fail(fp)

        assert cache.should_skip(fp, mode="FAST") is False
        assert cache.should_skip(fp, mode="STRICT") is False

    def test_scenario_5_validator_version_change_forces_reanalyze(self, tmp_path):
        """Scenario 5: validator_version bumped => reanalyze even if visuals identical."""
        png = _png(tmp_path, content=b"UI_CONTENT_V1" * 20)
        ctx = _context()
        deps = _deps()
        builder = VisualFingerprintBuilder()

        fp_old = builder.build(
            png, ctx, _render(), dependencies=deps,
            validator_version="va-1.0", ruleset_version="rs-1.0",
        )
        cache = VisualDeltaCache(tmp_path)
        cache.record_pass(fp_old)

        fp_new = builder.build(
            png, ctx, _render(), dependencies=deps,
            validator_version="va-2.0",   # upgraded AI engine
            ruleset_version="rs-1.0",
        )
        assert fp_old.normalized_image_sha256 == fp_new.normalized_image_sha256
        assert cache.should_skip(fp_new, mode="STRICT") is False

    def test_scenario_6_ruleset_version_change_forces_reanalyze(self, tmp_path):
        """Scenario 6: ruleset_version bumped => reanalyze even if visuals identical."""
        png = _png(tmp_path, content=b"UI_CONTENT_V1" * 20)
        ctx = _context()
        deps = _deps()
        builder = VisualFingerprintBuilder()

        fp_old = builder.build(
            png, ctx, _render(), dependencies=deps,
            validator_version="va-1.0", ruleset_version="rs-1.0",
        )
        cache = VisualDeltaCache(tmp_path)
        cache.record_pass(fp_old)

        fp_new = builder.build(
            png, ctx, _render(), dependencies=deps,
            validator_version="va-1.0",
            ruleset_version="rs-2.0",    # mustShow/mustNotShow rules updated
        )
        assert fp_old.normalized_image_sha256 == fp_new.normalized_image_sha256
        assert cache.should_skip(fp_new, mode="STRICT") is False

    def test_scenario_7_mask_version_change_forces_reanalyze(self, tmp_path):
        """Scenario 7: mask_version bumped => reanalyze even if visuals identical."""
        png = _png(tmp_path, content=b"UI_CONTENT_V1" * 20)
        ctx = _context()
        deps = _deps()
        builder = VisualFingerprintBuilder()

        fp_old = builder.build(
            png, ctx, _render(), dependencies=deps,
            validator_version="va-1.0", ruleset_version="rs-1.0",
            mask_version="mask-1.0",
        )
        cache = VisualDeltaCache(tmp_path)
        cache.record_pass(fp_old)

        fp_new = builder.build(
            png, ctx, _render(), dependencies=deps,
            validator_version="va-1.0", ruleset_version="rs-1.0",
            mask_version="mask-2.0",    # normalization masks updated
        )
        assert fp_old.normalized_image_sha256 == fp_new.normalized_image_sha256
        assert cache.should_skip(fp_new, mode="STRICT") is False

    def test_v2_fields_persisted_and_reloaded(self, tmp_path):
        """v2 fields survive JSONL round-trip and are enforced after reload."""
        png = _png(tmp_path, content=b"UI_CONTENT_V1" * 20)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            dependencies=_deps("comp-v1"),
            validator_version="va-1.0",
            ruleset_version="rs-1.0",
            mask_version="mask-1.0",
            source_commit_sha="abc123",
        )
        cache = VisualDeltaCache(tmp_path)
        cache.record_pass(fp)

        # Reload from disk
        cache2 = VisualDeltaCache(tmp_path)
        entry = cache2.latest_pass_for_screen("test-screen")
        assert entry is not None
        assert entry.dependency_sha256 == fp.dependency_sha256
        assert entry.validator_version == "va-1.0"
        assert entry.ruleset_version == "rs-1.0"
        assert entry.mask_version == "mask-1.0"
        assert entry.source_commit_sha == "abc123"
        assert cache2.should_skip(fp, mode="STRICT") is True


# ---------------------------------------------------------------------------
# WAVE 8 — Visual Engine Hardening
# ---------------------------------------------------------------------------

def _real_png(tmp_dir: Path, name: str = "screen.png", color=(100, 149, 237)) -> Path:
    """Create a minimal real 64x64 PNG using PIL."""
    from PIL import Image as PILImage
    img = PILImage.new("RGB", (64, 64), color=color)
    path = tmp_dir / name
    img.save(str(path), format="PNG")
    return path


def _complete_fp(tmp_path: Path, screen_key: str = "test-screen") -> object:
    """Build a fully populated fingerprint (all v2 fields set)."""
    png = _real_png(tmp_path)
    ctx = _context(screen_key)
    semantic = SemanticContext(texts=["Brugere"], headings=["Dashboard"])
    deps = DependencyManifest(
        component_hashes={"Main.razor": "comp-v1"},
        css_hashes={"app.css": "css-v1"},
    )
    return VisualFingerprintBuilder().build(
        png, ctx, _render(),
        semantic=semantic,
        dependencies=deps,
        validator_version="va-1.0",
        ruleset_version="rs-1.0",
        mask_version="mask-1.0",
    )


class TestWave8Normalization:
    """RULE-VISUAL-NORMALIZATION — PIL pipeline is deterministic and correct."""

    def test_same_image_same_config_deterministic(self, tmp_path):
        """Same PNG + same config → identical normalized hash."""
        png = _real_png(tmp_path)
        h1 = hash_normalized_image(png, DEFAULT_NORMALIZATION)
        h2 = hash_normalized_image(png, DEFAULT_NORMALIZATION)
        assert h1 == h2
        assert len(h1) == 64  # SHA256 hex

    def test_different_images_different_hash(self, tmp_path):
        """Different content → different normalized hash."""
        png_a = _real_png(tmp_path, "a.png", color=(255, 0, 0))
        png_b = _real_png(tmp_path, "b.png", color=(0, 255, 0))
        assert hash_normalized_image(png_a) != hash_normalized_image(png_b)

    def test_canvas_resize_produces_consistent_hash(self, tmp_path):
        """A 64x64 PNG and a 128x128 PNG of same content hash identically after resize."""
        from PIL import Image as PILImage
        # Both are solid blue — after resize to same canvas they're the same image
        img_small = PILImage.new("RGB", (64, 64), color=(0, 0, 255))
        img_large = PILImage.new("RGB", (128, 128), color=(0, 0, 255))
        path_small = tmp_path / "small.png"
        path_large = tmp_path / "large.png"
        img_small.save(str(path_small))
        img_large.save(str(path_large))
        cfg = NormalizationConfig(canvas_size=(32, 32))
        assert hash_normalized_image(path_small, cfg) == hash_normalized_image(path_large, cfg)

    def test_mask_region_blanks_volatile_area(self, tmp_path):
        """A dynamic badge region is blanked — two images differing only in badge hash equal."""
        from PIL import Image as PILImage, ImageDraw

        # Base image: all white
        base = PILImage.new("RGB", (100, 100), color=(255, 255, 255))
        # Image with dynamic badge (red square at 10,10 → 20,20)
        with_badge = base.copy()
        draw = ImageDraw.Draw(with_badge)
        draw.rectangle((10, 10, 20, 20), fill=(255, 0, 0))

        cfg = NormalizationConfig(
            canvas_size=(100, 100),
            mask_regions=[MaskRegion(x=10, y=10, width=10, height=10, label="badge")],
        )
        path_base  = tmp_path / "base.png"
        path_badge = tmp_path / "badge.png"
        base.save(str(path_base))
        with_badge.save(str(path_badge))

        assert hash_normalized_image(path_base, cfg) == hash_normalized_image(path_badge, cfg)

    def test_mask_region_does_not_affect_unmasked_area(self, tmp_path):
        """Content outside mask regions still differentiates images."""
        from PIL import Image as PILImage, ImageDraw

        img_a = PILImage.new("RGB", (100, 100), color=(255, 255, 255))
        img_b = img_a.copy()
        draw = ImageDraw.Draw(img_b)
        draw.rectangle((50, 50, 70, 70), fill=(0, 0, 255))  # different in unmasked area

        cfg = NormalizationConfig(
            canvas_size=(100, 100),
            mask_regions=[MaskRegion(x=0, y=0, width=30, height=30, label="top-left")],
        )
        path_a = tmp_path / "a.png"
        path_b = tmp_path / "b.png"
        img_a.save(str(path_a))
        img_b.save(str(path_b))
        assert hash_normalized_image(path_a, cfg) != hash_normalized_image(path_b, cfg)

    def test_grayscale_flag_changes_hash(self, tmp_path):
        """Grayscale=True produces a different hash than grayscale=False."""
        png = _real_png(tmp_path, color=(100, 200, 50))
        h_rgb  = hash_normalized_image(png, NormalizationConfig(grayscale=False))
        h_gray = hash_normalized_image(png, NormalizationConfig(grayscale=True))
        assert h_rgb != h_gray

    def test_mask_version_in_normalization_config(self, tmp_path):
        """NormalizationConfig carries mask_version that must be passed to fingerprint."""
        cfg = NormalizationConfig(
            mask_regions=[MaskRegion(10, 10, 20, 20, label="timestamp")],
            mask_version="mask-ts-v1",
        )
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["x"]),
            dependencies=DependencyManifest(component_hashes={"A.razor": "h1"}),
            validator_version="va-1", ruleset_version="rs-1",
            mask_version=cfg.mask_version,
            normalization_config=cfg,
        )
        assert fp.mask_version == "mask-ts-v1"
        assert len(fp.normalized_image_sha256) == 64


class TestWave8ProductionMode:
    """RULE-VISUAL-DELTA-ENGINE v2 — production_mode enforces non-empty fields."""

    def test_empty_semantic_in_production_mode_forces_reanalysis(self, tmp_path):
        """production_mode=True: empty semantic → must NOT skip."""
        png = _real_png(tmp_path)
        fp_complete = _complete_fp(tmp_path)

        cache = VisualDeltaCache(tmp_path, production_mode=True)
        cache.record_pass(fp_complete)

        # Build a fingerprint without semantic
        fp_no_semantic = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            dependencies=DependencyManifest(component_hashes={"Main.razor": "comp-v1"}),
            validator_version="va-1.0", ruleset_version="rs-1.0", mask_version="mask-1.0",
            # semantic omitted → semantic_sha256 = ""
        )
        assert cache.should_skip(fp_no_semantic, mode="STRICT") is False

    def test_empty_dependency_in_production_mode_forces_reanalysis(self, tmp_path):
        """production_mode=True: empty dependency_sha256 → must NOT skip."""
        fp_complete = _complete_fp(tmp_path)
        png = _real_png(tmp_path)

        cache = VisualDeltaCache(tmp_path, production_mode=True)
        cache.record_pass(fp_complete)

        fp_no_dep = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["Brugere"]),
            validator_version="va-1.0", ruleset_version="rs-1.0", mask_version="mask-1.0",
            # dependencies omitted → dependency_sha256 = ""
        )
        assert cache.should_skip(fp_no_dep, mode="STRICT") is False

    def test_empty_validator_version_in_production_mode_forces_reanalysis(self, tmp_path):
        """production_mode=True: empty validator_version → must NOT skip."""
        fp_complete = _complete_fp(tmp_path)
        png = _real_png(tmp_path)

        cache = VisualDeltaCache(tmp_path, production_mode=True)
        cache.record_pass(fp_complete)

        fp_no_validator = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["Brugere"]),
            dependencies=DependencyManifest(component_hashes={"Main.razor": "comp-v1"}),
            ruleset_version="rs-1.0", mask_version="mask-1.0",
            # validator_version omitted → ""
        )
        assert cache.should_skip(fp_no_validator, mode="STRICT") is False

    def test_test_mode_allows_empty_fields_for_backward_compat(self, tmp_path):
        """Default mode (production_mode=False): empty fields still allow skip."""
        png = _real_png(tmp_path)
        ctx = _context()
        fp = VisualFingerprintBuilder().build(png, ctx, _render())  # no v2 fields
        cache = VisualDeltaCache(tmp_path, production_mode=False)
        cache.record_pass(fp)
        assert cache.should_skip(fp, mode="STRICT") is True


class TestWave8ValidationFastFail:
    """validate_fingerprint() raises FingerprintValidationError on incomplete fingerprints."""

    def test_complete_fingerprint_passes_validation(self, tmp_path):
        fp = _complete_fp(tmp_path)
        validate_fingerprint(fp)  # must not raise

    def test_missing_semantic_raises(self, tmp_path):
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            dependencies=DependencyManifest(component_hashes={"A.razor": "h"}),
            validator_version="va-1", ruleset_version="rs-1", mask_version="m-1",
        )
        with pytest.raises(FingerprintValidationError, match="semantic_sha256"):
            validate_fingerprint(fp)

    def test_missing_dependency_raises(self, tmp_path):
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["x"]),
            validator_version="va-1", ruleset_version="rs-1", mask_version="m-1",
        )
        with pytest.raises(FingerprintValidationError, match="dependency_sha256"):
            validate_fingerprint(fp)

    def test_missing_validator_version_raises(self, tmp_path):
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["x"]),
            dependencies=DependencyManifest(component_hashes={"A.razor": "h"}),
            ruleset_version="rs-1", mask_version="m-1",
        )
        with pytest.raises(FingerprintValidationError, match="validator_version"):
            validate_fingerprint(fp)

    def test_missing_ruleset_version_raises(self, tmp_path):
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["x"]),
            dependencies=DependencyManifest(component_hashes={"A.razor": "h"}),
            validator_version="va-1", mask_version="m-1",
        )
        with pytest.raises(FingerprintValidationError, match="ruleset_version"):
            validate_fingerprint(fp)

    def test_missing_mask_version_raises(self, tmp_path):
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["x"]),
            dependencies=DependencyManifest(component_hashes={"A.razor": "h"}),
            validator_version="va-1", ruleset_version="rs-1",
        )
        with pytest.raises(FingerprintValidationError, match="mask_version"):
            validate_fingerprint(fp)

    def test_all_missing_reports_all_fields(self, tmp_path):
        """Error message lists all missing fields at once."""
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(png, _context(), _render())
        with pytest.raises(FingerprintValidationError) as exc_info:
            validate_fingerprint(fp)
        msg = str(exc_info.value)
        assert "semantic_sha256" in msg
        assert "dependency_sha256" in msg
        assert "validator_version" in msg
        assert "ruleset_version" in msg
        assert "mask_version" in msg


class TestWave8DependencyManifest:
    """DependencyManifest.is_empty() and dependency_source."""

    def test_empty_manifest_is_empty(self):
        assert DependencyManifest().is_empty() is True

    def test_non_empty_manifest_is_not_empty(self):
        m = DependencyManifest(component_hashes={"A.razor": "abc"})
        assert m.is_empty() is False

    def test_dependency_source_default_is_manual(self):
        assert DependencyManifest().dependency_source == "MANUAL"

    def test_dependency_source_in_canonical_dict(self):
        m = DependencyManifest(
            component_hashes={"A.razor": "h"},
            dependency_source="AUTO",
        )
        d = m.to_canonical_dict()
        assert d["dependencySource"] == "AUTO"

    def test_different_dependency_source_different_hash(self):
        """MANUAL vs AUTO manifests with same files produce different SHA256."""
        m_manual = DependencyManifest(
            component_hashes={"A.razor": "h"},
            dependency_source="MANUAL",
        )
        m_auto = DependencyManifest(
            component_hashes={"A.razor": "h"},
            dependency_source="AUTO",
        )
        from core.visual_fingerprint import _sha256_dict
        assert _sha256_dict(m_manual.to_canonical_dict()) != _sha256_dict(m_auto.to_canonical_dict())


# ---------------------------------------------------------------------------
# WAVE 8 — Visual Engine Hardening
# ---------------------------------------------------------------------------

def _real_png(tmp_dir: Path, name: str = "screen.png", color=(100, 149, 237)) -> Path:
    """Create a minimal real 64x64 PNG using PIL."""
    from PIL import Image as PILImage
    img = PILImage.new("RGB", (64, 64), color=color)
    path = tmp_dir / name
    img.save(str(path), format="PNG")
    return path


def _complete_fp(tmp_path: Path, screen_key: str = "test-screen") -> object:
    """Build a fully populated fingerprint (all v2 fields set)."""
    png = _real_png(tmp_path)
    ctx = _context(screen_key)
    semantic = SemanticContext(texts=["Brugere"], headings=["Dashboard"])
    deps = DependencyManifest(
        component_hashes={"Main.razor": "comp-v1"},
        css_hashes={"app.css": "css-v1"},
    )
    return VisualFingerprintBuilder().build(
        png, ctx, _render(),
        semantic=semantic,
        dependencies=deps,
        validator_version="va-1.0",
        ruleset_version="rs-1.0",
        mask_version="mask-1.0",
    )


class TestWave8Normalization:
    """RULE-VISUAL-NORMALIZATION — PIL pipeline is deterministic and correct."""

    def test_same_image_same_config_deterministic(self, tmp_path):
        """Same PNG + same config → identical normalized hash."""
        png = _real_png(tmp_path)
        h1 = hash_normalized_image(png, DEFAULT_NORMALIZATION)
        h2 = hash_normalized_image(png, DEFAULT_NORMALIZATION)
        assert h1 == h2
        assert len(h1) == 64  # SHA256 hex

    def test_different_images_different_hash(self, tmp_path):
        """Different content → different normalized hash."""
        png_a = _real_png(tmp_path, "a.png", color=(255, 0, 0))
        png_b = _real_png(tmp_path, "b.png", color=(0, 255, 0))
        assert hash_normalized_image(png_a) != hash_normalized_image(png_b)

    def test_canvas_resize_produces_consistent_hash(self, tmp_path):
        """A 64x64 PNG and a 128x128 PNG of same content hash identically after resize."""
        from PIL import Image as PILImage
        # Both are solid blue — after resize to same canvas they're the same image
        img_small = PILImage.new("RGB", (64, 64), color=(0, 0, 255))
        img_large = PILImage.new("RGB", (128, 128), color=(0, 0, 255))
        path_small = tmp_path / "small.png"
        path_large = tmp_path / "large.png"
        img_small.save(str(path_small))
        img_large.save(str(path_large))
        cfg = NormalizationConfig(canvas_size=(32, 32))
        assert hash_normalized_image(path_small, cfg) == hash_normalized_image(path_large, cfg)

    def test_mask_region_blanks_volatile_area(self, tmp_path):
        """A dynamic badge region is blanked — two images differing only in badge hash equal."""
        from PIL import Image as PILImage, ImageDraw

        # Base image: all white
        base = PILImage.new("RGB", (100, 100), color=(255, 255, 255))
        # Image with dynamic badge (red square at 10,10 → 20,20)
        with_badge = base.copy()
        draw = ImageDraw.Draw(with_badge)
        draw.rectangle((10, 10, 20, 20), fill=(255, 0, 0))

        cfg = NormalizationConfig(
            canvas_size=(100, 100),
            mask_regions=[MaskRegion(x=10, y=10, width=10, height=10, label="badge")],
        )
        path_base  = tmp_path / "base.png"
        path_badge = tmp_path / "badge.png"
        base.save(str(path_base))
        with_badge.save(str(path_badge))

        assert hash_normalized_image(path_base, cfg) == hash_normalized_image(path_badge, cfg)

    def test_mask_region_does_not_affect_unmasked_area(self, tmp_path):
        """Content outside mask regions still differentiates images."""
        from PIL import Image as PILImage, ImageDraw

        img_a = PILImage.new("RGB", (100, 100), color=(255, 255, 255))
        img_b = img_a.copy()
        draw = ImageDraw.Draw(img_b)
        draw.rectangle((50, 50, 70, 70), fill=(0, 0, 255))  # different in unmasked area

        cfg = NormalizationConfig(
            canvas_size=(100, 100),
            mask_regions=[MaskRegion(x=0, y=0, width=30, height=30, label="top-left")],
        )
        path_a = tmp_path / "a.png"
        path_b = tmp_path / "b.png"
        img_a.save(str(path_a))
        img_b.save(str(path_b))
        assert hash_normalized_image(path_a, cfg) != hash_normalized_image(path_b, cfg)

    def test_grayscale_flag_changes_hash(self, tmp_path):
        """Grayscale=True produces a different hash than grayscale=False."""
        png = _real_png(tmp_path, color=(100, 200, 50))
        h_rgb  = hash_normalized_image(png, NormalizationConfig(grayscale=False))
        h_gray = hash_normalized_image(png, NormalizationConfig(grayscale=True))
        assert h_rgb != h_gray

    def test_mask_version_in_normalization_config(self, tmp_path):
        """NormalizationConfig carries mask_version that must be passed to fingerprint."""
        cfg = NormalizationConfig(
            mask_regions=[MaskRegion(10, 10, 20, 20, label="timestamp")],
            mask_version="mask-ts-v1",
        )
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["x"]),
            dependencies=DependencyManifest(component_hashes={"A.razor": "h1"}),
            validator_version="va-1", ruleset_version="rs-1",
            mask_version=cfg.mask_version,
            normalization_config=cfg,
        )
        assert fp.mask_version == "mask-ts-v1"
        assert len(fp.normalized_image_sha256) == 64


class TestWave8ProductionMode:
    """RULE-VISUAL-DELTA-ENGINE v2 — production_mode enforces non-empty fields."""

    def test_empty_semantic_in_production_mode_forces_reanalysis(self, tmp_path):
        """production_mode=True: empty semantic → must NOT skip."""
        png = _real_png(tmp_path)
        fp_complete = _complete_fp(tmp_path)

        cache = VisualDeltaCache(tmp_path, production_mode=True)
        cache.record_pass(fp_complete)

        # Build a fingerprint without semantic
        fp_no_semantic = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            dependencies=DependencyManifest(component_hashes={"Main.razor": "comp-v1"}),
            validator_version="va-1.0", ruleset_version="rs-1.0", mask_version="mask-1.0",
            # semantic omitted → semantic_sha256 = ""
        )
        assert cache.should_skip(fp_no_semantic, mode="STRICT") is False

    def test_empty_dependency_in_production_mode_forces_reanalysis(self, tmp_path):
        """production_mode=True: empty dependency_sha256 → must NOT skip."""
        fp_complete = _complete_fp(tmp_path)
        png = _real_png(tmp_path)

        cache = VisualDeltaCache(tmp_path, production_mode=True)
        cache.record_pass(fp_complete)

        fp_no_dep = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["Brugere"]),
            validator_version="va-1.0", ruleset_version="rs-1.0", mask_version="mask-1.0",
            # dependencies omitted → dependency_sha256 = ""
        )
        assert cache.should_skip(fp_no_dep, mode="STRICT") is False

    def test_empty_validator_version_in_production_mode_forces_reanalysis(self, tmp_path):
        """production_mode=True: empty validator_version → must NOT skip."""
        fp_complete = _complete_fp(tmp_path)
        png = _real_png(tmp_path)

        cache = VisualDeltaCache(tmp_path, production_mode=True)
        cache.record_pass(fp_complete)

        fp_no_validator = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["Brugere"]),
            dependencies=DependencyManifest(component_hashes={"Main.razor": "comp-v1"}),
            ruleset_version="rs-1.0", mask_version="mask-1.0",
            # validator_version omitted → ""
        )
        assert cache.should_skip(fp_no_validator, mode="STRICT") is False

    def test_test_mode_allows_empty_fields_for_backward_compat(self, tmp_path):
        """Default mode (production_mode=False): empty fields still allow skip."""
        png = _real_png(tmp_path)
        ctx = _context()
        fp = VisualFingerprintBuilder().build(png, ctx, _render())  # no v2 fields
        cache = VisualDeltaCache(tmp_path, production_mode=False)
        cache.record_pass(fp)
        assert cache.should_skip(fp, mode="STRICT") is True


class TestWave8ValidationFastFail:
    """validate_fingerprint() raises FingerprintValidationError on incomplete fingerprints."""

    def test_complete_fingerprint_passes_validation(self, tmp_path):
        fp = _complete_fp(tmp_path)
        validate_fingerprint(fp)  # must not raise

    def test_missing_semantic_raises(self, tmp_path):
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            dependencies=DependencyManifest(component_hashes={"A.razor": "h"}),
            validator_version="va-1", ruleset_version="rs-1", mask_version="m-1",
        )
        with pytest.raises(FingerprintValidationError, match="semantic_sha256"):
            validate_fingerprint(fp)

    def test_missing_dependency_raises(self, tmp_path):
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["x"]),
            validator_version="va-1", ruleset_version="rs-1", mask_version="m-1",
        )
        with pytest.raises(FingerprintValidationError, match="dependency_sha256"):
            validate_fingerprint(fp)

    def test_missing_validator_version_raises(self, tmp_path):
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["x"]),
            dependencies=DependencyManifest(component_hashes={"A.razor": "h"}),
            ruleset_version="rs-1", mask_version="m-1",
        )
        with pytest.raises(FingerprintValidationError, match="validator_version"):
            validate_fingerprint(fp)

    def test_missing_ruleset_version_raises(self, tmp_path):
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["x"]),
            dependencies=DependencyManifest(component_hashes={"A.razor": "h"}),
            validator_version="va-1", mask_version="m-1",
        )
        with pytest.raises(FingerprintValidationError, match="ruleset_version"):
            validate_fingerprint(fp)

    def test_missing_mask_version_raises(self, tmp_path):
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(
            png, _context(), _render(),
            semantic=SemanticContext(texts=["x"]),
            dependencies=DependencyManifest(component_hashes={"A.razor": "h"}),
            validator_version="va-1", ruleset_version="rs-1",
        )
        with pytest.raises(FingerprintValidationError, match="mask_version"):
            validate_fingerprint(fp)

    def test_all_missing_reports_all_fields(self, tmp_path):
        """Error message lists all missing fields at once."""
        png = _real_png(tmp_path)
        fp = VisualFingerprintBuilder().build(png, _context(), _render())
        with pytest.raises(FingerprintValidationError) as exc_info:
            validate_fingerprint(fp)
        msg = str(exc_info.value)
        assert "semantic_sha256" in msg
        assert "dependency_sha256" in msg
        assert "validator_version" in msg
        assert "ruleset_version" in msg
        assert "mask_version" in msg


class TestWave8DependencyManifest:
    """DependencyManifest.is_empty() and dependency_source."""

    def test_empty_manifest_is_empty(self):
        assert DependencyManifest().is_empty() is True

    def test_non_empty_manifest_is_not_empty(self):
        m = DependencyManifest(component_hashes={"A.razor": "abc"})
        assert m.is_empty() is False

    def test_dependency_source_default_is_manual(self):
        assert DependencyManifest().dependency_source == "MANUAL"

    def test_dependency_source_in_canonical_dict(self):
        m = DependencyManifest(
            component_hashes={"A.razor": "h"},
            dependency_source="AUTO",
        )
        d = m.to_canonical_dict()
        assert d["dependencySource"] == "AUTO"

    def test_different_dependency_source_different_hash(self):
        """MANUAL vs AUTO manifests with same files produce different SHA256."""
        m_manual = DependencyManifest(
            component_hashes={"A.razor": "h"},
            dependency_source="MANUAL",
        )
        m_auto = DependencyManifest(
            component_hashes={"A.razor": "h"},
            dependency_source="AUTO",
        )
        from core.visual_fingerprint import _sha256_dict
        assert _sha256_dict(m_manual.to_canonical_dict()) != _sha256_dict(m_auto.to_canonical_dict())
