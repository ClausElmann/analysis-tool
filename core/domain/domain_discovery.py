"""Domain discovery engine — identifies business domains from all scanned assets.

Two complementary strategies:

1. **Vocabulary matching** — scores known domain seeds against asset keywords
   (``domain_asset_matcher._DOMAIN_KEYWORDS``).

2. **Path-prefix clustering** — groups assets by shared namespace tokens
   extracted from their ``path``/``id`` fields, surfacing custom/unknown
   domains not in the seed vocabulary.

Discovered domains are normalised to ``snake_case``, deduplicated, and
sorted for deterministic output.  All output is written as atomic JSON.

Output format (``discovered_domains.json``)::

    [
      {
        "domain":         "identity_access",
        "confidence":     0.93,
        "keywords":       ["auth", "login", "role", "token"],
        "sources":        ["code", "sql", "work_items"],
        "estimated_size": "large",
        "reasoning":      ["42 assets matched across 3 source type(s)"]
      }
    ]
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.domain.domain_asset_matcher import _DOMAIN_KEYWORDS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Minimum matching assets for a candidate to be returned
_MIN_MATCH_COUNT: int = 2

# Limit content scanning to avoid huge blobs
_CONTENT_SCAN_LIMIT: int = 1_000

# Asset count thresholds for estimated_size
_SIZE_SMALL: int = 5
_SIZE_LARGE: int = 25

# Tokens that carry no domain signal
_NOISE: frozenset = frozenset(
    {
        "service", "services", "controller", "handler", "manager",
        "helper", "util", "utils", "model", "models", "dto", "dtos",
        "data", "base", "abstract", "interface", "impl",
        "implementation", "test", "tests", "spec", "common", "shared",
        "core", "api", "web", "app", "application", "infrastructure",
        "domain", "bin", "obj", "src", "lib", "the", "and", "or",
        "in", "of", "for", "to", "at", "by", "with", "a", "an",
    }
)

# Map asset.type → source category for diversity scoring
_TYPE_SOURCE_MAP: Dict[str, str] = {
    "code_file":          "code",
    "sql":                "sql",
    "sql_table":          "sql",
    "sql_procedure":      "sql",
    "wiki_section":       "wiki",
    "work_items_batch":   "work_items",
    "git_insights_batch": "git",
    "labels_namespace":   "labels",
    "pdf_section":        "pdf",
    "batch":              "batch",
    "event":              "events",
    "webhook":            "events",
    "background":         "batch",
}

_CAMEL_PAT = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


# ---------------------------------------------------------------------------
# DomainCandidate
# ---------------------------------------------------------------------------


@dataclass
class DomainCandidate:
    """A single discovered business domain candidate."""

    domain: str
    confidence: float
    keywords: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    estimated_size: str = "medium"   # "small" | "medium" | "large"
    reasoning: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain":         self.domain,
            "confidence":     round(self.confidence, 4),
            "keywords":       sorted(set(self.keywords)),
            "sources":        sorted(set(self.sources)),
            "estimated_size": self.estimated_size,
            "reasoning":      list(dict.fromkeys(self.reasoning)),  # dedup, keep order
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DomainCandidate":
        return cls(
            domain=str(d.get("domain", "")),
            confidence=float(d.get("confidence", 0.0)),
            keywords=list(d.get("keywords", [])),
            sources=list(d.get("sources", [])),
            estimated_size=str(d.get("estimated_size", "medium")),
            reasoning=list(d.get("reasoning", [])),
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_domain(text: str) -> str:
    """Convert any text fragment to a normalised ``snake_case`` domain name."""
    split = _CAMEL_PAT.sub("_", text).lower()
    clean = re.sub(r"[^a-z0-9]+", "_", split).strip("_")
    return clean[:50]


def _source_category(asset: Dict[str, Any]) -> str:
    return _TYPE_SOURCE_MAP.get(asset.get("type", ""), "other")


def _estimated_size(count: int) -> str:
    if count <= _SIZE_SMALL:
        return "small"
    if count <= _SIZE_LARGE:
        return "medium"
    return "large"


def _confidence(match_count: int, source_count: int, keyword_hit_count: int) -> float:
    """Compute 0–1 confidence from match statistics.

    * asset_score:   up to 0.70 (30+ matching assets → full score)
    * diversity:     up to 0.15 (5 source types → full bonus)
    * keyword_depth: up to 0.10 (8+ distinct keywords → full bonus)
    """
    asset_score = min(match_count / 30.0, 0.70)
    diversity   = min(source_count      / 5.0,  1.0) * 0.15
    kw_depth    = min(keyword_hit_count / 8.0,  1.0) * 0.10
    return round(min(asset_score + diversity + kw_depth, 0.99), 4)


def _asset_text(asset: Dict[str, Any]) -> str:
    """Return combined, lowercased, length-limited searchable text."""
    return (
        (asset.get("id")   or "")
        + " "
        + (asset.get("path") or "")
        + " "
        + (str(asset.get("content") or "")[:_CONTENT_SCAN_LIMIT])
    ).lower()


# ---------------------------------------------------------------------------
# DomainDiscoveryEngine
# ---------------------------------------------------------------------------


class DomainDiscoveryEngine:
    """Discovers all business domains present in a scanned asset corpus."""

    # ------------------------------------------------------------------
    # Internal: path-token extraction

    @staticmethod
    def _path_tokens(asset: Dict[str, Any]) -> List[str]:
        """Extract meaningful lowercase tokens from an asset's path and id."""
        raw = (asset.get("path") or "") + " " + (asset.get("id") or "")
        parts = re.split(r"[/\\.\-_ ]", raw)
        tokens: List[str] = []
        for part in parts:
            sub = _CAMEL_PAT.sub(" ", part).split()
            tokens.extend(
                t.lower()
                for t in sub
                if len(t) >= 3 and t.lower() not in _NOISE
            )
        return tokens

    # ------------------------------------------------------------------
    # Phase 1 — known vocabulary matching

    def _discover_from_vocabulary(
        self, assets: List[Dict[str, Any]]
    ) -> List[DomainCandidate]:
        """Score each seed domain in ``_DOMAIN_KEYWORDS`` against *assets*."""
        candidates: List[DomainCandidate] = []

        for domain_name, keywords in sorted(_DOMAIN_KEYWORDS.items()):
            patterns = {
                kw: re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
                for kw in keywords
            }

            matching_assets: int = 0
            keyword_hits: set = set()
            source_categories: set = set()

            for asset in assets:
                text = _asset_text(asset)
                hit = False
                for kw, pat in patterns.items():
                    if pat.search(text):
                        hit = True
                        keyword_hits.add(kw)
                if hit:
                    matching_assets += 1
                    source_categories.add(_source_category(asset))

            if matching_assets < _MIN_MATCH_COUNT:
                continue

            conf = _confidence(matching_assets, len(source_categories), len(keyword_hits))
            candidates.append(
                DomainCandidate(
                    domain=domain_name,
                    confidence=conf,
                    keywords=sorted(keyword_hits),
                    sources=sorted(source_categories),
                    estimated_size=_estimated_size(matching_assets),
                    reasoning=[
                        f"{matching_assets} assets matched across "
                        f"{len(source_categories)} source type(s)"
                    ],
                )
            )

        return candidates

    # ------------------------------------------------------------------
    # Phase 2 — path-prefix clustering

    def _discover_from_paths(
        self, assets: List[Dict[str, Any]]
    ) -> List[DomainCandidate]:
        """Surface new domain candidates from shared path-token prefixes."""
        # Build token → asset count + source set
        token_data: Dict[str, Dict[str, Any]] = {}
        for asset in assets:
            for token in self._path_tokens(asset):
                if token not in token_data:
                    token_data[token] = {"count": 0, "sources": set()}
                token_data[token]["count"] += 1
                token_data[token]["sources"].add(_source_category(asset))

        # Collect known vocabulary tokens to skip (handled by phase 1)
        all_known_kws: set = set()
        for kws in _DOMAIN_KEYWORDS.values():
            all_known_kws.update(kws)

        candidates: List[DomainCandidate] = []
        for token, td in sorted(token_data.items()):
            if td["count"] < _MIN_MATCH_COUNT:
                continue
            if token in all_known_kws or token in _NOISE:
                continue

            domain_name = _normalize_domain(token)
            if not domain_name:
                continue

            sources = sorted(td["sources"])
            conf = _confidence(td["count"], len(sources), 0)
            candidates.append(
                DomainCandidate(
                    domain=domain_name,
                    confidence=conf,
                    keywords=[token],
                    sources=sources,
                    estimated_size=_estimated_size(td["count"]),
                    reasoning=[
                        f"token '{token}' appears in {td['count']} asset paths"
                    ],
                )
            )

        return candidates

    # ------------------------------------------------------------------
    # Merge

    @staticmethod
    def _merge_candidates(
        *candidate_lists: List[DomainCandidate],
    ) -> List[DomainCandidate]:
        """Merge multiple lists, deduplicating by domain name."""
        by_domain: Dict[str, DomainCandidate] = {}

        for candidates in candidate_lists:
            for c in candidates:
                if c.domain not in by_domain:
                    by_domain[c.domain] = c
                else:
                    existing = by_domain[c.domain]
                    by_domain[c.domain] = DomainCandidate(
                        domain=existing.domain,
                        confidence=max(existing.confidence, c.confidence),
                        keywords=sorted(set(existing.keywords) | set(c.keywords)),
                        sources=sorted(set(existing.sources)  | set(c.sources)),
                        estimated_size=(
                            existing.estimated_size
                            if existing.confidence >= c.confidence
                            else c.estimated_size
                        ),
                        reasoning=list(
                            dict.fromkeys(existing.reasoning + c.reasoning)
                        ),
                    )

        # Stable sort: confidence desc, then domain name asc
        return sorted(
            by_domain.values(),
            key=lambda c: (-c.confidence, c.domain),
        )

    # ------------------------------------------------------------------
    # Public API

    def discover(self, assets: List[Dict[str, Any]]) -> List[DomainCandidate]:
        """Identify all domain candidates from *assets*.

        Returns a sorted, deduplicated list of ``DomainCandidate`` objects.
        Output is deterministic for the same input.
        """
        if not assets:
            return []

        phase1 = self._discover_from_vocabulary(assets)
        phase2 = self._discover_from_paths(assets)
        return self._merge_candidates(phase1, phase2)

    def save(self, candidates: List[DomainCandidate], path: str) -> None:
        """Atomically write *candidates* to *path* as JSON."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(
                [c.to_dict() for c in candidates],
                fh,
                indent=2,
                ensure_ascii=False,
                sort_keys=False,
            )
        os.replace(tmp, path)

    def load(self, path: str) -> List[DomainCandidate]:
        """Load previously saved candidates from *path*.  Returns ``[]`` if absent."""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return [DomainCandidate.from_dict(d) for d in data]
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            pass
        return []
