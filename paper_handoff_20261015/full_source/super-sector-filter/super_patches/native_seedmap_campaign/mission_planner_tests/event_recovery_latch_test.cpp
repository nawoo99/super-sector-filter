#include <mission_planner/event_recovery_latch.hpp>
#include <cassert>
#include <iostream>

int main() {
  native_sector::EventRecoveryLatch gate;
  assert(!gate.active && !gate.requestClose());
  gate.start(10, 1000);
  // Pre-event queued frames, missing stamps, and old source stamps fail closed.
  assert(!gate.select(10, 1100));
  assert(!gate.select(11, 0));
  assert(!gate.select(11, 999));
  assert(!gate.select(11, 1000));
  assert(gate.select(11, 1100));
  assert(!gate.acknowledge(1000, 9, true));
  assert(!gate.acknowledge(1100, 9, false));
  assert(!gate.acknowledge(1100, 0, true));
  assert(gate.active && !gate.committed);
  // Even a real committed map cannot close without the planner's release.
  assert(!gate.acknowledge(1100, 9, true));
  assert(gate.active && gate.committed);
  assert(gate.requestClose() && !gate.active);
  // Planner completion arriving before the frontend's ACK remains latched.
  gate.start(20, 2000);
  assert(gate.select(21, 2100));
  assert(!gate.requestClose() && gate.active);
  assert(!gate.acknowledge(1100, 9, true));
  assert(gate.acknowledge(2100, 10, true) && !gate.active);
  // Lost cloud/retry: an ACK for a superseded token cannot release the gate.
  gate.start(30, 3000);
  assert(gate.select(31, 3100));
  assert(gate.select(32, 3200));
  assert(!gate.requestClose());
  assert(!gate.acknowledge(3100, 11, true));
  assert(gate.active);
  assert(gate.acknowledge(3200, 12, true));
  // No path / no release: remain open indefinitely, regardless of elapsed time.
  gate.start(40, 4000);
  assert(gate.select(41, 4100));
  assert(!gate.acknowledge(4100, 13, true));
  for (int i = 0; i < 10000; ++i) assert(gate.active);
  // A subsequent guard episode invalidates all evidence from the prior one.
  gate.start(50, 5000);
  assert(!gate.committed && !gate.close_requested);
  assert(!gate.requestClose());
  assert(!gate.acknowledge(4100, 13, true));
  assert(gate.active && gate.cycle == 5);
  std::cout << "event recovery: stale/absent/no-commit/reordered/retry/no-path/new-cycle checks passed\n";
}
