# Domain Distillation — sms_group

**Status:** APPROVED_BASELINE  
**Completeness score (Layer 1):** 0.84  
**Evidence:** Layer 1 partial entities + UI source (status.component, status-shared.service, status-details routes, status-addresses, status-report covered in reporting domain)

---

## 1. Core Concept

`sms_group` is the central domain entity — an SmsGroup is a **broadcast event** (also called "message" in status UI). Every message sent via the wizard results in an SmsGroup record. The `status` feature provides the lookup and monitoring UI for sent SmsGroups.

---

## 2. Core Entity: `SmsGroupDto`

An SmsGroup represents a single broadcast send operation.

### Creation Variants
| Command | Description |
|---|---|
| `SmsGroupCreateCommand` | Generic create |
| `CreateSmsGroupFromLevelFilterDto` | Create from level filter (ByLevel send method) |
| `SmsGroupByMunicipalitiesCommand` | Create targeting specific municipalities |
| `SmsGroupCreateByLevelCommand` | Create by administrative level |
| `SmsGroupIdAndAddressesCommand` | Create with explicit address list |

### Key Operations
| Command/DTO | Description |
|---|---|
| `LookupSmsGroupCommand` | Trigger address→owner lookup for the draft before sending |
| `ScheduleCommand` | Schedule the broadcast for a future time |
| `SendSmsGroupCommand` | Execute send immediately |
| `RecalculationSmsGroupReadModel` | Recalculate eBoks recipients (post-send) |
| `SmsGroupApprovalRequestDto` | Request approval from designated approver |
| `SmsGroupApproverDto` / `SmsGroupApproverService` | Approver management |
| `SmsGroupAttachmentDto/ReadModel` | File attachments on a broadcast |

### Lifecycle Events
- `SmsGroupDeletedHandler` — broadcast deleted
- `SmsGroupMarkedAsStencilEventHandler` — broadcast saved as stencil template

### Supporting Structures
- `SmsGroupAddressReadModel` — address-level details for a broadcast
- `SmsGroupIdAndAddressesDto` — address resolution output
- `MultiSmsMessageDto` — multi-recipient message bundle
- `SingleSmsModel` — single send model
- `SmsExampleDto` — preview/example of resolved message text
- `ReceiverIdsAndGroupIdsDto` — direct receiver + group targeting

---

## 3. MessageModel — Runtime State

The `MessageModel` is the full read model for a selected broadcast in the status feature. Its `messageMetadata` contains:

| Field | Type | Notes |
|---|---|---|
| `isLookedUp` | boolean | Whether recipients were looked up (ByAddress) |
| `isMonthGroup` | boolean | Whether this is a monthly aggregate group |
| `eboksMessage` | object? | Present if eBoks channel included |
| `dateSentUtc` | datetime? | Populated when broadcast was actually sent |
| `isRecalculated` | boolean | eBoks recalculation status |
| `quickResponseSetup.responseOptions` | array | Quick response options; non-empty if QR configured |
| `isLargeBroadcast` | boolean | Flag for large broadcasts (special handling) |
| `hasAddresses` | boolean | Has address-based recipients |
| `testMode` | boolean | Sent in test mode |
| `sendSMS` / `sendVoice` / `sendEmail` | boolean | Active delivery channels |
| `profileId` | number | Associated profile |
| `sendMethod` | `SmsSendMethod` | The send method used |

---

## 4. Status Feature UI

The `status` feature is the primary UI layer for the `sms_group` domain.

### Status List (`status.component`)
- SuperAdmin: country + customer + profile selector
- Non-admin: profile selector only (no country/customer)
- Date range query (fromDate / toDate, max today) → `onGetSmsGroupsClicked()`
- SmsGroups table with click-to-detail navigation
- State managed by `StatusSharedService` (scoped `BiStore`)
- State cleared on navigation away from `/status/*`

### Status Detail (`status-details.component`) + Child Routes

| Route | Component | Notes |
|---|---|---|
| `detail` | `StatusDetailsComponent` | Shell with Back button + message name heading |
| `detail/overview` | `OverviewComponent` | Summary of the broadcast |
| `detail/addresses` | `StatusAddressesComponent` | Addresses table + map view |
| `detail/status-report` | `StatusReportComponent` | Per-recipient status + Excel download |
| `detail/message-content` | `StatusMessageContentComponent` | Message content + metadata + eBoks data |

**StatusDetailsComponent** header:
- Back button → list
- Message name shown; test mode → background color indicator
- `bi-tabs` with `tabConfigs()` (lazy-loaded child components)

### StatusSharedService (State Store)
Stores the selected `MessageModel` state and computed signals:

| Signal | Logic |
|---|---|
| `showMessageContentInfo` | `true` if `isMonthGroup === false` |
| `isEboksAbsentOrIsMessageSent` | eBoks not present OR `dateSentUtc` is set |
| `isEboksFullySentOrIsFirstMessageSent` | eBoks recalculated OR (non-eBoks and dateSentUtc set) |
| `hasQuickResponseSetup` | sendMethod ≠ BySmsLogs AND quickResponseSetup has options |
| `isLargeBroadcast` | from `messageMetadata.isLargeBroadcast` |
| `isMessageLookedUp` | `messageMetadata.isLookedUp` |
| `messageHasAddresses` | `messageMetadata.hasAddresses` |
| `messageOnlyHasWebMessages` | No SMS/voice/email AND no eBoks → only web message |

---

## 5. Approval and Scheduling Subsystems

| Service/Repository | Purpose |
|---|---|
| `ISmsGroupApproverService/Repository` | CRUD for approvers per profile |
| `ISmsGroupScheduleService/Repository` | Schedule management (future sends) |
| `ISmsGroupStencilService/Repository` | Stencil (template-from-broadcast) management |
| `ISmsGroupStatisticService/Repository` | Per-group statistics |

---

## 6. Rules

1. State in `StatusSharedService` is cleared when navigating away from the `/status/` route tree
2. `status-report` tab is only accessible when `isMessageLookedUp = true` AND NOT `messageOnlyHasWebMessages`
3. `messageOnlyHasWebMessages` is true when all of `sendSMS`, `sendVoice`, `sendEmail` are false and `eboksMessage` is null
4. Test mode broadcasts are visually flagged on the detail header (background color)
5. `isLargeBroadcast` flag can trigger different handling in downstream services (chunked delivery)
6. eBoks `isRecalculated` is checked to determine whether eBoks send is fully complete
7. Quick response is only available if `sendMethod ≠ BySmsLogs` (direct SmsLog-based sends don't support QR)
