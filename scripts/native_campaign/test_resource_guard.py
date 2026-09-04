from native_campaign import (
    SustainedResourceViolation,
    cleanup_active_process_groups,
    resource_violation_reasons,
    spawn_process_group,
    wait_for_resource_preflight,
)


def healthy(available=9000.0, psi_some=0.0, psi_full=0.0):
    return {
        "system_available_mib": available,
        "psi_some_avg10": psi_some,
        "psi_full_avg10": psi_full,
    }


def test_resource_violation_reports_memory_and_psi():
    reasons = resource_violation_reasons(
        healthy(available=512.0, psi_some=55.87, psi_full=52.89),
        min_available_mib=2048.0,
        max_psi_some_avg10=10.0,
        max_psi_full_avg10=5.0,
    )

    assert len(reasons) == 3
    assert reasons[0] == "MemAvailable 512.0 MiB < 2048.0 MiB"
    assert "55.87" in reasons[1]
    assert "52.89" in reasons[2]


def test_runtime_violation_must_be_sustained_and_resets_when_healthy():
    guard = SustainedResourceViolation(2048.0, 10.0, 5.0, hold_s=5.0)
    unsafe = healthy(available=500.0)

    assert guard.observe(unsafe, now=10.0) is None
    assert guard.observe(unsafe, now=14.9) is None
    assert guard.observe(healthy(), now=15.0) is None
    assert guard.observe(unsafe, now=20.0) is None
    assert "MemAvailable" in guard.observe(unsafe, now=25.0)


def test_preflight_requires_a_continuous_healthy_window():
    snapshots = iter([
        healthy(available=1000.0),
        healthy(),
        healthy(),
        healthy(available=1000.0),
        healthy(),
        healthy(),
        healthy(),
    ])
    clock = {"now": 0.0}

    def monotonic():
        return clock["now"]

    def sleep(seconds):
        clock["now"] += seconds

    snapshot, waited = wait_for_resource_preflight(
        8192.0,
        10.0,
        5.0,
        stable_s=2.0,
        timeout_s=10.0,
        sample_s=1.0,
        snapshot_fn=lambda: next(snapshots),
        monotonic_fn=monotonic,
        sleep_fn=sleep,
    )

    assert snapshot["system_available_mib"] == 9000.0
    assert waited == 6.0


def test_registered_process_group_is_killed():
    child = spawn_process_group(["sleep", "30"])
    try:
        cleanup_active_process_groups()
        child.wait(timeout=5)
        assert child.returncode != 0
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
