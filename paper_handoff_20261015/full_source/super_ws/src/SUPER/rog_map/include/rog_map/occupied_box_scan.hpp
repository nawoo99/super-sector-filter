#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>

namespace rog_map {
namespace occupied_box_scan {

using Index = std::array<int, 3>;

// Match ROGMap::snapshotHash's signed ring mapping exactly. The caller uses
// odd dimensions (size == 2 * half_size + 1), as the existing map does.
inline int localCoordinate(const int global, const int size, const int half_size) {
    int local = global % size;
    if (local > half_size) {
        local -= size;
    } else if (local < -half_size) {
        local += size;
    }
    return local + half_size;
}

inline unsigned trailingZeros(const std::uint64_t nonzero_word) {
#if defined(__GNUC__) || defined(__clang__)
    return static_cast<unsigned>(__builtin_ctzll(nonzero_word));
#else
    unsigned count = 0;
    std::uint64_t remaining = nonzero_word;
    while ((remaining & std::uint64_t{1}) == 0) {
        ++count;
        remaining >>= 1U;
    }
    return count;
#endif
}

// Visit occupied global indices in exactly the existing i/j/k triple-loop
// order. Bounds are [begin, end), deliberately independent of physical-box
// rounding and clipping: raw boxSearch supplies min_id + 1 and max_id.
// read_word(word_id) accesses the already-pinned snapshot without acquiring
// another shared_ptr. emit(i, j, k) is invoked only for occupied bits.
//
// This helper does not change map versions, map/virtual-height clipping,
// empty-map handling, query types, output point conversion, or CIRI order.
// It must not be used to silently replace UNKNOWN/FRONTIER query semantics.
template <typename ReadWord, typename Emit>
void forEachOccupied(const Index &begin, const Index &end,
                     const Index &size, const Index &half_size,
                     ReadWord &&read_word, Emit &&emit) {
    if (begin[0] >= end[0] || begin[1] >= end[1] || begin[2] >= end[2]) {
        return;
    }

    const int yz_stride = size[1] * size[2];
    int local_x = localCoordinate(begin[0], size[0], half_size[0]);
    const int first_local_y = localCoordinate(begin[1], size[1], half_size[1]);
    const int first_local_z = localCoordinate(begin[2], size[2], half_size[2]);
    for (int i = begin[0]; i < end[0]; ++i) {
        const int x_offset = local_x * yz_stride;
        int local_y = first_local_y;
        for (int j = begin[1]; j < end[1]; ++j) {
            const int row_offset = x_offset + local_y * size[2];
            int global_z = begin[2];
            int local_z = first_local_z;
            while (global_z < end[2]) {
                // Ring wrap is not necessarily a word or page boundary.
                int span_remaining = std::min(end[2] - global_z,
                                              size[2] - local_z);
                int hash = row_offset + local_z;
                while (span_remaining > 0) {
                    const unsigned bit_offset = static_cast<unsigned>(hash & 63);
                    const int bits = std::min(span_remaining,
                                              static_cast<int>(64U - bit_offset));
                    std::uint64_t occupied = read_word(
                            static_cast<std::size_t>(hash) >> 6U) >> bit_offset;
                    // Avoid shifting by 64, which is undefined in C++.
                    if (bits < 64) {
                        occupied &= (std::uint64_t{1} << bits) - 1U;
                    }
                    while (occupied != 0) {
                        const unsigned bit = trailingZeros(occupied);
                        emit(i, j, global_z + static_cast<int>(bit));
                        occupied &= occupied - 1U;
                    }
                    hash += bits;
                    global_z += bits;
                    span_remaining -= bits;
                }
                local_z = 0;
            }
            if (++local_y == size[1]) {
                local_y = 0;
            }
        }
        if (++local_x == size[0]) {
            local_x = 0;
        }
    }
}

}  // namespace occupied_box_scan
}  // namespace rog_map
