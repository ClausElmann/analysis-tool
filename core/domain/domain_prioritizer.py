"""Domain prioritization engine — determines optimal build order of domains.

Uses a two-step approach:

1. **Foundation-tier rules** — keyword-based rules assign a baseline priority
   tier to each domain (e.g. identity/auth → tier 1, messaging → tier 4).
   Lower tier numbers = higher build priority.

2. **Cross-dependency coupling** — for each domain, counts how many other
   domains reference its vocabulary.  Domains referenced by many others
   are pulled earlier in the build order (higher coupling → built first).

Output is always sorted by ``(tier asc, coupling desc, domain asc)``
for deterministic, stable ordering.

Output format (``domain_priority.json``)::

    [
      {"domain": "identity_access", "priority": 1, "tier": 1,
       "reason": "tier 1 foundation; referenced by 3 other domain(s)"},
      ...
    ]
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Tuple

from core.domain.domain_discovery import DomainCandidate

# ---------------------------------------------------------------------------
# Foundation-tier rules
# (tier, trigger_keywords) — lowest matching tier wins per domain
# ---------------------------------------------------------------------------

_FOUNDATION_TIERS: List[Tuple[int, List[str]]] = [
    (1,  ["identity", "auth", "login", "logout", "token", "jwt", "oauth",
          "session", "credential", "access"]),
    (2,  ["user", "customer", "account", "profile", "tenant", "client",
          "organisation", "organization"]),
    (3,  ["permission", "role", "policy", "privilege", "entitlement",
          "claims", "scope", "authoriz"]),
    (4,  ["message", "sms", "email", "notification", "send", "deliver",
          "channel", "inbox", "outbox"]),
    (5,  ["recipient", "contact", "subscriber", "distribution", "group",
          "segment", "target"]),
    (6,  ["subscription", "billing", "payment", "invoice", "plan",
          "renew", "trial", "tier", "licen"]),
    (7,  ["template", "content", "document", "asset"]),
    (8,  ["schedule", "cron", "job", "batch", "worker", "background",
          "queue", "task"]),
    (9,  ["integration", "connector", "webhook", "gateway", "provider",
          "adapter", "bridge", "sync"]),
    (10, ["report", "analytic", "dashboard", "statistic", "metric",
          "chart", "export"]),
    (11, ["monitor", "alert", "health", "log", "trace", "diagnostic",
          "uptime", "watchdog"]),
    (20, ["benchmark", "performance", "load", "stress", "kpi"]),
    (50, ["sales", "pipeline", "lead", "deal", "opportunity", "funnel"]),
]

_DEFAULT_TIER: int = 30


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _assign_tier(domain_name: str, keywords: List[str]) -> int:
    """Return the lowest matching foundation tier for *domain_name*."""
    domain_text = (domain_name + " " + " ".join(keywords)).lower()
    best = _DEFAULT_TIER
    for tier, triggers in _FOUNDATION_TIERS:
        if any(trig in domain_text for trig in triggers):
            best = min(best, tier)
    return best


def _coupling_score(
    domain_name: str, all_candidates: List[DomainCandidate]
) -> int:
    """Count how many OTHER domains' keyword sets reference *domain_name*.

    Domains that appear in many others' vocabularies are foundational and
    should be built earlier.
    """
    dn_parts = {
        p for p in domain_name.lower().replace("_", " ").split() if len(p) > 3
    }
    count = 0
    for c in all_candidates:
        if c.domain == domain_name:
            continue
        all_kws = " ".join(c.keywords).lower()
        if any(part in all_kws for part in dn_parts):
            count += 1
    return count


# ---------------------------------------------------------------------------
# DomainPrioritizer
# ---------------------------------------------------------------------------


class DomainPrioritizer:
    """Orders domain candidates into an optimal rebuild sequence."""

    def prioritize(
        self,
        candidates: List[DomainCandidate],
    ) -> List[Dict[str, Any]]:
        """Return a priority-ordered list of domain dicts.

        Each entry contains:
        * ``domain``   — snake_case domain name
        * ``priority`` — 1-based integer (1 = build first)
        * ``tier``     — foundation tier used for ordering
        * ``reason``   — human-readable ordering rationale

        The ordering is deterministic: same candidates → same order.
        """
        if not candidates:
            return []

        # Build (tier, -coupling, domain, reason) tuples for sorting
        rows: List[Tuple[int, int, str, str]] = []
        for c in candidates:
            tier     = _assign_tier(c.domain, c.keywords)
            coupling = _coupling_score(c.domain, candidates)
            reason   = self._reason(c, tier, coupling)
            rows.append((tier, -coupling, c.domain, reason))

        # Sort: tier asc, coupling desc (negated), domain asc
        rows.sort(key=lambda x: (x[0], x[1], x[2]))

        return [
            {
                "domain":   domain,
                "priority": i + 1,
                "tier":     tier,
                "reason":   reason,
            }
            for i, (tier, _, domain, reason) in enumerate(rows)
        ]

    @staticmethod
    def _reason(c: DomainCandidate, tier: int, coupling: int) -> str:
        parts = [f"tier {tier} foundation"]
        if coupling > 0:
            parts.append(f"referenced by {coupling} other domain(s)")
        parts.append(
            f"{c.estimated_size} domain across {len(c.sources)} source type(s)"
        )
        return "; ".join(parts)

    def save(self, priority_list: List[Dict[str, Any]], path: str) -> None:
        """Atomically write *priority_list* to *path* as JSON."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(priority_list, fh, indent=2, ensure_ascii=False, sort_keys=False)
        os.replace(tmp, path)

    def load(self, path: str) -> List[Dict[str, Any]]:
        """Load a previously saved priority list.  Returns ``[]`` if absent."""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return data
        except (OSError, json.JSONDecodeError):
            pass
        return []
