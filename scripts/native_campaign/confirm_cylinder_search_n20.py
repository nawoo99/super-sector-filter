#!/usr/bin/env python3
"""Freeze an eligible development map, then run 20 NEW trials per mode.

User criterion: Full and Adaptive complete contact-free in every measured
trial, and Sector has at least one actual completion/contact failure.
Brake-rejection diagnostics never substitute for that criterion.
"""
import argparse
import csv
import json
from pathlib import Path

import cylinder_map_search as search
from analyze_cylinder_only_stress_full_gate import boolean, contact_free, quality_valid, integer

ROOT = search.ROOT / "results/cylinder_confirmation_n20_20260915"
MODES = ("full", "sector", "adaptive")
RUNS = tuple(range(101, 121))


def safe(row):
    return (boolean(row.get("success")) and contact_free(row)
            and integer(row,"solid_collision_episodes")==0)


def known_outcome(row):
    return (str(row.get("success", "")).strip().lower() in {"true", "false", "1", "0", "yes", "no"}
            and integer(row, "safety_collisions") >= 0
            and integer(row, "static_pcd_collisions") >= 0
            and integer(row, "solid_collision_episodes") >= 0
            and boolean(row.get("solid_observer_valid")))


def eligible(rows):
    by_mode = {m: [r for r in rows if r.get("mode") == m] for m in MODES}
    keys = [(r.get("map"), str(r.get("run")), r.get("mode")) for r in rows]
    return (bool(rows) and len(keys) == len(set(keys))
            and len({r.get("map") for r in rows}) == 1
            and all(r.get("map") and r.get("mode") in MODES for r in rows)
            and all(by_mode.values()) and all(quality_valid(r) and known_outcome(r) for r in rows)
            and all(safe(r) for m in ("full", "adaptive") for r in by_mode[m])
            and any(not safe(r) for r in by_mode["sector"]))


def result(rows):
    counts = {}
    for mode in MODES:
        group = [r for r in rows if r["mode"] == mode]
        counts[mode] = dict(rows=len(group), complete=sum(boolean(r.get("success")) for r in group),
                           contact_free=sum(contact_free(r) and integer(r,"solid_collision_episodes")==0 for r in group),
                           solid_contact_trials=sum(integer(r,"solid_collision_episodes")>0 for r in group),
                           safe_complete=sum(safe(r) for r in group),
                           quality_valid=sum(quality_valid(r) for r in group))
    keys = {(int(r["run"]), r["mode"]) for r in rows}
    exact = len(rows) == 60 and keys == {(r, m) for r in RUNS for m in MODES}
    valid = (exact and len({r.get("map") for r in rows}) == 1
             and all(r.get("map") and quality_valid(r) and known_outcome(r) for r in rows))
    passed = (valid and counts["full"]["safe_complete"] == 20
              and counts["adaptive"]["safe_complete"] == 20
              and counts["sector"]["safe_complete"] < 20)
    return dict(criterion="actual_contact_or_completion_failure_only", counts=counts,
                exact_60_unique_rows=exact, all_quality_valid=valid,
                observed_user_criterion_met=passed,
                population_guarantee=False,
                decision="OBSERVED_N20_CRITERION_MET" if passed else
                         "N20_CRITERION_NOT_MET" if exact else "INCOMPLETE")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    if not args.map.startswith("cyl2_") or not args.map.replace("_", "").isalnum():
        parser.error("Use an emitted cyl2_ candidate")
    development = search.OUT / args.map
    import cylinder_solid_campaign as solid
    development_data = solid.OUT / args.map
    output = ROOT / args.map
    raw = output / "raw.csv"
    read_rows = lambda p: list(csv.DictReader(p.open())) if p.exists() else []
    if args.analyze_only:
        print(json.dumps(result(read_rows(raw)), indent=2))
        return
    candidate = json.loads((development / "manifest.json").read_text())
    development_rows = read_rows(development_data / "raw.csv")
    if not eligible(development_rows):
        parser.error("Development map does not meet the user's actual outcome criterion")
    instrumentation={str(p):search.geometry.sha256(p) for p in (solid.OBSERVER,Path(solid.__file__))}
    def verify():
        if search.frozen_policy() != candidate["policy"]:
            raise RuntimeError("Runtime policy hash changed")
        for p, sha in candidate["assets"].items():
            if search.geometry.sha256(Path(p)) != sha:
                raise RuntimeError(f"Frozen map asset changed: {p}")
        if any(search.geometry.sha256(Path(p))!=sha for p,sha in instrumentation.items()):
            raise RuntimeError("Frozen solid-observer instrumentation changed")
    verify()
    output.mkdir(parents=True, exist_ok=True)
    declaration = dict(map=args.map, runs=list(RUNS), modes=list(MODES),
                       expected_rows=60, selection="development_outcome_selected",
                       source_manifest_sha256=search.geometry.sha256(development / "manifest.json"),
                       source_development_raw=str(development_data / "raw.csv"),
                       source_development_raw_sha256=search.geometry.sha256(development_data / "raw.csv"),
                       measurement_protocol="prelaunch-solid-cylinder-observer-v1",
                       instrumentation_sha256=instrumentation,
                       simulator_dynamics_unchanged=True,
                       criterion="Full=20/20 safe complete, Adaptive=20/20 safe complete, Sector<20/20 safe complete",
                       retry_policy="no automatic retry; retain all requested rows including failures",
                       mode_order="rotation by run; no outcome-dependent ordering",
                       candidate=candidate)
    freeze = output / "freeze.json"
    if freeze.exists():
        if json.loads(freeze.read_text()) != declaration:
            raise RuntimeError("Confirmation freeze does not match current development snapshot")
    else:
        with freeze.open("x") as stream:
            json.dump(declaration, stream, indent=2); stream.write("\n")
    rows = read_rows(raw)
    existing = {(int(r["run"]), r["mode"]) for r in rows}
    if len(existing) != len(rows) or existing - {(r, m) for r in RUNS for m in MODES}:
        raise RuntimeError("Duplicate or unexpected confirmation rows")
    if any(r.get("map") != args.map or not quality_valid(r) or not known_outcome(r) for r in rows):
        raise RuntimeError("Existing row is mismatched or quality-invalid; diagnose without overwriting it")
    campaign = search.campaign
    campaign.install_campaign_signal_handlers()
    with raw.open("a", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=solid.FIELDS, extrasaction="ignore", lineterminator="\n")
        if not rows: writer.writeheader(); stream.flush()
        try:
            for index, run in enumerate(RUNS):
                shift = index % 3
                modes = MODES[shift:] + MODES[:shift]
                for position, mode in enumerate(modes, 1):
                    if (run, mode) in existing: continue
                    verify()
                    rec = solid.run_trial(args.map,mode,run,output)
                    rec["campaign_sequence_index"] = index * 3 + position
                    rec["mode_order_position"] = position
                    writer.writerow(rec); stream.flush(); rows.append(rec)
                    verify()
                    summary = result(rows)
                    (output / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
                    print("CONFIRMATION_PROGRESS " + json.dumps(summary), flush=True)
                    if not quality_valid(rec) or not known_outcome(rec):
                        raise RuntimeError("Quality-invalid row retained; stop to diagnose infrastructure")
        finally:
            campaign.cleanup_active_process_groups()


if __name__ == "__main__": main()
