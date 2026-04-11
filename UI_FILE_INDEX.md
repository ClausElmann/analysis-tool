# UI FILE INDEX
**Source:** `sms-service/ServiceAlert.Web/ClientApp/`
**Protocol:** Layer 1 SSOT extraction artefact. Updated per domain distillation.

**Status legend:**
- `[ ]` not mapped
- `[~]` mapped (raw — identified and validated against domain artifact)
- `[x]` distilled (formally included in 099_distillation.md)

---

## identity_access

| File | Status |
|---|---|
| `src/features/bi-login/bi-login.component.ts` | `[x]` — STEP 12-C+D verified |
| `src/features/bi-login/bi-login.component.html` | `[x]` — STEP 12-C+D verified |
| `src/features/bi-login/transparent-login.component.ts` | `[~]` |
| `src/features/bi-login/ad-login-info-box/ad-login-info-box.component.ts` | `[~]` |
| `src/features/bi-login/ad-login-info-box/ad-login-info-box.component.html` | `[~]` |
| `src/features/password-reset-create/password-reset-create.component.ts` | `[~]` |
| `src/features/password-reset-create/password-reset-create.component.html` | `[~]` |
| `src/features/my-user/user-security/user-security.component.ts` | `[~]` |
| `src/features/my-user/user-security/user-security.component.html` | `[~]` |
| `src/features/my-user/user-info-edit/bi-two-factor-handler/bi-two-factor-handler.ts` | `[~]` |
| `src/features/my-user/user-info-edit/bi-two-factor-handler/bi-two-factor-handler.html` | `[~]` |
| `src/core/services/user-nudging.service.ts` | `[~]` |
| `src/features/broadcasting/customer-survey-nudge-dialog/customer-survey-nudge-dialog.component.ts` | `[~]` |
| `src/features/administration/super-administration/internal-reports/failed-ad-logins/failed-ad-logins.component.ts` | `[~]` |
| `src/features/administration/super-administration/internal-reports/nudging-report/nudging-report.component.ts` | `[~]` |
| `side-projects/subscription-app/src/features/login/en-login.component.ts` | `[~]` |
| `side-projects/subscription-app/src/features/login/en-login.component.html` | `[~]` |
| `app-globals/openapi-models/model/loginEmailPasswordModel.ts` | `[~]` |
| `app-globals/openapi-models/model/loginAdModel.ts` | `[~]` |
| `app-globals/openapi-models/model/nudgeType.ts` | `[~]` |
| `app-globals/openapi-models/model/userNudgingBlocksDto.ts` | `[~]` |
| `app-globals/openapi-models/model/saveUserNudgingResponseCommand.ts` | `[~]` |
| `app-globals/openapi-models/model/authenticatorAppCodeDto.ts` | `[~]` |
| `app-globals/openapi-models/model/resetPasswordModel.ts` | `[~]` |
| `app-globals/openapi-models/model/passwordVerificationModel.ts` | `[~]` |
| `src/shared/components/dialog-content/bi-profile-selection-dialog-content/bi-profile-selection-dialog-content.component.ts` | `[~]` |

---

## email

| File | Status |
|---|---|
| *(email domain closed — no interactive UI components identified for distillation)* | `[x]` |

---

## profile_management

