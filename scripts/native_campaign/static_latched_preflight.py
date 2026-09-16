#!/usr/bin/env python3
"""Offline, hash-bound acceptance of the C18 static-map publisher/reader contract.

This validates no-flight transport and actual-RViz evidence; it is not flight,
safety, CPU-saving, or persistent-across-publisher-restart certification.
No ROS imports, subprocesses, environment overrides, or simulator writes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

SCHEMA = "static-latched-contract-v1"
EXPECTED_SHA256 = "b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f"
EXPECTED_POINTS = 241490
EXPECTED_BYTES = 7727680
EXPECTED_GEOMETRY = {"sha256": EXPECTED_SHA256, "points": EXPECTED_POINTS,
                     "bytes": EXPECTED_BYTES, "point_step": 32, "frame": "world"}
PAIRS = {(mode, sequence) for mode in ("standalone", "full", "adaptive")
         for sequence in ("reader-first", "late")}
VIEWS = ("watch_sector", "top_down", "fpv", "benchmark")
RUNTIME = Path("/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim")
INSTALL = Path("/root/super_ws/install/perfect_drone_sim")
EXECUTABLES = {"standalone": "perfect_drone_node", "full": "perfect_drone_full_node",
               "adaptive": "perfect_drone_adaptive_node"}
BINDING_PATHS = {
    "planner_async_recovery_policy": Path('/root/super_ws/src/SUPER/super_planner/include/fsm/async_certified_recovery.hpp'),
    "planner_fsm_source": Path('/root/super_ws/src/SUPER/super_planner/include/ros_interface/ros2/fsm_ros2.hpp'),
    "frontend_component": Path('/root/super_ws/install/mission_planner/lib/libnative_sector_cpp_component.so'),
    "frontend_source": Path('/root/super_ws/src/SUPER/mission_planner/Apps/native_sector_cpp.cpp'),
    "frontend_heading_policy": Path('/root/super_ws/src/SUPER/mission_planner/include/mission_planner/sector_heading_policy.hpp'),
    "runtime_model": RUNTIME / "include/perfect_drone_sim/ros2_perfect_drone_model.hpp",
    "runtime_latched_policy": RUNTIME / "include/perfect_drone_sim/static_pc_latched_policy.hpp",
    "runtime_durable_policy": RUNTIME / "include/perfect_drone_sim/static_pc_durable_policy.hpp",
    "seed1_config": RUNTIME / "config/seed1.yaml",
    "seed1_pcd": RUNTIME / "pcd/seed_maps/seed1.pcd",
    "runtime_view_launcher": RUNTIME / "launch/static_map_view.launch.py",
    "installed_view_launcher": INSTALL / "share/perfect_drone_sim/launch/static_map_view.launch.py",
    **{f"binary_{mode}": INSTALL / "lib/perfect_drone_sim" / name
       for mode, name in EXECUTABLES.items()},
    **{f"runtime_view_{view}": RUNTIME / f"rviz2/{view}_durable.rviz" for view in VIEWS},
    **{f"installed_view_{view}": INSTALL / f"share/perfect_drone_sim/rviz2/{view}_durable.rviz"
       for view in VIEWS},
}
COUNTER_KEYS = ("publications", "points", "bytes", "stamp_ns", "timers_created", "poll_callbacks")
AUDIT_CHECKS = ("complete_geometry", "exact_sha256", "all_readers_same_stamp",
                "publication_count_one", "no_static_timers", "no_static_poll_callbacks",
                "cumulative_summaries_steady_at_least5s")
QOS = {"reliability": "reliable", "durability": "transient_local", "history": "keep_last", "depth": 1}

# Independent canonical XYZI expectations derived from the frozen ASCII XYZ
# backgrounds (xyz, homogeneous1, missing intensity0, zero tail padding).
# Each must ALSO pass actual six-arm DDS and actual RViz verification.
MAP_GEOMETRIES = {
    'seed1': (241490, EXPECTED_SHA256),
    'seed3': (444850, 'e4713ddd834a41adeabb3c3a535746a5e51cfb9917705fb47942b4f06f4ec1fd'),
    'seed5': (635500, 'b0fdf7706d62e21549124ca552a25e8db43155061413bf76d66480269159d982'),
    'seed7': (838860, 'b33865379ffd5a318ef79d5a89fd2148b9da8b50c6853d62ccfb2e99d7ec9802'),
    'seed9': (1042220, '3c0efe025ec5ba6335ade66ec19e3609575f7fbb098b95a205ea2a4a47491fd4'),
}


def map_context(map_name='seed1'):
    if map_name not in MAP_GEOMETRIES:
        raise ValueError('Unsupported frozen Normal map: ' + map_name)
    points, digest = MAP_GEOMETRIES[map_name]
    paths = dict(BINDING_PATHS)
    if map_name != 'seed1':
        paths.pop('seed1_config')
        paths.pop('seed1_pcd')
        paths[map_name + '_config'] = RUNTIME / 'config' / (map_name + '.yaml')
        paths[map_name + '_pcd'] = RUNTIME / 'pcd/seed_maps' / (map_name + '.pcd')
    return dict(map=map_name, geometry=dict(sha256=digest, points=points,
                bytes=points * 32, point_step=32, frame='world'), paths=paths)


def spec(context):
    # Preserve existing seed1 fixtures/legacy evidence without mutable globals
    # for new maps; callers carry explicit independent contexts.
    return context if context is not None else dict(map='seed1', geometry=EXPECTED_GEOMETRY, paths=BINDING_PATHS)


class InvalidEvidence(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidEvidence(message)


def integer(value: Any, name: str, *, allow_string: bool = False) -> int:
    if allow_string and isinstance(value, str) and re.fullmatch(r"-?\d+", value):
        return int(value)
    require(type(value) is int, f"{name}: integer required (not bool/float)")
    return value


def number(value: Any, name: str) -> float:
    require(type(value) in (int, float) and math.isfinite(value), f"{name}: finite number required")
    return float(value)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _unique_object(items: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in items:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(), object_pairs_hook=_unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          InvalidEvidence(f"invalid JSON number: {value}")))
    require(type(data) is dict, f"JSON object required: {path}")
    return data


def file_record(path: Path) -> dict:
    path = path.resolve(strict=True)
    require(path.is_file(), f"not a regular file: {path}")
    return {"path": str(path), "sha256": file_sha256(path)}


def checked_file(record: Any, *, expected_path: Path | None = None) -> Path:
    require(type(record) is dict and set(record) == {"path", "sha256"}, "invalid file binding")
    require(isinstance(record["path"], str) and Path(record["path"]).is_absolute(), "absolute file path required")
    path = Path(record["path"]).resolve(strict=True)
    if expected_path is not None:
        require(path == expected_path.resolve(strict=True), f"unexpected bound path: {path}")
    require(path.is_file() and re.fullmatch(r"[a-f0-9]{64}", record["sha256"] or "") is not None,
            f"invalid file/hash: {path}")
    require(file_sha256(path) == record["sha256"], f"hash mismatch: {path}")
    return path


def records(text: str, marker: str) -> list[dict]:
    result = []
    for line in text.splitlines():
        if marker not in line:
            continue
        prefix, body = line.split(marker, 1)
        values = dict(re.findall(r"(\w+)=([^\s]+)", body))
        stamps = re.findall(r"\[(\d+)\.(\d{1,9})\]", prefix)
        if stamps:
            sec, fraction = stamps[-1]
            values["_log_stamp_ns"] = int(sec) * 10**9 + int(fraction.ljust(9, "0"))
        result.append(values)
    return result


def counters(record: dict, *, strings: bool = False, context=None) -> dict:
    require(type(record) is dict, "counter object required")
    result = {key: integer(record.get(key), key, allow_string=strings) for key in COUNTER_KEYS}
    require(result["publications"] == 1 and result["timers_created"] == 0 and result["poll_callbacks"] == 0,
            "one publication and zero timers/polls required")
    geometry = spec(context)['geometry']
    require(result["points"] == geometry['points'] and result["bytes"] == geometry['bytes'] and result["stamp_ns"] > 0,
            "unexpected static geometry or nonpositive test timestamp")
    return result


def audit_log(path: Path, context=None) -> dict:
    text = path.read_text(errors="strict")
    initial = records(text, "[STATIC_PC_LATCHED_PUBLICATION]")
    summaries = records(text, "[STATIC_PC_LATCHED_SUMMARY]")
    require(len(initial) == 1 and len(summaries) >= 2, "need exactly one publication and >=2 summaries")
    base = counters(initial[0], strings=True, context=context)
    require(initial[0].get("complete_geometry") == "1", "complete-geometry marker absent")
    require(all(item.get("enabled") == "1" and counters(item, strings=True, context=context) == base for item in summaries),
            "cumulative publisher evidence changed")
    stamps = [integer(item.get("_log_stamp_ns"), "summary timestamp") for item in summaries]
    require(all(b >= a for a, b in zip(stamps, stamps[1:])), "summary clock moved backwards")
    span = (stamps[-1] - stamps[0]) / 1e9
    require(span >= 5, "steady summaries span less than5s")
    require("[STATIC_PC_PUBLICATION]" not in text and "Publish global map size:" not in text,
            "legacy static publication also ran")
    poll = records(text, "[STATIC_PC_POLL_SETTINGS]")
    padding = records(text, "[STATIC_PC_LATCHED_SERIALIZATION]")
    require(len(padding) == 1 and all(padding[0].get(k) == v for k, v in {
        "point_step": "32", "tail_zeroed_bytes": "12",
        "declared_fields_and_homogeneous_bytes_unchanged": "1"}.items()),
        "deterministic wire padding not verified")
    require(len(poll) == 1 and poll[0].get("poll_ms") == "0" and poll[0].get("bootstrap_once") == "1",
            "effective static poll is not zero")
    qos = records(text, "[STATIC_PC_DURABLE_SETTINGS]")
    require(len(qos) == 1 and all(qos[0].get(key) == value for key, value in {
        "enabled": "1", "actual_qos": "1", "reliability": "reliable", "durability": "transient_local",
        "history": "keep_last", "depth": "1", "intra_process": "disabled", "publication_schedule": "latched_once"
    }.items()), "effective static QoS/schedule mismatch")
    cadence = records(text, "[SENSOR_CADENCE_SUMMARY]")
    require(bool(cadence), "source cadence evidence absent")
    require(all(math.isfinite(float(item["hz"])) for item in cadence), "nonfinite source cadence")
    require(9.5 <= float(cadence[-1]["hz"]) <= 10.5 and int(cadence[-1]["frames"]) >= 50,
            "source cadence not10Hz / fewer than50 frames")
    return {"counters": base, "summary_count": len(summaries), "steady_summary_span_s": span,
            "cadence_hz": float(cadence[-1]["hz"]), "last_summary": summaries[-1]}


def check_geometry(cloud: dict, baseline: dict, *, rviz: bool = False, context=None) -> None:
    require(type(cloud) is dict, "geometry object required")
    for key, expected in spec(context)['geometry'].items():
        value = cloud.get(key)
        if type(expected) is int:
            value = integer(value, f"geometry.{key}")
        require(value == expected, f"geometry.{key} mismatch")
    require(integer(cloud.get("stamp_ns"), "geometry.stamp_ns", allow_string=rviz) == baseline["stamp_ns"],
            "readers did not receive the one retained publication timestamp")


def check_layout(layout: dict, context=None) -> None:
    width = integer(layout.get("width"), "layout.width")
    height = integer(layout.get("height"), "layout.height")
    require(width > 0 and height > 0 and width * height == spec(context)['geometry']['points'], "layout point dimensions")
    require(integer(layout.get("point_step"), "layout.point_step") == 32 and
            integer(layout.get("row_step"), "layout.row_step") == width * 32, "layout byte dimensions")
    require(type(layout.get("is_bigendian")) is bool and type(layout.get("is_dense")) is bool, "layout flags")
    fields = layout.get("fields")
    require(type(fields) is list and len(fields) == 4, "expected XYZI fields")
    require(fields == [{"name": name, "offset": offset, "datatype": 7, "count": 1}
                       for name, offset in (("x", 0), ("y", 4), ("z", 8), ("intensity", 16))], "XYZI layout changed")


def no_error(result: dict) -> None:
    require(result.get("valid") is True, "evidence does not explicitly pass")
    require(not result.get("error") and not result.get("cleanup_error"), "error retained in passing evidence")


def check_command(command: Any, composition: str, bindings: dict, context=None) -> None:
    require(type(command) is list and all(isinstance(item, str) for item in command) and bool(command), "command absent")
    require(Path(command[0]).resolve() == Path(bindings[f"binary_{composition}"]["path"]).resolve(), "wrong simulator binary")
    config_arg = ('config_name:=' if composition == 'standalone' else 'drone_config:=') + spec(context)['map'] + '.yaml'
    require(config_arg in command, "not the required map configuration")


def validate_transport(result: dict, log: dict, bindings: dict, context=None) -> tuple[str, str]:
    geometry = spec(context)['geometry']
    no_error(result)
    pair = (result.get("composition"), result.get("sequence"))
    require(pair in PAIRS, "unexpected transport case")
    mode, sequence = pair
    for key, value in {"latched_once": True, "durable": True, "reader_qos": "durable", "poll_ms": 1,
                       "effective_poll_ms": 0, "two_phase": False, "fixture_publishes_no_goals_or_commands": True,
                       "exact_child_reaped": True, "expected_sha256": geometry['sha256']}.items():
        require(result.get(key) == value and type(result.get(key)) is type(value), f"transport.{key}")
    require(result.get("no_fsm") is (mode == "standalone"), "FSM scope mismatch")
    require(str(result.get("ros_domain_id")) == "190", "wrong isolated transport domain")
    require(integer(result.get("simulator_exit_code"), "simulator exit") == 0 and result.get("forced_cleanup", False) is False,
            "transport child cleanup not clean")
    check_command(result.get("command"), mode, bindings, context)
    require(result.get("publisher_actual_qos") == QOS, "transport publisher actual QoS")
    graph = result.get("graph_qos_verified", {})
    offered = result.get("offered_qos", {})
    require(graph.get("reliability") is True and graph.get("durability") is True and
            offered.get("reliability") == 1 and offered.get("durability") == 1, "transport offered QoS not proven")
    if graph.get("history") is True:
        require(offered.get("history") == 1, "known graph history mismatch")
    if graph.get("depth") is True:
        require(offered.get("depth") == 1, "known graph depth mismatch")
    audit = result.get("latched_once_audit", {})
    require(audit.get("valid") is True and all(audit.get("checks", {}).get(key) is True for key in AUDIT_CHECKS),
            "detailed transport audit absent or failed")
    require(counters(audit.get("initial"), context=context) == log["counters"], "audit/log counters mismatch")
    require(integer(audit.get("publication_count"), "publication_count") == 1 and
            integer(audit.get("summary_count"), "summary_count") == log["summary_count"], "audit/log counts mismatch")
    require(number(audit.get("observation_before_shutdown_s"), "observation") >= 5 and
            number(audit.get("steady_summary_span_s"), "summary span") == log["steady_summary_span_s"], "audit observation/span")
    for key in ("one_publication", "no_static_timers", "no_static_poll_callbacks", "all_readers_same_stamp"):
        require(audit.get(key) is True, f"audit.{key}")
    clouds = result.get("clouds", {})
    require(set(clouds) == {"first", "second", "reconnected"}, "missing or extra reader phase")
    for phase, samples in clouds.items():
        require(type(samples) is list and len(samples) == 1, f"{phase}: exactly one retained sample required")
        check_geometry(samples[0], log["counters"], context=context)
    require(result.get("geometry_sha256") == geometry['sha256'] and result.get("geometry_validated_clouds") == 3,
            "phase-local geometry validation incomplete")
    require(integer(result.get("latched_geometry_stamp_ns"), "retained timestamp") == log["counters"]["stamp_ns"], "retained timestamp mismatch")
    check_layout(result.get("geometry_layout", {}), context)
    phases = result.get("phases", [])
    required_phases = ["one_shot_geometry_published"] + (
        ["reader_first_static_geometry", "reader_first_steady_no_republish"] if sequence == "reader-first" else
        ["one_shot_without_subscribers", "late_subscriber_0_to_1"]) + [
        "subscriber_1_to_2", "subscriber_2_to_1_retained_without_republish", "subscriber_1_to_0_to_1"]
    require(phases == required_phases, "transport sequence evidence mismatch")
    if sequence == "reader-first":
        require(result.get("reader_first_geometry_valid") is True and result.get("reader_first_geometry_sha256") == geometry['sha256'],
                "reader-first geometry not independently validated")
    motion = result.get("no_flight_observation", {})
    require(integer(motion.get("command_messages"), "commands") == 0 and integer(motion.get("odom_messages"), "odom") >= 2,
            "no-flight command/odometry evidence")
    position = motion.get("initial_position")
    require(type(position) is list and len(position) == 3, "initial position absent")
    require(all(math.isfinite(number(v, "position")) for v in position), "invalid position")
    require(0 <= number(motion.get("max_position_delta_m"), "position delta") <= 1e-6, "fixture moved")
    first = integer(motion.get("first_odom_receipt_ns"), "first odom")
    require(first > 0 and integer(motion.get("last_odom_receipt_ns"), "last odom") > first, "odom interval absent")
    cadence = result.get("sensor_cadence_hz")
    require(type(cadence) is list and cadence and all(math.isfinite(number(v, "cadence")) for v in cadence), "cadence list absent")
    # Top-level cadence is collected before cleanup; the final raw-log summary
    # can legitimately add a later reading. Both must separately be in range.
    require(9.5 <= cadence[-1] <= 10.5, "transport cadence outside10Hz smoke bound")
    return pair


def validate_probe(probe: dict, baseline: dict, bindings: dict, context=None) -> None:
    geometry = spec(context)['geometry']
    require(probe.get("screenshot_method") == "rviz_render_window_capture",
            "actual Ogre render-target screenshot required, not QWidget capture")
    no_error(probe)
    require(probe.get("actual_rviz_display") is True and probe.get("extra_map_subscription") is False,
            "not a witness of the actual RViz display")
    require(integer(probe.get("rviz_received_messages"), "RViz messages") == 1 and
            integer(probe.get("own_global_pc_endpoints"), "RViz endpoints") == 1, "RViz reader count")
    require(probe.get("expected_sha256") == geometry['sha256'] and probe.get("expected_points") == geometry['points'],
            "RViz expected geometry mismatch")
    check_geometry(probe.get("geometry", {}), baseline, rviz=True, context=context)
    check_layout(probe["geometry"], context)
    require(probe.get("configured_reader_qos") == QOS, "RViz configured QoS")
    graph = probe.get("requested_qos_graph", {})
    require(graph.get("reliability") == 1 and graph.get("durability") == 1, "RViz actual requested QoS")
    if graph.get("history_known") is True:
        require(graph.get("history") == 1, "RViz known history")
    if graph.get("depth_known") is True:
        require(graph.get("depth") == 1, "RViz known depth")
    statuses = probe.get("display_statuses")
    require(type(statuses) is list and statuses and all(type(s) is dict and s.get("level") != 2 for s in statuses),
            "RViz status missing/error")
    require(any(s.get("name") == "Points" and s.get("level") == 0 and
                s.get('value') == f"Showing [{geometry['points']}] points from [1] messages"
                for s in statuses), "actual RViz complete Points status absent")
    configured_path = Path(probe.get("config", "")).resolve()
    accepted = [record for key, record in bindings.items() if key.startswith("installed_view_") and key != "installed_view_launcher"]
    require(any(configured_path == Path(record["path"]).resolve() and probe.get("config_sha256") == record["sha256"]
                for record in accepted), "RViz used unbound or modified config")


def validate_rviz(result: dict, log: dict, probes: dict, bindings: dict, context=None) -> None:
    geometry = spec(context)['geometry']
    no_error(result)
    require(result.get("schema") == "static-latched-rviz-v1", "wrong RViz evidence schema")
    for key in ("publisher_no_republish", "no_fsm", "no_goals_or_commands_published", "actual_rviz"):
        require(result.get(key) is True, f"RViz scope.{key}")
    require(integer(result.get("reader_restarts"), "reader restarts") == 1 and result.get("ros_domain_id") == 191,
            "RViz reconnect/domain proof")
    require(result.get("expected_sha256") == geometry['sha256'] and result.get("expected_points") == geometry['points'],
            "RViz expected reference mismatch")
    check_command(result.get("simulator_command"), "standalone", bindings, context)
    require(counters(result.get("publication_counters"), context=context) == log["counters"] and
            counters(result.get("latched_summary"), strings=True, context=context) == log["counters"], "RViz publication/log mismatch")
    require(number(result.get("steady_summary_span_s"), "RViz summary span") == log["steady_summary_span_s"] and
            number(result.get("observation_before_shutdown_s"), "RViz observation") >= 5, "RViz steady observation")
    for kind in ("viewer_cleanup", "simulator_cleanup"):
        cleanup = result.get(kind, {})
        require(cleanup.get("forced") is False and integer(cleanup.get("exit_code"), kind) == 0, f"{kind} not clean")
    require(result.get("phases") == ["one_shot_before_any_viewer", "late_actual_rviz_full_sha_display",
            "late_viewer_disconnected", "reconnected_actual_rviz_full_sha_display", "reconnected_viewer_disconnected"],
            "RViz phase sequence incomplete")
    expected_probes = []
    for phase in ("late", "reconnected"):
        require(result.get(phase) == probes[phase], f"{phase} embedded/external RViz evidence mismatch")
        validate_probe(probes[phase], log["counters"], bindings, context)
        expected_probes.append(dict(probes[phase], phase=phase))
    require(result.get("probes") == expected_probes, "RViz probes list mismatch")


def _validate_document(document: dict, context=None) -> dict:
    contract = spec(context)
    binding_paths = contract['paths']
    checks = {}
    errors = []
    evidence_hashes = {}
    runtime_hashes = {}

    def check(label, function):
        try:
            value = function()
            checks[label] = True
            return value
        except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as error:
            checks[label] = False
            errors.append(f"{label}: {error}")
            return None

    check("schema", lambda: require(document.get("schema") == SCHEMA, "unsupported schema"))
    check("map", lambda: require(document.get('map', 'seed1') == contract['map'], 'map identity mismatch'))
    check("expected_geometry", lambda: require(document.get("expected_geometry") == contract['geometry'], "reference geometry changed"))
    bindings = document.get("bindings", {})
    check("binding_inventory", lambda: require(type(bindings) is dict and set(bindings) == set(binding_paths), "missing/extra bound runtime artifacts"))
    if type(bindings) is not dict:
        bindings = {}
    for name, expected_path in binding_paths.items():
        path = check(f"binding:{name}", lambda name=name, expected_path=expected_path:
                     checked_file(bindings.get(name), expected_path=expected_path))
        if path:
            runtime_hashes[name] = bindings[name]["sha256"]
    for view in (*VIEWS, "launcher"):
        source = "runtime_view_launcher" if view == "launcher" else f"runtime_view_{view}"
        installed = "installed_view_launcher" if view == "launcher" else f"installed_view_{view}"
        check(f"installed_matches_source:{view}", lambda source=source, installed=installed:
              require(bindings[source]["sha256"] == bindings[installed]["sha256"], "installed reader differs from source"))

    transports = document.get("transports")
    check("six_transport_cases", lambda: require(type(transports) is list and len(transports) == 6, "exactly six transport records required"))
    seen = []
    seen_paths = []
    for index, record in enumerate(transports if type(transports) is list else []):
        def one_transport(record=record):
            result_path = checked_file(record["result"])
            log_path = checked_file(record["log"], expected_path=result_path.parent / "simulator.log")
            pair = validate_transport(read_json(result_path), audit_log(log_path, context), bindings, context)
            require(list(pair) == record.get("case"), "manifest case label differs from actual evidence")
            seen.append(pair)
            seen_paths.append(str(result_path))
            evidence_hashes[str(result_path)] = record["result"]["sha256"]
            evidence_hashes[str(log_path)] = record["log"]["sha256"]
        check(f"transport:{index}", one_transport)
    check("transport_case_coverage", lambda: require(len(seen) == 6 and set(seen) == PAIRS and len(set(seen_paths)) == 6,
                                                   "duplicate/missing transport case or evidence path"))

    def rviz_case():
        record = document["rviz"]
        path = checked_file(record["result"])
        log_path = checked_file(record["log"], expected_path=path.parent / "simulator.log")
        probes = {}
        require(set(record["probes"]) == {"late", "reconnected"}, "two RViz lifecycles required")
        for phase in ("late", "reconnected"):
            assets = record["probes"][phase]
            require(set(assets) == {"result", "screenshot", "log"}, "RViz assets incomplete")
            for kind, suffix in (("result", ".json"), ("screenshot", ".png"), ("log", ".log")):
                asset = checked_file(assets[kind], expected_path=path.parent / (phase + suffix))
                evidence_hashes[str(asset)] = assets[kind]["sha256"]
                if kind == "result":
                    probes[phase] = read_json(asset)
                elif kind == "screenshot":
                    with asset.open("rb") as stream:
                        require(stream.read(8) == b"\x89PNG\r\n\x1a\n" and asset.stat().st_size > 32, "RViz screenshot not PNG")
                    require(Path(probes[phase].get("screenshot", "")).resolve() == asset, "RViz screenshot path mismatch")
        validate_rviz(read_json(path), audit_log(log_path, context), probes, bindings, context)
        evidence_hashes[str(path)] = record["result"]["sha256"]
        evidence_hashes[str(log_path)] = record["log"]["sha256"]
    check("actual_rviz_late_reconnect", rviz_case)
    return {"valid": bool(checks) and all(checks.values()), "schema": SCHEMA, "checks": checks,
            "errors": errors, "evidence_sha256": evidence_hashes, "runtime_sha256": runtime_hashes,
            "scope": "No-flight transport and actual RViz reader migration; not flight/CPU/safety certification"}


def validate_manifest(path: str | Path, context=None) -> dict:
    """Return structured invalid on missing/malformed/tampered/stale evidence."""
    try:
        path = Path(path).resolve(strict=True)
        before = file_sha256(path)
        result = _validate_document(read_json(path), context)
        require(file_sha256(path) == before, "manifest changed during validation")
        result["manifest_sha256"] = before
        return result
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as error:
        return {"valid": False, "schema": SCHEMA, "checks": {"manifest_read": False},
                "errors": [str(error)], "manifest_sha256": None, "evidence_sha256": {}, "runtime_sha256": {}}


def create_manifest(transport_paths: list[str | Path], rviz_path: str | Path, output: str | Path, context=None) -> dict:
    output = Path(output)
    require(not output.exists(), f"refusing to overwrite manifest: {output}")
    transports = []
    for value in transport_paths:
        path = Path(value)
        data = read_json(path)
        transports.append({"case": [data.get("composition"), data.get("sequence")], "result": file_record(path),
                           "log": file_record(path.parent / "simulator.log")})
    rviz_path = Path(rviz_path)
    document = {"schema": SCHEMA, "created_utc": datetime.now(timezone.utc).isoformat(),
                "map": spec(context)['map'], "expected_geometry": spec(context)['geometry'],
                "bindings": {name: file_record(path) for name, path in spec(context)['paths'].items()},
                "transports": transports, "rviz": {"result": file_record(rviz_path),
                    "log": file_record(rviz_path.parent / "simulator.log"),
                    "probes": {phase: {kind: file_record(rviz_path.parent / (phase + suffix))
                                for kind, suffix in (("result", ".json"), ("screenshot", ".png"), ("log", ".log"))}
                               for phase in ("late", "reconnected")}}}
    validation = _validate_document(document, context)
    require(validation["valid"], "preflight rejected: " + "; ".join(validation["errors"]))
    # Exclusive creation is the final anti-overwrite guard; do not create dirs or
    # a misleading manifest at all when detailed evidence has failed validation.
    with output.open("x") as stream:
        json.dump(document, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return validate_manifest(output, context)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    create = commands.add_parser("create")
    create.add_argument("--transport", action="append", required=True, type=Path)
    create.add_argument("--rviz", required=True, type=Path)
    create.add_argument("--output", required=True, type=Path)
    create.add_argument('--map', choices=tuple(MAP_GEOMETRIES), default='seed1')
    validate = commands.add_parser("validate")
    validate.add_argument("path", type=Path)
    validate.add_argument('--map', choices=tuple(MAP_GEOMETRIES), default='seed1')
    args = parser.parse_args(argv)
    try:
        context = map_context(args.map)
        result = (create_manifest(args.transport, args.rviz, args.output, context) if args.action == "create"
                  else validate_manifest(args.path, context))
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {"valid": False, "schema": SCHEMA, "checks": {"create": False}, "errors": [str(error)]}
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
