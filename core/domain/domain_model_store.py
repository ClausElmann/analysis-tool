"""Domain model store — persists a domain model as numbered section files.

Directory layout::

    domains/{domain}/
        000_meta.json
        010_entities.json
        020_behaviors.json
        030_flows.json
        040_events.json
        050_batch.json
        060_integrations.json
        070_rules.json
        080_pseudocode.json
        090_rebuild.json

All writes are atomic (``path.tmp`` → ``os.replace``).
All lists are sorted and deduplicated before writing.
``sort_keys=True`` on all JSON output for deterministic diffs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.domain.ai.semantic_analyzer import INSIGHT_KEYS

# ---------------------------------------------------------------------------
# File name registry (ordered)
# ---------------------------------------------------------------------------

_FILE_MAP: Dict[str, str] = {
    "meta":             "000_meta.json",
    "entities":         "010_entities.json",
    "behaviors":        "020_behaviors.json",
    "flows":            "030_flows.json",
    "events":           "040_events.json",
    "batch":            "050_batch.json",
    "integrations":     "060_integrations.json",
    "rules":            "070_rules.json",
    "pseudocode":       "080_pseudocode.json",
    "rebuild":          "090_rebuild.json",
    "decision_support": "095_decision_support.json",
}

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _write_atomic(path: str, data: Any) -> None:
    """Write *data* as JSON to *path* via an atomic rename."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, path)


def _load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# DomainModelStore
# ---------------------------------------------------------------------------


