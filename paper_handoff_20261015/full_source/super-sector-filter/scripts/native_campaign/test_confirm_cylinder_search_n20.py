from confirm_cylinder_search_n20 import eligible, qualified, reference_failure, stopped_result, result, MODES, RUNS


def row(mode, run=1, success=True, contacts=0):
    return dict(map="cyl2_test", run=run, mode=mode, success=success,
                safety_collisions=contacts, static_pcd_collisions=contacts,
                solid_collision_episodes=contacts,solid_observer_valid=True,
                run_valid=True, resource_valid=True, speed_limit_valid=True,
                infrastructure_failure=False, attempt_count=1, retry_count=0)


def test_brake_rejections_alone_do_not_qualify():
    rows = [row(m) for m in MODES]
    rows[1]["guard_brake_rejections"] = 500
    assert not eligible(rows)


def test_sector_completion_or_contact_failure_can_qualify():
    assert eligible([row("full"), row("sector", success=False), row("adaptive")])
    assert eligible([row("full"), row("sector", contacts=1), row("adaptive")])
    assert not eligible([row("full", success=False), row("sector", contacts=1), row("adaptive")])


def test_confirmation_requires_all_sixty_and_no_full_adaptive_failures():
    rows = [row(m, r) for r in RUNS for m in MODES]
    rows[1]["success"] = False
    assert result(rows)["observed_user_criterion_met"]
    assert not result(rows[:-1])["observed_user_criterion_met"]
    rows[0]["static_pcd_collisions"] = 1
    assert not result(rows)["observed_user_criterion_met"]


def test_quality_or_duplicate_cannot_qualify():
    rows = [row("full"), row("sector", success=False), row("adaptive")]
    assert not eligible(rows + [rows[0]])
    rows[1]["resource_valid"] = False
    assert not eligible(rows)


def test_other_map_or_missing_outcome_does_not_create_separation():
    rows = [row("full"), row("sector", contacts=1), row("adaptive")]
    rows[1]["map"] = "cyl2_other"
    assert not eligible(rows)
    rows[1]["map"] = "cyl2_test"
    rows[1]["static_pcd_collisions"] = ""
    assert not eligible(rows)
    rows[1]["static_pcd_collisions"] = 0
    rows[1]["success"] = ""
    assert not eligible(rows)


def test_surface_only_rows_cannot_certify_no_contact_and_solid_contacts_count():
    rows=[row("full"),row("sector"),row("adaptive")]
    rows[1]["solid_collision_episodes"]=1
    assert eligible(rows)
    del rows[0]["solid_collision_episodes"]
    assert not eligible(rows)


def test_repeated_pilot_and_futility_stop_are_not_twenty_completed_trials():
    rows=[row(m,r,success=(m!="sector")) for r in range(1,4) for m in MODES]
    assert qualified(rows,3)
    assert not qualified(rows[:-1],3)
    assert not qualified(rows[:3],3)
    assert not reference_failure(rows)
    rows[0]["success"]=False
    assert reference_failure(rows)
    assert not qualified(rows,3)
    report=stopped_result(rows,{"planned_rows":60})
    assert report["stopped_early"]
    assert report["decision"]=="STOPPED_EARLY_REFERENCE_FAILURE"
    assert not report["observed_user_criterion_met"]
