#!/usr/bin/env python3
"""Build a versioned, source-checked package from existing V6 results only.

No simulations, runtime changes, raw outcome relabeling, or frozen-file writes.
Run with /usr/bin/python3 -s. Existing generated outputs are never overwritten.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


FROZEN = Path("/root/share/here/v6_frozen_20261008")
MAP_IMAGES = Path("/root/share/map_visualizations_20261010")
REPO = Path("/root/super-sector-filter")
MODES = ("full", "sector", "adaptive")
MODE_NAMES = {"full": "Full", "sector": "Active-Yaw Sector", "adaptive": "Adaptive"}
MAPS = [
    ("gapfree_d1_m01", "Map1", "Normal1-5"),
    ("gapfree_d1_m02", "Map2", "Normal1-5"),
    ("gapfree_d1_m03", "Map3", "Normal1-5"),
    ("gapfree_d1_m04", "Map4", "Normal1-5"),
    ("gapfree_d1_m05r2", "Map5-R2", "Normal1-5"),
    ("urban_blocks_u01", "Urban", "Urban"),
    ("forest_cluster_f01", "Forest", "Forest"),
]
MAP_INFO = {key: (label, env) for key, label, env in MAPS}
ENVIRONMENTS = ("Normal1-5", "Urban", "Forest")
PRIMARY_METRICS = (
    "cpu_cores", "cpu_core_s", "input_mib_s", "input_mib_run", "map_ms",
    "mapping_elapsed_s", "mapping_frames", "mapping_mean_ms_from_log", "map_frames_s", "mapping_points_total",
    "mapping_points_mean", "mapping_points_s", "mapping_max_ms", "mapping_p95_ms",
    "mapping_raycast_elapsed_s", "mapping_cache_update_elapsed_s", "mapping_inflation_elapsed_s",
    "host_cpu_pct_mean", "baseline_host_cpu_pct_mean", "experiment_host_capacity_pct",
)
EXTRA_METRICS = (
    "end_to_end_cpu_cores_p95_1s", "end_to_end_cpu_cores_max_1s", "cgroup_cpu_duration_s",
    "end_to_end_peak_rss_mib", "end_to_end_peak_pss_mib", "end_to_end_peak_swap_mib",
    "trajectory_commit_unique_generations", "trajectory_commit_span_s", "trajectory_commit_hz",
    "sensor_hz", "filter_frames", "filter_cloud_input_callbacks", "filter_cloud_input_hz",
    "filter_cloud_publish_hz", "filter_map_commit_hz", "filter_cloud_compute_ms_mean",
    "filter_cloud_compute_ms_max", "filter_frontend_compute_core_equivalent",
    "filter_input_points", "filter_kept_points", "filter_kept_pct", "filter_open_duty_pct",
    "guard_recoveries", "guard_recovery_active_duration_s", "guard_recovery_active_duration_mean_s",
    "guard_recovery_active_duration_max_s", "path_length_m", "max_odom_speed_3d_mps",
    "filter_trajectory_guard_full_refresh_ack_count",
    "filter_trajectory_guard_full_refresh_ack_latency_mean_s",
    "filter_trajectory_guard_full_refresh_ack_latency_max_s",
    "filter_slowdown_full_refresh_ack_count", "filter_slowdown_full_refresh_ack_latency_mean_s",
    "filter_slowdown_full_refresh_ack_latency_max_s",
    "filter_pre_stale_full_refresh_ack_count", "filter_pre_stale_full_refresh_ack_latency_mean_s",
    "filter_pre_stale_full_refresh_ack_latency_max_s",
)
REDUCTION_METRICS = ("cpu_cores", "cpu_core_s", "input_mib_s", "input_mib_run", "map_ms", "mapping_elapsed_s")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_sha(path, expected):
    actual = sha(path)
    if actual != expected:
        raise ValueError(f"Source hash mismatch: {path}")
    return actual


def number(value):
    if value is None or isinstance(value, bool) or str(value).strip().lower() in ("", "none", "nan", "null", "true", "false"):
        return None
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


def boolean(value):
    if value is True or str(value) == "True":
        return True
    if value is False or str(value) == "False":
        return False
    raise ValueError(f"Unexpected boolean {value!r}")


def same(left, right, label):
    if not math.isclose(float(left), float(right), rel_tol=1e-10, abs_tol=1e-8):
        raise ValueError(f"Metric mismatch {label}: {left} != {right}")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"Empty output table {path}")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def verify_inputs():
    freeze = read_json(FROZEN / "freeze_manifest.json")
    assert freeze["state"] == "FROZEN"
    for relative, expected in freeze["sha256"].items():
        check_sha(FROZEN / relative, expected)
    sources = read_json(FROZEN / "source_manifest.json")["sha256"]
    geometry = read_json(MAP_IMAGES / "map_sources.json")
    assert {m["map"] for m in geometry["maps"]} == set(MAP_INFO)
    for item in geometry["maps"]:
        for kind in ("geometry", "mission"):
            path = Path(item[kind + "_file"])
            check_sha(path, item[kind + "_sha256"])
            check_sha(path, sources[str(path)])
    for name, expected in geometry["outputs_sha256"].items():
        check_sha(MAP_IMAGES / name, expected)
    return freeze, sources, geometry


def perf_segment(path, raw):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    header = [field.strip() for field in rows[0]]
    valid = [row for row in rows[1:] if len(row) == len(header) and row[0].strip()]
    start, end = int(raw["perf_row_start"]), int(raw["perf_row_end"])
    assert boolean(raw["perf_window_valid"])
    assert 0 <= start < end <= len(valid)
    segment = [dict(zip(header, map(float, row))) for row in valid[start:end]]
    assert len(segment) == int(raw["map_perf_frames"])
    assert all(math.isfinite(value) for row in segment for value in row.values())
    assert all(row["Total"] >= 0 for row in segment)
    same(st.mean(row["Total"] for row in segment) * 1000, raw["total_ms_mean"], "Total mean")
    return segment, start, end


def load_flights(rows, out, sources, gate=False):
    extended, fullraw, evidence = [], [], []
    for original in rows:
        folder = Path(original["directory"])
        raw_file = folder / "raw.csv"
        check_sha(raw_file, original["raw_sha256"])
        check_sha(raw_file, sources[str(raw_file)])
        raw_rows = read_csv(raw_file)
        assert len(raw_rows) == 1
        raw = raw_rows[0]
        assert raw["map"] == original["map"] and raw["mode"] == original["mode"]
        assert int(raw["run"]) == int(original["run"])
        for frozen_key, raw_key in (("time_s", "mission_time_s"), ("cpu_cores", "end_to_end_cpu_cores_mean"),
                                    ("cpu_core_s", "end_to_end_cpu_core_s"), ("map_ms", "total_ms_mean")):
            same(original[frozen_key], raw[raw_key], frozen_key)
        label, env = MAP_INFO[original["map"]]
        perf = folder / "artifacts" / f"{original['map']}_run{original['run']}_{original['mode']}.attempt1.performance.csv"
        perf_sha = check_sha(perf, sources[str(perf)])
        segment, start, end = perf_segment(perf, raw)
        relative = Path("mapping_performance")
        if gate:
            relative /= "separate_gate"
        relative /= original["map"]
        relative /= f"r{int(original['repeat']):02d}"
        relative /= original["mode"] + ".csv"
        destination = out / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(perf, destination)
        completed = boolean(original["success"])
        contact = int(original["contacts"]) > 0
        safe = completed and not contact
        assert boolean(original["quality_valid"]) and boolean(original["solid_replay_valid"])
        result = dict(original)
        result.update(map_label=label, environment=env, mode_label=MODE_NAMES[original["mode"]],
                      goal_complete=completed, contact_run=contact, safe_complete=safe, mission_failure=not safe,
                      mapping_frames=len(segment), mapping_elapsed_s=math.fsum(row["Total"] for row in segment),
                      mapping_mean_ms_from_log=st.mean(row["Total"] for row in segment) * 1000,
                      mapping_raycast_elapsed_s=math.fsum(row["Raycast"] for row in segment),
                      mapping_cache_update_elapsed_s=math.fsum(row["Update_cache"] for row in segment),
                      mapping_inflation_elapsed_s=math.fsum(row["Inflation"] for row in segment),
                      mapping_max_ms=max(row["Total"] for row in segment) * 1000,
                      mapping_p95_ms=float(np.percentile([row["Total"] for row in segment], 95)) * 1000,
                      mapping_points_total=math.fsum(row["PointCloudNumber"] for row in segment),
                      mapping_points_mean=st.mean(row["PointCloudNumber"] for row in segment),
                      mapping_points_s=math.fsum(row["PointCloudNumber"] for row in segment) / float(original["time_s"]),
                      mapping_payload_bytes_total=math.fsum(row["PointCloudPayloadBytes"] for row in segment),
                      mapping_performance_file=relative.as_posix(), mapping_performance_sha256=perf_sha,
                      mapping_perf_row_start=start, mapping_perf_row_end=end, raw_file=str(raw_file))
        same(result["mapping_elapsed_s"], float(original["map_ms"]) * len(segment) / 1000, "cumulative Total")
        same(result["mapping_payload_bytes_total"] / 2**20, original["input_mib_run"], "input payload total")
        same(len(segment) / float(original["time_s"]), original["map_frames_s"], "mapping frame rate")
        for key in EXTRA_METRICS:
            value = number(raw.get(key))
            # Zero latency with zero ACKs means no event, not instant response.
            if "_ack_latency_" in key:
                count_key = key.split("_ack_latency_")[0] + "_ack_count"
                if (number(raw.get(count_key)) or 0) <= 0:
                    value = None
            result[key] = value
        result["algorithm_cpu_scope"] = raw.get("algorithm_cpu_scope", "")
        result["end_to_end_cpu_scope"] = raw.get("end_to_end_cpu_scope", "")
        extended.append(result)
        fullraw.append(dict(package_map_label=label, package_environment=env,
                            package_raw_file=str(raw_file), package_raw_sha256=original["raw_sha256"], **raw))
        evidence.append(dict(stage=original["stage"], map=original["map"], repeat=int(original["repeat"]),
                             mode=original["mode"], raw_file=str(raw_file), raw_sha256=original["raw_sha256"],
                             performance_original=str(perf), performance_file=relative.as_posix(),
                             performance_sha256=perf_sha, start=start, end=end, frame_count=len(segment),
                             mapping_elapsed_s=result["mapping_elapsed_s"]))
    return extended, fullraw, evidence


def stats(values):
    vals = [value for item in values if (value := number(item)) is not None]
    return dict(n=len(vals), mean=st.mean(vals) if vals else None,
                median=st.median(vals) if vals else None, sd=st.stdev(vals) if len(vals) > 1 else None,
                min=min(vals) if vals else None, max=max(vals) if vals else None)


def summary(rows, group):
    record = dict(group=group, mode=rows[0]["mode"], mode_label=MODE_NAMES[rows[0]["mode"]], n=len(rows))
    for field, output in (("goal_complete", "goal_complete"), ("contact_run", "contact_run"),
                          ("safe_complete", "safe_complete"), ("mission_failure", "mission_failure")):
        count = sum(row[field] for row in rows)
        record[output + "_count"] = count
        record[output + "_rate_pct"] = 100 * count / len(rows)
    record["contact_episode_count"] = sum(int(row["contacts"]) for row in rows)
    for prefix, subset in (("observed_time_s", rows),
                           ("goal_time_s", [row for row in rows if row["goal_complete"]]),
                           ("safe_time_s", [row for row in rows if row["safe_complete"]])):
        for name, value in stats([row["time_s"] for row in subset]).items():
            record[prefix + "_" + name] = value
    for metric in PRIMARY_METRICS + EXTRA_METRICS:
        result = stats([row.get(metric) for row in rows])
        record[metric + "_mean"] = result["mean"]
        record[metric + "_n_available"] = result["n"]
    transitions = [number(row["full_transitions"]) for row in rows]
    vals = [v for v in transitions if v is not None]
    record["adaptive_full_transitions_sum"] = int(sum(vals)) if vals else None
    record["adaptive_full_transitions_mean"] = st.mean(vals) if vals else None
    record["adaptive_full_transitions_median"] = st.median(vals) if vals else None
    return record


def group_tables(rows):
    map_rows = [summary([row for row in rows if row["map"] == map_id and row["mode"] == mode], label)
                for map_id, label, env in MAPS for mode in MODES]
    env_rows = [summary([row for row in rows if row["environment"] == env and row["mode"] == mode], env)
                for env in ENVIRONMENTS for mode in MODES]
    all_rows = [summary([row for row in rows if row["mode"] == mode], "All7") for mode in MODES]
    return map_rows, env_rows, all_rows


def verify_old_summaries(per_map, per_env):
    old_map = {(row["group"], row["mode"]): row for row in read_csv(FROZEN / "summary_by_map.csv")}
    old_env = {(row["group"], row["mode"]): row for row in read_csv(FROZEN / "summary_by_environment.csv")}
    mapping = {"n": "n", "goal_complete_count": "complete", "contact_run_count": "contact_runs",
               "safe_complete_count": "safe_complete", "observed_time_s_mean": "observed_time_s_mean",
               "goal_time_s_mean": "complete_time_s_mean", "goal_time_s_median": "complete_time_s_median"}
    mapping.update({key + "_mean": key for key in ("cpu_cores", "cpu_core_s", "input_mib_s", "input_mib_run", "map_ms")})
    for records, original in ((per_map, old_map), (per_env, old_env)):
        for row in records:
            old = original[("Map5" if row["group"] == "Map5-R2" else row["group"], row["mode"])]
            for new_key, old_key in mapping.items():
                same(row[new_key], old[old_key], row["group"] + "/" + new_key)


def availability(raw_rows):
    fields = list(dict.fromkeys(key for row in raw_rows for key in row if not key.startswith("package_")))
    results = []
    for field in fields:
        record = dict(field=field)
        all_values = [row.get(field, "") for row in raw_rows]
        present = [value for value in all_values if str(value).strip() not in ("", "None", "nan", "null")]
        record["recorded_n"] = len(present)
        record["missing_n"] = len(raw_rows) - len(present)
        if not present:
            kind = "unavailable"
        elif all(str(value) in ("True", "False") for value in present):
            kind = "boolean"
        elif all(number(value) is not None for value in present):
            kind = "numeric"
        else:
            kind = "text_or_mixed"
        record["type"] = kind
        record["numeric_n"] = sum(number(value) is not None for value in all_values)
        for mode in MODES:
            vals = [row.get(field, "") for row in raw_rows if row["mode"] == mode]
            record[mode + "_recorded_n"] = sum(str(value).strip() not in ("", "None", "nan", "null") for value in vals)
        results.append(record)
    return results


def supplemental(rows):
    results = []
    for level, groups in (("map", [label for _, label, _ in MAPS]), ("environment", ENVIRONMENTS)):
        for group in groups:
            for mode in MODES:
                selected = [row for row in rows if row["mode"] == mode and row["map_label" if level == "map" else "environment"] == group]
                for metric in PRIMARY_METRICS + EXTRA_METRICS:
                    values = stats([row.get(metric) for row in selected])
                    results.append(dict(level=level, group=group, mode=mode, metric=metric,
                                        n_runs=len(selected), n_available=values["n"],
                                        n_missing=len(selected) - values["n"],
                                        **{key: value for key, value in values.items() if key != "n"}))
    return results


def reductions(env_rows):
    lookup = {(row["group"], row["mode"]): row for row in env_rows}
    result = []
    for env in ENVIRONMENTS:
        baseline = lookup[(env, "full")]
        for mode in ("sector", "adaptive"):
            candidate = lookup[(env, mode)]
            row = dict(group=env, mode=mode, baseline="full", n_runs=candidate["n"])
            for metric in REDUCTION_METRICS:
                row[metric + "_reduction_pct"] = 100 * (1 - candidate[metric + "_mean"] / baseline[metric + "_mean"])
            result.append(row)
    return result


def fmt(value, precision=3):
    return "NA" if value is None else f"{float(value):.{precision}f}"


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"] +
                      ["| " + " | ".join(map(str, row)) + " |" for row in rows])


def render_report(out, per_map, per_env, overall, reduced):
    lines = ["# SUPER 맵별 모드별 최종 실험 결과", "",
             "2026년 10월 12일 정리 기준이다. 본실험은 V6의 7개 정적 맵에서 Full, Active-Yaw Sector, Adaptive를 맵·모드당 10회씩 실행한 210회다. 별도 숲 사전시험 30회와 이전 구현의 600회는 본실험 수치에 합산하지 않는다.", "",
             "Full과 Adaptive는 각각 70회 모두 무접촉 완주했다. Active-Yaw Sector는 목표 도달 68회, 접촉 주행 2회, 무접촉 완주 67회, 미션 실패 3회다. 접촉과 미완주가 중첩되는 주행은 실패에 한 번만 포함한다.", "",
             "## 모드별 전체 판정", "",
             table(["Mode", "N", "Goal complete", "Contact runs", "Contact-free complete", "Mission failure"],
                   [[r["mode_label"], r["n"], r["goal_complete_count"], r["contact_run_count"], r["safe_complete_count"], r["mission_failure_count"]] for r in overall]), "",
             "전체 판정 표는 주행 수 집계용이다. 주 처리 비용은 아래의 Normal1–5, Urban, Forest를 따로 비교한다.", "",
             "## 맵별 목표 도달 접촉 미션 성공", "",
             table(["Map", "Mode", "N", "Goal complete", "Contact runs", "Contact episodes", "Contact-free complete", "Mission failure", "Success (%)"],
                   [[r["group"], r["mode_label"], r["n"], r["goal_complete_count"], r["contact_run_count"], r["contact_episode_count"], r["safe_complete_count"], r["mission_failure_count"], fmt(r["safe_complete_rate_pct"], 1)] for r in per_map]), "",
             "미션 성공은 무접촉 완주다. 맵 1 Sector의 접촉 후 목표 도달은 목표 도달에는 포함되지만 미션 성공에는 제외된다. 숲 Sector의 무접촉 미완주 1회는 미션 실패지만 접촉 주행은 아니다. 이 분류는 원본 판정을 변경하지 않은 파생 지표다.", "",
             "## 맵별 주행시간", "",
             table(["Map", "Mode", "Observed mean (s)", "Goal-complete N", "Goal-complete mean (s)", "Median (s)", "SD (s)", "Contact-free N", "Contact-free mean (s)"],
                   [[r["group"], r["mode_label"], fmt(r["observed_time_s_mean"]), r["goal_time_s_n"], fmt(r["goal_time_s_mean"]), fmt(r["goal_time_s_median"]), fmt(r["goal_time_s_sd"]), r["safe_time_s_n"], fmt(r["safe_time_s_mean"])] for r in per_map]), "",
             "Observed mean은 미완주를 포함한 전체 관측시간이다. Goal-complete mean은 접촉 후 도달도 포함하며 숲 Sector의 분모는 8회다. Contact-free mean은 무접촉 완주만 포함하며 맵 1 Sector의 분모는 9회다. SD는 표본 표준편차다. 총 미션시간 상한은 없지만 동일 목표에서 기준 위치 반경 2 cm 안에 60초 정체하면 관측을 종료한 조건은 유지했다.", "",
             "## 맵별 처리 비용", "",
             table(["Map", "Mode", "CPU (cores)", "CPU time (core-s/run)", "Bandwidth (MiB/s)", "Payload (MiB/run)", "Mapping (ms/frame)", "Accumulated mapping (s/run)", "Map frames/run"],
                   [[r["group"], r["mode_label"], fmt(r["cpu_cores_mean"]), fmt(r["cpu_core_s_mean"]), fmt(r["input_mib_s_mean"]), fmt(r["input_mib_run_mean"]), fmt(r["map_ms_mean"]), fmt(r["mapping_elapsed_s_mean"]), fmt(r["mapping_frames_mean"], 1)] for r in per_map]), "",
             "비용 평균은 접촉·미완주를 포함한 각 맵·모드의 전체 10회다. Accumulated mapping은 각 주행의 유효 측정 구간에 기록된 ROG-Map Total 경과시간을 합산한 뒤 주행별 산술평균을 구한 값이다. CPU 시간 또는 전체 지도 서브시스템의 경과시간이 아니다. Raycast, Update_cache, Inflation은 중첩될 수 있으므로 서로 더해 Total을 대체하지 않는다.", "",
             "## 환경별 처리 비용", "",
             table(["Environment", "Mode", "N", "CPU (cores)", "CPU time (core-s/run)", "Bandwidth (MiB/s)", "Payload (MiB/run)", "Mapping (ms/frame)", "Accumulated mapping (s/run)"],
                   [[r["group"], r["mode_label"], r["n"], fmt(r["cpu_cores_mean"]), fmt(r["cpu_core_s_mean"]), fmt(r["input_mib_s_mean"]), fmt(r["input_mib_run_mean"]), fmt(r["map_ms_mean"]), fmt(r["mapping_elapsed_s_mean"])] for r in per_env]), "",
             "Normal1–5는 50회/모드의 평균이며 Urban과 Forest는 각각 10회/모드의 평균이다. 그룹 평균의 프레임당 시간과 평균 프레임 수를 곱한 값은 주행별 누적값의 평균과 같지 않을 수 있다.", "",
             "## Full 대비 처리 비용 감소율", "",
             table(["Environment", "Mode", "Mean CPU (%)", "CPU time (%)", "Bandwidth (%)", "Payload (%)", "Mapping/frame (%)", "Accumulated mapping (%)"],
                   [[r["group"], MODE_NAMES[r["mode"]]] + [fmt(r[m + "_reduction_pct"], 2) for m in REDUCTION_METRICS] for r in reduced]), "",
             "감소율은 100 × (1 − 해당 모드의 주행별 평균 / Full의 주행별 평균)이다. 양수는 감소, 음수는 증가다. 실패 비행도 비용 평균에 포함하므로 저비용 자체를 동일한 미션 수행 성능으로 해석하지 않는다.", "",
             "## CPU 메모리 처리 주파수", "",
             table(["Environment", "Mode", "Host CPU (%)", "Experiment capacity (%)", "Peak sampled RSS (MiB)", "Peak sampled PSS (MiB)", "Map frames/s", "Trajectory commits/s"],
                   [[r["group"], r["mode_label"], fmt(r["host_cpu_pct_mean_mean"]), fmt(r["experiment_host_capacity_pct_mean"]), fmt(r["end_to_end_peak_rss_mib_mean"]), fmt(r["end_to_end_peak_pss_mib_mean"]), fmt(r["map_frames_s_mean"]), fmt(r["trajectory_commit_hz_mean"])] for r in per_env]), "",
             "Host CPU는 배경 부하를 포함한다. Experiment capacity는 실험 cgroup의 CPU cores를 20개 논리 프로세서 용량으로 나눈 비율이며 배경을 차감한 호스트 CPU가 아니다. 메모리는 샘플링으로 얻은 프로세스 합계의 주행별 peak 평균이므로 실제 순간 최대값을 보장하지 않는다. Trajectory commits/s는 고유 커밋 세대의 첫 시각과 마지막 시각 사이에서 계산한 빈도이며 플래너 루프 주파수가 아니다.", "",
             "## Adaptive Full 전환", "",
             table(["Map", "Runs", "Full transitions", "Mean/run", "Median/run"],
                   [[r["group"], r["n"], r["adaptive_full_transitions_sum"], fmt(r["adaptive_full_transitions_mean"], 1), fmt(r["adaptive_full_transitions_median"], 1)] for r in per_map if r["mode"] == "adaptive"]), "",
             "본실험 전환 합계는 509회다. 별도 숲 사전시험의 109회는 합산하지 않는다. 전환 주기별 프레임·맵 ACK·경로 준비·Sector 복귀는 14_adaptive_cycles_509.csv와 원본 독립 감사에 기록돼 있다. 전환을 확인한 것은 위험 탐지율이나 미탐률을 측정한 것과 다르다.", "",
             "## 접촉과 미완주 사례", "",
             table(["Map", "Mode", "Repeat", "Goal complete", "Contact", "Observed time (s)", "Outcome"],
                   [["Map1", "Active-Yaw Sector", 6, "Yes", "Yes", "108.080", "Contact then goal completion"],
                    ["Forest", "Active-Yaw Sector", 4, "No", "Yes", "193.310", "Contact then 60 s stall"],
                    ["Forest", "Active-Yaw Sector", 5, "No", "No", "154.050", "Departure rejected then 60 s stall"]]), "",
             "숲 5회차는 새 맵에서의 출발 인증과 공통 복구 예산의 진행성 민감도가 함께 관여했다. 시야 제한만을 배타적인 원인으로 확정하지 않는다. 자세한 원본 분석과 사례 그림은 source_frozen/failure_analysis.md 및 source_frozen/case_*.png에 있다.", "",
             "## 환경 지도", "",
             "맵 1~5는 동일 조건의 비중첩 무작위 원기둥 배치이며 맵 5는 R2 수정본이다. 도심지는 4×4 건물 블록, 숲은 10개 군집의 270개 수목과 배경 140개 수목이다. 모든 맵은 64×64 m, 초기 위치와 목표 고도는 1.5 m다. 지도는 environment_maps/에 있으며 실제 정적 형상과 웨이포인트를 나타낸다. 점선은 목표 방문 순서이지 실제 비행 경로나 통과 가능성 증명이 아니다.", "",
             "## 해석 범위", "",
             "현재 PerfectDrone은 이상적 궤적 추종을 사용하며 충격·파손·추락 물리를 평가하지 않는다. 접촉 판정은 수신 위치 표본의 반경 0.2 m 구체와 정적 실체의 기하학적 교차다. 연속 swept-volume이나 실제 비행 안전 보장이 아니다. 반복 주행은 같은 환경에서의 반복이며 독립적인 새 환경 210개를 뜻하지 않는다. 현행 Urban·Forest는 통제된 blind-zone stress로 재분류하지 않는다. 현행 결과에 새로운 통계적 안전성 우위나 인과 검정을 추가하지 않았다.", ""]
    (out / "01_authoritative_result.md").write_text("\n".join(lines), encoding="utf-8")


def map_conditions(geometry):
    rows = []
    for item in geometry["maps"]:
        label, env = MAP_INFO[item["map"]]
        cylinders, boxes = item["cylinders"], item["boxes"]
        rows.append(dict(map=item["map"], map_label=label, environment=env,
                         field_width_m=64, field_height_m=64, flight_altitude_m=item["flight_altitude_m"],
                         cylinder_count=len(cylinders), box_count=len(boxes),
                         cylinder_diameter_m=2 * cylinders[0]["r"] if cylinders else None,
                         box_size_x_m=boxes[0]["size_x"] if boxes else None,
                         box_size_y_m=boxes[0]["size_y"] if boxes else None,
                         obstacle_height_m=item["statistics"]["height_m"],
                         min_surface_gap_m=item["statistics"]["min_surface_gap_m"],
                         nearest_surface_gap_mean_m=item["statistics"]["nearest_surface_gap_mean_m"],
                         initial_xyz=json.dumps(item["initial_position_xyz"]),
                         waypoints_xyz=json.dumps(item["waypoints_xyz"]),
                         geometry_sha256=item["geometry_sha256"], mission_sha256=item["mission_sha256"],
                         image_file="environment_maps/" + item["file_stem"] + ".png"))
    return rows


def plot_cumulative(out, per_map):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.fonttype": "none", "pdf.fonttype": 42})
    labels = [label for _, label, _ in MAPS]
    lookup = {(r["group"], r["mode"]): r for r in per_map}
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    colors = ["#546A7B", "#D78327", "#218C74"]
    for index, mode in enumerate(MODES):
        values = [lookup[(label, mode)]["mapping_elapsed_s_mean"] for label in labels]
        bars = ax.bar(x + (index - 1) * 0.24, values, width=0.23, color=colors[index], label=MODE_NAMES[mode])
        for bar, value in zip(bars, values):
            ax.annotate(f"{value:.2f}", (bar.get_x() + bar.get_width() / 2, value),
                        xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Accumulated logged mapping elapsed time (s/run)")
    ax.set_title("Accumulated mapping time by map and mode")
    ax.legend(frameon=False)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#DFE5EA", linewidth=0.6)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.13)
    fig.text(0.5, 0.025, "Mean of 10 runs per map/mode, including incomplete runs | Sum of ROG-Map Total timers, not CPU time", ha="center", fontsize=9)
    fig.subplots_adjust(left=0.09, right=0.985, top=0.9, bottom=0.13)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out / "figures" / ("cumulative_mapping_by_map." + ext), dpi=240)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    out = args.output.resolve()
    if (out / "04_run_level_210.csv").exists() or (out / "build_complete.json").exists():
        raise FileExistsError("Choose a fresh output directory; do not overwrite a generated package")
    if out == FROZEN or FROZEN in out.parents or out == MAP_IMAGES or MAP_IMAGES in out.parents:
        raise ValueError("Do not overwrite source directories")
    freeze, sources, geometry = verify_inputs()
    originals = read_csv(FROZEN / "main_210.csv")
    assert len(originals) == 210
    identities = {(row["stage"], row["map"], row["repeat"], row["mode"]) for row in originals}
    assert len(identities) == 210
    assert {row["map"] for row in originals} == set(MAP_INFO)
    for map_id in MAP_INFO:
        for mode in MODES:
            assert {int(r["repeat"]) for r in originals if r["map"] == map_id and r["mode"] == mode} == set(range(1, 11))
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FROZEN, out / "source_frozen")
    shutil.copytree(MAP_IMAGES, out / "environment_maps")
    (out / "figures").mkdir()
    (out / "separate_gate").mkdir()
    rows, fullraw, evidence = load_flights(originals, out, sources)
    per_map, per_env, overall = group_tables(rows)
    verify_old_summaries(per_map, per_env)
    reduced = reductions(per_env)
    write_csv(out / "02_summary_by_map.csv", per_map)
    write_csv(out / "03_summary_by_environment.csv", per_env)
    write_csv(out / "04_run_level_210.csv", rows)
    write_csv(out / "05_all_recorded_fields_210.csv", fullraw)
    write_csv(out / "06_metric_availability.csv", availability(fullraw))
    write_csv(out / "07_supplementary_numeric_summary.csv", supplemental(rows))
    write_csv(out / "11_map_conditions.csv", map_conditions(geometry))
    write_csv(out / "13_full_baseline_reductions.csv", reduced)
    write_csv(out / "15_overall_outcome_counts.csv", overall)
    failures = [r for r in rows if r["mission_failure"]]
    assert len(failures) == 3
    write_csv(out / "12_failure_runs.csv", failures)
    adaptive = read_json(FROZEN / "adaptive_contract_audit.json")
    cycles = []
    for flight in adaptive["flight_audits"]:
        if flight["stage"] != "seven_map_n10":
            continue
        assert flight["valid"]
        cycles.extend(dict(stage=flight["stage"], map=flight["map"], repeat=flight["repeat"],
                           run=flight["run"], mode=flight["mode"], **cycle) for cycle in flight["cycles"])
    assert len(cycles) == 509
    for row in rows:
        if row["mode"] == "adaptive":
            count = sum(c["map"] == row["map"] and int(c["repeat"]) == int(row["repeat"]) for c in cycles)
            transition_count = float(row["full_transitions"])
            assert transition_count.is_integer() and count == int(transition_count)
    write_csv(out / "14_adaptive_cycles_509.csv", cycles)
    gate, gate_raw, gate_evidence = load_flights(read_csv(FROZEN / "forest_gate_30.csv"), out, sources, gate=True)
    assert len(gate) == 30
    write_csv(out / "separate_gate/forest_gate_run_level_30.csv", gate)
    write_csv(out / "separate_gate/forest_gate_all_recorded_fields_30.csv", gate_raw)
    write_csv(out / "separate_gate/forest_gate_summary.csv", [summary([r for r in gate if r["mode"] == mode], "Forest gate only") for mode in MODES])
    render_report(out, per_map, per_env, overall, reduced)
    plot_cumulative(out, per_map)
    write_json(out / "16_result_bundle.json", dict(
        schema="super-v6-comprehensive-result-package-v1", date_kst="2026-10-12",
        basis="V6 frozen on 2026-10-08; reanalysis of preserved results, no new flight",
        main_runs=210, separate_gate_runs=30, modes=MODE_NAMES,
        outcome_definitions=dict(goal_complete="All goals reached, independent of contact",
                                 contact_run="At least one geometric solid contact episode",
                                 safe_complete="goal_complete AND NOT contact_run",
                                 mission_failure="contact_run OR NOT goal_complete"),
        main_overall=overall, main_by_map=per_map, main_by_environment=per_env,
        reductions_vs_full=reduced, map_conditions=map_conditions(geometry),
        adaptive_main_cycles=509, raw_recorded_fields=len([k for k in fullraw[0] if not k.startswith("package_")]),
        source_freeze_sha256=sha(FROZEN / "freeze_manifest.json")))
    write_json(out / "17_mapping_evidence.json", dict(
        metric="Accumulated logged ROG-Map Total elapsed seconds per run",
        equation="sum(Total[start:end]) == mean_Total_ms * counted_frames / 1000",
        scope="Elapsed time in updateProbMap; excludes later ESDF/initial clearing and outside transaction/snapshot work",
        stage_overlap="Inflation is nested. Do not sum Raycast + Update_cache + Inflation to replace Total.",
        main=evidence, separate_gate=gate_evidence,
        total_main_frames=sum(r["mapping_frames"] for r in rows)))
    # Preserve source provenance after copying; no frozen result has been resealed.
    for relative, expected in freeze["sha256"].items():
        check_sha(FROZEN / relative, expected)
        check_sha(out / "source_frozen" / relative, expected)
    for source in (FROZEN / "freeze_manifest.json", MAP_IMAGES / "map_sources.json"):
        assert source.exists()
    write_json(out / "build_complete.json", dict(
        state="BUILT_AWAITING_INDEPENDENT_VALIDATION", main_runs=210, separate_gate_runs=30,
        map_mode_groups=len(per_map), environment_mode_groups=len(per_env), main_failure_runs=3,
        mapping_frames_checked=sum(r["mapping_frames"] for r in rows), adaptive_cycles=509,
        raw_fields_per_run=len(fullraw[0]) - 4, simulation_launched=False, runtime_modified=False,
        frozen_outputs_modified=False, original_contact_labels_preserved=True))
    print(json.dumps({"output": str(out), "main_runs": len(rows), "gate_runs": len(gate),
                      "mapping_frames": sum(r["mapping_frames"] for r in rows),
                      "mapping_summary": [{"environment": r["group"], "mode": r["mode"],
                                           "mapping_elapsed_s_mean": r["mapping_elapsed_s_mean"]} for r in per_env]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
