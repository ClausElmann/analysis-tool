"""AI Reasoner — provider abstraction + heuristic implementation.

Provides structured reasoning over assets and domain models.

Design
------
``AIProvider``
    Abstract interface.  Swap ``HeuristicAIProvider`` for a GPT/Copilot
    provider without changing any caller code.

``HeuristicAIProvider``
    Default stub — uses regex heuristics.  No LLM required.  Produces
    deterministic, resumable results identical to ``semantic_analyzer``
    but via the normalised provider interface.

``AIReasoner``
    High-level reasoning methods:
    * ``analyze_asset``     — per-asset insight extraction
    * ``cross_analyze``     — pattern detection across the full model
    * ``detect_gaps``       — structured gap records
    * ``estimate_signal_strength`` — how relevant an asset is
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Dict, List, Optional

from core.domain.ai.semantic_analyzer import INSIGHT_KEYS, analyze as _semantic_analyze
from core.domain.ai_prompt_builder import build_prompt

# ---------------------------------------------------------------------------
# Evidence weights — how much trust to place in each source type
# ---------------------------------------------------------------------------

_EVIDENCE_WEIGHTS: Dict[str, float] = {
    "code_file":          1.00,
    "sql_procedure":      0.95,
    "sql_table":          0.95,
    "batch":              0.90,
    "event":              0.90,
    "webhook":            0.90,
    "background":         0.90,
    "work_items_batch":   0.75,
    "wiki_section":       0.70,
    "git_insights_batch": 0.60,
    "labels_namespace":   0.50,
    "pdf_section":        0.50,
}


# ---------------------------------------------------------------------------
# Gap type constants
# ---------------------------------------------------------------------------

GAP_TYPES = (
    "missing_entity",
    "missing_flow",
    "orphan_event",
    "weak_rule",
    "incomplete_integration",
    "missing_context",
)

# Per-section targets mirror domain_scoring._SECTION_TARGETS
_SECTION_TARGETS: Dict[str, int] = {
    "entities":     5,
    "behaviors":    5,
    "flows":        3,
    "rules":        3,
    "events":       2,
    "integrations": 2,
}

# Gap type mapped from section name
_SECTION_GAP_TYPE: Dict[str, str] = {
    "entities":     "missing_entity",
    "behaviors":    "missing_entity",     # behaviors are entity-like
    "flows":        "missing_flow",
    "rules":        "weak_rule",
    "events":       "orphan_event",
    "integrations": "incomplete_integration",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slug(text: str) -> str:
    """Convert *text* to a lowercase slug."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def _sha8(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# AIProvider interface
# ---------------------------------------------------------------------------


