"""
DOMAIN CONSOLIDATION ENGINE
Reads JSONL events → grouped canonical entries → harvest/consolidated/UNKNOWN/
Hard rules: no writes to domains/, no deletion of evidence, no invention.
"""
import json, re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

NORMALIZED_DIR = Path("harvest/angular/normalized")
OUT_DIR = Path("harvest/consolidated/UNKNOWN")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── FILTER RULES ─────────────────────────────────────────────────────────────
TECHNICAL_WORDS = {
    "initialize", "initialise", "load", "component", "display",
    "fetch", "init", "subscribe", "lifecycle", "handler", "observable"
}

def is_llm_valid_behavior(entry):
    """True only if entry is LLM-sourced, verified, confidence >= 0.70,
    and text does not contain technical lifecycle wording."""
    if entry.get("source") != "angular":
        return False
    if entry.get("verified") is False:
        return False
    if entry.get("confidence", 0) < 0.70:
        return False
    text = entry.get("behavior", "").lower()
    for word in TECHNICAL_WORDS:
        if word in text.split():
            return False
    return True

def is_llm_valid_flow(entry):
    """True only if all 4 legs present and source is LLM."""
    if entry.get("source") != "angular":
        return False
    if not entry.get("method"):
        return False
    if not entry.get("service_call"):
        return False
    if not (entry.get("http") or entry.get("api")):
        return False
    if entry.get("confidence", 0) < 0.70:
        return False
    return True

def is_llm_valid_requirement(entry, llm_endpoints):
    """True only if endpoint matches an LLM-verified flow endpoint."""
    if entry.get("source") == "regex":
        # Accept regex requirement ONLY if its endpoint key is confirmed by LLM flow
        ep_norm = normalize_text(entry.get("endpoint", ""))
        return any(normalize_text(e) == ep_norm for e in llm_endpoints)
    return True  # LLM-sourced requirements are kept

def load_jsonl(path):
    lines = []
    if not path.exists():
        return lines
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return lines

def normalize_text(t):
    t = t.strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = t.replace("text message", "sms")
    return t

def canonical_text(entries):
    """Pick the LLM-sourced text if available, else first occurrence."""
    for e in entries:
        if e.get("source") == "angular":
            return e.get("behavior") or e.get("trigger") or e.get("endpoint")
    return entries[0].get("behavior") or entries[0].get("trigger") or entries[0].get("endpoint")

now = datetime.utcnow().isoformat()

# ── BEHAVIORS ────────────────────────────────────────────────────────────────
raw_behaviors = load_jsonl(NORMALIZED_DIR / "behaviors.jsonl")
dropped_behaviors = [b for b in raw_behaviors if not is_llm_valid_behavior(b)]
valid_behaviors = [b for b in raw_behaviors if is_llm_valid_behavior(b)]

# Group by normalized behavior text
b_groups = defaultdict(list)
for b in valid_behaviors:
    key = normalize_text(b.get("behavior", ""))
    b_groups[key].append(b)

behaviors_out = []
for key, group in b_groups.items():
    components = list(dict.fromkeys(e.get("component", "") for e in group))
    sources = list(dict.fromkeys(e.get("source", "regex") for e in group))
    confs = [e.get("confidence", 0.0) for e in group]
    avg_conf = round(sum(confs) / len(confs), 3)
    evidence_refs = []
    for e in group:
        ev = e.get("evidence")
        if ev and ev.get("file"):
            evidence_refs.append({"file": ev["file"], "line": ev.get("line")})
    # deduplicate evidence_refs
    seen = set()
    deduped_refs = []
    for r in evidence_refs:
        k = (r["file"], r.get("line"))
        if k not in seen:
            seen.add(k)
            deduped_refs.append(r)

    entry = {
        "behavior": canonical_text(group),
        "domain": "UNKNOWN",
        "confidence": avg_conf,
        "evidence_count": len(group),
        "components": components,
        "sources": sources,
        "quality": "OK",
        "verified": True,
        "evidence_refs": deduped_refs,
        "consolidated_at": now
    }
    behaviors_out.append(entry)

# Sort by confidence desc (all are OK quality now)
behaviors_out.sort(key=lambda x: -x["confidence"])

# ── FLOWS ────────────────────────────────────────────────────────────────────
raw_flows = load_jsonl(NORMALIZED_DIR / "flows.jsonl")
dropped_flows = [f for f in raw_flows if not is_llm_valid_flow(f)]
valid_flows = [f for f in raw_flows if is_llm_valid_flow(f)]

# Group by (normalized trigger, http endpoint)
def flow_key(f):
    trigger = normalize_text(f.get("trigger", ""))
    http = normalize_text(f.get("http", f.get("api", "")))
    return (trigger, http)

f_groups = defaultdict(list)
for f in valid_flows:
    k = flow_key(f)
    f_groups[k].append(f)

