# GreenAI — Standard UI Blueprints

> Dette dokument er SYSTEM KERNEL.  
> Alle ændringer kræver Architect approval.  
> Ingen afvigelser tilladt under build.

**Status:** LOCKED — Architect approved  
**Dato:** 2026-04-23  
**Regel:** Hver story MÅ KUN bruge én blueprint. Ingen custom UI uden godkendelse.

---

## EXECUTION PATTERNS (OBLIGATORISKE — gælder ALLE blueprints)

### A. DATA LOADING

```csharp
// State fields (alle komponenter)
private IEnumerable<T> Items = [];
private bool isLoading = true;
private string? errorMessage;

protected override async Task OnInitializedAsync()
{
    isLoading = true;
    var result = await Mediator.Send(new GetXxxQuery(...));
    if (result.IsSuccess)
        Items = result.Value;
    else
        errorMessage = result.Error;
    isLoading = false;
}
```

### B. COMMAND FLOW (Submit)

```csharp
private async Task HandleSubmit()
{
    var result = await Mediator.Send(command);
    if (result.IsSuccess)
    {
        MudDialog.Close(DialogResult.Ok(true));
        await OnSuccess.InvokeAsync(); // reload parent list
    }
    else
    {
        errorMessage = result.Error; // vis via MudAlert
    }
}
```

### C. STANDARD EVENTS

```csharp
// List page callback handlers
private void OnCreate() => OpenDialog(null);
private void OnEdit(T item) => OpenDialog(item);
private async Task OnDelete(T item)
{
    var confirmed = await ConfirmDeleteDialog.ShowAsync(item.Name);
    if (!confirmed) return;
    var result = await Mediator.Send(new DeleteXxxCommand(item.Id));
    if (result.IsSuccess) await Reload();
    else errorMessage = result.Error;
}
```

### D. RESULT<T> REGEL

```csharp
// ✅ KORREKT
var result = await Mediator.Send(query);
if (!result.IsSuccess) { errorMessage = result.Error; return; }

// ❌ FORBUDT
try { ... } catch (Exception ex) { ... }
```

### E. NO GUESS REGEL

Hvis DTO-felter, Query-parametre eller Command-properties ikke kendes:  
→ **STOP — returnér `UNKNOWN` og bed om afklaring**  
Copilot må ALDRIG antage feltnavne, typer eller parametre.

### F. GRID RELOAD PATTERN

```csharp
private async Task Reload()
{
    isLoading = true;
    var result = await Mediator.Send(new GetXxxQuery(...));
    if (result.IsSuccess) Items = result.Value;
    isLoading = false;
    StateHasChanged();
}
```

---

## 1. LIST PAGE

**Bruges til:** CRUD lists (fx US-001, US-002)

```
┌─────────────────────────────────────────┐
│ Toolbar: [Search]          [+ Create]   │
├─────────────────────────────────────────┤
│ AppDataGrid                             │
│  Columns: dynamisk fra DTO              │
│  Row actions: [Edit] [Delete]           │
│  Paging + sorting                       │
└─────────────────────────────────────────┘
```

**Komponenter:**
- `AppDataGrid` (wrapper)
- `MudTextField` (search)
- `MudButton` (create → åbner form dialog)
- `MudIconButton` per row: Edit, Delete
- `ConfirmDeleteDialog` ved sletning
- `MudAlert` ved errorMessage != null

**State:**
```csharp
private IEnumerable<XxxDto> Items = [];
private bool isLoading = true;
private string? errorMessage;
private string searchTerm = "";
```

**Loading:** Execution Pattern A  
**Events:** Execution Pattern C  
**Sletning:** Execution Pattern D

---

## 2. FORM PAGE / DIALOG

**Bruges til:** Create + Edit (alle CRUD stories)

```
┌─────────────────────────────────────────┐
│ BaseFormDialog                          │
│  MudForm                                │
│   [Field 1]                             │
│   [Field 2]                             │
│   ...                                   │
│  [MudAlert hvis errorMessage]           │
│  [Cancel]              [Submit]         │
└─────────────────────────────────────────┘
```

