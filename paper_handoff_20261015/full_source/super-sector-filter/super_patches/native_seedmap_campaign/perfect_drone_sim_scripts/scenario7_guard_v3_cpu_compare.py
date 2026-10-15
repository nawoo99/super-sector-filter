#!/usr/bin/env python3
"""Separate near-hit/async-generation child; frozen v2 checks remain active."""
from __future__ import annotations

import os
import math
from pathlib import Path
import re

import yaml
import scenario7_guard_v2_cpu_compare as previous

PREVIOUS_SHA256 = 'a045b9aa00bfcd2f882a6e77312deb0b35978d15c44ac867f14cde61bca4fa81'
runtime = previous.previous.runtime
SOURCE = Path('/root/super_ws/src/SUPER')
MIRROR = Path('/root/super-sector-filter/super_patches/native_seedmap_campaign')
DEFAULT_INSTALL = Path('/root/super_ws/scenario7_guard_v3_20260926/install')
BASE_PROFILES = {
    'full': 'static_seedmaps_guard_viability_tight_v7.yaml',
    'sector': 'static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml',
    'adaptive': 'static_seedmaps_guard_viability_tight_v7_event_recovery_v1.yaml',
}
PROFILES = {mode: name.removesuffix('.yaml') + '_nearhit_v3.yaml'
            for mode, name in BASE_PROFILES.items()}


def selected_install(value=None):
    install = runtime.RuntimeBinding(value or os.environ.get(
        'SCENARIO7_REPAIR_INSTALL', str(DEFAULT_INSTALL))).install
    for preserved in (runtime.DEFAULT_INSTALL, previous.DEFAULT_INSTALL):
        if install.is_relative_to(preserved.resolve()):
            raise ValueError('Guard-v3 refuses a preserved v1/v2 installation')
    return install


def validate_profile_pair(original, candidate):
    """Admit only the documented near-hit and bounded escape additions."""
    additions = (
        (r'^    occupancy_only_min_range: 0\.1(?:[ \t]+#[^\r\n]*)?\r?\n',
         'Near-hit profile requires exactly one explicit 0.1 m key'),
        (r'^    local_escape_max_distance_m: 1\.20(?:[ \t]+#[^\r\n]*)?\r?\n',
         'Near-hit profile requires exactly one 1.20 m escape maximum'),
        (r'^    local_escape_distance_steps: 2(?:[ \t]+#[^\r\n]*)?\r?\n',
         'Near-hit profile requires exactly two bounded escape distances'),
    )
    stripped = candidate
    for pattern, error in additions:
        stripped, count = re.subn(pattern, '', stripped, count=1, flags=re.M)
        if count != 1 or re.search(pattern, stripped, re.M):
            raise ValueError(error)
    if stripped != original:
        raise ValueError(
            'Near-hit profile changed an input beyond the admitted additions')
    before, after = yaml.safe_load(original), yaml.safe_load(candidate)
    ray = after['rog_map']['raycasting']
    reroute = after['super_planner']['guard_topology_reroute']
    if ray.pop('occupancy_only_min_range', None) != 0.1:
        raise ValueError('Near-hit key must be nested under rog_map/raycasting')
    if reroute.pop('local_escape_max_distance_m', None) != 1.2 or \
       reroute.pop('local_escape_distance_steps', None) != 2:
        raise ValueError(
            'Bounded escape additions must be nested under guard_topology_reroute')
    if before != after:
        raise ValueError('Profile semantic diff exceeds admitted additions')
    if ray.get('enable') is not False or ray.get('ray_range', [None])[0] != 0.5:
        raise ValueError('Legacy occupancy-only mode and 0.5 m ray range must stay unchanged')
    return True


def profile_admission(profiles, map_name, install_root, *, source=SOURCE, mirror=MIRROR):
    if profiles != PROFILES:
        raise ValueError('Guard-v3 requires the exact three near-hit profiles')
    sha = previous.previous.previous.support.sha256
    hashes, rows = {}, {}
    for mode, name in profiles.items():
        original = source / 'super_planner/config' / BASE_PROFILES[mode]
        candidate = source / 'super_planner/config' / name
        validate_profile_pair(original.read_text(), candidate.read_text())
        copies = (candidate, mirror / 'super_planner_config' / name,
                  Path(install_root) / 'super_planner/share/super_planner/config' / name)
        digest = sha(candidate)
        if any(not path.is_file() or sha(path) != digest for path in copies):
            raise ValueError('Near-hit runtime/mirror/install profile mismatch: ' + name)
        hashes.update({str(path): sha(path) for path in (original, *copies)})
        rows[mode] = dict(profile=name, original_profile=original.name,
                          profile_sha256=digest, original_sha256=sha(original))
    sensor = source / f'mars_uav_sim/perfect_drone_sim/config/{map_name}.yaml'
    if yaml.safe_load(sensor.read_text()).get('sensing_blind') != 0.1:
        raise ValueError('Near-hit minimum must match this map sensor blind range of 0.1 m')
    hashes[str(sensor)] = sha(sensor)
    return dict(schema='scenario7-nearfield-async-inputs-v3', async_generate_trajectory=True,
                occupancy_only_min_range_m=0.1, legacy_ray_range_min_m=0.5,
                local_escape_distance_range_m=[0.6, 1.2],
                local_escape_distance_steps=2,
                sensor_blind_m=0.1, profiles=rows, assets_sha256=hashes)


