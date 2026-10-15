#!/usr/bin/env python3
"""Run frozen c34 compute-budget validation with the two-stage scheduler."""
from pathlib import Path

import run_scenario7_v7_n10 as previous


CANDIDATE = 'c34_decoupled_planning_compute_budget_v9_n10'
BASE_RUN = 86100
THIS_FILE = Path(__file__).resolve()


def main():
    old_candidate = previous.CANDIDATE
    old_base_run = previous.BASE_RUN
    old_frozen_identity = previous.frozen_identity

    def frozen_identity(root):
        hashes = old_frozen_identity(root)
        hashes[str(THIS_FILE)] = previous.sha256(THIS_FILE)
        for relative in (
                'super_planner/include/super_core/config.hpp',
                'super_planner/src/super_core/super_planner.cpp'):
            path = previous.SOURCE / relative
            hashes[str(path)] = previous.sha256(path)
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
