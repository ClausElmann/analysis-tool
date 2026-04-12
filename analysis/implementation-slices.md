# implementation-slices.md — CODE-LEVEL IMPLEMENTATION SPEC

**Source:** Wave 8 (extracted from temp.md 2026-04-12)  
**Status:** Awaiting Architect approval before Wave 9  
**Authority:** INFORMATIONAL — feeds green-ai implementation  
**Governance:** [ai-safe-rules.md](ai-safe-rules.md) — BINDING

---

## SCOPE

Slices 1–3 only. DK path only. Pure logic spec.  
No DB schema, no HTTP, no queues, no Norway/1881, no StandardReceiver, no retries.

---

## SLICE 1 — Create + Submit Broadcast

### Domain Model

```
BroadcastId       : strongly-typed wrapper over int (or Guid — caller-opaque)

BroadcastState    : enum  Draft | Submitted | Targeting | Targeted | Scheduled
                         | Dispatching | Completed | Cancelled

BroadcastMessage  : value type
  Text:          string   // required, non-empty
  SenderName:    string?  // optional

RecipientSpec     : value type
  CountryId:          int
  GeographicFilter:   GeographicFilter   // opaque to this slice — just carried
  AddressRestriction: AddressRestriction

Broadcast         : aggregate root
  BroadcastId:       BroadcastId
  ProfileId:         int
  CountryId:         int
  Message:           BroadcastMessage
  RecipientSpec:     RecipientSpec
  Priority:          DeliveryPriority
  State:             BroadcastState
  CreatedAtUtc:      DateTime

  Submit() → void
    pre:  State == Draft
    post: State = Submitted
    emits: BroadcastReady(BroadcastId)
    throws: InvalidOperationException if State != Draft
```

### Command + Handler

```
CreateBroadcastCommand:
  ProfileId:          int
  CountryId:          int
  Message:            BroadcastMessage
  RecipientSpec:      RecipientSpec
  Priority:           DeliveryPriority
  AddressRestriction: AddressRestriction

Handle(CreateBroadcastCommand cmd) → BroadcastId

  Step 1 — ValidatePermission
    permissionSet = IPermissionService.GetPermissionSet(cmd.ProfileId)
    if not permissionSet.Roles.Contains(CanSendBroadcast):
      throw PermissionDeniedException(cmd.ProfileId, CanSendBroadcast)
    trace.Add(PipelineStepResult.Ok("ValidatePermission", inputCount:1, outputCount:1))

  Step 2 — CreateBroadcast
    broadcast = new Broadcast(cmd.ProfileId, cmd.CountryId, cmd.Message,
                               cmd.RecipientSpec, cmd.Priority, cmd.AddressRestriction)
    // state = Draft on construction
    IBroadcastRepository.Save(broadcast)
    trace.Add(PipelineStepResult.Ok("CreateBroadcast", inputCount:1, outputCount:1))

  Step 3 — SubmitBroadcast
    broadcast.Submit()
    // state: Draft → Submitted
    // emits BroadcastReady(broadcastId) as domain event
    IBroadcastRepository.Save(broadcast)
    trace.Add(PipelineStepResult.Ok("SubmitBroadcast", inputCount:1, outputCount:1))

  return broadcast.BroadcastId

// BroadcastReady is dispatched by the handler after Save as an EXPLICIT in-process
// call to the Targeting Engine — NOT an event bus, NOT a background job.
```

### Service Interfaces

```
IPermissionService:
  GetPermissionSet(profileId: int) → PermissionSet

IBroadcastRepository:           // internal to Broadcast Service
  Save(broadcast: Broadcast) → void
  GetById(broadcastId: BroadcastId) → Broadcast?
```

### Method Signatures

```
Handle(CreateBroadcastCommand) → BroadcastId
Broadcast.Submit()             → void  (Draft → Submitted, emits BroadcastReady)
```

### Tests (from empty state)

