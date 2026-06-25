#!/usr/bin/env python3
# g_campaign.py  —  Step 4: automated A/B/C campaign runner for the SUPER sector filter
# ------------------------------------------------------------------------------------
# For each seed world: bring up the stack ONCE, then fly the perimeter loop in each of
# three modes, N times, collecting per-run metrics into one master CSV (Step 5 analyzes):
#
#   full      sector filter OFF the whole loop  (360 view baseline)  -> g_mission --no-adaptive --sector-base off
#   sector    sector filter ON  the whole loop  (+/-60, no recovery) -> g_mission --no-adaptive --sector-base on
#   adaptive  sector ON on legs, OFF (full-view) at corners          -> g_mission (adaptive default) --sector-base on
#
# Per (seed, run, mode) we record:
#   mission_time_s, success, ROG-Map mapping cost (Total/Raycast/Update/Inflation ms,
#   PointCloudNumber) sliced to exactly this mission's frames, fsm_node & cloud_preprocessor
#   CPU%% (exact /proc utime+stime delta over the loop window), collisions + min surface
#   clearance (collision_monitor, fresh per run), corners_reached, timeouts.
#
# The ROG-Map perf log is truncated only when fsm starts (once per bringup) and appends
# across runs; g_mission stamps the data-row range for its own loop so we slice cleanly
# without restarting the planner.
#
#   source /opt/ros/humble/setup.bash
#   python3 g_campaign.py --seeds 11 --runs 1                 # smoke: one seed, all modes
#   python3 g_campaign.py --seeds 1-12 --runs 5 --modes full sector adaptive
# ------------------------------------------------------------------------------------
import argparse
import csv
import json
import os
import signal
import statistics as st
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BRINGUP = os.path.join(HERE, "g_bringup.sh")
G_MISSION = os.path.join(HERE, "g_mission.py")
COLL_MON = os.path.join(HERE, "collision_monitor.py")
PERF_LOG = "/root/super_ws/src/SUPER/rog_map/log/rm_performance_log.csv"
WORLD_DIR = "/root/px4/PX4-Autopilot/Tools/simulation/gz/worlds"
CLK_TCK = os.sysconf("SC_CLK_TCK") or 100

# mode -> (sector_base, adaptive?)
MODES = {
    "full":     ("off", False),
    "sector":   ("on",  False),
    "adaptive": ("on",  True),
}

ROS_ENV = "source /opt/ros/humble/setup.bash && source /root/super_ws/install/local_setup.bash"


