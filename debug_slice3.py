"""Diagnostic for SLICE_3 — run standalone."""
import json, os, re, sys
sys.path.insert(0, ".")
from core.execution_engine import ExecutionEngine, _extract_dapper_sqls

e = ExecutionEngine(
    solution_root="c:/Udvikling/sms-service",
    db_root="C:/Udvikling/sms-service/ServiceAlert.DB",
)

with open("data/solution_structure.json", encoding="utf-8") as f:
    sol = json.load(f)

cs_files = []
for proj in sol["projects"]:
    pt = proj.get("type", "")
    if pt in ("api", "unknown", "database", "batch", "library", "service"):
        pp = proj.get("path", "")
        if pp and os.path.isdir(pp):
            for dp, dirs, fnames in os.walk(pp):
                skip = any(
                    p.lower() in ("bin", "obj", "node_modules", "dist", ".git")
                    for p in dp.replace("\\", "/").split("/")
                )
                if not skip:
                    for fname in fnames:
                        if fname.endswith(".cs"):
                            cs_files.append(os.path.join(dp, fname))

print(f"CS files: {len(cs_files)}")
svc_idx = e._build_service_index_3(cs_files)
ctrl_idx = e._build_controller_index(cs_files)
print(f"Controllers: {len(ctrl_idx)}  Services: {len(svc_idx)}")

# Check benchmark
bm_svcs = [(k, v) for k, v in svc_idx.items() if "benchmark" in k.lower()]
print(f"\nBenchmark services: {bm_svcs[:5]}")

if bm_svcs:
    svc_name, svc_file = bm_svcs[0]
    content = e._read_file(svc_file) or ""
    sqls = _extract_dapper_sqls(content)
    print(f"SQLs in {svc_name}: {len(sqls)}")
    for s in sqls[:2]:
        print(f"  {s[:120]}")

# Check what URL resolves to
with open("data/component_api_map.json", encoding="utf-8") as f:
    cmap = json.load(f)

print("\nComponent API map entries:")
for m in cmap["mappings"]:
    print(f"  {m['component']}: {[a['url'] for a in m.get('apis', [])[:2]]}")

# Try to resolve ApiRoutes
api_routes = e._build_api_routes_index()
print(f"\nApiRoutes index size: {len(api_routes)}")
sample_url = "ApiRoutes.benchmarkRoutes.get.getBenchmarks"
print(f"Resolved {sample_url!r}: {api_routes.get(sample_url, 'NOT FOUND')}")

# Try controller match
for m in cmap["mappings"]:
    comp = m["component"]
    for api in m.get("apis", []):
        url = api["url"]
        if url.startswith("ApiRoutes.") and url in api_routes:
            url = api_routes[url]
        route_idx = e._build_controller_route_index(cs_files)
        ctrl_name, ctrl_file, ctrl_method = e._find_controller_and_action(url, route_idx, ctrl_idx)
        print(f"\n{comp} → {url}")
        print(f"  Controller: {ctrl_name or 'NOT FOUND'} | method: {ctrl_method or '-'}")
        if ctrl_file:
            content = e._read_file(ctrl_file) or ""
            sqls = _extract_dapper_sqls(content)
            print(f"  SQL in controller file: {len(sqls)}")
        # Level 4 fallback: service lookup by keyword
        keyword = url.lstrip("/")
        if keyword.lower().startswith("api/"):
            keyword = keyword[4:]
        keyword = keyword.split("/")[0].lower()
        matched_svcs = [(k, v) for k, v in svc_idx.items() if keyword and keyword in k.lower()]
        print(f"  Level-4 keyword={keyword!r} → matched services: {[k for k, v in matched_svcs[:3]]}")
        for svc_name, svc_file in matched_svcs[:3]:
            sqls = _extract_dapper_sqls(e._read_file(svc_file) or "")
            print(f"    {svc_name}: {len(sqls)} SQLs")
        break  # one API per component
    break  # first component only
