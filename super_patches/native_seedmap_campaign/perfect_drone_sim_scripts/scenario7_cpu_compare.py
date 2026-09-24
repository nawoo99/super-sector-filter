#!/usr/bin/env python3
"""Seven-map child adapter preserving the hash-pinned gapfree/C24 flight gates.

Only the inherited main function is compiled into an isolated namespace. The
checked substitutions below change map metadata and independent solid-audit
bindings; parser options, runtime policy and measurement gates are inherited.
No legacy module or file is patched in place.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import shutil

import scenario7_campaign_support as support

support.verify_baselines()
import gapfree_cpu_compare as inherited

MONITOR = support.PACKAGE / 'scripts/scenario7_native_loop_monitor.py'
OBSERVER_DEPENDENCIES = (support.PACKAGE / 'scripts/scenario7_geometry.py', support.GAPFREE_MONITOR)
MAP_MATCH_FIELDS = ('scenario7_manifest_sha256', 'scenario7_geometry',
                    'scenario7_adapter_baseline_sha256', 'scenario7_gapfree_adapter_sha256',
                    'scenario7_solid_geometry_sha256', 'scenario7_observer_sha256')
SUPPLEMENTAL_SUFFIXES = ('solid_audit.json', 'odometry.csv')

# Exact cardinalities prevent a source change from silently adapting new code.
MAIN_REPLACEMENTS = (
    ("prefix='gapfree_n5_'", "prefix='scenario7_n10_'", 1),
    ("os.environ['GAPFREE_BASE_MONITOR']", "os.environ['SCENARIO7_BASE_MONITOR']", 1),
    ('gapfree_manifest_sha256=', 'scenario7_manifest_sha256=', 1),
    ('gapfree_geometry=', 'scenario7_geometry=', 1),
    ('gapfree_adapter_baseline_sha256=', 'scenario7_adapter_baseline_sha256=', 1),
    ('    files.update({MANIFEST, LEGACY_CHILD, Path(support.__file__).resolve(), MONITOR})',
     '    files.update({MANIFEST, LEGACY_CHILD, Path(support.__file__).resolve(), MONITOR})\n'
     '    files.update(OBSERVER_DEPENDENCIES)', 1),
    ("        schema='adaptive-cpu40-seed1-exploratory-v1', candidate=args.candidate,",
     "        scenario7_gapfree_adapter_sha256=support.GAPFREE_ADAPTER_SHA256,\n"
     "        scenario7_solid_geometry_sha256=map_admission['maps'][args.map]['solid_geometry_sha256'],\n"
     "        scenario7_observer_sha256=support.sha256(MONITOR),\n"
     "        schema='adaptive-cpu40-seed1-exploratory-v1', candidate=args.candidate,", 1),
    ('gapfree observer recorded', 'scenario7 solid observer recorded', 1),
    ('solid_cylinder_audit', 'solid_obstacle_audit', 4),
    ('solid_cylinder_observation_valid', 'solid_obstacle_observation_valid', 1),
)


def small_pool_profile_reference_audit(plan, reference_plan, summaries):
    audit = inherited.legacy.small_pool_profile_reference_audit(plan, reference_plan, summaries)
    match = all(key in plan and key in reference_plan and plan[key] == reference_plan[key]
                for key in MAP_MATCH_FIELDS)
    added = dict(scenario7_frozen_map_match=match)
    for mode in plan.get('modes', []):
        solid = summaries.get(mode, {}).get('solid_obstacle_audit', {})
        if not isinstance(solid, dict):
            solid = {}
        count = solid.get('contact_episodes')
        samples = solid.get('samples')
        valid = (solid.get('schema') == 'scenario-solid-audit-v1'
                 and solid.get('schema_version') == 1
                 and solid.get('audit_valid') is True and solid.get('completion') is True
                 and solid.get('map') == plan.get('map')
                 and solid.get('geometry_sha256') == plan.get('scenario7_solid_geometry_sha256')
                 and solid.get('observer_code_sha256') == plan.get('scenario7_observer_sha256')
                 and solid.get('robot_radius_m') == 0.2
                 and solid.get('observation') == 'received_odometry_samples_only'
                 and solid.get('swept_collision_check') is False
                 and type(count) is int and count >= 0
                 and type(samples) is int and samples > 1
                 and all(type(solid.get(key)) is int and solid[key] == 0 for key in
                         ('invalid_samples', 'timestamp_nonmonotonic_count', 'receipt_nonmonotonic_count')))
        added[mode + '_solid_observation_valid'] = valid
        if mode in ('full', 'adaptive'):
            added[mode + '_solid_zero_contact'] = valid and count == 0
    audit['checks'].update(added)
    audit['acceptance_checks'].update(added)
    audit['valid'] = audit['valid'] and all(added.values())
    return audit


def copy_supplemental_artifacts(root, map_name, run, mode, campaign):
    stem = f'{map_name}_run{run}_{mode}.attempt1'
    dest = Path(root) / 'artifacts'
    dest.mkdir(parents=True, exist_ok=True)
    sources = [Path(campaign.TMPDIR) / f'{stem}.{suffix}' for suffix in (*SUPPLEMENTAL_SUFFIXES, 'json')]
    # Resolve every required artifact before copying any of them.
    for origin in sources:
        if not origin.is_file():
            raise FileNotFoundError('Missing supplemental evidence: ' + str(origin))
        target = dest / origin.name
        # A failed legacy attempt may already preserve its native JSON. Its
        # bytes must agree; a fresh successful run usually only has tag.json.
        already_native = origin.name == stem + '.json' and target.is_file()
        if target.exists() and not (already_native and support.sha256(target) == support.sha256(origin)):
            raise RuntimeError('Supplemental evidence overwrite refused: ' + str(dest / origin.name))
    for origin in sources:
        if not (dest / origin.name).exists():
            shutil.copy2(origin, dest / origin.name)
    result = json.loads((dest / f'{stem}.solid_audit.json').read_text())
    result['artifact_path'] = str(dest / f'{stem}.solid_audit.json')
    return result


def preserve_supplemental_artifacts(root, campaign):
    dest = Path(root) / 'artifacts'
    dest.mkdir(parents=True, exist_ok=True)
    records = []
    origins = set()
    for suffix in SUPPLEMENTAL_SUFFIXES:
        for origin in Path(campaign.TMPDIR).glob('*.' + suffix):
            origins.add(origin)
            native = origin.with_name(origin.name.removesuffix('.' + suffix) + '.json')
            if native.is_file():
                origins.add(native)
    for origin in sorted(origins):
        target = dest / origin.name
        try:
            if target.exists():
                if support.sha256(target) != support.sha256(origin):
                    raise RuntimeError('Existing supplemental evidence differs; overwrite refused')
                state = 'ALREADY_PRESERVED'
            else:
                shutil.copy2(origin, target)
                state = 'COPIED'
            records.append(dict(source=str(origin), target=str(target), state=state))
        except Exception as error:
            records.append(dict(source=str(origin), target=str(target),
                                state='PRESERVED_IN_SCRATCH', error=repr(error)))
    inherited.diagnostic.save(Path(root) / 'supplemental_preservation.json', dict(
        scratch_directory=campaign.TMPDIR, scratch_retained=True, files=records))


def adapted_main_source():
    support.verify_baselines()
    tree = ast.parse(support.GAPFREE_ADAPTER.read_text())
    definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main']
    if len(definitions) != 1:
        raise ValueError('Expected one inherited main function')
    source = ast.get_source_segment(support.GAPFREE_ADAPTER.read_text(), definitions[0])
    for old, new, count in MAIN_REPLACEMENTS:
        if source.count(old) != count:
            raise ValueError('Inherited main adaptation cardinality mismatch: ' + old)
        source = source.replace(old, new)
    return source


def build_main():
    namespace = dict(vars(inherited))
    namespace.update(__file__=str(Path(__file__).resolve()), __name__=__name__, __doc__=__doc__,
                     support=support, MANIFEST=support.MANIFEST, MAPS=support.MAPS7,
                     LEGACY_DIR=support.LEGACY_DIR, LEGACY_CHILD=support.LEGACY_CHILD,
                     PACKAGE=support.PACKAGE, MONITOR=MONITOR, register_maps=support.register_maps,
                     OBSERVER_DEPENDENCIES=OBSERVER_DEPENDENCIES,
                     small_pool_profile_reference_audit=small_pool_profile_reference_audit,
                     copy_supplemental_artifacts=copy_supplemental_artifacts,
                     preserve_supplemental_artifacts=preserve_supplemental_artifacts)
    exec(compile(adapted_main_source(), str(Path(__file__).resolve()), 'exec'), namespace)
    return namespace['main']


def main():
    return build_main()()


if __name__ == '__main__':
    main()