class DomainModelStore:
    """Read and write domain model section files under ``domains_root``."""

    def __init__(self, domains_root: str) -> None:
        self._domains_root = os.path.abspath(domains_root)

    # ------------------------------------------------------------------

    def _domain_dir(self, domain_name: str) -> str:
        return os.path.join(self._domains_root, domain_name)

    def ensure_dir(self, domain_name: str) -> str:
        """Create domain directory if missing; return its path."""
        path = self._domain_dir(domain_name)
        os.makedirs(path, exist_ok=True)
        return path

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load_model(self, domain_name: str) -> Dict[str, Any]:
        """Load model from individual section files.

        Returns an empty model (all keys present, empty lists) if files
        are absent or corrupt.
        """
        domain_dir = self._domain_dir(domain_name)
        model: Dict[str, Any] = {k: [] for k in INSIGHT_KEYS}

        for section, filename in _FILE_MAP.items():
            if section == "meta":
                continue
            path = os.path.join(domain_dir, filename)
            data = _load_json(path)
            if isinstance(data, list):
                # Normalise: deduplicate and sort
                model[section] = sorted({str(x) for x in data if x})

        return model

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save_model(
        self,
        domain_name: str,
        model: Dict[str, Any],
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Atomically write all model section files for *domain_name*.

        Each section file contains a sorted, deduplicated JSON array.
        ``000_meta.json`` is written last with a UTC timestamp.
        """
        domain_dir = self.ensure_dir(domain_name)

        # Write section files (skip meta and decision_support — handled separately)
        for section, filename in _FILE_MAP.items():
            if section in ("meta", "decision_support"):
                continue
            items = sorted({str(x) for x in (model.get(section) or []) if x})
            path = os.path.join(domain_dir, filename)
            _write_atomic(path, items)

        # Write meta
        meta_data: Dict[str, Any] = dict(meta or {})
        meta_data["domain"] = domain_name
        meta_data["saved_utc"] = datetime.now(timezone.utc).isoformat()
        meta_path = os.path.join(domain_dir, _FILE_MAP["meta"])
        _write_atomic(meta_path, meta_data)

    def save_decision_support(
        self,
        domain_name: str,
        data: Dict[str, Any],
    ) -> None:
        """Atomically write ``095_decision_support.json`` for *domain_name*.

        Parameters
        ----------
        domain_name:
            The domain to write decision support data for.
        data:
            Arbitrary dict with decision support fields.  Common keys:
            ``business_value``, ``complexity``, ``legacy_coupling``,
            ``rebuild_priority``, ``candidate_for_v2_core``,
            ``candidate_for_phase_2``, ``candidate_for_retirement``,
            ``reasoning``.
        """
        domain_dir = self.ensure_dir(domain_name)
        payload: Dict[str, Any] = dict(data)
        payload["domain"] = domain_name
        payload["saved_utc"] = datetime.now(timezone.utc).isoformat()
        path = os.path.join(domain_dir, _FILE_MAP["decision_support"])
        _write_atomic(path, payload)

    # ------------------------------------------------------------------
    # Upgrade #4: strong rebuild spec helpers
    # ------------------------------------------------------------------

    def build_rebuild_spec(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Derive a structured rebuild specification from *model*.

        The spec always contains all six mandatory keys.  Values are derived
        from the domain model — nothing is invented.  Empty lists are used
        when data is absent (keys are never omitted).

        Structure
        ---------
        ``entities``    — copy of model entities (non-null strings only)
        ``core_flows``  — copy of model flows
        ``api_surface`` — extracted from integrations + behaviors that look
                          like endpoints (contain "Controller", "Api", "Endpoint", etc.)
        ``state_model`` —  "stateful" when rules or events present, else "stateless"
        ``constraints`` — copy of model rules
        ``ui_modules``  — behaviors / entities whose name hints at UI
                          (contain "Controller", "View", "Page", "Component", "Form")
        """
        # Fix 2: Blazor-ready rebuild specification schema
        _UI_HINTS    = frozenset({"controller", "view", "page", "component", "form", "ui", "screen"})
        _API_HINTS   = frozenset({"controller", "api", "endpoint", "route", "http", "rest", "graphql"})
        _ENTITY_SKIP = frozenset({"dto", "model", "view", "service", "factory", "helper", "utils"})
        _HTTP_VERBS  = frozenset({"get", "post", "put", "delete", "patch"})
        _AUTH_HINTS  = frozenset({"auth", "login", "logout", "permission", "role", "claim", "identity", "token"})

        def _clean(items) -> List[str]:
            return [str(x) for x in (items or []) if x]

        entities     = _clean(model.get("entities"))
        flows        = _clean(model.get("flows"))
        integrations = _clean(model.get("integrations"))
        behaviors    = _clean(model.get("behaviors"))
        rules        = _clean(model.get("rules"))
        events       = _clean(model.get("events"))

        # blazor_pages: entities/behaviors with UI hints → infer component name + route
        blazor_pages: List[Dict[str, Any]] = []
        seen_pages: set = set()
        for item in behaviors + entities:
            lc = item.lower()
            if any(h in lc for h in _UI_HINTS) and item not in seen_pages:
                seen_pages.add(item)
                route_name = item.replace(" ", "").replace("Controller", "").replace("Page", "").replace("View", "")
                auth_required = any(h in lc for h in _AUTH_HINTS)
                blazor_pages.append({
                    "component": item,
                    "route": f"/{route_name.lower() or 'index'}",
                    "auth_required": auth_required,
                    "source": "inferred",
                })

        # api_contracts: integrations + verb-hinted behaviors
        api_contracts: List[Dict[str, Any]] = []
        seen_api: set = set()
        for item in integrations:
            if item not in seen_api:
                seen_api.add(item)
                api_contracts.append({"method": item, "source": "integration"})
        for item in behaviors:
            lc = item.lower()
            if any(h in lc for h in _API_HINTS) and item not in seen_api:
                seen_api.add(item)
                verb = next((v.upper() for v in _HTTP_VERBS if v in lc), "GET")
                api_contracts.append({"method": f"{verb} /{item.lower()}", "source": "inferred"})

        # ef_core_entities: entities without DTO/Service/View/Helper noise
        ef_core_entities: List[Dict[str, Any]] = [
            {"entity": e, "table": e.lower() + "s"}
            for e in entities
            if not any(sk in e.lower() for sk in _ENTITY_SKIP)
        ]

        # blazor_state_model
        state_type = "stateful" if (rules or events) else "stateless"
        blazor_state_model: Dict[str, Any] = {
            "type":   state_type,
            "events": events,
            "rules":  rules,
        }

        # authorization_hints: rules + behaviors that mention auth concepts
        auth_hints = [
            item for item in rules + behaviors
            if any(h in item.lower() for h in _AUTH_HINTS)
        ]

        import datetime
        return {
            "_meta": {
                "target_stack":  "Blazor Server",
                "generated_by":  "HeuristicAIProvider",
                "generated_at":  datetime.datetime.utcnow().isoformat() + "Z",
                "schema_version": "2.0",
            },
            "blazor_pages":        blazor_pages,
            "api_contracts":       api_contracts,
            "ef_core_entities":    ef_core_entities,
            "blazor_state_model":  blazor_state_model,
            "known_integrations":  integrations,
            "authorization_hints": auth_hints,
            "domain_flows":        flows,
            "validation_rules":    rules,
        }

    def save_rebuild_spec(self, domain_name: str, model: Dict[str, Any]) -> None:
        """Write ``090_rebuild.json`` with the structured rebuild specification.

        Parameters
        ----------
        domain_name:
            Domain to write for.
        model:
            The current refined domain model (all INSIGHT_KEYS present).
        """
        spec = self.build_rebuild_spec(model)
        domain_dir = self.ensure_dir(domain_name)
        path = os.path.join(domain_dir, _FILE_MAP["rebuild"])
        _write_atomic(path, spec)

    def build_rebuild_spec_v2(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Derive a structured Gen 3 rebuild specification from *model*.

        Uses the canonical V2 schema that describes domain behaviour rather
        than a specific target stack.  Both ``build_rebuild_spec()`` and this
        method coexist until rebuild V2 migration is fully validated (Phase L4).

        Returns
        -------
        dict
            14 canonical top-level keys (aggregates, entities, commands,
            queries, workflows, state_transitions, invariants, permissions,
            persistence, integrations, background_processes, ui_surfaces,
            events_emitted, events_consumed) plus ``_meta``.
        """
        _MUTATION_VERBS = frozenset({
            "create", "update", "delete", "add", "remove", "set", "save",
            "write", "post", "put", "patch", "insert", "upsert", "change",
        })
        _QUERY_VERBS = frozenset({
            "get", "fetch", "list", "read", "find", "search", "load",
            "show", "check", "count", "query",
        })
        _AUTH_HINTS = frozenset({
            "auth", "login", "logout", "permission", "role", "claim",
            "identity", "token", "authorize",
        })
        _UI_HINTS = frozenset({
            "page", "view", "component", "screen", "form", "controller",
        })
        _CONSUME_HINTS = frozenset({
            "consume", "subscribe", "receive", "handle", "listen",
        })
        _SUB_ENTITY_HINTS = frozenset({
            "detail", "item", "line", "child", "sub",
        })

        def _clean(items) -> List[str]:
            return [str(x) for x in (items or []) if x]

        entities     = _clean(model.get("entities"))
        behaviors    = _clean(model.get("behaviors"))
        flows        = _clean(model.get("flows"))
        rules        = _clean(model.get("rules"))
        integrations = _clean(model.get("integrations"))
        batch        = _clean(model.get("batch"))
        events       = _clean(model.get("events"))

        # behaviors → commands vs queries (default: command)
        commands: List[str] = []
        queries: List[str] = []
        for b in behaviors:
            lc = b.lower()
            if any(v in lc for v in _QUERY_VERBS) and not any(v in lc for v in _MUTATION_VERBS):
                queries.append(b)
            else:
                commands.append(b)

        # aggregates: entities without obvious sub-entity naming
        aggregates: List[str] = [
            e for e in entities
            if not any(h in e.lower() for h in _SUB_ENTITY_HINTS)
        ]

        # permissions: rules + behaviors mentioning auth concepts
        permissions: List[str] = [
            item for item in rules + behaviors
            if any(h in item.lower() for h in _AUTH_HINTS)
        ]

        # persistence: one mapping per entity
        persistence: List[Dict[str, str]] = [
            {"entity": e, "table": e.lower().replace(" ", "_") + "s"}
            for e in entities
        ]

        # ui_surfaces: behaviors + entities with UI hints
        ui_surfaces: List[str] = [
            item for item in behaviors + entities
            if any(h in item.lower() for h in _UI_HINTS)
        ]

        # events_emitted vs events_consumed
        events_emitted: List[str] = []
        events_consumed: List[str] = []
        for ev in events:
            lc = ev.lower()
            if any(h in lc for h in _CONSUME_HINTS):
                events_consumed.append(ev)
            else:
                events_emitted.append(ev)

        # state_transitions: flows that explicitly mention state changes
        state_transitions: List[str] = [
            f for f in flows
            if any(kw in f.lower() for kw in ("transition", "state", "status", "->", "\u2192"))
        ]

        return {
            "_meta": {
                "schema_version": "2.0",
                "generated_by":   "build_rebuild_spec_v2",
                "generated_at":   datetime.now(timezone.utc).isoformat(),
            },
            "aggregates":           aggregates,
            "entities":             entities,
            "commands":             commands,
            "queries":              queries,
            "workflows":            flows,
            "state_transitions":    state_transitions,
            "invariants":           rules,
            "permissions":          permissions,
            "persistence":          persistence,
            "integrations":         integrations,
            "background_processes": batch,
            "ui_surfaces":          ui_surfaces,
            "events_emitted":       events_emitted,
            "events_consumed":      events_consumed,
        }

    def migrate_rebuild_v1_to_v2(self, domain_name: str) -> None:
        """One-time migration: promote 090_rebuild.json from v1 to V2 schema.

        Maps v1 Blazor-centric keys to canonical V2 keys:
          - ``blazor_pages``    → ``ui_surfaces``
          - ``api_contracts``   → ``commands`` (POST/PUT/DELETE/PATCH) + ``queries`` (GET)
          - ``ef_core_entities`` → ``entities`` + ``persistence``
          - ``domain_flows``    → ``workflows``
          - ``validation_rules`` → ``invariants``
          - ``authorization_hints`` → ``permissions``
          - ``known_integrations`` → ``integrations``

        The original v1 payload is preserved verbatim under ``_v1_legacy``.
        Writes the result back to ``090_rebuild.json`` atomically.
        """
        domain_dir = self._domain_dir(domain_name)
        rebuild_path = os.path.join(domain_dir, _FILE_MAP["rebuild"])

        try:
            with open(rebuild_path, "r", encoding="utf-8") as fh:
                v1: Dict[str, Any] = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cannot read {rebuild_path}: {exc}") from exc

        # blazor_pages → ui_surfaces (preserve full records)
        ui_surfaces = v1.get("blazor_pages") or []

        # api_contracts → commands / queries split by HTTP verb
        _QUERY_HTTP = {"get", "head", "options"}
        commands: List[Any] = []
        queries: List[Any] = []
        for contract in (v1.get("api_contracts") or []):
            method_str = (
                contract.get("method", "") if isinstance(contract, dict) else str(contract)
            ).upper()
            if any(method_str.startswith(v.upper()) for v in _QUERY_HTTP):
                queries.append(contract)
            else:
                commands.append(contract)

        v2: Dict[str, Any] = {
            "_meta": {
                "schema_version": "2.0",
                "migrated_from":  "v1",
                "migrated_at":    datetime.now(timezone.utc).isoformat(),
                "domain":         domain_name,
            },
            "aggregates":           [],
            "entities":             v1.get("ef_core_entities") or [],
            "commands":             commands,
            "queries":              queries,
            "workflows":            v1.get("domain_flows") or [],
            "state_transitions":    [],
            "invariants":           v1.get("validation_rules") or [],
            "permissions":          v1.get("authorization_hints") or [],
            "persistence":          v1.get("ef_core_entities") or [],
            "integrations":         v1.get("known_integrations") or [],
            "background_processes": [],
            "ui_surfaces":          ui_surfaces,
            "events_emitted":       [],
            "events_consumed":      [],
            "_v1_legacy":           v1,
        }
        _write_atomic(rebuild_path, v2)

    def build_decision_support(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Derive heuristic decision-support metadata from *model*.

        Derives ``complexity``, ``business_value``, ``coupling``, and
        ``rebuild_priority`` from entity / integration / flow counts.
        Nothing is invented — all values are computed from the model.

        Returns
        -------
        dict
            ``complexity``       — "low" | "medium" | "high"
            ``business_value``   — "low" | "medium" | "high"
            ``coupling``         — "low" | "medium" | "high"
            ``rebuild_priority`` — int 1..10 (higher = rebuild sooner)
        """
        entity_count      = len(model.get("entities") or [])
        flow_count        = len(model.get("flows") or [])
        integration_count = len(model.get("integrations") or [])
        rule_count        = len(model.get("rules") or [])

        # Complexity: driven by entities + flows
        total_complexity = entity_count + flow_count + rule_count
        if total_complexity < 10:
            complexity = "low"
        elif total_complexity < 25:
            complexity = "medium"
        else:
            complexity = "high"

        # Business value: proxy from flow + rule richness
        value_score = flow_count * 2 + rule_count
        if value_score < 5:
            business_value = "low"
        elif value_score < 15:
            business_value = "medium"
        else:
            business_value = "high"

        # Coupling: based on integration count
        if integration_count == 0:
            coupling = "low"
        elif integration_count < 3:
            coupling = "medium"
        else:
            coupling = "high"

        # Rebuild priority: 1-10, higher when high complexity + high coupling
        _LEVEL = {"low": 1, "medium": 2, "high": 3}
        priority_raw = _LEVEL[complexity] + _LEVEL[coupling] + _LEVEL[business_value]
        # Map 3-9 → 1-10
        rebuild_priority = round(1 + (priority_raw - 3) / 6 * 9)
        rebuild_priority = max(1, min(10, rebuild_priority))

        return {
            "complexity":        complexity,
            "business_value":    business_value,
            "coupling":          coupling,
            "rebuild_priority":  rebuild_priority,
        }
