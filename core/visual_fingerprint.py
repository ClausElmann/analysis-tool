"""visual_fingerprint.py — Validation fingerprint builder.

RULE-VISUAL-DELTA-CACHE (ARCHITECT DECISION 2026-04-14)
========================================================
A visual artefact may be skipped ONLY when a prior PASS exists with identical:
  - normalized_image_sha256  (pre-processed: masks, stable crop, no animations)
  - validation_context_sha256 (gates, mustShow/mustNotShow, device, locale, roles)
  - render_input_sha256       (component hash, CSS, loc-resources, seed, feature flags)

Identity is NEVER: filename, timestamp, wave, or screenshot-id alone.

Fingerprint composition
-----------------------
  validation_fingerprint_sha256 = SHA256(
      normalized_image_sha256
    + validation_context_sha256
    + render_input_sha256
  )

Two operating modes
-------------------
  FAST:   skip if image_hash + context_hash both match a prior PASS
  STRICT: skip only if all three hashes + policy_version match

RULE-VISUAL-NORMALIZATION (ARCHITECT DECISION 2026-04-15)
=========================================================
  hash_normalized_image() must use the full PIL pipeline:
    1. Strip metadata (PNG chunks)
    2. Resize to deterministic canvas (NormalizationConfig.canvas_size)
    3. Convert to RGB (remove alpha)
    4. Apply mask regions (fill with MASK_FILL_COLOR)
    5. Optional: grayscale + blur
    6. Serialize raw pixel bytes → SHA256

  mask_version MUST match a prior PASS for a STRICT skip.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

try:
    from PIL import Image, ImageFilter
    _PIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PIL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Current policy version — bump this whenever gates / mustShow / mustNotShow
# rules change to force cache invalidation across the board.
# ---------------------------------------------------------------------------
VISUAL_VALIDATION_POLICY_VERSION = "2026-04-14-v1"


# ---------------------------------------------------------------------------
# Normalization primitives — RULE-VISUAL-NORMALIZATION
# ---------------------------------------------------------------------------

#: Fill color used to blank out dynamic/volatile mask regions.
MASK_FILL_COLOR = (128, 128, 128)  # mid-grey — neutral, easy to spot in debug

#: Default deterministic canvas size (width, height).
DEFAULT_CANVAS_SIZE = (1280, 800)


@dataclass
class MaskRegion:
    """A rectangular area to blank out before hashing.

    Coordinates are in normalized device pixels on the DEFAULT_CANVAS_SIZE canvas.
    If the screenshot is resized from a different resolution, coordinates scale
    proportionally.

    Common labels: "timestamp", "spinner", "cursor", "badge", "animation"
    """
    x: int
    y: int
    width: int
    height: int
    label: str = ""   # human-readable name (logging only, not hashed)

    def to_pil_box(self) -> tuple[int, int, int, int]:
        """Return (left, upper, right, lower) for PIL.ImageDraw.rectangle."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class NormalizationConfig:
    """Controls deterministic canonical rendering pipeline.

    mask_version MUST be bumped whenever masks change —
    this invalidates all prior cache entries (enforced in STRICT skip).
    """
    canvas_size: tuple[int, int] = DEFAULT_CANVAS_SIZE
    mask_regions: list[MaskRegion] = field(default_factory=list)
    grayscale: bool = False
    blur_radius: float = 0.0      # 0.0 = no blur; >0 applies GaussianBlur
    mask_version: str = "mask-none-v1"   # change this when masks change


#: Shared default config — no masks, RGB, no blur.
DEFAULT_NORMALIZATION = NormalizationConfig()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ValidationContext:
    """Everything that makes a previous validation result valid.

    If ANY of these change, the cached result must NOT be trusted.
    """
    screen_key: str
    device: str                           # desktop | mobile | tablet
    locale: str                           # e.g. da-DK, en-US
    must_show: list[str] = field(default_factory=list)
    must_not_show: list[str] = field(default_factory=list)
    quality_gate_version: str = "v1"
    journey_version: str = "v1"
    seed_scenario: str = "default"
    auth_role: str = "anonymous"
    policy_version: str = VISUAL_VALIDATION_POLICY_VERSION

    def to_canonical_dict(self) -> dict:
        """Stable, sorted dict — order must not affect hash."""
        return {
            "screenKey":           self.screen_key,
            "device":              self.device,
            "locale":              self.locale,
            "mustShow":            sorted(self.must_show),
            "mustNotShow":         sorted(self.must_not_show),
            "qualityGateVersion":  self.quality_gate_version,
            "journeyVersion":      self.journey_version,
            "seedScenario":        self.seed_scenario,
            "authRole":            self.auth_role,
            "policyVersion":       self.policy_version,
        }


