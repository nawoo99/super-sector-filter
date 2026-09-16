#pragma once

// OUTSIDE-RUNTIME prototype, deliberately not a delivery guarantee.
// Caller serializes all access on the static-map callback group, polls at10Hz,
// obtains matched_count from the publisher, and passes current graph GIDs.
// Reliable/TransientLocal canonical readers use middleware retained history;
// this edge-triggered send only assists unchanged volatile legacy readers.
#include <algorithm>
#include <cstddef>
#include <set>
#include <string>

namespace static_map_edge {
struct Decision {
  bool publish{false};
  bool initial{false};
  bool new_reader{false};
  bool unsupported{false};
};

class Policy {
 public:
  static constexpr std::size_t max_readers = 64;
  Decision observe(const std::set<std::string>& reader_gids,
                   const std::size_t matched_count) {
    if (reader_gids.size() > max_readers || matched_count > max_readers ||
        std::any_of(reader_gids.begin(), reader_gids.end(),
                    [](const auto& gid) { return gid.empty(); })) {
      return {false, false, false, true};
    }
    if (!initialized_) {
      initialized_ = true;
      previous_ = reader_gids;
      // The initial publish creates durable writer history even with no reader.
      // A not-yet-matched existing reader still gets a later compatibility edge.
      pending_legacy_edge_ = !reader_gids.empty() && matched_count == 0;
      return {true, true, !reader_gids.empty(), false};
    }
    bool joined = false;
    for (const auto& gid : reader_gids) {
      joined = joined || previous_.count(gid) == 0;
    }
    pending_legacy_edge_ = pending_legacy_edge_ || joined;
    previous_ = reader_gids;
    if (reader_gids.empty()) pending_legacy_edge_ = false;
    if (pending_legacy_edge_ && matched_count != 0) {
      pending_legacy_edge_ = false;
      return {true, false, true, false};
    }
    return {};
  }

 private:
  bool initialized_{false};
  bool pending_legacy_edge_{false};
  std::set<std::string> previous_;
};
}  // namespace static_map_edge
