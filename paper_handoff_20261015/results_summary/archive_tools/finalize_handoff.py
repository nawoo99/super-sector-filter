#!/usr/bin/env python3
"""Seal a new, validated Codex handoff without editing any result source."""
from __future__ import annotations

import hashlib
import csv
import json
from pathlib import Path
import re
import zipfile


HERE = Path(__file__).resolve().parent
ORIGINAL = Path('/root/share/results_package_20261012')
FROZEN = Path('/root/share/here/v6_frozen_20261008')
ARCHIVE = HERE.with_suffix('.zip')
SUPER = Path('/root/super_ws/src/SUPER')
INSTALL = Path('/root/super_ws/forest_liveness_trial_v6_20261006/install')


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def verify_sources():
    prior = load(ORIGINAL / 'release_manifest.json')
    require(prior['state'] == 'VALIDATED', 'Original package is not released')
    require(digest(HERE / 'data/release_manifest.json') == digest(ORIGINAL / 'release_manifest.json'),
            'Copied original release manifest changed')
    for name, expected in prior['sha256'].items():
        require(digest(ORIGINAL / name) == expected, f'Original package changed: {name}')
        require(digest(HERE / 'data' / name) == expected, f'Copy differs: {name}')
    frozen = load(FROZEN / 'freeze_manifest.json')
    require(frozen['state'] == 'FROZEN' and len(frozen['sha256']) == 27, 'Invalid original freeze')
    for name, expected in frozen['sha256'].items():
        require(digest(FROZEN / name) == expected, f'Frozen source changed: {name}')
    return {'original_package_files_checked': len(prior['sha256']),
            'original_release_manifest_sha256': digest(ORIGINAL / 'release_manifest.json'),
            'original_frozen_files_checked': 27,
            'original_freeze_manifest_sha256': digest(FROZEN / 'freeze_manifest.json')}


def implementation_evidence():
    inventory = load(FROZEN / 'source_manifest.json')['sha256']
    specifications = [
        (SUPER / 'mission_planner/Apps/native_sector_cpp.cpp', [(688, 722), (1180, 1228)]),
        (SUPER / 'mission_planner/include/mission_planner/sector_heading_policy.hpp', [(1, 23)]),
        (SUPER / 'super_planner/include/ros_interface/ros2/fsm_ros2.hpp',
         [(293, 304), (603, 691), (4394, 4415), (4464, 4498)]),
        (SUPER / 'super_planner/src/super_core/super_planner.cpp', [(3424, 3474)]),
        (SUPER / 'mars_uav_sim/perfect_drone_sim/include/perfect_drone_sim/ros2_perfect_drone_model.hpp', [(651, 673), (752, 776)]),
        (SUPER / 'mars_uav_sim/marsim_render/src/marsim_render.cpp', [(1, 27)]),
        (SUPER / 'mission_planner/include/waypoint_mission/ros2_waypoint_planner.hpp', [(55, 70), (131, 140)]),
        (Path('/root/super-sector-filter/scripts/native_campaign/native_loop_monitor.py'), [(947, 955)]),
        (Path('/root/super-sector-filter/scripts/native_campaign/native_campaign.py'), [(693, 722)]),
        (SUPER / 'super_planner/src/super_core/fsm.cpp', [(313, 332)]),
        (SUPER / 'mission_planner/data/loop24.txt', [(1, 5)]),
        (INSTALL / 'super_planner/share/super_planner/config/static_seedmaps_guard_viability_tight_v7_event_recovery_v1_nearhit_v3.yaml', [(47, 54), (270, 277)]),
        (INSTALL / 'perfect_drone_sim/share/perfect_drone_sim/config/urban_blocks_u01.yaml', [(1, 22)]),
    ]
    records = []
    for path, ranges in specifications:
        lines = path.read_text(encoding='utf-8').splitlines()
        actual = digest(path)
        frozen_path = str(path) if str(path) in inventory else None
        if frozen_path is None and path.name == 'ros2_perfect_drone_model.hpp':
            frozen_path = str(INSTALL / 'perfect_drone_sim/include/perfect_drone_sim/ros2_perfect_drone_model.hpp')
        expected = inventory.get(frozen_path) if frozen_path else None
        if expected:
            require(expected == actual, f'Implementation source differs from frozen inventory: {path}')
        records.append({'path': str(path), 'sha256': actual,
                        'frozen_inventory_path': frozen_path,
                        'matches_frozen_inventory': True if expected else None,
                        'provenance_scope': 'hash_matches_frozen_inventory' if expected else
                            'current_read_only_explanatory_source_not_directly_enumerated',
                        'excerpts': [{'first_line': start, 'last_line': end,
                                     'text': '\n'.join(lines[start - 1:end])}
                                    for start, end in ranges]})
    logs = []
    for mode, run in [('adaptive', 99506), ('sector', 99506)]:
        folder = Path('/root/super-sector-filter/results/topology_polyline_v6_n10_20261006/seven_map_n10/urban_blocks_u01/r01') / mode / 'artifacts'
        path = folder / f'urban_blocks_u01_run{run}_{mode}.attempt1.stack.log'
        require(path.is_file(), f'Missing exact frozen primary log: {path}')
        selected = []
        for line_number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if '[ACTIVE_YAW_SCAN] enabled=' in line or '[SECTOR_HEADING_POLICY]' in line:
                selected.append({'line': line_number, 'text': line})
            elif mode == 'adaptive' and '[SENSOR_ACQUISITION_FRAME]' in line and '"full":1' in line:
                if not any('SENSOR_ACQUISITION_FRAME' in item['text'] for item in selected):
                    selected.append({'line': line_number, 'text': line})
        require(len(selected) >= 2, f'Missing actual mode evidence: {path}')
        actual = digest(path)
        expected = inventory.get(str(path))
        require(expected == actual, f'Frozen primary log hash mismatch: {path}')
        logs.append({'mode': mode, 'path': str(path), 'sha256': actual,
                     'matches_frozen_inventory': True, 'selected_lines': selected})
    return {'schema': 'codex-final-implementation-evidence-v1', 'review_date_kst': '2026-10-14',
            'runtime_modified': False, 'result_labels_modified': False,
            'notes': 'Stored excerpts explain existing implementation; unlisted source files are explicitly qualified.',
            'sources': records, 'actual_primary_mode_logs': logs}


