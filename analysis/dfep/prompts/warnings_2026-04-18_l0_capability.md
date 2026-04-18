# DFEP v3 — Capability Extraction Prompt
> Domain: **Warnings** | Source: **Level 0 (sms-service)** | Generated: 2026-04-18 02:32

---

## YOUR ROLE

You are analyzing source code facts to extract structured capabilities.

**STRICT RULES (non-negotiable):**
1. Use ONLY facts listed in the table below — NEVER invent
2. If evidence is insufficient → set `confidence` below 0.80 and note it
3. Do NOT suggest design or implementation
4. Do NOT reference code from memory — only from the table below
5. Each flow step MUST include `file:line` from the evidence table

---

## EXTRACTED FACTS (128 facts from Level 0 (sms-service))

| File:Line | Class.Method | DB Tables | SQL Ops | Filters/Scope |
|-----------|-------------|-----------|---------|---------------|
| `ServiceAlert.Core/Domain/Warnings/Warning.cs:34` | `Warning.AddFields` | — | — | — |
| `ServiceAlert.Core/Domain/Warnings/Warning.cs:39` | `Warning.AddRecipients` | — | — | — |
| `ServiceAlert.Services/Messages/WarningMessageSender.cs:67` | `WarningMessageSender.Send` | — | — | — |
| `ServiceAlert.Services/Messages/WarningMessageSender.cs:160` | `WarningMessageSender.SendGrouped` | — | SELECT | — |
| `ServiceAlert.Services/Messages/WarningMessageSender.cs:268` | `WarningMessageSender.SendNoRecipientEmailAsync` | — | SELECT | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:37` | `WarningService.ProcessWarningsAsync` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:56` | `WarningService.SendNoRecipientEmailsAsync` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:67` | `WarningService.CreateWarning` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:74` | `WarningService.GetWarningTypesForProfile` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:79` | `WarningService.GetWarningTemplates` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:84` | `WarningService.GetWarningTemplatesByCustomer` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:90` | `WarningService.GetWarningTemplate` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:95` | `WarningService.GetWarningTemplate` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:100` | `WarningService.CreateWarningTemplate` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:116` | `WarningService.UpdateWarningTemplate` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:132` | `WarningService.DeleteWarningTemplate` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:147` | `WarningService.GetWarningProfileSettings` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:154` | `WarningService.UpdateWarningProfileSettings` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:159` | `WarningService.CreateWarningProfileSettings` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:168` | `WarningService.GetWarningsByProfile` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:173` | `WarningService.GetWarningTypes` | — | — | — |
| `ServiceAlert.Services/Warnings/WarningService.cs:178` | `WarningService.WarningsStatus4Alarm` | — | — | — |
| `ServiceAlert.Services/Warnings/Dto/WarningProfileSettingsDto.cs:27` | `WarningProfileSettingsDto.ToDbEntity` | — | — | — |
| `ServiceAlert.Services/Warnings/InjectionPoints/Dto/WarningMessageDto.cs:21` | `WarningMessageDto.AddRecipients` | — | — | — |
| `ServiceAlert.Services/Warnings/InjectionPoints/Dto/WarningMessageDto.cs:25` | `WarningMessageDto.AddFields` | — | — | — |
| `ServiceAlert.Services/Warnings/InjectionPoints/Dto/WarningNoRecipientDto.cs:17` | `WarningNoRecipientDto.AddFields` | — | — | — |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:18` | `WarningRepository.CreateWarning` | Warnings, top | EXECUTE, UPDATE | Status = @postponedAgainStatus | Status = @postponedStatus |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:43` | `WarningRepository.ResetPostponedWarnings` | Warnings, top | EXECUTE, UPDATE, SELECT | Status = @postponedAgainStatus | Status = @postponedStatus |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:55` | `WarningRepository.UpdateAndFetchPostponedWarnings` | top, Warnings, WarningFields | UPDATE, SELECT | Status = @postponedStatus |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:75` | `WarningRepository.UpdateAndFetchUnprocessedWarnings` | Warnings, top, WarningFields | SELECT, UPDATE | — |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:110` | `WarningRepository.EnrichWarnings` | WarningFields, WarningRecipients, Warnings | SELECT, UPDATE | Status = @noRecipientsStatus | ProfileId = @ProfileId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:127` | `WarningRepository.UpdateAndFetchNoRecipientWarnings` | Warnings, WarningTypes, ProfileRoles | UPDATE, SELECT | Status = @noRecipientsStatus | ProfileId = @ProfileId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:149` | `WarningRepository.UpdateWarning` | Warnings, WarningTypes, ProfileRoles | SELECT | ProfileId = @ProfileId | WarningTypeId = @WarningTypeId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:159` | `WarningRepository.WarningExists` | Warnings, WarningTypes, ProfileRoles | SELECT | ProfileId = @ProfileId | WarningTypeId = @WarningTypeId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:169` | `WarningRepository.GetWarningTypes` | WarningTypes, ProfileRoles, ProfileRoleMappings | SELECT | pr.Name = @ProfileRoleName | ProfileId = @ProfileId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:176` | `WarningRepository.GetWarningTypes` | WarningTypes, ProfileRoles, ProfileRoleMappings | SELECT | pr.Name = @ProfileRoleName | ProfileId = @ProfileId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:188` | `WarningRepository.GetWarningTemplates` | WarningTemplates, WarningTypes, ProfileRoles | SELECT | wt.ProfileId = @profileId | pr.Name = @profileRoleName |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:204` | `WarningRepository.GetWarningTemplatesByCustomer` | WarningTemplates, WarningTypes, Profiles | SELECT | p.CustomerId = @customerId | wt.Id = @id |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:215` | `WarningRepository.GetWarningTemplate` | WarningTemplates, WarningTypes, WarningProfileSettings | SELECT | wt.Id = @id | ProfileId = @profileId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:225` | `WarningRepository.GetWarningTemplate` | WarningTemplates, WarningTypes, WarningProfileSettings | SELECT | ProfileId = @profileId | TypeId = @warningTypeId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:231` | `WarningRepository.InsertWarningTemplate` | WarningProfileSettings, Warnings | SELECT | ProfileId = @profileId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:237` | `WarningRepository.UpdateWarningTemplate` | WarningProfileSettings, Warnings | SELECT | ProfileId = @profileId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:248` | `WarningRepository.DeleteWarningTemplate` | WarningProfileSettings, Warnings | SELECT | ProfileId = @profileId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:262` | `WarningRepository.GetWarningProfileSettings` | WarningProfileSettings, Warnings | SELECT | ProfileId = @profileId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:268` | `WarningRepository.UpdateProfileWarningSettings` | Warnings | SELECT | ProfileId = @profileId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:274` | `WarningRepository.CreateProfileWarningSettings` | Warnings | SELECT | ProfileId = @profileId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:280` | `WarningRepository.GetWarningsByProfile` | Warnings | SELECT | ProfileId = @profileId |
| `ServiceAlert.Services/Warnings/Repository/WarningRepository.cs:286` | `WarningRepository.GetOldWarningsInStatusProgress` | Warnings | SELECT | — |
| `ServiceAlert.Services/Warnings/Workload/NoRecipientWarningWorkloadLoader.cs:24` | `NoRecipientWarningWorkloadLoader.GetWorkloadChunk` | — | SELECT | — |
| `ServiceAlert.Services/Warnings/Workload/NoRecipientWarningWorkloadProcessor.cs:27` | `NoRecipientWarningWorkloadProcessor.ProcessWorkAsync` | — | SELECT | — |
| `ServiceAlert.Services/Warnings/Workload/PostponedWarningProcessor.cs:19` | `PostponedWarningProcessor.ProcessWorkAsync` | — | — | — |
| `ServiceAlert.Services/Warnings/Workload/PostponedWarningWorkloadLoader.cs:21` | `PostponedWarningWorkloadLoader.GetWorkloadChunk` | — | SELECT | — |
| `ServiceAlert.Services/Warnings/Workload/WarningStatus.cs:30` | `WarningStatus.GetFailedStatus` | — | — | — |
| `ServiceAlert.Services/Warnings/Workload/WarningStatus.cs:35` | `WarningStatus.GetWarningStatusTranslationKeyDictionary` | — | — | — |
| `ServiceAlert.Services/Warnings/Workload/WarningStatusWriter.cs:17` | `WarningStatusWriter.SetStatuses` | — | — | — |
| `ServiceAlert.Services/Warnings/Workload/WarningWorkloadLoader.cs:22` | `WarningWorkloadLoader.GetWorkloadChunk` | — | SELECT | — |
| `ServiceAlert.Services/Warnings/Workload/WarningWorkloadProcessor.cs:33` | `WarningWorkloadProcessor.ShouldSendToAddress` | — | SELECT | — |
| `ServiceAlert.Services/Warnings/Workload/WarningWorkloadProcessor.cs:34` | `WarningWorkloadProcessor.ShouldSendToOwner` | — | SELECT | — |
| `ServiceAlert.Services/Warnings/Workload/WarningWorkloadProcessor.cs:35` | `WarningWorkloadProcessor.ShouldSendToIncludedNumber` | — | SELECT | — |
| `ServiceAlert.Services/Warnings/Workload/WarningWorkloadProcessor.cs:37` | `WarningWorkloadProcessor.ProcessWorkAsync` | — | SELECT | — |
| `ServiceAlert.Services/Warnings/Workload/WarningWorkloadProcessor.cs:57` | `WarningWorkloadProcessor.ProcessWarning` | — | SELECT | — |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningRepository.cs:22` | `WeatherWarningRepository.GetWeatherWarningTypes` | WeatherWarningTypes, WeatherWarningTemplates | SELECT, INSERT, UPDATE, DELETE | CustomerId = @CustomerId | Id = @Id |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningRepository.cs:29` | `WeatherWarningRepository.GetWeatherWarningTemplates` | WeatherWarningTemplates | SELECT, INSERT, UPDATE, DELETE | CustomerId = @CustomerId | Id = @Id |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningRepository.cs:37` | `WeatherWarningRepository.GetWeatherWarningTemplate` | WeatherWarningTemplates | SELECT, INSERT, UPDATE, DELETE | Id = @Id |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningRepository.cs:47` | `WeatherWarningRepository.CreateWeatherWarningTemplate` | — | INSERT, UPDATE, DELETE | — |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningRepository.cs:55` | `WeatherWarningRepository.UpdateWeatherWarningTemplate` | WeatherWarnings | UPDATE, DELETE, INSERT, SELECT | WarningTypeNumber = @TypeNumber | CreatedUtc = @Created |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningRepository.cs:66` | `WeatherWarningRepository.DeleteWeatherWarningTemplate` | WeatherWarnings | DELETE, INSERT, SELECT | WarningTypeNumber = @TypeNumber | CreatedUtc = @Created |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningRepository.cs:77` | `WeatherWarningRepository.CreateWeatherWarning` | WeatherWarnings | INSERT, SELECT | WarningTypeNumber = @TypeNumber | CreatedUtc = @Created |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningRepository.cs:110` | `WeatherWarningRepository.WeatherWarningExists` | WeatherWarnings, WeatherWarningZips, WeatherWarningTypes | SELECT | WarningTypeNumber = @TypeNumber | CreatedUtc = @Created |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningRepository.cs:119` | `WeatherWarningRepository.CreateWeatherWarningZips` | WeatherWarnings, WeatherWarningZips, WeatherWarningTypes | SELECT | w.ExecuteStatus = @Status |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningRepository.cs:124` | `WeatherWarningRepository.GetWeatherWarningMessages` | WeatherWarnings, WeatherWarningZips, WeatherWarningTypes | SELECT | w.ExecuteStatus = @Status |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningRepository.cs:198` | `WeatherWarningRepository.UpdateWarningStatus` | WeatherWarnings | UPDATE, EXECUTE, SELECT | ExecuteStatus = @statusCurent | Id = @warningId |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningRepository.cs:208` | `WeatherWarningRepository.UpdateWarningStatus` | WeatherWarnings | UPDATE, EXECUTE | Id = @warningId | ExecuteStatus = @statusCurent |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningService.cs:59` | `WeatherWarningService.GetWeatherWarningTypes` | — | — | — |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningService.cs:63` | `WeatherWarningService.GetWeatherWarningTemplates` | — | — | — |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningService.cs:72` | `WeatherWarningService.CreateWeatherWarningTemplate` | — | — | — |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningService.cs:78` | `WeatherWarningService.GetWeatherWarningTemplate` | — | — | — |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningService.cs:83` | `WeatherWarningService.IsMessageTemplateUsedForWeatherWarnings` | — | — | — |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningService.cs:88` | `WeatherWarningService.UpdateWeatherWarningTemplate` | — | — | — |
| `ServiceAlert.Services/WeatherWarnings/WeatherWarningService.cs:93` | `WeatherWarningService.DeleteWeatherWarningTemplate` | — | — | — |

---

## CAPABILITY GROUPING HINTS

Use these known capability clusters as starting point. Add/omit based on actual facts:

_No predefined grouping hints for this domain._

---

## REQUIRED OUTPUT FORMAT

Return ONLY valid JSON — no markdown wrapping, no explanation text:

```json
{
  "domain": "Warnings",
  "source": "Level 0 (sms-service)",
  "capabilities": [
    {
      "id": "list_templates",
      "intent": "Short action-oriented description of WHAT this capability does",
      "business_value": "Why this matters to the end user or business",
      "flow": [
        "Step 1: description (evidence: file:line)",
        "Step 2: description (evidence: file:line)"
      ],
      "constraints": [
        "CustomerId isolation required",
        "ProfileId from JWT — immutable"
      ],
      "rules": [
        "Always filter by CustomerId",
        "Profile access is additive (M:M)"
      ],
      "evidence": [
        "path/to/file.cs:121",
        "path/to/file.sql:1"
      ],
      "confidence": 0.95
    }
  ],
  "unknown_hints": [
    "list_capability_ids_that_had_NO_evidence_in_facts"
  ]
}
```

**confidence scale:**
- `>= 0.90` — strong evidence, multiple corroborating facts
- `0.80–0.89` — good evidence, minor gaps
- `< 0.80` — insufficient evidence → mark as UNKNOWN in `unknown_hints`, still include entry with low confidence

---

## STOP CONDITIONS

- If > 20% of capabilities would be UNKNOWN: write to `unknown_hints` and report in output
- Do NOT hallucinate capabilities. An empty capability list is valid output.