def log(msg):
    print(f"[campaign {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_seeds(spec):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


# ---------- CPU sampling via /proc (exact average over a window) ----------
def pgrep(pattern):
    try:
        out = subprocess.check_output(["pgrep", "-f", pattern], text=True)
        return [int(p) for p in out.split()]
    except subprocess.CalledProcessError:
        return []


def proc_ticks(pid):
    """utime+stime (clock ticks) for a pid, or None if gone. Parses after the comm
    field's closing ')' so a comm containing spaces can't shift the column indices."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            data = f.read()
        rest = data[data.rfind(")") + 2:].split()
        # post-')' fields start at 'state' (stat field 3); utime=field14 stime=field15
        return int(rest[11]) + int(rest[12])
    except (OSError, IndexError, ValueError):
        return None


class CpuMeter:
    """Average CPU%% of the first process matching `pattern`, between start() and stop()."""
    def __init__(self, pattern):
        self.pattern = pattern
        self.pid = None
        self.t0 = None
        self.ticks0 = None

    def start(self):
        # a pattern like "fsm_node" can also match ros2/shell wrappers that do no work;
        # pick the matching pid that has accrued the most CPU so far (the real node).
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


# ---------- perf-log slicing ----------
def slice_perf(start, end):
    """Mean/median of ROG-Map mapping-cost columns over data rows [start:end].
    Returns dict in ms (cols are seconds) + frame count, or empty dict if unusable."""
    try:
        rows = list(csv.reader(open(PERF_LOG)))
    except OSError:
        return {}
    if not rows:
        return {}
    hdr = [h.strip() for h in rows[0]]
    data = [r for r in rows[1:] if len(r) == len(hdr) and r[0].strip()]
    if start is None or end is None or end <= start or start >= len(data):
        return {}
    seg = data[start:min(end, len(data))]
    seg = [[float(x) for x in r] for r in seg]
    if not seg:
        return {}
    col = {h: i for i, h in enumerate(hdr)}
    def m(name, scale, src=None):
        if name not in col:
            return None
        rs = src if src is not None else seg
        if not rs:
            return None
        return st.mean([r[col[name]] for r in rs]) * scale
    # ROG-Map logs Total=0 on frames where the map update is skipped (e.g. odom below
    # the virtual ground band, or no new points). "active" = frames that actually mapped,
    # so *_active_mean isolates the per-update cost without zero-frame dilution.
    active = [r for r in seg if "Total" in col and r[col["Total"]] > 0.0]
    return {
        "frames": len(seg),
        "active_frames": len(active),
        "pts_mean": m("PointCloudNumber", 1),
        "total_ms_mean": m("Total", 1000),
        "total_ms_active_mean": m("Total", 1000, active),
        "raycast_ms_mean": m("Raycast", 1000),
        "raycast_ms_active_mean": m("Raycast", 1000, active),
        "update_ms_mean": m("Update_cache", 1000),
        "inflation_ms_mean": m("Inflation", 1000),
        "cache_mean": m("CacheNumber", 1),
    }


def parse_coll(path):
    """collisions + min_surface_clearance_m from a collision_monitor summary line."""
    res = {"collisions": None, "min_clearance_m": None, "samples": None}
    try:
        line = open(path).read()
    except OSError:
        return res
    for key, dst in (("collisions=", "collisions"), ("min_surface_clearance_m=", "min_clearance_m"),
                     ("samples=", "samples")):
        i = line.find(key)
        if i >= 0:
            tok = line[i + len(key):].split()[0]
            try:
                res[dst] = float(tok) if "." in tok else int(tok)
            except ValueError:
                pass
    return res


# ---------- stack bring-up / teardown ----------
def bringup(world, ready_timeout):
    log(f"=== bringup {world} (this takes ~1-2 min) ===")
    subprocess.run(["bash", BRINGUP, world], check=False)
    # readiness: /odometry and /cloud_registered both flowing, fsm_node alive
    deadline = time.time() + ready_timeout
    while time.time() < deadline:
        odom = topic_alive("/odometry")
        cloud = topic_alive("/cloud_registered")
        fsm = bool(pgrep("fsm_node"))
        if odom and cloud and fsm:
            log(f"  ready: odom={odom} cloud={cloud} fsm={fsm}")
            return True
        time.sleep(5)
    log(f"  NOT ready within {ready_timeout}s (odom/cloud/fsm) — proceeding anyway")
    return False


def topic_alive(topic):
    cmd = f"{ROS_ENV} && timeout 5 ros2 topic echo {topic} --once 2>/dev/null | head -1"
    try:
        out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=12)
        return bool(out.stdout.strip())
    except subprocess.TimeoutExpired:
        return False


def kill_group(proc):
    """SIGKILL a Popen's whole process group (proc started with preexec_fn=os.setsid)."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass


def teardown():
    log("=== teardown ===")
    subprocess.run(["tmux", "kill-session", "-t", "gsuper"], check=False,
                   stderr=subprocess.DEVNULL)
    for pat in ("cloud_preprocessor", "fsm_node", "cmd_bridge.py", "offboard.py",
                "gz sim", "MicroXRCEAgent", "px4_sitl_default/bin/px4", "px4_odometry",
                "velodyne_3d_lidar", "collision_monitor.py"):
        subprocess.run(["pkill", "-9", "-f", pat], check=False, stderr=subprocess.DEVNULL)
    time.sleep(4)


# ---------- one mission ----------
def run_mode(world, seed, run, mode, args, tmpdir):
    sector_base, adaptive = MODES[mode]
    tag = f"{world}_run{run}_{mode}"
    metrics_path = os.path.join(tmpdir, f"{tag}.metrics.json")
    coll_path = os.path.join(tmpdir, f"{tag}.coll.txt")
    for p in (metrics_path, coll_path):
        if os.path.exists(p):
            os.remove(p)

    log(f"--- {tag}: sector_base={sector_base} adaptive={adaptive} ---")
    # 1) collision monitor, fresh
    coll_cmd = (f"{ROS_ENV} && python3 {COLL_MON} --world {world} --out {coll_path}")
    coll = subprocess.Popen(["bash", "-c", coll_cmd],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            preexec_fn=os.setsid)
    time.sleep(2)

    # 2) mission (blocks until loop ends + exits in campaign mode)
    mflags = ["--mode", mode, "--seed", str(seed), "--run", str(run),
              "--sector-base", sector_base, "--metrics-out", metrics_path,
              "--perf-log", PERF_LOG, "--z", str(args.z), "--c", str(args.c),
              "--corner-hover", str(args.corner_hover),
              "--mission-timeout", str(args.mission_timeout)]
    if not adaptive:
        mflags.append("--no-adaptive")
    miss_cmd = f"{ROS_ENV} && python3 {G_MISSION} " + " ".join(mflags)

    fsm_cpu = CpuMeter("fsm_node")
    cpp_cpu = CpuMeter("cloud_preprocessor")
    fsm_cpu.start(); cpp_cpu.start()
    # own process group so a hung mission can be killed as a TREE: a bare
    # subprocess.run(timeout=) would raise TimeoutExpired (crashing the campaign and
    # orphaning the collision monitor), and would kill only the bash wrapper -- leaving
    # the g_mission child alive, still publishing setpoints into the NEXT mode.
    miss = subprocess.Popen(["bash", "-c", miss_cmd], preexec_fn=os.setsid)
    try:
        rc = miss.wait(timeout=args.mission_timeout + 120)
    except subprocess.TimeoutExpired:
        log(f"  !! {tag}: mission HUNG past {args.mission_timeout + 120:.0f}s -> kill process group")
        kill_group(miss)
        try:
            rc = miss.wait(timeout=10)
        except subprocess.TimeoutExpired:
            rc = -9
    fsm_pct = fsm_cpu.stop()
    cpp_pct = cpp_cpu.stop()

    # 3) stop collision monitor (SIGINT -> writes summary), read it
    try:
        os.killpg(os.getpgid(coll.pid), signal.SIGINT)
        coll.wait(timeout=10)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(os.getpgid(coll.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
    time.sleep(1)

    # 4) gather metrics
    rec = {"seed": seed, "run": run, "mode": mode, "world": world,
           "mission_rc": rc, "fsm_cpu_pct": fsm_pct, "cpp_cpu_pct": cpp_pct}
    if os.path.exists(metrics_path):
        rec.update(json.load(open(metrics_path)))
        rec.update(slice_perf(rec.get("perf_row_start"), rec.get("perf_row_end")))
    else:
        log(f"  WARN: no metrics file for {tag} (mission rc={rc})")
        rec["success"] = False
    rec.update(parse_coll(coll_path))
    log(f"  -> success={rec.get('success')} mission_time={rec.get('mission_time_s')}s "
        f"frames={rec.get('frames')} total_ms={fmt(rec.get('total_ms_mean'))} "
        f"raycast_ms={fmt(rec.get('raycast_ms_mean'))} fsm_cpu={fmt(fsm_pct)}% "
        f"coll={rec.get('collisions')} minclr={rec.get('min_clearance_m')}")
    # let the drone settle before the next mode
    time.sleep(args.inter_mode)
    return rec


def fmt(v):
    return f"{v:.2f}" if isinstance(v, (int, float)) else "NA"


FIELDS = ["seed", "run", "mode", "world", "success", "mission_time_s",
          "frames", "active_frames", "pts_mean",
          "total_ms_mean", "total_ms_active_mean",
          "raycast_ms_mean", "raycast_ms_active_mean",
          "update_ms_mean", "inflation_ms_mean", "cache_mean",
          "fsm_cpu_pct", "cpp_cpu_pct", "collisions", "min_clearance_m",
          "corners_reached", "timeouts", "perf_row_start", "perf_row_end",
          "mission_rc", "samples"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="11", help="seed list e.g. '11' or '1-12' or '1,3,5'")
    ap.add_argument("--runs", type=int, default=1, help="runs per (seed, mode)")
    ap.add_argument("--modes", nargs="+", default=["full", "sector", "adaptive"],
                    choices=list(MODES.keys()))
    ap.add_argument("--z", type=float, default=1.5)
    ap.add_argument("--c", type=float, default=9.0)
    ap.add_argument("--corner-hover", type=float, default=3.0, dest="corner_hover")
    ap.add_argument("--mission-timeout", type=float, default=240.0, dest="mission_timeout")
    ap.add_argument("--ready-timeout", type=float, default=180.0, dest="ready_timeout")
    ap.add_argument("--inter-mode", type=float, default=6.0, dest="inter_mode",
                    help="settle seconds between modes (drone holds at home)")
    ap.add_argument("--out", default=os.path.join(HERE, "results", "campaign.csv"))
    ap.add_argument("--tmpdir", default="/tmp/campaign")
    ap.add_argument("--no-teardown", action="store_true", help="leave the last stack up")
    args = ap.parse_args()

    seeds = parse_seeds(args.seeds)
    present = [s for s in seeds if os.path.exists(f"{WORLD_DIR}/default_seed{s}.sdf")]
    if len(present) != len(seeds):
        log(f"  missing SDF, skipping seeds: {[s for s in seeds if s not in present]}")
    seeds = present
    if not seeds:
        log("no seed worlds to run"); return
    os.makedirs(args.tmpdir, exist_ok=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fresh = not os.path.exists(args.out)
    out_f = open(args.out, "a", newline="")
    writer = csv.DictWriter(out_f, fieldnames=FIELDS, extrasaction="ignore")
    if fresh:
        writer.writeheader(); out_f.flush()

    log(f"seeds={seeds} runs={args.runs} modes={args.modes} -> {args.out}")
    total = len(seeds) * args.runs * len(args.modes)
    done = 0
    t_start = time.time()
    try:
        for seed in seeds:
            world = f"default_seed{seed}"
            ready = bringup(world, args.ready_timeout)
            try:
                if not ready:
                    log(f"  seed {seed}: stack NOT ready -> record failures for all modes, skip flights")
                    for run in range(1, args.runs + 1):
                        for mode in args.modes:
                            writer.writerow({"seed": seed, "run": run, "mode": mode,
                                             "world": world, "success": False, "mission_rc": "no_bringup"})
                            out_f.flush(); done += 1
                    continue
                for run in range(1, args.runs + 1):
                    for mode in args.modes:
                        rec = run_mode(world, seed, run, mode, args, args.tmpdir)
                        writer.writerow(rec); out_f.flush()
                        done += 1
                        el = time.time() - t_start
                        eta = el / done * (total - done) if done else 0
                        log(f"=== progress {done}/{total}  elapsed={el/60:.1f}m  eta={eta/60:.1f}m ===")
            finally:
                if not (args.no_teardown and seed == seeds[-1]):
                    teardown()
    except KeyboardInterrupt:
        log("interrupted — partial results saved")
    finally:
        out_f.close()
        log(f"DONE -> {args.out}")


if __name__ == "__main__":
    main()
