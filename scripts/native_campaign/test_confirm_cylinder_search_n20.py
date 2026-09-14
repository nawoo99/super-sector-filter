from confirm_cylinder_search_n20 import eligible, result, MODES, RUNS


def row(mode, run=1, success=True, contacts=0):
    return dict(map="cyl2_test", run=run, mode=mode, success=success,
                safety_collisions=contacts, static_pcd_collisions=contacts,
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
