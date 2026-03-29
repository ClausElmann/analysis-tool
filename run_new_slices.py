"""Run only the 5 new slices: SLICE_3b, SLICE_12, SLICE_13, SLICE_14, SLICE_16."""
import sys
from core.execution_engine import ExecutionEngine, _KNOWN_SLICES

e = ExecutionEngine(
    solution_root="c:/Udvikling/sms-service",
    protocol_root="protocol",
    data_root="data",
    wiki_root="C:/Udvikling/SMS-service.wiki",
    csv_path="C:/Udvikling/analysis-tool/raw/data.csv",
    raw_root="C:/Udvikling/analysis-tool/raw",
    db_root="C:/Udvikling/sms-service/ServiceAlert.DB",
    label_path="C:/Udvikling/analysis-tool/raw/labels.json",
)

STOP_AT = {"SLICE_7"}

while True:
    state = e.load_state()
    cs = state.get("current_slice")
    if cs not in _KNOWN_SLICES or cs in STOP_AT:
        print(f"Stopped at: {cs}")
        break
    r = e.execute_next_slice()
    items = r.get("items_found", 0)
    status = r.get("status", "?")
    errs = r.get("errors", [])
    print(f"{r['slice']}: {status} | items={items} | errors={len(errs)}")
    for err in errs[:5]:
        print(f"  ERR: {err[:120]}")
