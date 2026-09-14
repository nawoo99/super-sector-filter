#!/usr/bin/env python3
"""Map-only exploratory search. Never changes runtime planner/filter settings.

Every emitted candidate and every flight is immutable; development results are
not confirmatory evidence. Existing v1 and wall/dropout datasets stay untouched.
"""
from __future__ import annotations

import argparse
import csv
import inspect
import json
import math
import random
from pathlib import Path
import shutil

import gen_cylinder_only_stress as geometry
import native_campaign as campaign
from analyze_cylinder_only_stress_full_gate import quality_valid, contact_free, boolean

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/cylinder_map_search_20260914"
PROFILES = {
    "full": "static_seedmaps_guard_viability_tight_v7.yaml",
    "sector": "static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml",
    "adaptive": "static_seedmaps_guard_viability_tight_v7_frontend_risk_enforce.yaml",
}
OPTIONS = dict(
    attempt_max=1, seedmap_static_pcd=True, loop_timeout_override=180,
    filter_profile="strict-burst", filter_backend="cpp-frontend",
    filter_half_angle_deg=45, adaptive_max_publish_hz=5,
    adaptive_risk_max_eval_hz=5, adaptive_risk_body_clearance_m=0.20,
    adaptive_risk_body_horizon_s=0.15, adaptive_risk_body_max_odom_age_s=0.20,
    filtered_reliable_map_link=True, full_sensor_intra_process=True,
    cgroup_cpu_accounting=True, optimizer_phase_memory_trace=True,
    resource_preflight_min_available_mib=7168,
)


def frozen_policy():
    runtime = geometry.SUPER_ROOT
    paths = set()
    for package in ("super_planner", "mission_planner", "rog_map",
                    "mars_uav_sim/perfect_drone_sim"):
        for folder in ("src", "include", "launch"):
            base = runtime / package / folder
            paths.update(p for p in base.rglob("*") if p.is_file()
                         and "__pycache__" not in str(p))
    paths.update(runtime / "super_planner/config" / name
                 for name in PROFILES.values())
    paths.update((runtime / "mission_planner/config").rglob("loop24.txt"))
    paths.add(Path(campaign.__file__))
    for name in ("fsm_node", "perfect_drone_full_node", "perfect_drone_frontend_node"):
        paths.update(Path("/root/super_ws/install").rglob(name))
    defaults = {k: v.default for k, v in inspect.signature(campaign.run_one).parameters.items()
                if v.default is not inspect.Parameter.empty}
    return {"profiles": PROFILES, "options": {**defaults, **OPTIONS},
            "sha256": {str(p): geometry.sha256(p) for p in sorted(paths)}}


def clearance(path, cylinders):
    return min(geometry.point_segment_distance((c.x, c.y), a, b) - c.radius - .2
               for a, b in zip(path, path[1:]) for c in cylinders)


def loop_slalom(radius, feature_radius, lateral, disjoint_posts=False):
    """Static posts along all five legs; returned paths are certificates only."""
    structure, paths = [], []
    for start, end in zip(geometry.LOOP_WAYPOINTS, geometry.LOOP_WAYPOINTS[1:]):
        length = math.dist(start, end)
        ux, uy = ((end[0]-start[0])/length, (end[1]-start[1])/length)
        def xy(s, l):
            return (start[0]+ux*s-uy*l, start[1]+uy*s+ux*l)
        for side in (-1, 1):
            for i in range(int(length-14)+1):
                structure.append(geometry.Cylinder(*xy(7+i, side*3.8), radius, "loop_rail"))
        path = [start, xy(6, 0)]
        for i in range(int((length-20)/7)+1):
            s = 10+7*i
            structure.append(geometry.Cylinder(*xy(s, 1.1*(-1)**i), feature_radius, "loop_slalom"))
            path.append(xy(s, -lateral*(-1)**i))
        path.extend((xy(length-6, 0), end))
        paths.append(path)
    if disjoint_posts:
        kept = [c for c in structure if c.role=="loop_slalom"]
        for c in structure:
            if c.role=="loop_rail" and not geometry.conflicts(c, kept, .15):
                kept.append(c)
        structure = kept
    return structure, paths


