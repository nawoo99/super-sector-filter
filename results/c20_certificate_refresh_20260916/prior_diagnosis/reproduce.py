#!/usr/bin/env python3
"""Read-only production-function concurrency audit; not a geometry/flight replay.

Source functions/types are extracted verbatim. Geometry, time, map freshness,
and command storage are small controlled fixtures. No deployed file is written.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path('/root/super_ws/src/SUPER/super_planner')
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'existing_extractor', ROOT / 'test/clearance_gate_differential_test.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
extract = module.extract
paths = {
    'planner': ROOT / 'src/super_core/super_planner.cpp',
    'types': ROOT / 'include/super_core/super_planner.h',
    'fsm': ROOT / 'include/ros_interface/ros2/fsm_ros2.hpp',
}
source = {k: p.read_text() for k, p in paths.items()}
fragments = {
    'production_types.inc': extract(source['types'], 'enum class TrajectorySafetyStatus') + ';\n' + extract(source['types'], 'struct TrajectorySafetyResult') + ';\n',
    'production_names.inc': extract(source['planner'], 'const char *trajectorySafetyStatusName('),
    'production_validation.inc': extract(source['planner'], 'TrajectorySafetyResult SuperPlanner::validateCommittedTrajectory('),
    'production_refresh.inc': extract(source['fsm'], 'bool refreshSafetyCertificate('),
    'production_decision.inc': extract(source['fsm'], 'if (cfg_.trajectory_guard_en && machine_state_ == FOLLOW_TRAJ &&\n                !refreshSafetyCertificate("main_pre"))'),
}
for name, body in fragments.items():
    (OUT / name).write_text(body + '\n')
manifest = {
    'scope': 'Controlled concurrency/control-flow reproduction, NOT flight or geometry validation',
    'unchanged_extracted_functions': ['validateCommittedTrajectory', 'refreshSafetyCertificate', 'main_pre non-SAFE brake decision'],
    'fixture_dependencies': ['command snapshot store', 'geometry validator', 'map health/freshness', 'clock', 'logging', 'brake actuator'],
    'source_sha256': {str(paths[k]): hashlib.sha256(s.encode()).hexdigest() for k, s in source.items()},
    'fragment_sha256': {n: hashlib.sha256((s+'\n').encode()).hexdigest() for n, s in fragments.items()},
}
subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-pthread', str(OUT / 'harness.cpp'), '-o', str(OUT / 'audit')], check=True)
run = subprocess.run([str(OUT / 'audit')], text=True, capture_output=True, timeout=30)
manifest['exit_code'] = run.returncode
manifest['stdout'] = run.stdout
manifest['stderr'] = run.stderr
manifest['source_unchanged_after_test'] = all(p.read_text() == source[k] for k, p in paths.items())
(OUT / 'result.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
raise SystemExit(run.returncode)
