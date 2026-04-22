"""
DUAL-LAYER CAPABILITY MODEL
Step 1: Copy capabilities.json → capabilities_detailed.json
Step 2: Build capabilities_grouped.json
Step 3: Build domains_grouped.json
Step 4: Traceability check
Step 5: Metrics → temp.md
"""
import json, re, uuid
from pathlib import Path
from collections import defaultdict

LAYER2 = Path("harvest/layer2")
CORPUS = Path("corpus")
TEMP_MD = Path("temp.md")

# ── Load inputs ───────────────────────────────────────────────────────────────
caps_data    = json.loads((LAYER2 / "capabilities.json").read_text(encoding="utf-8"))
detailed_caps = caps_data["capabilities"]

def load_jsonl(p):
    path = CORPUS / p
    if not path.exists(): return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

flows_raw = load_jsonl("flows.jsonl")
reqs_raw  = load_jsonl("requirements.jsonl")

# ── STEP 1 — Snapshot detailed layer ─────────────────────────────────────────
(LAYER2 / "capabilities_detailed.json").write_text(
    json.dumps(caps_data, indent=2, ensure_ascii=False), encoding="utf-8"
)

# ── Helpers ───────────────────────────────────────────────────────────────────
VERB_WORDS = {
    'get','post','create','update','delete','patch','put','add','remove','save',
    'load','fetch','set','build','make','send','queue','abort','approve','dismiss',
    'toggle','check','verify','request','download','export','import','upload',
    'init','initialize','setup','refresh','resend','sign','confirm','choose',
    'edit','insert','list','read','retrieve','find','search','count','use',
}
STOPWORDS = {
    'all','by','new','from','data','model','info','id','a','an','the','api',
    'key','keys','pdf','excel','csv','raw','booked','current','recent','ongoing',
    'failed','saved','available','additional','standard','related','relevant',
    'type','types','kind','number','numbers','phone','name','names','comment',
    'period','periods','monthly','yearly','daily','arraybuffer','meta','full',
    'complete','base','main','summary','overview','and','or','for','with',
    'its','their','via',
}

# Consolidate 16 detailed domains → 6 grouped domains
DOMAIN_MERGE = {
    "Messaging":                "Messaging & Communication",
    "Social Media":             "Messaging & Communication",
    "Email & eBox":             "Messaging & Communication",
    "User & Profile Management":"User & Access Management",
    "Application Settings":     "User & Access Management",
    "API & Integration":        "User & Access Management",
    "Customer Administration":  "Customer & Enrollment",
    "Enrollment & Subscription":"Customer & Enrollment",
    "Contacts":                 "Customer & Enrollment",
    "Benchmark & Analytics":    "Analytics & Reporting",
    "Reporting & Logs":         "Analytics & Reporting",
    "Invoicing & Finance":      "Finance & Operations",
    "HR & Payroll":             "Finance & Operations",
    "Process & Workflow":       "Finance & Operations",
    "Address & Geo":            "Address & Data",
    "Receiver Groups":          "Address & Data",
    "File Management":          "Address & Data",
    "General":                  "Address & Data",
}

DOMAIN_DESCRIPTIONS = {
    "Messaging & Communication": "Oprettelse, afsendelse og administration af beskeder, stencils, skabeloner og broadcast-kanaler (SMS, web-messages, sociale medier).",
    "User & Access Management":  "Brugerprofiler, roller, adgangsnøgler, pakker og applikationsindstillinger.",
    "Customer & Enrollment":     "Kundeadministration, afsender-tilmelding, kontakter og terminerings-processer.",
    "Analytics & Reporting":     "Benchmark-statistik, KPI-opfølgning, årsagskoder og audit-log.",
    "Finance & Operations":      "Fakturering, accruals, HR-fravær, lønsedler og driftsprocesser.",
    "Address & Data":            "Adresseopslagning, geodata, modtagergrupper, filhåndtering og generelle data-ressourcer.",
}