```
TEST 1: Success
  permissionService: GetPermissionSet(1) → Roles=[CanSendBroadcast], IsStale=false
  → result is BroadcastId
  → saved broadcast.State = Submitted
  → BroadcastReady event emitted
  → PipelineTrace: [ValidatePermission Ok, CreateBroadcast Ok, SubmitBroadcast Ok]

TEST 2: Permission denied
  permissionService: GetPermissionSet(2) → Roles=[]
  → throws PermissionDeniedException
  → no broadcast saved
  → PipelineTrace: [ValidatePermission Failed(isRetryable=false)]

TEST 3: Stale permission (role present, IsStale=true)
  permissionService: GetPermissionSet(3) → Roles=[CanSendBroadcast], IsStale=true
  → proceeds normally (stale policy = Wave 9+ concern)
  → saved broadcast.State = Submitted
```

---

## SLICE 2 — Targeting (DK path only, no 1881)

### Domain Model (additions)

```
DeliveryTarget    : aggregate root
  DeliveryTargetId:  int  (auto-assigned)
  BroadcastId:       BroadcastId
  State:             DeliveryState  // = ReadyForDispatch on creation
  SourceType:        DeliverySource // = GeographicAddress
  Kvhx:              string         // non-null for geographic path
  PhoneCode:         string?        // null — phone resolution is a later slice (OBS 2)
  PhoneNumber:       string?        // null — phone resolution is a later slice (OBS 2)
  Priority:          DeliveryPriority
  RetryCount:        int            // = 0 on creation
```

### Command + Handler

```
TargetBroadcastCommand:
  BroadcastId: BroadcastId
  // RecipientSpec and AddressRestriction read from Broadcast aggregate

Handle(TargetBroadcastCommand cmd) → PipelineTrace

  // Called EXPLICITLY by BroadcastReady signal handler — NOT from event bus

  Step 1 — ReadRecipientSpec
    broadcast = IBroadcastRepository.GetById(cmd.BroadcastId)
    spec = broadcast.RecipientSpec
    trace.Add(PipelineStepResult.Ok("ReadRecipientSpec", inputCount:1, outputCount:1))

  Step 2 — ResolveAddresses
    result = IAddressService.GetAddressesByGeography(
               countryId=spec.CountryId, filter=spec.GeographicFilter,
               restriction=spec.AddressRestriction, customerId=broadcast.CustomerId)
    if result is Failed:
      trace.Add(result)
      return trace    // abort — caller may retry
    addresses = result.Value
    trace.Add(PipelineStepResult.Ok("ResolveAddresses", inputCount:1, outputCount:addresses.Count))

  Step 3 — FilterVirtualAddresses
    nonVirtual = addresses.Where(a => a.IsVirtual == false)
    // IsVirtual is an explicit field on AddressRecord — no hidden SQL exclusion
    trace.Add(PipelineStepResult.Ok("FilterVirtualAddresses",
               inputCount:addresses.Count, outputCount:nonVirtual.Count))

  Step 4 — ApplyAddressRestriction
    filtered = spec.AddressRestriction == None
               ? nonVirtual
               : nonVirtual.Where(a => criticalAddressIds.Contains(a.Kvhx))
    trace.Add(PipelineStepResult.Ok("ApplyAddressRestriction",
               inputCount:nonVirtual.Count, outputCount:filtered.Count))

  Step 5 — CreateDeliveryTargets
    targets = filtered.Select(addr => new DeliveryTarget(
                BroadcastId:  cmd.BroadcastId,
                State:        ReadyForDispatch,
                SourceType:   GeographicAddress,
                Kvhx:         addr.Kvhx,
                PhoneCode:    null,
                PhoneNumber:  null,
                Priority:     broadcast.Priority,
                RetryCount:   0))
    IDeliveryTargetRepository.SaveAll(targets)
    trace.Add(PipelineStepResult.Ok("CreateDeliveryTargets",
               inputCount:filtered.Count, outputCount:targets.Count))

  Step 6 — MarkBroadcastTargeted
    broadcast.MarkTargeted()    // Targeting → Targeted
    IBroadcastRepository.Save(broadcast)
    trace.Add(PipelineStepResult.Ok("MarkBroadcastTargeted", inputCount:1, outputCount:1))

  return trace
```

