# Domain Distillation — web_messages

**Status:** APPROVED_BASELINE  
**Completeness score (Layer 1):** 0.88  
**Evidence:** Layer 1 stable (behaviors/flows garbage — discarded) + UI source (web-messages component, web-message-part-admin, web-message-part wizard component)

---

## 1. Core Concept

`web_messages` handles web-published messages and internal messages that accompany SMS broadcasts. A web message is a complementary channel alongside SMS — the message is published on a web portal or internal portal, optionally for Facebook/Twitter, with its own title, text, validity period, and scheduling.

---

## 2. WebMessageType Enum

| Value | Description |
|---|---|
| `Sms2Webs` | Message published to public web portal |
| `Sms2Internals` | Message published to internal portal |
| `Facebook` | Post to Facebook |
| `Twitter` | Post to Twitter/X |

---

## 3. Web Message Entity Fields

| Field | Notes |
|---|---|
| `title` | Header text (max 100 chars) — only for Sms2Webs and Sms2Internals types |
| `text` | Message body (max 10,000 chars) |
| `dateDelayUtc` | ValidFrom — scheduled publish time |
| `dateExpireUtc` | ValidTo — expiry time |
| `typeId` | `WebMessageType` enum value |
| `critical` | Boolean flag — critical message indicator |
| `profileName` | Profile the message belongs to |
| `status` | Current publication status |
| `sendAsap` | If true: publish immediately, no dateFrom required |

---

## 4. Admin UI — `web-messages.component`

**Context:** administration → web-messages

**SuperAdmin features:**
- Country + Customer selector (`bi-country-customer-profile-selection`, customer required)
- Date range query (showMessagesFromDate / showMessagesToDate) — validated for ordering

**Table columns:** Title, Message, ValidFrom (`dateDelayUtc`), ValidTo (`dateExpireUtc`), MessageType (`typeId`), Critical, Profile, Status + [Edit] [Delete] action buttons

**Behaviors:**
- Date range required to load messages
- Create button → `web-message-part-admin` form
- Date validation: fromDate must be before toDate (cross-field validators)

---

## 5. Admin Form — `web-message-part-admin.component`

Used within `bi-accordion` for create/edit of individual web messages. The form is embedded per-message in the list.

**Form fields:**
- `title` — shown only for `Sms2Webs` and `Sms2Internals` types
- `text` — textarea, 10,000 char limit; merge fields hidden in admin context
- `sendAsap` checkbox — shown for Sms2Webs, Sms2Internals, Facebook, Twitter
- `dateFrom` + `timeFrom` — publish start (hidden if sendAsap=true); time required for all types except Facebook/Twitter
- `dateTo` + `timeTo` — publish end

**CopyFromWeb button:** Shown if `canCopyTextFromWeb()` — copies text from the web channel version

---

## 6. Wizard Integration — `web-message-part.component`

Message wizard step for composing a web or internal message alongside the SMS.

**Inputs:**
- `forInternalMessage()` — switches between web title id (`web-title`) and internal title id (`internal-title`)
- `forStdReceivers()` — if true: merge fields hidden in textarea
- `showCopyFromSmsPartButton()` / `showCopyFromEmailPartButton()` — show copy-source buttons

**Form fields:**
- `title` — `sms2WebTitleMaxLength` chars
- `message` — `sms2WebMaxLength` chars; merge fields supported (unless `forStdReceivers`)

**Copy behavior:**
- "Copy from SMS" button: emits `onCopyFromSmsMessagePart` event
- "Copy from Email" button: emits `onCopyFromEmailMessagePart` event
- Merge field validation: `messageCtrl.errors.mergeField` shown if invalid merge field included

---

## 7. Rules

1. Title field only rendered for `Sms2Webs` and `Sms2Internals` message types — not for Facebook/Twitter
2. `sendAsap` checkbox only shown for Sms2Webs, Sms2Internals, Facebook, Twitter (not for eBoks/other types)
3. Time field (`timeFrom`) is required for all types except Facebook and Twitter
4. In admin form: merge fields are always hidden (no manual merge field insertion in admin manage context)
5. In wizard form: merge fields hidden if `forStdReceivers()` (standard receivers context)
6. Facebook/Twitter use `useClearText` option in textarea — resets to empty on clear
7. Date range query required in admin list before messages load (no default "show all")