@dataclass
class RenderInputs:
    """Hashes of sources that drive the rendered output.

    Same screenshot but changed source → STRICT mode must re-validate.
    """
    component_hash: str = ""      # SHA256 of relevant component/page source
    css_hash: str = ""            # SHA256 of relevant CSS / design tokens
    loc_hash: str = ""            # SHA256 of relevant localization resources
    seed_hash: str = ""           # SHA256 of DB seed / fixture snapshot
    feature_flags_hash: str = ""  # SHA256 of active feature-flag values
    browser_profile_hash: str = ""
    props_hash: str = ""          # SHA256 of component props / input bindings (render_signature)
    data_model_hash: str = ""     # SHA256 of data model / state snapshot JSON (render_signature)

    def to_canonical_dict(self) -> dict:
        return {
            "componentHash":     self.component_hash,
            "cssHash":           self.css_hash,
            "locHash":           self.loc_hash,
            "seedHash":          self.seed_hash,
            "featureFlagsHash":  self.feature_flags_hash,
            "browserProfileHash": self.browser_profile_hash,
            "propsHash":         self.props_hash,
            "dataModelHash":     self.data_model_hash,
        }


@dataclass
class SemanticContext:
    """DOM/text content extracted from the UI.

    RULE-VISUAL-DELTA-03: If semantic content changes, always re-analyze,
    even if the visual diff is below the pHash threshold.
    """
    texts: list[str] = field(default_factory=list)     # visible text elements
    elements: list[str] = field(default_factory=list)  # UI element types (button, input…)
    headings: list[str] = field(default_factory=list)  # h1/h2/h3 content

    def to_canonical_dict(self) -> dict:
        return {
            "texts":    sorted(self.texts),
            "elements": sorted(self.elements),
            "headings": sorted(self.headings),
        }


@dataclass
class DependencyManifest:
    """Hashes of source files that can affect the rendered screen.

    RULE-VISUAL-DELTA-ENGINE v2 (ARCHITECT DECISION 2026-04-15):
    If ANY dependency changes since the last validation, the cached result
    is invalid — even if the visual output appears pixel-identical.

    Covers:
      - Razor/Blazor components (.razor, .razor.cs)
      - CSS / design tokens
      - Localization resources (.json, .resx)
      - Shared layouts and dialog/drawer shells
      - Test journey definitions
      - mustShow / mustNotShow rule files

    dependency_source:
      MANUAL  — caller provided hashes explicitly
      AUTO    — engine scanned filesystem automatically
      HYBRID  — partial auto + caller overrides
    """
    component_hashes: dict[str, str] = field(default_factory=dict)    # filename → sha256
    css_hashes: dict[str, str] = field(default_factory=dict)
    localization_hashes: dict[str, str] = field(default_factory=dict)
    layout_hashes: dict[str, str] = field(default_factory=dict)
    journey_hashes: dict[str, str] = field(default_factory=dict)
    rule_hashes: dict[str, str] = field(default_factory=dict)          # mustShow/mustNotShow rule files
    dependency_source: str = "MANUAL"   # MANUAL | AUTO | HYBRID

    def is_empty(self) -> bool:
        """True when no dependency hashes have been provided."""
        return not any([
            self.component_hashes,
            self.css_hashes,
            self.localization_hashes,
            self.layout_hashes,
            self.journey_hashes,
            self.rule_hashes,
        ])

    def to_canonical_dict(self) -> dict:
        """Stable sorted representation — file order must not affect hash."""
        return {
            "componentHashes":    {k: v for k, v in sorted(self.component_hashes.items())},
            "cssHashes":          {k: v for k, v in sorted(self.css_hashes.items())},
            "localizationHashes": {k: v for k, v in sorted(self.localization_hashes.items())},
            "layoutHashes":       {k: v for k, v in sorted(self.layout_hashes.items())},
            "journeyHashes":      {k: v for k, v in sorted(self.journey_hashes.items())},
            "ruleHashes":         {k: v for k, v in sorted(self.rule_hashes.items())},
            "dependencySource":   self.dependency_source,
        }


