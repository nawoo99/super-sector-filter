#!/usr/bin/env python3
"""Sequential, resumable map-only search with immutable failures and fresh n20.

No planner/filter/sensor/dynamics changes. Candidates are predeclared related
geometry variants, not independent blind test environments. Invalid measurement
stops the search for diagnosis; it is never silently retried or discarded.
"""
import argparse
import csv
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import cylinder_map_search as search
import cylinder_solid_campaign as solid
import confirm_cylinder_search_n20 as confirmation
from analyze_cylinder_only_stress_full_gate import quality_valid
from audit_cylinder_flight_segments import segments
from refine_cylinder_map import emit

ROOT = search.ROOT/"results/cylinder_refinement_repeat_20260915"
RECIPES = [dict(name=f"cyl2_j{index+2:02d}", parent="cyl2_j01", legs=legs, tip_count=tips)
           for index, (tips, legs) in enumerate(
               (tips, legs) for tips in (1, 2) for legs in
               ([4], [3, 4], [2, 3, 4], [1, 2, 3, 4], [1, 2, 3, 4, 5]))]


def read_rows(path):
    if not path.exists():
        return []
    with path.open() as stream:
        return list(csv.DictReader(stream))


def validate_rows(rows, name):
    keys = {(r["run"], r["mode"]) for r in rows}
    if len(keys) != len(rows):
        raise RuntimeError("Duplicate trial evidence")
    if any(r["map"] != name or not quality_valid(r) or not confirmation.known_outcome(r) for r in rows):
        raise RuntimeError("Invalid measurement/infrastructure row retained; manual diagnosis required")


def references_failed(rows):
    return any(r["mode"] in ("full", "adaptive") and not confirmation.safe(r) for r in rows)


def failure_audit(rows):
    reports = []
    for row in rows:
        if confirmation.safe(row):
            continue
        path = Path(row["solid_report_json"])
        trace = read_rows(path.with_suffix(".poses.csv"))
        log_path = path.parent.parent/"artifacts"/f"{row['map']}_run{row['run']}_{row['mode']}.attempt1.stack.log"
        log = log_path.read_text(errors="replace") if log_path.exists() else ""
        reports.append(dict(run=row["run"], mode=row["mode"], success=row["success"],
                            solid_contacts=row["solid_collision_episodes"],
                            segments=segments(path), final_pose=trace[-1] if trace else None,
                            log_pattern_counts={pattern:log.count(pattern) for pattern in
                                ("MAP_STALE", "Empty or non-dense point cloud", "Replan over time",
                                 "0.1 seconds time limit exceeded", "REROUTE_EPOCH_RESET")},
                            interpretation="Descriptive failure localization, not independently identified causality",
                            report=str(path), log=str(log_path)))
    return reports


def save(path, data):
    if path.name == "status.json":
        data["updated_epoch_s"] = time.time()
    temporary = path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(data, indent=2)+"\n")
    temporary.replace(path)


