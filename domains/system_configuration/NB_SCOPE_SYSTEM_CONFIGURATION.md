# NB_SCOPE — system_configuration
**Dato:** 2026-04-19 (updated: FINAL FLOW VALIDATION)
**Source:** 3 verified flows (030_flows.json) + 6 verified rules (070_rules.json)

---

## FLOW → IMPLEMENTATION MAP

---

### Flow 1: LazySettingResolutionFlow

```
flow:       LazySettingResolutionFlow
endpoint:   NONE — internal service behavior (no API endpoint)
handler:    N/A — consumed by other handlers that need a setting value
service:    IApplicationSettingService.Get(AppSetting settingType, string defaultSetting)
sql:        GetSetting.sql  (SELECT WHERE ApplicationSettingTypeId = @SettingType)
            UpsertSetting.sql (INSERT if not exists — triggered by Get internally)
validation: defaultSetting must not be null/empty when auto-creation is desired
```

**CreateDefault location:** INSIDE `Get()` service method (ApplicationSettingService.cs line 43).
Not in handler. Handler calls `Get()` — service handles creation internally.
This is the verified sms-service behavior — not implicit design, it is the design.

---

### Flow 2: AdminSettingEditFlow

```
flow:       AdminSettingEditFlow
endpoint:   GET /admin/settings          → GetAllSettingsQuery
            PUT /admin/settings          → UpdateSettingCommand
handler:    GetAllSettingsQuery          → returns all settings (uncached)
            UpdateSettingCommand         → upsert + cache clear
service:    IApplicationSettingService.GetUncached()  (line 25-35)
            IApplicationSettingService.Save()          (line 57-79)
sql:        GetAllSettings.sql  (SELECT * FROM dbo.ApplicationSettings ORDER BY Id DESC)
            UpsertSetting.sql   (check existing → INSERT or UPDATE)
validation: - AppSetting enum IsDefined check on incoming SettingType
            - GET must bypass cache (direct DB — GetUncached rule)
            - Save must call RemoveByPattern("Sms.applicationsettings")
            - Setting value: no constraint in sms-service (free string)
```

---

### Flow 3: FileUploadValidationFlow

```
flow:       FileUploadValidationFlow
endpoint:   NONE in system_configuration — provider side only
            Consumer: profile upload endpoint in profile_management domain
handler:    N/A in this domain — handler lives in profile_management
service:    IFileTypeValidationService.GetFileTypeId(string extension) → int
sql:        NONE — code-defined extension-to-ID mapping (no DB lookup)
validation: caller MUST return BadRequest if GetFileTypeId() returns 0
```

**Who calls it:** In sms-service: `ProfileController.cs` line 221 calls
`_profileStorageService.FileTypeIdFromExtension()` directly.
In green-ai: system_configuration provides `IFileTypeValidationService`;
profile_management upload handler injects and calls it.
Not exposed as HTTP endpoint — internal domain service boundary.

---

## SQL FILES

| File | Operation | Table |
|------|-----------|-------|
| `GetAllSettings.sql` | SELECT * ORDER BY Id DESC | dbo.ApplicationSettings |
| `GetSetting.sql` | SELECT WHERE ApplicationSettingTypeId = @SettingType | dbo.ApplicationSettings |
| `UpsertSetting.sql` | check + INSERT or UPDATE | dbo.ApplicationSettings |

---

## DB — dbo.ApplicationSettings

| Column | Type | Rule |
|--------|------|------|
| `Id` | int PK | auto |
| `ApplicationSettingTypeId` | int | = AppSetting enum value (e.g. 184) |
| `ApplicationSettingName` | string | = enum name, set on Save |
| `Setting` | string | free text |
| `DateLastUpdatedUtc` | datetime | UTC, set on Save |

---

## OUT OF SCOPE

- Free-text keys (enum-only)
- New AppSetting enum values
- Any endpoint not in the 3 flows above
