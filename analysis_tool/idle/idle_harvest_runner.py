"""analysis_tool/idle/idle_harvest_runner.py

DFEP-Driven Idle Harvest Loop — v1

Governance rules (MANDATORY):
  - DFEP v3 is the ONLY driver — never harvest without a gap
  - MAX 3 targets per run
  - MAX 2 iterations without improvement before STOP
  - Improvement threshold: match_score delta >= 0.05 to continue
  - NO overwrite of existing facts (append-only)
  - NO run without a valid DFEP snapshot as input

CLI (Run 1 — generate prompts):
  python -m analysis_tool.idle.idle_harvest_runner --domain Templates

CLI (Run 2 — process responses):
  python -m analysis_tool.idle.idle_harvest_runner --domain Templates \\
      --responses-dir analysis/dfep/responses/idle

Flow:
  Run 1:
    1. Load latest DFEP snapshot for domain
    2. Identify gaps (HIGH missing + LOW confidence + UNKNOWN flows)
    3. Select MAX 3 targets by priority
    4. Generate 1 targeted harvest prompt per target
    5. Write prompts to analysis/dfep/prompts/idle/
    6. STOP — tell user to send prompts to Copilot + save responses

  Run 2 (--responses-dir provided):
    7. Read Copilot responses from responses-dir
    8. Run targeted extractor → merge into domain facts file
    9. Re-run DFEP v3 phase2 (using existing l0/ga response files + re-extracted GA)
   10. Compare before/after match_score
   11. Print IdleHarvestResult
   12. STOP if improvement < 0.05 OR iteration >= 2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Root resolution
_IDLE_DIR = Path(__file__).parent
_TOOL_ROOT = _IDLE_DIR.parent.parent
sys.path.insert(0, str(_TOOL_ROOT))

from dfep_v3.output.drift_tracker import DomainSnapshot
from analysis_tool.idle.gap_prompt_generator import GapPromptGenerator
from analysis_tool.idle.result_comparator import ResultComparator, IdleHarvestResult

# ---------------------------------------------------------------------------
# Constants + safety limits
# ---------------------------------------------------------------------------

MAX_TARGETS_PER_RUN = 3
MAX_ITERATIONS = 2
MIN_IMPROVEMENT_THRESHOLD = 0.05   # match_score delta required to continue

_DEFAULT_SNAPSHOTS = str(_TOOL_ROOT / "analysis" / "dfep" / "snapshots")
_DEFAULT_PROMPTS_DIR = str(_TOOL_ROOT / "analysis" / "dfep" / "prompts" / "idle")
_DEFAULT_RESPONSES_DIR = str(_TOOL_ROOT / "analysis" / "dfep" / "responses" / "idle")
_DEFAULT_RESPONSES_BASE = str(_TOOL_ROOT / "analysis" / "dfep" / "responses")

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class HarvestTarget:
    """A single capability gap selected for targeted harvesting."""
    capability_id: str
    gap_type: str           # "HIGH_GAP" | "LOW_CONFIDENCE" | "UNKNOWN_FLOW"
    reason: str
    priority: int           # 1 = highest
    capability_intent: str  # from snapshot or comparison JSON (for prompt generation)
    confidence: float = 0.0


@dataclass
class IdleHarvestPlan:
    """Describes what this harvest run will target."""
    domain: str
    run_date: str
    targets: list[HarvestTarget] = field(default_factory=list)
    iteration: int = 1      # which iteration this is (max = MAX_ITERATIONS)
    prior_match_score: float = 0.0
    snapshot_date: str = ""

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "run_date": self.run_date,
            "iteration": self.iteration,
            "prior_match_score": self.prior_match_score,
            "snapshot_date": self.snapshot_date,
            "targets": [
                {
                    "capability_id": t.capability_id,
                    "gap_type": t.gap_type,
                    "reason": t.reason,
                    "priority": t.priority,
                    "capability_intent": t.capability_intent,
                    "confidence": t.confidence,
                }
                for t in self.targets
            ],
        }


# ---------------------------------------------------------------------------
# Plan builder — reads DFEP snapshot + comparison JSON
# ---------------------------------------------------------------------------


class HarvestPlanBuilder:
    """
    Reads the latest DFEP snapshot for a domain and builds an IdleHarvestPlan.

    Priority ordering:
      1. HIGH/CRITICAL capability gaps (missing entirely)
      2. LOW confidence capabilities (< 0.65)
      3. UNKNOWN flows (is_unknown == True in capability response)
    """

    def __init__(
        self,
        snapshots_dir: str = _DEFAULT_SNAPSHOTS,
        responses_dir: str = _DEFAULT_RESPONSES_BASE,
    ):
        self._snapshots_dir = snapshots_dir
        self._responses_dir = responses_dir

    def build(self, domain: str) -> IdleHarvestPlan:
        snapshot = self._load_snapshot(domain)
        cmp_data = self._load_comparison(domain)
        l0_data = self._load_l0_capabilities(domain)

        targets: list[HarvestTarget] = []
        priority = 1

        # 1. HIGH/CRITICAL missing gaps — from snapshot missing_ids + comparison severity
        missing_ids = set(snapshot.get("missing_ids", []))
        high_ids = self._get_high_missing_ids(cmp_data)

        for cap_id in high_ids:
            if len(targets) >= MAX_TARGETS_PER_RUN:
                break
            intent = self._get_intent(cap_id, l0_data, cmp_data)
            targets.append(HarvestTarget(
                capability_id=cap_id,
                gap_type="HIGH_GAP",
                reason=f"Missing HIGH-severity capability: {intent[:80]}",
                priority=priority,
                capability_intent=intent,
            ))
            priority += 1

        # 2. LOW confidence — from L0 capability response
        if len(targets) < MAX_TARGETS_PER_RUN:
            low_conf = self._get_low_confidence(l0_data)
            for cap_id, conf in low_conf:
                if len(targets) >= MAX_TARGETS_PER_RUN:
                    break
                intent = self._get_intent(cap_id, l0_data, cmp_data)
                targets.append(HarvestTarget(
                    capability_id=cap_id,
                    gap_type="LOW_CONFIDENCE",
                    reason=f"L0 capability confidence {conf:.0%} < 65% — evidence likely incomplete",
                    priority=priority,
                    capability_intent=intent,
                    confidence=conf,
                ))
                priority += 1

        # 3. UNKNOWN flows — L0 caps with is_unknown == True
        if len(targets) < MAX_TARGETS_PER_RUN:
            unknowns = self._get_unknowns(l0_data)
            for cap_id in unknowns:
                if len(targets) >= MAX_TARGETS_PER_RUN:
                    break
                intent = self._get_intent(cap_id, l0_data, cmp_data)
                targets.append(HarvestTarget(
                    capability_id=cap_id,
                    gap_type="UNKNOWN_FLOW",
                    reason="Capability marked as UNKNOWN — flow cannot be verified from extracted facts",
                    priority=priority,
                    capability_intent=intent,
                ))
                priority += 1

        plan = IdleHarvestPlan(
            domain=domain,
            run_date=datetime.now().strftime("%Y-%m-%d"),
            targets=targets,
            prior_match_score=float(snapshot.get("match_score", 0.0)),
            snapshot_date=str(snapshot.get("date", "unknown")),
        )
        return plan

    # --- Loaders ---

    def _load_snapshot(self, domain: str) -> dict:
        path = os.path.join(self._snapshots_dir, f"{domain.lower()}_snapshot.json")
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"No DFEP snapshot found for domain '{domain}' at: {path}\n"
                "Run DFEP v3 first: python -m dfep_v3.engine.dfep_runner --domain {domain} --parse-response ..."
            )
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _load_comparison(self, domain: str) -> dict:
        path = os.path.join(self._responses_dir, f"{domain.lower()}_comparison.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _load_l0_capabilities(self, domain: str) -> dict:
        path = os.path.join(self._responses_dir, f"{domain.lower()}_l0.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    # --- Selectors ---

    def _get_high_missing_ids(self, cmp_data: dict) -> list[str]:
        result = []
        for c in cmp_data.get("comparisons", []):
            match = c.get("match", "")
            severity = c.get("severity", "LOW")
            if match in ("MISSING", "false") and severity in ("HIGH", "CRITICAL"):
                result.append(c.get("l0_capability_id", ""))
        return [x for x in result if x]

    def _get_low_confidence(self, l0_data: dict) -> list[tuple[str, float]]:
        result = []
        for cap in l0_data.get("capabilities", []):
            conf = float(cap.get("confidence", 1.0))
            if conf < 0.65:
                result.append((cap.get("id", ""), conf))
        return [(cap_id, conf) for cap_id, conf in result if cap_id]

    def _get_unknowns(self, l0_data: dict) -> list[str]:
        return [
            cap.get("id", "")
            for cap in l0_data.get("capabilities", [])
            if cap.get("is_unknown", False)
        ]

    def _get_intent(self, cap_id: str, l0_data: dict, cmp_data: dict) -> str:
        # Try L0 capabilities first
        for cap in l0_data.get("capabilities", []):
            if cap.get("id") == cap_id:
                return str(cap.get("intent", cap_id))
        # Try comparison difference field
        for c in cmp_data.get("comparisons", []):
            if c.get("l0_capability_id") == cap_id:
                return str(c.get("difference", cap_id)[:120])
        return cap_id


# ---------------------------------------------------------------------------
# Domain Selector — finds highest-priority domain automatically
# ---------------------------------------------------------------------------


@dataclass
class DomainStatus:
    domain: str
    match_score: float
    missing_count: int
    high_gap_count: int
    gate_verdict: str
    snapshot_date: str
    has_pending_responses: bool  # idle response files exist but not yet processed


class DomainSelector:
    """
    Scans all DFEP snapshots and ranks domains by harvest priority.

    Priority ordering (highest first):
      1. Domains with pending idle responses (harvest started, not finished)
      2. Domains with FAILED gate + highest HIGH gap count
      3. Domains with FAILED gate + lowest match_score

    Skips domains with no snapshot (run DFEP v3 first).
    """

    def __init__(
        self,
        snapshots_dir: str = _DEFAULT_SNAPSHOTS,
        responses_dir: str = _DEFAULT_RESPONSES_BASE,
        idle_responses_dir: str = _DEFAULT_RESPONSES_DIR,
    ):
        self._snapshots_dir = snapshots_dir
        self._responses_dir = responses_dir
        self._idle_responses_dir = idle_responses_dir

    def select(self) -> DomainStatus | None:
        """Return the highest-priority domain to harvest, or None if nothing to do."""
        statuses = self._load_all()
        if not statuses:
            return None

        # 1. Pending responses first — finish what was started
        pending = [s for s in statuses if s.has_pending_responses]
        if pending:
            return pending[0]

        # 2. Failed domains — sort by high_gap_count desc, then match_score asc
        failed = [s for s in statuses if s.gate_verdict == "FAILED"]
        if not failed:
            return None  # all domains passing — nothing to harvest

        failed.sort(key=lambda s: (-s.high_gap_count, s.match_score))
        return failed[0]

    def print_status(self) -> None:
        """Print a status table of all known domains."""
        statuses = self._load_all()
        if not statuses:
            print("No DFEP snapshots found. Run DFEP v3 first.")
            return

        print(f"\n{'Domain':<20} {'Score':>6} {'Gate':<8} {'HIGH':>5} {'Missing':>8} {'Snapshot':<12} {'Pending'}")
        print("-" * 75)
        for s in sorted(statuses, key=lambda x: x.match_score):
            pending_str = "⚠ responses waiting" if s.has_pending_responses else ""
            gate_icon = "✅" if s.gate_verdict == "PASSED" else "❌"
            print(
                f"{s.domain:<20} {s.match_score:>5.0%} {gate_icon} {s.gate_verdict:<7} "
                f"{s.high_gap_count:>5} {s.missing_count:>8} {s.snapshot_date:<12} {pending_str}"
            )
        print()

    def _load_all(self) -> list[DomainStatus]:
        if not os.path.isdir(self._snapshots_dir):
            return []

        statuses: list[DomainStatus] = []
        for snap_file in Path(self._snapshots_dir).glob("*_snapshot.json"):
            try:
                with open(snap_file, encoding="utf-8") as f:
                    snap = json.load(f)

                domain = snap.get("domain", snap_file.stem.replace("_snapshot", "").title())

                # Check for pending idle responses
                pending = False
                if os.path.isdir(self._idle_responses_dir):
                    resp_files = list(
                        Path(self._idle_responses_dir).glob(
                            f"{domain.lower()}_*_harvest_response.json"
                        )
                    )
                    pending = any(f.stat().st_size > 10 for f in resp_files)

                # Count HIGH gaps from comparison JSON
                high_count = self._count_high_gaps(domain)

                statuses.append(DomainStatus(
                    domain=domain,
                    match_score=float(snap.get("match_score", 0.0)),
                    missing_count=int(snap.get("missing", 0)),
                    high_gap_count=high_count,
                    gate_verdict=str(snap.get("gate_verdict", "FAILED")),
                    snapshot_date=str(snap.get("date", "unknown")),
                    has_pending_responses=pending,
                ))
            except Exception:
                pass  # skip corrupt snapshots silently

        return statuses

    def _count_high_gaps(self, domain: str) -> int:
        cmp_path = os.path.join(self._responses_dir, f"{domain.lower()}_comparison.json")
        if not os.path.exists(cmp_path):
            return 0
        try:
            with open(cmp_path, encoding="utf-8") as f:
                data = json.load(f)
            return sum(
                1 for c in data.get("comparisons", [])
                if c.get("severity") in ("HIGH", "CRITICAL")
                and c.get("match") in ("MISSING", "false", "INTENT_DRIFT")
            )
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# Idle Harvest Runner — orchestrates the full loop
# ---------------------------------------------------------------------------


class IdleHarvestRunner:
    """
    Orchestrates one iteration of the gap-driven idle harvest loop.

    Safety rules enforced here:
      - STOP if no targets found (nothing to harvest)
      - STOP after MAX_ITERATIONS without MIN_IMPROVEMENT_THRESHOLD gain
      - NO run without valid DFEP snapshot
      - Prompts written to file — user sends to Copilot manually
    """

    def __init__(
        self,
        domain: str,
        snapshots_dir: str = _DEFAULT_SNAPSHOTS,
        prompts_dir: str = _DEFAULT_PROMPTS_DIR,
        responses_dir_base: str = _DEFAULT_RESPONSES_BASE,
        idle_responses_dir: str = _DEFAULT_RESPONSES_DIR,
    ):
        self.domain = domain
        self.snapshots_dir = snapshots_dir
        self.prompts_dir = prompts_dir
        self.responses_dir_base = responses_dir_base
        self.idle_responses_dir = idle_responses_dir

    def run_phase1_generate(self) -> IdleHarvestPlan:
        """
        Phase 1: Read snapshot → select targets → write prompts.
        Returns the plan. Exits if no targets.
        """
        print(f"\n{'=' * 60}")
        print(f"Idle Harvest Loop — Phase 1: Plan & Generate Prompts")
        print(f"Domain: {self.domain}")
        print(f"{'=' * 60}\n")

        print(f"[1/3] Loading DFEP snapshot...")
        builder = HarvestPlanBuilder(
            snapshots_dir=self.snapshots_dir,
            responses_dir=self.responses_dir_base,
        )
        plan = builder.build(self.domain)

        print(f"      Prior match score: {plan.prior_match_score:.0%}  (snapshot: {plan.snapshot_date})")
        print(f"      Targets selected: {len(plan.targets)}")

        # Safety guard: no targets → nothing to harvest
        if not plan.targets:
            print("\n[STOP] No harvest targets found.")
            print("  Possible reasons:")
            print("  - No HIGH gaps in domain (check DFEP report)")
            print("  - All capabilities have confidence >= 0.65")
            print("  - Domain is passing (match_score >= 90%)")
            print("  Re-run DFEP to refresh gaps before harvesting.")
            return plan

        for t in plan.targets:
            print(f"  → [{t.gap_type}] {t.capability_id} (priority {t.priority}): {t.reason[:70]}")

        print(f"\n[2/3] Generating targeted harvest prompts (max {MAX_TARGETS_PER_RUN})...")
        os.makedirs(self.prompts_dir, exist_ok=True)

        gen = GapPromptGenerator()
        prompt_files: list[str] = []
        for target in plan.targets:
            slug = target.capability_id.lower().replace(" ", "_")
            prompt_path = os.path.join(
                self.prompts_dir,
                f"{self.domain.lower()}_{slug}_harvest.md"
            )
            gen.generate(target=target, domain=self.domain, output_path=prompt_path)
            prompt_files.append(prompt_path)
            print(f"      Written: {prompt_path}")

        # Save plan to disk (for run 2 to read)
        plan_path = self._plan_path()
        os.makedirs(os.path.dirname(plan_path), exist_ok=True)
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n[3/3] Plan saved: {plan_path}")

        print(f"\n{'=' * 60}")
        print(f"NEXT STEP — Send prompts to Copilot:")
        for pf in prompt_files:
            print(f"  {pf}")
        print(f"\nSave Copilot responses as JSON to:")
        print(f"  {self.idle_responses_dir}/")
        print(f"\nExpected filenames:")
        for t in plan.targets:
            slug = t.capability_id.lower().replace(" ", "_")
            print(f"  {self.domain.lower()}_{slug}_harvest_response.json")
        print(f"\nThen run:")
        print(f"  python -m analysis_tool.idle.idle_harvest_runner --domain {self.domain} --process-responses")
        print(f"{'=' * 60}\n")

        return plan

    def run_phase2_process(self) -> IdleHarvestResult:
        """
        Phase 2: Read Copilot responses → extract facts → re-run DFEP → compare.
        Returns IdleHarvestResult with improvement metrics.
        """
        print(f"\n{'=' * 60}")
        print(f"Idle Harvest Loop — Phase 2: Process Responses")
        print(f"Domain: {self.domain}")
        print(f"{'=' * 60}\n")

        # Load plan from phase 1
        plan = self._load_plan()

        # Safety guard: reject if responses dir is missing or empty
        if not os.path.isdir(self.idle_responses_dir):
            raise FileNotFoundError(
                f"Responses directory not found: {self.idle_responses_dir}\n"
                "Run phase 1 first, then place Copilot responses in the idle responses dir."
            )

        response_files = list(Path(self.idle_responses_dir).glob(f"{self.domain.lower()}_*_harvest_response.json"))

        # Safety guard: reject empty responses
        non_empty = [f for f in response_files if f.stat().st_size > 10]
        if not non_empty:
            raise ValueError(
                f"No non-empty harvest response files found in: {self.idle_responses_dir}\n"
                "Place Copilot JSON responses there before running phase 2."
            )

        print(f"[1/4] Found {len(non_empty)} response file(s):")
        for f in non_empty:
            print(f"      {f}")

        # Import here to avoid circular issues at module level
        from analysis_tool.idle.targeted_extractor import TargetedExtractor

        print(f"\n[2/4] Extracting facts from responses (append-only)...")
        extractor = TargetedExtractor(domain=self.domain)
        extracted_count = 0
        for resp_file in non_empty:
            cap_id = self._cap_id_from_filename(resp_file.name, self.domain)
            n = extractor.process_response(
                response_path=str(resp_file),
                capability_id=cap_id,
            )
            extracted_count += n
            print(f"      {resp_file.name}: {n} new facts extracted")

        print(f"      Total new facts: {extracted_count}")

        print(f"\n[3/4] Re-running DFEP v3 comparison (using existing L0/GA responses)...")
        new_match_score = self._rerun_dfep()
        print(f"      New match score: {new_match_score:.0%}")

        print(f"\n[4/4] Comparing before/after...")
        comparator = ResultComparator(snapshots_dir=self.snapshots_dir)
        result = comparator.compare(
            domain=self.domain,
            before_score=plan.prior_match_score,
            after_score=new_match_score,
            iteration=plan.iteration,
        )
        comparator.print_result(result)

        return result

    # --- Internals ---

    def _plan_path(self) -> str:
        return os.path.join(
            _DEFAULT_RESPONSES_DIR,
            f"{self.domain.lower()}_harvest_plan.json"
        )

    def _load_plan(self) -> IdleHarvestPlan:
        path = self._plan_path()
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"No harvest plan found at: {path}\n"
                "Run phase 1 first: python -m analysis_tool.idle.idle_harvest_runner --domain {self.domain}"
            )
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        targets = [
            HarvestTarget(
                capability_id=t["capability_id"],
                gap_type=t["gap_type"],
                reason=t["reason"],
                priority=t["priority"],
                capability_intent=t["capability_intent"],
                confidence=t.get("confidence", 0.0),
            )
            for t in data.get("targets", [])
        ]
        return IdleHarvestPlan(
            domain=data["domain"],
            run_date=data["run_date"],
            targets=targets,
            iteration=data.get("iteration", 1),
            prior_match_score=data.get("prior_match_score", 0.0),
            snapshot_date=data.get("snapshot_date", ""),
        )

    def _rerun_dfep(self) -> float:
        """
        Re-run DFEP v3 phase2 using existing L0 + comparison responses.
        Returns the new match_score from the updated snapshot.
        """
        responses_dir = self.responses_dir_base
        domain_slug = self.domain.lower()

        l0_resp = os.path.join(responses_dir, f"{domain_slug}_l0.json")
        ga_resp = os.path.join(responses_dir, f"{domain_slug}_ga.json")
        cmp_resp = os.path.join(responses_dir, f"{domain_slug}_comparison.json")

        # All three must exist
        for p in (l0_resp, ga_resp, cmp_resp):
            if not os.path.exists(p):
                raise FileNotFoundError(
                    f"Required DFEP response file missing: {p}\n"
                    "Run DFEP v3 phase2 for this domain first."
                )

        # Call dfep_runner phase2 programmatically
        from dfep_v3.engine.dfep_runner import phase2_parse_and_report, _DEFAULT_OUTPUT, _DEFAULT_PROMPTS

        phase2_parse_and_report(
            domain=self.domain,
            l0_response_path=l0_resp,
            ga_response_path=ga_resp,
            cmp_response_path=cmp_resp,
            prompts_dir=_DEFAULT_PROMPTS,
            output_dir=_DEFAULT_OUTPUT,
            temp_md_path=None,  # don't write to temp.md for intermediate runs
            snapshots_dir=self.snapshots_dir,
        )

        # Read the new match score from the updated snapshot
        snap_path = os.path.join(self.snapshots_dir, f"{domain_slug}_snapshot.json")
        with open(snap_path, encoding="utf-8") as f:
            snap = json.load(f)
        return float(snap.get("match_score", 0.0))

    @staticmethod
    def _cap_id_from_filename(filename: str, domain: str) -> str:
        """
        Extract capability_id from filename pattern:
          {domain}_{capability_id}_harvest_response.json
        """
        prefix = f"{domain.lower()}_"
        suffix = "_harvest_response.json"
        if filename.startswith(prefix) and filename.endswith(suffix):
            return filename[len(prefix):-len(suffix)]
        return filename


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Idle Harvest Loop — gap-driven enrichment (DFEP v3-driven)"
    )
    ap.add_argument(
        "--domain",
        default=None,
        help="Domain name (e.g. Templates). Omit to use --auto selection.",
    )
    ap.add_argument(
        "--auto",
        action="store_true",
        help="Automatically select the highest-priority domain from DFEP snapshots.",
    )
    ap.add_argument(
        "--status",
        action="store_true",
        help="Print status of all domains and exit.",
    )
    ap.add_argument(
        "--process-responses",
        action="store_true",
        help="Phase 2: process Copilot responses + re-run DFEP. Default: phase 1 (generate prompts).",
    )
    ap.add_argument(
        "--snapshots-dir",
        default=_DEFAULT_SNAPSHOTS,
        help=f"DFEP snapshots dir (default: {_DEFAULT_SNAPSHOTS})",
    )
    ap.add_argument(
        "--prompts-dir",
        default=_DEFAULT_PROMPTS_DIR,
        help=f"Output dir for harvest prompts (default: {_DEFAULT_PROMPTS_DIR})",
    )
    ap.add_argument(
        "--idle-responses-dir",
        default=_DEFAULT_RESPONSES_DIR,
        help=f"Dir where Copilot harvest responses are placed (default: {_DEFAULT_RESPONSES_DIR})",
    )
    args = ap.parse_args()

    selector = DomainSelector(
        snapshots_dir=args.snapshots_dir,
        idle_responses_dir=args.idle_responses_dir,
    )

    # --status: just print overview and exit
    if args.status:
        selector.print_status()
        sys.exit(0)

    # Resolve domain
    domain = args.domain
    if not domain:
        if not args.auto:
            print("ERROR: provide --domain <name> or use --auto to select automatically.")
            print("       Use --status to see all domains.")
            sys.exit(1)
        chosen = selector.select()
        if not chosen:
            print("[DONE] No domains need harvesting — all gates passing or no snapshots found.")
            selector.print_status()
            sys.exit(0)
        domain = chosen.domain
        print(f"[AUTO] Selected domain: {domain}")
        print(f"       Score: {chosen.match_score:.0%} | HIGH gaps: {chosen.high_gap_count} | Missing: {chosen.missing_count}")
        # If pending responses exist, auto-switch to phase 2
        if chosen.has_pending_responses and not args.process_responses:
            print(f"       Pending responses detected — switching to --process-responses")
            args.process_responses = True

    runner = IdleHarvestRunner(
        domain=domain,
        snapshots_dir=args.snapshots_dir,
        prompts_dir=args.prompts_dir,
        idle_responses_dir=args.idle_responses_dir,
    )

    if args.process_responses:
        result = runner.run_phase2_process()
        sys.exit(0 if result.recommendation != "STOP_REGRESSION" else 1)
    else:
        plan = runner.run_phase1_generate()
        sys.exit(0 if plan.targets else 1)


if __name__ == "__main__":
    main()
