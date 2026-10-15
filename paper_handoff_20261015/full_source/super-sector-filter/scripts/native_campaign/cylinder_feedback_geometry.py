#!/usr/bin/env python3
"""Immutable cylinder-only feedback redesign. Never edits flight code/settings."""
import argparse
import csv
import json
import math
from pathlib import Path
import shutil

import cylinder_map_search as search
import cylinder_forest_geometry as routes
from cylinder_background_variants import read_cylinders, BACKGROUND_ROLES

FEATURE_ROLES={'loop_baffle','loop_slalom','corner_blind_post'}
PROTECTED_ROLES=BACKGROUND_ROLES|{'origin_background','recovery_background'}


def add_observability(cylinders,centers=((0.,0.),),ring_radius=8.):
    """Static sparse posts, not a renderer visibility guarantee or fake return."""
    g=search.geometry;kept=list(cylinders);added=[]
    for center in centers:
        for degrees in range(0,360,20):
            angle=math.radians(degrees)
            c=g.Cylinder(center[0]+ring_radius*math.cos(angle),
                         center[1]+ring_radius*math.sin(angle),.4,
                         'origin_background' if center==(0.,0.) else 'recovery_background')
            if (max(abs(c.x),abs(c.y))>30.5 or math.hypot(c.x,c.y)-c.radius<3.
                    or min(math.dist(c[:2],w)-c.radius for w in g.LOOP_WAYPOINTS[1:5])<2.5
                    or g.route_surface_distance(c)<1.5 or g.conflicts(c,kept,.2)):
                continue
            kept.append(c);added.append(c)
    return kept,added


def open_escape(cylinders,position,radius=4.):
    # A map opening at an observed planning dead end, not a new runtime waypoint.
    removed=[c for c in cylinders if c.role not in PROTECTED_ROLES
             and math.dist(c[:2],position[:2])<=radius]
    return [c for c in cylinders if c not in removed],removed


def harden(cylinders,iteration):
    """Low-discrepancy interior alternatives; same perimeter, mission and sensor."""
    # Rebuild internal features, not accumulated radius growth with no new maps.
    g=search.geometry
    u=(iteration*.6180339887498949)%1
    v=(iteration*.4142135623730951)%1
    pitch=round(3.5+3*u,3)
    radius=round(.32+.17*v,3)
    fixed=[c for c in cylinders if c.role not in FEATURE_ROLES]
    if iteration%3==0:
        feature_radius=round(.9+.8*v,3)
        structure,_=search.loop_slalom(.4,feature_radius,2.8,False,pitch,round(.6+.9*u,3))
        features=[c for c in structure if c.role=='loop_slalom']
        kind='loop_slalom'
    else:
        structure,_=search.loop_baffles(radius,pitch,2.8)
        features=[c for c in structure if c.role=='loop_baffle']
        feature_radius=radius;kind='loop_baffles'
    # A small deterministic stagger changes headings, not the flight policy.
    accepted=[];skipped=[]
    for c in features:
        if g.conflicts(c,fixed+accepted,.02):skipped.append(c)
        else:accepted.append(c)
    return fixed+accepted,dict(iteration=iteration,pitch=pitch,radius=feature_radius,kind=kind,
                               accepted=len(accepted),skipped=[list(c) for c in skipped])


def transform(original,recipe):
    cylinders,central=add_observability(original)
    change=dict(origin_posts_added=[list(c) for c in central],removed=[],extra_posts_added=[])
    action=recipe.get('action','origin_background')
    if action=='open_escape':
        cylinders,removed=open_escape(cylinders,recipe['position'],recipe.get('escape_radius',4.))
        change['removed']=[list(c) for c in removed]
    elif action=='add_observability':
        cylinders,added=add_observability(cylinders,(tuple(recipe['position'][:2]),),6.)
        change['extra_posts_added']=[list(c) for c in added]
    elif action=='harden':
        cylinders,change['interior_parameters']=harden(cylinders,recipe['iteration'])
    elif action!='origin_background':raise ValueError('Unknown map-only action')
    return cylinders,change


