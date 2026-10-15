#!/usr/bin/env python3
"""Run frozen c33 escape-hold validation using the c32 two-stage scheduler."""
from pathlib import Path

import run_scenario7_v7_n10 as previous


CANDIDATE = 'c33_escape_hold_gate_v8_n10'
BASE_RUN = 84100
THIS_FILE = Path(__file__).resolve()


def main():
    old_candidate = previous.CANDIDATE
    old_base_run = previous.BASE_RUN
    old_frozen_identity = previous.frozen_identity

    def frozen_identity(root):
        hashes = old_frozen_identity(root)
        hashes[str(THIS_FILE)] = previous.sha256(THIS_FILE)
        return hashes

    previous.CANDIDATE = CANDIDATE
    previous.BASE_RUN = BASE_RUN
    previous.frozen_identity = frozen_identity
    try:
        return previous.main()
    finally:
        previous.frozen_identity = old_frozen_identity
        previous.BASE_RUN = old_base_run
        previous.CANDIDATE = old_candidate


if __name__ == '__main__':
    raise SystemExit(main())