@dataclass
class VisualFingerprint:
    """Complete validation fingerprint for a single screenshot."""
    screen_key: str
    image_sha256: str
    normalized_image_sha256: str
    validation_context_sha256: str
    render_input_sha256: str
    validation_fingerprint_sha256: str   # composite of all three
    policy_version: str = VISUAL_VALIDATION_POLICY_VERSION
    perceptual_hash: str = ""            # RULE-VISUAL-DELTA-02: dHash for visual similarity
    semantic_sha256: str = ""            # RULE-VISUAL-DELTA-03: DOM/text content hash
    # RULE-VISUAL-DELTA-ENGINE v2 fields
    dependency_sha256: str = ""          # SHA256(DependencyManifest) — components/CSS/loc/rules
    validator_version: str = ""          # version of the AI analysis engine
    ruleset_version: str = ""            # version of mustShow/mustNotShow rule set
    mask_version: str = ""               # version of image normalization masks
    source_commit_sha: str = ""          # git commit of source when validated


# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_str(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _sha256_dict(d: dict) -> str:
    canonical = json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return _sha256_str(canonical)


# ---------------------------------------------------------------------------
# Perceptual hash (RULE-VISUAL-DELTA-02)
# ---------------------------------------------------------------------------

def compute_phash(data: bytes, hash_size: int = 8) -> str:
    """64-bit dHash on raw image bytes.

    Pure-Python implementation: samples ``hash_size*hash_size + 1`` values
    uniformly from the byte array, then builds a difference hash by comparing
    adjacent samples.  For production use with real screenshots, replace the
    sampling step with PIL-based greyscale pixel extraction
    (image.convert("L").resize((9, 8))) — the interface stays stable.

    Returns a 16-character hex string (64 bits).
    """
    n = hash_size * hash_size  # 64 comparison slots
    length = len(data)
    if length == 0:
        return "0" * 16

    sample_count = n + 1  # need one extra for pairwise comparison
    step = max(1.0, length / sample_count)
    samples = [data[min(int(i * step), length - 1)] for i in range(sample_count)]

    bits = 0
    for i in range(n):
        if samples[i] > samples[i + 1]:
            bits |= (1 << i)
    return format(bits, "016x")


def phash_similarity(hash1: str, hash2: str) -> float:
    """Hamming-based similarity in [0.0, 1.0] between two 16-char hex pHashes.

    1.0 = identical, 0.0 = completely different (all 64 bits differ).
    """
    bits1 = int(hash1, 16)
    bits2 = int(hash2, 16)
    diff = bin(bits1 ^ bits2).count("1")
    return 1.0 - (diff / 64.0)


# ---------------------------------------------------------------------------
# Image hash helpers
# ---------------------------------------------------------------------------

def hash_image_file(path: str | Path) -> str:
    """SHA256 of the raw PNG/JPEG bytes — bit-identical identity."""
    return _sha256_bytes(Path(path).read_bytes())


def hash_normalized_image(
    path: str | Path,
    config: "NormalizationConfig | None" = None,
) -> str:
    """SHA256 of a deterministically normalized screenshot.

    RULE-VISUAL-NORMALIZATION pipeline (ARCHITECT DECISION 2026-04-15):
      1. Open with PIL (strips file-level metadata automatically)
      2. Resize to config.canvas_size using LANCZOS (deterministic)
      3. Convert to RGB (removes alpha channel — avoids alpha noise)
      4. Apply mask regions: fill each MaskRegion with MASK_FILL_COLOR
      5. Optional grayscale (stabilizes font rendering differences)
      6. Optional Gaussian blur (stabilizes anti-alias sub-pixel noise)
      7. Serialize to raw pixel bytes (tobytes()) → SHA256

    The result is deterministic: same visual content + same config → same hash.

    Raises:
        RuntimeError: if Pillow is not installed.
    """
    if not _PIL_AVAILABLE:
        raise RuntimeError(
            "RULE-VISUAL-NORMALIZATION requires Pillow. "
            "Install it: pip install Pillow"
        )

    cfg = config or DEFAULT_NORMALIZATION

    try:
        img = Image.open(path)
    except Exception:
        # Fallback: file is not a parseable image (e.g. synthetic test data).
        # Raw SHA256 is still deterministic for identical bytes.
        return hash_image_file(path)

    # Step 2 — deterministic canvas
    img = img.resize(cfg.canvas_size, Image.LANCZOS)

    # Step 3 — strip alpha
    img = img.convert("RGB")

    # Step 4 — blank volatile regions
    if cfg.mask_regions:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        for region in cfg.mask_regions:
            draw.rectangle(region.to_pil_box(), fill=MASK_FILL_COLOR)

    # Step 5 — optional grayscale
    if cfg.grayscale:
        img = img.convert("L")

    # Step 6 — optional blur
    if cfg.blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=cfg.blur_radius))

    # Step 7 — deterministic bytes → SHA256
    raw_pixels = img.tobytes()
    return _sha256_bytes(raw_pixels)


