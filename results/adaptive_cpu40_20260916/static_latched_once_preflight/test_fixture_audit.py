#!/usr/bin/env python3
"""Pure audit regression tests; AST-load only audit function, no ROS imports/run."""
import ast
import copy
from pathlib import Path
import re
from types import SimpleNamespace
import unittest


SOURCE = Path('/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py')
definition = next(node for node in ast.parse(SOURCE.read_text()).body
                  if isinstance(node, ast.FunctionDef) and node.name == 'audit_latched_once')
namespace = {'re': re}
exec(compile(ast.Module(body=[definition], type_ignores=[]), str(SOURCE), 'exec'), namespace)
audit = namespace['audit_latched_once']
SHA = 'b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f'
FIELDS = 'publications=1 points=241490 bytes=7727680 stamp_ns=123456789 timers_created=0 poll_callbacks=0'
INITIAL = '[INFO] [100.000000001] [perfect_drone]: [STATIC_PC_LATCHED_PUBLICATION] ' + FIELDS + ' complete_geometry=1'
SUMMARY1 = '[INFO] [105.000000001] [perfect_drone]: [STATIC_PC_LATCHED_SUMMARY] enabled=1 ' + FIELDS
SUMMARY2 = '[INFO] [111.000000001] [perfect_drone]: [STATIC_PC_LATCHED_SUMMARY] enabled=1 ' + FIELDS
LOG = '\n'.join((INITIAL, SUMMARY1, SUMMARY2))
CLOUD = dict(sha256=SHA, points=241490, bytes=7727680, stamp_ns=123456789,
             frame='world', point_step=32)
READERS = {label: [dict(CLOUD)] for label in ('first', 'second', 'reconnected')}


class AuditTest(unittest.TestCase):
    def check_rejected(self, text=LOG, readers=None, span=11.):
        with self.assertRaises(ValueError):
            audit(text, READERS if readers is None else readers, 241490, SHA, span)

    def test_valid_all_phases(self):
        result = audit(LOG, READERS, 241490, SHA, 11.)
        self.assertTrue(result['valid'])
        self.assertEqual(result['publication_count'], 1)
        self.assertEqual(result['summary_count'], 2)
        self.assertEqual(result['steady_summary_span_s'], 6.)
        self.assertTrue(all(result['checks'].values()))

    def test_duplicate_initial(self):
        self.check_rejected(LOG + '\n' + INITIAL)

    def test_no_initial(self):
        self.check_rejected('\n'.join((SUMMARY1, SUMMARY2)))

    def test_only_one_summary(self):
        self.check_rejected('\n'.join((INITIAL, SUMMARY1)))

    def test_timers_created(self):
        self.check_rejected(LOG.replace('timers_created=0', 'timers_created=1'))

    def test_poll_callbacks_even_if_constant(self):
        self.check_rejected(LOG.replace('poll_callbacks=0', 'poll_callbacks=1'))

    def test_final_publication_increased(self):
        self.check_rejected(LOG.replace(SUMMARY2, SUMMARY2.replace('publications=1', 'publications=2')))

    def test_final_stamp_changed(self):
        self.check_rejected(LOG.replace(SUMMARY2, SUMMARY2.replace('stamp_ns=123456789', 'stamp_ns=123456790')))

    def test_disabled_final(self):
        self.check_rejected(LOG.replace(SUMMARY2, SUMMARY2.replace('enabled=1', 'enabled=0')))

    def test_unvalidated_initial(self):
        self.check_rejected(LOG.replace('complete_geometry=1', 'complete_geometry=0'))

    def test_missing_field(self):
        self.check_rejected(LOG.replace('bytes=7727680 ', ''))

    def test_noninteger_field(self):
        self.check_rejected(LOG.replace('publications=1', 'publications=NaN'))

    def test_no_log_timestamp(self):
        self.check_rejected(LOG.replace('[105.000000001]', '[unknown]'))

    def test_summary_window_short(self):
        self.check_rejected(LOG.replace('[111.000000001]', '[109.999999999]'))

    def test_backward_summary_stamp(self):
        self.check_rejected(LOG.replace('[111.000000001]', '[104.000000001]'))

    def test_exact_nanosecond_boundary(self):
        result = audit(LOG.replace('[111.000000001]', '[110.000000001]'), READERS, 241490, SHA, 11.)
        self.assertEqual(result['steady_summary_span_s'], 5.)

    def test_monotonic_observation_short_or_missing(self):
        for span in (None, 4.999):
            with self.subTest(span=span):
                self.check_rejected(span=span)

    def test_legacy_publication(self):
        for line in ('[STATIC_PC_PUBLICATION] count=1', 'Publish global map size: 241490'):
            with self.subTest(line=line):
                self.check_rejected(LOG + '\n' + line)

    def test_reader_missing(self):
        for label in READERS:
            readers = copy.deepcopy(READERS)
            readers[label] = []
            with self.subTest(label=label):
                self.check_rejected(readers=readers)

    def test_duplicate_sample(self):
        readers = copy.deepcopy(READERS)
        readers['first'].append(dict(CLOUD))
        self.check_rejected(readers=readers)

    def test_reader_wrong_stamp_sha_count_frame_or_layout(self):
        for key, value in (('stamp_ns', 123456790), ('sha256', 'bad'), ('points', 241489),
                           ('bytes', 7727648), ('frame', 'map'), ('point_step', 16)):
            readers = copy.deepcopy(READERS)
            readers['reconnected'][0][key] = value
            with self.subTest(key=key):
                self.check_rejected(readers=readers)

    def test_invalid_return_without_exception_fails_overall_result(self):
        # Execute the actual finalizer branch with a deliberately nonthrowing
        # invalid audit. This protects its caller contract, not just the parser.
        self.assertFalse(self.run_finalizer(True, False)['valid'])

    def test_valid_audit_does_not_erase_earlier_failure(self):
        self.assertFalse(self.run_finalizer(False, True)['valid'])

    @staticmethod
    def run_finalizer(previous_valid, audit_valid):
        main = next(node for node in ast.parse(SOURCE.read_text()).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'main')
        outer_try = next(node for node in main.body
                         if isinstance(node, ast.Try) and node.finalbody)
        finalizer = next(node for node in outer_try.finalbody
                         if isinstance(node, ast.If) and ast.unparse(node.test) == 'args.latched_once')
        result = dict(valid=previous_valid)
        local = dict(args=SimpleNamespace(latched_once=True, expected_points=241490,
                                         expected_sha256=SHA),
                     shutdown_requested_at=11., latched_publication_observed_at=0.,
                     result=result, received=READERS, log_text=lambda: LOG,
                     audit_latched_once=lambda *unused: dict(valid=audit_valid))
        exec(compile(ast.Module(body=[finalizer], type_ignores=[]), str(SOURCE), 'exec'), local)
        return result


if __name__ == '__main__':
    unittest.main(verbosity=2)
