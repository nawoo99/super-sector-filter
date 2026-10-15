#!/usr/bin/env python3
"""Guard-v2 child: unchanged v1 gates plus exact runtime-policy identity."""
from __future__ import annotations

import os
from pathlib import Path
import re

import scenario7_cpu_compare_v3 as previous

PREVIOUS_SHA256 = '77cfe33404834a3f812791c0beb0eaa576f0faf98ba7ec36e600c12cb0646353'
DEFAULT_INSTALL = Path('/root/super_ws/scenario7_guard_v2_20260926/install')
STOP_POLICY = 'sampled_unknown_allowed_soft_margin_after_complete_hard_checks'
POLICY_REVISION = 2


def policy_audit(stack):
    records = re.findall(r'\[GUARDED_DEMAND_REPLAN\][^\r\n]*', stack)
    policies = [re.findall(r'\bstop_policy=([^\s]+)', row) for row in records]
    revisions = [re.findall(r'\bstop_policy_revision=([^\s]+)', row) for row in records]
    enabled = [re.findall(r'\benabled=([^\s]+)', row) for row in records]
    valid = (len(records) == 1 and policies == [[STOP_POLICY]] and revisions == [['2']]
             and enabled == [['true']])
    return dict(valid=valid, records=records, stop_policy=STOP_POLICY,
                policy_revision=POLICY_REVISION,
                scope='Complete hard-check traversal before a soft-margin stop exception; not strict-known-free certification.')


def adapt_main(source):
    replacements = (
        ('    plan = dict(\n',
         '    plan = dict(\n        guard_contract_revision=POLICY_REVISION,\n'
         '        guard_contract_stop_policy=STOP_POLICY,\n'),
        ('    hashes = {str(p): event.sha(p) for p in sorted(files)}',
         '    files.add(GUARD_CHILD_SOURCE)\n'
         '    hashes = {str(p): event.sha(p) for p in sorted(files)}'),
        ("                result['event_body_heading'] = args.event_body_heading",
         "                result['guard_contract_audit'] = policy_audit(stack)\n"
         "                result['source_acquisition']['checks']['guard_contract_revision_2'] = result['guard_contract_audit']['valid']\n"
         "                result['event_body_heading'] = args.event_body_heading"),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise ValueError('Guard-v2 child adaptation cardinality changed: ' + old)
        source = source.replace(old, new, 1)
    return source


def build_main(*, install_root=None):
    if previous.previous.support.sha256(previous.__file__) != PREVIOUS_SHA256:
        raise ValueError('Frozen repair-v1 child changed')
    selected = previous.runtime.RuntimeBinding(install_root or os.environ.get(
        'SCENARIO7_REPAIR_INSTALL', str(DEFAULT_INSTALL))).install
    if selected.is_relative_to(previous.runtime.DEFAULT_INSTALL.resolve()):
        raise ValueError('Guard-v2 child refuses the preserved repair-v1 overlay')
    main = previous.build_main(install_root=selected, source_transform=adapt_main,
        namespace_updates=dict(policy_audit=policy_audit, POLICY_REVISION=POLICY_REVISION,
                               STOP_POLICY=STOP_POLICY, GUARD_CHILD_SOURCE=Path(__file__).resolve(),
                               __doc__=__doc__))
    inherited_reference = main.__globals__['small_pool_profile_reference_audit']

    def reference_audit(plan, reference_plan, summaries):
        audit = inherited_reference(plan, reference_plan, summaries)
        valid = all(value.get('guard_contract_revision') == POLICY_REVISION
                    and value.get('guard_contract_stop_policy') == STOP_POLICY
                    for value in (plan, reference_plan))
        valid = valid and all(summaries.get(mode, {}).get('guard_contract_audit', {}).get('valid') is True
                              for mode in plan.get('modes', []))
        audit['checks']['guard_contract_revision_2_match'] = valid
        audit['acceptance_checks']['guard_contract_revision_2_match'] = valid
        audit['valid'] = audit['valid'] and valid
        return audit

    main.__globals__['small_pool_profile_reference_audit'] = reference_audit
    return main


def main():
    return build_main()()


if __name__ == '__main__':
    raise SystemExit(main())