def create(args):
    folder = OUT / args.name
    if folder.exists() or (geometry.CONFIG_DIR / f"{args.name}.yaml").exists():
        raise ValueError("Candidate already exists: use a new name, never overwrite")
    r = args.radius
    custom_rest = None
    if args.layout=="corner":
        inner_end = min(args.closure_x,args.inner_end)
        structure = geometry.chain_axis(21.35, inner_end, 6, r, "inner_row")
        structure += geometry.chain_axis(26.65, 6, 26.65, r, "outer_row")
        closure = geometry.chain_axis(args.closure_x, args.closure_base, args.closure_top,
                                       r, "closure", vertical=True)
        structure += closure[1:] if args.closure_base==21.35 and inner_end==args.closure_x else closure
        bypass = [(24.,24.), (23.,args.bypass_y), (args.closure_x+1.0,args.bypass_y),
                  (args.closure_x-1.2,args.bypass_y), (args.closure_x-2.5,24.)]
        inbound = [(0.,0.),(24.,24.)]
    elif args.layout=="slalom":
        def xy(s,l): return ((s-l)/math.sqrt(2),(s+l)/math.sqrt(2))
        structure = []
        for side in (-1,1):
            for i in range(23):
                structure.append(geometry.Cylinder(*xy(5+i,side*3.8),r,"rail"))
        for i,s in enumerate((12,18,24)):
            structure.append(geometry.Cylinder(*xy(s,1.1*(-1)**i),
                                               args.feature_radius,"slalom"))
        lateral = args.slalom_offset
        inbound = [(0.,0.),xy(6,0),xy(12,-lateral),xy(18,lateral),xy(24,-lateral),xy(30,0),(24.,24.)]
        bypass = [(24.,24.),(17.,24.)]
    elif args.layout=="loop_slalom":
        structure, paths = loop_slalom(r, args.feature_radius, args.slalom_offset, args.disjoint_posts)
        inbound, bypass = paths[:2]
        custom_rest = [paths[2][0]] + [p for path in paths[2:] for p in path[1:]]
    elif args.layout=="forest":
        import cylinder_forest_geometry as forest_geometry
        structure = forest_geometry.forest(args.source_seed, r, args.count, args.clear_pocket)
        if args.forest_rotation_deg:
            angle = math.radians(args.forest_rotation_deg)
            cosine, sine = round(math.cos(angle)), round(math.sin(angle))
            structure = [geometry.Cylinder(c.x*cosine-c.y*sine, c.x*sine+c.y*cosine,
                                           c.radius, c.role) for c in structure]
        try:
            paths = forest_geometry.paths(structure)
        except ValueError as error:
            folder.mkdir(parents=True)
            geometry.write_cylinder_csv(folder/"cylinders.csv",structure)
            (folder/"design_rejection.json").write_text(json.dumps({
                "parameters":vars(args),"reason":str(error),"flown":False,
                "policy":frozen_policy()},indent=2)+"\n")
            raise
        inbound, bypass = paths[:2]
        custom_rest = [paths[2][0]] + [p for path in paths[2:] for p in path[1:]]
    elif args.layout=="culdesac":
        # A cylinder-post U, open to the east. Unlike the corner layout, the
        # west closure joins BOTH rails: recovery requires leaving the pocket.
        lower, upper = 24-args.u_half_width, 24+args.u_half_width
        structure = geometry.chain_axis(lower, args.closure_x, args.inner_end, r, "u_rail")
        structure += geometry.chain_axis(upper, args.closure_x, args.inner_end, r, "u_rail")
        for c in geometry.chain_axis(args.closure_x, lower, upper, r, "u_closure", vertical=True):
            if not any(math.dist(c[:2], other[:2])<1e-8 for other in structure):
                structure.append(c)
        inbound=[(0.,0.),(24.5,20.),(25.,22.),(24.,24.)]
        bypass=[(24.,24.),(24.5,upper+1.2),(args.closure_x-1.5,upper+1.2),(args.closure_x-1.5,24.)]
        custom_rest=[bypass[-1],(-24.,24.),(-24.,-24.),(24.,-24.),(0.,0.)]
    elif args.layout=="corner_ring":
        low,high=args.ring_gap
        angle=math.radians((low+high)/2)
        structure=[geometry.Cylinder(24+args.ring_radius*math.cos(math.radians(a)),
                     24+args.ring_radius*math.sin(math.radians(a)),r,"corner_ring")
                   for a in range(0,360,12) if not low<=a<=high
                   and not any(lo<=a<=hi for lo,hi in args.ring_extra_gap)]
        exit_point=(24+(args.ring_radius+3)*math.cos(angle),
                    24+(args.ring_radius+3)*math.sin(angle))
        inbound=[(0.,0.),(24.,24.)]
        bypass=[(24.,24.),exit_point,(18.,exit_point[1]),(17.,24.)]
        ring_return=[(0.,0.)]
    else:
        # Static cylindrical enclosure; openings are map-only parameters.
        # Goal and mission are unchanged; Full must first prove this is flyable.
        low,high=args.ring_gap
        angle=math.radians((low+high)/2)
        ring_exit=((args.ring_radius+3)*math.cos(angle),(args.ring_radius+3)*math.sin(angle))
        structure = [geometry.Cylinder(args.ring_radius*math.cos(math.radians(a)),
                         args.ring_radius*math.sin(math.radians(a)),r,"ring")
                     for a in range(0,360,12) if not low<=a<=high
                     and not any(lo<=a<=hi for lo,hi in args.ring_extra_gap)]
        inbound = ([(0.,0.),ring_exit,(-7.,-4.),(-7.,7.),(7.,7.),(24.,24.)]
                   if ring_exit[1]<0 else [(0.,0.),ring_exit,(-5.,7.),(7.,7.),(24.,24.)])
        ring_return=([(0.,-8.),ring_exit,(0.,0.)] if ring_exit[1]<0
                     else [(9.,9.),(-5.,7.),ring_exit,(0.,0.)])
        if args.ring_return_angle is not None:
            return_angle=math.radians(args.ring_return_angle)
            return_entry=((args.ring_radius+3)*math.cos(return_angle),
                          (args.ring_radius+3)*math.sin(return_angle))
            ring_return=[(0.,-8.),return_entry,(0.,0.)]
        bypass = [(24.,24.),(17.,24.)]
    for x,y,post_radius in args.extra_post:
        if post_radius<=0: raise ValueError("Post radius must be positive")
        structure.append(geometry.Cylinder(x,y,post_radius,"side_post"))
    if args.inbound_via:
        # Geometry certificate only: runtime mission stays the original loop24.
        inbound = [(0.,0.),*map(tuple,args.inbound_via),(24.,24.)]
    if args.count<len(structure):
        raise ValueError("Cylinder count is smaller than structural count")
    source = geometry.load_source(5, .4)
    retained = [geometry.Cylinder(c.x, c.y, r, "background") for c in source]
    retained = [c for c in retained if geometry.route_surface_distance(c) > 2
                and not geometry.protected_location(c)
                and not geometry.conflicts(c, structure, 1)]
    if args.layout in ("ring","corner_ring","loop_slalom","culdesac"):
        certificate = (inbound + bypass[1:] + custom_rest[1:] if custom_rest else
                       inbound + bypass[1:] + [(-24.,24.),(-24.,-24.),(24.,-24.),*ring_return])
        def admissible(c):
            return min(geometry.point_segment_distance((c.x,c.y),a,b)-c.radius
                       for a,b in zip(certificate,certificate[1:]))>1.0
        background=[c for c in retained if admissible(c)][:args.count-len(structure)]
        rng=random.Random(0xC7110005)
        for _ in range(100000):
            if len(background)==args.count-len(structure):break
            c=geometry.Cylinder(rng.uniform(-31,31),rng.uniform(-31,31),r,"supplement")
            if (admissible(c) and not geometry.protected_location(c)
                    and geometry.route_surface_distance(c)>2
                    and not geometry.conflicts(c,structure+background,1)):
                background.append(c)
        if len(background)!=args.count-len(structure):raise ValueError("Background refill exhausted")
    else:
        background = geometry.refill_background(retained[:args.count-len(structure)],
                        structure, r, 5, args.count-len(structure))
    cylinders = background + structure
    # Analytic centerline feasibility, including the previously missed inbound.
    # Not a claim about a dynamically executable SUPER trajectory.
    rest = [bypass[-1], (-24.,24.),(-24.,-24.),(24.,-24.),(0.,0.)]
    if args.layout in ("ring","corner_ring"):
        rest = [bypass[-1],(-24.,24.),(-24.,-24.),(24.,-24.),*ring_return]
    if custom_rest is not None:
        rest = custom_rest
    gates = {"inbound_body_clearance_m": clearance(inbound,cylinders),
             "bypass_body_clearance_m": clearance(bypass,cylinders),
             "rest_body_clearance_m": clearance(rest,cylinders)}
    if min(gates.values()) < .35 - 1e-9:
        raise ValueError(f"Analytic route infeasible: {gates}")
    folder.mkdir(parents=True)
    csv_path = folder / "cylinders.csv"
    pcd_path = geometry.PCD_DIR / f"{args.name}.pcd"
    config_path = geometry.CONFIG_DIR / f"{args.name}.yaml"
    geometry.write_cylinder_csv(csv_path,cylinders)
    points = geometry.write_pcd(pcd_path,cylinders)
    geometry.write_config(config_path,args.name)
    mirror = ROOT / "super_patches/native_seedmap_campaign/mars_uav_sim_perfect_drone_sim"
    for original, target in ((pcd_path,mirror/"pcd/seed_maps"/pcd_path.name),
                             (config_path,mirror/"config"/config_path.name)):
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(original,target)
    manifest = {"schema":"cylinder-map-only-exploration-v2", "name":args.name,
                "parameters":vars(args), "cylinder_count":len(cylinders),
                "structural_count":len(structure), "height_m":3.0,
                "point_count":points, "sensor_faults":False,
                "inbound":inbound,"bypass":bypass,"rest":rest, "geometry_gate":gates,
                "monitor_witness":list(next(c for c in reversed(structure)
                                  if c.role in (("closure",) if args.layout=="corner"
                                               else ("slalom","side_post","ring","corner_ring","loop_slalom","u_closure","forest"))))[:3]+[3.0],
                "assets":{str(p):geometry.sha256(p) for p in (csv_path,pcd_path,config_path)},
                "policy":frozen_policy()}
    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    plot(folder,cylinders,inbound+bypass[1:]+rest[1:])
    print(json.dumps({k:v for k,v in manifest.items() if k not in ("policy","assets")},indent=2))