def main():
    outputs = [HERE / '05_package_manifest.json', HERE / '06_validation_summary.json',
               HERE / '07_implementation_evidence.json', ARCHIVE]
    require(not any(path.exists() for path in outputs), 'Refusing to overwrite existing handoff release outputs')
    verified_before = verify_sources()
    report = load(HERE / '04_independent_validation.json')
    counts = report['checked_counts']
    require(report['valid'] and not report['errors'], 'Independent numerical validation failed')
    for key, expected in {'original_main_rows': 210, 'original_gate_rows': 30,
                          'main_run_rows': 210, 'full_raw_original_columns': 686,
                          'map_summary_rows': 21, 'environment_summary_rows': 9,
                          'main_adaptive_cycles': 509, 'gate_adaptive_cycles': 109}.items():
        require(counts[key] == expected, f'Unexpected cohort count: {key}')
    require(digest(HERE / '01_final_results.md') == digest(ORIGINAL / '01_authoritative_result.md'),
            'Final numerical report differs from released source')
    for name in ['00_READ_ME_FIRST.md', '02_implementation_clarifications.md', '03_codex_prompt.txt']:
        text = (HERE / name).read_text(encoding='utf-8')
        require('\ufffd' not in text and not re.search('[\u3040-\u30ff]', text), f'Invalid prose encoding or language: {name}')
    evidence = implementation_evidence()
    with (HERE / 'data/05_all_recorded_fields_210.csv').open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    cadence_errors = [abs(float(row['sensor_hz']) - (int(row['sensor_frames']) - 1) /
                         float(row['sensor_span_s'])) for row in rows]
    require(len(cadence_errors) == 210 and max(cadence_errors) < 1e-6,
            'sensor_hz does not match measured generation cadence')
    verified_after = verify_sources()
    require(verified_before == verified_after, 'Protected sources changed during handoff creation')
    write_new(HERE / '07_implementation_evidence.json', evidence)
    write_new(HERE / '06_validation_summary.json', {
        'state': 'VALIDATED', 'handoff_date_kst': '2026-10-14', 'experiment_freeze_date': '2026-10-08',
        'new_simulations': 0, 'original_sources_unchanged': True, 'copied_values_unchanged': True,
        'original_contact_labels_preserved': True, 'independent_numerical_checks': counts,
        'sensor_hz_definition': 'Observed source generation frequency: (sensor_frames-1)/sensor_span_s, not configured nominal rate',
        'sensor_cadence_formula_rows_checked': len(cadence_errors),
        'sensor_cadence_formula_max_abs_error_hz': max(cadence_errors),
        'error_count': 0, **verified_after})
    files = sorted(path for path in HERE.rglob('*') if path.is_file())
    require(not any(path.is_symlink() for path in HERE.rglob('*')), 'Symlink in portable handoff')
    for path in files:
        require(path.resolve().is_relative_to(HERE.resolve()), f'Unsafe release member: {path}')
        require('__pycache__' not in path.parts and path.suffix not in {'.mp4', '.bag'},
                f'Demo or transient file in numerical handoff: {path}')
    manifest = {'schema': 'codex-final-results-handoff-v1', 'state': 'VALIDATED',
                'handoff_date_kst': '2026-10-14', 'experiment_freeze_date': '2026-10-08',
                'main_runs': 210, 'separate_gate_runs': 30, 'main_adaptive_cycles': 509,
                'new_simulations': 0, 'frozen_outputs_modified': False,
                'numerical_validation': '04_independent_validation.json',
                'implementation_clarifications': '02_implementation_clarifications.md',
                'file_count_excluding_manifest': len(files),
                'sha256': {path.relative_to(HERE).as_posix(): digest(path) for path in files}}
    write_new(HERE / '05_package_manifest.json', manifest)
    files.append(HERE / '05_package_manifest.json')
    with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(files):
            archive.write(path, arcname=(Path(HERE.name) / path.relative_to(HERE)).as_posix())
    with zipfile.ZipFile(ARCHIVE) as archive:
        require(archive.testzip() is None, 'ZIP CRC error')
        require(len(archive.namelist()) == len(files), 'ZIP member count differs')
        for path in files:
            member = (Path(HERE.name) / path.relative_to(HERE)).as_posix()
            require(hashlib.sha256(archive.read(member)).hexdigest() == digest(path), f'ZIP payload mismatch: {member}')
    require(verify_sources() == verified_after, 'Protected evidence changed after ZIP creation')
    print(json.dumps({'state': 'VALIDATED', 'folder': str(HERE), 'archive': str(ARCHIVE),
                      'archive_sha256': digest(ARCHIVE), 'archive_mib': ARCHIVE.stat().st_size / 2**20,
                      'files': len(files), 'main_runs': 210, 'original_raw_fields': 686,
                      'independent_assertions': counts['assertions'], 'errors': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
