#pragma once

#include <cstring>
#include <optional>

namespace native_sector {
// Default-off ablation: event Adaptive uses the same body-forward sector as
// Fixed Sector. It changes neither aperture nor the certified Full handshake.
inline bool exactBodyHeadingOptIn(const char* value) {
  return value && std::strcmp(value, "1") == 0;
}

inline bool usesVelocityHeading(bool velocity_mode, bool body_aligned_event) {
  return velocity_mode && !body_aligned_event;
}

inline double sectorHeading(bool velocity_mode, bool body_aligned_event,
                            const std::optional<double>& velocity_yaw,
                            double body_yaw) {
  return usesVelocityHeading(velocity_mode, body_aligned_event) && velocity_yaw
      ? *velocity_yaw : body_yaw;
}
}  // namespace native_sector
