# DFEP v3 — Capability Extraction Prompt
> Domain: **Templates** | Source: **Level 0 (sms-service)** | Generated: 2026-04-18 00:39

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

## EXTRACTED FACTS (132 facts from Level 0 (sms-service))

| File:Line | Class.Method | DB Tables | SQL Ops | Filters/Scope |
|-----------|-------------|-----------|---------|---------------|
| `ServiceAlert.Api/Controllers/TemplateController.cs:33` | `TemplateController.GetSmsTemplates` | — | SELECT | — |
| `ServiceAlert.Contracts/Models/Templates/TemplateQuickResponseSetupDto.cs:35` | `TemplateQuickResponseSetupDto.ToUpdateCommand` | — | SELECT | — |
| `ServiceAlert.Core/Domain/Mails/EmailTemplate.cs:33` | `EmailTemplate.MergeMasterMainContent` | — | — | — |
| `ServiceAlert.Core/Domain/Mails/EmailTemplate.cs:43` | `EmailTemplate.MergeSupportCaseTextAndBodyHtmlFields` | — | — | — |
| `ServiceAlert.Core/Domain/Templates/ReadModels/TemplateAttachmentReadModel.cs:15` | `TemplateAttachmentReadModel.ToDomainModel` | — | — | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:31` | `EmailTemplateService.GetTemplateByNameEnum` | master | — | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:65` | `EmailTemplateService.GetMasterTemplate` | — | — | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:78` | `EmailTemplateService.EmailFromFormatted` | — | INSERT, UPDATE | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:90` | `EmailTemplateService.MergeEmailFields` | — | INSERT, UPDATE, DELETE | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:101` | `EmailTemplateService.MergeEmailFields` | — | INSERT, UPDATE, DELETE | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:115` | `EmailTemplateService.RemoveEmailTags` | — | INSERT, UPDATE, DELETE | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:126` | `EmailTemplateService.GetAllTemplates` | — | INSERT, UPDATE, DELETE | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:131` | `EmailTemplateService.Insert` | — | INSERT, UPDATE, DELETE | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:136` | `EmailTemplateService.Update` | — | UPDATE, DELETE | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:141` | `EmailTemplateService.Delete` | — | DELETE, UPDATE | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:146` | `EmailTemplateService.GetTemplateHtmlByNameEnum` | — | UPDATE | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:165` | `EmailTemplateService.SaveToFile` | — | UPDATE | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:172` | `EmailTemplateService.SaveAllToDisc` | — | UPDATE | — |
| `ServiceAlert.Services/Mails/EmailTemplateService.cs:180` | `EmailTemplateService.UpdateTemplatesFromEmbeddedResources` | — | UPDATE | — |
| `ServiceAlert.Services/Mails/EmailContentGenerator/BroadcastReceiptEmailContentGenerators/BroadcastReceiptEmailTemplateTagsRemover/AddressBroadcastReceiptEmailTemplateTagsRemover.cs:36` | `AddressBroadcastReceiptEmailTemplateTagsRemover.RemoveTagsFromEmailBody` | — | — | — |
| `ServiceAlert.Services/Mails/EmailContentGenerator/BroadcastReceiptEmailContentGenerators/BroadcastReceiptEmailTemplateTagsRemover/ByStandardReceiversBroadcastReceiptEmailTemplateTagsRemover.cs:17` | `ByStandardReceiversBroadcastReceiptEmailTemplateTagsRemover.RemoveTagsFromEmailBody` | — | — | — |
| `ServiceAlert.Services/Mails/Repository/EmailTemplateRepository.cs:17` | `EmailTemplateRepository.Insert` | EmailTemplates | INSERT, UPDATE, DELETE, SELECT | LanguageId = @LanguageId | Name = @TemplateName |
| `ServiceAlert.Services/Mails/Repository/EmailTemplateRepository.cs:22` | `EmailTemplateRepository.Update` | EmailTemplates | UPDATE, DELETE, SELECT | LanguageId = @LanguageId | Name = @TemplateName |
| `ServiceAlert.Services/Mails/Repository/EmailTemplateRepository.cs:27` | `EmailTemplateRepository.Delete` | EmailTemplates | DELETE, SELECT | LanguageId = @LanguageId | Name = @TemplateName |
| `ServiceAlert.Services/Mails/Repository/EmailTemplateRepository.cs:32` | `EmailTemplateRepository.GetAllTemplates` | EmailTemplates | SELECT | LanguageId = @LanguageId | Name = @TemplateName |
| `ServiceAlert.Services/Mails/Repository/EmailTemplateRepository.cs:37` | `EmailTemplateRepository.GetTemplateByNameEnum` | EmailTemplates | SELECT | LanguageId = @LanguageId | Name = @TemplateName |
| `ServiceAlert.Services/Templates/TemplateService.cs:32` | `TemplateService.GetTemplatesForSmsAndEmail` | — | DELETE | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:40` | `TemplateService.GetTemplates` | — | DELETE | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:45` | `TemplateService.GetTemplateById` | — | DELETE | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:50` | `TemplateService.InsertAsync` | — | DELETE | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:55` | `TemplateService.UpdateAsync` | — | DELETE | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:80` | `TemplateService.Delete` | — | DELETE, SELECT | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:95` | `TemplateService.InsertTemplateResponseOptions` | — | SELECT | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:100` | `TemplateService.DeleteTemplateResponseOptionsAsync` | — | SELECT | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:105` | `TemplateService.UpdateTemplateResponseOptionsAsync` | — | SELECT | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:117` | `TemplateService.GetResponseOptionsByTemplateIdAsync` | — | SELECT | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:122` | `TemplateService.GetQuickReponseSetupAsync` | — | SELECT | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:127` | `TemplateService.SetupQuickResponseAsync` | — | SELECT | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:136` | `TemplateService.UpdateQuickResponseSetupAsync` | — | SELECT | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:150` | `TemplateService.DeleteteQuickResponseSetupAsync` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:160` | `TemplateService.InsertSystemDefinedDynamicMergefields` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:213` | `TemplateService.GetDynamicMergefieldString` | — | MERGE | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:229` | `TemplateService.GetDynamicMergefields` | text, the, in | MERGE, UPDATE | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:242` | `TemplateService.InsertDynamicMergefield` | text, the, in | MERGE, UPDATE | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:255` | `TemplateService.CheckMergefieldUsageAndProcessTemplates` | text, the, in | MERGE, UPDATE | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:417` | `TemplateService.UpdateDynamicMergefield` | those, every | UPDATE | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:428` | `TemplateService.DeleteDynamicMergefield` | every | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:445` | `TemplateService.ExtractDynamicMergefields` | every | MERGE, SELECT | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:598` | `TemplateService.GetTemplateProfileMappings` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:603` | `TemplateService.LinkProfileToTemplates` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:608` | `TemplateService.UnlinkProfileFromTemplates` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:613` | `TemplateService.LinkTemplateToProfiles` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:618` | `TemplateService.UnlinkTemplateFromProfiles` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:626` | `TemplateService.GetSmsExample` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:631` | `TemplateService.GetSmsExamples` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:636` | `TemplateService.InsertSmsExample` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:641` | `TemplateService.UpdateSmsExample` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:646` | `TemplateService.DeleteSmsExample` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:652` | `TemplateService.GetEboksExample` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:657` | `TemplateService.GetEboksExamples` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:662` | `TemplateService.InsertEboksExample` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:667` | `TemplateService.UpdateEboksExample` | — | — | — |
| `ServiceAlert.Services/Templates/TemplateService.cs:672` | `TemplateService.DeleteEboksExample` | — | — | — |
| `ServiceAlert.Services/Templates/Commands/TemplateResponseOptionUpdateCommand.cs:14` | `TemplateResponseOptionUpdateCommand.ToEntity` | — | — | — |
| `ServiceAlert.Services/Templates/Commands/TemplateResponseSettingsUpdateCommand.cs:16` | `TemplateResponseSettingsUpdateCommand.ToEntity` | — | — | — |
| `ServiceAlert.Services/Templates/Dto/TemplateAttachmentDto.cs:33` | `TemplateAttachmentDto.ToDomainModel` | — | — | — |
| `ServiceAlert.Services/Templates/Dto/TemplateMergeFieldOptionsDto.cs:27` | `TemplateMergeFieldOptionsDto.AddSelectItems` | — | — | — |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:29` | `TemplateRepository.FillTemplateParts` | TemplateBenchmarks, TemplateSms, TemplateEmails | SELECT | tbm.Id = @ID | tsms.Id = @ID |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:60` | `TemplateRepository.GetBenchmarkTemplatePart` | TemplateBenchmarks, TemplateSms, TemplateEmails | SELECT | tbm.Id = @ID | tsms.Id = @ID |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:68` | `TemplateRepository.GetSmsTemplatePart` | TemplateSms, TemplateEmails, TemplateVoice | SELECT | tsms.Id = @ID | tEmail.Id = @ID |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:74` | `TemplateRepository.GetEmailTemplatePart` | TemplateEmails, TemplateVoice, TemplateWebs | SELECT | tEmail.Id = @ID | tVoice.Id = @ID |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:80` | `TemplateRepository.GetVoiceTemplatePart` | TemplateVoice, TemplateWebs, TemplateInternals | SELECT | tVoice.Id = @ID | tw.Id = @ID |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:86` | `TemplateRepository.GetWebTemplatePart` | TemplateWebs, TemplateInternals, TemplateFacebooks | SELECT | tw.Id = @ID | tint.Id = @ID |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:92` | `TemplateRepository.GetInternalTemplatePart` | TemplateInternals, TemplateFacebooks, TemplateTwitters | SELECT | tint.Id = @ID | tfb.Id = @ID |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:98` | `TemplateRepository.GetFacebookTemplatePart` | TemplateFacebooks, TemplateTwitters, TemplateEboks | SELECT | tfb.Id = @ID | tt.Id = @ID |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:104` | `TemplateRepository.GetTwitterTemplatePart` | TemplateTwitters, TemplateEboks, Templates | SELECT | tt.Id = @ID | te.Id = @ID |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:110` | `TemplateRepository.GetEboksTemplatePart` | TemplateEboks, Templates, TemplateProfileMappings | SELECT | te.Id = @ID | t.CustomerId = @customerId |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:120` | `TemplateRepository.GetTemplatesForSmsAndEmail` | Templates, TemplateProfileMappings, TemplateSms | SELECT | t.CustomerId = @customerId | tpm.ProfileId = @profileId |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:145` | `TemplateRepository.GetTemplates` | Templates, TemplateProfileMappings, TemplateAttachments | SELECT | tpm.ProfileId = @profileId | t.Id = @templateId |
| `ServiceAlert.Services/Templates/Repository/TemplateRepository.cs:182` | `TemplateRepository.GetTemplateById` | Templates, TemplateAttachments, ProfileStorageFiles | SELECT | t.Id = @templateId |

---

## CAPABILITY GROUPING HINTS

Use these known capability clusters as starting point. Add/omit based on actual facts:

- **list_templates** — look for: `GetTemplate`, `ListTemplate`, `GetForProfile`, `GetAll`
- **get_template_by_id** — look for: `GetById`, `GetTemplateById`, `FindTemplate`, `GetSingle`
- **create_template** — look for: `Create`, `Insert`, `Add`, `NewTemplate`
- **update_template** — look for: `Update`, `Edit`, `Modify`, `Save`
- **delete_template** — look for: `Delete`, `Remove`
- **resolve_content** — look for: `ResolveContent`, `MergeSms`, `MergeField`, `Substitute`
- **template_profile_access** — look for: `ProfileMapping`, `ProfileAccess`, `GetForProfile`, `TemplateProfileMapping`

---

## REQUIRED OUTPUT FORMAT

Return ONLY valid JSON — no markdown wrapping, no explanation text:

```json
{
  "domain": "Templates",
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
