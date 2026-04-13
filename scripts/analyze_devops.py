import csv, sys
csv.field_size_limit(10000000)
with open('raw/data.csv', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
items_by_id = {r['ID']: r for r in rows}
top_ids = ['11038','11805','12131','7763','10941','12069','5565','11453','2828','6950',
           '10343','10793','6624','4551','5594','10090','8984','10247','3768','7333']
print('Top referenced work items (commit frequency):')
for wid in top_ids:
    if wid in items_by_id:
        r = items_by_id[wid]
        wtype = r['Work Item Type']
        state = r['State']
        title = r['Title']
        print(f'  #{wid} [{wtype}][{state}] {title}')
    else:
        print(f'  #{wid} NOT IN CSV')

# Bugs by keyword domain
print('\nBugs per domæne-keyword:')
from collections import Counter
bugs = [r for r in rows if r['Work Item Type'] == 'Bug']
keywords = ['broadcast','smsgroup','smslog','lookup','gateway','webhook','schedule',
            'conversation','archive','voice','eboks','subscription','template',
            'address','positivelist','warning','single sms','merge']
for kw in keywords:
    matches = [r for r in bugs if kw.lower() in r['Title'].lower()]
    if matches:
        open_bugs = [m for m in matches if m['State'] not in ('Done','Removed','Closed')]
        print(f'  {kw}: {len(matches)} total, {len(open_bugs)} open')
