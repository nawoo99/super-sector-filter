import os
import tempfile
import unittest

from native_campaign import (
    parse_full_refresh_ack_log,
    parse_optimizer_phase_memory_logs,
    parse_sensor_cadence_log,
    parse_shadow_guard_log,
)


class SensorCadenceLogTest(unittest.TestCase):
    def test_reads_last_complete_summary(self):
        lines = """\
[INFO] [SENSOR_CADENCE_SUMMARY] frames=3 span_s=0.200000 hz=10.000000 raw_published=3 direct_handoffs=0 payload_bytes=1200
[INFO] [SENSOR_CADENCE_SUMMARY] frames=101 span_s=10.000000 hz=10.000000 raw_published=0 direct_handoffs=101 payload_bytes=40400
"""
        handle, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(handle, "w") as stream:
                stream.write(lines)
            result = parse_sensor_cadence_log(path)
        finally:
            os.unlink(path)

        self.assertEqual(result["sensor_frames"], 101)
        self.assertEqual(result["sensor_raw_published"], 0)
        self.assertEqual(result["sensor_direct_handoffs"], 101)
        self.assertAlmostEqual(result["sensor_hz"], 10.0)


class OptimizerPhaseMemoryLogTest(unittest.TestCase):
    def test_aggregates_completed_and_oom_interrupted_phases(self):
        attempts = [
            """\
[OPTIMIZER_PHASE_MEMORY] optimizer=exp event=begin call=1 rss_mib=3100.000 swap_mib=0.000 variables=12 pieces=4
[OPTIMIZER_PHASE_MEMORY] optimizer=exp event=end call=1 duration_ms=10.000 iterations=4 ret=0 rss_mib=3110.000 swap_mib=0.000 rss_delta_mib=10.000
[OPTIMIZER_PHASE_MEMORY] optimizer=backup event=begin call=1 rss_mib=3110.000 swap_mib=0.000 variables=8 pieces=3
""",
            """\
[OPTIMIZER_PHASE_MEMORY] optimizer=exp event=begin call=1 rss_mib=3050.000 swap_mib=0.000 variables=12 pieces=4
[OPTIMIZER_PHASE_MEMORY] optimizer=exp event=end call=1 duration_ms=30.000 iterations=8 ret=-1000 rss_mib=3070.000 swap_mib=0.000 rss_delta_mib=20.000
[OPTIMIZER_PHASE_MEMORY] optimizer=backup event=begin call=1 rss_mib=3070.000 swap_mib=0.000 variables=8 pieces=3
[OPTIMIZER_PHASE_MEMORY] optimizer=backup event=end call=1 duration_ms=12.000 iterations=5 ret=0 rss_mib=3075.000 swap_mib=0.000 rss_delta_mib=5.000
""",
        ]
        paths = []
        try:
            for lines in attempts:
                handle, path = tempfile.mkstemp(text=True)
                paths.append(path)
                with os.fdopen(handle, "w") as stream:
                    stream.write(lines)
            result = parse_optimizer_phase_memory_logs(paths)
        finally:
            for path in paths:
                os.unlink(path)

        self.assertTrue(result["optimizer_phase_trace_enabled"])
        self.assertEqual(result["optimizer_exp_phase_started"], 2)
        self.assertEqual(result["optimizer_exp_phase_completed"], 2)
        self.assertAlmostEqual(result["optimizer_exp_duration_ms_mean"], 20.0)
        self.assertAlmostEqual(result["optimizer_exp_duration_ms_max"], 30.0)
        self.assertAlmostEqual(result["optimizer_exp_rss_mib_max"], 3110.0)
        self.assertAlmostEqual(result["optimizer_exp_rss_delta_mib_max"], 20.0)
        self.assertEqual(result["optimizer_backup_phase_started"], 2)
        self.assertEqual(result["optimizer_backup_phase_completed"], 1)
        self.assertEqual(result["optimizer_phase_incomplete_events"], 1)
        self.assertEqual(
            result["optimizer_phase_last_incomplete"], "attempt1:backup:1"
        )


