#pragma once

#include <cmath>
#include <limits>
#include <utility>
#include <vector>

#include <utils/header/eigen_alias.hpp>

namespace traj_opt {

    using PassageFaceCandidates = std::vector<std::pair<int, int>>;

    inline PassageFaceCandidates buildPassageFaceCandidates(
            const super_utils::PolyhedronH &h_poly,
            const std::vector<uint8_t> &face_obstacle_flags,
            const double min_opposition_cos,
            const double min_horizontal_normal) {
        PassageFaceCandidates candidates;
        if (face_obstacle_flags.size() !=
            static_cast<std::size_t>(h_poly.rows())) {
            return candidates;
        }
        for (int i = 0; i < h_poly.rows(); ++i) {
            if (face_obstacle_flags[i] == 0) {
                continue;
            }
            super_utils::Vec3f first = h_poly.block<1, 3>(i, 0);
            const double first_norm = first.norm();
            if (first_norm <= 1.0e-9) {
                continue;
            }
            first /= first_norm;
            const double first_horizontal = first.head<2>().norm();
            if (first_horizontal < min_horizontal_normal) {
                continue;
            }
            const Eigen::Vector2d first_xy =
                    first.head<2>() / first_horizontal;
            for (int j = i + 1; j < h_poly.rows(); ++j) {
                if (face_obstacle_flags[j] == 0) {
                    continue;
                }
                super_utils::Vec3f second = h_poly.block<1, 3>(j, 0);
                const double second_norm = second.norm();
                if (second_norm <= 1.0e-9) {
                    continue;
                }
                second /= second_norm;
                const double second_horizontal = second.head<2>().norm();
                if (second_horizontal < min_horizontal_normal) {
                    continue;
                }
                const Eigen::Vector2d second_xy =
                        second.head<2>() / second_horizontal;
                if (first_xy.dot(second_xy) <= -min_opposition_cos) {
                    candidates.emplace_back(i, j);
                }
            }
        }
        return candidates;
    }

    struct PassageFacePair {
        bool valid{false};
        int first_face{-1};
        int second_face{-1};
        double first_clearance_m{0.0};
        double second_clearance_m{0.0};
        double width_m{0.0};
        double imbalance_m{0.0};
        super_utils::Vec3f first_normal{super_utils::Vec3f::Zero()};
        super_utils::Vec3f second_normal{super_utils::Vec3f::Zero()};
        super_utils::Vec3f imbalance_gradient{
                super_utils::Vec3f::Zero()};
    };

    // Select the narrowest pair of approximately opposing, predominantly
    // horizontal SFC faces containing `position`. Plane interiors use
    // n.dot(p)+d <= 0. Open space, floor/ceiling pairs, and one-sided walls
    // therefore do not create an artificial centering target.
    inline PassageFacePair findPassageFacePair(
            const super_utils::PolyhedronH &h_poly,
            const PassageFaceCandidates &candidates,
            const super_utils::Vec3f &position,
            const double max_width_m,
            const double inside_tolerance_m = 0.05) {
        PassageFacePair best;
        if (max_width_m <= 0.0 || h_poly.rows() < 2 ||
            !position.array().isFinite().all()) {
            return best;
        }
        double best_width = std::numeric_limits<double>::infinity();
        for (const auto &[i, j] : candidates) {
            super_utils::Vec3f first = h_poly.block<1, 3>(i, 0);
            const double first_norm = first.norm();
            if (first_norm <= 1.0e-9) {
                continue;
            }
            first /= first_norm;
            const double first_clearance = -(
                    first.dot(position) + h_poly(i, 3) / first_norm);
            if (first_clearance < -inside_tolerance_m) {
                continue;
            }
            super_utils::Vec3f second = h_poly.block<1, 3>(j, 0);
            const double second_norm = second.norm();
            if (second_norm <= 1.0e-9) {
                continue;
            }
            second /= second_norm;
            const double second_clearance = -(
                    second.dot(position) + h_poly(j, 3) / second_norm);
            if (second_clearance < -inside_tolerance_m) {
                continue;
            }
            const double width = first_clearance + second_clearance;
            if (!std::isfinite(width) || width <= 0.0 ||
                width > max_width_m || width >= best_width) {
                continue;
            }
            best.valid = true;
            best.first_face = i;
            best.second_face = j;
            best.first_clearance_m = first_clearance;
            best.second_clearance_m = second_clearance;
            best.width_m = width;
            best.imbalance_m = first_clearance - second_clearance;
            best.first_normal = first;
            best.second_normal = second;
            best.imbalance_gradient = -first + second;
            best_width = width;
        }
        return best;
    }

}  // namespace traj_opt
