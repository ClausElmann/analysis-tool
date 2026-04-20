"""
Restore domain_state.json from HEAD, but carry over the completed status
for domains that were harvested in this session:
  delivery, web_messages, standard_receivers, sms_group,
  eboks_integration, logging
Also preserve the earlier-session fixes for product_scope and system_configuration.
"""
import json
import shutil
import os

head_path = 'domains/domain_state_from_head.json'
current_path = 'domains/domain_state.json'
backup_path = 'domains/domain_state_corrupt_backup.json'

# Backup corrupt version
shutil.copy(current_path, backup_path)
print('Backed up corrupt file to', backup_path)

# Load HEAD (full 39 entries)
with open(head_path, encoding='utf-8') as f:
    head = json.load(f)

# Domains we successfully harvested to complete + score=1.0 this session
harvested = {
    'delivery', 'web_messages', 'standard_receivers', 'sms_group',
    'eboks_integration', 'logging'
}

for domain in harvested:
    if domain in head:
        head[domain]['status'] = 'complete'
        head[domain]['completeness_score'] = 1.0
        head[domain]['consistency_score'] = 1.0
        head[domain]['saturation_score'] = 1.0
        print(f'Updated {domain}: status=complete, scores=1.0')

# Clear active_domain
head['_global']['active_domain'] = None

with open(current_path, 'w', encoding='utf-8') as f:
    json.dump(head, f, indent=2, ensure_ascii=False)

print('\nRestored domain_state.json with', len(head), 'entries')

# Verify
with open(current_path, encoding='utf-8') as f:
    check = json.load(f)
print('Verification: entries =', len(check))
for d in sorted(harvested):
    e = check.get(d, {})
    print(f'  {d}: status={e.get("status","?")} score={e.get("completeness_score","?")}')
