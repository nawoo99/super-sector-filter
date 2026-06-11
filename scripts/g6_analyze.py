#!/usr/bin/env python3
# G6 analysis: compare ROG-Map mapping cost with sector filter ON vs OFF.
# Single perf log (fsm/ROG-Map never restarted), segmented by row:
#   ON  = data rows [warmup : LON-1]   (sector_enable=true)
#   OFF = data rows [LON+warmup : end] (sector_enable=false, relaunched mid-run)
# Same drone pose / scene for both => controlled comparison.
import csv
import statistics as st
import sys

LON = int(sys.argv[1]) if len(sys.argv) > 1 else 503   # lines in on.csv (incl header)
WARMUP = int(sys.argv[2]) if len(sys.argv) > 2 else 40
PATH = sys.argv[3] if len(sys.argv) > 3 else "/tmp/g6_full.csv"

rows = list(csv.reader(open(PATH)))
hdr = [h.strip() for h in rows[0]]
data = [[float(x) for x in r] for r in rows[1:] if len(r) == len(hdr) and r[0].strip()]

# data index 0 == file line 2. ON data = file lines 2..LON => data[0 : LON-1].
on = data[WARMUP: LON - 1]
off = data[(LON - 1) + WARMUP:]

col = {h: i for i, h in enumerate(hdr)}
def stat(seg, name):
    v = [r[col[name]] for r in seg]
    return st.mean(v), st.median(v)

print(f"ON frames={len(on)}  OFF frames={len(off)}  (warmup {WARMUP} skipped each)\n")
metrics = ["PointCloudNumber", "Raycast", "Total", "Update_cache", "Inflation", "CacheNumber"]
unit = {"PointCloudNumber": ("pts", 1), "Raycast": ("ms", 1000), "Total": ("ms", 1000),
        "Update_cache": ("ms", 1000), "Inflation": ("ms", 1000), "CacheNumber": ("", 1)}
print(f"{'metric':18s} {'sectorON':>12s} {'sectorOFF':>12s} {'reduction':>11s}")
print("-" * 56)
for m in metrics:
    u, sc = unit[m]
    on_mean, _ = stat(on, m)
    off_mean, _ = stat(off, m)
    red = (1 - on_mean / off_mean) * 100 if off_mean else 0.0
    print(f"{m:18s} {on_mean*sc:10.3f}{u:>2s} {off_mean*sc:10.3f}{u:>2s} {red:9.1f}%")
print("\n(reduction = how much sector ON cuts vs OFF; mapping cost = Raycast+Update_cache+Inflation -> Total)")
