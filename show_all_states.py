import json

with open('domains/domain_state.json', encoding='utf-8') as f:
    j = json.load(f)

not_done = []
done = []
for k, v in j.items():
    if k == '_global' or not isinstance(v, dict):
        continue
    st = v.get('status', '?')
    sc = v.get('completeness_score', 0)
    if st not in ('complete', 'stable'):
        not_done.append((k, sc, st))
    else:
        done.append((k, sc, st))

print('=== NOT DONE ===')
for k, sc, st in sorted(not_done, key=lambda x: x[1]):
    print(k + ': score=' + str(sc) + ' status=' + st)

print('\n=== DONE (' + str(len(done)) + ') ===')
for k, sc, st in sorted(done, key=lambda x: x[1]):
    print(k + ': score=' + str(sc) + ' status=' + st)
