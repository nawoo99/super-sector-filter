#pragma once

#include <cstddef>

namespace fsm {

// The path accumulator is independent of this publication-only policy. A
// subscriber arriving later must still receive the complete pose history.
constexpr bool visualizedPathPublicationAllowed(
        const bool skip_unobserved,
        const std::size_t subscription_count,
        const std::size_t intra_process_subscription_count) noexcept {
    return !skip_unobserved || subscription_count != 0 ||
           intra_process_subscription_count != 0;
}

}  // namespace fsm
