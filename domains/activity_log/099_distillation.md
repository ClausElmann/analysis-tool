# Domain Distillation: activity_log

**STATUS:** APPROVED_BASELINE  
**Completeness source:** 0.92 (Layer 1) + UI verification  
**UI verified from:** `activity-log-dialog-content.component.html`, `activity-logs-table.component.html`  
**Date:** 2026-04-11  

---

## PURPOSE

Activity log is the audit trail for customer-owned data objects. Whenever an important operation completes — a broadcast is created, a subscription file is imported, a positive list is uploaded, standard receivers are imported — a log entry is written recording when it happened, who did it, and a description key. This log is surfaced in the UI as a dialog showing the change history for a specific data object.

---

## CORE CONCEPTS

1. **ActivityLog** — the parent record per data object. One ActivityLog exists per (type, objectId) combination. It is created the first time an event is recorded for that object; subsequent events add children without changing the parent.

2. **ActivityLogEntry** — a child event under an ActivityLog. Each capture: a timestamp, the user who performed the action, and a description translation key with optional parameters.

3. **ActivityLogType** — a fixed set of object types that can be tracked: Broadcast, SubscriptionsImport, PositiveListsImport, StandardReceiversImport. This list is defined in code and cannot be extended without a code change.

4. **descriptionTranslationKey** — the description stored in the log is a locale resource key, not a pre-translated string. The text is resolved at display time using the viewer's language, so the same log entry can be read in any language.

5. **objectId** — the primary key of the data object being tracked (e.g. the ID of the FTP setting file, the broadcast row, or the import file). Used to load all history for that specific object.

---

## CAPABILITIES

1. Record an activity event for a data object (created by a service operation — not directly by an admin action).
2. Record multiple activity events in a batch (used when a bulk operation completes with several outcomes).
3. View the full change history for a specific data object — displayed as a dialog with a table of: date, description, uploaded-by name.
4. Description text is shown in the viewer's current language via the translation system.

---

## FLOWS

### 1. Event Recording
A service operation completes a mutation (e.g. a data import finishes) → `CreateActivityLogEntryAsync(type, objectId, translationKey, params, userId)` is called → if no ActivityLog parent exists for (type, objectId), one is created → an ActivityLogEntry child row is inserted → the event is now part of the object's history.

### 2. Viewing History
Admin navigates to a data object (e.g. an FTP import file) → clicks "Activity log" → a dialog opens → `GetActivityLogsAsync(type, objectId)` called → all entries for that object returned → table displays: date, translated description, username.

---

## RULES

1. ActivityLogType is a bounded four-value enum (Broadcast, SubscriptionsImport, PositiveListsImport, StandardReceiversImport). Adding a new tracked type requires a code change.
2. One ActivityLog parent per (type, objectId). Multiple events for the same object simply add more child entries.
3. The description is stored as a translation key, never as a pre-translated string. The viewer sees it in their own language.
4. All tracked objects belong to customer-owned data — this is not a system-level audit log but a customer-data-change log.
5. `maxRecordsToReturn` is optional — callers can limit how many entries are returned for performance in high-volume objects.

---

## EDGE CASES

1. If `CreateActivityLogEntry` is called for a (type, objectId) pair that already has an ActivityLog parent, the parent is reused — no duplicate parent rows.
2. The `descriptionTranslationParms` are stored as a JSON string and parsed at display time via `biJsonParser` pipe — if the params are malformed JSON, the translation will display without token replacement.
3. The activity log is a shared dialog component used across multiple features — it is not a standalone page.

---

## GAPS

1. **No deletion** — there is no mechanism to delete or purge activity log entries. Logs accumulate indefinitely for the lifetime of the data object.
2. **Limited object types** — only four types are tracked. Many other mutable data objects (e.g. profile changes, user changes, template edits) have no activity trail in this domain.