flows_out = []
for (trigger_norm, http_norm), group in f_groups.items():
    components = list(dict.fromkeys(e.get("component", "") for e in group))
    sources = list(dict.fromkeys(e.get("source", "regex") for e in group))
    confs = [e.get("confidence", 0.0) for e in group if e.get("confidence")]
    avg_conf = round(sum(confs) / len(confs), 3) if confs else 0.0

    # Pick canonical values from LLM source if possible
    canonical = next((e for e in group if e.get("source") == "angular"), group[0])
    evidence_refs = []
    for e in group:
        ev = e.get("evidence")
        if ev and ev.get("file"):
            evidence_refs.append({"file": ev["file"], "line": ev.get("line")})

    quality = "OK"
    entry = {
        "trigger": canonical.get("trigger", ""),
        "method": canonical.get("method", ""),
        "service_call": canonical.get("service_call", ""),
        "http": canonical.get("http", ""),
        "result": canonical.get("result", ""),
        "domain": "UNKNOWN",
        "confidence": avg_conf,
        "evidence_count": len(group),
        "components": components,
        "sources": sources,
        "quality": quality,
        "evidence_refs": evidence_refs,
        "consolidated_at": now
    }
    flows_out.append(entry)

flows_out.sort(key=lambda x: -x["confidence"])

# Collect LLM-confirmed endpoints for requirement cross-validation
llm_endpoints = set()
for f in valid_flows:
    ep = f.get("http", "")
    if ep:
        llm_endpoints.add(ep)

# ── REQUIREMENTS ─────────────────────────────────────────────────────────────
raw_reqs = load_jsonl(NORMALIZED_DIR / "requirements.jsonl")
dropped_reqs = [r for r in raw_reqs if not is_llm_valid_requirement(r, llm_endpoints)]
valid_reqs = [r for r in raw_reqs if is_llm_valid_requirement(r, llm_endpoints)]

# Normalise endpoint keys for grouping
def req_key(r):
    ep = r.get("endpoint", "")
    # Strip ApiRoutes wrapper for matching
    ep = re.sub(r"^\{?ApiRoutes\.\w+Routes\.\w+\.(\w+)\}?$",
                lambda m: m.group(1).lower(), ep)
    ep = normalize_text(ep)
    m = (r.get("method", "") or "").upper()
    return (m, ep)

r_groups = defaultdict(list)
for r in valid_reqs:
    k = req_key(r)
    r_groups[k].append(r)

# Also group regex vs LLM for same semantic endpoint
reqs_out = []
for (method, ep_key), group in r_groups.items():
    components = list(dict.fromkeys(e.get("component", "") for e in group))
    sources = list(dict.fromkeys(e.get("source", "regex") for e in group))
    # Prefer LLM endpoint string; fall back to regex
    canonical_ep = next(
        (e.get("endpoint") for e in group if e.get("source") == "angular"),
        group[0].get("endpoint")
    )
    types = list(dict.fromkeys(e.get("type", "") for e in group))
    evidence_refs = []
    for e in group:
        ev = e.get("evidence")
        if ev and ev.get("file"):
            evidence_refs.append({"file": ev["file"], "line": ev.get("line")})

    entry = {
        "method": method,
        "endpoint": canonical_ep,
        "type": types[0] if types else "UNKNOWN",
        "domain": "UNKNOWN",
        "evidence_count": len(group),
        "components": components,
        "sources": sources,
        "evidence_refs": evidence_refs,
        "consolidated_at": now
    }
    reqs_out.append(entry)

reqs_out.sort(key=lambda x: x.get("method", "") + x.get("endpoint", ""))

# ── CONFLICTS ────────────────────────────────────────────────────────────────
conflicts_out = []

# CONFLICT: same method in same component maps to different HTTP endpoints in LLM flows
method_to_apis = defaultdict(list)
for f in valid_flows:
    method = f.get("method", "")
    api = f.get("http", "")
    comp = f.get("component", "")
    if method:
        method_to_apis[(comp, method)].append(api)

for (comp, method), apis in method_to_apis.items():
    unique_apis = list(dict.fromkeys(normalize_text(a) for a in apis))
    if len(unique_apis) > 1:
        conflicts_out.append({
            "type": "FLOW_CONFLICT",
            "component": comp,
            "method": method,
            "description": f"Method '{method}' maps to different HTTP endpoints",
            "endpoints": list(dict.fromkeys(apis)),
            "resolution": "UNRESOLVED — Architect review required",
            "detected_at": now
        })

# ── WRITE OUTPUT ──────────────────────────────────────────────────────────────
def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written: {path} ({len(data)} entries)")

write_json(OUT_DIR / "behaviors.json", behaviors_out)
write_json(OUT_DIR / "flows.json", flows_out)
write_json(OUT_DIR / "requirements.json", reqs_out)
write_json(OUT_DIR / "conflicts.json", conflicts_out)

total_dropped = len(dropped_behaviors) + len(dropped_flows) + len(dropped_reqs)
print("\nConsolidation complete (LLM-only filter applied).")
print(f"  behaviors:    {len(behaviors_out)} kept | {len(dropped_behaviors)} dropped")
print(f"  flows:        {len(flows_out)} kept | {len(dropped_flows)} dropped")
print(f"  requirements: {len(reqs_out)} kept | {len(dropped_reqs)} dropped")
print(f"  conflicts:    {len(conflicts_out)} detected")
print(f"  TOTAL DROPPED: {total_dropped}")
