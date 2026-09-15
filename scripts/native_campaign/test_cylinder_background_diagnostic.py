import pytest
from cylinder_background_diagnostic import gap_metrics


def test_gap_includes_silent_tail_and_warmup_boundary():
    result=gap_metrics([1,9,10.2,10.4],10,20)
    assert result['samples']==2
    assert result['max_gap_s']==pytest.approx(9.6)
    assert result['hz']==.2


def test_no_ack_is_full_window_gap():
    assert gap_metrics([],10,20)==dict(samples=0,max_gap_s=10,hz=0)
    assert gap_metrics([],20,10)==dict(samples=0,max_gap_s=None,hz=None)
