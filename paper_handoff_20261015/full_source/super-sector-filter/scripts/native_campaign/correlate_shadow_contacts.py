#!/usr/bin/env python3
"""Correlate shadow trajectory warnings with independently observed contact."""

import argparse
import json
import re


GEOMETRIC_STATUSES = {"OCCUPIED", "OUT_OF_MAP"}
STAMP = re.compile(r"\[(\d{9,}(?:\.\d+)?)\]")


def parse_unsafe_events(stack_log):
    events = []
    with open(stack_log, errors="replace") as stream:
        for line in stream:
            if "TRAJ_GUARD_SHADOW_UNSAFE" not in line:
                continue
            def field(name):
                match = re.search(rf"\b{name}=([^ ]+)", line)
                return match.group(1) if match else None
            stamp = STAMP.search(line)
            if not stamp:
                continue
            status = field("status") or "UNKNOWN"
            if status not in GEOMETRIC_STATUSES:
                continue
            try:
                from_tt = float(field("from_tt"))
                collision_tt = float(field("collision_tt"))
            except (TypeError, ValueError):
                from_tt = 0.0
                collision_tt = 0.0
            epoch_s = float(stamp.group(1))
            events.append({
                "epoch_s": epoch_s,
                "predicted_contact_epoch_s": epoch_s + max(0.0, collision_tt - from_tt),
                "segment": field("segment") or "UNKNOWN",
                "status": status,
                "generation": field("gen"),
                "map_version": field("map"),
                "from_tt": from_tt,
                "collision_tt": collision_tt,
            })
    return events


def correlate(stack_log, monitor_json, prior_window_s=2.0,
              prediction_tolerance_s=1.0):
    unsafe = parse_unsafe_events(stack_log)
    with open(monitor_json) as stream:
        monitor = json.load(stream)
    contacts = [event for event in monitor.get("contact_events", [])
                if event.get("epoch_s") is not None]
    matches = []
    for contact in contacts:
        contact_epoch = float(contact["epoch_s"])
        candidates = [event for event in unsafe
                      if 0.0 <= contact_epoch - event["epoch_s"] <= prior_window_s]
        if not candidates:
            continue
        best = min(candidates, key=lambda event: abs(
            contact_epoch - event["predicted_contact_epoch_s"]))
        matches.append({
            "contact_epoch_s": contact_epoch,
            "contact_kind": contact.get("kind"),
            "segment": best["segment"],
            "status": best["status"],
            "warning_lead_s": contact_epoch - best["epoch_s"],
            "prediction_error_s": contact_epoch - best["predicted_contact_epoch_s"],
        })

    followed = 0
    for event in unsafe:
        if any(abs(float(contact["epoch_s"]) - event["predicted_contact_epoch_s"])
               <= prediction_tolerance_s for contact in contacts):
            followed += 1
    errors = [abs(match["prediction_error_s"]) for match in matches]
    return {
        "shadow_contact_events_with_epoch": len(contacts),
        "shadow_contacts_with_prior_unsafe": len(matches),
        "shadow_contacts_without_prior_unsafe": len(contacts) - len(matches),
        "shadow_geometric_unsafe_followed_by_contact": followed,
        "shadow_geometric_unsafe_not_followed_by_contact": len(unsafe) - followed,
        "shadow_nearest_prediction_error_s": min(errors) if errors else None,
        "shadow_correlated_segments": sorted({match["segment"] for match in matches}),
        "shadow_contact_matches": matches,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stack_log")
    parser.add_argument("monitor_json")
    parser.add_argument("--prior-window-s", type=float, default=2.0)
    parser.add_argument("--prediction-tolerance-s", type=float, default=1.0)
    parser.add_argument("--out")
    args = parser.parse_args()
    result = correlate(args.stack_log, args.monitor_json,
                       args.prior_window_s, args.prediction_tolerance_s)
    text = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, "w") as stream:
            stream.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
