"""
capability_extractor_greenai.py — GreenAI capability extractor.

RULES:
- Reads ONLY from green-ai source code
- Parses: Endpoints, Handlers, Repositories, SQL files
- Every capability carries evidence: file + method + line

Extracts capabilities from:
  - Features/**/*Handler.cs
  - Features/**/*Endpoint.cs
  - Features/**/*Repository.cs
  - Features/**/*.sql

Output: list of CapabilityGreenAI dicts (same canonical structure as L0).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CapabilityGreenAI:
    id: str                             # unique slug e.g. "templates.list_templates"
    name: str
    domain: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    flow: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    http_method: Optional[str] = None   # GET / POST / PUT / DELETE
    http_route: Optional[str] = None    # e.g. "/api/v1/templates"
    raw_method: str = ""


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

_HANDLER_RE = re.compile(
    r"public\s+(?:async\s+)?Task<[^>]+>\s+Handle\s*\(",
    re.MULTILINE,
)

_MAP_METHOD_RE = re.compile(
    r"app\.(MapGet|MapPost|MapPut|MapDelete)\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

_COMMAND_QUERY_RE = re.compile(
    r"(?:record|class)\s+([A-Za-z_][A-Za-z0-9_]*(?:Command|Query|Request))\s*[({]",
    re.MULTILINE,
)

_RESULT_RE = re.compile(r"Result<([^>]+)>", re.MULTILINE)

_REPO_METHOD_RE = re.compile(
    r"(?:public|Task)\s+(?:async\s+)?(?:Task<[^>]+>|[A-Za-z_][A-Za-z0-9_<>]*)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*(?:Async)?)\s*\(",
    re.MULTILINE,
)

_SQL_TABLE_RE = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE)\s+(?:\[?dbo\]?\.)?\[?(\w+)\]?",
    re.IGNORECASE,
)

_CUSTOMER_FILTER = re.compile(r"CustomerId\s*=\s*@|CustomerID\s*=\s*@", re.I)
_PROFILE_FILTER  = re.compile(r"ProfileId\s*=\s*@|ProfileAccess|ProfileMappings", re.I)

# Capability detection: map file/class/method patterns → (cap_id_suffix, cap_name)
_CAPABILITY_HINTS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"GetTemplates?Handler|GetTemplates?Query",   re.I), "list_templates",          "List templates for profile"),
    (re.compile(r"GetTemplateById|TemplateById",              re.I), "get_template_by_id",      "Get single template by ID"),
    (re.compile(r"CreateTemplate|AddTemplate",               re.I), "create_template",         "Create new template"),
    (re.compile(r"UpdateTemplate|EditTemplate",              re.I), "update_template",         "Update existing template"),
    (re.compile(r"DeleteTemplate|RemoveTemplate",            re.I), "delete_template",         "Delete template"),
    (re.compile(r"AssignTemplateProfile|TemplateProfileAccess", re.I), "assign_template_profile", "Assign template to profile"),
    (re.compile(r"SendDirect",                               re.I), "send_direct",             "Send direct message"),
    (re.compile(r"GetAddressOwnership|AddressOwnership",     re.I), "address_ownership",       "Address + owner lookup"),
    (re.compile(r"AddressLookup",                            re.I), "address_lookup",          "Address lookup"),
    (re.compile(r"OwnerLookup",                              re.I), "owner_lookup",            "Property owner lookup"),
    (re.compile(r"CvrLookup",                                re.I), "cvr_lookup",              "CVR company lookup"),
    (re.compile(r"TrackDelivery",                            re.I), "track_delivery",          "Track delivery status"),
    (re.compile(r"MergeField|MergeContent",                  re.I), "merge_fields",            "Merge field substitution"),
    (re.compile(r"DynamicMergeField",                        re.I), "dynamic_merge_fields",    "Customer dynamic merge fields"),
    (re.compile(r"OutboxWorker|ProcessMessage",              re.I), "outbox_send",             "Outbox message processing"),
    (re.compile(r"ResolveContent|ResolveTemplate",           re.I), "resolve_template",        "Resolve template content"),
]


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class CapabilityExtractorGreenAI:
    """
    Walks a green-ai source tree and extracts capabilities.

    Usage:
        extractor = CapabilityExtractorGreenAI(root="C:/Udvikling/green-ai/src")
        caps = extractor.extract_domain("Templates")
    """

    def __init__(self, root: str):
        self.root = root
        self._cache: dict[str, list[CapabilityGreenAI]] = {}

    # ------------------------------------------------------------------
    def extract_domain(self, domain: str) -> list[CapabilityGreenAI]:
        if domain in self._cache:
            return self._cache[domain]

        caps: list[CapabilityGreenAI] = []
        for fpath, content in self._walk_source():
            caps.extend(self._extract_from_file(fpath, content, domain))

        seen: set[str] = set()
        unique: list[CapabilityGreenAI] = []
        for c in caps:
            if c.id not in seen:
                seen.add(c.id)
                unique.append(c)

        self._cache[domain] = unique
        return unique

    # ------------------------------------------------------------------
    def extract_all(self) -> list[CapabilityGreenAI]:
        caps: list[CapabilityGreenAI] = []
        for fpath, content in self._walk_source():
            caps.extend(self._extract_from_file(fpath, content, domain=None))

        seen: set[str] = set()
        unique: list[CapabilityGreenAI] = []
        for c in caps:
            if c.id not in seen:
                seen.add(c.id)
                unique.append(c)
        return unique

    # ------------------------------------------------------------------
    def _walk_source(self):
        extensions = {".cs", ".sql"}
        exclude_dirs = {"bin", "obj", ".git", "node_modules", "TestResults"}

        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
            rel_dir = os.path.relpath(dirpath, self.root)
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in extensions:
                    continue
                fpath = os.path.join(dirpath, fname)
                rel_path = os.path.join(rel_dir, fname).replace("\\", "/")
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        yield rel_path, f.read()
                except OSError:
                    continue

    # ------------------------------------------------------------------
    def _extract_from_file(
        self, rel_path: str, content: str, domain: Optional[str]
    ) -> list[CapabilityGreenAI]:
        caps: list[CapabilityGreenAI] = []
        lines = content.splitlines()

        file_domain = self._infer_domain(rel_path, content)

        # Detect HTTP mapping from endpoint files
        http_method = None
        http_route = None
        for m in _MAP_METHOD_RE.finditer(content):
            http_method = m.group(1).replace("Map", "").upper()
            http_route = m.group(2)

        # Try handler/endpoint class name first for hint matching
        fname_lower = os.path.splitext(os.path.basename(rel_path))[0].lower()

        for pattern, cap_id_suffix, cap_name in _CAPABILITY_HINTS:
            # Match against filename
            if not pattern.search(fname_lower) and not pattern.search(content[:2000]):
                continue

            inferred_domain = file_domain if file_domain.lower() != "unknown" else (
                domain or "Unknown"
            )

            # Domain filter: if explicit domain given, skip non-matching
            if domain is not None and inferred_domain.lower() != domain.lower():
                # Still include if cap_id_suffix is universally relevant
                if inferred_domain.lower() == "unknown":
                    inferred_domain = domain
                else:
                    continue

            cap_id = f"{inferred_domain.lower()}.{cap_id_suffix}"

            # Find line number (first Handle or Map method)
            line_no = 1
            for m in _HANDLER_RE.finditer(content):
                line_no = content[: m.start()].count("\n") + 1
                break

            cap = CapabilityGreenAI(
                id=cap_id,
                name=cap_name,
                domain=inferred_domain,
                inputs=self._extract_inputs(content),
                outputs=self._extract_outputs(content),
                side_effects=self._extract_side_effects(content, lines, line_no),
                rules=self._extract_rules(content),
                flow=self._extract_flow(content, http_route),
                evidence=[f"{rel_path}:{line_no}"],
                http_method=http_method,
                http_route=http_route,
            )
            caps.append(cap)
            break  # one cap per file

        return caps

    # ------------------------------------------------------------------
    def _infer_domain(self, rel_path: str, content: str) -> str:
        path_lower = rel_path.lower()
        if "template" in path_lower:
            return "Templates"
        if "senddirect" in path_lower or "send_direct" in path_lower:
            return "Send"
        if "outbox" in path_lower or "outboxworker" in path_lower:
            return "Send"
        if "lookup" in path_lower or "address" in path_lower or "owner" in path_lower or "cvr" in path_lower:
            return "Lookup"
        if "auth" in path_lower:
            return "Auth"
        if "profile" in path_lower:
            return "Profiles"
        return "Unknown"

    # ------------------------------------------------------------------
    def _extract_inputs(self, content: str) -> list[str]:
        inputs = []
        # From Command/Query record properties
        for m in re.finditer(
            r"(?:string|int|long|bool|Guid|decimal)\??\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|,|\)|\{)",
            content,
        ):
            name = m.group(1)
            if name[0].isupper():   # property-style names
                inputs.append(name)
        return list(dict.fromkeys(inputs))[:8]

    # ------------------------------------------------------------------
    def _extract_outputs(self, content: str) -> list[str]:
        outputs = []
        for m in _RESULT_RE.finditer(content):
            outputs.append(f"Result<{m.group(1)}>")
        return list(dict.fromkeys(outputs))[:4]

    # ------------------------------------------------------------------
    def _extract_side_effects(self, content: str, lines: list[str], line_no: int) -> list[str]:
        effects = []
        snippet = content
        tables = _SQL_TABLE_RE.findall(snippet)
        if re.search(r"\bINSERT\b", snippet, re.I):
            for t in set(tables):
                effects.append(f"INSERT → {t}")
        if re.search(r"\bUPDATE\b", snippet, re.I):
            for t in set(tables):
                effects.append(f"UPDATE → {t}")
        if re.search(r"\bDELETE\b", snippet, re.I):
            for t in set(tables):
                effects.append(f"DELETE → {t}")
        return list(dict.fromkeys(effects))

    # ------------------------------------------------------------------
    def _extract_rules(self, content: str) -> list[str]:
        rules = []
        if _CUSTOMER_FILTER.search(content):
            rules.append("Customer isolation")
        if _PROFILE_FILTER.search(content):
            rules.append("Profile visibility filter")
        if re.search(r"RequireAuthorization|Authorize\b", content):
            rules.append("Authorization required")
        if re.search(r"Result\.Fail|return Fail", content, re.I):
            rules.append("Validation / error handling")
        if re.search(r"ICurrentUser", content):
            rules.append("JWT identity (ICurrentUser)")
        return rules

    # ------------------------------------------------------------------
    def _extract_flow(self, content: str, http_route: Optional[str]) -> list[str]:
        flow = []
        if http_route:
            flow.append(f"HTTP endpoint: {http_route}")
        if re.search(r"ICurrentUser|_currentUser", content):
            flow.append("Read identity from JWT")
        if re.search(r"GetForProfile|GetTemplateById|templateRepo", content, re.I):
            flow.append("Load template from DB")
        if re.search(r"ResolveContent|TemplateId.*null", content, re.I):
            flow.append("Resolve template content")
        if re.search(r"MergeField|Substitute", content, re.I):
            flow.append("Merge field substitution")
        if re.search(r"InsertAsync|INSERT.*OutboundMessages", content, re.I):
            flow.append("Insert OutboundMessages row")
        if re.search(r"Result\.Ok|return Ok|ToHttpResult", content, re.I):
            flow.append("Return result")
        return flow
