#!/usr/bin/env python3
"""Native (MARSIM/perfect-tracking) campaign: full/sector/adaptive x N runs x 11 maps
(seed1..seed10 = user's size/density sweep, converted to PCD; reference = original
dense-forest PCD, the same map the SUPER paper's own benchmark_dense uses).

Reliability lessons ported from the Gazebo g_campaign.py saga: fresh process
teardown+restart per (map,mode,run), retry on startup failure, own process group
so a hung run can be killed as a tree.
"""
import argparse, csv, os, signal, subprocess, sys, time, json, statistics as st

ROS_ENV = "source /opt/ros/humble/setup.bash && source /root/super_ws/install/setup.bash"
PERF_LOG = "/root/super_ws/src/SUPER/rog_map/log/rm_performance_log.csv"
LOOP_MON = "/tmp/native_loop_monitor.py"
SECTOR = "/tmp/native_sector.py"
TMPDIR = "/tmp/native_campaign"
os.makedirs(TMPDIR, exist_ok=True)

LOOP_WPS = "9,9;-9,9;-9,-9;9,-9;0,0"
LOOP_SWITCH = 1.5
LOOP_TIMEOUT = 150.0
REF_WPS = "0,50;0,-50"
REF_SWITCH = 2.0
REF_TIMEOUT = 90.0

MAPS = [f"seed{i}" for i in range(1, 11)] + ["reference"]
MODES = ["full", "sector", "adaptive"]

FIELDS = ["map", "run", "mode", "success", "mission_time_s", "waypoints_reached",
          "n_waypoints", "collisions", "min_clearance_m", "samples",
          "pts_mean", "total_ms_mean", "raycast_ms_mean", "update_ms_mean",
          "inflation_ms_mean", "kept_pct", "perf_row_start", "perf_row_end"]


