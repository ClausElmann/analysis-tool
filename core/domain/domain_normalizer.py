"""Domain normalizer — filters noise domains and suggests merges.

Prevents low-signal, generic domain names (e.g. ``misc``, ``other``,
``job``) from polluting the domain registry.  Also maps common aliases
to their canonical domain names so the engine doesn't split one real
domain into two.

Usage::

    from core.domain.domain_normalizer import is_noise_domain, suggest_merge

    cleaned = []
    for d in discovered_domains:
        if is_noise_domain(d):
            continue
        target = suggest_merge(d)
        if target:
            merge_into(d, target)
            continue
        cleaned.append(d)
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Noise filters — single-word or generic tokens that carry no domain signal
# ---------------------------------------------------------------------------

_NOISE_DOMAINS: frozenset[str] = frozenset(
    {
        "other",
        "misc",
        "start",
        "process",
        "secondary",
        "ready",
        "job",
        "i",
        "common",
        "shared",
        "base",
        "core",
        "util",
        "utils",
        "helper",
        "helpers",
        "general",
        "default",
        "unknown",
        "todo",
        "temp",
        "tmp",
        "test",
        "tests",
    }
)

# ---------------------------------------------------------------------------
# Merge map — alias → canonical domain
# ---------------------------------------------------------------------------

_MERGE_MAP: dict[str, str] = {
    # SMS / messaging aliases
    "sms":              "messaging",
    "sms_send":         "messaging",
    "sms_delivery":     "messaging",
    "message":          "messaging",
    "messages":         "messaging",
    "notification":     "messaging",
    "notifications":    "messaging",
    # Client / frontend aliases
    "client":           "client_events",
    "clients":          "client_events",
    "frontend":         "client_events",
    # Job / scheduling aliases
    "job":              "batch_processing",
    "jobs":             "batch_processing",
    "batch":            "batch_processing",
    "scheduler":        "batch_processing",
    "scheduling":       "batch_processing",
    # Auth aliases
    "auth":             "identity_access",
    "authentication":   "identity_access",
    "authorization":    "identity_access",
    "login":            "identity_access",
    # Address aliases
    "address":          "address_management",
    "addresses":        "address_management",
    # Phone aliases
    "phone":            "phone_numbers",
    "phones":           "phone_numbers",
    "telephone":        "phone_numbers",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_noise_domain(name: str) -> bool:
    """Return *True* when *name* should be dropped entirely.

    Parameters
    ----------
    name:
        Normalised domain name (snake_case).

    Returns
    -------
    bool
        ``True`` — the domain is noise and should be skipped.
        ``False`` — the domain is legitimate.
    """
    return name.lower() in _NOISE_DOMAINS


def suggest_merge(name: str) -> Optional[str]:
    """Return a canonical merge target for *name*, or *None*.

    When a non-``None`` value is returned the caller should merge the
    domain into the returned canonical domain instead of registering it
    as a new domain.

    Parameters
    ----------
    name:
        Normalised domain name (snake_case).

    Returns
    -------
    str or None
        The canonical merge target, or ``None`` if no mapping exists.
    """
    return _MERGE_MAP.get(name.lower())
