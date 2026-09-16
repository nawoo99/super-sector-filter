from pathlib import Path

from run_c19_frozen_validation import ORDERS, REFERENCE_SOURCES, common_args


def test_fixed_orders_cover_five_of_each_mode_without_duplicates():
    assert len(ORDERS) == 5
    assert len(set(ORDERS)) == 5
    assert all(set(order) == {'full', 'sector', 'adaptive'} and len(order) == 3
               for order in ORDERS)


def test_common_flags_preserve_c19_and_do_not_enable_profile_by_default():
    args = common_args(Path('/tmp/example'))
    assert '--profile-cpu' not in args
    assert '--compare-occupied-box-scan' not in args
    assert '--frontend-dedicated-executor' not in args
    assert args[args.index('--side-executor-threads') + 1] == '2'
    assert args[args.index('--mean-cpu-reduction-target-pct') + 1] == '30'
    for flag in ('--compose', '--static-pc-latched-once', '--monitor-intervals',
                 '--guarded-demand-replan', '--extended-demand-lease',
                 '--goal-retransmit-identity', '--optimizer-clearance-gate-first'):
        assert flag in args


def test_timing_reference_provenance_is_mode_specific():
    assert set(REFERENCE_SOURCES) == {'full', 'sector', 'adaptive'}
    for mode, path in REFERENCE_SOURCES.items():
        assert path.name == f'{mode}_summary.json'
