# DFEP v3 Report — Templates

> Generated: 2026-04-17 22:08  
> Engine: DFEP v3 — Copilot-Native (no external LLM)  
> Intelligence: GitHub Copilot (VS Code)  

---

## Coverage Summary

| Metric | Value |
|--------|-------|
| L0 source facts | 132 |
| GreenAI facts | 6 |
| L0 capabilities | 8 |
| GreenAI capabilities | 2 |
| Total L0 (in comparison) | 8 |
| Matched (exact) | 2 |
| Matched (partial) | 0 |
| Missing | 6 |
| **Match score** | **25%** |
| CRITICAL gaps | 0 |
| HIGH gaps | 2 |
| Low-confidence capabilities | 0 |

> **DFEP GATE: FAILED** — Match score 25% < 90% threshold. Missing: 6 L0 capabilities.

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
| `get_template_by_id` | Retrieve a single message template by ID, scoped to the authenticated customer A | ✅ 0.93 |
| `list_templates` | List message templates for the authenticated user's customer and profile via JWT | ✅ 0.91 |

---

## Capability Comparison

| L0 Capability | GreenAI Capability | Match | Severity | Impact |
|--------------|-------------------|-------|----------|--------|
| `list_templates` | `list_templates` | ✅ MATCH_CLEAN_REBUILD | 🟢 LOW | Customer-wide listing (no profile filter) not available in G |
| `get_template_by_id` | `get_template_by_id` | ✅ MATCH_EXACT | 🟢 LOW | No user impact — GreenAI is functionally equivalent and more |
| `create_template` | — | ❌ MISSING | 🟠 HIGH | GreenAI users cannot create new message templates. Templates |
| `update_template` | — | ❌ MISSING | 🟠 HIGH | GreenAI templates are immutable once seeded. Cannot correct  |
| `delete_template` | — | ❌ MISSING | 🟡 MEDIUM | GreenAI users cannot remove obsolete templates. Moderate — t |
| `template_profile_access` | — | 🔀 INTENT_DRIFT | 🟡 MEDIUM | Template-profile mappings in GreenAI are set at DB seed time |
| `dynamic_mergefields_management` | — | ❌ MISSING | 🟡 MEDIUM | GreenAI cannot define or manage custom personalization token |
| `email_template_crud` | — | ❌ MISSING | 🟢 LOW | System notification emails in GreenAI presumably handled via |

---

## Drift vs Prior Run

[DRIFT] Prior run: 2026-04-17 | Score delta: +25%
  Resolved gaps: get_template_by_id, list_templates

---

## Gaps Requiring Action

### 🟠 HIGH: `create_template`

**Difference:** L0 InsertAsync creates message templates (SMS + email channel variants, profile access seed). GreenAI has no create-template capability. What the customer achieves: create a reusable message template for outgoing SMS/email. Constraints: must belong to a CustomerId, channel-typed. Access: customer admin or system. State: new row in MessageTemplates.

**Impact:** GreenAI users cannot create new message templates. Templates must be seeded via DB migration.

**Required Action:** Phase 2: ADD Create Template feature — POST /api/v1/templates

### 🟠 HIGH: `update_template`

**Difference:** L0 UpdateAsync modifies template content, channel variants, and profile access. GreenAI has no update capability. What customer achieves: edit an existing template's body/subject. State: updated row in MessageTemplates.

**Impact:** GreenAI templates are immutable once seeded. Cannot correct or update content.

**Required Action:** Phase 2: ADD Update Template feature — PUT /api/v1/templates/{id}

---

## Summary

GreenAI Templates domain covers 2 of 8 L0 capabilities exactly/clean-rebuild (list_templates as CLEAN_REBUILD, get_template_by_id as EXACT). template_profile_access reclassified as INTENT_DRIFT MEDIUM: L0 mapping management is admin-only, not customer self-service — runtime enforcement in GreenAI is Phase 1 sufficient. 2 HIGH gaps remain: create and update (Phase 2 CRUD). delete is MEDIUM. DFEP gate FAILED on match score 25% — 5 missing capabilities. Phase 1 verdict for template access: runtime enforcement sufficient.

---