**Komponenter:**
- `BaseFormDialog` (wrapper)
- `MudForm` + `MudTextField`, `MudSelect` etc.
- FluentValidation regler bindes via `@ref` + `Validate()`
- Submit → Execution Pattern B
- Cancel → `MudDialog.Cancel()`

**State:**
```csharp
private XxxCommand command = new();
private bool isLoading = false;
private string? errorMessage;
MudForm form = null!;
```

---

## 3. DETAILS PAGE

**Bruges til:** Read-only visning af enkelt entitet

```
┌─────────────────────────────────────────┐
│ MudPaper (section 1)                    │
│  [Field: Value]  [Field: Value]         │
├─────────────────────────────────────────┤
│ MudPaper (section 2) / MudTabs          │
│  ...                                    │
└─────────────────────────────────────────┘
```

**Komponenter:**
- `MudPaper` per sektion
- `MudTabs` ved komplekse detaljer
- Ingen edit-inputs — kun display
- Data via `IMediator.Send(Query)` — Execution Pattern A

**State:**
```csharp
private XxxDto? Item;
private bool isLoading = true;
private string? errorMessage;
```

---

## 4. MESSAGING UI

**Bruges til:** US-038 (beskeder/notifikationer)

```
┌──────────────┬──────────────────────────┐
│ Liste        │ Conversation view        │
│ [item 1]     │  [msg 1]                 │
│ [item 2]     │  [msg 2]                 │
│              │                          │
│              │ [Input box]   [Send →]   │
│              │ Status: [0–4 mapping]    │
└──────────────┴──────────────────────────┘
```

**Komponenter:**
- `MudList` (venstre panel)
- `MudPaper` (conversation view, højre)
- `MudTextField` + `MudIconButton` (send)
- Status mapping: 0=Draft, 1=Queued, 2=Sent, 3=Delivered, 4=Failed

**State:**
```csharp
private IEnumerable<MessageDto> Messages = [];
private MessageDto? Selected;
private bool isLoading = true;
private string? errorMessage;
private string inputText = "";
```

Send → Execution Pattern B (Command + reload conversation)

---

## 5. AUTH UI

**Bruges til:** GS-001 (Login)

```
┌─────────────────────────────────────────┐
│ Login form                              │
│  [Username]                             │
│  [Password]                             │
│  [MudAlert hvis errorMessage]           │
│               [Login]                   │
└─────────────────────────────────────────┘
```

**Komponenter:**
- `MudForm` + `MudTextField`
- Token håndtering via auth-service (ikke i component)
- Redirect efter login via `NavigationManager`
- Fejl vises inline via `MudAlert` (ikke toast)

**State:**
```csharp
private LoginCommand command = new();
private bool isLoading = false;
private string? errorMessage;
```

Submit → Execution Pattern B (success → `NavigationManager.NavigateTo("/")`)

---

## 6. BLUEPRINT OVERSIGT

| Blueprint | Bruges til |
|-----------|-----------|
| LIST PAGE | US-001, US-002, US-003, US-004, US-005, US-006, US-007, US-008 |
| FORM PAGE | Alle create/edit i CRUD stories |
| DETAILS PAGE | Stories med read-only detaljevisning |
| MESSAGING UI | US-038 |
| AUTH UI | GS-001 |

---

## 7. REGLER

- ✅ Alle stories vælger én blueprint inden implementering starter
- ✅ AppDataGrid og BaseFormDialog SKAL bygges (WAVE 1) inden WAVE 2
- ✅ Execution Patterns A–F er obligatoriske — ingen afvigelser
- ✅ NO GUESS REGEL: STOP ved ukendt DTO/Query/Command
- ❌ Ingen custom layouts uden Architect-godkendelse
- ❌ Ingen inline CSS — kun MudBlazor props + globale CSS-variabler
- ❌ Ingen direkte exceptions — ALT via `Result<T>`

