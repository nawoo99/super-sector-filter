from analyze_sensor_burst_dropout_smoke import analyze


def summary(*, enabled, rendered, delivered, dropped, bursts, consecutive, gap, phase, override):
    return (
        "[INFO] [perfect_tracking]: [SENSOR_CADENCE_SUMMARY] "
        f"frames={rendered} span_s=5.900000 hz=10.000000 raw_published={delivered} "
        "direct_handoffs=0 payload_bytes=100 side_entry_v1_enabled=0 "
        "side_entry_v1_spawned=0 side_entry_v1_injected_frames=0\n"
        "[INFO] [perfect_tracking]: [SENSOR_BURST_DROPOUT_SUMMARY] "
        f"enabled={enabled} warmup_s=1.000000 period_s=2.000000 "
        f"duration_s=0.500000 phase_s={phase:.6f} phase_env_override={override} "
        f"rendered={rendered} delivered={delivered} dropped={dropped} bursts={bursts} "
        f"max_consecutive_dropped={consecutive} max_delivered_gap_s={gap:.6f} "
        f"dropped_payload_bytes={dropped * 10}\n"
    )


def test_default_off_and_enabled_schedule_pass(tmp_path):
    default = tmp_path / "default.log"
    enabled = tmp_path / "enabled.log"
    default.write_text(summary(
        enabled=0, rendered=59, delivered=59, dropped=0, bursts=0,
        consecutive=0, gap=0.1, phase=0.0, override=0,
    ))
    enabled.write_text(summary(
        enabled=1, rendered=63, delivered=48, dropped=15, bursts=3,
        consecutive=5, gap=0.6, phase=0.6, override=1,
    ))
    result = analyze(default, enabled)
    assert result["decision"] == "PASS"


def test_missing_default_off_is_rejected(tmp_path):
    default = tmp_path / "default.log"
    enabled = tmp_path / "enabled.log"
    default.write_text(summary(
        enabled=1, rendered=59, delivered=54, dropped=5, bursts=1,
        consecutive=5, gap=0.6, phase=0.0, override=0,
    ))
    enabled.write_text(summary(
        enabled=1, rendered=63, delivered=48, dropped=15, bursts=3,
        consecutive=5, gap=0.6, phase=0.6, override=1,
    ))
    result = analyze(default, enabled)
    assert result["decision"] == "FAIL"
    assert not result["checks"]["ordinary_config_default_off"]
