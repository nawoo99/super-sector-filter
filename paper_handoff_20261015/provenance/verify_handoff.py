#!/usr/bin/env python3
"""Read-only SHA256 validation of an extracted handoff (Python 3, no ROS required)."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory', type=Path, nargs='?', default=Path(__file__).resolve().parent.parent)
    ap.add_argument('--with-runtime-assets', action='store_true')
    args = ap.parse_args()
    root = args.directory.resolve(strict=True)
    inventory = json.loads((root / 'provenance/handoff_manifest.json').read_text(encoding='utf-8'))
    checked, errors = 0, []

    def check(relative, size, checksum):
        nonlocal checked
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            errors.append({'path': relative, 'error': 'unsafe_path'})
        elif not path.is_file():
            errors.append({'path': relative, 'error': 'missing'})
        elif path.stat().st_size != size or sha(path) != checksum:
            errors.append({'path': relative, 'error': 'size_or_sha256_mismatch'})
        else:
            checked += 1

    for row in inventory['files']:
        check(row['path'], row['bytes'], row['sha256'])
    if args.with_runtime_assets:
        manifest = json.loads((root / 'provenance/runtime_assets.json').read_text(encoding='utf-8'))
        for row in manifest['assets']:
            check(row['archive_path'], row['bytes'], row['sha256'])
    print(json.dumps({'status': 'PASS' if not errors else 'FAIL',
                      'checked': checked, 'runtime_assets_requested': args.with_runtime_assets,
                      'errors': errors}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == '__main__':
    main()