```
┌─────────────────────────────────────────┐
│ Toolbar: [Search]          [+ Create]   │
├─────────────────────────────────────────┤
│ AppDataGrid                             │
│  Columns: dynamisk fra DTO              │
│  Row actions: [Edit] [Delete]           │
│  Paging + sorting                       │
└─────────────────────────────────────────┘
```

**Komponenter:**
- `AppDataGrid` (wrapper)
- `MudTextField` (search)
- `MudButton` (create → åbner form dialog)
- `MudIconButton` per row: Edit, Delete
- `ConfirmDeleteDialog` ved sletning

---

## 2. FORM PAGE / DIALOG

**Bruges til:** Create + Edit (alle CRUD stories)

```
┌─────────────────────────────────────────┐
│ BaseFormDialog                          │
│  MudForm                                │
│   [Field 1]                             │
│   [Field 2]                             │
│   ...                                   │
│  [Cancel]              [Submit]         │
└─────────────────────────────────────────┘
```

**Komponenter:**
- `BaseFormDialog` (wrapper)
- `MudForm` + `MudTextField`, `MudSelect` etc.
- FluentValidation regler bindes via `@ref` + `Validate()`
- Submit → `IMediator.Send(Command)` → `Result<T>`
- Cancel → lukker dialog uden side-effects

---

## 3. DETAILS PAGE

**Bruges til:** Read-only visning af enkelt entitet

```
┌─────────────────────────────────────────┐
│ MudPaper (section 1)                    │
│  [Field: Value]  [Field: Value]         │
├─────────────────────────────────────────┤
│ MudPaper (section 2) / MudTabs          │
│  ...                                    │
└─────────────────────────────────────────┘
```

**Komponenter:**
- `MudPaper` per sektion
- `MudTabs` ved komplekse detaljer
- Ingen edit-inputs — kun display
- Data via `IMediator.Send(Query)`

---

## 4. MESSAGING UI

**Bruges til:** US-038 (beskeder/notifikationer)

```
┌──────────────┬──────────────────────────┐
│ Liste        │ Conversation view        │
│ [item 1]     │  [msg 1]                 │
│ [item 2]     │  [msg 2]                 │
│              │                          │
│              │ [Input box]   [Send →]   │
│              │ Status: [0–4 mapping]    │
└──────────────┴──────────────────────────┘
```

**Komponenter:**
- `MudList` (venstre panel)
- `MudPaper` (conversation view, højre)
- `MudTextField` + `MudIconButton` (send)
- Status mapping: 0=Draft, 1=Queued, 2=Sent, 3=Delivered, 4=Failed

---

## 5. AUTH UI

**Bruges til:** GS-001 (Login)

```
┌─────────────────────────────────────────┐
│ Login form                              │
│  [Username]                             │
│  [Password]                             │
│               [Login]                   │
└─────────────────────────────────────────┘
```

**Komponenter:**
- `MudForm` + `MudTextField`
- Token håndtering via auth-service (ikke i component)
- Redirect efter login via `NavigationManager`
- Fejl vises inline (ikke toast)

---

## 6. BLUEPRINT OVERSIGT

| Blueprint | Bruges til |
|-----------|-----------|
| LIST PAGE | US-001, US-002, US-003, US-004, US-005, US-006, US-007, US-008 |
| FORM PAGE | Alle create/edit i CRUD stories |
| DETAILS PAGE | Stories med read-only detaljevisning |
| MESSAGING UI | US-038 |
| AUTH UI | GS-001 |

---

## 7. REGLER

- ✅ Alle stories vælger én blueprint inden implementering starter
- ✅ AppDataGrid og BaseFormDialog SKAL bygges (WAVE 1) inden WAVE 2
- ❌ Ingen custom layouts uden Architect-godkendelse
- ❌ Ingen inline CSS — kun MudBlazor props + globale CSS-variabler
