#pragma once
#include <super_utils/type_utils.hpp>
#include <algorithm>
#include <cmath>
#include <limits>

namespace path_search {
// A search-only flag: legacy requests never set it. The stopped recovery
// uses 6-connected edges rather than assuming diagonal free endpoints prove
// the segment between them is free.
constexpr int AXIS_ALIGNED_RECOVERY = (1 << 7);

// Closed-voxel supercover of a segment, including edge/corner tangencies.
// Callback receives voxel centres and implements the *inflated* map policy.
// This is a conservative shortcut prefilter, never a flight certificate.
template<class FreeCell>
bool recoverySegmentFree(const super_utils::Vec3f& start,
                         const super_utils::Vec3f& end,
                         const double resolution, FreeCell&& free_cell) {
    if (!start.array().isFinite().all() || !end.array().isFinite().all() ||
        !std::isfinite(resolution) || resolution <= 0.0) return false;
    constexpr double epsilon = 1.0e-8;
    const double index_limit = double(std::numeric_limits<int>::max())-2.0;
    if (start.cwiseAbs().maxCoeff()/resolution >= index_limit ||
        end.cwiseAbs().maxCoeff()/resolution >= index_limit) return false;
    const super_utils::Vec3f delta = end-start;
    const super_utils::Vec3i first =
            ((start.cwiseMin(end).array()-epsilon)/resolution).floor().cast<int>();
    const super_utils::Vec3i last =
            ((start.cwiseMax(end).array()+epsilon)/resolution).floor().cast<int>();
    const auto volume = (last-first+super_utils::Vec3i::Ones()).cast<double>().prod();
    if (!std::isfinite(volume) || volume > 1000000.0) return false;
    for (int x = first.x(); x <= last.x(); ++x)
        for (int y = first.y(); y <= last.y(); ++y)
            for (int z = first.z(); z <= last.z(); ++z) {
                const super_utils::Vec3i index(x,y,z);
                const super_utils::Vec3f low = index.cast<double>()*resolution;
                const super_utils::Vec3f high = low+super_utils::Vec3f::Constant(resolution);
                double entry=0.0, exit=1.0;
                bool intersects=true;
                for (int axis=0; axis<3; ++axis) {
                    if (std::abs(delta(axis)) <= epsilon) {
                        if (start(axis)<low(axis)-epsilon || start(axis)>high(axis)+epsilon)
                            intersects=false;
                    } else {
                        const double a=(low(axis)-epsilon-start(axis))/delta(axis);
                        const double b=(high(axis)+epsilon-start(axis))/delta(axis);
                        entry=std::max(entry,std::min(a,b));
                        exit=std::min(exit,std::max(a,b));
                        if (entry>exit) intersects=false;
                    }
                    if (!intersects) break;
                }
                if (intersects && !free_cell(low+super_utils::Vec3f::Constant(0.5*resolution)))
                    return false;
            }
    return true;
}
}