def plot(folder,cylinders,route):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    fig,axes = plt.subplots(1,2,figsize=(13,6))
    for ax in axes:
        for c in cylinders:
            ax.add_patch(Circle((c.x,c.y),c.radius,
                         color="#c65332" if c.role!="background" else "#687985"))
        ax.plot(*zip(*route),"--",color="#188666",linewidth=1,label="Analytic feasible centerline")
        ax.scatter(*zip(*geometry.LOOP_WAYPOINTS),color="black",s=15)
        ax.set_aspect("equal"); ax.grid(alpha=.2); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    axes[0].set_xlim(-33,33); axes[0].set_ylim(-33,33)
    if any(c.role=="corner_ring" for c in cylinders):
        axes[1].set_xlim(15,32); axes[1].set_ylim(16,32)
    elif any(c.role=="ring" for c in cylinders):
        axes[1].set_xlim(-9,9); axes[1].set_ylim(-9,9)
    elif any(c.role in ("slalom","loop_slalom") for c in cylinders):
        axes[1].set_xlim(0,24); axes[1].set_ylim(0,24)
    else:
        axes[1].set_xlim(14,29); axes[1].set_ylim(17,29)
    axes[0].set_title(folder.name+": cylinders only; loop24; nominal 10 Hz")
    axes[1].set_title("Stress geometry detail (no planner modifications)")
    fig.tight_layout(); fig.savefig(folder/"layout.png",dpi=150); plt.close(fig)


