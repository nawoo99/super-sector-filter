#!/usr/bin/env python3
"""Plot measured XY traces; these plots are not collision certificates."""
import csv
import json
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from cylinder_map_search import OUT


for name in sys.argv[1:]:
    folder=OUT/name
    cylinders=list(csv.DictReader((folder/"cylinders.csv").open()))
    manifest=json.loads((folder/"manifest.json").read_text())
    fig,ax=plt.subplots(figsize=(8,7))
    for c in cylinders:
        ax.add_patch(Circle((float(c["x"]),float(c["y"])),float(c["r"]),
                           color="#a1a7ad" if c["role"]=="background" else "#6d7278",alpha=.65))
    for mode,color in (("full","#276bb0"),("sector","#d26928"),("adaptive","#189a69")):
        path=folder/f"artifacts/{name}_run1_{mode}.json"
        if not path.exists():continue
        payload=json.loads(path.read_text())
        points=[]
        for row in payload.get("heading_trace",[]):
            points.append(row["position_xy_m"])
            if manifest["parameters"].get("layout")=="slalom" and math.dist(points[-1],(24,24))<1.5:
                break
        if points:
            ax.plot(*zip(*points),color=color,linewidth=1.5,label=mode)
        contact=payload.get("first_static_pcd_contact_context")
        if contact and "position" in contact:
            ax.scatter(*contact["position"][:2],s=90,marker="x",color=color)
    if manifest["parameters"].get("layout")=="slalom":
        ax.set_xlim(0,24);ax.set_ylim(0,24)
    else:
        ax.set_xlim(14,29);ax.set_ylim(17,29)
    ax.set_aspect("equal");ax.grid(alpha=.2);ax.set_xlabel("x (m)");ax.set_ylabel("y (m)")
    ax.set_title(name+": measured XY, exploratory run 1")
    ax.legend();fig.tight_layout();fig.savefig(folder/"flight_paths.png",dpi=150);plt.close(fig)
