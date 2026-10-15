"""Comparison Sector admission preserves outcomes without selecting solver opportunities."""
import copy

import pytest

import adaptive_cpu40_seed1 as runner
import run_c24_normal_validation as controller
from test_adaptive_cpu40_seed1 import three_mode_profile_reference_fixture
from test_c24_normal_validation import valid_triplet, change_summary, write_raw


SETTINGS = (
    '[MISSION_GOAL_IDENTITY_SETTINGS] enabled=1 executor=single '
    'callbacks_serialized=1 timers_qos_unchanged=1\n'
    '[GOAL_RETRANSMIT_IDENTITY] enabled=true role=receiver guarded_demand=true '
    'identity=creation_stamp_raw_pose_frame default_off=true\n'
)
INITIAL = '[MISSION_GOAL_IDENTITY] stamp_ns=100 new_intent=1 new_identity=1 supported=1 waypoint=0\n'
REPEAT = '[MISSION_GOAL_IDENTITY] stamp_ns=100 new_intent=0 new_identity=0 supported=1 waypoint=0\n'
COALESCED = ('[GOAL_RETRANSMIT_COALESCED] stamp_ns=100 generation=2 map=3 '
             'queued_revision=1 accepted_revision=1 coalesced_total=1\n')


def no_opportunity():
    return runner.goal_identity_audit(SETTINGS + INITIAL)


def test_no_opportunity_keeps_strict_proof_false_but_checks_consistency():
    audit = no_opportunity()
    assert audit['valid'] is False
    assert audit['checks']['actual_retransmissions'] is False
    assert audit['checks']['actual_receiver_coalescing'] is False
    assert audit['checks']['coalesced_identity_linkage'] is False
    assert audit['publications'] == 1 and audit['coalesced'] == 0
    assert audit['identity_consistency_valid'] is True
    assert runner.goal_identity_admission_valid(audit, 'sector', True)
    for mode in ('full', 'adaptive', 'sector'):
        assert not runner.goal_identity_admission_valid(audit, mode)
    for mode in ('full', 'adaptive'):
        assert not runner.goal_identity_admission_valid(audit, mode, True)


@pytest.mark.parametrize('stack', [
    '', SETTINGS, INITIAL, SETTINGS.replace('receiver', 'broken') + INITIAL,
    SETTINGS + INITIAL.replace('supported=1', 'supported=0'),
    SETTINGS + INITIAL + INITIAL,
    SETTINGS + REPEAT,
    SETTINGS + INITIAL + REPEAT.replace('waypoint=0', 'waypoint=1'),
    SETTINGS + INITIAL + '[MISSION_GOAL_IDENTITY] malformed\n',
    SETTINGS + INITIAL + '[GOAL_RETRANSMIT_COALESCED] malformed\n',
    SETTINGS + INITIAL + COALESCED,
    SETTINGS + INITIAL + REPEAT + COALESCED.replace('stamp_ns=100', 'stamp_ns=101'),
    SETTINGS + INITIAL + REPEAT + COALESCED.replace('generation=2', 'generation=0'),
    SETTINGS + INITIAL + REPEAT + COALESCED.replace('coalesced_total=1', 'coalesced_total=2'),
    SETTINGS + INITIAL + REPEAT + COALESCED + COALESCED,
])
def test_missing_or_corrupted_producer_or_observed_coalescing_never_admitted(stack):
    audit = runner.goal_identity_audit(stack)
    assert audit['identity_consistency_valid'] is False
    assert not runner.goal_identity_admission_valid(audit, 'sector', True)


def test_observed_coalescing_still_requires_exact_linkage_and_monotonic_counter():
    stack = SETTINGS + INITIAL + REPEAT + COALESCED + REPEAT + COALESCED.replace(
        'coalesced_total=1', 'coalesced_total=2')
    audit = runner.goal_identity_audit(stack)
    assert audit['valid'] and audit['identity_consistency_valid']
    assert audit['coalesced'] == 2


def reference_fixture():
    plan, reference, summaries = three_mode_profile_reference_fixture()
    for value in (plan, reference):
        value.update(sector_outcomes_as_metrics=True, goal_retransmit_identity=True)
    for mode, row in summaries.items():
        row['goal_retransmit_exercised'] = True
        row['goal_identity_audit'] = runner.goal_identity_audit(SETTINGS + INITIAL + REPEAT + COALESCED)
    sector = summaries['sector']
    sector.update(success=False, safety_collisions=2, demand_replan_exercised=False,
                  goal_retransmit_exercised=False, goal_identity_audit=no_opportunity())
    sector['source_acquisition']['checks'].update(
        goal_identity_audit=True, goal_identity_consistency=True)
    return plan, reference, summaries


