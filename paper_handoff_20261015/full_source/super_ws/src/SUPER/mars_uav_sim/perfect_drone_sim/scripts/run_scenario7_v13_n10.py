#!/usr/bin/env python3
"""Run the fresh c39 seven-map campaign after bounded recovery repair."""
from pathlib import Path
import os
import re

import run_scenario7_v12_n10 as previous


CANDIDATE = 'c39_bounded_recovery_refresh_v13_n10'
BASE_RUN = 96200
THIS_FILE = Path(__file__).resolve()
INSTALL_ROOT = Path('/root/super_ws/sector_active_yaw_scan_v1_20260929/install')
RUNTIME_BINARY = (
    INSTALL_ROOT
    / 'perfect_drone_sim/lib/perfect_drone_sim/perfect_drone_full_node'
)
RUNTIME_PROFILE_CONTRACT = {
    'super_planner/guard_topology_reroute/local_escape_distance_m': 0.6,
    'super_planner/guard_topology_reroute/local_escape_max_distance_m': 1.2,
    'super_planner/guard_topology_reroute/local_escape_distance_steps': 2.0,
}
ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')


def bounded_recovery_runtime_audit(stack: str):
    """Require the repaired schedule to be loaded exactly once per flight."""
    clean = ANSI_ESCAPE.sub('', stack)
    checks = {}
    for key, expected in RUNTIME_PROFILE_CONTRACT.items():
        matches = re.findall(
            rf'Load param {re.escape(key)} success:\s*([^\s]+)', clean)
        parsed = []
        for value in matches:
            try:
                parsed.append(float(value))
            except ValueError:
                parsed.append(None)
        checks[key] = {
            'expected': expected,
            'matches': matches,
            'valid': len(parsed) == 1 and parsed[0] == expected,
        }
    return {
        'schema': 'scenario7-bounded-recovery-runtime-v1',
        'valid': all(check['valid'] for check in checks.values()),
        'checks': checks,
    }


def verify_runtime_install():
    if not RUNTIME_BINARY.is_file():
        raise RuntimeError(f'missing integrated runtime binary: {RUNTIME_BINARY}')
    binary = RUNTIME_BINARY.read_bytes()
    missing = [marker.decode() for marker in (
        b'local_escape_max_distance_m',
        b'local_escape_distance_steps',
        b'distance_step={}/{}',
    ) if marker not in binary]
    if missing:
        raise RuntimeError(
            'integrated runtime lacks bounded-recovery markers: ' + ', '.join(missing))
    # The child deliberately sources the base install and then this overlay's
    # local_setup.  If the overlay is already present in the outer process,
    # sourcing the base can move it behind /root/super_ws/install and colcon's
    # non-duplicate hook will not restore precedence.  Fail before any flight.
    prefixes = os.environ.get('AMENT_PREFIX_PATH', '').split(':')
    preloaded = [value for value in prefixes if value.startswith(str(INSTALL_ROOT))]
    if preloaded:
        raise RuntimeError(
            'Active-Yaw overlay is preloaded in the outer campaign environment; '
            'this can select the stale base binary: ' + ', '.join(preloaded))
    return {
        'valid': True,
        'install_root': str(INSTALL_ROOT),
        'runtime_binary': str(RUNTIME_BINARY),
        'markers': 'bounded_multi_distance_v1',
        'outer_overlay_preloaded': False,
    }


def main():
    # v12 -> v11 -> v10 -> v9 -> v7, where the scheduler and validators live.
    base = previous.previous.previous.previous.previous
    verify_runtime_install()
    old_candidate = previous.CANDIDATE
    old_base_run = previous.BASE_RUN
    old_frozen_identity = base.frozen_identity
    old_validate_triplet = base.validate_triplet
    old_write_progress = base.write_progress

    def frozen_identity(root):
        hashes = old_frozen_identity(root)
        for path in (THIS_FILE, RUNTIME_BINARY):
            hashes[str(path)] = base.sha256(path)
        return hashes

    def validate_triplet(item):
        result = old_validate_triplet(item)
        artifact_root = Path(item['output']) / 'artifacts'
        for mode in base.MODES:
            stack_path = artifact_root / (
                f"{item['map']}_run{item['run']}_{mode}.attempt1.stack.log")
            stack = stack_path.read_text(errors='replace') if stack_path.is_file() else ''
            audit = bounded_recovery_runtime_audit(stack)
            result['outcomes'].setdefault(mode, {})[
                'bounded_recovery_runtime_audit'] = audit
            if not audit['valid']:
                result['errors'].append(
                    mode + ': bounded recovery runtime profile audit failed')
        result['valid'] = not result['errors']
        result['blocking'] = bool(result['errors'])
        base.atomic_json(
            Path(item['output']) / 'v7_triplet_validation.json', result)
        return result

    def write_progress(root):
        rows = old_write_progress(root)
        summary = Path(root) / 'summary_by_map.md'
        if summary.is_file():
            summary.write_text(summary.read_text().replace(
                '# Scenario7 c32 n10 progress',
                '# Scenario7 c39 bounded-recovery refresh n10 progress', 1))
        return rows

    previous.CANDIDATE = CANDIDATE
    previous.BASE_RUN = BASE_RUN
    base.frozen_identity = frozen_identity
    base.validate_triplet = validate_triplet
    base.write_progress = write_progress
    try:
        return previous.main()
    finally:
        base.write_progress = old_write_progress
        base.validate_triplet = old_validate_triplet
        base.frozen_identity = old_frozen_identity
        previous.BASE_RUN = old_base_run
        previous.CANDIDATE = old_candidate


if __name__ == '__main__':
    raise SystemExit(main())