def fly(args):
    folder = OUT / args.name
    manifest = json.loads((folder/"manifest.json").read_text())
    if frozen_policy() != manifest["policy"]:
        raise ValueError("Frozen algorithm/config/binary hash changed; refusing flight")
    if any(geometry.sha256(Path(p))!=sha for p,sha in manifest["assets"].items()):
        raise ValueError("Candidate assets changed; refusing flight")
    # Physical map preflight, not a runtime planner/metric change. Distinct
    # vertical cylinders may form a close row but must not overlap in XY.
    cylinders = [geometry.Cylinder(float(r["x"]),float(r["y"]),float(r["r"]),r["role"])
                 for r in csv.DictReader((folder/"cylinders.csv").open())]
    overlap = next(((a,b,geometry.surface_gap(a,b)) for i,a in enumerate(cylinders)
                    for b in cylinders[i+1:] if geometry.surface_gap(a,b)<-1e-8), None)
    if overlap:
        rejection = {"decision":"REJECT_GEOMETRY_OVERLAPPING_POSTS", "witness":overlap,
                     "flown":False, "note":"Retain candidate; redesign under a new name"}
        (folder/"geometry_rejection.json").write_text(json.dumps(rejection,indent=2)+"\n")
        raise ValueError("Distinct static cylinders overlap; candidate retained, flight refused")
    # Read-only trajectory/heading diagnostics about one actual cylinder.
    # No filter probe, synthetic bounding disc or runtime algorithm change.
    if "monitor_witness" in manifest:
        original_monitor_command = campaign.build_loop_monitor_command
        x,y,r,h = manifest["monitor_witness"]
        def observed_monitor(wps,switch,timeout,out_json,monitor_options=""):
            monitor_options += (f" --trajectory-risk-audit --trajectory-audit-center-x {x}"
                f" --trajectory-audit-center-y {y} --trajectory-audit-radius-m {r}"
                f" --trajectory-audit-height-m {h}")
            return original_monitor_command(wps,switch,timeout,out_json,monitor_options)
        campaign.build_loop_monitor_command = observed_monitor
    raw = folder/"raw.csv"
    rows = list(csv.DictReader(raw.open())) if raw.exists() else []
    existing = {(int(r["run"]),r["mode"]) for r in rows}
    campaign.install_campaign_signal_handlers()
    with raw.open("a",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=campaign.FIELDS,extrasaction="ignore")
        if not rows: writer.writeheader(); stream.flush()
        try:
            for run in range(args.first_run,args.first_run+args.runs):
                modes = list(args.modes)
                if args.rotate:
                    offset = (run-args.first_run)%len(modes)
                    modes = modes[offset:]+modes[:offset]
                for mode in modes:
                    if (run,mode) in existing:
                        raise ValueError("This flight already exists; never overwrite or select a retry")
                    rec = campaign.run_one(args.name,mode,run,**OPTIONS,
                          artifacts_dir=str(folder/"artifacts"),
                          seedmap_super_config_override=PROFILES[mode])
                    writer.writerow(rec); stream.flush()
                    print("SEARCH_RESULT "+json.dumps(rec),flush=True)
                    if frozen_policy()!=manifest["policy"]:
                        raise RuntimeError("Algorithm changed during flight")
                    if args.full_gate and mode=="full" and not (
                        boolean(rec.get("success")) and contact_free(rec)
                        and quality_valid(rec)):
                        print("FULL_GATE_STOP: inspect all evidence before next candidate",flush=True)
                        return
        finally:
            campaign.cleanup_active_process_groups()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command",required=True)
    gen = sub.add_parser("create")
    gen.add_argument("name"); gen.add_argument("--radius",type=float,default=.4)
    gen.add_argument("--count",type=int,default=300)
    gen.add_argument("--closure-x",type=float,default=19.5)
    gen.add_argument("--closure-top",type=float,default=24.35)
    gen.add_argument("--closure-base",type=float,default=21.35)
    gen.add_argument("--inner-end",type=float,default=19.5)
    gen.add_argument("--bypass-y",type=float,default=25.3,
                     help="Analytic certificate only; not mission waypoints")
    gen.add_argument("--layout",choices=("corner","slalom","ring","corner_ring","loop_slalom","culdesac","forest"),default="corner")
    gen.add_argument("--ring-radius",type=float,default=4.5)
    gen.add_argument("--ring-gap",nargs=2,type=float,default=[210,240])
    gen.add_argument("--ring-extra-gap",nargs=2,type=float,action="append",default=[])
    gen.add_argument("--ring-return-angle",type=float,default=None,
                     help="Analytic certificate only; not mission waypoints")
    gen.add_argument("--feature-radius",type=float,default=1.5)
    gen.add_argument("--slalom-offset",type=float,default=1.8)
    gen.add_argument("--disjoint-posts",action="store_true",
                     help="Prune overlapping rail posts at loop junctions; map geometry only")
    gen.add_argument("--u-half-width",type=float,default=3.)
    gen.add_argument("--source-seed",type=int,choices=range(1,11),default=9)
    gen.add_argument("--forest-rotation-deg",type=int,choices=(0,90,180,270),default=0,
                     help="Rotate only cylinder XY locations around origin before offline feasibility checks")
    gen.add_argument("--clear-pocket",nargs=3,type=float,action="append",default=[],
                     metavar=("X","Y","CLEAR_RADIUS"),
                     help="Map-only local cylinder relocation; never alters runtime goals")
    gen.add_argument("--extra-post",nargs=3,type=float,action="append",default=[],
                     metavar=("X","Y","RADIUS"))
    gen.add_argument("--inbound-via",nargs=2,type=float,action="append",default=[],
                     metavar=("X","Y"),help="Analytic certificate only; not mission waypoints")
    run = sub.add_parser("fly")
    run.add_argument("name"); run.add_argument("--modes",nargs="+",choices=tuple(PROFILES),default=list(PROFILES))
    run.add_argument("--runs",type=int,default=1); run.add_argument("--first-run",type=int,default=1)
    run.add_argument("--rotate",action="store_true"); run.add_argument("--full-gate",action="store_true")
    args = parser.parse_args()
    if not args.name.startswith("cyl2_") or not args.name.replace("_","").isalnum():
        parser.error("Use a new cyl2_ alphanumeric candidate name")
    if args.command=="create":
        if args.radius<=0 or args.count<60: parser.error("Invalid geometry")
        create(args)
    else:
        if args.runs<1 or args.first_run<1: parser.error("Run indices must be positive")
        fly(args)


if __name__=="__main__": main()
