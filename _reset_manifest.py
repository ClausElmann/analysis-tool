"""Reset SMART DONE components to PENDING if evidence_pack now has http calls."""
import json
from pathlib import Path

raw = Path("harvest/angular/raw")
mpath = Path("harvest/harvest-manifest.json")
manifest = json.loads(mpath.read_text(encoding="utf-8"))

reset = []
for k, v in manifest.items():
    if v.get("status") == "DONE":
        name = Path(k).stem.replace(".component", "")
        ep = raw / name / "evidence_pack.json"
        if ep.exists():
            p = json.loads(ep.read_text(encoding="utf-8"))
            if p["meta"]["type"] == "SMART" and v.get("pipeline_status") in ("INFERRED_UI", "PARTIAL", None):
                shc = p.get("service_http_calls", [])
                if shc:
                    manifest[k]["status"] = "PENDING"
                    manifest[k]["retryCount"] = 0
                    manifest[k]["pipeline_status"] = None
                    reset.append(name)

mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Reset {len(reset)} SMART DONE->PENDING (now have http evidence):")
for n in reset:
    print(f"  {n}")

vals = list(manifest.values())
done = sum(1 for v in vals if v["status"] == "DONE")
pend = sum(1 for v in vals if v["status"] == "PENDING")
skip = sum(1 for v in vals if v["status"] == "SKIPPED")
print(f"\nDONE={done}  PENDING={pend}  SKIPPED={skip}")
