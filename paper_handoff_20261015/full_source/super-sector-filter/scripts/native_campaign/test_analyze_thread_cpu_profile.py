from analyze_thread_cpu_profile import role_cpu_summary


def row(end=12., dt=2., pid=10, tid=11, pct=5., mode='full'):
    return dict(monotonic_s=end, interval_s=dt, mode=mode, campaign_active=True,
                experiment_threads=[dict(pid=pid, tid=tid, cpu_pct_one_core=pct)])


def test_role_uses_exact_pid_tid_and_fully_enclosed_weighted_intervals():
    log = '[THREAD_CPU_ROLE] version=1 pid=10 tid=11 role=static\n'
    rows = [row(), row(13., 1., pct=20.), row(10.5, 1., pct=100.),
            row(13., 1., pid=99, pct=100.), row(mode='adaptive')]
    r = role_cpu_summary(log, rows, 'full', 10, 10., 14.)['roles'][0]
    assert r['samples'] == 2
    assert r['observed_interval_s'] == 3.
    assert abs(r['sampled_cpu_core_s'] - .3) < 1e-12
    assert abs(r['mean_used_cores'] - .1) < 1e-12


def test_missing_or_ambiguous_role_is_not_zero_or_inferred_from_thread_name():
    assert role_cpu_summary('', [row()], 'full', 10, 10., 14.)['roles'] == []
    log = '[THREAD_CPU_ROLE] version=1 pid=10 tid=12 role=static\n'
    r = role_cpu_summary(log, [row()], 'full', 10, 10., 14.)['roles'][0]
    assert r['samples'] == 0 and r['mean_used_cores'] is None
    log += '[THREAD_CPU_ROLE] version=1 pid=10 tid=11 role=static\n'
    r = role_cpu_summary(log, [row()], 'full', 10, 10., 14.)['roles'][0]
    assert not r['unambiguous'] and r['mean_used_cores'] is None


def test_invalid_thread_samples_and_duplicate_markers_fail_closed():
    log = '[THREAD_CPU_ROLE] version=1 pid=10 tid=11 role=static\n' * 2
    for pct in (float('nan'), float('inf'), -1., None):
        r = role_cpu_summary(log, [row(pct=pct)], 'full', 10, 10., 14.)['roles'][0]
        assert r['unambiguous'] and r['mean_used_cores'] is None
