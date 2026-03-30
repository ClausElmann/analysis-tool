"""Domain asset matcher — maps assets to a domain using keyword and path heuristics.

Output is always:
* sorted (deterministic)
* deduplicated
* based only on the asset dict fields (id, path, content)
"""

from __future__ import annotations

import re
from typing import Dict, List

# ---------------------------------------------------------------------------
# Domain keyword registry
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "identity_access": [
        "identity", "auth", "login", "logout", "token", "jwt", "oauth",
        "permission", "role", "claim", "user", "password", "credential",
        "otp", "mfa", "sso", "openid",
    ],
    "customer_administration": [
        "customer", "account", "organisation", "organization", "company",
        "tenant", "profile", "address", "contact", "crm", "client",
    ],
    "messaging": [
        "message", "sms", "email", "notification", "send", "deliver",
        "template", "channel", "inbox", "outbox", "recipient", "text",
        "push", "mms",
    ],
    "recipient_management": [
        "recipient", "subscriber", "contact", "distribution", "list",
        "group", "segment", "target", "import", "export",
    ],
    "subscriptions": [
        "subscription", "subscribe", "unsubscribe", "plan", "billing",
        "invoice", "payment", "renew", "trial", "tier", "licence", "license",
    ],
    "reporting": [
        "report", "statistic", "analytic", "dashboard", "chart",
        "export", "csv", "summary", "aggregate", "metric",
    ],
    "monitoring": [
        "monitor", "health", "alert", "heartbeat", "watchdog",
        "log", "trace", "diagnostic", "uptime", "status",
    ],
    "benchmark": [
        "benchmark", "performance", "throughput", "latency", "load",
        "stress", "measure", "kpi", "sla",
    ],
    "pipeline_sales": [
        "sales", "pipeline", "lead", "deal", "opportunity",
        "funnel", "stage", "prospect", "conversion",
    ],
    "integrations": [
        "integration", "api", "webhook", "endpoint", "connector",
        "sync", "bridge", "adapter", "provider", "gateway", "http",
    ],
}

# Precompiled word-boundary patterns (keyword → pattern)
_COMPILED: Dict[str, Dict[str, re.Pattern]] = {}


def _get_patterns(domain_name: str) -> Dict[str, re.Pattern]:
    if domain_name not in _COMPILED:
        keywords = _DOMAIN_KEYWORDS.get(domain_name, [domain_name.replace("_", " ")])
        _COMPILED[domain_name] = {
            kw: re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
            for kw in keywords
        }
    return _COMPILED[domain_name]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _asset_text(asset: Dict) -> str:
    """Return combined, lowercased searchable text from an asset dict."""
    return " ".join(
        str(asset.get(f, "") or "")
        for f in ("id", "path", "content")
    ).lower()


def _name_variants(domain_name: str) -> List[str]:
    """Return all lowercase substrings of the domain name (word parts)."""
    return [v for v in domain_name.lower().split("_") if v]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def match_assets(domain_name: str, assets: List[Dict]) -> List[str]:
    """Return sorted, deduplicated asset IDs that match *domain_name*.

    Matching strategy (an asset matches if ANY rule fires):
    1. Any name-variant of the domain name appears in id or path.
    2. At least one keyword from the domain keyword list appears as a whole
       word in ``id + path + content``.
    """
    patterns = _get_patterns(domain_name)
    variants = _name_variants(domain_name)

    matched: set = set()
    for asset in assets:
        asset_id = asset.get("id", "")
        text = _asset_text(asset)

        # Rule 1 — domain name fragment in id/path
        id_path = (str(asset.get("id", "")) + " " + str(asset.get("path", ""))).lower()
        if any(v in id_path for v in variants):
            matched.add(asset_id)
            continue

        # Rule 2 — keyword word-boundary match anywhere in the asset
        if any(pat.search(text) for pat in patterns.values()):
            matched.add(asset_id)

    return sorted(matched)
