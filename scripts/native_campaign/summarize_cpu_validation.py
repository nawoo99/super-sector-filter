#!/usr/bin/env python3
"""Offline, run-weighted Full/Sector/Adaptive computational metric comparison.

This does not run ROS, change a measurement, discard a failed run, or identify
CPU energy from CPU time. All original numeric raw.csv fields are inventoried;
selected summary/trace fields supply tails, GPU, cadence, and recovery evidence.
Instrumented cohorts are NEVER pooled into the unprofiled primary comparison.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics


MODES = ("full", "sector", "adaptive")
SUMMARY_ROOTS = (
    "host_cpu_pct", "gpu_device_util_pct", "gpu_memory_mib", "gpu_power_w",
    "observer_process_cpu_pct", "cgroup_interval_cores", "experiment_proc_sum_cores",
    "baseline_host_cpu_pct", "baseline_gpu_device_util_pct", "map_Total_ms",
    "map_Raycast_ms", "map_Update_cache_ms", "map_Inflation_ms", "message_intervals",
    "small_pool_timing", "goal_identity_audit",
)
NOTES = [
    "Primary = cpu_profile:false; instrumented preflight/stage results are separate supplemental cohorts.",
    "Each observation is one run. Means and sample SD are across run-level values, never pooled 1 Hz samples. SD is unavailable for n=1.",
    "All recorded attempts remain, including failed/invalid runs. Missing, NaN and infinity are unavailable, never zero. Aborted slots with no raw.csv row cannot be inferred; inspect campaign status.",
    "Reduction = 100*(Full run-mean - mode run-mean)/Full run-mean. No reduction is defined for zero Full or missing values. A decrease is not automatically a benefit.",
    "CPU cores are average utilized logical cores; whole-host capacity percent = 100*cores/logical_cpus. Cgroup CPU excludes the external measurement observer but includes simulator, frontend/planner, mission and launch processes. Core-s covers cgroup_cpu_duration_s, a measurement window slightly wider than mission_time_s; do not divide it by mission time to recompute mean CPU.",
    "The algorithm cgroup is a composed simulator+planner(+frontend) process here, NOT autonomy-only CPU. fsm_cpu_pct is also not pure planner CPU in this configuration.",
    "GPU utilization, GPU memory and GPU power are whole-device observations including background. Host CPU is whole-host including background. Baseline subtraction would not establish causal attribution.",
    "PointCloud payload counts measure logical data at the named pipeline edge, not physical NIC/PCIe/DRAM bandwidth. Same shared buffer may be counted on multiple edges; do not add nested delivery totals as unique bytes.",
    "Map frames/points/payload rates use mission duration as denominator although the captured performance slice includes startup; these are historical mission-normalized proxies, not exact source frequency. sensor_hz uses its own source-report span; latest periodic source byte/frame counters are not necessarily full-flight totals.",
    "source_logged metrics describe only observed SOURCE_ACQUISITION log records: per-frame rays/readback/points/bytes and coverage checks, not inferred full-flight totals or time duty. Readback pixels and converted rays are different work counters, not executed GPU instructions.",
    "Event-recovery cycles, certified closures and observed source Sector-to-Full/Full-to-Sector changes are distinct from legacy filter risk-switch counters. Initial recovery is not evidence of an avoided collision; no collision-avoidance count is inferred.",
    "Map callback timing is elapsed wall time, not thread CPU time. Inflation is nested within update/total; do not add the timing columns. Sum of callback wall time is not CPU core-s.",
    "Command/odometry received frequencies and intervals include transport and observer jitter; command holds may be intentional. They are not producer callback frequency. Actual callback counts are unavailable with CPU profiling OFF unless independently instrumented.",
    "Per-run p95/max are summarized across runs, not represented as a pooled campaign p95/max. Per-process percentages are sampled diagnostics, not a substitute for cumulative cgroup accounting.",
    "RSS/PSS/swap peaks are sampled peaks (periodic plus boundary samples), not continuous maxima. Summed RSS can count shared pages more than once; PSS is preferable for aggregate physical-memory comparisons.",
    "Success/contact observations are finite-run results, not population guarantees. CPU-to-completion comparisons are outcome-confounded if a mode does not complete all attempts.",
    "A candidate name is not proof of identical configuration. Asset hash/policy fingerprints are reported; inspect differing fingerprints before pooling scientifically.",
]


def numeric(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return float(value.lower() == "true")
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


def flatten_numeric(value, prefix=""):
    """Lists hold identities/events: retain in source, never align them by index."""
    result = {}
    if isinstance(value, dict):
        for key, item in value.items():
            result.update(flatten_numeric(item, f"{prefix}.{key}" if prefix else key))
    elif not isinstance(value, list):
        converted = numeric(value)
        if converted is not None:
            result[prefix] = converted
    return result


def is_numeric_field(value):
    if value is None or value == "" or isinstance(value, (bool, int, float)):
        return True
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return True
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def distribution(values):
    vals = [v for value in values if (v := numeric(value)) is not None]
    if not vals:
        return dict(n=0, mean=None, sd=None, min=None, max=None)
    return dict(n=len(vals), mean=statistics.mean(vals),
                sd=statistics.stdev(vals) if len(vals) > 1 else None,
                min=min(vals), max=max(vals))


def nearest_rank(values, quantile):
    vals = sorted(v for value in values if (v := numeric(value)) is not None)
    return vals[max(0, math.ceil(quantile * len(vals)) - 1)] if vals else None


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.is_file() else ({} if default is None else default)


def resolve_artifact(value, folder, repo):
    if not value:
        return None
    path = Path(value)
    candidates = (path, repo / path, folder / path, folder / "artifacts" / path.name)
    return next((p for p in candidates if p.is_file()), None)


def perf_metrics(row, folder, repo):
    path = resolve_artifact(row.get("perf_trace_csv"), folder, repo)
    if path is None or numeric(row.get("perf_window_valid")) != 1:
        return {}, "performance trace unavailable or window invalid"
    with path.open(newline="") as stream:
        values = list(csv.DictReader(stream, skipinitialspace=True))
    start_value, end_value = numeric(row.get("perf_row_start")), numeric(row.get("perf_row_end"))
    if start_value is None or end_value is None or not start_value.is_integer() or not end_value.is_integer():
        return {}, "performance trace row bounds missing, nonfinite or noninteger"
    start, end = int(start_value), int(end_value)
    # Native artifact copies the entire performance log. Original indices bound
    # the intended window; never take startup/teardown rows outside that slice.
    if start < 0 or end < start or end > len(values):
        return {}, f"performance trace row bounds invalid: {start}:{end} / {len(values)}"
    values = values[start:end]
    if not values:
        return {}, "performance trace selected slice is empty; unavailable, not zero"
    out = {}
    for column in ("Total", "Raycast", "Update_cache", "Inflation", "PointCloudNumber",
                   "CacheNumber", "InflationNumber", "PointCloudPayloadBytes", "PointCloudPointStep"):
        vals = [n for r in values if (n := numeric(r.get(column))) is not None]
        if not vals:
            continue
        factor = 1000 if column in ("Total", "Raycast", "Update_cache", "Inflation") else 1
        vals = [v * factor for v in vals]
        unit = "ms" if factor == 1000 else "value"
        root = f"performance.{column}.{unit}"
        out.update({f"{root}.{key}": value for key, value in distribution(vals).items()})
        out[root + ".p95"] = nearest_rank(vals, .95)
        out[root + ".p99"] = nearest_rank(vals, .99)
        out[root + ".sum"] = sum(vals)
    return out, None


def telemetry_metrics(samples, mode):
    selected = [s for s in samples if s.get("mode") == mode and s.get("campaign_active") is True]
    keys = sorted({key for sample in selected for key, value in sample.items()
                   if is_numeric_field(value) and key not in
                   ("epoch_s", "monotonic_s", "raw_cpu_counters_version", "campaign_active")})
    result = {}
    for key in keys:
        vals = [sample.get(key) for sample in selected]
        stats = distribution(vals)
        stats["p95"] = nearest_rank(vals, .95)
        for stat, value in stats.items():
            result[f"telemetry.{key}.{stat}"] = value
    cpu_count = max((len(s.get("host_per_logical_cpu_pct", [])) for s in selected), default=0)
    for index in range(cpu_count):
        vals = [s["host_per_logical_cpu_pct"][index] for s in selected
                if len(s.get("host_per_logical_cpu_pct", [])) > index]
        for stat, value in distribution(vals).items():
            result[f"telemetry.host_logical_cpu{index}_pct.{stat}"] = value
    return result


def source_log_metrics(summary):
    frames = summary.get("source_acquisition", {}).get("frames", [])
    if not frames:
        return {}
    metrics = {"source_logged.frames": len(frames)}
    ids = [numeric(frame.get("frame")) for frame in frames]
    valid_ids = all(value is not None and value.is_integer() for value in ids)
    metrics["source_logged.contiguous_unique_ids"] = float(valid_ids and ids == list(range(int(ids[0]), int(ids[0]) + len(ids))))
    metrics["source_logged.starts_at_frame1"] = float(valid_ids and ids[0] == 1)
    for key in ("width", "height", "readback_pixels", "conversion_rays", "generated_points", "bytes", "half_angle_deg"):
        values = [frame.get(key) for frame in frames]
        for stat, value in distribution(values).items():
            metrics[f"source_logged.{key}.{stat}"] = value
    full_flags = [numeric(frame.get("full")) for frame in frames]
    metrics["source_logged.full_frame_fraction_pct"] = (
        100 * sum(full_flags) / len(full_flags) if all(v in (0, 1) for v in full_flags) else None)
    contiguous_flags = metrics["source_logged.contiguous_unique_ids"] == 1 and all(v in (0, 1) for v in full_flags)
    for previous, current, key in ((0, 1, "sector_to_full_count"), (1, 0, "full_to_sector_count")):
        metrics["source_logged." + key] = (
            sum(a == previous and b == current for a, b in zip(full_flags, full_flags[1:]))
            if contiguous_flags else None)
    metrics["source_logged.direction_change_count"] = (
        sum(a != b for a, b in zip(full_flags, full_flags[1:])) if contiguous_flags else None)
    return metrics


def process_metrics(summary):
    # Do not pool individual TIDs/PIDs across runs. Known composed process
    # executable names differ between modes, but have the same measured scope.
    result = {}
    for item in summary.get("processes", []):
        name = item.get("name", "unknown")
        role = "composed_simulator_frontend_planner" if name.startswith("perfect_drone_") else name
        for stat, value in item.get("cpu_pct_one_core", {}).items():
            key = f"process.{role}.cpu_pct_one_core.{stat}"
            if key in result:
                # An ambiguous multiple-process role is not averaged or summed
                # after quantiles have been calculated.
                result[key] = None
            else:
                result[key] = numeric(value)
    return result


def protocol_fingerprint(plan):
    excluded = {"run", "modes", "candidate", "schema", "time_reference_folder", "runtime_policy",
                "small_pool_profile_reference", "effective_run_options", "effective_frontend_executor",
                "baseline_seconds", "mean_cpu_reduction_target_pct", "exploratory_tuning",
                "no_automatic_retry", "not_pooled_with_previous_results"}
    selected = {key: value for key, value in plan.items() if key not in excluded}
    return hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()


def load_runs(campaign_roots, repo):
    runs, seen, warnings = [], set(), []
    paths = sorted({path.resolve() for root in campaign_roots for path in root.rglob("raw.csv")})
    for path in paths:
        folder = path.parent
        plan = read_json(folder / "plan.json")
        if not plan:
            warnings.append(f"Skipped {path}: no adjacent plan.json; not assumed to be compatible.")
            continue
        with path.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        telemetry_path = folder / "telemetry.jsonl"
        telemetry = []
        if telemetry_path.is_file():
            with telemetry_path.open() as stream:
                for line in stream:
                    try:
                        telemetry.append(json.loads(line))
                    except json.JSONDecodeError:
                        warnings.append(f"Incomplete telemetry row in {telemetry_path}")
        for row in rows:
            mode = row.get("mode")
            if mode not in MODES:
                warnings.append(f"Unknown mode {mode!r} in {path}")
                continue
            identity = (plan.get("candidate", "unknown"), plan.get("cpu_profile"),
                        row.get("map"), row.get("run"), mode)
            if identity in seen:
                raise ValueError(f"Duplicate recorded run: {identity}")
            seen.add(identity)
            summary = read_json(folder / f"{mode}_summary.json")
            for field in ("map", "mode", "run"):
                if field in summary and str(summary[field]) != str(row.get(field)):
                    raise ValueError(f"Mismatched {field} in {folder}/{mode}_summary.json")
            profile = summary.get("cpu_profile", plan.get("cpu_profile"))
            if "cpu_profile" in summary and "cpu_profile" in plan and summary["cpu_profile"] != plan["cpu_profile"]:
                raise ValueError(f"Profiling state mismatch in {folder}/{mode}_summary.json")
            if profile not in (True, False):
                warnings.append(f"Unknown profiling state for {identity}; separate unknown cohort")
            metrics = {key: numeric(value) for key, value in row.items() if is_numeric_field(value)}
            for root in SUMMARY_ROOTS:
                metrics.update(flatten_numeric(summary.get(root, {}), "summary." + root))
            metrics.update(process_metrics(summary))
            metrics.update(telemetry_metrics(telemetry, mode))
            metrics.update(source_log_metrics(summary))
            metrics.update(flatten_numeric(summary.get("source_acquisition", {}).get("frontend_stats", {}), "frontend_stats"))
            reason_reports = summary.get("demand_reason_audit", {}).get("reports", [])
            if reason_reports:
                metrics.update(flatten_numeric(reason_reports[-1], "demand_latest_cumulative"))
            trace_metrics, error = perf_metrics(row, folder, repo)
            metrics.update(trace_metrics)
            if error:
                warnings.append(f"{row.get('run')}/{mode}: {error}")
            logical = numeric(plan.get("logical_cpus"))
            metrics["logical_cpus"] = logical
            for prefix in ("end_to_end", "algorithm"):
                for source, suffix in (("mean", "mean"), ("p95_1s", "p95_1s"), ("max_1s", "max_1s")):
                    val = numeric(row.get(f"{prefix}_cpu_cores_{source}"))
                    metrics[f"{prefix}_host_capacity_pct_{suffix}"] = (
                        100 * val / logical if val is not None and logical and logical > 0 else None)
            recovery = summary.get("strict_recovery_audit", {})
            for key in ("opened_cycles", "source_frames", "timestamp_observed_completed_cycles"):
                metrics["recovery_audit." + key] = numeric(recovery.get(key))
            for key in ("completed_cycles", "outstanding_cycles"):
                metrics["recovery_audit." + key + "_count"] = (
                    len(recovery[key]) if isinstance(recovery.get(key), list) else None)
            metrics["autonomy_only_cpu_cores_mean"] = None
            metrics["autonomy_only_cpu_core_s"] = None
            metrics["physical_wire_mib_s"] = None
            metrics["cpu_energy_j"] = None
            metrics["planner_callback_latency_ms_mean_unprofiled"] = None
            runs.append(dict(map=row.get("map"), mode=mode, run=row.get("run"),
                             candidate=plan.get("candidate", "unknown"), cpu_profile=profile,
                             source=str(path), summary_source=str(folder / f"{mode}_summary.json"),
                             protocol_fingerprint=protocol_fingerprint(plan),
                             scopes={key: row.get(key) for key in ("algorithm_cpu_scope", "end_to_end_cpu_scope",
                                      "algorithm_cpu_excludes_simulator", "cgroup_memory_source")},
                             metrics=metrics))
    return runs, warnings


def category(key):
    lower = key.lower()
    if "cpu" in lower or "core_s" in lower:
        return "CPU"
    if "gpu" in lower:
        return "GPU (device-wide)"
    if any(s in lower for s in ("rss", "pss", "swap", "memory", "psi_", "available_mib")):
        return "Memory / resource pressure"
    if any(s in lower for s in ("payload", "points", "pointcloud", "pts_mean", "cache_number", "inflationnumber", "cachenumber", "wire_")):
        return "Point count / logical payload"
    if any(s in lower for s in ("map_", "performance.", "total_ms", "raycast", "inflation", "update_ms")):
        return "Map computation / frequency"
    if any(s in lower for s in ("replan", "optimizer", "trajectory_commit", "planner_", "shadow")):
        return "Planner / optimizer / diagnostics"
    if any(s in lower for s in ("hz", "cadence", "message_intervals", "sensor_")):
        return "Sensor / control cadence"
    if any(s in lower for s in ("filter_", "recovery", "guard_", "frontend_")):
        return "Frontend / switching / recovery"
    return "Mission / safety / settings / other diagnostics"


def metric_note(key):
    if key.startswith("demand_latest_cumulative."):
        return "Latest periodic cumulative report; early-gated ticks and final partial interval excluded."
    if key.startswith("source_logged."):
        return "Observed source log records only; per-record statistics, not inferred full-flight coverage/time duty."
    if key.startswith("autonomy_only_"):
        return "Unavailable: simulator and autonomy share a process; unprofiled CPU cannot be separated."
    if key == "physical_wire_mib_s":
        return "Unavailable: no physical network/bus counters collected."
    if key == "cpu_energy_j":
        return "Unavailable: no CPU package energy counter collected; core-s is not energy."
    if key == "planner_callback_latency_ms_mean_unprofiled":
        return "Unavailable in unprofiled cohort; profiled stage CPU is a separate diagnostic, not callback wall latency."
    if "core_equivalent" in key:
        return "Legacy name: derived from elapsed frontend callback time, NOT measured CPU cores."
    if "algorithm_cpu" in key or key == "fsm_cpu_pct":
        return "Composed simulator+planner(+frontend) scope; not planner-only CPU."
    if key in ("map_frames_s", "map_points_s", "map_payload_mib_s", "map_payload_mbps", "planner_ingress_payload_mib_s"):
        return "Mission-normalized proxy: performance slice includes startup; not exact source frequency."
    if key in ("sensor_payload_bytes", "sensor_frames", "sensor_payload_mib_s"):
        return "Latest periodic source report over its own span, not necessarily whole-flight coverage."
    if "payload" in key or "pointcloud" in key.lower():
        return "Named logical data edge; may share underlying buffer; not physical bandwidth."
    if key.startswith("summary.message_intervals"):
        return "Observed messages, not actual producer callback cadence."
    if key.startswith("summary.small_pool_timing.callback_hz"):
        return "Actual callback counts require profiling; unavailable in OFF cohort."
    return ""


def aggregate(runs):
    grouped = {}
    for run in runs:
        profile = "profiled_supplement" if run["cpu_profile"] is True else (
            "unprofiled_primary" if run["cpu_profile"] is False else "unknown_profile")
        key = (run["candidate"], profile, run["map"])
        grouped.setdefault(key, []).append(run)
    cohorts = []
    ordering = {"unprofiled_primary": 0, "profiled_supplement": 1, "unknown_profile": 2}
    for (candidate, profile, map_name), members in sorted(
            grouped.items(), key=lambda item: (item[0][0], item[0][2], ordering[item[0][1]])):
        fingerprints = {run["protocol_fingerprint"] for run in members}
        if len(fingerprints) != 1:
            raise ValueError(f"Mixed protocol fingerprints in {candidate}/{profile}/{map_name}; separate incompatible cohorts before comparison")
        metrics = sorted({key for run in members for key in run["metrics"]})
        modes = {}
        for mode in MODES:
            selected = [run for run in members if run["mode"] == mode]
            if not selected:
                continue
            modes[mode] = dict(attempts=len(selected),
                successes=sum(run["metrics"].get("success") == 1 for run in selected),
                valid_runs=sum(run["metrics"].get("run_valid") == 1 for run in selected),
                contact_runs=sum((run["metrics"].get("safety_collisions") or 0) > 0 for run in selected),
                contact_unknown_runs=sum(run["metrics"].get("safety_collisions") is None for run in selected),
                protocol_fingerprints=sorted({run["protocol_fingerprint"] for run in selected}),
                run_ids=[run["run"] for run in selected],
                metrics={metric: distribution(run["metrics"].get(metric) for run in selected) for metric in metrics})
        all_completed = set(modes) == set(MODES) and all(v["successes"] == v["attempts"] for v in modes.values())
        for mode, values in modes.items():
            for metric, stats in values["metrics"].items():
                full = modes.get("full", {}).get("metrics", {}).get(metric, {}).get("mean")
                stats["reduction_vs_full_pct"] = (
                    100 * (full - stats["mean"]) / full
                    if full is not None and full != 0 and stats["mean"] is not None else None)
                stats["n_missing"] = values["attempts"] - stats["n"]
        cohorts.append(dict(candidate=candidate, profile=profile, map=map_name,
                            all_modes_completed_all_attempts=all_completed, modes=modes))
    return cohorts


def planned_coverage(cohorts, roots):
    manifests = [read_json(root / "plan.json") for root in roots]
    for cohort in cohorts:
        key = "unprofiled_runs_per_mode" if cohort["profile"] == "unprofiled_primary" else "profile_preflight_runs_per_mode"
        expected = {int(plan[key]) for plan in manifests if key in plan
                    and plan.get("map", cohort["map"]) == cohort["map"]}
        n = next(iter(expected)) if len(expected) == 1 else None
        cohort["planned_attempts_per_mode"] = n
        cohort["planned_slots_observed"] = (
            all(cohort["modes"].get(mode, {}).get("attempts", 0) == n for mode in MODES)
            if n is not None else None)


DISPLAY = [
    ("Mission time (s)", "mission_time_s"),
    ("Path length (m)", "path_length_m"),
    ("Minimum static-PC clearance (m)", "static_pcd_clearance_m"),
    ("Experiment CPU (cores)", "end_to_end_cpu_cores_mean"),
    ("Experiment CPU (whole-host %)", "end_to_end_host_capacity_pct_mean"),
    ("Experiment measurement-window CPU (core-s)", "end_to_end_cpu_core_s"),
    ("Accounting window (s)", "cgroup_cpu_duration_s"),
    ("Experiment CPU 1 s p95 (cores)", "end_to_end_cpu_cores_p95_1s"),
    ("Experiment CPU 1 s maximum (cores)", "end_to_end_cpu_cores_max_1s"),
    ("Composed runtime CPU (cores; includes simulator)", "algorithm_cpu_cores_mean"),
    ("Composed runtime measurement-window CPU (core-s)", "algorithm_cpu_core_s"),
    ("Autonomy-only CPU (cores)", "autonomy_only_cpu_cores_mean"),
    ("Observer CPU (one-core %)", "summary.observer_process_cpu_pct.mean"),
    ("Whole-host CPU (%)", "summary.host_cpu_pct.mean"),
    ("Baseline whole-host CPU (%)", "summary.baseline_host_cpu_pct.mean"),
    ("Experiment sampled peak RSS (MiB)", "end_to_end_peak_rss_mib"),
    ("Experiment sampled peak PSS (MiB)", "end_to_end_peak_pss_mib"),
    ("Experiment sampled peak process swap (MiB)", "end_to_end_peak_swap_mib"),
    ("Host minimum available memory (MiB)", "system_min_available_mib"),
    ("GPU device utilization (%)", "summary.gpu_device_util_pct.mean"),
    ("GPU device utilization p95 (%)", "summary.gpu_device_util_pct.p95"),
    ("GPU device memory-controller utilization (%)", "telemetry.gpu_memory_util_pct.mean"),
    ("GPU device memory (MiB)", "summary.gpu_memory_mib.mean"),
    ("GPU device power (W; not flight attribution)", "summary.gpu_power_w.mean"),
    ("Observed source frame records", "source_logged.frames"),
    ("Observed source readback width (pixels/frame)", "source_logged.width.mean"),
    ("Observed source depth-readback pixels (/frame)", "source_logged.readback_pixels.mean"),
    ("Observed source conversion rays (/frame)", "source_logged.conversion_rays.mean"),
    ("Observed source generated points (/frame)", "source_logged.generated_points.mean"),
    ("Observed source cloud payload (bytes/frame)", "source_logged.bytes.mean"),
    ("Map total elapsed mean (ms/frame)", "total_ms_mean"),
    ("Map total elapsed p95 (ms/frame)", "summary.map_Total_ms.p95"),
    ("Map total elapsed max (ms/frame)", "summary.map_Total_ms.max"),
    ("Map raycast elapsed mean (ms/frame)", "raycast_ms_mean"),
    ("Map update elapsed mean (ms/frame)", "update_ms_mean"),
    ("Map inflation elapsed mean (ms/frame; nested)", "inflation_ms_mean"),
    ("Map processed frames / mission time (Hz proxy)", "map_frames_s"),
    ("Trajectory commits (Hz)", "trajectory_commit_hz"),
    ("Goal retransmissions coalesced", "summary.goal_identity_audit.coalesced"),
    ("Demand replan checks (latest cumulative report)", "demand_latest_cumulative.checks"),
    ("Demand replans skipped (latest cumulative report)", "demand_latest_cumulative.counts.SKIP"),
    ("Unprofiled planner callback latency (ms)", "planner_callback_latency_ms_mean_unprofiled"),
    ("Frontend cloud elapsed mean (ms/frame)", "filter_cloud_compute_ms_mean"),
    ("Frontend cloud elapsed max (ms/frame)", "filter_cloud_compute_ms_max"),
    ("Map points mean (/frame)", "pts_mean"),
    ("Map points / mission time (points/s proxy)", "map_points_s"),
    ("Map payload / mission time (MiB/s proxy, logical edge)", "map_payload_mib_s"),
    ("Sensor report payload (MiB/s, logical edge; own span)", "sensor_payload_mib_s"),
    ("Planner ingress / mission time (MiB/s proxy, logical edge)", "planner_ingress_payload_mib_s"),
    ("DDS cloud payload (MiB/s, logical messages)", "dds_cloud_payload_mib_s"),
    ("Physical wire bandwidth (MiB/s)", "physical_wire_mib_s"),
    ("LiDAR source frequency (Hz)", "sensor_hz"),
    ("Received odometry frequency (Hz)", "summary.message_intervals.odometry.mean_received_hz"),
    ("Received command frequency (Hz; holds included)", "summary.message_intervals.command.mean_received_hz"),
    ("Odometry receipt p99 gap (ms)", "summary.message_intervals.odometry.receipt_interval.p99_ms"),
    ("Odometry receipt max gap (ms)", "summary.message_intervals.odometry.receipt_interval.max_ms"),
    ("Actual FSM main callback frequency (profiled only)", "summary.small_pool_timing.callback_hz.fsm_main_callback"),
    ("Actual FSM command callback frequency (profiled only)", "summary.small_pool_timing.callback_hz.fsm_command_callback"),
    ("Observed source Sector-to-Full activations", "source_logged.sector_to_full_count"),
    ("Observed source Full-to-Sector returns", "source_logged.full_to_sector_count"),
    ("Event recovery cycles (frontend state)", "frontend_stats.event_recovery_cycles"),
    ("Event recovery completed (frontend state)", "frontend_stats.event_recovery_completed"),
    ("Certified recovery cycles opened", "recovery_audit.opened_cycles"),
    ("Certified recovery cycles completed", "recovery_audit.completed_cycles_count"),
    ("Recovery cycles outstanding", "recovery_audit.outstanding_cycles_count"),
    ("Trajectory guard Full-open duty (%)", "filter_trajectory_guard_open_duty_pct"),
    ("Guard active duration (s)", "guard_recovery_active_duration_s"),
]


def format_stats(stats):
    if not stats or stats["n"] == 0:
        return "N/A"
    sd = f" ± {stats['sd']:.4g}" if stats["sd"] is not None else " (n=1)"
    return f"{stats['mean']:.5g}{sd} [{stats['min']:.5g}, {stats['max']:.5g}]"


def write_report(output, runs, cohorts, warnings, supplements):
    output.mkdir(parents=True, exist_ok=True)
    metrics = sorted({key for run in runs for key in run["metrics"]} | {key for _, key in DISPLAY})
    payload = dict(schema="cpu-validation-comparison-v1", notes=NOTES, warnings=warnings,
                   runs=runs, cohorts=cohorts, profiled_stage_supplements=supplements)
    (output / "comparison.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    with (output / "run_metrics.csv").open("w", newline="") as stream:
        fields = ["candidate", "cpu_profile", "map", "mode", "run", "source", "protocol_fingerprint", *metrics]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for run in runs:
            writer.writerow({**{key: run[key] for key in fields[:7]}, **run["metrics"]})
    with (output / "all_metrics.csv").open("w", newline="") as stream:
        fields = ["candidate", "profile", "map", "mode", "category", "metric", "n", "n_missing",
                  "mean", "sd", "min", "max", "reduction_vs_full_pct", "note"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for cohort in cohorts:
            for mode, values in cohort["modes"].items():
                for metric, stats in values["metrics"].items():
                    writer.writerow({**{k: cohort[k] for k in ("candidate", "profile", "map")},
                                     "mode": mode, "category": category(metric), "metric": metric,
                                     **stats, "note": metric_note(metric)})
    with (output / "metric_inventory.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["metric", "category", "observed_runs", "unavailable_runs", "note"])
        writer.writeheader()
        for metric in metrics:
            observed = sum(run["metrics"].get(metric) is not None for run in runs)
            writer.writerow(dict(metric=metric, category=category(metric), observed_runs=observed,
                                 unavailable_runs=len(runs)-observed, note=metric_note(metric)))
    stage_fields = ["source", "mode", "process_index", "window_duration_s", "stage", "calls",
                    "inclusive_cpu_s", "exclusive_cpu_s", "mean_used_cores_exclusive",
                    "inclusive_cpu_ms_per_call", "clock_errors", "calls_per_window_s", "exclusive_cpu_ms_per_call",
                    "reduction_vs_full_exclusive_mean_pct", "reduction_vs_full_inclusive_ms_per_call_pct"]
    stage_rows = []
    for supplement in supplements:
        for mode, data in supplement["data"].items():
            if mode not in MODES or not isinstance(data, dict):
                continue
            for index, process in enumerate(data.get("processes", [])):
                for stage in process.get("stages", []):
                    duration, calls = numeric(process.get("duration_s")), numeric(stage.get("calls"))
                    exclusive = numeric(stage.get("exclusive_cpu_s"))
                    stage_rows.append(dict(source=supplement["source"], mode=mode, process_index=index,
                                           window_duration_s=process.get("duration_s"),
                                           **{key: stage.get(key) for key in stage_fields[4:11]},
                                           calls_per_window_s=calls/duration if duration and calls is not None else None,
                                           exclusive_cpu_ms_per_call=1000*exclusive/calls if calls and exclusive is not None else None))
    for row in stage_rows:
        matches = [other for other in stage_rows if other["source"] == row["source"]
                   and other["process_index"] == row["process_index"] and other["stage"] == row["stage"]
                   and other["mode"] == "full"]
        full = matches[0] if len(matches) == 1 else {}
        for field, suffix in (("mean_used_cores_exclusive", "exclusive_mean"),
                              ("inclusive_cpu_ms_per_call", "inclusive_ms_per_call")):
            before, after = numeric(full.get(field)), numeric(row.get(field))
            row[f"reduction_vs_full_{suffix}_pct"] = (
                100 * (before-after) / before if before and after is not None else None)
    with (output / "profiled_stages.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=stage_fields)
        writer.writeheader()
        writer.writerows(stage_rows)
    lines = ["# Full / Sector / Adaptive 연산량 비교 (Computational comparison)", "",
             "Values: run mean ± sample SD [minimum, maximum]. N/A is not zero.", ""]
    for cohort in cohorts:
        lines.extend([f"## {cohort['map']} — {cohort['candidate']} — {cohort['profile']}", "",
                      "| Outcome | Full | Sector | Adaptive |", "|---|---:|---:|---:|"])
        for label, key in (("Recorded attempts", "attempts"), ("Successes", "successes"),
                           ("Valid runs", "valid_runs"), ("Runs with contact", "contact_runs"),
                           ("Unknown contact outcome", "contact_unknown_runs")):
            lines.append("| " + label + " | " + " | ".join(str(cohort["modes"].get(m, {}).get(key, "N/A")) for m in MODES) + " |")
        planned = cohort.get("planned_attempts_per_mode")
        if planned is not None:
            state = "all planned run rows observed" if cohort["planned_slots_observed"] else "INCOMPLETE — planned rows still missing"
            lines.extend(["", f"Declared plan: {planned} runs per mode; {state}. Recording all rows is not a safety or performance acceptance decision."])
        else:
            lines.extend(["", "Planned run count unavailable in supplied root manifest; observed counts above do not establish campaign completion."])
        if not cohort["all_modes_completed_all_attempts"]:
            lines.extend(["", "WARNING: not all runs completed. Completion-time/CPU comparisons are outcome-confounded; failures remain in the tables."])
        lines.extend(["", "| Metric | Full | Sector | Adaptive | Sector reduction vs Full | Adaptive reduction vs Full |",
                      "|---|---:|---:|---:|---:|---:|"])
        for label, metric in DISPLAY:
            cells = [format_stats(cohort["modes"].get(mode, {}).get("metrics", {}).get(metric)) for mode in MODES]
            reductions = []
            for mode in ("sector", "adaptive"):
                value = cohort["modes"].get(mode, {}).get("metrics", {}).get(metric, {}).get("reduction_vs_full_pct")
                reductions.append("N/A" if value is None else f"{value:.2f}%")
            lines.append("| " + " | ".join([label, *cells, *reductions]) + " |")
        lines.append("")
    lines.extend(["## Instrumented stage CPU supplement (not primary CPU evidence)", "",
                  "Separate profiled windows, not complete mission windows. Only exclusive core means are shown below; inclusive CPU per call and all counts/windows are in `profiled_stages.csv`. No stage total is added to cgroup CPU.", ""])
    if stage_rows:
        for source in sorted({row["source"] for row in stage_rows}):
            rows = [row for row in stage_rows if row["source"] == source]
            lines.extend([f"Source: `{source}`", "", "| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |",
                          "|---|---:|---:|---:|"])
            for stage, index in sorted({(row["stage"], row["process_index"]) for row in rows}):
                cells = []
                for mode in MODES:
                    matches = [row for row in rows if row["stage"] == stage and row["process_index"] == index and row["mode"] == mode]
                    value = matches[0].get("mean_used_cores_exclusive") if len(matches) == 1 else None
                    cells.append("N/A" if numeric(value) is None else f"{value:.6g}")
                lines.append("| " + " | ".join([f"{stage} / {index}", *cells]) + " |")
            lines.append("")
    else:
        lines.extend(["No separately analyzed profiled stage file available yet; stage CPU is N/A, not zero.", ""])
    lines.extend(["## Interpretation and measurement boundaries", "", *["- " + note for note in NOTES], "",
                  "## Complete data", "", "- `all_metrics.csv`: all available numeric metrics, run-weighted statistics and signed reductions.",
                  "- `run_metrics.csv`: original run identity and per-run numeric observations, including failures.",
                  "- `metric_inventory.csv`: coverage and unavailable fields.",
                  "- `comparison.json`: full machine-readable report and separately tagged profiled stage supplements.",
                  "- Per-process/TID identities, trace event arrays, configuration strings remain in linked original artifacts; they are not cross-run scalar measurements.",
                  "- [Detailed measurement-scope audit](/root/super-sector-filter/docs/cpu_metric_scope_audit_20260916.md)."])
    if warnings:
        lines.extend(["", "## Data warnings", "", *["- " + warning for warning in warnings]])
    (output / "README.md").write_text("\n".join(lines) + "\n")
    write_korean_summary(output, cohorts)


def write_korean_summary(output, cohorts):
    rows = [
        ("주행시간 (s)", "mission_time_s"),
        ("실험 CPU 평균 (사용 코어 수)", "end_to_end_cpu_cores_mean"),
        ("실험 CPU 평균 (전체 논리 CPU 용량=100%)", "end_to_end_host_capacity_pct_mean"),
        ("주행 중 컴퓨터 전체 CPU (배경 포함, %)", "summary.host_cpu_pct.mean"),
        ("주행 전 baseline 컴퓨터 전체 CPU (배경 포함, %)", "summary.baseline_host_cpu_pct.mean"),
        ("측정 구간 누적 CPU (core-s)", "end_to_end_cpu_core_s"),
        ("CPU 측정 구간 (s)", "cgroup_cpu_duration_s"),
        ("실험 CPU 1초 표본 p95 (코어)", "end_to_end_cpu_cores_p95_1s"),
        ("실험 프로세스 RSS 표본 최대 (MiB)", "end_to_end_peak_rss_mib"),
        ("실험 프로세스 PSS 표본 최대 (MiB)", "end_to_end_peak_pss_mib"),
        ("GPU 장치 전체 사용률 (%)", "summary.gpu_device_util_pct.mean"),
        ("GPU 장치 전체 메모리 (MiB)", "summary.gpu_memory_mib.mean"),
        ("맵 갱신 경과시간 평균 (ms/frame)", "total_ms_mean"),
        ("맵 갱신 경과시간 p95 (ms/frame)", "summary.map_Total_ms.p95"),
        ("Raycast 경과시간 평균 (ms/frame)", "raycast_ms_mean"),
        ("맵 유입 포인트 (points/frame)", "pts_mean"),
        ("관측된 프레임의 변환 ray 수 (/frame)", "source_logged.conversion_rays.mean"),
        ("맵 입력 논리 payload/주행시간 (MiB/s 환산)", "map_payload_mib_s"),
        ("LiDAR 소스 주파수 (Hz)", "sensor_hz"),
        ("수신 odometry 주파수 (Hz)", "summary.message_intervals.odometry.mean_received_hz"),
        ("경로 commit 주파수 (Hz)", "trajectory_commit_hz"),
        ("소스 Sector→Full 전환 횟수", "source_logged.sector_to_full_count"),
        ("소스 Full→Sector 복귀 횟수", "source_logged.full_to_sector_count"),
        ("인증된 복구 완료 횟수", "recovery_audit.completed_cycles_count"),
    ]
    lines = ["# 연산량 비교 핵심 요약", "", "프로파일링 OFF 본시험만 집계합니다. 값은 회차 평균 ± 표본 표준편차 [최솟값, 최댓값]입니다.", ""]
    primary = [c for c in cohorts if c["profile"] == "unprofiled_primary"]
    if not primary:
        lines.append("프로파일링 OFF 본시험 데이터가 아직 없습니다. 프로파일링 ON 보조자료와 합산하지 않습니다.")
    for cohort in primary:
        lines.extend([f"## {cohort['map']} / {cohort['candidate']}", ""])
        n = cohort.get("planned_attempts_per_mode")
        if cohort.get("planned_slots_observed") is not True:
            lines.extend([f"주의: 계획된 모드당 {n if n is not None else '미확인'}회가 모두 수집된 최종 결과는 아닙니다.", ""])
        lines.extend(["| 결과 | Full | Sector | Adaptive |", "|---|---:|---:|---:|"])
        for label, field in (("완주/수행", "successes"), ("접촉이 발생한 회차/수행", "contact_runs")):
            cells = []
            for mode in MODES:
                data = cohort["modes"].get(mode)
                cells.append(f"{data[field]}/{data['attempts']}" if data else "N/A")
            lines.append("| " + " | ".join([label, *cells]) + " |")
        if not cohort["all_modes_completed_all_attempts"]:
            lines.extend(["", "미완주 회차도 제외하지 않았습니다. 모드별 완주 여부가 다르면 주행시간·누적 CPU 단순 비교에는 제한이 있습니다."])
        lines.extend(["", "| 항목 | Full | Sector | Adaptive | Sector 감소율 | Adaptive 감소율 |", "|---|---:|---:|---:|---:|---:|"])
        for label, metric in rows:
            cells = [format_stats(cohort["modes"].get(mode, {}).get("metrics", {}).get(metric)) for mode in MODES]
            for mode in ("sector", "adaptive"):
                value = cohort["modes"].get(mode, {}).get("metrics", {}).get(metric, {}).get("reduction_vs_full_pct")
                cells.append("N/A" if value is None else f"{value:.2f}%")
            lines.append("| " + " | ".join([label, *cells]) + " |")
        lines.append("")
    lines.extend(["## 해석 범위", "",
        "- 감소율은 Full 평균 대비 상대 감소율입니다. 음수는 증가이며, 주파수·안전거리 등의 감소가 반드시 좋은 것은 아닙니다.",
        "- 실험 CPU에는 시뮬레이터·frontend·planner·mission·launcher가 포함되고 외부 측정기는 제외됩니다. 시뮬레이터와 planner가 한 프로세스여서 순수 자율주행 CPU는 현재 N/A입니다.",
        "- 컴퓨터 전체 CPU는 배경 프로그램까지 포함한 시스템 관측값이고, 실험 CPU는 해당 실험 프로세스만의 관측값입니다. 주행 전 baseline을 전체 CPU에서 빼도 알고리즘의 인과적 CPU 비용이 되지는 않습니다.",
        "- RSS/PSS 최대치는 주기적·경계 시점 표본의 최대값입니다. 여러 프로세스의 RSS 합은 공유 페이지를 중복 계산할 수 있어, 물리 메모리 비교에는 PSS도 함께 확인합니다.",
        "- 누적 CPU는 주행시간보다 조금 넓은 cgroup 측정 구간입니다. CPU core-s를 주행시간으로 나눠 평균 사용률을 재계산하면 안 됩니다.",
        "- GPU는 배경 작업을 포함한 장치 전체 값입니다. 논리 payload는 실제 네트워크·PCIe·메모리 대역폭이 아니며, 같은 버퍼를 전달하는 여러 구간을 합하면 중복됩니다.",
        "- 맵 경과시간은 CPU 시간이 아니고 inflation 등 하위 시간은 중첩됩니다. 누적해서 CPU 총량으로 주장하지 않습니다.",
        "- 미측정은 N/A이며 0이 아닙니다. OFF 본시험에서 개별 planner CPU 단계·실제 FSM callback 주파수는 별도 ON 보조자료로만 확인합니다.",
        "- 전환 횟수는 연속된 소스 프레임 로그의 실제 시야 변경입니다. 복구 완료는 새 Full 관측·맵 갱신·경로 인증의 로그 검증 횟수이며, 초기 복구도 포함합니다. 회피한 충돌 횟수로 해석하지 않습니다.",
        "- 전체 항목과 회차별 원자료: README.md, all_metrics.csv, run_metrics.csv, metric_inventory.csv, profiled_stages.csv, comparison.json."])
    (output / "summary_ko.md").write_text("\n".join(lines) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, action="append", required=True,
                        help="Root containing per-run plan.json/raw.csv; can repeat")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    runs, warnings = load_runs(args.campaign, args.repo)
    if not runs:
        parser.error("No readable run rows with adjacent plan.json")
    supplements = []
    for folder in sorted({Path(run["source"]).parent for run in runs if run["cpu_profile"] is True}):
        path = folder / "thread_cpu_summary.json"
        if path.is_file():
            supplements.append(dict(source=str(path), data=read_json(path),
                                    scope="Instrumented diagnostic window only; inclusive stages nest; do not sum inclusive CPU or merge with unprofiled mission accounting."))
    cohorts = aggregate(runs)
    planned_coverage(cohorts, args.campaign)
    write_report(args.output, runs, cohorts, warnings, supplements)
    print(json.dumps(dict(runs=len(runs), cohorts=len(cohorts), warnings=len(warnings), output=str(args.output))))


if __name__ == "__main__":
    main()
