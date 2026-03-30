"""AI asset scanner — adaptive chunking layer.

Produces a flat list of Asset dicts from all configured data sources.

Each Asset dict contains:
    type        : discriminator string (see ASSET_TYPES below)
    id          : stable, deterministic string key (never changes unless content restructures)
    group_size  : number of logical items/pages in this group
    content_hash: SHA-256 hex digest of the group's canonical content (for change detection)
    ... type-specific fields

Grouping rules
--------------
pdf_section
    Use TOC if available; else split pages on heading font-size heuristics.
    id = "pdf:{filename}:{section_index}" (0-based)

wiki_section
    Split each .md file on ## (level 2+) headings into sections.
    id = "wiki:{filename}:{section_index}" (0-based within file)

work_items_batch
    Batch work-item feature records in groups of WORK_ITEMS_BATCH_SIZE.
    id = "work_items:batch:{batch_index}" (0-based)

git_insights_batch
    Batch git insight records in groups of GIT_INSIGHTS_BATCH_SIZE.
    id = "git_insights:batch:{batch_index}" (0-based)

labels_namespace
    One asset per i18n namespace prefix from label_map.json.
    id = "labels:ns:{namespace}"

code_file
    One file = one asset.
    id = "code:{relative_path_forward_slashes}"

Hard guarantees
---------------
- All IDs are stable (same input → same ID, always).
- No duplication: each source record appears in exactly one group.
- No overlap: groups are non-overlapping windows over the source data.
- Grouping is deterministic: sorted inputs, fixed batch windows.
"""

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WORK_ITEMS_BATCH_SIZE: int = 100
GIT_INSIGHTS_BATCH_SIZE: int = 100

ASSET_TYPES = frozenset({
    "pdf_section",
    "wiki_section",
    "work_items_batch",
    "git_insights_batch",
    "labels_namespace",
    "code_file",
})

# Code file extensions considered scannable assets
_CODE_EXTENSIONS = {".ts", ".cs", ".sql", ".html", ".scss", ".css", ".py"}

# Directories to skip when scanning code files
_SKIP_DIRS = frozenset({
    "node_modules", "obj", "bin", "dist", ".git", ".vs",
    "__pycache__", ".angular", "coverage",
})

# Wiki: match level-2+ headings that start a new section
_WIKI_SECTION_HEADING_RE = re.compile(r'^(#{2,6})\s+(.+)', re.MULTILINE)

# PDF font-size thresholds (PyMuPDF point units) — mirrors execution_engine.py
_PDF_MAX_HEADING_SIZE: float = 40.0
_PDF_SECTION_SIZE_MIN: float = 13.0  # any heading that starts a section


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    """Return a hex SHA-256 digest of *text* encoded as UTF-8."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _stable_json(obj: Any) -> str:
    """Return a deterministic JSON string (sorted keys, no whitespace)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _safe_filename_segment(name: str) -> str:
    """Normalise *name* for use inside an asset ID: lowercase, underscores."""
    return re.sub(r'[^a-z0-9_.-]', '_', name.lower()).strip('_')


def _load_json(path: str) -> Any:
    """Load a JSON file; return None on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _read_text(path: str) -> Optional[str]:
    """Read a text file; return None on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


# ---------------------------------------------------------------------------
# PDF helpers (mirrors execution_engine.py logic extended for chunking)
# ---------------------------------------------------------------------------

