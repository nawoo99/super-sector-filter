#!/usr/bin/env python3
"""Generate shm1_h9 by changing only h8 common LiDAR rate from 4 to 2 Hz."""

from __future__ import annotations

import copy
import json
import os
import shutil
from pathlib import Path

import gen_static_heading_mismatch_h8 as h8
from gen_static_blind_corner_supplement import sha256


MANIFEST_PATH = h8.h7.SCRIPT_DIR / "static_heading_mismatch_h9_manifest.json"
MAP_CLEAR = "shm1_h9_clear"
MAP_HAZARD = "shm1_h9_hazard"
SENSING_RATE_HZ = 2


def generate() -> dict:
    base = h8.generate()
    maps = []
    for item, target_name in zip(base["maps"], (MAP_CLEAR, MAP_HAZARD)):
        source_name = item["map"]
        source_pcd = h8.h7.PCD_DIR / f"{source_name}.pcd"
        target_pcd = h8.h7.PCD_DIR / f"{target_name}.pcd"
        source_config = h8.h7.CONFIG_DIR / f"{source_name}.yaml"
        target_config = h8.h7.CONFIG_DIR / f"{target_name}.yaml"
        temporary_pcd = target_pcd.with_suffix(".pcd.tmp")
        shutil.copyfile(source_pcd, temporary_pcd)
        os.replace(temporary_pcd, target_pcd)
        contents = source_config.read_text().replace(
            f"{source_name}.pcd", f"{target_name}.pcd"
        ).replace("sensing_rate: 4\n", "sensing_rate: 2\n")
        temporary_config = target_config.with_suffix(".yaml.tmp")
        temporary_config.write_text(contents)
        os.replace(temporary_config, target_config)
        row = copy.deepcopy(item)
        row.update({
            "map": target_name,
            "pcd_sha256": sha256(target_pcd),
            "config_sha256": sha256(target_config),
        })
        maps.append(row)

    manifest = copy.deepcopy(base)
    manifest.update({
        "schema": "static-heading-mismatch-v9",
        "role": "exploratory common 2 Hz severe dropout-equivalent stress",
        "predecessor": "shm1_h8",
        "single_changed_factor": {
            "name": "common_lidar_sensing_rate_hz", "before": 4, "after": 2
        },
        "maps": maps,
        "sensing_rate_hz": SENSING_RATE_HZ,
        "generator_sha256": sha256(Path(__file__)),
    })
    temporary = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, MANIFEST_PATH)
    return manifest


def main() -> None:
    print(json.dumps(generate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