# ---------------------------------------------------------------------------
# Fingerprint builder
# ---------------------------------------------------------------------------

class VisualFingerprintBuilder:
    """Builds a VisualFingerprint from a screenshot path + context objects.

    Usage::

        builder = VisualFingerprintBuilder()
        fp = builder.build(
            screenshot_path="screenshots/customer-admin-users.png",
            context=ValidationContext(
                screen_key="customer-admin-users",
                device="desktop",
                locale="da-DK",
                must_show=["Brugere"],
                must_not_show=["shared.", "â€™"],
            ),
            render_inputs=RenderInputs(
                component_hash="abc123",
                css_hash="def456",
            ),
        )
        print(fp.validation_fingerprint_sha256)
    """

    def build(
        self,
        screenshot_path: str | Path,
        context: ValidationContext,
        render_inputs: Optional[RenderInputs] = None,
        semantic: Optional["SemanticContext"] = None,
        dependencies: Optional["DependencyManifest"] = None,
        validator_version: str = "",
        ruleset_version: str = "",
        mask_version: str = "",
        source_commit_sha: str = "",
        normalization_config: Optional["NormalizationConfig"] = None,
    ) -> VisualFingerprint:
        render_inputs = render_inputs or RenderInputs()

        raw_bytes               = Path(screenshot_path).read_bytes()
        image_sha256            = hash_image_file(screenshot_path)
        normalized_image_sha256 = hash_normalized_image(screenshot_path, normalization_config)
        context_sha256          = _sha256_dict(context.to_canonical_dict())
        render_sha256           = _sha256_dict(render_inputs.to_canonical_dict())
        perceptual_hash         = compute_phash(raw_bytes)
        semantic_sha256         = _sha256_dict(semantic.to_canonical_dict()) if semantic else ""
        dependency_sha256       = _sha256_dict(dependencies.to_canonical_dict()) if dependencies else ""

        # Composite fingerprint: normalized image + context + render inputs
        composite_input = normalized_image_sha256 + context_sha256 + render_sha256
        fingerprint_sha256 = _sha256_str(composite_input)

        return VisualFingerprint(
            screen_key=context.screen_key,
            image_sha256=image_sha256,
            normalized_image_sha256=normalized_image_sha256,
            validation_context_sha256=context_sha256,
            render_input_sha256=render_sha256,
            validation_fingerprint_sha256=fingerprint_sha256,
            policy_version=context.policy_version,
            perceptual_hash=perceptual_hash,
            semantic_sha256=semantic_sha256,
            dependency_sha256=dependency_sha256,
            validator_version=validator_version,
            ruleset_version=ruleset_version,
            mask_version=mask_version,
            source_commit_sha=source_commit_sha,
        )

    def build_context_hash(self, context: ValidationContext) -> str:
        return _sha256_dict(context.to_canonical_dict())

    def build_render_hash(self, render_inputs: RenderInputs) -> str:
        return _sha256_dict(render_inputs.to_canonical_dict())


# ---------------------------------------------------------------------------
# Production fingerprint validation — RULE-VISUAL-DELTA-ENGINE v2
# ---------------------------------------------------------------------------

class FingerprintValidationError(ValueError):
    """Raised when a fingerprint is incomplete in production mode."""


def validate_fingerprint(fp: "VisualFingerprint") -> None:
    """FAIL-FAST: raise FingerprintValidationError if required v2 fields are empty.

    Call this before recording or skip-checking in production mode.
    Empty fields are only allowed in test / migration mode.
    """
    missing: list[str] = []
    if not fp.semantic_sha256:
        missing.append("semantic_sha256")
    if not fp.dependency_sha256:
        missing.append("dependency_sha256")
    if not fp.validator_version:
        missing.append("validator_version")
    if not fp.ruleset_version:
        missing.append("ruleset_version")
    if not fp.mask_version:
        missing.append("mask_version")

    if missing:
        raise FingerprintValidationError(
            f"FAIL-FAST: Incomplete fingerprint for '{fp.screen_key}'. "
            f"Missing production fields: {', '.join(missing)}. "
            "Pass these fields to VisualFingerprintBuilder.build() or "
            "use non-production mode."
        )
