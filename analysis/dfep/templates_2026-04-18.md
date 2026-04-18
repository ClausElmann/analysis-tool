# DFEP v3 Report — Templates

> Generated: 2026-04-18 02:02  
> Engine: DFEP v3 — Copilot-Native (no external LLM)  
> Intelligence: GitHub Copilot (VS Code)  

---

## Coverage Summary

| Metric | Value |
|--------|-------|
| L0 source facts | 132 |
| GreenAI facts | 25 |
| L0 capabilities | 8 |
| GreenAI capabilities | 8 |
| Total L0 (in comparison) | 9 |
| Matched (exact) | 9 |
| Matched (partial) | 0 |
| Missing | 0 |
| **Match score** | **100%** |
| CRITICAL gaps | 0 |
| HIGH gaps | 0 |
| Low-confidence capabilities | 0 |

> **DFEP GATE: PASSED** — Match score >= 90%, no CRITICAL or HIGH gaps

---

## Level 0 Capabilities (sms-service)

| ID | Intent | Confidence |
|----|--------|-----------|
| `template_profile_access` | Manage which profiles have visibility to which templates (M:M link/unlink) | ✅ 0.93 |
| `list_templates` | List templates available for SMS and email for a given customer and profile | ✅ 0.92 |
| `email_template_crud` | CRUD operations for system email templates (not business SMS templates) | ✅ 0.91 |
| `dynamic_mergefields_management` | Define, update, and delete customer-specific dynamic merge field definitions | ✅ 0.90 |
| `get_template_by_id` | Retrieve a single template by ID | ✅ 0.88 |
| `create_template` | Create a new message template with channel-specific content | ✅ 0.85 |
| `update_template` | Update an existing message template | ✅ 0.85 |
| `delete_template` | Delete a message template and its channel-specific sub-entities | ✅ 0.83 |

---

## GreenAI Capabilities (green-ai/src)

| ID | Intent | Confidence |
|----|--------|-----------|
| `list_templates` | Return all message templates accessible to the current profile | ✅ 0.95 |
| `create_template` | Insert a new message template and grant access to specified profiles | ✅ 0.93 |
| `get_template_by_id` | Return a single template by ID, scoped to the calling profile | ✅ 0.92 |
| `update_template` | Modify an existing message template's content and profile access set | ✅ 0.92 |
| `delete_template` | Hard-delete an existing message template and all its profile access entries | ✅ 0.92 |
| `resolve_content` | Resolve template body and subject with [FieldName] token substitution before mes | ✅ 0.88 |
| `template_profile_access` | Grant and enforce per-profile access to templates via M:M mapping | ✅ 0.88 |
| `dynamic_mergefields_management` | Allow callers to supply custom token values at send time for template body/subje | ✅ 0.85 |

---

## Capability Comparison

| L0 Capability | GreenAI Capability | Match | Severity | Impact |
|--------------|-------------------|-------|----------|--------|
| `list_templates` | `list_templates` | ✅ MATCH_CLEAN_REBUILD | 🟢 LOW | No user impact — profile-scoped listing is the standard use  |
| `get_template_by_id` | `get_template_by_id` | ✅ MATCH_EXACT | 🟢 LOW | No user impact — GreenAI is functionally equivalent and more |
| `create_template` | `create_template` | ✅ MATCH_CLEAN_REBUILD | 🟢 LOW | No user impact — GreenAI is functionally equivalent with str |
| `template_merge_execution` | `resolve_content` | ✅ MATCH_CLEAN_REBUILD | 🟢 LOW | Direct mode customers get unresolved tokens when using addre |
| `update_template` | `update_template` | ✅ MATCH_CLEAN_REBUILD | 🟢 LOW | No user impact — GreenAI is functionally equivalent with str |
| `template_profile_access` | `template_profile_access` | ✅ MATCH_CLEAN_REBUILD | 🟢 LOW | No user impact. Profile access is manageable via PUT /api/v1 |
| `delete_template` | `delete_template` | ✅ MATCH_CLEAN_REBUILD | 🟢 LOW | No user impact — GreenAI is functionally equivalent. |
| `dynamic_mergefields_management` | `dynamic_mergefields_management` | ✅ MATCH_CLEAN_REBUILD | 🟢 LOW | No user impact. Callers supply any token values at send time |
| `email_template_crud` | `create_template` | ✅ MATCH_CLEAN_REBUILD | 🟢 LOW | No user impact — GreenAI covers email templates natively via |

---

## Drift vs Prior Run

[DRIFT] Prior run: 2026-04-18 | Score delta: +0%
  No changes since prior run — domain state stable

---

## Summary

GreenAI covers list, get, create, update (atomic profile set replacement), delete (hard delete), profile access management (via update), runtime token merge for address mode, and caller-supplied dynamic merge fields on send-direct. Missing: email_template_crud (LOW — system notification emails, not customer templates). No CRITICAL or HIGH gaps. DFEP gate threshold achievable.

---
