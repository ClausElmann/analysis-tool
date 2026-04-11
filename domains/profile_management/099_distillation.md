# Domain Distillation: profile_management

**STATUS:** APPROVED_BASELINE  
**Completeness source:** 0.91 (Layer 1) + UI verification  
**UI verified from:** `edit-profile.component.ts`, `edit-profile.component.html`, `profile-info.component.html`, `create-profile.component.html`, `profile-roles.component.html`, `profile-api-keys.component.html`  
**Date:** 2026-04-11  

---

## PURPOSE

A profile is the primary operational unit for sending notifications. Every customer has one or more profiles. All notification sending, recipient management, and feature capabilities are scoped to a profile — not to the customer or user directly. A profile has an identity (name, sender name, logo), a type (the kind of utility it represents), a set of capability roles (which determine what it can do), and a list of users who can work within it.

---

## CORE CONCEPTS

1. **Profile** — a bounded operational workspace under a customer. The sending identity, recipient lists, templates, and feature access all belong to a profile. A user must be explicitly granted access to a profile — belonging to the customer does not automatically grant access.

2. **ProfileType** — a category label for what the profile represents: Water, Wastewater, Electricity, Heating, Renovation, or general-purpose. Determines context in UI labels and some country-specific behavior.

3. **ProfileRole (Capability)** — a named on/off toggle that unlocks a specific feature. The full set of roles assigned to a profile defines everything it can do — sending by eBoks, map-based sending, Facebook posting, Kamstrup meter reporting, etc. Role assignment is the commercial capability model: each role has a price.

4. **ProfileRoleGroup (Package)** — a preset collection of roles applied at the moment a profile is created. This is a one-shot template: changing the package later does NOT update profiles that were already created with it.

5. **ProfileUser** — a user who has been explicitly given access to this profile. Access is per-profile, not inherited from the customer level. Removal of the mapping revokes access immediately.

6. **API Key** — a key+secret pair that allows an external system to operate as this profile. Scoped per profile.

7. **Sender Identity** — the outward-facing name of the profile: SMS sender name, email sender name, public name, public address, and logo. These appear on all outgoing messages from this profile.

---

## CAPABILITIES

1. Create a new profile with a name, type, country, optional package, and optional initial user list.
2. Edit the profile's core information: name, type, package, sender name, email sender name.
3. Edit the profile's public identity: public name, public address, company registration ID, logo.
4. Configure sender name for SMS — subject to minimum and maximum character length rules; may be locked if the user lacks the required permission.
5. Configure email sender name for outgoing email notifications.
6. Configure an optional internal display name for SMS-to-internal messages.
7. Configure an optional benchmark display name.
8. Assign and remove capability roles from the profile (superAdmin only, presented as grouped checkboxes).
9. Apply a capability package at creation time to pre-load a role set.
10. Grant and revoke user access to the profile.
11. Manage API keys for external system access (superAdmin only, inline editable table).
12. Upload, view, and delete a profile logo.
13. Upload and manage files in profile-scoped cloud storage.
14. Configure FTP import settings for the profile (superAdmin only).
15. Configure Email-to-SMS whitelist (role-gated, superAdmin only).
16. Link the profile to standard receiver groups for distribution (role-gated).
17. Configure map search method for Norwegian profiles.
18. Configure eBoks delivery strategy (superAdmin, if profile has eBoks capability).
19. Configure warning notification emails and default recipient strategy (superAdmin, if profile has warning capability).
20. Configure maximum number of address lookup results (superAdmin only).
21. Configure a weekly summary report email address (superAdmin only).
22. View Kamstrup Ready reports (superAdmin + role-gated): meters, readings, warnings, raw data.
23. Configure billing/account settings for Norwegian profiles (superAdmin only).
24. Soft-delete a profile (superAdmin only); triggers 120-day countdown to full PII cleanup.
25. Switch the active profile context in the current user session.

---

## TAB STRUCTURE (UI verified)

All tabs in the profile edit view are conditionally shown:

| Tab | Visibility condition |
|---|---|
| **Info** | Always |
| **Users** | Always |
| **Map** | Profile has map-sending capability |
| **Social Media** | Profile has Facebook or Twitter posting role |
| **Email2sms** | Profile has Email2sms role AND user is superAdmin |
| **Distribution** | Profile has DistributeToStdReceiverGroups role |
| **Statstidende** | Profile has Statstidende role AND (superAdmin OR user has Statstidende setup permission) |
| **Account** | SuperAdmin AND profile is Norwegian |
| **Roles** | SuperAdmin only |
| **API Keys** | SuperAdmin only |
| **FTP** | SuperAdmin only |
| **Kamstrup Reports** | SuperAdmin AND profile has KamstrupReady role |

