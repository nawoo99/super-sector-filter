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
    def __init__(self, capacity=32768):
        if capacity < 1:
            raise ValueError('capacity must be positive')
        self.capacity = capacity
        self.count = self.repeated_stamps = self.backward_stamps = 0
        self.backward_receipts = self.dropped_intervals = 0
        self.first_receipt = self.last_receipt = self.last_stamp = None
        self.stamps = array('q')
        self.receipts = array('q')

    def observe(self, stamp_ns, receipt_ns):
        self.count += 1
        if self.last_stamp is not None:
            stamp_delta = stamp_ns - self.last_stamp
            receipt_delta = receipt_ns - self.last_receipt
            self.repeated_stamps += stamp_delta == 0
            self.backward_stamps += stamp_delta < 0
            self.backward_receipts += receipt_delta < 0
            if len(self.stamps) < self.capacity:
                self.stamps.append(stamp_delta)
                self.receipts.append(receipt_delta)
            else:
                self.dropped_intervals += 1
        else:
            self.first_receipt = receipt_ns
        self.last_stamp, self.last_receipt = stamp_ns, receipt_ns

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
                    quantile_scope='first bounded intervals; inspect intervals_dropped',
                    scope='Observed messages; includes DDS/observer jitter and intentional command holds, not producer callback latency')