class AIProvider:
    """Abstract AI provider interface.

    Subclass and override ``generate_json`` to plug in a live LLM.
    """

    def generate_json(self, prompt: str, schema_name: str) -> Dict[str, Any]:
        """Generate a structured JSON response for *prompt*.

        Parameters
        ----------
        prompt:
            The full prompt string.
        schema_name:
            A hint about the expected JSON schema (e.g. ``"asset_insight"``).

        Returns
        -------
        dict
            Structured JSON response.  Must never return None.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# HeuristicAIProvider — default stub (no LLM)
# ---------------------------------------------------------------------------


class HeuristicAIProvider(AIProvider):
    """Deterministic heuristic provider.

    Extracts domain knowledge using regex patterns.  No network calls.
    Output is structurally identical to what a real LLM provider would
    return for ``schema_name="asset_insight"``.
    """

    # Patterns for intent/role extraction
    _CLASS_PAT = re.compile(r"\b(?:class|interface|struct|record)\s+(\w+)", re.IGNORECASE)
    _METHOD_PAT = re.compile(
        r"\b(?:public|private|protected|internal)\s+(?:async\s+)?(?:\w+\s+)+(\w+)\s*\(",
        re.IGNORECASE,
    )
    _RULE_PAT = re.compile(
        r"\b(?:if|when|must|should|require|validate|assert|check|throw|guard)\b[^\n]{0,80}",
        re.IGNORECASE,
    )
    # Fix 3: expanded event patterns — captures Commands, RxJS next(), MSAL EventType, Angular emitters
    _EVENT_PAT = re.compile(r"\b(\w+(?:Event|Notification|Command|Query|Message))\b")
    _EVENT_RXJS_PAT = re.compile(r"\.next\((\w+)\)")
    _EVENT_MSAL_PAT = re.compile(r"EventType\.(\w+)")
    _EVENT_EMITTER_PAT = re.compile(r"eventsManager\.(\w+)\.")
    # Fix 1: named integration detection — emits structured names, not raw tokens
    _NAMED_INTEGRATION_PATTERNS: List = [
        ("Azure AD (MSAL)",       re.compile(r"MsalService|MsalBroadcastService|@azure/msal", re.IGNORECASE)),
        ("SAML2 SSO",              re.compile(r"CustomerSamlSettings|SamlSettings|EntityId.*MetadataUrl|SAML2|ITfoxtec", re.IGNORECASE)),
        ("SCIM 2.0",               re.compile(r"ScimUsersController|ScimGroupsController|ScimTokenUUID|ScimExternalId", re.IGNORECASE)),
        ("TOTP Authenticator",     re.compile(r"AuthenticatorSecret|TwoFactorAuthNet|getAuthenticatorSecretQR|confirmAuthenticatorApp|TwoFactorModel", re.IGNORECASE)),
        ("Email Notification",     re.compile(r"EmailTemplateName|send2FaCodeByEmail|ResetSAMLUser|NewSAMLUser|IEmailService|SmtpClient", re.IGNORECASE)),
        ("SMS Gateway",            re.compile(r"send2FaCodeBySms|sendPinCode.*sms|ISmsService|SmsService|SmsClient", re.IGNORECASE)),
        ("MediatR Event Bus",      re.compile(r"IMediator|MediatR|IRequest|INotification|IRequestHandler|INotificationHandler", re.IGNORECASE)),
        ("HTTP REST Client",       re.compile(r"HttpClient|IHttpClientFactory|WebClient|RestClient|ApiClient", re.IGNORECASE)),
        ("Azure Service Bus",      re.compile(r"ServiceBusClient|ServiceBusSender|ServiceBusProcessor|ITopicClient", re.IGNORECASE)),
        ("Database (EF Core)",     re.compile(r"DbContext|IRepository|DbSet<|EntityFramework|EfCoreRepository", re.IGNORECASE)),
        ("Azure Blob Storage",     re.compile(r"BlobClient|BlobServiceClient|BlobContainerClient|IBlobService", re.IGNORECASE)),
    ]
    # Fix 1: generic HTTP URLs as fallback
    _HTTP_URL_PAT = re.compile(r"https?://[^\s\"'<>{}\[\]]+")
    # Fix 4: Angular component / service detection
    _ANGULAR_SELECTOR_PAT = re.compile(r"selector:\s*['\"]([a-z][a-z0-9-]*)['\"]")
    _ANGULAR_ROUTE_PAT    = re.compile(r"path:\s*['\"]([^'\"]{1,80})['\"]")
    _ANGULAR_GUARD_PAT    = re.compile(r"CanActivate|canActivate|CanMatch|canMatch", re.IGNORECASE)
    _ANGULAR_INJECTABLE_PAT = re.compile(r"@Injectable")
    _ANGULAR_HTTP_CALL_PAT  = re.compile(r"this\.http\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]")
    _FLOW_PAT = re.compile(
        r"\b(\w+(?:Flow|Process|Pipeline|Workflow|Handler|Processor|Step))\b"
    )

    def _extract(self, pat: re.Pattern, text: str, group: int = 1, limit: int = 8) -> List[str]:
        found: set = set()
        for m in pat.finditer(text):
            try:
                token = m.group(group).strip()
            except IndexError:
                token = m.group(0).strip()
            if token:
                found.add(token)
        return sorted(found)[:limit]

    def _extract_named_integrations(self, text: str) -> List[str]:
        """Fix 1: return human-readable integration names matched in text."""
        found: List[str] = []
        for name, pat in self._NAMED_INTEGRATION_PATTERNS:
            if pat.search(text):
                found.append(name)
        # Also pick up raw HTTP URLs as fallback
        for m in self._HTTP_URL_PAT.finditer(text):
            url = m.group(0)[:60]
            if url not in found:
                found.append(url)
        return found[:8]

    def _extract_events_expanded(self, text: str) -> List[str]:
        """Fix 3: extract events from multiple patterns (suffix, RxJS, MSAL, emitters)."""
        found: set = set()
        for m in self._EVENT_PAT.finditer(text):
            found.add(m.group(1))
        for m in self._EVENT_RXJS_PAT.finditer(text):
            tok = m.group(1)
            if len(tok) > 2 and not tok[0].isdigit():
                found.add(tok)
        for m in self._EVENT_MSAL_PAT.finditer(text):
            found.add(f"MsalEvent.{m.group(1)}")
        for m in self._EVENT_EMITTER_PAT.finditer(text):
            tok = m.group(1)
            if len(tok) > 3:
                found.add(tok)
        return sorted(found)[:10]

    def _extract_angular_hints(self, text: str) -> Dict[str, Any]:
        """Fix 4: extract Angular-specific patterns for component/service detection."""
        selectors = [m.group(1) for m in self._ANGULAR_SELECTOR_PAT.finditer(text)]
        routes    = [m.group(1) for m in self._ANGULAR_ROUTE_PAT.finditer(text)][:4]
        is_guard  = bool(self._ANGULAR_GUARD_PAT.search(text))
        is_service = bool(self._ANGULAR_INJECTABLE_PAT.search(text))
        api_calls = [
            f"{m.group(1).upper()} {m.group(2)}"
            for m in self._ANGULAR_HTTP_CALL_PAT.finditer(text)
        ][:5]
        return {
            "selectors":  selectors,
            "routes":     routes,
            "is_guard":   is_guard,
            "is_service": is_service,
            "api_calls":  api_calls,
        }

    def _generate_pseudocode(self, text: str, entities: List[str], behaviors: List[str], rules: List[str]) -> List[str]:
        """Fix 5: generate readable pseudo-steps from code patterns."""
        steps: List[str] = []
        # Step 1: derive action steps from public methods
        for b in behaviors[:5]:
            steps.append(f"ACTION: call {b}")
        # Step 2: derive guard steps from rule snippets
        for r in rules[:3]:
            trimmed = r.strip()[:70]
            steps.append(f"GUARD: {trimmed}")
        # Step 3: detect HTTP call patterns
        http_pats = re.findall(
            r"(?:HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch|http\.(?:get|post|put|delete|patch))\b[^;\n]{0,60}",
            text, re.IGNORECASE,
        )
        for h in http_pats[:3]:
            steps.append(f"HTTP: {h.strip()[:70]}")
        # Step 4: detect conditional branches
        branches = re.findall(r"if\s*\([^)]{5,60}\)", text)[:3]
        for b in branches:
            steps.append(f"IF: {b.strip()[:70]}")
        return steps[:10]

    def generate_json(self, prompt: str, schema_name: str) -> Dict[str, Any]:
        """Analyse the prompt text heuristically."""
        text = prompt

        entities = self._extract(self._CLASS_PAT, text)
        behaviors = self._extract(self._METHOD_PAT, text)
        rules: List[str] = []
        for m in self._RULE_PAT.finditer(text):
            snippet = m.group(0).strip()[:80]
            if snippet:
                rules.append(snippet)
        rules = sorted(set(rules))[:5]
        # Fix 3: expanded event detection
        events = self._extract_events_expanded(text)
        # Fix 1: named integration detection
        integrations = self._extract_named_integrations(text)
        flows = self._extract(self._FLOW_PAT, text)
        # Fix 4: Angular hints merged into entities/flows/integrations
        angular = self._extract_angular_hints(text)
        if angular["selectors"]:
            # Selector names are Angular component display names → entities
            entities = sorted(set(entities) | {
                sel.replace("-", " ").title().replace(" ", "") for sel in angular["selectors"]
            })[:8]
        if angular["is_guard"]:
            flows = sorted(set(flows) | {"RouteGuard"})[:8]
        if angular["is_service"]:
            integrations = sorted(set(integrations) | {"Angular Injectable Service"})[:8]
        if angular["api_calls"]:
            integrations = sorted(set(integrations) | set(angular["api_calls"]))[:8]
        # Fix 5: generate pseudocode steps
        pseudocode = self._generate_pseudocode(text, entities, behaviors, rules)

        # Derive intent from path tokens
        path_tokens = re.findall(r"[A-Za-z][a-z]+|[A-Z]{2,}", text.split("\n")[0])
        intent = " ".join(path_tokens[:8]) if path_tokens else "unknown intent"
        domain_role = f"Contributes to {intent[:50]}"

        rebuild_note = (
            f"Implements {entities[0] if entities else 'module'} "
            f"with {len(behaviors)} behaviors, {len(integrations)} integrations, "
            f"{len(events)} events"
        )

        return {
            "intent":       intent,
            "domain_role":  domain_role,
            "entities":     entities,
            "behaviors":    behaviors,
            "rules":        rules,
            "flow_relevance": flows,
            "events":       events,
            "integrations": integrations,
            "pseudocode":   pseudocode,
            "rebuild_note": rebuild_note,
        }


# ---------------------------------------------------------------------------
# OpenAIJsonProvider — real LLM provider (optional, requires openai package)
# ---------------------------------------------------------------------------


class OpenAIJsonProvider(AIProvider):
    """Live OpenAI-backed provider.

    Reads configuration from environment variables:
    * ``DOMAIN_ENGINE_AI_MODEL``    — model name (default: ``gpt-4o-mini``)
    * ``DOMAIN_ENGINE_AI_PROVIDER`` — provider tag  (default: ``openai``)
    * ``OPENAI_API_KEY``            — API key (required by openai library)

    Retries up to ``_MAX_RETRIES`` times on transient errors.
    """

    _MAX_RETRIES: int = 3

    def __init__(self) -> None:
        self._model = os.environ.get("DOMAIN_ENGINE_AI_MODEL", "gpt-4o-mini")

    def generate_json(self, prompt: str, schema_name: str) -> Dict[str, Any]:
        """Call the OpenAI chat-completions endpoint and return parsed JSON."""
        try:
            import openai  # noqa: PLC0415  (optional dependency)
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "openai package is not installed. "
                "Run: pip install openai"
            ) from exc

        client = openai.OpenAI()
        last_exc: Optional[Exception] = None
        for attempt in range(self._MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model=self._model,
                    temperature=0,
                    response_format={"type": "json_object"},
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a domain knowledge extractor. "
                                "Respond ONLY with valid JSON. "
                                "Never include code snippets or raw source code."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                raw = response.choices[0].message.content or "{}"
                import json  # noqa: PLC0415
                return json.loads(raw)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self._MAX_RETRIES - 1:
                    import time  # noqa: PLC0415
                    time.sleep(2 ** attempt)
        raise RuntimeError(
            f"OpenAIJsonProvider failed after {self._MAX_RETRIES} attempts"
        ) from last_exc


# ---------------------------------------------------------------------------
# CompositeAIProvider — tries real provider, falls back to heuristic
# ---------------------------------------------------------------------------


class CompositeAIProvider(AIProvider):
    """Wraps a primary provider with a heuristic fallback.

    When ``DOMAIN_ENGINE_AI_ENABLED`` is ``"false"`` (case-insensitive),
    the heuristic provider is always used regardless of what *real_provider*
    is set to.

    Parameters
    ----------
    real_provider:
        The primary (live LLM) provider.  Defaults to ``OpenAIJsonProvider``.
    fallback:
        Fallback provider used on errors.  Defaults to ``HeuristicAIProvider``.
    """

    def __init__(
        self,
        real_provider: Optional[AIProvider] = None,
        fallback: Optional[AIProvider] = None,
    ) -> None:
        self._real = real_provider or OpenAIJsonProvider()
        self._fallback = fallback or HeuristicAIProvider()

    def _ai_enabled(self) -> bool:
        return os.environ.get("DOMAIN_ENGINE_AI_ENABLED", "true").lower() not in (
            "false", "0", "no", "off"
        )

    def generate_json(self, prompt: str, schema_name: str) -> Dict[str, Any]:
        if not self._ai_enabled():
            return self._fallback.generate_json(prompt, schema_name)
        try:
            return self._real.generate_json(prompt, schema_name)
        except Exception:  # noqa: BLE001
            return self._fallback.generate_json(prompt, schema_name)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_provider_from_env() -> AIProvider:
    """Construct the appropriate AI provider based on environment variables.

    * ``DOMAIN_ENGINE_AI_ENABLED=false`` → ``HeuristicAIProvider``
    * ``DOMAIN_ENGINE_AI_PROVIDER=openai`` (default) → ``CompositeAIProvider``
      wrapping ``OpenAIJsonProvider`` with heuristic fallback.
    * Any other value → ``HeuristicAIProvider``.
    """
    enabled = os.environ.get("DOMAIN_ENGINE_AI_ENABLED", "true").lower() not in (
        "false", "0", "no", "off"
    )
    if not enabled:
        return HeuristicAIProvider()

    provider_tag = os.environ.get("DOMAIN_ENGINE_AI_PROVIDER", "openai").lower()
    if provider_tag == "openai":
        return CompositeAIProvider()
    return HeuristicAIProvider()


# ---------------------------------------------------------------------------
# AIReasoner
# ---------------------------------------------------------------------------


class AIReasoner:
    """High-level reasoning over assets and domain models.

    Parameters
    ----------
    provider:
        AI provider.  Defaults to ``HeuristicAIProvider``.
    """

    def __init__(self, provider: Optional[AIProvider] = None) -> None:
        self._provider = provider or HeuristicAIProvider()

    # ------------------------------------------------------------------
    # Per-asset analysis
    # ------------------------------------------------------------------

    def analyze_asset(self, asset: Dict[str, Any], domain_name: str) -> Dict[str, Any]:
        """Extract domain insight from a single asset.

        Combines ``semantic_analyzer.analyze()`` with the provider's
        structured output, merging results into the canonical INSIGHT_KEYS
        format.

        Returns
        -------
        dict
            Keys: all INSIGHT_KEYS + optional ``"signal_strength"`` float.
        """
        # Base extraction via existing semantic analyzer
        base = _semantic_analyze(asset, domain_name)

        # Provider enrichment via prompt
        prompt = build_prompt(asset, domain_name)
        try:
            enriched = self._provider.generate_json(prompt, schema_name="asset_insight")
        except Exception:
            enriched = {}

        # Merge into canonical insight keys
        insight: Dict[str, Any] = {k: list(base.get(k) or []) for k in INSIGHT_KEYS}

        # Map provider output to insight keys
        _provider_map = {
            "entities":     ["entities"],
            "behaviors":    ["behaviors"],
            "rules":        ["rules"],
            "events":       ["events"],
            "integrations": ["integrations"],
            "flows":        ["flow_relevance"],   # provider uses flow_relevance → flows
            "pseudocode":   ["pseudocode"],       # Fix 5: map pseudocode steps
            "rebuild":      ["rebuild_note"],
            "batch":        [],
        }
        for insight_key, provider_keys in _provider_map.items():
            for pkey in provider_keys:
                val = enriched.get(pkey)
                if isinstance(val, list):
                    insight[insight_key] = sorted(
                        set(insight[insight_key]) | {str(x) for x in val if x}
                    )
                elif isinstance(val, str) and val.strip():
                    insight[insight_key] = sorted(
                        set(insight[insight_key]) | {val.strip()}
                    )

        insight["signal_strength"] = round(self.estimate_signal_strength(asset, domain_name), 4)
        return insight

    # ------------------------------------------------------------------
    # Cross-model analysis
    # ------------------------------------------------------------------

    def cross_analyze(
        self, domain_model: Dict[str, Any], domain_name: str
    ) -> Dict[str, Any]:
        """Detect cross-cutting patterns in the full domain model.

        Returns a dict with:
        * ``linked_pairs``              — entity pairs that likely interact
        * ``flow_stubs``                — flow names inferred from entity names
        * ``coverage``                  — per-section item counts
        * ``consistency``               — 0-1 score of cross-source agreement
        * ``confirmed_entities``        — entities appearing in ≥2 sections
        * ``confirmed_flows``           — flows with matching events or behaviors
        * ``confirmed_rules``           — rules with an enforcement point in code
        * ``uncertain_items``           — items appearing in only one section
        * ``contradictions``            — items with conflicting signals
        * ``recommended_focus_terms``   — search terms to fill remaining gaps
        """
        entities = list(domain_model.get("entities") or [])
        flows = list(domain_model.get("flows") or [])
        rules = list(domain_model.get("rules") or [])
        events = list(domain_model.get("events") or [])
        behaviors = list(domain_model.get("behaviors") or [])
        integrations = list(domain_model.get("integrations") or [])

        # Detect entity pairs that share name tokens (e.g. UserService + UserRepo)
        linked_pairs: List[str] = []
        for i, a in enumerate(entities):
            for b in entities[i + 1:]:
                a_tok = set(re.findall(r"[A-Za-z][a-z]+|[A-Z]+(?=[A-Z][a-z]|$)", a))
                b_tok = set(re.findall(r"[A-Za-z][a-z]+|[A-Z]+(?=[A-Z][a-z]|$)", b))
                if a_tok & b_tok:
                    linked_pairs.append(f"{a} ↔ {b}")
        linked_pairs = sorted(linked_pairs)[:10]

        # Infer flow stubs from behavior names (verbs → flows)
        _VERB_PAT = re.compile(
            r"^(?:Send|Create|Update|Delete|Get|List|Process|Handle|Publish|Subscribe|"
            r"Validate|Import|Export|Notify|Build|Generate|Calculate|Apply)\w+",
            re.IGNORECASE,
        )
        flow_stubs = sorted({b for b in behaviors if _VERB_PAT.match(b)})[:10]

        # Coverage dict
        coverage = {k: len(domain_model.get(k) or []) for k in INSIGHT_KEYS}

        # Consistency: how many sections have at least their minimum items
        scored = sum(
            1
            for key, target in _SECTION_TARGETS.items()
            if len(domain_model.get(key) or []) >= target
        )
        consistency = round(scored / len(_SECTION_TARGETS), 4)

        # ------------------------------------------------------------------
        # Confirmed / uncertain / contradictions
        # ------------------------------------------------------------------

        # confirmed_entities: appear in entities AND referenced in behaviors
        behavior_text = " ".join(behaviors).lower()
        confirmed_entities = sorted(
            e for e in entities if _slug(e) in behavior_text or any(
                tok.lower() in behavior_text
                for tok in re.findall(r"[A-Za-z][a-z]+|[A-Z]+(?=[A-Z][a-z]|$)", e)
                if len(tok) > 3
            )
        )[:10]

        # confirmed_flows: flows that have a matching event or behavior stub
        flow_names_lower = {_slug(f) for f in flows}
        event_text = " ".join(events).lower()
        confirmed_flows = sorted(
            f for f in flows if _slug(f) in event_text or any(
                fb for fb in flow_stubs if _slug(f) in _slug(fb) or _slug(fb) in _slug(f)
            )
        )[:10]

        # confirmed_rules: rules that mention an entity or flow name
        entity_slugs = {_slug(e) for e in entities}
        confirmed_rules = sorted(
            r for r in rules if any(es in r.lower() for es in entity_slugs)
        )[:10]

        # uncertain_items: entities NOT in confirmed_entities
        uncertain_items = sorted(set(entities) - set(confirmed_entities))[:10]

        # contradictions: flows named in rules but absent from flows list
        rule_text = " ".join(rules).lower()
        contradictions: List[str] = []
        for stub in flow_stubs:
            if _slug(stub) not in flow_names_lower and stub.lower() in rule_text:
                contradictions.append(f"flow '{stub}' referenced in rules but not in flows")
        contradictions = sorted(contradictions)[:5]

        # recommended_focus_terms: gap-filling hints
        focus_terms: set = set()
        if len(entities) < _SECTION_TARGETS["entities"]:
            focus_terms.update(["class", "interface", "service", "manager"])
        if len(flows) < _SECTION_TARGETS["flows"]:
            focus_terms.update(["process", "pipeline", "handler", "workflow"])
        if len(rules) < _SECTION_TARGETS["rules"]:
            focus_terms.update(["validate", "check", "must", "require"])
        if len(events) < _SECTION_TARGETS["events"]:
            focus_terms.update(["event", "notification", "command", "publish"])
        if len(integrations) < _SECTION_TARGETS["integrations"]:
            focus_terms.update(["httpclient", "api", "webhook", "endpoint"])
        recommended_focus_terms = sorted(focus_terms)[:10]

        return {
            "domain": domain_name,
            "linked_pairs": linked_pairs,
            "flow_stubs": flow_stubs,
            "coverage": coverage,
            "consistency": consistency,
            "confirmed_entities": confirmed_entities,
            "confirmed_flows": confirmed_flows,
            "confirmed_rules": confirmed_rules,
            "uncertain_items": uncertain_items,
            "contradictions": contradictions,
            "recommended_focus_terms": recommended_focus_terms,
        }

    # ------------------------------------------------------------------
    # Gap detection
    # ------------------------------------------------------------------

    def detect_gaps(
        self, domain_model: Dict[str, Any], domain_name: str
    ) -> List[Dict[str, Any]]:
        """Return a list of structured gap records for *domain_model*.

        Each gap has a stable ``id`` so gap lists can be diffed across
        iterations.

        Returns
        -------
        list[dict]
            Sorted by priority (high → medium → low), then by id.
        """
        gaps: List[Dict[str, Any]] = []

        for section, target in _SECTION_TARGETS.items():
            items = list(domain_model.get(section) or [])
            count = len(items)
            if count >= target:
                continue

            gap_type = _SECTION_GAP_TYPE.get(section, "missing_context")
            shortfall = target - count
            priority = "high" if count == 0 else ("medium" if count < target // 2 + 1 else "low")
            slug = _slug(f"{section}_{shortfall}")
            gap_id = f"gap:{domain_name}:{gap_type}:{slug}"

            # Suggest search terms based on section and domain
            suggested_terms = [section, domain_name.replace("_", " ")]
            if section == "entities":
                suggested_terms += ["class", "interface", "service", "manager"]
            elif section == "flows":
                suggested_terms += ["process", "pipeline", "handler", "workflow"]
            elif section == "rules":
                suggested_terms += ["validate", "check", "must", "require"]
            elif section == "events":
                suggested_terms += ["event", "notification", "command", "publish"]
            elif section == "integrations":
                suggested_terms += ["httpclient", "api", "webhook", "endpoint"]

            gaps.append(
                {
                    "id": gap_id,
                    "type": gap_type,
                    "priority": priority,
                    "description": (
                        f"Section '{section}' has {count}/{target} items "
                        f"(need {shortfall} more)"
                    ),
                    "suggested_terms": sorted(set(suggested_terms)),
                    "related_asset_ids": [],
                }
            )

        # Also flag missing flows when flow_stubs exist in cross-analysis
        if not (domain_model.get("flows") or []):
            if domain_model.get("behaviors"):
                gap_id = f"gap:{domain_name}:missing_flow:no_explicit_flows"
                gaps.append(
                    {
                        "id": gap_id,
                        "type": "missing_flow",
                        "priority": "medium",
                        "description": "Behaviors exist but no explicit flows documented",
                        "suggested_terms": ["flow", "pipeline", "process", "workflow"],
                        "related_asset_ids": [],
                    }
                )

        # Add missing_context gap when rebuild section is empty
        if not (domain_model.get("rebuild") or []):
            gap_id = f"gap:{domain_name}:missing_context:no_rebuild_notes"
            gaps.append(
                {
                    "id": gap_id,
                    "type": "missing_context",
                    "priority": "low",
                    "description": "No rebuild notes — domain cannot be reconstructed",
                    "suggested_terms": ["rebuild", "reconstruct", "implement"],
                    "related_asset_ids": [],
                }
            )

        _PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
        return sorted(gaps, key=lambda g: (_PRIORITY_ORDER.get(g["priority"], 9), g["id"]))

    # ------------------------------------------------------------------
    # Signal strength
    # ------------------------------------------------------------------

    def estimate_signal_strength(
        self, asset: Dict[str, Any], domain_name: str
    ) -> float:
        """Return 0.0–1.0 relevance score for *asset* in *domain_name*.

        Combines path overlap, keyword density, and asset type weight.
        """
        from core.domain.domain_asset_matcher import _DOMAIN_KEYWORDS, _get_patterns  # noqa: PLC0415

        text = (
            (asset.get("id") or "")
            + " "
            + (asset.get("path") or "")
            + " "
            + (asset.get("content") or "")
        ).lower()

        # Keyword density
        patterns = _get_patterns(domain_name)
        kw_hits = sum(1 for pat in patterns.values() if pat.search(text))
        kw_score = min(kw_hits / max(len(patterns), 1), 1.0)

        # Name tokens
        name_parts = domain_name.lower().split("_")
        id_path = (
            (asset.get("id") or "") + " " + (asset.get("path") or "")
        ).lower()
        name_score = 1.0 if any(p in id_path for p in name_parts) else 0.0

        # Asset type weight
        _TYPE_WEIGHTS = {
            "code_file": 1.0,
            "sql": 0.9,
            "wiki_section": 0.8,
            "work_items_batch": 0.6,
            "git_insights_batch": 0.4,
            "labels_namespace": 0.3,
            "pdf_section": 0.5,
        }
        type_weight = _TYPE_WEIGHTS.get(asset.get("type", ""), 0.5)

        return round(
            (kw_score * 0.4 + name_score * 0.4 + type_weight * 0.2),
            4,
        )
