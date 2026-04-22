import json, re
from pathlib import Path
from collections import defaultdict

flows_path = Path("corpus/flows.jsonl")
flows = [json.loads(l) for l in flows_path.read_text(encoding="utf-8").splitlines() if l.strip()]

VERB_MAP = {
    "get": "get", "fetch": "get", "load": "get", "list": "get", "getall": "get",
    "init": "get", "initialize": "get", "setup": "get", "refresh": "get",
    "create": "create", "add": "create", "insert": "create", "new": "create", "send": "create",
    "update": "update", "edit": "update", "save": "update", "put": "update",
    "patch": "update", "set": "update", "toggle": "update",
    "delete": "delete", "remove": "delete", "destroy": "delete", "clear": "delete",
}

def normalize_method(method_name):
    s = re.sub(r"([A-Z])", r" \1", method_name).lower().strip()
    words = s.split()
    if not words:
        return method_name.lower()
    norm_verb = VERB_MAP.get(words[0], words[0])
    rest = [w for w in words[1:] if w not in ("model", "data", "result", "response", "list", "info")]
    rest = [re.sub(r"\d+", "{id}", w) for w in rest]
    return (norm_verb + " " + " ".join(rest)).strip() if rest else norm_verb

def normalize_http(http_str):
    parts = http_str.strip().split(" ", 1)
    verb = parts[0].upper() if parts else "?"
    url = parts[1] if len(parts) > 1 else ""
    url = re.sub(r"\{ApiRoutes\.[^}]+\}", lambda m: "{" + m.group(0).split(".")[-1].rstrip("}") + "}", url)
    url = re.sub(r"/\d+", "/{id}", url)
    url = re.sub(r"[a-f0-9]{8}-[a-f0-9-]{27}", "{guid}", url)
    return (verb + " " + url.strip()).strip()

results = []
for f in flows:
    svc_call = f.get("service_call", "")
    method_name = svc_call.split(".")[-1].rstrip("()") if "." in svc_call else svc_call
    norm_method = normalize_method(method_name)
    norm_http = normalize_http(f.get("http", ""))
    results.append({
        "id": f.get("id"),
        "component": f.get("component", ""),
        "original_service_call": svc_call,
        "norm_method": norm_method,
        "norm_key": norm_http,
        "trigger": f.get("trigger", ""),
    })

clusters = defaultdict(list)
for r in results:
    clusters[r["norm_key"]].append(r)

unique_flows = []
for key, members in sorted(clusters.items(), key=lambda x: -len(x[1])):
    unique_flows.append({
        "norm_key": key,
        "representative": members[0]["original_service_call"],
        "count": len(members),
        "source_components": sorted(set(m["component"] for m in members)),
    })

orig = len(results)
unique = len(unique_flows)
ratio = orig / unique if unique else 0

print(f"original_flows_count: {orig}")
print(f"unique_flows_count:   {unique}")
print(f"compression_ratio:    {ratio:.2f}x")
print()
print("=== UNIQUE FLOWS (sorted by count desc) ===")
for u in sorted(unique_flows, key=lambda x: -x["count"]):
    comps = ", ".join(u["source_components"])
    print(f"  [{u['count']:3}x]  {u['norm_key']}")
    print(f"         via: {u['representative']}")
    print(f"         components: {comps}")
print()
print(f"compression_ratio {ratio:.2f}x  (krav: > 2x)")
if ratio >= 2.0:
    print("KRAV OPFYLDT")
else:
    print("KRAV IKKE OPFYLDT")