def log(msg):
    print(f"[native_campaign {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def kill_all():
    for n in ("perfect_drone_node", "fsm_node", "waypoint_mission", "native_sector.py",
              "native_loop_monitor.py"):
        subprocess.run(["pkill", "-9", "-f", n], stderr=subprocess.DEVNULL)
    time.sleep(1.5)


def perf_row_count():
    try:
        with open(PERF_LOG) as f:
            return max(0, sum(1 for _ in f) - 1)
    except OSError:
        return 0


def slice_perf(start, end):
    try:
        rows = list(csv.reader(open(PERF_LOG)))
    except OSError:
        return {}
    if not rows or start is None or end is None or end <= start:
        return {}
    hdr = [h.strip() for h in rows[0]]
    data = [r for r in rows[1:] if len(r) == len(hdr) and r[0].strip()]
    if start >= len(data):
        return {}
    seg = [[float(x) for x in r] for r in data[start:min(end, len(data))]]
    if not seg:
        return {}
    col = {h: i for i, h in enumerate(hdr)}
    def m(name, scale):
        if name not in col:
            return None
        return st.mean([r[col[name]] for r in seg]) * scale
    return {
        "pts_mean": m("PointCloudNumber", 1),
        "total_ms_mean": m("Total", 1000),
        "raycast_ms_mean": m("Raycast", 1000),
        "update_ms_mean": m("Update_cache", 1000),
        "inflation_ms_mean": m("Inflation", 1000),
    }


def run_one(map_name, mode, run, attempt_max=3):
    is_ref = (map_name == "reference")
    wps, switch, timeout = (REF_WPS, REF_SWITCH, REF_TIMEOUT) if is_ref else (LOOP_WPS, LOOP_SWITCH, LOOP_TIMEOUT)
    tag = f"{map_name}_run{run}_{mode}"
    out_json = os.path.join(TMPDIR, f"{tag}.json")
    filt_log = os.path.join(TMPDIR, f"{tag}.filt.log")

    for attempt in range(1, attempt_max + 1):
        kill_all()
        if os.path.exists(out_json):
            os.remove(out_json)

        if is_ref:
            launch_cmd = "ros2 launch mission_planner benchmark_reference.launch.py"
        else:
            launch_cmd = (
                "ros2 launch mission_planner benchmark_seedmap.launch.py "
                f"waypoint_data:=loop9.txt drone_config:={map_name}.yaml "
                "super_config:=static_seedmaps.yaml"
            )
        launch_proc = subprocess.Popen(
            ["bash", "-c", f"{ROS_ENV} && {launch_cmd}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
        time.sleep(4)

        # confirm fsm_node actually came up
        up = subprocess.run(["pgrep", "-f", "fsm_node"], stdout=subprocess.DEVNULL).returncode == 0
        if not up:
            log(f"  {tag} attempt {attempt}/{attempt_max}: fsm_node did not start -> retry")
            try:
                os.killpg(os.getpgid(launch_proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            continue

        row_start = perf_row_count()
        filt_proc = subprocess.Popen(
            ["bash", "-c", f"python3 {SECTOR} {mode} > {filt_log} 2>&1"],
            preexec_fn=os.setsid)
        time.sleep(2)

        mon_cmd = f"python3 {LOOP_MON} '{wps}' {switch} {timeout} {out_json}"
        mon_proc = subprocess.Popen(["bash", "-c", f"{ROS_ENV} && {mon_cmd}"],
                                    preexec_fn=os.setsid)
        try:
            mon_proc.wait(timeout=timeout + 30)
        except subprocess.TimeoutExpired:
            log(f"  {tag}: monitor HUNG -> kill")
            try:
                os.killpg(os.getpgid(mon_proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass

        row_end = perf_row_count()

        # kept% from the filter log (last report line)
        kept_pct = None
        try:
            for line in open(filt_log):
                if "kept" in line:
                    import re
                    m = re.search(r"kept (\d+)%", line)
                    if m:
                        kept_pct = int(m.group(1))
        except OSError:
            pass

        try:
            os.killpg(os.getpgid(filt_proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.killpg(os.getpgid(launch_proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        kill_all()

        rec = {"map": map_name, "run": run, "mode": mode,
               "perf_row_start": row_start, "perf_row_end": row_end, "kept_pct": kept_pct}
        if os.path.exists(out_json):
            rec.update(json.load(open(out_json)))
            rec.update(slice_perf(row_start, row_end))
        else:
            rec["success"] = False

        # retry if we never even got odom samples (startup race), else accept the result
        if rec.get("samples", 0) in (0, None) and attempt < attempt_max:
            log(f"  {tag} attempt {attempt}/{attempt_max}: no odom samples -> retry")
            continue

        log(f"  {tag}: success={rec.get('success')} time={rec.get('mission_time_s')}s "
            f"coll={rec.get('collisions')} minclr={rec.get('min_clearance_m')} "
            f"pts={rec.get('pts_mean')} kept={kept_pct}%")
        return rec

    return {"map": map_name, "run": run, "mode": mode, "success": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--maps", nargs="+", default=MAPS)
    ap.add_argument("--modes", nargs="+", default=MODES)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "native_campaign.csv"))
    args = ap.parse_args()

    fresh = not os.path.exists(args.out)
    f = open(args.out, "a", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    if fresh:
        w.writeheader(); f.flush()

    total = len(args.maps) * len(args.modes) * args.runs
    done = 0
    t0 = time.time()
    for map_name in args.maps:
        for run in range(1, args.runs + 1):
            for mode in args.modes:
                rec = run_one(map_name, mode, run)
                w.writerow(rec); f.flush()
                done += 1
                el = time.time() - t0
                eta = el / done * (total - done) if done else 0
                log(f"=== progress {done}/{total} elapsed={el/60:.1f}m eta={eta/60:.1f}m ===")
    f.close()
    log(f"DONE -> {args.out}")


if __name__ == "__main__":
    main()
