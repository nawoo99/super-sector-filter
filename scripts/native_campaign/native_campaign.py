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
CLK_TCK = os.sysconf("SC_CLK_TCK") or 100


def pgrep(pattern):
    try:
        out = subprocess.check_output(["pgrep", "-f", pattern], text=True)
        return [int(p) for p in out.split()]
    except subprocess.CalledProcessError:
        return []


def proc_ticks(pid):
    """utime+stime (clock ticks) for a pid, or None if gone."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            data = f.read()
        rest = data[data.rfind(")") + 2:].split()
        return int(rest[11]) + int(rest[12])
    except (OSError, IndexError, ValueError):
        return None


class CpuMeter:
    """Average CPU% of the busiest process matching `pattern`, between start()/stop()."""
    def __init__(self, pattern):
        self.pattern = pattern
        self.pid = None
        self.t0 = None
        self.ticks0 = None

    def start(self):
        cand = [(proc_ticks(p) or -1, p) for p in pgrep(self.pattern)]
        self.pid = max(cand)[1] if cand else None
        self.t0 = time.time()
        self.ticks0 = proc_ticks(self.pid) if self.pid else None

    def stop(self):
        if self.pid is None or self.ticks0 is None:
            return None
        ticks1 = proc_ticks(self.pid)
        dt = time.time() - self.t0
        if ticks1 is None or dt <= 0:
            return None
        return 100.0 * (ticks1 - self.ticks0) / CLK_TCK / dt

LOOP_WPS = "12,12;-12,12;-12,-12;12,-12;0,0"
LOOP_SWITCH = 1.5
LOOP_TIMEOUT = 150.0
# seed11 = the original SUPER-paper dense-forest map (random_map_2_26609.pcd),
# NOT a gen_world cylinder map -- straight 100m corridor, launched via
# benchmark_reference.launch.py / static_reference.yaml.
REF_WPS = "0,50;0,-50"
REF_SWITCH = 2.0
REF_TIMEOUT = 90.0

MAPS = [f"seed{i}" for i in range(1, 11)] + ["seed11"]
MODES = ["full", "sector", "adaptive"]

FIELDS = ["map", "run", "mode", "success", "mission_time_s", "waypoints_reached",
          "n_waypoints", "collisions", "min_clearance_m", "samples",
          "pts_mean", "total_ms_mean", "raycast_ms_mean", "update_ms_mean",
          "inflation_ms_mean", "kept_pct", "fsm_cpu_pct", "filter_cpu_pct",
          "perf_row_start", "perf_row_end"]


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
    is_ref = (map_name == "seed11")  # seed11 = the original SUPER-paper dense-forest map
    if is_ref:
        wps, switch, timeout = REF_WPS, REF_SWITCH, REF_TIMEOUT
    else:
        wps, switch, timeout = LOOP_WPS, LOOP_SWITCH, LOOP_TIMEOUT
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
                f"waypoint_data:=loop12.txt drone_config:={map_name}.yaml "
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

        fsm_cpu = CpuMeter("fsm_node")
        filt_cpu = CpuMeter("native_sector.py")
        fsm_cpu.start(); filt_cpu.start()

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

        fsm_cpu_pct = fsm_cpu.stop()
        filter_cpu_pct = filt_cpu.stop()
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
               "perf_row_start": row_start, "perf_row_end": row_end, "kept_pct": kept_pct,
               "fsm_cpu_pct": fsm_cpu_pct, "filter_cpu_pct": filter_cpu_pct}
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
            f"pts={rec.get('pts_mean')} kept={kept_pct}% fsm_cpu={fsm_cpu_pct}")
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