def inspect(recipe):
    original=read_cylinders(search.OUT/recipe['parent']/'cylinders.csv')
    cylinders,change=transform(original,recipe)
    g=search.geometry
    gap=min(g.surface_gap(a,b) for i,a in enumerate(cylinders) for b in cylinders[i+1:])
    if gap < -1e-8:raise ValueError('Overlapping cylinders')
    if cylinders==original:raise ValueError('Recipe changes no geometry')
    paths=routes.paths(cylinders)
    clearances=[search.clearance(path,cylinders) for path in paths]
    if min(clearances)<.35-1e-8:raise ValueError('Geometric route clearance below .35 m')
    return cylinders,change,paths,gap,clearances


def emit(recipe):
    for name in (recipe['name'],recipe['parent']):
        if not name.startswith('cyl2_') or not name.replace('_','').isalnum():raise ValueError('Invalid map name')
    g=search.geometry;parent_file=search.OUT/recipe['parent']/'manifest.json'
    parent=json.loads(parent_file.read_text())
    if parent['policy']!=search.frozen_policy():raise RuntimeError('Frozen policy changed')
    if any(g.sha256(Path(p))!=h for p,h in parent['assets'].items()):raise RuntimeError('Parent asset changed')
    out=search.OUT/recipe['name'];pcd=g.PCD_DIR/f"{recipe['name']}.pcd";config=g.CONFIG_DIR/f"{recipe['name']}.yaml"
    mirror=search.ROOT/'super_patches/native_seedmap_campaign/mars_uav_sim_perfect_drone_sim'
    targets=[out,pcd,config,mirror/'pcd/seed_maps'/pcd.name,mirror/'config'/config.name]
    if any(p.exists() for p in targets):raise RuntimeError('Never overwrite a candidate')
    cylinders,change,paths,gap,clearances=inspect(recipe)
    source=(g.CONFIG_DIR/f"{recipe['parent']}.yaml").read_text()
    needle=f'pcd_name: "seed_maps/{recipe["parent"]}.pcd"'
    if source.count(needle)!=1:raise RuntimeError('Unexpected parent YAML')
    out.mkdir(parents=True);table=out/'cylinders.csv';g.write_cylinder_csv(table,cylinders)
    point_count=g.write_pcd(pcd,cylinders)
    config.write_text(source.replace(needle,f'pcd_name: "seed_maps/{recipe["name"]}.pcd"'))
    for a,b in [(pcd,targets[3]),(config,targets[4])]:
        b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a,b)
    features=[c for c in cylinders if c.role in FEATURE_ROLES]
    witness=features[0] if features else cylinders[0]
    result=dict(schema='cylinder-feedback-redesign-v1',name=recipe['name'],parameters=recipe,
        parent_manifest_sha256=g.sha256(parent_file),selection='outcome-dependent exploration, including n20 selection',
        height_m=parent['height_m'],cylinder_count=len(cylinders),point_count=point_count,
        sensor_faults=False,changes=change,inbound=paths[0],bypass=paths[1],
        rest=[paths[2][0],*[q for path in paths[2:] for q in path[1:]]],
        geometry_gate=dict(per_leg_body_clearance_m=clearances,minimum_body_clearance_m=min(clearances)),
        minimum_surface_gap_m=gap,monitor_witness=list(witness[:3])+[parent['height_m']],
        geometric_route_not_dynamic_certificate=True,trajectory_audit_one_cylinder_only=True,
        assets={str(p):g.sha256(p) for p in (table,pcd,config)},policy=parent['policy'])
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    search.plot(out,cylinders,[paths[0][0],*[q for path in paths for q in path[1:]]])
    return {k:result[k] for k in ('name','cylinder_count','geometry_gate','changes')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent');parser.add_argument('name')
    parser.add_argument('--action',choices=('origin_background','open_escape','add_observability','harden'),default='origin_background')
    parser.add_argument('--position',type=float,nargs=2);parser.add_argument('--iteration',type=int)
    parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    recipe={k:v for k,v in vars(args).items() if k!='dry_run' and v is not None}
    if args.dry_run:
        cs,change,_,gap,clearances=inspect(recipe)
        print(json.dumps(dict(name=args.name,count=len(cs),changes=change,gap=gap,clearances=clearances)))
    else:print(json.dumps(emit(recipe)))