def execute(script, arguments, log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as stream:
        process = subprocess.Popen([sys.executable, str(Path(__file__).with_name(script)), *arguments],
                                   stdout=stream, stderr=stream, start_new_session=True)
        try:
            returncode = process.wait()
        except BaseException:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    # Do not force-kill a flight or erase partial evidence.
                    pass
            raise
    if returncode != 0:
        raise RuntimeError(f"Child stopped with status {returncode}; inspect {log_path}")


def ensure_candidate(recipe):
    name = recipe["name"]
    manifest_path = search.OUT/name/"manifest.json"
    expected = dict(parent=recipe["parent"], trim_baffle_legs=recipe["legs"], tip_count=recipe["tip_count"])
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest["parameters"] != expected:
            raise RuntimeError("Existing candidate has different geometry; refusing overwrite")
        if manifest["policy"] != search.frozen_policy():
            raise RuntimeError("Runtime policy changed")
        if any(search.geometry.sha256(Path(p)) != sha for p, sha in manifest["assets"].items()):
            raise RuntimeError("Existing candidate asset changed")
    else:
        emit(recipe["parent"], name, recipe["legs"], recipe["tip_count"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-passing-maps", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.target_passing_maps <= len(RECIPES):
        parser.error("Invalid passing-map target")
    ROOT.mkdir(parents=True, exist_ok=True)
    lock_stream = (ROOT/"controller.lock").open("a")
    try:
        fcntl.flock(lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise RuntimeError("A refinement controller is already running") from error
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f"Controller interrupted by signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    declaration = dict(recipes=RECIPES, target_passing_maps=args.target_passing_maps,
                       minimum_development_blocks=3, confirmation_new_trials_per_mode=20,
                       runtime_policy=search.frozen_policy(), no_parallel_flights=True,
                       no_generation_build_git_during_confirmation=True,
                       rejects_reference_failure=True, preserves_all_outcomes=True,
                       geometry_family_not_independent_holdout=True,
                       selection="exploratory; family designed after J01 run106 failure",
                       prior_j02_first_pilot_started_before_this_family_declaration=True,
                       research_implementation_sha256={str(p):search.geometry.sha256(p) for p in
                           (Path(__file__).resolve(), Path(__file__).with_name("refine_cylinder_map.py").resolve(),
                            Path(confirmation.__file__).resolve(), solid.OBSERVER, Path(solid.__file__).resolve())})
    freeze = ROOT/"search_plan.json"
    if freeze.exists():
        if json.loads(freeze.read_text()) != declaration:
            raise RuntimeError("Search declaration changed")
    else:
        with freeze.open("x") as stream:
            json.dump(declaration, stream, indent=2); stream.write("\n")
    status = dict(started_epoch_s=time.time(), pid=os.getpid(), state="RUNNING", passed=[], candidates=[])
    current = None
    try:
        for recipe in RECIPES:
            current = recipe["name"]
            status.update(current=current, phase="geometry")
            save(ROOT/"status.json", status)
            ensure_candidate(recipe)
            pilot_path = solid.OUT/current/"raw.csv"
            confirmed_path = confirmation.ROOT/current/"raw.csv"
            pilot, confirmed = read_rows(pilot_path), read_rows(confirmed_path)
            validate_rows(pilot, current); validate_rows(confirmed, current)
            if not references_failed(pilot+confirmed):
                for run in range(1, 4):
                    existing = {(int(r["run"]), r["mode"]) for r in pilot}
                    missing = [mode for mode in confirmation.MODES if (run, mode) not in existing]
                    if missing:
                        status.update(phase="development", run=run)
                        save(ROOT/"status.json", status)
                        execute("cylinder_solid_campaign.py", [current, "--run", str(run), "--modes", *missing],
                                ROOT/current/f"development_run{run}.log")
                        pilot = read_rows(pilot_path); validate_rows(pilot, current)
                    if references_failed(pilot):
                        break
            if references_failed(pilot+confirmed):
                decision = "REJECT_REFERENCE_FAILURE"
            elif not confirmation.qualified(pilot, 3):
                decision = "NO_DEVELOPMENT_OUTCOME_SEPARATION"
            else:
                status.update(phase="confirmation_n20")
                save(ROOT/"status.json", status)
                if not confirmation.result(confirmed)["exact_60_unique_rows"]:
                    execute("confirm_cylinder_search_n20.py",
                            [current, "--min-development-runs", "3", "--stop-on-reference-failure"],
                            ROOT/current/"confirmation.log")
                confirmed = read_rows(confirmed_path); validate_rows(confirmed, current)
                outcome = confirmation.result(confirmed)
                if not outcome["exact_60_unique_rows"] and not references_failed(confirmed):
                    raise RuntimeError("Confirmation ended incomplete without a reference-failure stop")
                decision = ("OBSERVED_N20_CRITERION_MET" if outcome["observed_user_criterion_met"] else
                            "REJECT_REFERENCE_FAILURE" if references_failed(confirmed) else
                            "N20_NO_OUTCOME_SEPARATION")
            candidate = dict(map=current, decision=decision, development_rows=len(pilot),
                             confirmation_rows=len(confirmed),
                             confirmation=confirmation.result(confirmed),
                             descriptive_failures=failure_audit(pilot+confirmed))
            (ROOT/current).mkdir(exist_ok=True)
            save(ROOT/current/"audit.json", candidate)
            status["candidates"].append({k:v for k,v in candidate.items() if k != "descriptive_failures"})
            if decision == "OBSERVED_N20_CRITERION_MET":
                status["passed"].append(current)
            save(ROOT/"status.json", status)
            print("REFINEMENT_RESULT "+json.dumps(dict(map=current, decision=decision,
                                                      passed=status["passed"])), flush=True)
            if len(status["passed"]) >= args.target_passing_maps:
                status["state"] = "TARGET_OBSERVED"
                break
        else:
            status["state"] = "RECIPE_FAMILY_EXHAUSTED_REQUIRES_NEW_DESIGN"
    except BaseException as error:
        status.update(state="STOPPED_FOR_DIAGNOSIS", error=str(error), current=current)
        raise
    finally:
        status["updated_epoch_s"] = time.time()
        save(ROOT/"status.json", status)


if __name__ == "__main__":
    main()
