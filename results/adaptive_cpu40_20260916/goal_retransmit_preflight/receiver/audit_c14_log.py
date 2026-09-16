#!/usr/bin/env python3
"""Light, read-only C14 explicit-goal protocol log audit (not safety proof)."""
import collections
import json
import re
import sys


def audit(path):
    producer = []
    coalesced = []
    accepted = []
    certificates = {}
    all_certificates = collections.defaultdict(list)
    commits = []
    successful_replans = 0
    latest_demand = None
    latest_cpu = {}
    for line_no, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        fields = dict(re.findall(r"([A-Za-z_]+)=([^\s,]+)", line))
        if "[MISSION_GOAL_IDENTITY]" in line:
            producer.append({"line": line_no, **{key: int(fields[key]) for key in (
                "stamp_ns", "new_intent", "new_identity", "supported", "waypoint")}})
        if "[TRAJ_GUARD_CERT]" in line:
            key = (int(fields["gen"]), int(fields["map"]))
            item = {"line": line_no, "status": fields["status"], "trigger": fields["trigger"]}
            certificates[key] = item
            all_certificates[key].append(item)
        if "[GOAL_RETRANSMIT_COALESCED]" in line:
            item = {"line": line_no, **{key: int(fields[key]) for key in (
                "stamp_ns", "generation", "map", "queued_revision", "accepted_revision", "coalesced_total")}}
            source = next((event for event in reversed(producer)
                           if event["stamp_ns"] == item["stamp_ns"]), None)
            item["prior_producer"] = source
            item["preceding_exact_certificate"] = certificates.get((item["generation"], item["map"]))
            coalesced.append(item)
        if "Receive click goal at:" in line:
            match = re.search(r"goal at:\s*\[([^]]+)\]", line)
            accepted.append({"line": line_no, "point": tuple(float(x) for x in match.group(1).split())})
        if "[TRAJ_GUARD_COMMIT]" in line:
            commits.append({"line": line_no, "phase": fields["phase"], "generation": int(fields["gen"])})
        if "ReplanOnce succeed." in line:
            successful_replans += 1
        if "[DEMAND_REPLAN]" in line:
            latest_demand = {key: fields[key] for key in ("checks", "skips", "renewals", "reason")}
        if "[THREAD_CPU_PROFILE]" in line:
            latest_cpu[fields["stage"]] = int(fields["calls"])

    protocol_errors = []
    prior_queued = prior_accepted = 0
    missing_cert = []
    by_waypoint = collections.Counter()
    nearby_exact_safe = 0
    no_nearby_exact_safe = []
    for index, item in enumerate(coalesced, 1):
        source = item["prior_producer"]
        if source is None or source["supported"] != 1 or source["new_identity"] != 0 or source["new_intent"] != 0:
            protocol_errors.append({"line": item["line"], "error": "missing preceding supported retransmission"})
        else:
            by_waypoint[source["waypoint"]] += 1
        if item["coalesced_total"] != index:
            protocol_errors.append({"line": item["line"], "error": "counter not contiguous"})
        if (min(item[key] for key in ("stamp_ns", "generation", "map", "queued_revision", "accepted_revision")) <= 0
                or item["queued_revision"] < prior_queued or item["accepted_revision"] < prior_accepted):
            protocol_errors.append({"line": item["line"], "error": "invalid/nonmonotonic identity metadata"})
        prior_queued, prior_accepted = item["queued_revision"], item["accepted_revision"]
        cert = item["preceding_exact_certificate"]
        if cert is None:
            missing_cert.append({"line": item["line"], "generation": item["generation"], "map": item["map"]})
        elif cert["status"] != "SAFE":
            protocol_errors.append({"line": item["line"], "error": "preceding exact certificate not SAFE", "certificate": cert})
        matching = all_certificates.get((item["generation"], item["map"]), [])
        nearest = min(matching, key=lambda x: abs(x["line"] - item["line"]), default=None)
        if nearest is not None and nearest["status"] == "SAFE" and abs(nearest["line"] - item["line"]) <= 30:
            nearby_exact_safe += 1
        else:
            no_nearby_exact_safe.append({"line": item["line"], "generation": item["generation"],
                                         "map": item["map"], "nearest_exact_certificate": nearest})

    return {
        "path": path,
        "producer_publications": len(producer),
        "producer_new_identities": sum(x["new_identity"] == 1 for x in producer),
        "producer_retransmissions": sum(x["new_identity"] == 0 for x in producer),
        "producer_distinct_ids": len({x["stamp_ns"] for x in producer}),
        "accepted_goal_logs": len(accepted),
        "accepted_distinct_mapped_points": len({x["point"] for x in accepted}),
        "coalesced_count": len(coalesced),
        "coalesced_by_waypoint": dict(sorted(by_waypoint.items())),
        "coalesced_preceding_exact_safe_certificates": sum(
            item["preceding_exact_certificate"] is not None and item["preceding_exact_certificate"]["status"] == "SAFE"
            for item in coalesced),
        "no_preceding_exact_certificate_log": missing_cert,
        "nearby_exact_safe_certificates_within_30_lines": nearby_exact_safe,
        "no_nearby_exact_safe_certificate_log": no_nearby_exact_safe,
        "successful_replan_logs": successful_replans,
        "ordinary_replan_commit_logs": sum(x["phase"].startswith("ReplanOnce/") for x in commits),
        "all_commit_logs": len(commits),
        "latest_periodic_demand": latest_demand,
        "last_profile_replan_core_calls": latest_cpu.get("fsm_replan_core"),
        "protocol_errors": protocol_errors,
        "last_coalesced": coalesced[-1] if coalesced else None,
    }


if __name__ == "__main__":
    print(json.dumps([audit(path) for path in sys.argv[1:]], indent=2))