### Service Interfaces

```
IAddressService:
  GetAddressesByGeography(countryId, filter, restriction, customerId)
    → PipelineStepResult<IReadOnlyCollection<AddressRecord>>

IBroadcastRepository:
  GetById(broadcastId) → Broadcast

IDeliveryTargetRepository:    // internal to Targeting Engine
  SaveAll(targets: IEnumerable<DeliveryTarget>) → void
  GetById(deliveryTargetId: int) → DeliveryTarget?
```

### Method Signatures

```
Handle(TargetBroadcastCommand)  → PipelineTrace
Broadcast.MarkTargeted()        → void  (Targeting → Targeted)
DeliveryTarget constructor      → DeliveryTarget (state=ReadyForDispatch)
```

### Tests (from empty state)

```
TEST 1: Success (3 addresses, restriction=None, no virtual)
  addressService: returns [DK001 IsVirtual=false, DK002 IsVirtual=false, DK003 IsVirtual=false]
  → 3 DeliveryTargets saved: State=ReadyForDispatch, PhoneCode=null, PhoneNumber=null
  → broadcast.State = Targeted
  → PipelineTrace 6 steps all Ok
  → inputCount=3, outputCount=3 on CreateDeliveryTargets
  → NO ITeledataService calls

TEST 2: Virtual filtered (1 of 3 virtual)
  addressService: [DK001 false, DK002 true, DK003 false]
  → 2 DeliveryTargets saved (DK001, DK003)
  → FilterVirtualAddresses: {inputCount=3, outputCount=2}
  → CreateDeliveryTargets: {inputCount=2, outputCount=2}

TEST 3: Address Service fails (retryable)
  addressService: Failed("AddressServiceUnavailable", isRetryable=true)
  → 0 DeliveryTargets saved
  → broadcast.State unchanged
  → PipelineTrace aborted at step 2: [ReadRecipientSpec Ok, ResolveAddresses Failed(retryable)]

TEST 4: Empty result valid (0 recipients)
  addressService: Empty()
  → 0 DeliveryTargets saved
  → broadcast.State = Targeted  ← zero is valid, still transitions
  → CreateDeliveryTargets: {inputCount=0, outputCount=0, Ok}
```

---

## SLICE 3 — Dispatch Dry-Run

### Domain Model (additions)

```
ClaimResult  : enum  Ok | AlreadyClaimed | NotFound | Cancelled

DispatchResult : discriminated union
  Sent(gatewayRef: string, sentAtUtc: DateTime)
  Failed(reason: string, isRetryable: bool)
  Skipped(reason: string)

DeliveryLogEntry : value type (append-only)
  DeliveryTargetId:  int
  FromState:         DeliveryState
  ToState:           DeliveryState
  Action:            string
  TimestampUtc:      DateTime
```

### Command + Handler

