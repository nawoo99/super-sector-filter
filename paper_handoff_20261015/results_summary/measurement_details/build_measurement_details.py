#!/usr/bin/env python3
"""Lossless exports of the 240 frozen run summaries, with resource statistics.

Writes only new files in measurement_details. Reads the archived trial copies
and verifies their original frozen hashes; never launches or changes runtime.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
FROZEN = Path("/root/share/here/v6_frozen_20261008")
RECORDED = PACKAGE / "recorded_trials"
META_FIELDS = ("cohort", "map", "map_label", "environment", "repeat", "mode", "run")
MAP_LABELS = {"gapfree_d1_m01": "Map1", "gapfree_d1_m02": "Map2",
              "gapfree_d1_m03": "Map3", "gapfree_d1_m04": "Map4",
              "gapfree_d1_m05r2": "Map5-R2", "urban_blocks_u01": "Urban",
              "forest_cluster_f01": "Forest"}
SUMMARY_METRICS = {
    "host_cpu_pct": "% of whole-host capacity",
    "baseline_host_cpu_pct": "% of whole-host capacity",
    "observer_process_cpu_pct": "% of one logical CPU core",
    "gpu_device_util_pct": "% of whole GPU, background included",
    "gpu_memory_mib": "MiB, whole GPU, background included",
    "gpu_power_w": "W, whole GPU, background included",
    "baseline_gpu_device_util_pct": "% of whole GPU, background included",
    "cgroup_interval_cores": "logical CPU cores",
    "experiment_proc_sum_cores": "logical CPU cores",
}
MEMORY_CGROUP = ("algorithm_rss_kib", "algorithm_pss_kib", "algorithm_swap_kib",
                 "end_to_end_rss_kib", "end_to_end_pss_kib", "end_to_end_swap_kib")
MEMORY_TRACE = ("fsm_rss_kib", "fsm_pss_kib", "fsm_swap_kib", "system_available_kib",
                "system_swap_used_kib", "cgroup_memory_kib", "cgroup_swap_kib",
                "psi_some_avg10", "psi_full_avg10")
OUTPUTS = ("thread_profiles.csv", "process_profiles.csv", "run_summary_values.csv",
           "run_resource_summary.csv", "resource_summary_by_environment.csv",
           "resource_summary_by_map.csv", "resource_summary_separate_gate.csv",
           "coverage.json", "validation.json")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def load_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def write_json_new(path, value):
    require(path.parent == HERE, "Writes must remain in measurement_details")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def write_csv_new(path, rows, fields=None):
    require(path.parent == HERE, "Writes must remain in measurement_details")
    if fields is None:
        fields = list(rows[0])
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def number(value):
    if value is None or value == "" or isinstance(value, bool):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def percentile(values, probability=0.95):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * probability
    low, high = math.floor(position), math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def descriptive(values, expected_count=None):
    valid = [value for value in values if value is not None]
    total = len(values) if expected_count is None else expected_count
    return {"n": len(valid), "mean": statistics.mean(valid) if valid else None,
            "p95": percentile(valid), "max": max(valid) if valid else None,
            "n_missing": total - len(valid), "missing": not valid}


def escape_pointer(token):
    return str(token).replace("~", "~0").replace("/", "~1")


def nodes(value, pointer=""):
    """Preorder RFC6901 nodes; container markers retain empty/type information."""
    if isinstance(value, dict):
        yield pointer, "object", "{}"
        for key, item in value.items():
            yield from nodes(item, pointer + "/" + escape_pointer(key))
    elif isinstance(value, list):
        yield pointer, "array", "[]"
        for index, item in enumerate(value):
            yield from nodes(item, pointer + "/" + str(index))
    else:
        kind = ("null" if value is None else "boolean" if isinstance(value, bool)
                else "integer" if isinstance(value, int) else "number" if isinstance(value, float)
                else "string")
        yield pointer, kind, encode(value)


def flatten_record(value, prefix=""):
    result = {}
    for key, item in value.items():
        label = prefix + key
        if isinstance(item, dict) and item:
            result.update(flatten_record(item, label + "."))
        elif isinstance(item, (dict, list)):
            result[label] = encode(item)
        else:
            result[label] = item
    return result


def meta(row):
    label = MAP_LABELS[row["map"]]
    return {"cohort": row["cohort"], "map": row["map"], "map_label": label,
            "environment": "Normal1-5" if label.startswith("Map") else label,
            "repeat": int(row["repeat"]), "mode": row["mode"], "run": int(row["run"])}


def identity(row):
    return row["cohort"], row["map"], int(row["repeat"]), row["mode"], int(row["run"])


def verify_input(path, original, pins, sources):
    require(path.is_file() and not path.is_symlink(), f"Invalid archived input: {path}")
    require(path.resolve().is_relative_to(RECORDED.resolve()), f"Input outside recorded_trials: {path}")
    require(str(original) in pins, f"Input absent from frozen source inventory: {original}")
    expected = pins[str(original)]
    require(digest(path) == expected and digest(original) == expected, f"Frozen/copy hash mismatch: {path}")
    sources[str(original)] = {"archive_file": path.relative_to(PACKAGE).as_posix(), "sha256": expected}


def metric_definitions():
    result = {key: {"unit": unit, "source": "Original mode-summary n/mean/p95/max",
                    "sample_scope": "Recorded summary; flight and campaign_active for nonbaseline metrics"}
              for key, unit in SUMMARY_METRICS.items()}
    result["gpu_memory_util_pct"] = {"unit": "% of whole GPU, background included",
                                    "source": "Raw telemetry", "sample_scope": "phase=flight and campaign_active=true"}
    for index in range(20):
        result[f"host_logical_cpu_{index:02d}_pct"] = {
            "unit": "% of one logical CPU core", "source": "Raw telemetry host_per_logical_cpu_pct",
            "sample_scope": "phase=flight and campaign_active=true"}
    for field in MEMORY_CGROUP:
        result["fresh_" + field] = {"unit": "KiB", "source": "Original cgroup.csv",
                                   "sample_scope": "Only memory_sampled=true rows; whole recorded CPU-accounting window"}
    for field in MEMORY_TRACE:
        result["trace_" + field] = {"unit": "KiB" if field.endswith("_kib") else "% PSI avg10",
                                   "source": "Original memory.csv", "sample_scope": "All finite recorded trace samples"}
    return result


def resource_stats(summary, cgroup, memory, telemetry):
    metrics = {}
    for field in SUMMARY_METRICS:
        original = summary.get(field)
        if original is None:
            metrics[field] = descriptive([])
        else:
            require(isinstance(original, dict) and all(key in original for key in ("n", "mean", "p95", "max")),
                    f"Unexpected summary statistic structure: {field}")
            # Preserve original values exactly; never substitute a recomputation.
            metrics[field] = {key: original[key] for key in ("n", "mean", "p95", "max")}
            metrics[field].update(n_missing=None, missing=original["n"] == 0)
    active = [row for row in telemetry if row.get("phase") == "flight" and row.get("campaign_active") is True]
    metrics["gpu_memory_util_pct"] = descriptive([number(row.get("gpu_memory_util_pct")) for row in active])
    for index in range(20):
        values = []
        for row in active:
            values_in_row = row.get("host_per_logical_cpu_pct", [])
            values.append(number(values_in_row[index]) if index < len(values_in_row) else None)
        metrics[f"host_logical_cpu_{index:02d}_pct"] = descriptive(values)
    fresh = [row for row in cgroup if row.get("memory_sampled", "").strip().lower() == "true"]
    for field in MEMORY_CGROUP:
        metrics["fresh_" + field] = descriptive([number(row.get(field)) for row in fresh])
    for field in MEMORY_TRACE:
        metrics["trace_" + field] = descriptive([number(row.get(field)) for row in memory])
    return metrics, len(active), len(fresh)


def grouping(resources, kind, metrics):
    grouped = {}
    for row in resources:
        if kind == "separate_gate":
            if row["cohort"] != "separate_gate":
                continue
            label = row["environment"]
        else:
            if row["cohort"] != "main":
                continue
            label = row["environment"] if kind == "environment" else row["map_label"]
        grouped.setdefault((label, row["mode"]), []).append(row)
    result = []
    for (label, mode), rows in sorted(grouped.items()):
        record = {"cohort": "separate_gate" if kind == "separate_gate" else "main",
                  "group": label, "mode": mode, "n_runs": len(rows)}
        for metric in metrics:
            stats = descriptive([None if row[metric + "_missing"] else number(row[metric + "_mean"])
                                 for row in rows])
            for field, value in stats.items():
                name = {"n": "run_mean_n", "mean": "mean_of_run_means", "p95": "p95_of_run_means",
                        "max": "max_run_mean", "n_missing": "run_mean_missing_runs", "missing": "all_missing"}[field]
                record[metric + "_" + name] = value
            p95s = [None if row[metric + "_missing"] else number(row[metric + "_p95"]) for row in rows]
            maxima = [None if row[metric + "_missing"] else number(row[metric + "_max"]) for row in rows]
            record[metric + "_mean_run_p95"] = descriptive(p95s)["mean"]
            record[metric + "_mean_run_max"] = descriptive(maxima)["mean"]
        result.append(record)
    return result


def validate_profile_export(path, expected):
    rows = read_csv(path)
    require(len(rows) == len(expected), f"Profile export count mismatch: {path.name}")
    for row, source in zip(rows, expected):
        require(identity(row) == identity(source), f"Profile identity mismatch: {path.name}")
        record = json.loads(row["original_record_json"])
        require(encode(record) == source["original_record_json"], f"Lossless profile record mismatch: {path.name}")
        for key, value in flatten_record(record).items():
            require(row[key] == ("" if value is None else str(value)), f"Flattened profile value mismatch: {path.name}:{key}")
    return len(rows)


def validate_summary_values(path, cases):
    """Reconstruct every original JSON summary from the streamed long CSV."""
    count, validated, current, registry, restored = 0, 0, None, {}, None
    source_by_key = {identity(case["meta"]): case["summary"] for case in cases}

    def finish():
        nonlocal validated
        if current is not None:
            require(encode(restored) == encode(source_by_key[current]),
                    f"Long-format summary does not reconstruct losslessly: {current}")
            validated += 1

    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = identity(row)
            if key != current:
                finish()
                require(key in source_by_key, f"Unexpected summary identity: {key}")
                current, registry, restored = key, {}, None
            pointer, kind = row["json_pointer"], row["json_type"]
            require(pointer not in registry, f"Duplicate JSON pointer: {key}:{pointer}")
            value = json.loads(row["value_json"])
            require((kind == "object" and isinstance(value, dict)) or (kind == "array" and isinstance(value, list))
                    or kind not in {"object", "array"}, f"Bad container marker: {key}:{pointer}")
            if pointer == "":
                restored = value
            else:
                parent_pointer, token = pointer.rsplit("/", 1)
                parent = registry[parent_pointer]
                token = token.replace("~1", "/").replace("~0", "~")
                if isinstance(parent, list):
                    require(int(token) == len(parent), f"Unordered array index: {pointer}")
                    parent.append(value)
                else:
                    parent[token] = value
            registry[pointer] = value
            count += 1
        finish()
    require(validated == len(cases), "Not all 240 summaries reconstructed")
    return count, validated


def main():
    require(HERE.is_dir() and not HERE.is_symlink(), "Invalid output directory")
    require({path.name for path in HERE.iterdir()} == {Path(__file__).name},
            "Refusing existing measurement_details outputs; partial files are preserved")
    pins = load_json(FROZEN / "source_manifest.json")["sha256"]
    index = read_csv(RECORDED / "run_index.csv")
    require(len(index) == 240 and len({identity(row) for row in index}) == 240, "Expected 240 unique frozen runs")
    require(sum(row["cohort"] == "main" for row in index) == 210
            and sum(row["cohort"] == "separate_gate" for row in index) == 30, "Cohort count mismatch")
    metrics = metric_definitions()
    cases, sources, thread_rows, process_rows, resources = [], {}, [], [], []
    telemetry_total, active_total, node_total = 0, 0, 0
    thread_fields, process_fields = set(), set()
    for index_number, row in enumerate(index, 1):
        folder = PACKAGE / row["copied_directory"]
        original = Path(row["original_directory"])
        prefix = f"{row['map']}_run{row['run']}_{row['mode']}.attempt1"
        relative_inputs = (f"{row['mode']}_summary.json", "summary.json", "raw.csv", "telemetry.jsonl",
                           f"artifacts/{prefix}.cgroup.csv", f"artifacts/{prefix}.memory.csv")
        for relative in relative_inputs:
            verify_input(folder / relative, original / relative, pins, sources)
        summary = load_json(folder / f"{row['mode']}_summary.json")
        require(summary == load_json(folder / "summary.json")["results"][0], "Summary alias content differs")
        require(summary["map"] == row["map"] and summary["mode"] == row["mode"]
                and summary["run"] == int(row["run"]), "Summary identity differs")
        metadata = meta(row)
        for source_field, target, fields in (("threads_sorted_by_mean", thread_rows, thread_fields),
                                              ("processes", process_rows, process_fields)):
            for record_index, record in enumerate(summary[source_field]):
                flat = flatten_record(record)
                fields.update(flat)
                target.append({**metadata, "record_index": record_index, **flat,
                               "original_record_json": encode(record)})
        telemetry = []
        with (folder / "telemetry.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                require(line.strip(), "Blank telemetry JSONL record")
                telemetry.append(json.loads(line))
        cgroup = read_csv(folder / f"artifacts/{prefix}.cgroup.csv")
        memory = read_csv(folder / f"artifacts/{prefix}.memory.csv")
        values, active_count, fresh_count = resource_stats(summary, cgroup, memory, telemetry)
        resource = dict(metadata)
        for metric in metrics:
            for stat, value in values[metric].items():
                resource[metric + "_" + stat] = value
        resources.append(resource)
        telemetry_total += len(telemetry)
        active_total += active_count
        nodes_in_case = sum(1 for _ in nodes(summary))
        node_total += nodes_in_case
        cases.append({"meta": metadata, "summary": summary,
                      "summary_archive_file": (folder / f"{row['mode']}_summary.json").relative_to(PACKAGE).as_posix(),
                      "summary_sha256": pins[str(original / f"{row['mode']}_summary.json")],
                      "json_nodes": nodes_in_case, "telemetry_records": len(telemetry),
                      "active_flight_telemetry_records": active_count, "fresh_cgroup_memory_rows": fresh_count})
        if index_number % 30 == 0:
            print(f"READ_MEASUREMENTS {index_number}/240", flush=True)
    require(len(thread_rows) == 7600 and len(process_rows) == 1680, "Unexpected source profile record counts")
    require(telemetry_total == 21893, "Unexpected source telemetry record count")
    write_csv_new(HERE / "thread_profiles.csv", thread_rows,
                  list(META_FIELDS) + ["record_index"] + sorted(thread_fields) + ["original_record_json"])
    write_csv_new(HERE / "process_profiles.csv", process_rows,
                  list(META_FIELDS) + ["record_index"] + sorted(process_fields) + ["original_record_json"])
    long_path = HERE / "run_summary_values.csv"
    with long_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(META_FIELDS) + ["json_pointer", "json_type", "value_json"])
        writer.writeheader()
        for case_number, case in enumerate(cases, 1):
            for pointer, kind, value in nodes(case["summary"]):
                writer.writerow({**case["meta"], "json_pointer": pointer, "json_type": kind, "value_json": value})
            if case_number % 30 == 0:
                print(f"EXPORT_SUMMARY_VALUES {case_number}/240", flush=True)
    write_csv_new(HERE / "run_resource_summary.csv", resources)
    grouped = {"resource_summary_by_environment.csv": grouping(resources, "environment", metrics),
               "resource_summary_by_map.csv": grouping(resources, "map", metrics),
               "resource_summary_separate_gate.csv": grouping(resources, "separate_gate", metrics)}
    require([len(grouped[name]) for name in grouped] == [9, 21, 3], "Unexpected resource grouping counts")
    for filename, rows in grouped.items():
        write_csv_new(HERE / filename, rows)
    print("VALIDATING_LOSSLESS_EXPORTS", flush=True)
    threads_checked = validate_profile_export(HERE / "thread_profiles.csv", thread_rows)
    processes_checked = validate_profile_export(HERE / "process_profiles.csv", process_rows)
    nodes_checked, summaries_checked = validate_summary_values(long_path, cases)
    require(nodes_checked == node_total, "Summary-node count differs")
    # Verify original files again after all generated output writes.
    for original, source in sources.items():
        require(digest(Path(original)) == source["sha256"], f"Original changed during extraction: {original}")
        require(digest(PACKAGE / source["archive_file"]) == source["sha256"], "Archived input changed during extraction")
    generated = {name: {"bytes": (HERE / name).stat().st_size, "sha256": digest(HERE / name)}
                 for name in OUTPUTS if name not in {"coverage.json", "validation.json"}}
    coverage = {"schema": "complete-frozen-measurement-details-v1", "state": "VALIDATED",
                "created_utc": datetime.now(timezone.utc).isoformat(), "main_runs": 210, "separate_gate_runs": 30,
                "thread_profile_records": len(thread_rows), "process_profile_records": len(process_rows),
                "lossless_run_summary_json_nodes": node_total, "lossless_original_summaries": 240,
                "telemetry_records_archived_not_duplicated": telemetry_total,
                "active_flight_telemetry_records": active_total, "resource_run_rows": 240,
                "resource_environment_main_groups": 9, "resource_map_main_groups": 21,
                "resource_separate_gate_groups": 3, "resource_metric_definitions": metrics,
                "json_pointer_export": "RFC6901 preorder; explicit object/array markers including empty containers; scalar value_json retains null, bool, integer, float and string types",
                "group_statistic_scope": "Arithmetic statistics across run means; p95_of_run_means is not a pooled frame/sample p95. mean_run_p95 and mean_run_max average conditional per-run statistics.",
                "source_summary_missing_count_scope": "Original n/mean/p95/max retained exactly. n_missing=null for original summary metrics because attempted/missing observations were not enumerated. missing=true denotes n=0 or absent metric; such runs are excluded from grouped means even if an original placeholder statistic is zero.",
                "memory_scope": "Fresh cgroup memory only where memory_sampled=true; separate memory.csv finite samples retained in KiB. No carry-forward rows treated as fresh observations.",
                "gpu_scope": "Whole device including background; per-flight GPU attribution unavailable, no causal baseline subtraction",
                "cpu_scope": "cpu_pct_one_core is percent of one logical core, not host capacity. Short-lived process/thread sample counts differ; do not sum conditional means or add process and thread totals.",
                "raw_recording_paths": "recorded_trials holds all240 raw summaries/telemetry/trace files; no duplicated JSONL here",
                "source_files": sources, "cases": [{key: value for key, value in case.items() if key != "summary"} for case in cases],
                "generated_files": generated, "builder_sha256": digest(Path(__file__)),
                "new_simulations": 0, "runtime_changed": False, "original_results_changed": False}
    write_json_new(HERE / "coverage.json", coverage)
    validation = {"schema": "measurement-details-validation-v1", "valid": True, "errors": [],
                  "profile_records_checked": {"threads": threads_checked, "processes": processes_checked},
                  "original_summaries_reconstructed_exactly": summaries_checked, "summary_json_nodes_checked": nodes_checked,
                  "original_and_archived_source_files_rehashed_after_export": len(sources),
                  "original_values_changed": 0, "writes_outside_measurement_details": 0,
                  "new_simulations": 0, "full_telemetry_coverage": telemetry_total,
                  "generated_files": generated, "coverage_sha256": digest(HERE / "coverage.json")}
    write_json_new(HERE / "validation.json", validation)
    print(encode({"state": "MEASUREMENT_DETAILS_COMPLETE", "thread_records": threads_checked,
                  "process_records": processes_checked, "summary_nodes": nodes_checked,
                  "summaries_reconstructed": summaries_checked, "telemetry_records": telemetry_total,
                  "output_bytes": sum((HERE / name).stat().st_size for name in OUTPUTS)}), flush=True)


if __name__ == "__main__":
    main()