def runtime_audit(stack):
    clean = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', stack)
    records = re.findall(r'\[ASYNC_GENERATE_TRAJ\][^\r\n]*', clean)
    # Exact marker fields are intentionally required; absent/old/duplicate
    # startup identity may not silently qualify a new-cohort run.
    async_fields = dict(enabled='true', executor='existing_replan', main_finalization='true', default_off='true')
    async_valid = len(records) == 1 and all(
        re.findall(r'\b' + key + r'=([^\s]+)', records[0]) == [value]
        for key, value in async_fields.items())
    near_records = re.findall(r'\[OCCUPANCY_ONLY_RANGE\][^\r\n]*', clean)
    near_valid = len(near_records) == 1
    if near_valid:
        for key, expected in dict(enabled=1.0, hit_min=0.1, free_ray_min=0.5, startup_clear_radius=0.5).items():
            values = re.findall(r'\b' + key + r'=([^\s]+)', near_records[0])
            try:
                value = float(values[0]) if len(values) == 1 else math.nan
                near_valid = near_valid and math.isfinite(value) and value == expected
            except ValueError:
                near_valid = False
    escape_param_records = {}
    escape_param_valid = True
    for name, expected in {
        'super_planner/guard_topology_reroute/local_escape_max_distance_m': 1.2,
        'super_planner/guard_topology_reroute/local_escape_distance_steps': 2.0,
    }.items():
        values = re.findall(
            r'Load param ' + re.escape(name) + r' success:\s*([^\s]+)', clean)
        escape_param_records[name] = values
        try:
            value = float(values[0]) if len(values) == 1 else math.nan
            escape_param_valid = (escape_param_valid and
                                  math.isfinite(value) and value == expected)
        except ValueError:
            escape_param_valid = False
    return dict(valid=async_valid and near_valid and escape_param_valid,
                async_records=records, near_range_records=near_records,
                escape_param_records=escape_param_records, checks=dict(
                    async_generate_enabled_once=async_valid,
                    near_range_loaded_0_1=near_valid,
                    bounded_escape_parameters_loaded=escape_param_valid))


def adapt_main(source):
    replacements = (
        ("default=diagnostic.search.PROFILES['full']", "default=V3_PROFILES['full']"),
        ("default=diagnostic.search.PROFILES['sector']", "default=V3_PROFILES['sector']"),
        ('default=event.PROFILE', "default=V3_PROFILES['adaptive']"),
        ('    args = parser.parse_args()',
         "    args = parser.parse_args()\n"
         "    v3_admission = profile_admission(dict(full=args.full_config, sector=args.sector_config,\n"
         "        adaptive=args.adaptive_config), args.map, repair_runtime.install)"),
        ("    os.environ['SUPER_CPU_PROFILE'] =", "    os.environ['SUPER_ASYNC_GENERATE_TRAJ'] = '1'\n"
         "    os.environ['SUPER_CPU_PROFILE'] ="),
        ('    hashes = {str(p): event.sha(p) for p in sorted(files)}',
         '    files.update(Path(path) for path in v3_admission[\'assets_sha256\'])\n'
         '    files.update((V2_CHILD_SOURCE, V3_CHILD_SOURCE))\n'
         '    hashes = {str(p): event.sha(p) for p in sorted(files)}'),
        ('    plan = dict(\n', '    plan = dict(\n        nearfield_async_revision=v3_admission,\n'),
        ("                result['event_body_heading'] = args.event_body_heading",
         "                result['nearfield_async_audit'] = runtime_audit(stack)\n"
         "                result['source_acquisition']['checks']['nearfield_async_revision_3'] = result['nearfield_async_audit']['valid']\n"
         "                result['event_body_heading'] = args.event_body_heading"),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise ValueError('Guard-v3 child adaptation cardinality changed: ' + old)
        source = source.replace(old, new, 1)
    return source


def build_main(*, install_root=None):
    sha = previous.previous.previous.support.sha256
    if sha(previous.__file__) != PREVIOUS_SHA256:
        raise ValueError('Frozen guard-v2 child changed')
    install = selected_install(install_root)
    v2 = runtime.clone_module(previous)
    repair = runtime.clone_module(previous.previous)
    repair_build = repair.build_main

    def extended_build(**kwargs):
        updates = dict(kwargs.pop('namespace_updates', {}), profile_admission=profile_admission,
                       runtime_audit=runtime_audit, V2_CHILD_SOURCE=Path(previous.__file__).resolve(),
                       V3_CHILD_SOURCE=Path(__file__).resolve(), V3_PROFILES=PROFILES, __doc__=__doc__)
        return repair_build(namespace_updates=updates, **kwargs)

    repair.build_main = extended_build
    v2.previous = repair
    v2.__file__ = str(Path(__file__).resolve())
    v2.adapt_main = lambda source: adapt_main(previous.adapt_main(source))
    main = v2.build_main(install_root=install)
    inherited_reference = main.__globals__['small_pool_profile_reference_audit']

    def reference_audit(plan, reference_plan, summaries):
        audit = inherited_reference(plan, reference_plan, summaries)
        identity = plan.get('nearfield_async_revision')
        valid = (isinstance(identity, dict) and identity.get('schema') == 'scenario7-nearfield-async-inputs-v3'
                 and identity.get('async_generate_trajectory') is True
                 and identity.get('occupancy_only_min_range_m') == 0.1
                 and identity == reference_plan.get('nearfield_async_revision'))
        valid = valid and all(summaries.get(mode, {}).get('nearfield_async_audit', {}).get('valid') is True
                              for mode in plan.get('modes', []))
        audit['checks']['nearfield_async_revision_3_match'] = valid
        audit['acceptance_checks']['nearfield_async_revision_3_match'] = valid
        audit['valid'] = audit['valid'] and valid
        return audit

    main.__globals__['small_pool_profile_reference_audit'] = reference_audit
    return main


def main():
    return build_main()()


if __name__ == '__main__':
    raise SystemExit(main())