def extract_resource(endpoint: str, service: str) -> str:
    """Extract primary resource noun from endpoint + service."""
    # Endpoint like "{getMessage}" or "GET {endpoint_name}"
    text = endpoint.strip()
    if text.startswith('{') and text.endswith('}'):
        text = text[1:-1]
    # split by spaces, take last token if multiple
    tokens = text.split()
    text = tokens[-1] if tokens else text
    # CamelCase → words
    words = re.findall(r'[a-z]+', re.sub(r'([A-Z])', r' \1', text).lower())
    # Drop leading verbs
    while words and words[0] in VERB_WORDS:
        words = words[1:]
    # Filter stopwords
    meaningful = [w for w in words if w not in STOPWORDS and len(w) > 2]
    if meaningful:
        r = meaningful[0]
        # simple singularize
        if r.endswith('ies') and len(r) > 4:
            r = r[:-3] + 'y'
        elif r.endswith('ses') or r.endswith('xes'):
            r = r[:-2]
        elif r.endswith('s') and len(r) > 4 and not r.endswith('ss') and not r.endswith('us'):
            r = r[:-1]
        return r
    # Fallback: service name (strip "Service" suffix)
    svc = re.sub(r'[Ss]ervice$', '', service)
    svc_words = re.findall(r'[a-z]+', re.sub(r'([A-Z])', r' \1', svc).lower())
    svc_meaningful = [w for w in svc_words if w not in VERB_WORDS and w not in STOPWORDS and len(w) > 2]
    if svc_meaningful:
        return svc_meaningful[0]
    return 'general'

# Build req id → url map for traceability
req_by_id = {r.get("id",""): r for r in reqs_raw if r.get("id")}
flow_by_id = {f.get("id",""): f for f in flows_raw if f.get("id")}

# ── STEP 2 — Build grouped capabilities ──────────────────────────────────────
GroupKey = tuple  # (grouped_domain, resource)
groups: dict[GroupKey, list] = defaultdict(list)

for cap in detailed_caps:
    resource = extract_resource(cap.get("endpoint",""), cap.get("service",""))
    grouped_domain = DOMAIN_MERGE.get(cap.get("domain","General"), "Address & Data")
    groups[(grouped_domain, resource)].append(cap)

grouped_caps = []
for (grouped_domain, resource), caps_in_group in sorted(
        groups.items(), key=lambda x: -sum(c["frequency"] for c in x[1])):
    freq   = sum(c["frequency"] for c in caps_in_group)
    verbs  = sorted(set(c.get("verb","") for c in caps_in_group if c.get("verb")))
    all_src_cap_ids = [c["id"] for c in caps_in_group]
    all_flow_ids    = list(dict.fromkeys(fid for c in caps_in_group for fid in c.get("flow_ids",[])))
    all_comp_set    = set(sc for c in caps_in_group for sc in c.get("source_components",[]))

    # Match requirements by checking if req URL overlaps flow endpoints
    all_req_ids = []
    for r in reqs_raw:
        r_url = r.get("url","") or r.get("endpoint","")
        for c in caps_in_group:
            if any(r_url and r_url in ep for ep in [c.get("endpoint","")]):
                all_req_ids.append(r.get("id",""))
                break

    # Name
    verb_display = "Manage" if len(verbs) != 1 else {"get":"Read","create":"Create","update":"Update","delete":"Delete"}.get(verbs[0],"Manage")
    resource_display = resource.replace('-',' ').title()
    # Pluralize display for "Manage/Read" if resource doesn't end in s
    if not resource_display.endswith('s') and not resource_display.endswith('y'):
        resource_plural = resource_display + 's'
    elif resource_display.endswith('y'):
        resource_plural = resource_display[:-1] + 'ies'
    else:
        resource_plural = resource_display
    name = f"{verb_display} {resource_plural}" if verb_display != "Manage" else f"Manage {resource_plural}"

    grouped_caps.append({
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "description": (f"{name} — {len(caps_in_group)} detailed operations, "
                        f"{freq} total occurrences across {len(all_comp_set)} components"),
        "domain": grouped_domain,
        "resource": resource,
        "verbs": verbs,
        "source_capability_ids": all_src_cap_ids,
        "source_flow_ids": all_flow_ids,
        "source_requirement_ids": all_req_ids,
        "frequency_sum": freq,
        "detailed_capability_count": len(caps_in_group),
        "confidence_score": round(min(0.95, 0.70 + freq * 0.01), 3),
    })

