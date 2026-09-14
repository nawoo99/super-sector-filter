#!/usr/bin/env python3
"""Plot measured XY traces; these plots are not collision certificates."""
import argparse
import csv
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from cylinder_map_search import OUT
from cylinder_solid_campaign import OUT as SOLID_OUT


parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("maps",nargs="+")
parser.add_argument("--solid",action="store_true",help="Use pre-launch actual XYZ observations")
args=parser.parse_args()
for name in args.maps:
    folder=OUT/name
    output=SOLID_OUT/name if args.solid else folder
    cylinders=list(csv.DictReader((folder/"cylinders.csv").open()))
    manifest=json.loads((folder/"manifest.json").read_text())
    fig,ax=plt.subplots(figsize=(8,7))
    for c in cylinders:
        ax.add_patch(Circle((float(c["x"]),float(c["y"])),float(c["r"]),
                           color="#a1a7ad" if c["role"]=="background" else "#6d7278",alpha=.65))
    for mode,color in (("full","#276bb0"),("sector","#d26928"),("adaptive","#189a69")):
        path=(output/f"solid/{name}_run1_{mode}.json" if args.solid else
              folder/f"artifacts/{name}_run1_{mode}.json")
        if not path.exists():continue
        payload=json.loads(path.read_text())
        points=[]
        if args.solid:
            points=[(float(r["x"]),float(r["y"])) for r in csv.DictReader(path.with_suffix(".poses.csv").open())]
        else:
            for row in payload.get("heading_trace",[]):
                points.append(row["position_xy_m"])
                if manifest["parameters"].get("layout")=="slalom" and math.dist(points[-1],(24,24))<1.5:
                    break
        if points:
            ax.plot(*zip(*points),color=color,linewidth=1.5,label=mode)
            ax.scatter(*points[-1],color=color,marker="s",s=22)
        contact=payload.get("first_contact" if args.solid else "first_static_pcd_contact_context")
        if contact and "position" in contact:
            ax.scatter(*contact["position"][:2],s=90,marker="x",color=color)
    if manifest["parameters"].get("layout") in ("loop_slalom","forest"):
        ax.set_xlim(-33,33);ax.set_ylim(-33,33)
    elif manifest["parameters"].get("layout")=="slalom":
        ax.set_xlim(0,24);ax.set_ylim(0,24)
    elif manifest["parameters"].get("layout")=="ring":
        ax.set_xlim(-9,9);ax.set_ylim(-9,9)
    elif manifest["parameters"].get("layout")=="corner_ring":
        ax.set_xlim(15,32);ax.set_ylim(16,32)
    else:
        ax.set_xlim(14,29);ax.set_ylim(17,29)
    ax.set_aspect("equal");ax.grid(alpha=.2);ax.set_xlabel("x (m)");ax.set_ylabel("y (m)")
    ax.set_title(name+": measured XY, exploratory run 1"+(" (pre-launch observer)" if args.solid else ""))
    ax.legend();fig.tight_layout();fig.savefig(output/"flight_paths.png",dpi=150);plt.close(fig)
