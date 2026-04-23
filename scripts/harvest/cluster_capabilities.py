"""
cluster_capabilities.py — Groups flows/requirements into 10-20 high-level capabilities.

Reads:
  harvest/angularharvest/flows.jsonl
  harvest/angularharvest/requirements.jsonl

Output:
  harvest/architect-review/package_002/capabilities.jsonl

This is an ANALYSIS script — runs under N-A mode. No build gate required.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FLOWS_FILE = REPO_ROOT / "harvest" / "angularharvest" / "flows.jsonl"
REQS_FILE  = REPO_ROOT / "harvest" / "angularharvest" / "requirements.jsonl"
OUT_DIR    = REPO_ROOT / "harvest" / "architect-review" / "package_002"
OUT_FILE   = OUT_DIR / "capabilities.jsonl"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_jsonl(path: Path) -> list[dict]:
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# ─── Capability taxonomy (endpoint-keyword → capability name) ─────────────────
# Each rule: list of substrings to match in endpoint (case-insensitive)
TAXONOMY: list[tuple[str, str, str]] = [
    # (capability_key, label, keyword_substrings_as_pipe_sep)
    ("manage_customer",       "Kundehåndtering",           "customer|GetCustomer|UpdateCustomer|CreateCustomer|DeleteCustomer"),
    ("manage_subscription",   "Abonnementhåndtering",       "Subscription|Abonnement|subscription"),
    ("manage_recipients",     "Modtagerhåndtering",         "Recipient|recipient|modtager"),
    ("manage_messages",       "Beskedhåndtering",           "Message|GetDrift|WebMessage|message"),
    ("manage_addresses",      "Adressehåndtering",          "Address|address|GetAddress|lookup"),
    ("manage_profiles",       "Profilhåndtering",           "Profile|profile|GetProfile"),
    ("manage_users",          "Brugerhåndtering",           "User|user|Login|login|Auth|auth"),
    ("manage_map",            "Kortfunktionalitet",         "Map|map|Layer|layer|Shape|shape"),
    ("manage_templates",      "Skabelonhåndtering",         "Template|template|skabelon"),
    ("manage_statistics",     "Statistik & rapportering",   "Statistics|statistic|Report|report|Log|log"),
    ("manage_settings",       "Indstillinger",              "Setting|setting|Config|config|Setup|setup"),
    ("manage_notifications",  "Notifikationer",             "Notification|notification|Alert|alert|Send|send"),
    ("manage_groups",         "Gruppehåndtering",           "Group|group"),
    ("manage_imports",        "Import & batch",             "Import|import|Batch|batch|Upload|upload"),
    ("manage_integrations",   "Integrationer",              "Integration|integration|Webhook|webhook|Callback|callback"),
]


def match_capability(endpoint: str) -> str:
    ep_lower = endpoint.lower()
    for key, _label, keywords in TAXONOMY:
        for kw in keywords.split("|"):
            if kw.lower() in ep_lower:
                return key
    return "other"


def main() -> None:
    flows = load_jsonl(FLOWS_FILE)
    reqs  = load_jsonl(REQS_FILE)

    # Group flows by capability
    cap_flows: dict[str, list[dict]] = defaultdict(list)
    for f in flows:
        ep = f.get("http", "")
        key = match_capability(ep)
        cap_flows[key].append(f)

    # Group requirements by capability
    cap_reqs: dict[str, list[dict]] = defaultdict(list)
    for r in reqs:
        ep = r.get("endpoint", "")
        key = match_capability(ep)
        cap_reqs[key].append(r)

    # Build capability records
    taxonomy_map = {key: label for key, label, _ in TAXONOMY}
    all_keys = sorted(
        set(list(cap_flows.keys()) + list(cap_reqs.keys())),
        key=lambda k: -(len(cap_flows.get(k, [])) + len(cap_reqs.get(k, []))),
    )

    records: list[dict] = []
    for key in all_keys:
        if key == "other":
            continue
        f_list = cap_flows.get(key, [])
        r_list = cap_reqs.get(key, [])
        if not f_list and not r_list:
            continue

        # Deduplicate endpoints
        seen_endpoints: set[str] = set()
        deduped_flows = []
        for f in f_list:
            ep = f.get("http", "")
            if ep not in seen_endpoints:
                seen_endpoints.add(ep)
                deduped_flows.append({"http": ep, "method": f.get("method", ""), "component": f.get("component", "")})

        seen_req: set[str] = set()
        deduped_reqs = []
        for r in r_list:
            ep = r.get("endpoint", "")
            if ep not in seen_req:
                seen_req.add(ep)
                deduped_reqs.append({"endpoint": ep, "method": r.get("method", ""), "type": r.get("type", "")})

        verified = sum(1 for f in f_list if f.get("classification") == "VERIFIED_STRUCTURAL")
        confidence = round(verified / len(f_list), 2) if f_list else 0.0

        records.append({
            "id": str(uuid.uuid4()),
            "name": key,
            "label": taxonomy_map.get(key, key),
            "domain": "UNKNOWN",
            "flows_count": len(deduped_flows),
            "requirements_count": len(deduped_reqs),
            "flows": deduped_flows[:10],  # top 10 per capability
            "requirements": deduped_reqs[:10],
            "confidence": confidence,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Sort: highest confidence + most flows first
    records.sort(key=lambda r: (-r["confidence"], -r["flows_count"]))

    # Write output
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} capabilities to {OUT_FILE}")
    for r in records:
        print(f"  {r['name']:30s}  flows={r['flows_count']:3d}  reqs={r['requirements_count']:3d}  conf={r['confidence']:.2f}")


if __name__ == "__main__":
    main()
