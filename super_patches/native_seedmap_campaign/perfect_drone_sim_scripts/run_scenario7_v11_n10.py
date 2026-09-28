#!/usr/bin/env python3
"""Run frozen c36 sixteen-direction forest-recovery validation."""
from pathlib import Path

import run_scenario7_v10_n10 as previous


CANDIDATE = 'c36_escape16_forest_recovery_v11_n10'
BASE_RUN = 90100
THIS_FILE = Path(__file__).resolve()


def main():
    old_candidate = previous.CANDIDATE
    old_base_run = previous.BASE_RUN
    old_frozen_identity = previous.previous.previous.frozen_identity

    def frozen_identity(root):
        hashes = old_frozen_identity(root)
        hashes[str(THIS_FILE)] = previous.previous.previous.sha256(THIS_FILE)
        return hashes

    previous.CANDIDATE = CANDIDATE
    previous.BASE_RUN = BASE_RUN
    previous.previous.previous.frozen_identity = frozen_identity
    try:
        return previous.main()
    finally:
        previous.previous.previous.frozen_identity = old_frozen_identity
        previous.BASE_RUN = old_base_run
        previous.CANDIDATE = old_candidate


if __name__ == '__main__':
    raise SystemExit(main())