def _pdf_toc_sections(doc: Any, fpath: str) -> List[Dict]:
    """Split a PDF into sections using its table of contents.

    Returns a list of section dicts:
        {"pages": [int, ...], "heading": str, "level": int, "content": str}
    """
    toc = doc.get_toc()  # [[level, title, page_num], ...]
    if not toc:
        return []

    page_count = doc.page_count

    def _page_text(p: int) -> str:
        try:
            return doc[p].get_text()
        except Exception:
            return ""

    # Build section windows: each TOC entry starts a new section
    # Sections cover [entry_page, next_entry_page - 1]
    _seen_keys: set = set()
    sections: List[Dict] = []

    # Normalise: use 0-based page indices
    entries: List[Tuple[int, str, int]] = []
    for entry in toc:
        level: int = int(entry[0]) if entry else 1
        title: str = str(entry[1]).strip() if len(entry) > 1 else ""
        page_1based: int = int(entry[2]) if len(entry) > 2 else 1
        page_0based: int = max(0, page_1based - 1)
        if not title:
            continue
        key = (level, title, page_0based)
        if key in _seen_keys:
            continue
        _seen_keys.add(key)
        entries.append((level, title, page_0based))

    for idx, (level, title, start_page) in enumerate(entries):
        end_page = entries[idx + 1][2] - 1 if idx + 1 < len(entries) else page_count - 1
        end_page = min(end_page, page_count - 1)
        # Guard: ensure at least the start page is included even when two
        # consecutive TOC entries land on the same physical page.
        end_page = max(start_page, end_page)
        pages = list(range(start_page, end_page + 1))
        content = "\n".join(_page_text(p) for p in pages)
        sections.append({
            "heading": title,
            "level": level,
            "pages": pages,
            "content": content,
        })

    return sections


def _pdf_heading_sections(doc: Any) -> List[Dict]:
    """Split a PDF into sections using font-size heading heuristics.

    Any span with font size >= _PDF_SECTION_SIZE_MIN and <= _PDF_MAX_HEADING_SIZE
    is treated as the start of a new section.
    """
    page_count = doc.page_count
    # Collect (page_idx, heading_text) pairs
    headings: List[Tuple[int, str]] = []
    seen: set = set()

    for page_num in range(page_count):
        try:
            blocks = doc[page_num].get_text("dict")["blocks"]
        except Exception:
            continue
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_text = " ".join(s["text"] for s in spans).strip()
                if not line_text or len(line_text) < 3:
                    continue
                max_size = max((s["size"] for s in spans), default=0.0)
                if max_size > _PDF_MAX_HEADING_SIZE:
                    continue
                if max_size >= _PDF_SECTION_SIZE_MIN:
                    key = (page_num, line_text)
                    if key not in seen:
                        seen.add(key)
                        headings.append((page_num, line_text))
                    break  # one heading per page-block is enough

    if not headings:
        # No headings found — treat entire document as one section
        full_text = "\n".join(
            doc[p].get_text() for p in range(page_count)
        )
        return [{"heading": "Document", "level": 1,
                 "pages": list(range(page_count)), "content": full_text}]

    # Build page windows
    sections: List[Dict] = []
    for idx, (start_page, heading) in enumerate(headings):
        end_page = headings[idx + 1][0] - 1 if idx + 1 < len(headings) else page_count - 1
        end_page = min(end_page, page_count - 1)
        pages = list(range(start_page, end_page + 1))
        content = "\n".join(doc[p].get_text() for p in pages)
        sections.append({
            "heading": heading,
            "level": 1,
            "pages": pages,
            "content": content,
        })

    return sections


# ---------------------------------------------------------------------------
# Wiki helpers
# ---------------------------------------------------------------------------

