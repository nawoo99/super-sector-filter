#!/usr/bin/env python3
"""One prospective, instrumented heading ablation; never a replacement pilot."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from run_c22_normal_campaign import (ROOT, static_commands, common_args, save, sha,
                                     triplet_audit, frozen_policy, stages, MODES)
import static_latched_preflight as static


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--map', choices=tuple(static.MAP_GEOMETRIES), required=True)
    parser.add_argument('--run', type=int, required=True)
    parser.add_argument('--reference-root', type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    commands = static_commands(root, args.map)
    flight = root / 'flight'
    command = common_args(root)
    command.remove('--extended-demand-lease')
    command[command.index('--candidate') + 1] = 'c22_body_heading_probe_' + args.map
    command[command.index('--side-executor-threads') + 1] = '3'
    command[command.index('--static-latched-preflight') + 1] = str(root/'static_preflight'/args.map/'acceptance.json')
    command[command.index('--time-reference-folder') + 1] = str(args.reference_root.resolve()/args.map)
    command += ['--event-body-heading', '--profile-cpu', '--map', args.map,
                '--run', str(args.run), '--output', str(flight), '--modes', *MODES]
    commands.append(dict(name='flight', phase='diagnostic', command=command))
    frozen = frozen_policy()['sha256']
    paths = list(static.map_context(args.map)['paths'].values())
    paths += list((ROOT/'scripts/native_campaign').glob('*.py'))
    paths += list((args.reference_root.resolve()/args.map).glob('*.json'))
    frozen.update({str(p):sha(p) for p in paths})
    save(root/'plan.json', dict(map=args.map, run=args.run, commands=commands,
         frozen_sha256=frozen, profile_preflight_runs_per_mode=1, unprofiled_runs_per_mode=0,
         primary=False, no_retry=True, separate_from_pilot=True, event_body_heading=True,
         common_dispatch_lease_s=0.25, created_local=time.strftime('%Y-%m-%dT%H:%M:%S%z')))
    completed = []
    current = None
    try:
        for item in commands:
            current = item['name']
            if any(sha(p) != value for p,value in frozen.items()):
                raise RuntimeError('Frozen inputs changed during probe')
            save(root/'status.json', dict(state='RUNNING', current=current, completed=completed, pid=os.getpid()))
            env = dict(os.environ, SUPER_CPU_PROFILE='0', SUPER_CALLBACK_TRACE='0',
                       SUPER_EVENT_BODY_ALIGNED_SECTOR='0')
            if 'domain' in item:
                env['ROS_DOMAIN_ID'] = item['domain']
            print('START', current, flush=True)
            with (root/(current+'.log')).open('x') as log:
                result = subprocess.run(item['command'], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            completed.append(dict(name=current, returncode=result.returncode))
            if result.returncode:
                raise RuntimeError('Probe failed: ' + current)
        audit = triplet_audit(flight, args.map, args.run, True)
        save(flight/'triplet_verification.json', audit)
        save(flight/'thread_cpu_summary.json', {m:stages.summarize(flight,m,args.run,args.map) for m in MODES})
        if not audit['valid']:
            raise RuntimeError('Diagnostic triplet failed quality/time gate')
        save(root/'status.json', dict(state='COMPLETE', current=current, completed=completed, pid=os.getpid(),
             diagnostic_only=True))
    except BaseException as exc:
        save(root/'status.json', dict(state='STOPPED_FOR_DIAGNOSIS', current=current,
             completed=completed, pid=os.getpid(), error=repr(exc)))
        raise


if __name__ == '__main__':
    main()
