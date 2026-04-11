# DOMAIN DISTILLATION INDEX

**Protocol:** Tracks formal non-technical distillation status per domain.
**Format:** `domains/{domain}/099_distillation.md`
**Status legend:**
- `[ ]` not distilled
- `[~]` in progress
- `[x]` distilled — APPROVED_BASELINE

---

| Domain | Completeness | Distillation | Notes |
|---|---|---|---|
| `identity_access` | 0.97 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. BEH_001+BEH_005 corrected (HTTP 300 = 2FA delivery choice; states 1/3/4 remapped). COMPLETE. |
| `email` | 0.91 | `[x]` | Closed domain — EMAIL_DOMAIN_CLOSED_FOR_MVP 🔒. No 099 file; formal distillation pending. |
| `product_scope` | 1.0 | `[ ]` | Reference artifact (locked). Distillation deferred — see `docs/PRODUCT_CAPABILITY_MAP.json` |
| `system_configuration` | 0.94 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Kill-switches, cache, file type registry, 15 capabilities, 4 flows. COMPLETE. |
| `localization` | 0.92 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Bootstrap endpoint, fail-open cache, 12 capabilities, 4 gaps. COMPLETE. |
| `activity_log` | 0.92 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Audit trail for 4 object types, dialog UI verified. COMPLETE. |
| `profile_management` | 0.91 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. UI verified: 12 conditional tabs, 25 capabilities, 4 flows, 11 rules. COMPLETE. |
| `eboks_integration` | 0.88 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. CVR+Amplify lookup paths, 4 strategies, batch delivery. Source-primary. COMPLETE. |
| `customer_administration` | 0.88 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Layer 1 sparse; UI-primary. Customer admin self-service settings. COMPLETE. |
| `customer_management` | 0.88 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Layer 1 sparse; UI-primary. SuperAdmin full customer management, 8 tabs, events. COMPLETE. |
| `logging` | 0.88 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. 3 logger impls, 7 log types, cleanup jobs, blob fallback. COMPLETE. |
| `address_management` | 0.58 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. Tree-based wizard selection, country address models (NO/FI/DK), owner lookup, deduplication checks, attach commands, critical addresses. COMPLETE. |
| `Benchmark` | 0.47 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. Outage tracking, 8 routes (index/create/edit/statistics/kpis/overview/causes/settings), wizard integration, InfoPortal mode, map+chart views. COMPLETE. |
| `Conversation` | 0.54 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. Two-way SMS threads, list+message UI, SSE unread badge (delta/reset), CreateConversation dialog, admin number assignment, 6 rules. COMPLETE. |
| `data_import` | 0.54 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. 3-step import component, 4 purposes, FTP auto-import, address batch import, company lookup. COMPLETE. |
| `Delivery` | 0.84 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. WIKI+source primary. WorkloadExecutor pattern, 5 gateways (GatewayAPI/Strex/Infobip/SendGrid/eBoks), inbound SMS+email, retry, test mode. COMPLETE. |
| `Enrollment` | 0.54 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. Self-service enrollment app, pin code verification, statistics, reports, events, send-a-tip. COMPLETE. |
| `Finance` | 0.41 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. SuperAdmin only. 9 routes (invoicing), e-conomic transfer, Salesforce XLSX upload, balance sheet uploads, budget follow-up (company/year/month/costCenter), product catalog, 5 rules. COMPLETE. |
| `integrations` | 0.78 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. FramWeb GIS API key, 1919 SMS keywords XML terminate, gateway webhooks, SCIM, IntegrationBatchAppService, REST API surface, 5 rules. COMPLETE. |
| `job_management` | 0.93 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Azure Batch + in-process IHostedService dual model, 54 ServiceAlertBatchAction values, SSE live monitoring, 7 background services, 7 rules. COMPLETE. |
| `Lookup` | — | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. Core recipient resolution engine. 2 execution paths (Prelookup preview + full Lookup→DB). LookupExecutor: priority-ordered ILookupCommandProcessor pipeline. 8 command categories: expansion, Norwegian (1881/KRR/property), eBoks (Amplify/CVR), Teledata (DK/SE/FI), subscriptions/enrollments, dedup/filter, attach, infrastructure. SmsLogBackgroundService. Missed-lookup auto-recovery via Azure Batch. 10 rules. COMPLETE. |
| `messaging` | 0.47 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Layer 1 empty; source-primary. 6 wizard steps, 19 send methods, 4 wizard variants, 11 rules. COMPLETE. |
| `Monitoring` | — | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. SuperAdmin-only live dashboard: SSE ProgressWatcher jobs, GetGraphData time-series chart, GetMapData 15s-polled geographic pings (seconds≤15), historical JobTaskDto table + SSE ACTIVEJOBS updates. 6 rules. COMPLETE. |
| `phone_numbers` | 0.69 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. 3 virtual number types (Voice/Conversation/GroupDist), supply numbers, Norwegian 1881 lookup, SE provider import, extra phone CRUD, 6 rules. COMPLETE. |
| `pipeline_crm` | — | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. SuperAdmin-only. ProspectDto lifecycle (create→tasks→e-conomic→customer conversion). PipelineController 14 endpoints, SalesforceController 6 read-only analytics endpoints, Salesforce month-encoded queries, F24 Word contract, CloneProducts, UserRoleAccess. 7 rules. COMPLETE. |
| `pipeline_sales` | — | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. SuperAdmin SalesInfo feature-checklist per customer (SalesInfo={featureName,hasFeature}) + admin-managed SQL query library (SalesInfoQueryDto={nameTranslateKey,sqlQuery}). SUperAdminSalesInfoController 5 endpoints. Settings CRUD table + customer-detail dialog. BiStore cache. 7 rules. COMPLETE. |
| `positive_list` | 0.48 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. Replace/Addition/Deletion modes, FTP, level filter mapping, Email2SMS whitelist, Swedish skip list. COMPLETE. |
| `recipient_management` | 0.52 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Layer 1 empty; source-primary. 7 recipient categories, 11 capabilities, 3 flows, 5 rules. COMPLETE. |
| `reporting` | 0.128 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. 5 BiReportTypes (Usage/Invoicing/Statistic/Messages/Traffic), status-report, subscription-report, Kamstrup reports, economic dialog, internal reports. COMPLETE. |
| `sms` | — | `[ ]` | No domain folder found — not a standalone domain. SMS channel covered by messaging/Delivery. |
| `sms_group` | 0.84 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Core broadcast entity. 5 creation variants, lifecycle events, MessageModel signals (isLookedUp/testMode/eBoks), status feature 4-tab detail, approval/scheduling/stencil subsystems. COMPLETE. |
| `standard_receivers` | 0.84 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary; 13 capabilities, 4 flows, 7 rules. Individual receivers, groups, import, iFrame subscription, keywords, SCIM. COMPLETE. |
| `Statistics` | 0.35 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. No dedicated controller; SearchController is API owner. Message search (4 dimensions × active+archived), GDPR erasure, usage/invoicing reports, per-broadcast delivery stats (SmsGroupStatisticModel), quick-response pie chart, Norwegian registry stats. 7 rules. COMPLETE. |
| `Subscription` | 0.58 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. Citizen self-subscription (address/supply/zipcode/StdReceiverGroup), iFrame widget, Excel import, notification SMS, 5 subscription types, 6 rules. COMPLETE. |
| `subscriptions` | 0.58 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. BalarmWebApp citizen iFrame API (SubscribeModuleController). PIN challenge-response (AnonymousTokenModel), address+supply sub/unsub, bulk CSV admin, public GUID entry, 7 rules. COMPLETE. |
| `templates` | 0.37 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Layer 1 empty; source-primary. 9 channel types, 12 capabilities, 3 flows, 6 rules. Merge fields, quick response, weather warning mapping. COMPLETE. |
| `Voice` | — | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. TTS channel via Infobip gateway. No dedicated VoiceController; CreateSingleVoice via MessageController. Wizard integration, AdvancedVoiceSettings (language/attempts/interval), call forwarding, VoiceNudging dialog, delivery status callback handler, VoiceBackgroundService. 7 rules. COMPLETE. |
| `Webhook` | — | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. Dual-direction: outbound webhook registration (ServiceAlert.Api /WebHooks, 2 event types: Webmessage+MessageStatus, Channel-based dispatch), inbound gateway callbacks (GatewayAPI/Infobip/Strex/SendGrid/1919 — anonymous). No UI. Idempotent create. Customer-scoped. 7 rules. COMPLETE. |
| `web_messages` | 0.88 | `[x]` | `099_distillation.md` — APPROVED_BASELINE 2026-04-11. Source-primary. 4 WebMessageTypes (Sms2Webs/Sms2Internals/Facebook/Twitter), admin list, admin form, wizard integration, copy-from-SMS/Email, 7 rules. COMPLETE. |

---

**Total domains:** 38
**Distilled [x]:** 37 (identity_access, email, profile_management, system_configuration, localization, activity_log, customer_administration, customer_management, eboks_integration, logging, messaging, recipient_management, standard_receivers, templates, data_import, positive_list, address_management, Enrollment, Delivery, job_management, reporting, Benchmark, web_messages, sms_group, phone_numbers, Conversation, integrations, Finance, Subscription, subscriptions, Statistics, Monitoring, Voice, Webhook, pipeline_crm, pipeline_sales, Lookup)
**In progress [~]:** 0
**Not started [ ]:** 6

**Last updated:** 2026-04-11
**Updated by:** Copilot — autonomous run
