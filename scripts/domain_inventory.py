import json, os, re

def count_items(domain, filename):
    path = f'domains/{domain}/{filename}'
    if not os.path.exists(path): return 0, 0
    try:
        with open(path, encoding='utf-8') as f:
            raw = f.read()
        raw = re.sub(r'//[^\n]*', '', raw)
        data = json.loads(raw)
    except Exception:
        return -1, -1
    items = data if isinstance(data, list) else []
    if not isinstance(data, list):
        for k in ('entities','behaviors','flows','rules'):
            if k in data:
                items = data[k]; break
    total = len(items)
    with_ev = sum(1 for i in items if isinstance(i, dict) and i.get('source_file','UNKNOWN') not in ('UNKNOWN','','null',None))
    return total, with_ev

with open('domains/domain_state.json', encoding='utf-8') as f:
    state = json.load(f)

skip = {'_global', 'product_scope'}
rows = []
for domain, v in state.items():
    if domain in skip: continue
    c = v.get('completeness_score', 0)
    it = v.get('iteration', 0)
    gaps = len(v.get('gaps', []))
    rows.append((c, domain, it, gaps))

rows.sort(reverse=True)

header = "Domain                         Score  Iter  Gaps  E(t/ev)    B(t/ev)    F(t/ev)    R(t/ev)"
print(header)
print('-' * len(header))
for c, d, it, g in rows:
    e = count_items(d, '010_entities.json')
    b = count_items(d, '020_behaviors.json')
    f = count_items(d, '030_flows.json')
    r = count_items(d, '070_rules.json')
    print(f"{d:<30} {c:>5.2f} {it:>5} {g:>5}  {e[0]:>3}/{e[1]:<3}  {b[0]:>3}/{b[1]:<3}  {f[0]:>3}/{f[1]:<3}  {r[0]:>3}/{r[1]:<3}")
