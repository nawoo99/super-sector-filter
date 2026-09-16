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


def test_gap_context_keeps_clock_domains_separate():
    counter = MessageIntervals(event_threshold_ns=20_000_000)
    counter.observe(1_000_000_000, 200_000_000, 9_000_000_000)
    counter.observe(1_057_000_000, 260_000_000, 8_000_000_000)
    out = counter.summary()
    assert out['receipt_interval']['max_ms'] == 60
    assert out['header_interval']['max_ms'] == 57
    event = out['gap_events'][0]
    assert event['message_index'] == 2
    assert event['previous_receipt_epoch_ns'] == 9_000_000_000
    assert event['receipt_epoch_ns'] == 8_000_000_000
    assert event['receipt_delta_ns'] == 60_000_000
    assert out['max_receipt_context'] == event


def test_events_bounded_but_maximum_not_lost_on_overflow():
    counter = MessageIntervals(capacity=1, event_capacity=1, event_threshold_ns=20)
    for stamp in (0, 20, 50, 90):
        counter.observe(stamp, stamp)
    out = counter.summary()
    assert out['gap_events_total'] == 2
    assert out['gap_events_dropped'] == 1
    assert len(out['gap_events']) == 1
    assert out['max_header_context']['header_delta_ns'] == 40
    assert out['max_receipt_context']['receipt_epoch_ns'] is None
    assert out['intervals_dropped'] == 2


@pytest.mark.parametrize('options', [dict(event_capacity=0), dict(event_threshold_ns=0)])
def test_invalid_event_limits(options):
    with pytest.raises(ValueError):
        MessageIntervals(**options)
