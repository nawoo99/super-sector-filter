#!/usr/bin/env python3
"""Positive and negative contracts for ACK-before-goal Full overlap."""
import unittest

import audit_goal_change_full_refresh_v8 as v8


def fixture():
    rows = [
        '[GOAL_CHANGE_FULL_REFRESH_V6] enabled=true',
        '[MISSION_GOAL_IDENTITY] new_intent=1 new_identity=1 waypoint=0',
        '[FULL_REFRESH_RECOVERY_GATE_ARM] min_request_seq=1',
        '[EVENT_RECOVERY_FULL] cycle=1',
        '[FULL_REFRESH_RECOVERY_ACK] request_seq=1 committed=1',
        '[MISSION_GOAL_IDENTITY] new_intent=1 new_identity=1 waypoint=1',
        '[GOAL_CHANGE_FULL_REFRESH_REQUEST] request=1',
        '[SENSOR_ACQUISITION_FRAME] frame=10 cycle=1 full=1',
        'Receive click goal at: waypoint 1',
        '[EVENT_RECOVERY_PATH_READY] request_seq=1 ack_map=10 certified_map=11',
        '[EVENT_RECOVERY_SECTOR] cycle=1 planner_release=1',
    ]
    for goal in range(2, 5):
        rows += [
            f'[MISSION_GOAL_IDENTITY] new_intent=1 new_identity=1 waypoint={goal}',
            f'[GOAL_CHANGE_FULL_REFRESH_REQUEST] request={goal}',
            f'[FULL_REFRESH_RECOVERY_GATE_ARM] min_request_seq={goal}',
            f'[EVENT_RECOVERY_FULL] cycle={goal}',
            f'[FULL_REFRESH_RECOVERY_ACK] request_seq={goal} committed=1',
            f'Receive click goal at: waypoint {goal}',
            f'[EVENT_RECOVERY_PATH_READY] request_seq={goal}',
            f'[EVENT_RECOVERY_SECTOR] cycle={goal} planner_release=1',
        ]
    return '\n'.join(rows)


class OverlapAuditTest(unittest.TestCase):
    def test_certified_overlap_accepted(self):
        result = v8.audit(fixture(), 'adaptive')
        self.assertTrue(result['valid'], result)
        self.assertEqual(result['covered_goals'][0]['method'],
                         'request_during_open_acked_full')

    def test_missing_post_goal_full_frame_rejected(self):
        stack = fixture().replace(
            '[SENSOR_ACQUISITION_FRAME] frame=10 cycle=1 full=1\n', '')
        self.assertFalse(v8.audit(stack, 'adaptive')['valid'])

    def test_stale_map_rejected(self):
        stack = fixture().replace('certified_map=11', 'certified_map=10')
        self.assertFalse(v8.audit(stack, 'adaptive')['valid'])

    def test_missing_goal_receipt_rejected(self):
        stack = fixture().replace('Receive click goal at: waypoint 1\n', '')
        self.assertFalse(v8.audit(stack, 'adaptive')['valid'])

    def test_missing_sector_release_rejected(self):
        stack = fixture().replace(
            '[EVENT_RECOVERY_SECTOR] cycle=1 planner_release=1\n', '')
        self.assertFalse(v8.audit(stack, 'adaptive')['valid'])

    def test_missing_goal_request_rejected(self):
        stack = fixture().replace(
            '[GOAL_CHANGE_FULL_REFRESH_REQUEST] request=1\n', '')
        self.assertFalse(v8.audit(stack, 'adaptive')['valid'])


if __name__ == '__main__':
    unittest.main()
