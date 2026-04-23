"""
Layer 2 — Capability Clustering
Læser behaviors/flows/requirements fra corpus og grupperer til capabilities.
Kører lokalt — ingen LLM, ingen ekstern API.

Output: corpus/capabilities.jsonl
Format: {id, capability, capability_label, domain, behaviors[], components[], flows[], requirements[], created_at}

Usage:
    python scripts/layer2/build_capabilities.py [--corpus-dir DIR] [--output FILE]
"""

from __future__ import annotations

# ─── BUILD GATE (non-bypassable) ────────────────────────────────────────────
import subprocess as _sp, sys as _sys, pathlib as _pl
_guard = _pl.Path(__file__).resolve().parents[2] / "scripts" / "guard" / "check_build_gate.py"
if _sp.run([_sys.executable, str(_guard)], check=False).returncode != 0:
    print("BUILD BLOCKED — guard returned BLOCK. See harvest/architect-review/build_state.json")
    _sys.exit(1)
# ─────────────────────────────────────────────────────────────────────────────

import argparse
import json
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--corpus-dir", default=r".\corpus")
parser.add_argument("--output",     default=r".\corpus\capabilities.jsonl")
args = parser.parse_args()

CORPUS_DIR = Path(args.corpus_dir)
OUTPUT     = Path(args.output)

# ─────────────────────────────────────────────────────────────
# Capability keyword map
# Hvert entry: (keyword_list, capability_id, dansk_label)
# Matcher mod lowercase behavior tekst
# ─────────────────────────────────────────────────────────────
_CAP_RULES: list[tuple[list[str], str, str]] = [
    # Broadcasting / Messaging
    (["sende", "afsende", "udsende", "afsend", "send"], "dispatch_message", "Afsende beskeder"),
    (["planlæg", "planlægge", "forsink", "fremtidig", "planlagt udsendelse", "udskyd"], "schedule_message", "Planlægge udsendelse"),
    (["skabelon", "template", "flettefelt", "mergefelt", "fletfelt"], "message_template", "Beskedskabeloner og flettefelter"),
    (["bekræft", "bekræfte", "confirmation", "dialog vises inden"], "confirm_action", "Bekræftelsesflow"),

    # Subscription
    (["tilmeld", "abonnement", "subscribe", "tilmelding", "enrollment"], "subscribe", "Abonnementstilmelding"),
    (["afmeld", "unsubscribe", "fjerne en afsender", "afmelde"], "unsubscribe", "Afmelding fra abonnement"),
    (["vælge afsendere", "vælg afsendere", "ekstra afsendere", "additional sender"], "select_senders", "Vælge afsendere til abonnement"),
    (["vilkår", "betingelser", "terms", "privatlivspolitik", "privacy"], "accept_terms", "Vilkår og privatlivspolitik"),
    (["mobilnummer", "pin-kode", "pin kode", "verifikationskode", "validere sin kode"], "verify_mobile", "Verificere mobilnummer og PIN"),

    # Address
    (["adresse", "adresseoplysninger", "adresseformular", "postnummer", "gadenavn"], "manage_address", "Adressehåndtering"),
    (["importere", "importér", "import adress", "critical addresses", "kritiske adresser"], "import_addresses", "Importere adresser"),
    (["kort", "map", "polygon", "markør", "kortvisning", "driftsmeldinger.*kort", "alarmer.*kort"], "map_view", "Kortvisning"),

    # Navigation
    (["navigere", "navigerer", "navigation", "gå til", "gå videre", "gå tilbage", "næste trin", "tilbage"], "navigate", "Navigation"),
    (["menu", "tiles", "modul"], "navigation_menu", "Navigationsmenuen"),

    # Search / Filter
    (["søge", "søger", "søgning", "søg i", "filtrere", "filtrer", "filter"], "search_filter", "Søgning og filtrering"),

    # CRUD — employees
    (["medarbejder", "medarbejderdata", "medarbejderoplysninger"], "manage_employees", "Medarbejderadministration"),

    # CRUD — receivers / std-receivers
    (["modtager", "modtageroplysninger", "telefonnumre til modtager", "ekstra telefonnumre"], "manage_receivers", "Modtagere og telefonnumre"),

    # Benchmark
    (["benchmark", "kpi", "statistik", "kvhx", "causes", "årsag"], "benchmark_management", "Benchmark og statistik"),

    # Scheduled broadcasts
    (["planlagt udsendelse", "annullere", "annuller", "genaktiver", "omplanlæg", "nulstille.*udsendelse"], "manage_scheduled_broadcasts", "Planlagte udsendelser"),

    # Driftstatus (iframe-modules)
    (["driftsstatus", "driftsmelding", "driftsmeld", "aktiv.*inaktiv", "arkiverede"], "driftstatus", "Driftsstatusvisning"),

    # Group subscription
    (["gruppeabonnement", "gruppevalg", "gruppe.*abonnement"], "group_subscription", "Gruppeabonnement"),

    # Quick response
    (["hurtigt svar", "quick response", "besked der skal besvares"], "quick_response", "Hurtigt svar på besked"),

    # Access / Auth
    (["logge ind", "log ind", "login", "log ud", "logout"], "authentication", "Login og logout"),
    (["rettigheder", "rolleadgang", "rolle", "adgang", "profilkategori"], "access_control", "Adgangskontrol"),

    # Misc display
    (["nyhedsbrev", "newsletter"], "newsletter", "Nyhedsbrev"),
    (["rapport", "historik", "afsendeklare"], "message_report", "Beskedrapporter"),
    (["geojson", "geografisk datafil", "geodata"], "geo_import", "Geografisk dataimport"),
]


