# LEGACY — DO NOT RUN
# This script is superseded by run_domain_engine.py (Gen 3 canonical entrypoint).
# Retained for reference only. Running this file may corrupt domain state.
import json
from collections import Counter
ext = json.load(open('data/system_model_extended.json', encoding='utf-8'))
stats = ext['coverage_stats']
print(json.dumps(stats, indent=2))
print()
print('Use case types:')
types = Counter(uc['type'] for uc in ext['use_cases'])
for t, c in sorted(types.items()):
    print(f'  {t}: {c}')
print()
print('Modules with linked non-REST data:')
for mod in ext['modules']:
    has = {k: mod[k] for k in ('batch_jobs','webhooks','events','background_services','realtime') if mod.get(k)}
    if has:
        parts = ', '.join(f"{k}:{len(v)}" for k, v in has.items())
        print(f'  {mod["name_raw"][:45]:45} -> {parts}')
