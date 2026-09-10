#!/usr/bin/env python3
"""Fail-closed gate for the default-off/common burst-dropout smoke."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

from native_campaign import parse_sensor_cadence_log


def close(value: object, expected: float, tolerance: float = 1e-6) -> bool:
    try:
        return math.isclose(float(value), expected, abs_tol=tolerance)
    except (TypeError, ValueError):
        return False


def analyze(default_log: Path, enabled_log: Path) -> dict[str, object]:
    default = parse_sensor_cadence_log(default_log)
    enabled = parse_sensor_cadence_log(enabled_log)
    checks = {
        "ordinary_config_default_off": default.get("sensor_dropout_enabled") is False,
        "ordinary_config_drops_zero": default.get("sensor_dropped_frames") == 0,
        "ordinary_config_delivers_all": (
            default.get("sensor_rendered_frames") == default.get("sensor_delivered_frames")
            and (default.get("sensor_rendered_frames") or 0) > 0
        ),
        "heldout_config_enabled": enabled.get("sensor_dropout_enabled") is True,
        "heldout_env_phase_override_observed": (
            enabled.get("sensor_dropout_phase_env_override") is True
        ),
        "heldout_schedule_configured": (
            close(enabled.get("sensor_dropout_warmup_s"), 1.0)
            and close(enabled.get("sensor_dropout_period_s"), 2.0)
            and close(enabled.get("sensor_dropout_duration_s"), 0.5)
            and close(enabled.get("sensor_dropout_phase_s"), 0.6)
        ),
        "heldout_accounting_balanced": (
            (enabled.get("sensor_rendered_frames") or -1)
            == (enabled.get("sensor_delivered_frames") or 0)
            + (enabled.get("sensor_dropped_frames") or 0)
        ),
        "heldout_burst_exercised": (
            (enabled.get("sensor_dropout_bursts") or 0) >= 1
            and (enabled.get("sensor_dropped_frames") or 0) >= 5
            and (enabled.get("sensor_dropout_max_consecutive_dropped") or 0) >= 5
            and (enabled.get("sensor_dropout_max_delivered_gap_s") or 0.0) >= 0.5
        ),
        "renderer_cadence_near_10_hz": (
            9.5 <= float(default.get("sensor_hz") or 0.0) <= 10.5
            and 9.5 <= float(enabled.get("sensor_hz") or 0.0) <= 10.5
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema": "sensor-burst-dropout-smoke-gate-v1",
        "decision": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failure_reasons": failed,
        "ordinary_default_off": default,
        "heldout_enabled_phase_0p6": enabled,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--default-log", type=Path, required=True)
    parser.add_argument("--enabled-log", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.default_log, args.enabled_log)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    temporary.write_text(rendered)
    os.replace(temporary, args.out)
    print(rendered, end="")
    return 0 if result["decision"] == "PASS" else 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
