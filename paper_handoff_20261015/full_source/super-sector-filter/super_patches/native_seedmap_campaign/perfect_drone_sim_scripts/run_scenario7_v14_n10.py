#!/usr/bin/env python3
"""Fresh c39-equivalent seven-map campaign with no mission-duration cutoff.

The c39 evidence is preserved.  All three modes use the same infinite mission
horizon; an independent 60 s/2 cm no-progress terminal is declared and audited.
"""
import json
import math
from pathlib import Path

import run_scenario7_v7_n10 as base
import run_scenario7_v13_n10 as previous


CANDIDATE = 'c40_no_mission_cutoff_v14_n10'
BASE_RUN = 96400
THIS_FILE = Path(__file__).resolve()
WRAPPER = THIS_FILE.with_name('scenario7_no_mission_cutoff_cpu_compare.py')


def no_cutoff_audit(item, mode):
    root = Path(item['output'])
    plan_path = root / 'plan.json'
    artifact_path = root / 'artifacts' / (
        f"{item['map']}_run{item['run']}_{mode}.attempt1.solid_audit.json")
    try:
        plan = json.loads(plan_path.read_text())
        effective = plan['effective_run_options'][mode]['loop_timeout_override']
        solid = json.loads(artifact_path.read_text())
        policy = solid['terminal_stall_policy']
        checks = {
            'infinite_mission_horizon': isinstance(effective, (int, float))
                                        and math.isinf(effective) and effective > 0,
            'no_mission_time_cutoff': policy['mission_time_cutoff_s'] is None,
            'no_progress_terminal_enabled': policy['enabled'] is True,
            'no_progress_window_s': policy['window_s'] == 60.0,
            'no_progress_radius_m': policy['radius_m'] == 0.02,
            'measurement_only': policy['effect'] ==
                                'measurement-only observer termination; no planner input',
        }
        return {'valid': all(checks.values()), 'checks': checks,
                'effective_loop_timeout_override': effective, 'terminal_policy': policy}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {'valid': False, 'error': repr(error)}


def main():
    previous.verify_runtime_install()
    if not WRAPPER.is_file():
        raise RuntimeError('No-cutoff child wrapper missing: ' + str(WRAPPER))
    old_wrapper = base.WRAPPER
    old_identity = base.frozen_identity
    old_validation = base.validate_triplet
    old_candidate = previous.CANDIDATE
    old_run = previous.BASE_RUN

    def frozen_identity(root):
        hashes = old_identity(root)
        hashes[str(THIS_FILE)] = base.sha256(THIS_FILE)
        hashes[str(WRAPPER)] = base.sha256(WRAPPER)
        return hashes

    def validate_triplet(item):
        result = old_validation(item)
        for mode in base.MODES:
            audit = no_cutoff_audit(item, mode)
            result['outcomes'].setdefault(mode, {})['no_mission_cutoff_audit'] = audit
            if not audit['valid']:
                result['errors'].append(mode + ': no-cutoff runtime audit failed')
        result['valid'] = not result['errors']
        result['blocking'] = bool(result['errors'])
        base.atomic_json(Path(item['output']) / 'v7_triplet_validation.json', result)
        return result

    base.WRAPPER = WRAPPER
    base.frozen_identity = frozen_identity
    base.validate_triplet = validate_triplet
    previous.CANDIDATE = CANDIDATE
    previous.BASE_RUN = BASE_RUN
    try:
        return previous.main()
    finally:
        previous.BASE_RUN = old_run
        previous.CANDIDATE = old_candidate
        base.validate_triplet = old_validation
        base.frozen_identity = old_identity
        base.WRAPPER = old_wrapper


if __name__ == '__main__':
    raise SystemExit(main())
