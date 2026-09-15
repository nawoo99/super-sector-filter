"""Artifact-only policy model; not imported by the simulator.

Future caller schedules an actual 100 ms timer, replacing the 1 ms timer.
Only /global_pc publication decisions are affected, never acquired LiDAR scans.
Publication remains the current complete static map and current QoS. A decision
is acknowledged only after the publication call succeeds.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    publish: bool
    subscriber_change: bool
    bootstrap: bool


class StaticPcPolicy:
    def __init__(self, bootstrap_after_ns=5_000_000_000):
        self.bootstrap_after_ns = bootstrap_after_ns
        self.last_subscribers = 0
        self.bootstrap_done = False
        self.pending_subscriber_publish = False

    def observe(self, elapsed_ns, subscribers):
        if elapsed_ns < 0 or subscribers < 0:
            raise ValueError('elapsed time and subscriber count must be nonnegative')
        if subscribers > 0 and subscribers != self.last_subscribers:
            self.pending_subscriber_publish = True
        self.last_subscribers = subscribers
        bootstrap = not self.bootstrap_done and elapsed_ns >= self.bootstrap_after_ns
        return Decision(self.pending_subscriber_publish or bootstrap,
                        self.pending_subscriber_publish, bootstrap)

    def published(self, decision):
        if not decision.publish:
            raise ValueError('cannot acknowledge a non-publication decision')
        if decision.subscriber_change:
            self.pending_subscriber_publish = False
        if decision.bootstrap:
            self.bootstrap_done = True
