#!/usr/bin/env python3
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
FSM_H = (ROOT / "include/fsm/fsm.h").read_text()
FSM_CPP = (ROOT / "src/super_core/fsm.cpp").read_text()
ROS2 = (ROOT / "include/ros_interface/ros2/fsm_ros2.hpp").read_text()


class GoalChangeFullRefreshV6SourceContract(unittest.TestCase):
    def test_default_off_and_dependencies_are_exact(self):
        self.assertIn('std::getenv("SUPER_GOAL_CHANGE_FULL_REFRESH_V6")', ROS2)
        self.assertIn('cfg_.event_recovery_en && stoppedDepartureV4Enabled()', ROS2)
        self.assertIn('Goal-change Full refresh v6 requires event recovery and stopped departure v4', ROS2)
        self.assertIn('default_off=true', ROS2)

    def test_distinct_identity_is_latched_inside_goal_queue_transaction(self):
        hook = FSM_H.index('virtual void onGoalQueuedLocked(bool distinct_identity)')
        enqueue = FSM_CPP.index('void Fsm::enqueueGoal')
        same = FSM_CPP.index('goal_retransmit::sameRequest(', enqueue)
        queued = FSM_CPP.index('onGoalQueuedLocked(!repeated_identity);', enqueue)
        unlock = FSM_CPP.index('started_.store(true', enqueue)
        self.assertGreater(hook, 0)
        self.assertLess(same, queued)
        self.assertLess(queued, unlock)

    def test_only_distinct_following_goal_requests_cycle(self):
        hook = ROS2.index('void onGoalQueuedLocked(const bool distinct_identity) override')
        main = ROS2.index('void mainFsmTimerCallback()')
        block = ROS2[hook:main]
        self.assertIn('!distinct_identity', block)
        self.assertIn('!= FOLLOW_TRAJ', block)
        self.assertIn('goal_change_full_refresh_requested_.fetch_add(', block)

    def test_main_stops_before_normal_fsm_and_reuses_exact_ack_recovery(self):
        main = ROS2.index('void mainFsmTimerCallback()')
        request = ROS2.index('[GOAL_CHANGE_FULL_REFRESH_REQUEST]', main)
        brake = ROS2.index('"goal_change_full_refresh"', request)
        ordinary = ROS2.index('callMainFsmOnce();', request)
        self.assertLess(request, brake)
        self.assertLess(brake, ordinary)
        self.assertIn('action=certified_stop_then_full_ack_reroute', ROS2[request:brake])
        self.assertIn('fullRefreshRecoveryGateSatisfied(health)', ROS2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
