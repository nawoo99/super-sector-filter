#!/usr/bin/env python3
"""Native (MARSIM/perfect-tracking) campaign.

The default campaign is full/sector/adaptive x N runs x seed1..seed11.
Seed12/13 are opt-in dynamic blind-sector diagnostics; seed14/15 are
mirrored controlled-hold stall-recovery diagnostics.

Reliability lessons ported from the Gazebo g_campaign.py saga: fresh process
teardown+restart per (map,mode,run), retry on startup failure, own process group
so a hung run can be killed as a tree.
"""
import argparse, csv, fcntl, math, os, re, shutil, signal, subprocess, sys, time, json, statistics as st

from correlate_shadow_contacts import correlate as correlate_shadow_contacts

ROS_ENV = "source /opt/ros/humble/setup.bash && source /root/super_ws/install/setup.bash"
PERF_LOG = "/root/super_ws/src/SUPER/rog_map/log/rm_performance_log.csv"
SUPER_CONFIG_DIR = "/root/super_ws/src/SUPER/super_planner/config"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
LOOP_MON = os.path.join(SCRIPT_DIR, "native_loop_monitor.py")
REFERENCE_MON = os.path.join(SCRIPT_DIR, "native_reference_monitor.py")
SECTOR = os.path.join(SCRIPT_DIR, "native_sector.py")
SECTOR_CPP_EXECUTABLE = "native_sector_cpp"
SEED12_SCENARIO = os.path.join(SCRIPT_DIR, "native_seed12_scenario.py")
RECOVERY_SCENARIO = os.path.join(SCRIPT_DIR, "native_recovery_scenario.py")
RECOVERY_MISSION = os.path.join(SCRIPT_DIR, "native_recovery_mission.py")
TMPDIR = "/tmp/native_campaign"
LOCK_PATH = "/tmp/super_sector_filter_native.lock"
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


def read_keyed_kib(path, key):
    """Read a ``Key: N kB`` value, returning None when unavailable."""
    try:
        with open(path) as stream:
            for line in stream:
                if line.startswith(key + ":"):
                    return int(line.split()[1])
    except (OSError, IndexError, ValueError):
        pass
    return None


def read_int_file(path):
    try:
        return int(open(path).read().strip())
    except (OSError, ValueError):
        return None


def read_cgroup_event(name):
    try:
        with open("/sys/fs/cgroup/memory.events") as stream:
            for line in stream:
                key, value = line.split()
                if key == name:
                    return int(value)
    except (OSError, ValueError):
        pass
    return None


def super_config_cloud_topic(config_name):
    """Return a SUPER config's ROG-Map cloud topic without a YAML dependency."""
    if not config_name:
        return None
    path = os.path.join(SUPER_CONFIG_DIR, os.path.basename(config_name))
    try:
        with open(path) as stream:
            for line in stream:
                match = re.match(r'^\s*cloud_topic:\s*["\']?([^"\'\s#]+)', line)
                if match:
                    return match.group(1)
    except OSError:
        return None
    return None


def super_config_max_velocity(config_name):
    """Return traj_opt/boundary/max_vel without requiring PyYAML."""
    if not config_name:
        return None
    path = os.path.join(SUPER_CONFIG_DIR, os.path.basename(config_name))
    try:
        with open(path) as stream:
            for line in stream:
                match = re.match(
                    r"^\s*max_vel:\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                    line,
                )
                if match:
                    value = float(match.group(1))
                    return value if value > 0.0 else None
    except (OSError, ValueError):
        return None
    return None


def read_memory_psi():
    values = {"psi_some_avg10": None, "psi_full_avg10": None}
    try:
        with open("/proc/pressure/memory") as stream:
            for line in stream:
                fields = line.split()
                if not fields:
                    continue
                prefix = fields[0]
                for field in fields[1:]:
                    if field.startswith("avg10=") and prefix in ("some", "full"):
                        values[f"psi_{prefix}_avg10"] = float(field.split("=", 1)[1])
    except (OSError, ValueError):
        pass
    return values


class MemoryMeter:
    """Low-rate per-attempt FSM and host memory sampler."""

    FIELDNAMES = (
        "elapsed_s", "fsm_rss_kib", "fsm_pss_kib", "fsm_swap_kib",
        "system_available_kib", "system_swap_used_kib",
        "cgroup_memory_kib", "cgroup_swap_kib",
        "psi_some_avg10", "psi_full_avg10",
    )

    def __init__(self, pid, trace_path):
        self.pid = pid
        self.trace_path = trace_path
        self.started = time.monotonic()
        self.rows = []
        with open(trace_path, "w", newline="") as stream:
            csv.DictWriter(
                stream, fieldnames=self.FIELDNAMES, lineterminator="\n"
            ).writeheader()

    def sample(self):
        mem_total = read_keyed_kib("/proc/meminfo", "SwapTotal")
        mem_free = read_keyed_kib("/proc/meminfo", "SwapFree")
        row = {
            "elapsed_s": round(time.monotonic() - self.started, 3),
            "fsm_rss_kib": read_keyed_kib(f"/proc/{self.pid}/status", "VmRSS"),
            "fsm_pss_kib": read_keyed_kib(f"/proc/{self.pid}/smaps_rollup", "Pss"),
            "fsm_swap_kib": read_keyed_kib(f"/proc/{self.pid}/status", "VmSwap"),
            "system_available_kib": read_keyed_kib("/proc/meminfo", "MemAvailable"),
            "system_swap_used_kib": (
                mem_total - mem_free
                if mem_total is not None and mem_free is not None else None
            ),
            "cgroup_memory_kib": (
                value // 1024
                if (value := read_int_file("/sys/fs/cgroup/memory.current")) is not None
                else None
            ),
            "cgroup_swap_kib": (
                value // 1024
                if (value := read_int_file("/sys/fs/cgroup/memory.swap.current")) is not None
                else None
            ),
        }
        row.update(read_memory_psi())
        self.rows.append(row)
        with open(self.trace_path, "a", newline="") as stream:
            csv.DictWriter(
                stream, fieldnames=self.FIELDNAMES, lineterminator="\n"
            ).writerow(row)

    def summary(self):
        def extrema(key, fn):
            values = [row[key] for row in self.rows if row.get(key) is not None]
            return fn(values) / 1024.0 if values else None

        return {
            "fsm_peak_rss_mib": extrema("fsm_rss_kib", max),
            "fsm_peak_pss_mib": extrema("fsm_pss_kib", max),
            "fsm_peak_swap_mib": extrema("fsm_swap_kib", max),
            "system_min_available_mib": extrema("system_available_kib", min),
            "system_peak_swap_used_mib": extrema("system_swap_used_kib", max),
            "cgroup_peak_memory_mib": extrema("cgroup_memory_kib", max),
            "cgroup_peak_swap_mib": extrema("cgroup_swap_kib", max),
            "memory_psi_some_avg10_max": max(
                (row["psi_some_avg10"] for row in self.rows
                 if row.get("psi_some_avg10") is not None), default=None
            ),
            "memory_psi_full_avg10_max": max(
                (row["psi_full_avg10"] for row in self.rows
                 if row.get("psi_full_avg10") is not None), default=None
            ),
        }


def read_cpu_usage_usec(cgroup_path):
    """Read hierarchical cgroup-v2 CPU usage, or None when unavailable."""
    try:
        with open(os.path.join(cgroup_path, "cpu.stat")) as stream:
            for line in stream:
                key, value = line.split()
                if key == "usage_usec":
                    return int(value)
    except (OSError, ValueError):
        pass
    return None