def classify_behavior(text: str) -> str | None:
    """Return capability_id for a behavior text, or None if no match."""
    t = text.lower()
    for keywords, cap_id, _ in _CAP_RULES:
        for kw in keywords:
            if re.search(kw, t):
                return cap_id
    return None


def cap_label(cap_id: str) -> str:
    for _, cid, label in _CAP_RULES:
        if cid == cap_id:
            return label
    return cap_id


# ─────────────────────────────────────────────────────────────
# Load corpus
# ─────────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


behaviors    = load_jsonl(CORPUS_DIR / "behaviors.jsonl")
flows        = load_jsonl(CORPUS_DIR / "flows.jsonl")
requirements = load_jsonl(CORPUS_DIR / "requirements.jsonl")

# Only angular source behaviors for clustering
angular_behaviors = [b for b in behaviors if b.get("source") == "angular"]

print(f"Input: {len(angular_behaviors)} angular behaviors, {len(flows)} flows, {len(requirements)} requirements")

# ─────────────────────────────────────────────────────────────
# Cluster behaviors → capabilities
# ─────────────────────────────────────────────────────────────

# Structure: {(domain, capability_id): {behaviors, components}}
clusters: dict[tuple[str, str], dict] = defaultdict(lambda: {
    "behaviors": [],
    "components": set(),
    "behavior_texts": [],
})

unmatched = []

for b in angular_behaviors:
    text    = b.get("behavior", "")
    domain  = b.get("domain", "UNKNOWN")
    comp    = b.get("component", "")
    cap_id  = classify_behavior(text)

    if cap_id is None:
        unmatched.append(text)
        # Fallback: put in "misc" capability for domain
        cap_id = "misc"

    key = (domain, cap_id)
    clusters[key]["behaviors"].append(b)
    clusters[key]["behavior_texts"].append(text)
    if comp:
        clusters[key]["components"].add(comp)


# ─────────────────────────────────────────────────────────────
# Attach flows and requirements to capabilities
# ─────────────────────────────────────────────────────────────

# Index flows/requirements by component
flows_by_comp: dict[str, list[dict]] = defaultdict(list)
for f in flows:
    c = f.get("component", "")
    if c:
        flows_by_comp[c].append(f)

reqs_by_comp: dict[str, list[dict]] = defaultdict(list)
for r in requirements:
    c = r.get("component", "")
    if c:
        reqs_by_comp[c].append(r)


# ─────────────────────────────────────────────────────────────
# Build output
# ─────────────────────────────────────────────────────────────

now = datetime.now(timezone.utc).isoformat()
output_entries = []

for (domain, cap_id), data in sorted(clusters.items(), key=lambda x: (x[0][0], x[0][1])):
    # Skip misc — unmatched behaviors are reported but not written as capabilities
    if cap_id == "misc":
        continue
    comps = sorted(data["components"])

    # Collect unique flows/requirements for this capability's components
    cap_flows: list[dict] = []
    cap_reqs:  list[dict] = []
    seen_f: set[str] = set()
    seen_r: set[str] = set()

    for comp in comps:
        for f in flows_by_comp.get(comp, []):
            key_f = f.get("trigger", "") + f.get("http", "")
            if key_f not in seen_f:
                seen_f.add(key_f)
                cap_flows.append({"trigger": f.get("trigger"), "http": f.get("http"), "component": comp})
        for r in reqs_by_comp.get(comp, []):
            key_r = r.get("method", "") + r.get("endpoint", "")
            if key_r not in seen_r:
                seen_r.add(key_r)
                cap_reqs.append({"method": r.get("method"), "endpoint": r.get("endpoint"), "component": comp})

    # Deduplicate behavior texts
    seen_texts: set[str] = set()
    unique_behaviors = []
    for b in data["behaviors"]:
        t = b.get("behavior", "")
        if t not in seen_texts:
            seen_texts.add(t)
            unique_behaviors.append(t)

    entry = {
        "capability":              cap_id,
        "capability_label":        cap_label(cap_id),
        "domain":                  domain,
        "behaviors":               unique_behaviors,
        "components":              comps,
        "candidate_flows":         cap_flows,
        "candidate_requirements":  cap_reqs,
        "behavior_count":          len(unique_behaviors),
        "evidence_count":          len(data["behaviors"]),
        "source_components_count": len(comps),
        "confidence":              round(min(1.0, len(unique_behaviors) / max(3, len(unique_behaviors))), 2),
        "created_at":              now,
    }
    output_entries.append(entry)


# ─────────────────────────────────────────────────────────────
# Write output
# ─────────────────────────────────────────────────────────────

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
lines = "\n".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in output_entries)
OUTPUT.write_bytes(lines.encode("utf-8"))

print(f"\nOutput: {len(output_entries)} capabilities -> {OUTPUT}")
print(f"Unmatched behaviors (misc, excluded): {len(unmatched)}")

# Print summary table
print("\n=== CAPABILITY SUMMARY ===")
print(f"{'Domain':<25} {'Capability':<35} {'#B':>3} {'#F':>3} {'#R':>3} {'Conf':>5}  Components")
print("-" * 110)
for e in sorted(output_entries, key=lambda x: (x["domain"], x["capability"])):
    comps_short = ", ".join(e["components"][:3])
    if len(e["components"]) > 3:
        comps_short += f" +{len(e['components'])-3}"
    print(f"{e['domain']:<25} {e['capability']:<35} {e['behavior_count']:>3} {len(e['candidate_flows']):>3} {len(e['candidate_requirements']):>3} {e['confidence']:>5.2f}  {comps_short}")

if unmatched:
    print(f"\n--- {len(unmatched)} unmatched behaviors (NOT written) ---")
    for u in sorted(set(unmatched))[:20]:
        print(f"  {u}")
    if len(unmatched) > 20:
        print(f"  ... +{len(unmatched)-20} mere")
