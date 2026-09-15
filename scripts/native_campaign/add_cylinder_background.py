#!/usr/bin/env python3
"""Add immutable perimeter cylinders; never change flight policy or parent assets."""
import argparse
import csv
import json
import math
from pathlib import Path
import shutil

import cylinder_map_search as search


def perimeter_background(original, half_width=32., pitch=2., radius=.4):
    if not all(math.isfinite(x) and x > 0 for x in (half_width, pitch, radius)):
        raise ValueError("Positive finite perimeter parameters required")
    intervals = round(2*half_width/pitch)
    if not math.isclose(intervals*pitch, 2*half_width):
        raise ValueError("Pitch must divide perimeter side length")
    values = [-half_width+i*pitch for i in range(intervals+1)]
    positions = sorted({(x,y) for x in (-half_width,half_width) for y in values} |
                       {(x,y) for y in (-half_width,half_width) for x in values})
    added, skipped = [], []
    for x,y in positions:
        c = search.geometry.Cylinder(x,y,radius,"perimeter_background")
        if search.geometry.conflicts(c, [*original,*added], .2):
            skipped.append([x,y])
        else:
            added.append(c)
    return [*original,*added], added, skipped


def heading_proxy(cylinders, position, sensing_range=15., half_angle=45.):
    """Center-based XY visibility proxy, not renderer/occlusion/point-return proof."""
    counts = []
    for degrees in range(0,360,5):
        heading = math.radians(degrees)
        count = 0
        for c in cylinders:
            angle = math.atan2(c.y-position[1], c.x-position[0])-heading
            bearing = abs(math.atan2(math.sin(angle),math.cos(angle)))
            count += math.dist(position,c[:2]) <= sensing_range and bearing <= math.radians(half_angle)
        counts.append(count)
    return dict(position=position, yaw_step_deg=5, minimum_center_count=min(counts),
                maximum_center_count=max(counts), sensor_returns_verified=False)


def emit(parent_name, name):
    if any(not n.startswith("cyl2_") or not n.replace("_","").isalnum()
           for n in (parent_name,name)):
        raise ValueError("Use new cyl2_ names")
    g = search.geometry
    parent_dir, output = search.OUT/parent_name, search.OUT/name
    parent_file = parent_dir/"manifest.json"
    parent = json.loads(parent_file.read_text())
    if parent["policy"] != search.frozen_policy():
        raise RuntimeError("Frozen policy mismatch")
    if any(g.sha256(Path(p)) != h for p,h in parent["assets"].items()):
        raise RuntimeError("Parent assets changed")
    mirror = search.ROOT/"super_patches/native_seedmap_campaign/mars_uav_sim_perfect_drone_sim"
    pcd,config = g.PCD_DIR/f"{name}.pcd",g.CONFIG_DIR/f"{name}.yaml"
    targets = [output,pcd,config,mirror/"pcd/seed_maps"/pcd.name,mirror/"config"/config.name]
    if any(p.exists() for p in targets):
        raise RuntimeError("Never overwrite a candidate")
    with (parent_dir/"cylinders.csv").open() as stream:
        original = [g.Cylinder(float(r['x']),float(r['y']),float(r['r']),r['role'])
                    for r in csv.DictReader(stream)]
    cylinders,added,skipped = perimeter_background(original)
    gates = {k+"_body_clearance_m":search.clearance(parent[k],cylinders)
             for k in ("inbound","bypass","rest")}
    if min(gates.values()) < .35-1e-8:
        raise RuntimeError("Existing feasible route obstructed")
    parent_config = (g.CONFIG_DIR/f"{parent_name}.yaml").read_text()
    needle = f'pcd_name: "seed_maps/{parent_name}.pcd"'
    if parent_config.count(needle) != 1:
        raise RuntimeError("Unexpected parent config")
    output.mkdir(parents=True)
    csv_path = output/"cylinders.csv"
    g.write_cylinder_csv(csv_path,cylinders)
    points = g.write_pcd(pcd,cylinders)
    config.write_text(parent_config.replace(needle,f'pcd_name: "seed_maps/{name}.pcd"'))
    for source,target in [(pcd,targets[3]),(config,targets[4])]:
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
    manifest = dict(parent)
    manifest.update(name=name,schema="cylinder-perimeter-background-v1",
        parameters=dict(parent=parent_name,half_width_m=32.,pitch_m=2.,radius_m=.4),
        parent_manifest_sha256=g.sha256(parent_file),cylinder_count=len(cylinders),
        point_count=points,geometry_gate=gates,
        refinement=dict(parent_cylinders_preserved_at_csv_precision=True,added=[list(c) for c in added],
                        skipped_conflicting_centers=skipped,removed=[],count_change=len(added),
                        pcd_regenerated_not_byte_subset=True,
                        selection="Exploratory liveness diagnostic after J05 empty-cloud failure"),
        heading_proxies=[heading_proxy(cylinders,q) for q in [(22.,22.),*g.LOOP_WAYPOINTS[1:5]]],
        assets={str(p):g.sha256(p) for p in (csv_path,pcd,config)})
    manifest["minimum_surface_gap_m"] = min(g.surface_gap(a,b) for i,a in enumerate(cylinders) for b in cylinders[i+1:])
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    search.plot(output,cylinders,parent["inbound"]+parent["bypass"][1:]+parent["rest"][1:])
    print(json.dumps(dict(name=name,parent=parent_name,original=len(original),added=len(added),
                         total=len(cylinders),geometry_gate=gates,skipped=skipped)),flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent"); parser.add_argument("name")
    args = parser.parse_args(); emit(args.parent,args.name)
