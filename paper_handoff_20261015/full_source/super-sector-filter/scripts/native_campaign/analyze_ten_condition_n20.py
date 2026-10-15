#!/usr/bin/env python3
"""Build the frozen ten-condition n=20 paper summary."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

import analyze_eight_condition_n20 as base


MODES = base.MODES
NORMAL_CONDITIONS = base.NORMAL_CONDITIONS
LEGACY_STRESS_CONDITIONS = base.STRESS_CONDITIONS
EXTENSION_STRESS_CONDITIONS = {
    "C4_deep_mirror": ("shc4_deep_mirror_hazard",),
    "C5_asymmetric_offset": ("shc5_asymmetric_offset_hazard",),
}
EXTENSION_MAPS = tuple(
    maps[0] for maps in EXTENSION_STRESS_CONDITIONS.values()
)
FROZEN_HASHES = {
    "normal_campaign": (
        "b40f880271a52f4b3332bfe67afe3d489cf8c6d444ac0c72ed30d9e9cd445ec5"
    ),
    "normal_validation": (
        "ea8091c1fac455e07e153e9034a4fef913563509ccb3db4c27ae2374fae7ae0a"
    ),
    "legacy_stress_campaign": (
        "7cc9bbaf238203bc8b9d0ec16dceb977a44fbb118dc41d5aabe7356cf30fad1a"
    ),
    "eight_condition_result": (
        "f6c20e1a5ef4dffc3c6306c3c3a5f8eec7fb24aadb8c7647dbcf306702706c80"
    ),
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prerequisite_gate_checks(
    structure_gate: dict[str, object],
    replay_gates: list[dict[str, object]],
    full_gate_rows: list[dict[str, str]],
) -> dict[str, bool]:
    variants = structure_gate.get("variants", {})
    structure_variants_pass = (
        isinstance(variants, dict)
        and set(variants) == {"c4_deep_mirror", "c5_asymmetric_offset"}
        and all(
            isinstance(payload, dict) and payload.get("status") == "PASS"
            for payload in variants.values()
        )
    )
    full_keys = {
        (row.get("map"), row.get("run"), row.get("mode"))
        for row in full_gate_rows
    }
    expected_full_keys = {
        (map_name, "1", "full") for map_name in EXTENSION_MAPS
    }
    return {
        "C4_C5_structure_gate_passed": (
            structure_gate.get("status") == "PASS"
            and structure_variants_pass
        ),
        "C4_C5_paired_cpp_replay_gates_passed": (
            len(replay_gates) == len(EXTENSION_MAPS)
            and all(gate.get("decision") == "PASS" for gate in replay_gates)
        ),
        "C4_C5_full_feasibility_gate_passed": (
            len(full_gate_rows) == len(expected_full_keys)
            and full_keys == expected_full_keys
            and all(
                base.dropout_integrity(row) and base.safe_complete(row)
                for row in full_gate_rows
            )
        ),
    }


def analyze(normal_rows: list[dict[str, str]],
            normal_validation: dict[str, object],
            legacy_stress_rows: list[dict[str, str]],
            extension_rows: list[dict[str, str]],
            eight_condition_result: dict[str, object],
            source_hashes_valid: bool = True,
            prerequisite_gates: dict[str, bool] | None = None) -> dict[str, object]:
    normal_maps = tuple(
        map_name for maps in NORMAL_CONDITIONS.values() for map_name in maps
    )
    legacy_maps = tuple(
        maps[0] for maps in LEGACY_STRESS_CONDITIONS.values()
    )
    extension_maps = EXTENSION_MAPS
    all_stress_rows = legacy_stress_rows + extension_rows

    normal_matrix = base.expected_matrix(normal_rows, normal_maps, 1, 10)
    legacy_matrix = base.expected_matrix(
        legacy_stress_rows, legacy_maps, 1, 20
    )
    extension_matrix = base.expected_matrix(
        extension_rows, extension_maps, 1, 20
    )
    normal_integrity = normal_matrix and all(
        base.common_integrity(row) for row in normal_rows
    )
    legacy_integrity = legacy_matrix and all(
        base.dropout_integrity(row) for row in legacy_stress_rows
    )
    extension_integrity = extension_matrix and all(
        base.dropout_integrity(row) for row in extension_rows
    )

    conditions: dict[str, object] = {}
    for name, maps in NORMAL_CONDITIONS.items():
        rows = [row for row in normal_rows if row.get("map") in maps]
        conditions[name] = {
            "family": "normal_radius_tier",
            "physical_maps": list(maps),
            **base.summarize_group(rows, base.common_integrity),
        }
    for name, maps in LEGACY_STRESS_CONDITIONS.items():
        rows = [row for row in legacy_stress_rows if row.get("map") in maps]
        conditions[name] = {
            "family": "static_burst_dropout_original_extension",
            "physical_maps": list(maps),
            **base.summarize_group(rows, base.dropout_integrity),
        }
    for name, maps in EXTENSION_STRESS_CONDITIONS.items():
        rows = [row for row in extension_rows if row.get("map") in maps]
        conditions[name] = {
            "family": "static_burst_dropout_prospective_c4_c5",
            "physical_maps": list(maps),
            **base.summarize_group(rows, base.dropout_integrity),
        }

    extension_group = base.summarize_group(
        extension_rows, base.dropout_integrity
    )
    extension_pair = extension_group["paired_adaptive_vs_sector"]
    extension_full_safe = all(
        sum(base.safe_complete(row) for row in extension_rows
            if row["map"] == map_name and row["mode"] == "full") == 20
        for map_name in extension_maps
    )
    extension_adaptive_safe = all(
        sum(base.safe_complete(row) for row in extension_rows
            if row["map"] == map_name and row["mode"] == "adaptive") == 20
        for map_name in extension_maps
    )
    extension_sector_unsafe = all(
        sum(base.safe_complete(row) for row in extension_rows
            if row["map"] == map_name and row["mode"] == "sector") < 20
        for map_name in extension_maps
    )
    extension_checks = {
        "complete_unique_120_row_matrix": extension_matrix,
        "all_extension_rows_integrity_valid": extension_integrity,
        "full_20_of_20_safe_each_map": extension_full_safe,
        "adaptive_20_of_20_safe_each_map": extension_adaptive_safe,
        "sector_unsafe_at_least_once_each_map": extension_sector_unsafe,
        "discordance_adaptive_favouring": (
            extension_pair["sector_unsafe_adaptive_safe"]
            > extension_pair["sector_safe_adaptive_unsafe"]
        ),
        "exact_mcnemar_p_below_0_05": (
            extension_pair["exact_mcnemar_two_sided_p"] < 0.05
        ),
    }
    if all(extension_checks.values()):
        extension_decision = "C4_C5_EXTENSION_OBSERVED"
    elif extension_matrix and extension_integrity and (
        extension_pair["sector_unsafe_adaptive_safe"]
        > extension_pair["sector_safe_adaptive_unsafe"]
    ):
        extension_decision = "C4_C5_EXTENSION_PARTIAL"
    else:
        extension_decision = "C4_C5_EXTENSION_FAILED"

    complete_conditions = all(
        condition["modes"][mode]["runs"] == 20
        for condition in conditions.values() for mode in MODES
    )
    gate_checks = prerequisite_gates or {
        "C4_C5_structure_gate_passed": True,
        "C4_C5_paired_cpp_replay_gates_passed": True,
        "C4_C5_full_feasibility_gate_passed": True,
    }
    checks = {
        "frozen_source_hashes_match": source_hashes_valid,
        "normal_source_validation_passed": normal_validation.get("passed") is True,
        "normal_matrix_complete_and_integrity_valid": normal_integrity,
        "eight_condition_source_complete": (
            eight_condition_result.get("decision")
            == "EIGHT_CONDITION_N20_COMPLETE"
        ),
        "legacy_C1_C3_complete_and_integrity_valid": legacy_integrity,
        "C4_C5_extension_observed": (
            extension_decision == "C4_C5_EXTENSION_OBSERVED"
        ),
        "ten_conditions_have_20_rows_per_mode": complete_conditions,
        **gate_checks,
    }
    decision = (
        "TEN_CONDITION_N20_COMPLETE"
        if all(checks.values()) else "TEN_CONDITION_N20_INCOMPLETE"
    )
    return {
        "schema": "ten-condition-n20-result-v1",
        "decision": decision,
        "checks": checks,
        "failure_reasons": [name for name, passed in checks.items() if not passed],
        "extension_decision": extension_decision,
        "extension_checks": extension_checks,
        "prerequisite_gates": gate_checks,
        "conditions": conditions,
        "groups": {
            "normal_R1_R5": base.summarize_group(
                normal_rows, base.common_integrity
            ),
            "stress_C1_C3": base.summarize_group(
                legacy_stress_rows, base.dropout_integrity
            ),
            "stress_C4_C5": extension_group,
            "stress_C1_C5_descriptive": base.summarize_group(
                all_stress_rows, base.dropout_integrity
            ),
        },
        "row_accounting": {
            "normal_rows": len(normal_rows),
            "legacy_stress_rows": len(legacy_stress_rows),
            "extension_stress_rows": len(extension_rows),
            "all_stress_rows": len(all_stress_rows),
            "paper_table_rows": len(normal_rows) + len(all_stress_rows),
        },
        "claim_boundary": (
            "Ten reporting conditions: five normal radius tiers retain two "
            "physical layouts each; C1-C3 retain their prior two-block result; "
            "C4-C5 are a prospective post-confirmation extension. Normal and "
            "stress metrics are not pooled, and C1-C5 inference is descriptive."
        ),
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal-campaign", type=Path, required=True)
    parser.add_argument("--normal-validation", type=Path, required=True)
    parser.add_argument("--legacy-stress-campaign", type=Path, required=True)
    parser.add_argument("--extension-stress-campaign", type=Path, required=True)
    parser.add_argument("--eight-condition-result", type=Path, required=True)
    parser.add_argument("--structure-gate", type=Path, required=True)
    parser.add_argument("--replay-gates", type=Path, nargs=2, required=True)
    parser.add_argument("--full-gate-campaign", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source_paths = {
        "normal_campaign": args.normal_campaign,
        "normal_validation": args.normal_validation,
        "legacy_stress_campaign": args.legacy_stress_campaign,
        "eight_condition_result": args.eight_condition_result,
    }
    observed_hashes = {
        name: file_sha256(path) for name, path in source_paths.items()
    }
    source_hashes_valid = observed_hashes == FROZEN_HASHES
    prerequisite_gates = prerequisite_gate_checks(
        json.loads(args.structure_gate.read_text()),
        [json.loads(path.read_text()) for path in args.replay_gates],
        read_csv(args.full_gate_campaign),
    )
    result = analyze(
        read_csv(args.normal_campaign),
        json.loads(args.normal_validation.read_text()),
        read_csv(args.legacy_stress_campaign),
        read_csv(args.extension_stress_campaign),
        json.loads(args.eight_condition_result.read_text()),
        source_hashes_valid=source_hashes_valid,
        prerequisite_gates=prerequisite_gates,
    )
    result["source_hashes"] = {
        "expected": FROZEN_HASHES,
        "observed": observed_hashes,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    temporary.write_text(rendered)
    os.replace(temporary, args.out)
    print(rendered, end="")
    return 0 if result["decision"] == "TEN_CONDITION_N20_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
