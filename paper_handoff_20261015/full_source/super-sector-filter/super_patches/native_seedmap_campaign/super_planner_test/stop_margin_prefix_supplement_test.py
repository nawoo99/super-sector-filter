#!/usr/bin/env python3
"""Additive exact-validator prefix/deadline coverage; no production mutation.

Map/trajectory/DDA are fixtures. The timeout uses real steady_clock with a
three-second budget and explicit visited-order assertions, not a substituted
standard-library clock or a deterministic claim under arbitrary system load.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--prepare-only', action='store_true', help='Extract/inventory only; no compiler or executable')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    package = Path(__file__).resolve().parents[1]
    previous_driver = package / 'test/stop_margin_validator_integration_test.py'
    spec = importlib.util.spec_from_file_location('frozen_stop_validator_extract', previous_driver)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    types_path = package / 'include/super_core/super_planner.h'
    planner_path = package / 'src/super_core/super_planner.cpp'
    fixture_path = package / 'test/stop_margin_prefix_supplement_test.cpp'
    types, planner = types_path.read_text(), planner_path.read_text()
    geometry = module.extract(planner, 'TrajectorySafetyResult SuperPlanner::validatePositionTrajectory(')
    fragments = {
        'types.inc': module.extract(types, 'enum class TrajectorySafetyStatus') + ';\n'
                     + module.extract(types, 'struct TrajectorySafetyResult') + ';',
        'names.inc': module.extract(planner, 'const char *trajectorySafetyStatusName('),
        'validator.inc': geometry,
    }
    for name, body in fragments.items():
        (args.output / name).write_text(body + '\n')
    command = ['g++', '-std=c++17', '-O1', '-Wall', '-Wextra', '-pthread',
               '-I', str(args.output), '-I', str(package / 'include'),
               '-I', str(package.parent / 'rog_map/include'), '-I', '/usr/include/eigen3',
               str(fixture_path), '-o', str(args.output / 'test')]
    if args.sanitize:
        command[2:2] = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    dependencies = (Path(__file__).resolve(), fixture_path, previous_driver, types_path, planner_path,
                    package / 'include/fsm/stop_margin_certificate.hpp',
                    package / 'include/fsm/initial_footprint_egress_receipt.hpp',
                    package.parent / 'rog_map/include/rog_map/diagnostic_trace.hpp')
    report = dict(schema='stop-margin-prefix-supplement-v1', prepared_only=args.prepare_only,
                  scope='exact extracted production validator; fixture map/linear trajectory/midpoint DDA',
                  allow_initial_clearance_escape=True, cases_expected=10,
                  timing_scope='real clock; three-second budget; visited-order asserted; not deterministic under arbitrary load',
                  sanitize=args.sanitize, compiler_command=command,
                  extracted_validator_sha256=hashlib.sha256(geometry.encode()).hexdigest(),
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies})
    (args.output / 'prepared.json').write_text(json.dumps(report, indent=2) + '\n')
    if args.prepare_only:
        print(json.dumps(report, indent=2))
        return 0
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=120)
    report.update(compile_exit_code=compiled.returncode, compile_stdout=compiled.stdout,
                  compile_stderr=compiled.stderr)
    if compiled.returncode == 0:
        result = subprocess.run([str(args.output / 'test')], capture_output=True, text=True, timeout=20)
        report.update(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
        report['cases_reported'] = sum(line.startswith('case=') for line in result.stdout.splitlines())
        if result.returncode == 0 and report['cases_reported'] != report['cases_expected']:
            report['exit_code'] = 1
            report['evidence_error'] = 'Unexpected number of case outcomes'
    else:
        report['exit_code'] = compiled.returncode
    (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return report['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