def nearest_rank_percentile(values, percentile):
    """Deterministic nearest-rank percentile for interval samples."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[min(len(ordered), rank) - 1]


def process_tree_pids(root_pid):
    """Return a live root process and every descendant visible in /proc."""
    children = {}
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        pid = int(name)
        try:
            with open(f"/proc/{pid}/stat") as stream:
                data = stream.read()
            rest = data[data.rfind(")") + 2:].split()
            parent = int(rest[1])
        except (OSError, IndexError, ValueError):
            continue
        children.setdefault(parent, []).append(pid)
    found = []
    pending = [root_pid]
    seen = set()
    while pending:
        pid = pending.pop()
        if pid in seen:
            continue
        seen.add(pid)
        if os.path.exists(f"/proc/{pid}"):
            found.append(pid)
            pending.extend(children.get(pid, ()))
    return found


class CgroupRunMeter:
    """Mission-window CPU and process-memory accounting for two scopes.

    ``algorithm`` contains fsm_node plus the optional cloud filter. ``stack``
    contains the simulator, waypoint driver and ros2 launch wrapper. The
    parent cgroup's cpu.stat is hierarchical, so it measures end-to-end CPU
    while the algorithm child remains independently measurable. The host does
    not delegate the memory controller at the root cgroup; peak RSS/PSS/swap
    are therefore summed from the member PIDs instead of memory.current.
    """

    TRACE_FIELDS = (
        "elapsed_s", "algorithm_usage_usec", "end_to_end_usage_usec",
        "algorithm_interval_cores", "end_to_end_interval_cores",
        "memory_sampled",
        "algorithm_pids", "end_to_end_pids",
        "algorithm_rss_kib", "algorithm_pss_kib", "algorithm_swap_kib",
        "end_to_end_rss_kib", "end_to_end_pss_kib",
        "end_to_end_swap_kib",
    )

    def __init__(self, tag, trace_path, root="/sys/fs/cgroup"):
        safe_tag = re.sub(r"[^A-Za-z0-9_.-]+", "_", tag)
        self.path = os.path.join(
            root, f"super_sector_filter_{os.getpid()}_{safe_tag}"
        )
        self.algorithm_path = os.path.join(self.path, "algorithm")
        self.stack_path = os.path.join(self.path, "stack")
        self.trace_path = trace_path
        self.started = None
        self.last_sample_time = None
        self.last_memory_sample_time = None
        self.start_usage = {}
        self.last_usage = {}
        self.interval_cores = {"algorithm": [], "end_to_end": []}
        self.memory_peaks = {
            scope: {"rss_kib": 0, "pss_kib": 0, "swap_kib": 0,
                    "pids": 0}
            for scope in ("algorithm", "end_to_end")
        }
        self.last_memory = {
            scope: {"rss_kib": 0, "pss_kib": 0, "swap_kib": 0,
                    "pids": 0}
            for scope in ("algorithm", "end_to_end")
        }
        os.mkdir(self.path)
        try:
            os.mkdir(self.algorithm_path)
            os.mkdir(self.stack_path)
            if read_cpu_usage_usec(self.path) is None:
                raise RuntimeError("parent cpu.stat has no usage_usec")
            if read_cpu_usage_usec(self.algorithm_path) is None:
                raise RuntimeError("algorithm cpu.stat has no usage_usec")
        except Exception:
            self.cleanup()
            raise
        with open(self.trace_path, "w", newline="") as stream:
            csv.DictWriter(
                stream, fieldnames=self.TRACE_FIELDS, lineterminator="\n"
            ).writeheader()

    @staticmethod
    def _write_pid(cgroup_path, pid):
        try:
            with open(os.path.join(cgroup_path, "cgroup.procs"), "w") as stream:
                stream.write(str(pid))
            return True
        except (OSError, ValueError):
            return False

    def assign_tree(self, root_pid, scope):
        target = self.algorithm_path if scope == "algorithm" else self.stack_path
        moved = 0
        # Move parents before children so later descendants inherit the same
        # scope even if they fork while this snapshot is being traversed.
        for pid in process_tree_pids(root_pid):
            moved += int(self._write_pid(target, pid))
        return moved

    def assign_pid(self, pid, scope):
        if pid is None:
            return False
        target = self.algorithm_path if scope == "algorithm" else self.stack_path
        return self._write_pid(target, pid)

    @staticmethod
    def _recursive_pids(path):
        found = set()
        for directory, _, files in os.walk(path):
            if "cgroup.procs" not in files:
                continue
            try:
                with open(os.path.join(directory, "cgroup.procs")) as stream:
                    found.update(int(line) for line in stream if line.strip())
            except (OSError, ValueError):
                continue
        return sorted(found)

    @staticmethod
    def _process_memory(pids):
        totals = {"rss_kib": 0, "pss_kib": 0, "swap_kib": 0, "pids": 0}
        for pid in pids:
            rss = read_keyed_kib(f"/proc/{pid}/status", "VmRSS")
            pss = read_keyed_kib(f"/proc/{pid}/smaps_rollup", "Pss")
            swap = read_keyed_kib(f"/proc/{pid}/status", "VmSwap")
            if rss is None and pss is None and swap is None:
                continue
            totals["pids"] += 1
            totals["rss_kib"] += rss or 0
            totals["pss_kib"] += pss or 0
            totals["swap_kib"] += swap or 0
        return totals

    def start(self):
        now = time.monotonic()
        self.started = now
        self.last_sample_time = now
        self.start_usage = {
            "algorithm": read_cpu_usage_usec(self.algorithm_path),
            "end_to_end": read_cpu_usage_usec(self.path),
        }
        if None in self.start_usage.values():
            raise RuntimeError("cgroup cpu.stat became unavailable")
        self.last_usage = dict(self.start_usage)
        self.sample(write_interval=False)

    def sample(self, write_interval=True, force_memory=False):
        if self.started is None:
            return
        now = time.monotonic()
        current = {
            "algorithm": read_cpu_usage_usec(self.algorithm_path),
            "end_to_end": read_cpu_usage_usec(self.path),
        }
        dt = now - self.last_sample_time
        intervals = {"algorithm": None, "end_to_end": None}
        if write_interval and dt > 0.0 and None not in current.values():
            for scope in intervals:
                delta_usec = max(0, current[scope] - self.last_usage[scope])
                intervals[scope] = delta_usec / 1.0e6 / dt
                self.interval_cores[scope].append(intervals[scope])
        memory_sampled = bool(
            force_memory or self.last_memory_sample_time is None or
            now - self.last_memory_sample_time >= 10.0
        )
        if memory_sampled:
            algorithm_pids = self._recursive_pids(self.algorithm_path)
            end_to_end_pids = self._recursive_pids(self.path)
            self.last_memory = {
                "algorithm": self._process_memory(algorithm_pids),
                "end_to_end": self._process_memory(end_to_end_pids),
            }
            self.last_memory_sample_time = now
            for scope, values in self.last_memory.items():
                for key, value in values.items():
                    self.memory_peaks[scope][key] = max(
                        self.memory_peaks[scope][key], value
                    )
        memory = self.last_memory
        row = {
            "elapsed_s": round(now - self.started, 6),
            "algorithm_usage_usec": current["algorithm"],
            "end_to_end_usage_usec": current["end_to_end"],
            "algorithm_interval_cores": intervals["algorithm"],
            "end_to_end_interval_cores": intervals["end_to_end"],
            "memory_sampled": memory_sampled,
            "algorithm_pids": memory["algorithm"]["pids"],
            "end_to_end_pids": memory["end_to_end"]["pids"],
            "algorithm_rss_kib": memory["algorithm"]["rss_kib"],
            "algorithm_pss_kib": memory["algorithm"]["pss_kib"],
            "algorithm_swap_kib": memory["algorithm"]["swap_kib"],
            "end_to_end_rss_kib": memory["end_to_end"]["rss_kib"],
            "end_to_end_pss_kib": memory["end_to_end"]["pss_kib"],
            "end_to_end_swap_kib": memory["end_to_end"]["swap_kib"],
        }
        with open(self.trace_path, "a", newline="") as stream:
            csv.DictWriter(
                stream, fieldnames=self.TRACE_FIELDS, lineterminator="\n"
            ).writerow(row)
        if None not in current.values():
            self.last_usage = current
        self.last_sample_time = now

    def summary(self):
        now = time.monotonic()
        duration = max(0.0, now - self.started) if self.started else 0.0
        result = {
            "cgroup_cpu_accounting": True,
            "cgroup_cpu_duration_s": duration,
            "cgroup_cpu_trace_csv": self.trace_path,
            "cgroup_memory_source": "sum_proc_rss_pss_swap",
        }
        for scope, path in (
            ("algorithm", self.algorithm_path),
            ("end_to_end", self.path),
        ):
            usage = read_cpu_usage_usec(path)
            core_s = (
                max(0, usage - self.start_usage[scope]) / 1.0e6
                if usage is not None and self.start_usage.get(scope) is not None
                else None
            )
            values = self.interval_cores[scope]
            result.update({
                f"{scope}_cpu_core_s": core_s,
                f"{scope}_cpu_cores_mean": (
                    core_s / duration if core_s is not None and duration > 0 else None
                ),
                f"{scope}_cpu_cores_p95_1s": nearest_rank_percentile(values, 0.95),
                f"{scope}_cpu_cores_max_1s": max(values) if values else None,
                f"{scope}_peak_rss_mib": self.memory_peaks[scope]["rss_kib"] / 1024.0,
                f"{scope}_peak_pss_mib": self.memory_peaks[scope]["pss_kib"] / 1024.0,
                f"{scope}_peak_swap_mib": self.memory_peaks[scope]["swap_kib"] / 1024.0,
                f"{scope}_max_processes": self.memory_peaks[scope]["pids"],
            })
        return result

    def cleanup(self):
        # Call only after campaign-owned processes have been terminated. Do
        # not kill or migrate unrelated processes as part of cleanup.
        for path in (self.algorithm_path, self.stack_path, self.path):
            try:
                os.rmdir(path)
            except OSError:
                pass


def merge_memory_summaries(summaries):
    merged = {}
    for key in (
        "fsm_peak_rss_mib", "fsm_peak_pss_mib", "fsm_peak_swap_mib",
        "system_peak_swap_used_mib", "cgroup_peak_memory_mib",
        "cgroup_peak_swap_mib", "memory_psi_some_avg10_max",
        "memory_psi_full_avg10_max",
    ):
        values = [item[key] for item in summaries if item.get(key) is not None]
        merged[key] = max(values) if values else None
    values = [item["system_min_available_mib"] for item in summaries
              if item.get("system_min_available_mib") is not None]
    merged["system_min_available_mib"] = min(values) if values else None
    return merged


def parse_shadow_guard_log(path):
    """Summarize shadow validation without treating map races as geometry."""
    safe_count = 0
    skipped_count = 0
    unsafe_records = []
    validation_ms = []
    with open(path, errors="replace") as stream:
        for line in stream:
            if "TRAJ_GUARD_SHADOW_SAFE" in line:
                safe_count += 1
            elif "TRAJ_GUARD_SHADOW_UNSAFE" in line:
                segment_match = re.search(r"segment=([^ ]+)", line)
                status_match = re.search(r"status=([^ ]+)", line)
                unsafe_records.append((
                    status_match.group(1) if status_match else "UNKNOWN",
                    segment_match.group(1) if segment_match else "UNKNOWN",
                ))
            elif "TRAJ_GUARD_SHADOW_SKIPPED" in line:
                skipped_count += 1
            if "TRAJ_GUARD_SHADOW_" in line:
                match = re.search(r"validation_ms=([0-9.]+)", line)
                if match:
                    validation_ms.append(float(match.group(1)))

    geometric_statuses = {"OCCUPIED", "OUT_OF_MAP"}
    map_race_statuses = {"MAP_UPDATING", "VERSION_CHANGED"}
    geometric_segments = [
        segment for status, segment in unsafe_records
        if status in geometric_statuses
    ]
    return {
        "shadow_safe_candidates": safe_count,
        "shadow_unsafe_candidates": len(unsafe_records),
        "shadow_skipped_candidates": skipped_count,
        "shadow_validated_candidates": safe_count + len(unsafe_records),
        "shadow_geometric_unsafe": len(geometric_segments),
        "shadow_map_race": sum(
            status in map_race_statuses for status, _ in unsafe_records
        ),
        "shadow_other_indeterminate": sum(
            status not in geometric_statuses | map_race_statuses
            for status, _ in unsafe_records
        ),
        "shadow_unsafe_exp": geometric_segments.count("EXP"),
        "shadow_unsafe_appended_backup": geometric_segments.count(
            "APPENDED_BACKUP"
        ),
        "shadow_unsafe_carry_backup": geometric_segments.count("CARRY_BACKUP"),
        "shadow_unsafe_stitch": sum(
            segment.endswith("STITCH") for segment in geometric_segments
        ),
        "shadow_validation_ms_mean": (
            st.mean(validation_ms) if validation_ms else None
        ),
        "shadow_validation_ms_max": max(validation_ms) if validation_ms else None,
    }


def parse_full_refresh_ack_log(path):
    """Count generation-ACK safety transitions from the planner log."""
    counts = {
        "full_refresh_ack_timeouts": 0,
        "full_refresh_recovery_gate_arms": 0,
        "full_refresh_recovery_targets": 0,
        "full_refresh_recovery_acks": 0,
        "full_refresh_ack_timeout_recoveries": 0,
        "guard_same_map_replan_skips": 0,
        "guard_topology_reroute_arms": 0,
        "guard_topology_reroute_searches": 0,
        "guard_base_no_path_local_escape_arms": 0,
        "guard_base_no_path_test_injections": 0,
        "guard_base_no_path_forced_failures": 0,
        "guard_local_escape_test_injections": 0,
        "guard_local_escape_direction_skips": 0,
        "guard_local_escape_direction_rejections": 0,
        "guard_local_escape_commits": 0,
        "guard_local_escape_rejections": 0,
        "guard_initial_footprint_egress_commits": 0,
        "guard_initial_footprint_test_injections": 0,
        "guard_brake_successes": 0,
        "guard_brake_rejections": 0,
        "guard_brake_stationary_defers": 0,
        "trajectory_velocity_slowdowns": 0,
        "trajectory_velocity_rejections": 0,
        "guard_brake_main_pre_successes": 0,
        "guard_brake_retry_successes": 0,
        "guard_brake_ack_timeout_successes": 0,
        "guard_main_pre_map_stale": 0,
        "guard_recoveries": 0,
        "guard_recovery_active_duration_s": 0.0,
        "guard_recovery_active_duration_mean_s": None,
        "guard_recovery_active_duration_max_s": None,
    }
    markers = {
        "FULL_REFRESH_ACK_TIMEOUT": "full_refresh_ack_timeouts",
        "FULL_REFRESH_RECOVERY_GATE_ARM":
            "full_refresh_recovery_gate_arms",
        "FULL_REFRESH_RECOVERY_TARGET": "full_refresh_recovery_targets",
        "FULL_REFRESH_RECOVERY_ACK": "full_refresh_recovery_acks",
        "TRAJ_GUARD_REROUTE_ARM": "guard_topology_reroute_arms",
        "TRAJ_GUARD_REROUTE_SEARCH": "guard_topology_reroute_searches",
        "TRAJ_GUARD_BASE_NO_PATH_LOCAL_ESCAPE":
            "guard_base_no_path_local_escape_arms",
    }
    active_since = None
    active_durations = []
    stamp_pattern = re.compile(r"\[(\d+(?:\.\d+)?)\]")
    same_map_replan_summary_pattern = re.compile(
        r"\[REPLAN_SAME_MAP_COALESCE_SUMMARY\]\s+skipped=(\d+)"
    )
    with open(path, errors="replace") as stream:
        for line in stream:
            same_map_summary = same_map_replan_summary_pattern.search(line)
            if same_map_summary:
                counts["guard_same_map_replan_skips"] = int(
                    same_map_summary.group(1)
                )
            elif "[REPLAN_SAME_MAP_COALESCED]" in line:
                counts["guard_same_map_replan_skips"] += 1
            for marker, key in markers.items():
                if marker in line:
                    counts[key] += 1
            if "[TEST_FAULT_BASE_NO_PATH_ARM]" in line:
                counts["guard_base_no_path_test_injections"] += 1
            if "[TEST_FAULT_BASE_NO_PATH]" in line:
                counts["guard_base_no_path_forced_failures"] += 1
            if "[TEST_FAULT_LOCAL_ESCAPE_ARM]" in line:
                counts["guard_local_escape_test_injections"] += 1
            if "[TEST_FAULT_LOCAL_ESCAPE_DIRECTION_SKIP]" in line:
                counts["guard_local_escape_direction_skips"] += 1
            if "[TRAJ_GUARD_LOCAL_ESCAPE_DIRECTION_REJECTED]" in line:
                counts["guard_local_escape_direction_rejections"] += 1
            if "[TRAJ_GUARD_LOCAL_ESCAPE] action=commit" in line:
                counts["guard_local_escape_commits"] += 1
            if "[TRAJ_GUARD_LOCAL_ESCAPE_REJECTED]" in line:
                counts["guard_local_escape_rejections"] += 1
            if (
                "[TRAJ_GUARD_COMMIT]" in line
                and "footprint_egress=true" in line
            ):
                counts["guard_initial_footprint_egress_commits"] += 1
            if "[TEST_FAULT_INITIAL_FOOTPRINT_OCCUPANCY]" in line:
                counts["guard_initial_footprint_test_injections"] += 1
            if (
                "TRAJ_GUARD_RECOVERED" in line
                and "trigger=full_refresh_ack_timeout" in line
            ):
                counts["full_refresh_ack_timeout_recoveries"] += 1
            if "[TRAJ_GUARD_BRAKE] trigger=" in line:
                counts["guard_brake_successes"] += 1
                if "trigger=main_pre_uncertified" in line:
                    counts["guard_brake_main_pre_successes"] += 1
                elif "trigger=emergency_stop_retry" in line:
                    counts["guard_brake_retry_successes"] += 1
                elif "trigger=full_refresh_ack_timeout" in line:
                    counts["guard_brake_ack_timeout_successes"] += 1
            if "[TRAJ_GUARD_BRAKE_REJECTED]" in line:
                counts["guard_brake_rejections"] += 1
            if "[TRAJ_GUARD_STATIONARY_DEFER]" in line:
                counts["guard_brake_stationary_defers"] += 1
            if "[TRAJ_VELOCITY_SLOWDOWN]" in line:
                counts["trajectory_velocity_slowdowns"] += 1
            if "[TRAJ_VELOCITY_REJECT]" in line:
                counts["trajectory_velocity_rejections"] += 1
            if (
                "[TRAJ_GUARD_CERT] trigger=main_pre status=MAP_STALE"
                in line
            ):
                counts["guard_main_pre_map_stale"] += 1
            if "[TRAJ_GUARD_RECOVERED]" in line:
                counts["guard_recoveries"] += 1
            stamp_match = stamp_pattern.search(line)
            stamp = float(stamp_match.group(1)) if stamp_match else None
            if "[TRAJ_GUARD_RECOVERY_SIGNAL] active=true" in line:
                if active_since is None and stamp is not None:
                    active_since = stamp
            elif "[TRAJ_GUARD_RECOVERY_SIGNAL] active=false" in line:
                if active_since is not None and stamp is not None:
                    active_durations.append(max(0.0, stamp - active_since))
                    active_since = None
    if active_durations:
        counts["guard_recovery_active_duration_s"] = sum(active_durations)
        counts["guard_recovery_active_duration_mean_s"] = st.mean(
            active_durations
        )
        counts["guard_recovery_active_duration_max_s"] = max(
            active_durations
        )
    return counts


class CpuMeter:
    """Average CPU% of the busiest process matching `pattern`, between start()/stop()."""
    def __init__(self, pattern):
        self.pattern = pattern
        self.pid = None
        self.t0 = None
        self.ticks0 = None
        self.t_last = None
        self.ticks_last = None

    def start(self):
        cand = [(proc_ticks(p) or -1, p) for p in pgrep(self.pattern)]
        self.pid = max(cand)[1] if cand else None
        self.t0 = time.time()
        self.ticks0 = proc_ticks(self.pid) if self.pid else None
        self.t_last = self.t0
        self.ticks_last = self.ticks0

    def start_pid(self, pid):
        self.pid = pid
        self.t0 = time.time()
        self.ticks0 = proc_ticks(pid)
        self.t_last = self.t0
        self.ticks_last = self.ticks0

    def start_executable(self, executable_name):
        """Select the real executable, not a `ros2 run`/shell wrapper."""
        candidates = []
        for pid in pgrep(self.pattern):
            try:
                argv0 = open(f"/proc/{pid}/cmdline", "rb").read().split(b"\0", 1)[0]
                argv0 = os.path.basename(os.fsdecode(argv0))
            except OSError:
                continue
            if argv0 == executable_name:
                candidates.append(pid)
        if not candidates:
            self.start()
            return
        # There should be one campaign-owned process. If teardown lag leaves
        # another match, prefer the newest PID instead of wrapper CPU history.
        self.start_pid(max(candidates))

    def sample(self):
        if self.pid is None:
            return
        ticks = proc_ticks(self.pid)
        if ticks is not None:
            self.ticks_last = ticks
            self.t_last = time.time()

    def stop(self):
        if self.pid is None or self.ticks0 is None:
            return None
        self.sample()
        dt = self.t_last - self.t0
        if self.ticks_last is None or dt <= 0:
            return None
        return 100.0 * (self.ticks_last - self.ticks0) / CLK_TCK / dt

LOOP_WPS = "24,24;-24,24;-24,-24;24,-24;0,0"
LOOP_SWITCH = 1.5
LOOP_TIMEOUT = 300.0
SEED12_WPS = "24,24;-24,24"
SEED12_TIMEOUT = 90.0
# seed13 mirrors seed12's corner-obstacle layout and uses the same loop24
# mission and dynamic-trap protocol.
SEED13_WPS = SEED12_WPS
SEED13_TIMEOUT = SEED12_TIMEOUT
# The recovery mission driver owns the approach/hold sequence.  The loop
# monitor watches only the final goal so the controlled hold is not mistaken
# for a failed intermediate waypoint.
RECOVERY_MONITOR_WPS = {
    "seed14": "40,1",
    "seed15": "40,-1",
}
RECOVERY_SWITCH = 1.5
RECOVERY_TIMEOUT = float(os.environ.get("RECOVERY_TIMEOUT_S", "120.0"))
# seed11 = SUPER's public dense MARSIM example (random_map_2_26609.pcd), not
# one of the paper's identified 60-map evaluation assets.  All current seed11
# measurements stop at the single outbound goal, (0,-50) -> (0,50).
REF_WPS = "0,50"
REF_SWITCH = 2.0
REF_TIMEOUT = 90.0
REF_READY_CLOUDS = 5
REF_STATIONARY_WARMUP_S = 3.0
REF_PCD = (
    "/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/pcd/"
    "random_map_2_26609.pcd"
)

# map0 = one of the actual maps from SUPER's own paper data release
# (Zenodo doi.org/10.5281/zenodo.14528604, mock_map_opt_26121_20.pcd),
# NOT the public GitHub demo map (that's seed11). Same +-7.5x110m
# benchmark scale as the paper describes. Start/goal chosen by scanning
# for maximum local point clearance near y=-49/+49 (~0.60 m each).
MAP0_WPS = "-2.5,49"
MAP0_SWITCH = 2.0
MAP0_TIMEOUT = 90.0
MAP0_PCD = (
    "/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/pcd/map0.pcd"
)

# seed12..15 are separate safety/recovery experiments. Keep them opt-in so the
# original efficiency campaign remains seed1..seed11.
MAPS = [f"seed{i}" for i in range(1, 11)] + ["seed11"]
MODES = ["full", "sector", "adaptive"]
VALID_MAPS = tuple(f"seed{i}" for i in range(1, 16)) + ("map0",)
VALID_MODES = (
    "raw", "upstream",
    "raw_v1", "raw_v4", "raw_v7", "raw_v10", "raw_v14", "raw_v18",
    "raw_oneway_repeat", "raw_oneway_once",
    "raw_oneway_once_quiet", "raw_oneway_ready", "raw_oneway_guarded",
    "raw_oneway_guarded_slow",
    "raw_oneway_guarded_v2",
    "raw_oneway_guarded_v2_scheduled",
    "raw_oneway_guarded_v2_reso",
    "raw_oneway_guarded_v2_corridor",
    "raw_oneway_guarded_v2_aligned",
    "raw_oneway_guarded_scheduled",
    "raw_oneway_guarded_margin",
    "full_control_v10", "full_shadow_v10",
    "full_guard_v4", "full_guard_v7", "full_guard_v10",
    "full_guard_reroute_v7",
    "full", "sector", "velocity", "adaptive", "adaptive_baseline", "trigger",
    # Paper-matched speed sweep for the seed1..10 filter ablation itself
    # (max_acc=20 m/s^2, max_vel in the paper's swept set) -- distinct from
    # the raw_v* sweep, which targets seed11/map0's SUPER-as-is comparison.
    *(f"{base}_v{v}" for base in ("full", "sector", "adaptive")
      for v in (1, 4, 7, 10, 14, 18)),
)
SEEDMAP_SPEED_SWEEP = (1, 4, 7, 10, 14, 18)

REFERENCE_ABLATION_PROFILES = {
    # Step 1 isolates repeated versus one-shot goal publication.  Everything
    # else, including ROG visualization, is held fixed.
    "raw_oneway_repeat": {
        "waypoint_config": "waypoint_repeat_1hz.yaml",
        "super_config": "static_reference_raw.yaml",
    },
    "raw_oneway_once": {
        "waypoint_config": "waypoint_goal_once.yaml",
        "super_config": "static_reference_raw.yaml",
    },
    # Step 2 holds goal-once fixed and removes detailed/ROG visualization load.
    "raw_oneway_once_quiet": {
        "waypoint_config": "waypoint_goal_once.yaml",
        "super_config": "static_reference_raw_quiet.yaml",
    },
    # Step 3 keeps the one-shot/quiet profile and starts planning only after
    # accepted scans have actually committed to a fresh map.
    "raw_oneway_ready": {
        "waypoint_config": "waypoint_goal_once.yaml",
        "super_config": "static_reference_raw_ready.yaml",
    },
    # Step 4 continuously validates the committed trajectory against fresh map
    # state and emits a bounded braking trajectory when validation fails.
    "raw_oneway_guarded": {
        "waypoint_config": "waypoint_goal_once.yaml",
        "super_config": "static_reference_raw_guarded.yaml",
    },
    # Step 5b preserves the same guard and reduces only the trajectory dynamic
    # limits, increasing reaction/stopping distance margin.
    "raw_oneway_guarded_slow": {
        "waypoint_config": "waypoint_goal_once.yaml",
        "super_config": "static_reference_raw_guarded_slow.yaml",
    },
    # Step 5a limits only cruise speed; acceleration, jerk, and emergency
    # braking authority stay at the guarded baseline values.
    "raw_oneway_guarded_v2": {
        "waypoint_config": "waypoint_goal_once.yaml",
        "super_config": "static_reference_raw_guarded_v2.yaml",
    },
    # Step 5b additionally reduces optimizer timer pressure so fresh map
    # commits are not starved by 15 Hz replanning.
    "raw_oneway_guarded_v2_scheduled": {
        "waypoint_config": "waypoint_goal_once.yaml",
        "super_config": "static_reference_raw_guarded_v2_scheduled.yaml",
    },
    # Step 5c samples the soft corridor constraints more densely so the
    # polynomial is less likely to cut between optimizer quadrature points.
    "raw_oneway_guarded_v2_reso": {
        "waypoint_config": "waypoint_goal_once.yaml",
        "super_config": "static_reference_raw_guarded_v2_reso.yaml",
    },
    # Step 5d shortens safe-corridor seed lines after denser constraint
    # sampling, reducing corner cutting around inflated obstacles.
    "raw_oneway_guarded_v2_corridor": {
        "waypoint_config": "waypoint_goal_once.yaml",
        "super_config": "static_reference_raw_guarded_v2_corridor.yaml",
    },
    # Step 5e aligns the planner's geometric body radius with the guard's
    # 0.30 m inflated-obstacle margin instead of weakening the map inflation.
    "raw_oneway_guarded_v2_aligned": {
        "waypoint_config": "waypoint_goal_once.yaml",
        "super_config": "static_reference_raw_guarded_v2_aligned.yaml",
    },
    # Step 5c reduces replan timer pressure so committed map updates are not
    # starved by continuous optimization in the shared safety callback group.
    "raw_oneway_guarded_scheduled": {
        "waypoint_config": "waypoint_goal_once.yaml",
        "super_config": "static_reference_raw_guarded_scheduled.yaml",
    },
    # Step 6 aligns the safe-corridor planning radius with the online inflated
    # map (0.30 m) and tightens numerical constraint sampling.
    "raw_oneway_guarded_margin": {
        "waypoint_config": "waypoint_goal_once.yaml",
        "super_config": "static_reference_raw_guarded_margin.yaml",
    },
}
RAW_DIRECT_REF_MODES = frozenset(
    ("raw", "upstream",
     "raw_v1", "raw_v4", "raw_v7", "raw_v10", "raw_v14", "raw_v18",
     *REFERENCE_ABLATION_PROFILES.keys())
)

FIELDS = ["map", "run", "mode", "campaign_sequence_index",
          "mode_order_position", "experiment_profile", "filter_profile",
          "filter_backend",
          "success", "run_valid",
          "monitor_type", "monitor_flight_cpu_pct", "live_cloud_enabled", "preflight_ready",
          "preflight_cloud_messages", "preflight_odom_messages", "goal_messages",
          "position_command_messages", "trajectory_flag2_messages",
          "trajectory_flag3_messages",
          "guard_stop_detected", "guard_stop_time_s",
          "full_refresh_ack_timeouts",
          "full_refresh_recovery_gate_arms",
          "full_refresh_recovery_targets",
          "full_refresh_recovery_acks",
          "full_refresh_ack_timeout_recoveries",
          "guard_same_map_replan_skips",
          "guard_topology_reroute_arms",
          "guard_topology_reroute_searches",
          "guard_base_no_path_local_escape_arms",
          "guard_base_no_path_test_injections",
          "guard_base_no_path_forced_failures",
          "guard_local_escape_test_injections",
          "guard_local_escape_direction_skips",
          "guard_local_escape_direction_rejections",
          "guard_local_escape_commits",
          "guard_local_escape_rejections",
          "guard_initial_footprint_egress_commits",
          "guard_initial_footprint_test_injections",
          "guard_brake_successes", "guard_brake_rejections",
          "guard_brake_stationary_defers",
          "trajectory_velocity_slowdowns",
          "trajectory_velocity_rejections",
          "guard_brake_main_pre_successes",
          "guard_brake_retry_successes",
          "guard_brake_ack_timeout_successes",
          "guard_main_pre_map_stale", "guard_recoveries",
          "guard_recovery_active_duration_s",
          "guard_recovery_active_duration_mean_s",
          "guard_recovery_active_duration_max_s",
          "shadow_safe_candidates", "shadow_unsafe_candidates",
          "shadow_skipped_candidates", "shadow_validated_candidates",
          "shadow_geometric_unsafe", "shadow_map_race",
          "shadow_other_indeterminate",
          "shadow_unsafe_exp", "shadow_unsafe_appended_backup",
          "shadow_unsafe_carry_backup", "shadow_unsafe_stitch",
          "shadow_validation_ms_mean", "shadow_validation_ms_max",
          "shadow_contact_events_with_epoch",
          "shadow_contacts_with_prior_unsafe",
          "shadow_contacts_without_prior_unsafe",
          "shadow_geometric_unsafe_followed_by_contact",
          "shadow_geometric_unsafe_not_followed_by_contact",
          "shadow_nearest_prediction_error_s", "shadow_correlated_segments",
          "first_position_command_s", "first_trajectory_flag2_s",
          "first_trajectory_flag3_s",
          "max_position_command_gap_s", "first_motion_s",
          "start_pose_error_m", "start_pose_valid", "odom_gap_limit_s",
          "max_odom_gap_s", "odom_gap_valid", "mission_time_s", "waypoints_reached",
          "n_waypoints", "collisions", "min_clearance_m",
          "static_pcd_enabled", "static_pcd_point_count",
          "static_pcd_collisions", "static_pcd_min_distance_m",
          "static_pcd_clearance_m", "static_pcd_min_context",
          "static_pcd_contact_r015",
          "static_pcd_contact_r020", "static_pcd_contact_r025",
          "static_pcd_episodes_r015", "static_pcd_episodes_r020",
          "static_pcd_episodes_r025", "contact_event_count",
          "safety_contact_source", "safety_collisions",
          "live_only_contact_event_count",
          "static_confirmed_live_contact_event_count",
          "first_contact_kind", "first_contact_time_s",
          "first_contact_distance_m", "first_contact_x", "first_contact_y",
          "first_contact_z", "first_contact_speed_mps",
          "first_contact_nearest_x", "first_contact_nearest_y",
          "first_contact_nearest_z",
          "first_contact_static_distance_m",
          "first_contact_static_clearance_m",
          "first_contact_static_confirmed",
          "first_contact_live_point_static_distance_m",
          "forensics_json", "samples",
          "clearance_samples",
          "final_x", "final_y", "final_z", "min_x", "max_x", "min_y", "max_y",
          "path_length_m", "max_speed_mps", "max_odom_speed_3d_mps",
          "max_command_speed_mps", "max_command_horizontal_speed_mps",
          "speed_limit_mps", "speed_tolerance_mps", "speed_limit_valid",
          "speed_exceedance_count", "command_speed_exceedance_count",
          "odom_speed_exceedance_count", "first_speed_exceedance_kind",
          "first_speed_exceedance_time_s", "first_speed_exceedance_mps",
          "first_speed_exceedance_trajectory_id",
          "first_speed_exceedance_trajectory_flag",
          "closest_final_goal_distance_m",
          "observed_open_time_s", "observed_open_x", "observed_open_y",
          "observed_close_time_s", "observed_close_x", "observed_close_y",
          "trap_collisions", "trap_min_surface_distance_m", "trap_clearance_m",
          "trap_x", "trap_y", "trigger_x", "trigger_y", "trigger_mismatch_deg",
          "trap_count", "trap_spacing_m", "trap_start_offset_m",
          "trap_first_distance_m", "trap_last_distance_m",
          "trigger_speed_mps", "trap_input_time_s", "trap_kept_time_s",
          "trap_keep_delay_s", "input_body_relative_deg",
          "input_velocity_relative_deg", "kept_body_relative_deg",
          "kept_velocity_relative_deg", "trigger_trap_distance_m",
          "trigger_trap_body_relative_deg",
          "trigger_trap_velocity_relative_deg",
          "trigger_trap_angular_radius_deg",
          "trigger_predicted_x", "trigger_predicted_y",
          "trigger_trap_nudge_deg", "trigger_trap_nudge_lateral_m",
          "event", "valid_spawn", "invalid_reasons", "spawn_time_s",
          "spawn_wall_time_s", "trigger_evaluation_time_s",
          "trigger_evaluation_wall_time_s", "side", "trigger_threshold_x", "trigger_z",
          "trigger_yaw_deg", "trigger_velocity_yaw_deg",
          "trigger_cruise_duration_s", "trigger_cruise_qualified",
          "min_trigger_speed_mps",
          "min_cruise_s", "max_trigger_abs_y_m",
          "max_trigger_velocity_yaw_deg",
          "trigger_abs_y_diagnostic_ok",
          "trigger_velocity_yaw_diagnostic_ok", "wall_x", "blocker_x",
          "blocker_y", "wall_y_min", "wall_y_max", "short_endpoint_y",
          "short_endpoint_x", "long_endpoint_y", "long_endpoint_x",
          "short_endpoint_inner_edge_deg", "long_endpoint_inner_edge_deg",
          "barrier_frame", "local_blocker_forward_m",
          "local_short_endpoint_forward_m", "local_short_endpoint_lateral_m",
          "local_long_endpoint_forward_m", "local_long_endpoint_lateral_m",
          "wall_radius_m", "wall_height_m", "wall_cylinder_count",
          "wall_center_spacing_m", "wall_point_count", "horizon_m",
          "intensity",
          "matched_prefix",
          "filter_half_angle_deg", "filter_reliable_output",
          "filter_stall_v", "filter_stall_t",
          "filter_resume_v", "filter_resume_t", "filter_velocity_yaw_update_v",
          "filter_slowdown_full_refresh_v",
          "filter_slowdown_full_refresh_rearm_v",
          "filter_slowdown_full_refresh_armed",
          "filter_slowdown_full_refresh_pending",
          "filter_slowdown_full_refresh_triggers",
          "filter_slowdown_full_refresh_frames",
          "filter_slowdown_full_refresh_pending_ack",
          "filter_slowdown_full_refresh_ack_count",
          "filter_slowdown_full_refresh_ack_committed_count",
          "filter_slowdown_full_refresh_superseded_count",
          "filter_slowdown_full_refresh_ack_latency_mean_s",
          "filter_slowdown_full_refresh_ack_latency_max_s",
          "filter_frames", "filter_cloud_input_callbacks",
          "filter_cloud_worker_overwrites", "filter_published_frames",
          "filter_rate_limited_frames", "filter_max_publish_hz",
          "filter_map_commit_topic", "filter_map_commit_refresh_age_s",
          "filter_map_commit_refresh_min_interval_s",
          "filter_map_commit_pre_stale_full_age_s",
          "filter_map_commit_pre_stale_ack_retry_age_s",
          "filter_full_refresh_generation_ack_en",
          "filter_map_process_ack_topic",
          "filter_full_refresh_request_topic",
          "filter_map_commit_status_count", "filter_map_commit_version",
          "filter_commit_refresh_frames",
          "filter_pre_stale_full_refresh_frames",
          "filter_pre_stale_full_refresh_ack_count",
          "filter_pre_stale_full_refresh_pending_ack",
          "filter_pre_stale_full_refresh_pending_ack_count",
          "filter_pre_stale_full_refresh_pending_ack_max",
          "filter_pre_stale_full_refresh_ack_committed_count",
          "filter_pre_stale_full_refresh_superseded_count",
          "filter_pre_stale_full_refresh_ack_retry_frames",
          "filter_pre_stale_full_refresh_ack_retry_suppressed_frames",
          "filter_pre_stale_full_refresh_version_advance_count",
          "filter_pre_stale_full_refresh_pending_version_advance",
          "filter_full_refresh_request_count",
          "filter_full_refresh_request_sequence",
          "filter_full_refresh_duplicate_stamp_count",
          "filter_map_process_ack_status_count",
          "filter_map_process_ack_malformed_count",
          "filter_last_map_process_ack_scan_seq",
          "filter_last_map_process_ack_stamp_ns",
          "filter_last_map_process_ack_version",
          "filter_pre_stale_full_refresh_same_version_suppressed_frames",
          "filter_pre_stale_full_refresh_trigger_age_mean_s",
          "filter_pre_stale_full_refresh_trigger_age_max_s",
          "filter_pre_stale_full_refresh_ack_latency_mean_s",
          "filter_pre_stale_full_refresh_ack_latency_max_s",
          "filter_map_commit_age_mean_s",
          "filter_map_commit_age_max_s",
          "filter_full_open_extra_max_points",
          "filter_full_open_extra_candidates",
          "filter_full_open_extra_kept",
          "filter_publish_duty_pct", "filter_input_points", "filter_kept_points",
          "filter_kept_pct", "filter_armed", "filter_armed_duty_pct",
          "filter_open", "filter_open_duty_pct", "filter_open_point_duty_pct",
          "filter_recovery_active", "filter_open_burst_s",
          "filter_open_cooldown_s",
          "filter_near_field_radius_m", "filter_near_field_speed_gain_s",
          "filter_near_field_max_radius_m",
          "filter_max_effective_near_field_radius_m",
          "filter_arm_transitions", "filter_open_transitions",
          "filter_close_transitions", "filter_first_transition_time_s",
          "filter_first_arm_time_s", "filter_first_stall_candidate_time_s",
          "filter_first_open_stall_start_time_s", "filter_first_open_time_s",
          "filter_first_open_delay_s", "filter_first_close_time_s",
          "filter_first_open_duration_s", "filter_stall_candidate_count",
          "filter_max_stall_candidate_duration_s",
          "filter_min_armed_closed_speed_mps",
          "filter_replan_guard_en", "filter_replan_guard_bounded",
          "filter_replan_guard_active", "filter_replan_guard_burst_s",
          "filter_replan_guard_cooldown_s", "filter_replan_fail_streak_open",
          "filter_replan_ok_streak_close", "filter_replan_guard_open",
          "filter_replan_guard_open_transitions",
          "filter_replan_guard_close_transitions",
          "filter_effective_full_open_transitions",
          "filter_effective_full_close_transitions",
          "filter_replan_guard_open_duty_pct",
          "filter_replan_status_count", "filter_replan_fail_count",
          "filter_max_replan_fail_streak",
          "filter_first_replan_guard_open_time_s",
          "filter_first_effective_full_open_time_s",
          "filter_trajectory_guard_topic",
          "filter_trajectory_guard_hold_s",
          "filter_trajectory_guard_active_max_publish_hz",
          "filter_trajectory_guard_ack_retry_age_s",
          "filter_trajectory_guard_active",
          "filter_trajectory_guard_open",
          "filter_trajectory_guard_status_count",
          "filter_trajectory_guard_active_count",
          "filter_trajectory_guard_open_transitions",
          "filter_trajectory_guard_close_transitions",
          "filter_trajectory_guard_refresh_frames",
          "filter_trajectory_guard_full_refresh_pending_ack",
          "filter_trajectory_guard_full_refresh_pending_ack_max",
          "filter_trajectory_guard_full_refresh_ack_count",
          "filter_trajectory_guard_full_refresh_ack_committed_count",
          "filter_trajectory_guard_full_refresh_superseded_count",
          "filter_trajectory_guard_full_refresh_ack_retry_frames",
          "filter_trajectory_guard_full_refresh_abandoned_count",
          "filter_trajectory_guard_full_refresh_ack_latency_mean_s",
          "filter_trajectory_guard_full_refresh_ack_latency_max_s",
          "filter_test_drop_first_trajectory_guard_full_cloud",
          "filter_test_dropped_trajectory_guard_full_clouds",
          "filter_trajectory_guard_open_duty_pct",
          "filter_trajectory_guard_active_frames",
          "filter_trajectory_guard_hold_only_frames",
          "filter_trajectory_guard_active_published_frames",
          "filter_trajectory_guard_hold_only_published_frames",
          "filter_trajectory_guard_active_duty_pct",
          "filter_trajectory_guard_hold_only_duty_pct",
          "filter_first_trajectory_guard_open_time_s",
          "recovery_triggered",
          "recovery_reclosed", "recovery_spawn_after_arm",
          "recovery_open_after_spawn", "recovery_open_during_hold",
          "recovery_success",
          "mission_driver_phase", "mission_driver_start_delay_s",
          "mission_driver_approach_radius_m",
          "mission_driver_hold_low_speed_s", "mission_driver_low_speed_v",
          "mission_driver_approach_start_time_s",
          "mission_driver_approach_start_wall_time_s",
          "mission_driver_approach_start_speed_mps",
          "mission_driver_hold_start_time_s",
          "mission_driver_hold_start_wall_time_s",
          "mission_driver_hold_start_speed_mps",
          "mission_driver_hold_start_distance_m",
          "mission_driver_release_time_s",
          "mission_driver_release_wall_time_s",
          "mission_driver_release_speed_mps",
          "mission_driver_release_low_speed_duration_s",
          "pts_mean", "map_perf_frames", "map_frames_s", "map_points_s",
          "map_payload_bytes_mean", "map_payload_bytes_total",
          "map_payload_mib_s", "map_payload_mbps", "map_point_step_mean",
          "total_ms_mean", "raycast_ms_mean", "update_ms_mean",
          "inflation_ms_mean", "kept_pct", "fsm_cpu_pct", "filter_cpu_pct",
          "monitor_cpu_pct",
          "cgroup_cpu_accounting", "cgroup_cpu_duration_s",
          "cgroup_memory_source", "cgroup_accounting_error",
          "algorithm_cpu_core_s", "algorithm_cpu_cores_mean",
          "algorithm_cpu_cores_p95_1s", "algorithm_cpu_cores_max_1s",
          "algorithm_peak_rss_mib", "algorithm_peak_pss_mib",
          "algorithm_peak_swap_mib", "algorithm_max_processes",
          "end_to_end_cpu_core_s", "end_to_end_cpu_cores_mean",
          "end_to_end_cpu_cores_p95_1s", "end_to_end_cpu_cores_max_1s",
          "end_to_end_peak_rss_mib", "end_to_end_peak_pss_mib",
          "end_to_end_peak_swap_mib", "end_to_end_max_processes",
          "cgroup_cpu_trace_csv",
          "attempt_count", "retry_count", "first_attempt_success",
          "retry_reasons", "oom_kill_delta",
          "fsm_peak_rss_mib", "fsm_peak_pss_mib", "fsm_peak_swap_mib",
          "system_min_available_mib", "system_peak_swap_used_mib",
          "cgroup_peak_memory_mib", "cgroup_peak_swap_mib",
          "memory_psi_some_avg10_max", "memory_psi_full_avg10_max",
          "memory_trace_csv",
          "perf_log_generation_ready", "perf_window_valid",
          "perf_trace_csv", "perf_row_start", "perf_row_end", "input_distance_m",
          "kept_distance_m"]


def log(msg):
    print(f"[native_campaign {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def kill_all():
    for n in ("perfect_drone_node", "fsm_node", "waypoint_mission", "native_sector.py",
              "native_sector_cpp",
              "native_loop_monitor.py", "native_reference_monitor.py",
              "native_seed12_scenario.py",
              "native_recovery_scenario.py", "native_recovery_mission.py"):
        subprocess.run(["pkill", "-9", "-f", n], stderr=subprocess.DEVNULL)
    time.sleep(1.5)


def kill_group(proc):
    if proc is None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except ProcessLookupError:
        pass


def terminate_group(proc, grace_s=1.0):
    """Give a process tree a chance to flush diagnostics before SIGKILL."""
    if proc is None:
        return
    try:
        process_group = os.getpgid(proc.pid)
        os.killpg(process_group, signal.SIGINT)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + grace_s
    while proc.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    if proc.poll() is None:
        try:
            os.killpg(process_group, signal.SIGKILL)
        except ProcessLookupError:
            pass


def perf_row_count():
    try:
        with open(PERF_LOG) as f:
            return max(0, sum(1 for _ in f) - 1)
    except OSError:
        return 0


def perf_log_signature():
    """Identify the current ROG-Map performance-log generation."""
    try:
        stat = os.stat(PERF_LOG)
        return stat.st_mtime_ns, stat.st_size
    except OSError:
        return None


def wait_for_perf_log_generation(previous_signature, timeout_s=30.0,
                                 poll_s=0.05):
    """Wait until the newly launched ROG-Map has truncated/opened its log.

    Large static maps can take more than the historical fixed four-second
    startup delay to construct.  Taking ``perf_row_start`` before that point
    races ROGMap::init(), whose ofstream opens the shared CSV with ``trunc``.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        signature = perf_log_signature()
        if signature is not None and signature != previous_signature:
            try:
                with open(PERF_LOG) as perf_file:
                    header = perf_file.readline()
                if "PointCloudNumber" in header and "Total" in header:
                    return True
            except OSError:
                pass
        time.sleep(poll_s)
    return False


