"""
common_guard.py — Shared guard utilities for analysis-tool guard scripts.

Provides:
  - load_capability_domain_map()     → dict mapping capability names to domain keys
  - validate_capability_mapping(cap) → bool: capability exists in map
  - validate_domain_exists(domain)   → bool: domain key exists in domain_state.json
  - compute_coverage(domains)        → float: ratio of done domains
  - fail_with_reset(reason)          → prints RESET/ONBOARD required, raises SystemExit(1)

HARD RULES:
  - No silent fallback
  - No best-effort
  - No continuation after failure
  - No implicit defaults
  - No auto-fix
"""

import json
from pathlib import Path

REPO_ROOT         = Path(__file__).resolve().parents[2]
DOMAIN_STATE_FILE = REPO_ROOT / "domains" / "domain_state.json"
DONE_STATUSES     = {"complete", "done", "locked"}

# Capability → domain_state.json key mapping.
# Extend as new capabilities are analyzed and registered.
CAPABILITY_DOMAIN_MAP: dict[str, list[str]] = {
    "manage_customer": ["customer"],
    # message_wizard and message_management are new capability splits;
    # their domain_state.json keys must be registered by Architect.
    # Until registered, these capabilities are valid but domain-scoped gate
    # cannot run — gate must be run in global mode or with registered keys.
}


def load_capability_domain_map() -> dict[str, list[str]]:
    """Return the capability → domain key mapping."""
    return dict(CAPABILITY_DOMAIN_MAP)


def load_domain_state() -> dict:
    """Load and return domain_state.json. Fails hard if missing or invalid."""
    if not DOMAIN_STATE_FILE.exists():
        fail_with_reset(f"domain_state.json not found at {DOMAIN_STATE_FILE}")
    try:
        with DOMAIN_STATE_FILE.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        fail_with_reset(f"domain_state.json is not valid JSON: {exc}")


def validate_capability_mapping(capability: str) -> bool:
    """Return True if capability is registered in CAPABILITY_DOMAIN_MAP."""
    return capability in CAPABILITY_DOMAIN_MAP


def validate_domain_exists(domain: str) -> bool:
    """Return True if domain key exists in domain_state.json."""
    state = load_domain_state()
    entries = {k: v for k, v in state.items() if not k.startswith("_")}
    return domain in entries


def compute_coverage(domains: list[str]) -> float:
    """
    Return ratio of domains (from given list) with status in DONE_STATUSES.
    Fails hard if any domain key is missing from domain_state.json.
    """
    state = load_domain_state()
    entries = {k: v for k, v in state.items() if not k.startswith("_")}
    missing = [d for d in domains if d not in entries]
    if missing:
        fail_with_reset(f"domains not found in domain_state.json: {missing}")
    total = len(domains)
    if total == 0:
        fail_with_reset("compute_coverage called with empty domain list")
    done = sum(1 for d in domains if entries[d].get("status", "").lower() in DONE_STATUSES)
    return done / total


def fail_with_reset(reason: str) -> None:
    """
    Print RESET REQUIRED + ONBOARD REQUIRED, then exit(1).
    This function never returns.
    """
    print("RESET REQUIRED")
    print("ONBOARD REQUIRED")
    print(f"REASON: {reason}")
    raise SystemExit(1)