class ShadowGuardLogTest(unittest.TestCase):
    def test_separates_geometry_from_map_races(self):
        lines = """\
[INFO] -- [TRAJ_GUARD_SHADOW_SAFE] phase=x gen=1 map=1 samples=5 range=[0,1] validation_ms=2.000 action=observed_after_commit
[WARN] -- [TRAJ_GUARD_SHADOW_UNSAFE] phase=x segment=EXP status=VERSION_CHANGED gen=2 map=2 validation_ms=3.000 action=observed_after_commit
[WARN] -- [TRAJ_GUARD_SHADOW_UNSAFE] phase=x segment=APPENDED_BACKUP status=OCCUPIED gen=3 map=2 validation_ms=4.000 action=observed_after_commit
[WARN] -- [TRAJ_GUARD_SHADOW_UNSAFE] phase=x segment=EXP_TO_BACKUP_STITCH status=OUT_OF_MAP gen=4 map=2 validation_ms=5.000 action=observed_after_commit
[WARN] -- [TRAJ_GUARD_SHADOW_UNSAFE] phase=x segment=NOT_APPLICABLE status=MAP_NOT_COMMITTED gen=5 map=0 validation_ms=0.100 action=observed_after_commit
[INFO] -- [TRAJ_GUARD_SHADOW_SKIPPED] phase=x gen=6 reason=RATE_LIMIT since_last_ms=25.000 min_interval_ms=250.000 action=observed_after_commit
"""
        handle, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(handle, "w") as stream:
                stream.write(lines)
            result = parse_shadow_guard_log(path)
        finally:
            os.unlink(path)

        self.assertEqual(result["shadow_safe_candidates"], 1)
        self.assertEqual(result["shadow_unsafe_candidates"], 4)
        self.assertEqual(result["shadow_skipped_candidates"], 1)
        self.assertEqual(result["shadow_validated_candidates"], 5)
        self.assertEqual(result["shadow_geometric_unsafe"], 2)
        self.assertEqual(result["shadow_map_race"], 1)
        self.assertEqual(result["shadow_other_indeterminate"], 1)
        self.assertEqual(result["shadow_unsafe_exp"], 0)
        self.assertEqual(result["shadow_unsafe_appended_backup"], 1)
        self.assertEqual(result["shadow_unsafe_stitch"], 1)
        self.assertAlmostEqual(result["shadow_validation_ms_mean"], 2.82)
        self.assertAlmostEqual(result["shadow_validation_ms_max"], 5.0)


