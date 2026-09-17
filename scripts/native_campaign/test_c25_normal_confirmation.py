"""C25 exact OFF300 and immutable pilot admission: no simulated flights."""
from collections import Counter
from pathlib import Path
from unittest import mock

import pytest
import run_c25_normal_confirmation as controller
from test_c24_normal_validation import valid_triplet


def test_exact_315_with_independent_off300_and_fresh_static(tmp_path):
    plan = controller.build_plan(tmp_path, 'c24_iteration01')
    static = [c for c in plan if c['phase'] == 'static']
    flights = [c for c in plan if 'path' in c]
    assert len(static) == 40 and len(flights) == 105
    assert len({(c['map'], c['run'], m) for c in flights for m in c['modes']}) == 315
    for phase, repeats in controller.COUNTS.items():
        slots = Counter((c['map'], m) for c in flights if c['phase'] == phase for m in c['modes'])
        assert len(slots) == 15 and set(slots.values()) == {repeats}
    for c in flights:
        cmd = c['command']
        assert c['candidate'] == 'c24_iteration01' and c['async_certified_recovery'] is True
        assert '--async-certified-recovery' in cmd and '--extended-demand-lease' not in cmd
        assert cmd[cmd.index('--side-executor-threads')+1] == '3'
        assert '--event-body-heading' in cmd and '--mission-time-as-metric' in cmd
        assert '--sector-outcomes-as-metrics' in cmd
        assert ('--profile-cpu' in cmd) == (c['phase'] == 'preflight')
        assert ('--small-pool-profile-reference' in cmd) == (c['phase'] == 'confirmation20')


def test_map_positions_are_exactly_balanced_over_20_repeats(tmp_path):
    plan = controller.build_plan(tmp_path, 'fixture')
    off = [c for c in plan if c['phase'] == 'confirmation20']
    positions = Counter((c['map'], i % 5) for i, c in enumerate(off))
    assert len(positions) == 25 and set(positions.values()) == {4}
    # Twenty does not divide six permutations: disclose rather than claim exact mode balance.
    for m in controller.base.MAPS:
        orders = Counter(tuple(c['modes']) for c in off if c['map'] == m)
        assert len(orders) == 6 and set(orders.values()) == {3, 4}


@pytest.mark.parametrize('run', [0, -1, True, 1.2])
def test_invalid_run_refused(tmp_path, run):
    with pytest.raises(ValueError):
        controller.build_plan(tmp_path, 'fixture', run)


def test_missing_incomplete_duplicate_or_modified_confirmation_evidence_fails(tmp_path):
    commands = controller.build_plan(tmp_path/'campaign', 'fixture')
    assert not controller.phase_gate(commands, 'confirmation20')['valid']
    selected = [c for c in commands if c['phase'] == 'confirmation20']
    for c in selected:
        folder = Path(c['path'])
        valid_triplet(folder, c['map'], c['run'], False, c['candidate'], c['modes'], True)
        audit = controller.base.triplet_audit(folder, c['map'], c['run'], False, c['candidate'], c['modes'], True)
        controller.base.save(folder/'triplet_verification.json', audit)
    assert controller.phase_gate(commands, 'confirmation20')['valid']
    assert not controller.phase_gate(commands + [selected[0]], 'confirmation20')['valid']
    assert not controller.phase_gate(commands[:-1], 'confirmation20')['valid']
    stored = Path(selected[0]['path'])/'triplet_verification.json'
    audit = controller.base.read(stored)
    audit['checks']['full:completed'] = False
    controller.base.save(stored, audit)
    assert not controller.phase_gate(commands, 'confirmation20')['valid']


def test_absent_pilot_cannot_be_admitted(tmp_path):
    with mock.patch.dict('os.environ', {}, clear=True):
        assert not controller.admit_previous(tmp_path)['valid']


def test_existing_destination_refused(tmp_path):
    with pytest.raises(SystemExit):
        controller.main(['--output', str(tmp_path)])
