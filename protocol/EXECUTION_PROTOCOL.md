# Execution Protocol – Analysis Tool

## PURPOSE

This protocol defines how the system executes analysis in autonomous slices.

The system MUST NOT rely on chat prompts.
All behavior must be driven by this protocol and persisted state.

---

## EXECUTION MODEL

Each run performs exactly ONE slice.

Flow:

1. Read state.json
2. Determine current slice
3. Execute slice
4. Write result to disk
5. Write log entry
6. Update state.json
7. STOP

---

## STATE FILE

File: protocol/state.json

Structure:

{
"current_slice": "SLICE_1",
"completed_slices": [],
"status": "READY",
"last_run": null
}

---

## SLICE DEFINITIONS

### SLICE_1 – Angular Entry Detection

OUTPUT:
data/angular_entries.json

REQUIREMENTS:

* detect routes
* detect menu if present
* map to components

---

### SLICE_2 – Angular → API Mapping

INPUT:
angular_entries.json

OUTPUT:
data/component_api_map.json

---

### SLICE_3 – Use Case Creation

INPUT:
component_api_map.json

OUTPUT:
data/use-cases.analysis.json

---

### SLICE_4 – Coverage

INPUT:
use-cases.analysis.json

OUTPUT:
data/coverage.json

---

### SLICE_5 – Data Model Extraction

OUTPUT:
data/data-model.json

---

## RULES

* Only one slice per run
* Never skip slices
* Never overwrite previous slice output unless specified
* All outputs must be deterministic
* No null values
* If uncertain → write UNKNOWN

---

## LOGGING

Each run must create:

protocol/logs/{timestamp}.md

Content:

* slice executed
* files changed
* summary
* verification result
* errors (if any)

---

## FAILURE HANDLING

If a slice fails:

* write log with FAILED
* update state.json:
  "status": "FAILED"
* STOP

---

## COMPLETION

When all slices complete:

state.json:

{
"status": "DONE"
}

---

END