```
ClaimAndSendCommand:
  DeliveryTargetId:  int
  DryRun:            bool

Handle(ClaimAndSendCommand cmd) → (DispatchResult, PipelineTrace)

  Step 1 — ClaimForDispatch
    claimResult = ITargetingEngine.ClaimForDispatch(cmd.DeliveryTargetId)
    // LOCK 1: this is the ONLY legal entry point into the dispatch lifecycle

    match claimResult:
      AlreadyClaimed → return (Skipped("AlreadyClaimed"), trace with Skipped)
      NotFound       → return (Failed("NotFound", isRetryable=false), trace with Failed)
      Cancelled      → return (Skipped("BroadcastCancelled"), trace with Skipped)
      Ok             → continue  // target.State = Claimed

    trace.Add(PipelineStepResult.Ok("ClaimForDispatch", inputCount:1, outputCount:1))

  Step 2 — ExecuteSend
    if cmd.DryRun == true:
      // OBS 1: MUST NOT transition to Sending
      // OBS 1: MUST NOT increment RetryCount
      // OBS 1: MUST NOT trigger DLR logic
      trace.Add(PipelineStepResult.Skipped("ExecuteSend", inputCount:1, outputCount:0, reason:"dryRun=true"))
      dispatchResult = DispatchResult.Skipped("dryRun=true")
    else:
      throw NotImplementedException("Live gateway dispatch is Wave 9+")

  Step 3 — LogTransition
    IDeliveryLogRepository.Append(new DeliveryLogEntry(
      DeliveryTargetId: cmd.DeliveryTargetId,
      FromState:        ReadyForDispatch,
      ToState:          Claimed,
      Action:           "DryRunSkipped",
      TimestampUtc:     DateTime.UtcNow))
    trace.Add(PipelineStepResult.Ok("LogTransition", inputCount:1, outputCount:1))

  return (dispatchResult, trace)
```

### Service Interfaces

```
ITargetingEngine:                     // cross-service — LOCK 1 enforcement
  ClaimForDispatch(deliveryTargetId: int) → ClaimResult

IDeliveryLogRepository:               // internal to Dispatch Service
  Append(entry: DeliveryLogEntry) → void
```

### Method Signatures

```
Handle(ClaimAndSendCommand)             → (DispatchResult, PipelineTrace)
ITargetingEngine.ClaimForDispatch(int)  → ClaimResult
IDeliveryLogRepository.Append(entry)    → void
```

### Tests (from empty state)

```
TEST 1: Success dry-run
  targetingEngine: ClaimForDispatch(42) → Ok
  → result = Skipped("dryRun=true")
  → DeliveryLog entry: {DeliveryTargetId=42, Action="DryRunSkipped", ToState=Claimed}
  → target.State = Claimed (NOT Sending)
  → RetryCount = 0 (unchanged)
  → No gateway call
  → PipelineTrace: [ClaimForDispatch Ok, ExecuteSend Skipped, LogTransition Ok]

TEST 2: AlreadyClaimed
  targetingEngine: ClaimForDispatch(42) → AlreadyClaimed
  → result = Skipped("AlreadyClaimed")
  → DeliveryLog: 0 entries
  → PipelineTrace: [ClaimForDispatch Skipped]

TEST 3: NotFound
  targetingEngine: ClaimForDispatch(99) → NotFound
  → result = Failed("NotFound", isRetryable=false)
  → DeliveryLog: 0 entries

TEST 4: Cancelled
  targetingEngine: ClaimForDispatch(42) → Cancelled
  → result = Skipped("BroadcastCancelled")
  → DeliveryLog: 0 entries

OBS 1 INVARIANT TESTS:
TEST 5: DryRun MUST NOT transition to Sending
  Assert: target.State == Claimed after DryRun=true

TEST 6: DryRun MUST NOT increment RetryCount
  Arrange: RetryCount=0
  Assert:  RetryCount==0 after DryRun=true

TEST 7: DryRun MUST NOT produce DLR event
  Assert:  no DLR callback raised after DryRun=true
```

---

## INVARIANTS CARRIED FORWARD (OBS from Wave 7)

| OBS | Invariant | Enforced in |
|---|---|---|
| OBS 1 | `dryRun=true` MUST NOT: transition to `Sending`, increment `RetryCount`, trigger DLR | Slice 3 Step 2 + Tests 5–7 |
| OBS 2 | `DeliveryTarget` valid with null `PhoneCode`/`PhoneNumber` — Teledata not in scope | Slice 2 domain model + Tests |
| OBS 3 | `BroadcastReady` = explicit orchestrator call, NOT event bus / background job | Slice 1 handler note |

---

**Last updated:** Wave 8 (2026-04-12)  
**Next:** Wave 9 — live gateway dispatch + phone resolution (after Architect approval)
