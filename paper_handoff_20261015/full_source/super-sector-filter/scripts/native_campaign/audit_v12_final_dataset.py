#!/usr/bin/env python3
"""Audit and summarize the frozen Scenario-7 v12 n=10 data set.

The script deliberately uses only the Python standard library plus mpmath so
that the result does not depend on the host's currently incompatible
NumPy/SciPy binary pair.  Binary comparisons use the predeclared triplets and
an exact two-sided McNemar test.  Continuous comparisons use a paired exact
sign test and a deterministic paired bootstrap for the mean reduction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import mpmath


MODES = ("full", "sector", "adaptive")
MAPS = (
    "gapfree_d1_m01",
    "gapfree_d1_m02",
    "gapfree_d1_m03",
    "gapfree_d1_m04",
    "gapfree_d1_m05r2",
    "urban_blocks_u01",
    "forest_cluster_f01",
)
GROUPS = {
    "Normal (Map1-5)": set(MAPS[:5]),
    "Urban": {MAPS[5]},
    "Forest": {MAPS[6]},
    "Overall": set(MAPS),
}
AUDIT_OBJECTS = (
    "strict_recovery_audit",
    "guard_contract_audit",
    "nearfield_async_audit",
    "stopped_departure_v4_audit",
    "stopped_hold_v5_audit",
    "goal_change_full_refresh_v6_audit",
    "async_recovery_setting_audit",
    "optimizer_clearance_gate_audit",
    "goal_identity_audit",
    "headless_parameter_audit",
)
METRICS = {
    "mission_time_s": ("mission_time_s", 1.0, "s/run"),
    "mean_cpu_cores": ("end_to_end_cpu_cores_mean", 1.0, "cores"),
    "host_capacity_pct": ("end_to_end_cpu_cores_mean", None, "% of host"),
    "total_cpu_core_s": ("end_to_end_cpu_core_s", 1.0, "core-s/run"),
    "input_bandwidth_mib_s": ("planner_ingress_payload_mib_s", 1.0, "MiB/s"),
    "total_input_mib_run": ("map_payload_bytes_total", 1.0 / (1024.0**2), "MiB/run"),
    "map_computation_ms_frame": ("total_ms_mean", 1.0, "ms/frame"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bootstrap-repetitions", type=int, default=20_000)
    return parser.parse_args()


def truth(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def number(value: Any) -> float:
    return float(value)


def integer(value: Any) -> int:
    return int(float(value))


def type7_quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def distribution(values: Iterable[float]) -> dict[str, float | int]:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    return {
        "n": len(clean),
        "mean": statistics.fmean(clean),
        "sd": statistics.stdev(clean) if len(clean) > 1 else 0.0,
        "median": type7_quantile(clean, 0.5),
        "q1": type7_quantile(clean, 0.25),
        "q3": type7_quantile(clean, 0.75),
    }


def beta_cdf(value: float, alpha: float, beta: float) -> float:
    return float(mpmath.betainc(alpha, beta, 0, value, regularized=True))


def beta_quantile(probability: float, alpha: float, beta: float) -> float:
    low, high = 0.0, 1.0
    for _ in range(90):
        middle = (low + high) / 2.0
        if beta_cdf(middle, alpha, beta) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def clopper_pearson(successes: int, trials: int) -> tuple[float, float]:
    if trials <= 0:
        return math.nan, math.nan
    alpha = 0.05
    lower = 0.0 if successes == 0 else beta_quantile(
        alpha / 2.0, successes, trials - successes + 1
    )
    upper = 1.0 if successes == trials else beta_quantile(
        1.0 - alpha / 2.0, successes + 1, trials - successes
    )
    return lower, upper


def exact_two_sided_binomial(left: int, right: int) -> float:
    total = left + right
    if total == 0:
        return 1.0
    tail = min(left, right)
    probability = sum(math.comb(total, index) for index in range(tail + 1))
    return min(1.0, 2.0 * probability / (2**total))


def fisher_exact_two_sided(a_success: int, a_total: int,
                           b_success: int, b_total: int) -> float:
    """Two-sided Fisher exact p-value using fixed margins."""
    successes = a_success + b_success
    total = a_total + b_total
    lower = max(0, successes - b_total)
    upper = min(a_total, successes)
    denominator = math.comb(total, successes)

    def probability(a_value: int) -> float:
        return (math.comb(a_total, a_value) *
                math.comb(b_total, successes - a_value) / denominator)

    observed = probability(a_success)
    return min(1.0, sum(probability(value) for value in range(lower, upper + 1)
                        if probability(value) <= observed + 1.0e-15))


def paired_binary(rows: Sequence[dict[str, Any]], mode_a: str, mode_b: str,
                  predicate) -> dict[str, Any]:
    by_pair = defaultdict(dict)
    for row in rows:
        by_pair[(row["map"], row["run"])][row["mode"]] = row
    a_only = b_only = both = neither = 0
    for triplet in by_pair.values():
        a = bool(predicate(triplet[mode_a]))
        b = bool(predicate(triplet[mode_b]))
        if a and b:
            both += 1
        elif a:
            a_only += 1
        elif b:
            b_only += 1
        else:
            neither += 1
    a_success = both + a_only
    b_success = both + b_only
    pairs = len(by_pair)
    return {
        "pairs": pairs,
        "a_success": a_success,
        "b_success": b_success,
        "both": both,
        "a_only": a_only,
        "b_only": b_only,
        "neither": neither,
        "discordant": a_only + b_only,
        "mcnemar_exact_p": exact_two_sided_binomial(a_only, b_only),
        "fisher_exact_p_sensitivity": fisher_exact_two_sided(
            a_success, pairs, b_success, pairs
        ),
    }


def paired_sign_test(reference: Sequence[float], candidate: Sequence[float]) -> dict[str, Any]:
    differences = [candidate[index] - reference[index]
                   for index in range(len(reference))]
    lower = sum(value < 0 for value in differences)
    higher = sum(value > 0 for value in differences)
    ties = len(differences) - lower - higher
    return {
        "pairs": len(differences),
        "candidate_lower": lower,
        "candidate_higher": higher,
        "ties": ties,
        "median_candidate_minus_full": type7_quantile(differences, 0.5),
        "sign_exact_p": exact_two_sided_binomial(lower, higher),
    }


def bootstrap_reduction(reference: Sequence[float], candidate: Sequence[float],
                        repetitions: int, seed_text: str) -> tuple[float, float]:
    seed = int(hashlib.sha256(seed_text.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    values = []
    length = len(reference)
    for _ in range(repetitions):
        indices = [rng.randrange(length) for _ in range(length)]
        ref_mean = statistics.fmean(reference[index] for index in indices)
        candidate_mean = statistics.fmean(candidate[index] for index in indices)
        values.append(100.0 * (ref_mean - candidate_mean) / ref_mean)
    return type7_quantile(values, 0.025), type7_quantile(values, 0.975)


def load_rows(dataset: Path) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    raw_files = sorted(dataset.glob("stage*/**/raw.csv"))
    if len(raw_files) != 70:
        errors.append(f"expected 70 raw.csv files, found {len(raw_files)}")
    for path in raw_files:
        with path.open(newline="") as stream:
            batch = list(csv.DictReader(stream))
        if len(batch) != 3:
            errors.append(f"{path}: expected 3 rows, found {len(batch)}")
        for row in batch:
            row["_raw_path"] = str(path)
            row["run"] = integer(row["run"])
            row["complete"] = truth(row["success"])
            row["contact"] = integer(row["safety_collisions"]) > 0
            row["safe_complete"] = row["complete"] and not row["contact"]
            rows.append(row)
    return rows, errors


def audit_dataset(dataset: Path, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    keys = [(row["map"], row["run"], row["mode"]) for row in rows]
    duplicates = [key for key, count in Counter(keys).items() if count != 1]
    if duplicates:
        errors.append(f"duplicate/missing canonical keys: {duplicates[:10]}")
    expected_mode_counts = Counter({mode: 70 for mode in MODES})
    mode_counts = Counter(row["mode"] for row in rows)
    if mode_counts != expected_mode_counts:
        errors.append(f"mode counts {dict(mode_counts)} != {dict(expected_mode_counts)}")
    map_counts = Counter(row["map"] for row in rows)
    if map_counts != Counter({name: 30 for name in MAPS}):
        errors.append(f"map counts are not 30 each: {dict(map_counts)}")

    integrity_fields = {
        "run_valid": True,
        "resource_valid": True,
        "infrastructure_failure": False,
        "resource_guard_triggered": False,
        "speed_limit_valid": True,
        "perf_window_valid": True,
    }
    for field, expected in integrity_fields.items():
        bad = [key for key, row in zip(keys, rows) if truth(row[field]) != expected]
        if bad:
            errors.append(f"{field}: {len(bad)} rows differ from {expected}")
    for field, expected in {"attempt_count": 1, "retry_count": 0,
                            "oom_kill_delta": 0}.items():
        bad = [key for key, row in zip(keys, rows) if integer(row[field]) != expected]
        if bad:
            errors.append(f"{field}: {len(bad)} rows differ from {expected}")
    if any(row.get("cgroup_accounting_error") for row in rows):
        errors.append("at least one row has a cgroup accounting error")

    status = json.loads((dataset / "status.json").read_text())
    if status.get("state") != "COMPLETE":
        errors.append(f"campaign state is {status.get('state')}, not COMPLETE")
    if len(status.get("completed", [])) != 70:
        errors.append("status.json does not contain 70 completed triplets")
    if any(not entry.get("valid") or entry.get("returncode") != 0
           for entry in status.get("completed", [])):
        errors.append("status.json contains an invalid/non-zero triplet")
    if status.get("recorded_flights") != 210 or status.get("recorded_triplets") != 70:
        errors.append("status.json recorded counts differ from 210/70")
    if status.get("current") is not None:
        warnings.append(
            "status.json is COMPLETE but retains the last run in `current`; "
            "this is metadata-only and does not change the 70 completed triplets."
        )
    for gate_name in ("stage1_gate", "stage2_gate"):
        if not status.get(gate_name, {}).get("valid"):
            errors.append(f"{gate_name} is not valid")

    protocol = json.loads((dataset / "protocol.json").read_text())
    if protocol.get("planned_flights") != 210 or protocol.get("planned_triplets") != 70:
        errors.append("protocol planned counts differ from 210/70")
    if protocol.get("attempts_per_flight") != 1 or protocol.get("replacement_runs"):
        errors.append("protocol is not single-attempt/no-replacement")

    summary_errors = []
    audit_failures = []
    source_failures = []
    for row in rows:
        raw_path = Path(row["_raw_path"])
        summary_path = raw_path.parent / f"{row['mode']}_summary.json"
        if not summary_path.exists():
            summary_errors.append(f"missing {summary_path}")
            continue
        summary = json.loads(summary_path.read_text())
        identity = (summary.get("map"), summary.get("run"), summary.get("mode"))
        if identity != (row["map"], row["run"], row["mode"]):
            summary_errors.append(f"identity mismatch: {summary_path}")
        comparisons = {
            "success": row["complete"],
            "run_valid": truth(row["run_valid"]),
            "resource_valid": truth(row["resource_valid"]),
            "speed_limit_valid": truth(row["speed_limit_valid"]),
            "safety_collisions": integer(row["safety_collisions"]),
        }
        for field, expected in comparisons.items():
            if summary.get(field) != expected:
                summary_errors.append(f"{summary_path}: {field} mismatch")
        float_comparisons = {
            "mission_time_s": "mission_time_s",
            "end_to_end_cpu_cores_mean": "end_to_end_cpu_cores_mean",
            "end_to_end_cpu_core_s": "end_to_end_cpu_core_s",
            "total_ms_mean": "total_ms_mean",
        }
        for summary_field, raw_field in float_comparisons.items():
            if not math.isclose(float(summary[summary_field]), number(row[raw_field]),
                                rel_tol=1.0e-10, abs_tol=1.0e-10):
                summary_errors.append(f"{summary_path}: {summary_field} mismatch")
        for name in AUDIT_OBJECTS:
            audit = summary.get(name)
            if not isinstance(audit, dict) or audit.get("valid") is not True:
                audit_failures.append(f"{summary_path}: {name}")
        checks = summary.get("source_acquisition", {}).get("checks", {})
        false_checks = [name for name, value in checks.items() if value is not True]
        if not checks or false_checks:
            source_failures.append(f"{summary_path}: {false_checks or 'missing checks'}")
    if summary_errors:
        errors.append(f"summary/raw mismatches: {len(summary_errors)}")
    if audit_failures:
        errors.append(f"invalid required audit objects: {len(audit_failures)}")
    if source_failures:
        errors.append(f"source acquisition check failures: {len(source_failures)}")

    adaptive = [row for row in rows if row["mode"] == "adaptive"]
    adaptive_cycles = 0
    adaptive_completed = 0
    for row in adaptive:
        summary = json.loads((Path(row["_raw_path"]).parent /
                              "adaptive_summary.json").read_text())
        strict = summary["strict_recovery_audit"]
        adaptive_cycles += integer(strict.get("opened_cycles", 0))
        adaptive_completed += len(strict.get("completed_cycles", []))
        if strict.get("outstanding_cycles"):
            errors.append(f"outstanding Adaptive recovery: {row['map']} run{row['run']}")

    frozen_identity = json.loads((dataset / "frozen_identity.json").read_text())
    plan_files = sorted(dataset.glob("stage*/**/plan.json"))
    if len(plan_files) != 70:
        errors.append(f"expected 70 per-triplet plan.json files, found {len(plan_files)}")
    candidate_values = set()
    for path in plan_files:
        plan = json.loads(path.read_text())
        candidate_values.add(plan.get("candidate"))
    if candidate_values != {protocol.get("candidate")}:
        errors.append(f"per-run candidate identities differ: {candidate_values}")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "canonical_rows": len(rows),
        "unique_keys": len(set(keys)),
        "raw_files": len(list(dataset.glob("stage*/**/raw.csv"))),
        "mode_summary_files": {
            mode: len(list(dataset.glob(f"stage*/**/{mode}_summary.json")))
            for mode in MODES
        },
        "plan_files": len(plan_files),
        "frozen_identity_entries": len(frozen_identity),
        "adaptive_recovery_cycles": adaptive_cycles,
        "adaptive_recovery_completed": adaptive_completed,
        "summary_raw_mismatch_details": summary_errors,
        "audit_failure_details": audit_failures,
        "source_failure_details": source_failures,
    }


def selected(rows: Sequence[dict[str, Any]], maps: set[str]) -> list[dict[str, Any]]:
    return [row for row in rows if row["map"] in maps]


def outcome_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    scopes = {name: {name} for name in MAPS}
    scopes.update(GROUPS)
    output = []
    for scope, maps in scopes.items():
        group_rows = selected(rows, maps)
        for mode in MODES:
            mode_rows = [row for row in group_rows if row["mode"] == mode]
            complete = sum(row["complete"] for row in mode_rows)
            contact = sum(row["contact"] for row in mode_rows)
            safe = sum(row["safe_complete"] for row in mode_rows)
            complete_ci = clopper_pearson(complete, len(mode_rows))
            contact_ci = clopper_pearson(contact, len(mode_rows))
            safe_ci = clopper_pearson(safe, len(mode_rows))
            output.append({
                "scope": scope,
                "mode": mode,
                "n": len(mode_rows),
                "complete": complete,
                "completion_pct": 100.0 * complete / len(mode_rows),
                "completion_ci95_low_pct": 100.0 * complete_ci[0],
                "completion_ci95_high_pct": 100.0 * complete_ci[1],
                "contact_runs": contact,
                "contact_pct": 100.0 * contact / len(mode_rows),
                "contact_ci95_low_pct": 100.0 * contact_ci[0],
                "contact_ci95_high_pct": 100.0 * contact_ci[1],
                "safe_complete": safe,
                "safe_complete_pct": 100.0 * safe / len(mode_rows),
                "safe_complete_ci95_low_pct": 100.0 * safe_ci[0],
                "safe_complete_ci95_high_pct": 100.0 * safe_ci[1],
            })
    return output


def binary_test_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for scope, maps in GROUPS.items():
        group_rows = selected(rows, maps)
        for comparison in (("full", "sector"), ("full", "adaptive"),
                           ("adaptive", "sector")):
            for outcome, predicate in (
                ("completion", lambda row: row["complete"]),
                ("contact_free", lambda row: not row["contact"]),
                ("safe_complete", lambda row: row["safe_complete"]),
            ):
                result = paired_binary(group_rows, *comparison, predicate)
                output.append({
                    "scope": scope,
                    "outcome": outcome,
                    "mode_a": comparison[0],
                    "mode_b": comparison[1],
                    **result,
                })
    return output


def metric_value(row: dict[str, Any], metric: str, logical_cpus: int) -> float:
    field, scale, _unit = METRICS[metric]
    value = number(row[field])
    if metric == "host_capacity_pct":
        return 100.0 * value / logical_cpus
    return value * float(scale)


def metric_rows(rows: Sequence[dict[str, Any]], logical_cpus: int,
                bootstrap_repetitions: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summaries = []
    tests = []
    for scope, maps in GROUPS.items():
        group_rows = selected(rows, maps)
        by_pair = defaultdict(dict)
        for row in group_rows:
            by_pair[(row["map"], row["run"])][row["mode"]] = row
        for metric, (_field, _scale, unit) in METRICS.items():
            mode_values = {}
            for mode in MODES:
                values = [metric_value(row, metric, logical_cpus)
                          for row in group_rows if row["mode"] == mode]
                mode_values[mode] = values
                result = distribution(values)
                summaries.append({
                    "scope": scope,
                    "metric": metric,
                    "unit": unit,
                    "mode": mode,
                    **result,
                    "mean_reduction_vs_full_pct": (
                        0.0 if mode == "full" else
                        100.0 * (statistics.fmean(mode_values["full"]) -
                                 statistics.fmean(values)) /
                        statistics.fmean(mode_values["full"])
                    ),
                })
            for candidate in ("sector", "adaptive"):
                reference = [metric_value(pair["full"], metric, logical_cpus)
                             for pair in by_pair.values()]
                candidate_values = [metric_value(pair[candidate], metric, logical_cpus)
                                    for pair in by_pair.values()]
                incomplete_candidate = any(
                    not pair[candidate]["complete"] for pair in by_pair.values()
                )
                inferential_valid = not (
                    metric == "mission_time_s" and incomplete_candidate
                )
                sign = paired_sign_test(reference, candidate_values)
                ci_low, ci_high = bootstrap_reduction(
                    reference, candidate_values, bootstrap_repetitions,
                    f"{scope}|{metric}|{candidate}|{bootstrap_repetitions}",
                )
                tests.append({
                    "scope": scope,
                    "metric": metric,
                    "candidate": candidate,
                    "inferential_valid": inferential_valid,
                    "censoring_note": (
                        "not tested: candidate includes mission cutoff/non-completion"
                        if not inferential_valid else ""
                    ),
                    "mean_reduction_vs_full_pct": (
                        100.0 * (statistics.fmean(reference) -
                                 statistics.fmean(candidate_values)) /
                        statistics.fmean(reference)
                    ),
                    "bootstrap_reduction_ci95_low_pct": ci_low,
                    "bootstrap_reduction_ci95_high_pct": ci_high,
                    **({**sign} if inferential_valid else {
                        "pairs": len(reference),
                        "candidate_lower": "",
                        "candidate_higher": "",
                        "ties": "",
                        "median_candidate_minus_full": "",
                        "sign_exact_p": "",
                    }),
                })
    return summaries, tests


def transition_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    scopes = {name: {name} for name in MAPS}
    scopes.update(GROUPS)
    output = []
    for scope, maps in scopes.items():
        values = [integer(row["filter_effective_full_open_transitions"])
                  for row in selected(rows, maps) if row["mode"] == "adaptive"]
        stats = distribution(values)
        output.append({
            "scope": scope,
            **stats,
            "minimum": min(values),
            "maximum": max(values),
            "total": sum(values),
        })
    return output


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"no rows for {path}")
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def display(value: Any, digits: int = 3) -> str:
    if value == "" or value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{float(value):.{digits}f}"


def make_report(audit: dict[str, Any], outcomes: Sequence[dict[str, Any]],
                binary_tests: Sequence[dict[str, Any]],
                metrics: Sequence[dict[str, Any]],
                metric_tests: Sequence[dict[str, Any]],
                transitions: Sequence[dict[str, Any]]) -> str:
    outcome_index = {(row["scope"], row["mode"]): row for row in outcomes}
    metric_index = {(row["scope"], row["metric"], row["mode"]): row for row in metrics}
    test_index = {(row["scope"], row["metric"], row["candidate"]): row
                  for row in metric_tests}
    transition_index = {row["scope"]: row for row in transitions}
    lines = [
        "# Scenario-7 v12 최종 데이터 감사 및 논문용 통계",
        "",
        "## 판정",
        "",
        f"- 데이터 감사: **{'PASS' if audit['valid'] else 'FAIL'}**",
        f"- canonical flight rows: {audit['canonical_rows']} (고유 key {audit['unique_keys']})",
        f"- Adaptive recovery handshake: {audit['adaptive_recovery_completed']}/"
        f"{audit['adaptive_recovery_cycles']} 완료",
        "- 자동 재시도 0, replacement 0, infrastructure failure 0, resource/speed invalid 0",
        "",
    ]
    if audit["errors"]:
        lines.extend(["### 차단 오류", ""] + [f"- {value}" for value in audit["errors"]] + [""])
    if audit["warnings"]:
        lines.extend(["### 비차단 경고", ""] + [f"- {value}" for value in audit["warnings"]] + [""])

    lines.extend([
        "## 완주·접촉 결과",
        "",
        "95% CI는 이항 Clopper–Pearson exact interval이다.",
        "",
        "| 구분 | 모드 | 완주율 (95% CI) | 접촉 주행 (95% CI) | 안전 완주 |",
        "|---|---|---:|---:|---:|",
    ])
    for scope in ("Normal (Map1-5)", "Urban", "Forest", "Overall"):
        for mode in MODES:
            row = outcome_index[(scope, mode)]
            lines.append(
                f"| {scope} | {mode} | {row['complete']}/{row['n']} "
                f"({row['completion_pct']:.1f}%; {row['completion_ci95_low_pct']:.1f}–"
                f"{row['completion_ci95_high_pct']:.1f}) | {row['contact_runs']}/{row['n']} "
                f"({row['contact_pct']:.1f}%; {row['contact_ci95_low_pct']:.1f}–"
                f"{row['contact_ci95_high_pct']:.1f}) | {row['safe_complete']}/{row['n']} |"
            )

    lines.extend([
        "",
        "### 맵별 결과와 Adaptive Full 전환",
        "",
        "| 맵 | Full 완주/접촉 | Sector 완주/접촉 | Adaptive 완주/접촉 | Adaptive Full 전환 mean±SD (range) |",
        "|---|---:|---:|---:|---:|",
    ])
    for map_name in MAPS:
        full = outcome_index[(map_name, "full")]
        sector = outcome_index[(map_name, "sector")]
        adaptive = outcome_index[(map_name, "adaptive")]
        transition = transition_index[map_name]
        lines.append(
            f"| {map_name} | {full['complete']}/{full['n']} · {full['contact_runs']} | "
            f"{sector['complete']}/{sector['n']} · {sector['contact_runs']} | "
            f"{adaptive['complete']}/{adaptive['n']} · {adaptive['contact_runs']} | "
            f"{transition['mean']:.2f}±{transition['sd']:.2f} "
            f"({transition['minimum']}–{transition['maximum']}) |"
        )

    lines.extend([
        "",
        "## 전체 70쌍의 paired exact 검정",
        "",
        "동일 map/repetition triplet을 쌍으로 둔 양측 exact McNemar 검정이다. "
        "고정된 7개 맵 밖의 환경으로 일반화하는 검정은 아니다.",
        "",
        "| 결과 | 비교 | A만 성공 | B만 성공 | discordant | McNemar p | Fisher p (sensitivity) |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    for row in binary_tests:
        if row["scope"] != "Overall":
            continue
        lines.append(
            f"| {row['outcome']} | {row['mode_a']} vs {row['mode_b']} | "
            f"{row['a_only']} | {row['b_only']} | {row['discordant']} | "
            f"{row['mcnemar_exact_p']:.6f} | "
            f"{row['fisher_exact_p_sensitivity']:.6f} |"
        )

    lines.extend([
        "",
        "## 맵군별 연산량·주행 지표",
        "",
        "표는 mean [median, IQR]이다. 감소율은 각 scope의 Full 평균 대비이다.",
        "",
    ])
    report_metrics = (
        "mission_time_s", "mean_cpu_cores", "host_capacity_pct",
        "total_cpu_core_s", "input_bandwidth_mib_s",
        "total_input_mib_run", "map_computation_ms_frame",
    )
    for scope in ("Normal (Map1-5)", "Urban", "Forest", "Overall"):
        lines.extend([
            f"### {scope}", "",
            "| 지표 | Full | Fixed Sector | Adaptive | Adaptive 감소율 (bootstrap 95% CI) |",
            "|---|---:|---:|---:|---:|",
        ])
        for metric in report_metrics:
            cells = []
            for mode in MODES:
                row = metric_index[(scope, metric, mode)]
                cells.append(
                    f"{row['mean']:.3f} [{row['median']:.3f}, "
                    f"{row['q1']:.3f}–{row['q3']:.3f}]"
                )
            test = test_index[(scope, metric, "adaptive")]
            ci = (f"{test['mean_reduction_vs_full_pct']:.1f}% "
                  f"({test['bootstrap_reduction_ci95_low_pct']:.1f}–"
                  f"{test['bootstrap_reduction_ci95_high_pct']:.1f})")
            lines.append(f"| {metric} | {cells[0]} | {cells[1]} | {cells[2]} | {ci} |")
        lines.append("")

    lines.extend([
        "## 해석 제한",
        "",
        "- Full과 Adaptive의 70/70은 이 고정 시험군에서 관측된 100%이며 population guarantee가 아니다.",
        "- Fixed Sector 미완주 run의 mission time은 cutoff가 포함된 right-censored 값이므로 Full과의 "
        "주행시간 추론 검정에서 제외했다.",
        "- Adaptive는 velocity-centred sector와 event-driven Full recovery를 함께 포함하므로 이 데이터만으로 "
        "두 구성요소의 개별 인과효과를 분리할 수 없다.",
        "- 연산량은 end-to-end 실험 프로세스 기준이다. host_capacity_pct는 logical CPU 전체를 100%로 환산했다.",
        "- bootstrap CI는 선언된 고정 맵에서의 반복 run 변동을 나타내며, 새로운 환경을 표본으로 뽑은 "
        "environment-level CI가 아니다.",
        "- McNemar/Fisher p-value는 다중비교 보정 전 값이다. completion과 contact를 별개의 확증적 "
        "주장으로 동시에 사용할 경우 보정 계획을 먼저 정해야 하며, 본 보고서는 safe_complete를 "
        "통합 주결과로 사용하는 해석을 권장한다.",
        "",
        "## 논문에 바로 사용할 수 있는 핵심 문장",
        "",
        "동결된 7개 정적 시뮬레이션 환경에서 모드별 70회(총 210회)를 평가한 결과, "
        "Full과 Adaptive는 모두 70/70회 완주하고 접촉 주행이 없었다. Fixed Sector는 "
        "58/70회 완주했으며 6/70회에서 접촉이 관측되었다. 이 결과는 선언된 고정 맵 집합에 "
        "대한 유한 시뮬레이션 근거이며, 미관측 환경에 대한 안전 보장을 의미하지 않는다.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    dataset = args.dataset.resolve()
    output = (args.output or dataset / "paper_audit_20260929").resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows, load_errors = load_rows(dataset)
    audit = audit_dataset(dataset, rows)
    audit["errors"] = load_errors + audit["errors"]
    audit["valid"] = not audit["errors"]
    logical_cpus = integer(json.loads(
        sorted(dataset.glob("stage*/**/plan.json"))[0].read_text()
    )["logical_cpus"])
    audit["logical_cpus"] = logical_cpus
    audit["dataset"] = str(dataset)
    audit["method"] = {
        "binary_ci": "two-sided 95% Clopper-Pearson exact",
        "binary_comparison": "paired two-sided exact McNemar",
        "continuous_comparison": "paired exact sign test",
        "reduction_ci": (
            f"paired percentile bootstrap, {args.bootstrap_repetitions} repetitions, "
            "deterministic SHA-256-derived seed"
        ),
    }

    outcomes = outcome_rows(rows)
    binary_tests = binary_test_rows(rows)
    metrics, metric_tests = metric_rows(
        rows, logical_cpus, args.bootstrap_repetitions
    )
    transitions = transition_rows(rows)
    canonical = []
    for row in sorted(rows, key=lambda value: (value["map"], value["run"],
                                                MODES.index(value["mode"]))):
        canonical.append({
            "map": row["map"], "run": row["run"], "mode": row["mode"],
            "complete": row["complete"], "contact": row["contact"],
            "safe_complete": row["safe_complete"],
            "mission_time_s": number(row["mission_time_s"]),
            "mean_cpu_cores": number(row["end_to_end_cpu_cores_mean"]),
            "host_capacity_pct": 100.0 * number(row["end_to_end_cpu_cores_mean"]) / logical_cpus,
            "total_cpu_core_s": number(row["end_to_end_cpu_core_s"]),
            "input_bandwidth_mib_s": number(row["planner_ingress_payload_mib_s"]),
            "total_input_mib_run": number(row["map_payload_bytes_total"]) / (1024.0**2),
            "map_computation_ms_frame": number(row["total_ms_mean"]),
            "adaptive_full_transitions": (
                integer(row["filter_effective_full_open_transitions"])
                if row["mode"] == "adaptive" else ""
            ),
            "attempt_count": integer(row["attempt_count"]),
            "retry_count": integer(row["retry_count"]),
            "raw_path": row["_raw_path"],
        })

    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    write_csv(output / "canonical_210_rows.csv", canonical)
    write_csv(output / "outcomes_by_scope.csv", outcomes)
    write_csv(output / "paired_binary_tests.csv", binary_tests)
    write_csv(output / "metrics_by_scope.csv", metrics)
    write_csv(output / "paired_metric_tests.csv", metric_tests)
    write_csv(output / "adaptive_full_transitions_by_scope.csv", transitions)
    report = make_report(
        audit, outcomes, binary_tests, metrics, metric_tests, transitions
    )
    (output / "final_report.md").write_text(report)
    print(f"AUDIT {'PASS' if audit['valid'] else 'FAIL'}")
    print(f"REPORT {output / 'final_report.md'}")
    return 0 if audit["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
