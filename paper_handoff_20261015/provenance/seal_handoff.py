#!/usr/bin/env python3
"""Seal an additive handoff, verify ZIP payloads, and create release checksums."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('directory', type=Path)
    ap.add_argument('source_zip', type=Path)
    ap.add_argument('assets_zip', type=Path)
    ap.add_argument('results_zip', type=Path)
    ap.add_argument('checksums', type=Path)
    args = ap.parse_args()
    root = args.directory.resolve(strict=True)
    if args.source_zip.exists() or args.checksums.exists():
        raise SystemExit('Refusing existing ZIP/checksum outputs')
    manifest_path = root / 'provenance/handoff_manifest.json'
    files = []
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('No symlinks permitted in the payload')
        if path.is_file():
            files.append({'path': path.relative_to(root).as_posix(),
                          'bytes': path.stat().st_size, 'sha256': sha(path)})
    manifest = {'schema': 'windows-source-handoff-payload-v1',
                'file_count': len(files), 'bytes': sum(item['bytes'] for item in files),
                'self_excluded': 'provenance/handoff_manifest.json', 'files': files}
    with manifest_path.open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    subprocess.run(['python3', str(root / 'provenance/verify_handoff.py'), str(root)], check=True)
    with zipfile.ZipFile(args.source_zip, 'x', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as archive:
        for path in sorted(root.rglob('*')):
            if path.is_file():
                archive.write(path, (Path(root.name) / path.relative_to(root)).as_posix())
    with zipfile.ZipFile(args.source_zip) as archive:
        if archive.testzip() is not None:
            raise ValueError('Source ZIP CRC mismatch')
        for row in files:
            payload = archive.read(root.name + '/' + row['path'])
            if len(payload) != row['bytes'] or hashlib.sha256(payload).hexdigest() != row['sha256']:
                raise ValueError('Source ZIP payload mismatch: ' + row['path'])
        archived_manifest = archive.read(root.name + '/provenance/handoff_manifest.json')
        if hashlib.sha256(archived_manifest).hexdigest() != sha(manifest_path):
            raise ValueError('Archived handoff manifest mismatch')
    checksum_rows = [(sha(p), p.name, p.stat().st_size) for p in
                     (args.source_zip, args.assets_zip, args.results_zip)]
    if checksum_rows[2][0] != 'bd3a8db03a5fd93355db7054745539b28628754bb310bde1f1acae8dc6899936':
        raise ValueError('Complete final-result archive changed')
    assets_manifest = json.loads((root / 'provenance/runtime_assets.json').read_text())
    if checksum_rows[1][0] != assets_manifest['archive_sha256']:
        raise ValueError('Runtime assets archive mismatch')
    with args.checksums.open('x', encoding='utf-8', newline='\n') as stream:
        for checksum, name, size in checksum_rows:
            stream.write(checksum + '  ' + name + '\n')
    print(json.dumps({'state': 'SEALED', 'payload_files': len(files) + 1,
                      'archives': [{'sha256': c, 'name': n, 'bytes': s} for c, n, s in checksum_rows]}, indent=2))


if __name__ == '__main__':
    main()
