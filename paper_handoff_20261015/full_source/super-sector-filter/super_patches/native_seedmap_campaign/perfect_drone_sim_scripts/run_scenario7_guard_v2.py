#!/usr/bin/env python3
"""Separate C27 guard-contract cohort; never amend or resume repair-v1.

Reuse the pinned v1 controller through an isolated module namespace. Changes
are limited to exact source admission, cohort identity and the distinct v2
install prefix. Existing timing/safety/resource gates and no-retry scheduling
remain unchanged. Execution requires a fresh output and a completed v2 build.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import run_scenario7_repair as previous

SCRIPTS = Path(__file__).resolve().parent
REPO = previous.REPO
SOURCE = previous.SOURCE
PREVIOUS_SHA256 = 'abb78685974499fbea2c7593e1884e9c88b9f77aee2622698a56a1dd030f1202'
PRIOR_ROOT = REPO / 'results/scenario7_repair_smoke_20260926_v1'
PRIOR_INVENTORY = PRIOR_ROOT / 'frozen_inputs_and_evidence.json'
PRIOR_INVENTORY_SHA256 = '49a2543a8b51f35266b25315470f267a87218aa5640ad4e5db16251b4d6b3e6d'
DEFAULT_INSTALL = Path('/root/super_ws/scenario7_guard_v2_20260926/install')
SCHEMA = 'scenario7-guard-contract-manual-v2'
CANDIDATE = 'c27_guard_contract_v2'
PROTOCOL = REPO / 'docs/scenario7_guard_v2_20260926.md'
MODIFIED_CPP = previous.MODIFIED_CPP + (
    'rog_map/src/rog_map/prob_map.cpp',
    'super_planner/include/ros_interface/ros2/fsm_ros2.hpp',
)
ADDED_CPP = previous.ADDED_CPP + (
    'super_planner/include/fsm/stop_margin_certificate.hpp',
    'super_planner/test/stop_margin_certificate_test.cpp',
    'super_planner/test/stop_margin_demand_policy_test.cpp',
    'super_planner/test/stop_margin_validator_integration_test.cpp',
    'rog_map/test/occupancy_hit_multiplicity_test.cpp',
)
ADDED_TEST_SCRIPTS = ('super_planner/test/stop_margin_validator_integration_test.py',)


def selected_install(value=None):
    selected = Path(value or os.environ.get('SCENARIO7_GUARD_V2_INSTALL', str(DEFAULT_INSTALL)))
    binding = previous.runtime.RuntimeBinding(selected)
    if binding.install.is_relative_to(previous.runtime.DEFAULT_INSTALL.resolve()):
        raise ValueError('Guard-v2 requires a separate build; repair-v1 install is immutable')
    return binding.install


def private_previous():
    if previous.sha(previous.__file__) != PREVIOUS_SHA256:
        raise ValueError('Frozen repair-v1 controller changed')
    module = previous.runtime.clone_module(previous)
    module.__file__ = str(Path(__file__).resolve())
    module.SCHEMA, module.CANDIDATE, module.PROTOCOL = SCHEMA, CANDIDATE, PROTOCOL
    module.PRIOR_ROOT, module.PRIOR_INVENTORY = PRIOR_ROOT, PRIOR_INVENTORY
    module.PRIOR_INVENTORY_SHA256 = PRIOR_INVENTORY_SHA256
    module.MODIFIED_CPP, module.ADDED_CPP = MODIFIED_CPP, ADDED_CPP
    # This changes only default folder/error/report labels in the already
    # checked inherited source adaptation, not control flow or any gate.
    module.REPLACEMENTS = tuple((old, new.replace(
        "'scenario7_repair_'", "'scenario7_guard_v2_'").replace(
        'Not a scenario7 repair campaign', 'Not a scenario7 guard-v2 campaign').replace(
        '# Seven-map repair results', '# Seven-map guard-contract-v2 results'), count)
        for old, new, count in previous.REPLACEMENTS)
    return module


def build_namespace(rounds=10, *, install_root=None):
    install = selected_install(install_root)
    adapted = private_previous()
    namespace = adapted.build_namespace(rounds, install_root=install)
    original_freeze = namespace.freeze_sources
    original_execute = namespace.base.execute
    original_plan = namespace.build_plan

    def freeze_sources(root, admission):
        added_test_paths = []
        for relative in ADDED_TEST_SCRIPTS:
            source, mirrored = SOURCE / relative, adapted.mirror_path(relative)
            if not source.is_file() or not mirrored.is_file() or previous.sha(source) != previous.sha(mirrored):
                raise ValueError('Guard-v2 runtime/mirror mismatch: ' + relative)
            added_test_paths.extend((source, mirrored))
        frozen, provenance = original_freeze(root, admission)
        scripts = (Path(__file__).resolve(), SCRIPTS / 'run_scenario7_guard_v2.sh',
                   SCRIPTS / 'scenario7_guard_v2_cpu_compare.py',
                   Path(previous.__file__).resolve(),
                   REPO / 'scripts/native_campaign/run_scenario7_guard_v2.sh',
                   REPO / 'super_patches/native_seedmap_campaign/perfect_drone_sim_scripts/run_scenario7_guard_v2.py',
                   REPO / 'super_patches/native_seedmap_campaign/perfect_drone_sim_scripts/run_scenario7_guard_v2.sh',
                   REPO / 'super_patches/native_seedmap_campaign/perfect_drone_sim_scripts/scenario7_guard_v2_cpu_compare.py',
                   SCRIPTS.parent / 'test/test_run_scenario7_guard_v2.py',
                   REPO / 'super_patches/native_seedmap_campaign/perfect_drone_sim_test/test_run_scenario7_guard_v2.py')
        namespace.base.freeze_files(frozen, (*scripts, *added_test_paths))
        provenance.update(schema='scenario7-guard-contract-admission-v2',
            contract_revision=2, candidate=CANDIDATE, previous_controller_sha256=PREVIOUS_SHA256,
            previous_repair_install=str(previous.runtime.DEFAULT_INSTALL),
            selected_install=str(install), previous_repair_install_preserved=True,
            added_test_script_paths=[str(path) for path in added_test_paths],
            new_profiled_preflight_required=True, old_profile_references_not_reused=True,
            primary_cohort_distinct_from_diagnostics=True)
        return frozen, provenance

    def execute(item, root, base_env):
        # Preserve the original controller-owned process/memory sentinel while
        # preventing an inherited v1 environment from choosing stale binaries.
        environment = dict(base_env, SCENARIO7_REPAIR_INSTALL=str(install))
        return original_execute(item, root, environment)

    def build_plan(root, maps=namespace.MAPS, base_run=70000):
        commands = original_plan(root, maps, base_run)
        for item in commands:
            if item['phase'] != 'static':
                item['command'][1] = str(SCRIPTS / 'scenario7_guard_v2_cpu_compare.py')
        return commands

    namespace.freeze_sources = freeze_sources
    namespace.base.execute = execute
    namespace.build_plan = build_plan
    namespace.__doc__ = __doc__
    namespace.guard_contract_revision = 2
    namespace.guard_v2_install = install
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
                raise ValueError('Not a guard-contract-v2 campaign')
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
