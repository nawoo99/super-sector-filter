#!/usr/bin/env python3
"""Copy every frozen result file in exactly 210 main and 30 gate run folders."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parents[1]
FROZEN = Path('/root/share/here/v6_frozen_20261008')
OUTPUT = HERE / 'recorded_trials'
EXPECTED = {'main': (210, 4130, 997421965), 'separate_gate': (30, 590, 161586454)}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def write_csv(path, rows):
    with path.open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    require(not OUTPUT.exists(), 'Refusing to overwrite existing recorded_trials')
    inventory = json.loads((FROZEN / 'source_manifest.json').read_text(encoding='utf-8'))['sha256']
    selected, keys, directories = [], set(), set()
    for cohort, filename in [('main', 'main_210.csv'), ('separate_gate', 'forest_gate_30.csv')]:
        with (FROZEN / filename).open(newline='', encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        require(len(rows) == EXPECTED[cohort][0], f'Unexpected rows for {cohort}')
        for row in rows:
            key = (cohort, row['map'], int(row['repeat']), row['mode'])
            require(key not in keys, f'Duplicate frozen run key: {key}')
            keys.add(key)
            source = Path(row['directory'])
            require(source.is_absolute() and source.is_dir() and not source.is_symlink(), f'Invalid run source: {source}')
            require(source.resolve().is_relative_to(Path('/root/super-sector-filter/results').resolve()),
                    f'Run outside results scope: {source}')
            require(str(source) not in directories, f'Duplicate run source: {source}')
            directories.add(str(source))
            paths = sorted(source.rglob('*'))
            require(not any(path.is_symlink() for path in paths), f'Symlink in run result: {source}')
            files = [path for path in paths if path.is_file()]
            require(all(path.is_file() or path.is_dir() for path in paths), f'Nonregular run artifact: {source}')
            for path in files:
                require(path.suffix in {'.csv', '.json', '.jsonl', '.log'}, f'Unexpected result type: {path}')
                require(str(path) in inventory, f'Result missing frozen hash: {path}')
                require(digest(path) == inventory[str(path)], f'Frozen run artifact changed: {path}')
            relative = Path(cohort) / row['map'] / f"r{int(row['repeat']):02d}" / row['mode']
            selected.append((cohort, row, source, relative, files))
    for cohort, expected in EXPECTED.items():
        cases = [item for item in selected if item[0] == cohort]
        count = sum(len(item[4]) for item in cases)
        size = sum(path.stat().st_size for item in cases for path in item[4])
        require((len(cases), count, size) == expected, f'Run inventory differs for {cohort}: {(len(cases),count,size)}')
    OUTPUT.mkdir()
    run_index, file_index = [], []
    for index, (cohort, row, source, relative, files) in enumerate(selected, 1):
        destination = OUTPUT / relative
        shutil.copytree(source, destination)
        copied = sorted(path for path in destination.rglob('*') if path.is_file())
        require(len(copied) == len(files), f'Copy file count differs: {source}')
        for path in files:
            local = path.relative_to(source)
            target = destination / local
            expected = inventory[str(path)]
            require(digest(target) == expected and digest(path) == expected, f'Byte mismatch: {path}')
            file_index.append({'cohort': cohort, 'map': row['map'], 'repeat': int(row['repeat']),
                               'mode': row['mode'], 'run': int(row['run']),
                               'original_file': str(path),
                               'copied_file': target.relative_to(HERE).as_posix(),
                               'bytes': target.stat().st_size, 'sha256': expected,
                               'matches_frozen_inventory': True})
        run_index.append({'cohort': cohort, 'map': row['map'], 'repeat': int(row['repeat']),
                          'mode': row['mode'], 'run': int(row['run']),
                          'original_directory': str(source),
                          'copied_directory': destination.relative_to(HERE).as_posix(),
                          'file_count': len(files), 'bytes': sum(path.stat().st_size for path in files)})
        if index % 30 == 0:
            print(json.dumps({'state': 'COPYING_RECORDED_RESULTS', 'runs': index, 'total': 240}), flush=True)
    write_csv(OUTPUT / 'run_index.csv', run_index)
    write_csv(OUTPUT / 'file_index.csv', file_index)
    coverage = {'schema': 'complete-frozen-run-artifacts-v1', 'state': 'VALIDATED',
                'collection_date_kst': '2026-10-14', 'experiment_freeze_date': '2026-10-08',
                'source_manifest_sha256': digest(FROZEN / 'source_manifest.json'),
                'main_runs': 210, 'separate_gate_runs': 30,
                'original_recorded_files': len(file_index),
                'original_recorded_bytes': sum(item['bytes'] for item in file_index),
                'all_files_pinned_by_frozen_source_inventory': True,
                'all_original_and_copy_hashes_match': True, 'new_simulations': 0,
                'runtime_changed': False, 'original_results_changed': False,
                'included': 'Every regular result file recursively inside the exact frozen 240 run directories',
                'excluded': 'Source/runtime binaries, external static PCD assets, unrelated runs and demonstration recordings',
                'cohorts': {cohort: {'runs': counts[0], 'files': counts[1], 'bytes': counts[2]}
                            for cohort, counts in EXPECTED.items()}}
    write_json(OUTPUT / 'recording_coverage.json', coverage)
    print(json.dumps(coverage, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
