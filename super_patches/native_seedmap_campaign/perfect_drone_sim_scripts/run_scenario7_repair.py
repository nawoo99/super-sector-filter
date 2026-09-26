#!/usr/bin/env python3
"""Separate repair cohort: fresh ON qualification and independent OFF rounds.

The pinned v2 controller is compiled in a private namespace. Only explicit
cohort identity/count/report plumbing and overlay bindings differ; existing
gates, memory sentinel, failure retention and no-retry scheduling are reused.
No flight is launched by --dry-run or --report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import types

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import scenario7_repair_runtime as runtime
import scenario7_repair_loop_monitor as observer
import scenario7_repair_pcd_index as pcd_index

REPO = Path('/root/super-sector-filter')
SOURCE = Path('/root/super_ws/src/SUPER')
PREVIOUS = SCRIPTS / 'run_scenario7_n10.py'
PREVIOUS_SHA256 = 'dea81b6e85b761482d095506bc07cfd8cc39b0c743c9e830af34c511e83e8dd4'
PRIOR_ROOT = REPO / 'results/scenario7_n10_20260925_213533_3120932'
PRIOR_INVENTORY = PRIOR_ROOT / 'frozen_inputs_and_evidence.json'
PRIOR_INVENTORY_SHA256 = '9345d9172a77e4a6be99078be06f217f0697dbed3a5b9b87a82217585935fcd1'
SCHEMA = 'scenario7-repair-manual-v1'
CANDIDATE = 'c26_scenario7_repair_v1'
PROTOCOL = REPO / 'docs/scenario7_repair_20260926.md'
MODIFIED_CPP = (
    'super_planner/include/data_structure/base/polytope.h',
    'super_planner/include/data_structure/cmd_traj.h',
    'super_planner/include/super_core/super_planner.h',
    'super_planner/src/super_core/super_planner.cpp',
)
ADDED_CPP = (
    'super_planner/include/fsm/initial_footprint_egress_receipt.hpp',
    'super_planner/include/fsm/trajectory_handoff_guard.hpp',
    'super_planner/test/initial_footprint_egress_receipt_test.cpp',
    'super_planner/test/initial_footprint_cmd_traj_test.cpp',
    'super_planner/test/trajectory_handoff_guard_test.cpp',
    'super_planner/test/simplify_sfc_progress_test.cpp',
)
# This preexisting opt-in diagnostic dependency predates the repair but was
# omitted by the completed campaign's source inventory. Admit its exact bytes,
# not an open-ended exception for any new production header.
PRIOR_EXTRA_CPP = {
    'rog_map/include/rog_map/diagnostic_trace.hpp':
        'd41f6dee49ef7d0b72df438693da508c35ab591072a399cff5de5257f7dfabf5',
}
PACKAGES = ('rog_map', 'super_planner', 'mars_uav_sim/perfect_drone_sim')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def mirror_path(relative):
    package, category, suffix = relative.split('/', 2)
    return REPO / 'super_patches/native_seedmap_campaign' / (package + '_' + category) / suffix


def admitted_cpp_paths():
    return {str(path) for relative in MODIFIED_CPP
            for path in (SOURCE / relative, mirror_path(relative))}


def verify_prior_inventory(inventory, *, allowed=None):
    """No map, original binary, old observation or unlisted change is admitted."""
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError('Missing completed campaign inventory')
    allowed = admitted_cpp_paths() if allowed is None else set(allowed)
    changed, unexpected = [], []
    for name, expected in inventory.items():
        if (not isinstance(name, str) or not Path(name).is_absolute()
                or not isinstance(expected, str) or len(expected) != 64):
            raise ValueError('Malformed completed campaign inventory')
        path = Path(name)
        if not path.is_file():
            unexpected.append(dict(path=name, reason='missing'))
            continue
        current = sha(path)
        if current != expected:
            record = dict(path=name, baseline_sha256=expected, current_sha256=current)
            (changed if name in allowed else unexpected).append(record)
    if unexpected:
        raise ValueError('Unadmitted change to completed campaign inputs/evidence: ' + repr(unexpected))
    return changed


def verify_production_additions(inventory):
    allowed = set(ADDED_CPP) | set(PRIOR_EXTRA_CPP)
    observed = []
    for package in PACKAGES:
        for directory in ('include', 'src'):
            for path in (SOURCE / package / directory).rglob('*'):
                if (not path.is_file() or path.suffix not in ('.h', '.hpp', '.cpp', '.cc', '.c', '.cu', '.cuh')
                        or str(path) in inventory):
                    continue
                relative = str(path.relative_to(SOURCE))
                if relative not in allowed:
                    raise ValueError('Unadmitted new production C++ input: ' + relative)
                digest = sha(path)
                if relative in PRIOR_EXTRA_CPP and digest != PRIOR_EXTRA_CPP[relative]:
                    raise ValueError('Preexisting diagnostic dependency changed: ' + relative)
                observed.append(dict(path=str(path), sha256=digest,
                    classification='pinned_preexisting_dependency' if relative in PRIOR_EXTRA_CPP else 'repair_added_header'))
    return observed


def freeze_sources(root, admission, namespace, binding):
    """Fresh repair admission, deliberately not the old C25 source admission."""
    base = namespace.base
    if sha(PRIOR_INVENTORY) != PRIOR_INVENTORY_SHA256:
        raise ValueError('Completed campaign inventory changed')
    prior = base.load_document(PRIOR_INVENTORY)
    changed = verify_prior_inventory(prior)
    additions = verify_production_additions(prior)
    relative_inputs = MODIFIED_CPP + ADDED_CPP + tuple(PRIOR_EXTRA_CPP)
    required = [SOURCE / relative for relative in relative_inputs]
    for relative, path in zip(relative_inputs, required):
        mirrored = mirror_path(relative)
        if not path.is_file() or not mirrored.is_file() or sha(path) != sha(mirrored):
            raise ValueError('Repair runtime/mirror mismatch: ' + relative)
    mission_admission = namespace.missions.validate_missions()
    if admission.get('valid') is not True or mission_admission.get('valid') is not True:
        raise ValueError('Map/mission admission failed')
    frozen = {name: digest for name, digest in prior.items()
              if not Path(name).is_relative_to(REPO / 'results')}
    for record in changed:
        frozen[record['path']] = record['current_sha256']
    for evidence in (admission, mission_admission):
        for name, expected in evidence['assets_sha256'].items():
            if sha(name) != expected:
                raise ValueError('Map/mission changed during repair admission: ' + name)
            frozen[name] = expected
    assets = binding.asset_paths()
    files = {Path(__file__).resolve(), PREVIOUS, PRIOR_INVENTORY, PROTOCOL,
             SCRIPTS / 'run_scenario7_repair.sh',
             REPO / 'scripts/native_campaign/run_scenario7_repair.sh',
             *required, *(mirror_path(relative) for relative in relative_inputs),
             *assets}
    # Inventory all active source/build/config/launch/test inputs, including
    # newly added files absent from the previous campaign's inventory.
    for package in PACKAGES:
        package_root = SOURCE / package
        for directory in ('include', 'src', 'config', 'launch', 'scripts', 'test'):
            files.update(path for path in (package_root / directory).rglob('*')
                         if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc')
        files.update((package_root / 'CMakeLists.txt', package_root / 'package.xml'))
    files.update((REPO / 'super_patches/native_seedmap_campaign/perfect_drone_sim_scripts').glob('*scenario7*'))
    files.update((REPO / 'super_patches/native_seedmap_campaign/perfect_drone_sim_test').glob('test*scenario7*.py'))
    base.freeze_files(frozen, sorted(files))
    identity = binding.identity()
    return frozen, dict(schema='scenario7-repair-admission-v1',
        candidate=CANDIDATE, previous_campaign=str(PRIOR_ROOT),
        previous_inventory_sha256=sha(PRIOR_INVENTORY), previous_files_verified=len(prior),
        admitted_source_changes=changed, added_cpp_files=[str(SOURCE / relative) for relative in ADDED_CPP],
        admitted_production_additions=additions,
        modified_cpp_allowlist=sorted(admitted_cpp_paths()),
        repair_runtime=identity, scenario7=admission, scenario7_missions=mission_admission,
        planner_algorithm_changed=True, old_cohorts_not_pooled=True,
        original_install_retained=True, original_results_preserved=True,
        memory_runaway_limit_mib=namespace.base.MEMORY_RUNAWAY_MIB)


# Each substitution is exact and counted against the pinned complete v2 file.
# This makes the small adaptation reviewable without copying its ~680 lines or
# mutating imported legacy module globals. Run-ID stride 10 is NOT a round count.
REPLACEMENTS = (
    ("    parser.add_argument('--output', type=Path)",
     "    parser.add_argument('--output', type=Path)\n"
     "    parser.add_argument('--rounds', type=int, default=COUNTS['test10'], help='OFF repetitions per map/mode, 1..10 (default 10); report uses stored count')", 1),
    ('10 * len(members)', 'COUNTS["test10"] * len(members)', 1),
    ('{10*len(members)}', "{COUNTS['test10']*len(members)}", 1),
    ('support.MAP_LABELS[name], name, mode, 10)', 'support.MAP_LABELS[name], name, mode, COUNTS["test10"])', 1),
    ("'# Seven-map n10 results'", "'# Seven-map repair results'", 1),
    ('× 10회 = {30*len(maps)}회.', '× {COUNTS["test10"]}회 = {3*COUNTS["test10"]*len(maps)}회.', 1),
    ("'scenario7_n10_'", "'scenario7_repair_'", 1),
    ("'Not a scenario7-n10 campaign directory'", "'Not a scenario7 repair campaign directory'", 1),
    ('requested_off_flights=30*len(maps)', 'requested_off_flights=3*COUNTS["test10"]*len(maps)', 1),
    ("unprofiled_runs_per_mode=10 if phase == 'test10' else 0", "unprofiled_runs_per_mode=COUNTS['test10'] if phase == 'test10' else 0", 1),
    ('schema=SCHEMA, maps=list(maps), modes=list(MODES),',
     'schema=SCHEMA, rounds=COUNTS["test10"], repair_controller_sha256=repair_controller_sha256(), maps=list(maps), modes=list(MODES),', 1),
    ('unprofiled_primary_flights=30*len(maps)', 'unprofiled_primary_flights=3*COUNTS["test10"]*len(maps)', 1),
    ('planned_flights=33*len(maps)', 'planned_flights=3*(COUNTS["test10"]+1)*len(maps)', 1),
    ('primary OFF{30*len(maps)}', 'primary OFF{3*COUNTS["test10"]*len(maps)}', 1),
    ('scheduled_off_flights=30*len(maps)', 'scheduled_off_flights=3*COUNTS["test10"]*len(maps)', 1),
)


def build_namespace(rounds=10, *, install_root=None):
    if type(rounds) is not int or not 1 <= rounds <= 10:
        raise ValueError('--rounds must be an integer from 1 through 10')
    if sha(PREVIOUS) != PREVIOUS_SHA256:
        raise ValueError('Frozen v2 root controller changed')
    source = PREVIOUS.read_text()
    for old, new, count in REPLACEMENTS:
        if source.count(old) != count:
            raise ValueError('Required v2 controller adaptation changed: ' + old)
        source = source.replace(old, new)
    namespace = types.ModuleType('scenario7_repair_private_controller')
    namespace.__file__ = str(PREVIOUS)
    exec(compile(source, str(PREVIOUS), 'exec'), vars(namespace))
    namespace.COUNTS = dict(preflight=1, test10=rounds)
    namespace.CANDIDATE, namespace.SCHEMA, namespace.PROTOCOL = CANDIDATE, SCHEMA, PROTOCOL
    namespace.geometry = observer
    namespace.repair_controller_sha256 = lambda: sha(Path(__file__).resolve())
    namespace.__doc__ = __doc__
    binding = runtime.RuntimeBinding(install_root or os.environ.get(
        'SCENARIO7_REPAIR_INSTALL', str(runtime.DEFAULT_INSTALL)))
    namespace.base = runtime.clone_module(namespace.base)
    namespace.base.static = binding.namespace()['static_latched_preflight']
    if namespace.base.MEMORY_RUNAWAY_MIB != 4608:
        raise ValueError('Required 4608 MiB memory sentinel changed')
    original_plan = namespace.build_plan
    original_fingerprint = namespace._contact_input_fingerprint

    def contact_input_fingerprint(path, pcd, document):
        original = original_fingerprint(path, pcd, document)
        # The repair observer additionally validates the exact index source.
        # Preserve the old cache's complete pre/post snapshots and audit-first
        # tuple position while binding both recorded and executing index code.
        added = tuple(namespace._contact_file_fingerprint(item) for item in (
            Path(document['index_code_path']), Path(pcd_index.__file__), Path(__file__)))
        return original[0], original[1], original[2] + added

    def build_plan(root, maps=namespace.MAPS, base_run=60000):
        commands = original_plan(root, maps, base_run)
        for item in commands:
            command = item['command']
            if item['phase'] != 'static':
                command[1] = str(SCRIPTS / 'scenario7_cpu_compare_v3.py')
            elif item['name'].startswith('accept_'):
                command[:] = [command[0], str(SCRIPTS / 'scenario7_repair_runtime.py'), 'static', *command[3:]]
            else:
                action = 'rviz' if item['name'].startswith('rviz_') else 'transport'
                command[:] = [command[0], str(SCRIPTS / 'scenario7_repair_runtime.py'), action, *command[2:]]
        return commands

    namespace.build_plan = build_plan
    namespace._contact_input_fingerprint = contact_input_fingerprint
    namespace.freeze_sources = lambda root, admission: freeze_sources(root, admission, namespace, binding)
    namespace.repair_runtime = binding
    return namespace


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument('--rounds', type=int, default=None)
    parser.add_argument('--report', type=Path)
    args, remaining = parser.parse_known_args(argv)
    if args.report is not None:
        remaining += ['--report', str(args.report)]
        try:
            plan = json.loads((args.report / 'plan.json').read_text())
            rounds = plan['rounds']
            if plan.get('schema') != SCHEMA:
                raise ValueError('Not a repair campaign')
            if args.rounds is not None and args.rounds != rounds:
                raise ValueError('--report uses stored rounds; conflicting --rounds refused')
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(str(error))
    else:
        rounds = 10 if args.rounds is None else args.rounds
    try:
        namespace = build_namespace(rounds)
    except ValueError as error:
        parser.error(str(error))
    return namespace.main(remaining)


if __name__ == '__main__':
    raise SystemExit(main())
