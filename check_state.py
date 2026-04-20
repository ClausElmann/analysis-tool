import json

with open('domains/domain_state.json', encoding='utf-8') as f:
    j = json.load(f)

for d in ['delivery', 'web_messages', 'standard_receivers', 'sms_group']:
    entry = j.get(d, None)
    if entry is None:
        print(d + ': MISSING from domain_state.json')
    else:
        it = entry.get('iteration', '?')
        no_op = entry.get('no_op_iterations', '?')
        st = entry.get('status', '?')
        sc = entry.get('completeness_score', '?')
        print(d + ': iteration=' + str(it) + ' no_op=' + str(no_op) + ' status=' + str(st) + ' score=' + str(sc))

print('---')
print('active_domain=' + str(j.get('_global', {}).get('active_domain', '?')))
