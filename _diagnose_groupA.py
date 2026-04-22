import json
from pathlib import Path
raw = Path('harvest/angular/raw')

targets = ['my-senders','subscription-app','mobile-and-pin','sender-selection','additional-sender-selection','send-a-tip-dialog-content','en-address-selector']
out = {}
for name in targets:
    ep = json.loads((raw/name/'evidence_pack.json').read_text(encoding='utf-8'))
    shc = ep.get('service_http_calls',[]) or []
    ta  = ep.get('template_actions',[]) or []
    tsm = ep.get('ts_methods',[]) or []
    inj = ep.get('injected_services',[]) or []
    out[name] = {
        'type': ep['meta']['type'],
        'svc': len(inj),
        'http_raw': len(shc),
        'actions': len(ta),
        'methods': len(tsm),
        'shc': [{'svc':h.get('service'),'method':h.get('service_method'),'http':h.get('http_method'),'url':h.get('url')} for h in shc],
        'template_handlers': [a.get('handler') for a in ta if a.get('handler')],
    }

print(json.dumps(out, indent=2, ensure_ascii=False))
