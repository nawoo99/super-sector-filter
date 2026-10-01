#!/usr/bin/env python3
"""Run the canonical three modes without a global mission-time cutoff.

The finite c39 runner is deliberately left unchanged.  A measurement-only
no-progress terminal keeps an absorbing stop from hanging a flight forever;
it is not a mission-duration limit and does not feed the planner.
"""
import math
import os

import scenario7_guard_v6_cpu_compare as previous
import normal_cpu_gpu_diagnostic as diagnostic


def main():
    options = diagnostic.search.OPTIONS
    inherited = options.get('loop_timeout_override')
    if inherited != 180:
        raise RuntimeError(
            f'Expected the inherited 180 s cutoff, found {inherited!r}')
    previous_window = os.environ.get('SCENARIO7_TERMINAL_STALL_WINDOW_S')
    previous_radius = os.environ.get('SCENARIO7_TERMINAL_STALL_RADIUS_M')
    options['loop_timeout_override'] = math.inf
    os.environ['SCENARIO7_TERMINAL_STALL_WINDOW_S'] = '60'
    os.environ['SCENARIO7_TERMINAL_STALL_RADIUS_M'] = '0.02'
    try:
        return previous.main()
    finally:
        options['loop_timeout_override'] = inherited
        for key, old in (
            ('SCENARIO7_TERMINAL_STALL_WINDOW_S', previous_window),
            ('SCENARIO7_TERMINAL_STALL_RADIUS_M', previous_radius),
        ):
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


if __name__ == '__main__':
    raise SystemExit(main())
