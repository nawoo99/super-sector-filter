"""Offline checks for the c39 fresh common campaign; no ROS or flights."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_scenario7_v13_n10 as campaign


def runtime_log(distance='0.6', maximum='1.2', steps='2'):
    prefix = '[perfect_drone_full_node-1] \x1b[0;32m Load param '
    suffix = ' success: \x1b[0;0m'
    return ''.join((
        prefix + 'super_planner/guard_topology_reroute/local_escape_distance_m'
        + suffix + distance + '\n',
        prefix + 'super_planner/guard_topology_reroute/local_escape_max_distance_m'
        + suffix + maximum + '\n',
        prefix + 'super_planner/guard_topology_reroute/local_escape_distance_steps'
        + suffix + steps + '\n',
    ))


def test_campaign_has_fresh_identity_and_nonoverlapping_run_range():
    assert campaign.CANDIDATE == 'c39_bounded_recovery_refresh_v13_n10'
    assert campaign.BASE_RUN == 96200
    assert campaign.BASE_RUN > campaign.previous.BASE_RUN


def test_bounded_recovery_runtime_contract_accepts_exact_profile():
    audit = campaign.bounded_recovery_runtime_audit(runtime_log())
    assert audit['valid']
    assert all(check['valid'] for check in audit['checks'].values())


@pytest.mark.parametrize('log', (
    '',
    runtime_log(maximum='0.6'),
    runtime_log(steps='1'),
    runtime_log() + runtime_log(),
))
def test_bounded_recovery_runtime_contract_fails_closed(log):
    assert not campaign.bounded_recovery_runtime_audit(log)['valid']


def test_current_integrated_runtime_contains_repair_markers(monkeypatch):
    monkeypatch.delenv('AMENT_PREFIX_PATH', raising=False)
    assert campaign.verify_runtime_install()['valid']


def test_preloaded_overlay_is_rejected_before_flight(monkeypatch):
    monkeypatch.setenv('AMENT_PREFIX_PATH', str(campaign.INSTALL_ROOT / 'perfect_drone_sim'))
    with pytest.raises(RuntimeError, match='overlay is preloaded'):
        campaign.verify_runtime_install()
