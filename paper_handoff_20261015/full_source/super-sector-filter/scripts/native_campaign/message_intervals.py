"""Bounded observational message intervals, not producer callback latency."""
from array import array


def distribution(values):
    if not values:
        return None
    ordered = sorted(values)
    def percentile(fraction):
        position = (len(ordered) - 1) * fraction
        low = int(position)
        high = min(low + 1, len(ordered) - 1)
        return (ordered[low] + (ordered[high] - ordered[low]) * (position - low)) / 1e6
    return dict(min_ms=ordered[0] / 1e6, p50_ms=percentile(.50),
                p95_ms=percentile(.95), p99_ms=percentile(.99), max_ms=ordered[-1] / 1e6)


class MessageIntervals:
    def __init__(self, capacity=32768, event_capacity=128, event_threshold_ns=20_000_000):
        if capacity < 1:
            raise ValueError('capacity must be positive')
        if event_capacity < 1 or event_threshold_ns < 1:
            raise ValueError('event limits must be positive')
        self.capacity = capacity
        self.event_capacity = event_capacity
        self.event_threshold_ns = event_threshold_ns
        self.gap_events = []
        self.gap_events_total = 0
        self.max_header_context = self.max_receipt_context = None
        self.last_epoch = None
        self.count = self.repeated_stamps = self.backward_stamps = 0
        self.backward_receipts = self.dropped_intervals = 0
        self.first_receipt = self.last_receipt = self.last_stamp = None
        self.stamps = array('q')
        self.receipts = array('q')

    def observe(self, stamp_ns, receipt_ns, receipt_epoch_ns=None):
        self.count += 1
        if self.last_stamp is not None:
            stamp_delta = stamp_ns - self.last_stamp
            receipt_delta = receipt_ns - self.last_receipt
            self.repeated_stamps += stamp_delta == 0
            self.backward_stamps += stamp_delta < 0
            self.backward_receipts += receipt_delta < 0
            # Never subtract different clock domains. Epoch is correlation
            # metadata only; existing receipt intervals remain monotonic.
            header_max = (self.max_header_context is None or
                          stamp_delta > self.max_header_context['header_delta_ns'])
            receipt_max = (self.max_receipt_context is None or
                           receipt_delta > self.max_receipt_context['receipt_delta_ns'])
            long_gap = max(stamp_delta, receipt_delta) > self.event_threshold_ns
            if header_max or receipt_max or long_gap:
                context = dict(message_index=self.count, previous_stamp_ns=self.last_stamp,
                               stamp_ns=stamp_ns, previous_receipt_ns=self.last_receipt,
                               receipt_ns=receipt_ns, previous_receipt_epoch_ns=self.last_epoch,
                               receipt_epoch_ns=receipt_epoch_ns,
                               header_delta_ns=stamp_delta, receipt_delta_ns=receipt_delta)
                if header_max:
                    self.max_header_context = context
                if receipt_max:
                    self.max_receipt_context = context
                if long_gap:
                    self.gap_events_total += 1
                    if len(self.gap_events) < self.event_capacity:
                        self.gap_events.append(context)
            if len(self.stamps) < self.capacity:
                self.stamps.append(stamp_delta)
                self.receipts.append(receipt_delta)
            else:
                self.dropped_intervals += 1
        else:
            self.first_receipt = receipt_ns
        self.last_stamp, self.last_receipt = stamp_ns, receipt_ns
        self.last_epoch = receipt_epoch_ns

    def summary(self):
        duration = ((self.last_receipt - self.first_receipt) / 1e9
                    if self.count > 1 else 0.)
        return dict(messages=self.count, intervals_retained=len(self.stamps),
                    intervals_dropped=self.dropped_intervals,
                    receipt_duration_s=duration,
                    mean_received_hz=(self.count - 1) / duration if duration > 0 else None,
                    repeated_stamps=self.repeated_stamps,
                    backward_stamps=self.backward_stamps,
                    backward_receipts=self.backward_receipts,
                    header_interval=distribution(self.stamps),
                    receipt_interval=distribution(self.receipts),
                    gap_event_threshold_ns=self.event_threshold_ns,
                    gap_events=self.gap_events, gap_events_total=self.gap_events_total,
                    gap_events_dropped=self.gap_events_total - len(self.gap_events),
                    max_header_context=self.max_header_context,
                    max_receipt_context=self.max_receipt_context,
                    context_scope='All observed intervals including quantile overflow; epoch metadata is not used for interval arithmetic',
                    quantile_scope='first bounded intervals; inspect intervals_dropped',
                    scope='Observed messages; includes DDS/observer jitter and intentional command holds, not producer callback latency')
