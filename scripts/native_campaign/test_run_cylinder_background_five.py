import pytest
import run_cylinder_background_five as runner


def row(mode='full',run=1,success=True):
    return dict(map='cyl2_k02',run=run,mode=mode,success=success)


def test_validate_duplicate_and_out_of_plan_refused(monkeypatch):
    monkeypatch.setattr(runner,'quality_valid',lambda _:True)
    monkeypatch.setattr(runner.confirmation,'known_outcome',lambda _:True)
    runner.validate([row()],'cyl2_k02')
    for rows in ([row(),row()],[row(run=4)],[row(mode='unknown')]):
        with pytest.raises(RuntimeError):runner.validate(rows,'cyl2_k02')


def test_only_reference_failure_prevents_candidate_extension(monkeypatch):
    monkeypatch.setattr(runner.confirmation,'safe',lambda r:r['success'])
    assert not runner.reference_failed([row('sector',success=False),row('full')])
    assert runner.reference_failed([row('adaptive',success=False)])
    assert runner.reference_failed([row('full',success=False)])


def test_five_unique_predeclared_maps():
    assert len(runner.variants.RECIPES)==5
    assert len({r['name'] for r in runner.variants.RECIPES})==5
    assert all(r['name']!='cyl2_k01' for r in runner.variants.RECIPES)


def test_resume_finishes_partly_failed_block_but_does_not_start_next(monkeypatch):
    monkeypatch.setattr(runner.confirmation,'safe',lambda r:r['success'])
    rows=[row('sector',2),row('adaptive',2,False)]
    assert runner.may_start_or_finish_block(rows,2)
    assert not runner.may_start_or_finish_block(rows,3)


def test_zero_acks_can_be_real_liveness_failure():
    ack=dict(malformed=0,first_odom_epoch_s=1,last_odom_epoch_s=190,total_ack_samples=0)
    assert runner.ack_observer_valid(ack)
    ack['first_odom_epoch_s']=None
    assert not runner.ack_observer_valid(ack)
