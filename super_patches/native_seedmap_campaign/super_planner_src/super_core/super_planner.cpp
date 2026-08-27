/**
* This file is part of SUPER
*
* Copyright 2025 Yunfan REN, MaRS Lab, University of Hong Kong, <mars.hku.hk>
* Developed by Yunfan REN <renyf at connect dot hku dot hk>
* for more information see <https://github.com/hku-mars/SUPER>.
* If you use this code, please cite the respective publications as
* listed on the above website.
*
* SUPER is free software: you can redistribute it and/or modify
* it under the terms of the GNU Lesser General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* SUPER is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU Lesser General Public License
* along with SUPER. If not, see <http://www.gnu.org/licenses/>.
*/

#include <super_core/super_planner.h>
#include <memory>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <stdexcept>
#include <super_utils/scope_timer.hpp>
#include <utils/optimization/polynomial_interpolation.h>
#include <fmt/color.h>

using namespace super_utils;

namespace super_planner {
    const char *trajectorySafetyStatusName(const TrajectorySafetyStatus status) {
        switch (status) {
            case TrajectorySafetyStatus::DISABLED: return "DISABLED";
            case TrajectorySafetyStatus::SAFE: return "SAFE";
            case TrajectorySafetyStatus::EMPTY_TRAJECTORY: return "EMPTY_TRAJECTORY";
            case TrajectorySafetyStatus::INVALID_TRAJECTORY: return "INVALID_TRAJECTORY";
            case TrajectorySafetyStatus::MAP_NOT_COMMITTED: return "MAP_NOT_COMMITTED";
            case TrajectorySafetyStatus::MAP_UPDATING: return "MAP_UPDATING";
            case TrajectorySafetyStatus::MAP_STALE: return "MAP_STALE";
            case TrajectorySafetyStatus::OCCUPIED: return "OCCUPIED";
            case TrajectorySafetyStatus::CLEARANCE_MARGIN: return "CLEARANCE_MARGIN";
            case TrajectorySafetyStatus::UNOBSERVED: return "UNOBSERVED";
            case TrajectorySafetyStatus::OUT_OF_MAP: return "OUT_OF_MAP";
            case TrajectorySafetyStatus::VERSION_CHANGED: return "VERSION_CHANGED";
            default: return "UNKNOWN";
        }
    }

    SuperPlanner::SuperPlanner
            (const std::string &cfg_path,
             const ros_interface::RosInterface::Ptr &ros_ptr,
             const rog_map::ROGMapROS::Ptr &map_ptr
            ) : cfg_(Config(cfg_path)), ros_ptr_(ros_ptr), map_ptr_(map_ptr) {

        ros_ptr_->setResolution(cfg_.resolution);
        ros_ptr_->setVisualizationEn(cfg_.visualization_en);
        exp_traj_opt_ = std::make_shared<traj_opt::ExpTrajOpt>(cfg_.exp_traj_cfg, ros_ptr_);
        back_traj_opt_ = std::make_shared<traj_opt::BackupTrajOpt>(cfg_.back_traj_cfg, ros_ptr_);
        yaw_traj_opt_ = std::make_shared<traj_opt::YawTrajOpt>(cfg_.yaw_dot_max);
        const auto &rog_map_cfg = map_ptr_->getMapConfig();
        const double inflation_radius = rog_map_cfg.inflation_resolution *
                                        rog_map_cfg.inflation_step;
        trajectory_guard_hard_clearance_m_ = trajectoryValidationEnabled()
                ? inflation_radius + cfg_.trajectory_guard_additional_clearance_m
                : cfg_.robot_r;
        if (trajectoryValidationEnabled()) {
            const double clearance_resolution = rog_map_cfg.inflation_resolution;
            const int clearance_steps = static_cast<int>(std::ceil(
                    cfg_.trajectory_guard_additional_clearance_m /
                    clearance_resolution));
            for (int x = -clearance_steps; x <= clearance_steps; ++x) {
                for (int y = -clearance_steps; y <= clearance_steps; ++y) {
                    for (int z = -clearance_steps; z <= clearance_steps; ++z) {
                        if (x == 0 && y == 0 && z == 0) {
                            continue;
                        }
                        const Vec3f offset = clearance_resolution *
                                Vec3f(x, y, z);
                        if (offset.norm() <=
                            cfg_.trajectory_guard_additional_clearance_m +
                            1.0e-9) {
                            trajectory_guard_clearance_offsets_.push_back(offset);
                        }
                    }
                }
            }
            if (!std::isfinite(inflation_radius) ||
                inflation_radius + 1.0e-9 < cfg_.robot_r) {
                if (cfg_.trajectory_guard_en) {
                    throw std::runtime_error(
                            "trajectory_guard requires inflated-map radius >= robot radius");
                }
                ros_ptr_->warn(" -- [TRAJ_GUARD_SHADOW_CONFIG] inflation_radius={:.3f}m "
                               "is smaller than robot_r={:.3f}m; observations do not "
                               "certify body clearance",
                               inflation_radius, cfg_.robot_r);
            }
            ros_ptr_->info(" -- [TRAJ_GUARD] mode={} sample_dt={:.4f}s "
                           "shadow_min_interval={:.3f}s inflation_radius={:.3f}m "
                           "robot_r={:.3f}m additional_clearance={:.3f}m "
                           "hard_clearance={:.3f}m "
                           "clearance_offsets={}",
                           cfg_.trajectory_guard_en ? "enforce" : "shadow",
                           cfg_.trajectory_guard_sample_dt_s,
                           cfg_.trajectory_guard_shadow_min_interval_s,
                           inflation_radius, cfg_.robot_r,
                           cfg_.trajectory_guard_additional_clearance_m,
                           trajectory_guard_hard_clearance_m_,
                           trajectory_guard_clearance_offsets_.size());
        }
        astar_ptr_ = std::make_shared<path_search::Astar>(cfg_path, ros_ptr_, map_ptr_);
        // CIRI builds a body-feasible candidate corridor. The independent
        // composite certificate below is the hard operational-clearance gate
        // for Exp, Backup and every stitch. Using the voxelized guard radius
        // inside raw-point CIRI made feasible inflated-map paths disappear due
        // to representation quantization (e.g. 0.369 m vs a 0.4 m grid gate).
        cg_ptr_ = std::make_shared<CorridorGenerator>(ros_ptr_, map_ptr_, cfg_.corridor_bound_dis,
                                                      cfg_.corridor_line_max_length,
                                                      cfg_.resolution, rog_map_cfg.virtual_ground_height,
                                                      rog_map_cfg.virtual_ceil_height,
                                                      cfg_.corridor_min_margin,
                                                      cfg_.obs_skip_num,
                                                      cfg_.iris_iter_num,
                                                      cfg_.corridor_pref_margin,
                                                      cfg_.corridor_use_inflated_obstacles,
                                                      cfg_.corridor_use_inflated_seed_lines);
        cg_ptr_->SetLineNeighborList(cfg_.seed_line_neighbour);
        if (cfg_.corridor_guard_retry_inflated) {
            // Inflated occupancy already contains the operational radius. A
            // small positive CIRI radius handles voxel-boundary numerics
            // without adding the physical radius a second time.
            //
            // 2026-08-19: tried raising this to 2x resolution (0.10m) on the
            // theory that 0.005m left no slack over CIRI's own margin
            // non-uniformity. That was wrong -- it made SearchPolytopeOnPath
            // fail outright far more often (~28x more failures per run across
            // a seed1-10 x n=5 sweep, 14/45 completions vs the 74/100
            // baseline), because this retry generator's whole point is
            // finding *some* corridor in a spot already too tight for the
            // normal generator; a bigger required margin just makes it more
            // often find none. Reverted to the original value. See the
            // guard_corridor_retry_alternate_every mechanism below for the
            // (validated-neutral) part of that day's change that stayed.
            const double retry_margin = std::max(0.005, 0.1 * cfg_.resolution);
            cg_guard_retry_ptr_ = std::make_shared<CorridorGenerator>(
                    ros_ptr_, map_ptr_, cfg_.corridor_bound_dis,
                    cfg_.corridor_line_max_length, cfg_.resolution,
                    rog_map_cfg.virtual_ground_height,
                    rog_map_cfg.virtual_ceil_height, retry_margin,
                    cfg_.obs_skip_num, cfg_.iris_iter_num, retry_margin,
                    true, true);
            cg_guard_retry_ptr_->SetLineNeighborList(cfg_.seed_line_neighbour);
        }

        // Separate instance (not a reuse of cg_ptr_) specifically so this
        // can be called safely from activateEmergencyBrake's callback
        // group without sharing mutable CIRI/CorridorGenerator state with
        // whatever thread is running the normal replan pipeline. Margins
        // match cg_ptr_ (raw points, paper-aligned preference margin), not
        // cg_guard_retry_ptr_'s near-zero tight-retry margin.
        cg_brake_ptr_ = std::make_shared<CorridorGenerator>(
                ros_ptr_, map_ptr_, cfg_.corridor_bound_dis,
                cfg_.corridor_line_max_length, cfg_.resolution,
                rog_map_cfg.virtual_ground_height,
                rog_map_cfg.virtual_ceil_height, cfg_.corridor_min_margin,
                cfg_.obs_skip_num, cfg_.iris_iter_num,
                cfg_.corridor_pref_margin, false, false);
        cg_brake_ptr_->SetLineNeighborList(cfg_.seed_line_neighbour);

        time_consuming_.resize(8);

        robot_state_.rcv = false;
        planner_process_start_WT_ = ros_ptr_->getSimTime();
        fov_checker_ = std::make_shared<FOVChecker>(FOVType::OMNI,
                                                    -1.0,
                                                    -35.0,
                                                    35.0);
        // horizontal +-angle FoV cut (models the horizontal sector filter at the planner level)
        fov_checker_->setHorizontalAngleDeg(cfg_.fov_horizontal_angle);
        fov_checker_->setCenterOnHeading(cfg_.fov_center_heading);

        // In enforcement mode the frontend must plan with the same clearance
        // boundary that the trajectory certificate will require. The normal
        // inflated map already supplies its own radius; only add the guard's
        // explicit extra clearance here.
        astar_ptr_->setClearanceRadii(trajectory_guard_hard_clearance_m_,
                                     inflation_radius);
        if (trajectoryGuardShadowEnabled()) {
            shadow_worker_ = std::thread(&SuperPlanner::shadowValidationLoop, this);
        }
    }

    SuperPlanner::~SuperPlanner() {
        {
            std::lock_guard<std::mutex> lock(shadow_worker_mutex_);
            stop_shadow_worker_ = true;
            pending_shadow_job_.reset();
        }
        shadow_worker_cv_.notify_all();
        if (shadow_worker_.joinable()) {
            shadow_worker_.join();
        }
    }