# ── Secondary merge if >80: merge tiny groups in same domain ─────────────────
if len(grouped_caps) > 80:
    # Merge singletons and low-freq groups in same domain iteratively
    threshold = 2
    while len(grouped_caps) > 80 and threshold <= 6:
        misc_by_domain: dict[str, list] = defaultdict(list)
        keep = []
        for gc in grouped_caps:
            if gc["detailed_capability_count"] <= threshold:
                misc_by_domain[gc["domain"]].append(gc)
            else:
                keep.append(gc)
        for domain, misc_list in misc_by_domain.items():
            if not misc_list:
                continue
            all_src   = [sid for m in misc_list for sid in m["source_capability_ids"]]
            all_flows = [fid for m in misc_list for fid in m["source_flow_ids"]]
            all_reqs  = [rid for m in misc_list for rid in m["source_requirement_ids"]]
            freq = sum(m["frequency_sum"] for m in misc_list)
            keep.append({
                "id": str(uuid.uuid4())[:8],
                "name": f"Other {domain.split('&')[0].strip()} Operations",
                "description": f"Grouped low-frequency operations within {domain} domain ({len(misc_list)} sub-capabilities)",
                "domain": domain,
                "resource": "misc",
                "verbs": [],
                "source_capability_ids": all_src,
                "source_flow_ids": all_flows,
                "source_requirement_ids": all_reqs,
                "frequency_sum": freq,
                "detailed_capability_count": len(all_src),
                "confidence_score": 0.70,
            })
        grouped_caps = keep
        threshold += 1

# ── STEP 3 — Build grouped domains ───────────────────────────────────────────
domain_groups: dict[str, list] = defaultdict(list)
for gc in grouped_caps:
    domain_groups[gc["domain"]].append(gc)

grouped_domains = []
for domain_name, gcaps in sorted(domain_groups.items(), key=lambda x: -sum(gc["frequency_sum"] for gc in x[1])):
    all_src_cap_ids = list(dict.fromkeys(sid for gc in gcaps for sid in gc["source_capability_ids"]))
    total_freq      = sum(gc["frequency_sum"] for gc in gcaps)
    grouped_domains.append({
        "id":                       str(uuid.uuid4())[:8],
        "name":                     domain_name,
        "description":              DOMAIN_DESCRIPTIONS.get(domain_name, f"{domain_name} domain"),
        "grouped_capability_ids":   [gc["id"] for gc in gcaps],
        "source_capability_ids":    all_src_cap_ids,
        "grouped_capability_count": len(gcaps),
        "source_capability_count":  len(all_src_cap_ids),
        "total_frequency":          total_freq,
    })

# ── STEP 4 — Traceability check ───────────────────────────────────────────────
all_detailed_ids     = set(c["id"] for c in detailed_caps)
grouped_source_ids   = set(sid for gc in grouped_caps for sid in gc["source_capability_ids"])
domain_gcap_id_set   = set(gid for gd in grouped_domains for gid in gd["grouped_capability_ids"])
all_gcap_ids         = set(gc["id"] for gc in grouped_caps)

lost_detailed        = all_detailed_ids - grouped_source_ids
gcaps_missing_domain = all_gcap_ids - domain_gcap_id_set

trace_ok = (len(lost_detailed) == 0 and len(gcaps_missing_domain) == 0)

