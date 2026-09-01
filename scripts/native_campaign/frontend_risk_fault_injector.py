#!/usr/bin/env python3
"""Inject one bounded front-end risk verdict for enforcement fault gates."""

import argparse
import time

import rclpy
from mars_quadrotor_msgs.msg import PolynomialTrajectory, TrajectoryRiskVerdict
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy


class FaultInjector(Node):
    def __init__(self, mode: str, delay_s: float) -> None:
        super().__init__("frontend_risk_fault_injector")
        self.mode = mode
        self.delay_s = delay_s
        self.latest_trajectory = None
        trajectory_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=4,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        verdict_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=4,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.create_subscription(
            PolynomialTrajectory,
            "/planning_cmd/poly_traj",
            self._trajectory_callback,
            trajectory_qos,
        )
        self.publisher = self.create_publisher(
            TrajectoryRiskVerdict,
            "/planning/trajectory_risk_verdict",
            verdict_qos,
        )

    def _trajectory_callback(self, msg: PolynomialTrajectory) -> None:
        # The full polynomial is transient only, while 100 Hz heartbeats carry
        # the same exact generation without coefficient arrays. Generation and
        # start time are sufficient for this validator fault injection.
        if msg.trajectory_generation:
            self.latest_trajectory = msg

    def wait_and_publish(self, timeout_s: float) -> None:
        deadline = time.monotonic() + timeout_s
        while rclpy.ok() and self.latest_trajectory is None:
            if time.monotonic() >= deadline:
                raise TimeoutError("no committed polynomial trajectory received")
            rclpy.spin_once(self, timeout_sec=0.05)

        time.sleep(self.delay_s)
        for _ in range(5):
            rclpy.spin_once(self, timeout_sec=0.02)
        trajectory = self.latest_trajectory
        now = self.get_clock().now()
        stamp_ns = now.nanoseconds
        if self.mode == "stale":
            stamp_ns -= 1_000_000_000

        verdict = TrajectoryRiskVerdict()
        verdict.header.stamp.sec = stamp_ns // 1_000_000_000
        verdict.header.stamp.nanosec = stamp_ns % 1_000_000_000
        verdict.request_id = 9_000_000_000
        verdict.trajectory_generation = trajectory.trajectory_generation
        if self.mode == "wrong-generation":
            verdict.trajectory_generation += 1_000_000
        verdict.cloud_sequence = 9_000_000_000
        verdict.source_cloud_stamp_ns = now.nanoseconds
        verdict.status = TrajectoryRiskVerdict.OCCUPIED
        verdict.trajectory_start_wt = trajectory.start_wt_pos
        verdict.checked_from_tt = 0.0
        verdict.checked_to_tt = 1.0e6
        verdict.witness_tt = max(
            0.0, now.nanoseconds * 1.0e-9 - trajectory.start_wt_pos
        )
        verdict.minimum_distance_m = 0.0
        verdict.body_distance_m = 0.0
        verdict.end_distance_m = 0.0
        verdict.source_point_count = 1
        verdict.cropped_point_count = 1
        verdict.source_cloud_age_s = 0.0
        verdict.compute_ms = 0.0

        # Repeat briefly so discovery timing cannot turn this test into a
        # false pass. Identical request IDs still represent one fault edge.
        for _ in range(3):
            self.publisher.publish(verdict)
            rclpy.spin_once(self, timeout_sec=0.05)
        print(
            "FRONTEND_RISK_FAULT_INJECTOR "
            f"mode={self.mode} request={verdict.request_id} "
            f"generation={verdict.trajectory_generation}",
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=("wrong-generation", "stale", "fresh"), required=True
    )
    parser.add_argument("--delay-s", type=float, default=1.0)
    parser.add_argument("--timeout-s", type=float, default=20.0)
    args = parser.parse_args()
    if args.delay_s < 0.0 or args.timeout_s <= 0.0:
        parser.error("delay must be non-negative and timeout must be positive")

    rclpy.init()
    node = FaultInjector(args.mode, args.delay_s)
    try:
        node.wait_and_publish(args.timeout_s)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
