"""SLICE_6 — Work item CSV analysis.

Parses a semicolon- or comma-delimited CSV of work items, extracts
keywords, groups by Area Path into capabilities, and emits one feature
entry per work item.

Public API
----------
analyze_work_items(csv_path: str) -> dict
    Returns ``{"capabilities": [...], "features": [...], "errors": [...]}``.
"""

from __future__ import annotations

import csv
import io
import os
import re
from typing import Dict, List

# ---------------------------------------------------------------------------
# Danish + English stopwords (hardcoded)
# ---------------------------------------------------------------------------

_STOPWORDS: frozenset = frozenset([
    # English
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "her", "was", "one", "our", "out", "day", "get", "has", "him", "his",
    "how", "man", "new", "now", "old", "see", "two", "way", "who", "its",
    "did", "let", "put", "say", "she", "too", "use", "that", "this", "with",
    "been", "from", "have", "more", "than", "they", "when", "will", "your",
    "also", "back", "into", "just", "like", "make", "most", "over", "such",
    "then", "time", "very", "well", "what", "were", "which", "while", "would",
    "about", "after", "again", "could", "every", "first", "going", "great",
    "other", "right", "should", "their", "there", "these", "those", "where",
    # Danish
    "det", "den", "der", "som", "til", "fra", "med", "ved", "for", "kan",
    "har", "var", "vil", "est", "han", "hun", "sig", "sin", "sit", "sine",
    "man", "men", "men", "men", "ikke", "skal", "blive", "efter", "under",
    "over", "alle", "hver", "ingen", "noget", "nogle", "dette", "disse",
    "disse", "enten", "eller", "eller", "hvis", "naar", "naar", "ngen",
    "ogsaa", "aldrig", "altid", "mere", "mest", "men", "men", "men",
    "naar", "naar", "naar", "endnu", "ogs", "ved", "som", "som", "hvor",
    "hvad", "hvem", "hvilken", "hvilket", "hvilke", "her", "der", "saa",
    "got", "att", "och", "men", "typ", "bra", "ska", "ett", "och",
    # Short filler
    "www", "http", "https", "com", "org", "net",
])

# ---------------------------------------------------------------------------
# HTML / text helpers
# ---------------------------------------------------------------------------

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ENTITY_MAP = {
    "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
    "&quot;": '"', "&#39;": "'", "&apos;": "'",
}
_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    text = _HTML_TAG_RE.sub(" ", text)
    for entity, replacement in _HTML_ENTITY_MAP.items():
        text = text.replace(entity, replacement)
    return text


def _normalise(text: str) -> str:
    """Strip HTML, lowercase, remove punctuation, collapse whitespace."""
    text = _strip_html(text)
    text = text.lower()
    text = _PUNCTUATION_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _extract_keywords(normalised_text: str) -> List[str]:
    """Return deduped keywords: words length >= 3, not in stopwords, in order of first appearance."""
    seen: set = set()
    result: List[str] = []
    for word in normalised_text.split():
        if len(word) >= 3 and word not in _STOPWORDS and word not in seen:
            seen.add(word)
            result.append(word)
    return result


# ---------------------------------------------------------------------------
# Area Path normalisation
# ---------------------------------------------------------------------------

_NON_WORD_RE = re.compile(r"[^\w]+")


def _area_to_name(area_path: str) -> str:
    """Convert ``SMS-service\\General`` → ``sms_service_general``."""
    name = area_path.lower()
    name = _NON_WORD_RE.sub("_", name)
    name = name.strip("_")
    return name or "unknown"


# ---------------------------------------------------------------------------
# Delimiter detection
# ---------------------------------------------------------------------------

def _detect_delimiter(first_line: str) -> str:
    """Return ``';'`` or ``','`` based on which appears more in *first_line*."""
    if first_line.count(";") > first_line.count(","):
        return ";"
    return ","


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_work_items(csv_path: str) -> Dict:
    """Parse *csv_path* and extract capabilities, features, and keyword data.

    Parameters
    ----------
    csv_path:
        Absolute path to the UTF-8 CSV file.

    Returns
    -------
    dict
        ``{"capabilities": [...], "features": [...], "errors": [...]}``
    """
    errors: List[str] = []

    if not os.path.isfile(csv_path):
        errors.append(f"CSV not found: '{csv_path}'")
        return {"capabilities": [], "features": [], "errors": errors}

    try:
        with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as fh:
            raw = fh.read()
    except OSError as exc:
        errors.append(str(exc))
        return {"capabilities": [], "features": [], "errors": errors}

    if not raw.strip():
        return {"capabilities": [], "features": [], "errors": errors}

    first_line = raw.split("\n", 1)[0]
    delimiter = _detect_delimiter(first_line)

    # Raise the field size limit to handle large description/criteria fields
    csv.field_size_limit(10 * 1024 * 1024)  # 10 MB
    reader = csv.DictReader(io.StringIO(raw), delimiter=delimiter)

    # area_name → aggregation bucket
    area_buckets: Dict[str, Dict] = {}
    all_features: List[Dict] = []

    for row in reader:
        item_id = (row.get("ID") or "").strip()
        title = (row.get("Title") or "").strip()

        # Skip rows with neither ID nor title (blank rows, secondary header lines)
        if not item_id and not title:
            continue

        desc = row.get("Description") or ""
        criteria = row.get("Acceptance Criteria") or ""
        tags = row.get("Tags") or ""
        area_path = (row.get("Area Path") or "").strip()

        combined = f"{title} {desc} {criteria} {tags}"
        norm = _normalise(combined)
        keywords = _extract_keywords(norm)[:20]  # cap per item

        area_name = _area_to_name(area_path) if area_path else "unknown"

        all_features.append({
            "id": item_id,
            "title": title,
            "capability": area_name,
            "keywords": sorted(keywords),
        })

        # Aggregate keyword frequencies per area
        if area_name not in area_buckets:
            area_buckets[area_name] = {
                "area": area_path,
                "kw_freq": {},
                "count": 0,
            }
        bucket = area_buckets[area_name]
        bucket["count"] += 1
        for kw in keywords:
            bucket["kw_freq"][kw] = bucket["kw_freq"].get(kw, 0) + 1

    # Build capabilities — sorted by area name (deterministic)
    capabilities: List[Dict] = []
    for area_name in sorted(area_buckets):
        bucket = area_buckets[area_name]
        # Top 10 keywords: sort by descending frequency, then lexicographic
        top_kws = sorted(
            bucket["kw_freq"],
            key=lambda k: (-bucket["kw_freq"][k], k),
        )[:10]
        capabilities.append({
            "name": area_name,
            "area": bucket["area"],
            "keywords": sorted(top_kws),
            "item_count": bucket["count"],
        })

    # Sort features by ID (lexicographic of the string representation)
    all_features.sort(key=lambda f: f["id"])

    return {
        "capabilities": capabilities,
        "features": all_features,
        "errors": errors,
    }
