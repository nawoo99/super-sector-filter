#!/usr/bin/env python3
"""Create a new, hash-checked runtime asset ZIP and sidecar manifest.

Usage: build_runtime_assets.py /absolute/new-assets.zip /absolute/new-manifest.json
Extract the ZIP into paper_handoff_20261015; entries start with full_source/.
This host-side packager never builds, stages, pushes, or modifies source assets.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile


SUPER = Path("/root/super_ws/src/SUPER")
REPO = Path("/root/super-sector-filter")
FROZEN = Path("/root/share/here/v6_frozen_20261008")
FREEZE_MANIFEST_SHA256 = "18e2c2240f4084601bb2f06cd72165759dfb49f0b2071307dcc4fec4c1b29781"
MAX_REGULAR_FILE_BYTES = 100_000_000
FROZEN_MAPS = {
    "gapfree_d1_m01": "98ad0e49a126ecbb7f1b6ee8532db06aa76720f4d3cfd7c513441fa9ab576d9e",
    "gapfree_d1_m02": "a756f29a9bfd1840f15d38e05deca82e30f5106f7e2fd24b28873462ab357ba2",
    "gapfree_d1_m03": "69126feaea243f6423da8885ce01d3691040328b45e481de04c3bd4614956d9b",
    "gapfree_d1_m04": "1ccbf89dcf6192b104c26457d0e73b7b2bf1bd0400fa270c575ce084b5287632",
    "gapfree_d1_m05r2": "a740f7b64a1a3949e37333439c80ca6f2bb4d626ead4a6b51896a0fdd7499695",
    "urban_blocks_u01": "cb824fa3d977f2e3b9757e6154bb8bcd6b2eaae8f3f405365c0267b661270f39",
    "forest_cluster_f01": "2f9662d5ceabbd3abc4e25485b56713c5b7216da5001d0e929e5c2e14b77ac74",
}
RESULTS_TEXT = (
    "gapfree_d1_maps_20260921_r2/manifest.json",
    "scenario7_maps_20260924/manifest.json",
    "scenario7_missions_20260924/manifest.json",
    "scenario7_missions_20260924/urban_blocks_u01_proof.json",
    "scenario7_missions_20260924/forest_cluster_f01_proof.json",
    "gapfree_d1_maps_20260918/gapfree_d1_m01_cylinders.csv",
    "gapfree_d1_maps_20260918/gapfree_d1_m02_cylinders.csv",
    "gapfree_d1_maps_20260918/gapfree_d1_m03_cylinders.csv",
    "gapfree_d1_maps_20260918/gapfree_d1_m04_cylinders.csv",
    "gapfree_d1_maps_20260921_r2/gapfree_d1_m05r2_cylinders.csv",
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def stream_digest(stream):
    result = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        result.update(chunk)
    return result.hexdigest()


def digest(path):
    with path.open("rb") as stream:
        return stream_digest(stream)


def load_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def frozen_inventory():
    freeze_path = FROZEN / "freeze_manifest.json"
    require(digest(freeze_path) == FREEZE_MANIFEST_SHA256, "Original frozen manifest changed")
    freeze = load_json(freeze_path)
    source_path = FROZEN / "source_manifest.json"
    require(digest(source_path) == freeze["sha256"]["source_manifest.json"],
            "Original frozen source inventory changed")
    return load_json(source_path)["sha256"], digest(source_path)


def specifications():
    result = []
    for name, expected in FROZEN_MAPS.items():
        relative = Path("mars_uav_sim/perfect_drone_sim/pcd/seed_maps") / (name + ".pcd")
        result.append((SUPER / relative, "full_source/super_ws/src/SUPER/" + relative.as_posix(),
                       "frozen_seven_map", expected))
        mirror_relative = Path("super_patches/native_seedmap_campaign/perfect_drone_sim_pcd/seed_maps") / (name + ".pcd")
        result.append((REPO / mirror_relative, "full_source/super-sector-filter/" + mirror_relative.as_posix(),
                       "frozen_seven_map_mirror_alias", expected))
    for relative, role in (
        ("mars_uav_sim/perfect_drone_sim/pcd/seed_maps/seed1.pcd", "default_startup_compatibility_not_frozen_seven"),
        ("mars_uav_sim/perfect_drone_sim/meshes/yunque-M.dae", "optional_visualization_mesh_not_frozen"),
        ("mars_uav_sim/perfect_drone_sim/meshes/R.jpeg", "optional_visualization_texture_not_frozen"),
        ("mars_uav_sim/perfect_drone_sim/meshes/MaRS LOGO (2).png", "optional_visualization_image_not_frozen"),
    ):
        result.append((SUPER / relative, "full_source/super_ws/src/SUPER/" + relative, role, None))
    for relative in RESULTS_TEXT:
        result.append((REPO / "results" / relative,
                       "full_source/super-sector-filter/results/" + relative,
                       "frozen_runtime_registry_or_validation_dependency", None))
    return result


def validate_output(path):
    require(path.is_absolute(), f"Output must be absolute: {path}")
    require(path.parent.is_dir() and not path.parent.is_symlink(), f"Output parent must exist: {path.parent}")
    require(not path.exists() and not path.is_symlink(), f"Refusing existing output: {path}")
    resolved = path.resolve()
    require(not any(resolved.is_relative_to(root.resolve()) for root in (REPO, Path("/root/super_ws"), FROZEN)),
            f"Refusing output inside an original source/workspace/frozen tree: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dest_zip", type=Path)
    parser.add_argument("manifest_json", type=Path)
    args = parser.parse_args()
    validate_output(args.dest_zip)
    validate_output(args.manifest_json)
    require(args.dest_zip.resolve() != args.manifest_json.resolve(), "ZIP and manifest must be different files")
    require(args.dest_zip.suffix.lower() == ".zip" and args.manifest_json.suffix.lower() == ".json",
            "Expected .zip and .json destinations")
    pins, source_manifest_hash = frozen_inventory()
    mission_registry = REPO / 'results/scenario7_missions_20260924/manifest.json'
    require(digest(mission_registry) == pins.get(str(mission_registry)),
            'Mission registry is not frozen byte-identical')
    mission_asset_pins = load_json(mission_registry)['assets_sha256']
    records = []
    for source, member, role, hard_pin in specifications():
        require(source.is_file() and not source.is_symlink(), f"Missing/nonregular runtime asset: {source}")
        require(source.stat().st_size < MAX_REGULAR_FILE_BYTES, f"Asset exceeds chosen 100MB regular-file ceiling: {source}")
        require(member.startswith("full_source/") and ".." not in Path(member).parts,
                f"Invalid archive restore path: {member}")
        actual = digest(source)
        frozen_pin = pins.get(str(source))
        transitive_pin = mission_asset_pins.get(str(source)) if source.name.endswith('_proof.json') else None
        if hard_pin is not None:
            require(actual == hard_pin and frozen_pin == hard_pin, f"Frozen seven-map SHA256 mismatch: {source}")
        if role == "frozen_runtime_registry_or_validation_dependency":
            require((frozen_pin == actual) or (transitive_pin == actual),
                    f"Frozen runtime registry/dependency mismatch: {source}")
        if frozen_pin is not None:
            require(frozen_pin == actual, f"Frozen source-inventory mismatch: {source}")
        records.append({"source": str(source), "archive_path": member,
                        "restore_relative_to_paper_handoff": member,
                        "role": role, "bytes": source.stat().st_size, "sha256": actual,
                        "is_frozen_seven_map": role == "frozen_seven_map",
                        "is_frozen_seven_map_mirror_alias": role == "frozen_seven_map_mirror_alias",
                        "canonical_archive_path": ("full_source/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/pcd/seed_maps/" + source.name)
                            if role == "frozen_seven_map_mirror_alias" else None,
                        "frozen_source_inventory_pinned": frozen_pin is not None,
                        "frozen_expected_sha256": frozen_pin,
                        "frozen_registry_transitive_sha256": transitive_pin,
                        "frozen_registry_evidence_path": str(mission_registry) if transitive_pin else None,
                        "required_for_explicit_frozen_map_launch": role.startswith("frozen_"),
                        "visualization_only": role.startswith("optional_visualization")})
    require(len(records) == 28 and len({item["archive_path"] for item in records}) == 28,
            "Unexpected runtime-asset whitelist")
    require(sum(item["is_frozen_seven_map"] for item in records) == 7, "Expected exactly seven frozen maps")
    require(sum(item["is_frozen_seven_map_mirror_alias"] for item in records) == 7,
            "Expected all seven frozen map mirror aliases required by runtime admission")
    by_member = {item["archive_path"]: item for item in records}
    for item in records:
        if item["is_frozen_seven_map_mirror_alias"]:
            canonical = by_member[item["canonical_archive_path"]]
            require(item["sha256"] == canonical["sha256"] and item["bytes"] == canonical["bytes"],
                    "Frozen map mirror does not match canonical source")
    with zipfile.ZipFile(args.dest_zip, mode="x", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as archive:
        for item in records:
            archive.write(item["source"], arcname=item["archive_path"])
    with zipfile.ZipFile(args.dest_zip) as archive:
        require(archive.testzip() is None, "Runtime ZIP CRC validation failed")
        require(set(archive.namelist()) == {item["archive_path"] for item in records}, "Archive member-set mismatch")
        for item in records:
            with archive.open(item["archive_path"]) as stream:
                require(stream_digest(stream) == item["sha256"], f"Archived payload hash mismatch: {item['archive_path']}")
            require(digest(Path(item["source"])) == item["sha256"], f"Original asset changed during packaging: {item['source']}")
            item["zip_compressed_bytes"] = archive.getinfo(item["archive_path"]).compress_size
    manifest = {"schema": "super-frozen-seven-runtime-assets-v1", "state": "VALIDATED",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "archive": str(args.dest_zip), "archive_sha256": digest(args.dest_zip),
                "archive_bytes": args.dest_zip.stat().st_size,
                "uncompressed_bytes": sum(item["bytes"] for item in records), "files": len(records),
                "frozen_seven_pcd_files": 7, "frozen_seven_mirror_pcd_files": 7,
                "total_pcd_archive_members": 15, "startup_compatibility_pcd_files": 1,
                "optional_visual_files_not_frozen": 3, "runtime_registry_and_validation_files": 10,
                "frozen_source_manifest_sha256": source_manifest_hash,
                "restore_instructions": "Extract into paper_handoff_20261015; full_source/ prefix is part of each member path. Do not extract inside full_source again.",
                "visualization_scope": "All three existing mesh-folder files are retained: yunque-M.dae, its only external image R.jpeg, and the unreferenced MaRS LOGO (2).png. They are RViz/visual resources, not sensing geometry or frozen measurement evidence; hashes are current snapshot hashes.",
                "known_preexisting_limitations": ["Config fallback meshes/f250.dae is absent in the original source tree. No replacement is invented; all frozen-seven YAMLs explicitly select the existing yunque-M.dae."],
                "startup_scope": "seed1.pcd supports benchmark_seedmap.launch.py defaults but is not one of the frozen seven. Other historical/demo PCDs are intentionally excluded; use explicit frozen map configs for the final experiment.",
                "mirror_scope": "The same seven frozen map bytes are restored under both canonical SUPER paths and the exact super-sector-filter patch-mirror paths required by validate_suite(). They are aliases, not additional maps or experiments. No seed1 mirror exists or is required for these final-seven admission/default direct-launch paths.",
                "required_text_source_not_repeated": [
                    "super_ws/src/SUPER/mission_planner/data/*.txt (all26, including benchmark.txt and protected legacy templates)",
                    "super_ws/src/SUPER/mission_planner/config/waypoint.yaml",
                    "super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/config/*.yaml",
                    "super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/pcd/seed_maps/*_cylinders.csv and *_geometry.json",
                    "super_ws/src/SUPER/mars_uav_sim/marsim_render/config/pattern/{360camera.vs,camera.fs,camera.vs}"],
                "excluded": "Historical PCDs, generated build/install/log trees, runtime binaries, papers/PDFs, videos and measurement logs",
                "maximum_regular_asset_bytes": MAX_REGULAR_FILE_BYTES,
                "new_experiments": 0, "original_assets_modified": False, "git_operations": False,
                "crc_and_all_payload_sha256_verified": True, "assets": records,
                "builder_sha256": digest(Path(__file__))}
    with args.manifest_json.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"state": "VALIDATED", "archive": str(args.dest_zip),
                      "manifest": str(args.manifest_json), "files": len(records),
                      "archive_bytes": manifest["archive_bytes"], "archive_sha256": manifest["archive_sha256"]}), flush=True)


if __name__ == "__main__":
    main()
