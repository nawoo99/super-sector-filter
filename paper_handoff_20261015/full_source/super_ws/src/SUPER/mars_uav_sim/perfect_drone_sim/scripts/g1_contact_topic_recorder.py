#!/usr/bin/env python3
"""Bounded, external, logging-only observer for one G1 contact diagnostic.

Callbacks enqueue references without file I/O. A separate writer retains full
ROS message fields, including all polynomial coefficients; heartbeat messages
never replace earlier trajectories. This observer publishes no control input.
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import queue
import signal
import threading
import time


TOPICS = {
    "/lidar_slam/odom": "odometry.jsonl",
    "/planning/pos_cmd": "position_commands.jsonl",
    "/planning_cmd/poly_traj": "polynomial_trajectories.jsonl",
}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_message(value, nonfinite_paths=None, path="message"):
    """Serialize ROS slots recursively without importing ROS in offline tests."""
    nonfinite_paths = [] if nonfinite_paths is None else nonfinite_paths
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        nonfinite_paths.append(path)
        return "NaN" if math.isnan(value) else "Infinity" if value > 0 else "-Infinity"
    if hasattr(value, "get_fields_and_field_types"):
        return {name: json_message(getattr(value, name), nonfinite_paths, path + "." + name)
                for name in value.get_fields_and_field_types()}
    if isinstance(value, dict):
        return {str(k): json_message(v, nonfinite_paths, path + "." + str(k))
                for k, v in value.items()}
    if isinstance(value, (list, tuple, array)):
        return [json_message(v, nonfinite_paths, f"{path}[{i}]") for i, v in enumerate(value)]
    # Some generated ROS array fields are NumPy arrays/scalars.
    if hasattr(value, "tolist"):
        return json_message(value.tolist(), nonfinite_paths, path)
    raise TypeError("Unsupported ROS field type: " + type(value).__name__)


def classify_polynomial(message):
    kind = message.get("type", 0)
    position_flag = isinstance(kind, int) and bool(kind & 2)
    yaw_flag = isinstance(kind, int) and bool(kind & 4)
    has_position = position_flag and message.get("piece_num_pos", 0) > 0
    has_yaw = yaw_flag and message.get("piece_num_yaw", 0) > 0
    lengths_valid = True
    if position_flag:
        pieces, order = message.get("piece_num_pos", 0), message.get("order_pos", -1)
        lengths_valid = (type(pieces) is int and pieces > 0 and type(order) is int and order >= 0
                         and len(message.get("time_pos", [])) == pieces
                         and all(len(message.get(k, [])) == pieces * (order + 1)
                                 for k in ("coef_pos_x", "coef_pos_y", "coef_pos_z")))
    if yaw_flag:
        pieces, order = message.get("piece_num_yaw", 0), message.get("order_yaw", -1)
        lengths_valid = lengths_valid and (
            type(pieces) is int and pieces > 0 and type(order) is int and order >= 0
            and len(message.get("time_yaw", [])) == pieces
            and len(message.get("coef_yaw", [])) == pieces * (order + 1))
    return dict(kind="full_polynomial" if has_position or has_yaw else "heartbeat_only"
                if isinstance(kind, int) and kind & 1 and not position_flag and not yaw_flag
                else "other_or_empty_polynomial",
                coefficient_lengths_valid=bool(lengths_valid),
                emergency=bool(isinstance(kind, int) and kind & 16),
                trajectory_id=message.get("trajectory_id"),
                trajectory_generation=message.get("trajectory_generation"),
                start_wt_pos=message.get("start_wt_pos"),
                start_wt_yaw=message.get("start_wt_yaw"))


class Recorder:
    def __init__(self, output, *, max_bytes=128 * 1024 * 1024, queue_capacity=4096):
        if type(max_bytes) is not int or max_bytes < 1 or type(queue_capacity) is not int or queue_capacity < 1:
            raise ValueError("Positive bounded byte and queue budgets required")
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=False)
        self.queue = queue.Queue(maxsize=queue_capacity)
        self.max_bytes = max_bytes
        self.lock = threading.Lock()
        self.closing = threading.Event()
        self.started_monotonic_ns = time.monotonic_ns()
        self.started_epoch_ns = time.time_ns()
        self.next_sequence = 0
        self.stats = {topic: Counter() for topic in TOPICS}
        self.last_header = {}
        self.total_bytes = 0
        self.writer_error = None
        self.last_full_polynomial = None
        self.thread = threading.Thread(target=self._write, name="g1-diagnostic-json-writer", daemon=True)
        self.thread.start()

    def submit(self, topic, message):
        """No serialization, file writes, or waiting for free queue capacity."""
        if topic not in self.stats:
            raise ValueError("Unknown diagnostic topic")
        receipt_monotonic_ns, receipt_epoch_ns = time.monotonic_ns(), time.time_ns()
        header_ns = None
        if hasattr(message, "header") and hasattr(message.header, "stamp"):
            header_ns = int(message.header.stamp.sec) * 1000000000 + int(message.header.stamp.nanosec)
        with self.lock:
            self.next_sequence += 1
            sequence = self.next_sequence
            stats = self.stats[topic]
            stats["received"] += 1
            if header_ns is None:
                stats["missing_header_stamp"] += 1
            elif topic in self.last_header:
                delta = header_ns - self.last_header[topic]
                stats["repeated_header_stamps"] += int(delta == 0)
                stats["backward_header_stamps"] += int(delta < 0)
                stats["max_header_interval_ns"] = max(stats["max_header_interval_ns"], delta)
            if header_ns is not None:
                self.last_header[topic] = header_ns
            if self.closing.is_set():
                stats["dropped_after_close"] += 1
                return False
            envelope = dict(sequence=sequence, topic=topic, header_ns=header_ns,
                            receipt_monotonic_ns=receipt_monotonic_ns, receipt_epoch_ns=receipt_epoch_ns)
            try:
                self.queue.put_nowait((envelope, message))
            except queue.Full:
                stats["dropped_queue_full"] += 1
                return False
            stats["enqueued"] += 1
            stats["queue_high_watermark"] = max(stats["queue_high_watermark"], self.queue.qsize())
        return True

    def middleware_lost(self, topic, count):
        with self.lock:
            self.stats[topic]["middleware_lost_notifications"] += 1
            self.stats[topic]["middleware_reported_lost_messages"] += int(count)

    def _write(self):
        streams = {}
        try:
            streams = {topic: (self.output / filename).open("xb") for topic, filename in TOPICS.items()}
            last_flush = time.monotonic()
            while not self.closing.is_set() or not self.queue.empty():
                try:
                    envelope, message = self.queue.get(timeout=.1)
                except queue.Empty:
                    if time.monotonic() - last_flush >= .5:
                        for stream in streams.values():
                            stream.flush()
                        last_flush = time.monotonic()
                    continue
                topic = envelope["topic"]
                try:
                    nonfinite_paths = []
                    envelope["message"] = json_message(message, nonfinite_paths)
                    envelope["nonfinite_field_paths"] = nonfinite_paths
                    if topic == "/planning_cmd/poly_traj":
                        envelope["polynomial"] = classify_polynomial(envelope["message"])
                    payload = (json.dumps(envelope, separators=(",", ":"), allow_nan=False) + "\n").encode()
                    with self.lock:
                        exceeds_budget = self.total_bytes + len(payload) > self.max_bytes
                        if exceeds_budget:
                            self.stats[topic]["dropped_byte_budget"] += 1
                    if not exceeds_budget:
                        streams[topic].write(payload)
                        with self.lock:
                            self.total_bytes += len(payload)
                            stats = self.stats[topic]
                            stats["written"] += 1
                            stats["written_bytes"] += len(payload)
                            stats["messages_with_nonfinite_fields"] += bool(nonfinite_paths)
                            if "polynomial" in envelope:
                                info = envelope["polynomial"]
                                stats[info["kind"]] += 1
                                stats["invalid_polynomial_lengths"] += not info["coefficient_lengths_valid"]
                                if info["kind"] == "full_polynomial":
                                    self.last_full_polynomial = dict(info, sequence=envelope["sequence"],
                                                                    header_ns=envelope["header_ns"])
                except Exception as error:
                    with self.lock:
                        self.stats[topic]["serialization_or_write_errors"] += 1
                        self.writer_error = repr(error)
                finally:
                    self.queue.task_done()
                if time.monotonic() - last_flush >= .5:
                    for stream in streams.values():
                        stream.flush()
                    last_flush = time.monotonic()
        except Exception as error:
            with self.lock:
                self.writer_error = repr(error)
        finally:
            for stream in streams.values():
                stream.close()

    def close(self, reason="requested_stop", timeout_s=10.):
        self.closing.set()
        self.thread.join(timeout_s)
        with self.lock:
            keys = ("received", "enqueued", "written", "written_bytes", "dropped_queue_full",
                    "dropped_byte_budget", "dropped_after_close", "serialization_or_write_errors",
                    "missing_header_stamp", "repeated_header_stamps", "backward_header_stamps",
                    "max_header_interval_ns", "queue_high_watermark", "middleware_lost_notifications",
                    "middleware_reported_lost_messages", "messages_with_nonfinite_fields",
                    "full_polynomial", "heartbeat_only", "other_or_empty_polynomial", "invalid_polynomial_lengths")
            topics = {topic: {key: counts[key] for key in keys} for topic, counts in self.stats.items()}
            result = dict(schema="g1-contact-topic-recorder-v1", started_epoch_ns=self.started_epoch_ns,
                finished_epoch_ns=time.time_ns(), elapsed_s=(time.monotonic_ns()-self.started_monotonic_ns)/1e9,
                stop_reason=reason, writer_stopped=not self.thread.is_alive(), writer_error=self.writer_error,
                queue_capacity=self.queue.maxsize, remaining_queue=self.queue.qsize(),
                max_jsonl_bytes=self.max_bytes, written_jsonl_bytes=self.total_bytes,
                topics=topics, last_full_polynomial=self.last_full_polynomial,
                observer_only=True, control_publishers=0,
                qos="best_effort/volatile/keep_last1000", all_received_messages_requested=True,
                loss_scope="Local queue/budget/serialization and reported DDS loss only; unseen network/publisher losses are not measurable here",
                coefficient_order="Original message arrays unchanged; per segment descending polynomial powers as published by SUPER",
                nonfinite_encoding="NaN/Infinity/-Infinity strings with explicit field paths")
            result["local_retention_complete"] = (
                result["writer_stopped"] and self.writer_error is None and self.queue.empty()
                and all(c["received"] == c["written"] for c in topics.values()))
        try:
            result["process_cgroup_membership"] = Path("/proc/self/cgroup").read_text()
            result["diagnostic_cpu_excluded_from_experiment_cgroup"] = (
                "super_sector_filter_" not in result["process_cgroup_membership"])
        except OSError:
            result["process_cgroup_membership"] = None
            result["diagnostic_cpu_excluded_from_experiment_cgroup"] = None
        files = {}
        if result["writer_stopped"]:
            for filename in TOPICS.values():
                path = self.output / filename
                if path.exists():
                    files[filename] = dict(bytes=path.stat().st_size, sha256=sha256_file(path))
        result["files"] = files
        with (self.output / "summary.json").open("x") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration-s", type=float, default=240.)
    parser.add_argument("--max-mib", type=int, default=128)
    parser.add_argument("--queue-capacity", type=int, default=4096)
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration_s) or not 0 < args.duration_s <= 3600:
        parser.error("--duration-s must be finite and in (0,3600]")
    if not 1 <= args.max_mib <= 1024 or not 1 <= args.queue_capacity <= 20000:
        parser.error("--max-mib in1..1024 and --queue-capacity in1..20000 required")
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
    from rclpy.qos_event import SubscriptionEventCallbacks
    from rclpy.signals import SignalHandlerOptions
    from nav_msgs.msg import Odometry
    from mars_quadrotor_msgs.msg import PositionCommand, PolynomialTrajectory

    recorder = Recorder(args.output, max_bytes=args.max_mib * 1024 * 1024,
                        queue_capacity=args.queue_capacity)
    stop = threading.Event()
    reason = ["duration_elapsed"]
    def request_stop(signum, _frame):
        reason[0] = "signal_" + str(signum)
        stop.set()
    previous = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    node = None
    result = None
    try:
        rclpy.init(args=[], signal_handler_options=SignalHandlerOptions.NO)
        node = rclpy.create_node("g1_contact_topic_recorder")
        qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1000,
                         reliability=ReliabilityPolicy.BEST_EFFORT, durability=DurabilityPolicy.VOLATILE)
        for topic, message_type in zip(TOPICS, (Odometry, PositionCommand, PolynomialTrajectory)):
            callbacks = SubscriptionEventCallbacks(message_lost=lambda info, t=topic:
                                                   recorder.middleware_lost(t, info.total_count_change))
            node.create_subscription(message_type, topic, lambda message, t=topic: recorder.submit(t, message),
                                     qos, event_callbacks=callbacks)
        with (args.output / "ready.json").open("x") as stream:
            json.dump(dict(ready=True, pid=__import__('os').getpid(), topics=TOPICS,
                           observer_only=True, epoch_ns=time.time_ns()), stream, indent=2)
        deadline = time.monotonic() + args.duration_s
        while not stop.is_set() and time.monotonic() < deadline and rclpy.ok():
            rclpy.spin_once(node, timeout_sec=.1)
    except BaseException as error:
        reason[0] = "exception: " + repr(error)
        raise
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        result = recorder.close(reason[0])
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        print(json.dumps({"output": str(args.output), "local_retention_complete": result["local_retention_complete"],
                          "topics": result["topics"]}), flush=True)


if __name__ == "__main__":
    main()