def slice_perf(start, end, perf_log=PERF_LOG, duration_s=None):
    try:
        rows = list(csv.reader(open(perf_log)))
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
    def values(name):
        if name not in col:
            return []
        return [r[col[name]] for r in seg]
    def m(name, scale):
        vals = values(name)
        return st.mean(vals) * scale if vals else None
    point_values = values("PointCloudNumber")
    payload_values = values("PointCloudPayloadBytes")
    result = {
        "pts_mean": st.mean(point_values) if point_values else None,
        "map_perf_frames": len(seg),
        "map_payload_bytes_mean": (
            st.mean(payload_values) if payload_values else None
        ),
        "map_payload_bytes_total": (
            sum(payload_values) if payload_values else None
        ),
        "map_point_step_mean": m("PointCloudPointStep", 1),
        "total_ms_mean": m("Total", 1000),
        "raycast_ms_mean": m("Raycast", 1000),
        "update_ms_mean": m("Update_cache", 1000),
        "inflation_ms_mean": m("Inflation", 1000),
    }
    if duration_s is not None and duration_s > 0:
        result["map_frames_s"] = len(seg) / duration_s
        result["map_points_s"] = (
            sum(point_values) / duration_s if point_values else None
        )
        result["map_payload_mib_s"] = (
            sum(payload_values) / duration_s / (1024.0 * 1024.0)
            if payload_values else None
        )
        result["map_payload_mbps"] = (
            sum(payload_values) * 8.0 / duration_s / 1e6
            if payload_values else None
        )
    return result