def test_profile_reference_admits_measured_sector_failure_without_optimization_opportunities():
    plan, reference, summaries = reference_fixture()
    audit = runner.small_pool_profile_reference_audit(plan, reference, summaries)
    assert audit['valid']
    for key in ('sector_safe_source', 'sector_demand_exercised', 'sector_goal_identity_exercised'):
        assert audit['checks'][key] is False
        assert key not in audit['acceptance_checks']
    assert audit['acceptance_checks']['sector_identity_consistency'] is True
    assert summaries['sector']['success'] is False and summaries['sector']['safety_collisions'] == 2


@pytest.mark.parametrize('mutation', ['missing_audit', 'bad_audit', 'missing_source', 'unknown_success',
                                     'unknown_contact', 'bad_resource', 'bad_timing'])
def test_comparison_sector_reference_never_approves_missing_or_invalid_evidence(mutation):
    plan, reference, summaries = reference_fixture()
    sector = summaries['sector']
    if mutation == 'missing_audit':
        sector.pop('goal_identity_audit')
    elif mutation == 'bad_audit':
        sector['goal_identity_audit']['identity_consistency_valid'] = False
    elif mutation == 'missing_source':
        sector['source_acquisition']['checks'].pop('goal_identity_consistency')
    elif mutation == 'unknown_success':
        sector.pop('success')
    elif mutation == 'unknown_contact':
        sector['safety_collisions'] = None
    elif mutation == 'bad_resource':
        sector['resource_valid'] = False
    else:
        sector['small_pool_timing']['valid'] = False
    assert not runner.small_pool_profile_reference_audit(plan, reference, summaries)['valid']


@pytest.mark.parametrize('mode', ['full', 'adaptive'])
def test_reference_full_adaptive_keep_strict_exercise_requirements(mode):
    plan, reference, summaries = reference_fixture()
    summaries[mode].update(goal_retransmit_exercised=False, demand_replan_exercised=False,
                           goal_identity_audit=no_opportunity())
    audit = runner.small_pool_profile_reference_audit(plan, reference, summaries)
    assert not audit['valid']
    assert audit['acceptance_checks'][mode + '_demand_exercised'] is False
    assert audit['acceptance_checks'][mode + '_goal_identity_exercised'] is False


def test_reference_default_sector_behavior_remains_strict():
    plan, reference, summaries = reference_fixture()
    plan['sector_outcomes_as_metrics'] = False
    assert not runner.small_pool_profile_reference_audit(plan, reference, summaries)['valid']


@pytest.mark.parametrize('profile', [False, True])
def test_controller_preserves_sector_strict_observations_but_accepts_comparison(tmp_path, profile):
    _, raw = valid_triplet(tmp_path, profile=profile)
    change_summary(tmp_path, 'sector', success=False, safety_collisions=1,
                   goal_retransmit_exercised=False, demand_replan_exercised=False,
                   goal_identity_audit=no_opportunity())
    for row in raw:
        if row['mode'] == 'sector':
            row.update(success='False', safety_collisions='1', static_pcd_collisions='1')
    write_raw(tmp_path, raw)
    audit = controller.triplet_audit(tmp_path, 'seed1', 18000, profile)
    assert audit['valid']
    assert audit['checks']['sector:goal_identity'] is False
    assert audit['checks']['sector:demand_exercised'] is False
    assert 'sector:goal_identity' not in audit['acceptance_checks']
    assert audit['outcome_failures']['sector'] == {'success': False, 'safety_collisions': 1}
    broken = copy.deepcopy(no_opportunity())
    broken['identity_consistency_valid'] = False
    change_summary(tmp_path, 'sector', goal_identity_audit=broken)
    assert not controller.triplet_audit(tmp_path, 'seed1', 18000, profile)['valid']


@pytest.mark.parametrize('mode', ['full', 'adaptive'])
def test_controller_full_adaptive_remain_strict(tmp_path, mode):
    valid_triplet(tmp_path)
    change_summary(tmp_path, mode, goal_retransmit_exercised=False,
                   demand_replan_exercised=False, goal_identity_audit=no_opportunity())
    audit = controller.triplet_audit(tmp_path, 'seed1', 18000, True)
    assert not audit['valid']
    assert audit['acceptance_checks'][mode + ':goal_identity'] is False
    assert audit['acceptance_checks'][mode + ':demand_exercised'] is False