def _wiki_split_sections(content: str, filename: str) -> List[Dict]:
    """Split markdown *content* on level-2+ headings.

    The preamble before the first heading (if any) is treated as section 0
    with heading = filename stem.

    Returns list of dicts:
        {"heading": str, "level": int, "line_start": int, "line_end": int, "content": str}
    """
    lines = content.splitlines(keepends=True)
    # Find all heading positions
    heading_positions: List[Tuple[int, int, str]] = []  # (line_index, level, text)
    for i, line in enumerate(lines):
        m = _WIKI_SECTION_HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            heading_text = m.group(2).strip()
            heading_positions.append((i, level, heading_text))

    if not heading_positions:
        # No headings — whole file is one section
        return [{
            "heading": os.path.splitext(filename)[0],
            "level": 1,
            "line_start": 0,
            "line_end": len(lines) - 1,
            "content": content,
        }]

    sections: List[Dict] = []

    # Preamble before first heading
    first_heading_line = heading_positions[0][0]
    if first_heading_line > 0:
        preamble = "".join(lines[:first_heading_line])
        if preamble.strip():
            sections.append({
                "heading": os.path.splitext(filename)[0],
                "level": 1,
                "line_start": 0,
                "line_end": first_heading_line - 1,
                "content": preamble,
            })

    # Sections from headings
    for idx, (line_idx, level, heading_text) in enumerate(heading_positions):
        end_line = (
            heading_positions[idx + 1][0] - 1
            if idx + 1 < len(heading_positions)
            else len(lines) - 1
        )
        section_content = "".join(lines[line_idx: end_line + 1])
        sections.append({
            "heading": heading_text,
            "level": level,
            "line_start": line_idx,
            "line_end": end_line,
            "content": section_content,
        })

    return sections


# ---------------------------------------------------------------------------
# AssetScanner
# ---------------------------------------------------------------------------

