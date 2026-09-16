#pragma once

#include <cstddef>
#include <vector>

namespace path_search {
namespace parent_chain {

enum class Result { SUCCESS, NULL_START, NODE_LIMIT, CYCLE };

inline const char* resultName(const Result result) noexcept {
    switch (result) {
        case Result::SUCCESS: return "SUCCESS";
        case Result::NULL_START: return "NULL_START";
        case Result::NODE_LIMIT: return "NODE_LIMIT";
        case Result::CYCLE: return "CYCLE";
    }
    return "UNKNOWN";
}

// The caller owns stable, live nodes for this operation (the planner's replan
// mutex serializes its A* searches). Validate the chain without allocating
// before copying it. A malformed cycle can otherwise append until OOM. This
// structural check intentionally imposes no new cost/round/geometry semantics.
template <typename Node>
Result reconstruct(Node* current, const std::size_t max_nodes,
                   std::vector<Node*>& path) {
    path.clear();
    if (current == nullptr) return Result::NULL_START;

    Node* slow = current;
    Node* fast = current;
    std::size_t count = 0;
    while (slow != nullptr) {
        if (count >= max_nodes) return Result::NODE_LIMIT;
        ++count;
        slow = slow->father_ptr;
        if (fast != nullptr) fast = fast->father_ptr;
        if (fast != nullptr) fast = fast->father_ptr;
        if (slow != nullptr && slow == fast) return Result::CYCLE;
    }

    path.reserve(count);
    for (std::size_t i = 0; i < count; ++i) {
        path.push_back(current);
        current = current->father_ptr;
    }
    return Result::SUCCESS;
}

}  // namespace parent_chain
}  // namespace path_search
