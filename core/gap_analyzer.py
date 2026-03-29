"""SLICE_10 — Gap Analysis.

Detects missing, unused, and orphaned functionality by comparing
system_model.json, work_item_analysis.json, and component_api_map.json.

All matching is simple string-based. No inference, no guessing.

Public API
----------
analyze_gaps(data_root: str) -> dict
    Returns ``{"gaps": [...]}`` ready for JSON serialisation.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Set


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Normalisation helper
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    """Lowercase and strip for consistent comparison."""
    return text.lower().strip()


# ---------------------------------------------------------------------------
# Gap detectors (pure functions — accept pre-loaded data)
# ---------------------------------------------------------------------------

def _detect_work_items_without_modules(
    wi_features: List[Dict],
    module_names: Set[str],
) -> List[Dict]:
    """Gap type: work item feature exists but no module name matches."""
    gaps: List[Dict] = []
    seen: Set[str] = set()
    for feat in wi_features:
        title = feat.get("title", "") or ""
        keywords = [_norm(k) for k in feat.get("keywords", []) if k]
        # A feature is "covered" if any module name appears in title or keywords
        covered = any(
            _norm(mod) in _norm(title) or _norm(mod) in keywords
            for mod in module_names
        )
        if not covered and title and title not in seen:
            seen.add(title)
            gaps.append({
                "type": "missing_feature",
                "description": f'"{title}" exists in work items but no module found',
            })
    return gaps


def _detect_modules_without_features(
    modules: List[Dict],
    wi_feature_titles: Set[str],
) -> List[Dict]:
    """Gap type: module has no matching work item feature."""
    gaps: List[Dict] = []
    norm_titles = {_norm(t) for t in wi_feature_titles}
    for mod in modules:
        mod_name = mod.get("name", "") or ""
        # Module is covered if any feature title contains the module name
        covered = any(_norm(mod_name) in t for t in norm_titles)
        if not covered and mod_name:
            gaps.append({
                "type": "missing_requirement",
                "description": f'Module "{mod_name}" has no matching work item feature',
            })
    return gaps


def _detect_apis_without_ui(
    modules: List[Dict],
    api_map_entry_ids: Set[str],
    route_entry_ids: Set[str],
) -> List[Dict]:
    """Gap type: API exists in module but no route/UI links to it."""
    gaps: List[Dict] = []
    seen: Set[str] = set()
    for mod in modules:
        mod_name = mod.get("name", "") or ""
        apis = mod.get("apis", []) or []
        routes = mod.get("routes", []) or []
        if apis and not routes:
            for api in apis:
                key = (mod_name, api)
                if key not in seen:
                    seen.add(key)
                    gaps.append({
                        "type": "orphan_api",
                        "description": f'API "{api}" in module "{mod_name}" has no UI route',
                    })
    return gaps


def _detect_routes_without_api(
    modules: List[Dict],
) -> List[Dict]:
    """Gap type: route exists but no API is linked."""
    gaps: List[Dict] = []
    seen: Set[str] = set()
    for mod in modules:
        mod_name = mod.get("name", "") or ""
        routes = mod.get("routes", []) or []
        apis = mod.get("apis", []) or []
        if routes and not apis:
            for route in routes:
                key = (mod_name, route)
                if key not in seen:
                    seen.add(key)
                    gaps.append({
                        "type": "dead_route",
                        "description": f'Route "{route}" in module "{mod_name}" has no API',
                    })
    return gaps


def _detect_tables_not_referenced(
    modules: List[Dict],
    all_tables_in_model: Set[str],
    api_map_tables: Set[str],
    db_schema_tables: Set[str],
) -> List[Dict]:
    """Gap type: table exists in DB schema but is not referenced by any module with an API.

    FIX 8: only flag if the table exists in db_schema AND has no API in any module.
    """
    gaps: List[Dict] = []
    # Collect all tables referenced through an api chain anywhere in model
    api_referenced: Set[str] = set()
    for mod in modules:
        if mod.get("apis"):
            api_referenced.update(mod.get("tables", []))

    # FIX 8: use db_schema_tables as the authority; only flag if DB confirms the table exists
    candidate_tables = db_schema_tables if db_schema_tables else all_tables_in_model
    for table in sorted(candidate_tables - api_referenced):
        gaps.append({
            "type": "dead_table",
            "description": f'Table "{table}" exists in DB schema but is not referenced by any API in the system model',
        })
    return gaps


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_gaps(data_root: str) -> Dict:
    """Run all gap detectors and return ``{"gaps": [...]}``.

    Parameters
    ----------
    data_root:
        Directory containing the input JSON files.
    """
    def _path(name: str) -> str:
        return os.path.join(data_root, name)

    # Load inputs
    system_model   = _load_json(_path("system_model.json"),         {"modules": []})
    work_items     = _load_json(_path("work_item_analysis.json"),    {"capabilities": [], "features": []})
    api_map        = _load_json(_path("component_api_map.json"),     {"mappings": []})
    db_schema      = _load_json(_path("db_schema.json"),             {"tables": []})

    modules: List[Dict]    = system_model.get("modules", []) or []
    wi_features: List[Dict] = work_items.get("features", []) or []

    # Derived sets
    module_names: Set[str] = {m.get("name", "") for m in modules if m.get("name")}

    wi_feature_titles: Set[str] = {
        feat.get("title", "") for feat in wi_features if feat.get("title")
    }

    # All tables mentioned anywhere in system model
    all_tables_in_model: Set[str] = set()
    for mod in modules:
        all_tables_in_model.update(mod.get("tables", []))

    # FIX 8: load db_schema table names as authoritative source
    db_schema_tables: Set[str] = {t.get("name", "") for t in db_schema.get("tables", []) if t.get("name")}

    # Tables referenced through api_map (for dead-table cross-check)
    api_map_tables: Set[str] = set()
    for mapping in (api_map.get("mappings", []) or []):
        sql = mapping.get("sql", {}) or {}
        api_map_tables.update(sql.get("tables", []))

    # Entry IDs that have routes (used for orphan_api detection)
    route_entry_ids: Set[str] = set()
    api_map_entry_ids: Set[str] = set()
    for mapping in (api_map.get("mappings", []) or []):
        eid = mapping.get("entry_id", "")
        if eid:
            api_map_entry_ids.add(eid)

    # Run detectors
    gaps: List[Dict] = []
    gaps.extend(_detect_work_items_without_modules(wi_features, module_names))
    gaps.extend(_detect_modules_without_features(modules, wi_feature_titles))
    gaps.extend(_detect_apis_without_ui(modules, api_map_entry_ids, route_entry_ids))
    gaps.extend(_detect_routes_without_api(modules))
    gaps.extend(_detect_tables_not_referenced(modules, all_tables_in_model, api_map_tables, db_schema_tables))

    # Sort for determinism: type first, then description
    gaps.sort(key=lambda g: (g.get("type", ""), g.get("description", "")))

    return {"gaps": gaps}
