#!/usr/bin/env python3
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FSM = (ROOT / "include/ros_interface/ros2/fsm_ros2.hpp").read_text()


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


class StoppedHoldV5SourceContract(unittest.TestCase):
    def test_exact_opt_in_and_v4_dependency(self):
        self.assertIn('std::getenv("SUPER_STOPPED_HOLD_V5")', FSM)
        enabled = body(FSM, "bool stoppedHoldV5Enabled() const")
        self.assertIn("stoppedDepartureV4Enabled()", enabled)
        init = body(FSM, "void init(")
        self.assertIn("Stopped hold v5 requires stopped departure v4", init)
        self.assertIn("[STOPPED_HOLD_V5]", init)

    def test_only_stationary_stable_soft_or_unknown_enters_v5(self):
        brake = body(FSM, "bool activateEmergencyBrake(")
        gate = brake.index("stoppedHoldV5Enabled()")
        policy = brake.index("DeferSoftMarginUntilHardChecksComplete", gate)
        self.assertIn("stationary_candidate && passive_stop_stable",
                      brake[gate:policy])
        self.assertIn("TrajectorySafetyStatus::CLEARANCE_MARGIN",
                      brake[gate:policy])
        self.assertIn("TrajectorySafetyStatus::UNOBSERVED",
                      brake[gate:policy])

    def test_relaxation_is_bounded_by_full_hard_check_proof(self):
        brake = body(FSM, "bool activateEmergencyBrake(")
        gate = brake.index("stoppedHoldV5Enabled()")
        section = brake[gate:brake.index("raw_brake_status =", gate)]
        self.assertIn("relaxed_unknown_as_occupied", section)
        self.assertIn("stop_margin::admissibleStop", section)
        self.assertIn("hold_safety.hard_checks_complete", section)
        self.assertIn("hold_safety.map_version", section)
        self.assertIn("hold_health_after.map_version", section)


if __name__ == "__main__":
    unittest.main(verbosity=2)