class AssetScanner:
    """Scans all configured data sources and returns grouped Asset dicts.

    Parameters
    ----------
    data_root:
        Directory containing pipeline JSON outputs (data/).
    wiki_root:
        Root directory of wiki .md files.
    raw_root:
        Directory for raw inputs (PDFs, etc.).
    solution_root:
        Root of the source code solution (for code file scanning).
    """

    def __init__(
        self,
        data_root: str,
        wiki_root: str = "",
        raw_root: str = "",
        solution_root: str = "",
    ) -> None:
        self.data_root = os.path.abspath(data_root)
        self.wiki_root = os.path.abspath(wiki_root) if wiki_root else ""
        self.raw_root = os.path.abspath(raw_root) if raw_root else ""
        self.solution_root = os.path.abspath(solution_root) if solution_root else ""

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def scan_all_assets(self) -> List[Dict]:
        """Scan all data sources and return a flat list of grouped Asset dicts.

        Groups are produced in a deterministic order:
            pdf_section → wiki_section → work_items_batch
            → git_insights_batch → labels_namespace → code_file
        """
        assets: List[Dict] = []
        assets.extend(self._scan_pdf_assets())
        assets.extend(self._scan_wiki_assets())
        assets.extend(self._scan_work_item_assets())
        assets.extend(self._scan_git_insight_assets())
        assets.extend(self._scan_label_assets())
        assets.extend(self._scan_code_assets())
        return assets

    # ------------------------------------------------------------------
    # PDF — STEP 1
    # ------------------------------------------------------------------

    def _scan_pdf_assets(self) -> List[Dict]:
        """Group PDF pages into sections.

        Strategy (per file):
          1. If TOC is available  → use _pdf_toc_sections()
          2. Else                 → use _pdf_heading_sections() (font-size heuristic)

        Asset id: "pdf:{filename}:{section_index}"
        """
        assets: List[Dict] = []

        try:
            import fitz  # type: ignore[import]
        except ImportError:
            return assets  # PyMuPDF not installed — skip silently

        search_dir = (
            self.raw_root
            if self.raw_root and os.path.isdir(self.raw_root)
            else self.solution_root
        )
        if not search_dir or not os.path.isdir(search_dir):
            return assets

        try:
            pdf_files = sorted(
                f for f in os.listdir(search_dir)
                if f.lower().endswith(".pdf")
                and os.path.isfile(os.path.join(search_dir, f))
            )
        except OSError:
            return assets

        for fname in pdf_files:
            fpath = os.path.join(search_dir, fname)
            fname_safe = _safe_filename_segment(fname)
            try:
                doc = fitz.open(fpath)
            except Exception:
                continue

            # Choose strategy
            toc = doc.get_toc()
            if toc:
                sections = _pdf_toc_sections(doc, fpath)
                strategy = "toc"
            else:
                sections = _pdf_heading_sections(doc)
                strategy = "font_size"

            for section_idx, section in enumerate(sections):
                asset_id = f"pdf:{fname}:{section_idx}"
                page_count = len(section["pages"])
                assets.append({
                    "type": "pdf_section",
                    "id": asset_id,
                    "group_size": page_count,
                    "file": fname,
                    "section_index": section_idx,
                    "heading": section["heading"],
                    "level": section.get("level", 1),
                    "pages": section["pages"],
                    "content": section["content"],
                    "strategy": strategy,
                    "content_hash": _sha256(section["content"]),
                })

        return assets

    # ------------------------------------------------------------------
    # Wiki — STEP 1
    # ------------------------------------------------------------------

    def _scan_wiki_assets(self) -> List[Dict]:
        """Split each wiki .md file on ## headings into section assets.

        Asset id: "wiki:{filename}:{section_index}"
        """
        assets: List[Dict] = []

        if not self.wiki_root or not os.path.isdir(self.wiki_root):
            return assets

        md_files = sorted(
            f for f in os.listdir(self.wiki_root)
            if f.lower().endswith(".md")
            and os.path.isfile(os.path.join(self.wiki_root, f))
        )

        for fname in md_files:
            fpath = os.path.join(self.wiki_root, fname)
            content = _read_text(fpath)
            if not content or not content.strip():
                continue

            sections = _wiki_split_sections(content, fname)
            fname_safe = _safe_filename_segment(fname)

            for section_idx, section in enumerate(sections):
                asset_id = f"wiki:{fname}:{section_idx}"
                assets.append({
                    "type": "wiki_section",
                    "id": asset_id,
                    "group_size": 1,              # one logical section
                    "file": fname,
                    "section_index": section_idx,
                    "heading": section["heading"],
                    "level": section["level"],
                    "line_start": section["line_start"],
                    "line_end": section["line_end"],
                    "content": section["content"],
                    "content_hash": _sha256(section["content"]),
                })

        return assets

    # ------------------------------------------------------------------
    # Work items — STEP 1
    # ------------------------------------------------------------------

    def _scan_work_item_assets(self) -> List[Dict]:
        """Batch work-item feature records in groups of WORK_ITEMS_BATCH_SIZE.

        Source: data/work_item_analysis.json → features[]
        Asset id: "work_items:batch:{batch_index}"
        """
        assets: List[Dict] = []
        source_path = os.path.join(self.data_root, "work_item_analysis.json")
        data = _load_json(source_path)
        if not data:
            return assets

        features: List[Dict] = data.get("features", [])
        if not features:
            return assets

        # Sort by id for deterministic batching
        features_sorted = sorted(features, key=lambda x: str(x.get("id", "")))

        batch_index = 0
        for i in range(0, len(features_sorted), WORK_ITEMS_BATCH_SIZE):
            batch = features_sorted[i: i + WORK_ITEMS_BATCH_SIZE]
            batch_content = _stable_json(batch)
            asset_id = f"work_items:batch:{batch_index}"
            assets.append({
                "type": "work_items_batch",
                "id": asset_id,
                "group_size": len(batch),
                "batch_index": batch_index,
                "item_ids": [str(item.get("id", "")) for item in batch],
                "items": batch,
                "content_hash": _sha256(batch_content),
            })
            batch_index += 1

        return assets

    # ------------------------------------------------------------------
    # Git insights — STEP 1
    # ------------------------------------------------------------------

    def _scan_git_insight_assets(self) -> List[Dict]:
        """Batch git insight records in groups of GIT_INSIGHTS_BATCH_SIZE.

        Source: data/git_insights.json → insights[]
        Asset id: "git_insights:batch:{batch_index}"
        """
        assets: List[Dict] = []
        source_path = os.path.join(self.data_root, "git_insights.json")
        data = _load_json(source_path)
        if not data:
            return assets

        insights: List[Dict] = data.get("insights", [])
        if not insights:
            return assets

        # Sort by id for deterministic batching
        insights_sorted = sorted(insights, key=lambda x: str(x.get("id", "")))

        batch_index = 0
        for i in range(0, len(insights_sorted), GIT_INSIGHTS_BATCH_SIZE):
            batch = insights_sorted[i: i + GIT_INSIGHTS_BATCH_SIZE]
            batch_content = _stable_json(batch)
            asset_id = f"git_insights:batch:{batch_index}"
            # Collect insight types present in the batch for logging
            types_in_batch = sorted({item.get("type", "unknown") for item in batch})
            assets.append({
                "type": "git_insights_batch",
                "id": asset_id,
                "group_size": len(batch),
                "batch_index": batch_index,
                "insight_ids": [str(item.get("id", "")) for item in batch],
                "insight_types": types_in_batch,
                "items": batch,
                "content_hash": _sha256(batch_content),
            })
            batch_index += 1

        return assets

    # ------------------------------------------------------------------
    # Labels — STEP 1
    # ------------------------------------------------------------------

    def _scan_label_assets(self) -> List[Dict]:
        """One asset per i18n namespace prefix.

        Source: data/label_map.json → namespaces[]
        Asset id: "labels:ns:{namespace}"
        """
        assets: List[Dict] = []
        source_path = os.path.join(self.data_root, "label_map.json")
        data = _load_json(source_path)
        if not data:
            return assets

        namespaces: List[Dict] = data.get("namespaces", [])
        if not namespaces:
            return assets

        # Sort by namespace name for deterministic order
        namespaces_sorted = sorted(namespaces, key=lambda x: x.get("namespace", "").lower())

        for ns_entry in namespaces_sorted:
            ns_name = ns_entry.get("namespace", "")
            if not ns_name:
                continue
            ns_safe = _safe_filename_segment(ns_name)
            asset_id = f"labels:ns:{ns_safe}"
            ns_content = _stable_json(ns_entry)
            assets.append({
                "type": "labels_namespace",
                "id": asset_id,
                "group_size": ns_entry.get("key_count", 0),
                "namespace": ns_name,
                "key_count": ns_entry.get("key_count", 0),
                "sample_keys": ns_entry.get("sample_keys", []),
                "matched_modules": ns_entry.get("matched_modules", []),
                "is_duplicate": ns_entry.get("is_duplicate", False),
                "content_hash": _sha256(ns_content),
            })

        return assets

    # ------------------------------------------------------------------
    # Code files — STEP 1 (UNCHANGED: 1 file = 1 asset)
    # ------------------------------------------------------------------

    def _scan_code_assets(self) -> List[Dict]:
        """Scan solution_root for code files: one file = one asset.

        Asset id: "code:{relative_path_with_forward_slashes}"

        Skips: _SKIP_DIRS, non-_CODE_EXTENSIONS files.
        """
        assets: List[Dict] = []
        if not self.solution_root or not os.path.isdir(self.solution_root):
            return assets

        for dirpath, dirnames, filenames in os.walk(self.solution_root):
            # Prune skip directories in-place so os.walk doesn't descend into them
            dirnames[:] = [
                d for d in dirnames
                if d.lower() not in _SKIP_DIRS and not d.startswith(".")
            ]

            for filename in sorted(filenames):
                ext = os.path.splitext(filename)[1].lower()
                if ext not in _CODE_EXTENSIONS:
                    continue

                abs_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(abs_path, self.solution_root).replace("\\", "/")
                asset_id = f"code:{rel_path}"

                content = _read_text(abs_path)
                if content is None:
                    continue

                assets.append({
                    "type": "code_file",
                    "id": asset_id,
                    "group_size": 1,
                    "path": rel_path,
                    "extension": ext,
                    "size_bytes": os.path.getsize(abs_path),
                    "content_hash": _sha256(content),
                })

        return assets
