#!/usr/bin/env python3
"""Run frozen c37 velocity-centred Adaptive validation."""
from pathlib import Path
import re

import run_scenario7_v11_n10 as previous


CANDIDATE = 'c37_velocity_centered_adaptive_v12_n10'
BASE_RUN = 92100
THIS_FILE = Path(__file__).resolve()


def main():
    # v11 -> v10 -> v9 -> v7, where the scheduler and COMMON arguments live.
    base = previous.previous.previous.previous
    old_candidate = previous.CANDIDATE
    old_base_run = previous.BASE_RUN
    old_common = base.COMMON
    old_frozen_identity = base.frozen_identity
    old_validate_triplet = base.validate_triplet

    def frozen_identity(root):
        hashes = old_frozen_identity(root)
        for path in (
                THIS_FILE,
                base.SOURCE / 'mission_planner/Apps/native_sector_cpp.cpp',
                base.SOURCE / 'mission_planner/include/mission_planner/sector_heading_policy.hpp',
                base.SOURCE / 'mars_uav_sim/perfect_drone_sim/include/perfect_drone_sim/ros2_perfect_drone_model.hpp'):
            hashes[str(path)] = base.sha256(path)
        return hashes

    def validate_triplet(item):
        result = old_validate_triplet(item)
        artifact_root = Path(item['output']) / 'artifacts'
        expected = {
            'sector': r'\[SECTOR_HEADING_POLICY\] body_aligned_event=0 velocity_center=0',
            'adaptive': r'\[SECTOR_HEADING_POLICY\] body_aligned_event=0 velocity_center=1',
        }
        for mode, pattern in expected.items():
            stack_path = artifact_root / (
                f"{item['map']}_run{item['run']}_{mode}.attempt1.stack.log")
            stack = stack_path.read_text(errors='replace') if stack_path.is_file() else ''
            count = len(re.findall(pattern, stack))
            valid = count == 1
            result['outcomes'].setdefault(mode, {})['heading_policy_valid'] = valid
            result['outcomes'][mode]['heading_policy_matches'] = count
            if not valid:
                result['errors'].append(
                    f'{mode}: c37 heading-policy audit failed (matches={count})')
        result['valid'] = not result['errors']
        result['blocking'] = bool(result['errors'])
        base.atomic_json(Path(item['output']) / 'v7_triplet_validation.json', result)
        return result

    previous.CANDIDATE = CANDIDATE
    previous.BASE_RUN = BASE_RUN
    base.COMMON = tuple(
        value for value in old_common if value != '--event-body-heading')
    base.frozen_identity = frozen_identity
    base.validate_triplet = validate_triplet
    try:
        return previous.main()
    finally:
        base.validate_triplet = old_validate_triplet
        base.frozen_identity = old_frozen_identity
        base.COMMON = old_common
        previous.BASE_RUN = old_base_run
        previous.CANDIDATE = old_candidate


if __name__ == '__main__':
    raise SystemExit(main())