def build_loop_monitor_command(wps, switch, timeout, out_json, monitor_options=""):
    """Build a monitor command with options before the positional delimiter."""
    return (
        f"python3 {LOOP_MON}{monitor_options} -- "
        f"'{wps}' {switch} {timeout} {out_json}"
    )


def run_one(map_name, mode, run, attempt_max=3, artifacts_dir=None,
            seedmap_super_config_override=None,
            seedmap_static_pcd=False,
            loop_timeout_override=None,
            filter_profile="legacy",
            filter_backend="python",
            adaptive_max_publish_hz=5.0,
            adaptive_slowdown_full_refresh_v=0.0,
            adaptive_slowdown_full_refresh_rearm_v=0.0,
            adaptive_trajectory_guard_hold_s=2.5,
            adaptive_trajectory_guard_active_max_publish_hz=0.0,
            adaptive_trajectory_guard_ack_retry_age_s=0.0,
            adaptive_test_drop_first_trajectory_guard_full_cloud=False,
            adaptive_pre_stale_full_age_s=0.25,
            adaptive_pre_stale_ack_retry_age_s=0.0,
            adaptive_full_refresh_generation_ack=True,
            filtered_reliable_map_link=False,
            adaptive_full_open_extra_max_points=6000,
            test_force_local_escape_once=False,
            test_force_initial_footprint_egress_once=False,
            cgroup_cpu_accounting=False):
    is_ref = (map_name == "seed11")  # SUPER public dense MARSIM example
    is_map0 = (map_name == "map0")  # SUPER paper's own Zenodo-released map
    is_seed12 = (map_name == "seed12")
    is_seed13 = (map_name == "seed13")
    is_dynamic = is_seed12 or is_seed13
    is_recovery = map_name in ("seed14", "seed15")
    # Paper-matched speed sweep on the seed1..10 filter ablation itself:
    # "sector_v10" -> filter mode "sector" run under static_seedmaps_paper_v10.yaml
    # (max_acc=20 m/s^2, max_vel=10) instead of the default static_seedmaps.yaml
    # (max_acc=15, max_vel=3) used by the plain full/sector/adaptive modes.
    is_seedmap_shadow = mode == "full_shadow_v10"
    guard_sweep_match = re.match(
        r"^full_guard(?:_reroute)?_v(4|7|10)$", mode
    )
    is_seedmap_guard = guard_sweep_match is not None
    is_seedmap_guard_reroute = mode.startswith("full_guard_reroute_")
    is_seedmap_observed_control = mode == "full_control_v10"
    is_seedmap_observed = (
        is_seedmap_shadow or is_seedmap_guard or is_seedmap_observed_control
    )
    seedmap_sweep_match = re.match(r"^(full|sector|adaptive)_v(\d+)$", mode)
    base_mode = (
        "full" if is_seedmap_observed
        else "adaptive" if mode == "adaptive_baseline"
        else seedmap_sweep_match.group(1) if seedmap_sweep_match
        else mode
    )
    sweep_vel = (
        float(guard_sweep_match.group(1)) if is_seedmap_guard
        else 10.0 if is_seedmap_observed
        else float(seedmap_sweep_match.group(2)) if seedmap_sweep_match
        else None
    )
    matched_prefix = (
        is_dynamic
        and os.environ.get(f"{map_name.upper()}_MATCHED_PREFIX", "0").lower()
        in ("1", "true", "yes", "on")
    )
    override_cloud_topic = super_config_cloud_topic(
        seedmap_super_config_override
    )
    if (
        base_mode in ("sector", "adaptive")
        and seedmap_super_config_override
        and override_cloud_topic != "/cloud_sector"
    ):
        raise ValueError(
            f"{base_mode} requires a SUPER config whose cloud_topic is "
            f"/cloud_sector; {seedmap_super_config_override} uses "
            f"{override_cloud_topic or 'an unknown topic'}"
        )
    if is_ref or is_map0:
        base_wps, base_switch, base_timeout = (
            (MAP0_WPS, MAP0_SWITCH, MAP0_TIMEOUT) if is_map0
            else (REF_WPS, REF_SWITCH, REF_TIMEOUT)
        )
        wps, switch, timeout = base_wps, base_switch, base_timeout
        if mode.startswith("raw_v") and mode[5:].isdigit():
            # ~100 m goal; give generous margin over 100/max_vel so slow
            # sweep points (e.g. raw_v1 -> ~100s cruise) don't time out.
            sweep_vel = float(mode[5:])
            timeout = max(base_timeout, 100.0 / sweep_vel * 2.0 + 30.0)
    elif is_seed12:
        wps, switch, timeout = SEED12_WPS, LOOP_SWITCH, SEED12_TIMEOUT
    elif is_seed13:
        wps, switch, timeout = SEED13_WPS, LOOP_SWITCH, SEED13_TIMEOUT
    elif is_recovery:
        wps, switch, timeout = (
            RECOVERY_MONITOR_WPS[map_name],
            RECOVERY_SWITCH,
            RECOVERY_TIMEOUT,
        )
    else:
        wps, switch, timeout = LOOP_WPS, LOOP_SWITCH, LOOP_TIMEOUT
        if sweep_vel is not None:
            # loop24's four-corner path is ~220-250 m total; scale the
            # timeout so low sweep speeds (e.g. 1 m/s -> ~250s cruise)
            # don't time out and high speeds don't wait needlessly.
            timeout = max(60.0, 250.0 / sweep_vel + 60.0)
        if is_seedmap_guard_reroute:
            # Certified stop-and-reroute deliberately trades time for safety.
            # Keep the ordinary v7 cohort's 95.71 s budget unchanged, while
            # giving this explicitly named recovery experiment enough time to
            # distinguish eventual recovery from a true geometric deadlock.
            timeout = max(timeout, 120.0)
        # An explicit campaign override is authoritative.  Applying it before
        # the speed/reroute defaults silently changed --loop-timeout 140 back
        # to 120 for full_guard_reroute_v7.
        if loop_timeout_override is not None:
            timeout = loop_timeout_override
    tag = f"{map_name}_run{run}_{mode}"
    oom_kill_start = read_cgroup_event("oom_kill")
    retry_reasons = []
    memory_summaries = []
    memory_trace_paths = []

    for attempt in range(1, attempt_max + 1):
        kill_all()
        # Every attempt gets unique evidence paths. A retry must never replace
        # the stack/memory trace that explains the first-attempt failure.
        attempt_tag = f"{tag}.attempt{attempt}"
        out_json = os.path.join(TMPDIR, f"{attempt_tag}.json")
        filt_log = os.path.join(TMPDIR, f"{attempt_tag}.filt.log")
        filt_event_json = os.path.join(TMPDIR, f"{attempt_tag}.filt_event.json")
        filt_stats_json = os.path.join(TMPDIR, f"{attempt_tag}.filt_stats.json")
        scenario_log = os.path.join(TMPDIR, f"{attempt_tag}.scenario.log")
        scenario_event_json = os.path.join(TMPDIR, f"{attempt_tag}.scenario_event.json")
        scenario_trace_csv = os.path.join(TMPDIR, f"{attempt_tag}.scenario_trace.csv")
        mission_log = os.path.join(TMPDIR, f"{attempt_tag}.mission.log")
        mission_event_json = os.path.join(TMPDIR, f"{attempt_tag}.mission_event.json")
        reference_monitor_log = os.path.join(TMPDIR, f"{attempt_tag}.reference_monitor.log")
        reference_stack_log = os.path.join(TMPDIR, f"{attempt_tag}.stack.log")
        memory_trace_csv = os.path.join(TMPDIR, f"{attempt_tag}.memory.csv")
        cgroup_trace_csv = os.path.join(TMPDIR, f"{attempt_tag}.cgroup.csv")
        perf_trace_csv = os.path.join(TMPDIR, f"{attempt_tag}.performance.csv")
        ready_json = os.path.join(TMPDIR, f"{attempt_tag}.ready.json")
        for path in (
            out_json,
            filt_event_json,
            filt_stats_json,
            scenario_event_json,
            scenario_trace_csv,
            mission_event_json,
            ready_json,
            ready_json + ".tmp",
            cgroup_trace_csv,
            perf_trace_csv,
        ):
            if os.path.exists(path):
                os.remove(path)

        scenario_proc = None
        recovery_mission_proc = None
        reference_mission_proc = None
        if is_dynamic:
            # seed13's mirrored funnel geometry needed more reaction margin
            # than seed12's original layout to separate sector from adaptive
            # (n=10 at seed12's tuned settings gave 1/10 collisions for ALL
            # three modes -- no signal). Widen prediction/trigger-distance
            # further for seed13 only; leave seed12's already-validated
            # settings untouched.
            prediction_s = 0.6 if is_seed13 else 0.7
            trigger_distance_max = 2.0 if is_seed13 else 2.5
            # 3-point/0.25m-radius rough trap leaves a residual ~5% collision
            # rate on BOTH full and adaptive at seed13's tight timing (2/40
            # runs, both instant-detected but still clipped). Tried thinning
            # to 2 points (worse: full 20%/sector 65%/adaptive 15% at n=20)
            # and shrinking radius to 0.20 (no clear improvement, full 20%/
            # sector 40%/adaptive 10% at n=10) -- neither helped, reverted to
            # the original 3-point/0.25m config. full hitting the same ~5%
            # floor as adaptive indicates this residual isn't a sector-filter
            # effect at all (full has no angular blind spot) -- it's the
            # scenario's own worst-case reaction-time limit, so a true 0%
            # for adaptive specifically isn't achievable without also
            # trivializing the trap for sector (destroying the comparison).
            scenario_cmd = (
                f"python3 {SEED12_SCENARIO} "
                f"--prediction-s {prediction_s} "
                f"--nudge-outside-sector "
                f"--trigger-distance-min 0.6 --trigger-distance-max {trigger_distance_max} "
                f"--radius-m 0.25 "
                f"--rough-trap-count 3 --rough-trap-start-m 0.20 "
                f"--rough-trap-spacing-m 0.35 "
                f"--hold-s 0.02 "
                f"--event-json {scenario_event_json} "
                f"--trace-csv {scenario_trace_csv} "
                f"> {scenario_log} 2>&1"
            )
            scenario_proc = subprocess.Popen(
                ["bash", "-c", f"{ROS_ENV} && {scenario_cmd}"],
                preexec_fn=os.setsid,
            )
            time.sleep(0.5)
        elif is_recovery:
            side = "left" if map_name == "seed14" else "right"
            scenario_cmd = (
                f"python3 {RECOVERY_SCENARIO} --side {side} "
                "--trigger-x 18.0 "
                f"--event-json {scenario_event_json} "
                f"> {scenario_log} 2>&1"
            )
            scenario_proc = subprocess.Popen(
                ["bash", "-c", f"{ROS_ENV} && {scenario_cmd}"],
                preexec_fn=os.setsid,
            )
            time.sleep(0.5)
            mission_cmd = (
                f"python3 {RECOVERY_MISSION} --side {side} "
                f"--event-json {mission_event_json} "
                f"> {mission_log} 2>&1"
            )
            recovery_mission_proc = subprocess.Popen(
                ["bash", "-c", f"{ROS_ENV} && {mission_cmd}"],
                preexec_fn=os.setsid,
            )

        # The guarded full profile subscribes directly to /cloud_registered.
        # Starting native_sector in passthrough mode would deserialize and
        # republish the same large cloud for no consumer, wasting CPU needed
        # by the simulator renderer and safety callbacks.
        raw_direct = ((is_ref or is_map0) and mode in RAW_DIRECT_REF_MODES) or (
            is_seedmap_guard
        ) or (
            base_mode == "full" and
            override_cloud_topic == "/cloud_registered"
        )
        filter_options = f" --stats-json {filt_stats_json}"
        if filter_profile == "strict-burst" and base_mode != "full":
            # A fixed-sector ablation must remain a fixed sector.  Adaptive
            # keeps velocity alignment and stall recovery, but recovery uses
            # bounded full-cloud bursts instead of the legacy nearly
            # continuous replan-failure opening.
            if base_mode == "adaptive":
                filter_options += (
                    " --open-burst-s 0.6 --open-cooldown-s 1.4"
                    " --bounded-replan-guard --replan-fail-streak-open 3"
                    " --replan-open-burst-s 0.6"
                    " --replan-open-cooldown-s 1.4"
                    f" --max-publish-hz {adaptive_max_publish_hz}"
                    f" --trajectory-guard-hold-s "
                    f"{adaptive_trajectory_guard_hold_s}"
                    f" --trajectory-guard-active-max-publish-hz "
                    f"{adaptive_trajectory_guard_active_max_publish_hz}"
                    f" --trajectory-guard-ack-retry-age-s "
                    f"{adaptive_trajectory_guard_ack_retry_age_s}"
                    f"{' --test-drop-first-trajectory-guard-full-cloud' if adaptive_test_drop_first_trajectory_guard_full_cloud else ''}"
                    f" --map-commit-pre-stale-full-age-s "
                    f"{adaptive_pre_stale_full_age_s}"
                    f" --map-commit-pre-stale-ack-retry-age-s "
                    f"{adaptive_pre_stale_ack_retry_age_s}"
                    f"{' --full-refresh-generation-ack' if adaptive_full_refresh_generation_ack else ''}"
                    f" --full-open-extra-max-points "
                    f"{adaptive_full_open_extra_max_points}"
                    " --near-field-speed-gain-s 0.2"
                    " --near-field-max-radius-m 3.0"
                )
                if filter_backend == "cpp":
                    filter_options += (
                        f" --slowdown-full-refresh-v "
                        f"{adaptive_slowdown_full_refresh_v}"
                        f" --slowdown-full-refresh-rearm-v "
                        f"{adaptive_slowdown_full_refresh_rearm_v}"
                    )
            else:
                filter_options += " --no-replan-guard"
            if filtered_reliable_map_link:
                filter_options += " --reliable-output"
        if is_dynamic:
            filter_options += (
                f" --input-topic /cloud_seed12 --track-trap "
                f"--event-json {filt_event_json}"
            )
            if matched_prefix:
                filter_options += " --sector-until-trap"
        elif is_recovery:
            filter_options += " --input-topic /cloud_recovery"
        filt_proc = None
        if not raw_direct:
            filter_command = (
                f"python3 {SECTOR}"
                if filter_backend == "python"
                else f"ros2 run mission_planner {SECTOR_CPP_EXECUTABLE}"
            )
            filt_proc = subprocess.Popen(
                [
                    "bash",
                    "-c",
                    f"{ROS_ENV} && {filter_command} {base_mode}{filter_options} "
                    f"> {filt_log} 2>&1",
                ],
                preexec_fn=os.setsid,
            )
        # The filter must be subscribed before the recovery driver's 3 s
        # auto-start (and before waypoint_mission on the standard maps).
        time.sleep(1.0)

        active_super_config = None
        if is_ref:
            if mode in REFERENCE_ABLATION_PROFILES:
                super_config = REFERENCE_ABLATION_PROFILES[mode]["super_config"]
                launch_cmd = (
                    "{ ros2 run perfect_drone_sim perfect_drone_node --ros-args "
                    "-p config_name:=dense.yaml & "
                    "ros2 run super_planner fsm_node --ros-args "
                    f"-p config_name:={super_config} & wait; }} "
                    f"> {reference_stack_log} 2>&1"
                )
            elif mode == "raw":
                super_config = "static_reference_raw.yaml"
            elif mode.startswith("raw_v") and mode[5:].isdigit():
                # Paper speed-sweep replication: "maximum velocity varying
                # from 1 to 18 m/s" at a fixed max_acc=20 m/s^2. Each
                # raw_vN config is static_reference_raw.yaml with only
                # max_vel changed to N.
                super_config = f"static_reference_raw_v{mode[5:]}.yaml"
            elif mode == "upstream":
                super_config = "static_upstream_raw.yaml"
            else:
                super_config = "static_reference.yaml"
            if mode not in REFERENCE_ABLATION_PROFILES:
                launch_cmd = (
                    "ros2 launch mission_planner benchmark_reference.launch.py "
                    f"super_config:={super_config}"
                )
            active_super_config = super_config
        elif is_map0:
            # map0 only supports the plain raw-direct comparison and the
            # paper's speed sweep -- none of seed11's ablation-debugging
            # profiles apply here.
            if mode == "raw":
                super_config = "static_reference_raw.yaml"
            elif mode.startswith("raw_v") and mode[5:].isdigit():
                super_config = f"static_reference_raw_v{mode[5:]}.yaml"
            else:
                super_config = "static_reference_raw.yaml"
            launch_cmd = (
                "ros2 launch mission_planner benchmark_map0.launch.py "
                f"super_config:={super_config}"
            )
            active_super_config = super_config
        elif is_recovery:
            launch_cmd = (
                "{ ros2 run perfect_drone_sim perfect_drone_node --ros-args "
                f"-p config_name:={map_name}.yaml & "
                "ros2 run super_planner fsm_node --ros-args "
                "-p config_name:=static_recovery.yaml & wait; }"
            )
            active_super_config = "static_recovery.yaml"
        else:
            if is_seedmap_shadow:
                seedmap_super_config = "static_seedmaps_shadow_v10.yaml"
            elif is_seedmap_guard:
                profile_suffix = (
                    f"reroute_v{int(sweep_vel)}"
                    if is_seedmap_guard_reroute
                    else f"v{int(sweep_vel)}"
                )
                seedmap_super_config = f"static_seedmaps_guard_{profile_suffix}.yaml"
            elif is_seedmap_observed_control:
                seedmap_super_config = "static_seedmaps_paper_v10.yaml"
            else:
                seedmap_super_config = (
                    f"static_seedmaps_paper_v{int(sweep_vel)}.yaml"
                    if sweep_vel is not None else "static_seedmaps.yaml"
                )
            if seedmap_super_config_override:
                seedmap_super_config = seedmap_super_config_override
            active_super_config = seedmap_super_config
            launch_cmd = (
                "ros2 launch mission_planner benchmark_seedmap.launch.py "
                f"waypoint_data:=loop24.txt drone_config:={map_name}.yaml "
                f"super_config:={seedmap_super_config}"
            )
            if is_seedmap_observed or seedmap_super_config_override:
                launch_cmd += f" > {reference_stack_log} 2>&1"
        if test_force_local_escape_once:
            launch_cmd = "SUPER_TEST_FORCE_LOCAL_ESCAPE_ONCE=1 " + launch_cmd
        if test_force_initial_footprint_egress_once:
            launch_cmd = (
                "SUPER_TEST_FORCE_INITIAL_FOOTPRINT_EGRESS_ONCE=1 "
                + launch_cmd
            )
        perf_log_before_launch = perf_log_signature()
        launch_proc = subprocess.Popen(
            ["bash", "-c", f"{ROS_ENV} && {launch_cmd}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
        time.sleep(4)

        # confirm fsm_node actually came up
        up = subprocess.run(["pgrep", "-f", "fsm_node"], stdout=subprocess.DEVNULL).returncode == 0
        if not up:
            retry_reasons.append("fsm_node did not start")
            log(f"  {tag} attempt {attempt}/{attempt_max}: fsm_node did not start -> retry")
            kill_group(launch_proc)
            kill_group(filt_proc)
            kill_group(scenario_proc)
            kill_group(recovery_mission_proc)
            continue

        required_processes = []
        if filt_proc is not None:
            required_processes.append(("filter", filt_proc))
        if scenario_proc is not None:
            required_processes.append(("scenario", scenario_proc))
        if recovery_mission_proc is not None:
            required_processes.append(("recovery mission", recovery_mission_proc))
        exited = [name for name, proc in required_processes if proc.poll() is not None]
        if exited:
            retry_reasons.append(f"{', '.join(exited)} exited during startup")
            log(
                f"  {tag} attempt {attempt}/{attempt_max}: "
                f"{', '.join(exited)} exited during startup -> retry"
            )
            kill_group(launch_proc)
            kill_group(filt_proc)
            kill_group(scenario_proc)
            kill_group(recovery_mission_proc)
            continue

        perf_log_generation_ready = wait_for_perf_log_generation(
            perf_log_before_launch
        )
        if not perf_log_generation_ready:
            log(
                f"  {tag} attempt {attempt}/{attempt_max}: performance log "
                "did not open a new generation before measurement"
            )

        is_reference_ablation = mode in REFERENCE_ABLATION_PROFILES
        if is_reference_ablation:
            mon_cmd = (
                f"python3 {REFERENCE_MON} '{wps}' {switch} {timeout} {out_json} "
                f"--static-pcd {REF_PCD} --ready-file {ready_json} "
                f"--ready-clouds {REF_READY_CLOUDS} "
                f"{'--stop-on-sticky-flag3-s 5.0' if mode.startswith('raw_oneway_guarded') else ''} "
                f"> {reference_monitor_log} 2>&1"
            )
            mon_proc = subprocess.Popen(
                ["bash", "-c", f"{ROS_ENV} && {mon_cmd}"],
                preexec_fn=os.setsid,
            )
            ready_deadline = time.monotonic() + 45.0
            while (
                mon_proc.poll() is None
                and not os.path.exists(ready_json)
                and time.monotonic() < ready_deadline
            ):
                time.sleep(0.1)
            if mon_proc.poll() is not None or not os.path.exists(ready_json):
                retry_reasons.append("reference monitor did not reach READY")
                log(
                    f"  {tag} attempt {attempt}/{attempt_max}: "
                    "reference monitor did not reach READY -> retry"
                )
                kill_group(mon_proc)
                kill_group(launch_proc)
                kill_all()
                continue
            # The monitor is subscribed and the sensor has produced multiple
            # scans.  Keep the vehicle stationary while ROG consumes them.
            time.sleep(REF_STATIONARY_WARMUP_S)

        row_start = perf_row_count()
        fsm_cpu = CpuMeter("fsm_node")
        filt_cpu = CpuMeter(
            "native_sector.py"
            if filter_backend == "python" else SECTOR_CPP_EXECUTABLE
        )
        fsm_cpu.start()
        memory_meter = MemoryMeter(fsm_cpu.pid, memory_trace_csv)
        memory_trace_paths.append(memory_trace_csv)
        memory_meter.sample()
        if filt_proc is not None:
            if filter_backend == "cpp":
                filt_cpu.start_executable(SECTOR_CPP_EXECUTABLE)
            else:
                filt_cpu.start()

        cgroup_meter = None
        cgroup_summary = {
            "cgroup_cpu_accounting": False,
            "cgroup_accounting_error": None,
        }
        if cgroup_cpu_accounting:
            try:
                cgroup_meter = CgroupRunMeter(attempt_tag, cgroup_trace_csv)
                if cgroup_meter.assign_tree(launch_proc.pid, "stack") == 0:
                    raise RuntimeError("launch process tree could not be assigned")
                if filt_proc is not None:
                    if cgroup_meter.assign_tree(filt_proc.pid, "algorithm") == 0:
                        raise RuntimeError("filter process tree could not be assigned")
                if not cgroup_meter.assign_pid(fsm_cpu.pid, "algorithm"):
                    raise RuntimeError("fsm_node could not be assigned")
                if scenario_proc is not None:
                    cgroup_meter.assign_tree(scenario_proc.pid, "stack")
                if recovery_mission_proc is not None:
                    cgroup_meter.assign_tree(recovery_mission_proc.pid, "stack")
                cgroup_meter.start()
            except Exception as error:
                if cgroup_meter is not None:
                    cgroup_meter.cleanup()
                raise RuntimeError(
                    f"required cgroup CPU accounting failed: {error}"
                ) from error

        if is_reference_ablation:
            waypoint_config = REFERENCE_ABLATION_PROFILES[mode]["waypoint_config"]
            reference_mission_cmd = (
                "ros2 run mission_planner waypoint_mission --ros-args "
                f"-p config_name:={waypoint_config} "
                "-p data_name:=benchmark_outbound.txt "
                f"> {mission_log} 2>&1"
            )
            reference_mission_proc = subprocess.Popen(
                ["bash", "-c", f"{ROS_ENV} && {reference_mission_cmd}"],
                preexec_fn=os.setsid,
            )
            if cgroup_meter is not None:
                cgroup_meter.assign_tree(reference_mission_proc.pid, "stack")
            monitor_pattern = "native_reference_monitor.py"
        else:
            if is_dynamic:
                monitor_options = " --cloud-topic /cloud_seed12"
            elif is_recovery:
                monitor_options = (
                    " --cloud-topic /cloud_recovery --trap-intensity 14015"
                )
            else:
                monitor_options = ""
            if is_ref:
                monitor_options += f" --static-pcd {REF_PCD}"
            elif is_map0:
                monitor_options += f" --static-pcd {MAP0_PCD}"
            elif is_seedmap_observed or seedmap_static_pcd:
                monitor_options += (
                    " --static-pcd /root/super_ws/src/SUPER/"
                    "mars_uav_sim/perfect_drone_sim/pcd/seed_maps/"
                    f"{map_name}.pcd"
                )
            speed_limit_mps = super_config_max_velocity(active_super_config)
            if speed_limit_mps is not None:
                monitor_options += (
                    f" --speed-limit-mps {speed_limit_mps:.9g}"
                    " --speed-tolerance-mps 0.01"
                )
            # Options must precede "--". Everything after it is positional,
            # protecting waypoint strings that start with "-" (for example
            # map0's negative-x goal).
            mon_cmd = build_loop_monitor_command(
                wps, switch, timeout, out_json, monitor_options
            )
            mon_proc = subprocess.Popen(
                ["bash", "-c", f"{ROS_ENV} && {mon_cmd}"],
                preexec_fn=os.setsid,
            )
            monitor_pattern = "native_loop_monitor.py"

        monitor_cpu = CpuMeter(monitor_pattern)
        # The shell waits on the Python child, so sampling the wrapper PID
        # reports 0%. Resolve the actual monitor process by command pattern.
        monitor_cpu.start()
        monitor_deadline = time.monotonic() + timeout + 30
        runtime_process_failure = None
        while mon_proc.poll() is None and time.monotonic() < monitor_deadline:
            time.sleep(1.0)
            monitor_cpu.sample()
            memory_meter.sample()
            if cgroup_meter is not None:
                cgroup_meter.sample()
            if not pgrep("/fsm_node"):
                runtime_process_failure = "fsm_node exited during mission"
                break
            if filt_proc is not None and filt_proc.poll() is not None:
                runtime_process_failure = "filter exited during mission"
                break
        if runtime_process_failure is not None:
            if cgroup_meter is not None:
                cgroup_meter.sample(force_memory=True)
                cgroup_summary = cgroup_meter.summary()
            memory_summaries.append(memory_meter.summary())
            retry_reasons.append(runtime_process_failure)
            log(
                f"  {tag} attempt {attempt}/{attempt_max}: "
                f"{runtime_process_failure} -> retry"
            )
            kill_group(mon_proc)
            kill_group(filt_proc)
            kill_group(launch_proc)
            kill_all()
            if cgroup_meter is not None:
                cgroup_meter.cleanup()
            continue
        if mon_proc.poll() is None:
            log(f"  {tag}: monitor HUNG -> kill")
            kill_group(mon_proc)

        memory_meter.sample()
        memory_summaries.append(memory_meter.summary())
        if cgroup_meter is not None:
            cgroup_meter.sample(force_memory=True)
            cgroup_summary = cgroup_meter.summary()

        fsm_cpu_pct = fsm_cpu.stop()
        filter_cpu_pct = filt_cpu.stop() if filt_proc is not None else None
        monitor_cpu_pct = monitor_cpu.stop()
        row_end = perf_row_count()
        perf_window_valid = bool(
            perf_log_generation_ready and row_end > row_start
        )
        try:
            shutil.copyfile(PERF_LOG, perf_trace_csv)
        except OSError:
            pass

        # Backward-compatible fallback when a filter predates --stats-json.
        kept_pct = None
        try:
            for line in open(filt_log):
                if "kept" in line:
                    m = re.search(r"kept (\d+)%", line)
                    if m:
                        kept_pct = int(m.group(1))
        except OSError:
            pass

        terminate_group(filt_proc)
        kill_group(scenario_proc)
        kill_group(recovery_mission_proc)
        kill_group(reference_mission_proc)
        kill_group(launch_proc)
        kill_all()
        if cgroup_meter is not None:
            cgroup_meter.cleanup()

        rec = {"map": map_name, "run": run, "mode": mode,
               "experiment_profile": mode if is_reference_ablation else None,
               "filter_profile": filter_profile,
               "filter_backend": filter_backend if filt_proc is not None else "direct",
               "perf_log_generation_ready": perf_log_generation_ready,
               "perf_window_valid": perf_window_valid,
               "perf_trace_csv": perf_trace_csv if os.path.exists(perf_trace_csv) else None,
               "perf_row_start": row_start, "perf_row_end": row_end, "kept_pct": kept_pct,
               "fsm_cpu_pct": fsm_cpu_pct, "filter_cpu_pct": filter_cpu_pct,
               "monitor_cpu_pct": monitor_cpu_pct,
               "attempt_count": attempt,
               "retry_count": attempt - 1,
               "first_attempt_success": attempt == 1,
               "retry_reasons": "; ".join(retry_reasons) or None,
               "oom_kill_delta": (
                   max(0, current_oom - oom_kill_start)
                   if oom_kill_start is not None
                   and (current_oom := read_cgroup_event("oom_kill")) is not None
                   else None
               ),
               "matched_prefix": matched_prefix if is_dynamic else None}
        rec.update(cgroup_summary)
        rec.update(merge_memory_summaries(memory_summaries))
        if os.path.exists(out_json):
            monitor_result = json.load(open(out_json))
            rec.update(monitor_result)
            if seedmap_static_pcd:
                static_pcd_valid = bool(
                    monitor_result.get("static_pcd_enabled") is True
                    and (monitor_result.get("static_pcd_point_count") or 0) > 0
                )
                speed_limit_valid = monitor_result.get("speed_limit_valid")
                rec["run_valid"] = bool(
                    static_pcd_valid and speed_limit_valid is not False
                )
            events = monitor_result.get("contact_events") or []
            if events:
                first_event = events[0]
                position = first_event.get("position") or [None, None, None]
                nearest = first_event.get("nearest_point") or [None, None, None]
                rec.update({
                    "first_contact_kind": first_event.get("kind"),
                    "first_contact_time_s": first_event.get("elapsed_s"),
                    "first_contact_distance_m": first_event.get("distance_m"),
                    "first_contact_x": position[0],
                    "first_contact_y": position[1],
                    "first_contact_z": position[2],
                    "first_contact_speed_mps": first_event.get("speed_mps"),
                    "first_contact_nearest_x": nearest[0],
                    "first_contact_nearest_y": nearest[1],
                    "first_contact_nearest_z": nearest[2],
                    "first_contact_static_distance_m": first_event.get(
                        "static_distance_at_event_m"
                    ),
                    "first_contact_static_clearance_m": first_event.get(
                        "static_clearance_at_event_m"
                    ),
                    "first_contact_static_confirmed": first_event.get(
                        "static_contact_at_event"
                    ),
                    "first_contact_live_point_static_distance_m": (
                        first_event.get("live_point_static_distance_m")
                    ),
                })
            if artifacts_dir:
                os.makedirs(artifacts_dir, exist_ok=True)
                artifact_path = os.path.join(artifacts_dir, f"{tag}.json")
                shutil.copyfile(out_json, artifact_path)
                rec["forensics_json"] = os.path.relpath(artifact_path, REPO_ROOT)
                copied_memory_traces = []
                for attempt_number in range(1, attempt + 1):
                    evidence_prefix = f"{tag}.attempt{attempt_number}"
                    for suffix in (
                        "stack.log", "memory.csv", "cgroup.csv", "filt.log",
                        "filt_stats.json", "performance.csv",
                        "reference_monitor.log", "mission.log",
                    ):
                        source = os.path.join(
                            TMPDIR, f"{evidence_prefix}.{suffix}"
                        )
                        if not os.path.exists(source):
                            continue
                        destination = os.path.join(
                            artifacts_dir, os.path.basename(source)
                        )
                        shutil.copyfile(source, destination)
                        if suffix == "memory.csv":
                            copied_memory_traces.append(
                                os.path.relpath(destination, REPO_ROOT)
                            )
                        elif suffix == "cgroup.csv":
                            rec["cgroup_cpu_trace_csv"] = os.path.relpath(
                                destination, REPO_ROOT
                            )
                        elif suffix == "performance.csv":
                            rec["perf_trace_csv"] = os.path.relpath(
                                destination, REPO_ROOT
                            )
                rec["memory_trace_csv"] = ";".join(copied_memory_traces)
                if is_reference_ablation:
                    for source, suffix in (
                        (reference_stack_log, "stack.log"),
                        (mission_log, "mission.log"),
                        (reference_monitor_log, "monitor.log"),
                    ):
                        if os.path.exists(source):
                            shutil.copyfile(
                                source,
                                os.path.join(artifacts_dir, f"{tag}.{suffix}"),
                            )
                elif (
                    (is_seedmap_observed or seedmap_super_config_override)
                    and os.path.exists(reference_stack_log)
                ):
                    shutil.copyfile(
                        reference_stack_log,
                        os.path.join(artifacts_dir, f"{tag}.stack.log"),
                    )
            else:
                rec["memory_trace_csv"] = ";".join(memory_trace_paths)
            if perf_window_valid:
                rec.update(slice_perf(
                    row_start, row_end, perf_trace_csv,
                    duration_s=rec.get("mission_time_s"),
                ))
        else:
            rec["success"] = False
        if os.path.exists(scenario_event_json):
            rec.update(json.load(open(scenario_event_json)))
        if os.path.exists(mission_event_json):
            mission_event = json.load(open(mission_event_json))
            rec.update(
                {f"mission_driver_{key}": value for key, value in mission_event.items()}
            )
        if os.path.exists(filt_event_json):
            rec.update(json.load(open(filt_event_json)))
        filter_stats = {}
        if os.path.exists(filt_stats_json):
            filter_stats = json.load(open(filt_stats_json))
            rec.update({f"filter_{key}": value for key, value in filter_stats.items()
                        if key != "mode"})
            if filter_stats.get("kept_pct") is not None:
                rec["kept_pct"] = filter_stats["kept_pct"]
                kept_pct = filter_stats["kept_pct"]
        if is_seedmap_shadow and os.path.exists(reference_stack_log):
            rec.update(parse_shadow_guard_log(reference_stack_log))
            if os.path.exists(out_json):
                correlation = correlate_shadow_contacts(
                    reference_stack_log, out_json
                )
                rec.update({
                    key: (
                        ";".join(value)
                        if key == "shadow_correlated_segments" else value
                    )
                    for key, value in correlation.items()
                    if key != "shadow_contact_matches"
                })
                if artifacts_dir:
                    correlation_path = os.path.join(
                        artifacts_dir, f"{tag}.shadow_contact_correlation.json"
                    )
                    with open(correlation_path, "w") as stream:
                        json.dump(correlation, stream, indent=2)
                        stream.write("\n")
        if os.path.exists(reference_stack_log):
            rec.update(parse_full_refresh_ack_log(reference_stack_log))
        if is_recovery:
            base_recovery_success = bool(
                rec.get("success")
                and rec.get("collisions", 0) == 0
                and rec.get("valid_spawn") is True
                and rec.get("mission_driver_phase") == "final"
            )
            rec["recovery_success"] = base_recovery_success

        if is_recovery and mode in ("adaptive", "trigger"):
            rec["recovery_triggered"] = rec.get("filter_open_transitions", 0) > 0
            arm_time = rec.get("filter_first_arm_time_s")
            spawn_time = rec.get("spawn_time_s")
            rec["recovery_spawn_after_arm"] = bool(
                arm_time is not None
                and spawn_time is not None
                and spawn_time >= arm_time
            )
            hold_time = rec.get("mission_driver_hold_start_time_s")
            release_time = rec.get("mission_driver_release_time_s")
            open_times = filter_stats.get("open_transition_times_s") or [
                rec.get("filter_first_open_time_s")
            ]
            open_times = [value for value in open_times if value is not None]
            close_times = filter_stats.get("close_transition_times_s") or [
                rec.get("filter_first_close_time_s")
            ]
            close_times = [value for value in close_times if value is not None]
            rec["recovery_open_after_spawn"] = bool(
                spawn_time is not None
                and any(value >= spawn_time for value in open_times)
            )
            qualifying_open_times = [
                value
                for value in open_times
                if hold_time is not None
                and release_time is not None
                and hold_time <= value <= release_time
            ]
            rec["recovery_reclosed"] = bool(
                release_time is not None
                and qualifying_open_times
                and any(
                    value >= max(release_time, qualifying_open_times[0])
                    for value in close_times
                )
            )
            rec["recovery_open_during_hold"] = bool(qualifying_open_times)
            rec["recovery_success"] = bool(
                base_recovery_success
                and rec["recovery_triggered"]
                and rec["recovery_spawn_after_arm"]
                and rec["recovery_open_after_spawn"]
                and rec["recovery_open_during_hold"]
                and rec["recovery_reclosed"]
            )

        # retry if we never even got odom samples (startup race), else accept the result
        if rec.get("samples", 0) in (0, None) and attempt < attempt_max:
            retry_reasons.append("no odom samples")
            log(f"  {tag} attempt {attempt}/{attempt_max}: no odom samples -> retry")
            continue
        if (
            is_reference_ablation
            and rec.get("run_valid") is not True
            and attempt < attempt_max
        ):
            retry_reasons.append("reference validity failed")
            if artifacts_dir and os.path.exists(out_json):
                invalid_artifact = os.path.join(
                    artifacts_dir, f"{tag}_attempt{attempt}_invalid.json"
                )
                shutil.copyfile(out_json, invalid_artifact)
            log(
                f"  {tag} attempt {attempt}/{attempt_max}: "
                "reference validity failed "
                f"(ready={rec.get('preflight_ready')}, "
                f"start_error={rec.get('start_pose_error_m')}, "
                f"max_odom_gap={rec.get('max_odom_gap_s')}, "
                f"gap_limit={rec.get('odom_gap_limit_s')}) -> retry"
            )
            continue
        if (
            seedmap_static_pcd
            and not (
                rec.get("static_pcd_enabled") is True
                and (rec.get("static_pcd_point_count") or 0) > 0
            )
            and attempt < attempt_max
        ):
            retry_reasons.append("static PCD monitor was not active")
            log(
                f"  {tag} attempt {attempt}/{attempt_max}: "
                "static PCD monitor was not active -> retry"
            )
            continue
        if (
            is_recovery
            and rec.get("valid_spawn") is False
            and attempt < attempt_max
        ):
            retry_reasons.append("invalid recovery trigger pose")
            log(
                f"  {tag} attempt {attempt}/{attempt_max}: "
                "invalid recovery trigger pose -> retry"
            )
            continue

        use_static_contact = is_reference_ablation or seedmap_static_pcd
        contact_count = (
            rec.get("static_pcd_collisions")
            if use_static_contact else rec.get("collisions")
        )
        clearance = (
            rec.get("static_pcd_clearance_m")
            if use_static_contact else rec.get("min_clearance_m")
        )
        log(f"  {tag}: success={rec.get('success')} time={rec.get('mission_time_s')}s "
            f"coll={contact_count} minclr={clearance} "
            f"speed={rec.get('max_command_speed_mps')}/"
            f"{rec.get('speed_limit_mps')} valid={rec.get('speed_limit_valid')} "
            f"pts={rec.get('pts_mean')} kept={kept_pct}% "
            f"payload={rec.get('map_payload_mib_s')}MiB/s "
            f"fsm_cpu={fsm_cpu_pct}")
        return rec

    oom_kill_end = read_cgroup_event("oom_kill")
    failed_rec = {"map": map_name, "run": run, "mode": mode,
            "experiment_profile": mode if mode in REFERENCE_ABLATION_PROFILES else None,
            "filter_profile": filter_profile, "filter_backend": filter_backend,
            "success": False, "run_valid": False,
            "attempt_count": attempt_max, "retry_count": attempt_max - 1,
            "first_attempt_success": False,
            "retry_reasons": "; ".join(retry_reasons) or None,
            "oom_kill_delta": (
                max(0, oom_kill_end - oom_kill_start)
                if oom_kill_start is not None and oom_kill_end is not None
                else None
            ),
            "memory_trace_csv": ";".join(memory_trace_paths)}
    failed_rec.update(merge_memory_summaries(memory_summaries))
    return failed_rec


def main():
    lock_stream = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(
            "another native campaign/watch process owns " + LOCK_PATH
        )

    ap = argparse.ArgumentParser()
    ap.add_argument("--maps", nargs="+", choices=VALID_MAPS, default=MAPS)
    ap.add_argument("--modes", nargs="+", choices=VALID_MODES, default=MODES)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument(
        "--rotate-modes",
        action="store_true",
        help="rotate requested mode order each run to balance order effects",
    )
    ap.add_argument(
        "--resume-existing",
        action="store_true",
        help=(
            "skip map/run/mode keys already present in --out and append only "
            "the missing rows"
        ),
    )
    ap.add_argument(
        "--seedmap-super-config",
        help=(
            "override the SUPER config for seed1..10 modes; intended for a "
            "common guarded full/sector/adaptive comparison"
        ),
    )
    ap.add_argument(
        "--seedmap-full-super-config",
        help=(
            "direct-Full SUPER config for a mixed full/sector/adaptive "
            "campaign; must use /cloud_registered"
        ),
    )
    ap.add_argument(
        "--seedmap-filtered-super-config",
        help=(
            "Sector/Adaptive SUPER config for a mixed campaign; must use "
            "/cloud_sector"
        ),
    )
    ap.add_argument(
        "--seedmap-adaptive-baseline-super-config",
        help=(
            "optional /cloud_sector SUPER config used only by the "
            "adaptive_baseline mode in a same-binary crossed A/B campaign"
        ),
    )
    ap.add_argument(
        "--seedmap-static-pcd",
        action="store_true",
        help="measure every seedmap mode against the same unfiltered static PCD",
    )
    ap.add_argument(
        "--loop-timeout",
        type=float,
        help="override the seedmap loop timeout in seconds",
    )
    ap.add_argument(
        "--filter-profile",
        choices=("legacy", "strict-burst"),
        default="legacy",
        help=(
            "legacy preserves the historical replan full-open valve; "
            "strict-burst keeps sector fixed and gives adaptive bounded "
            "stall-triggered full-cloud bursts"
        ),
    )
    ap.add_argument(
        "--filter-backend",
        choices=("python", "cpp"),
        default="python",
        help=(
            "implementation of /cloud_registered -> /cloud_sector; the C++ "
            "backend currently supports static seed1..10 campaigns"
        ),
    )
    ap.add_argument(
        "--adaptive-max-publish-hz",
        type=float,
        default=5.0,
        help="strict-burst Adaptive publication cap (default: 5.0 Hz)",
    )
    ap.add_argument(
        "--adaptive-slowdown-full-refresh-v",
        type=float,
        default=0.0,
        help=(
            "send one uncropped generation-ACKed scan when Adaptive slows "
            "below this speed after re-arming; 0 disables the trigger"
        ),
    )
    ap.add_argument(
        "--adaptive-slowdown-full-refresh-rearm-v",
        type=float,
        default=0.0,
        help=(
            "speed required to re-arm the one-shot Adaptive slowdown full "
            "refresh; must exceed the trigger speed"
        ),
    )
    ap.add_argument(
        "--adaptive-trajectory-guard-hold-s",
        type=float,
        default=2.5,
        help="strict-burst Adaptive post-guard full-open hold (default: 2.5 s)",
    )
    ap.add_argument(
        "--adaptive-trajectory-guard-active-max-publish-hz",
        type=float,
        default=0.0,
        help=(
            "strict-burst Adaptive cap used only while the direct trajectory "
            "guard is active (0 keeps the base cap)"
        ),
    )
    ap.add_argument(
        "--adaptive-trajectory-guard-ack-retry-age-s",
        type=float,
        default=0.0,
        help=(
            "while certified recovery is active, resend one latest full "
            "generation at this stop-and-wait interval until its exact ACK; "
            "0 disables the recovery-only retry"
        ),
    )
    ap.add_argument(
        "--adaptive-test-drop-first-trajectory-guard-full-cloud",
        action="store_true",
        help=(
            "test only: drop the first trajectory-guard full cloud after its "
            "generation request to prove the recovery-only ACK retry"
        ),
    )
    ap.add_argument(
        "--adaptive-full-open-extra-max-points",
        type=int,
        default=6000,
        help="strict-burst Adaptive far-field point budget while open",
    )
    ap.add_argument(
        "--adaptive-pre-stale-full-age-s",
        type=float,
        default=0.25,
        help=(
            "send at most one full scan per map version after this ACK age; "
            "0 disables the pre-stale refresh"
        ),
    )
    ap.add_argument(
        "--adaptive-pre-stale-ack-retry-age-s",
        type=float,
        default=0.0,
        help=(
            "after a missing exact ACK, send one newer full generation per "
            "source map version at this age; 0 disables the bounded retry"
        ),
    )
    ap.add_argument(
        "--no-adaptive-full-refresh-generation-ack",
        dest="adaptive_full_refresh_generation_ack",
        action="store_false",
        default=True,
        help=(
            "disable the strict-burst Adaptive exact-cloud generation ACK "
            "and planner recovery handshake"
        ),
    )
    ap.add_argument(
        "--filtered-reliable-map-link",
        action="store_true",
        help=(
            "request reliable depth-1 delivery from the native C++ filter; "
            "the selected filtered planner config must request the same QoS"
        ),
    )
    ap.add_argument(
        "--cgroup-cpu-accounting",
        action="store_true",
        help=(
            "require per-run cgroup-v2 CPU accounting for algorithm "
            "(fsm+filter) and end-to-end (sim+mission+algorithm) scopes"
        ),
    )
    ap.add_argument(
        "--test-force-local-escape-once",
        action="store_true",
        help=(
            "test only: arm one stopped local escape and skip its first "
            "direction before certifying the remaining directions"
        ),
    )
    ap.add_argument(
        "--test-force-initial-footprint-egress-once",
        action="store_true",
        help=(
            "test only: inject one synthetic stale voxel inside the stopped "
            "initial footprint and require bounded certified egress"
        ),
    )
    ap.add_argument(
        "--artifacts-dir",
        help="copy each run's monitor JSON, including contact context, here",
    )
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "native_campaign.csv"))
    args = ap.parse_args()

    if args.loop_timeout is not None and args.loop_timeout <= 0.0:
        ap.error("--loop-timeout must be positive")
    if args.adaptive_max_publish_hz < 0.0:
        ap.error("--adaptive-max-publish-hz must be non-negative")
    if args.adaptive_slowdown_full_refresh_v < 0.0:
        ap.error("--adaptive-slowdown-full-refresh-v must be non-negative")
    if args.adaptive_slowdown_full_refresh_v > 0.0 and not (
        args.adaptive_slowdown_full_refresh_rearm_v
        > args.adaptive_slowdown_full_refresh_v
    ):
        ap.error(
            "--adaptive-slowdown-full-refresh-rearm-v must exceed "
            "--adaptive-slowdown-full-refresh-v"
        )
    if (
        args.adaptive_slowdown_full_refresh_v == 0.0
        and args.adaptive_slowdown_full_refresh_rearm_v != 0.0
    ):
        ap.error(
            "--adaptive-slowdown-full-refresh-rearm-v requires a positive "
            "--adaptive-slowdown-full-refresh-v"
        )
    if (
        args.adaptive_slowdown_full_refresh_v > 0.0
        and args.filter_backend != "cpp"
    ):
        ap.error("Adaptive slowdown full refresh requires --filter-backend cpp")
    if args.adaptive_trajectory_guard_hold_s < 0.0:
        ap.error("--adaptive-trajectory-guard-hold-s must be non-negative")
    if args.adaptive_trajectory_guard_active_max_publish_hz < 0.0:
        ap.error(
            "--adaptive-trajectory-guard-active-max-publish-hz must be "
            "non-negative"
        )
    if args.adaptive_trajectory_guard_ack_retry_age_s < 0.0:
        ap.error(
            "--adaptive-trajectory-guard-ack-retry-age-s must be "
            "non-negative"
        )
    if args.adaptive_full_open_extra_max_points < 0:
        ap.error("--adaptive-full-open-extra-max-points must be non-negative")
    if args.adaptive_pre_stale_full_age_s < 0.0:
        ap.error("--adaptive-pre-stale-full-age-s must be non-negative")
    if args.adaptive_pre_stale_ack_retry_age_s < 0.0:
        ap.error(
            "--adaptive-pre-stale-ack-retry-age-s must be non-negative"
        )
    if args.filtered_reliable_map_link and args.filter_backend != "cpp":
        ap.error("--filtered-reliable-map-link requires --filter-backend cpp")
    if args.adaptive_test_drop_first_trajectory_guard_full_cloud:
        if args.filter_backend != "cpp":
            ap.error(
                "--adaptive-test-drop-first-trajectory-guard-full-cloud "
                "requires --filter-backend cpp"
            )
        if not args.adaptive_full_refresh_generation_ack:
            ap.error(
                "--adaptive-test-drop-first-trajectory-guard-full-cloud "
                "requires generation ACK"
            )
        if "adaptive" not in args.modes:
            ap.error(
                "--adaptive-test-drop-first-trajectory-guard-full-cloud "
                "requires adaptive mode"
            )
    if args.test_force_local_escape_once:
        if args.modes != ["adaptive"]:
            ap.error(
                "--test-force-local-escape-once requires exactly "
                "--modes adaptive"
            )
        if args.runs != 1:
            ap.error("--test-force-local-escape-once requires --runs 1")
    if args.test_force_initial_footprint_egress_once:
        if args.modes != ["adaptive"]:
            ap.error(
                "--test-force-initial-footprint-egress-once requires exactly "
                "--modes adaptive"
            )
        if args.runs != 1:
            ap.error(
                "--test-force-initial-footprint-egress-once requires --runs 1"
            )
    split_configs = (
        args.seedmap_full_super_config,
        args.seedmap_filtered_super_config,
    )
    adaptive_baseline_config = args.seedmap_adaptive_baseline_super_config
    if args.seedmap_super_config and any(split_configs):
        ap.error(
            "--seedmap-super-config cannot be combined with the mode-specific "
            "--seedmap-full-super-config/--seedmap-filtered-super-config"
        )
    if any(split_configs) and not all(split_configs):
        ap.error(
            "mode-specific routing requires both --seedmap-full-super-config "
            "and --seedmap-filtered-super-config"
        )
    if all(split_configs):
        unsupported_modes = [
            mode for mode in args.modes
            if mode not in ("full", "sector", "adaptive")
        ]
        if unsupported_modes:
            ap.error(
                "mode-specific config routing supports only plain "
                "full/sector/adaptive modes; unsupported modes: "
                + ", ".join(unsupported_modes)
            )
        full_topic = super_config_cloud_topic(args.seedmap_full_super_config)
        if full_topic != "/cloud_registered":
            ap.error(
                "--seedmap-full-super-config must use /cloud_registered; "
                f"{args.seedmap_full_super_config} uses "
                f"{full_topic or 'an unknown topic'}"
            )
        filtered_topic = super_config_cloud_topic(
            args.seedmap_filtered_super_config
        )
        if filtered_topic != "/cloud_sector":
            ap.error(
                "--seedmap-filtered-super-config must use /cloud_sector; "
                f"{args.seedmap_filtered_super_config} uses "
                f"{filtered_topic or 'an unknown topic'}"
            )
    if "adaptive_baseline" in args.modes and not adaptive_baseline_config:
        ap.error(
            "adaptive_baseline mode requires "
            "--seedmap-adaptive-baseline-super-config"
        )
    if adaptive_baseline_config:
        if "adaptive_baseline" not in args.modes:
            ap.error(
                "--seedmap-adaptive-baseline-super-config requires "
                "adaptive_baseline mode"
            )
        baseline_topic = super_config_cloud_topic(adaptive_baseline_config)
        if baseline_topic != "/cloud_sector":
            ap.error(
                "--seedmap-adaptive-baseline-super-config must use "
                f"/cloud_sector; {adaptive_baseline_config} uses "
                f"{baseline_topic or 'an unknown topic'}"
            )

    if (
        args.seedmap_super_config
        or any(split_configs)
        or adaptive_baseline_config
        or args.seedmap_static_pcd
    ):
        invalid_maps = [
            map_name for map_name in args.maps
            if not re.fullmatch(r"seed(?:[1-9]|10)", map_name)
        ]
        if invalid_maps:
            ap.error(
                "seedmap config/static-PCD overrides support only seed1..10; "
                f"unsupported maps: {', '.join(invalid_maps)}"
            )

    if args.filter_backend == "cpp":
        unsupported_maps = [
            map_name for map_name in args.maps
            if map_name in ("seed12", "seed13", "seed14", "seed15")
        ]
        if unsupported_maps:
            ap.error(
                "the C++ backend does not yet implement dynamic trap-event "
                "instrumentation; use --filter-backend python for: "
                + ", ".join(unsupported_maps)
            )

    if any(mode in RAW_DIRECT_REF_MODES for mode in args.modes):
        invalid_maps = [
            map_name for map_name in args.maps if map_name not in ("seed11", "map0")
        ]
        if invalid_maps:
            ap.error(
                "raw-direct controls are currently defined only for seed11/map0; "
                f"unsupported maps: {', '.join(invalid_maps)}"
            )

    fresh = not os.path.exists(args.out) or os.path.getsize(args.out) == 0
    existing_keys = set()
    max_existing_sequence = 0
    if not fresh:
        with open(args.out, newline="") as existing:
            reader = csv.DictReader(existing)
            existing_header = reader.fieldnames or []
            existing_rows = list(reader) if args.resume_existing else []
        if existing_header != FIELDS:
            raise SystemExit(
                f"refusing to append to {args.out}: CSV header is from a different "
                "campaign schema; choose a new --out path"
            )
        for row in existing_rows:
            try:
                row_run = int(row["run"])
            except (KeyError, TypeError, ValueError):
                continue
            existing_keys.add((row.get("map"), row_run, row.get("mode")))
            try:
                max_existing_sequence = max(
                    max_existing_sequence,
                    int(row.get("campaign_sequence_index") or 0),
                )
            except (TypeError, ValueError):
                pass
    f = open(args.out, "a", newline="")
    w = csv.DictWriter(
        f, fieldnames=FIELDS, extrasaction="ignore", lineterminator="\n"
    )
    if fresh:
        w.writeheader(); f.flush()

    requested_keys = {
        (map_name, run, mode)
        for map_name in args.maps
        for run in range(1, args.runs + 1)
        for mode in args.modes
    }
    total = len(requested_keys - existing_keys)
    done = 0
    t0 = time.time()
    try:
        for map_index, map_name in enumerate(args.maps):
            for run in range(1, args.runs + 1):
                modes = list(args.modes)
                if args.rotate_modes and modes:
                    # Continue the rotation across seed boundaries. Resetting
                    # at every seed gives a systematic 20/10/20 position
                    # imbalance for 10 seeds x 5 runs x 3 modes; the global
                    # sequence gives the closest possible 17/17/16 balance.
                    shift = (
                        map_index * args.runs + run - 1
                    ) % len(modes)
                    modes = modes[shift:] + modes[:shift]
                for mode_position, mode in enumerate(modes, start=1):
                    if (map_name, run, mode) in existing_keys:
                        continue
                    mode_config = args.seedmap_super_config
                    if mode == "adaptive_baseline":
                        mode_config = adaptive_baseline_config
                    if all(split_configs):
                        mode_config = (
                            args.seedmap_full_super_config
                            if mode == "full"
                            else args.seedmap_filtered_super_config
                        )
                    rec = run_one(
                        map_name,
                        mode,
                        run,
                        artifacts_dir=(
                            os.path.abspath(args.artifacts_dir)
                            if args.artifacts_dir
                            else None
                        ),
                        seedmap_super_config_override=mode_config,
                        seedmap_static_pcd=args.seedmap_static_pcd,
                        loop_timeout_override=args.loop_timeout,
                        filter_profile=args.filter_profile,
                        filter_backend=args.filter_backend,
                        adaptive_max_publish_hz=args.adaptive_max_publish_hz,
                        adaptive_slowdown_full_refresh_v=(
                            args.adaptive_slowdown_full_refresh_v
                        ),
                        adaptive_slowdown_full_refresh_rearm_v=(
                            args.adaptive_slowdown_full_refresh_rearm_v
                        ),
                        adaptive_trajectory_guard_hold_s=(
                            args.adaptive_trajectory_guard_hold_s
                        ),
                        adaptive_trajectory_guard_active_max_publish_hz=(
                            args.adaptive_trajectory_guard_active_max_publish_hz
                        ),
                        adaptive_trajectory_guard_ack_retry_age_s=(
                            args.adaptive_trajectory_guard_ack_retry_age_s
                        ),
                        adaptive_test_drop_first_trajectory_guard_full_cloud=(
                            args.adaptive_test_drop_first_trajectory_guard_full_cloud
                        ),
                        adaptive_pre_stale_full_age_s=(
                            args.adaptive_pre_stale_full_age_s
                        ),
                        adaptive_pre_stale_ack_retry_age_s=(
                            args.adaptive_pre_stale_ack_retry_age_s
                        ),
                        adaptive_full_refresh_generation_ack=(
                            args.adaptive_full_refresh_generation_ack
                        ),
                        filtered_reliable_map_link=(
                            args.filtered_reliable_map_link
                        ),
                        adaptive_full_open_extra_max_points=(
                            args.adaptive_full_open_extra_max_points
                        ),
                        test_force_local_escape_once=(
                            args.test_force_local_escape_once
                        ),
                        test_force_initial_footprint_egress_once=(
                            args.test_force_initial_footprint_egress_once
                        ),
                        cgroup_cpu_accounting=args.cgroup_cpu_accounting,
                    )
                    rec["campaign_sequence_index"] = (
                        max_existing_sequence + done + 1
                    )
                    rec["mode_order_position"] = mode_position
                    w.writerow(rec); f.flush()
                    done += 1
                    el = time.time() - t0
                    eta = el / done * (total - done) if done else 0
                    log(f"=== progress {done}/{total} elapsed={el/60:.1f}m "
                        f"eta={eta/60:.1f}m ===")
    finally:
        f.close()
        kill_all()
    log(f"DONE -> {args.out}")


if __name__ == "__main__":
    main()
