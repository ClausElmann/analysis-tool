"""SLICE_7 — System Fusion.

Fuses all prior slice outputs into a single unified system model.
All operations are pure / deterministic / no external dependencies.

Public API
----------
fuse_system(data_root: str) -> dict
    Returns ``{"modules": [...]}`` ready for JSON serialisation.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Set

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _load_json(path: str, default: Any) -> Any:
    """Load JSON from *path*; return *default* on any error."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Name normalisation helpers
# ---------------------------------------------------------------------------

_NON_WORD_RE = re.compile(r"[^\w]+")


def _route_to_module_name(route_path: str) -> str:
    """'customers/details' → 'customers'  (first non-empty path segment, lowercased)."""
    if not route_path:
        return ""
    segments = [s for s in route_path.strip("/").split("/") if s]
    if not segments:
        return ""
    return segments[0].lower()


def _component_to_module_name(component: str) -> str:
    """'CustomerListComponent' → 'customer'  (strip suffix, lowercase, first token)."""
    name = re.sub(r"(Component|Module|Page|View)$", "", component, flags=re.IGNORECASE)
    # CamelCase → lower
    name = re.sub(r"([A-Z])", r" \1", name).strip().lower()
    tokens = name.split()
    return tokens[0] if tokens else component.lower()


def _keyword_tokens(text: str) -> Set[str]:
    """Tokenise *text* into lowercase words of length ≥ 3."""
    return {w.lower() for w in re.findall(r"[a-zA-ZæøåÆØÅ]{3,}", text)}


def _tokens_overlap(t1: Set[str], t2: Set[str]) -> bool:
    """Return True if any token in *t1* matches any token in *t2*.

    Matching uses exact equality first, then prefix matching (min len 4)
    to handle common singular/plural pairs like 'customer'/'customers'.
    """
    if t1 & t2:
        return True
    for a in t1:
        for b in t2:
            short, long_ = (a, b) if len(a) <= len(b) else (b, a)
            if len(short) >= 4 and long_.startswith(short):
                return True
    return False


