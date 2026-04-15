"""visual_intelligence_reporter.py — Layer 2.5 Visual Intelligence stats generator.

Reads data/visual_validation_registry.jsonl and produces sanitized artefacts
for the Architect Review Package:

  visual-intelligence/
    cache_index.jsonl               Sanitized registry — hashes + metadata, NO file paths
    stats/
      component_stability.json      Pass/fail ratio per screen_key (least stable first)
      failure_patterns.json         Failure breakdown by wave, device, top-failing screens

Called by Generate-ChatGPT-Package.ps1 before ZIP creation.

CLI usage (from analysis-tool root):
  python -m core.visual_intelligence_reporter \\
      --registry data/visual_validation_registry.jsonl \\
      --output-dir /tmp/visual-intelligence
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------

_STRIP_KEYS = {"artifacts"}
_PATH_KEYS = {"screenshotPath", "failuresPath", "analysisZipPath"}


def _sanitize_entry(entry: dict) -> dict:
    """Strip file-system paths; keep only hashes + metadata."""
    return {k: v for k, v in entry.items() if k not in _STRIP_KEYS}


# ---------------------------------------------------------------------------
# Registry reader
# ---------------------------------------------------------------------------

def _load_registry(registry_path: Path) -> List[dict]:
    """Read JSONL registry. Returns empty list if file missing or unreadable."""
    entries: List[dict] = []
    if not registry_path.exists():
        return entries
    with open(registry_path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                # corrupt line — skip silently (matches VisualDeltaCache behavior)
                pass
    return entries


# ---------------------------------------------------------------------------
# Stats builders
# ---------------------------------------------------------------------------

def _build_component_stability(entries: List[dict]) -> dict:
    """Per screen_key: total, pass, fail, passRate, stable (>=90%), lastResult."""
    screen_stats: Dict[str, dict] = defaultdict(
        lambda: {"total": 0, "pass": 0, "fail": 0, "last_result": "", "last_seen": ""}
    )

    for entry in entries:
        key = entry.get("screenKey", "unknown")
        s = screen_stats[key]
        s["total"] += 1
        result = entry.get("result", "")
        if result == "PASS":
            s["pass"] += 1
        elif result == "FAIL":
            s["fail"] += 1
        ts = entry.get("validatedAtUtc", "")
        if ts > s["last_seen"]:
            s["last_seen"] = ts
            s["last_result"] = result

    rows = []
    for screen_key, s in sorted(screen_stats.items()):
        pass_rate = round(s["pass"] / s["total"], 3) if s["total"] > 0 else 0.0
        rows.append({
            "screenKey":   screen_key,
            "total":       s["total"],
            "pass":        s["pass"],
            "fail":        s["fail"],
            "passRate":    pass_rate,
            "lastResult":  s["last_result"],
            "lastSeen":    s["last_seen"],
            "stable":      pass_rate >= 0.90,
        })

    # least stable first — easiest for Architect to spot problems
    rows.sort(key=lambda x: x["passRate"])

    return {
        "generatedAt":     datetime.now(timezone.utc).isoformat(),
        "totalScreens":    len(rows),
        "stableScreens":   sum(1 for r in rows if r["stable"]),
        "unstableScreens": sum(1 for r in rows if not r["stable"]),
        "screens":         rows,
    }


def _build_failure_patterns(entries: List[dict]) -> dict:
    """Failure breakdown: by wave, by device, top-10 failing screens."""
    fail_entries = [e for e in entries if e.get("result") == "FAIL"]

    wave_counts:        Dict[str, int] = defaultdict(int)
    device_counts:      Dict[str, int] = defaultdict(int)
    screen_fail_counts: Dict[str, int] = defaultdict(int)

    for e in fail_entries:
        wave_counts[e.get("wave", "unknown")] += 1
        device_counts[e.get("device", "unknown")] += 1
        screen_fail_counts[e.get("screenKey", "unknown")] += 1

    top_failing = sorted(screen_fail_counts.items(), key=lambda x: -x[1])[:10]

    total      = len(entries)
    total_pass = sum(1 for e in entries if e.get("result") == "PASS")
    total_fail = len(fail_entries)

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "totalValidations": total,
            "totalPass":        total_pass,
            "totalFail":        total_fail,
            "overallPassRate":  round(total_pass / total, 3) if total > 0 else 0.0,
        },
        "failuresByWave":      dict(sorted(wave_counts.items())),
        "failuresByDevice":    dict(sorted(device_counts.items())),
        "topFailingScreens":   [{"screenKey": k, "failCount": v} for k, v in top_failing],
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_visual_intelligence(
    registry_path: Path,
    output_dir: Path,
) -> dict:
    """
    Read registry JSONL and write Layer 2.5 artefacts to output_dir.

    Returns a summary dict: {"entries": N, "screens": N, "fail_entries": N}
    Works correctly even if registry_path does not exist (returns empty stats).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stats_dir = output_dir / "stats"
    stats_dir.mkdir(parents=True, exist_ok=True)

    entries = _load_registry(registry_path)

    # --- cache_index.jsonl (sanitized — no file paths) ---
    cache_index_path = output_dir / "cache_index.jsonl"
    with open(cache_index_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(_sanitize_entry(entry), ensure_ascii=False) + "\n")

    # --- stats/component_stability.json ---
    stability = _build_component_stability(entries)
    with open(stats_dir / "component_stability.json", "w", encoding="utf-8") as f:
        json.dump(stability, f, indent=2, ensure_ascii=False)

    # --- stats/failure_patterns.json ---
    patterns = _build_failure_patterns(entries)
    with open(stats_dir / "failure_patterns.json", "w", encoding="utf-8") as f:
        json.dump(patterns, f, indent=2, ensure_ascii=False)

    fail_count = sum(1 for e in entries if e.get("result") == "FAIL")
    return {
        "entries":     len(entries),
        "screens":     stability["totalScreens"],
        "fail_entries": fail_count,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Layer 2.5 visual intelligence stats")
    parser.add_argument("--registry",   default="data/visual_validation_registry.jsonl")
    parser.add_argument("--output-dir", default="visual-intelligence")
    args = parser.parse_args()

    result = generate_visual_intelligence(
        Path(args.registry),
        Path(args.output_dir),
    )
    print(f"Layer 2.5: {result['entries']} entries | {result['screens']} screens | {result['fail_entries']} failures")
    sys.exit(0)
