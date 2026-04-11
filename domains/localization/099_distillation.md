# Domain Distillation: localization

**STATUS:** APPROVED_BASELINE  
**Completeness source:** 0.92 (Layer 1) + UI verification  
**UI verified from:** `translation-management.component.html`, `translation-management.component.ts`  
**Date:** 2026-04-11  

---

## PURPOSE

Localization is the system that makes all user-facing text configurable per language without code changes. Every label, error message, date format pattern, and status description used anywhere in the system — both in the web UI and in server-generated notifications — is stored in a database table and served from a cache. The superAdmin has a full CRUD interface to add, edit, delete, and export these translation strings. A public endpoint serves the complete translation set to the Angular frontend at startup.

---

## CORE CONCEPTS

1. **LocaleStringResource** — a single row with three fields: a language, a key name (ResourceName), and a value (ResourceValue). This is the atomic unit of the entire translation system.

2. **ResourceName** — the key that identifies a piece of text across languages. Always uppercase in cache lookups. By convention names are dot-separated (e.g. `shared.Save`, `errorMessages.MustBeFilled`). The same ResourceName exists exactly once per language.

3. **Language** — one of five active languages: Danish (1), Swedish (2), English (3), Finnish (4), Norwegian (5). German (6) exists in the database but is incomplete and not exposed in the admin UI.

4. **Missing Translation placeholder** — when a new ResourceName is created for one language, the system automatically inserts a row for every other active language with the value `Missing Translation`. This ensures the ResourceName always exists for all languages. A query (`GetIncomplete`) surfaces all ResourceNames that still have any `Missing Translation` row.

5. **Read-through cache** — all translation strings for a language are loaded into memory as a block. Cache is keyed per language per key (`sms.lsr.{languageId}-{UPPER(key)}`). The entire localization cache is cleared whenever any string is saved or inserted.

6. **Fail-open lookup** — if a ResourceName is not found in the database, the lookup returns the ResourceName itself (the key string) rather than an empty string. This makes missing translations visible in the UI without causing a runtime crash.

7. **Localized date formats** — date and datetime format patterns are stored as LocaleStringResources, not hardcoded. This allows each language to have its own date display convention without code changes.

8. **CountryId = LanguageId** — in this system, the numeric country ID and language ID use the same range (1–6) with the same mapping. They are used interchangeably in code.

---

## CAPABILITIES

1. Serve the complete set of translation strings for a language to the Angular frontend at application bootstrap (public endpoint, no login required).
2. Translate any text key to a language — server-side, used in notification generation and error messages.
3. Translate a text key with dynamic token replacement (e.g. insert a count or name into a template string).
4. Load all translation strings for a language in bulk for batch processing.
5. Format dates and datetimes in the locale-appropriate format using stored format patterns.
6. Detect incomplete translations — list all ResourceNames where any language version still shows `Missing Translation`.
7. Search and filter all translations with pagination: filter by key name, by value text, by language, or show only incomplete rows.
8. Add a new translation key with a value for one language — all other languages receive `Missing Translation` automatically.
9. Edit an existing translation (key name, value, or language).
10. Delete a single translation row (the row for one specific language — does NOT cascade to other languages).
11. Export all translations (or a single language) as an Excel file.
12. Bulk import translations from a JSON file (batch operation).

---

## FLOWS

### 1. Frontend Translation Bootstrap
Angular application loads → `BiHttpTranslateLoader.getTranslation()` maps the user's language code to a language ID → calls `GET /api/Common/GetResourcesJson?languageId=X` → server returns all translation strings as a flat JSON object (all keys uppercased) → Angular registers the dictionary → every `| translate` pipe in the UI resolves from this dictionary.

### 2. Server-Side Translation Lookup
A server-side process needs a translated string (e.g. to put in an SMS message) → `GetLocalizedResource(resourceKey, languageId)` called → cache check for `sms.lsr.{languageId}-{UPPER(key)}` → if hit: return cached value → if miss: load all strings for that language from DB into cache, return the value → if key not found: return the key itself.

### 3. Admin Creates a New Translation Key
SuperAdmin clicks Add in the translation table → enters ResourceName and value, selects a language → `InsertLocalizedResource` called → DB insert for the provided language → for every other active language, a `Missing Translation` row is automatically inserted → full localization cache cleared → new key is now visible in the table.

### 4. Admin Edits a Translation
SuperAdmin finds a row, clicks edit → modifies the value → `UpdateLocalizedResource` called with the row ID → DB row updated → full cache cleared → value is live on next request.

---

## RULES

1. Every ResourceName must exist for every active language. This is enforced at the application level by auto-inserting `Missing Translation` rows on creation. The database does not enforce it by constraint — a direct DB insert could violate it.
2. `(LanguageId, ResourceName)` has a unique database index — a key can only appear once per language. No duplicates possible.
3. Missing key lookups return the key string itself, never null or empty string. This is intentional — it makes missing translations visible without breaking the UI.
4. The full localization cache is invalidated on any write (insert or update) — not per-key, but all at once.
5. `GetUncached` is not available for translations — all reads go through the cache. The admin UI therefore reads from the same cache it writes to (stale until invalidated).
6. Deleting a single translation row leaves the `Missing Translation` rows for other languages in place — orphan rows are possible after deletion.
7. The user's active language is resolved from the database (not from the JWT) on every request — changing the language setting takes effect without re-login.
8. CountryId and LanguageId share the same numeric mapping. They are semantically equivalent in this codebase.
9. German (Id=6) is partially implemented on the server side but is absent from the frontend language list and the admin UI's language selector — German translations cannot be managed through the UI.

---

## EDGE CASES

1. **Batch import cache miss** — importing translations via the batch job does NOT clear the in-memory cache. Newly imported strings will not appear in the live application until the cache expires naturally or the application restarts. This is a known open gap.
2. **Token replacement double-substitution** — if a translation value itself contains a token-shaped pattern (e.g. `{name}`), and the caller passes a token named `name` that contains `{someOtherKey}`, double replacement occurs. Not observed as a real bug but is a latent risk.
3. **German language gap** — German exists in the DB but the frontend treats only 5 languages as valid. German users (if any) would fall back to English or see key strings.
4. **Delete leaves orphans** — deleting a row for one language does not clean up the `Missing Translation` rows for other languages referencing the same ResourceName. The `GetIncomplete` query would continue returning that ResourceName as incomplete.
5. **Countries table is dead** — the `dbo.Countries` table exists and has data, but is never read at runtime. All country/culture mappings are hardcoded in `CountryConstants.cs`. Adding a new country requires both a code change and a database migration — no single source of truth.

---

## INTEGRATIONS

1. **Angular frontend** — the public `GetResourcesJson` endpoint is the startup contract. The frontend calls this before rendering anything that requires translated text.
2. **Batch job** — `import_translations` batch action can bulk-load a JSON file of translations. Used for seeding or migrating translations across environments.
3. **Notification generation** — server-side translation service is called inside message assembly pipelines to localise status descriptions, datetime formats, and group names into the recipient's language.

---

## GAPS

1. **Batch import does not clear cache** (GAP_002 — open) — translations imported via batch are not live until cache expires or app restarts.
2. **Countries table is unused** (GAP_003 — open) — `dbo.Countries` is never queried; all country logic is hardcoded.
3. **German language incomplete** (GAP_004 — open) — German exists in DB and partial backend support exists, but the admin UI does not expose it and the frontend has no German language code mapping.
4. **Frontend cache update bug** (GAP_005 — open) — the frontend `tap()` handler that updates the client-side translation cache after an edit hardcodes language codes `'da'`/`'se'` instead of dynamically looking up the language code by ID.
