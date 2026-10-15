#!/usr/bin/env python3
"""Bounded diagnostic-only reproduction; capture stacks before resource abort.

Never contributes a primary comparison or replaces a failed attempt. GDB pauses
the target, so every run in this diagnostic is excluded from timing/CPU claims.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import psutil
from run_c22_normal_campaign import ROOT, common_args, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--run', type=int, default=17000)
    parser.add_argument('--map', choices=('seed5','seed9'), default='seed5')
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--mode', choices=('full','adaptive'), default='adaptive')
    args = parser.parse_args()
    root = args.output.resolve(); root.mkdir(parents=True, exist_ok=False)
    evidence = ROOT/'results/c22_normal_five_20260916/iteration04'
    command = common_args(root)
    command.remove('--extended-demand-lease')
    for flag, value in {'--candidate':'c24_memory_diagnostic', '--side-executor-threads':'3',
        '--static-latched-preflight':str(evidence/'static_preflight'/args.map/'acceptance.json'),
        '--time-reference-folder':str(evidence/'references'/args.map)}.items():
        command[command.index(flag)+1] = value
    command += ['--event-body-heading', '--mission-time-as-metric', '--map', args.map,
                '--run', str(args.run), '--output', str(root/'flight')]
    if args.profile:
        command += ['--profile-cpu', '--callback-trace', '--modes', args.mode]
    else:
        assert args.map == 'seed5'
        command += ['--small-pool-profile-reference',str(evidence/'preflight/seed5/r01_run14002'),
                    '--modes','sector','adaptive','full']
    save(root/'diagnostic_plan.json',dict(command=command, primary=False,
         gdb_trigger_rss_mib=4096, stop_after_stack=True, max_wall_s=480))
    captured = None
    started = time.monotonic()
    with (root/'runner.log').open('x') as stream:
        child = subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
                                 env=dict(os.environ,SUPER_CPU_PROFILE='0',SUPER_CALLBACK_TRACE='0'))
        owner = psutil.Process(child.pid)
        try:
            while child.poll() is None:
                nodes = []
                for proc in owner.children(recursive=True):
                    try:
                        cmd = proc.cmdline()
                        if cmd and Path(cmd[0]).name in ('perfect_drone_adaptive_node','perfect_drone_full_node'):
                            rss = proc.memory_info().rss/(1024*1024)
                            nodes.append(dict(pid=proc.pid,create_time=proc.create_time(),rss_mib=rss))
                            if rss > 4096:
                                captured = dict(pid=proc.pid,rss_mib=rss,elapsed_s=time.monotonic()-started)
                                with (root/'gdb_stacks.txt').open('x') as trace:
                                    result = subprocess.run(['gdb','-batch','-nx','-p',str(proc.pid),
                                        '-ex','set pagination off','-ex','thread apply all bt 24','-ex','detach'],
                                        stdout=trace,stderr=subprocess.STDOUT,timeout=20)
                                captured['gdb_returncode'] = result.returncode
                                child.send_signal(signal.SIGINT)
                                break
                    except (psutil.NoSuchProcess,psutil.AccessDenied):
                        continue
                save(root/'diagnostic_status.json',dict(state='CAPTURED' if captured else 'RUNNING',
                     nodes=nodes,captured=captured,elapsed_s=time.monotonic()-started,pid=child.pid))
                if captured or time.monotonic()-started > 480:
                    if child.poll() is None: child.send_signal(signal.SIGINT)
                    break
                time.sleep(1)
            code = child.wait(timeout=30)
            save(root/'diagnostic_status.json',dict(state='STACK_CAPTURED' if captured else 'ENDED_NO_CAPTURE',
                 captured=captured,returncode=code,elapsed_s=time.monotonic()-started,primary=False))
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGINT)
                child.wait(timeout=30)


if __name__ == '__main__':
    main()
