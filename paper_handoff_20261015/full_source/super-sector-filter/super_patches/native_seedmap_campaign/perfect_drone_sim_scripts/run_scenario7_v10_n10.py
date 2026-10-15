#!/usr/bin/env python3
"""Run frozen c35 rest-only compute-budget validation."""
from pathlib import Path

import run_scenario7_v9_n10 as previous


CANDIDATE = 'c35_rest_only_compute_budget_v10_n10'
BASE_RUN = 88100
THIS_FILE = Path(__file__).resolve()


def main():
    old_candidate = previous.CANDIDATE
    old_base_run = previous.BASE_RUN
    old_frozen_identity = previous.previous.frozen_identity

    def frozen_identity(root):
        hashes = old_frozen_identity(root)
        hashes[str(THIS_FILE)] = previous.previous.sha256(THIS_FILE)
        return hashes

    previous.CANDIDATE = CANDIDATE
    previous.BASE_RUN = BASE_RUN
    previous.previous.frozen_identity = frozen_identity
    try:
        return previous.main()
    finally:
        previous.previous.frozen_identity = old_frozen_identity
        previous.BASE_RUN = old_base_run
        previous.CANDIDATE = old_candidate


if __name__ == '__main__':
    raise SystemExit(main())
