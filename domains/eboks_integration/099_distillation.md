# Domain Distillation: eboks_integration

**STATUS:** APPROVED_BASELINE  
**Completeness source:** 0.88 (Layer 1 — behaviors EMPTY) + source code evidence  
**UI verified from:** `eboks-create-edit.component.html`, `eboks-mobile-preview.component.ts`  
**Source verified from:** `EboksCvrWorkloadProcessor.cs`, `IEboksService.cs`, `EboksStrategies.cs`  
**Date:** 2026-04-11  
**NOTE:** Layer 1 behaviors and rules are empty. Distillation from entity list + direct source reading.  

---

## PURPOSE

eBoks is a Danish digital mail delivery system used as an alternative to SMS for reaching business recipients. When a recipient has an eBoks address (tied to their CVR number or personal eBoks Amplify address), the system can deliver a formatted document (headline + rich text body) directly to their eBoks inbox instead of or in addition to sending an SMS. The profile must have the eBoks capability role to use this channel. Delivery strategy is configurable: always use eBoks, always use SMS, try eBoks first and fall back to SMS, or try SMS first and use eBoks as fallback.

---

## CORE CONCEPTS

1. **eBoks message** — a formatted digital document with a headline and a rich-text body. Unlike SMS, eBoks supports formatting and file-like appearance. The recipient receives it in their digital mailbox.

2. **Recipient eBoks address** — the recipient's mailbox identifier in the eBoks system. Stored as `RecipientEboksAddress`. Looked up by either CVR number (business) or eBoks Amplify address (personal).

3. **Two lookup paths:**
   - **CVR lookup** — finds the eBoks mailbox for a business recipient by their company registration number. Goes through `EboksCvrWorkloadProcessor`.
   - **Amplify lookup** — finds the eBoks mailbox for a personal (citizen) eBoks account via the Amplify service. Goes through `EboksAmplifyWorkloadProcessor`.

4. **Delivery strategy** — a configurable four-option setting per profile (and overridable per message):
   - `NoEboks` (0) — never use eBoks
   - `EboksAll` (1) — always deliver via eBoks
   - `SmsFirst` (2) — try SMS; if no phone number, use eBoks
   - `EboksFirst` (3) — try eBoks; if no eBoks address, use SMS

5. **EboksMessage record** — a DB row tracking the delivery status of each eBoks document sent. Linked to the SmsLog row (SmsLogId) of the originating broadcast item.

6. **EboksMessageStatistic** — per-message delivery outcome record. Used for reporting.

7. **eBoks gateway** — the outbound HTTP integration calling the eBoks REST API. Parallel processing via TPL Dataflow (max 15 concurrent sends).

8. **Mergefields** — the eBoks message body supports merge fields (variable substitution) to personalise the document per recipient.

---

## CAPABILITIES

1. Author an eBoks message: enter headline and rich-text body (with merge field support), with live mobile preview of the rendered document.
2. Select a delivery strategy per message (if the profile allows strategy selection).
3. Deliver eBoks messages to business recipients via CVR number lookup.
4. Deliver eBoks messages to personal recipients via Amplify address lookup.
5. Check whether a customer/profile is enabled for eBoks delivery (`HasEboksAsync`).
6. Track per-message delivery status in the `EboksMessages` table.
7. Record delivery statistics in `EboksMessageStatistics`.
8. Clean up old eBoks message records via scheduled batch (`CleanupEboksMessages`).
9. Send queued eBoks messages in a batch run (`SendEboksMessagesAsync`).
10. Configure eBoks as a delivery option on a profile (role-gated: `CanSendByEboks`).
11. Duplicate checking — before sending, checks for double CVR or Amplify address entries in the workload to prevent duplicate delivery.
12. Check CVR-to-name match — optional validation that the CVR belongs to the expected company name.

---

## FLOWS

### 1. eBoks Message Authoring
Operator opens a broadcast, selects eBoks as a channel (if profile has the capability) → enters headline (required) + rich-text body (required, size-limited) → selects delivery strategy → live preview renders the document as it will appear on mobile eBoks app → saves as part of the broadcast.

### 2. CVR-Based eBoks Delivery (Business)
Broadcast reaches delivery phase → for each business recipient: lookup CVR number against the eBoks CVR directory → check for duplicates → if found and no duplicate: generate the eBoks document, POST to eBoks REST API → receive status code back → update `EboksMessages` and `SmsLog` status → mark `SmsGroup` as sent.

### 3. Amplify-Based eBoks Delivery (Personal)
Same as CVR flow but uses the eBoks Amplify API to look up the recipient's personal mailbox address → validates ownership → delivers document.

### 4. Strategy-Based Fallback
Delivery engine evaluates the strategy for this recipient and broadcast:
- `EboksFirst` — try eBoks lookup; if no address found → fall back to SMS delivery
- `SmsFirst` — try SMS; if no phone number → attempt eBoks delivery
- `EboksAll` — only eBoks, no SMS fallback
- `NoEboks` — skip eBoks entirely, deliver by SMS only

---

## RULES

1. eBoks capability is a profile role (`CanSendByEboks`). A profile without this role cannot author or send eBoks messages.
2. eBoks requires the recipient to have a registered CVR number (for businesses) or a registered Amplify address (for personal eBoks).
3. Delivery strategy `NoEboks` = eBoks channel is completely unused even if the profile has the capability.
4. The eBoks document body has a size limit measured in kilobytes (not characters) — UI enforces this with a real-time counter.
5. Merge fields in the message body are validated before sending. An invalid merge field token blocks saving.
6. Parallel delivery uses up to 15 concurrent HTTP connections to the eBoks API.
7. Test mode is supported — status codes 802 and 803 are treated as test-mode results and do not trigger real delivery.

---

## INTEGRATIONS

1. **eBoks CVR API** — outbound HTTP REST calls to the eBoks system for business recipient delivery.
2. **eBoks Amplify API** — outbound HTTP REST calls for personal citizen mailbox delivery.
3. **Internal event bus (MediatR)** — `BenchmarkFinishedNotificationHandler`, `StartLookupBatchNotificationHandler`, and others hook into the message pipeline to trigger eBoks workloads.

---

## GAPS

1. **Layer 1 behaviors and rules are empty** — the full lookup/send pipeline logic was derived from direct source reading; no structured Layer 1 behaviors exist.
2. **Strategy configuration per recipient unclear** — it is not captured whether the strategy can be overridden per individual recipient, or only at profile and message level.
3. **eBoks status code mapping** — the full set of eBoks API response codes (other than 802/803 test codes) is not captured in Layer 1.
