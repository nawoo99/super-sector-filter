#!/usr/bin/env python3
"""Copy selected, unchanged result evidence into the isolated handoff."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

BUNDLE = Path('/root/share/codex_final_results_20261014_all')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def write_new(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('destination', type=Path)
    args = ap.parse_args()
    dest = args.destination.resolve(strict=True)
    if not (dest / 'full_source/snapshot_complete.json').is_file():
        raise SystemExit('Complete source snapshot required')
    target = dest / 'results_summary'
    target.mkdir()
    provenance = dest / 'provenance'
    provenance.mkdir()
    files = [p for p in BUNDLE.iterdir() if p.is_file() and p.name != '05_package_manifest.json']
    for directory in ('data', 'cpu_analysis', 'measurement_details', 'archive_tools'):
        for path in sorted((BUNDLE / directory).rglob('*')):
            if not path.is_file():
                continue
            rel = path.relative_to(BUNDLE)
            if 'mapping_performance' in rel.parts:
                continue
            if path.name in {'raw_profile_reports.csv', 'run_summary_values.csv'}:
                continue
            files.append(path)
    rows = []
    for source in sorted(files):
        rel = source.relative_to(BUNDLE)
        output = target / rel
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise ValueError('Refusing an existing result copy')
        shutil.copy2(source, output)
        checksum = sha(source)
        if sha(output) != checksum:
            raise ValueError('Result copy hash mismatch')
        rows.append({'original_path': str(source), 'copied_path': str(output.relative_to(dest)),
                     'bytes': output.stat().st_size, 'sha256': checksum})
    write_new(provenance / 'result_summary_inventory.json', {
        'schema': 'selected-unchanged-result-evidence-v1', 'source_bundle': str(BUNDLE),
        'selection': 'Top-level guidance/validation except full package manifest; data except mapping_performance; CPU/detail analysis except raw_profile_reports.csv and run_summary_values.csv; archive tools.',
        'not_a_complete_raw_archive': True,
        'excluded': ['recorded_trials/', 'previous_release/', 'data/mapping_performance/',
                     'cpu_analysis/raw_profile_reports.csv', 'measurement_details/run_summary_values.csv',
                     '05_package_manifest.json'],
        'full_archive_name': 'codex_final_results_20261014_all.zip',
        'full_archive_sha256': 'bd3a8db03a5fd93355db7054745539b28628754bb310bde1f1acae8dc6899936',
        'files': rows, 'file_count': len(rows), 'bytes': sum(r['bytes'] for r in rows)})
    inventory = json.loads((dest / 'full_source/source_inventory.json').read_text())
    summary = {
        'schema': 'paper-source-and-evidence-handoff-v1', 'date_kst': '2026-10-15',
        'full_source_files': inventory['source_files'], 'full_source_bytes': inventory['source_bytes'],
        'source_roots': inventory['roots'],
        'source_inventory': '../full_source/source_inventory.json',
        'source_exclusions': '../full_source/source_exclusions.json',
        'source_provenance': '../full_source/source_provenance.json',
        'source_copy_checks': '../full_source/snapshot_complete.json',
        'secret_pattern_scan': '../full_source/source_secret_scan.json',
        'entire_experiment_time_tree_proven': False,
        'provenance_limitation': 'Full current source reconstruction; only explicit frozen identity/hash matches establish experiment-time bytes. No rebuilding or rerunning was done.',
        'result_files': len(rows), 'result_bytes': sum(r['bytes'] for r in rows),
        'main_experiment_runs': 210, 'separate_gate_runs_not_pooled': 30,
        'supplied_complete_results_zip': 'codex_final_results_20261014_all.zip',
        'complete_result_zip_sha256': 'bd3a8db03a5fd93355db7054745539b28628754bb310bde1f1acae8dc6899936',
        'actual_runtime_overlay': '/root/super_ws/forest_liveness_trial_v6_20261006/install',
        'publish_repository': 'nawoo99/super-sector-filter', 'upstream_push_forbidden': 'hku-mars/SUPER',
        'no_source_algorithm_or_result_modifications': True,
        'local_dirty_files_preserved': True,
        'runtime_assets_manifest': 'runtime_assets.json',
    }
    write_new(provenance / 'snapshot_summary.json', summary)
    shutil.copy2(Path(__file__), provenance / 'prepare_handoff.py')
    print(json.dumps({'result_files': len(rows), 'result_bytes': summary['result_bytes'],
                      'full_source_files': inventory['source_files']}))


if __name__ == '__main__':
    main()
