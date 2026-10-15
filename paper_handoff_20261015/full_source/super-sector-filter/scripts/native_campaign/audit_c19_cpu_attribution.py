#!/usr/bin/env python3
"""Retain a verification verdict separately from controller execution COMPLETE."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign', type=Path)
    args = parser.parse_args()
    root = args.campaign.resolve()
    output = root / 'verification.json'
    if output.exists():
        raise RuntimeError('No overwrite')
    plan = json.loads((root/'plan.json').read_text())
    arms = {}
    evidence = {}
    for arm, folder in [('ON',root/'profile_preflight_run9500'),
                        ('OFF',root/'repeats/r01_run9501')]:
        summary = json.loads((folder/'summary.json').read_text())
        rows = summary['results']
        checks = dict(three_modes=set(r['mode'] for r in rows)=={'full','sector','adaptive'} and len(rows)==3,
            all_completed=all(r['success'] is True for r in rows),
            no_contacts=all(r['safety_collisions']==0 for r in rows),
            source_contracts=all(all(r['source_acquisition']['checks'].values()) for r in rows),
            safety_quality=summary['comparison']['safety_and_quality_pass'],
            paired_mission_time=summary['comparison']['mission_time_guardrail_pass'])
        for mode in ('full','sector','adaptive'):
            log_path = next((folder/'artifacts').glob(f'*_{mode}.attempt1.stack.log'))
            log = log_path.read_text()
            checks[f'{mode}_profile_presence_correct'] = ('[THREAD_CPU_PROFILE]' in log) == (arm=='ON')
            if mode == 'adaptive':
                episodes = {}
                for time, event, cycle in re.findall(
                        r'\[([\d.]+)\].*\[EVENT_RECOVERY_(FULL|SECTOR)\] cycle=(\d+)', log):
                    episodes.setdefault(cycle,{})[event]=float(time)
                for episode in episodes.values():
                    if set(episode) != {'FULL','SECTOR'}:
                        raise ValueError('Unclosed recovery episode')
                    episode['full_residence_s']=episode['SECTOR']-episode['FULL']
                evidence[arm]=dict(log=str(log_path), sha256=sha(log_path), episodes=episodes,
                    version_changed_lines=[line for line in log.splitlines()
                                           if '[TRAJ_GUARD_CERT]' in line and 'status=VERSION_CHANGED' in line],
                    brake_rejected_lines=[line for line in log.splitlines()
                                          if '[TRAJ_GUARD_BRAKE_REJECTED]' in line],
                    full_residence_not_identical_to_added_mission_time=True)
        arms[arm]=dict(checks=checks, comparison=summary['comparison'])
    hashes_ok = all(sha(p)==digest for p,digest in plan['runtime_sha256'].items())
    frozen_normal_ok = sha('/root/share/here/90_raw_normal_300_rows.csv') == (
        'b40f880271a52f4b3332bfe67afe3d489cf8c6d444ac0c72ed30d9e9cd445ec5')
    result = dict(schema='c19-attribution-verification-v1', arms=arms,
        runtime_hashes_unchanged=hashes_ok, frozen_normal_unchanged=frozen_normal_ok,
        diagnostic_execution_complete=True,
        all_verification_gates_pass=hashes_ok and frozen_normal_ok and
            all(all(a['checks'].values()) for a in arms.values()),
        expansion_campaign_started=False, new_flight_retries=0,
        profiler_overhead_causal_estimate_available=False,
        autonomy_full_cpu_independently_measured=False,
        recovery_evidence=evidence)
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('arms','recovery_evidence')},indent=2))


if __name__ == '__main__':
    main()