def _name_overlaps(module_name: str, text: str) -> bool:
    """Return True if *module_name* (or its tokens) appear in *text*."""
    if not module_name or not text:
        return False
    if module_name in text.lower():
        return True
    m_tokens = _keyword_tokens(module_name)
    t_tokens = _keyword_tokens(text)
    return _tokens_overlap(m_tokens, t_tokens)


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def _compute_confidence(module: Dict) -> float:
    score = 0
    if module.get("routes"):
        score += 20
    if module.get("apis"):
        score += 20
    if module.get("tables"):
        score += 20
    if module.get("features"):
        score += 20
    if module.get("signals"):
        # Check if any signals come from wiki or pdf (non-git)
        non_git = [s for s in module["signals"] if not s.startswith("git:")]
        if non_git:
            score += 10
        git_sigs = [s for s in module["signals"] if s.startswith("git:")]
        if git_sigs:
            score += 10
    score = max(0, min(100, score))
    return round(score / 100, 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fuse_system(data_root: str) -> Dict:
    """Fuse all prior slice outputs into a unified system model.

    Parameters
    ----------
    data_root:
        Directory containing ``angular_entries.json``, ``component_api_map.json``,
        ``api_db_map.json``, ``work_item_analysis.json``, ``wiki_signals.json``,
        ``pdf_capabilities.json``, and ``git_insights.json``.

    Returns
    -------
    dict
        ``{"modules": [...]}``
    """

    def _path(name: str) -> str:
        return os.path.join(data_root, name)

    # ------------------------------------------------------------------
    # STEP 1 — Load all input files gracefully
    # ------------------------------------------------------------------
    angular_data    = _load_json(_path("angular_entries.json"),    {"entries": []})
    api_map_data    = _load_json(_path("component_api_map.json"),  {"mappings": []})
    db_map_data     = _load_json(_path("api_db_map.json"),         {"mappings": []})
    work_item_data  = _load_json(_path("work_item_analysis.json"), {"capabilities": [], "features": []})
    wiki_data       = _load_json(_path("wiki_signals.json"),       {"capabilities": []})
    pdf_data        = _load_json(_path("pdf_capabilities.json"),   {"capabilities": []})
    git_data        = _load_json(_path("git_insights.json"),       {"insights": []})

    # ------------------------------------------------------------------
    # STEP 2 — Build route → component map from angular_entries.json
    # ------------------------------------------------------------------
    # entry_id → {route_path, component}
    # FIX: angular_entries.json uses key "entry_points" not "entries"
    route_map: Dict[str, Dict] = {}
    _angular_entries = angular_data.get("entry_points", angular_data.get("entries", []))
    for entry in _angular_entries:
        entry_id = entry.get("entry_id") or entry.get("id") or ""
        route_path = entry.get("route", entry.get("path", ""))
        component  = entry.get("component", "")
        # FIX 4: if path is empty, derive a path from component name as fallback
        if not route_path and component and component not in ("UNKNOWN", ""):
            comp_stripped = re.sub(r"(Component|Module|Page|View)$", "", component, flags=re.IGNORECASE)
            route_path = comp_stripped.lower()
        if entry_id:
            route_map[entry_id] = {
                "route_path": route_path,
                "component":  component,
            }

    # ------------------------------------------------------------------
    # STEP 3 — Join with component_api_map
    # ------------------------------------------------------------------
    # entry_id → {component, apis: [{url, method}], method_names}
    api_by_entry: Dict[str, Dict] = {}
    for mapping in api_map_data.get("mappings", []):
        entry_id  = mapping.get("entry_id", "")
        component = mapping.get("component", "")
        apis      = mapping.get("apis", [])
        for api in apis:
            rec = api_by_entry.setdefault(entry_id, {
                "component":    component,
                "api_urls":     [],
                "method_names": [],
            })
            url = api.get("url", "")
            if url:
                rec["api_urls"].append(url)
            mn = api.get("method_name", "")
            if mn:
                rec["method_names"].append(mn)

    # ------------------------------------------------------------------
    # STEP 4 — Build api_url → {controller, service, tables} index
    # ------------------------------------------------------------------
    db_by_url: Dict[str, Dict] = {}
    for mapping in db_map_data.get("mappings", []):
        url        = mapping.get("api_url", "")
        controller = mapping.get("controller", "")
        service    = mapping.get("service", "")
        sql        = mapping.get("sql", {})
        tables     = sql.get("tables", []) if isinstance(sql, dict) else []
        if url:
            rec = db_by_url.setdefault(url, {
                "controllers": [],
                "services":    [],
                "tables":      [],
            })
            if controller:
                rec["controllers"].append(controller)
            if service:
                rec["services"].append(service)
            rec["tables"].extend(tables)

    # ------------------------------------------------------------------
    # STEP 5 — Build initial module candidates from routes
    # ------------------------------------------------------------------
    # module_name → raw accumulation dict
    modules_raw: Dict[str, Dict] = {}

    def _get_or_create(name: str) -> Dict:
        if name not in modules_raw:
            modules_raw[name] = {
                "name":        name,
                "routes":      set(),
                "components":  set(),
                "apis":        set(),
                "controllers": set(),
                "services":    set(),
                "tables":      set(),
                "features":    set(),
                "signals":     set(),
            }
        return modules_raw[name]

    # Seed from angular entries
    for entry_id, route_info in route_map.items():
        route_path = route_info["route_path"]
        component  = route_info["component"]
        mod_name   = _route_to_module_name(route_path) or _component_to_module_name(component)
        if not mod_name:
            continue
        mod = _get_or_create(mod_name)
        if route_path:
            mod["routes"].add(route_path)
        if component:
            mod["components"].add(component)

        # Pull in API + DB data for this entry_id
        api_info = api_by_entry.get(entry_id, {})
        for url in api_info.get("api_urls", []):
            mod["apis"].add(url)
            db_info = db_by_url.get(url, {})
            mod["controllers"].update(db_info.get("controllers", []))
            mod["services"].update(db_info.get("services", []))
            mod["tables"].update(db_info.get("tables", []))
        for comp in [api_info.get("component", "")]:
            if comp:
                mod["components"].add(comp)

    # Also seed modules from api_map entries that have no matching route
    for entry_id, api_info in api_by_entry.items():
        if entry_id in route_map:
            continue  # already seeded via the route loop above
        component = api_info.get("component", "")
        mod_name  = _component_to_module_name(component) if component else ""
        if not mod_name:
            continue
        mod = _get_or_create(mod_name)
        if component:
            mod["components"].add(component)
        for url in api_info.get("api_urls", []):
            mod["apis"].add(url)
            db_info = db_by_url.get(url, {})
            mod["controllers"].update(db_info.get("controllers", []))
            mod["services"].update(db_info.get("services", []))
            mod["tables"].update(db_info.get("tables", []))

    # ------------------------------------------------------------------
    # STEP 6 — Attach features from work_item_analysis.json
    # ------------------------------------------------------------------
    wi_features     = work_item_data.get("features", [])
    wi_capabilities = work_item_data.get("capabilities", [])

    # Build capability name → keywords lookup for faster matching
    cap_keywords: Dict[str, Set[str]] = {}
    for cap in wi_capabilities:
        cap_name = cap.get("name", "")
        kws = set(cap.get("keywords", []))
        if cap_name:
            cap_keywords[cap_name] = kws

    for feat in wi_features:
        feat_title = feat.get("title", "")
        feat_cap   = feat.get("capability", "")
        feat_kws   = set(feat.get("keywords", []))

        for mod_name, mod in modules_raw.items():
            matched = False
            m_tokens = _keyword_tokens(mod_name)

            # Match 1: module name appears in capability name
            if feat_cap and _name_overlaps(mod_name, feat_cap):
                matched = True

            # Match 2: module name tokens overlap with feature keywords
            if not matched and _tokens_overlap(m_tokens, feat_kws):
                matched = True

            # Match 3: module name appears in feature title
            if not matched and _name_overlaps(mod_name, feat_title):
                matched = True

            # Match 4: module name in capability keywords
            if not matched and feat_cap in cap_keywords:
                if m_tokens & cap_keywords[feat_cap]:
                    matched = True

            if matched and feat_title:
                mod["features"].add(feat_title)

    # ------------------------------------------------------------------
    # STEP 7 — Attach signals from wiki / pdf / git
    # ------------------------------------------------------------------

    # Wiki signals
    for cap in wiki_data.get("capabilities", []):
        cap_name    = cap.get("name", "") or ""
        cap_signals = cap.get("signals", [])
        for mod_name, mod in modules_raw.items():
            if _name_overlaps(mod_name, cap_name) or any(
                _name_overlaps(mod_name, s) for s in cap_signals
            ):
                for sig in cap_signals:
                    if sig:
                        mod["signals"].add(sig)

    # PDF signals
    for cap in pdf_data.get("capabilities", []):
        cap_name     = cap.get("name", "") or ""
        cap_features = cap.get("features", [])
        for mod_name, mod in modules_raw.items():
            if _name_overlaps(mod_name, cap_name) or any(
                _name_overlaps(mod_name, f) for f in cap_features
            ):
                if cap_name:
                    mod["signals"].add(cap_name)
                for f in cap_features:
                    if f:
                        mod["signals"].add(f)

    # Git signals — prefix with "git:" so confidence scorer can distinguish
    for insight in git_data.get("insights", []):
        text = insight.get("text", "") or ""
        for mod_name, mod in modules_raw.items():
            if _name_overlaps(mod_name, text):
                if text:
                    mod["signals"].add(f"git:{text}")

    # ------------------------------------------------------------------
    # STEP 8+9+10 — Dedup, score, filter, finalise
    # ------------------------------------------------------------------
    modules_out: List[Dict] = []

    for mod_name in sorted(modules_raw):
        mod = modules_raw[mod_name]

        # Sort + deduplicate all sets → lists
        routes      = sorted(mod["routes"])
        components  = sorted(mod["components"])
        apis        = sorted(mod["apis"])
        controllers = sorted(mod["controllers"])
        services    = sorted(mod["services"])
        tables      = sorted(mod["tables"])
        features    = sorted(mod["features"])
        signals     = sorted(mod["signals"])

        # STEP 10 — filter: must have at least one signal
        # FIX 5: also accept components — do not require API
        if not routes and not components and not apis and not features:
            continue

        assembled = {
            "name":        mod_name,
            "routes":      routes,
            "components":  components,
            "apis":        apis,
            "controllers": controllers,
            "services":    services,
            "tables":      tables,
            "features":    features,
            "signals":     signals,
            "confidence":  0.0,   # placeholder; filled below
        }
        assembled["confidence"] = _compute_confidence(assembled)
        modules_out.append(assembled)

    return {"modules": modules_out}
