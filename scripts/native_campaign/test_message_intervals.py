import pytest
from message_intervals import MessageIntervals


def test_empty_and_single():
    counter = MessageIntervals()
    assert counter.summary()['header_interval'] is None
    counter.observe(0, 5)
    assert counter.summary()['messages'] == 1
    assert counter.summary()['mean_received_hz'] is None


def test_100_hz_and_distinct_receipt_jitter():
    counter = MessageIntervals()
    for n, receipt in enumerate([0, 9, 21, 30]):
        counter.observe(n * 10_000_000, receipt * 1_000_000)
    out = counter.summary()
    assert out['mean_received_hz'] == 100
    assert out['header_interval']['p99_ms'] == 10
    assert out['receipt_interval']['min_ms'] == 9
    assert out['receipt_interval']['max_ms'] == 12


def test_repeat_backward_and_overflow_are_visible():
    counter = MessageIntervals(2)
    for stamp, receipt in [(10, 10), (10, 20), (9, 30), (12, 29)]:
        counter.observe(stamp, receipt)
    out = counter.summary()
    assert out['repeated_stamps'] == 1
    assert out['backward_stamps'] == 1
    assert out['backward_receipts'] == 1
    assert out['intervals_dropped'] == 1
    assert out['intervals_retained'] == 2
    assert out['messages'] == 4


def test_invalid_capacity():
    with pytest.raises(ValueError):
        MessageIntervals(0)
