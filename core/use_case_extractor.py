"""Phase 4.5 – Use Case Extractor.

Derives use cases from Angular analysis results using the hierarchy:
    Menu → Tab → Component → API

Each use case represents:
- one menu item (derived from route or component name)
- one tab (optional; present when Angular tab components are detected)
- one component

Naming format: "{Verb} {Menu} {Tab}"
Examples: "View Customers Overview", "Edit Customer Details"

Rules:
- If no tabs exist → component directly under menu (no tab in name).
- If multiple components exist in a tab → multiple use cases.
- Tabs are never merged.
- No use cases are invented from backend code alone.
"""

import re
from typing import Any, Dict, List, Optional


class UseCaseExtractor:
    """Derives hierarchical use cases (Menu → Tab → Component → API).

    Parameters
    ----------
    angular_results:
        List of FileAnalysis objects (or dicts) produced by AngularAnalyzer.
    capabilities:
        Parsed capabilities.json dict (contains ``functions`` list).
    modules:
        Parsed modules.json dict (contains ``modules`` list).
    """

    # Mapping from HTTP verb / component keyword to display verb.
    _VERB_MAP: Dict[str, str] = {
        "get": "View",
        "list": "View",
        "view": "View",
        "overview": "View",
        "detail": "View",
        "post": "Create",
        "create": "Create",
        "add": "Create",
        "new": "Create",
        "put": "Edit",
        "patch": "Edit",
        "edit": "Edit",
        "update": "Edit",
        "delete": "Delete",
        "remove": "Delete",
        "search": "Search",
        "submit": "Submit",
        "upload": "Upload",
        "download": "Download",
        "login": "Login",
        "logout": "Logout",
    }

    # Words stripped when converting component names to menu labels.
    _GENERIC_COMPONENT_WORDS = frozenset(
        {"component", "module", "page", "view", "container", "widget"}
    )

    def __init__(
        self,
        angular_results: List[Any],
        capabilities: Dict,
        modules: Dict,
    ) -> None:
        self._angular = angular_results
        self._capabilities = capabilities
        self._modules = modules

        self._capability_names: frozenset = frozenset(
            f["name"] for f in capabilities.get("functions", [])
        )
        # Build component → function lookup using source_file path heuristics.
        self._func_to_module: Dict[str, str] = {}
        for mod in modules.get("modules", []):
            for fn in mod.get("functions", []):
                self._func_to_module[fn] = mod["name"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self) -> List[Dict]:
        """Return list of use case analysis records sorted by ``id``."""
        raw: List[Dict] = []
        for analysis in self._angular:
            raw.extend(self._extract_from_analysis(analysis))

        # Sort deterministically before ID assignment.
        raw.sort(key=lambda uc: (uc["entry_point"], uc["menu"], uc["tab"]))

        raw = self._assign_ids(raw)
        raw = self._deduplicate_names(raw)

        raw.sort(key=lambda uc: uc["id"])
        return raw

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_from_analysis(self, analysis: Any) -> List[Dict]:
        ke = self._key_elements(analysis)
        components: List[str] = ke.get("classes", [])
        if not components:
            return []

        tabs: List[str] = ke.get("tabs", [])
        api_calls: List[str] = ke.get("http_calls", [])
        menu: str = self._infer_menu(ke, components)

        if tabs:
            return self._usecases_with_tabs(menu, tabs, components, api_calls)
        return self._usecases_without_tabs(menu, components, api_calls)

    def _usecases_with_tabs(
        self,
        menu: str,
        tabs: List[str],
        components: List[str],
        api_calls: List[str],
    ) -> List[Dict]:
        """One use case per (tab, component) pair. Tabs are never merged."""
        results: List[Dict] = []
        for tab in tabs:
            for component in components:
                results.append(
                    self._build_use_case(
                        menu=menu,
                        tab=tab,
                        component=component,
                        api_calls=api_calls,
                    )
                )
        return results

    def _usecases_without_tabs(
        self,
        menu: str,
        components: List[str],
        api_calls: List[str],
    ) -> List[Dict]:
        """One use case per component when no tabs are present."""
        return [
            self._build_use_case(menu=menu, tab=None, component=c, api_calls=api_calls)
            for c in components
        ]

    def _build_use_case(
        self,
        menu: str,
        tab: Optional[str],
        component: str,
        api_calls: List[str],
    ) -> Dict:
        verb = self._infer_verb(component, api_calls)
        name = self._format_name(verb, menu, tab)
        flow_steps = self._build_flow_steps(component, api_calls)
        functions = self._resolve_functions(flow_steps)
        module = self._resolve_module(functions, flow_steps)
        confidence = self._compute_confidence(component, flow_steps)

        return {
            "id": "",  # assigned in _assign_ids after sorting
            "name": name,
            "entry_point": component,
            "menu": menu,
            "tab": tab if tab is not None else "",
            "component": component,
            "flow_steps": flow_steps,
            "functions": sorted(functions),
            "module": module,
            "description": self._make_description(name),
            "confidence": confidence,
        }

    # ------------------------------------------------------------------
    # Flow and function helpers
    # ------------------------------------------------------------------

    def _build_flow_steps(
        self, component: str, api_calls: List[str]
    ) -> List[Dict]:
        steps: List[Dict] = [{"type": "UI", "name": component}]
        depth = 1
        for call in api_calls:
            if depth >= 10:
                steps.append({"type": "API", "name": "[DEPTH LIMIT]"})
                break
            matched = self._match_capability(call)
            steps.append({"type": "API", "name": matched if matched else "UNKNOWN"})
            depth += 1
        return steps

    def _resolve_functions(self, flow_steps: List[Dict]) -> List[str]:
        return [
            s["name"]
            for s in flow_steps
            if s["type"] in {"API", "DB"} and s["name"] in self._capability_names
        ]

    def _resolve_module(
        self, functions: List[str], flow_steps: List[Dict]
    ) -> str:
        # Prefer the module of the first API step in the trace.
        for step in flow_steps:
            if step["type"] == "API" and step["name"] in self._func_to_module:
                return self._func_to_module[step["name"]]
        # Fall back to the first resolved function.
        for fn in functions:
            if fn in self._func_to_module:
                return self._func_to_module[fn]
        return "Uncategorized"

    def _match_capability(self, api_call: str) -> Optional[str]:
        """Match an HTTP-verb string to the best capability name.

        Exact substring match first; then longest common prefix; then
        lexicographically first if still ambiguous.
        """
        norm = api_call.lower()
        candidates = sorted(self._capability_names)
        # Exact substring match
        exact = [c for c in candidates if norm in c.lower() or c.lower() in norm]
        if exact:
            return exact[0]
        return None

    # ------------------------------------------------------------------
    # Confidence scoring (per spec Section 4.5.4)
    # ------------------------------------------------------------------

    def _compute_confidence(self, component: str, flow_steps: List[Dict]) -> int:
        score = 0
        step_types = {s["type"] for s in flow_steps}
        step_names = {s["name"] for s in flow_steps}

        if component:
            score += 30
        if "API" in step_types:
            score += 20
        if "Service" in step_types:
            score += 20
        if "DB" in step_types:
            score += 20
        if "UNKNOWN" in step_names:
            score -= 20
        if "[CIRCULAR]" in step_names:
            score -= 30

        return max(0, min(100, score))

    # ------------------------------------------------------------------
    # ID generation and deduplication (per spec Section 4.5.1.1)
    # ------------------------------------------------------------------

    def _assign_ids(self, raw: List[Dict]) -> List[Dict]:
        seen: Dict[str, int] = {}
        for uc in raw:
            base = self._compute_base_id(uc)
            if base not in seen:
                seen[base] = 0
                uc["id"] = base
            else:
                seen[base] += 1
                uc["id"] = f"{base}__{seen[base] + 1}"
        return raw

    def _compute_base_id(self, uc: Dict) -> str:
        entry = re.sub(r"[^a-z0-9]", "", uc["entry_point"].lower())
        first_api = next(
            (s["name"] for s in uc["flow_steps"] if s["type"] == "API"),
            "none",
        )
        api_norm = re.sub(r"[^a-z0-9]", "", first_api.lower())
        return f"{entry}__{api_norm}"

    def _deduplicate_names(self, raw: List[Dict]) -> List[Dict]:
        seen: Dict[str, int] = {}
        for uc in raw:
            n = uc["name"]
            if n not in seen:
                seen[n] = 0
            else:
                seen[n] += 1
                uc["name"] = f"{n} ({seen[n] + 1})"
        return raw

    # ------------------------------------------------------------------
    # Naming helpers
    # ------------------------------------------------------------------

    def _infer_menu(self, ke: Dict, components: List[str]) -> str:
        routes = ke.get("routes", [])
        if routes:
            segment = routes[0].lstrip("/").split("/")[0]
            return self._to_title(segment) if segment else "UNKNOWN"
        # Fall back to first component name (minus generic suffix)
        if components:
            tokens = self._split_camel(components[0])
            meaningful = [
                t for t in tokens
                if t.lower() not in self._GENERIC_COMPONENT_WORDS
            ]
            return " ".join(t.title() for t in meaningful) if meaningful else "UNKNOWN"
        return "UNKNOWN"

    def _infer_verb(self, component: str, api_calls: List[str]) -> str:
        # Try HTTP verbs first (most reliable signal)
        for call in api_calls:
            verb = self._VERB_MAP.get(call.lower())
            if verb:
                return verb
        # Fall back to keywords in the component name
        name_lower = component.lower()
        for keyword, verb in self._VERB_MAP.items():
            if keyword in name_lower:
                return verb
        return "View"

    @staticmethod
    def _format_name(verb: str, menu: str, tab: Optional[str]) -> str:
        if tab:
            return f"{verb} {menu} {tab}"
        return f"{verb} {menu}"

    @staticmethod
    def _make_description(name: str) -> str:
        if not name or name == "UNKNOWN":
            return "UNKNOWN"
        return name[:100]

    # ------------------------------------------------------------------
    # Static utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _split_camel(name: str) -> List[str]:
        return re.findall(r"[A-Z][a-z0-9]*|[a-z0-9]+", name)

    @staticmethod
    def _to_title(raw: str) -> str:
        words = re.split(r"[-_\s]+", raw)
        return " ".join(w.title() for w in words if w)

    @staticmethod
    def _key_elements(analysis: Any) -> Dict:
        if hasattr(analysis, "key_elements"):
            return analysis.key_elements or {}
        if isinstance(analysis, dict):
            return analysis.get("key_elements") or {}
        return {}
