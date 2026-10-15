#!/usr/bin/env python3
"""Post-hoc recovery audit of preserved Scenario7 flight logs.

This leaves original flight summaries and the stopped campaign status intact.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from audit_cpu40_recovery import audit_file


NAME = re.compile(r'(?P<map>.+)_run(?P<run>\d+)_(?P<mode>full|sector|adaptive)\.attempt1\.stack\.log$')


def reaudited_rows(root):
    rows = []
    for log in sorted(root.glob('stage*/*/r*_run*/artifacts/*.attempt1.stack.log')):
        match = NAME.fullmatch(log.name)
        if match is None:
            raise ValueError(f'unrecognized flight log: {log}')
        flight = log.parent.parent
        mode = match['mode']
        summary = flight / f'{mode}_summary.json'
        if not summary.is_file():
            raise ValueError(f'missing original flight summary: {summary}')
        original = json.loads(summary.read_text())
        updated = audit_file(log, mode=mode)
        rows.append({
            'stage': flight.parent.parent.name,
            'map': match['map'],
            'repeat': int(flight.name.split('_', 1)[0][1:]),
            'run': int(match['run']),
            'mode': mode,
            'log': str(log),
            'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
            'original_valid': original['strict_recovery_audit']['valid'],
            'reaudit_valid': updated['valid'],
            'errors': updated['errors'],
            'opened_cycles': updated['opened_cycles'],
            'completed_cycles': len(updated['completed_cycles']),
            'outstanding_cycles': updated['outstanding_cycles'],
            'path_certificates': sum(
                cycle.get('path_certificates', 0)
                for cycle in updated['completed_cycles']),
            'superseded_cycles': [
                cycle['cycle'] for cycle in updated['completed_cycles']
                if cycle.get('path_certificates', 0) > 1],
        })
    identity = [(row['stage'], row['map'], row['repeat'], row['run'], row['mode'])
                for row in rows]
    if len(identity) != len(set(identity)):
        raise ValueError('duplicate preserved flight identity')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign', type=Path)
    args = parser.parse_args()
    root = args.campaign.resolve()
    rows = reaudited_rows(root)
    report = {
        'schema': 'scenario7-posthoc-recovery-reaudit-v2',
        'scope': 'preserved flights only; no rerun, replacement, or physical safety inference',
        'campaign': str(root),
        'flight_count': len(rows),
        'original_valid_count': sum(row['original_valid'] for row in rows),
        'reaudit_valid_count': sum(row['reaudit_valid'] for row in rows),
        'changed_verdicts': [row for row in rows
                             if row['original_valid'] != row['reaudit_valid']],
        'invalid_flights': [row for row in rows if not row['reaudit_valid']],
        'rows': rows,
    }
    output = root / 'posthoc_recovery_audit_v2.json'
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    lines = [
        '# Preserved Scenario7 recovery-log re-audit', '',
        f"- Actual flight logs: {len(rows)}",
        f"- Original strict audit valid: {report['original_valid_count']}/{len(rows)}",
        f"- Revised strict audit valid: {report['reaudit_valid_count']}/{len(rows)}",
        f"- Changed verdicts: {len(report['changed_verdicts'])}",
        f"- Remaining invalid flights: {len(report['invalid_flights'])}", '',
        'Original summaries and stopped status remain unchanged. This is an audit',
        'of the same preserved logs and does not fill the unflown Full trial.', '',
    ]
    for row in report['changed_verdicts']:
        lines.append(f"- {row['map']} repeat {row['repeat']} run {row['run']} "
                     f"{row['mode']}: {row['original_valid']} → {row['reaudit_valid']}; "
                     f"superseded cycles {row['superseded_cycles']}")
    for row in report['invalid_flights']:
        lines.append(f"- Invalid: {row['map']} repeat {row['repeat']} "
                     f"run {row['run']} {row['mode']}: {row['errors']}")
    (root / 'posthoc_recovery_audit_v2.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({key: report[key] for key in
                      ('flight_count', 'original_valid_count',
                       'reaudit_valid_count', 'changed_verdicts', 'invalid_flights')},
                     indent=2))
    return 0 if rows and not report['invalid_flights'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