| File | Status |
|---|---|
| `src/features/administration/customer-admin/customer-profiles/edit-profile/edit-profile.component.ts` | `[x]` — tab structure verified |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/edit-profile.component.html` | `[x]` |
| `src/features/administration/customer-admin/customer-profiles/create-profile/create-profile.component.ts` | `[x]` |
| `src/features/administration/customer-admin/customer-profiles/create-profile/create-profile.component.html` | `[x]` — creation form fields verified |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-info/profile-info.component.ts` | `[x]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-info/profile-info.component.html` | `[x]` — all Info tab sections verified |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-roles/profile-roles.component.ts` | `[x]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-roles/profile-roles.component.html` | `[x]` — category+checkbox layout verified |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-api-keys/profile-api-keys.component.html` | `[x]` — inline editable key+secret table verified |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-users/profile-users.component.ts` | `[~]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-users/profile-users.component.html` | `[~]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-social-media/profile-social-media.component.ts` | `[~]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-social-media/profile-social-media.component.html` | `[~]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-email2sms/profile-email2sms.component.ts` | `[~]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-email2sms/profile-email2sms.component.html` | `[~]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-distribution/profile-distribution-number-admin.component.ts` | `[~]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-distribution/profile-distribution-number-admin.component.html` | `[~]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-map-settings/profile-map-settings.component.ts` | `[~]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-map-settings/profile-map-settings.component.html` | `[~]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-ready-reports/profile-ready-reports.component.ts` | `[~]` |
| `src/features/administration/customer-admin/customer-profiles/edit-profile/tab-children/profile-ready-reports/profile-ready-reports.component.html` | `[~]` |
| `src/core/services/profile.service.ts` | `[~]` |
| `src/core/routing/guards/profile-role.guard.ts` | `[~]` |
| `src/shared/components/country-customer-profile-selection/bi-country-customer-profile-selection.component.ts` | `[~]` |
| `src/shared/components/country-customer-profile-selection/bi-country-customer-profile-selection.component.html` | `[~]` |

---

## customer_management

| File | Status |
|---|---|
| `src/features/administration/super-administration/customers/super-customers-main.component.ts` | `[~]` |
| `src/features/administration/super-administration/customers/super-customer-detail/SuperCustomerDetailTabsConfig.ts` | `[x]` — 8 tabs verified |
| `src/features/administration/super-administration/customers/super-customer-detail/super-customers-detail.component.ts` | `[~]` |
| `src/features/administration/super-administration/customers/super-customer-detail/super-customer-settings/super-customer-settings.component.ts` | `[~]` |
| `src/features/administration/super-administration/customers/super-customer-detail/super-customer-contact-persons/Table/super-customer-contact-persons-table.component.ts` | `[~]` |
| `src/features/administration/super-administration/customers/super-customer-detail/super-customer-gdpr-accept/super-customer-gdpr-accept.component.ts` | `[~]` |
| `src/features/administration/super-administration/customers/create-customer/create-customer.component.ts` | `[~]` |
| `src/features-shared/customer-create-edit/customer-create-edit.component.ts` | `[x]` — form sections verified (shared with customer_administration) |
| `src/features-shared/customer-create-edit/customer-create-edit.component.html` | `[x]` — Account Data + Broadcast Settings sections verified |

---

## system_configuration

| File | Status |
|---|---|
| `src/features/administration/super-administration/super-admin-settings/super-admin-settings.component.ts` | `[x]` — tab structure verified |
| `src/features/administration/super-administration/super-admin-settings/super-admin-settings.component.html` | `[x]` |
| `src/features/administration/super-administration/super-admin-settings/packages-setup/packages-setup.component.ts` | `[x]` |
| `src/features/administration/super-administration/super-admin-settings/packages-setup/packages-setup.component.html` | `[x]` — package+role checkboxes verified |
| `src/features/administration/super-administration/super-admin-settings/super-admin-functions/super-admin-functions.component.ts` | `[x]` |
| `src/features/administration/super-administration/super-admin-settings/super-admin-functions/super-admin-functions.component.html` | `[x]` — kill-switch, cache clear, stats recalc verified |
| `src/features/administration/super-administration/super-admin-settings/profile-role-country-mapping/profile-role-country-mapping.component.ts` | `[~]` |
| `src/features/administration/super-administration/super-admin-settings/user-role-country-mapping/user-role-country-mapping.component.ts` | `[~]` |
| `src/features/administration/super-administration/super-admin-settings/sales-info/sales-info.component.ts` | `[~]` |

---

## Remaining domains — distillation status

> Note: Individual UI file tracking for domains below was collected during autonomous distillation run (2026-04-11).
> Files are referenced within each domain's `099_distillation.md`. Full per-file tracking can be backfilled here if needed.

| Domain | Status | Notes |
|---|---|---|
| `activity_log` | `[x]` | Distilled 2026-04-11 |
| `address_management` | `[x]` | Distilled 2026-04-11 |
| `Benchmark` | `[x]` | Distilled 2026-04-11 |
| `Conversation` | `[x]` | Distilled 2026-04-11 |
| `customer_administration` | `[x]` | Distilled 2026-04-11 |
| `data_import` | `[x]` | Distilled 2026-04-11 |
| `Delivery` | `[x]` | Distilled 2026-04-11 |
| `eboks_integration` | `[x]` | Distilled 2026-04-11 |
| `Enrollment` | `[x]` | Distilled 2026-04-11 |
| `Finance` | `[x]` | Distilled 2026-04-11 |
| `integrations` | `[x]` | Distilled 2026-04-11 |
| `job_management` | `[x]` | Distilled 2026-04-11 |
| `localization` | `[x]` | Distilled 2026-04-11 |
| `logging` | `[x]` | Distilled 2026-04-11 |
| `Lookup` | `[x]` | Distilled 2026-04-11 |
| `messaging` | `[x]` | Distilled 2026-04-11 |
| `Monitoring` | `[x]` | Distilled 2026-04-11 |
| `phone_numbers` | `[x]` | Distilled 2026-04-11 |
| `pipeline_crm` | `[x]` | Distilled 2026-04-11 |
| `pipeline_sales` | `[x]` | Distilled 2026-04-11 |
| `positive_list` | `[x]` | Distilled 2026-04-11 |
| `product_scope` | `[ ]` | Reference artifact — locked. Distillation deferred. |
| `recipient_management` | `[x]` | Distilled 2026-04-11 |
| `reporting` | `[x]` | Distilled 2026-04-11 |
| `sms` | `[ ]` | Not a standalone domain — covered by messaging/Delivery |
| `sms_group` | `[x]` | Distilled 2026-04-11 |
| `standard_receivers` | `[x]` | Distilled 2026-04-11 |
| `Statistics` | `[x]` | Distilled 2026-04-11 |
| `Subscription` | `[x]` | Distilled 2026-04-11 |
| `subscriptions` | `[x]` | Distilled 2026-04-11 |
| `templates` | `[x]` | Distilled 2026-04-11 |
| `Voice` | `[x]` | Distilled 2026-04-11 |
| `Webhook` | `[x]` | Distilled 2026-04-11 |
| `web_messages` | `[x]` | Distilled 2026-04-11 |

---

**Last updated:** 2026-04-11
**Updated by:** Copilot — autonomous distillation run
**Domains with [x] distillation:** 37
**Domains not distilled [ ]:** 2 (product_scope — deferred; sms — not standalone)
**Total tracked:** 38 (per `_distillation_index.md`)
