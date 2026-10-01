#!/usr/bin/env python3
"""Synthetic positive and negative contracts for the event-based audit."""
import unittest

from audit_goal_change_full_refresh_v7 import audit


def fixture(already_open=False):
    rows = ['[GOAL_CHANGE_FULL_REFRESH_V6] enabled=true']
    rows.append('[MISSION_GOAL_IDENTITY] new_intent=1 new_identity=1 waypoint=0')
    rows.extend(('[FULL_REFRESH_RECOVERY_GATE_ARM] min_request_seq=1',
                 '[EVENT_RECOVERY_FULL] cycle=1',
                 '[FULL_REFRESH_RECOVERY_ACK] request_seq=1 committed=1',
                 'Receive click goal at: first',
                 '[EVENT_RECOVERY_PATH_READY] request_seq=1',
                 '[EVENT_RECOVERY_SECTOR] cycle=1 planner_release=1'))
    next_cycle = 2
    next_request = 1
    for goal in range(1, 5):
        if goal == 1 and already_open:
            rows.extend((f'[FULL_REFRESH_RECOVERY_GATE_ARM] min_request_seq={next_cycle}',
                         f'[EVENT_RECOVERY_FULL] cycle={next_cycle}'))
        rows.append(f'[MISSION_GOAL_IDENTITY] new_intent=1 new_identity=1 waypoint={goal}')
        if not (goal == 1 and already_open):
            rows.append(f'[GOAL_CHANGE_FULL_REFRESH_REQUEST] request={next_request}')
            next_request += 1
            rows.extend((f'[FULL_REFRESH_RECOVERY_GATE_ARM] min_request_seq={next_cycle}',
                         f'[EVENT_RECOVERY_FULL] cycle={next_cycle}'))
        rows.extend((f'[FULL_REFRESH_RECOVERY_ACK] request_seq={next_cycle} committed=1',
                     f'Receive click goal at: waypoint {goal}',
                     f'[EVENT_RECOVERY_PATH_READY] request_seq={next_cycle}',
                     f'[EVENT_RECOVERY_SECTOR] cycle={next_cycle} planner_release=1'))
        next_cycle += 1
    return '\n'.join(rows)


class GoalChangeAuditTest(unittest.TestCase):
    def test_four_explicit_requests(self):
        result = audit(fixture(), 'adaptive')
        self.assertTrue(result['valid'], result)
        self.assertEqual(result['request_count'], 4)

    def test_one_already_open_full_cycle(self):
        result = audit(fixture(already_open=True), 'adaptive')
        self.assertTrue(result['valid'], result)
        self.assertEqual(result['request_count'], 3)
        self.assertEqual(result['covered_goals'][0]['method'], 'already_open_full_refresh')

    def test_missing_request_without_preexisting_full_rejected(self):
        stack = fixture().replace('[GOAL_CHANGE_FULL_REFRESH_REQUEST] request=1\n', '')
        self.assertFalse(audit(stack, 'adaptive')['valid'])

    def test_missing_ack_rejected(self):
        stack = fixture(already_open=True).replace(
            '[FULL_REFRESH_RECOVERY_ACK] request_seq=2 committed=1\n', '')
        self.assertFalse(audit(stack, 'adaptive')['valid'])

    def test_missing_path_certificate_rejected(self):
        stack = fixture(already_open=True).replace(
            '[EVENT_RECOVERY_PATH_READY] request_seq=2\n', '')
        self.assertFalse(audit(stack, 'adaptive')['valid'])

    def test_missing_sector_release_rejected(self):
        stack = fixture(already_open=True).replace(
            '[EVENT_RECOVERY_SECTOR] cycle=2 planner_release=1\n', '')
        self.assertFalse(audit(stack, 'adaptive')['valid'])

    def test_duplicate_goal_identity_rejected(self):
        marker = '[MISSION_GOAL_IDENTITY] new_intent=1 new_identity=1 waypoint=2'
        stack = fixture(already_open=True).replace(marker, marker + '\n' + marker)
        self.assertFalse(audit(stack, 'adaptive')['valid'])

    def test_wrong_runtime_mode_rejected(self):
        self.assertFalse(audit(fixture(), 'sector')['valid'])
        self.assertTrue(audit('[GOAL_CHANGE_FULL_REFRESH_V6] enabled=false', 'sector')['valid'])


if __name__ == '__main__':
    unittest.main()
