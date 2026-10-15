#!/usr/bin/env python3
"""Release a validated local data package without changing frozen sources."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from PIL import Image


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    folder = args.package.resolve()
    archive = args.zip.resolve()
    manifest_file = folder / "release_manifest.json"
    if manifest_file.exists() or archive.exists():
        raise FileExistsError("Release outputs already exist; do not overwrite them")
    report = json.loads((folder / "10_validation.json").read_text(encoding="utf-8"))
    assert report["valid"] and not report["errors"]
    assert report["checked_counts"]["original_main_rows"] == 210
    assert report["checked_counts"]["original_gate_rows"] == 30
    assert report["checked_counts"]["main_adaptive_cycles"] == 509
    assert not report["simulation_launched"] and not report["source_files_modified"]
    for path in folder.rglob("*.png"):
        with Image.open(path) as picture:
            picture.verify()
    for path in folder.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert "\ufffd" not in text
    filenames = [path for path in sorted(folder.rglob("*")) if path.is_file() and "__pycache__" not in path.parts]
    manifest = {
        "schema": "super-comprehensive-package-release-v1", "state": "VALIDATED",
        "release_date_kst": "2026-10-12", "original_result_freeze_date": "2026-10-08",
        "main_cohort_runs": 210, "separate_gate_runs": 30,
        "independent_validation": "10_validation.json",
        "new_simulations": 0, "frozen_sources_modified": False,
        "original_contact_labels_preserved": True,
        "mapping_timer_scope": "Recorded ROG-Map Total elapsed in updateProbMap, not CPU time or whole mapping subsystem",
        "sha256": {path.relative_to(folder).as_posix(): digest(path) for path in filenames},
    }
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Recheck after manifest generation and include the manifest itself in ZIP.
    for relative, expected in manifest["sha256"].items():
        assert digest(folder / relative) == expected, relative
    filenames.append(manifest_file)
    with zipfile.ZipFile(archive, mode="x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in filenames:
            bundle.write(path, arcname=(Path(folder.name) / path.relative_to(folder)).as_posix())
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert len(bundle.infolist()) == len(filenames)
        for path in filenames:
            member = (Path(folder.name) / path.relative_to(folder)).as_posix()
            assert hashlib.sha256(bundle.read(member)).hexdigest() == digest(path)
    print(json.dumps({"package": str(folder), "archive": str(archive), "files": len(filenames),
                      "archive_mib": archive.stat().st_size / 2**20,
                      "archive_sha256": digest(archive), "valid": True}, indent=2))


if __name__ == "__main__":
    main()
