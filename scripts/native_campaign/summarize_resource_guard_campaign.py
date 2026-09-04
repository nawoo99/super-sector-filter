#!/usr/bin/env python3
"""Validate and summarize a resource-gated three-mode native campaign.

The raw campaign CSV is the source of truth.  This tool rejects duplicate or
missing map/run/mode keys and records measurement-quality failures separately
from planner completion/collision outcomes.  It writes:

* ``<prefix>_validation.json``
* ``<prefix>_summary.csv``
* ``<prefix>_reductions.csv``

Reduction percentages use ``100 * (baseline - candidate) / baseline``.  Thus
positive values mean that the candidate used less of the reported metric.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


MODES = ("full", "sector", "adaptive")
TRUE_QUALITY_FIELDS = (
    "run_valid",
    "resource_guard_enabled",
    "resource_valid",
    "speed_limit_valid",
    "perf_window_valid",
    "cgroup_cpu_accounting",
    "static_pcd_enabled",
    "first_attempt_success",
)
FALSE_QUALITY_FIELDS = (
    "infrastructure_failure",
    "resource_guard_triggered",
)
ZERO_QUALITY_FIELDS = (
    "resource_guard_abort_count",
    "retry_count",
    "oom_kill_delta",
    "optimizer_phase_incomplete_events",
)

METRICS = (
    ("mission_time_s", "mission_time_s"),
    ("total_ms_mean", "map_compute_ms_per_frame"),
    ("algorithm_cpu_cores_mean", "algorithm_cores_mean"),
    ("algorithm_cpu_core_s", "algorithm_core_s"),
    ("algorithm_cpu_cores_p95_1s", "algorithm_cores_p95_1s"),
    ("algorithm_peak_pss_mib", "algorithm_peak_pss_mib"),
    ("end_to_end_cpu_cores_mean", "end_to_end_cores_mean"),
    ("end_to_end_cpu_core_s", "end_to_end_core_s"),
    ("end_to_end_cpu_cores_p95_1s", "end_to_end_cores_p95_1s"),
    ("end_to_end_peak_pss_mib", "end_to_end_peak_pss_mib"),
    ("planner_ingress_payload_mib_s", "planner_ingress_mib_s"),
    ("dds_total_algorithm_payload_mib_s", "dds_algorithm_mib_s"),
)

ALGORITHM_SCOPE_METRICS = {
    "algorithm_cores_mean",
    "algorithm_core_s",
    "algorithm_cores_p95_1s",
    "algorithm_peak_pss_mib",
}


class ValidationError(RuntimeError):
    pass


def parse_bool(value: object) -> Optional[bool]:
    text = str(value).strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    return None


def parse_float(value: object) -> Optional[float]:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def mean(values: Iterable[Optional[float]]) -> Optional[float]:
    usable = [value for value in values if value is not None]
    return statistics.mean(usable) if usable else None


def sample_sd(values: Iterable[Optional[float]]) -> Optional[float]:
    usable = [value for value in values if value is not None]
    if not usable:
        return None
    return statistics.stdev(usable) if len(usable) > 1 else 0.0


def minimum(values: Iterable[Optional[float]]) -> Optional[float]:
    usable = [value for value in values if value is not None]
    return min(usable) if usable else None


def maximum(values: Iterable[Optional[float]]) -> Optional[float]:
    usable = [value for value in values if value is not None]
    return max(usable) if usable else None


def sum_values(values: Iterable[Optional[float]]) -> float:
    return sum(value for value in values if value is not None)


def key(row: Mapping[str, str]) -> Tuple[str, int, str]:
    try:
        return row["map"], int(row["run"]), row["mode"]
    except (KeyError, ValueError) as exc:
        raise ValidationError(f"invalid campaign key: {row!r}") from exc


def quality_issues(row: Mapping[str, str]) -> List[str]:
    issues: List[str] = []
    for field in TRUE_QUALITY_FIELDS:
        if parse_bool(row.get(field)) is not True:
            issues.append(f"{field}!=true")
    for field in FALSE_QUALITY_FIELDS:
        if parse_bool(row.get(field)) is not False:
            issues.append(f"{field}!=false")
    for field in ZERO_QUALITY_FIELDS:
        if parse_float(row.get(field)) != 0.0:
            issues.append(f"{field}!=0")
    attempt = parse_float(row.get("attempt_count"))
    if attempt != 1.0:
        issues.append("attempt_count!=1")
    return issues


def collision_count(row: Mapping[str, str]) -> float:
    for field in ("safety_collisions", "static_pcd_collisions"):
        value = parse_float(row.get(field))
        if value is not None:
            return value
    return 0.0


def validate(
    rows: Sequence[Mapping[str, str]], maps: Sequence[str], runs: int
) -> Dict[str, object]:
    expected = {
        (map_name, run, mode)
        for map_name in maps
        for run in range(1, runs + 1)
        for mode in MODES
    }
    keys = [key(row) for row in rows]
    counts = Counter(keys)
    duplicate = sorted(item for item, count in counts.items() if count > 1)
    observed = set(keys)
    quality = []
    for row in rows:
        issues = quality_issues(row)
        if issues:
            quality.append({"key": list(key(row)), "issues": issues})

    missing = sorted(expected - observed)
    unexpected = sorted(observed - expected)
    scope_failures = []
    for mode in MODES:
        mode_rows = [row for row in rows if row.get("mode") == mode]
        algorithm_scopes = sorted(
            {row.get("algorithm_cpu_scope", "") for row in mode_rows}
        )
        end_to_end_scopes = sorted(
            {row.get("end_to_end_cpu_scope", "") for row in mode_rows}
        )
        if len(algorithm_scopes) != 1 or not algorithm_scopes[0]:
            scope_failures.append(
                {"mode": mode, "field": "algorithm_cpu_scope", "values": algorithm_scopes}
            )
        if len(end_to_end_scopes) != 1 or not end_to_end_scopes[0]:
            scope_failures.append(
                {"mode": mode, "field": "end_to_end_cpu_scope", "values": end_to_end_scopes}
            )
    all_e2e_scopes = sorted({row.get("end_to_end_cpu_scope", "") for row in rows})
    if len(all_e2e_scopes) != 1 or not all_e2e_scopes[0]:
        scope_failures.append(
            {
                "mode": "cross_mode",
                "field": "end_to_end_cpu_scope",
                "values": all_e2e_scopes,
            }
        )

    passed = (
        not duplicate
        and not missing
        and not unexpected
        and not quality
        and not scope_failures
    )
    return {
        "passed": passed,
        "expected_rows": len(expected),
        "observed_rows": len(rows),
        "unique_rows": len(observed),
        "missing_keys": [list(item) for item in missing],
        "duplicate_keys": [list(item) for item in duplicate],
        "unexpected_keys": [list(item) for item in unexpected],
        "quality_failure_count": len(quality),
        "quality_failures": quality,
        "scope_failure_count": len(scope_failures),
        "scope_failures": scope_failures,
    }


def summarize_group(
    map_name: str, mode: str, rows: Sequence[Mapping[str, str]]
) -> Dict[str, object]:
    successes = [row for row in rows if parse_bool(row.get("success")) is True]
    collisions = [row for row in rows if collision_count(row) > 0]
    result: Dict[str, object] = {
        "map": map_name,
        "mode": mode,
        "n": len(rows),
        "complete": len(successes),
        "completion_pct": 100.0 * len(successes) / len(rows) if rows else None,
        "collision_runs": len(collisions),
        "collision_events": sum(collision_count(row) for row in rows),
        "run_valid_count": sum(parse_bool(row.get("run_valid")) is True for row in rows),
        "speed_limit_valid_count": sum(
            parse_bool(row.get("speed_limit_valid")) is True for row in rows
        ),
        "resource_valid_count": sum(
            parse_bool(row.get("resource_valid")) is True for row in rows
        ),
        "first_attempt_count": sum(
            parse_bool(row.get("first_attempt_success")) is True for row in rows
        ),
        "retry_total": int(sum_values(parse_float(row.get("retry_count")) for row in rows)),
        "resource_abort_total": int(
            sum_values(parse_float(row.get("resource_guard_abort_count")) for row in rows)
        ),
        "algorithm_cpu_scope": ";".join(
            sorted({row.get("algorithm_cpu_scope", "") for row in rows})
        ),
        "end_to_end_cpu_scope": ";".join(
            sorted({row.get("end_to_end_cpu_scope", "") for row in rows})
        ),
        "mission_time_mean_all_s": mean(
            parse_float(row.get("mission_time_s")) for row in rows
        ),
        "mission_time_sd_all_s": sample_sd(
            parse_float(row.get("mission_time_s")) for row in rows
        ),
        "mission_time_mean_success_s": mean(
            parse_float(row.get("mission_time_s")) for row in successes
        ),
        "mission_time_min_s": minimum(
            parse_float(row.get("mission_time_s")) for row in rows
        ),
        "mission_time_max_s": maximum(
            parse_float(row.get("mission_time_s")) for row in rows
        ),
        "clearance_mean_m": mean(
            parse_float(row.get("static_pcd_clearance_m")) for row in rows
        ),
        "clearance_min_m": minimum(
            parse_float(row.get("static_pcd_clearance_m")) for row in rows
        ),
        "clearance_below_0p20_count": sum(
            (
                (clearance := parse_float(row.get("static_pcd_clearance_m")))
                is not None
                and clearance < 0.20
            )
            for row in rows
        ),
        "effective_full_open_total": int(
            sum_values(
                parse_float(row.get("filter_effective_full_open_transitions"))
                for row in rows
            )
        ),
        "effective_full_open_mean": mean(
            parse_float(row.get("filter_effective_full_open_transitions"))
            for row in rows
        ),
        "system_available_min_mib": minimum(
            parse_float(row.get("system_min_available_mib")) for row in rows
        ),
        "system_peak_swap_max_mib": maximum(
            parse_float(row.get("system_peak_swap_used_mib")) for row in rows
        ),
        "psi_some_avg10_max": maximum(
            parse_float(row.get("memory_psi_some_avg10_max")) for row in rows
        ),
        "psi_full_avg10_max": maximum(
            parse_float(row.get("memory_psi_full_avg10_max")) for row in rows
        ),
        "preflight_wait_mean_s": mean(
            parse_float(row.get("resource_guard_preflight_wait_s")) for row in rows
        ),
    }
    for field, label in METRICS:
        result[label] = mean(parse_float(row.get(field)) for row in rows)
    return result


def build_summary(
    rows: Sequence[Mapping[str, str]], maps: Sequence[str]
) -> List[Dict[str, object]]:
    grouped: Dict[Tuple[str, str], List[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["map"], row["mode"])].append(row)
    output = []
    for map_name in maps:
        for mode in MODES:
            output.append(summarize_group(map_name, mode, grouped[(map_name, mode)]))
    for mode in MODES:
        pooled = [row for row in rows if row["mode"] == mode]
        output.append(summarize_group("all", mode, pooled))
    return output


def reduction(candidate: Optional[float], baseline: Optional[float]) -> Optional[float]:
    if candidate is None or baseline is None or baseline == 0:
        return None
    return 100.0 * (baseline - candidate) / baseline


def comparison_valid(
    label: str,
    candidate: Mapping[str, object],
    baseline: Mapping[str, object],
) -> bool:
    if candidate.get(label) is None or baseline.get(label) is None:
        return False
    # A reduction is a like-for-like protocol comparison only when every run in
    # both groups passed the campaign contract (including the v7 speed cap).
    # Planner outcomes remain summarized separately, but an invalid run must not
    # silently enter a compute/bandwidth reduction claim.
    if (
        candidate.get("run_valid_count") != candidate.get("n")
        or baseline.get("run_valid_count") != baseline.get("n")
    ):
        return False
    if label in ALGORITHM_SCOPE_METRICS:
        return (
            bool(candidate.get("algorithm_cpu_scope"))
            and candidate.get("algorithm_cpu_scope")
            == baseline.get("algorithm_cpu_scope")
        )
    if label.startswith("end_to_end_"):
        return (
            bool(candidate.get("end_to_end_cpu_scope"))
            and candidate.get("end_to_end_cpu_scope")
            == baseline.get("end_to_end_cpu_scope")
        )
    return True


def build_reductions(summary: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    lookup = {(row["map"], row["mode"]): row for row in summary}
    maps = list(dict.fromkeys(row["map"] for row in summary))
    output: List[Dict[str, object]] = []
    labels = [label for _field, label in METRICS]
    for map_name in maps:
        full = lookup[(map_name, "full")]
        sector = lookup[(map_name, "sector")]
        adaptive = lookup[(map_name, "adaptive")]
        for label in labels:
            f = full[label]
            s = sector[label]
            a = adaptive[label]
            sf_valid = comparison_valid(label, sector, full)
            af_valid = comparison_valid(label, adaptive, full)
            as_valid = comparison_valid(label, adaptive, sector)
            output.append(
                {
                    "map": map_name,
                    "metric": label,
                    "full": f,
                    "sector": s,
                    "adaptive": a,
                    "sector_vs_full_comparison_valid": sf_valid,
                    "sector_vs_full_reduction_pct": reduction(s, f) if sf_valid else None,
                    "adaptive_vs_full_comparison_valid": af_valid,
                    "adaptive_vs_full_reduction_pct": reduction(a, f) if af_valid else None,
                    "adaptive_vs_sector_comparison_valid": as_valid,
                    "adaptive_vs_sector_reduction_pct": reduction(a, s) if as_valid else None,
                }
            )
    return output


def write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise ValidationError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: "" if value is None else value
                    for field, value in row.items()
                }
            )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--prefix", required=True, type=Path)
    parser.add_argument("--maps", nargs="+", default=[f"seed{i}" for i in range(1, 11)])
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="write partial summaries and return success even when validation fails",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    with args.campaign.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValidationError("campaign CSV has no header")
        required = {
            "map", "run", "mode", "success", "attempt_count",
            "algorithm_cpu_scope", "algorithm_cpu_excludes_simulator",
            "end_to_end_cpu_scope",
            *TRUE_QUALITY_FIELDS, *FALSE_QUALITY_FIELDS, *ZERO_QUALITY_FIELDS,
            *(field for field, _label in METRICS),
        }
        missing_columns = sorted(required - set(reader.fieldnames))
        if missing_columns:
            raise ValidationError(f"missing required columns: {missing_columns}")
        rows = list(reader)

    validation = validate(rows, args.maps, args.runs)
    validation.update(
        {
            "campaign": str(args.campaign),
            "maps": args.maps,
            "runs_per_mode": args.runs,
            "modes": list(MODES),
        }
    )
    validation_path = Path(f"{args.prefix}_validation.json")
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    validation_path.write_text(
        json.dumps(validation, indent=2, ensure_ascii=False) + "\n"
    )

    summary = build_summary(rows, args.maps)
    reductions = build_reductions(summary)
    write_csv(Path(f"{args.prefix}_summary.csv"), summary)
    write_csv(Path(f"{args.prefix}_reductions.csv"), reductions)
    print(json.dumps(validation, indent=2, ensure_ascii=False))
    return 0 if validation["passed"] or args.allow_incomplete else 2


if __name__ == "__main__":
    raise SystemExit(main())
