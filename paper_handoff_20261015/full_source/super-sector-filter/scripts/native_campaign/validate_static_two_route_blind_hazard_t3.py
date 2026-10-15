#!/usr/bin/env python3
"""Fail closed on the one-factor sbd2_t3 redesign."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from validate_static_two_route_blind_hazard import validate


SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SCRIPT_DIR / "static_two_route_blind_hazard_t3_manifest.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = validate(
        MANIFEST_PATH,
        expected_schema="static-two-route-blind-hazard-v3",
        expected_maps=("sbd2_t3_clear", "sbd2_t3_hazard"),
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.out.with_suffix(args.out.suffix + ".tmp")
        temporary.write_text(rendered)
        os.replace(temporary, args.out)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
