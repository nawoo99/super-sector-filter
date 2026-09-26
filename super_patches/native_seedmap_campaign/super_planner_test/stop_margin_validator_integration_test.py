#!/usr/bin/env python3
"""Compile the exact production validator against controlled query fixtures.

Real production traversal, result statuses, deferral branches and completion
proof are exercised. Map queries, linear trajectory and DDA samples are fixtures:
this is not a sensor-map geometry integration test or physical safety proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def extract(text, signature):
    """Keep source byte-for-byte; ignore braces inside comments/literals."""
    begin = text.index(signature)
    masked = re.sub(r'''//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*' ''',
                    lambda match: " " * len(match.group()), text, flags=re.S | re.X)
    brace = masked.index("{", begin)
    depth = 1
    end = brace + 1
    while depth:
        depth += (masked[end] == "{") - (masked[end] == "}")
        end += 1
    return text[begin:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    package = Path(__file__).resolve().parents[1]
    types_path = package / "include/super_core/super_planner.h"
    planner_path = package / "src/super_core/super_planner.cpp"
    fsm_path = package / "include/ros_interface/ros2/fsm_ros2.hpp"
    paths = [types_path, planner_path, fsm_path,
             package / "include/fsm/stop_margin_certificate.hpp"]
    types, planner, fsm = (p.read_text() for p in paths[:3])
    geometry = extract(planner, "TrajectorySafetyResult SuperPlanner::validatePositionTrajectory(")
    stop = extract(planner, "bool SuperPlanner::certifiedStopExistsFrom(")
    states = extract(planner, "bool SuperPlanner::candidateStopsViable(")
    # These are SOURCE-CONTRACT checks, distinct from the executable traversal
    # regression below. They ensure the live caller consumes the new proof.
    assert "DeferSoftMarginUntilHardChecksComplete" in stop
    assert "stop_margin::admissibleStop" in stop and "safety.hard_checks_complete" in stop
    assert "!pos_traj.getState(tt, state)" in states
    assert "!state.array().isFinite().all()" in states
    assert "policy.viability_policy_revision = planner_ptr_->stopViabilityPolicyRevision();" in fsm
    assert "static_cast<unsigned int>(command.trajectory_flag)" in fsm
    fragments = {
        "types.inc": extract(types, "enum class TrajectorySafetyStatus") + ";\n"
                     + extract(types, "struct TrajectorySafetyResult") + ";",
        "names.inc": extract(planner, "const char *trajectorySafetyStatusName("),
        "validator.inc": geometry,
        "candidate_states.inc": states,
    }
    for name, body in fragments.items():
        (args.output / name).write_text(body + "\n")
    command = ["g++", "-std=c++17", "-O1", "-Wall", "-Wextra", "-pthread",
               "-I", str(args.output), "-I", str(package / "include"),
               "-I", str(package.parent / "rog_map/include"),
               "-I", "/usr/include/eigen3",
               str(package / "test/stop_margin_validator_integration_test.cpp"),
               "-o", str(args.output / "test")]
    if args.sanitize:
        command[2:2] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    subprocess.run(command, check=True)
    result = subprocess.run([str(args.output / "test")], capture_output=True,
                            text=True, timeout=30)
    report = dict(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr,
                  scope="exact production validator and sampled-state traversal; fixture map/trajectory/DDA/stop predicate",
                  source_contracts="stop caller proof, invalid-state rejection, revision consumer, numeric uint8 trace",
                  sanitize=args.sanitize,
                  extracted_validator_sha256=hashlib.sha256(geometry.encode()).hexdigest(),
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (args.output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
