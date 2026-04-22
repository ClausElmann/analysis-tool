"""Diagnostic Layer 2 — cluster behaviors per domain, classify health, write to temp.md."""
import json, re
from pathlib import Path
from collections import defaultdict, Counter

REPO = Path(__file__).parent.parent.parent
CORPUS = REPO / "corpus"
TEMP_MD = REPO / "temp.md"

def load(p):
    p = CORPUS / p
    if not p.exists(): return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

behaviors = load("behaviors.jsonl")
flows     = load("flows.jsonl")
reqs      = load("requirements.jsonl")

# Index flows/reqs by component
flows_by_comp = defaultdict(list)
for f in flows:
    flows_by_comp[f.get("component","")].append(f)

reqs_by_comp = defaultdict(list)
for r in reqs:
    reqs_by_comp[r.get("component","")].append(r)

# ── Simple heuristic clustering ──────────────────────────────────────────────
# Extract 2-3 word "concept" from behavior text for grouping
def _concept(text):
    """Extract first meaningful verb+noun pair from 'Brugeren kan ...' text."""
    t = text.lower()
    # Strip prefix
    t = re.sub(r"^brugeren kan\s*", "", t)
    t = re.sub(r"^viser?\s+", "vise ", t)
    words = t.split()
    # Take first 2 words as concept key
    return " ".join(words[:2]) if len(words) >= 2 else (words[0] if words else "?")

# Group by (domain, concept)
clusters = defaultdict(lambda: {"behaviors": [], "components": set()})
unknown_behaviors = []

for b in behaviors:
    domain = b.get("domain") or "UNKNOWN"
    if domain in ("", "?", "UNKNOWN", None):
        unknown_behaviors.append(b)
        domain = "UNKNOWN"
    concept = _concept(b.get("behavior", ""))
    key = (domain, concept)
    clusters[key]["behaviors"].append(b.get("behavior",""))
    clusters[key]["components"].add(b.get("component",""))

# ── Build capability candidates per domain ───────────────────────────────────
domain_caps = defaultdict(list)

for (domain, concept), data in sorted(clusters.items()):
    comps = sorted(data["components"])
    # Count flows/reqs for these components
    f_count = sum(len(flows_by_comp[c]) for c in comps)
    r_count = sum(len(reqs_by_comp[c]) for c in comps)
    b_count = len(data["behaviors"])

    # Health classification
    if b_count >= 3 and (f_count > 0 or r_count > 0):
        health = "STRONG"
    elif b_count >= 3:
        health = "UI_ONLY"
    elif b_count <= 2 and (f_count > 0 or r_count > 0):
        health = "WEAK_SIGNAL_WITH_DATA"
    else:
        health = "WEAK_SIGNAL"

    domain_caps[domain].append({
        "concept":     concept,
        "health":      health,
        "b_count":     b_count,
        "f_count":     f_count,
        "r_count":     r_count,
        "components":  comps,
        "behaviors":   data["behaviors"],
    })

# ── Build report ─────────────────────────────────────────────────────────────
lines = [
    "# DIAGNOSTIC LAYER 2 — Corpus health analyse",
    "",
    "## Corpus input",
    f"- behaviors: {len(behaviors)}",
    f"- flows:     {len(flows)}",
    f"- requirements: {len(reqs)}",
    "",
]

# Domain distribution
dc = Counter(b.get("domain","?") for b in behaviors)
lines.append("## Domain distribution (behaviors)")
for d, c in sorted(dc.items(), key=lambda x: -x[1]):
    lines.append(f"- {d}: {c}")
lines.append("")

# Per-domain capability candidates
all_weak = []
all_ui_only = []
all_strong = []

for domain in sorted(domain_caps.keys()):
    caps = domain_caps[domain]
    lines.append(f"## Domain: {domain} ({len(caps)} capability candidates)")
    lines.append("")
    lines.append(f"{'Concept':<35} {'Health':<25} {'#B':>3} {'#F':>3} {'#R':>3}  Components")
    lines.append("-" * 90)
    for cap in sorted(caps, key=lambda x: (-x['b_count'], x['concept'])):
        comps_str = ", ".join(cap['components'][:3])
        if len(cap['components']) > 3:
            comps_str += f" +{len(cap['components'])-3}"
        lines.append(f"{cap['concept']:<35} {cap['health']:<25} {cap['b_count']:>3} {cap['f_count']:>3} {cap['r_count']:>3}  {comps_str}")
        if cap['health'] in ("WEAK_SIGNAL", "WEAK_SIGNAL_WITH_DATA"):
            all_weak.append((domain, cap))
        elif cap['health'] == "UI_ONLY":
            all_ui_only.append((domain, cap))
        elif cap['health'] == "STRONG":
            all_strong.append((domain, cap))
    lines.append("")

# Summary lists
lines.append("## STRONG capabilities")
if all_strong:
    for domain, cap in all_strong:
        lines.append(f"- [{domain}] {cap['concept']} (B={cap['b_count']}, F={cap['f_count']}, R={cap['r_count']})")
else:
    lines.append("- (ingen endnu)")
lines.append("")

lines.append("## UI_ONLY (behaviors men ingen flows/requirements)")
if all_ui_only:
    for domain, cap in all_ui_only:
        lines.append(f"- [{domain}] {cap['concept']} (B={cap['b_count']}, komponenter: {', '.join(cap['components'])})")
else:
    lines.append("- (ingen)")
lines.append("")

lines.append("## WEAK_SIGNAL (1-2 behaviors)")
if all_weak:
    for domain, cap in all_weak:
        lines.append(f"- [{domain}] {cap['concept']} (B={cap['b_count']}, F={cap['f_count']}, R={cap['r_count']})")
else:
    lines.append("- (ingen)")
lines.append("")

lines.append("## UNKNOWN domain behaviors")
if unknown_behaviors:
    for b in unknown_behaviors:
        lines.append(f"- {b.get('behavior','?')} / {b.get('component','?')}")
else:
    lines.append("- (ingen)")
lines.append("")

lines.append("## Diagnose-konklusion")
total_caps = sum(len(v) for v in domain_caps.values())
strong_pct = round(100 * len(all_strong) / max(1, total_caps))
lines += [
    f"- Total capability candidates: {total_caps}",
    f"- STRONG: {len(all_strong)} ({strong_pct}%)",
    f"- UI_ONLY: {len(all_ui_only)}",
    f"- WEAK_SIGNAL: {len(all_weak)}",
    f"- UNKNOWN: {len(unknown_behaviors)} behaviors",
    "",
    "DIAGNOSTIC_DONE",
]

content = "\n".join(lines) + "\n"
TEMP_MD.write_bytes(content.encode("utf-8"))
print(f"temp.md skrevet — {total_caps} candidates, {len(all_strong)} STRONG, {len(all_ui_only)} UI_ONLY, {len(all_weak)} WEAK")
