#pragma once

#include <cstdint>

namespace native_sector {

// Immutable request sampled BEFORE sensor rendering. The same value must
// accompany the generated cloud, so a queued Sector scan cannot become a
// Full observation just because recovery opened while rendering was in flight.
struct SensorAcquisition {
  bool enabled{false};
  bool full{false};
  std::uint64_t cycle{0};
  double center_yaw_rad{0.0};
  double half_angle_deg{45.0};

  bool matches(bool current_full, std::uint64_t current_cycle) const {
    return enabled && full == current_full && cycle == current_cycle;
  }
};

}  // namespace native_sector
