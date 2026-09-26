#!/usr/bin/env python3
"""Read-only source contracts for the real ordinary async FSM wiring.

These supplement executable policy/interleaving tests and human lock review;
they are not ROS executor or physical hold integration tests.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FSM = (ROOT / "include/ros_interface/ros2/fsm_ros2.hpp").read_text()
BASE = (ROOT / "src/super_core/fsm.cpp").read_text()
HEADER = (ROOT / "include/fsm/fsm.h").read_text()


def body(text, signature):
    begin = text.index(signature)
    masked = re.sub(r'''//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*' ''',
                    lambda match: " " * len(match.group()), text, flags=re.S | re.X)
    brace = masked.index("{", begin)
    depth, end = 1, brace + 1
    while depth:
        depth += (masked[end] == "{") - (masked[end] == "}")
        end += 1
    return text[begin:end]


class SourceContracts(unittest.TestCase):
    def test_opt_in_and_legacy_hook(self):
        self.assertIn('std::getenv("SUPER_ASYNC_GENERATE_TRAJ")', FSM)
        self.assertIn("virtual bool dispatchGenerateTrajectoryAsync() { return false; }", HEADER)
        main = body(BASE, "void Fsm::callMainFsmOnce()")
        self.assertLess(main.index("if (dispatchGenerateTrajectoryAsync()) return;"),
                        main.index("planner_ptr_->PlanFromRest("))

    def test_worker_is_profiled_and_reserved(self):
        callback = body(FSM, "void replanTimerCallback()")
        self.assertLess(callback.index("Stage::FsmReplanCallback"),
                        callback.index("serviceAsyncGenerateTrajectory()"))
        self.assertLess(callback.index("serviceAsyncGenerateTrajectory()"),
                        callback.index("serviceAsyncCertifiedRecovery()"))
        worker = body(FSM, "bool serviceAsyncGenerateTrajectory()")
        self.assertIn("Stage::FsmReplanCore", worker)
        self.assertIn("planner_ptr_->PlanFromRest(", worker)
        self.assertIn("recordLatestReplanLog()", worker)
        for forbidden in ("mpc_cmd_pub_->publish", "cmd_pub_->publish", "ChangeState(",
                          "gi_.new_goal =", "clearAsyncGenerateQuarantineLocked()"):
            self.assertNotIn(forbidden, worker)

    def test_main_drains_even_after_brake_and_avoids_cache_writer(self):
        self.assertIn("refreshMainRobotState();", body(BASE, "void Fsm::callMainFsmOnce()"))
        refresh = body(FSM, "void refreshMainRobotState() override")
        self.assertIn("async_generate_quarantine_.load", refresh)
        self.assertIn("robot_state_ = map_ptr_->getRobotState();", refresh)
        main = body(FSM, "void mainFsmTimerCallback()")
        self.assertLess(main.index("async_generate_slot_.completed()"),
                        main.index("tryRecoverFromEmergencyBrake()"))
        self.assertLess(main.index("refreshAsyncGenerateHold()"), main.index("callMainFsmOnce()"))
        self.assertLess(main.index("if (async_generate_slot_.busy()) return;"),
                        main.index("callMainFsmOnce()"))
        post = main[main.index("callMainFsmOnce()"):]
        self.assertLess(post.index("async_generate_slot_.busy()"),
                        post.index("consumeTrajectoryGuardRejection()"))

    def test_no_implicit_full_for_ordinary_request(self):
        dispatch = body(FSM, "bool dispatchGenerateTrajectoryAsync() override")
        self.assertNotIn("publishTrajectoryGuardRecoveryState(true)", dispatch)
        identity = body(FSM, "async_from_rest::Identity asyncGenerateIdentityLocked(")
        self.assertIn("required_full_refresh_min_seq_ != 0", identity)
        self.assertIn("identity.ack.required = false;", identity)
        self.assertIn("identity.ack.advertised_or_event = false;", identity)

    def test_quarantine_is_not_cleared_on_discard(self):
        finish = body(FSM, "bool finishAsyncGenerateTrajectory(")
        self.assertLess(finish.index("async_from_rest::mayComplete"),
                        finish.index("clearAsyncGenerateQuarantineLocked()"))
        success = finish[finish.index("if (completed) {"):finish.index("async_generate_slot_.release")]
        self.assertIn("machine_state_.store(FOLLOW_TRAJ", success)
        self.assertIn("clearAsyncGenerateQuarantineLocked();", success)
        self.assertIn("mpc_cmd_pub_->publish(message)", success)
        discard = success[success.index("} else {"):]
        self.assertNotIn("clearAsyncGenerateQuarantineLocked", discard)

    def test_final_handoff_and_finite_stopped_odometry(self):
        finish = body(FSM, "bool finishAsyncGenerateTrajectory(")
        self.assertIn("trajectory_handoff::compareAt<StatePVAJ>", finish)
        self.assertIn("proof.handoff_continuous = handoff.continuous;", finish)
        self.assertIn("ASYNC_GENERATE_HANDOFF_REJECT", finish)
        self.assertLess(finish.index("std::lock_guard<std::mutex> safety", finish.index("bool completed = false")),
                        finish.index("handoff_wt = ros_ptr_->getSimTime()"))
        held = body(FSM, "bool asyncGenerateHoldPoseValidLocked(")
        self.assertIn("asyncGenerateStationaryTwist(now)", held)
        self.assertNotIn("odom.v", held)

    def test_stopped_speed_uses_actual_ros2_twist_api(self):
        twist = body(FSM, "bool asyncGenerateStationaryTwist(")
        self.assertIn("map_ptr_->getLatestOdomTwist(velocity, receive_time)", twist)
        self.assertIn("velocity.array().isFinite().all()", twist)
        self.assertIn("async_from_rest::freshStationaryTwist(", twist)
        self.assertIn("available, velocity.norm(), receive_time, now", twist)
        dispatch = body(FSM, "bool dispatchGenerateTrajectoryAsync() override")
        self.assertIn("bool needs_stop = !asyncGenerateStationaryTwist(now);", dispatch)
        self.assertNotIn("odom.v", dispatch)

    def test_delayed_ordinary_sample_checked_after_final_lock(self):
        command = body(FSM, "void pubCmdTimerCallback()")
        final = command[command.index("std::lock_guard<std::mutex> publication_lock(safety_mutex_);"):]
        self.assertIn("getCommittedSharedTrajectorySnapshot()", final)
        self.assertIn("safety_certificate_.map_version == health.map_version", final)
        self.assertIn("command_sample.generation, command_sample.start_wt", final)
        self.assertIn("current.generation, current.start_wt", final)
        self.assertIn("safety_certificate_.trajectory_generation", final)
        self.assertIn("safety_certificate_.checked_from_tt", final)
        self.assertIn("safety_certificate_.checked_to_tt", final)
        self.assertLess(final.index("async_from_rest::mayPublishOrdinarySample"),
                        final.index("mpc_cmd_pub_->publish(heartbeat)"))

    def test_both_recovery_release_paths_clear_quarantine(self):
        asynchronous = body(FSM, "bool finishAsyncCertifiedRecovery(")
        legacy = body(FSM, "bool tryRecoverFromEmergencyBrake()")
        self.assertIn("clearAsyncGenerateQuarantineLocked()", asynchronous)
        self.assertIn("clearAsyncGenerateQuarantineLocked()", legacy)
        self.assertIn("async_generate_slot_.busy()) return false", legacy)

    def test_brake_fallback_does_not_select_unpublished_candidate(self):
        brake = body(FSM, "bool activateEmergencyBrake(")
        self.assertIn("getExecutableSampleForBrake(current_sample)", brake)
        self.assertNotIn("getOneCommandSample(current_sample)", brake)
        sampler = body(FSM, "bool getExecutableSampleForBrake(")
        self.assertIn("async_generate_quarantine_.load", sampler)
        self.assertIn("sample = async_generate_hold_sample_", sampler)
        self.assertIn("asyncGenerateHoldPoseValidLocked()", sampler)

    def test_command_and_poly_publication_gates(self):
        command = body(FSM, "void pubCmdTimerCallback()")
        self.assertIn("mayPublishPinnedHold", command)
        self.assertIn("getOneHeartBeatMsg(heartbeat, held)", command)
        self.assertGreaterEqual(command.count("async_generate_quarantine_.load"), 3)
        poly = body(FSM, "void publishPolyTraj() override")
        self.assertGreaterEqual(poly.count("async_generate_quarantine_.load"), 2)
        self.assertLess(poly.index("publication.lock()"), poly.index("mpc_cmd_pub_->publish(cmd_traj)"))

    def test_exact_replay_precedes_healthy_coalescer(self):
        callback = body(FSM, "void goalCallback(")
        self.assertLess(callback.index("ignoreExactInFlightGenerateReplay(request)"),
                        callback.index("coalesceExplicitGoalRetransmission(request)"))
        replay = body(FSM, "bool ignoreExactInFlightGenerateReplay(")
        self.assertIn("accepted_raw_goal_source_revision_ == queued_goal_revision_", replay)
        self.assertIn("ASYNC_GENERATE_EXACT_GOAL_REPLAY", replay)
        self.assertNotIn("publishGoalRetransmissionToken", replay)


if __name__ == "__main__":
    unittest.main(verbosity=2)
