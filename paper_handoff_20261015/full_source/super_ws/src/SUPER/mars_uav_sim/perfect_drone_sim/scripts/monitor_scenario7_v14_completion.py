#!/usr/bin/env python3
"""Observe c40 continuation, write terminal verdict, and show a local notice."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import run_scenario7_v14_completion as campaign


ROOT = campaign.COMPLETION
STATUS = ROOT / 'status.json'
MONITOR = ROOT / 'monitor_terminal_status.json'
SUMMARY = Path(__file__).with_name('summarize_scenario7_v14_completion.py')


def notice(message):
    if not os.environ.get('DISPLAY'):
        return 'DISPLAY unavailable'
    try:
        result = subprocess.run(['zenity', '--notification', '--text', message],
                                capture_output=True, text=True, timeout=20, check=False)
        return 'exit=' + str(result.returncode) + ' ' + result.stderr[-300:]
    except (OSError, subprocess.TimeoutExpired) as error:
        return repr(error)


def main():
    while True:
        try:
            campaign_status = json.loads(STATUS.read_text())
        except (OSError, json.JSONDecodeError):
            time.sleep(30)
            continue
        state = campaign_status.get('state')
        if state in ('COMPLETE', 'STOPPED_FOR_DIAGNOSIS'):
            break
        time.sleep(30)
    report = None
    error = None
    if state == 'COMPLETE':
        result = subprocess.run([sys.executable, str(SUMMARY)],
                                capture_output=True, text=True, timeout=120, check=False)
        if result.returncode == 0:
            report = str(ROOT / 'summary_no_cutoff.md')
        else:
            error = result.stderr[-2000:] or result.stdout[-2000:]
    if state == 'COMPLETE' and report:
        message = 'SUPER c40: 210회 완료. 결과: ' + report
    elif state == 'COMPLETE':
        message = 'SUPER c40: 비행은 완료됐지만 합산 보고서 생성 실패. monitor_terminal_status.json 확인'
    else:
        message = 'SUPER c40: 실험 중단. ' + str(ROOT / 'status.json')
    notification = notice(message)
    campaign.base.atomic_json(MONITOR,
                              dict(campaign_state=state, completed_triplets=len(
                                  campaign_status.get('completed', [])),
                                   report=report, report_error=error,
                                   notification=notification, message=message))
    print(message, flush=True)
    return 0 if state == 'COMPLETE' and report else 1


if __name__ == '__main__':
    raise SystemExit(main())
