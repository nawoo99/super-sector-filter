#!/usr/bin/env python3
"""Build an additive full-source snapshot; no Git writes, network, or pushes.

The destination must already exist and must be outside all original sources.
Its full_source child must not exist. Unverified files are explicitly labeled.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess


REPO = Path('/root/super-sector-filter')
SUPER = Path('/root/super_ws/src/SUPER')
BRIDGE = Path('/root/super_ws/src/gz_super_bridge')
FROZEN = Path('/root/share/here/v6_frozen_20261008/source_manifest.json')
ROOTS = [('super-sector-filter', REPO), ('super_ws/src/SUPER', SUPER),
         ('super_ws/src/gz_super_bridge', BRIDGE)]
EXCLUDED_DIRS = {'.git', 'build', 'install', 'log', '__pycache__', '.pytest_cache', '.cache',
                 'results', 'artifacts'}
EXCLUDED_SUFFIXES = {'.pcd', '.bag', '.db3', '.mcap', '.so', '.a', '.o', '.pyc', '.pyo',
    '.dll', '.exe', '.lib', '.obj', '.gif', '.png', '.jpg', '.jpeg', '.bmp', '.tiff',
    '.pdf', '.mp4', '.webm', '.dae', '.stl', '.ply', '.blend', '.zip', '.gz', '.tar', '.7z'}
EXCLUDED_NAMES = {'symlink_install_manifest.txt'}
RESULT_EXCEPTIONS = [Path('results/gapfree_d1_maps_20260921_r2/manifest.json'),
    Path('results/scenario7_maps_20260924/manifest.json'),
    Path('results/scenario7_missions_20260924/manifest.json'),
    Path('results/scenario7_missions_20260924/urban_blocks_u01_proof.json'),
    Path('results/scenario7_missions_20260924/forest_cluster_f01_proof.json')]
MAX_TEXT_FILE_BYTES = 16 * 1024 * 1024
EXPECTED_UNPINNED_MODIFIED_SUPER = sorted([
    'mars_uav_sim/mars_quadrotor_msgs/CMakeLists.txt',
    'mars_uav_sim/mars_quadrotor_msgs/package.xml',
    'mars_uav_sim/mars_quadrotor_msgs/ros2_msg/PolynomialTrajectory.msg',
    'mars_uav_sim/marsim_render/CMakeLists.txt',
    'mars_uav_sim/marsim_render/include/marsim_render/marsim_render.hpp',
    'mars_uav_sim/marsim_render/package.xml',
    'mars_uav_sim/marsim_render/src/marsim_render.cpp',
    'mars_uav_sim/perfect_drone_sim/CMakeLists.txt',
    'mars_uav_sim/perfect_drone_sim/ros/ros2.CMakeLists.txt',
    'mars_uav_sim/perfect_drone_sim/ros/ros2.package.xml',
    'mars_uav_sim/perfect_drone_sim/src/ros2_perfect_drone_node.cpp',
    'mission_planner/CMakeLists.txt', 'mission_planner/config/waypoint.yaml',
    'mission_planner/include/waypoint_mission/ros2_waypoint_planner.hpp',
    'mission_planner/package.xml', 'rog_map/CMakeLists.txt',
    'rog_map/include/rog_map/inf_map.h', 'rog_map/include/rog_map/prob_map.h',
    'rog_map/include/rog_map/rog_map_core/config.hpp',
    'rog_map/include/rog_map_ros/rog_map_ros1.hpp',
    'rog_map/include/rog_map_ros/rog_map_ros2.hpp', 'rog_map/package.xml',
    'rog_map/src/rog_map/inf_map.cpp', 'rog_map/src/rog_map/prob_map.cpp',
    'super_planner/Apps/fsm_node_ros2.cpp', 'super_planner/src/super_core/ciri.cpp',
    'super_planner/src/super_core/corridor_generator.cpp', 'super_planner/src/utils/polytope.cpp'])
SECRET_RULES = {
    'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'github_token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b'),
    'aws_key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'openai_like': re.compile(r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{30,}\b'),
    'slack_token': re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
    'credential_literal': re.compile(r'''(?i)(?:password|passwd|api[_-]?key|access[_-]?token|client[_-]?secret|auth[_-]?token)\s*[=:]\s*["'][^"'\n]{8,}["']'''),
    'credential_url': re.compile(r'https?://[^\s/:@]+:[^\s/@]+@'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args, allowed=(0,)):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    result = subprocess.run(['git', '-C', str(root), *args], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode not in allowed:
        # Do not echo arbitrary output or credential-bearing remote URLs.
        raise RuntimeError(f'Git read-only operation failed: {args[0]} code={result.returncode}')
    return result.stdout.decode('utf-8', errors='strict')


def git_metadata(root):
    if not (root / '.git').exists():
        return dict(repository=False, head=None, branch=None, index={}, status={})
    index = {}
    for record in git(root, 'ls-files', '--stage', '-z').split('\0'):
        if not record:
            continue
        meta, path = record.split('\t', 1)
        mode, blob, stage = meta.split()
        if stage != '0':
            raise RuntimeError(f'Unmerged Git index at {root}/{path}')
        if mode == '160000':
            raise RuntimeError(f'Submodule requires explicit vendoring at {root}/{path}')
        index[path] = dict(mode=mode, index_blob=blob)
    status = {}
    for record in git(root, 'status', '--porcelain=v1', '--no-renames', '-z', '--untracked-files=no').split('\0'):
        if record:
            status[record[3:]] = record[:2]
    return dict(repository=True, head=git(root, 'rev-parse', 'HEAD').strip(),
                branch=git(root, 'branch', '--show-current').strip(), index=index, status=status,
                gitmodules_present=(root / '.gitmodules').exists())


def evidence_mapping(manifest):
    """Explicit identity mappings, not an arbitrary equal-hash ownership claim."""
    mapping = collections.defaultdict(list)
    packages = {p.name: p for p in [SUPER / 'mission_planner', SUPER / 'rog_map',
        SUPER / 'super_planner', SUPER / 'mars_uav_sim/mars_quadrotor_msgs',
        SUPER / 'mars_uav_sim/marsim_render', SUPER / 'mars_uav_sim/perfect_drone_sim']}
    installed = '/root/super_ws/forest_liveness_trial_v6_20261006/install/'
    mirror = REPO / 'super_patches/native_seedmap_campaign'
    for name, expected in manifest.items():
        mapping[name].append(dict(evidence_path=name, expected_sha256=expected, mapping='direct_frozen_path'))
        target = None
        kind = None
        if name.startswith(installed):
            parts = Path(name[len(installed):]).parts
            if len(parts) >= 3 and parts[0] in packages:
                if parts[1] == 'include':
                    target = packages[parts[0]] / Path(*parts[1:])
                elif len(parts) > 4 and parts[1] == 'share' and parts[2] == parts[0] and parts[3] in {
                        'config', 'launch', 'rviz2', 'rviz', 'data', 'scripts'}:
                    target = packages[parts[0]] / Path(*parts[3:])
            kind = 'frozen_installed_header_or_resource_to_source'
        elif name.startswith(str(mirror) + '/'):
            parts = Path(name).relative_to(mirror).parts
            for package, package_root in packages.items():
                if parts[0].startswith(package + '_'):
                    subdir = parts[0][len(package) + 1:]
                    target = package_root / Path(*parts[1:]) if subdir == 'root' else package_root / subdir / Path(*parts[1:])
                    break
            kind = 'frozen_named_patch_mirror_to_runtime_source'
        if target is not None:
            mapping[str(target)].append(dict(evidence_path=name, expected_sha256=expected, mapping=kind))
    return mapping


def selected_files(root, exclusions):
    selected = []
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs.sort()
        names.sort()
        allowed_dirs = []
        for name in dirs:
            path = Path(base) / name
            if path.is_symlink():
                raise RuntimeError(f'Symlink directory needs explicit review: {path}')
            if name in EXCLUDED_DIRS:
                exclusions.append(dict(origin_path=str(path), relative_path=str(path.relative_to(root)),
                    kind='directory', reason='generated_history_cache_or_git_directory',
                    descendants_enumerated=False))
            else:
                allowed_dirs.append(name)
        dirs[:] = allowed_dirs
        for name in names:
            path = Path(base) / name
            if path.is_symlink():
                raise RuntimeError(f'Symlink source needs explicit review: {path}')
            if not path.is_file():
                raise RuntimeError(f'Nonregular source entry needs explicit review: {path}')
            reason = None
            if name in EXCLUDED_NAMES:
                reason = 'generated_install_manifest'
            elif path.suffix.lower() in EXCLUDED_SUFFIXES:
                reason = 'data_media_archive_or_compiled_suffix'
            else:
                with path.open('rb') as stream:
                    prefix = stream.read(8)
                if prefix.startswith((b'\x7fELF', b'!<arch>', b'MZ')):
                    reason = 'compiled_binary_magic'
            if reason:
                exclusions.append(dict(origin_path=str(path), relative_path=str(path.relative_to(root)),
                    kind='file', reason=reason, bytes=path.stat().st_size))
            else:
                selected.append(path)
    if root == REPO:
        for rel in RESULT_EXCEPTIONS:
            path = root / rel
            if not path.is_file() or path.is_symlink():
                raise RuntimeError(f'Required runtime manifest missing/unsafe: {path}')
            selected.append(path)
    if len(selected) != len(set(selected)):
        raise RuntimeError('Duplicate source selection')
    return sorted(selected)


def stable_read(path):
    before = path.stat()
    if before.st_size > MAX_TEXT_FILE_BYTES:
        raise RuntimeError(f'Unexpected large source needs review: {path}')
    data = path.read_bytes()
    after = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if identity(before) != identity(after) or len(data) != after.st_size:
        raise RuntimeError(f'Source changed during read: {path}')
    if b'\x00' in data:
        raise RuntimeError(f'Unexpected binary/NUL content needs review: {path}')
    try:
        text = data.decode('utf-8-sig')
    except UnicodeError:
        # Preserve text byte-for-byte, including historical non-UTF8 comments.
        text = data.decode('latin-1')
    return data, text, after


def write_json(path, obj):
    with path.open('x', encoding='utf-8') as output:
        json.dump(obj, output, ensure_ascii=False, allow_nan=False, indent=2)
        output.write('\n')


def build(destination):
    destination = destination.resolve(strict=True)
    if not destination.is_dir() or str(destination) in {'/', '/root', '/tmp', '/root/super_ws', '/root/super_ws/src'}:
        raise RuntimeError('Use an existing isolated destination directory')
    for _, root in ROOTS:
        if destination == root or destination.is_relative_to(root) or root.is_relative_to(destination):
            raise RuntimeError('Destination must be isolated from original source trees')
    target = destination / 'full_source'
    if target.exists() or target.is_symlink():
        raise RuntimeError('Refuse to overwrite an existing full_source snapshot')
    manifest_bytes = FROZEN.read_bytes()
    frozen_object = json.loads(manifest_bytes)
    manifest = frozen_object['sha256']
    mapping = evidence_mapping(manifest)
    by_hash = collections.defaultdict(list)
    for path, digest in manifest.items():
        by_hash[digest].append(path)
    inventory = []
    payloads = []
    exclusions = []
    secret_hits = []
    git_states = {}
    root_summaries = []
    used_relative = set()
    selected_by_root = {}
    for name, root in ROOTS:
        metadata = git_metadata(root)
        git_states[str(root)] = metadata
        selected = selected_files(root, exclusions)
        selected_by_root[root] = selected
        for path in selected:
            data, text, info = stable_read(path)
            relative = path.relative_to(root)
            output_rel = Path(name) / relative
            folded = str(output_rel).casefold()
            if folded in used_relative:
                raise RuntimeError(f'Case-insensitive destination collision: {output_rel}')
            used_relative.add(folded)
            for line_number, line in enumerate(text.splitlines(), 1):
                for rule, pattern in SECRET_RULES.items():
                    if pattern.search(line):
                        secret_hits.append(dict(origin_path=str(path), line=line_number, rule=rule))
            digest = sha(data)
            evidence = [dict(item, byte_match=item['expected_sha256'] == digest)
                        for item in mapping.get(str(path), [])]
            verified = [item for item in evidence if item['byte_match']]
            tracked = str(relative) in metadata['index']
            status = metadata['status'].get(str(relative))
            state = 'not_in_git_repository' if not metadata['repository'] else (
                    'untracked' if not tracked else ('tracked_changed' if status else 'tracked_clean'))
            row = dict(source_root=str(root), source_relative_path=str(relative),
                origin_path=str(path), snapshot_path=str(Path('full_source') / output_rel),
                bytes=len(data), sha256=digest, source_mode=oct(stat.S_IMODE(info.st_mode)),
                snapshot_mode='0755' if info.st_mode & stat.S_IXUSR else '0644',
                git_tracked=tracked if metadata['repository'] else None,
                git_current_state=state, git_porcelain_status=status,
                git_baseline_head=metadata['head'], git_index_entry=metadata['index'].get(str(relative)),
                frozen_byte_verified=bool(verified), frozen_identity_evidence=evidence,
                frozen_verified_source_evidence_paths=sorted({item['evidence_path'] for item in verified}),
                frozen_same_bytes_anywhere=bool(by_hash.get(digest)),
                frozen_same_hash_other_paths=sorted(set(by_hash.get(digest, [])) - {item['evidence_path'] for item in evidence}),
                experiment_time_entire_tree_proven=False,
                explicit_runtime_results_exception=root == REPO and relative in RESULT_EXCEPTIONS)
            inventory.append(row)
            payloads.append((output_rel, data, row))
        entries = [row for row in inventory if row['source_root'] == str(root)]
        root_summaries.append(dict(source_root=str(root), snapshot_prefix=str(Path('full_source') / name),
            files=len(entries), bytes=sum(row['bytes'] for row in entries),
            frozen_byte_verified=sum(row['frozen_byte_verified'] for row in entries),
            frozen_unverified=sum(not row['frozen_byte_verified'] for row in entries),
            git_states=dict(collections.Counter(row['git_current_state'] for row in entries))))
    if len(selected_by_root[SUPER]) != 1287 or len(selected_by_root[BRIDGE]) != 3:
        raise RuntimeError('SUPER/bridge source inventory drifted from audited 1287/3; review before publishing')
    super_changed = git_states[str(SUPER)]['status']
    unmatched_changed = sorted(row['source_relative_path'] for row in inventory
        if row['source_root'] == str(SUPER) and row['source_relative_path'] in super_changed
        and not row['frozen_same_bytes_anywhere'])
    if unmatched_changed != EXPECTED_UNPINNED_MODIFIED_SUPER:
        raise RuntimeError('The audited 28 changed/unpinned SUPER paths drifted; review before publishing')
    secret_report = dict(schema='source-snapshot-secret-scan-v1', scanned_files=len(inventory),
        rule_names=sorted(SECRET_RULES), hit_count=len(secret_hits), hits=secret_hits,
        content_or_credentials_emitted=False, full_security_audit=False,
        status='PASS' if not secret_hits else 'REVIEW_REQUIRED',
        limitation='Pattern scan only; no absence-of-secrets guarantee. No matched text is emitted.')
    # Even on a scan hit, write only metadata, never copy suspect source.
    target.mkdir()
    write_json(target / 'source_secret_scan.json', secret_report)
    if secret_hits:
        raise RuntimeError('Secret-pattern candidates require review; sources were not copied')
    write_json(target / 'copy_started.json', dict(status='COPY_STARTED', complete=False))
    for output_rel, data, row in payloads:
        output = target / output_rel
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('xb') as stream:
            stream.write(data)
        output.chmod(int(row['snapshot_mode'], 8))
        if sha(output.read_bytes()) != row['sha256']:
            raise RuntimeError(f'Copied source hash mismatch: {row["snapshot_path"]}')
    # Validate source stability rather than silently mixing concurrent edits.
    for row in inventory:
        if sha(Path(row['origin_path']).read_bytes()) != row['sha256']:
            raise RuntimeError(f'Original source changed while snapshotting: {row["origin_path"]}')
    for _, root in ROOTS:
        original = git_states[str(root)]
        latest = git_metadata(root)
        if latest != original:
            raise RuntimeError(f'Git state changed while snapshotting: {root}')
    for _, root in ROOTS:
        if selected_files(root, []) != selected_by_root[root]:
            raise RuntimeError(f'Source file inventory changed while snapshotting: {root}')
    if FROZEN.read_bytes() != manifest_bytes:
        raise RuntimeError('Frozen reference manifest changed during snapshot')
    for root in (REPO, SUPER):
        if not (target / ('super-sector-filter' if root == REPO else 'super_ws/src/SUPER') / 'README.md').is_file():
            raise RuntimeError('Original root README was not preserved')
    write_json(target / 'source_inventory.json', dict(schema='complete-source-snapshot-inventory-v1',
        source_files=len(inventory), source_bytes=sum(row['bytes'] for row in inventory),
        roots=root_summaries, files=inventory,
        meanings=dict(frozen_byte_verified='Current bytes equal the frozen SHA256 for a direct source identity or explicit installed/mirror mapping.',
            frozen_same_bytes_anywhere='Matching bytes somewhere in frozen manifest, not necessarily the same source identity.',
            frozen_unverified='No matching explicit frozen source identity; current snapshot only, not proof of experiment-time bytes.')))
    write_json(target / 'source_exclusions.json', dict(schema='source-snapshot-exclusions-v1',
        excluded_directory_names=sorted(EXCLUDED_DIRS), excluded_suffixes=sorted(EXCLUDED_SUFFIXES),
        excluded_names=sorted(EXCLUDED_NAMES), compiled_magic=['ELF', 'ar archive', 'MZ'],
        max_text_file_bytes=MAX_TEXT_FILE_BYTES, large_unexpected_text='abort rather than silently omit',
        runtime_results_exceptions=[str(path) for path in RESULT_EXCEPTIONS],
        excluded_entries=exclusions, directory_descendants_not_enumerated=True,
        external_assets_archive_created=False))
    baseline = {}
    for root_name, metadata in git_states.items():
        baseline[root_name] = {key: value for key, value in metadata.items() if key != 'index'}
        baseline[root_name]['tracked_index_entries'] = len(metadata['index'])
    builder = Path(__file__).resolve()
    builder_bytes = builder.read_bytes()
    with (target / 'snapshot_builder.py').open('xb') as stream:
        stream.write(builder_bytes)
    frozen_copy = target / 'frozen_v6_source_manifest.reference.json'
    with frozen_copy.open('xb') as stream:
        stream.write(manifest_bytes)
    write_json(target / 'source_provenance.json', dict(schema='complete-source-snapshot-provenance-v1',
        created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        roots=root_summaries, baseline_git=baseline,
        frozen_manifest_origin=str(FROZEN), frozen_manifest_sha256=sha(manifest_bytes),
        frozen_candidate=frozen_object.get('candidate'),
        frozen_manifest_entries=len(manifest), complete_experiment_time_source_verified=False,
        exact_28_modified_SUPER_paths_without_any_frozen_byte_hash=unmatched_changed,
        exact_28_audited_list_matched=True, builder_origin=str(builder), builder_sha256=sha(builder_bytes),
        source_changes_made=False, git_writes_made=False, push_attempted=False,
        licenses=dict(root_SUPER_license_present=False,
            package_declarations={'most_packages': 'BSD', 'mars_quadrotor_msgs': 'Apache License 2.0'},
            vendor_license_and_header_notices_preserved=True, license_reassignment=False,
            new_blanket_license_added=False),
        submodules_copied=False, symlinks_followed=False,
        limitations=['Snapshot includes untracked and dirty source, not only upstream Git HEAD.',
            'Frozen verification covers named/hash-matched subsets; unpinned files are current sources.',
            'Assets, generated install/build trees, binaries and historical results are external to this source snapshot.',
            'Three explicit small results manifests and two mission proof JSON files are retained because runtime code depends on them.',
            'Sources can be inspected on Windows; native Windows execution was not tested.']))
    # A distinct final marker avoids rewriting any previously emitted file.
    write_json(target / 'snapshot_complete.json', dict(status='COMPLETE', complete=True,
        source_files=len(inventory), source_bytes=sum(row['bytes'] for row in inventory),
        metadata_sha256={p.name: sha(p.read_bytes()) for p in sorted(target.iterdir()) if p.is_file()},
        no_source_mutations=True, no_git_mutations=True))
    print(json.dumps(dict(status='COMPLETE', destination=str(target), roots=root_summaries,
        source_files=len(inventory), source_bytes=sum(row['bytes'] for row in inventory),
        secret_pattern_hits=0, full_tree_experiment_time_proven=False), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='Existing isolated destination; full_source must not exist')
    args = parser.parse_args()
    build(args.destination)


if __name__ == '__main__':
    main()
