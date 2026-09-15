#!/usr/bin/env python3
"""Immutable map-only refinement of an emitted cylinder candidate.

Remove the inner tip of each alternating cylinder row on selected loop legs.
All other cylinders, sensor settings, mission and runtime hashes are preserved.
This uses failed development/confirmation evidence and is explicitly exploratory.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import shutil

import cylinder_map_search as search


def trim_baffle_tips(cylinders, legs, tip_count=1):
    if not legs or len(set(legs)) != len(legs) or any(leg not in range(1, 6) for leg in legs):
        raise ValueError("Specify distinct loop legs 1..5")
    if tip_count not in (1, 2):
        raise ValueError("Trim one or two inner posts per row")
    removed = set()
    details = []
    for leg in legs:
        start, end = search.geometry.LOOP_WAYPOINTS[leg-1:leg+1]
        length = math.dist(start, end)
        ux, uy = (end[0]-start[0])/length, (end[1]-start[1])/length
        rows = {}
        for index, c in enumerate(cylinders):
            if c.role != "loop_baffle":
                continue
            dx, dy = c.x-start[0], c.y-start[1]
            axial, lateral = dx*ux+dy*uy, -dx*uy+dy*ux
            if 8 <= axial <= length-8 and abs(lateral) <= 3.01:
                rows.setdefault(round(axial, 4), []).append((index, lateral))
        if not rows:
            raise ValueError(f"No baffle rows found on leg {leg}")
        for axial, members in sorted(rows.items()):
            if len(members) != 5:
                raise ValueError("Refine an untrimmed five-post row, not an already trimmed row")
            occupied_side = math.copysign(1, sum(lateral for _, lateral in members))
            tips = sorted(members, key=lambda item: occupied_side*item[1])[:tip_count]
            for index, _ in tips:
                if index in removed:
                    raise ValueError("Ambiguous leg ownership")
                removed.add(index)
                details.append(dict(parent_index=index, leg=leg, axial_m=axial,
                                    cylinder=list(cylinders[index])))
    kept = [c for index, c in enumerate(cylinders) if index not in removed]
    return kept, details


def emit(parent_name, name, legs, tip_count):
    for value in (parent_name, name):
        if not value.startswith("cyl2_") or not value.replace("_", "").isalnum():
            raise ValueError("Use a generated cyl2_ candidate name")
    geometry = search.geometry
    parent_dir, output = search.OUT/parent_name, search.OUT/name
    parent_manifest = parent_dir/"manifest.json"
    parent = json.loads(parent_manifest.read_text())
    if parent["policy"] != search.frozen_policy():
        raise RuntimeError("Runtime policy changed")
    if any(geometry.sha256(Path(p)) != sha for p, sha in parent["assets"].items()):
        raise RuntimeError("Parent asset changed")
    mirror = search.ROOT/"super_patches/native_seedmap_campaign/mars_uav_sim_perfect_drone_sim"
    pcd, config = geometry.PCD_DIR/f"{name}.pcd", geometry.CONFIG_DIR/f"{name}.yaml"
    targets = (output, pcd, config, mirror/"pcd/seed_maps"/pcd.name, mirror/"config"/config.name)
    if any(p.exists() for p in targets):
        raise RuntimeError("Candidate or mirror exists; never overwrite")
    with (parent_dir/"cylinders.csv").open() as stream:
        original = [geometry.Cylinder(float(c["x"]), float(c["y"]), float(c["r"]), c["role"])
                    for c in csv.DictReader(stream)]
    cylinders, removed = trim_baffle_tips(original, legs, tip_count)
    gates = {key+"_body_clearance_m": search.clearance(parent[key], cylinders)
             for key in ("inbound", "bypass", "rest")}
    gap = min(geometry.surface_gap(a, b) for i, a in enumerate(cylinders) for b in cylinders[i+1:])
    if min(gates.values()) < .35-1e-8 or gap < -1e-8:
        raise RuntimeError("Map geometry preflight failed")
    parent_config = (geometry.CONFIG_DIR/f"{parent_name}.yaml").read_text()
    needle = f'pcd_name: "seed_maps/{parent_name}.pcd"'
    if parent_config.count(needle) != 1:
        raise RuntimeError("Unexpected parent map configuration")
    output.mkdir(parents=True)
    csv_path = output/"cylinders.csv"
    geometry.write_cylinder_csv(csv_path, cylinders)
    points = geometry.write_pcd(pcd, cylinders)
    config.write_text(parent_config.replace(needle, f'pcd_name: "seed_maps/{name}.pcd"'))
    for source, destination in ((pcd, targets[3]), (config, targets[4])):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    manifest = dict(parent)
    witness = next(c for c in reversed(cylinders) if c.role == "loop_baffle")
    manifest.update(name=name, schema="cylinder-map-only-parent-refinement-v1",
                    parameters=dict(parent=parent_name, trim_baffle_legs=legs, tip_count=tip_count),
                    parent_manifest_sha256=geometry.sha256(parent_manifest),
                    refinement=dict(removed=removed, retained_cylinders_unchanged=True,
                                    background_refilled=False, count_change=len(cylinders)-len(original),
                                    selection="exploratory; uses previous flight failure evidence"),
                    cylinder_count=len(cylinders),
                    structural_count=sum(c.role not in ("background", "supplement") for c in cylinders),
                    point_count=points, geometry_gate=gates, minimum_surface_gap_m=gap,
                    monitor_witness=list(witness[:3])+[parent["height_m"]],
                    assets={str(p): geometry.sha256(p) for p in (csv_path, pcd, config)})
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    search.plot(output, cylinders, parent["inbound"]+parent["bypass"][1:]+parent["rest"][1:])
    print(json.dumps({k:manifest[k] for k in ("name", "parameters", "cylinder_count", "refinement",
                                           "geometry_gate", "minimum_surface_gap_m")}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent")
    parser.add_argument("name")
    parser.add_argument("--legs", type=int, nargs="+", required=True)
    parser.add_argument("--tip-count", type=int, default=1)
    args = parser.parse_args()
    emit(args.parent, args.name, args.legs, args.tip_count)


if __name__ == "__main__":
    main()
