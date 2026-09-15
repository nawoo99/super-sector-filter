#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <type_traits>

namespace rog_map {
namespace snapshot_neighborhood_cache {

using Index = std::array<int, 3>;

// All non-snapshot state read by the integer occupancy predicate. Float queries
// bypass this cache: their physical virtual bounds and division are different.
struct PredicateIdentity {
    const void* map_instance{nullptr};
    int ground_index{0};
    int ceiling_index{0};
    int safe_margin{0};

    bool operator==(const PredicateIdentity& other) const noexcept {
        return map_instance == other.map_instance && ground_index == other.ground_index &&
               ceiling_index == other.ceiling_index && safe_margin == other.safe_margin;
    }
};

// Exact, direct-mapped per-thread cache of "any neighbor occupied" for one
// center index. A collision replaces one entry, never approximates an answer.
// The caller must use immutable snapshots and the matching neighbors/predicate
// throughout a line, call beginLine once per line, and retain the final C4
// publication check before accepting a free line. This cache owns no map data.
template <std::size_t Capacity = 4096, std::size_t MaxNeighbors = 512,
          typename Epoch = std::uint32_t>
class Cache {
    static_assert(Capacity && (Capacity & (Capacity - 1)) == 0, "capacity must be a power of two");
    static_assert(std::is_integral<Epoch>::value && std::is_unsigned<Epoch>::value,
                  "epoch must be an unsigned integer");
    static_assert(!std::is_same<Epoch, bool>::value, "bool is not a usable epoch counter");

    struct Entry {
        Index center{};
        Epoch epoch{0};
        bool occupied{false};
    };

public:
    static constexpr std::size_t capacity = Capacity;
    static constexpr std::size_t max_neighbors = MaxNeighbors;

    template <typename Snapshot, typename Neighbors>
    bool beginLine(const std::shared_ptr<const Snapshot>& snapshot,
                   const std::uint64_t version, const PredicateIdentity& identity,
                   const Neighbors& neighbors) {
        active_ = false;
        if (!snapshot || neighbors.empty() || neighbors.size() > MaxNeighbors) {
            // Bounded memory: unusually large neighbor lists are evaluated
            // directly. Clear context instead of retaining any map ownership.
            resetContext();
            return false;
        }

        bool changed = !has_context_ || owner_.owner_before(snapshot) ||
                       snapshot.owner_before(owner_) || snapshot.get() != snapshot_address_ ||
                       version != version_ || !(identity == identity_) ||
                       neighbors.size() != neighbor_count_;
        if (!changed) {
            for (std::size_t n = 0; n < neighbors.size(); ++n) {
                for (int axis = 0; axis < 3; ++axis) {
                    if (neighbors[n][axis] != neighbors_[n][axis]) {
                        changed = true;
                        break;
                    }
                }
                if (changed) break;
            }
        }

        if (changed) {
            advanceEpoch();
            // Weak control-block identity prevents raw-address ABA reuse while
            // avoiding strong ownership of obsolete snapshots/pages.
            owner_ = snapshot;
            snapshot_address_ = snapshot.get();
            version_ = version;
            identity_ = identity;
            neighbor_count_ = neighbors.size();
            for (std::size_t n = 0; n < neighbors.size(); ++n) {
                for (int axis = 0; axis < 3; ++axis) neighbors_[n][axis] = neighbors[n][axis];
            }
            has_context_ = true;
        }
        active_ = true;
        return true;
    }

    template <typename EvaluateNeighborhood>
    bool anyOccupied(const Index& center, EvaluateNeighborhood&& evaluate) {
        if (!active_) return evaluate();
        auto& entry = entries_[bucketFor(center)];
        if (entry.epoch == epoch_ && entry.center == center) return entry.occupied;
        const bool occupied = evaluate();
        entry.center = center;
        entry.epoch = epoch_;
        entry.occupied = occupied;
        return occupied;
    }

    static std::size_t bucketFor(const Index& center) noexcept {
        // Defined unsigned arithmetic for negative coordinates and overflow.
        std::uint32_t hash = static_cast<std::uint32_t>(center[0]) * 73856093U ^
                             static_cast<std::uint32_t>(center[1]) * 19349663U ^
                             static_cast<std::uint32_t>(center[2]) * 83492791U;
        hash ^= hash >> 16U;
        hash *= 0x7feb352dU;
        hash ^= hash >> 15U;
        return static_cast<std::size_t>(hash) & (Capacity - 1U);
    }

private:
    void advanceEpoch() noexcept {
        epoch_ = static_cast<Epoch>(epoch_ + Epoch{1});
        if (epoch_ == 0) {
            // No stale entry can survive epoch wrap. Narrow epochs in tests
            // exercise the identical path without billions of map updates.
            for (auto& entry : entries_) entry.epoch = 0;
            epoch_ = 1;
        }
    }

    void resetContext() noexcept {
        if (has_context_) advanceEpoch();
        has_context_ = false;
        owner_.reset();
        snapshot_address_ = nullptr;
        neighbor_count_ = 0;
    }

    std::array<Entry, Capacity> entries_{};
    std::array<Index, MaxNeighbors> neighbors_{};
    std::weak_ptr<const void> owner_;
    const void* snapshot_address_{nullptr};
    PredicateIdentity identity_{};
    std::uint64_t version_{0};
    std::size_t neighbor_count_{0};
    Epoch epoch_{1};
    bool has_context_{false};
    bool active_{false};
};

// Same C4 traversal with the neighbor loop factored into a whole-neighborhood
// callback. This lets callers cache the exact boolean without touching the
// unchanged RayCaster or the separate float occupancy path.
template <typename RayCaster, typename Point, typename FloatOccupied,
          typename PointToIndex, typename NeighborhoodOccupied, typename StillCurrent>
bool isLineFree(RayCaster& raycaster, const Point& start_point,
                const double max_distance, const bool has_neighbors,
                FloatOccupied&& float_occupied, PointToIndex&& point_to_index,
                NeighborhoodOccupied&& neighborhood_occupied, StillCurrent&& still_current) {
    Point ray_point;
    while (raycaster.step(ray_point)) {
        if (max_distance > 0 && (ray_point - start_point).norm() > max_distance) return false;
        if (has_neighbors) {
            if (neighborhood_occupied(point_to_index(ray_point))) return false;
        } else if (float_occupied(ray_point)) {
            return false;
        }
    }
    return still_current();
}

}  // namespace snapshot_neighborhood_cache
}  // namespace rog_map
