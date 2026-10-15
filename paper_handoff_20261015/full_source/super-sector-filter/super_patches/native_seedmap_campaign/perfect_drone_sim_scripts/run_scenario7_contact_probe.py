#!/usr/bin/env python3
"""One opt-in Adaptive contact probe of the frozen repair-v1 runtime.

Diagnostic only: never primary CPU/safety evidence or a profile reference.
No algorithm/logging-equivalence claim, automatic retry, or v1 file mutation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile

import scenario7_cpu_compare_v3 as child
import run_scenario7_repair as controller

SCHEMA = 'scenario7-contact-probe-v1'
V1_ROOT = Path('/root/super-sector-filter/results/scenario7_repair_smoke_20260926_v1')
V1_INVENTORY = V1_ROOT / 'frozen_inputs_and_evidence.json'
V1_INVENTORY_SHA256 = '49a2543a8b51f35266b25315470f267a87218aa5640ad4e5db16251b4d6b3e6d'
CHILD_SHA256 = '77cfe33404834a3f812791c0beb0eaa576f0faf98ba7ec36e600c12cb0646353'
ROIS = {
    'gapfree_d1_m01': dict(name='cylinder_0068', center_x=-28.591183, center_y=-4.598807),
    # The fixed +-2 m hook window must cover the observed entry wall, not
    # the building center (19,7), which excludes the x=22 contact surface.
    'urban_blocks_u01': dict(name='building_12_entry_wall', center_x=22., center_y=9.5),
}
FILE_CAP = 256 * 1024 * 1024
REQUIRED_KINDS = {'sensor_render_cloud', 'map_input_cloud', 'map_snapshot_commit',
                  'trajectory_validation_start', 'trajectory_validation_result',
                  'trajectory_physical_body_query', 'published_position_command'}


def sha(path):
    return controller.sha(path)


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def changed_inputs(hashes):
    return [name for name, expected in hashes.items()
            if not Path(name).is_file() or sha(name) != expected]


def frozen_v1_inputs():
    if sha(V1_INVENTORY) != V1_INVENTORY_SHA256:
        raise ValueError('Frozen repair-v1 inventory changed')
    hashes = json.loads(V1_INVENTORY.read_text())
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError('Missing repair-v1 asset inventory')
    changed = changed_inputs(hashes)
    if changed:
        raise ValueError('Repair-v1 assets changed; this probe cannot launch a later revision: ' + repr(changed))
    if sha(child.__file__) != CHILD_SHA256:
        raise ValueError('Frozen repair-v1 child changed')
    hashes[str(V1_INVENTORY)] = V1_INVENTORY_SHA256
    hashes[str(Path(__file__).resolve())] = sha(__file__)
    return hashes


def replace_option(command, option, values):
    index = command.index(option)
    end = index + 1
    while end < len(command) and not command[end].startswith('--'):
        end += 1
    command[index + 1:end] = list(values)


def flight_arguments(root, map_name, run_id, static_preflight):
    child.previous.support.register_maps()
    namespace = controller.build_namespace(rounds=1)
    # The inherited static command builder creates its fixture directories.
    # Derive arguments in an owned temporary tree, never in the real output;
    # parent admission and child verification must be repeatable/read-only there.
    with tempfile.TemporaryDirectory(prefix='scenario7_contact_probe_plan_') as temporary:
        staging = Path(temporary)
        item = next(item for item in namespace.build_plan(staging, (map_name,), run_id)
                    if item['phase'] == 'preflight')
        command = [str(root) + value[len(str(staging)):]
                   if value.startswith(str(staging) + '/') else value
                   for value in item['command']]
    for option, values in (
        ('--modes', ['adaptive']), ('--run', [str(run_id)]),
        ('--output', [str(root / 'flight')]), ('--candidate', ['contact_probe_repair_v1']),
        ('--static-latched-preflight', [str(static_preflight)]),
    ):
        replace_option(command, option, values)
    if ('--profile-cpu' not in command or '--small-pool-profile-reference' in command
            or '--time-reference-folder' in command):
        raise ValueError('Probe must be one profiled mode without a flight reference')
    return command[2:]


def trace_settings(root, map_name):
    selected = dict(ROIS[map_name], half_extent_xy_m=2., z_min_m=-.5, z_max_m=3.5,
                    file_cap_bytes=FILE_CAP, record_cap_bytes=1024 * 1024,
                    queue_record_cap=4096, queue_memory_cap_bytes=16 * 1024 * 1024)
    environment = dict(
        SUPER_G1_CONTACT_TRACE_DIR=str(root / 'cpp_trace'),
        SUPER_CONTACT_TRACE_CENTER_X=format(selected['center_x'], '.17g'),
        SUPER_CONTACT_TRACE_CENTER_Y=format(selected['center_y'], '.17g'))
    return dict(roi=selected, environment=environment,
                settings_sha256=hashlib.sha256(json.dumps(
                    dict(roi=selected, environment=environment), sort_keys=True,
                    separators=(',', ':')).encode()).hexdigest())


def adapt_child(source):
    changes = (
        ("        schema='adaptive-cpu40-seed1-exploratory-v1', candidate=args.candidate,",
         "        schema=PROBE['schema'], candidate=args.candidate,\n"
         "        diagnostic_only=True, primary_comparison_eligible=False,\n"
         "        CPU_comparison_eligible=False, profile_reference_eligible=False,\n"
         "        contact_probe=PROBE['trace'],"),
        ('    hashes = {str(p): event.sha(p) for p in sorted(files)}',
         "    files.update(Path(name) for name in PROBE['bound_assets_sha256'])\n"
         '    hashes = {str(p): event.sha(p) for p in sorted(files)}'),
        ("                result['candidate'] = args.candidate",
         "                result['diagnostic_only'] = True\n"
         "                result['primary_comparison_eligible'] = False\n"
         "                result['CPU_comparison_eligible'] = False\n"
         "                result['profile_reference_eligible'] = False\n"
         "                result['candidate'] = args.candidate"),
    )
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('Contact-probe adaptation cardinality changed: ' + old)
        source = source.replace(old, new, 1)
    return source


def child_main(plan_path):
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text())
    root = Path(plan['output'])
    if (plan.get('schema') != SCHEMA or plan.get('planned_flights') != 1
            or plan.get('mode') != 'adaptive' or plan.get('map') not in ROIS
            or plan_path != root / 'probe_plan.json'
            or plan['trace'] != trace_settings(root, plan['map'])
            or plan['child_arguments'] != flight_arguments(root, plan['map'], plan['run_id'],
                                                        Path(plan['static_preflight']))):
        raise ValueError('Invalid or altered single-flight probe plan')
    # A direct invocation of the internal entry point cannot bypass the fixed
    # historical source/binary admission or upgrade itself to a later build.
    canonical = frozen_v1_inputs()
    if any(plan['bound_assets_sha256'].get(name) != digest for name, digest in canonical.items()):
        raise ValueError('Probe omits or changes frozen repair-v1 inputs')
    changed = changed_inputs(plan['bound_assets_sha256'])
    if changed:
        raise ValueError('Probe inputs changed before launch: ' + repr(changed))
    if (root / 'flight').exists():
        raise FileExistsError('A probe invocation is never resumed or retried')
    os.environ.update(plan['trace']['environment'])
    previous_argv = sys.argv
    try:
        sys.argv = [str(Path(child.__file__)), *plan['child_arguments']]
        main = child.build_main(source_transform=adapt_child, namespace_updates={'PROBE': plan})
        return main()
    finally:
        sys.argv = previous_argv


def audit_trace_file(path):
    """Fail closed on incomplete/capped/dropped traces; retain all evidence."""
    path = Path(path)
    errors, counts, footer, last_kind, data_rows = [], Counter(), None, None, 0
    sequences = set()
    with path.open() as stream:
        for line_no, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
                kind = row['kind']
                if not isinstance(kind, str):
                    raise ValueError('kind must be a string')
                counts[kind] += 1
                last_kind = kind
                if kind == 'trace_footer':
                    if footer is not None:
                        errors.append('multiple_footers')
                    footer = row
                elif not kind.startswith('trace_'):
                    sequence = row.get('sequence')
                    # submit() allocates its sequence before locking the queue;
                    # concurrent producers may enqueue in a different order.
                    if type(sequence) is not int or sequence <= 0 or sequence in sequences:
                        errors.append(f'invalid_or_duplicate_sequence:{line_no}')
                    if type(sequence) is int:
                        sequences.add(sequence)
                    data_rows += 1
            except (ValueError, KeyError, TypeError) as error:
                errors.append(f'invalid_json_record:{line_no}:{error}')
    if footer is None or last_kind != 'trace_footer':
        errors.append('missing_final_footer')
    else:
        for field in ('dropped', 'errors', 'oversize_drops', 'queue_drops', 'contention_drops',
                      'exception_drops', 'closed_drops', 'file_cap_drops', 'queued_records', 'queued_bytes'):
            if type(footer.get(field)) is not int or footer[field] != 0:
                errors.append('nonzero_or_missing:' + field)
        if footer.get('file_cap_reached') is not False:
            errors.append('file_cap_reached_or_unknown')
        if footer.get('submitted') != data_rows or footer.get('written') != data_rows:
            errors.append('footer_row_count_mismatch')
        if sequences != set(range(1, data_rows + 1)):
            errors.append('incomplete_sequence_set')
        if footer.get('file_byte_cap') != FILE_CAP or path.stat().st_size > FILE_CAP:
            errors.append('invalid_file_cap')
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path),
                complete_lossless=not errors, errors=errors, kinds=dict(counts),
                data_rows=data_rows, footer=footer)


def audit_traces(directory):
    files = [audit_trace_file(path) for path in sorted(Path(directory).glob('contact_trace_*.jsonl'))]
    kinds = set().union(*(set(item['kinds']) for item in files)) if files else set()
    return dict(files=files, complete_lossless=bool(files) and all(item['complete_lossless'] for item in files),
                missing_evidence_kinds=sorted(REQUIRED_KINDS - kinds),
                interpretation='Absent records are not evidence of absence; any cap/drop/missing footer limits causal use.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--map', choices=tuple(ROIS))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--run-id', type=int)
    parser.add_argument('--static-preflight', type=Path,
                        help='Default: unchanged same-map repair-v1 static transport/RViz acceptance')
    parser.add_argument('--child-plan', type=Path, help=argparse.SUPPRESS)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument('--prepare-only', action='store_true')
    operation.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    if args.child_plan:
        return child_main(args.child_plan)
    if not args.map or args.output is None or not args.run_id or args.run_id < 1 or not (args.prepare_only or args.run):
        parser.error('--map, fresh --output, positive --run-id and --prepare-only|--run are required')
    root = args.output.resolve()
    if root == V1_ROOT or V1_ROOT in root.parents:
        parser.error('Diagnostic output must not modify the frozen v1 campaign')
    foreign = sorted(key for key in os.environ if key.startswith('SUPER_'))
    if foreign:
        parser.error('Unset inherited SUPER_* settings; probe owns and records its runtime environment: ' + ', '.join(foreign))
    root.mkdir(parents=True, exist_ok=False)
    (root / 'cpp_trace').mkdir()
    state, code, launched, error = 'ADMISSION_FAILED', 2, False, None
    try:
        hashes = frozen_v1_inputs()
        preflight = (args.static_preflight or V1_ROOT / 'static_preflight' / args.map / 'acceptance.json').resolve()
        hashes[str(preflight)] = sha(preflight)
        child.previous.support.register_maps()
        namespace = controller.build_namespace(rounds=1)
        context = namespace.base.static.map_context(args.map)
        acceptance = namespace.base.static.validate_manifest(preflight, context)
        if acceptance.get('valid') is not True:
            raise ValueError('Same-overlay static preflight invalid: ' + repr(acceptance))
        plan = dict(schema=SCHEMA, output=str(root), map=args.map, mode='adaptive', run_id=args.run_id,
                    planned_flights=1, attempt_max=1, no_automatic_retry=True,
                    diagnostic_only=True, primary_comparison_eligible=False,
                    CPU_comparison_eligible=False, profile_reference_eligible=False,
                    runtime_cohort='repair_v1_unchanged', equivalence_claim=False,
                    frozen_v1_inventory=str(V1_INVENTORY), frozen_v1_inventory_sha256=V1_INVENTORY_SHA256,
                    static_preflight=str(preflight), trace=trace_settings(root, args.map),
                    child_arguments=flight_arguments(root, args.map, args.run_id, preflight),
                    bound_assets_sha256=hashes, owned_composed_rss_limit_mib=4608,
                    instrumentation_note='ROI tracing changes timing; diagnostic outcome only, not a new primary/reference observation.')
        save(root / 'probe_plan.json', plan)
        if args.prepare_only:
            state, code = 'PREPARED_ONLY', 0
            return code
        if namespace.base.MEMORY_RUNAWAY_MIB != 4608:
            raise ValueError('Original memory sentinel changed')
        env = dict(os.environ, **plan['trace']['environment'])
        item = dict(name='probe_child', path=str(root / 'flight'),
                    command=[sys.executable, str(Path(__file__).resolve()), '--child-plan', str(root / 'probe_plan.json')])
        def interrupted(signum, _frame):
            raise KeyboardInterrupt(f'Contact probe interrupted by signal {signum}')
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, interrupted)
        launched = True
        code = namespace.base.execute(item, root, env)
        trace = audit_traces(root / 'cpp_trace')
        save(root / 'trace_audit.json', trace)
        changed = changed_inputs(hashes)
        save(root / 'input_preservation.json', dict(unchanged=not changed, changed=changed))
        valid = code == 0 and not changed and trace['complete_lossless'] and not trace['missing_evidence_kinds']
        state = 'DIAGNOSTIC_RECORDED' if valid else 'DIAGNOSTIC_RETAINED_WITH_FAILURES'
        code = 0 if valid else 2
        return code
    except BaseException as exc:
        error = repr(exc)
        if launched:
            state = 'DIAGNOSTIC_STOPPED'
        raise
    finally:
        # Keep trace/audits even when native execution, resource guards, or
        # cancellation interrupt the flight. Never synthesize a successful row.
        if not (root / 'trace_audit.json').exists():
            save(root / 'trace_audit.json', audit_traces(root / 'cpp_trace'))
        save(root / 'status.json', dict(schema=SCHEMA, state=state, child_invocations=int(launched),
            actual_flights='inspect retained flight/raw.csv and native attempt evidence' if launched else 0,
            diagnostic_only=True, primary_comparison_eligible=False, profile_reference_eligible=False,
            no_automatic_retry=True, exit_code=code, error=error))


if __name__ == '__main__':
    raise SystemExit(main())
