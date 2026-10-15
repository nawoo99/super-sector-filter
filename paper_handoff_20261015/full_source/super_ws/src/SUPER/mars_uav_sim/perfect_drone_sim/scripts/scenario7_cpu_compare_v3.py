#!/usr/bin/env python3
"""Separate repair-cohort child: overlay runtime and retained preflight failures.

The v2 adapter and all inherited gate expressions remain frozen. Checked
substitutions add structured blocked-reference outcomes and a narrowly scoped
best-effort ON-mode observation path. Timing failures never admit OFF flights.
"""
from __future__ import annotations

import os
from pathlib import Path

import scenario7_cpu_compare as previous
import scenario7_preflight_control as control
import scenario7_repair_runtime as runtime

PREVIOUS_SHA256 = '347fab0809b2a62276dcd6ac5e01c2b764bdee807c59004293448a1d59890212'
REPAIR_MONITOR = previous.support.PACKAGE / 'scripts/scenario7_repair_loop_monitor.py'
REPAIR_INDEX = previous.support.PACKAGE / 'scripts/scenario7_repair_pcd_index.py'


def revision_identity():
    paths = (Path(__file__).resolve(), Path(control.__file__).resolve(),
             Path(runtime.__file__).resolve(), Path(previous.__file__).resolve())
    return dict(schema='scenario7-child-control-repair-v1', previous_adapter_sha256=PREVIOUS_SHA256,
                source_sha256={str(path): previous.support.sha256(path) for path in paths},
                timing_thresholds_unchanged=True, no_automatic_retry=True,
                continuation='ON received-odometry-only failure after safe teardown',
                not_pooled_with_previous_results=True)


REPLACEMENTS = (
    ('    profile_reference_plan = None',
     "    if args.small_pool_profile_reference:\n"
     "        reference_presence = control.inspect_profile_reference(args.small_pool_profile_reference, args.modes)\n"
     "        if not reference_presence['valid']:\n"
     "            return control.blocked_reference(args, reference_presence['errors'], diagnostic.save)\n"
     '    profile_reference_plan = None'),
    ("            value = json.loads(path.read_text())",
     "            value = reference_presence['documents'][name]"),
    ('    hashes = {str(p): event.sha(p) for p in sorted(files)}',
     "    files = {repair_runtime.select_path(path) for path in files}\n"
     "    files.update(repair_runtime.asset_paths())\n"
     "    files.update(Path(path) for path in revision_identity()['source_sha256'])\n"
     '    hashes = {str(p): event.sha(p) for p in sorted(files)}'),
    ('    plan = dict(\n',
     '    plan = dict(\n'
     '        scenario7_control_revision=revision_identity(),\n'
     '        scenario7_repair_runtime=repair_runtime.identity(),\n'),
    ("        raise RuntimeError('Small-pool profiled preflight mismatch or failed gates: ' +\n"
     "                           json.dumps(profile_reference_audit['checks']))",
     "        return control.blocked_reference(args, [dict(reason='profile_reference_failed_gates',\n"
     "            failed_checks=control.failed_checks(profile_reference_audit['acceptance_checks']),\n"
     "            audit=profile_reference_audit)], diagnostic.save, output_exists=True)"),
    ('    results = []\n', '    results = []\n    retained_mode_failures = []\n'),
    ("    profiler = diagnostic.Profiler(root / 'telemetry.jsonl', map_name=args.map)\n", ''),
    ('    campaign.install_campaign_signal_handlers()',
     "    profiler = diagnostic.Profiler(root / 'telemetry.jsonl', map_name=args.map)\n"
     '    campaign.install_campaign_signal_handlers()'),
    ("                if not all(result['source_acquisition']['checks'].values()):\n"
     "                    raise RuntimeError('Source/recovery contract failure; stop for diagnosis')",
     "                if not all(result['source_acquisition']['checks'].values()):\n"
     "                    retained_mode_failures.append(control.retain_mode_failure(\n"
     "                        result, profile_cpu=args.profile_cpu, campaign=campaign,\n"
     "                        process_iter=psutil.process_iter, flight_names=FLIGHT_NAMES))\n"
     "                    diagnostic.save(root / 'retained_mode_failures.json', retained_mode_failures)"),
    ("        diagnostic.save(root / 'status.json', dict(pid=os.getpid(), state='COMPLETE',\n"
     "            candidate=args.candidate, completed=len(results), comparison=comp))",
     "        diagnostic.save(root / 'status.json', control.final_status(\n"
     "            args, results, retained_mode_failures, comp))"),
    ("        print('COMPARISON', json.dumps(comp), flush=True)",
     "        print('COMPARISON', json.dumps(comp), flush=True)\n"
     "        return 2 if retained_mode_failures else 0"),
)


def adapted_main_source():
    if previous.support.sha256(previous.__file__) != PREVIOUS_SHA256:
        raise ValueError('Frozen scenario7 v2 adapter changed')
    source = previous.adapted_main_source()
    for old, new in REPLACEMENTS:
        if source.count(old) != 1:
            raise ValueError('Repair adaptation cardinality changed: ' + old)
        source = source.replace(old, new, 1)
    return source


def build_main(*, install_root=None, source_transform=None, namespace_updates=None):
    """Build isolated code; explicit revision wrappers can extend its inventory.

    Merely constructing the child (including --help) does not require a build or
    start a profiler. The exact overlay is validated before any flight starts.
    """
    binding = runtime.RuntimeBinding(install_root or os.environ.get(
        'SCENARIO7_REPAIR_INSTALL', str(runtime.DEFAULT_INSTALL)))
    namespace = dict(previous.build_main().__globals__)
    namespace.update(binding.namespace())
    namespace.update(__file__=str(Path(__file__).resolve()), __name__=__name__, __doc__=__doc__,
                     control=control, revision_identity=revision_identity,
                     MONITOR=REPAIR_MONITOR,
                     OBSERVER_DEPENDENCIES=(*previous.OBSERVER_DEPENDENCIES, REPAIR_INDEX),
                     small_pool_profile_reference_audit=binding.profile_reference_audit)
    if namespace_updates:
        namespace.update(namespace_updates)
    source = adapted_main_source()
    if source_transform is not None:
        source = source_transform(source)
    exec(compile(source, str(Path(__file__).resolve()), 'exec'), namespace)
    return namespace['main']


def main():
    return build_main()()


if __name__ == '__main__':
    raise SystemExit(main())