class RecoveryBranchLogTest(unittest.TestCase):
    def test_extracts_unique_trajectory_commit_cadence(self):
        lines = """\
[INFO] [100.000000] -- [TRAJ_GUARD_COMMIT] phase=x gen=10 map=3
[INFO] [100.200000] -- [TRAJ_GUARD_COMMIT] phase=x gen=11 map=4
[INFO] [100.200000] -- [TRAJ_GUARD_COMMIT] phase=x gen=11 map=4
[INFO] [100.500000] -- [TRAJ_GUARD_COMMIT] phase=x gen=12 map=5
"""
        handle, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(handle, "w") as stream:
                stream.write(lines)
            result = parse_full_refresh_ack_log(path)
        finally:
            os.unlink(path)

        self.assertEqual(result["trajectory_commit_unique_generations"], 3)
        self.assertEqual(result["trajectory_commit_last_generation"], 12)
        self.assertAlmostEqual(result["trajectory_commit_span_s"], 0.5)
        self.assertAlmostEqual(result["trajectory_commit_hz"], 4.0)

    def test_counts_frontend_risk_enforcement(self):
        lines = """\
[FRONTEND_RISK_ENFORCE] action=IGNORE request=1 generation_match=false fresh=true source_fresh=true time_covered=true
[FRONTEND_RISK_ENFORCE] action=IGNORE request=2 generation_match=true fresh=false source_fresh=false time_covered=false
[FRONTEND_RISK_ENFORCE] action=BRAKE request=3
[FRONTEND_RISK_SUMMARY] received=10 occupied=3 ignored=2 enforced=1
[FRONTEND_BODY_ENFORCE] action=IGNORE request=4 generation_match=true fresh=false source_fresh=true time_covered=true
[FRONTEND_BODY_ENFORCE] action=BRAKE request=5
[TRAJ_GUARD_BRAKE] trigger=frontend_body_active_brake duration=0.500s
[FRONTEND_BODY_SUMMARY] received=20 occupied=2 ignored=1 enforced=1 clear_while_braking=4
"""
        handle, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(handle, "w") as stream:
                stream.write(lines)
            result = parse_full_refresh_ack_log(path)
        finally:
            os.unlink(path)

        self.assertEqual(result["frontend_risk_received"], 10)
        self.assertEqual(result["frontend_risk_occupied"], 3)
        self.assertEqual(result["frontend_risk_ignored"], 2)
        self.assertEqual(result["frontend_risk_enforced"], 1)
        self.assertEqual(result["frontend_risk_ignore_events"], 2)
        self.assertEqual(result["frontend_risk_brake_events"], 1)
        self.assertEqual(
            result["frontend_risk_generation_mismatch_ignores"], 1
        )
        self.assertEqual(result["frontend_risk_stale_result_ignores"], 1)
        self.assertEqual(result["frontend_risk_stale_source_ignores"], 1)
        self.assertEqual(result["frontend_risk_time_uncovered_ignores"], 1)
        self.assertEqual(result["frontend_body_received"], 20)
        self.assertEqual(result["frontend_body_occupied"], 2)
        self.assertEqual(result["frontend_body_ignored"], 1)
        self.assertEqual(result["frontend_body_enforced"], 1)
        self.assertEqual(result["frontend_body_clear_while_braking"], 4)
        self.assertEqual(result["frontend_body_ignore_events"], 1)
        self.assertEqual(result["frontend_body_brake_events"], 1)
        self.assertEqual(
            result["frontend_body_active_brake_replacements"], 1
        )

    def test_counts_optimizer_iteration_caps(self):
        lines = """\
[fsm_node] L-BFGS reaches the maximum number of iterations.
[fsm_node] unrelated optimizer warning
[fsm_node] L-BFGS reaches the maximum number of iterations.
"""
        handle, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(handle, "w") as stream:
                stream.write(lines)
            result = parse_full_refresh_ack_log(path)
        finally:
            os.unlink(path)
        self.assertEqual(result["optimizer_iteration_cap_hits"], 2)

    def test_extracts_latest_dedicated_guard_payload_counters(self):
        lines = """\
[WARN] -- [TRAJ_GUARD_RAW_DEBUG] sequence=3 latest_age_s=0.040 dedicated_messages=3 dedicated_payload_bytes=1200
[WARN] -- [TRAJ_GUARD_RAW_DEBUG] sequence=9 latest_age_s=0.020 dedicated_messages=9 dedicated_payload_bytes=4800
"""
        handle, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(handle, "w") as stream:
                stream.write(lines)
            result = parse_full_refresh_ack_log(path)
        finally:
            os.unlink(path)

        self.assertEqual(result["guard_dedicated_messages"], 9)
        self.assertEqual(result["guard_dedicated_payload_bytes"], 4800)

    def test_counts_fault_injection_and_bounded_egress_markers(self):
        lines = """\
[WARN] -- [TEST_FAULT_LOCAL_ESCAPE_ARM] direction=[1,0,0]
[WARN] -- [TEST_FAULT_BASE_NO_PATH_ARM] failures=3
[WARN] -- [TEST_FAULT_BASE_NO_PATH] remaining=2
[WARN] -- [TEST_FAULT_BASE_NO_PATH] remaining=1
[WARN] -- [TEST_FAULT_BASE_NO_PATH] remaining=0
[WARN] -- [TRAJ_GUARD_BASE_NO_PATH_LOCAL_ESCAPE] attempt=1/4
[WARN] -- [TEST_FAULT_LOCAL_ESCAPE_DIRECTION_SKIP] attempt=1/4
[WARN] -- [TRAJ_GUARD_LOCAL_ESCAPE_DIRECTION_REJECTED] attempt=2/4
[WARN] -- [TRAJ_GUARD_LOCAL_ESCAPE] action=commit direction_attempt=3/4
[WARN] -- [TRAJ_GUARD_LOCAL_ESCAPE_REJECTED] attempts=4
[WARN] -- [TEST_FAULT_INITIAL_FOOTPRINT_OCCUPANCY] action=inject_once
[INFO] -- [TRAJ_GUARD_COMMIT] phase=x footprint_egress=true
[INFO] -- [REPLAN_SAME_MAP_COALESCED] map=40 generation=51 skipped_total=1
[INFO] -- [REPLAN_SAME_MAP_COALESCED] map=40 generation=51 skipped_total=2
[INFO] -- [REPLAN_SAME_MAP_COALESCE_SUMMARY] skipped=73 last_map=41 last_generation=52
"""
        handle, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(handle, "w") as stream:
                stream.write(lines)
            result = parse_full_refresh_ack_log(path)
        finally:
            os.unlink(path)

        self.assertEqual(result["guard_local_escape_test_injections"], 1)
        self.assertEqual(result["guard_base_no_path_test_injections"], 1)
        self.assertEqual(result["guard_base_no_path_forced_failures"], 3)
        self.assertEqual(result["guard_base_no_path_local_escape_arms"], 1)
        self.assertEqual(result["guard_local_escape_direction_skips"], 1)
        self.assertEqual(result["guard_local_escape_direction_rejections"], 1)
        self.assertEqual(result["guard_local_escape_commits"], 1)
        self.assertEqual(result["guard_local_escape_rejections"], 1)
        self.assertEqual(result["guard_initial_footprint_test_injections"], 1)
        self.assertEqual(result["guard_initial_footprint_egress_commits"], 1)
        self.assertEqual(result["guard_same_map_replan_skips"], 73)


if __name__ == "__main__":
    unittest.main()
