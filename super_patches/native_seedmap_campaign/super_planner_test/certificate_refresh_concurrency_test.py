#!/usr/bin/env python3
"""Compile unchanged production refresh functions against controlled fixtures.

This is a control-flow/concurrency test, not geometry or flight validation.
The real validator's deadline checkpoints are also checked for presence; the
full ROS build verifies their types and integration.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from clearance_gate_differential_test import extract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    package = Path(__file__).resolve().parents[1]
    paths = [package / 'include/super_core/super_planner.h',
             package / 'src/super_core/super_planner.cpp',
             package / 'include/ros_interface/ros2/fsm_ros2.hpp']
    types, planner, fsm = [p.read_text() for p in paths]
    fragments = {
        'types.inc': extract(types, 'enum class TrajectorySafetyStatus') + ';\n' + extract(types, 'struct TrajectorySafetyResult') + ';',
        'names.inc': extract(planner, 'const char *trajectorySafetyStatusName('),
        'validation.inc': extract(planner, 'TrajectorySafetyResult SuperPlanner::validateCommittedTrajectory('),
        'refresh.inc': extract(fsm, 'bool refreshSafetyCertificate('),
        'decision.inc': extract(fsm, 'if (cfg_.trajectory_guard_en && machine_state_ == FOLLOW_TRAJ &&\n                !refreshSafetyCertificate("main_pre"))'),
    }
    geometry = extract(planner, 'TrajectorySafetyResult SuperPlanner::validatePositionTrajectory(')
    assert geometry.count('if (expired()) return result;') >= 6
    assert 'bounded && !map_ptr_->immutablePlannerSnapshotEnabled()' in geometry
    for name, body in fragments.items():
        (args.output / name).write_text(body + '\n')
    command = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-pthread',
               '-I', str(args.output), str(package / 'test/certificate_refresh_concurrency_test.cpp'),
               '-o', str(args.output / 'test')]
    if args.sanitize:
        command[2:2] = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    subprocess.run(command, check=True)
    result = subprocess.run([str(args.output / 'test')], capture_output=True, text=True, timeout=30)
    report = dict(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr,
                  scope='extracted production control flow, stub geometry/time/map/command storage',
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
