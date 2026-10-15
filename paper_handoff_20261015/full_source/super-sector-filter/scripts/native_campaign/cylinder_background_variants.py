#!/usr/bin/env python3
"""Five predeclared map-only variants of K01; no flight policy changes.

Keep every parent background/perimeter post and rail. Only interior feature
cylinders change. Offline routes are geometric witnesses, never planner inputs.
These related, outcome-guided exploration maps are not independent holdouts.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import shutil

import cylinder_map_search as search
import cylinder_forest_geometry as routes

PARENT = "cyl2_k01"
RECIPES = [
    dict(name="cyl2_k02", kind="restored_baffles", radius=.4, pitch=5.),
    dict(name="cyl2_k03", kind="larger_baffles", radius=.48, pitch=5.),
    dict(name="cyl2_k04", kind="closer_baffles", radius=.4, pitch=4.),
    dict(name="cyl2_k05", kind="large_slalom", radius=1.3, pitch=5.),
    dict(name="cyl2_k06", kind="corner_posts", radius=1.2, forward=3.5),
]
BACKGROUND_ROLES = {"background", "supplement", "perimeter_background"}


def read_cylinders(path):
    with path.open() as stream:
        return [search.geometry.Cylinder(float(r['x']), float(r['y']), float(r['r']), r['role'])
                for r in csv.DictReader(stream)]


def variant(parent, recipe):
    if recipe not in RECIPES:
        raise ValueError("Use an unmodified predeclared recipe")
    g = search.geometry
    if recipe['kind'] == 'corner_posts':
        features = []
        for start, end in zip(g.LOOP_WAYPOINTS[1:5], g.LOOP_WAYPOINTS[2:6]):
            distance = math.dist(start, end)
            x, y = (a + recipe['forward']*(b-a)/distance for a,b in zip(start,end))
            features.append(g.Cylinder(x,y,recipe['radius'],'corner_blind_post'))
        return [*parent,*features], features
    fixed = [c for c in parent if c.role != 'loop_baffle']
    if recipe['kind'] == 'large_slalom':
        structure, _ = search.loop_slalom(.4, recipe['radius'], 2.8, False, recipe['pitch'])
        features = [c for c in structure if c.role == 'loop_slalom']
    else:
        structure, _ = search.loop_baffles(recipe['radius'], recipe['pitch'], 2.8)
        features = [c for c in structure if c.role == 'loop_baffle']
    return [*fixed,*features], features


def inspect_geometry(parent, recipe):
    cylinders, features = variant(parent, recipe)
    if [c for c in cylinders if c.role in BACKGROUND_ROLES] != [c for c in parent if c.role in BACKGROUND_ROLES]:
        raise ValueError("Background must remain unchanged")
    gap = min(search.geometry.surface_gap(a,b) for i,a in enumerate(cylinders) for b in cylinders[i+1:])
    if gap < -1e-8:
        raise ValueError(f"Overlapping cylinders: minimum surface gap {gap}")
    paths = routes.paths(cylinders)
    clearances = [search.clearance(path,cylinders) for path in paths]
    if min(clearances) < .35-1e-8:
        raise ValueError("No adequate geometric detour witness")
    return cylinders, features, paths, gap, clearances


def emit(recipe):
    g = search.geometry
    parent_dir = search.OUT/PARENT
    parent_manifest = parent_dir/'manifest.json'
    parent = json.loads(parent_manifest.read_text())
    if parent['policy'] != search.frozen_policy():
        raise RuntimeError('Runtime policy changed')
    if any(g.sha256(Path(p)) != h for p,h in parent['assets'].items()):
        raise RuntimeError('Parent asset changed')
    name = recipe['name']; out = search.OUT/name
    mirror = search.ROOT/'super_patches/native_seedmap_campaign/mars_uav_sim_perfect_drone_sim'
    pcd = g.PCD_DIR/f'{name}.pcd'; config = g.CONFIG_DIR/f'{name}.yaml'
    targets = [out,pcd,config,mirror/'pcd/seed_maps'/pcd.name,mirror/'config'/config.name]
    if any(p.exists() for p in targets):
        raise RuntimeError('Candidate already exists; never overwrite')
    original = read_cylinders(parent_dir/'cylinders.csv')
    cylinders,features,paths,gap,clearances = inspect_geometry(original,recipe)
    source_config = (g.CONFIG_DIR/f'{PARENT}.yaml').read_text()
    needle = f'pcd_name: "seed_maps/{PARENT}.pcd"'
    if source_config.count(needle) != 1:
        raise RuntimeError('Unexpected parent sensor config')
    out.mkdir(parents=True)
    table = out/'cylinders.csv'; g.write_cylinder_csv(table,cylinders)
    count = g.write_pcd(pcd,cylinders)
    config.write_text(source_config.replace(needle,f'pcd_name: "seed_maps/{name}.pcd"'))
    for source,target in [(pcd,targets[3]),(config,targets[4])]:
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)
    # Explicit allowlist: do not inherit stale parent feature/refinement fields.
    manifest = dict(schema='fixed-background-interior-cylinders-v1',name=name,
        parameters=dict(parent=PARENT,recipe=recipe),parent_manifest_sha256=g.sha256(parent_manifest),
        height_m=parent['height_m'],cylinder_count=len(cylinders),point_count=count,
        structural_count=sum(c.role not in BACKGROUND_ROLES for c in cylinders),
        background_count=sum(c.role in BACKGROUND_ROLES for c in cylinders),
        perimeter_count=sum(c.role=='perimeter_background' for c in cylinders),
        background_and_rails_preserved=True,sensor_faults=False,
        selection='predeclared exploratory family after K01 all-mode success; not held-out validation',
        inbound=paths[0],bypass=paths[1],rest=[paths[2][0],*[q for path in paths[2:] for q in path[1:]]],
        geometry_gate=dict(per_leg_body_clearance_m=clearances,minimum_body_clearance_m=min(clearances)),
        geometric_witness_not_dynamic_certificate=True,minimum_surface_gap_m=gap,
        monitor_witness=list(features[0][:3])+[parent['height_m']],
        trajectory_witness_scope='one first feature cylinder; not an all-map trajectory risk audit',
        assets={str(p):g.sha256(p) for p in (table,pcd,config)},policy=parent['policy'])
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    route = [paths[0][0],*[q for path in paths for q in path[1:]]]
    search.plot(out,cylinders,route)
    return {k:manifest[k] for k in ('name','parameters','cylinder_count','point_count',
                                  'perimeter_count','minimum_surface_gap_m','geometry_gate')}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--map',choices=[r['name'] for r in RECIPES])
    args=parser.parse_args()
    for recipe in RECIPES:
        if args.map and args.map != recipe['name']: continue
        if args.dry_run:
            original=read_cylinders(search.OUT/PARENT/'cylinders.csv')
            cs,_,_,gap,clearances=inspect_geometry(original,recipe)
            print(json.dumps(dict(recipe=recipe,count=len(cs),minimum_gap=gap,clearances=clearances)),flush=True)
        else:
            print(json.dumps(emit(recipe)),flush=True)
