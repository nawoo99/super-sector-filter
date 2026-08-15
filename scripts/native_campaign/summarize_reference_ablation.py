#!/usr/bin/env python3
"""Summarize the seed11 raw-direct reference ablation campaigns.

The script keeps campaign files as separate blocking strata, summarizes only
explicitly valid runs, and computes paired candidate-minus-control effects from
rows that share (campaign, map, run).  CSV row order is retained to distinguish
AB from BA execution order.

Example:

    python3 summarize_reference_ablation.py \
      --campaign goal_ab=results/seed11_goal_ab.csv \
      --campaign quiet_ab=results/seed11_quiet_ab.csv \
      --out-prefix results/seed11_reference_ablation
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


TARGET_MODES = (
    "raw_oneway_repeat",
    "raw_oneway_once",
    "raw_oneway_once_quiet",
    "raw_oneway_ready",
    "raw_oneway_guarded",
    "raw_oneway_guarded_slow",
    "raw_oneway_guarded_scheduled",
    "raw_oneway_guarded_margin",
)
MODE_RANK = {mode: index for index, mode in enumerate(TARGET_MODES)}
CONTRASTS = (
    ("raw_oneway_repeat", "raw_oneway_once", "once_minus_repeat"),
    ("raw_oneway_once", "raw_oneway_once_quiet", "quiet_minus_once"),
    ("raw_oneway_once_quiet", "raw_oneway_ready", "ready_minus_quiet"),
    ("raw_oneway_ready", "raw_oneway_guarded", "guarded_minus_ready"),
    ("raw_oneway_guarded", "raw_oneway_guarded_slow", "slow_minus_guarded"),
    ("raw_oneway_guarded_slow", "raw_oneway_guarded_scheduled", "scheduled_minus_slow"),
    ("raw_oneway_guarded_slow", "raw_oneway_guarded_margin", "margin_minus_slow"),
)

CONTACT_COLUMNS = (
    ("contact_r015", "static_pcd_contact_r015"),
    ("contact_r020", "static_pcd_contact_r020"),
    ("contact_r025", "static_pcd_contact_r025"),
)

# Safety, goal, and command-observability metrics are defined for valid flights.
# Mission/performance metrics are compared only when both arms completed.
PAIRED_CONTINUOUS_METRICS = (
    ("clearance_m", "static_pcd_clearance_m", "valid"),
    ("center_distance_m", "static_pcd_min_distance_m", "valid"),
    ("goal_messages", "goal_messages", "valid"),
    ("position_command_messages", "position_command_messages", "valid"),
    ("trajectory_flag2_messages", "trajectory_flag2_messages", "valid"),
    ("first_trajectory_flag2_s", "first_trajectory_flag2_s", "valid"),
    ("trajectory_flag3_messages", "trajectory_flag3_messages", "valid"),
    ("first_trajectory_flag3_s", "first_trajectory_flag3_s", "valid"),
    ("max_position_command_gap_s", "max_position_command_gap_s", "valid"),
    ("mission_time_s", "mission_time_s", "complete"),
    ("path_length_m", "path_length_m", "complete"),
    ("fsm_cpu_pct", "fsm_cpu_pct", "complete"),
    ("monitor_flight_cpu_pct", "monitor_flight_cpu_pct", "complete"),
    ("perf_frames", "perf_frames", "complete"),
    ("pts_mean", "pts_mean", "complete"),
    ("total_ms_mean", "total_ms_mean", "complete"),
    ("raycast_ms_mean", "raycast_ms_mean", "complete"),
    ("update_ms_mean", "update_ms_mean", "complete"),
    ("inflation_ms_mean", "inflation_ms_mean", "complete"),
)

MODE_STAT_METRICS = (
    ("clearance_m", "static_pcd_clearance_m", "valid"),
    ("center_distance_m", "static_pcd_min_distance_m", "valid"),
    ("goal_messages", "goal_messages", "valid"),
    ("position_command_messages", "position_command_messages", "valid"),
    ("trajectory_flag2_messages", "trajectory_flag2_messages", "valid"),
    ("first_trajectory_flag2_s", "first_trajectory_flag2_s", "valid"),
    ("trajectory_flag3_messages", "trajectory_flag3_messages", "valid"),
    ("first_trajectory_flag3_s", "first_trajectory_flag3_s", "valid"),
    ("max_position_command_gap_s", "max_position_command_gap_s", "valid"),
    ("mission_time_s", "mission_time_s", "complete"),
    ("path_length_m", "path_length_m", "complete"),
    ("fsm_cpu_pct", "fsm_cpu_pct", "complete"),
    ("monitor_flight_cpu_pct", "monitor_flight_cpu_pct", "complete"),
    ("perf_frames", "perf_frames", "complete"),
    ("pts_mean", "pts_mean", "complete"),
    ("total_ms_mean", "total_ms_mean", "complete"),
    ("raycast_ms_mean", "raycast_ms_mean", "complete"),
    ("update_ms_mean", "update_ms_mean", "complete"),
    ("inflation_ms_mean", "inflation_ms_mean", "complete"),
)

REQUIRED_COLUMNS = {
    "map",
    "run",
    "mode",
    "experiment_profile",
    "success",
    "run_valid",
    "monitor_type",
    "live_cloud_enabled",
    "goal_messages",
    "n_waypoints",
    "static_pcd_contact_r015",
    "static_pcd_contact_r020",
    "static_pcd_contact_r025",
    "static_pcd_min_distance_m",
    "static_pcd_clearance_m",
    "mission_time_s",
    "path_length_m",
    "fsm_cpu_pct",
    "monitor_flight_cpu_pct",
    "pts_mean",
    "total_ms_mean",
    "raycast_ms_mean",
    "update_ms_mean",
    "inflation_ms_mean",
    "perf_row_start",
    "perf_row_end",
}

OPTIONAL_BOOL_COLUMNS = {
    "live_cloud_enabled",
    "static_pcd_contact_r015",
    "static_pcd_contact_r020",
    "static_pcd_contact_r025",
}

OPTIONAL_FLOAT_COLUMNS = {
    "static_pcd_min_distance_m",
    "static_pcd_clearance_m",
    "mission_time_s",
    "path_length_m",
    "fsm_cpu_pct",
    "monitor_flight_cpu_pct",
    "pts_mean",
    "total_ms_mean",
    "raycast_ms_mean",
    "update_ms_mean",
    "inflation_ms_mean",
}

OPTIONAL_INT_COLUMNS = {
    "goal_messages",
    "n_waypoints",
    "perf_row_start",
    "perf_row_end",
}

# These columns were added after the first three reference ablations.  Accept
# historical campaign files without them while exposing the measurements in
# all newly generated mode and paired summaries.
COMPATIBLE_OPTIONAL_FLOAT_COLUMNS = {
    "first_trajectory_flag2_s",
    "first_trajectory_flag3_s",
    "max_position_command_gap_s",
}

COMPATIBLE_OPTIONAL_INT_COLUMNS = {
    "position_command_messages",
    "trajectory_flag2_messages",
    "trajectory_flag3_messages",
}


class ValidationError(ValueError):
    """Raised when an input cannot support a trustworthy comparison."""


@dataclass(frozen=True)
class CampaignSpec:
    name: str
    path: Path


@dataclass(frozen=True)
class Pair:
    a: Mapping[str, object]
    b: Mapping[str, object]
    order: str


def parse_required_bool(value: str, field: str, context: str) -> bool:
    parsed = parse_optional_bool(value, field, context)
    if parsed is None:
        raise ValidationError(f"{context}: {field} is blank")
    return parsed


def parse_optional_bool(value: str, field: str, context: str) -> Optional[bool]:
    text = (value or "").strip()
    if not text:
        return None
    if text == "True":
        return True
    if text == "False":
        return False
    raise ValidationError(
        f"{context}: {field} must be exactly True, False, or blank; got {text!r}"
    )


def parse_optional_float(value: str, field: str, context: str) -> Optional[float]:
    text = (value or "").strip()
    if not text:
        return None
    try:
        result = float(text)
    except ValueError as exc:
        raise ValidationError(f"{context}: {field} is not numeric: {text!r}") from exc
    if not math.isfinite(result):
        raise ValidationError(f"{context}: {field} is not finite: {text!r}")
    return result


def parse_optional_int(value: str, field: str, context: str) -> Optional[int]:
    number = parse_optional_float(value, field, context)
    if number is None:
        return None
    if not number.is_integer():
        raise ValidationError(f"{context}: {field} is not an integer: {number}")
    return int(number)


def type7_quantile(values: Sequence[float], probability: float) -> Optional[float]:
    """Return the R/NumPy default (type 7) sample quantile."""
    if not values:
        return None
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between zero and one")
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def distribution(values: Iterable[Optional[float]]) -> Dict[str, Optional[float]]:
    clean = [float(value) for value in values if value is not None]
    return {
        "n": len(clean),
        "median": type7_quantile(clean, 0.50),
        "q1": type7_quantile(clean, 0.25),
        "q3": type7_quantile(clean, 0.75),
    }


def add_distribution(
    output: Dict[str, object], prefix: str, values: Iterable[Optional[float]]
) -> None:
    stats = distribution(values)
    for suffix, value in stats.items():
        output[f"{prefix}_{suffix}"] = value


def percent(numerator: int, denominator: int) -> Optional[float]:
    return 100.0 * numerator / denominator if denominator else None


def mcnemar_exact(a_only: int, b_only: int) -> Optional[float]:
    """Two-sided exact McNemar/binomial p-value for discordant pairs."""
    discordant = a_only + b_only
    if discordant == 0:
        return 1.0
    tail_limit = min(a_only, b_only)
    tail = sum(math.comb(discordant, index) for index in range(tail_limit + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


def parse_campaign_spec(value: str) -> CampaignSpec:
    if "=" not in value:
        raise argparse.ArgumentTypeError("campaign must be NAME=CSV_PATH")
    name, path_text = value.split("=", 1)
    name = name.strip()
    path_text = path_text.strip()
    if not name or not path_text:
        raise argparse.ArgumentTypeError("campaign must have a non-empty name and path")
    return CampaignSpec(name=name, path=Path(path_text))


def load_campaign(spec: CampaignSpec) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    try:
        stream = spec.path.open(newline="")
    except OSError as exc:
        raise ValidationError(f"cannot open {spec.path}: {exc}") from exc
    with stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValidationError(f"{spec.path}: missing CSV header")
        duplicate_headers = sorted(
            {name for name in reader.fieldnames if reader.fieldnames.count(name) > 1}
        )
        if duplicate_headers:
            raise ValidationError(
                f"{spec.path}: duplicate columns: {', '.join(duplicate_headers)}"
            )
        missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames))
        if missing:
            raise ValidationError(
                f"{spec.path}: missing required columns: {', '.join(missing)}"
            )

        ordinal = 0
        for line_number, raw in enumerate(reader, start=2):
            if None in raw:
                raise ValidationError(
                    f"{spec.path}:{line_number}: row has more values than the header"
                )
            if not any((value or "").strip() for value in raw.values() if value is not None):
                continue
            ordinal += 1
            context = f"{spec.path}:{line_number}"
            mode = (raw["mode"] or "").strip()
            profile = (raw["experiment_profile"] or "").strip()
            map_name = (raw["map"] or "").strip()
            if mode not in TARGET_MODES:
                raise ValidationError(f"{context}: unsupported ablation mode {mode!r}")
            if profile != mode:
                raise ValidationError(
                    f"{context}: experiment_profile {profile!r} does not equal mode {mode!r}"
                )
            run = parse_optional_int(raw["run"], "run", context)
            if run is None or run < 1:
                raise ValidationError(f"{context}: run must be a positive integer")

            row: Dict[str, object] = {
                "campaign": spec.name,
                "source_path": str(spec.path),
                "row_index": ordinal,
                "line_number": line_number,
                "map": map_name,
                "run": run,
                "mode": mode,
                "experiment_profile": profile,
                "monitor_type": (raw["monitor_type"] or "").strip(),
                "success": parse_required_bool(raw["success"], "success", context),
                "run_valid": parse_required_bool(raw["run_valid"], "run_valid", context),
            }
            for field in OPTIONAL_BOOL_COLUMNS:
                row[field] = parse_optional_bool(raw[field], field, context)
            for field in OPTIONAL_FLOAT_COLUMNS:
                row[field] = parse_optional_float(raw[field], field, context)
            for field in OPTIONAL_INT_COLUMNS:
                row[field] = parse_optional_int(raw[field], field, context)
            for field in COMPATIBLE_OPTIONAL_FLOAT_COLUMNS:
                row[field] = parse_optional_float(raw.get(field, ""), field, context)
            for field in COMPATIBLE_OPTIONAL_INT_COLUMNS:
                row[field] = parse_optional_int(raw.get(field, ""), field, context)

            start = row["perf_row_start"]
            end = row["perf_row_end"]
            if start is not None and end is not None:
                if int(end) < int(start):
                    raise ValidationError(
                        f"{context}: perf_row_end precedes perf_row_start"
                    )
                row["perf_frames"] = int(end) - int(start)
            else:
                row["perf_frames"] = None

            validate_parsed_row(row, context)
            rows.append(row)
    return rows


def validate_parsed_row(row: Mapping[str, object], context: str) -> None:
    if row["map"] != "seed11":
        raise ValidationError(f"{context}: expected map seed11, got {row['map']!r}")
    if not row["run_valid"]:
        return
    if row["monitor_type"] != "odom_static_pcd_swept_segment":
        raise ValidationError(
            f"{context}: unexpected monitor_type {row['monitor_type']!r}"
        )
    if row["live_cloud_enabled"] is not False:
        raise ValidationError(f"{context}: valid reference run must disable live cloud")
    if row["n_waypoints"] != 1:
        raise ValidationError(f"{context}: valid reference run must have one waypoint")

    must_exist = (
        "goal_messages",
        "static_pcd_contact_r015",
        "static_pcd_contact_r020",
        "static_pcd_contact_r025",
        "static_pcd_min_distance_m",
        "static_pcd_clearance_m",
        "mission_time_s",
        "path_length_m",
    )
    missing = [field for field in must_exist if row[field] is None]
    if missing:
        raise ValidationError(
            f"{context}: valid run has blank required values: {', '.join(missing)}"
        )
    if int(row["goal_messages"]) < 1:
        raise ValidationError(f"{context}: valid run has no goal message")
    if row["static_pcd_contact_r015"] and not row["static_pcd_contact_r020"]:
        raise ValidationError(f"{context}: r=.15 contact is not nested inside r=.20")
    if row["static_pcd_contact_r020"] and not row["static_pcd_contact_r025"]:
        raise ValidationError(f"{context}: r=.20 contact is not nested inside r=.25")

    center_distance = float(row["static_pcd_min_distance_m"])
    signed_clearance = float(row["static_pcd_clearance_m"])
    if not math.isclose(
        signed_clearance, center_distance - 0.20, rel_tol=0.0, abs_tol=2.1e-6
    ):
        raise ValidationError(
            f"{context}: clearance is inconsistent with center distance and robot_r=.20"
        )


def load_campaigns(specs: Sequence[CampaignSpec]) -> List[Dict[str, object]]:
    names = [spec.name for spec in specs]
    if len(names) != len(set(names)):
        raise ValidationError("campaign names must be unique")
    rows: List[Dict[str, object]] = []
    seen = set()
    for spec in specs:
        for row in load_campaign(spec):
            key = (row["campaign"], row["map"], row["run"], row["mode"])
            if key in seen:
                raise ValidationError(f"duplicate row key: {key}")
            seen.add(key)
            rows.append(row)
    if not rows:
        raise ValidationError("no data rows found")
    return rows


def goal_count_expected(mode: str, value: object) -> bool:
    count = int(value)
    if mode == "raw_oneway_repeat":
        return count > 1
    return count == 1


def build_mode_summary(rows: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[Tuple[str, str], List[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["campaign"]), str(row["mode"]))].append(row)

    output_rows: List[Dict[str, object]] = []
    for (campaign, mode), group in sorted(
        grouped.items(), key=lambda item: (item[0][0], MODE_RANK[item[0][1]])
    ):
        valid = [row for row in group if row["run_valid"] is True]
        complete = [row for row in valid if row["success"] is True]
        summary: Dict[str, object] = {
            "campaign": campaign,
            "mode": mode,
            "n_total": len(group),
            "n_valid": len(valid),
            "n_invalid": len(group) - len(valid),
            "n_complete": len(complete),
            "n_success": len(complete),
            "success_pct": percent(len(complete), len(valid)),
        }
        for label, field in CONTACT_COLUMNS:
            contact_count = sum(row[field] is True for row in valid)
            summary[f"{label}_n"] = contact_count
            summary[f"{label}_pct"] = percent(contact_count, len(valid))

        expected = sum(
            goal_count_expected(mode, row["goal_messages"]) for row in valid
        )
        summary["goal_expected_n"] = expected
        summary["goal_expected_pct"] = percent(expected, len(valid))

        for label, field, population in MODE_STAT_METRICS:
            selected = valid if population == "valid" else complete
            add_distribution(summary, label, (row[field] for row in selected))
        output_rows.append(summary)
    return output_rows


def pair_meta(
    campaign: str,
    contrast: str,
    a_mode: str,
    b_mode: str,
    relevant_block_count: int,
    pairs: Sequence[Pair],
) -> Dict[str, object]:
    valid_pairs = [
        pair
        for pair in pairs
        if pair.a["run_valid"] is True and pair.b["run_valid"] is True
    ]
    complete_pairs = [
        pair
        for pair in valid_pairs
        if pair.a["success"] is True and pair.b["success"] is True
    ]
    n_ab_present = sum(pair.order == "AB" for pair in pairs)
    n_ba_present = sum(pair.order == "BA" for pair in pairs)
    n_ab_valid = sum(pair.order == "AB" for pair in valid_pairs)
    n_ba_valid = sum(pair.order == "BA" for pair in valid_pairs)
    return {
        "campaign": campaign,
        "contrast": contrast,
        "a_mode": a_mode,
        "b_mode": b_mode,
        "delta_direction": "B_minus_A",
        "n_relevant_blocks": relevant_block_count,
        "n_present_pairs": len(pairs),
        "n_incomplete_pairs": relevant_block_count - len(pairs),
        "n_invalid_pairs": len(pairs) - len(valid_pairs),
        "n_valid_pairs": len(valid_pairs),
        "n_complete_pairs": len(complete_pairs),
        "n_AB_present": n_ab_present,
        "n_BA_present": n_ba_present,
        "n_AB_valid": n_ab_valid,
        "n_BA_valid": n_ba_valid,
        "order_balance_difference": n_ab_present - n_ba_present,
        "order_balanced": abs(n_ab_present - n_ba_present) <= 1,
    }


def contingency(
    values: Sequence[Tuple[bool, bool, str]], order: Optional[str] = None
) -> Dict[str, object]:
    selected = [value for value in values if order is None or value[2] == order]
    neither = sum(not a and not b for a, b, _ in selected)
    a_only = sum(a and not b for a, b, _ in selected)
    b_only = sum(not a and b for a, b, _ in selected)
    both = sum(a and b for a, b, _ in selected)
    count = len(selected)
    return {
        "n": count,
        "neither": neither,
        "a_only": a_only,
        "b_only": b_only,
        "both": both,
        "risk_difference": (b_only - a_only) / count if count else None,
        "mcnemar_p": mcnemar_exact(a_only, b_only) if count else None,
    }


def add_contingency(output: Dict[str, object], prefix: str, stats: Mapping[str, object]) -> None:
    for name, value in stats.items():
        output[f"{prefix}_{name}"] = value


def paired_distributions(
    pairs: Sequence[Pair], field: str
) -> Tuple[List[float], List[float], List[float]]:
    all_deltas: List[float] = []
    ab_deltas: List[float] = []
    ba_deltas: List[float] = []
    for pair in pairs:
        a_value = pair.a[field]
        b_value = pair.b[field]
        if a_value is None or b_value is None:
            continue
        delta = float(b_value) - float(a_value)
        all_deltas.append(delta)
        (ab_deltas if pair.order == "AB" else ba_deltas).append(delta)
    return all_deltas, ab_deltas, ba_deltas


def build_paired_summaries(
    rows: Sequence[Mapping[str, object]],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], List[str]]:
    continuous_rows: List[Dict[str, object]] = []
    binary_rows: List[Dict[str, object]] = []
    warnings: List[str] = []
    by_campaign: Dict[str, List[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        by_campaign[str(row["campaign"])].append(row)

    for campaign in sorted(by_campaign):
        campaign_rows = by_campaign[campaign]
        campaign_modes = {str(row["mode"]) for row in campaign_rows}
        for a_mode, b_mode, contrast in CONTRASTS:
            if a_mode not in campaign_modes or b_mode not in campaign_modes:
                continue
            blocks: Dict[Tuple[str, int], Dict[str, Mapping[str, object]]] = defaultdict(dict)
            for row in campaign_rows:
                if row["mode"] in (a_mode, b_mode):
                    blocks[(str(row["map"]), int(row["run"]))][str(row["mode"])] = row

            pairs: List[Pair] = []
            for block in blocks.values():
                if a_mode not in block or b_mode not in block:
                    continue
                a_row = block[a_mode]
                b_row = block[b_mode]
                order = "AB" if int(a_row["row_index"]) < int(b_row["row_index"]) else "BA"
                pairs.append(Pair(a=a_row, b=b_row, order=order))
            pairs.sort(key=lambda pair: (str(pair.a["map"]), int(pair.a["run"])))

            meta = pair_meta(
                campaign, contrast, a_mode, b_mode, len(blocks), pairs
            )
            if meta["n_incomplete_pairs"]:
                warnings.append(
                    f"{campaign}/{contrast}: {meta['n_incomplete_pairs']} incomplete pair(s) excluded"
                )
            if not meta["order_balanced"]:
                warnings.append(
                    f"{campaign}/{contrast}: AB/BA imbalance "
                    f"{meta['n_AB_present']} vs {meta['n_BA_present']}"
                )

            valid_pairs = [
                pair
                for pair in pairs
                if pair.a["run_valid"] is True and pair.b["run_valid"] is True
            ]
            complete_pairs = [
                pair
                for pair in valid_pairs
                if pair.a["success"] is True and pair.b["success"] is True
            ]

            binary_fields = (("success", "success"),) + CONTACT_COLUMNS
            for metric, field in binary_fields:
                values = [
                    (bool(pair.a[field]), bool(pair.b[field]), pair.order)
                    for pair in valid_pairs
                    if pair.a[field] is not None and pair.b[field] is not None
                ]
                overall = contingency(values)
                ab = contingency(values, "AB")
                ba = contingency(values, "BA")
                output: Dict[str, object] = dict(meta)
                output.update(
                    {
                        "metric": metric,
                        "preferred_direction": (
                            "higher_B" if metric == "success" else "lower_B"
                        ),
                    }
                )
                add_contingency(output, "all", overall)
                add_contingency(output, "AB", ab)
                add_contingency(output, "BA", ba)
                if ab["risk_difference"] is not None and ba["risk_difference"] is not None:
                    interaction = float(ab["risk_difference"]) - float(
                        ba["risk_difference"]
                    )
                    output["order_interaction"] = interaction
                    output["approx_order_effect"] = interaction / 2.0
                else:
                    output["order_interaction"] = None
                    output["approx_order_effect"] = None
                binary_rows.append(output)

            for metric, field, population in PAIRED_CONTINUOUS_METRICS:
                selected_pairs = valid_pairs if population == "valid" else complete_pairs
                all_deltas, ab_deltas, ba_deltas = paired_distributions(
                    selected_pairs, field
                )
                output = dict(meta)
                output.update({"metric": metric, "population": population})
                add_distribution(output, "delta", all_deltas)
                add_distribution(output, "delta_AB", ab_deltas)
                add_distribution(output, "delta_BA", ba_deltas)
                median_ab = type7_quantile(ab_deltas, 0.50)
                median_ba = type7_quantile(ba_deltas, 0.50)
                if median_ab is not None and median_ba is not None:
                    interaction = median_ab - median_ba
                    output["order_interaction"] = interaction
                    output["approx_order_effect"] = interaction / 2.0
                else:
                    output["order_interaction"] = None
                    output["approx_order_effect"] = None
                continuous_rows.append(output)

    return continuous_rows, binary_rows, warnings


def distribution_columns(prefix: str) -> List[str]:
    return [f"{prefix}_n", f"{prefix}_median", f"{prefix}_q1", f"{prefix}_q3"]


def mode_fieldnames() -> List[str]:
    fields = [
        "campaign",
        "mode",
        "n_total",
        "n_valid",
        "n_invalid",
        "n_complete",
        "n_success",
        "success_pct",
    ]
    for label, _ in CONTACT_COLUMNS:
        fields.extend((f"{label}_n", f"{label}_pct"))
    fields.extend(("goal_expected_n", "goal_expected_pct"))
    for label, _, _ in MODE_STAT_METRICS:
        fields.extend(distribution_columns(label))
    return fields


PAIR_META_FIELDS = [
    "campaign",
    "contrast",
    "a_mode",
    "b_mode",
    "delta_direction",
    "n_relevant_blocks",
    "n_present_pairs",
    "n_incomplete_pairs",
    "n_invalid_pairs",
    "n_valid_pairs",
    "n_complete_pairs",
    "n_AB_present",
    "n_BA_present",
    "n_AB_valid",
    "n_BA_valid",
    "order_balance_difference",
    "order_balanced",
]


def continuous_fieldnames() -> List[str]:
    return (
        PAIR_META_FIELDS
        + ["metric", "population"]
        + distribution_columns("delta")
        + distribution_columns("delta_AB")
        + distribution_columns("delta_BA")
        + ["order_interaction", "approx_order_effect"]
    )


def binary_fieldnames() -> List[str]:
    fields = PAIR_META_FIELDS + ["metric", "preferred_direction"]
    for prefix in ("all", "AB", "BA"):
        fields.extend(
            f"{prefix}_{suffix}"
            for suffix in (
                "n",
                "neither",
                "a_only",
                "b_only",
                "both",
                "risk_difference",
                "mcnemar_p",
            )
        )
    fields.extend(("order_interaction", "approx_order_effect"))
    return fields


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def display(value: object, digits: int = 3) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def print_console(
    mode_rows: Sequence[Mapping[str, object]],
    continuous_rows: Sequence[Mapping[str, object]],
    binary_rows: Sequence[Mapping[str, object]],
) -> None:
    print("\nMode summary")
    print(
        "campaign\tmode\tvalid\tsuccess\tcontact(.15/.20/.25)\t"
        "clearance median[IQR]\ttime median[IQR]\tgoals median[IQR]"
    )
    for row in mode_rows:
        clearance = (
            f"{display(row['clearance_m_median'])}"
            f"[{display(row['clearance_m_q1'])},{display(row['clearance_m_q3'])}]"
        )
        mission_time = (
            f"{display(row['mission_time_s_median'])}"
            f"[{display(row['mission_time_s_q1'])},{display(row['mission_time_s_q3'])}]"
        )
        goals = (
            f"{display(row['goal_messages_median'])}"
            f"[{display(row['goal_messages_q1'])},{display(row['goal_messages_q3'])}]"
        )
        contacts = "/".join(
            str(row[f"{label}_n"]) for label, _ in CONTACT_COLUMNS
        )
        print(
            f"{row['campaign']}\t{row['mode']}\t{row['n_valid']}/{row['n_total']}\t"
            f"{row['n_success']}/{row['n_valid']}\t{contacts}\t"
            f"{clearance}\t{mission_time}\t{goals}"
        )

    print("\nPaired binary effects (B-A risk difference)")
    for row in binary_rows:
        print(
            f"{row['campaign']} {row['contrast']} {row['metric']}: "
            f"pairs={row['all_n']} RD={display(row['all_risk_difference'], 4)} "
            f"McNemar={display(row['all_mcnemar_p'], 4)} "
            f"AB/BA={row['n_AB_present']}/{row['n_BA_present']}"
        )

    print("\nPaired continuous effects (median B-A [IQR])")
    for row in continuous_rows:
        print(
            f"{row['campaign']} {row['contrast']} {row['metric']}: "
            f"n={row['delta_n']} delta={display(row['delta_median'])}"
            f"[{display(row['delta_q1'])},{display(row['delta_q3'])}] "
            f"order_interaction={display(row['order_interaction'])}"
        )


def output_paths(prefix: Path) -> Tuple[Path, Path, Path]:
    return (
        Path(f"{prefix}_mode_summary.csv"),
        Path(f"{prefix}_paired_continuous.csv"),
        Path(f"{prefix}_paired_binary.csv"),
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign",
        action="append",
        required=True,
        type=parse_campaign_spec,
        metavar="NAME=CSV_PATH",
        help="named campaign CSV; repeat for independent A/B campaign files",
    )
    parser.add_argument(
        "--out-prefix",
        required=True,
        type=Path,
        help="output prefix without a .csv suffix",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out_mode, out_continuous, out_binary = output_paths(args.out_prefix)
    input_paths = {spec.path.resolve() for spec in args.campaign}
    for output_path in (out_mode, out_continuous, out_binary):
        if output_path.resolve() in input_paths:
            raise ValidationError(f"refusing to overwrite input CSV: {output_path}")

    rows = load_campaigns(args.campaign)
    mode_rows = build_mode_summary(rows)
    continuous_rows, binary_rows, warnings = build_paired_summaries(rows)
    write_csv(out_mode, mode_fieldnames(), mode_rows)
    write_csv(out_continuous, continuous_fieldnames(), continuous_rows)
    write_csv(out_binary, binary_fieldnames(), binary_rows)
    print_console(mode_rows, continuous_rows, binary_rows)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    print(f"\nWrote {out_mode}, {out_continuous}, and {out_binary}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
