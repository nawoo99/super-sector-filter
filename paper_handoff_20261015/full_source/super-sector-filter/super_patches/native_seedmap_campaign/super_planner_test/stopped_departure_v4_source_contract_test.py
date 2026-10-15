#!/usr/bin/env python3
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "src/super_core/super_planner.cpp").read_text()
HEADER = (ROOT / "include/super_core/super_planner.h").read_text()
FSM = (ROOT / "include/ros_interface/ros2/fsm_ros2.hpp").read_text()
CMD = (ROOT / "include/data_structure/cmd_traj.h").read_text()


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


class StoppedDepartureV4SourceContract(unittest.TestCase):
    def test_exact_opt_in_and_dependencies(self):
        self.assertIn('std::getenv("SUPER_STOPPED_DEPARTURE_V4")', CORE)
        init = body(FSM, "void init(")
        self.assertIn("both async planners", init)
        self.assertIn("stoppedDepartureV4SettingEnabled()", init)

    def test_physical_start_and_search_seed_are_separate(self):
        plan = body(CORE, "SuperPlanner::PlanFromRest(")
        self.assertIn("local_start_p_ = stoppedDepartureV4Enabled()", plan)
        self.assertIn("local_search_start_p_ = local_star_pt", plan)
        generate = body(CORE, "RET_CODE SuperPlanner::generateExpTraj(")
        self.assertIn("guide_path.push_back(local_search_start_p_)", generate)
        self.assertLess(generate.index("guide_path.push_back(local_search_start_p_)"),
                        generate.index("PathSearch(guide_path.back()"))

    def test_worker_certificate_begins_at_zero(self):
        commit = body(CORE, "bool SuperPlanner::commitTrajectoryCandidate(")
        self.assertIn("checked_from_tt = 0.0", commit)
        self.assertIn("stopped_departure_stage_.map_version = safety.map_version", commit)

    def test_release_is_generation_map_and_pva_bound(self):
        release = body(CORE, "StoppedDepartureRelease SuperPlanner::releaseStoppedDeparture(")
        for token in ("replan_lock_", "expected_generation", "expected_map_version",
                      "health.map_version", "comparePva", "rebaseStoppedCandidate",
                      "rebaseStartWallTime", "guard_rest_to_rest_hold_until_wt_"):
            self.assertIn(token, release)
        self.assertLess(release.index("comparePva"),
                        release.index("rebaseStoppedCandidate"))
        self.assertIn("generation deliberately stays the", CMD)

    def test_ordinary_and_emergency_use_same_release(self):
        ordinary = body(FSM, "bool finishAsyncGenerateTrajectory(")
        emergency = body(FSM, "bool finishAsyncCertifiedRecovery(")
        self.assertIn("releaseStoppedDeparture(", ordinary)
        self.assertIn("releaseStoppedDeparture(", emergency)
        self.assertLess(ordinary.index("refreshStoppedDepartureCertificate("),
                        ordinary.index("releaseStoppedDeparture("))
        self.assertLess(emergency.index("refreshStoppedDepartureCertificate("),
                        emergency.index("releaseStoppedDeparture("))
        self.assertLess(ordinary.index("releaseStoppedDeparture("),
                        ordinary.index("mpc_cmd_pub_->publish(message)"))
        self.assertLess(emergency.index("releaseStoppedDeparture("),
                        emergency.index("mpc_cmd_pub_->publish(message)"))
        self.assertIn("message.start_wt_pos = handoff_wt", ordinary)
        self.assertIn("message.start_wt_pos = stopped_release.release_wt", emergency)
        self.assertIn("health.map_version == stopped_release.map_version", ordinary)
        self.assertIn("health.map_version == stopped_release.map_version", emergency)


if __name__ == "__main__":
    unittest.main(verbosity=2)
