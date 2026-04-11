# templates — Domain Distillation

**Status:** APPROVED_BASELINE 2026-04-11  
**Completeness score (Layer 1):** 0.37 (behaviors=[] rules=garbage — source-primary)  
**Evidence source:** `administration/message-templates/` Angular feature, entity list from `010_entities.json`

---

## What this domain is

**Templates** is the domain for managing reusable message templates. Each template can contain content for multiple delivery channels simultaneously (SMS, Email, Voice, eBoks, Facebook, Twitter/X, Web, Internal, Benchmark/InfoPortal). Templates are assigned profile access rights, can include dynamic merge fields (user-defined and system-defined), may have quick response options, and can be mapped to weather warning types. Templates are consumed by the message wizard at compose time.

---

## Channel Types (per template)

| DTO | Channel |
|---|---|
| `TemplateSmsDto` | SMS |
| `TemplateEmailDto` | Email |
| `TemplateVoiceDto` | Voice |
| `TemplateEboksDto` | eBoks |
| `TemplateFacebookDto` | Facebook |
| `TemplateTwitterDto` | Twitter/X |
| `TemplateWebDto` | Web message |
| `TemplateInternalDto` | Internal channel |
| `TemplateBenchmarkDto` | Benchmark / InfoPortal |

---

## Template Structure

```
Template
├── name (required)
├── warningTemplateType (None | specific weather type)
├── parts[]  ← one per enabled channel (TemplateSmsDto, TemplateEmailDto, ...)
│   ├── text content
│   ├── mergefieldReferences[]
│   ├── attachments[] (TemplateAttachmentDto)
│   └── quickResponseEnabled flag
├── quickResponseSetup (TemplateQuickResponseSetupDto)
│   └── responseOptions[]  (TemplateResponseOptionUpdateCommand)
│       + responseSettings (TemplateResponseSettingsUpdateCommand)
└── profileAccess[]  ← set on creation; editable via ProfileAccess tab
```

---

## Template List UI

- `bi-item-indicator-table` — visual indicator columns showing which channels have content
- Per-row: Edit and Delete buttons
- Delete: confirmation dialog ("Sure to delete?")
- Create button → navigates to create form

---

## Template Create / Edit Form

**Template name:** required text field

**Copy from existing:** Available to impersonating super-admin only — select country + customer + source template → copies channel content

**Template parts layout (3 sections):**

1. **Benchmark / InfoPortal section** — separate content box; shown for new templates or when `warningTemplateType = None`
2. **Individual message types** — SMS, Email, Voice, eBoks, etc. in a single box with quick response setup above
3. **Public lookup message types** — shown only when `canUsePublicMessages=true` AND no warning type set

**Each `template-part` component exposes:**
- Enable/disable toggle
- Text editor with merge field insertion
- Optional file attachments (`canAttachFiles` per type)
- Dynamic merge fields (user-defined + system-defined)
- Test send buttons (SMS test / Voice test inline)
- Copy from SMS text → copy to email / Voice
- Quick response enable flag

**Profile access (create only):** Multi-select listbox of profiles → sets which profiles can use this template. Post-creation: managed via dedicated ProfileAccess tab.

---

## Merge Fields

**Two classes:**
- **User-defined fields** — created by admin; editable; can be all types
- **System-defined fields** — predefined by system; only `MergeFieldType.Date` fields are editable; others are read-only (disabled button)

**Field management:**
- `template-merge-fields` tab with Create + Edit dialog per field
- Displayed as buttons in two separate boxes (user / system)
- Icons per field type

**DTOs:** `TemplateMergeFieldDto`, `TemplateMergeFieldOptionsDto`

---

## Quick Response Setup

- Enabled per template via `TemplateQuickResponseSetupDto`
- Requires `writeMessageModel().allowedMessageTypes.quickReponse = true`
- `bi-quick-response-setup-enabler` component manages setup
- `responseOptions[]` — individual reply options (text + answer)
- `responseSettings` — global settings for the quick response
- When template with quick response is used in wizard: wizard shows quick response as configured

---

## Profile Access (Post-Create)

- `template-profile-access` component — separate tab from create form
- Shows list of all profiles; checkboxes to grant/revoke access
- Separated from create flow (create form has inline listbox for initial profiles)

---

## Weather Warning Template Mapping

- `weather-warning-type-to-template-setup` component
- Maps specific weather warning event types to a specific template
- When a weather warning is triggered: system auto-selects the mapped template
- Setting `warningTemplateType` on a template restricts its usage to warning broadcasts only (hides public message section in editor)

---

## Capabilities

1. Multi-channel templates (SMS, Email, Voice, eBoks, Facebook, Twitter/X, Web, Internal, Benchmark/InfoPortal)
2. Visual indicator table showing which channels are configured per template
3. Template create / edit / delete with name validation
4. Per-channel text editing with merge field insertion
5. File attachment support per channel (where enabled)
6. Dynamic merge fields — user-defined (all types) + system-defined (Date type editable)
7. Quick response option setup (response options + settings) per template
8. Profile access control (initial: listbox; ongoing: ProfileAccess tab)
9. Copy template from another customer (impersonating super-admin only)
10. In-editor test send (SMS, Voice) with test message and test mode
11. Cross-channel copy (copy SMS text → Email / Voice)
12. Weather warning template mapping (auto-template-selection on warning trigger)

---

## Flows

### FLOW_TPL_001: Create new template
1. Admin navigates to Administration → Message Templates → Templates tab
2. Clicks Create → form shown
3. Enter template name
4. Enable/fill desired channel parts (SMS text, Email text, etc.)
5. Add merge fields references as needed
6. (Optional) Enable quick response + configure options
7. Select profiles that should have access (listbox)
8. Save → template created; profile mappings created

### FLOW_TPL_002: Use template in message wizard
1. User reaches WriteMessage step in wizard
2. `message-template-selection` component shows available templates for current profile
3. User selects template → message parts pre-filled from template
4. Overwrite dialog (`bi-overwrite-template-dialog`) if message already has content
5. Merge fields resolved at compose/send time

### FLOW_TPL_003: Weather warning auto-template selection
1. Admin maps weather warning type → template in weather-warning setup
2. Weather warning event arrives
3. System auto-selects mapped template for broadcast
4. Template with `warningTemplateType != None` pre-fills warning broadcast channels

---

## Rules

| ID | Rule |
|---|---|
| TPL_R001 | Template name is required (TemplateNameRequired) |
| TPL_R002 | Profile access is set on create via listbox; managed via ProfileAccess tab after creation |
| TPL_R003 | Templates with `warningTemplateType != None` hide the public message section in editor |
| TPL_R004 | Copy from existing only available to impersonating super-admin |
| TPL_R005 | System-defined merge fields: only MergeFieldType.Date is editable; others are read-only |
| TPL_R006 | Quick response available only when `allowedMessageTypes.quickReponse = true` for the profile |

---

## Gaps

| ID | Gap |
|---|---|
| GAP_001 | `TemplateInternalDto` channel purpose not clarified — "internal" channel recipient type unknown |
| GAP_002 | Attachment upload flow not traced — how files are attached to a template not examined |
| GAP_003 | `TemplateBenchmarkDto` purpose not confirmed — appears to be InfoPortal/Benchmark feature |
| GAP_004 | Merge field type options (beyond Date) not fully read |
| GAP_005 | Facebook and Twitter template publishing paths not examined |
