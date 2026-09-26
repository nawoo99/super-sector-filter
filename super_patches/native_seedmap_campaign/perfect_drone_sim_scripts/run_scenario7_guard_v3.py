#!/usr/bin/env python3
"""Fresh C28 near-hit/async-generation cohort; preserved v2 is not resumed.

Pinned earlier controllers are reused only in private namespaces. New overlay,
source inventory, profiles and runtime markers require fresh matching ON
evidence. Existing timing/safety/resource gates and no-retry scheduling remain.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import run_scenario7_guard_v2 as previous
import scenario7_guard_v3_cpu_compare as child

SCRIPTS, REPO, SOURCE = previous.SCRIPTS, previous.REPO, previous.SOURCE
PREVIOUS_SHA256 = 'f49adcd823ecdd36b4a5c66ca7eb1846ccda4f82dd577074926591f1a5d18eb0'
PRIOR_ROOT = REPO / 'results/scenario7_guard_contract_smoke_20260926_v2b'
PRIOR_INVENTORY = PRIOR_ROOT / 'frozen_inputs_and_evidence.json'
PRIOR_INVENTORY_SHA256 = 'bf2fd286f18231f8761507d56ceed9cbf71b4bea689cd6baf7742571f3df98b1'
DEFAULT_INSTALL = child.DEFAULT_INSTALL
SCHEMA = 'scenario7-nearfield-async-manual-v3'
CANDIDATE = 'c28_observed_nearfield_async_generate'
PROTOCOL = REPO / 'docs/scenario7_guard_v3_20260926.md'
MODIFIED_CPP = previous.MODIFIED_CPP + (
    'rog_map/include/rog_map/rog_map_core/config.hpp',
    'super_planner/include/fsm/fsm.h',
    'super_planner/src/super_core/fsm.cpp',
)
ADDED_CPP = previous.ADDED_CPP + (
    'super_planner/include/fsm/async_from_rest_planning.hpp',
    'super_planner/test/async_from_rest_planning_test.cpp',
    'super_planner/test/stop_margin_prefix_supplement_test.cpp',
    'rog_map/test/near_range_wall_hole_test.cpp',
)
ADDED_TEST_SCRIPTS = previous.ADDED_TEST_SCRIPTS + (
    'super_planner/test/stop_margin_prefix_supplement_test.py',
    'super_planner/test/async_from_rest_source_contract_test.py',
)


def selected_install(value=None):
    return child.selected_install(value or os.environ.get(
        'SCENARIO7_GUARD_V3_INSTALL', str(DEFAULT_INSTALL)))


def private_previous():
    runtime = previous.previous.runtime
    if previous.previous.sha(previous.__file__) != PREVIOUS_SHA256:
        raise ValueError('Frozen guard-v2 controller changed')
    module = runtime.clone_module(previous)
    module.__file__ = str(Path(__file__).resolve())
    module.SCHEMA, module.CANDIDATE, module.PROTOCOL = SCHEMA, CANDIDATE, PROTOCOL
    module.PRIOR_ROOT, module.PRIOR_INVENTORY = PRIOR_ROOT, PRIOR_INVENTORY
    module.PRIOR_INVENTORY_SHA256 = PRIOR_INVENTORY_SHA256
    module.MODIFIED_CPP, module.ADDED_CPP = MODIFIED_CPP, ADDED_CPP
    module.ADDED_TEST_SCRIPTS = ADDED_TEST_SCRIPTS
    module.DEFAULT_INSTALL, module.selected_install = DEFAULT_INSTALL, selected_install
    original_private = module.private_previous

    def private_repair():
        repair = original_private()
        repair.REPLACEMENTS = tuple((old, new.replace(
            "'scenario7_guard_v2_'", "'scenario7_guard_v3_'").replace(
            'Not a scenario7 guard-v2 campaign', 'Not a scenario7 guard-v3 campaign').replace(
            '# Seven-map guard-contract-v2 results', '# Seven-map nearfield-async-v3 results'), count)
            for old, new, count in repair.REPLACEMENTS)
        return repair

    module.private_previous = private_repair
    return module


def build_namespace(rounds=10, *, install_root=None):
    install = selected_install(install_root)
    namespace = private_previous().build_namespace(rounds, install_root=install)
    original_plan, original_freeze, original_execute = (
        namespace.build_plan, namespace.freeze_sources, namespace.base.execute)

    def build_plan(root, maps=namespace.MAPS, base_run=80000):
        commands = original_plan(root, maps, base_run)
        for item in commands:
            if item['phase'] == 'static':
                continue
            command = item['command']
            command[1] = str(SCRIPTS / 'scenario7_guard_v3_cpu_compare.py')
            for mode, profile in child.PROFILES.items():
                flag = '--' + mode + '-config'
                if flag in command:
                    command[command.index(flag) + 1] = profile
                else:
                    command.extend((flag, profile))
            item.update(async_generate_trajectory=True, profiles=dict(child.PROFILES),
                        occupancy_only_min_range_m=0.1)
        return commands

    def freeze_sources(root, admission):
        profile_admissions = {name: child.profile_admission(child.PROFILES, name, install)
                              for name in namespace.MAPS}
        frozen, provenance = original_freeze(root, admission)
        files = [Path(__file__).resolve(), Path(child.__file__).resolve(),
                 SCRIPTS / 'run_scenario7_guard_v3.sh',
                 REPO / 'scripts/native_campaign/run_scenario7_guard_v3.sh',
                 SCRIPTS.parent / 'test/test_run_scenario7_guard_v3.py',
                 REPO / 'super_patches/native_seedmap_campaign/perfect_drone_sim_test/test_run_scenario7_guard_v3.py']
        files.extend(REPO / 'super_patches/native_seedmap_campaign/perfect_drone_sim_scripts' / name
                     for name in ('run_scenario7_guard_v3.py', 'run_scenario7_guard_v3.sh',
                                  'scenario7_guard_v3_cpu_compare.py'))
        for value in profile_admissions.values():
            files.extend(Path(path) for path in value['assets_sha256'])
        namespace.base.freeze_files(frozen, files)
        provenance.update(schema='scenario7-nearfield-async-admission-v3', candidate=CANDIDATE,
            control_revision=3, stop_contract_revision=2,
            previous_v2_controller_sha256=PREVIOUS_SHA256,
            previous_v2_install=str(previous.DEFAULT_INSTALL), previous_v2_install_preserved=True,
            selected_install=str(install), nearfield_profiles=profile_admissions,
            async_generate_trajectory=True, new_profiled_preflight_required=True,
            old_profile_references_not_reused=True)
        return frozen, provenance

    def execute(item, root, base_env):
        environment = dict(base_env, SCENARIO7_REPAIR_INSTALL=str(install), SUPER_ASYNC_GENERATE_TRAJ='1')
        return original_execute(item, root, environment)

    namespace.build_plan, namespace.freeze_sources, namespace.base.execute = build_plan, freeze_sources, execute
    namespace.__doc__ = __doc__
    namespace.guard_v3_install = install
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
                raise ValueError('Not a nearfield-async-v3 campaign')
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
