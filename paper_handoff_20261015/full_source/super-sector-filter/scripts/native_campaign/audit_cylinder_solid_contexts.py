#!/usr/bin/env python3
"""Read-only retrospective solid-volume audit of saved ACTUAL 3D poses.

Sparse saved contexts can disprove a surface-only zero-contact claim, but
cannot certify a complete flight. Planned points and XY-only traces are not
actual 3D poses and are deliberately excluded. Original results are untouched.
"""
import csv
import json
from pathlib import Path

import numpy as np

from cylinder_map_search import OUT
from cylinder_solid_observer import solid_clearances


def actual_contexts(report):
    for key in ("static_pcd_min_context", "static_hazard_min_context",
                "first_static_hazard_contact_context"):
        context = report.get(key)
        if isinstance(context, dict) and len(context.get("position", [])) == 3:
            yield key, context["position"]
    final = [report.get("final_" + axis) for axis in "xyz"]
    if all(isinstance(value, (int, float)) for value in final):
        yield "final_position", final


def audit(report, cylinders, height):
    contexts = []
    for source, position in actual_contexts(report):
        if not np.isfinite(position).all():
            continue
        margins = solid_clearances(position, cylinders, height)
        index = int(np.argmin(margins))
        contexts.append(dict(source=source, position=position,
                             signed_body_clearance_m=float(margins[index]),
                             cylinder_index=index, cylinder=cylinders[index].tolist()))
    contacts = [item for item in contexts if item["signed_body_clearance_m"] <= 0]
    return dict(contexts=contexts, definite_contact_in_saved_pose=bool(contacts),
                whole_flight_safety_certified=False,
                interpretation="CONTACT_CONFIRMED" if contacts else
                "NO_CONTACT_IN_SPARSE_CONTEXTS_NOT_A_SAFETY_CERTIFICATE")


def main():
    rows = []
    for raw in sorted(OUT.glob("cyl2_*/raw.csv")):
        folder = raw.parent
        manifest = json.loads((folder / "manifest.json").read_text())
        cylinders = np.asarray([(float(r["x"]), float(r["y"]), float(r["r"]))
                                for r in csv.DictReader((folder / "cylinders.csv").open())])
        for row in csv.DictReader(raw.open()):
            report_path = folder / "artifacts" / f"{folder.name}_run{row['run']}_{row['mode']}.json"
            if not report_path.exists():
                raise RuntimeError(f"Missing original evidence: {report_path}")
            report = json.loads(report_path.read_text())
            rows.append(dict(map=folder.name, run=int(row["run"]), mode=row["mode"],
                             original_success=row["success"],
                             original_surface_contacts=row["static_pcd_collisions"],
                             original_report=str(report_path),
                             **audit(report, cylinders, manifest["height_m"])))
    result = dict(protocol="sparse-actual-3d-pose-solid-audit-v1", body_radius_m=.2,
                  scope="Only saved actual 3D contexts, not planned trajectories or XY traces",
                  original_results_modified=False, trials=len(rows),
                  definite_contact_trials=sum(row["definite_contact_in_saved_pose"] for row in rows),
                  rows=rows)
    target = OUT / "solid_context_audit.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}))
    for row in rows:
        if row["definite_contact_in_saved_pose"]:
            print(json.dumps(row))


if __name__ == "__main__":
    main()
