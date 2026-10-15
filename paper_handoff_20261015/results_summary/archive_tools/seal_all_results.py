#!/usr/bin/env python3
"""Release all recorded final results plus validated CPU/detail exports."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parents[1]
ORIGINAL = Path('/root/share/results_package_20261012')
BASE = Path('/root/share/codex_final_results_20261014')
FROZEN = Path('/root/share/here/v6_frozen_20261008')
ARCHIVE = HERE.with_suffix('.zip')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def passed(report):
    return report.get('status') == 'PASS' or report.get('state') in {'PASS', 'VALIDATED'} or report.get('valid') is True


def verify_originals():
    prior = load(ORIGINAL / 'release_manifest.json')
    require(prior['state'] == 'VALIDATED', 'Original data package not validated')
    for name, expected in prior['sha256'].items():
        require(digest(ORIGINAL / name) == expected, f'Original data changed: {name}')
        require(digest(HERE / 'data' / name) == expected, f'Copied data changed: {name}')
    base = load(BASE / '05_package_manifest.json')
    for name, expected in base['sha256'].items():
        require(digest(BASE / name) == expected, f'Previous handoff changed: {name}')
    frozen = load(FROZEN / 'freeze_manifest.json')
    require(frozen['state'] == 'FROZEN' and len(frozen['sha256']) == 27, 'Unexpected freeze')
    for name, expected in frozen['sha256'].items():
        require(digest(FROZEN / name) == expected, f'Frozen result changed: {name}')
    return {'original_data_files_verified': len(prior['sha256']),
            'previous_handoff_files_verified': len(base['sha256']),
            'frozen_result_files_verified': len(frozen['sha256']),
            'original_manifest_sha256': digest(ORIGINAL / 'release_manifest.json'),
            'frozen_manifest_sha256': digest(FROZEN / 'freeze_manifest.json')}


def main():
    outputs = [HERE / '05_package_manifest.json', HERE / '06_validation_summary.json',
               HERE / '09_all_result_index.json', ARCHIVE]
    require(not any(path.exists() for path in outputs), 'Refusing to overwrite a completed full release')
    protected_before = verify_originals()
    primary = load(HERE / '04_independent_validation.json')
    require(primary['valid'] and not primary['errors'], 'Primary numeric validation failed')
    require(primary['checked_counts']['main_run_rows'] == 210 and
            primary['checked_counts']['main_adaptive_cycles'] == 509, 'Incorrect primary cohort')
    cpu = load(HERE / 'cpu_analysis/validation.json')
    cpu_independent = load(HERE / 'cpu_analysis/independent_validation.json')
    require(passed(cpu) and passed(cpu_independent), 'CPU validation failed')
    require(cpu['run_rows'] == 210 and cpu_independent['checked_runs'] == 210 and
            cpu_independent['checked_raw_profiles'] == 88136 and
            cpu_independent['checked_stage_rows'] == 8190, 'CPU result completeness failed')
    require(cpu['complete_simulator_excluded_cpu_claim'] is False, 'Incorrect CPU-total scope')
    details = load(HERE / 'measurement_details/validation.json')
    require(passed(details), 'Detailed measurement validation failed')
    coverage = load(HERE / 'recorded_trials/recording_coverage.json')
    require(coverage['state'] == 'VALIDATED' and coverage['main_runs'] == 210 and
            coverage['separate_gate_runs'] == 30 and coverage['original_recorded_files'] == 4720,
            'Recorded run evidence incomplete')
    with (HERE / 'recorded_trials/file_index.csv').open(newline='', encoding='utf-8') as stream:
        copied = list(csv.DictReader(stream))
    require(len(copied) == 4720, 'Incorrect recorded-file index size')
    inventory = load(FROZEN / 'source_manifest.json')['sha256']
    for item in copied:
        destination = HERE / item['copied_file']
        require(destination.resolve().is_relative_to(HERE.resolve()), 'Unsafe copied path')
        expected = inventory[item['original_file']]
        require(item['sha256'] == expected and digest(destination) == expected,
                f'Copied measurement changed: {destination}')
    for name in ['00_READ_ME_FIRST.md', '01_final_results.md', '02_implementation_clarifications.md',
                 '03_codex_prompt.txt', '08_cpu_without_simulator.md']:
        text = (HERE / name).read_text(encoding='utf-8')
        require('\ufffd' not in text and not re.search('[\u3040-\u30ff]', text), f'Invalid prose: {name}')
    summary = {
        'schema': 'complete-final-result-validation-v1', 'state': 'VALIDATED',
        'handoff_date_kst': '2026-10-14', 'experiment_freeze_date': '2026-10-08',
        'main_runs': 210, 'separate_gate_runs': 30, 'new_simulations': 0,
        'outcomes_modified': False, 'runtime_modified': False,
        'original_and_previous_packages_unchanged': True,
        'primary_numeric_assertions': primary['checked_counts']['assertions'],
        'cpu_independent_assertions': cpu_independent['assertions'],
        'raw_original_csv_fields': primary['checked_counts']['full_raw_original_columns'],
        'main_adaptive_cycles': 509, 'raw_cpu_profile_records': 88136,
        'cpu_stage_rows': 8190, 'thread_role_markers': 770,
        'preserved_original_result_files': len(copied),
        'preserved_original_result_bytes': sum(int(item['bytes']) for item in copied),
        'detail_validation': details, 'protected_sources': protected_before,
        'error_count': 0,
        'cpu_definition': 'Instrumented exclusive functional CPU subtotal, not complete simulator-excluded autonomy CPU',
    }
    write_new(HERE / '06_validation_summary.json', summary)
    index = {
        'schema': 'all-final-result-index-v1', 'state': 'VALIDATED',
        'main_runs': 210, 'separate_gate_runs': 30,
        'read_first': ['00_READ_ME_FIRST.md', '02_implementation_clarifications.md',
                       '01_final_results.md', '08_cpu_without_simulator.md'],
        'primary_results': 'data/16_result_bundle.json',
        'cpu_function_results': 'cpu_analysis/result.json',
        'cpu_by_map': 'cpu_analysis/summary_by_map_21.csv',
        'cpu_by_environment': 'cpu_analysis/summary_by_environment_9.csv',
        'all_original_run_files': 'recorded_trials/file_index.csv',
        'original_run_directory_index': 'recorded_trials/run_index.csv',
        'nested_summary_values': 'measurement_details/run_summary_values.csv',
        'process_details': 'measurement_details/process_profiles.csv',
        'thread_details': 'measurement_details/thread_profiles.csv',
        'resource_details': 'measurement_details/run_resource_summary.csv',
        'map_images': 'data/environment_maps',
        'prompt': '03_codex_prompt.txt',
        'no_outcome_relabeling': True,
        'gate_demos_historical_runs_not_pooled_with_main': True,
    }
    write_new(HERE / '09_all_result_index.json', index)
    require(verify_originals() == protected_before, 'Protected inputs changed during release')
    entries = sorted(path for path in HERE.rglob('*') if path.is_file())
    require(not any(path.is_symlink() for path in HERE.rglob('*')), 'Symlink in complete handoff')
    require(not any('__pycache__' in path.parts for path in entries), 'Generated bytecode in handoff')
    manifest = {
        'schema': 'complete-final-results-release-v1', 'state': 'VALIDATED',
        'handoff_date_kst': '2026-10-14', 'experiment_freeze_date': '2026-10-08',
        'main_runs': 210, 'separate_gate_runs': 30, 'new_simulations': 0,
        'original_frozen_records_preserved': True, 'raw_original_result_files': 4720,
        'includes_instrumented_function_cpu': True,
        'cpu_metric_is_complete_simulator_excluded_total': False,
        'file_count_excluding_manifest': len(entries),
        'sha256': {path.relative_to(HERE).as_posix(): digest(path) for path in entries},
    }
    write_new(HERE / '05_package_manifest.json', manifest)
    entries.append(HERE / '05_package_manifest.json')
    print(json.dumps({'state': 'CREATING_COMPLETE_ZIP', 'files': len(entries),
                      'uncompressed_mib': sum(path.stat().st_size for path in entries) / 2**20}), flush=True)
    with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3, allowZip64=True) as archive:
        for number, path in enumerate(sorted(entries), 1):
            archive.write(path, arcname=(Path(HERE.name) / path.relative_to(HERE)).as_posix())
            if number % 1000 == 0:
                print(json.dumps({'state': 'ZIP_WRITING', 'files': number, 'total': len(entries)}), flush=True)
    with zipfile.ZipFile(ARCHIVE) as archive:
        require(archive.testzip() is None, 'ZIP CRC failure')
        require(len(archive.namelist()) == len(entries), 'ZIP member count failure')
        for path in entries:
            member = (Path(HERE.name) / path.relative_to(HERE)).as_posix()
            actual = hashlib.sha256()
            with archive.open(member) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    actual.update(chunk)
            require(actual.hexdigest() == digest(path), f'ZIP payload mismatch: {member}')
    require(verify_originals() == protected_before, 'Protected inputs changed after release')
    print(json.dumps({'state': 'VALIDATED', 'folder': str(HERE), 'archive': str(ARCHIVE),
                      'archive_mib': ARCHIVE.stat().st_size / 2**20,
                      'archive_sha256': digest(ARCHIVE), 'files': len(entries),
                      'primary_runs': 210, 'separate_gate_runs': 30,
                      'original_recorded_files': 4720, 'errors': 0}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
