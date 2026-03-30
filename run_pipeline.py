"""Run the full pipeline and print a summary.

Usage:
    python run_pipeline.py [--reset]

Options:
    --reset   Restart pipeline from SLICE_0 (rewrites state.json)
"""
import json
import os
import sys

from core.execution_engine import ExecutionEngine, PIPELINE_ORDER

SOLUTION_ROOT  = "c:/Udvikling/sms-service"
PROTOCOL_ROOT  = "protocol"
DATA_ROOT      = "data"
WIKI_ROOT      = "C:/Udvikling/SMS-service.wiki"
CSV_PATH       = "C:/Udvikling/analysis-tool/raw/data.csv"
RAW_ROOT       = "C:/Udvikling/analysis-tool/raw"
DB_ROOT        = "C:/Udvikling/sms-service/ServiceAlert.DB"
LABEL_PATH     = "C:/Udvikling/analysis-tool/raw/labels.json"

# Required output files and the primary count key for each
REQUIRED_FILES = {
    "solution_structure.json":  "projects",
    "wiki_signals.json":        "capabilities",
    "pdf_capabilities.json":    "capabilities",
    "git_insights.json":        "insights",
    "db_schema.json":           "tables",
    "label_map.json":           "namespaces",
    "angular_entries.json":     "entry_points",
    "angular_apps.json":        "apps",
    "mvc_routes.json":          "mvc_routes",
    "component_api_map.json":   "mappings",
    "api_db_map.json":          "mappings",
    "webhook_map.json":         "webhooks",
    "background_services.json": "services",
    "batch_jobs.json":          "jobs",
    "event_map.json":           "events",
    "integrations.json":        "integrations",
    "realtime_map.json":        "streams",
    "rabbitmq_topology.json":   "connections",
    "work_item_analysis.json":  "features",
    "system_model.json":        "modules",
    "system_model_extended.json": "modules",
    "use-cases.analysis.json":  "use_cases",
    "use-cases.selection.json": "use_cases",
    "gap_analysis.json":        "gaps",
}


def _reset_state():
    """Write a clean state.json starting at SLICE_0."""
    os.makedirs(PROTOCOL_ROOT, exist_ok=True)
    state = {
        "current_slice": "SLICE_0",
        "completed_slices": [],
        "status": "READY",
        "last_run": None,
    }
    path = os.path.join(PROTOCOL_ROOT, "state.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
    print(f"State reset → SLICE_0")


def _build_final_report():
    """Collect metrics from output files and return the final report dict."""
    files_info = []
    for fname, key in REQUIRED_FILES.items():
        fp = os.path.join(DATA_ROOT, fname)
        exists = os.path.isfile(fp)
        items = 0
        if exists:
            try:
                with open(fp, encoding="utf-8") as fh:
                    d = json.load(fh)
                items = len(d.get(key, d.get(list(d.keys())[0], []))) if d else 0
            except Exception:
                pass
        files_info.append({"name": fname, "exists": exists, "items": items})

    def _count(fname, key):
        fp = os.path.join(DATA_ROOT, fname)
        if not os.path.isfile(fp):
            return 0
        try:
            with open(fp, encoding="utf-8") as fh:
                d = json.load(fh)
            return len(d.get(key, []))
        except Exception:
            return 0

    metrics = {
        "projects":   _count("solution_structure.json", "projects"),
        "routes":     _count("angular_entries.json", "entry_points"),
        "apis":       _count("api_db_map.json", "mappings"),
        "db_tables":  _count("db_schema.json", "tables"),
        "modules":    _count("system_model.json", "modules"),
        "use_cases":  _count("use-cases.analysis.json", "use_cases"),
        "gaps":       _count("gap_analysis.json", "gaps"),
    }

    all_exist = all(f["exists"] for f in files_info)
    uc_ok  = metrics["use_cases"] > 10
    mod_ok = metrics["modules"] > 10
    status = "READY_FOR_AUDIT" if (all_exist and uc_ok and mod_ok) else "INCOMPLETE"

    return {
        "files":   sorted(files_info, key=lambda f: f["name"]),
        "metrics": metrics,
        "status":  status,
    }


if __name__ == "__main__":
    if "--reset" in sys.argv:
        _reset_state()

    engine = ExecutionEngine(
        solution_root=SOLUTION_ROOT,
        protocol_root=PROTOCOL_ROOT,
        data_root=DATA_ROOT,
        wiki_root=WIKI_ROOT,
        csv_path=CSV_PATH,
        raw_root=RAW_ROOT,
        db_root=DB_ROOT,
        label_path=LABEL_PATH,
    )

    results = engine.run_full_pipeline()

    print("\n=== PIPELINE SUMMARY ===")
    for r in results:
        print(f"{r['slice']} → {r['status']} ({r['duration']}s)")

    print()
    print("=== OUTPUT FILES ===")
    for fname, key in REQUIRED_FILES.items():
        fp = os.path.join(DATA_ROOT, fname)
        exists = os.path.isfile(fp)
        if not exists:
            print(f"  MISSING  {fname}")
            continue
        try:
            with open(fp, encoding="utf-8") as fh:
                d = json.load(fh)
            count = len(d.get(key, d.get(list(d.keys())[0], []))) if d else 0
            print(f"  OK       {fname}: {count} {key}")
        except Exception as exc:
            print(f"  ERROR    {fname}: {exc}")

    # Write final_report.json
    final = _build_final_report()
    report_path = os.path.join(DATA_ROOT, "final_report.json")
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(final, fh, indent=2, ensure_ascii=False)
    print()
    print(f"final_report.json → status={final['status']}")
    print(json.dumps(final["metrics"], indent=2))