    TrajectorySafetyResult SuperPlanner::validatePositionTrajectory(
            const Trajectory &trajectory,
            double checked_from_tt,
            const std::uint64_t trajectory_generation,
            const bool allow_initial_clearance_escape,
            const bool unknown_as_occupied,
            const Vec3f *hard_current_pose,
            const bool test_force_initial_footprint_occupancy) const {
        TrajectorySafetyResult result;
        result.trajectory_generation = trajectory_generation;
        if (!trajectoryValidationEnabled()) {
            result.status = TrajectorySafetyStatus::DISABLED;
            return result;
        }

        const auto initial_health = map_ptr_->getMapHealthSnapshot();
        result.map_version = initial_health.map_version;
        if (initial_health.map_version == 0) {
            result.status = TrajectorySafetyStatus::MAP_NOT_COMMITTED;
            return result;
        }
        if (trajectory.empty()) {
            result.status = TrajectorySafetyStatus::EMPTY_TRAJECTORY;
            return result;
        }

        const double total_duration = trajectory.getTotalDuration();
        if (!std::isfinite(total_duration) || total_duration < 0.0 ||
            !std::isfinite(checked_from_tt)) {
            result.status = TrajectorySafetyStatus::INVALID_TRAJECTORY;
            return result;
        }
        checked_from_tt = std::clamp(checked_from_tt, 0.0, total_duration);
        result.checked_from_tt = checked_from_tt;
        result.checked_to_tt = total_duration;

        const auto &map_config = map_ptr_->getMapConfig();
        const double guard_ground_height =
                map_config.virtual_ground_height +
                trajectory_guard_hard_clearance_m_;
        const double guard_ceil_height =
                map_config.virtual_ceil_height -
                trajectory_guard_hard_clearance_m_;
        struct MapQueryPoint {
            Vec3f point;
            // `point` is the inflated-grid location used by the DDA/map
            // query.  A DDA cell centre is not necessarily on the
            // polynomial, so use this projected trajectory centre for the
            // raw occupied-voxel/body-distance test.
            Vec3f physical_center;
            double tt;
            bool hard_body_clearance;
        };
        std::vector<MapQueryPoint> map_queries;
        const auto append_finite_point = [&result, &map_queries](
                const Vec3f &point, const double tt,
                const bool hard_body_clearance = false) -> bool {
            if (!point.array().isFinite().all()) {
                result.status = TrajectorySafetyStatus::INVALID_TRAJECTORY;
                result.first_collision_tt = tt;
                result.first_collision_pos = point;
                return false;
            }
            map_queries.push_back(
                    {point, point, tt, hard_body_clearance});
            return true;
        };

        // Validation samples are monotonic in trajectory time. Avoid
        // Trajectory::getPos(), whose locatePieceIdx() rescans from piece zero
        // for every sample, by advancing one local piece cursor.
        std::size_t piece_index = 0;
        double piece_start_tt = 0.0;
        while (piece_index + 1 < trajectory.size() &&
               checked_from_tt > piece_start_tt +
                                 trajectory[piece_index].getDuration()) {
            piece_start_tt += trajectory[piece_index].getDuration();
            ++piece_index;
        }
        const auto sample_position = [&trajectory, &piece_index,
                                      &piece_start_tt](const double tt) {
            while (piece_index + 1 < trajectory.size() &&
                   tt > piece_start_tt + trajectory[piece_index].getDuration()) {
                piece_start_tt += trajectory[piece_index].getDuration();
                ++piece_index;
            }
            return trajectory[piece_index].getPos(tt - piece_start_tt);
        };

        double previous_tt = checked_from_tt;
        auto operation_start = std::chrono::steady_clock::now();
        Vec3f previous_point = sample_position(previous_tt);
        result.trajectory_eval_ms += std::chrono::duration<double, std::milli>(
                std::chrono::steady_clock::now() - operation_start).count();
        if (hard_current_pose) {
            ++result.checked_samples;
            if (!append_finite_point(*hard_current_pose, previous_tt, true)) {
                return result;
            }
        }
        ++result.checked_samples;
        if (!append_finite_point(previous_point, previous_tt, true)) {
            return result;
        }

        // Each interval is still voxel-raycast. Bound its chord length by one
        // inflated-map voxel at configured maximum speed; using the finer
        // probability-map sampling period here doubled trajectory/map queries
        // without increasing inflated-grid coverage.
        const double inflated_voxel_dt = map_config.inflation_resolution /
                                         cfg_.exp_traj_cfg.max_vel;
        const double sample_dt = std::max(1.0e-4,
                std::min(cfg_.trajectory_guard_sample_dt_s,
                         inflated_voxel_dt));
        rog_map::raycaster::RayCaster voxel_raycaster(
                map_config.inflation_resolution);
        while (previous_tt < total_duration) {
            const double next_tt = std::min(total_duration, previous_tt + sample_dt);
            operation_start = std::chrono::steady_clock::now();
            const Vec3f next_point = sample_position(next_tt);
            result.trajectory_eval_ms += std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - operation_start).count();
            ++result.checked_samples;
            if (!next_point.array().isFinite().all()) {
                result.status = TrajectorySafetyStatus::INVALID_TRAJECTORY;
                result.first_collision_tt = next_tt;
                result.first_collision_pos = next_point;
                return result;
            }
            operation_start = std::chrono::steady_clock::now();
            if (voxel_raycaster.setInput(previous_point, next_point)) {
                Vec3f ray_point;
                const Vec3f segment_delta = next_point - previous_point;
                const double segment_length_sq = segment_delta.squaredNorm();
                while (voxel_raycaster.step(ray_point)) {
                    double segment_alpha = 1.0;
                    if (segment_length_sq > 1.0e-12) {
                        segment_alpha = std::clamp(
                                (ray_point - previous_point).dot(segment_delta) /
                                        segment_length_sq,
                                0.0, 1.0);
                    }
                    map_queries.push_back(
                            {ray_point,
                             previous_point + segment_alpha * segment_delta,
                             previous_tt +
                                     segment_alpha * (next_tt - previous_tt),
                             false});
                }
            }
            map_queries.push_back({next_point, next_point, next_tt,
                                   next_tt >= total_duration - 1.0e-9});
            result.voxelize_ms += std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - operation_start).count();
            previous_tt = next_tt;
            previous_point = next_point;
        }

        // Trajectory evaluation and voxel traversal above are immutable CPU
        // work. Hold the shared map transaction only while reading the prepared
        // voxel set, so map commits are not stalled for the full validation.
        const auto wait_start = std::chrono::steady_clock::now();
        auto map_read_transaction = map_ptr_->acquireMapReadTransaction();
        const auto query_start = std::chrono::steady_clock::now();
        result.map_wait_ms = std::chrono::duration<double, std::milli>(
                query_start - wait_start).count();
        const auto health_before = map_ptr_->getMapHealthSnapshot();
        result.map_version = health_before.map_version;
        if (health_before.map_version == 0) {
            result.status = TrajectorySafetyStatus::MAP_NOT_COMMITTED;
            return result;
        }
        if (health_before.update_in_progress &&
            !map_ptr_->immutablePlannerSnapshotEnabled()) {
            result.status = TrajectorySafetyStatus::MAP_UPDATING;
            return result;
        }
        bool clearance_escape_prefix = false;
        bool clearance_escape_completed = false;
        double latest_clearance_violation_tt = -1.0;
        // Use one physical-body definition throughout the certificate.  The
        // previous general-path test sampled a robot-radius shell and then
        // queried the voxel containing every shell point.  That silently
        // added up to half a raw voxel to robot_r: a stopped pose could pass
        // the exact mandatory-pose check while every short escape from it was
        // labelled OCCUPIED.  Compare occupied voxel centres with robot_r,
        // matching the mandatory-pose check and the static-PCD contact oracle.
        const auto physical_body_occupied =
                [this, &map_config, hard_current_pose,
                 allow_initial_clearance_escape,
                 test_force_initial_footprint_occupancy, &result](
                        const Vec3f &point,
                        const bool allow_initial_footprint_mask) {
            if (point.z() <= map_config.virtual_ground_height + cfg_.robot_r ||
                point.z() >= map_config.virtual_ceil_height - cfg_.robot_r) {
                return true;
            }
            vec_E<Vec3f> occupied_points;
            const double search_radius = cfg_.robot_r +
                    0.5 * map_config.resolution;
            const Vec3f search_extent = Vec3f::Constant(search_radius);
            map_ptr_->boxSearch(point - search_extent,
                                point + search_extent,
                                rog_map::GridType::OCCUPIED,
                                occupied_points);
            if (test_force_initial_footprint_occupancy &&
                hard_current_pose != nullptr &&
                (point - *hard_current_pose).norm() <= cfg_.robot_r) {
                occupied_points.push_back(*hard_current_pose);
            }
            for (const auto &occupied_point : occupied_points) {
                const double candidate_distance =
                        (occupied_point - point).norm();
                if (candidate_distance <= cfg_.robot_r + 1.0e-9) {
                    const double initial_distance =
                            hard_current_pose != nullptr
                                    ? (occupied_point -
                                       *hard_current_pose).norm()
                                    : std::numeric_limits<double>::infinity();
                    const bool inside_initial_footprint =
                            allow_initial_footprint_mask &&
                            cfg_.trajectory_guard_initial_footprint_egress_en &&
                            allow_initial_clearance_escape &&
                            hard_current_pose != nullptr &&
                            initial_distance <= cfg_.robot_r + 1.0e-9 &&
                            // Never use the mask to move farther into a real
                            // hit.  It is only an egress exception for a cell
                            // already intersecting the stopped footprint.
                            candidate_distance + 1.0e-9 >= initial_distance;
                    if (inside_initial_footprint) {
                        result.used_initial_footprint_egress = true;
                        continue;
                    }
                    return true;
                }
            }
            return false;
        };
        // The per-segment DDA emits a voxel centre and the exact polynomial
        // endpoint at the same time stamp. Near a margin boundary those two
        // representations can alternate occupied/free until the trajectory
        // has actually left the starting voxel. Do not declare escape in the
        // middle of this stream: retain only the bounded starting-voxel
        // cluster, then require a continuous free tail after all queries have
        // been inspected.
        const double clearance_escape_free_confirmation_s =
                2.0 * sample_dt;
        const double clearance_escape_min_displacement_m =
                map_config.inflation_resolution;
        const double clearance_escape_cluster_radius_m =
                std::sqrt(3.0) * map_config.inflation_resolution + 1.0e-6;
        const double initial_footprint_egress_radius_m =
                cfg_.robot_r + trajectory_guard_hard_clearance_m_ +
                map_config.inflation_resolution;
        double first_clearance_violation_tt = -1.0;
        Vec3f first_clearance_violation_pos = Vec3f::Zero();
        for (std::size_t query_index = 0; query_index < map_queries.size(); ++query_index) {
            const auto &query = map_queries[query_index];
            const auto &point = query.point;
            if (!map_ptr_->insideLocalMap(point)) {
                result.status = TrajectorySafetyStatus::OUT_OF_MAP;
            } else {
                // The inflated grid is the efficient continuous-path guard,
                // but its coarser voxelization can disagree with the raw
                // occupied grid at a trajectory's current/terminal pose.  A
                // short tail that ends in such an alias must never become a
                // stationary hold: query raw occupied voxel centres directly
                // against the physical body radius at these mandatory poses.
                // This is a hard contact check and is intentionally outside
                // the ordinary initial-clearance escape exception below.
                // The optional footprint-egress mask is narrower: it ignores
                // only voxel centres already inside the stopped robot's
                // initial body, for at most the bounded escape window.  A
                // terminal violation still fails the continuous-free-tail
                // requirement below.
                if (query.hard_body_clearance) {
                    const bool footprint_mask_window =
                            query.tt - checked_from_tt <=
                                    cfg_.trajectory_guard_escape_max_duration_s;
                    if (physical_body_occupied(query.physical_center,
                                               footprint_mask_window)) {
                        result.status = TrajectorySafetyStatus::OCCUPIED;
                        result.first_collision_tt = query.tt;
                        result.first_collision_pos = point;
                        result.map_query_ms =
                                std::chrono::duration<double, std::milli>(
                                        std::chrono::steady_clock::now() -
                                        query_start).count();
                        return result;
                    }
                }

                // Unobserved space is not near any detected obstacle, so it
                // doesn't fit the OCCUPIED/CLEARANCE_MARGIN physical-escape
                // logic below (that logic assumes the violation is a margin
                // around a real hit). Treat it as a separate, harder
                // rejection with no escape allowed -- ambiguity about
                // whether space is safe should never be waved through the
                // way a soft inflation-margin graze can be.
                bool guard_unobserved = unknown_as_occupied &&
                                        map_ptr_->isUnknown(point);
                if (!guard_unobserved) {
                    for (const auto &offset : trajectory_guard_clearance_offsets_) {
                        const Vec3f clearance_point = point + offset;
                        if (map_ptr_->insideLocalMap(clearance_point) &&
                            unknown_as_occupied &&
                            map_ptr_->isUnknown(clearance_point)) {
                            guard_unobserved = true;
                            break;
                        }
                    }
                }
                if (guard_unobserved) {
                    result.status = TrajectorySafetyStatus::UNOBSERVED;
                    result.first_collision_tt = query.tt;
                    result.first_collision_pos = point;
                    result.map_query_ms = std::chrono::duration<double, std::milli>(
                            std::chrono::steady_clock::now() - query_start).count();
                    return result;
                }

                bool guard_occupied = point.z() <= guard_ground_height ||
                                      point.z() >= guard_ceil_height ||
                                      map_ptr_->isOccupiedInflate(point);
                if (test_force_initial_footprint_occupancy &&
                    hard_current_pose != nullptr &&
                    (point - *hard_current_pose).norm() <=
                            trajectory_guard_hard_clearance_m_) {
                    guard_occupied = true;
                }
                for (const auto &offset : trajectory_guard_clearance_offsets_) {
                    const Vec3f clearance_point = point + offset;
                    if (map_ptr_->insideLocalMap(clearance_point) &&
                        map_ptr_->isOccupiedInflate(clearance_point)) {
                        guard_occupied = true;
                        break;
                    }
                }
                if (!guard_occupied) {
                    continue;
                }

                // A conservative guard-margin violation may be escaped only
                // when the physical body still clears raw occupied voxels.
                const bool footprint_mask_window =
                        query.tt - checked_from_tt <=
                                cfg_.trajectory_guard_escape_max_duration_s;
                const bool physical_occupied = physical_body_occupied(
                        query.physical_center, footprint_mask_window);
                if (physical_occupied) {
                    result.status = TrajectorySafetyStatus::OCCUPIED;
                } else if (allow_initial_clearance_escape &&
                           !clearance_escape_completed &&
                           (query_index == 0 ||
                            (first_clearance_violation_tt < 0.0 &&
                             (point - map_queries.front().point).norm() <=
                                     clearance_escape_cluster_radius_m) ||
                            (clearance_escape_prefix &&
                             ((point - first_clearance_violation_pos).norm() <=
                                      clearance_escape_cluster_radius_m ||
                              (result.used_initial_footprint_egress &&
                               hard_current_pose != nullptr &&
                               (point - *hard_current_pose).norm() <=
                                       initial_footprint_egress_radius_m))) ||
                            (guard_corridor_retry_pending_.load(
                                     std::memory_order_acquire) &&
                             query.tt - checked_from_tt <=
                                     cfg_.trajectory_guard_escape_entry_grace_s)) &&
                           query.tt - checked_from_tt <=
                                   cfg_.trajectory_guard_escape_max_duration_s) {
                    clearance_escape_prefix = true;
                    latest_clearance_violation_tt = query.tt;
                    if (first_clearance_violation_tt < 0.0) {
                        first_clearance_violation_tt = query.tt;
                        first_clearance_violation_pos = point;
                    }
                    continue;
                } else {
                    result.status = TrajectorySafetyStatus::CLEARANCE_MARGIN;
                }
            }
            result.first_collision_tt = query.tt;
            result.first_collision_pos =
                    result.status == TrajectorySafetyStatus::OCCUPIED
                            ? query.physical_center
                            : point;
            result.map_query_ms = std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - query_start).count();
            return result;
        }
        if (clearance_escape_prefix) {
            const bool has_continuous_free_tail =
                    latest_clearance_violation_tt >= 0.0 &&
                    total_duration - latest_clearance_violation_tt >=
                            clearance_escape_free_confirmation_s;
            const bool has_spatial_departure =
                    first_clearance_violation_tt >= 0.0 &&
                    !map_queries.empty() &&
                    (map_queries.back().point -
                     first_clearance_violation_pos).norm() >=
                            clearance_escape_min_displacement_m;
            if (!has_continuous_free_tail || !has_spatial_departure) {
                result.status = TrajectorySafetyStatus::CLEARANCE_MARGIN;
                result.first_collision_tt = first_clearance_violation_tt;
                result.first_collision_pos = first_clearance_violation_pos;
                result.map_query_ms = std::chrono::duration<double, std::milli>(
                        std::chrono::steady_clock::now() - query_start).count();
                return result;
            }
            clearance_escape_completed = true;
            result.clearance_escape_completed_tt = std::min(
                    total_duration,
                    latest_clearance_violation_tt +
                            clearance_escape_free_confirmation_s);
        }
        result.used_clearance_escape = clearance_escape_completed;
        result.map_query_ms = std::chrono::duration<double, std::milli>(
                std::chrono::steady_clock::now() - query_start).count();
        const auto health_after = map_ptr_->getMapHealthSnapshot();
        if ((health_after.update_in_progress &&
             !map_ptr_->immutablePlannerSnapshotEnabled()) ||
            health_after.map_version != health_before.map_version) {
            result.status = TrajectorySafetyStatus::VERSION_CHANGED;
            result.map_version = health_after.map_version;
            return result;
        }
        result.status = TrajectorySafetyStatus::SAFE;
        return result;
    }

    TrajectorySafetyResult SuperPlanner::validateCommittedTrajectory(
            const double now_wt) const {
        const auto snapshot = cmd_traj_info_.snapshot();
        if (snapshot.empty) {
            TrajectorySafetyResult result;
            result.status = trajectoryValidationEnabled()
                    ? TrajectorySafetyStatus::EMPTY_TRAJECTORY
                    : TrajectorySafetyStatus::DISABLED;
            result.trajectory_generation = snapshot.generation;
            return result;
        }
        const double checked_from_tt = now_wt - snapshot.start_wt;
        auto result = validatePositionTrajectory(snapshot.pos_traj,
                                                 checked_from_tt,
                                                 snapshot.generation,
                                                 true);
        if (trajectoryValidationEnabled() &&
            cmd_traj_info_.generation() != snapshot.generation) {
            result.status = TrajectorySafetyStatus::VERSION_CHANGED;
        }
        return result;
    }

    void SuperPlanner::enqueueShadowValidation(CmdTraj::SharedSnapshot snapshot,
                                                const char *phase) {
        std::optional<std::uint64_t> replaced_generation;
        {
            std::lock_guard<std::mutex> lock(shadow_worker_mutex_);
            if (pending_shadow_job_) {
                replaced_generation = pending_shadow_job_->trajectory.generation;
            }
            pending_shadow_job_ = ShadowValidationJob{
                    std::move(snapshot), phase ? phase : "UNKNOWN"};
        }
        if (replaced_generation) {
            ros_ptr_->info(" -- [TRAJ_GUARD_SHADOW_SKIPPED] gen={} "
                           "reason=LATEST_ONLY action=async_after_commit",
                           *replaced_generation);
        }
        shadow_worker_cv_.notify_one();
    }

    bool SuperPlanner::enqueueCommittedTrajectoryShadowValidation(
            const char *phase) {
        if (!trajectoryGuardShadowEnabled()) {
            return false;
        }
        auto snapshot = cmd_traj_info_.sharedSnapshot();
        if (snapshot.empty || !snapshot.pos_traj) {
            return false;
        }
        enqueueShadowValidation(std::move(snapshot), phase);
        return true;
    }

    void SuperPlanner::shadowValidationLoop() {
        while (true) {
            ShadowValidationJob job;
            {
                std::unique_lock<std::mutex> lock(shadow_worker_mutex_);
                shadow_worker_cv_.wait(lock, [this] {
                    return stop_shadow_worker_ || pending_shadow_job_.has_value();
                });
                if (stop_shadow_worker_) {
                    return;
                }
                job = std::move(*pending_shadow_job_);
                pending_shadow_job_.reset();
            }

            const auto validation_start = std::chrono::steady_clock::now();
            if (last_shadow_validation_time_.time_since_epoch().count() != 0) {
                const double since_last_s = std::chrono::duration<double>(
                        validation_start - last_shadow_validation_time_).count();
                if (since_last_s < cfg_.trajectory_guard_shadow_min_interval_s) {
                    ros_ptr_->info(" -- [TRAJ_GUARD_SHADOW_SKIPPED] phase={} gen={} "
                                   "reason=RATE_LIMIT since_last_ms={:.3f} "
                                   "min_interval_ms={:.3f} action=async_after_commit",
                                   job.phase, job.trajectory.generation,
                                   1000.0 * since_last_s,
                                   1000.0 * cfg_.trajectory_guard_shadow_min_interval_s);
                    continue;
                }
            }
            last_shadow_validation_time_ = validation_start;
            const double checked_from_tt = ros_ptr_->getSimTime() -
                                           job.trajectory.start_wt;
            const auto safety = validatePositionTrajectory(
                    *job.trajectory.pos_traj, checked_from_tt,
                    job.trajectory.generation);
            const double validation_ms = std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - validation_start).count();
            const auto segment_name = [this, &job](const double tt) {
                if (!std::isfinite(tt) || tt < 0.0) return "NOT_APPLICABLE";
                const double stitch_tol = std::max(1.0e-4,
                        2.0 * cfg_.trajectory_guard_sample_dt_s);
                const auto &snapshot = job.trajectory;
                if (snapshot.has_appended_backup &&
                    std::isfinite(snapshot.backup_traj_start_tt)) {
                    if (std::abs(tt - snapshot.backup_traj_start_tt) <= stitch_tol) {
                        return "EXP_TO_BACKUP_STITCH";
                    }
                    if (tt > snapshot.backup_traj_start_tt) return "APPENDED_BACKUP";
                }
                if (snapshot.has_carry_backup &&
                    tt >= snapshot.carry_backup_start_tt &&
                    tt <= snapshot.carry_backup_end_tt) {
                    if (std::abs(tt - snapshot.carry_backup_start_tt) <= stitch_tol ||
                        std::abs(tt - snapshot.carry_backup_end_tt) <= stitch_tol) {
                        return "CARRY_BACKUP_STITCH";
                    }
                    return "CARRY_BACKUP";
                }
                return "EXP";
            };
            if (safety.safe()) {
                ros_ptr_->info(" -- [TRAJ_GUARD_SHADOW_SAFE] phase={} gen={} map={} "
                               "samples={} range=[{:.3f},{:.3f}] validation_ms={:.3f} "
                               "map_wait_ms={:.3f} map_query_ms={:.3f} "
                               "traj_eval_ms={:.3f} voxelize_ms={:.3f} "
                               "action=async_after_commit",
                               job.phase, job.trajectory.generation, safety.map_version,
                               safety.checked_samples, safety.checked_from_tt,
                               safety.checked_to_tt, validation_ms,
                               safety.map_wait_ms, safety.map_query_ms,
                               safety.trajectory_eval_ms, safety.voxelize_ms);
            } else {
                ros_ptr_->warn(" -- [TRAJ_GUARD_SHADOW_UNSAFE] phase={} segment={} "
                               "status={} gen={} map={} from_tt={:.3f} collision_tt={:.3f} "
                               "collision_p=[{:.3f},{:.3f},{:.3f}] samples={} "
                               "validation_ms={:.3f} map_wait_ms={:.3f} "
                               "map_query_ms={:.3f} traj_eval_ms={:.3f} "
                               "voxelize_ms={:.3f} action=async_after_commit",
                               job.phase, segment_name(safety.first_collision_tt),
                               trajectorySafetyStatusName(safety.status),
                               job.trajectory.generation, safety.map_version,
                               safety.checked_from_tt, safety.first_collision_tt,
                               safety.first_collision_pos.x(), safety.first_collision_pos.y(),
                               safety.first_collision_pos.z(), safety.checked_samples,
                               validation_ms, safety.map_wait_ms,
                               safety.map_query_ms, safety.trajectory_eval_ms,
                               safety.voxelize_ms);
            }
        }
    }

    void SuperPlanner::clearTopologyRecoverySearchState() {
        guard_topology_avoidance_centers_.clear();
        guard_topology_avoidance_radii_.clear();
        guard_topology_branch_directions_.clear();
        guard_topology_branch_depths_.clear();
        guard_topology_no_path_failures_ = 0;
        guard_topology_corridor_failures_ = 0;
        guard_topology_post_corridor_failures_ = 0;
        guard_topology_stall_generation_ = 0;
        guard_topology_stall_collision_.setZero();
        guard_topology_stall_rejects_ = 0;
        guard_local_escape_pending_.store(false,
                                          std::memory_order_release);
        guard_local_escape_direction_.setZero();
        guard_vertical_recovery_pending_.store(false,
                                               std::memory_order_release);
        guard_rest_to_rest_hold_until_wt_ =
                -std::numeric_limits<double>::infinity();
        guard_certified_stop_for_reroute_.store(false,
                                                std::memory_order_release);
    }

    void SuperPlanner::resetTopologyRecoveryState() {
        clearTopologyRecoverySearchState();
        guard_topology_base_no_path_recoveries_ = 0;
        guard_topology_saturation_recoveries_ = 0;
        guard_topology_local_escape_recoveries_ = 0;
        guard_topology_epoch_ = 0;
        guard_topology_episode_anchor_.setZero();
        guard_topology_episode_anchor_valid_ = false;
    }

    void SuperPlanner::armTopologyRouteBlock(
            const CmdTraj::Candidate &candidate,
            const TrajectorySafetyResult &safety,
            const std::uint64_t candidate_generation,
            const Vec3f &start_pos,
            const double current_speed_mps,
            const bool certified_stop,
            const bool collision_on_exp) {
        if (!cfg_.guard_topology_reroute_en ||
            !safety.first_collision_pos.array().isFinite().all() ||
            !start_pos.array().isFinite().all() ||
            (current_speed_mps >
                     cfg_.guard_topology_reroute_max_stop_speed_mps &&
             !certified_stop)) {
            return;
        }

        const bool same_generation =
                candidate_generation == guard_topology_stall_generation_ &&
                guard_topology_stall_rejects_ > 0;
        const bool same_collision_cluster =
                same_generation &&
                (safety.first_collision_pos.head<2>() -
                 guard_topology_stall_collision_.head<2>()).norm() <=
                        cfg_.guard_topology_reroute_collision_merge_m;
        bool arm_now = false;
        if (same_collision_cluster) {
            ++guard_topology_stall_rejects_;
            const double n = static_cast<double>(guard_topology_stall_rejects_);
            guard_topology_stall_collision_ +=
                    (safety.first_collision_pos - guard_topology_stall_collision_) / n;
            arm_now = guard_topology_stall_rejects_ %
                    cfg_.guard_topology_reroute_escalate_every_rejects == 0;
        } else if (!same_generation) {
            guard_topology_stall_generation_ = candidate_generation;
            guard_topology_stall_collision_ = safety.first_collision_pos;
            guard_topology_stall_rejects_ = 1;
            arm_now = true;
        } else {
            guard_topology_stall_collision_ = safety.first_collision_pos;
            guard_topology_stall_rejects_ = 1;
            ros_ptr_->warn(
                    " -- [TRAJ_GUARD_REROUTE_STALL] gen={} rejects=1 "
                    "collision=[{:.3f},{:.3f},{:.3f}] zones={} "
                    "action=changed_collision_hold",
                    candidate_generation,
                    guard_topology_stall_collision_.x(),
                    guard_topology_stall_collision_.y(),
                    guard_topology_stall_collision_.z(),
                    guard_topology_avoidance_centers_.size());
            return;
        }

        if (!arm_now) {
            ros_ptr_->warn(
                    " -- [TRAJ_GUARD_REROUTE_STALL] gen={} rejects={} "
                    "collision=[{:.3f},{:.3f},{:.3f}] zones={} action=hold",
                    candidate_generation, guard_topology_stall_rejects_,
                    guard_topology_stall_collision_.x(),
                    guard_topology_stall_collision_.y(),
                    guard_topology_stall_collision_.z(),
                    guard_topology_avoidance_centers_.size());
            return;
        }

        if (guard_topology_avoidance_centers_.size() >=
            static_cast<std::size_t>(cfg_.guard_topology_reroute_max_zones)) {
            const double horizontal_collision_distance =
                    (safety.first_collision_pos.head<2>() -
                     start_pos.head<2>()).norm();
            const bool start_adjacent_lower_rejection =
                    std::isfinite(horizontal_collision_distance) &&
                    horizontal_collision_distance <=
                            cfg_.guard_topology_vertical_recovery_trigger_distance_m &&
                    safety.first_collision_pos.z() <=
                            start_pos.z() + cfg_.resolution;
            const bool vertical_budget_available =
                    guard_topology_saturation_recoveries_ <
                            cfg_.guard_topology_saturation_vertical_attempts;
            if (cfg_.guard_topology_vertical_recovery_en &&
                vertical_budget_available) {
                const std::size_t cleared_zones =
                        guard_topology_avoidance_centers_.size();
                guard_topology_avoidance_centers_.clear();
                guard_topology_avoidance_radii_.clear();
                guard_topology_branch_directions_.clear();
                guard_topology_branch_depths_.clear();
                guard_topology_no_path_failures_ = 0;
                guard_topology_corridor_failures_ = 0;
                guard_topology_post_corridor_failures_ = 0;
                guard_topology_stall_generation_ = 0;
                guard_topology_stall_collision_.setZero();
                guard_topology_stall_rejects_ = 0;
                ++guard_topology_saturation_recoveries_;
                ++guard_topology_epoch_;
                guard_vertical_recovery_pending_.store(
                        true, std::memory_order_release);
                ros_ptr_->warn(
                        " -- [TRAJ_GUARD_VERTICAL_RECOVERY_ARM] gen={} "
                        "cleared_zones={} epoch={} attempt={}/{} "
                        "reason={} horizontal_distance={:.3f} "
                        "start_z={:.3f} collision_z={:.3f} action=lift_then_reroute",
                        candidate_generation, cleared_zones,
                        guard_topology_epoch_,
                        guard_topology_saturation_recoveries_,
                        cfg_.guard_topology_saturation_vertical_attempts,
                        start_adjacent_lower_rejection
                                ? "start_adjacent_lower_rejection"
                                : "horizontal_topology_exhausted",
                        horizontal_collision_distance,
                        start_pos.z(), safety.first_collision_pos.z());
                return;
            }
            ros_ptr_->warn(
                    " -- [TRAJ_GUARD_REROUTE_STALL] gen={} rejects={} zones={} "
                    "horizontal_distance={:.3f} start_z={:.3f} "
                    "collision_z={:.3f} vertical_attempts={}/{} "
                    "action=saturated",
                    candidate_generation, guard_topology_stall_rejects_,
                    guard_topology_avoidance_centers_.size(),
                    horizontal_collision_distance, start_pos.z(),
                    safety.first_collision_pos.z(),
                    guard_topology_saturation_recoveries_,
                    cfg_.guard_topology_saturation_vertical_attempts);
            return;
        }

        const double total_duration = candidate.pos_traj.getTotalDuration();
        const double collision_tt = std::clamp(
                safety.first_collision_tt, 0.0, total_duration);
        // The rejected segment can be APPENDED_BACKUP. A blocker must still
        // obstruct the outgoing EXP route from the stopped pose, not point
        // along a later backup manoeuvre. Sample just ahead of the guard's
        // checked-from time; only fall back to collision-time velocity when
        // the early EXP displacement is numerically degenerate.
        const double route_sample_tt = std::min(
                total_duration,
                std::clamp(safety.checked_from_tt, 0.0, total_duration) +
                        std::max(0.10,
                                 5.0 * cfg_.trajectory_guard_sample_dt_s));
        Vec3f collision_direction = safety.first_collision_pos - start_pos;
        collision_direction.z() = 0.0;
        const bool use_collision_direction = collision_on_exp &&
                collision_direction.array().isFinite().all() &&
                collision_direction.norm() >= cfg_.resolution;
        Vec3f route_direction = use_collision_direction
                ? collision_direction
                : candidate.pos_traj.getPos(route_sample_tt) - start_pos;
        const char *direction_source = use_collision_direction
                ? "exp_collision"
                : "exp_initial";
        if (!route_direction.array().isFinite().all() ||
            route_direction.norm() < 1.0e-3) {
            route_direction = candidate.pos_traj.getVel(route_sample_tt);
            direction_source = "exp_velocity";
        }
        if (!route_direction.array().isFinite().all() ||
            route_direction.norm() < 1.0e-3) {
            route_direction = candidate.pos_traj.getVel(collision_tt);
            direction_source = "collision_velocity";
        }
        if (!route_direction.array().isFinite().all() ||
            route_direction.norm() < 1.0e-3) {
            route_direction = safety.first_collision_pos - start_pos;
            direction_source = "collision_fallback";
        }
        if (!route_direction.array().isFinite().all() ||
            route_direction.norm() < 1.0e-3) {
            route_direction = gi_.goal_p - start_pos;
            direction_source = "goal_fallback";
        }
        // These route blockers encode a different horizontal homotopy for
        // the loop/forest mission. Using the polynomial's transient vertical
        // component previously placed several blockers below the floor or
        // above the useful flight band. Keep their axes at the certified stop
        // height; A* and CIRI both interpret each zone as a vertical cylinder,
        // so an altitude-only change cannot reuse the rejected passage.
        if (route_direction.array().isFinite().all()) {
            route_direction.z() = 0.0;
        }
        if (route_direction.norm() < 1.0e-3) {
            route_direction = gi_.goal_p - start_pos;
            route_direction.z() = 0.0;
            direction_source = "goal_xy_fallback";
        }
        if (!route_direction.array().isFinite().all() ||
            route_direction.norm() < 1.0e-3) {
            ros_ptr_->warn(
                    " -- [TRAJ_GUARD_REROUTE_STALL] gen={} rejects={} "
                    "action=no_route_direction",
                    candidate_generation, guard_topology_stall_rejects_);
            return;
        }
        route_direction.normalize();

        // The old global escalation index assumed every rejected candidate
        // remained on one route.  Seed9 exposed the opposite: the first
        // blocker pushed A* onto a new outgoing direction, but that direction
        // inherited a 1.85 m (then 2.85 m, ...) blocker distance.  Its unsafe
        // first few centimetres therefore stayed open forever.  Classify the
        // direction into stable branches.  A new branch starts at depth zero;
        // only another rejection along the same branch extends that chain.
        const double merge_angle_rad =
                cfg_.guard_topology_reroute_direction_merge_angle_deg *
                M_PI / 180.0;
        const double merge_cos = std::cos(merge_angle_rad);
        std::size_t branch = guard_topology_branch_directions_.size();
        double best_direction_dot = -1.0;
        for (std::size_t i = 0;
             i < guard_topology_branch_directions_.size(); ++i) {
            const double direction_dot =
                    route_direction.dot(guard_topology_branch_directions_[i]);
            if (direction_dot > best_direction_dot) {
                best_direction_dot = direction_dot;
                branch = i;
            }
        }
        int branch_depth = 0;
        if (branch < guard_topology_branch_directions_.size() &&
            best_direction_dot >= merge_cos) {
            branch_depth = ++guard_topology_branch_depths_[branch];
            // Keep an established chain collinear.  Candidate optimizer
            // jitter must not turn its cylinders into a fan with gaps.
            route_direction = guard_topology_branch_directions_[branch];
        } else {
            branch = guard_topology_branch_directions_.size();
            guard_topology_branch_directions_.push_back(route_direction);
            guard_topology_branch_depths_.push_back(0);
            best_direction_dot = 1.0;
        }

        const int escalation = branch_depth;
        const double radius = std::min(
                cfg_.guard_topology_reroute_max_radius_m,
                cfg_.guard_topology_reroute_radius_m +
                        static_cast<double>(escalation) *
                                cfg_.guard_topology_reroute_growth_m);
        const double forward_distance =
                radius + cfg_.guard_topology_reroute_start_clearance_m +
                static_cast<double>(escalation) *
                        cfg_.guard_topology_reroute_block_spacing_m;
        const Vec3f center = start_pos + forward_distance * route_direction;

        guard_topology_avoidance_centers_.push_back(center);
        guard_topology_avoidance_radii_.push_back(radius);
        const std::size_t zone = guard_topology_avoidance_centers_.size() - 1;
        ros_ptr_->warn(
                " -- [TRAJ_GUARD_REROUTE_ARM] zone={} zones={} gen={} rejects={} "
                "center=[{:.3f},{:.3f},{:.3f}] radius={:.3f} "
                "start_distance={:.3f} collision=[{:.3f},{:.3f},{:.3f}] "
                "stop_source={} direction_source={} branch={} depth={} "
                "direction_dot={:.3f} odom_speed={:.3f} "
                "action=block_rejected_route",
                zone, guard_topology_avoidance_centers_.size(),
                candidate_generation, guard_topology_stall_rejects_,
                center.x(), center.y(), center.z(), radius,
                (center - start_pos).norm(),
                safety.first_collision_pos.x(), safety.first_collision_pos.y(),
                safety.first_collision_pos.z(),
                certified_stop ? "certified_brake" : "odom",
                direction_source, branch, branch_depth, best_direction_dot,
                current_speed_mps);
    }

    bool SuperPlanner::armTopologyRouteBlockFromGuidePath(
            const vec_Vec3f &guide_path,
            const Vec3f &start_pos,
            const char *reason) {
        if (!cfg_.guard_topology_reroute_en || guide_path.size() < 2 ||
            !start_pos.array().isFinite().all() ||
            guard_topology_avoidance_centers_.size() >=
                    static_cast<std::size_t>(
                            cfg_.guard_topology_reroute_max_zones)) {
            return false;
        }

        // Use the actual outgoing A* guide, not the distant mission goal. A
        // point roughly half a metre ahead is far enough to ignore voxel
        // jitter at the start while still identifying the selected local
        // homotopy before a curved detour rejoins the global route.
        Vec3f route_direction = Vec3f::Zero();
        const double direction_sample_distance = std::max(
                0.5, 5.0 * cfg_.resolution);
        for (const auto &path_point : guide_path) {
            Vec3f delta = path_point - start_pos;
            delta.z() = 0.0;
            if (delta.array().isFinite().all() &&
                delta.norm() >= direction_sample_distance) {
                route_direction = delta;
                break;
            }
        }
        if (route_direction.norm() < 1.0e-3) {
            route_direction = gi_.goal_p - start_pos;
            route_direction.z() = 0.0;
        }
        if (!route_direction.array().isFinite().all() ||
            route_direction.norm() < 1.0e-3) {
            return false;
        }
        route_direction.normalize();

        const double merge_angle_rad =
                cfg_.guard_topology_reroute_direction_merge_angle_deg *
                M_PI / 180.0;
        const double merge_cos = std::cos(merge_angle_rad);
        std::size_t branch = guard_topology_branch_directions_.size();
        double best_direction_dot = -1.0;
        for (std::size_t i = 0;
             i < guard_topology_branch_directions_.size(); ++i) {
            const double direction_dot =
                    route_direction.dot(guard_topology_branch_directions_[i]);
            if (direction_dot > best_direction_dot) {
                best_direction_dot = direction_dot;
                branch = i;
            }
        }

        int branch_depth = 0;
        if (branch < guard_topology_branch_directions_.size() &&
            best_direction_dot >= merge_cos) {
            branch_depth = ++guard_topology_branch_depths_[branch];
            route_direction = guard_topology_branch_directions_[branch];
        } else {
            branch = guard_topology_branch_directions_.size();
            guard_topology_branch_directions_.push_back(route_direction);
            guard_topology_branch_depths_.push_back(0);
            best_direction_dot = 1.0;
        }

        const double radius = std::min(
                cfg_.guard_topology_reroute_max_radius_m,
                cfg_.guard_topology_reroute_radius_m +
                        static_cast<double>(branch_depth) *
                                cfg_.guard_topology_reroute_growth_m);
        const double forward_distance =
                radius + cfg_.guard_topology_reroute_start_clearance_m +
                static_cast<double>(branch_depth) *
                        cfg_.guard_topology_reroute_block_spacing_m;
        const Vec3f center = start_pos +
                forward_distance * route_direction;
        guard_topology_avoidance_centers_.push_back(center);
        guard_topology_avoidance_radii_.push_back(radius);
        ros_ptr_->warn(
                " -- [TRAJ_GUARD_REROUTE_ARM] zone={} zones={} "
                "center=[{:.3f},{:.3f},{:.3f}] radius={:.3f} "
                "start_distance={:.3f} branch={} depth={} "
                "direction_dot={:.3f} reason={} "
                "action=block_optimizer_failed_route",
                guard_topology_avoidance_centers_.size() - 1,
                guard_topology_avoidance_centers_.size(),
                center.x(), center.y(), center.z(), radius,
                (center - start_pos).norm(), branch, branch_depth,
                best_direction_dot, reason);
        return true;
    }

    bool SuperPlanner::checkKnownFreeViaCloud(const Vec3f &seed_near_pt,
                                              const Vec3f &seed_far_pt,
                                              const vec_E<Vec3f> &accumulated_cloud,
                                              const Trajectory &candidate,
                                              const double checked_from_tt,
                                              Vec3f &first_violation_pos) {
        if (!cg_brake_ptr_ || candidate.empty()) {
            return false;
        }
        Line seed{seed_near_pt, seed_far_pt};
        Polytope polytope;
        if (!cg_brake_ptr_->GeneratePolytopeFromLineAndCloud(
                    seed, accumulated_cloud, polytope)) {
            return false;
        }
        const double total_duration = candidate.getTotalDuration();
        const double sample_dt = std::max(0.005,
                cfg_.trajectory_guard_sample_dt_s);
        for (double tt = std::clamp(checked_from_tt, 0.0, total_duration);;
             tt = std::min(total_duration, tt + sample_dt)) {
            const Vec3f p = candidate.getPos(tt);
            if (!p.array().isFinite().all() ||
                !polytope.PointIsInside(p)) {
                first_violation_pos = p;
                return false;
            }
            if (tt >= total_duration) {
                break;
            }
        }
        return true;
    }

    bool SuperPlanner::commitTrajectoryCandidate(
            CmdTraj::Candidate candidate, const char *phase,
            std::string *rejected_segment_out) {
        if (rejected_segment_out) {
            rejected_segment_out->clear();
        }
        // The optimizer treats velocity as a soft penalty and its historical
        // post-check is disabled. Guarded publication needs a hard command
        // invariant, so time-scale a finite candidate before segment metadata
        // is captured or geometric certification is performed. The spatial
        // path is unchanged and the exact polynomial extremum is checked
        // again after scaling.
        if (cfg_.trajectory_guard_en) {
            const double velocity_limit = cfg_.exp_traj_cfg.max_vel;
            const double max_velocity = candidate.pos_traj.empty()
                    ? std::numeric_limits<double>::infinity()
                    : candidate.pos_traj.getMaxVelRate();
            if (!std::isfinite(velocity_limit) || velocity_limit <= 0.0 ||
                !std::isfinite(max_velocity)) {
                ros_ptr_->error(
                        " -- [TRAJ_VELOCITY_REJECT] phase={} gen={} "
                        "reason=NONFINITE max_vel={:.6f} limit={:.6f}",
                        phase, cmd_traj_info_.generation() + 1,
                        max_velocity, velocity_limit);
                trajectory_guard_rejection_pending_.store(
                        true, std::memory_order_release);
                return false;
            }
            if (max_velocity > velocity_limit * 1.001) {
                const double scale =
                        max_velocity / velocity_limit * 1.001;
                candidate.pos_traj = timeScaleTrajectory(
                        candidate.pos_traj, scale);
                candidate.yaw_traj = timeScaleTrajectory(
                        candidate.yaw_traj, scale);
                if (std::isfinite(candidate.backup_traj_start_tt)) {
                    candidate.backup_traj_start_tt *= scale;
                }
                if (candidate.carry_backup_start_tt >= 0.0) {
                    candidate.carry_backup_start_tt *= scale;
                }
                if (candidate.carry_backup_end_tt >= 0.0) {
                    candidate.carry_backup_end_tt *= scale;
                }
                const double scaled_max_velocity =
                        candidate.pos_traj.getMaxVelRate();
                if (!std::isfinite(scaled_max_velocity) ||
                    scaled_max_velocity > velocity_limit * 1.001) {
                    ros_ptr_->error(
                            " -- [TRAJ_VELOCITY_REJECT] phase={} gen={} "
                            "reason=RESCALE_FAILED before={:.6f} "
                            "after={:.6f} limit={:.6f} scale={:.6f}",
                            phase, cmd_traj_info_.generation() + 1,
                            max_velocity, scaled_max_velocity,
                            velocity_limit, scale);
                    trajectory_guard_rejection_pending_.store(
                            true, std::memory_order_release);
                    return false;
                }
                ros_ptr_->warn(
                        " -- [TRAJ_VELOCITY_SLOWDOWN] phase={} gen={} "
                        "before={:.6f} after={:.6f} limit={:.6f} "
                        "scale={:.6f}",
                        phase, cmd_traj_info_.generation() + 1,
                        max_velocity, scaled_max_velocity,
                        velocity_limit, scale);
            }
        }
        const bool has_appended_backup = candidate.has_appended_backup;
        const bool has_carry_backup = candidate.has_carry_backup;
        const double backup_start_tt = candidate.backup_traj_start_tt;
        const double carry_start_tt = candidate.carry_backup_start_tt;
        const double carry_end_tt = candidate.carry_backup_end_tt;
        const auto segment_name = [=, this](const double tt) {
            if (!std::isfinite(tt) || tt < 0.0) {
                return "NOT_APPLICABLE";
            }
            const double stitch_tol = std::max(1.0e-4,
                    2.0 * cfg_.trajectory_guard_sample_dt_s);
            if (has_appended_backup && std::isfinite(backup_start_tt)) {
                if (std::abs(tt - backup_start_tt) <= stitch_tol) {
                    return "EXP_TO_BACKUP_STITCH";
                }
                if (tt > backup_start_tt) {
                    return "APPENDED_BACKUP";
                }
            }
            if (has_carry_backup && tt >= carry_start_tt && tt <= carry_end_tt) {
                if (std::abs(tt - carry_start_tt) <= stitch_tol ||
                    std::abs(tt - carry_end_tt) <= stitch_tol) {
                    return "CARRY_BACKUP_STITCH";
                }
                return "CARRY_BACKUP";
            }
            return "EXP";
        };

        if (!trajectoryValidationEnabled()) {
            cmd_traj_info_.commitCandidate(std::move(candidate));
            trajectory_guard_rejection_pending_.store(false,
                                                      std::memory_order_release);
            return true;
        }

        // Shadow mode commits first and hands a snapshot to a bounded,
        // latest-only worker. Validation cannot delay or reject planning.
        if (trajectoryGuardShadowEnabled()) {
            const auto committed_generation =
                    cmd_traj_info_.commitCandidate(std::move(candidate));
            trajectory_guard_rejection_pending_.store(false,
                                                      std::memory_order_release);
            auto snapshot = cmd_traj_info_.sharedSnapshot();
            snapshot.generation = committed_generation;
            enqueueShadowValidation(std::move(snapshot), phase);
            return true;
        }

        const std::uint64_t candidate_generation =
                cmd_traj_info_.generation() + 1;
        double checked_from_tt = ros_ptr_->getSimTime() -
                                 candidate.pos_traj.start_WT;
        bool allow_clearance_escape = false;
        const std::string phase_name = phase ? phase : "";
        const bool plan_from_rest =
                phase_name.rfind("PlanFromRest/", 0) == 0;
        const bool topology_recovery_candidate =
                phase_name == "PlanFromRest/certified_local_escape" ||
                phase_name == "PlanFromRest/certified_vertical_recovery";
        bool stopped_for_reroute = false;
        const bool certified_stop_for_reroute = plan_from_rest &&
                guard_certified_stop_for_reroute_.load(
                        std::memory_order_acquire);
        std::optional<Vec3f> hard_current_pose;
        {
            std::lock_guard<std::mutex> state_lock(drone_state_mutex_);
            if (robot_state_.rcv && robot_state_.p.array().isFinite().all()) {
                hard_current_pose = robot_state_.p;
            }
        }
        double plan_from_rest_speed = std::numeric_limits<double>::infinity();
        if (plan_from_rest) {
            std::lock_guard<std::mutex> state_lock(drone_state_mutex_);
            plan_from_rest_speed = robot_state_.v.norm();
            allow_clearance_escape = plan_from_rest_speed <= 0.2;
            stopped_for_reroute = plan_from_rest_speed <=
                    cfg_.guard_topology_reroute_max_stop_speed_mps ||
                    certified_stop_for_reroute;
        }
        const char *test_force_initial_footprint_egress = std::getenv(
                "SUPER_TEST_FORCE_INITIAL_FOOTPRINT_EGRESS_ONCE");
        const bool inject_initial_footprint_occupancy =
                !guard_test_initial_footprint_egress_injected_ &&
                test_force_initial_footprint_egress != nullptr &&
                std::string(test_force_initial_footprint_egress) == "1" &&
                plan_from_rest && allow_clearance_escape &&
                cfg_.trajectory_guard_initial_footprint_egress_en;
        if (inject_initial_footprint_occupancy) {
            guard_test_initial_footprint_egress_injected_ = true;
            ros_ptr_->warn(
                    " -- [TEST_FAULT_INITIAL_FOOTPRINT_OCCUPANCY] "
                    "phase={} radius={:.3f}m action=inject_once",
                    phase, cfg_.robot_r);
        }
        const auto safety = validatePositionTrajectory(candidate.pos_traj,
                                                       checked_from_tt,
                                                       candidate_generation,
                                                       allow_clearance_escape,
                                                       false,
                                                       hard_current_pose
                                                               ? &*hard_current_pose
                                                               : nullptr,
                                                       inject_initial_footprint_occupancy);
        if (!safety.safe()) {
            trajectory_guard_rejection_pending_.store(true,
                                                      std::memory_order_release);
            const std::string rejected_segment =
                    segment_name(safety.first_collision_tt);
            if (rejected_segment_out) {
                *rejected_segment_out = rejected_segment;
            }
            // Both statuses are geometric evidence about the outgoing EXP
            // topology.  Previously only a clearance-margin rejection could
            // arm recovery; a stopped candidate whose first samples were
            // already OCCUPIED repeated the same guarded rejection forever.
            // MAP_STALE and UNOBSERVED remain excluded because they do not
            // identify a route that should be blocked.
            const bool plan_from_rest_geometric_rejection =
                    plan_from_rest &&
                    !topology_recovery_candidate &&
                    (safety.status ==
                             TrajectorySafetyStatus::CLEARANCE_MARGIN ||
                     safety.status == TrajectorySafetyStatus::OCCUPIED) &&
                    rejected_segment == "EXP";
            if (cfg_.corridor_guard_retry_inflated &&
                safety.status == TrajectorySafetyStatus::CLEARANCE_MARGIN &&
                rejected_segment == "EXP") {
                guard_corridor_retry_pending_.store(true,
                                                    std::memory_order_release);
            }
            if (plan_from_rest && stopped_for_reroute &&
                plan_from_rest_geometric_rejection) {
                Vec3f plan_from_rest_start = Vec3f::Zero();
                {
                    std::lock_guard<std::mutex> state_lock(drone_state_mutex_);
                    plan_from_rest_start = robot_state_.p;
                }
                armTopologyRouteBlock(candidate, safety, candidate_generation,
                                      plan_from_rest_start,
                                      plan_from_rest_speed,
                                      certified_stop_for_reroute,
                                      rejected_segment == "EXP");
            }
            ros_ptr_->error(" -- [TRAJ_GUARD_REJECT] phase={} segment={} status={} "
                            "gen={} map={} from_tt={:.3f} collision_tt={:.3f} "
                            "collision_p=[{:.3f},{:.3f},{:.3f}] samples={}",
                            phase, segment_name(safety.first_collision_tt),
                            trajectorySafetyStatusName(safety.status),
                            candidate_generation, safety.map_version,
                            safety.checked_from_tt, safety.first_collision_tt,
                            safety.first_collision_pos.x(), safety.first_collision_pos.y(),
                            safety.first_collision_pos.z(), safety.checked_samples);
            return false;
        }

        if (cfg_.guard_viability_en) {
            double scale = 1.0;
            int retry = 0;
            while (!candidateStopsViable(candidate.pos_traj, checked_from_tt,
                                         candidate_generation)) {
                const double next_scale = scale * cfg_.guard_viability_speed_scale_step;
                if (retry >= cfg_.guard_viability_max_retries ||
                    next_scale > cfg_.guard_viability_speed_scale_max) {
                    ros_ptr_->error(
                            " -- [TRAJ_GUARD_VIABILITY_REJECT] phase={} gen={} "
                            "scale={:.3f} retries={}",
                            phase, candidate_generation, scale, retry);
                    trajectory_guard_rejection_pending_.store(true,
                                                              std::memory_order_release);
                    return false;
                }
                scale = next_scale;
                ++retry;
                candidate.pos_traj = timeScaleTrajectory(candidate.pos_traj, scale);
                candidate.yaw_traj = timeScaleTrajectory(candidate.yaw_traj, scale);
                if (std::isfinite(candidate.backup_traj_start_tt)) {
                    candidate.backup_traj_start_tt *= scale;
                }
                if (candidate.carry_backup_start_tt >= 0.0) {
                    candidate.carry_backup_start_tt *= scale;
                }
                if (candidate.carry_backup_end_tt >= 0.0) {
                    candidate.carry_backup_end_tt *= scale;
                }
                checked_from_tt *= scale;
                // The rescaled candidate follows the exact same spatial path
                // (time-scaling only stretches duration), so this re-check is
                // defensive: it must remain safe, but is re-verified rather
                // than assumed.
                const auto rescaled_safety = validatePositionTrajectory(
                        candidate.pos_traj, checked_from_tt, candidate_generation,
                        allow_clearance_escape, false,
                        hard_current_pose ? &*hard_current_pose : nullptr);
                if (!rescaled_safety.safe()) {
                    ros_ptr_->error(
                            " -- [TRAJ_GUARD_VIABILITY_RESCALE_UNSAFE] phase={} "
                            "gen={} scale={:.3f}", phase, candidate_generation, scale);
                    trajectory_guard_rejection_pending_.store(true,
                                                              std::memory_order_release);
                    return false;
                }
            }
            if (retry > 0) {
                ros_ptr_->warn(
                        " -- [TRAJ_GUARD_VIABILITY_SLOWDOWN] phase={} gen={} "
                        "scale={:.3f} retries={}",
                        phase, candidate_generation, scale, retry);
            }
        }

        const auto committed_generation =
                cmd_traj_info_.commitCandidate(std::move(candidate));
        trajectory_guard_rejection_pending_.store(false,
                                                  std::memory_order_release);
        guard_corridor_retry_pending_.store(false, std::memory_order_release);
        guard_corridor_retry_attempts_.store(0, std::memory_order_release);
        // A successful short PlanFromRest candidate changes the current pose,
        // so its virtual blockers cannot be reused verbatim.  The recovery
        // budget, however, belongs to the stopped-location episode.  Resetting
        // the entire state here re-armed the same four-way escape and vertical
        // lift after every sub-metre commit (map8 Full: 154 arms/363 searches).
        // Preserve those budgets and the goal identity until PlanFromRest
        // observes material horizontal progress or a genuinely new goal.
        clearTopologyRecoverySearchState();
        if (cfg_.trajectory_guard_en) {
            ros_ptr_->info(" -- [TRAJ_GUARD_COMMIT] phase={} gen={} map={} samples={} "
                           "range=[{:.3f},{:.3f}] escape={} footprint_egress={} "
                           "escape_done_tt={:.3f}",
                           phase, committed_generation, safety.map_version,
                           safety.checked_samples, safety.checked_from_tt,
                           safety.checked_to_tt, safety.used_clearance_escape,
                           safety.used_initial_footprint_egress,
                           safety.clearance_escape_completed_tt);
        }
        return true;
    }

    Trajectory SuperPlanner::timeScaleTrajectory(const Trajectory &traj,
                                                 const double k) const {
        Trajectory out;
        out.reserve(static_cast<int>(traj.size()));
        out.start_WT = traj.start_WT;
        for (std::size_t i = 0; i < traj.size(); ++i) {
            const Piece &piece = traj[i];
            const Eigen::MatrixXd &coeff = piece.getCoeffMat();
            const int degree = piece.getDegree();
            Eigen::MatrixXd scaled = coeff;
            // coeff.col(degree) is the constant (t^0) term, coeff.col(0) is
            // the highest-degree term. q(t') = p(t'/k) divides the t^j
            // coefficient by k^j; j = degree - col.
            double kpow = 1.0;
            for (int col = degree; col >= 0; --col) {
                scaled.col(col) = coeff.col(col) / kpow;
                kpow *= k;
            }
            out.emplace_back(piece.getDuration() * k, scaled);
        }
        return out;
    }

    bool SuperPlanner::certifiedStopExistsFrom(
            const StatePVAJ &state,
            const std::uint64_t trajectory_generation) const {
        if (!state.array().isFinite().all()) {
            return false;
        }
        const double max_acc_limit = cfg_.guard_viability_brake_max_acc_mps2;
        const double max_jerk_limit = cfg_.guard_viability_brake_max_jerk_mps3;
        const double min_duration = cfg_.guard_viability_brake_min_duration_s;
        const double max_duration = cfg_.guard_viability_brake_max_duration_s;
        const Vec3f v0 = state.col(1);
        const Vec3f a0 = state.col(2);
        double duration = std::max({
                min_duration,
                1.5 * v0.norm() / max_acc_limit,
                std::sqrt(6.0 * v0.norm() / max_jerk_limit),
                2.0 * a0.norm() / max_jerk_limit});
        duration = std::min(duration, max_duration);

        Eigen::Matrix<double, 3, 3> initial_pva = state.leftCols<3>();
        bool last_dynamics_ok = false;
        TrajectorySafetyStatus last_status = TrajectorySafetyStatus::DISABLED;
        int attempts_used = 0;
        for (int attempt = 0; attempt < cfg_.guard_viability_brake_attempts;
             ++attempt) {
            ++attempts_used;
            Eigen::Matrix<double, 3, 3> goal_pva;
            goal_pva.setZero();
            goal_pva.col(0) = state.col(0) + 0.5 * duration * v0 +
                              (duration * duration / 12.0) * a0;
            Eigen::Matrix<double, 3, Eigen::Dynamic> waypoints(3, 0);
            VecDf durations(1);
            durations << duration;
            auto candidate = poly_interpo::minimumJerkInterpolation<3>(
                    initial_pva, goal_pva, waypoints, durations);

            bool dynamics_ok = !candidate.empty();
            if (dynamics_ok) {
                for (int i = 0; i <= 20; ++i) {
                    const double tt = duration * static_cast<double>(i) / 20.0;
                    const Vec3f acc = candidate.getAcc(tt);
                    const Vec3f jer = candidate.getJer(tt);
                    if (!acc.array().isFinite().all() ||
                        !jer.array().isFinite().all() ||
                        acc.norm() > max_acc_limit * 1.001 ||
                        jer.norm() > max_jerk_limit * 1.001) {
                        dynamics_ok = false;
                        break;
                    }
                }
            }
            last_dynamics_ok = dynamics_ok;
            if (dynamics_ok) {
                const auto safety = validatePositionTrajectory(
                        candidate, 0.0, trajectory_generation, true);
                last_status = safety.status;
                // Diagnostic logging showed almost all stop-viability failures
                // were CLEARANCE_MARGIN, not OCCUPIED, at speeds from 2.9 to
                // 6.7 m/s -- i.e. not fixed by slowing down. isOccupiedInflate
                // (used for CLEARANCE_MARGIN) inflates by inflation_step *
                // inflation_resolution = 0.3 m here, a full 0.1 m more than
                // the true physical robot_r = 0.2 m used for OCCUPIED. That
                // extra conservative buffer, not real obstacle proximity, was
                // rejecting brakes. An emergency stop is exactly the case
                // where trading that buffer for having a certified fallback
                // at all is the right call, so accept CLEARANCE_MARGIN here
                // too; only true physical contact (OCCUPIED) or map problems
                // (OUT_OF_MAP/MAP_STALE/etc.) still fail the check.
                if (safety.safe() ||
                    safety.status == TrajectorySafetyStatus::CLEARANCE_MARGIN) {
                    return true;
                }
            }
            if (duration >= max_duration - 1.0e-9) {
                break;
            }
            duration = std::min(max_duration, duration * 1.15);
        }
        if (std::getenv("VIABILITY_DEBUG") != nullptr) {
            ros_ptr_->warn(
                    " -- [TRAJ_GUARD_VIABILITY_STOP_FAIL] p=[{:.3f},{:.3f},{:.3f}] "
                    "v={:.3f} a={:.3f} attempts={} last_duration={:.3f} "
                    "last_dynamics_ok={} last_status={}",
                    state.col(0).x(), state.col(0).y(), state.col(0).z(),
                    v0.norm(), a0.norm(), attempts_used, duration,
                    last_dynamics_ok, trajectorySafetyStatusName(last_status));
        }
        return false;
    }

    bool SuperPlanner::candidateStopsViable(
            const Trajectory &pos_traj,
            double checked_from_tt,
            const std::uint64_t trajectory_generation) const {
        if (pos_traj.empty()) {
            return true;
        }
        const double total_duration = pos_traj.getTotalDuration();
        checked_from_tt = std::clamp(checked_from_tt, 0.0, total_duration);
        const double horizon_end = std::min(
                total_duration,
                checked_from_tt + cfg_.guard_viability_horizon_s);
        const double sample_dt = cfg_.guard_viability_sample_dt_s;
        double tt = checked_from_tt;
        bool checked_end = false;
        while (true) {
            StatePVAJ state;
            if (pos_traj.getState(tt, state)) {
                if (!certifiedStopExistsFrom(state, trajectory_generation)) {
                    return false;
                }
            }
            if (checked_end) {
                break;
            }
            tt += sample_dt;
            if (tt >= horizon_end) {
                tt = horizon_end;
                checked_end = true;
            }
        }
        return true;
    }

    bool SuperPlanner::tryCommitCertifiedDirectGoalFallback(
            const Vec3f &start_p, const Vec3f &goal_p) {
        const double distance = (goal_p - start_p).norm();
        Vec3f odom_position = Vec3f::Zero();
        double odom_yaw = 0.0;
        {
            std::lock_guard<std::mutex> state_lock(drone_state_mutex_);
            odom_position = robot_state_.p;
            odom_yaw = robot_state_.yaw;
        }
        const double start_shift = (start_p - odom_position).norm();
        if (!cfg_.guard_direct_goal_fallback_en ||
            !cfg_.guard_viability_en ||
            !guard_certified_stop_for_reroute_.load(
                    std::memory_order_acquire) ||
            !start_p.array().isFinite().all() ||
            !goal_p.array().isFinite().all() ||
            !std::isfinite(distance) || distance <= 1.0e-3 ||
            !std::isfinite(start_shift) || start_shift > 0.15 ||
            distance > cfg_.guard_direct_goal_fallback_max_distance_m) {
            return false;
        }

        // Exact extrema for a one-piece, zero-PVA endpoint minimum-jerk
        // polynomial are 1.875*d/T, ~5.774*d/T^2, and 60*d/T^3. Allocate
        // duration from the normal EXP limits with a 20% reserve; the normal
        // commit path below still performs geometric and stop-viability
        // validation and may time-scale it further.
        const double velocity_limit = std::max(
                1.0e-3, 0.8 * cfg_.exp_traj_cfg.max_vel);
        const double acceleration_limit = std::max(
                1.0e-3, 0.8 * cfg_.exp_traj_cfg.max_acc);
        const double jerk_limit = std::max(
                1.0e-3, 0.8 * cfg_.exp_traj_cfg.max_jerk);
        const double duration = std::max({
                cfg_.guard_direct_goal_fallback_min_duration_s,
                1.875 * distance / velocity_limit,
                std::sqrt(5.774 * distance / acceleration_limit),
                std::cbrt(60.0 * distance / jerk_limit)});

        Eigen::Matrix<double, 3, 3> initial_pva;
        Eigen::Matrix<double, 3, 3> goal_pva;
        initial_pva.setZero();
        goal_pva.setZero();
        initial_pva.col(0) = start_p;
        goal_pva.col(0) = goal_p;
        Eigen::Matrix<double, 3, Eigen::Dynamic> position_waypoints(3, 0);
        VecDf durations(1);
        durations << duration;
        Trajectory position_trajectory =
                poly_interpo::minimumJerkInterpolation<3>(
                        initial_pva, goal_pva, position_waypoints, durations);

        Eigen::Matrix<double, 1, 3> initial_yaw;
        Eigen::Matrix<double, 1, 3> goal_yaw;
        initial_yaw.setZero();
        goal_yaw.setZero();
        initial_yaw(0, 0) = odom_yaw;
        goal_yaw(0, 0) = odom_yaw;
        Eigen::Matrix<double, 1, Eigen::Dynamic> yaw_waypoints(1, 0);
        Trajectory yaw_trajectory =
                poly_interpo::minimumJerkInterpolation<1>(
                        initial_yaw, goal_yaw, yaw_waypoints, durations);

        const double start_wt = ros_ptr_->getSimTime();
        position_trajectory.start_WT = start_wt;
        yaw_trajectory.start_WT = start_wt;
        ExpTraj fallback_exp;
        fallback_exp.setTrajectory(start_wt, position_trajectory,
                                   yaw_trajectory);
        fallback_exp.setGoalConnectedFlag(true);

        CmdTraj::Candidate candidate;
        if (!CmdTraj::buildCandidate(fallback_exp, candidate) ||
            !commitTrajectoryCandidate(
                    std::move(candidate),
                    "PlanFromRest/certified_direct_goal_fallback")) {
            ros_ptr_->warn(
                    " -- [TRAJ_GUARD_DIRECT_GOAL_FALLBACK_REJECTED] "
                    "distance={:.3f}m duration={:.3f}s",
                    distance, duration);
            return false;
        }

        last_exp_traj_info_ = fallback_exp;
        robot_on_backup_traj_ = false;
        gi_.new_goal = false;
        // minimumJerkInterpolation produces a different polynomial order
        // from the normal EXP optimizer. Let this short rest-to-rest fallback
        // finish instead of hot-splicing a ReplanOnce polynomial into it;
        // mixed orders are intentionally rejected by the ROS trajectory
        // serializer and previously terminated fsm_node.
        guard_rest_to_rest_hold_until_wt_ =
                start_wt + cmd_traj_info_.getTotalDuration();
        ros_ptr_->vizCommittedTraj(cmd_traj_info_.posTraj(), -1);
        latest_replan.setRetCode(
                SUPER_RET_CODE::SUPER_SUCCESS_NO_BACKUP);
        ros_ptr_->warn(
                " -- [TRAJ_GUARD_DIRECT_GOAL_FALLBACK] action=commit "
                "distance={:.3f}m duration={:.3f}s",
                distance, duration);
        return true;
    }

    bool SuperPlanner::tryCommitCertifiedLocalEscape(
            const Vec3f &start_p) {
        if (!cfg_.guard_topology_local_escape_en ||
            !cfg_.guard_viability_en ||
            !guard_local_escape_pending_.load(std::memory_order_acquire) ||
            !start_p.array().isFinite().all()) {
            return false;
        }

        Vec3f odom_position = Vec3f::Zero();
        double odom_yaw = 0.0;
        double odom_speed = std::numeric_limits<double>::infinity();
        {
            std::lock_guard<std::mutex> state_lock(drone_state_mutex_);
            odom_position = robot_state_.p;
            odom_yaw = robot_state_.yaw;
            odom_speed = robot_state_.v.norm();
        }
        Vec3f escape_direction = guard_local_escape_direction_;
        escape_direction.z() = 0.0;
        const double direction_norm = escape_direction.norm();
        const double start_shift = (start_p - odom_position).norm();
        const bool certified_stop =
                guard_certified_stop_for_reroute_.load(
                        std::memory_order_acquire);
        if (!odom_position.array().isFinite().all() ||
            !std::isfinite(odom_yaw) || !std::isfinite(odom_speed) ||
            !std::isfinite(start_shift) || start_shift > 0.15 ||
            !std::isfinite(direction_norm) || direction_norm < 1.0e-3 ||
            (!certified_stop && odom_speed >
                    cfg_.guard_topology_reroute_max_stop_speed_mps)) {
            return false;
        }

        // Consume one bounded request only after odometry and the stored
        // escape direction are usable. A rejected escape is never submitted
        // again; the separately-budgeted vertical fallback may run next.
        if (!guard_local_escape_pending_.exchange(
                    false, std::memory_order_acq_rel)) {
            return false;
        }

        escape_direction /= direction_norm;
        const Vec3f escape_start = odom_position;
        // A single "away from the latest collision" direction is not a
        // topology change when optimizer jitter moves the reported collision
        // from one side of a stopped vehicle to the other.  Seed8 exposed
        // exactly that case: the stored direction pointed into the originally
        // rejected route and the planner then reseeded that route for almost a
        // minute.  Four cardinal exits were still insufficient at map8's
        // diagonal boundary pocket. Enumerate the eight horizontal homotopy
        // exits once and let the unchanged trajectory certificate select the
        // first safe one.
        // This remains a bounded, stop-only recovery; no unsafe candidate can
        // be published merely because it is an alternate direction.
        const Vec3f perpendicular(-escape_direction.y(),
                                  escape_direction.x(), 0.0);
        std::vector<Vec3f> escape_directions{
                escape_direction,
                -escape_direction,
                perpendicular,
                -perpendicular,
                (escape_direction + perpendicular).normalized(),
                (escape_direction - perpendicular).normalized(),
                (-escape_direction + perpendicular).normalized(),
                (-escape_direction - perpendicular).normalized()};
        // A geometrically safe step can still make the next corridor problem
        // worse when it moves toward the map boundary.  Seed10 exposed this:
        // the first safe "away from collision" direction moved north-east
        // while the waypoint was almost due west, leaving FIRI at y=24.95
        // indefinitely.  Keep the same eight certified alternatives, but try
        // the directions that make the most horizontal waypoint progress
        // first.  stable_sort preserves the collision-relative order when a
        // goal direction is unavailable or scores tie.
        Vec3f goal_direction = gi_.goal_p - escape_start;
        goal_direction.z() = 0.0;
        const double goal_direction_norm = goal_direction.norm();
        if (goal_direction.array().isFinite().all() &&
            std::isfinite(goal_direction_norm) &&
            goal_direction_norm >= cfg_.resolution) {
            goal_direction /= goal_direction_norm;
            std::stable_sort(
                    escape_directions.begin(), escape_directions.end(),
                    [&goal_direction](const Vec3f &lhs, const Vec3f &rhs) {
                        return lhs.dot(goal_direction) >
                               rhs.dot(goal_direction);
                    });
        }
        const double distance =
                cfg_.guard_topology_local_escape_distance_m;
        const double velocity_limit = std::max(
                1.0e-3, 0.8 * cfg_.exp_traj_cfg.max_vel);
        const double acceleration_limit = std::max(
                1.0e-3, 0.8 * cfg_.exp_traj_cfg.max_acc);
        const double jerk_limit = std::max(
                1.0e-3, 0.8 * cfg_.exp_traj_cfg.max_jerk);
        const double duration = std::max({
                cfg_.guard_direct_goal_fallback_min_duration_s,
                1.875 * distance / velocity_limit,
                std::sqrt(5.774 * distance / acceleration_limit),
                std::cbrt(60.0 * distance / jerk_limit)});

        const double start_wt = ros_ptr_->getSimTime();
        ExpTraj recovery_exp;
        bool committed = false;
        std::size_t committed_direction = 0;
        for (std::size_t direction_index = 0;
             direction_index < escape_directions.size(); ++direction_index) {
            const Vec3f trial_direction =
                    escape_directions[direction_index].normalized();
            if (guard_test_local_escape_skip_first_direction_ &&
                direction_index == 0) {
                guard_test_local_escape_skip_first_direction_ = false;
                ros_ptr_->warn(
                        " -- [TEST_FAULT_LOCAL_ESCAPE_DIRECTION_SKIP] "
                        "attempt=1/{} direction=[{:.3f},{:.3f},{:.3f}]",
                        escape_directions.size(), trial_direction.x(),
                        trial_direction.y(), trial_direction.z());
                continue;
            }
            const Vec3f escape_goal = escape_start +
                    distance * trial_direction;
            Eigen::Matrix<double, 3, 3> initial_pva;
            Eigen::Matrix<double, 3, 3> goal_pva;
            initial_pva.setZero();
            goal_pva.setZero();
            initial_pva.col(0) = escape_start;
            goal_pva.col(0) = escape_goal;
            Eigen::Matrix<double, 3, Eigen::Dynamic>
                    position_waypoints(3, 0);
            VecDf durations(1);
            durations << duration;
            Trajectory position_trajectory =
                    poly_interpo::minimumJerkInterpolation<3>(
                            initial_pva, goal_pva,
                            position_waypoints, durations);

            Eigen::Matrix<double, 1, 3> initial_yaw;
            Eigen::Matrix<double, 1, 3> goal_yaw;
            initial_yaw.setZero();
            goal_yaw.setZero();
            initial_yaw(0, 0) = odom_yaw;
            goal_yaw(0, 0) = odom_yaw;
            Eigen::Matrix<double, 1, Eigen::Dynamic> yaw_waypoints(1, 0);
            Trajectory yaw_trajectory =
                    poly_interpo::minimumJerkInterpolation<1>(
                            initial_yaw, goal_yaw,
                            yaw_waypoints, durations);
            position_trajectory.start_WT = start_wt;
            yaw_trajectory.start_WT = start_wt;

            ExpTraj trial_exp;
            trial_exp.setTrajectory(start_wt, position_trajectory,
                                    yaw_trajectory);
            trial_exp.setGoalConnectedFlag(false);
            CmdTraj::Candidate candidate;
            if (CmdTraj::buildCandidate(trial_exp, candidate) &&
                commitTrajectoryCandidate(
                        std::move(candidate),
                        "PlanFromRest/certified_local_escape")) {
                recovery_exp = trial_exp;
                escape_direction = trial_direction;
                committed_direction = direction_index;
                committed = true;
                break;
            }
            ros_ptr_->warn(
                    " -- [TRAJ_GUARD_LOCAL_ESCAPE_DIRECTION_REJECTED] "
                    "attempt={}/{} "
                    "distance={:.3f}m duration={:.3f}s "
                    "direction=[{:.3f},{:.3f},{:.3f}]",
                    direction_index + 1, escape_directions.size(),
                    distance, duration, trial_direction.x(),
                    trial_direction.y(), trial_direction.z());
        }
        if (!committed) {
            ros_ptr_->warn(
                    " -- [TRAJ_GUARD_LOCAL_ESCAPE_REJECTED] "
                    "attempts={} distance={:.3f}m duration={:.3f}s",
                    escape_directions.size(), distance, duration);
            return false;
        }

        // The vertical request is a fallback for the case where every
        // horizontal direction is rejected.  Do not leave it armed after a
        // certified horizontal escape was committed.
        guard_vertical_recovery_pending_.store(false,
                                               std::memory_order_release);

        last_exp_traj_info_ = recovery_exp;
        robot_on_backup_traj_ = false;
        gi_.new_goal = false;
        guard_rest_to_rest_hold_until_wt_ =
                start_wt + cmd_traj_info_.getTotalDuration();
        ros_ptr_->vizCommittedTraj(cmd_traj_info_.posTraj(), -1);
        latest_replan.setRetCode(
                SUPER_RET_CODE::SUPER_SUCCESS_NO_BACKUP);
        ros_ptr_->warn(
                " -- [TRAJ_GUARD_LOCAL_ESCAPE] action=commit "
                "attempt={}/{} distance={:.3f}m duration={:.3f}s "
                "direction=[{:.3f},{:.3f},{:.3f}] "
                "stop_source={} odom_speed={:.3f}",
                committed_direction + 1, escape_directions.size(),
                distance, duration, escape_direction.x(),
                escape_direction.y(), escape_direction.z(),
                certified_stop ? "certified_brake" : "stationary_odom",
                odom_speed);
        return true;
    }

    bool SuperPlanner::tryCommitCertifiedVerticalRecovery(
            const Vec3f &start_p) {
        if (!cfg_.guard_topology_vertical_recovery_en ||
            !cfg_.guard_viability_en ||
            !guard_vertical_recovery_pending_.load(
                    std::memory_order_acquire) ||
            !start_p.array().isFinite().all()) {
            return false;
        }

        Vec3f odom_position = Vec3f::Zero();
        double odom_yaw = 0.0;
        double odom_speed = std::numeric_limits<double>::infinity();
        {
            std::lock_guard<std::mutex> state_lock(drone_state_mutex_);
            odom_position = robot_state_.p;
            odom_yaw = robot_state_.yaw;
            odom_speed = robot_state_.v.norm();
        }
        const double start_shift = (start_p - odom_position).norm();
        const bool certified_stop =
                guard_certified_stop_for_reroute_.load(
                        std::memory_order_acquire);
        if (!odom_position.array().isFinite().all() ||
            !std::isfinite(odom_yaw) || !std::isfinite(start_shift) ||
            !std::isfinite(odom_speed) || start_shift > 0.15 ||
            (!certified_stop && odom_speed >
                    cfg_.guard_topology_reroute_max_stop_speed_mps)) {
            return false;
        }

        // Consume exactly one recovery request. If the lift itself is not
        // certifiable, normal guarded planning continues; another lift can be
        // armed only after a fresh bounded blocker-saturation episode.
        if (!guard_vertical_recovery_pending_.exchange(
                    false, std::memory_order_acq_rel)) {
            return false;
        }

        // The nearest grid-cell start used by A* may be centimetres away from
        // odometry. A recovery command must remain position-continuous, so
        // construct the lift from the measured stationary pose itself; the
        // full guard below decides whether escaping from that exact pose is
        // physically and geometrically admissible.
        const Vec3f lift_start = odom_position;
        Vec3f lift_goal = lift_start;
        lift_goal.z() += cfg_.guard_topology_vertical_recovery_lift_m;
        const double distance = (lift_goal - lift_start).norm();

        const double velocity_limit = std::max(
                1.0e-3, 0.8 * cfg_.exp_traj_cfg.max_vel);
        const double acceleration_limit = std::max(
                1.0e-3, 0.8 * cfg_.exp_traj_cfg.max_acc);
        const double jerk_limit = std::max(
                1.0e-3, 0.8 * cfg_.exp_traj_cfg.max_jerk);
        const double duration = std::max({
                cfg_.guard_direct_goal_fallback_min_duration_s,
                1.875 * distance / velocity_limit,
                std::sqrt(5.774 * distance / acceleration_limit),
                std::cbrt(60.0 * distance / jerk_limit)});

        Eigen::Matrix<double, 3, 3> initial_pva;
        Eigen::Matrix<double, 3, 3> goal_pva;
        initial_pva.setZero();
        goal_pva.setZero();
        initial_pva.col(0) = lift_start;
        goal_pva.col(0) = lift_goal;
        Eigen::Matrix<double, 3, Eigen::Dynamic> position_waypoints(3, 0);
        VecDf durations(1);
        durations << duration;
        Trajectory position_trajectory =
                poly_interpo::minimumJerkInterpolation<3>(
                        initial_pva, goal_pva, position_waypoints, durations);

        Eigen::Matrix<double, 1, 3> initial_yaw;
        Eigen::Matrix<double, 1, 3> goal_yaw;
        initial_yaw.setZero();
        goal_yaw.setZero();
        initial_yaw(0, 0) = odom_yaw;
        goal_yaw(0, 0) = odom_yaw;
        Eigen::Matrix<double, 1, Eigen::Dynamic> yaw_waypoints(1, 0);
        Trajectory yaw_trajectory =
                poly_interpo::minimumJerkInterpolation<1>(
                        initial_yaw, goal_yaw, yaw_waypoints, durations);

        const double start_wt = ros_ptr_->getSimTime();
        position_trajectory.start_WT = start_wt;
        yaw_trajectory.start_WT = start_wt;
        ExpTraj recovery_exp;
        recovery_exp.setTrajectory(start_wt, position_trajectory,
                                   yaw_trajectory);
        // This is an intermediate topology-changing manoeuvre. The mission
        // goal remains unchanged and is replanned after the lift finishes.
        recovery_exp.setGoalConnectedFlag(false);

        CmdTraj::Candidate candidate;
        if (!CmdTraj::buildCandidate(recovery_exp, candidate) ||
            !commitTrajectoryCandidate(
                    std::move(candidate),
                    "PlanFromRest/certified_vertical_recovery")) {
            ros_ptr_->warn(
                    " -- [TRAJ_GUARD_VERTICAL_RECOVERY_REJECTED] "
                    "lift={:.3f}m duration={:.3f}s start_z={:.3f} target_z={:.3f}",
                    distance, duration, lift_start.z(), lift_goal.z());
            return false;
        }

        last_exp_traj_info_ = recovery_exp;
        robot_on_backup_traj_ = false;
        gi_.new_goal = false;
        guard_rest_to_rest_hold_until_wt_ =
                start_wt + cmd_traj_info_.getTotalDuration();
        ros_ptr_->vizCommittedTraj(cmd_traj_info_.posTraj(), -1);
        latest_replan.setRetCode(
                SUPER_RET_CODE::SUPER_SUCCESS_NO_BACKUP);
        ros_ptr_->warn(
                " -- [TRAJ_GUARD_VERTICAL_RECOVERY] action=commit "
                "lift={:.3f}m duration={:.3f}s start_z={:.3f} target_z={:.3f} "
                "stop_source={} odom_speed={:.3f}",
                distance, duration, lift_start.z(), lift_goal.z(),
                certified_stop ? "certified_brake" : "stationary_odom",
                odom_speed);
        return true;
    }

    RET_CODE
    SuperPlanner::PlanFromRest(const Vec3f &goal_p,
                               const double &goal_yaw,
                               const bool &new_goal) {
        std::lock_guard<std::mutex> guard(replan_lock_);
        if (cfg_.guard_topology_reroute_en &&
            (!guard_topology_goal_valid_ ||
             (guard_topology_goal_ - goal_p).norm() > cfg_.resolution)) {
            resetTopologyRecoveryState();
            guard_topology_goal_ = goal_p;
            guard_topology_goal_valid_ = true;
        }
        latest_replan.reset();
        latest_replan.setGoal(goal_p, goal_yaw, robot_state_);
        if (robot_state_.rcv == false) {
            ros_ptr_->warn(" -- [SUPER] in [PlanFromRest]: No odom, force return.");
            latest_replan.setRetCode(SUPER_RET_CODE::SUPER_NO_ODOM);
            return FAILED;
        }
        gi_.goal_p = goal_p;
        gi_.goal_yaw = goal_yaw;
        gi_.new_goal = new_goal;
        gi_.goal_valid = true;
        vec_Vec3f viz_pts{goal_p, robot_state_.p};

        {
            TimeConsuming t_viz("viz goal path", false);
            ros_ptr_->vizGoalPath(viz_pts);
            time_consuming_[VISUALIZATION] += t_viz.stop();
        }


        /// 1) First, shift the start_point to free space.
        Vec3f local_star_pt;
        {
            auto map_read_transaction = map_ptr_->acquireMapReadTransaction();
            if (!map_ptr_->getNearestCellNot(GridType::OCCUPIED, robot_state_.p, local_star_pt, 3.0)) {
                ros_ptr_->error(
                        " -- [SUPER] in [PlanFromRest] Local start point is deeply occupied, which should not happened.");
                latest_replan.setRetCode(SUPER_RET_CODE::SUPER_NO_START_POINT);
                return FAILED;
            }
        }
        latest_replan.setLocalStartP(local_star_pt);

        if (cfg_.guard_topology_reroute_en) {
            const Vec3f episode_position = robot_state_.p;
            if (!guard_topology_episode_anchor_valid_) {
                guard_topology_episode_anchor_ = episode_position;
                guard_topology_episode_anchor_valid_ = true;
            } else {
                const double horizontal_progress =
                        (episode_position.head<2>() -
                         guard_topology_episode_anchor_.head<2>()).norm();
                if (std::isfinite(horizontal_progress) &&
                    horizontal_progress >=
                            cfg_.guard_topology_episode_progress_reset_m) {
                    const int old_local_recoveries =
                            guard_topology_local_escape_recoveries_;
                    const int old_vertical_recoveries =
                            guard_topology_saturation_recoveries_;
                    const int old_base_recoveries =
                            guard_topology_base_no_path_recoveries_;
                    const bool certified_stop =
                            guard_certified_stop_for_reroute_.load(
                                    std::memory_order_acquire);
                    clearTopologyRecoverySearchState();
                    guard_certified_stop_for_reroute_.store(
                            certified_stop, std::memory_order_release);
                    guard_topology_local_escape_recoveries_ = 0;
                    guard_topology_saturation_recoveries_ = 0;
                    guard_topology_base_no_path_recoveries_ = 0;
                    guard_topology_epoch_ = 0;
                    guard_topology_episode_anchor_ = episode_position;
                    guard_topology_episode_anchor_valid_ = true;
                    ros_ptr_->warn(
                            " -- [TRAJ_GUARD_RECOVERY_EPISODE_RESET] "
                            "reason=horizontal_progress progress={:.3f}m "
                            "threshold={:.3f}m prior_local={} "
                            "prior_vertical={} prior_base={}",
                            horizontal_progress,
                            cfg_.guard_topology_episode_progress_reset_m,
                            old_local_recoveries,
                            old_vertical_recoveries,
                            old_base_recoveries);
                }
            }
        }

        const char *test_force_local_escape =
                std::getenv("SUPER_TEST_FORCE_LOCAL_ESCAPE_ONCE");
        if (!guard_test_local_escape_injected_ &&
            test_force_local_escape != nullptr &&
            std::string(test_force_local_escape) == "1" &&
            cfg_.guard_topology_local_escape_en &&
            cfg_.guard_viability_en) {
            Vec3f test_direction = goal_p - robot_state_.p;
            test_direction.z() = 0.0;
            if (!test_direction.array().isFinite().all() ||
                test_direction.norm() < cfg_.resolution) {
                test_direction = Vec3f(std::cos(robot_state_.yaw),
                                       std::sin(robot_state_.yaw), 0.0);
            }
            guard_local_escape_direction_ = test_direction.normalized();
            guard_local_escape_pending_.store(true,
                                              std::memory_order_release);
            guard_test_local_escape_skip_first_direction_ = true;
            guard_test_local_escape_injected_ = true;
            ros_ptr_->warn(
                    " -- [TEST_FAULT_LOCAL_ESCAPE_ARM] "
                    "action=skip_first_then_certify direction="
                    "[{:.3f},{:.3f},{:.3f}]",
                    guard_local_escape_direction_.x(),
                    guard_local_escape_direction_.y(),
                    guard_local_escape_direction_.z());
        }

        if (tryCommitCertifiedLocalEscape(local_star_pt)) {
            return SUCCESS;
        }
        if (tryCommitCertifiedVerticalRecovery(local_star_pt)) {
            return SUCCESS;
        }

        /// 2) Generate Exp traj
        ExpTraj exp_traj_info;
        BackupTraj back_traj_info;
        last_exp_traj_info_.setEmpty();
        local_start_p_ = local_star_pt;
        RET_CODE exp_ret_code = generateExpTraj(last_exp_traj_info_, exp_traj_info);
        //GenerateRestToRestExpTraj(local_star_pt, exp_traj_info);
        if (exp_ret_code == FAILED) {
            if (tryCommitCertifiedDirectGoalFallback(local_star_pt, goal_p)) {
                return SUCCESS;
            }
            ros_ptr_->warn(" -- [SUPER] in [PlanFromRest] GenerateExpTrajectory failed with {}.",
                           RET_CODE_STR[exp_ret_code].c_str());
            return FAILED;
        } else {
            ros_ptr_->info(" -- [SUPER] in [PlanFromRest] GenerateExpTrajectory SUCCESS.");
        }

        back_traj_info.setEmpty();
        RET_CODE back_ret_code = generateBackupTrajectory(exp_traj_info, back_traj_info);;

        if (back_ret_code == SUCCESS) {
            if (cfg_.print_log) {
                ros_ptr_->info(" -- [SUPER] in [PlanFromRest] generateBackupTrajectory SUCCESS.");
            }

            CmdTraj::Candidate candidate;
            std::string rejected_segment;
            bool committed = CmdTraj::buildCandidate(
                    exp_traj_info, back_traj_info, candidate) &&
                    commitTrajectoryCandidate(
                            std::move(candidate), "PlanFromRest/with_backup",
                            &rejected_segment);
            bool used_certified_stop_fallback = false;
            // BackupTrajOpt is independent from the EXP corridor optimizer.
            // A guard failure confined to its appended portion does not prove
            // the outgoing EXP topology is bad, so never turn that failure
            // into an A* route blocker. When the viability guard is enabled,
            // retry the already-generated EXP by itself: commit still requires
            // the full geometric guard and a certified stop from every sampled
            // state in the configured horizon. This is a bounded certified-
            // stop fallback, not an unchecked no-backup commit.
            if (!committed && cfg_.guard_viability_en &&
                (rejected_segment == "APPENDED_BACKUP" ||
                 rejected_segment == "EXP_TO_BACKUP_STITCH")) {
                CmdTraj::Candidate exp_only_candidate;
                if (CmdTraj::buildCandidate(exp_traj_info,
                                             exp_only_candidate) &&
                    commitTrajectoryCandidate(
                            std::move(exp_only_candidate),
                            "PlanFromRest/certified_stop_fallback")) {
                    committed = true;
                    used_certified_stop_fallback = true;
                    ros_ptr_->warn(
                            " -- [TRAJ_GUARD_BACKUP_FALLBACK] rejected_segment={} "
                            "action=commit_guarded_exp_with_viable_stops",
                            rejected_segment);
                }
            }
            if (!committed) {
                return FAILED;
            }
            last_exp_traj_info_ = exp_traj_info;
            robot_on_backup_traj_ = false;
            gi_.new_goal = false;

            // For visualization
            {
                TimeConsuming t_viz("viz goal VisualizeCommitTrajectory", false);
                ros_ptr_->vizCommittedTraj(
                        cmd_traj_info_.posTraj(),
                        used_certified_stop_fallback
                                ? -1
                                : cmd_traj_info_.getBackupTrajStartTT());
                time_consuming_[VISUALIZATION] += t_viz.stop();
                latest_replan.setRetCode(
                        used_certified_stop_fallback
                                ? SUPER_RET_CODE::SUPER_SUCCESS_NO_BACKUP
                                : SUPER_RET_CODE::SUPER_SUCCESS_WITH_BACKUP);
            }

            return SUCCESS;
        } else if (back_ret_code == FINISH || back_ret_code == NO_NEED) {
            if (cfg_.print_log) {
                ros_ptr_->info(" -- [SUPER] in [PlanFromRest] generateBackupTrajectory Finish or NO_NEED.");
            }
            robot_on_backup_traj_ = false;
            CmdTraj::Candidate candidate;
            if (!CmdTraj::buildCandidate(exp_traj_info, candidate) ||
                !commitTrajectoryCandidate(std::move(candidate), "PlanFromRest/no_backup")) {
                return FAILED;
            }
            last_exp_traj_info_ = exp_traj_info;
            gi_.new_goal = false;

            // For visualization
            TimeConsuming t_viz("viz goal VisualizeCommitTrajectory", false);
            {
                ros_ptr_->vizCommittedTraj(cmd_traj_info_.posTraj(), -1);
                time_consuming_[VISUALIZATION] += t_viz.stop();
            }
            latest_replan.setRetCode(SUPER_RET_CODE::SUPER_SUCCESS_NO_BACKUP);
            return SUCCESS;
        }

        // BackupTraj's CIRI construction can be infeasible at a certified
        // stopped pose even though the already-generated outgoing EXP is
        // geometrically safe. Without this branch PlanFromRest regenerates
        // the same valid EXP and fails the independent backup corridor at the
        // same seed line indefinitely (observed >1,400 times on seed9).
        // The viability guard is the replacement certificate here: it proves
        // a dynamically-limited, map-safe emergency stop exists from sampled
        // states along the EXP horizon. Commit still passes through both the
        // full geometric guard and that stop-viability check.
        if (back_ret_code == FAILED && cfg_.guard_viability_en) {
            CmdTraj::Candidate exp_only_candidate;
            if (CmdTraj::buildCandidate(exp_traj_info,
                                         exp_only_candidate) &&
                commitTrajectoryCandidate(
                        std::move(exp_only_candidate),
                        "PlanFromRest/backup_generation_fallback")) {
                last_exp_traj_info_ = exp_traj_info;
                robot_on_backup_traj_ = false;
                gi_.new_goal = false;
                ros_ptr_->vizCommittedTraj(cmd_traj_info_.posTraj(), -1);
                latest_replan.setRetCode(
                        SUPER_RET_CODE::SUPER_SUCCESS_NO_BACKUP);
                ros_ptr_->warn(
                        " -- [TRAJ_GUARD_BACKUP_GENERATION_FALLBACK] "
                        "action=commit_guarded_exp_with_viable_stops");
                return SUCCESS;
            }
            ros_ptr_->warn(
                    " -- [TRAJ_GUARD_BACKUP_GENERATION_FALLBACK_REJECTED] "
                    "action=retain_certified_stop");
        }
        ros_ptr_->warn(" -- [SUPER] in [PlanFromRest] generateBackupTrajectory return [{}], force return",
                       RET_CODE_STR[back_ret_code].c_str());
        return FAILED;
    }


    RET_CODE
    SuperPlanner::ReplanOnce(const Vec3f &goal_p,
                             const double &goal_yaw,
                             const bool &new_goal) {
        TimeConsuming replan_total_t("ReplanOnce", false);
        std::lock_guard<std::mutex> guard(replan_lock_);

        // Certified vertical and direct-goal recoveries are complete
        // rest-to-rest manoeuvres. Do not let the normal 15 Hz moving-state
        // replanner replace either before its terminal stop.
        if (ros_ptr_->getSimTime() < guard_rest_to_rest_hold_until_wt_) {
            return FAILED;
        }

        gi_.goal_p = goal_p;
        gi_.goal_yaw = goal_yaw;
        gi_.new_goal = new_goal;
        gi_.goal_valid = true;
        latest_replan.reset();
        latest_replan.setGoal(goal_p, goal_yaw, robot_state_);

        vec_Vec3f viz_pts{goal_p, robot_state_.p};

        {
            TimeConsuming t_viz("tviz", false);
            ros_ptr_->vizGoalPath(viz_pts);
            time_consuming_[VISUALIZATION] += t_viz.stop();
        }


        /// 1) Replan EXP traj
        ExpTraj exp_traj_info;
        TimeConsuming t_exp("t_exp", false);
        RET_CODE exp_ret_code = generateExpTraj(last_exp_traj_info_, exp_traj_info);
        time_consuming_[GENERATE_EXP_TRAJ] = t_exp.stop();

        if (exp_ret_code == FAILED) {
            ros_ptr_->warn(" -- [SUPER] in [ReplanOnce]: GenerateExpTrajectory failed, force return");
            return FAILED;
        } else if (exp_ret_code == NEW_TRAJ) {
            if (cfg_.print_log) {
                ros_ptr_->info(" -- [SUPER] in [ReplanOnce]: Last epx traj end, switch to new traj.");
            }
            return NEW_TRAJ;
        } else if (exp_ret_code == EMER) {
            ros_ptr_->warn(" -- [SUPER] in [ReplanOnce]: Replan failed, switch to emer.");
            return EMER;
        } else if (exp_ret_code == SUCCESS) {
            if (cfg_.print_log) {
                ros_ptr_->info(" -- [SUPER] in [ReplanOnce]: Replan a new exp traj success.");
            }
        } else if (exp_ret_code == NO_NEED) {
            if (cfg_.print_log)
                ros_ptr_->info(" -- [SUPER] in [ReplanOnce]: No need to replan a new exp traj, use last one.");
        }

        {
            TimeConsuming t_viz("tviz", false);
            ros_ptr_->vizYawTraj(exp_traj_info.posTraj(), exp_traj_info.yawTraj());
            time_consuming_[VISUALIZATION] += t_viz.stop();
        }


        BackupTraj back_traj_info;
        // 2）生成back轨迹
        TimeConsuming t_back("t_back", false);
        RET_CODE back_ret_code = generateBackupTrajectory(exp_traj_info, back_traj_info);
        time_consuming_[GENERATE_BACK_TRAJ] = t_back.stop();

        {
            ft += time_consuming_[EPX_TRAJ_FRONTEND] + time_consuming_[BACK_TRAJ_FRONTEND];
            ft_cnt++;
            bt += time_consuming_[BACK_TRAJ_OPT] + time_consuming_[EXP_TRAJ_OPT];
            bt_cnt++;
        }

        double replan_dt = replan_total_t.stop();
        if (replan_dt > cfg_.replan_forward_dt * 0.9) {
            ros_ptr_->warn(" -- [SUPER] in [ReplanOnce]: Replan overtime, check parameters, replan dt = {}.", replan_dt);
            return FAILED;
        }

        if (back_ret_code == SUCCESS) {
            CmdTraj::Candidate candidate;
            if (!CmdTraj::buildCandidate(exp_traj_info, back_traj_info, candidate) ||
                !commitTrajectoryCandidate(std::move(candidate), "ReplanOnce/with_backup")) {
                return FAILED;
            }
            last_exp_traj_info_ = exp_traj_info;
            robot_on_backup_traj_ = false;
            gi_.new_goal = false;

            {
                // For visualization
                TimeConsuming t_viz("tviz", false);
                ros_ptr_->vizCommittedTraj(cmd_traj_info_.posTraj(), cmd_traj_info_.getBackupTrajStartTT());
                time_consuming_[VISUALIZATION] += t_viz.stop();
            }

            latest_replan.setRetCode(SUPER_SUCCESS_WITH_BACKUP);
            if (cfg_.print_log)
                ros_ptr_->info(" -- [SUPER] in [ReplanOnce]: Replan a new back traj success, all replan success.");
            return SUCCESS;
        } else if (back_ret_code == NO_NEED) {
            // 这次生成backup轨迹的点没有意义,
            robot_on_backup_traj_ = false;
            last_exp_traj_info_ = exp_traj_info;
            gi_.new_goal = false;


            {
                TimeConsuming t_viz("tviz", false);
                ros_ptr_->vizCommittedTraj(cmd_traj_info_.posTraj(), -1);
                time_consuming_[VISUALIZATION] += t_viz.stop();

            }

            if (cfg_.print_log)
                ros_ptr_->info(" -- [SUPER] in [ReplanOnce]: No need back traj success, all replan success.");
            latest_replan.setRetCode(SUPER_SUCCESS_NO_BACKUP);
            return SUCCESS;
        } else if (back_ret_code == FINISH) {
            // Which means the exp traj is all in known free, no need for backup traj
            CmdTraj::Candidate candidate;
            if (!CmdTraj::buildCandidate(exp_traj_info, candidate) ||
                !commitTrajectoryCandidate(std::move(candidate), "ReplanOnce/no_backup")) {
                return FAILED;
            }
            last_exp_traj_info_ = exp_traj_info;
            robot_on_backup_traj_ = false;
            gi_.new_goal = false;

            {
                TimeConsuming t_viz("tviz", false);
                ros_ptr_->vizCommittedTraj(cmd_traj_info_.posTraj(), -1);
                time_consuming_[VISUALIZATION] += t_viz.stop();
            }

            if (cfg_.print_log)
                ros_ptr_->info(" -- [SUPER] in [ReplanOnce]: No need back traj success, all replan success.");
            latest_replan.setRetCode(SUPER_SUCCESS_NO_BACKUP);
            return SUCCESS;
        }
        ros_ptr_->warn(" -- [SUPER] in [ReplanOnce]: generateBackupTrajectory return {}, replan Failed return",
                       RET_CODE_STR[back_ret_code].c_str());
        return FAILED;
    }

    void SuperPlanner::getOneHeartbeatTime(double &start_WT_pos, bool &traj_finish) {
        CmdTraj::Sample sample;
        if (!cmd_traj_info_.evaluate(ros_ptr_->getSimTime(), sample)) {
            start_WT_pos = 0.0;
            traj_finish = true;
            return;
        }
        start_WT_pos = sample.start_wt;
        traj_finish = sample.finished;
        robot_on_backup_traj_ = sample.on_backup;
    }

    Trajectory SuperPlanner::getCommittedPositionTrajectory() {
        return cmd_traj_info_.posTraj();
    }

    Trajectory SuperPlanner::getCommittedYawTrajectory() {
        return cmd_traj_info_.yawTraj();
    }


    void SuperPlanner::getOneCommandFromTraj(StatePVAJ &pvaj,
                                             double &yaw,
                                             double &yaw_dot,
                                             bool &on_backup_traj,
                                             bool &traj_finish) {
        CmdTraj::Sample sample;
        if (!cmd_traj_info_.evaluate(ros_ptr_->getSimTime(), sample)) {
            pvaj.setZero();
            yaw = 0.0;
            yaw_dot = 0.0;
            on_backup_traj = false;
            traj_finish = true;
            return;
        }
        pvaj = sample.pvaj;
        yaw = sample.yaw;
        yaw_dot = sample.yaw_dot;
        on_backup_traj = sample.on_backup;
        traj_finish = sample.finished;
        robot_on_backup_traj_ = sample.on_backup;
    }

    bool SuperPlanner::getOneCommandSample(CmdTraj::Sample &sample,
                                           const std::uint64_t expected_generation) const {
        return cmd_traj_info_.evaluate(ros_ptr_->getSimTime(), sample,
                                       expected_generation);
    }

    CmdTraj::Snapshot SuperPlanner::getCommittedTrajectorySnapshot() const {
        return cmd_traj_info_.snapshot();
    }

    std::uint64_t SuperPlanner::getCommittedTrajectoryGeneration() const {
        return cmd_traj_info_.generation();
    }


    void SuperPlanner::getModuleTimeConsuming(vector<double> &time) {
        time = time_consuming_;
        std::fill(time_consuming_.begin(), time_consuming_.end(), 0);
    }


    RET_CODE SuperPlanner::generateExpTraj(ExpTraj &last_exp_traj_info, ExpTraj &out_exp_traj_info) {
        /* 1) Log the exp traj frontend time*/
        TimeConsuming t_exp_frontend("t_exp_frontend", false);

        // A planning frontend must see one coherent committed map. Release
        // this transaction before trajectory optimization so map commits are
        // not starved by the CPU-heavy solver.
        auto map_read_transaction = map_ptr_->acquireMapReadTransaction();

        // use hot init or not, just prepare a guide path, a guide t, init and fina state and sfc for exp traj opt
        StatePVAJ pos_init_state, pos_fina_state;
        PolytopeVec sfc;
        vec_Vec3f guide_path;
        // the guide_stamp saves a TT
        vector<double> guide_stamp;
        double guide_path_end_vel{0.0};
        int reserve_size = cfg_.planning_horizon / cfg_.resolution * 1.2;
        guide_path.reserve(reserve_size);
        guide_stamp.reserve(reserve_size);

        Vec4f init_yaw{robot_state_.yaw, 0, 0, 0};
        Vec4f fina_yaw{0, 0, 0, 0};


        // alias for last_exp_traj_info
        Trajectory guide_pos_traj, guide_yaw_traj, last_exp_traj;

        // record the wall time (WT) and the trajectory time (TT) at the start of the replan.
        const double replan_process_start_WT = ros_ptr_->getSimTime();
        double replan_process_start_TT, replan_state_TT;

        /* 2) Check last exp traj */
        if (last_exp_traj_info.empty()) {
            /* 2.1) Perform rest2rest exp traj generation */
            // just skip the first part of the guide trajectory
            pos_init_state.setZero();
            pos_init_state.col(0) = local_start_p_;
            replan_process_start_TT = -1;
            replan_state_TT = -1;
        } else {
            guide_pos_traj = cmd_traj_info_.posTraj(); // last_exp_traj;
            guide_yaw_traj = cmd_traj_info_.yawTraj(); //last_exp_traj_info.exp_yaw_traj;
            last_exp_traj = last_exp_traj_info.posTraj();

            replan_process_start_TT = replan_process_start_WT - last_exp_traj.start_WT;
            replan_state_TT = replan_process_start_TT + cfg_.replan_forward_dt;
            /* 2.2) Perform collision check on last exp traj*/
            vector<TimePosPair> last_exp_traj_time_pos;
            vector<double> last_exp_traj_vel;


            // check early exit condition
            // 1) if the replan state is beyond the last cmd traj, return NO_NEED
            if (replan_state_TT >= cmd_traj_info_.getTotalDuration()) {
                out_exp_traj_info = last_exp_traj_info;

                if (robot_on_backup_traj_) {
                    if (cfg_.print_log)
                        ros_ptr_->warn(
                                " -- [SUPER] Replan, emergency stop, return FAILED and wait for plan form rest.");
                    return FAILED;
                }

                if (cfg_.print_log) {
                    ros_ptr_->warn(
                            " -- [generateExpTraj] replan_state_TT >= cmd_traj_info_.pos_traj.getTotalDuration(), return NONEED and wait for plan form rest.");
                }
                return NO_NEED;
            }

            if (!last_exp_traj_info.empty()) {
                if (replan_state_TT >= last_exp_traj.getTotalDuration()) {
                    out_exp_traj_info = last_exp_traj_info;
                    if (cfg_.print_log)
                        ros_ptr_->warn(
                                " -- [generateExpTraj] replan_state_TT >= last_exp_traj.getTotalDuration(), return NONEED and wait for plan form rest.");
                    if (robot_on_backup_traj_) {
                        if (cfg_.print_log)
                            ros_ptr_->warn(
                                    " -- [SUPER] Replan, emergency stop, return FAILED and wait for plan form rest.");
                        return FAILED;
                    } else {
                        return NO_NEED;
                    }
                }

                /// 1) Check a series of early termination conditions.
                if (!gi_.new_goal && last_exp_traj_info.getSFCSize() == 1 && last_exp_traj_info.connectedToGoal()) {
                    if (cfg_.print_log) {
                        ros_ptr_->warn(
                                " -- [SUPER] Replan, last exp have only one corridor and connected to goal return NONEED.");
                    }

                    out_exp_traj_info = last_exp_traj_info;
                    if (robot_on_backup_traj_) {
                        if (cfg_.print_log)
                            ros_ptr_->warn(
                                    " -- [SUPER] Replan, emergency stop, return FAILED and wait for plan form rest.");
                        return FAILED;
                    } else {
                        return NO_NEED;
                    }
                }

                if (!gi_.new_goal &&
                    (gi_.goal_p - last_exp_traj.getPos(replan_state_TT)).norm() < cfg_.resolution * 3) {
                    // Return if the traj close to goal
                    out_exp_traj_info = last_exp_traj_info;
                    out_exp_traj_info.setGoalConnectedFlag(true);

                    ros_ptr_->warn(" -- [SUPER] Replan, close to goal and return NONEED.");
                    if (robot_on_backup_traj_) {
                        ros_ptr_->warn(
                                " -- [SUPER] Replan, emergency stop, return FAILED and wait for plan form rest.");
                        return FAILED;
                    } else {
                        return NO_NEED;
                    }
                }
            }
            /// Ready for replan.
            out_exp_traj_info.setGoalConnectedFlag(false);

            // * 2) Check if in backup trajectory. While in backup trajectory,
            // *    the guide trajectory should be a part of cmd trajectory.
            // TODO: Why cannot directly replan on cmd traj? 241121

            // * 3) Perform collision check on the guide trajectory.
            // TODO 0929 critical change for hot init.
            double eval_t = replan_state_TT; //replan_process_start_TT;
            double guide_pos_traj_total_time = guide_pos_traj.getTotalDuration();

            Vec3f temp_pt, last_sample_pt;
            last_exp_traj_time_pos.clear();
            last_exp_traj_info.setWholeTrajKnownFreeFlag(true);
            last_sample_pt = guide_pos_traj.getPos(eval_t);
            eval_t += cfg_.sample_traj_dt;
            // * 4) 记录replan点在evaluated_pts上的id
            int replan_id = -1;
            for (; eval_t < guide_pos_traj_total_time; eval_t += cfg_.sample_traj_dt) {
                temp_pt = guide_pos_traj.getPos(eval_t);
                if ((temp_pt - last_sample_pt).norm() < cfg_.resolution * 0.8) {
                    continue;
                }

                rog_map::GridType temp_grid = map_ptr_->getInfGridType(temp_pt);

                if (temp_grid == rog_map::GridType::OCCUPIED || temp_grid == rog_map::GridType::OUT_OF_MAP) {
                    last_exp_traj_info.setWholeTrajKnownFreeFlag(false);
                    break;
                }
                if (eval_t > replan_state_TT && replan_id == -1) {
                    replan_id = last_exp_traj_time_pos.size();
                }
                last_exp_traj_time_pos.emplace_back(eval_t, temp_pt);
                last_exp_traj_vel.emplace_back(guide_pos_traj.getVel(eval_t).norm());
                last_sample_pt = temp_pt;
            }


            // * 6) Decide where to split the original exp trajecory and re-plan a new one with an A*,
            // *    If the whole trajectory if free,  the whole trajectory should be receding and if not, or a new goal
            // *    is given, we should only receiding a small distance and replan new trajectory ASAP
            double split_dis = cfg_.receding_dis;
            if (last_exp_traj_info.wholeTrajKnownFree() && !gi_.new_goal && cfg_.receding_dis > 0.0) {
                split_dis = std::numeric_limits<double>::max();
            }


            // * 7）Begin replan process, first get the replan state from the committed trajectory.
            if (!guide_pos_traj.getState(replan_state_TT, pos_init_state)) {
                ros_ptr_->warn(" -- [SUPER] Invalid traj or eval t");
                return FAILED;
            }
            // * Generate guide path with time stampe, for hot trajectory initialization
            // * the guide stamp is time from the replan start t
            guide_stamp.clear();
            guide_path.clear();
            if (split_dis <= 0 || last_exp_traj_time_pos.empty()) {
                /// No need receding, just path search.
                guide_path.push_back(pos_init_state.col(0));
                guide_stamp.push_back(0.0);
                last_exp_traj_time_pos.clear();
                last_exp_traj_time_pos.emplace_back(replan_state_TT, pos_init_state.col(0));
                guide_path_end_vel = robot_state_.v.norm();
            } else {
                temp_pt = last_exp_traj_time_pos.back().second;
                // * 8) Pop all evaluated pts after the sampled point.
                while (map_ptr_->isOccupiedInflate(temp_pt) ||
                       (temp_pt - pos_init_state.col(0)).norm() > split_dis) {
                    last_exp_traj_time_pos.pop_back();
                    last_exp_traj_vel.pop_back();
                    if (last_exp_traj_time_pos.empty()) {
                        ros_ptr_->warn(" -- [SUPER] WARN, all traj is collide in INF2");
                        break;
                    }
                    temp_pt = last_exp_traj_time_pos.back().second;
                }
                if (!last_exp_traj_time_pos.empty()) {
                    for (long unsigned int i = 0; i < last_exp_traj_time_pos.size(); i++) {
                        guide_path.push_back(last_exp_traj_time_pos[i].second);
                        guide_stamp.push_back(last_exp_traj_time_pos[i].first - last_exp_traj_time_pos.front().first);
                        guide_path_end_vel = last_exp_traj_vel[i];
                    }
                } else {
                    guide_path.push_back(pos_init_state.col(0));
                    guide_stamp.push_back(0.0);
                    last_exp_traj_time_pos.emplace_back(replan_state_TT, pos_init_state.col(0));
                    guide_path_end_vel = robot_state_.v.norm();
                }
            }
        }

        // second, geometry part of the guide path
        ///=================The Second Part of Guide Path ================================================

        double guide_path_length = geometry_utils::computePathLength(guide_path);
        double temp_horizon = cfg_.planning_horizon - guide_path_length;

        vector<int> path_passed_waypoint_id;
        vec_Vec3f inside_poly_goals;
        vector<int> sfc_waypoint_ids;

        if (guide_path.empty() ||
            ((guide_path.front() - pos_init_state.col(0)).norm() > 1e-2)) {
            guide_path.insert(guide_path.begin(), pos_init_state.col(0));
            guide_stamp.insert(guide_stamp.begin(), 0.0);
        }

        // if need a geometry path
        if (temp_horizon > cfg_.resolution * 2) {
            /// start point TT + exp_traj start_WT
//            double path_search_start_point_WT = guide_stamp.back() + guide_pos_traj.start_WT;
            // if the goal is close to the last point of the guide path, just add the goal to the guide path
            if ((guide_path.back() - gi_.goal_p).norm() < cfg_.resolution * 5) {
                guide_stamp.push_back(guide_stamp.back() +
                                      (guide_path.back() - gi_.goal_p).norm() / cfg_.exp_traj_cfg.max_vel);
                guide_path.push_back(gi_.goal_p);
                // NO NEED
            } else {
                vec_Vec3f new_path;
                // project goal within the planning horizon
//                const Vec3f dir = (gi_.goal_p - robot_state_.p).normalized();
//                const double dis2goal = (gi_.goal_p - robot_state_.p).norm();
//                Vec3f cadi_p = gi_.goal_p;
//                if(dis2goal > cfg_.planning_horizon) {
//                    double proj_l = cfg_.planning_horizon;
//                    Vec3f cadi_p = robot_state_.p + dir * proj_l;
//                    int max_iter = 100;
//                    while(map_ptr_->isOccupiedInflate(cadi_p) && max_iter-- > 0) {
//                        if(map_ptr_->getNearestInfCellNot(OCCUPIED, cadi_p, cadi_p, 1.0)) {
//                            break;
//                        }
//                        proj_l -= 2.0;
//                        if(proj_l < 1){
//                            ros_ptr_->warn(" -- [SUPER] Project goal failed");
//                            gi_.goal_valid = false;
//                            return FAILED;
//                        }
//                        cadi_p = robot_state_.p + dir * proj_l;
//                    }
//                    if(max_iter <= 0) {
//                        ros_ptr_->warn(" -- [SUPER] Project goal failed");
//                        gi_.goal_valid = false;
//                        return FAILED;
//                    }
//                }
                if (!PathSearch(guide_path.back(), gi_.goal_p, temp_horizon,
                                new_path, last_exp_traj_info.empty())) {
                    ros_ptr_->warn(" -- [SUPER] PathSearch for new path failed");
                    return FAILED;
                }
                if (new_path.size() < 2) {
                    ros_ptr_->warn(" -- [SUPER] PathSearch for new path failed");
                    return FAILED;
                }

                // compute total dis
                // backward compute dis for all points
                double total_dis{0.0};
                vector<double> dis(new_path.size());
                Vec3f last_p = new_path.back();
                for (int i = new_path.size() - 2; i >= 0; i--) {
                    auto d = (new_path[i] - last_p).norm();
                    total_dis += d;
                    dis[i+1] = total_dis;
                    last_p = new_path[i];
                }
                total_dis += (new_path.front() - guide_path.back()).norm();
                dis[0] = total_dis;
//                for (int i = 0; i < dis.size(); i++) {
//                    cout << dis[i] << " ";
//                }
//                cout << endl;
                vector<double> stamps(new_path.size(), 0);
                vector<double> dt(new_path.size(), 0);
                double last_stamp = 0;
                for (int i = dis.size() - 1; i >= 0; i--) {
                    double vel;
                    geometry_utils::simplePMTimeAllocator(cfg_.exp_traj_cfg.max_acc, cfg_.exp_traj_cfg.max_vel,
                                                          guide_path_end_vel,
                                                          total_dis,
                                                          dis[i], stamps[i], vel);
                    dt[i] = stamps[i] - last_stamp;
                    last_stamp = stamps[i];
                }
                double time_stamp = guide_stamp.back();

//                for (int i = 0; i < stamps.size(); i++) {
//                    cout << stamps[i] << " ";
//                }
//                cout << endl;
//
//                for (int i = 0; i < dt.size(); i++) {
//                    cout << dt[i] << " ";
//                }
//                cout << endl;

                for (long unsigned int i = 1; i < new_path.size(); i++) {
                    double t = dt[i];
                    time_stamp += t;
                    guide_path.emplace_back(new_path[i]);
                    guide_stamp.emplace_back(time_stamp);
                }
            }
        }

        const bool connected_goal = (guide_path.back().head(2) - gi_.goal_p.head(2)).norm() < cfg_.resolution * 2;
        out_exp_traj_info.setGoalConnectedFlag(connected_goal);

        sfc.clear();
        {
            TimeConsuming t_viz("tviz", false);
            ros_ptr_->vizFrontendPath(guide_path);
            time_consuming_[VISUALIZATION] += t_viz.stop();
        }
        shifted_sfc_start_pt_ = Vec3f(9999,9999,9999);
        bool use_guard_retry_corridor = false;
        bool guard_retry_alternated_to_normal = false;
        if (cg_guard_retry_ptr_ &&
            guard_corridor_retry_pending_.load(std::memory_order_acquire)) {
            const int attempt = guard_corridor_retry_attempts_.fetch_add(
                    1, std::memory_order_acq_rel) + 1;
            // Retry mode stays on until a candidate finally commits, so a
            // persistently rejected point would otherwise retry the exact
            // same tight-margin corridor generator indefinitely. Every Nth
            // consecutive attempt, fall back to the normal (raw-obstacle,
            // wider-margin) generator instead, so a stall isn't permanently
            // locked into one corridor-generation strategy. This never
            // loosens what the guard accepts -- validatePositionTrajectory
            // checks whatever candidate comes out the same way either way.
            const bool alternate_this_attempt =
                    cfg_.guard_corridor_retry_alternate_every > 0 &&
                    attempt % cfg_.guard_corridor_retry_alternate_every == 0;
            use_guard_retry_corridor = !alternate_this_attempt;
            guard_retry_alternated_to_normal = alternate_this_attempt;
        }
        auto &active_cg = use_guard_retry_corridor ? cg_guard_retry_ptr_ : cg_ptr_;
        if (use_guard_retry_corridor) {
            ros_ptr_->warn(" -- [SUPER] Retrying EXP with inflated guard corridor.");
        } else if (guard_retry_alternated_to_normal) {
            ros_ptr_->warn(" -- [SUPER] Guard corridor retry: alternating back "
                           "to normal corridor generator this attempt.");
        }
        bool bool_ret_code = active_cg->SearchPolytopeOnPath(
                guide_path, sfc, shifted_sfc_start_pt_, cfg_.use_fov_cut,
                guard_topology_avoidance_centers_, guard_topology_avoidance_radii_);

        if (!bool_ret_code) {
            // A moving-state ReplanOnce failure leaves the previously
            // committed trajectory in charge.  It is neither a certified
            // stop nor evidence that repeated PlanFromRest attempts selected
            // one unusable topology, so never mutate stopped-state recovery
            // from this path.
            if (!cfg_.guard_topology_reroute_en ||
                !last_exp_traj_info.empty()) {
                guard_topology_corridor_failures_ = 0;
                ros_ptr_->warn(" -- [SUPER] SearchPolytopeOnPath for new path failed");
                return FAILED;
            }
            ++guard_topology_corridor_failures_;
            if (guard_topology_corridor_failures_ >=
                cfg_.guard_topology_reroute_no_path_reset_attempts) {
                guard_topology_corridor_failures_ = 0;
                if (guard_topology_avoidance_centers_.empty()) {
                    // A* can return the same guide indefinitely even when its
                    // adjacent CIRI polytopes have no usable overlap.  The old
                    // counter only advanced when a temporary blocker already
                    // existed, so this base-corridor failure was a permanent
                    // PlanFromRest loop.  Reject the selected outgoing route
                    // after a bounded number of identical failures and let A*
                    // choose a different topology.  The resulting candidate
                    // still has to pass the unchanged corridor, geometric and
                    // stop-viability checks before it can be committed.
                    if (armTopologyRouteBlockFromGuidePath(
                                guide_path, pos_init_state.col(0),
                                "corridor_continuity_failed")) {
                        guard_topology_no_path_failures_ = 0;
                        ++guard_topology_epoch_;
                        guard_corridor_retry_pending_.store(
                                true, std::memory_order_release);
                        ros_ptr_->warn(
                                " -- [TRAJ_GUARD_CORRIDOR_RECOVERY] epoch={} "
                                "zones={} reason=corridor_continuity_failed "
                                "action=change_topology",
                                guard_topology_epoch_,
                                guard_topology_avoidance_centers_.size());
                    } else if (cfg_.guard_topology_vertical_recovery_en) {
                        guard_vertical_recovery_pending_.store(
                                true, std::memory_order_release);
                        ++guard_topology_epoch_;
                        ros_ptr_->warn(
                                " -- [TRAJ_GUARD_CORRIDOR_RECOVERY] epoch={} "
                                "zones=0 reason=corridor_continuity_failed "
                                "action=guarded_vertical_lift",
                                guard_topology_epoch_);
                    }
                } else {
                    const std::size_t cleared_zones =
                            guard_topology_avoidance_centers_.size();
                    const Vec3f stopped_start = pos_init_state.col(0);
                    const double horizontal_collision_distance =
                            (guard_topology_stall_collision_.head<2>() -
                             stopped_start.head<2>()).norm();
                    const double collision_z =
                            guard_topology_stall_collision_.z();
                    Vec3f local_escape_direction =
                            stopped_start - guard_topology_stall_collision_;
                    local_escape_direction.z() = 0.0;
                    const bool start_adjacent_rejection =
                            guard_topology_stall_rejects_ > 0 &&
                            guard_topology_stall_collision_.array()
                                    .isFinite().all() &&
                            std::isfinite(horizontal_collision_distance) &&
                            horizontal_collision_distance <=
                                    cfg_.guard_topology_vertical_recovery_trigger_distance_m;
                    const bool local_escape_direction_valid =
                            local_escape_direction.array().isFinite().all() &&
                            local_escape_direction.norm() >= cfg_.resolution;
                    const bool arm_local_escape =
                            cfg_.guard_topology_local_escape_en &&
                            start_adjacent_rejection &&
                            local_escape_direction_valid &&
                            guard_topology_local_escape_recoveries_ <
                                    cfg_.guard_topology_local_escape_attempts;
                    // A vertical lift is only sensible when the rejected
                    // boundary is not above the stopped vehicle. Horizontal
                    // escape is valid for either sign because it moves away
                    // from the observed start-adjacent rejection and is still
                    // subject to the unchanged trajectory guard.
                    const bool arm_vertical_recovery =
                            cfg_.guard_topology_vertical_recovery_en &&
                            start_adjacent_rejection &&
                            collision_z <=
                                    stopped_start.z() + cfg_.resolution &&
                            guard_topology_saturation_recoveries_ <
                                    cfg_.guard_topology_saturation_vertical_attempts;
                    guard_topology_avoidance_centers_.clear();
                    guard_topology_avoidance_radii_.clear();
                    guard_topology_branch_directions_.clear();
                    guard_topology_branch_depths_.clear();
                    guard_topology_stall_generation_ = 0;
                    guard_topology_stall_collision_.setZero();
                    guard_topology_stall_rejects_ = 0;
                    guard_topology_no_path_failures_ = 0;
                    guard_topology_post_corridor_failures_ = 0;
                    ++guard_topology_epoch_;
                    if (arm_local_escape) {
                        guard_local_escape_direction_ =
                                local_escape_direction.normalized();
                        ++guard_topology_local_escape_recoveries_;
                        guard_local_escape_pending_.store(
                                true, std::memory_order_release);
                        ros_ptr_->warn(
                                " -- [TRAJ_GUARD_LOCAL_ESCAPE_ARM] "
                                "cleared_zones={} epoch={} attempt={}/{} "
                                "reason=corridor_no_path "
                                "horizontal_distance={:.3f} "
                                "direction=[{:.3f},{:.3f},{:.3f}] "
                                "action=escape_then_reroute",
                                cleared_zones, guard_topology_epoch_,
                                guard_topology_local_escape_recoveries_,
                                cfg_.guard_topology_local_escape_attempts,
                                horizontal_collision_distance,
                                guard_local_escape_direction_.x(),
                                guard_local_escape_direction_.y(),
                                guard_local_escape_direction_.z());
                    } else if (arm_vertical_recovery) {
                        ++guard_topology_saturation_recoveries_;
                        guard_vertical_recovery_pending_.store(
                                true, std::memory_order_release);
                        ros_ptr_->warn(
                                " -- [TRAJ_GUARD_VERTICAL_RECOVERY_ARM] "
                                "cleared_zones={} epoch={} attempt={}/{} "
                                "reason=corridor_no_path "
                                "horizontal_distance={:.3f} start_z={:.3f} "
                                "collision_z={:.3f} action=lift_then_reroute",
                                cleared_zones, guard_topology_epoch_,
                                guard_topology_saturation_recoveries_,
                                cfg_.guard_topology_saturation_vertical_attempts,
                                horizontal_collision_distance,
                                stopped_start.z(),
                                collision_z);
                    } else {
                        guard_corridor_retry_pending_.store(
                                true, std::memory_order_release);
                        ros_ptr_->warn(
                                " -- [TRAJ_GUARD_REROUTE_EPOCH_RESET] epoch={} "
                                "cleared_zones={} reason=corridor_no_path "
                                "action=certified_stop_reseed",
                                guard_topology_epoch_, cleared_zones);
                    }
                }
            }
            ros_ptr_->warn(" -- [SUPER] SearchPolytopeOnPath for new path failed");
            return FAILED;
        }
        guard_topology_corridor_failures_ = 0;
        {
            TimeConsuming t_viz("tviz", false);
            ros_ptr_->vizExpSfc(sfc);
            time_consuming_[VISUALIZATION] += t_viz.stop();
        }

        time_consuming_[EPX_TRAJ_FRONTEND] = t_exp_frontend.stop();
        map_read_transaction.unlock();


        pos_fina_state.setZero();
        pos_fina_state.col(0) = guide_path.back();
        if (cfg_.goal_vel_en && (gi_.goal_p - robot_state_.p).norm() > cfg_.planning_horizon / 2) {
            pos_fina_state.col(1) = (gi_.goal_p - robot_state_.p).normalized() * cfg_.exp_traj_cfg.max_vel / 2;
        }
        if ((pos_fina_state.col(0) - gi_.goal_p).norm() < cfg_.resolution * 2) {
            pos_fina_state.col(1).setZero();
            pos_fina_state.col(0) = gi_.goal_p;
        }

        // optimize and update exp traj
        bool temp_ret;
        Trajectory out_traj;
        TimeConsuming t_exp_opt("t_exp_opt", false);
        auto original_sfc = sfc;
        auto record_post_corridor_failure = [&](const char *reason) {
            // Moving-state replans retain the previously committed safe
            // trajectory and must not mutate stopped-state topology recovery.
            // PlanFromRest has an empty guide trajectory and a zero-PVA start.
            if (!cfg_.guard_topology_reroute_en ||
                !last_exp_traj_info.empty()) {
                guard_topology_post_corridor_failures_ = 0;
                return;
            }
            ++guard_topology_post_corridor_failures_;
            if (guard_topology_post_corridor_failures_ <
                cfg_.guard_topology_reroute_no_path_reset_attempts) {
                return;
            }

            guard_topology_post_corridor_failures_ = 0;
            if (armTopologyRouteBlockFromGuidePath(
                        guide_path, pos_init_state.col(0), reason)) {
                guard_topology_no_path_failures_ = 0;
                guard_topology_corridor_failures_ = 0;
                ++guard_topology_epoch_;
                guard_corridor_retry_pending_.store(
                        true, std::memory_order_release);
                ros_ptr_->warn(
                        " -- [TRAJ_GUARD_POST_CORRIDOR_RECOVERY] epoch={} "
                        "zones={} reason={} action=change_topology",
                        guard_topology_epoch_,
                        guard_topology_avoidance_centers_.size(), reason);
                return;
            }

            // Every bounded horizontal topology has now been tried. Clear the
            // temporary blockers and request one fully guarded rest-to-rest
            // lift; the next PlanFromRest then searches again from a distinct
            // vertical state instead of oscillating between the same routes.
            const std::size_t cleared_zones =
                    guard_topology_avoidance_centers_.size();
            guard_topology_avoidance_centers_.clear();
            guard_topology_avoidance_radii_.clear();
            guard_topology_branch_directions_.clear();
            guard_topology_branch_depths_.clear();
            guard_topology_stall_generation_ = 0;
            guard_topology_stall_collision_.setZero();
            guard_topology_stall_rejects_ = 0;
            guard_topology_no_path_failures_ = 0;
            guard_topology_corridor_failures_ = 0;
            ++guard_topology_epoch_;
            if (cfg_.guard_topology_vertical_recovery_en) {
                guard_vertical_recovery_pending_.store(
                        true, std::memory_order_release);
            }
            ros_ptr_->warn(
                    " -- [TRAJ_GUARD_POST_CORRIDOR_RECOVERY] epoch={} "
                    "cleared_zones={} reason={} action={}",
                    guard_topology_epoch_, cleared_zones, reason,
                    cfg_.guard_topology_vertical_recovery_en
                            ? "guarded_vertical_lift"
                            : "reseed_without_lift");
        };
        temp_ret = exp_traj_opt_->optimize(pos_init_state,
                                           pos_fina_state,
                                           guide_path,
                                           guide_stamp,
                                           sfc,
                                           out_traj);
        time_consuming_[EXP_TRAJ_OPT] = t_exp_opt.stop();
        {
            VecDf init_ts;
            vec_Vec3f init_ps;
            exp_traj_opt_->getInitValue(init_ts, init_ps);
            latest_replan.setExpCondition(init_ts, init_ps, pos_init_state, pos_fina_state, sfc);
        }
        if (!temp_ret) {
            record_post_corridor_failure("trajectory_optimization_failed");
            ros_ptr_->warn(" -- [SUPER] OptimizationExpTrajInPolytopes for new path failed");
            return FAILED;
        }
        double replan_total_t = (ros_ptr_->getSimTime() - replan_process_start_WT);
        if (replan_total_t > cfg_.replan_forward_dt) {
            record_post_corridor_failure("trajectory_optimization_overtime");
            ros_ptr_->warn(" -- [SUPER] Replan over time({})!!!! Return FAILED", replan_total_t);
            return FAILED;
        }
        guard_topology_post_corridor_failures_ = 0;

        {
            TimeConsuming t_viz("tviz", false);
            ros_ptr_->vizExpTraj(out_traj);
            time_consuming_[VISUALIZATION] += t_viz.stop();
        }

        double new_traj_WT = replan_process_start_WT;

        replan_process_start_TT = replan_process_start_WT - guide_pos_traj.start_WT;
        Trajectory temp_exp_traj;
        if (!last_exp_traj_info_.empty() &&
            !guide_pos_traj.getPartialTrajectoryByTime(replan_process_start_TT, replan_state_TT,
                                                       temp_exp_traj)) {
            ros_ptr_->error(" -- [SUPER] in [generateExpTraj]: getPartialTrajectoryByTime failed, force return");
            return FAILED;
        }
        out_exp_traj_info.setSFC(sfc);
        temp_exp_traj = temp_exp_traj + out_traj;
        temp_exp_traj.start_WT = new_traj_WT; //last_exp_traj_info.replan_start_WT ;

        if (!last_exp_traj_info.empty()) {
            StatePVAJ yaw_replan_state;
            if (!guide_yaw_traj.getState(replan_state_TT, yaw_replan_state)) {
                ros_ptr_->warn(" -- [SUPER] Invalid traj or eval t");
                return FAILED;
            }
            init_yaw = yaw_replan_state.row(0);
        }


        bool free_end{true};
        if (cfg_.goal_yaw_en && !std::isnan(gi_.goal_yaw) && connected_goal) {
            free_end = false;
            fina_yaw[0] = gi_.goal_yaw;
        }
        Trajectory new_traj, old_traj;

        if (!yaw_traj_opt_->optimize(init_yaw, fina_yaw, out_traj, new_traj, 3, false, free_end)) {
            ros_ptr_->error(" -- [SUPER] in [generateExpTraj]: YawTrajOpt failed, force return");
            return FAILED;
        }
        if (!last_exp_traj_info.empty()) {
            if (!guide_yaw_traj.getPartialTrajectoryByTime(replan_process_start_TT, replan_state_TT,
                                                           old_traj)) {
                ros_ptr_->error(" -- [SUPER] in [generateExpTraj]: getPartialTrajectoryByTime failed, force return");
                return FAILED;
            }
        }

        const auto temp_yaw_traj = old_traj + new_traj;
        // check if part of the exp on last backup
        double on_backup_end_TT{-1}, on_backup_start_TT{-1};
        if (!last_exp_traj_info.empty() && replan_state_TT > cmd_traj_info_.getBackupTrajStartTT()) {
            on_backup_start_TT = cmd_traj_info_.getBackupTrajStartTT() - replan_process_start_TT;
            on_backup_end_TT = replan_state_TT - replan_process_start_TT;
        }
        out_exp_traj_info.setTrajectory(new_traj_WT, temp_exp_traj, temp_yaw_traj, on_backup_start_TT,
                                        on_backup_end_TT);

        latest_replan.setExpYawTraj(temp_yaw_traj);
        latest_replan.setExpTraj(temp_exp_traj);

        return SUCCESS;
    }

    RET_CODE SuperPlanner::generateBackupTrajectory(ExpTraj &ref_exp_traj, BackupTraj &back_traj_info) {
        // The backup frontend also mixes line-of-sight, nearest-cell and
        // corridor queries. Pin those reads to one map commit, then release
        // before optimizing the backup polynomial.
        auto map_read_transaction = map_ptr_->acquireMapReadTransaction();
        drone_state_mutex_.lock();
        back_traj_info.setRobotPos(robot_state_.p);
        drone_state_mutex_.unlock();
        TimeConsuming t_back_frontend("t_back_frontend", false);
        double total_dur = ref_exp_traj.getTotalDuration();
        double start_t = ros_ptr_->getSimTime() - ref_exp_traj.getStartWallTime();


        if (start_t > total_dur - 0.01) {
            if (cfg_.print_log) {
                ros_ptr_->info(" -- [SUPER] in [generateBackupTrajectory]: start_t > total_dur, return NO_NEED");
            }
            return NO_NEED;
        }

        Vec3f temp_point;
        double out_t;
        bool all_traj_visible{true};
        // 同时记录每一个点的刹车时间和刹车距离
        vector<double> min_stop_dis;
        vector<TimePosPair> eval_ps;
        Vec3f temp_vel;

        // 记录当前时刻到最远时刻的所有可视部分
        Vec3f last_pos = ref_exp_traj.getPos(start_t);
        for (out_t = start_t; out_t < total_dur; out_t += cfg_.sample_traj_dt) {
            temp_point = ref_exp_traj.getPos(out_t);
            if ((last_pos - temp_point).norm() < cfg_.resolution * 0.8) {
                continue;
            }
            last_pos = temp_point;
            temp_vel = ref_exp_traj.getVel(out_t);
            // Compute initial
            double v_norm = temp_vel.norm();
            min_stop_dis.push_back(v_norm * v_norm / 2.0 / cfg_.exp_traj_cfg.max_acc);
            eval_ps.push_back(std::pair<double, Vec3f>(out_t, temp_point));
            const double min_dis =
                    cfg_.sensing_horizon > 0 ? std::min(cfg_.sensing_horizon, cfg_.safe_corridor_line_max_length)
                                             : cfg_.safe_corridor_line_max_length;
            if (!map_ptr_->isLineFree(back_traj_info.getRobotPos(),
                                      temp_point,
                                      min_dis,
                                      cfg_.seed_line_neighbour)) {
                all_traj_visible = false;
                break;
            }
        }

        if (all_traj_visible) {
            back_traj_info.setEmpty();
            {
                double dur = ref_exp_traj.getTotalDuration();
                Vec3f seed_pt = ref_exp_traj.getPos(dur);
                Line line{back_traj_info.getRobotPos(), seed_pt};
                Polytope temp_poly;
                if (cg_ptr_->GeneratePolytopeFromLine(line, temp_poly)) {
                    back_traj_info.setSFC(temp_poly);
                    {
                        TimeConsuming t_viz("tviz", false);
                        ros_ptr_->vizBackupSfc(temp_poly);
                        time_consuming_[VISUALIZATION] += t_viz.stop();
                    }
                }
            }
            return FINISH;
        }
        Vec3f invisible_p = eval_ps.back().second;
        while (out_t > start_t) {
            out_t -= cfg_.sample_traj_dt;
            Vec3f out_p = ref_exp_traj.getPos(out_t);
            if ((out_p - invisible_p).norm() > cfg_.robot_r) {
                break;
            }
        }

        double seed_point_t = std::max(start_t, out_t);

        // TODO check this logic, comment on Dec. 13
        // if
        // 1) last exp traj has a backup traj
        // 2) last backup WT is larger than this term
        // 3) last exp is collision free
        // if (ref_exp_traj.back_traj_start_TT > 0 &&
        // seed_point_t < ref_exp_traj.back_traj_start_TT) {
        // return NO_NEED;
        // }


        Vec3f seed_point = ref_exp_traj.getPos(seed_point_t);

        Vec3f shifted_robot_p = shifted_sfc_start_pt_.norm()> 999?robot_state_.p:shifted_sfc_start_pt_;
        if (!map_ptr_->getNearestCellNot(GridType::OCCUPIED, shifted_robot_p, shifted_robot_p, 3.0)) {
            ros_ptr_->error(
                    " -- [SUPER] in [PlanFromRest] Local start point is deeply occupied, which should not happened.");
            latest_replan.setRetCode(SUPER_RET_CODE::SUPER_NO_START_POINT);
            return FAILED;
        }

        Line line{shifted_robot_p, seed_point};
        Polytope temp_poly;
        if (!cg_ptr_->GeneratePolytopeFromLine(line, temp_poly)) {
            ros_ptr_->warn(" -- [SUPER] GeneratePolytopeFromLine failed, force return");
            return FAILED;
        }
        Eigen::Vector3d inner;
        Eigen::Matrix3Xd vPoly;
        if (!geometry_utils::findInterior(temp_poly.GetPlanes(), inner)) {
            ros_ptr_->warn(" -- [SUPER] Cannot generate feasible backup sfc, force return");
            vec_Vec3f seed{back_traj_info.getRobotPos(), seed_point};
            return FAILED;
        }

        if (cfg_.use_fov_cut) {
            if (!fov_checker_->cutPolyByFov(robot_state_.p, robot_state_.q, seed_point,
                                            temp_poly)) {
                ros_ptr_->warn(" -- [SUPER] cutPolyByFov failed, force return");
                return FAILED;
            }
        }
        // cut by sensing horizon
        if (cfg_.sensing_horizon > 0 &&
            !fov_checker_->cutPolyBySensingHorizon(robot_state_.p, seed_point, cfg_.sensing_horizon,
                                                   temp_poly)) {
            ros_ptr_->warn(" -- [SUPER] cutPolyBySensingHorizon failed, force return");
            vec_Vec3f seed{back_traj_info.getRobotPos(), seed_point};
            return FAILED;
        }

        back_traj_info.setSFC(temp_poly);

        {
            TimeConsuming t_viz("tviz", false);
            ros_ptr_->vizBackupSfc(temp_poly);
            time_consuming_[VISUALIZATION] += t_viz.stop();
        }

//        Vec3f out_p = temp_point;
//        double t_R = 0.0;
        double eval_t = eval_ps.back().first + cfg_.sample_traj_dt;
        last_pos = eval_ps.back().second;
        while (temp_poly.PointIsInside(eval_ps.back().second) && eval_t < total_dur) {
            Vec3f cur_pos = ref_exp_traj.getPos(eval_t);

            if ((cur_pos - last_pos).norm() < cfg_.resolution * 0.8) {
                eval_t += cfg_.sample_traj_dt;
                continue;
            }
            temp_vel = ref_exp_traj.getVel(out_t);
            double v_norm = temp_vel.norm();
            min_stop_dis.push_back(v_norm * v_norm / 2.0 / cfg_.exp_traj_cfg.max_acc);
            eval_ps.emplace_back(eval_t, cur_pos);
            last_pos = cur_pos;
            eval_t += cfg_.sample_traj_dt;
        }
        eval_ps.pop_back();
        seed_point = eval_ps.back().second;
        seed_point_t = eval_ps.back().first;

        //        bool use_new{true};
        //        if (use_new) {
        double t0 = ros_ptr_->getSimTime() -
                    ref_exp_traj.getStartWallTime() + 0.01;
        double te = seed_point_t;
        //            cout << "t0: " << t0 << endl;
        //            cout << "te: " << te << endl;
        //            cout << "exp_traj_dur: " << ref_exp_traj.optimized_exp_traj.getTotalDuration() << endl;
        double vel_e_n = ref_exp_traj.getVel(te).norm();
        double heu_ts = std::max((t0 + te) / 2, te - vel_e_n / cfg_.back_traj_cfg.max_acc);
        double heu_dur = te - heu_ts;
        Vec3f heu_p = seed_point;
        time_consuming_[BACK_TRAJ_FRONTEND] = t_back_frontend.stop();
        map_read_transaction.unlock();
        TimeConsuming t_back_opt("t_back_opt", false);
        double opt_ts = heu_ts;
        Trajectory temp_pos_traj;
        auto sfc0 = back_traj_info.getSFC();
        bool temp_ret = back_traj_opt_->optimize(ref_exp_traj.posTraj(),
                                                 t0,
                                                 te,
                                                 heu_ts,
                                                 heu_p,
                                                 heu_dur,
                                                 back_traj_info.getSFC(),
                                                 temp_pos_traj,
                                                 opt_ts);
        time_consuming_[BACK_TRAJ_OPT] = t_back_opt.stop();

        {
            double init_ts;
            VecDf init_times;
            vec_Vec3f init_ps;
            back_traj_opt_->getInitValue(init_ts, init_times, init_ps);
            latest_replan.setBackupCondition(init_ts, init_times, init_ps,
                                             t0, te,
                                             back_traj_info.getSFC());
            Trajectory traj;
            double out_ts;
            back_traj_opt_->optimize(ref_exp_traj.posTraj(),
                                     t0,
                                     te,
                                     init_ts,
                                     sfc0,
                                     init_times,
                                     init_ps,
                                     traj,
                                     out_ts
            );

        }

        if (!temp_ret) {
            ros_ptr_->warn(" -- [SUPER] OptimizationBakTrajInPolytopes failed, force return");
            back_traj_info.setEmpty();
            return OPT_FAILED;
        } else {
            Vec4f yaw_init_vec = ref_exp_traj.getYawState(opt_ts).row(0);
            Vec4f yaw_goal{0, 0, 0, 0};
            bool free_end{true};
            if (cfg_.goal_yaw_en) {
                if (!std::isnan(gi_.goal_yaw)) {
                    free_end = false;
                    yaw_goal[0] = gi_.goal_yaw;
                }
            }
            Trajectory temp_yaw_traj;
            if (!yaw_traj_opt_->optimize(yaw_init_vec, yaw_goal, temp_pos_traj,
                                         temp_yaw_traj, 3, false, free_end)) {
                ros_ptr_->error(" -- [SUPER] in [generateBackupTrajectory] YawTrajOpt FAILD.");
                return OPT_FAILED;
            }


            if (opt_ts < t0) {
                ros_ptr_->error(" -- [SUPER] opt_ts {} < t0 {}", opt_ts, t0);
                return OPT_FAILED;
            }
            double new_ts_WT = ref_exp_traj.getStartWallTime() + opt_ts;
            const auto &committed_ts_WT = cmd_traj_info_.getBackupTrajStartTT();
            if (committed_ts_WT < cmd_traj_info_.getTotalDuration() && new_ts_WT < committed_ts_WT) {
                ros_ptr_->error(" -- [SUPER] new_ts_WT {} < committed_ts_WT {}", new_ts_WT, committed_ts_WT);
                return OPT_FAILED;
            }


            {
                TimeConsuming t_viz("tviz", false);
                ros_ptr_->vizBackupTraj(temp_pos_traj);
                time_consuming_[VISUALIZATION] += t_viz.stop();
            }

            back_traj_info.setTrajectory(new_ts_WT, opt_ts, temp_pos_traj, temp_yaw_traj);
            latest_replan.setBackupTraj(temp_pos_traj);
            latest_replan.setBackupYawTraj(temp_yaw_traj);
            return SUCCESS;
        }
        ros_ptr_->warn(" -- [SUPER] Cannot find backup traj start point.");
        return FAILED;
    }

    int SuperPlanner::getNearestFurtherGoalPoint(const vec_E<Vec3f> &goals, const Vec3f &start_pt) {
        if (goals.size() == 1) {
            return 0;
        }
        Vec3f a = start_pt, b;
        int min_id = 0;
        double min_dis = 1e10;
        for (long unsigned int i = 0; i < goals.size() - 1; i++) {
            b = goals[i];
            double dis = geometry_utils::pointLineSegmentDistance(start_pt, a, b);
            if (dis < min_dis) {
                min_dis = dis;
                min_id = i;
            }
            a = b;
        }
        return min_id;
    }

    bool
    SuperPlanner::PathSearch(const Vec3f &start_pt, const Vec3f &goal,
                             const double &searching_horizon,
                             vec_Vec3f &path,
                             const bool planning_from_rest) {
        using namespace path_search;
        if (searching_horizon <= 0.0) {
            ros_ptr_->error(" -- [SUPER] Goal waypoints empty or searching horizon negative, force return.");
            return false;
        }

        // 1) check and shift pts
        // 		For start point, must be collision free
        rog_map::GridType start_type;
        start_type = map_ptr_->getGridType(start_pt);

        /// If the start_pt is obstacle in prob map, just shift it to the nearest free point.
        if (start_type == rog_map::GridType::OCCUPIED ||
            start_type == rog_map::GridType::OUT_OF_MAP) {
            ros_ptr_->warn(
                    " -- [SUPER] The start point in obstacle, this should not happen since the start point should be shift before pathsearch.");
            return false;
        }
        vec_E<Vec3f> start_point_escape_path;

        int flag_es = ON_PROB_MAP | (cfg_.frontend_in_known_free ? UNKNOWN_AS_OCCUPIED : UNKNOWN_AS_FREE);
        vec_Vec3f out_path;
        RET_CODE ret_es = astar_ptr_->escapePathSearch(start_pt, flag_es, out_path);
        if (ret_es != NO_NEED) {
            if (ret_es != REACH_HORIZON && ret_es != REACH_GOAL) {
                ros_ptr_->error(
                        " -- [SUPER] Escape path search failed with [{}], force return.",
                        RET_CODE_STR[ret_es].c_str());
                return false;
            } else {
                start_point_escape_path = out_path;
            }
        }

        Vec3f shifted_start_pt = start_pt;

        if (!start_point_escape_path.empty()) {
            shifted_start_pt = start_point_escape_path.back();
        }

        Vec3f temp_goal_point, temp_start_point;
        temp_start_point = shifted_start_pt;
        double temp_plannning_horizon = searching_horizon;
        //            int start_id = getNearestFurtherGoalPoint(goal_waypoints, start_pt);

        const bool guard_clearance_frontend = cfg_.trajectory_guard_en &&
                cfg_.trajectory_guard_additional_clearance_m > 0.0;
        int flag = ON_INF_MAP |
                   (cfg_.frontend_in_known_free ? UNKNOWN_AS_OCCUPIED
                                                : UNKNOWN_AS_FREE) |
                   (guard_clearance_frontend ? USE_INF_NEIGHBOR
                                             : DONT_USE_INF_NEIGHBOR);

        if (cfg_.guard_topology_reroute_en &&
            !guard_topology_avoidance_centers_.empty()) {
            ros_ptr_->warn(
                    " -- [TRAJ_GUARD_REROUTE_SEARCH] zones={} start=[{:.3f},{:.3f},{:.3f}]",
                    guard_topology_avoidance_centers_.size(),
                    temp_start_point.x(), temp_start_point.y(),
                    temp_start_point.z());
        }
        RET_CODE ret_code = astar_ptr_->pointToPointPathSearch(
                temp_start_point, goal, flag, temp_plannning_horizon, path,
                guard_topology_avoidance_centers_,
                guard_topology_avoidance_radii_);

        // Explicit one-shot regression hook for the otherwise stochastic
        // base-NO_PATH tail. It is inert unless the test environment opts in.
        // Mark the vertical budget consumed so the bounded horizontal
        // fallback added below is the branch exercised by the smoke test.
        if (planning_from_rest &&
            guard_test_base_no_path_failures_remaining_ < 0) {
            const char *test_force_base_no_path = std::getenv(
                    "SUPER_TEST_FORCE_BASE_NO_PATH_ESCAPE_ONCE");
            if (test_force_base_no_path != nullptr &&
                std::string(test_force_base_no_path) == "1") {
                guard_test_base_no_path_failures_remaining_ =
                        cfg_.guard_topology_reroute_no_path_reset_attempts;
                guard_topology_base_no_path_recoveries_ =
                        cfg_.guard_topology_base_no_path_vertical_attempts;
                ros_ptr_->warn(
                        " -- [TEST_FAULT_BASE_NO_PATH_ARM] failures={} "
                        "action=exercise_certified_local_escape",
                        guard_test_base_no_path_failures_remaining_);
            } else {
                guard_test_base_no_path_failures_remaining_ = 0;
            }
        }
        if (planning_from_rest &&
            guard_topology_avoidance_centers_.empty() &&
            guard_test_base_no_path_failures_remaining_ > 0) {
            --guard_test_base_no_path_failures_remaining_;
            ret_code = NO_PATH;
            path.clear();
            ros_ptr_->warn(
                    " -- [TEST_FAULT_BASE_NO_PATH] remaining={} "
                    "action=return_no_path",
                    guard_test_base_no_path_failures_remaining_);
        }

        // A bounded A* TIME_OUT is the same recovery signal as NO_PATH while
        // planning from a certified stop: neither result produced a candidate
        // trajectory, and retrying the identical topology cannot make
        // progress.  Moving-state timeouts are deliberately excluded because
        // the already committed trajectory remains in charge there.
        const bool stopped_guard_astar_failure =
                cfg_.guard_topology_reroute_en && planning_from_rest &&
                (ret_code == NO_PATH || ret_code == TIME_OUT);
        const bool guarded_astar_failure_with_zones =
                cfg_.guard_topology_reroute_en &&
                (ret_code == NO_PATH ||
                 (planning_from_rest && ret_code == TIME_OUT));
        const char *astar_failure_reason =
                ret_code == TIME_OUT ? "astar_timeout" : "astar_no_path";

        if (stopped_guard_astar_failure &&
            guard_topology_avoidance_centers_.empty()) {
            // The old recovery counter only ran after a rejected candidate
            // had already created a virtual blocker. A stopped base search
            // with no path or a bounded timeout therefore retried the
            // identical topology forever.
            // After the same bounded threshold, request one guarded vertical
            // state change. A negative failure count marks exhausted recovery
            // for this goal and prevents repeated warning/action loops.
            if (guard_topology_no_path_failures_ >= 0) {
                ++guard_topology_no_path_failures_;
            }
            if (guard_topology_no_path_failures_ >=
                cfg_.guard_topology_reroute_no_path_reset_attempts) {
                guard_topology_corridor_failures_ = 0;
                guard_topology_post_corridor_failures_ = 0;
                const bool can_lift =
                        cfg_.guard_topology_vertical_recovery_en &&
                        guard_topology_base_no_path_recoveries_ <
                                cfg_.guard_topology_base_no_path_vertical_attempts;
                Vec3f base_escape_direction = goal - temp_start_point;
                base_escape_direction.z() = 0.0;
                const double base_escape_direction_norm =
                        base_escape_direction.norm();
                const bool can_escape =
                        cfg_.guard_topology_local_escape_en &&
                        base_escape_direction.array().isFinite().all() &&
                        std::isfinite(base_escape_direction_norm) &&
                        base_escape_direction_norm >= cfg_.resolution &&
                        guard_topology_local_escape_recoveries_ <
                                cfg_.guard_topology_local_escape_attempts;
                if (can_lift) {
                    ++guard_topology_base_no_path_recoveries_;
                    guard_topology_no_path_failures_ = 0;
                    ++guard_topology_epoch_;
                    guard_vertical_recovery_pending_.store(
                            true, std::memory_order_release);
                    ros_ptr_->warn(
                            " -- [TRAJ_GUARD_BASE_NO_PATH_RECOVERY] epoch={} "
                            "attempt={}/{} reason={} "
                            "start=[{:.3f},{:.3f},{:.3f}] "
                            "goal=[{:.3f},{:.3f},{:.3f}] "
                            "action=guarded_vertical_lift",
                            guard_topology_epoch_,
                            guard_topology_base_no_path_recoveries_,
                            cfg_.guard_topology_base_no_path_vertical_attempts,
                            astar_failure_reason,
                            temp_start_point.x(), temp_start_point.y(),
                            temp_start_point.z(), goal.x(), goal.y(), goal.z());
                } else if (can_escape) {
                    // A base search can remain disconnected after its one
                    // guarded vertical lift is rejected.  Previously that
                    // state went straight to permanent certified hold even
                    // when the separately-bounded horizontal escape budget
                    // was still available.  Reuse the existing stop-only,
                    // eight-direction local escape certificate to move to a
                    // distinct start cell, then rerun A*.  The waypoint
                    // direction is only an ordering hint; every trial still
                    // passes the unchanged trajectory and viability guards.
                    guard_local_escape_direction_ =
                            base_escape_direction /
                            base_escape_direction_norm;
                    ++guard_topology_local_escape_recoveries_;
                    guard_topology_no_path_failures_ = 0;
                    ++guard_topology_epoch_;
                    guard_local_escape_pending_.store(
                            true, std::memory_order_release);
                    ros_ptr_->warn(
                            " -- [TRAJ_GUARD_BASE_NO_PATH_LOCAL_ESCAPE] "
                            "epoch={} attempt={}/{} reason={} "
                            "start=[{:.3f},{:.3f},{:.3f}] "
                            "direction=[{:.3f},{:.3f},{:.3f}] "
                            "action=certified_escape_then_reroute",
                            guard_topology_epoch_,
                            guard_topology_local_escape_recoveries_,
                            cfg_.guard_topology_local_escape_attempts,
                            astar_failure_reason,
                            temp_start_point.x(), temp_start_point.y(),
                            temp_start_point.z(),
                            guard_local_escape_direction_.x(),
                            guard_local_escape_direction_.y(),
                            guard_local_escape_direction_.z());
                } else {
                    guard_topology_no_path_failures_ = -1;
                    ros_ptr_->warn(
                            " -- [TRAJ_GUARD_BASE_NO_PATH_EXHAUSTED] "
                            "attempts={}/{} reason={} "
                            "start=[{:.3f},{:.3f},{:.3f}] "
                            "action=certified_hold",
                            guard_topology_base_no_path_recoveries_,
                            cfg_.guard_topology_base_no_path_vertical_attempts,
                            astar_failure_reason,
                            temp_start_point.x(), temp_start_point.y(),
                            temp_start_point.z());
                }
            }
        } else if (guarded_astar_failure_with_zones &&
            !guard_topology_avoidance_centers_.empty()) {
            ++guard_topology_no_path_failures_;
            if (guard_topology_no_path_failures_ >=
                cfg_.guard_topology_reroute_no_path_reset_attempts) {
                const std::size_t cleared_zones =
                        guard_topology_avoidance_centers_.size();
                const double horizontal_collision_distance =
                        (guard_topology_stall_collision_.head<2>() -
                         temp_start_point.head<2>()).norm();
                const double collision_z =
                        guard_topology_stall_collision_.z();
                const bool start_adjacent_lower_rejection =
                        guard_topology_stall_rejects_ > 0 &&
                        guard_topology_stall_collision_.array()
                                .isFinite().all() &&
                        std::isfinite(horizontal_collision_distance) &&
                        horizontal_collision_distance <=
                                cfg_.guard_topology_vertical_recovery_trigger_distance_m &&
                        guard_topology_stall_collision_.z() <=
                                temp_start_point.z() + cfg_.resolution;
                Vec3f local_escape_direction =
                        temp_start_point - guard_topology_stall_collision_;
                local_escape_direction.z() = 0.0;
                const bool local_escape_direction_valid =
                        local_escape_direction.array().isFinite().all() &&
                        local_escape_direction.norm() >= cfg_.resolution;
                const bool arm_local_escape =
                        cfg_.guard_topology_local_escape_en &&
                        start_adjacent_lower_rejection &&
                        local_escape_direction_valid &&
                        guard_topology_local_escape_recoveries_ <
                                cfg_.guard_topology_local_escape_attempts;
                const bool arm_vertical_recovery =
                        cfg_.guard_topology_vertical_recovery_en &&
                        start_adjacent_lower_rejection &&
                        guard_topology_saturation_recoveries_ <
                                cfg_.guard_topology_saturation_vertical_attempts;
                guard_topology_avoidance_centers_.clear();
                guard_topology_avoidance_radii_.clear();
                guard_topology_branch_directions_.clear();
                guard_topology_branch_depths_.clear();
                guard_topology_stall_generation_ = 0;
                guard_topology_stall_collision_.setZero();
                guard_topology_stall_rejects_ = 0;
                guard_topology_no_path_failures_ = 0;
                guard_topology_corridor_failures_ = 0;
                guard_topology_post_corridor_failures_ = 0;
                ++guard_topology_epoch_;
                if (arm_local_escape) {
                    guard_local_escape_direction_ =
                            local_escape_direction.normalized();
                    ++guard_topology_local_escape_recoveries_;
                    guard_local_escape_pending_.store(
                            true, std::memory_order_release);
                    ros_ptr_->warn(
                            " -- [TRAJ_GUARD_LOCAL_ESCAPE_ARM] "
                            "cleared_zones={} epoch={} attempt={}/{} "
                            "reason={} horizontal_distance={:.3f} "
                            "direction=[{:.3f},{:.3f},{:.3f}] "
                            "action=escape_then_reroute",
                            cleared_zones, guard_topology_epoch_,
                            guard_topology_local_escape_recoveries_,
                            cfg_.guard_topology_local_escape_attempts,
                            astar_failure_reason,
                            horizontal_collision_distance,
                            guard_local_escape_direction_.x(),
                            guard_local_escape_direction_.y(),
                            guard_local_escape_direction_.z());
                } else if (arm_vertical_recovery) {
                    ++guard_topology_saturation_recoveries_;
                    guard_vertical_recovery_pending_.store(
                            true, std::memory_order_release);
                    ros_ptr_->warn(
                            " -- [TRAJ_GUARD_VERTICAL_RECOVERY_ARM] "
                            "cleared_zones={} epoch={} attempt={}/{} reason={} "
                            "horizontal_distance={:.3f} start_z={:.3f} "
                            "collision_z={:.3f} action=lift_then_reroute",
                            cleared_zones, guard_topology_epoch_,
                            guard_topology_saturation_recoveries_,
                            cfg_.guard_topology_saturation_vertical_attempts,
                            astar_failure_reason,
                            horizontal_collision_distance,
                            temp_start_point.z(), collision_z);
                } else {
                    guard_corridor_retry_pending_.store(
                            true, std::memory_order_release);
                    ros_ptr_->warn(
                            " -- [TRAJ_GUARD_REROUTE_EPOCH_RESET] epoch={} "
                            "cleared_zones={} reason={} "
                            "action=certified_stop_reseed",
                            guard_topology_epoch_, cleared_zones,
                            astar_failure_reason);
                }
            }
        } else if (ret_code == REACH_HORIZON || ret_code == REACH_GOAL) {
            guard_topology_no_path_failures_ = 0;
        }

        if(ret_code == INIT_ERROR){
            gi_.goal_valid = false;
            return false;
        }
        //add may23, if failed on inf map, use prob map try again

        if (ret_code == NO_PATH && !cfg_.trajectory_guard_en) {
            flag = ON_PROB_MAP | (cfg_.frontend_in_known_free ? UNKNOWN_AS_OCCUPIED : UNKNOWN_AS_FREE) |
                   USE_INF_NEIGHBOR;
            fmt::print(fg(fmt::color::indian_red) | fmt::emphasis::bold,
                       " -- [Astar] Path search failed on inf map, try again on prob map.\n");
            ret_code = astar_ptr_->pointToPointPathSearch(
                    temp_start_point, goal, flag, temp_plannning_horizon, path,
                    guard_topology_avoidance_centers_,
                    guard_topology_avoidance_radii_);
            if (ret_code == SUCCESS || ret_code == REACH_HORIZON || ret_code == REACH_GOAL) {
                fmt::print(fg(fmt::color::lime_green) | fmt::emphasis::bold,
                           " -- [Astar] Path search on prob map success.\n");
            } else {
                fmt::print(fg(fmt::color::indian_red) | fmt::emphasis::bold,
                           " -- [Astar] Path search failed on prob map still failed.\n");
            }
        } else if (ret_code == NO_PATH && cfg_.trajectory_guard_en) {
            fmt::print(fg(fmt::color::indian_red) | fmt::emphasis::bold,
                       " -- [Astar] Guarded path search failed on inflated map; "
                       "unsafe probability-map fallback is disabled.\n");
        }
        if (ret_code != REACH_HORIZON && ret_code != REACH_GOAL) {
            ros_ptr_->error(
                    " -- [SUPER] Path search failed with [{}], force return.\n", RET_CODE_STR[ret_code].c_str());
            return false;
        }
        if (!start_point_escape_path.empty()) {
            path.insert(path.begin(), start_point_escape_path.begin(),
                        start_point_escape_path.end());
        }

        if (path.empty()) {
            ros_ptr_->warn(
                    " -- [SUPER] Path search failed with empty segments, force return.");
            return false;
        }
        path.insert(path.begin(), start_pt);
        if (ret_code == REACH_GOAL) {
            path.push_back(goal);
        }
        return true;
    }


    void SuperPlanner::getRobotState(rog_map::RobotState &out) {
        robot_state_ = map_ptr_->getRobotState();
        out = robot_state_;
    }
}
