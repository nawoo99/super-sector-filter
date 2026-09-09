#!/usr/bin/env python3
"""Fail closed on the frozen shm1_h9 dropout-equivalent pair."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from gen_static_heading_mismatch_h9 import MANIFEST_PATH
from validate_static_heading_mismatch_h3 import validate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = validate(
        MANIFEST_PATH,
        "static-heading-mismatch-v9",
        ("shm1_h9_clear", "shm1_h9_hazard"),
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
