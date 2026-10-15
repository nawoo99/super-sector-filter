import pytest
import json
from pathlib import Path

import repeat_cylinder_refinements as controller

from repeat_cylinder_refinements import RECIPES, references_failed, validate_rows
from test_confirm_cylinder_search_n20 import row


def test_family_has_unique_geometry_recipes_and_fixed_parent():
    assert len(RECIPES) == 10
    assert len({r["name"] for r in RECIPES}) == 10
    assert len({(tuple(r["legs"]), r["tip_count"]) for r in RECIPES}) == 10
    assert all(r["parent"] == "cyl2_j01" for r in RECIPES)
    assert RECIPES[0] == dict(name="cyl2_j02", parent="cyl2_j01", legs=[4], tip_count=1)


def test_invalid_or_duplicate_row_stops_instead_of_being_dropped():
    r = row("full")
    validate_rows([r], "cyl2_test")
    with pytest.raises(RuntimeError, match="Duplicate"):
        validate_rows([r, r], "cyl2_test")
    r["resource_valid"] = False
    with pytest.raises(RuntimeError, match="Invalid"):
        validate_rows([r], "cyl2_test")


def test_sector_failure_does_not_reject_reference_but_adaptive_failure_does():
    assert not references_failed([row("full"), row("sector", success=False), row("adaptive")])
    assert references_failed([row("full"), row("adaptive", success=False)])
    assert references_failed([row("full", contacts=1), row("adaptive")])


@pytest.mark.parametrize("outcome", ["pass", "reference_failure", "invalid"])
def test_controller_preserves_development_confirmation_and_failure_boundaries(tmp_path, monkeypatch, outcome):
    name = "cyl2_test"
    recipe = dict(name=name, parent="cyl2_j01", legs=[4], tip_count=1)
    monkeypatch.setattr(controller, "ROOT", tmp_path/"controller")
    monkeypatch.setattr(controller, "RECIPES", [recipe])
    monkeypatch.setattr(controller.solid, "OUT", tmp_path/"pilot")
    monkeypatch.setattr(controller.confirmation, "ROOT", tmp_path/"confirmation")
    monkeypatch.setattr(controller.search, "frozen_policy", lambda: {})
    monkeypatch.setattr(controller, "ensure_candidate", lambda recipe: None)
    monkeypatch.setattr(controller, "failure_audit", lambda rows: [])
    monkeypatch.setattr(controller.signal, "signal", lambda *args: None)
    monkeypatch.setattr(controller.sys, "argv", ["repeat", "--target-passing-maps", "1"])
    stored, calls = {}, []
    pilot = tmp_path/"pilot"/name/"raw.csv"
    confirmed = tmp_path/"confirmation"/name/"raw.csv"
    monkeypatch.setattr(controller, "read_rows", lambda path: list(stored.get(Path(path), [])))
    def fake_execute(script, arguments, log_path):
        calls.append(script)
        if script == "cylinder_solid_campaign.py":
            run = int(arguments[arguments.index("--run")+1])
            generated = [row(mode, run, success=(mode != "sector")) for mode in controller.confirmation.MODES]
            if outcome == "invalid":
                generated[0]["resource_valid"] = False
            stored[pilot] = stored.get(pilot, [])+generated
        else:
            runs = controller.confirmation.RUNS if outcome == "pass" else [101]
            stored[confirmed] = [row(mode, run, success=(mode != "sector"))
                                 for run in runs for mode in controller.confirmation.MODES]
            if outcome == "reference_failure":
                stored[confirmed][0]["success"] = False
    monkeypatch.setattr(controller, "execute", fake_execute)
    if outcome == "invalid":
        with pytest.raises(RuntimeError, match="Invalid"):
            controller.main()
    else:
        controller.main()
    status = json.loads((tmp_path/"controller/status.json").read_text())
    if outcome == "pass":
        assert status["state"] == "TARGET_OBSERVED"
        assert status["passed"] == [name]
        assert len(stored[pilot]) == 9 and len(stored[confirmed]) == 60
    elif outcome == "reference_failure":
        assert status["state"] == "RECIPE_FAMILY_EXHAUSTED_REQUIRES_NEW_DESIGN"
        assert status["passed"] == []
        assert len(stored[confirmed]) == 3
        assert stored[confirmed][0]["success"] is False
    else:
        assert status["state"] == "STOPPED_FOR_DIAGNOSIS"
        assert len(calls) == 1 and confirmed not in stored
    if outcome != "invalid":
        assert calls.count("confirm_cylinder_search_n20.py") == 1
