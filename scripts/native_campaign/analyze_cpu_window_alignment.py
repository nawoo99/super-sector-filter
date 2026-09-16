#!/usr/bin/env python3
"""Offline CPU-window accounting without interpolating partial sample intervals.

The interval bounds apply to counter-reported CPU. Stage deltas are attributed
at scope completion, not a perfectly clipped physical CPU integral. Therefore
their subtraction is an accounting residual, not an exact bound on the amount
of truly uninstrumented work. No ROS, subprocess, build, or runtime writes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def finite(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label}: finite number required")
    return float(value)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def interval(start, end, cpu, *, next_start=None, index=None):
    """A delta between two cumulative reads; optional conservative read brackets.

    Collector timestamp m[i] precedes its actual counter reads. As collection
    is sequential, read q[i] is in [m[i],m[i+1]]. The delta reported by row i
    belongs to [q[i-1],q[i]], not necessarily [m[i-1],m[i]].
    """
    start, end, cpu = finite(start, "start"), finite(end, "end"), finite(cpu, "cpu")
    if end <= start or cpu < 0:
        raise ValueError("nonpositive duration or negative CPU delta")
    if next_start is None:
        return dict(start_earliest=start, start_latest=start,
                    end_earliest=end, end_latest=end, cpu_core_s=cpu, index=index,
                    counter_source="legacy_percentage_nominal_timestamp")
    after = finite(next_start, "next timestamp")
    if after <= end:
        raise ValueError("next timestamp must follow current timestamp")
    return dict(start_earliest=start, start_latest=end,
                end_earliest=end, end_latest=after, cpu_core_s=cpu, index=index,
                counter_source="legacy_percentage_next_sample_bracket")


def bound_intervals(intervals, start, end):
    """Nonnegative CPU: enclosed deltas form a lower bound; all possible
    intersecting deltas form an upper bound only with an unbroken read chain
    spanning the complete target. Partial intervals are NEVER prorated.
    """
    start, end = finite(start, "window start"), finite(end, "window end")
    if end <= start:
        raise ValueError("empty profile window")
    values = sorted(intervals, key=lambda row: row["end_earliest"])
    for row in values:
        for key in ("start_earliest", "start_latest", "end_earliest", "end_latest", "cpu_core_s"):
            finite(row[key], key)
        if (row["cpu_core_s"] < 0 or row["start_latest"] < row["start_earliest"] or
                row["end_latest"] < row["end_earliest"] or row["end_earliest"] <= row["start_earliest"]):
            raise ValueError("invalid interval")
    possible = [row for row in values if row["start_earliest"] < end and row["end_latest"] > start]
    enclosed = [row for row in possible if row["start_earliest"] >= start and row["end_latest"] <= end]
    boundaries = [row for row in possible if row not in enclosed]
    gaps = []
    for a, b in zip(possible, possible[1:]):
        left = (a["end_earliest"], a["end_latest"])
        right = (b["start_earliest"], b["start_latest"])
        if any(abs(x - y) > 1e-7 for x, y in zip(left, right)):
            gaps.append(dict(previous_end_bracket=left, next_start_bracket=right))
    covered = bool(possible) and not gaps and possible[0]["start_latest"] <= start and possible[-1]["end_earliest"] >= end
    lower = sum(row["cpu_core_s"] for row in enclosed)
    possible_sum = sum(row["cpu_core_s"] for row in possible)
    upper = possible_sum if covered else None
    duration = end - start
    return dict(window_duration_s=duration, complete_counter_chain=covered,
                wholly_enclosed_intervals=len(enclosed), possible_intersecting_intervals=len(possible),
                boundary_intervals=len(boundaries), missing_chain_edges=gaps,
                enclosed_cpu_core_s=lower, possible_intersection_cpu_core_s=possible_sum,
                lower_cpu_core_s=lower, upper_cpu_core_s=upper,
                lower_mean_cores=lower / duration,
                upper_mean_cores=None if upper is None else upper / duration,
                boundary_uncertainty_core_s=None if upper is None else upper - lower,
                wholly_enclosed_nominal_span_s=sum(row["end_earliest"] - row["start_earliest"] for row in enclosed),
                boundary_records=boundaries, interpolation_used=False)


class MissingCounter(ValueError):
    """A broken identity/read chain, which must remain a gap, never zero CPU."""


def _raw_counters(row, key, identity):
    if key not in row or not isinstance(row[key], list):
        raise MissingCounter(f"missing raw {key}")
    result = {}
    for item in row[key]:
        if not isinstance(item, dict) or identity not in item:
            raise ValueError("malformed raw counter entry")
        value = item[identity]
        if value in result:
            raise ValueError("duplicate raw counter identity")
        if identity == "pid" and type(value) is not int:
            raise ValueError("raw process PID must be an integer")
        if identity == "path" and not isinstance(value, str):
            raise ValueError("raw cgroup path must be a string")
        result[value] = item
    return result


def _read_bounds(item, row):
    first = finite(item.get("read_monotonic_start_s"), "read start")
    last = finite(item.get("read_monotonic_end_s"), "read end")
    if first > last or first < finite(row.get("monotonic_s"), "row timestamp"):
        raise ValueError("invalid actual counter-read bracket")
    return first, last


def precise_counter_interval(row, previous, pid, scope, index):
    """Use cumulative deltas and actual brackets. New malformed/reset evidence
    must not fall back to old percentage fields that clamp counter decreases.
    """
    if any(type(item.get("raw_cpu_counters_version")) is not int or
           item["raw_cpu_counters_version"] != 1 for item in (row, previous)):
        raise MissingCounter("raw-counter schema changed/missing at interval boundary")
    group = scope == "experiment_cgroup"
    key, identity = ("cgroup_cpu_cumulative", "path") if group else ("experiment_process_cumulative", "pid")
    current, old = _raw_counters(row, key, identity), _raw_counters(previous, key, identity)
    if scope == "composed_process":
        selected = {pid}
        if pid not in current or pid not in old:
            raise MissingCounter("composed process raw counter missing")
    else:
        if set(current) != set(old) or not current:
            raise MissingCounter("raw counter scope membership changed/missing")
        selected = set(current)
        if scope == "noncomposed_processes":
            selected.discard(pid)
            if not selected:
                raise MissingCounter("no noncomposed raw process counters")
    if group and (set(current) != set(row.get("cgroup_paths", [])) or
                  set(old) != set(previous.get("cgroup_paths", []))):
        raise MissingCounter("raw cgroup counters do not cover declared experiment scope")
    before_reads, after_reads, cpu = [], [], 0.0
    for identity_value in selected:
        a, b = old[identity_value], current[identity_value]
        if group:
            prior, latest = a.get("usage_usec"), b.get("usage_usec")
            if prior is None or latest is None:
                raise MissingCounter("raw cgroup CPU read unavailable")
            if type(prior) is not int or type(latest) is not int or min(prior, latest) < 0:
                raise ValueError("invalid cumulative cgroup CPU counter")
            delta = (latest - prior) / 1e6
        else:
            created_before = finite(a.get("create_time"), "prior process create_time")
            created_after = finite(b.get("create_time"), "current process create_time")
            if created_before != created_after or (a.get("name"), a.get("scope")) != (b.get("name"), b.get("scope")):
                raise MissingCounter("PID reused or process identity changed")
            for item in (a, b):
                user = finite(item.get("cpu_user_s"), "cumulative user CPU")
                system = finite(item.get("cpu_system_s"), "cumulative system CPU")
                total = finite(item.get("cpu_total_s"), "cumulative total CPU")
                if min(user, system, total) < 0 or abs(total - user - system) > 1e-8:
                    raise ValueError("inconsistent cumulative process CPU counters")
            delta = b["cpu_total_s"] - a["cpu_total_s"]
        if delta < 0:
            raise ValueError("cumulative CPU counter reset/decrease; percentage fallback prohibited")
        before = _read_bounds(a, previous)
        after = _read_bounds(b, row)
        if before[1] > after[0]:
            raise ValueError("counter-read brackets overlap/backtrack across samples")
        before_reads.append(before)
        after_reads.append(after)
        cpu += delta
    return dict(start_earliest=min(v[0] for v in before_reads), start_latest=max(v[1] for v in before_reads),
                end_earliest=min(v[0] for v in after_reads), end_latest=max(v[1] for v in after_reads),
                cpu_core_s=cpu, index=index, counter_source="raw_cumulative_actual_read_brackets",
                identities=sorted(selected), process_create_time_checked=not group)


def _process_values(row):
    result = {}
    for entry in row.get("experiment_processes", []):
        pid = entry.get("pid")
        if type(pid) is not int or pid in result:
            raise ValueError("invalid/duplicate telemetry process PID")
        pct = finite(entry.get("cpu_pct_one_core"), "process CPU%")
        if pct < 0:
            raise ValueError("negative process CPU%")
        result[pid] = (pct / 100.0, entry.get("name"), entry.get("scope"))
    return result


def telemetry_intervals(rows, mode, pid, scope, *, bracket_reads=False):
    """Construct deltas only when adjacent scope identities are continuous.

    Missing samples remain gaps. cgroup totals are a separate, inclusive scope
    and are never added to process totals. Caller chooses one scope at a time.
    """
    if scope not in ("composed_process", "noncomposed_processes", "experiment_process_sum", "experiment_cgroup"):
        raise ValueError("unknown accounting scope")
    output = []
    omitted = []
    for index in range(1, len(rows)):
        row, previous = rows[index], rows[index - 1]
        if row.get("mode") != mode or not row.get("campaign_active"):
            continue
        now = finite(row.get("monotonic_s"), "sample time")
        old = finite(previous.get("monotonic_s"), "previous sample time")
        dt = finite(row.get("interval_s"), "sample duration")
        if dt <= 0 or now <= old or abs((now - old) - dt) > 1e-6:
            raise ValueError("sample interval does not match adjacent monotonic timestamps")
        if previous.get("mode") != mode or not previous.get("campaign_active"):
            omitted.append(dict(index=index, reason="no previous active same-mode scope"))
            continue
        # Both requested output variants prefer the precise evidence when
        # present. The old nominal/next-sample distinction is C18 fallback only.
        if "raw_cpu_counters_version" in row or "raw_cpu_counters_version" in previous:
            try:
                output.append(precise_counter_interval(row, previous, pid, scope, index))
            except MissingCounter as error:
                omitted.append(dict(index=index, reason=str(error), percentage_fallback_prohibited=True))
            continue
        if bracket_reads and index + 1 >= len(rows):
            omitted.append(dict(index=index, reason="no next sample to bound read completion"))
            continue
        current_procs, old_procs = _process_values(row), _process_values(previous)
        if scope == "composed_process":
            if pid not in current_procs or pid not in old_procs or current_procs[pid][1:] != old_procs[pid][1:]:
                omitted.append(dict(index=index, reason="composed PID identity missing/changed"))
                continue
            cores = current_procs[pid][0]
        elif scope in ("noncomposed_processes", "experiment_process_sum"):
            if set(current_procs) != set(old_procs) or any(current_procs[p][1:] != old_procs[p][1:] for p in current_procs):
                omitted.append(dict(index=index, reason="experiment process membership changed"))
                continue
            cores = sum(values[0] for key, values in current_procs.items()
                        if scope == "experiment_process_sum" or key != pid)
        else:
            paths = row.get("cgroup_paths", [])
            if not paths or paths != previous.get("cgroup_paths") or row.get("cgroup_interval_cores") is None:
                omitted.append(dict(index=index, reason="cgroup delta/identity missing or changed"))
                continue
            cores = finite(row["cgroup_interval_cores"], "cgroup cores")
            if cores < 0:
                raise ValueError("negative cgroup cores")
        output.append(interval(old, now, cores * dt,
                               next_start=rows[index + 1]["monotonic_s"] if bracket_reads else None,
                               index=index))
    return output, omitted


def stage_accounting(process):
    start = finite(process.get("first_report_monotonic_s"), "first report")
    end = finite(process.get("last_report_monotonic_s"), "last report")
    duration = finite(process.get("duration_s"), "report duration")
    if duration <= 0 or abs(end - start - duration) > 1e-6:
        raise ValueError("profile duration/boundary mismatch")
    stages = process.get("stages", [])
    names = set()
    total = 0.0
    output = []
    for stage in stages:
        name = stage.get("stage")
        if not isinstance(name, str) or name in names:
            raise ValueError("duplicate/invalid stage name")
        names.add(name)
        exclusive = finite(stage.get("exclusive_cpu_s"), "exclusive stage CPU")
        inclusive = finite(stage.get("inclusive_cpu_s"), "inclusive stage CPU")
        if exclusive < -1e-10 or inclusive < -1e-10 or stage.get("clock_errors") != 0:
            raise ValueError("negative/reset stage counters or profiler clock error")
        # Small decimal roundoff is allowed; inclusive scopes are NOT summed.
        total += exclusive
        output.append(dict(stage=name, exclusive_cpu_core_s=exclusive,
                           exclusive_mean_cores=exclusive / duration,
                           inclusive_cpu_core_s=stage["inclusive_cpu_s"], calls=stage.get("calls")))
    claimed = finite(process.get("sum_exclusive_mean_cores"), "claimed exclusive sum")
    if abs(total / duration - claimed) > 1e-8:
        raise ValueError("profile exclusive total is inconsistent with stage deltas")
    return dict(start_monotonic_s=start, end_monotonic_s=end, duration_s=duration,
                exclusive_cpu_core_s=total, exclusive_mean_cores=total / duration,
                stages=sorted(output, key=lambda row: row["exclusive_cpu_core_s"], reverse=True))


def accounting_residual(bounds, stage_cpu):
    """Subtract an observed stage-counter delta, not a claimed exact physical integral."""
    lower = bounds["lower_cpu_core_s"] - stage_cpu
    upper = None if bounds["upper_cpu_core_s"] is None else bounds["upper_cpu_core_s"] - stage_cpu
    return dict(lower_accounting_cpu_core_s=lower, upper_accounting_cpu_core_s=upper,
                lower_accounting_mean_cores=lower / bounds["window_duration_s"],
                upper_accounting_mean_cores=None if upper is None else upper / bounds["window_duration_s"],
                negative_lower_is_not_clamped=True,
                physical_uninstrumented_cpu_bound=False,
                reason="Stage counters charge entire scopes at completion and report fields are not one atomic snapshot; boundary scope/report skew is not measured.")


def raw_cgroup_summary(path):
    with Path(path).open() as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) < 2:
        raise ValueError("raw cgroup trace has fewer than two observations")
    times = [float(row["elapsed_s"]) for row in rows]
    if any(not math.isfinite(t) for t in times) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("raw cgroup timestamps nonfinite/nonmonotonic")
    result = dict(path=str(Path(path).resolve()), sha256=digest(path), samples=len(rows),
                  elapsed_span_s=times[-1] - times[0], alignment_available=False,
                  reason="CSV stores relative elapsed_s only; absolute monotonic origin was not persisted. No origin inferred from launch, CPU shape, or wall timestamps.")
    for scope in ("algorithm", "end_to_end"):
        counters = [int(row[f"{scope}_usage_usec"]) for row in rows]
        if any(v < 0 for v in counters) or any(b < a for a, b in zip(counters, counters[1:])):
            raise ValueError("raw cgroup cumulative counter reset")
        result[f"{scope}_observed_cpu_core_s"] = (counters[-1] - counters[0]) / 1e6
    return result


LIMITATIONS = [
    "All means below divide by the same profiler report-window duration, not by the shorter enclosed-sample duration.",
    "New telemetry cumulative counters use actual before/after read brackets in BOTH variants; no midpoint is invented. For legacy C18 only, nominal bounds assume reads at sample-start while the conservative fallback allows reads before the next sampling pass.",
    "Deltas are never linearly interpolated or prorated. Enclosed intervals supply the lower amount; all possibly intersecting intervals supply the upper amount only if the counter-read chain covers the window.",
    "Bounds concern counter-reported CPU. /proc user/system counters remain tick-quantized. New telemetry checks PID create_time and actual read brackets; legacy C18 lacks those fields and therefore only PID/name/scope continuity can be checked. Cgroup path replacement without a counter reset remains unproven.",
    "Stage counters are completion-attributed and independently loaded, not exact clipped-window integrals. Unknown active-scope boundary CPU and report skew prevent calling the subtracted interval a strict physical uninstrumented-CPU bound.",
    "Exclusive stage CPU only is summed. Inclusive parent stages overlap children and must not be added; work performed by spawned worker threads is not implicitly attributed to their caller.",
    "Composed-process residual includes uninstrumented useful callbacks, executor/DDS work, profiling overhead and boundary attribution error. It is not all avoidable waste.",
    "Experiment cgroup includes launcher/mission/other experiment processes; process sum and cgroup are alternative measurements, never added. Observer CPU is outside this scope.",
    "Raw cumulative cgroup CSV remains useful for its own full span, but cannot be rigorously aligned without a persisted absolute monotonic origin.",
    "This is a profiled single-run offline diagnostic, not new flight evidence or an unprofiled40% acceptance result.",
]


def analyze(folder):
    folder = Path(folder)
    profile_path, telemetry_path = folder / "thread_cpu_summary.json", folder / "telemetry.jsonl"
    profile = json.loads(profile_path.read_text())
    telemetry = [json.loads(line) for line in telemetry_path.read_text().splitlines() if line.strip()]
    result = dict(schema="cpu-window-alignment-v1", input_folder=str(folder.resolve()),
                  inputs={str(path.resolve()): digest(path) for path in (profile_path, telemetry_path)},
                  modes={}, limitations=LIMITATIONS, interpolation_used=False)
    for mode, mode_profile in profile.items():
        if not mode_profile.get("available"):
            result["modes"][mode] = dict(available=False, reason="no stage profile")
            continue
        processes = []
        for process in mode_profile["processes"]:
            pid = process["pid"]
            stage = stage_accounting(process)
            scopes = {}
            for scope in ("composed_process", "noncomposed_processes", "experiment_process_sum", "experiment_cgroup"):
                scopes[scope] = {}
                for bracket_reads in (False, True):
                    values, omitted = telemetry_intervals(telemetry, mode, pid, scope, bracket_reads=bracket_reads)
                    bound = bound_intervals(values, stage["start_monotonic_s"], stage["end_monotonic_s"])
                    bound["omitted_samples"] = omitted
                    bound["counter_sources"] = sorted({item["counter_source"] for item in values
                        if item["start_earliest"] < stage["end_monotonic_s"] and
                        item["end_latest"] > stage["start_monotonic_s"]})
                    if scope != "noncomposed_processes":
                        bound["stage_subtracted_accounting_residual"] = accounting_residual(bound, stage["exclusive_cpu_core_s"])
                    scopes[scope]["read_bracket_conservative" if bracket_reads else "nominal_timestamp"] = bound
            processes.append(dict(pid=pid, stage_profile=stage, scopes=scopes))
        raw = [raw_cgroup_summary(path) for path in sorted((folder / "artifacts").glob(f"*_{mode}.attempt*.cgroup.csv"))]
        result["modes"][mode] = dict(available=True, processes=processes, raw_cgroup_traces=raw)
    return result


def markdown(report):
    lines = ["# CPU report-window alignment", "", "No partial interval interpolation; input artifacts were not modified.", "",
             "New cumulative evidence uses actual read brackets in both columns; nominal/conservative alternatives apply only to legacy telemetry.", "",
             "| Mode | Window s | Profiled exclusive cores | Composed bounds (legacy nominal fallback) | Composed bounds (legacy conservative fallback) | Conservative stage-subtracted accounting residual |",
             "|---|---:|---:|---:|---:|---:|"]
    def pair(a, b):
        return f"{a:.6f}–{b:.6f}" if b is not None else f">={a:.6f}; upper unavailable"
    for mode, data in report["modes"].items():
        for process in data.get("processes", []):
            stage = process["stage_profile"]
            nominal = process["scopes"]["composed_process"]["nominal_timestamp"]
            conservative = process["scopes"]["composed_process"]["read_bracket_conservative"]
            residual = conservative["stage_subtracted_accounting_residual"]
            lines.append(f"| {mode} | {stage['duration_s']:.6f} | {stage['exclusive_mean_cores']:.6f} | "
                         f"{pair(nominal['lower_mean_cores'], nominal['upper_mean_cores'])} | "
                         f"{pair(conservative['lower_mean_cores'], conservative['upper_mean_cores'])} | "
                         f"{pair(residual['lower_accounting_mean_cores'], residual['upper_accounting_mean_cores'])} |")
    lines += ["", "Residual ranges are **accounting ranges, not exact physical uninstrumented-work bounds**; see limitations below.", "",
              "## Dominant measured stages", "", "| Mode | Stage | Exclusive CPU-s | Exclusive cores |", "|---|---|---:|---:|"]
    for mode, data in report["modes"].items():
        for process in data.get("processes", []):
            for row in process["stage_profile"]["stages"][:8]:
                lines.append(f"| {mode} | {row['stage']} | {row['exclusive_cpu_core_s']:.6f} | {row['exclusive_mean_cores']:.6f} |")
    lines += ["", "## Interpretation limits", ""] + ["- " + value for value in report["limitations"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    output = args.output_dir or args.folder / "window_alignment"
    if output.exists():
        parser.error("refusing to overwrite existing analysis directory")
    report = analyze(args.folder)
    output.mkdir(parents=False, exist_ok=False)
    (output / "alignment.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    (output / "README.md").write_text(markdown(report))
    print(markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