Changing a profile's roles dynamically changes which tabs are visible.

---

## FLOWS

### 1. Profile Context Switch
User selects a different profile from the session selector → system checks whether the user has explicit access to that profile → if not, access is denied (403) → if yes, the user's active profile is updated in the database → on the next token refresh, the new profile ID is embedded in the JWT → all subsequent requests use the new profile.

### 2. Profile Creation
Admin fills the creation form: name (required), type (required), country (required), optional package, optional initial user list → profile record inserted → if a package was selected, its roles are applied immediately → if users were selected, access mappings are inserted → profile is now available in selectors.

### 3. Feature Gate Check
Any feature operation (e.g. send by eBoks, post on Facebook, use map) internally checks whether the active profile has the required role → lookup is cached per profile → if the role is missing, the operation is blocked with a 403 → if present, the operation proceeds. This is the primary capability enforcement mechanism across the entire system.

### 4. Profile Deletion and 120-Day Cleanup
Admin triggers delete → profile immediately disappears from all selectors (soft delete, `Deleted=true`) → after 120 days: a scheduled batch job removes all child records (email whitelist, FTP settings, role mappings, user mappings, standard receiver mappings, template links, etc.) → the profile record itself has all PII fields nulled and the name gets ` (DELETED)` appended.

---

## RULES

1. Belonging to a customer does NOT grant access to the customer's profiles. Each access mapping must be explicitly created.
2. A ProfileRoleGroup (package) is applied at creation time only. Updating the package definition later does NOT retroactively change already-assigned profiles.
3. ProfileRoles are the system's commercial capability model. Each role has an associated price, meaning the profile's capability set determines its billing cost.
4. Soft delete is the only deletion path for admins. Hard deletion happens automatically after 120 days via a scheduled batch job.
5. SMS sender name has enforced minimum and maximum character length. The UI validates and blocks saving if violated.
6. A profile can have its sender name "locked" — the UI shows an informational message and the field is disabled.
7. The Account settings tab is only available for Norwegian profiles (country = NO).
8. Roles, API Keys, and FTP tabs are superAdmin-only areas; regular customer admins cannot access them.
9. A user who is removed from all profiles can still belong to the customer but cannot send or access any profile data until access is re-granted.
10. Admin-manageable user roles shown in UI include access to sub-menu areas (e.g. standard receivers, text templates, web messages, enrollment/unenrollment) and operational abilities (edit recipients, delete drafts/scheduled messages).
11. User licenses are purchased separately. Each additional user login costs a fixed monthly amount, and customers have a license cap tied to their subscription.

---

## EDGE CASES

1. A user loses access to all profiles if their mappings are removed — no fallback to customer-level access.
2. Changing the package on a profile group does not affect previously created profiles — admins must manually reassign roles if desired.
3. After a profile is deleted, it immediately vanishes from all selectors, but data (message history, etc.) is retained for 120 days before cleanup.
4. Tab visibility changes dynamically when profile roles are changed — a tab may appear or disappear without a page reload after role reassignment.
5. Adding a profile role that unlocks a new tab (e.g. DistributeToStdReceiverGroups) requires the admin to revisit the profile to see the new tab.
6. Norwegian-specific fields (OneFlow document ID, map search method, account tab) are hidden for all other countries — no partial display.
7. If no API key types are configured at the system level, the API keys tab shows a "no types available" message and the create button is hidden.
8. Weekly report email field accepts free-text but validates email format on dirty state — invalid emails are flagged but not blocked from save at field level (server validates definitively).

---

## INTEGRATIONS

1. **Azure Blob Storage** — profile file storage: files are uploaded to a cloud container, with metadata (path, type, size) stored in the database. Download and delete also routed through this integration.
2. **Scheduled batch job** — `cleanup_deactivated_profiles` job runs on a schedule (daily), triggers the 120-day PII cleanup stored procedure.

---

## GAPS

No formal gap records (080_gaps.json absent). Observed potential gaps:

1. **No UI for profile usage overview** — `CustomerProfileUsageOverviewDto` exists in the data model but no corresponding UI component was found for standard customer admins (only superAdmin views likely cover this).
2. **FTP configuration scope unclear** — FTP settings appear in the superAdmin-only tab; whether non-superAdmin profiles can ever have FTP configured is not captured in Layer 1.