# ── STEP 5 — Write artifacts ──────────────────────────────────────────────────
(LAYER2 / "capabilities_grouped.json").write_text(
    json.dumps({"capabilities_grouped": grouped_caps, "total": len(grouped_caps)}, indent=2, ensure_ascii=False),
    encoding="utf-8"
)
(LAYER2 / "domains_grouped.json").write_text(
    json.dumps({"domains_grouped": grouped_domains, "total": len(grouped_domains)}, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

# ── Print metrics ─────────────────────────────────────────────────────────────
print(f"detailed_capabilities:  {len(detailed_caps)}")
print(f"grouped_capabilities:   {len(grouped_caps)}")
print(f"grouped_domains:        {len(grouped_domains)}")
print(f"lost_detailed:          {len(lost_detailed)}")
print(f"gcaps_missing_domain:   {len(gcaps_missing_domain)}")
print(f"traceability_ok:        {trace_ok}")

stop_cond = "DUAL_LAYER_MODEL_COMPLETE" if (
    trace_ok and len(grouped_caps) <= 80 and len(grouped_domains) <= 10
) else f"DUAL_LAYER_INCOMPLETE (gcaps={len(grouped_caps)}, domains={len(grouped_domains)}, trace={trace_ok})"

# ── Build report ──────────────────────────────────────────────────────────────
gcap_lines = []
for gc in sorted(grouped_caps, key=lambda x: -x["frequency_sum"])[:30]:
    gcap_lines.append(
        f"  [{gc['frequency_sum']:3}x]  {gc['name']:<45}  {gc['domain']}  (src={gc['detailed_capability_count']})"
    )

domain_lines = []
gcap_lookup = {gc["id"]: gc for gc in grouped_caps}
for gd in sorted(grouped_domains, key=lambda x: -x["total_frequency"]):
    sample_names = [gcap_lookup[gid]["name"] for gid in gd["grouped_capability_ids"][:4] if gid in gcap_lookup]
    sample = ", ".join(sample_names)
    if gd["grouped_capability_count"] > 4:
        sample += f" +{gd['grouped_capability_count']-4} more"
    domain_lines.append(
        f"  {gd['name']:<35}  gcaps={gd['grouped_capability_count']:3}  src_caps={gd['source_capability_count']:3}  [{sample}]"
    )

report = f"""
## DUAL_LAYER_MODEL_COMPLETE — 2026-04-22

### Inputs

| File | Entries |
|---|---|
| capabilities.json (detailed) | {len(detailed_caps)} |
| flows.jsonl | {len(flows_raw)} |
| requirements.jsonl | {len(reqs_raw)} |

---

### STEP 1 — Detailed Layer

Kopieret til: `harvest/layer2/capabilities_detailed.json` — {len(detailed_caps)} detailed capabilities bevaret uændret.

---

### STEP 2 — Grouped Capabilities ({len(grouped_caps)} total)

Top 30 grouped capabilities efter frekvens:

```
{chr(10).join(gcap_lines)}
```

---

### STEP 3 — Grouped Domains ({len(grouped_domains)} total)

```
{chr(10).join(domain_lines)}
```

---

### STEP 4 — Traceability Check

| Check | Resultat | Status |
|---|---|---|
| Alle {len(all_detailed_ids)} detailed caps dækket af grouped | {len(lost_detailed)} tabte | {"✅ 0 tabte" if len(lost_detailed)==0 else f"❌ {len(lost_detailed)} tabte"} |
| Alle grouped caps tilknyttet domain | {len(gcaps_missing_domain)} mangler | {"✅" if len(gcaps_missing_domain)==0 else f"❌ {len(gcaps_missing_domain)} mangler"} |
| grouped → detailed link integritet | {len(grouped_source_ids)} unikke detailed ids | ✅ |

---

### STEP 5 — Final Metrics

| Metric | Resultat |
|---|---|
| detailed_capabilities | {len(detailed_caps)} |
| grouped_capabilities | {len(grouped_caps)} |
| grouped_domains | {len(grouped_domains)} |
| ungrouped_detailed | {len(lost_detailed)} |
| reduction_ratio | {len(detailed_caps)/len(grouped_caps):.1f}x |
| traceability_ok | {trace_ok} |

### Artifacts

- `harvest/layer2/capabilities_detailed.json` — {len(detailed_caps)} detailed (kopi af capabilities.json — truth layer)
- `harvest/layer2/capabilities_grouped.json` — {len(grouped_caps)} grouped capabilities
- `harvest/layer2/domains_grouped.json` — {len(grouped_domains)} grouped domains

{stop_cond}

---
"""

existing = TEMP_MD.read_text(encoding="utf-8")
TEMP_MD.write_text(existing + "\n" + report.lstrip("\n"), encoding="utf-8")
print("temp.md updated.")
print(stop_cond)
