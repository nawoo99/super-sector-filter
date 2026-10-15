#pragma once

#include <cstddef>

namespace super_planner {
namespace sequence_guards {

// Returning size() means no usable element. Callers must reject this result
// before indexing; in particular, an all-occupied guide has no corridor seed.
template <typename Sequence, typename Occupied>
std::size_t firstUnoccupiedIndex(const Sequence& path, Occupied&& occupied) {
    std::size_t index = 0;
    while (index < path.size() && occupied(path[index])) ++index;
    return index;
}

// Backup construction drops the last (outside) sample, then uses the previous
// sample as its seed. Reject an empty/singleton sequence without mutating it.
template <typename Sequence>
bool discardTrailingSampleKeepingSeed(Sequence& samples) {
    if (samples.size() < 2) return false;
    samples.pop_back();
    return true;
}

}  // namespace sequence_guards
}  // namespace super_planner
