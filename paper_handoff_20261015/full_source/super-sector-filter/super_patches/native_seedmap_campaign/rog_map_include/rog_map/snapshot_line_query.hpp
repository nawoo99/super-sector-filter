#pragma once

namespace rog_map {
namespace snapshot_line_query {

// Traverse one line against caller-owned, immutable occupancy predicates.
// The caller must pin one snapshot for this entire operation, initialize the
// same RayCaster as the legacy query, and preserve the distinct floating-point
// and integer occupancy semantics in its callbacks. No snapshot is cached here.
//
// The final callback must verify that the pinned publication is still current.
// A publication change rejects an otherwise-free line conservatively. This is
// not a guarantee against a publication that occurs after this function returns.
// Existing distance/occupancy failures return immediately without that callback.
template <typename RayCaster, typename Point, typename Neighbors,
          typename FloatOccupied, typename PointToIndex, typename IndexOccupied,
          typename StillCurrent>
bool isLineFree(RayCaster& raycaster, const Point& start_point,
                const double max_distance, const Neighbors& neighbors,
                FloatOccupied&& float_occupied, PointToIndex&& point_to_index,
                IndexOccupied&& index_occupied, StillCurrent&& still_current) {
    Point ray_point;
    while (raycaster.step(ray_point)) {
        if (max_distance > 0 && (ray_point - start_point).norm() > max_distance) {
            return false;
        }
        if (neighbors.empty()) {
            if (float_occupied(ray_point)) {
                return false;
            }
        } else {
            const auto ray_point_index = point_to_index(ray_point);
            for (const auto& neighbor : neighbors) {
                const decltype(ray_point_index) shifted = ray_point_index + neighbor;
                if (index_occupied(shifted)) {
                    return false;
                }
            }
        }
    }
    return still_current();
}

}  // namespace snapshot_line_query
}  // namespace rog_map
