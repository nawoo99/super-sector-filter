#pragma once

#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <algorithm>
#include <vector>

namespace perfect_drone::static_pc_latched {

// PCL1.12 PointXYZI initializes XYZ, homogeneous data[3] and intensity, but
// not its final12 bytes. toPCLPointCloud2 copies those bytes too. Only the new
// one-shot wire copy is canonicalized; the renderer cloud and legacy path stay
// untouched. The caller verifies exact XYZI field metadata before calling.
inline void canonicalizeXyziTailPadding(std::vector<std::uint8_t>& data,
                                      std::uint32_t point_step) {
    if (point_step != 32 || data.empty() || data.size() % point_step != 0)
        throw std::invalid_argument("expected complete32-byte PointXYZI wire layout");
    for (std::size_t offset = 0; offset < data.size(); offset += point_step)
        std::fill(data.begin() + offset + 20, data.begin() + offset + 32, 0);
}

// Explicit publisher AND reader migration; legacy paths remain the default.
inline bool parseEnabled(const char* setting, bool durable, int poll_ms,
                         bool two_phase, const char* cached_executor) {
    if (!setting || std::strcmp(setting, "0") == 0) return false;
    if (std::strcmp(setting, "1") != 0)
        throw std::invalid_argument("SUPER_STATIC_PC_LATCHED_ONCE must be 0 or 1");
    if (!durable || poll_ms != 1 || two_phase ||
        (cached_executor && std::strcmp(cached_executor, "0") != 0))
        throw std::invalid_argument(
            "SUPER_STATIC_PC_LATCHED_ONCE=1 requires durable static geometry, "
            "legacy poll parameter1, two-phase OFF and cached executor OFF");
    return true;
}

// Constructor owns publication; afterwards this state is immutable, including
// during existing periodic sensor summaries. Poll-violation evidence is kept
// separately as an atomic by the owning node. No reporting timer is introduced.
struct Evidence {
    std::uint64_t publications{0};
    std::uint64_t points{0};
    std::uint64_t bytes{0};
    std::int64_t stamp_ns{0};

    void published(std::uint64_t point_count, std::uint64_t byte_count,
                   std::int64_t stamp) {
        if (publications != 0 || point_count == 0 || byte_count == 0 || stamp < 0)
            throw std::logic_error("invalid or duplicate latched static publication");
        points = point_count;
        bytes = byte_count;
        stamp_ns = stamp;
        ++publications;
    }
};

}  // namespace perfect_drone::static_pc_latched
