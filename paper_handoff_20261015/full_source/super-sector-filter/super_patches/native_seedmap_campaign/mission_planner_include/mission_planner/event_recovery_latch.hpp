#pragma once

#include <cstdint>

namespace native_sector {
// Transport-independent, fail-closed half of the recovery handshake.
// Only the planner may request closure after certifying a NEW trajectory.
// Out-of-order delivery of that closure and the cloud ACK is supported.
class EventRecoveryLatch {
 public:
  void start(std::uint64_t last_input_sequence, std::uint64_t not_before_stamp) {
    ++cycle;
    active = true;
    close_requested = false;
    committed = false;
    boundary_sequence = last_input_sequence;
    boundary_stamp = not_before_stamp;
    refresh_stamp = 0;
    map_version = 0;
  }
  bool fresh(std::uint64_t sequence, std::uint64_t stamp) const {
    return active && sequence > boundary_sequence && stamp > boundary_stamp;
  }
  bool select(std::uint64_t sequence, std::uint64_t stamp) {
    if (!fresh(sequence, stamp) || committed) return false;
    refresh_stamp = stamp;
    return true;
  }
  bool acknowledge(std::uint64_t stamp, std::uint64_t version,
                   bool did_commit) {
    if (!active || !refresh_stamp || stamp != refresh_stamp ||
        !did_commit || version == 0) return false;
    committed = true;
    map_version = version;
    return maybeClose();
  }
  bool requestClose() {
    if (!active) return false;
    close_requested = true;
    return maybeClose();
  }

  bool active{false}, close_requested{false}, committed{false};
  std::uint64_t cycle{0}, boundary_sequence{0}, boundary_stamp{0};
  std::uint64_t refresh_stamp{0}, map_version{0};

 private:
  bool maybeClose() {
    if (!committed || !close_requested) return false;
    active = false;
    return true;
  }
};
}  // namespace native_sector
