# LEGACY — DO NOT RUN
# This script is superseded by run_domain_engine.py (Gen 3 canonical entrypoint).
# Retained for reference only. Running this file may corrupt domain state.
import json
mod = json.load(open('data/system_model.json', encoding='utf-8'))
for m in mod['modules']:
    if m.get('apis') and m.get('tables'):
        print(json.dumps(m, indent=2, ensure_ascii=False)[:2000])
        break
print("\n---TOTAL MODULES:", len(mod['modules']))
print("Modules with APIs:", sum(1 for m in mod['modules'] if m.get('apis')))
print("Modules with tables:", sum(1 for m in mod['modules'] if m.get('tables')))
# Show batch_jobs.json sample
bj = json.load(open('data/batch_jobs.json', encoding='utf-8'))
print("\nbatch sample:", json.dumps(bj['jobs'][0], indent=2))
# Show background_services.json sample
bg = json.load(open('data/background_services.json', encoding='utf-8'))
print("\nbg sample:", json.dumps(bg['services'][0], indent=2))
# Show webhook sample
wh = json.load(open('data/webhook_map.json', encoding='utf-8'))
print("\nwebhook sample:", json.dumps(wh['webhooks'][0], indent=2))
# Show event sample
ev = json.load(open('data/event_map.json', encoding='utf-8'))
print("\nevent sample:", json.dumps(ev['events'][0], indent=2))
# Show realtime sample
rt = json.load(open('data/realtime_map.json', encoding='utf-8'))
print("\nrealtime sample:", json.dumps(rt['streams'][0], indent=2))
