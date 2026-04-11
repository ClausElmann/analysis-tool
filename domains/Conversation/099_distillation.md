# Domain Distillation — Conversation

**Status:** APPROVED_BASELINE  
**Completeness score (Layer 1):** 0.54  
**Evidence:** Source-primary. UI source: sms-conversations.component, conversations.service, create-conversation-dialog, write-conversation-reply, SSE handlers, sms-conversations-admin

---

## 1. Core Concept

`Conversation` is the two-way SMS messaging domain. A conversation is a persistent thread between the system (on behalf of a profile) and a citizen (phone number). Inbound messages from citizens are routed to the matching conversation by the conversation phone number they were sent to. Agents can reply from the web UI. Real-time updates arrive via SSE.

---

## 2. Entities

### `ConversationDto`
Core conversation record — thread container.
- `id` — conversation identifier
- `latestMessage` / `latestMessageDateUtc` — used for list ordering and display
- Linked to a `ConversationPhoneNumberModel` (the virtual number used as sender)

### `ConversationMessageDto`
Individual message within a conversation.
- Inbound (from citizen) or outbound (from agent)

### `ConversationPhoneNumberModel` / `ConversationPhoneNumberWithProfileIdsDto`
Virtual phone numbers used as conversation channels.
- `ConversationPhoneNumberWithUnreadCountDto` — includes unread message count per number
- `ConversationPhoneNumberWithProfileIdsDto` — with profile assignments
- `ConversationPhoneNumberWithCustomerInfoReadModel` — with customer context

### `CreateConversationCommand`
Creates a new outbound conversation (agent-initiated).
- Fields: `phoneNumber` (citizen phone), `conversationNumber` (sender number), `text` (initial message)

### `ConversationPartnerNameUpdateCommand`
Updates the display name associated with a citizen phone number.

### `UpdateConversationPhoneNumberCommand`
Updates the virtual phone number configuration.

---

## 3. Conversation List UI (`sms-conversations.component`)

Two-panel layout: left = conversation list + filters, right = message thread.

**Filters:**
- Sender number selector (dropdown by `conversationNumberId`; 0 = all)
- "Show only unread" checkbox toggle
- From date / To date
- Free text search (`textSearch`)

**Conversation list:**
- `bi-conversation-item` per conversation: shows `conversationModel`, active state, unread badge
- `showPhoneNumberName` = true when "All numbers" selected (shows which number each conversation is on)
- `markConversationUnread` action per item

**Create conversation:**
- "Create SMS Conversation" button → dialog: `create-conversation-dialog-content`
- Dialog form: `bi-phone-input` (citizen phone + country code), sender number selector, text (SMS-length limited, no merge fields)

**Empty states:**
- No sender numbers configured → "conversations.NoSenderNumbers"
- No matching conversations → "conversations.NoConversations"

---

## 4. Message Thread (right panel)

Selected conversation shows all messages chronologically + reply form.

**`write-conversation-reply` component:**
- Single `textControl` (required)
- Emits `onReply(text)` output on valid send
- Resets form after send

**`ConversationMessageSentEventDto`** — SSE payload for live message delivery confirmation.

---

## 5. Real-Time SSE Integration

### `ConversationUnreadStatusSSEHandler`
- Handles SSE event type `ConversationUnreadStatus`
- Payload: `{ totalUnreadCount, conversationId?, unread }`
- If `conversationId` present: delta update (increment/decrement local count)
- If no `conversationId`: full reset with `totalUnreadCount`
- Total count displayed in navigation bar badge

### `ConversationCreatedHandler`
- Handles SSE event for new inbound conversation creation

### `ConversationMessageSentHandler`
- Handles SSE event when a new message arrives in an existing conversation

---

## 6. Admin Config (`sms-conversations-admin`)

Embedded component in profile management for configuring conversation numbers.

**`assign-conversation-number.component`:**
- Assigns a `ConversationPhoneNumberModel` to a profile
- Calls `AssignConversationPhoneNumberCommand`

**`ConversationsService` (admin methods):**
- `getUnassignedPhoneNumbers(customerId, countryId)` → `ConversationPhoneNumberModel[]` (cached per customerId)
- `getConversationPhoneNumbersWithProfileIdsModels(customerId)` → phone numbers with all profile assignments (cached per customerId)

---

## 7. ConversationsService State

`BiStore<ConversationsStateData>` — client-side cache.

| State Key | Type | Description |
|---|---|---|
| `customerIdToPhoneNumbersMap` | `{[customerId]: ConversationPhoneNumberModel[]}` | Unassigned numbers per customer |
| `conversationPhoneNumberAndProfileModels` | `{customerId, models}` | Phone numbers + profile assignments |

---

## 8. Rules

1. Conversation numbers must be explicitly assigned to a profile before conversations can be created on that number
2. Unread count in navbar badge is maintained via SSE delta updates (increment/decrement per conversation) or full reset (no conversationId)
3. Initial message on new conversation is an SMS — same length constraints and delivery via SmsBackgroundService
4. `showPhoneNumberName` is set when the "All numbers" option is selected — allows users to see which number each conversation belongs to
5. Reply text control resets immediately after successful send
6. Conversation list filter is client-side once data is loaded; server query needed for date range + text search
