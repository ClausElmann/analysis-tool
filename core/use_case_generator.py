"""SLICE_8 — Use Case Generator.

Generates deterministic use cases from ``data/system_model.json``
(produced by SLICE_7 System Fusion).

Public API
----------
generate_use_cases(data_root: str) -> dict
    Returns ``{"use_cases": [...]}`` from the *analysis* pass.
    Also writes both output files as a side-effect when called
    via the engine.  The generator itself is pure — file I/O is
    done externally by the engine method.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Set

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
# Name helpers
# ---------------------------------------------------------------------------

_CAMEL_SPLIT_RE = re.compile(r"([A-Z][a-z]+|[A-Z]+(?=[A-Z]|$)|[a-z]+)")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_MAX_NAME_WORDS = 20


def _camel_split(text: str) -> List[str]:
    """'CustomerList' → ['Customer', 'List']"""
    return _CAMEL_SPLIT_RE.findall(text) or [text]


def _method_to_name(method_fragment: str) -> str:
    """'/api/customers' → 'Get customers'  using HTTP-verb heuristic."""
    # Strip leading /api/ or /api
    cleaned = re.sub(r"^/api/?", "", method_fragment).strip("/")
    if not cleaned:
        return method_fragment
    tokens = [t for seg in cleaned.split("/") for t in _camel_split(seg) if t]
    tokens = tokens[:_MAX_NAME_WORDS]
    if tokens:
        tokens[0] = tokens[0].capitalize()
    return " ".join(tokens)


def _api_to_name(url: str) -> str:
    """'/api/customers' → 'Get customers'"""
    cleaned = re.sub(r"^/api/?", "", url).strip("/")
    if not cleaned:
        return f"Get {url}"
    tokens = [t for seg in cleaned.split("/") for t in _camel_split(seg) if t]
    tokens = tokens[:_MAX_NAME_WORDS]
    first = tokens[0].lower() if tokens else ""
    rest = " ".join(t.lower() for t in tokens)
    return f"Get {rest}" if rest else f"Get {url}"


def _route_to_name(route: str) -> str:
    """'customers' → 'Open customers page'"""
    cleaned = route.strip("/")
    if not cleaned:
        return "Open page"
    tokens = [t for seg in cleaned.split("/") for t in _camel_split(seg) if t]
    tokens = tokens[:_MAX_NAME_WORDS]
    return "Open " + " ".join(t.lower() for t in tokens) + " page"


def _component_to_name(component: str) -> str:
    """'CustomerListComponent' → 'Customer list'"""
    name = re.sub(r"(Component|Module|Page|View)$", "", component, flags=re.IGNORECASE)
    tokens = _camel_split(name)
    tokens = [t.lower() for t in tokens if t][:_MAX_NAME_WORDS]
    if tokens:
        tokens[0] = tokens[0].capitalize()
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def _make_id(entry_point: str, first_api: str) -> str:
    """Normalise entry_point + first_api into a stable ID.

    Example: 'customers' + '/api/customers' → 'customers__apicustomers'
    """
    def _norm(s: str) -> str:
        return _NON_ALNUM_RE.sub("", s.lower())

    ep = _norm(entry_point)
    ap = _norm(first_api) if first_api else ""
    if ep and ap:
        return f"{ep}__{ap}"
    return ep or ap or "unknown"


# ---------------------------------------------------------------------------
# Flow step builders
# ---------------------------------------------------------------------------

def _build_flow_steps(
    routes: List[str],
    components: List[str],
    api_url: Optional[str],
    controllers: List[str],
    services: List[str],
    tables: List[str],
) -> List[str]:
    steps: List[str] = []
    if routes:
        steps.append(f"User opens {routes[0]}")
    if components:
        steps.append(f"Component {components[0]} loads")
    if api_url:
        steps.append(f"Calls API {api_url}")
    if controllers:
        steps.append(f"Handled by {controllers[0]}")
    if services:
        steps.append(f"Calls {services[0]}")
    if tables:
        verb = "Reads/writes"
        steps.append(f"{verb} {tables[0]}")
    return steps


# ---------------------------------------------------------------------------
# Systems list
# ---------------------------------------------------------------------------

def _build_systems(
    has_route: bool,
    has_api: bool,
    has_db: bool,
) -> List[str]:
    systems: List[str] = []
    if has_route:
        systems.append("UI")
    if has_api:
        systems.append("API")
    if has_db:
        systems.append("DB")
    return systems


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def _compute_confidence(
    routes: List[str],
    components: List[str],
    api_url: Optional[str],
    tables: List[str],
) -> float:
    score = 0
    if routes:
        score += 30
    if components:
        score += 20
    if api_url:
        score += 20
    if tables:
        score += 20
    if not api_url:
        score -= 20
    score = max(0, min(100, score))
    return round(score / 100, 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_use_cases(data_root: str) -> Dict:
    """Generate use cases from ``system_model.json`` in *data_root*.

    Returns ``{"use_cases": [...]}`` — the analysis model.
    Does NOT write files; the engine method does that.
    """
    model_path = os.path.join(data_root, "system_model.json")
    system_model = _load_json(model_path, {"modules": []})
    modules: List[Dict] = system_model.get("modules", [])

    use_cases: List[Dict] = []

    for module in modules:
        mod_name    = module.get("name", "") or ""
        routes      = module.get("routes", []) or []
        components  = module.get("components", []) or []
        apis        = module.get("apis", []) or []
        controllers = module.get("controllers", []) or []
        services    = module.get("services", []) or []
        tables      = module.get("tables", []) or []

        if apis:
            # One use case per API
            for api_url in apis:
                entry_point = routes[0] if routes else (components[0] if components else mod_name)

                # Name: api-based
                name = _api_to_name(api_url)

                uc_id = _make_id(entry_point, api_url)

                flow_steps = _build_flow_steps(
                    routes, components, api_url, controllers, services, tables
                )
                systems = _build_systems(
                    has_route=bool(routes),
                    has_api=True,
                    has_db=bool(tables),
                )
                confidence = _compute_confidence(routes, components, api_url, tables)

                use_cases.append({
                    "id":          uc_id,
                    "name":        name,
                    "entry_point": entry_point,
                    "flow_steps":  flow_steps,
                    "systems":     systems,
                    "confidence":  confidence,
                })
        else:
            # No APIs — one use case per module
            entry_point = routes[0] if routes else (components[0] if components else mod_name)

            if routes:
                name = _route_to_name(routes[0])
            elif components:
                name = _component_to_name(components[0])
            else:
                name = mod_name.capitalize()

            uc_id = _make_id(entry_point, "")

            flow_steps = _build_flow_steps(
                routes, components, None, controllers, services, tables
            )
            systems = _build_systems(
                has_route=bool(routes),
                has_api=False,
                has_db=bool(tables),
            )
            confidence = _compute_confidence(routes, components, None, tables)

            use_cases.append({
                "id":          uc_id,
                "name":        name,
                "entry_point": entry_point,
                "flow_steps":  flow_steps,
                "systems":     systems,
                "confidence":  confidence,
            })

    # STEP 8 — sort by id, no nulls
    use_cases.sort(key=lambda uc: uc["id"])

    return {"use_cases": use_cases}


def build_selection(analysis: Dict) -> Dict:
    """Build the write-once selection file from an analysis result."""
    return {
        "use_cases": [
            {"id": uc["id"], "name": uc["name"], "keep": True, "reason": ""}
            for uc in analysis.get("use_cases", [])
        ]
    }
