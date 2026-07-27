#!/usr/bin/env python3
"""Convert a gen_world.py obstacle manifest (x,y,r cylinders) into a native
MARSIM-loadable .pcd (ASCII, FIELDS x y z), by sampling each cylinder's surface.
Matches the header format of mars_uav_sim/perfect_drone_sim/pcd/*.pcd exactly.
"""
import sys, math, csv

def convert(csv_path, pcd_path, height=3.0, dz=0.1, ds=0.05):
    obs = []
    with open(csv_path) as f:
        r = csv.DictReader(f)
        for row in r:
            obs.append((float(row['x']), float(row['y']), float(row['r'])))

    pts = []
    for cx, cy, rad in obs:
        n_theta = max(8, int(round((2 * math.pi * rad) / ds)))
        n_z = max(2, int(round(height / dz)))
        for iz in range(n_z + 1):
            z = iz * height / n_z
            for it in range(n_theta):
                th = 2 * math.pi * it / n_theta
                pts.append((cx + rad * math.cos(th), cy + rad * math.sin(th), z))

    n = len(pts)
    with open(pcd_path, 'w') as f:
        f.write("# .PCD v0.7 - Point Cloud Data file format\n")
        f.write("VERSION 0.7\n")
        f.write("FIELDS x y z\n")
        f.write("SIZE 4 4 4\n")
        f.write("TYPE F F F\n")
        f.write("COUNT 1 1 1\n")
        f.write(f"WIDTH {n}\n")
        f.write("HEIGHT 1\n")
        f.write("VIEWPOINT 0 0 0 1 0 0 0\n")
        f.write(f"POINTS {n}\n")
        f.write("DATA ascii\n")
        for x, y, z in pts:
            f.write(f"{x:.4f} {y:.4f} {z:.4f}\n")
    print(f"{csv_path} ({len(obs)} obstacles) -> {pcd_path} ({n} points)")

if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
