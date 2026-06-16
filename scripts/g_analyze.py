#!/usr/bin/env python3
# g_analyze.py  —  Step 5: aggregate the campaign CSV into paper tables
# ---------------------------------------------------------------------
# Reads results/campaign.csv (written by g_campaign.py) and prints, per mode
# (full / sector / adaptive), the mean +/- std of each metric across all runs/seeds,
# plus the headline reductions vs the `full` (360 view) baseline:
#   - ROG-Map mapping cost (Total ms)   -> the efficiency claim
#   - Raycast ms, points, CPU%%
#   - collisions & min clearance        -> the safety cost / adaptive recovery payoff
#
#   python3 g_analyze.py [results/campaign.csv] [--by-seed] [--csv-out tables.csv]
# ---------------------------------------------------------------------
import argparse
import csv
import os
import statistics as st

MODE_ORDER = ["full", "sector", "adaptive"]
# (csv field, label, unit, fewer-is-better)
METRICS = [
    ("mission_time_s", "mission time", "s", True),
    ("frames", "ROG frames", "", False),
    ("pts_mean", "points/frame", "pts", True),
    ("total_ms_mean", "ROG Total", "ms", True),
    ("total_ms_active_mean", "Total actv", "ms", True),
    ("raycast_ms_mean", "Raycast", "ms", True),
    ("raycast_ms_active_mean", "Raycast actv", "ms", True),
    ("update_ms_mean", "Update_cache", "ms", True),
    ("inflation_ms_mean", "Inflation", "ms", True),
    ("fsm_cpu_pct", "fsm_node CPU", "%", True),
    ("cpp_cpu_pct", "preproc CPU", "%", True),
    ("collisions", "collisions", "", True),
    ("min_clearance_m", "min clearance", "m", False),
]


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def agg(rows, field):
    vals = [fnum(r.get(field)) for r in rows]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, None, 0
    mean = st.mean(vals)
    sd = st.pstdev(vals) if len(vals) > 1 else 0.0
    return mean, sd, len(vals)


def fmt(mean, sd):
    if mean is None:
        return "      NA"
    return f"{mean:8.3f}±{sd:.3f}"


def print_table(rows, title, csv_writer=None):
    modes = [m for m in MODE_ORDER if any(r["mode"] == m for r in rows)]
    by = {m: [r for r in rows if r["mode"] == m] for m in modes}
    n = {m: len(by[m]) for m in modes}
    print(f"\n=== {title} ===")
    print(f"  runs per mode: " + ", ".join(f"{m}={n[m]}" for m in modes))
    header = f"{'metric':16s}" + "".join(f"{m:>20s}" for m in modes)
    if "full" in by:
        header += f"{'sector vs full':>16s}{'adapt vs full':>16s}"
    print(header)
    print("-" * len(header))
    base = "full" if "full" in by else None
    for field, label, unit, fewer in METRICS:
        cells = {}
        for m in modes:
            mean, sd, _ = agg(by[m], field)
            cells[m] = mean
            print_cell = fmt(mean, sd)
            if m == modes[0]:
                line = f"{label+' ('+unit+')':16s}" if unit else f"{label:16s}"
            line += f"{print_cell:>20s}"
        # reductions vs full baseline
        red = ""
        if base and cells.get(base):
            for m in ("sector", "adaptive"):
                if m in cells and cells[m] is not None and cells[base]:
                    pct = (1 - cells[m] / cells[base]) * 100
                    red += f"{pct:>15.1f}%"
                elif m in modes:
                    red += f"{'NA':>16s}"
        print(line + red)
        if csv_writer:
            row = {"metric": label, "unit": unit}
            for m in modes:
                row[m] = cells[m]
            csv_writer.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "results", "campaign.csv"))
    ap.add_argument("--by-seed", action="store_true", help="also print one table per seed")
    ap.add_argument("--success-only", action="store_true", help="drop rows where success!=True")
    ap.add_argument("--csv-out", default=None, help="write the aggregate table to this CSV")
    args = ap.parse_args()

    if not os.path.exists(args.path):
        print(f"no campaign CSV at {args.path} — run g_campaign.py first")
        return
    rows = load(args.path)
    if args.success_only:
        rows = [r for r in rows if str(r.get("success")).lower() == "true"]
    if not rows:
        print("no rows to analyze"); return

    seeds = sorted({r["seed"] for r in rows}, key=lambda s: int(s) if s.isdigit() else s)
    print(f"loaded {len(rows)} rows | seeds={seeds} | modes={sorted({r['mode'] for r in rows})}")

    cw = None
    fout = None
    if args.csv_out:
        fout = open(args.csv_out, "w", newline="")
        cw = csv.DictWriter(fout, fieldnames=["metric", "unit"] + MODE_ORDER, extrasaction="ignore")
        cw.writeheader()

    print_table(rows, f"OVERALL (all {len(seeds)} seeds)", cw)
    if args.by_seed:
        for s in seeds:
            print_table([r for r in rows if r["seed"] == s], f"seed {s}")
    if fout:
        fout.close()
        print(f"\nwrote aggregate table -> {args.csv_out}")


if __name__ == "__main__":
    main()
