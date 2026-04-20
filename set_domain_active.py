"""
Usage: python set_domain_active.py <domain_name>
Sets domain status=in_progress and _global.active_domain without touching other fields.
"""
import json
import sys

domain = sys.argv[1]
path = "domains/domain_state.json"

with open(path, "r", encoding="utf-8") as f:
    j = json.load(f)

j[domain]["status"] = "in_progress"
j["_global"]["active_domain"] = domain

with open(path, "w", encoding="utf-8") as f:
    json.dump(j, f, indent=2, ensure_ascii=False)

print(f"Set {domain} → in_progress, active_domain={domain}")
print(f"Current: iter={j[domain].get('iteration',0)} no_op={j[domain].get('no_op_iterations',0)}")
