"""
capability_extractor_l0.py — Level 0 (sms-service / ServiceAlert) capability extractor.

RULES:
- Reads ONLY from sms-service source code (Layer 0)
- Never uses analysis summaries, domains/, or ai-slices/
- Every capability carries evidence: file + method + line

Extracts capabilities from:
  - C# service classes (*Service.cs, *Repository.cs)
  - SQL files (.sql)
  - Endpoint/Controller .cs files

Output: list of CapabilityL0 dicts with canonical fields.
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
class CapabilityL0:
    id: str                            # unique slug e.g. "template.send_sms"
    name: str                          # human label
    domain: str                        # e.g. "Templates"
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    flow: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)   # ["file.cs:123 – MethodName"]
    raw_method: str = ""


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

_METHOD_RE = re.compile(
    r"(?:public|protected|internal|private)\s+"
    r"(?:async\s+)?(?:Task<[^>]+>|IEnumerable<[^>]+>|List<[^>]+>|[A-Za-z_][A-Za-z0-9_<>,\s]*?)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)",
    re.MULTILINE,
)

_CLASS_RE = re.compile(
    r"(?:public|internal)\s+(?:sealed\s+|abstract\s+|partial\s+)*class\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)

_INTERFACE_RE = re.compile(
    r"(?:public|internal)\s+interface\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)

_SQL_TABLE_RE = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE)\s+(?:\[?dbo\]?\.)?\[?(\w+)\]?",
    re.IGNORECASE,
)

_CUSTOMER_FILTER = re.compile(
    r"CustomerId\s*=\s*@Cust|WHERE.*CustomerID\s*=|customerid",
    re.IGNORECASE,
)

_PROFILE_FILTER = re.compile(
    r"ProfileId\s*=\s*@Prof|JOIN.*ProfileMappings|profileid",
    re.IGNORECASE,
)

# Capability keyword patterns → maps to capability hints
_CAPABILITY_HINTS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"GetTemplates?For|GetTemplates?\b", re.I),   "list_templates",       "List templates for profile"),
    (re.compile(r"SendSms|SendMessage|FillSmsLog",   re.I),   "send_sms",             "Send SMS to recipient"),
    (re.compile(r"SendEmail|SendMail",               re.I),   "send_email",           "Send Email to recipient"),
    (re.compile(r"MergeSmsText|MergeFields",         re.I),   "merge_fields",         "Merge field token substitution"),
    (re.compile(r"GetTemplateById|LoadTemplate",     re.I),   "get_template_by_id",   "Get single template by ID"),
    (re.compile(r"CreateTemplate|AddTemplate|InsertTemplate", re.I), "create_template", "Create new template"),
    (re.compile(r"UpdateTemplate|SaveTemplate",      re.I),   "update_template",      "Update existing template"),
    (re.compile(r"DeleteTemplate|RemoveTemplate",    re.I),   "delete_template",      "Delete template"),
    (re.compile(r"AssignProfile|AddProfile|GrantProfile|MapProfile", re.I), "assign_template_profile", "Assign template to profile"),
    (re.compile(r"RemoveProfile|RevokeProfile|UnmapProfile", re.I), "remove_template_profile", "Remove template from profile"),
    (re.compile(r"GetDynamicMerge|DynamicMergeField", re.I),  "dynamic_merge_fields", "Manage customer dynamic merge fields"),
    (re.compile(r"GetSmsGroup|CreateSmsGroup",       re.I),   "sms_group",            "SMS group management"),
    (re.compile(r"SendDirect|DirectSend",            re.I),   "send_direct",          "Send direct message"),
    (re.compile(r"LookupAddress|GetAddress|FindAddress", re.I), "address_lookup",     "Address lookup"),
    (re.compile(r"GetOwner|LookupOwner|FindOwner",   re.I),   "owner_lookup",         "Property owner lookup"),
]


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class CapabilityExtractorL0:
    """
    Walks a sms-service source tree and extracts capabilities.

    Usage:
        extractor = CapabilityExtractorL0(root="C:/Udvikling/sms-service")
        caps = extractor.extract_domain("Templates")
    """

    def __init__(self, root: str):
        self.root = root
        self._cache: dict[str, list[CapabilityL0]] = {}

    # ------------------------------------------------------------------
    def extract_domain(self, domain: str) -> list[CapabilityL0]:
        if domain in self._cache:
            return self._cache[domain]

        caps: list[CapabilityL0] = []

        for fpath, content in self._walk_source():
            new_caps = self._extract_from_file(fpath, content, domain)
            caps.extend(new_caps)

        # Deduplicate by id — keep first occurrence
        seen: set[str] = set()
        unique: list[CapabilityL0] = []
        for c in caps:
            if c.id not in seen:
                seen.add(c.id)
                unique.append(c)

        self._cache[domain] = unique
        return unique

    # ------------------------------------------------------------------
    def extract_all(self) -> list[CapabilityL0]:
        """Extract ALL capabilities across all domains."""
        caps: list[CapabilityL0] = []
        for fpath, content in self._walk_source():
            caps.extend(self._extract_from_file(fpath, content, domain=None))

        seen: set[str] = set()
        unique: list[CapabilityL0] = []
        for c in caps:
            if c.id not in seen:
                seen.add(c.id)
                unique.append(c)
        return unique

    # ------------------------------------------------------------------
    def _walk_source(self):
        """Yield (relative_path, content) for all relevant source files."""
        extensions = {".cs", ".sql"}
        exclude_dirs = {"bin", "obj", ".git", "node_modules", "migrations", "Migrations"}

        for dirpath, dirnames, filenames in os.walk(self.root):
            # Prune excluded dirs
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
    ) -> list[CapabilityL0]:
        caps: list[CapabilityL0] = []

        # Determine file-level domain from path / class names
        file_domain = self._infer_domain(rel_path, content)

        if domain is not None and file_domain.lower() != domain.lower():
            # Still check — file may contain cross-domain methods
            # but only include if a hint matches
            pass

        lines = content.splitlines()

        for match in _METHOD_RE.finditer(content):
            method_name = match.group(1)
            params = match.group(2)

            # Find line number
            line_no = content[: match.start()].count("\n") + 1

            # Check capability hints
            for pattern, cap_id_suffix, cap_name in _CAPABILITY_HINTS:
                if not pattern.search(method_name):
                    continue

                # Build capability id
                inferred_domain = file_domain if domain is None else (
                    file_domain if file_domain.lower() != "unknown" else domain
                )
                cap_id = f"{inferred_domain.lower()}.{cap_id_suffix}"

                cap = CapabilityL0(
                    id=cap_id,
                    name=cap_name,
                    domain=inferred_domain,
                    inputs=self._extract_inputs(params),
                    outputs=self._extract_outputs(match.group(0)),
                    side_effects=self._extract_side_effects(content, method_name, lines, line_no),
                    rules=self._extract_rules(content, method_name, lines, line_no),
                    flow=self._extract_flow(method_name, content, line_no, lines),
                    evidence=[f"{rel_path}:{line_no} – {method_name}"],
                    raw_method=method_name,
                )
                caps.append(cap)
                break  # one hint match per method

        return caps

    # ------------------------------------------------------------------
    def _infer_domain(self, rel_path: str, content: str) -> str:
        """Guess domain from path and class name."""
        path_lower = rel_path.lower()
        content_lower = content.lower()

        if "template" in path_lower or "template" in content_lower[:500]:
            return "Templates"
        if "send" in path_lower or "outbox" in path_lower or "smsgroup" in path_lower:
            return "Send"
        if "lookup" in path_lower or "address" in path_lower:
            return "Lookup"
        if "owner" in path_lower:
            return "Lookup"
        if "auth" in path_lower or "login" in path_lower or "token" in path_lower:
            return "Auth"
        if "profile" in path_lower:
            return "Profiles"
        if "customer" in path_lower:
            return "Customers"
        return "Unknown"

    # ------------------------------------------------------------------
    def _extract_inputs(self, params: str) -> list[str]:
        if not params.strip():
            return []
        parts = [p.strip() for p in params.split(",") if p.strip()]
        result = []
        for p in parts:
            tokens = p.split()
            if tokens:
                result.append(tokens[-1].lstrip("@"))
        return result[:8]  # cap at 8

    # ------------------------------------------------------------------
    def _extract_outputs(self, signature: str) -> list[str]:
        # Extract return type from signature
        m = re.search(
            r"(?:Task<([^>]+)>|IEnumerable<([^>]+)>|List<([^>]+)>|([A-Za-z_][A-Za-z0-9_]*))\s+\w+\s*\(",
            signature,
        )
        if m:
            ret = next((g for g in m.groups() if g), "void")
            return [ret]
        return []

    # ------------------------------------------------------------------
    def _extract_side_effects(
        self, content: str, method_name: str, lines: list[str], line_no: int
    ) -> list[str]:
        effects = []
        # Look at next 40 lines after method declaration for DB writes
        snippet = "\n".join(lines[line_no : line_no + 40])
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
        return list(dict.fromkeys(effects))  # deduplicate, preserve order

    # ------------------------------------------------------------------
    def _extract_rules(
        self, content: str, method_name: str, lines: list[str], line_no: int
    ) -> list[str]:
        rules = []
        snippet = "\n".join(lines[max(0, line_no - 2) : line_no + 60])
        if _CUSTOMER_FILTER.search(snippet):
            rules.append("Customer isolation")
        if _PROFILE_FILTER.search(snippet):
            rules.append("Profile visibility filter")
        if re.search(r"throw|ArgumentNull|Unauthorized|Forbidden|NotFound", snippet):
            rules.append("Validation / error handling")
        if re.search(r"transaction|BeginTransaction|ExecuteInTransaction", snippet, re.I):
            rules.append("Transactional")
        return rules

    # ------------------------------------------------------------------
    def _extract_flow(
        self, method_name: str, content: str, line_no: int, lines: list[str]
    ) -> list[str]:
        flow = [f"Call {method_name}"]
        snippet = "\n".join(lines[line_no : line_no + 50])

        if re.search(r"GetTemplate|LoadTemplate|templateRepo", snippet, re.I):
            flow.append("Load template from DB")
        if re.search(r"MergeSmsText|MergeField|Substitute", snippet, re.I):
            flow.append("Resolve merge fields")
        if re.search(r"SendSms|GatewaySend|_provider\.Send|SendAsync", snippet, re.I):
            flow.append("Send via provider")
        if re.search(r"INSERT.*OutboundMessages|OutboxRepo|InsertAsync", snippet, re.I):
            flow.append("Insert OutboundMessages row")
        if re.search(r"Status.*=.*Delivered|TrackDelivery", snippet, re.I):
            flow.append("Track delivery status")
        if re.search(r"return|Result\.Ok|Result\.Fail", snippet, re.I):
            flow.append("Return result")
        return flow
