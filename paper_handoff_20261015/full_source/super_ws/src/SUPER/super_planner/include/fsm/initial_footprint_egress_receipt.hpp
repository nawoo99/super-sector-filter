#pragma once

#include <array>
#include <cmath>
#include <cstdint>
#include <vector>

namespace super_planner::initial_egress {

using Point = std::array<double, 3>;

// A receipt is part of one immutable trajectory generation, not a renewed
// permission to ignore everything near the current robot. Only the exact raw
// voxel centres ignored by the successful stopped-candidate check are retained.
struct Receipt {
    std::uint64_t generation{0};
    Point origin{};
    double start_wt{0.0}, from_tt{0.0}, until_tt{-1.0}, radius{0.0};
    std::vector<Point> occupied_centres;

    static double distanceSquared(const Point& a, const Point& b) noexcept {
        double d = 0.0;
        for (int i = 0; i < 3; ++i) d += (a[i] - b[i]) * (a[i] - b[i]);
        return d;
    }

    bool valid() const noexcept {
        if (!generation || !std::isfinite(start_wt) || !std::isfinite(from_tt) ||
            !std::isfinite(until_tt) || from_tt < 0.0 || until_tt <= from_tt ||
            !std::isfinite(radius) || radius <= 0.0 || occupied_centres.empty()) return false;
        for (double p : origin) if (!std::isfinite(p)) return false;
        for (const auto& hit : occupied_centres) {
            for (double p : hit) if (!std::isfinite(p)) return false;
            if (distanceSquared(hit, origin) > (radius + 1e-9) * (radius + 1e-9)) return false;
        }
        return true;
    }

    bool usable(std::uint64_t current_generation, double trajectory_start,
                double tt) const noexcept {
        return generation == current_generation && start_wt == trajectory_start &&
               valid() && std::isfinite(tt) && tt >= from_tt && tt <= until_tt;
    }

    bool contains(const Point& hit) const noexcept {
        for (const auto& initial : occupied_centres)
            if (distanceSquared(hit, initial) <= 1e-18) return true;
        return false;
    }

    void retain(const Point& hit) {
        if (!contains(hit)) occupied_centres.push_back(hit);
    }
};

}  // namespace super_planner::initial_egress
