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


#ifdef USE_ROS2

#ifndef SRC_FSM_ROS2_HPP
#define SRC_FSM_ROS2_HPP


#include "fsm/fsm.h"

#include <rclcpp/rclcpp.hpp>
#include <ros_interface/ros2/ros2_interface.hpp>
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "nav_msgs/msg/path.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "mars_quadrotor_msgs/msg/position_command.hpp"
#include "mars_quadrotor_msgs/msg/polynomial_trajectory.hpp"
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl_conversions/pcl_conversions.h>
#include <utils/optimization/polynomial_interpolation.h>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <limits>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_set>


namespace fsm {
    class FsmRos2 : public Fsm {

        rclcpp::Node::SharedPtr nh_;
        rclcpp::Publisher<mars_quadrotor_msgs::msg::PositionCommand>::SharedPtr cmd_pub_;
        rclcpp::Publisher<mars_quadrotor_msgs::msg::PolynomialTrajectory>::SharedPtr mpc_cmd_pub_;
        rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_pub_;
        rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr goal_sub_;
        rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr
                guard_cloud_sub_;
        bool ciri_shadow_uses_map_cloud_observer_{false};

        rclcpp::TimerBase::SharedPtr execution_timer_, replan_timer_, cmd_timer_;
        rclcpp::CallbackGroup::SharedPtr exec_cbk_group_, map_cbk_group_, replan_cbk_group_, cmd_cbk_group_, goal_cbk_group_;
        rclcpp::CallbackGroup::SharedPtr guard_cloud_cbk_group_;

        mars_quadrotor_msgs::msg::PositionCommand pid_cmd_;
        rog_map::ROGMapROS::Ptr map_ptr_;
        mars_quadrotor_msgs::msg::PositionCommand latest_cmd;
        nav_msgs::msg::Path path;

        vector<mars_quadrotor_msgs::msg::PositionCommand> cmd_logs_;

        mutable std::mutex safety_mutex_;
        TrajectorySafetyResult safety_certificate_{};
        bool safety_certificate_valid_{false};
        std::atomic_bool safety_brake_active_{false};
        std::atomic_bool safety_brake_finished_{false};
        std::atomic_bool safety_revalidation_requested_{false};
        std::uint64_t shadow_last_enqueued_map_version_{0};
        Trajectory brake_pos_traj_{};
        Trajectory brake_yaw_traj_{};
        double brake_start_wt_{0.0};
        double brake_duration_s_{0.0};
        double brake_yaw_{0.0};
        std::string brake_reason_{};
        Vec3f brake_stop_position_{Vec3f::Zero()};
        Vec3f brake_stability_anchor_{Vec3f::Zero()};
        double brake_stability_start_wt_{0.0};
        bool brake_stability_started_{false};
        double brake_recovery_last_attempt_wt_{-
                std::numeric_limits<double>::infinity()};

        enum class RawCloudSafetyStatus {
            DISABLED,
            STALE,
            EMPTY_TRAJECTORY,
            SAFE,
            OCCUPIED
        };

        struct RawCloudSnapshot {
            std::shared_ptr<pcl::KdTreeFLANN<rog_map::PointType>> tree;
            rog_map::MapHealthClock::time_point receive_time{};
            std::uint64_t sequence{0};
        };

        // 2026-08-19: paper-faithful (theorem 1) shadow check only -- see
        // docs/viability_guard_ciri_avoidance_2026-08-15.md 8.10. Reports
        // what an accumulated-raw-cloud CIRI known-free check would have
        // concluded, logged alongside the live (grid-based UNOBSERVED)
        // brake decision, without being able to affect it.
        enum class CiriShadowStatus {
            DISABLED,
            STALE,
            INSUFFICIENT_DATA,
            SAFE,
            UNSAFE
        };

        static const char *ciriShadowStatusName(const CiriShadowStatus status) {
            switch (status) {
                case CiriShadowStatus::DISABLED: return "DISABLED";
                case CiriShadowStatus::STALE: return "STALE";
                case CiriShadowStatus::INSUFFICIENT_DATA:
                    return "INSUFFICIENT_DATA";
                case CiriShadowStatus::SAFE: return "SAFE";
                case CiriShadowStatus::UNSAFE: return "UNSAFE";
            }
            return "UNKNOWN";
        }

        struct RawCloudWindowBatch {
            // Keep the subscription callback O(1) for CIRI-shadow-only
            // profiles. PointCloud2 -> PCL conversion is part of the heavy
            // accumulation work and therefore belongs to the worker too.
            // When the live raw-cloud guard is enabled, `converted_cloud`
            // reuses the conversion it already needs for its KD-tree.
            sensor_msgs::msg::PointCloud2::SharedPtr cloud_msg;
            std::shared_ptr<pcl::PointCloud<rog_map::PointType>>
                    converted_cloud;
            rog_map::MapHealthClock::time_point receive_time{};
        };

        mutable std::mutex raw_cloud_window_mutex_;
        std::deque<RawCloudWindowBatch> raw_cloud_window_;
        std::uint64_t raw_cloud_window_messages_total_{0};

        // Pulls the current window (pruned to accumulation_window_s) plus
        // health info the caller must check before trusting an empty
        // result as "open space" (theorem 1's own "sufficiently dense"
        // precondition -- see corridor_generator.cpp's
        // GeneratePolytopeFromLineAndCloud).
        void getAccumulatedCloudForShadow(
                double accumulation_window_s, vec_E<Vec3f> &out_cloud,
                double &time_since_last_msg_s, std::size_t &batch_count) const {
            out_cloud.clear();
            std::deque<RawCloudWindowBatch> window_copy;
            {
                std::lock_guard<std::mutex> lock(raw_cloud_window_mutex_);
                window_copy = raw_cloud_window_;
            }
            const auto now = rog_map::MapHealthClock::now();
            time_since_last_msg_s = window_copy.empty()
                    ? std::numeric_limits<double>::infinity()
                    : std::chrono::duration<double>(
                            now - window_copy.back().receive_time).count();
            batch_count = 0;
            // 2026-08-19: voxel-downsample while accumulating instead of
            // keeping every raw point. Measured need directly: an
            // undownsampled 1.5s window held 30,000-80,000 points (the
            // map-derived path's boxSearch returns a resolution-gridded
            // handful of hundreds by comparison), and CIRI decomposition
            // cost on that spiked to 15-40ms on a shared executor thread --
            // shadow-only means it can't affect the safety decision, but it
            // was still stealing real time from replanning and measurably
            // hurt completion in a seed1-10 sweep. A hash-set keyed by
            // voxel index keeps at most one point per
            // trajectory_guard_raw_cloud_ciri_voxel_m cell.
            const double voxel = std::max(0.01,
                    cfg_.trajectory_guard_raw_cloud_ciri_voxel_m);
            std::unordered_set<std::int64_t> seen_voxels;
            const auto voxel_key = [voxel](const Vec3f &p) -> std::int64_t {
                auto q = [voxel](double v) -> std::int64_t {
                    return static_cast<std::int64_t>(
                            std::floor(v / voxel));
                };
                // 21 bits/axis (+/-1,048,575 voxels, i.e. +/-10km at
                // voxel=0.01m) is ample for a local accumulation window and
                // keeps the combined key inside 63 bits.
                constexpr std::int64_t kBits = 21;
                constexpr std::int64_t kMask = (std::int64_t(1) << kBits) - 1;
                constexpr std::int64_t kOffset = std::int64_t(1) << (kBits - 1);
                const std::int64_t ix = (q(p.x()) + kOffset) & kMask;
                const std::int64_t iy = (q(p.y()) + kOffset) & kMask;
                const std::int64_t iz = (q(p.z()) + kOffset) & kMask;
                return (ix << (2 * kBits)) | (iy << kBits) | iz;
            };
            for (const auto &batch : window_copy) {
                const double age_s = std::chrono::duration<double>(
                        now - batch.receive_time).count();
                if (age_s < 0.0 || age_s > accumulation_window_s ||
                    (!batch.cloud_msg && !batch.converted_cloud)) {
                    continue;
                }
                ++batch_count;
                pcl::PointCloud<rog_map::PointType> converted;
                const pcl::PointCloud<rog_map::PointType> *cloud =
                        batch.converted_cloud.get();
                if (!cloud) {
                    pcl::fromROSMsg(*batch.cloud_msg, converted);
                    cloud = &converted;
                }
                for (const auto &pt : *cloud) {
                    const Vec3f p(pt.x, pt.y, pt.z);
                    if (seen_voxels.insert(voxel_key(p)).second) {
                        out_cloud.push_back(p);
                    }
                }
            }
        }

        // Shadow-only (see the CiriShadowStatus/config comments above):
        // reports what the paper's actual theorem-1 mechanism would have
        // concluded about this brake candidate. Never read by any accept/
        // reject decision -- activateEmergencyBrake only logs the result.
        // 2026-08-19: used only by the dedicated latest-only worker. The
        // 100Hz FSM callback queues one representative candidate and never
        // fetches, voxelizes or runs CIRI synchronously. This supersedes the
        // intermediate fix that merely hoisted one fetch outside the 30-way
        // brake-duration retry loop: that removed duplicate work but still
        // spent 0.8-15ms on a MutuallyExclusive 10ms timer callback.
        struct CiriShadowCloudSnapshot {
            bool enabled{false};
            bool sufficient{false};
            vec_E<Vec3f> cloud;
            double latest_cloud_age_s{
                    std::numeric_limits<double>::infinity()};
            std::size_t batch_count{0};
            double accumulation_ms{0.0};
        };

        CiriShadowCloudSnapshot fetchCiriShadowCloudSnapshot() {
            CiriShadowCloudSnapshot out;
            if (!cfg_.trajectory_guard_raw_cloud_ciri_shadow_en) {
                return out;
            }
            out.enabled = true;
            const auto t0 = rog_map::MapHealthClock::now();
            getAccumulatedCloudForShadow(
                    cfg_.trajectory_guard_raw_cloud_accum_window_s, out.cloud,
                    out.latest_cloud_age_s, out.batch_count);
            out.accumulation_ms = std::chrono::duration<double, std::milli>(
                    rog_map::MapHealthClock::now() - t0).count();
            // Accumulator health gate: theorem 1's known-free guarantee is
            // conditioned on a "sufficiently dense" input depth image. A
            // stale or sparse accumulator cannot honestly claim that, so
            // this reports insufficient rather than letting
            // GeneratePolytopeFromLineAndCloud's empty-box-is-open
            // convention silently stand in for "we don't actually know."
            out.sufficient = std::isfinite(out.latest_cloud_age_s) &&
                    out.latest_cloud_age_s <=
                            cfg_.trajectory_guard_raw_cloud_max_age_s &&
                    static_cast<int>(out.cloud.size()) >=
                            cfg_.trajectory_guard_raw_cloud_ciri_min_points;
            return out;
        }

        CiriShadowStatus checkBrakeCandidateAgainstCiriShadow(
                const CiriShadowCloudSnapshot &snapshot,
                const Vec3f &current_pos, const Trajectory &candidate,
                Vec3f &violation_pos, double &ciri_ms) {
            ciri_ms = 0.0;
            if (!snapshot.enabled || candidate.empty()) {
                return CiriShadowStatus::DISABLED;
            }
            if (!snapshot.sufficient) {
                return CiriShadowStatus::INSUFFICIENT_DATA;
            }
            const Vec3f seed_far_pt = candidate.getPos(
                    candidate.getTotalDuration());
            const auto ciri_t0 = rog_map::MapHealthClock::now();
            const bool known_free = planner_ptr_->checkKnownFreeViaCloud(
                    current_pos, seed_far_pt, snapshot.cloud, candidate, 0.0,
                    violation_pos);
            ciri_ms = std::chrono::duration<double, std::milli>(
                    rog_map::MapHealthClock::now() - ciri_t0).count();
            return known_free ? CiriShadowStatus::SAFE
                               : CiriShadowStatus::UNSAFE;
        }

        struct CiriShadowJob {
            std::uint64_t request_id{0};
            std::string trigger;
            Vec3f current_pos{Vec3f::Zero()};
            Trajectory candidate;
            rog_map::MapHealthClock::time_point enqueue_time{};
        };

        struct CiriShadowResult {
            std::uint64_t request_id{0};
            CiriShadowStatus status{CiriShadowStatus::DISABLED};
            Vec3f violation_pos{Vec3f::Zero()};
            rog_map::MapHealthClock::time_point completion_time{};
            double total_ms{0.0};
        };

        struct CiriShadowReadout {
            CiriShadowStatus status{CiriShadowStatus::DISABLED};
            std::uint64_t request_id{0};
            double age_s{std::numeric_limits<double>::infinity()};
        };

        mutable std::mutex ciri_shadow_worker_mutex_;
        std::condition_variable ciri_shadow_worker_cv_;
        std::optional<CiriShadowJob> pending_ciri_shadow_job_;
        std::optional<CiriShadowResult> latest_ciri_shadow_result_;
        bool stop_ciri_shadow_worker_{false};
        std::thread ciri_shadow_worker_;
        std::uint64_t next_ciri_shadow_request_id_{1};

        std::uint64_t enqueueCiriShadowCheck(
                const std::string &trigger, const Vec3f &current_pos,
                Trajectory candidate) {
            if (!cfg_.trajectory_guard_raw_cloud_ciri_shadow_en ||
                candidate.empty()) {
                return 0;
            }
            std::optional<std::uint64_t> replaced_request;
            std::uint64_t request_id;
            {
                std::lock_guard<std::mutex> lock(ciri_shadow_worker_mutex_);
                request_id = next_ciri_shadow_request_id_++;
                if (pending_ciri_shadow_job_) {
                    replaced_request =
                            pending_ciri_shadow_job_->request_id;
                }
                pending_ciri_shadow_job_ = CiriShadowJob{
                        request_id, trigger, current_pos,
                        std::move(candidate),
                        rog_map::MapHealthClock::now()};
            }
            if (replaced_request) {
                ros_ptr_->info(
                        " -- [TRAJ_GUARD_RAW_CIRI_ASYNC_SKIPPED] request={} "
                        "reason=LATEST_ONLY replacement={}",
                        *replaced_request, request_id);
            }
            ciri_shadow_worker_cv_.notify_one();
            return request_id;
        }

        CiriShadowReadout latestCiriShadowReadout() const {
            CiriShadowReadout out;
            if (!cfg_.trajectory_guard_raw_cloud_ciri_shadow_en) {
                return out;
            }
            std::lock_guard<std::mutex> lock(ciri_shadow_worker_mutex_);
            if (!latest_ciri_shadow_result_) {
                out.status = CiriShadowStatus::STALE;
                return out;
            }
            out.request_id = latest_ciri_shadow_result_->request_id;
            out.age_s = std::chrono::duration<double>(
                    rog_map::MapHealthClock::now() -
                    latest_ciri_shadow_result_->completion_time).count();
            const double max_result_age_s = std::max(
                    0.05, cfg_.trajectory_guard_raw_cloud_max_age_s);
            out.status = std::isfinite(out.age_s) && out.age_s >= 0.0 &&
                         out.age_s <= max_result_age_s
                    ? latest_ciri_shadow_result_->status
                    : CiriShadowStatus::STALE;
            return out;
        }

        void ciriShadowWorkerLoop() {
            while (true) {
                CiriShadowJob job;
                {
                    std::unique_lock<std::mutex> lock(
                            ciri_shadow_worker_mutex_);
                    ciri_shadow_worker_cv_.wait(lock, [this] {
                        return stop_ciri_shadow_worker_ ||
                               pending_ciri_shadow_job_.has_value();
                    });
                    if (stop_ciri_shadow_worker_) {
                        return;
                    }
                    job = std::move(*pending_ciri_shadow_job_);
                    pending_ciri_shadow_job_.reset();
                }

                const auto work_start = rog_map::MapHealthClock::now();
                const auto snapshot = fetchCiriShadowCloudSnapshot();
                Vec3f violation_pos = Vec3f::Zero();
                double ciri_ms = 0.0;
                const auto status = checkBrakeCandidateAgainstCiriShadow(
                        snapshot, job.current_pos, job.candidate,
                        violation_pos, ciri_ms);
                const auto completion_time =
                        rog_map::MapHealthClock::now();
                const double total_ms =
                        std::chrono::duration<double, std::milli>(
                                completion_time - work_start).count();
                const double queue_ms =
                        std::chrono::duration<double, std::milli>(
                                work_start - job.enqueue_time).count();
                {
                    std::lock_guard<std::mutex> lock(
                            ciri_shadow_worker_mutex_);
                    latest_ciri_shadow_result_ = CiriShadowResult{
                            job.request_id, status, violation_pos,
                            completion_time, total_ms};
                }
                ros_ptr_->warn(
                        " -- [TRAJ_GUARD_RAW_CIRI_ASYNC_RESULT] request={} "
                        "trigger={} status={} cloud_pts={} batches={} "
                        "cloud_age={:.3f}s queue_ms={:.3f} accum_ms={:.3f} "
                        "ciri_ms={:.3f} total_ms={:.3f} "
                        "p=[{:.3f},{:.3f},{:.3f}]",
                        job.request_id, job.trigger,
                        ciriShadowStatusName(status), snapshot.cloud.size(),
                        snapshot.batch_count, snapshot.latest_cloud_age_s,
                        queue_ms, snapshot.accumulation_ms, ciri_ms, total_ms,
                        violation_pos.x(), violation_pos.y(),
                        violation_pos.z());
            }
        }

        void stopCiriShadowWorker() {
            {
                std::lock_guard<std::mutex> lock(ciri_shadow_worker_mutex_);
                stop_ciri_shadow_worker_ = true;
                pending_ciri_shadow_job_.reset();
            }
            ciri_shadow_worker_cv_.notify_all();
            if (ciri_shadow_worker_.joinable()) {
                ciri_shadow_worker_.join();
            }
        }

        mutable std::mutex raw_cloud_mutex_;
        RawCloudSnapshot raw_cloud_snapshot_{};
        // 2026-08-19: isolated diagnostic only (see mainFsmTimerCallback).
        // Confirms whether guard_cloud_sub_ is actually receiving messages
        // before any accumulation/CIRI logic is built on top of it -- 8.4's
        // third attempt found this subscription's sequence stuck at 0 for
        // an entire mission and never diagnosed why.
        rog_map::MapHealthClock::time_point raw_cloud_debug_last_log_{};
        std::uint64_t raw_cache_cloud_sequence_{0};
        std::uint64_t raw_cache_trajectory_generation_{0};
        RawCloudSafetyStatus raw_cache_status_{RawCloudSafetyStatus::STALE};
        Vec3f raw_cache_collision_position_{Vec3f::Zero()};

        mutable std::mutex latest_cmd_mutex_;
        mars_quadrotor_msgs::msg::PositionCommand last_published_cmd_{};
        bool last_published_cmd_valid_{false};
        double last_published_cmd_wt_{-
                std::numeric_limits<double>::infinity()};
        // Serializes brake selection/certification across the main and replan
        // callback groups and supplies a position-derived motion estimate.
        // ROG-Map's legacy RobotState intentionally carries pose only; using
        // finite differences here avoids treating its unset velocity as a
        // real stopped certificate.
        mutable std::mutex brake_activation_mutex_;
        Vec3f recovery_motion_last_position_{Vec3f::Zero()};
        double recovery_motion_last_wt_{-
                std::numeric_limits<double>::infinity()};
        Vec3f recovery_motion_velocity_{Vec3f::Zero()};
        bool recovery_motion_velocity_valid_{false};

        static const char *rawCloudSafetyStatusName(
                const RawCloudSafetyStatus status) {
            switch (status) {
                case RawCloudSafetyStatus::DISABLED: return "DISABLED";
                case RawCloudSafetyStatus::STALE: return "STALE";
                case RawCloudSafetyStatus::EMPTY_TRAJECTORY:
                    return "EMPTY_TRAJECTORY";
                case RawCloudSafetyStatus::SAFE: return "SAFE";
                case RawCloudSafetyStatus::OCCUPIED: return "OCCUPIED";
            }
            return "UNKNOWN";
        }

        // Upper bound the window deque prunes to, independent of whatever
        // window duration a given read requests -- keeps enough history for
        // any reasonable accumulation_window_s without growing unbounded.
        static constexpr double kRawCloudWindowMaxRetainS = 3.0;

        void cacheGuardCloud(
                const sensor_msgs::msg::PointCloud2::SharedPtr &cloud_msg,
                const rog_map::MapHealthClock::time_point receive_time) {
            if (!cloud_msg || cloud_msg->data.empty() ||
                !cloud_msg->is_dense) {
                return;
            }

            std::shared_ptr<pcl::PointCloud<rog_map::PointType>> cloud;
            std::shared_ptr<pcl::KdTreeFLANN<rog_map::PointType>> tree;
            if (cfg_.trajectory_guard_raw_cloud_en) {
                cloud = std::make_shared<
                        pcl::PointCloud<rog_map::PointType>>();
                pcl::fromROSMsg(*cloud_msg, *cloud);
                if (cloud->empty() || !cloud->is_dense) {
                    return;
                }
                tree = std::make_shared<
                        pcl::KdTreeFLANN<rog_map::PointType>>();
                tree->setInputCloud(cloud);
            }
            {
                std::lock_guard<std::mutex> lock(raw_cloud_mutex_);
                // Sequence/age are also the cheap reception diagnostics for
                // CIRI-shadow-only mode. The KD-tree is built solely when
                // the live raw-cloud guard can consume it.
                if (tree) {
                    raw_cloud_snapshot_.tree = std::move(tree);
                }
                raw_cloud_snapshot_.receive_time = receive_time;
                ++raw_cloud_snapshot_.sequence;
            }
            if (cfg_.trajectory_guard_raw_cloud_ciri_shadow_en) {
                std::lock_guard<std::mutex> lock(raw_cloud_window_mutex_);
                raw_cloud_window_.push_back(
                        {cloud_msg, cloud, receive_time});
                ++raw_cloud_window_messages_total_;
                while (!raw_cloud_window_.empty() &&
                       std::chrono::duration<double>(
                               receive_time -
                               raw_cloud_window_.front().receive_time)
                                       .count() > kRawCloudWindowMaxRetainS) {
                    raw_cloud_window_.pop_front();
                }
            }
        }

        void guardCloudCallback(
                const sensor_msgs::msg::PointCloud2::SharedPtr cloud_msg) {
            cacheGuardCloud(cloud_msg, rog_map::MapHealthClock::now());
        }

        RawCloudSafetyStatus validateTrajectoryAgainstRawCloud(
                const Trajectory &trajectory,
                double checked_from_tt,
                Vec3f &collision_position,
                double &cloud_age_s,
                std::uint64_t &cloud_sequence) const {
            if (!cfg_.trajectory_guard_raw_cloud_en) {
                cloud_age_s = 0.0;
                cloud_sequence = 0;
                return RawCloudSafetyStatus::DISABLED;
            }

            RawCloudSnapshot snapshot;
            {
                std::lock_guard<std::mutex> lock(raw_cloud_mutex_);
                snapshot = raw_cloud_snapshot_;
            }
            cloud_sequence = snapshot.sequence;
            if (!snapshot.tree || snapshot.sequence == 0) {
                cloud_age_s = std::numeric_limits<double>::infinity();
                return RawCloudSafetyStatus::STALE;
            }
            cloud_age_s = std::chrono::duration<double>(
                    rog_map::MapHealthClock::now() -
                    snapshot.receive_time).count();
            if (!std::isfinite(cloud_age_s) || cloud_age_s < 0.0 ||
                cloud_age_s > cfg_.trajectory_guard_raw_cloud_max_age_s) {
                return RawCloudSafetyStatus::STALE;
            }
            if (trajectory.empty()) {
                return RawCloudSafetyStatus::EMPTY_TRAJECTORY;
            }

            const double total_duration = trajectory.getTotalDuration();
            checked_from_tt = std::clamp(checked_from_tt, 0.0,
                                         total_duration);
            const double sample_dt = std::max(
                    0.005,
                    std::min(cfg_.trajectory_guard_validation_sample_dt_s,
                             0.05 / std::max(1.0, 7.0)));
            std::vector<int> indices(1);
            std::vector<float> squared_distances(1);
            for (double tt = checked_from_tt;;
                 tt = std::min(total_duration, tt + sample_dt)) {
                const Vec3f position = trajectory.getPos(tt);
                if (!position.array().isFinite().all()) {
                    collision_position = position;
                    return RawCloudSafetyStatus::OCCUPIED;
                }
                rog_map::PointType query;
                query.x = static_cast<float>(position.x());
                query.y = static_cast<float>(position.y());
                query.z = static_cast<float>(position.z());
                query.intensity = 0.0F;
                if (snapshot.tree->radiusSearch(
                            query,
                            cfg_.trajectory_guard_raw_cloud_clearance_m,
                            indices, squared_distances, 1) > 0) {
                    collision_position = position;
                    return RawCloudSafetyStatus::OCCUPIED;
                }
                if (tt >= total_duration) {
                    break;
                }
            }
            return RawCloudSafetyStatus::SAFE;
        }

        bool rawCloudCommittedTrajectorySafe() {
            if (!cfg_.trajectory_guard_raw_cloud_en) {
                return true;
            }
            const auto trajectory = planner_ptr_->getCommittedTrajectorySnapshot();
            RawCloudSnapshot raw_snapshot;
            {
                std::lock_guard<std::mutex> lock(raw_cloud_mutex_);
                raw_snapshot = raw_cloud_snapshot_;
                const double cached_cloud_age_s = raw_snapshot.sequence == 0
                        ? std::numeric_limits<double>::infinity()
                        : std::chrono::duration<double>(
                                rog_map::MapHealthClock::now() -
                                raw_snapshot.receive_time).count();
                if (raw_cache_cloud_sequence_ == raw_snapshot.sequence &&
                    raw_cache_trajectory_generation_ == trajectory.generation &&
                    cached_cloud_age_s <=
                            cfg_.trajectory_guard_raw_cloud_max_age_s) {
                    return raw_cache_status_ !=
                                   RawCloudSafetyStatus::OCCUPIED &&
                           raw_cache_status_ !=
                                   RawCloudSafetyStatus::EMPTY_TRAJECTORY;
                }
            }

            Vec3f collision_position = Vec3f::Zero();
            double cloud_age_s = std::numeric_limits<double>::infinity();
            std::uint64_t cloud_sequence = raw_snapshot.sequence;
            const auto status = trajectory.empty
                    ? RawCloudSafetyStatus::EMPTY_TRAJECTORY
                    : validateTrajectoryAgainstRawCloud(
                            trajectory.pos_traj,
                            ros_ptr_->getSimTime() - trajectory.start_wt,
                            collision_position, cloud_age_s, cloud_sequence);
            bool changed;
            {
                std::lock_guard<std::mutex> lock(raw_cloud_mutex_);
                changed = raw_cache_status_ != status ||
                          raw_cache_cloud_sequence_ != cloud_sequence;
                raw_cache_cloud_sequence_ = cloud_sequence;
                raw_cache_trajectory_generation_ = trajectory.generation;
                raw_cache_status_ = status;
                raw_cache_collision_position_ = collision_position;
            }
            if (changed && status != RawCloudSafetyStatus::SAFE) {
                ros_ptr_->warn(
                        " -- [TRAJ_GUARD_RAW] status={} cloud={} age={:.3f}s "
                        "gen={} p=[{:.3f},{:.3f},{:.3f}]",
                        rawCloudSafetyStatusName(status), cloud_sequence,
                        cloud_age_s, trajectory.generation,
                        collision_position.x(), collision_position.y(),
                        collision_position.z());
            }
            // Cloud production is best-effort and may be slower than the map
            // certificate cadence.  STALE is therefore diagnostic only; a
            // fresh geometric intersection remains a hard stop trigger.
            return status != RawCloudSafetyStatus::OCCUPIED &&
                   status != RawCloudSafetyStatus::EMPTY_TRAJECTORY;
        }

        void resetVisualizedPath() override {
            path.poses.clear();
        }

        void publishCurPoseToPath() override {
            path.header.frame_id = "world";
            ros_ptr_->getSimTime(path.header.stamp.sec, path.header.stamp.nanosec);
            geometry_msgs::msg::PoseStamped pose;
            pose.header = path.header;
            pose.pose.position.x = robot_state_.p(0);
            pose.pose.position.y = robot_state_.p(1);
            pose.pose.position.z = robot_state_.p(2);
            pose.pose.orientation.x = robot_state_.q.x();
            pose.pose.orientation.y = robot_state_.q.y();
            pose.pose.orientation.z = robot_state_.q.z();
            pose.pose.orientation.w = robot_state_.q.w();
            path.poses.push_back(pose);
            path_pub_->publish(path);
        }

        void fillPolynomialTrajectory(
                const Trajectory &pos_traj,
                const Trajectory &yaw_traj,
                mars_quadrotor_msgs::msg::PolynomialTrajectory &cmd_traj,
                const bool emergency = false) {
            cmd_traj = mars_quadrotor_msgs::msg::PolynomialTrajectory{};
            ros_ptr_->getSimTime(cmd_traj.header.stamp.sec,
                                 cmd_traj.header.stamp.nanosec);
            cmd_traj.header.frame_id = "world";
            cmd_traj.type = mars_quadrotor_msgs::msg::PolynomialTrajectory::POSITION_TRAJ |
                            mars_quadrotor_msgs::msg::PolynomialTrajectory::HEART_BEAT;
            if (emergency) {
                cmd_traj.type |= mars_quadrotor_msgs::msg::PolynomialTrajectory::EMER_STOP;
            }

            cmd_traj.start_wt_pos = pos_traj.start_WT;
            cmd_traj.piece_num_pos = pos_traj.getPieceNum();
            cmd_traj.order_pos = pos_traj.empty() ? 0 : pos_traj[0].getDegree();
            const std::size_t pos_col_size = cmd_traj.order_pos + 1;
            cmd_traj.time_pos.resize(cmd_traj.piece_num_pos);
            cmd_traj.coef_pos_x.resize(cmd_traj.piece_num_pos * pos_col_size);
            cmd_traj.coef_pos_y.resize(cmd_traj.piece_num_pos * pos_col_size);
            cmd_traj.coef_pos_z.resize(cmd_traj.piece_num_pos * pos_col_size);
            for (std::size_t i = 0; i < cmd_traj.piece_num_pos; ++i) {
                const auto &coeff = pos_traj[static_cast<int>(i)].getCoeffMat();
                if (coeff.cols() != static_cast<int>(pos_col_size)) {
                    throw std::runtime_error("mixed polynomial orders are unsupported");
                }
                Eigen::Map<Eigen::VectorXd>(&cmd_traj.coef_pos_x[pos_col_size * i],
                                            pos_col_size) = coeff.row(0);
                Eigen::Map<Eigen::VectorXd>(&cmd_traj.coef_pos_y[pos_col_size * i],
                                            pos_col_size) = coeff.row(1);
                Eigen::Map<Eigen::VectorXd>(&cmd_traj.coef_pos_z[pos_col_size * i],
                                            pos_col_size) = coeff.row(2);
                cmd_traj.time_pos[i] = pos_traj[static_cast<int>(i)].getDuration();
            }

            if (!yaw_traj.empty()) {
                cmd_traj.type |= mars_quadrotor_msgs::msg::PolynomialTrajectory::YAW_TRAJ;
                cmd_traj.start_wt_yaw = yaw_traj.start_WT;
                cmd_traj.piece_num_yaw = yaw_traj.getPieceNum();
                cmd_traj.order_yaw = yaw_traj[0].getDegree();
                const std::size_t yaw_col_size = cmd_traj.order_yaw + 1;
                cmd_traj.time_yaw.resize(cmd_traj.piece_num_yaw);
                cmd_traj.coef_yaw.resize(cmd_traj.piece_num_yaw * yaw_col_size);
                for (std::size_t i = 0; i < cmd_traj.piece_num_yaw; ++i) {
                    const auto &coeff = yaw_traj[static_cast<int>(i)].getCoeffMat();
                    if (coeff.cols() != static_cast<int>(yaw_col_size)) {
                        throw std::runtime_error("mixed yaw polynomial orders are unsupported");
                    }
                    Eigen::Map<Eigen::VectorXd>(&cmd_traj.coef_yaw[yaw_col_size * i],
                                                yaw_col_size) = coeff.row(0);
                    cmd_traj.time_yaw[i] = yaw_traj[static_cast<int>(i)].getDuration();
                }
            }
        }

        void publishPolyTraj() override {
            if (cfg_.trajectory_guard_en && !refreshSafetyCertificate("poly_publish")) {
                safety_revalidation_requested_.store(true, std::memory_order_release);
                return;
            }
            const auto snapshot = planner_ptr_->getCommittedTrajectorySnapshot();
            if (snapshot.empty) {
                return;
            }
            if (cfg_.trajectory_guard_en) {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                if (!safety_certificate_valid_ || !safety_certificate_.safe() ||
                    safety_certificate_.trajectory_generation != snapshot.generation) {
                    safety_revalidation_requested_.store(true, std::memory_order_release);
                    return;
                }
            }
            mars_quadrotor_msgs::msg::PolynomialTrajectory cmd_traj;
            fillPolynomialTrajectory(snapshot.pos_traj, snapshot.yaw_traj, cmd_traj);
            mpc_cmd_pub_->publish(cmd_traj);
        }

        void getOneHeartBeatMsg(mars_quadrotor_msgs::msg::PolynomialTrajectory &heartbeat, bool &traj_finish) {
            heartbeat.type = mars_quadrotor_msgs::msg::PolynomialTrajectory::HEART_BEAT;
            ros_ptr_->getSimTime(heartbeat.header.stamp.sec, heartbeat.header.stamp.nanosec);
            heartbeat.header.frame_id = "world";
            double swt;
            planner_ptr_->getOneHeartbeatTime(swt, traj_finish);
            heartbeat.start_wt_pos = swt;
        }

        void getOneHeartBeatMsg(
                mars_quadrotor_msgs::msg::PolynomialTrajectory &heartbeat,
                const CmdTraj::Sample &sample,
                const bool emergency = false) {
            heartbeat = mars_quadrotor_msgs::msg::PolynomialTrajectory{};
            heartbeat.type = mars_quadrotor_msgs::msg::PolynomialTrajectory::HEART_BEAT;
            if (emergency) {
                heartbeat.type |= mars_quadrotor_msgs::msg::PolynomialTrajectory::EMER_STOP;
            }
            ros_ptr_->getSimTime(heartbeat.header.stamp.sec,
                                 heartbeat.header.stamp.nanosec);
            heartbeat.header.frame_id = "world";
            heartbeat.start_wt_pos = sample.start_wt;
        }

        void getCommittedTrajectory(mars_quadrotor_msgs::msg::PolynomialTrajectory &cmd_traj) {
            const auto snapshot = planner_ptr_->getCommittedTrajectorySnapshot();
            fillPolynomialTrajectory(snapshot.pos_traj, snapshot.yaw_traj, cmd_traj);
        }

        void fillPositionCommand(mars_quadrotor_msgs::msg::PositionCommand &pos_cmd,
                                 const CmdTraj::Sample &sample,
                                 const int trajectory_flag = -1) {
            pos_cmd.trajectory_flag = 0;
            ros_ptr_->getSimTime(pos_cmd.header.stamp.sec, pos_cmd.header.stamp.nanosec);
            pos_cmd.header.frame_id = "world";
            const auto &pvaj = sample.pvaj;
            pos_cmd.position.x = pvaj(0, 0);
            pos_cmd.position.y = pvaj(1, 0);
            pos_cmd.position.z = pvaj(2, 0);
            pos_cmd.velocity.x = pvaj(0, 1);
            pos_cmd.velocity.y = pvaj(1, 1);
            pos_cmd.velocity.z = pvaj(2, 1);
            pos_cmd.acceleration.x = pvaj(0, 2);
            pos_cmd.acceleration.y = pvaj(1, 2);
            pos_cmd.acceleration.z = pvaj(2, 2);
            pos_cmd.jerk.x = pvaj(0, 3);
            pos_cmd.jerk.y = pvaj(1, 3);
            pos_cmd.jerk.z = pvaj(2, 3);
            pos_cmd.yaw = sample.yaw;
            pos_cmd.yaw_dot = sample.yaw_dot;
            pos_cmd.trajectory_flag = trajectory_flag >= 0
                    ? trajectory_flag : (sample.on_backup ? 2 : 1);
            Vec3f rpy, omg;
            double aT;
            geometry_utils::convertFlatOutputToAttAndOmg(
                    pvaj.col(0), pvaj.col(1), pvaj.col(2), pvaj.col(3),
                    sample.yaw, sample.yaw_dot, rpy, omg, aT);
            pos_cmd.attitude.x = rpy(0);
            pos_cmd.attitude.y = rpy(1);
            pos_cmd.attitude.z = rpy(2);
            pos_cmd.angular_velocity.x = omg(0);
            pos_cmd.angular_velocity.y = omg(1);
            pos_cmd.angular_velocity.z = omg(2);
            pos_cmd.thrust.z = aT;
            latest_cmd = pos_cmd;
            cmd_logs_.push_back(latest_cmd);
        }

        void getOnePositionCommand(mars_quadrotor_msgs::msg::PositionCommand &pos_cmd,
                                   bool &traj_finish) {
            CmdTraj::Sample sample;
            if (!planner_ptr_->getOneCommandSample(sample)) {
                traj_finish = true;
                return;
            }
            traj_finish = sample.finished;
            fillPositionCommand(pos_cmd, sample);
        }

        bool mapFreshForGuard(const rog_map::MapHealthSnapshot &health,
                              double &map_age_s) const {
            if (health.map_version == 0) {
                map_age_s = std::numeric_limits<double>::infinity();
                return false;
            }
            const auto freshness_time =
                    map_ptr_->immutablePlannerSnapshotEnabled() &&
                    health.processed_scan_count > 0
                    ? health.latest_scan_process_time
                    : health.latest_map_commit_time;
            map_age_s = std::chrono::duration<double>(
                    rog_map::MapHealthClock::now() - freshness_time).count();
            // An in-progress writer does not invalidate the previous committed
            // map. Validation takes the map's shared transaction and will wait
            // for that writer before querying, then records the new version.
            return std::isfinite(map_age_s) && map_age_s >= 0.0 &&
                   map_age_s <= cfg_.trajectory_guard_max_map_age_s;
        }

        bool mapFreshEnoughForMotion(
                const rog_map::MapHealthSnapshot &health,
                double &map_age_s) const {
            return mapFreshForGuard(health, map_age_s) &&
                   map_age_s <=
                           cfg_.trajectory_guard_brake_trigger_map_age_s;
        }

        bool refreshSafetyCertificate(const char *trigger) {
            if (!cfg_.trajectory_guard_en) {
                return true;
            }
            const auto health = map_ptr_->getMapHealthSnapshot();
            const auto generation = planner_ptr_->getCommittedTrajectoryGeneration();
            double map_age_s;
            // Do not wait until the map is already too old to certify a stop.
            // The lower motion threshold reserves time for constructing and
            // atomically certifying the brake against a still-valid snapshot.
            const bool map_fresh = mapFreshEnoughForMotion(health, map_age_s);

            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                if (map_fresh && safety_certificate_valid_ &&
                    safety_certificate_.safe() &&
                    safety_certificate_.trajectory_generation == generation &&
                    safety_certificate_.map_version == health.map_version &&
                    !safety_revalidation_requested_.load(std::memory_order_acquire)) {
                    return true;
                }
            }

            TrajectorySafetyResult result;
            if (!map_fresh) {
                result.status = TrajectorySafetyStatus::MAP_STALE;
                result.trajectory_generation = generation;
                result.map_version = health.map_version;
            } else {
                result = planner_ptr_->validateCommittedTrajectory(
                        ros_ptr_->getSimTime());
            }

            bool changed;
            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                changed = !safety_certificate_valid_ ||
                          safety_certificate_.status != result.status ||
                          safety_certificate_.trajectory_generation !=
                                  result.trajectory_generation ||
                          safety_certificate_.map_version != result.map_version;
                safety_certificate_ = result;
                safety_certificate_valid_ = true;
            }
            safety_revalidation_requested_.store(false, std::memory_order_release);

            if (changed) {
                const auto snapshot = planner_ptr_->getCommittedTrajectorySnapshot();
                const double current_tt = snapshot.empty
                        ? 0.0 : ros_ptr_->getSimTime() - snapshot.start_wt;
                const double ttc = result.first_collision_tt >= 0.0
                        ? result.first_collision_tt - current_tt : -1.0;
                fmt::print(" -- [TRAJ_GUARD_CERT] trigger={} status={} gen={} map={} "
                           "map_age={:.3f}s samples={} range=[{:.3f},{:.3f}] "
                           "collision_tt={:.3f} ttc={:.3f} p=[{:.3f},{:.3f},{:.3f}]\n",
                           trigger, trajectorySafetyStatusName(result.status),
                           result.trajectory_generation, result.map_version,
                           map_age_s, result.checked_samples,
                           result.checked_from_tt, result.checked_to_tt,
                           result.first_collision_tt, ttc,
                           result.first_collision_pos.x(),
                           result.first_collision_pos.y(),
                           result.first_collision_pos.z());
            }
            return result.safe();
        }

        Trajectory buildBrakeTrajectory(const StatePVAJ &initial,
                                        const double duration_s,
                                        const double start_wt) const {
            Eigen::Matrix<double, 3, 3> initial_pva = initial.leftCols<3>();
            Eigen::Matrix<double, 3, 3> goal_pva;
            goal_pva.setZero();
            goal_pva.col(0) = initial.col(0) + 0.5 * duration_s * initial.col(1) +
                              (duration_s * duration_s / 12.0) * initial.col(2);
            Eigen::Matrix<double, 3, Eigen::Dynamic> waypoints(3, 0);
            VecDf durations(1);
            durations << duration_s;
            auto trajectory = poly_interpo::minimumJerkInterpolation<3>(
                    initial_pva, goal_pva, waypoints, durations);
            trajectory.start_WT = start_wt;
            return trajectory;
        }

        bool brakeDynamicsWithinLimits(const Trajectory &trajectory,
                                       double &max_acc,
                                       double &max_jerk) const {
            max_acc = 0.0;
            max_jerk = 0.0;
            if (trajectory.empty()) {
                return false;
            }
            const double duration = trajectory.getTotalDuration();
            for (int i = 0; i <= 100; ++i) {
                const double tt = duration * static_cast<double>(i) / 100.0;
                const Vec3f acceleration = trajectory.getAcc(tt);
                const Vec3f jerk = trajectory.getJer(tt);
                if (!acceleration.array().isFinite().all() ||
                    !jerk.array().isFinite().all()) {
                    return false;
                }
                max_acc = std::max(max_acc, acceleration.norm());
                max_jerk = std::max(max_jerk, jerk.norm());
            }
            return max_acc <= cfg_.brake_max_acc_mps2 * 1.001 &&
                   max_jerk <= cfg_.brake_max_jerk_mps3 * 1.001;
        }

        bool activateEmergencyBrake(const std::string &reason) {
            if (!cfg_.trajectory_guard_en) {
                return false;
            }
            std::lock_guard<std::mutex> activation_lock(
                    brake_activation_mutex_);
            if (safety_brake_active_.load(std::memory_order_acquire)) {
                return false;
            }
            // A new brake is not a terminal hold until its trajectory has
            // finished and the stability checks in tryRecoverFromEmergencyBrake
            // pass. Never carry a previous recovery certificate into it.
            planner_ptr_->setCertifiedStopForReroute(false);

            // Refresh odometry before selecting a brake initial state. A
            // PositionCommand is command-continuous only while it is recent
            // and still agrees with the tracked vehicle. Guard suppression
            // deliberately stops normal command publication, so a boolean
            // "was ever published" flag alone is not a validity condition.
            planner_ptr_->getRobotState(robot_state_);
            const double selection_wt = ros_ptr_->getSimTime();
            const bool odom_position_ready = robot_state_.rcv &&
                    std::isfinite(robot_state_.rcv_time) &&
                    selection_wt - robot_state_.rcv_time >= 0.0 &&
                    selection_wt - robot_state_.rcv_time <= 0.1 &&
                    robot_state_.p.array().isFinite().all();
            double recovery_motion_dt_s =
                    std::numeric_limits<double>::infinity();
            if (odom_position_ready) {
                recovery_motion_dt_s =
                        selection_wt - recovery_motion_last_wt_;
                if (std::isfinite(recovery_motion_last_wt_) &&
                    recovery_motion_dt_s >= 0.005 &&
                    recovery_motion_dt_s <= 0.5) {
                    const Vec3f measured_velocity =
                            (robot_state_.p - recovery_motion_last_position_) /
                            recovery_motion_dt_s;
                    recovery_motion_velocity_valid_ =
                            measured_velocity.array().isFinite().all() &&
                            measured_velocity.norm() <= 50.0;
                    if (recovery_motion_velocity_valid_) {
                        recovery_motion_velocity_ = measured_velocity;
                    }
                } else if (!std::isfinite(recovery_motion_last_wt_) ||
                           recovery_motion_dt_s > 0.5 ||
                           recovery_motion_dt_s < 0.0) {
                    recovery_motion_velocity_valid_ = false;
                }
                if (!std::isfinite(recovery_motion_last_wt_) ||
                    recovery_motion_dt_s >= 0.005 ||
                    recovery_motion_dt_s < 0.0) {
                    recovery_motion_last_position_ = robot_state_.p;
                    recovery_motion_last_wt_ = selection_wt;
                }
            } else {
                recovery_motion_velocity_valid_ = false;
            }

            mars_quadrotor_msgs::msg::PositionCommand start_command;
            bool cached_command_valid;
            double cached_command_wt;
            {
                std::lock_guard<std::mutex> lock(latest_cmd_mutex_);
                cached_command_valid = last_published_cmd_valid_;
                cached_command_wt = last_published_cmd_wt_;
                if (cached_command_valid) {
                    start_command = last_published_cmd_;
                }
            }

            const Vec3f cached_position(start_command.position.x,
                                        start_command.position.y,
                                        start_command.position.z);
            const Vec3f cached_velocity(start_command.velocity.x,
                                        start_command.velocity.y,
                                        start_command.velocity.z);
            const double cached_command_age_s = cached_command_valid
                    ? selection_wt - cached_command_wt
                    : std::numeric_limits<double>::infinity();
            const double cached_position_error_m =
                    cached_command_valid && odom_position_ready &&
                            cached_position.array().isFinite().all()
                    ? (cached_position - robot_state_.p).norm()
                    : std::numeric_limits<double>::infinity();
            const double cached_velocity_error_mps =
                    cached_command_valid && recovery_motion_velocity_valid_ &&
                            cached_velocity.array().isFinite().all()
                    ? (cached_velocity - recovery_motion_velocity_).norm()
                    : std::numeric_limits<double>::infinity();
            const bool use_cached_command = cached_command_valid &&
                    odom_position_ready &&
                    std::isfinite(cached_command_age_s) &&
                    cached_command_age_s >= 0.0 &&
                    cached_command_age_s <= cfg_.brake_command_max_age_s &&
                    cached_position_error_m <=
                            cfg_.brake_command_max_position_error_m &&
                    (!recovery_motion_velocity_valid_ ||
                     cached_velocity_error_mps <=
                             cfg_.brake_command_max_velocity_error_mps);

            StatePVAJ initial;
            initial.setZero();
            double initial_yaw = 0.0;
            const char *initial_source = "none";
            if (use_cached_command) {
                initial.col(0) = Vec3f(start_command.position.x,
                                       start_command.position.y,
                                       start_command.position.z);
                initial.col(1) = Vec3f(start_command.velocity.x,
                                       start_command.velocity.y,
                                       start_command.velocity.z);
                initial.col(2) = Vec3f(start_command.acceleration.x,
                                       start_command.acceleration.y,
                                       start_command.acceleration.z);
                initial.col(3) = Vec3f(start_command.jerk.x,
                                       start_command.jerk.y,
                                       start_command.jerk.z);
                initial_yaw = start_command.yaw;
                initial_source = "fresh_command";
            } else if (odom_position_ready &&
                       recovery_motion_velocity_valid_) {
                initial.col(0) = robot_state_.p;
                initial.col(1) = recovery_motion_velocity_;
                // Position-derived odometry has no reliable acceleration or
                // jerk at this callback rate. Keep the higher derivatives at
                // the zero value established above.
                initial_yaw = robot_state_.yaw;
                initial_source = "odom_motion";
            } else {
                CmdTraj::Sample current_sample;
                if (!planner_ptr_->getOneCommandSample(current_sample)) {
                    ros_ptr_->error(
                            " -- [TRAJ_GUARD_BRAKE] no fresh odometry, "
                            "cached command is unusable, and no current "
                            "trajectory sample exists; normal publication "
                            "remains suppressed");
                    return false;
                } else {
                    initial = current_sample.pvaj;
                    initial_yaw = current_sample.yaw;
                    initial_source = "trajectory_fallback";
                }
            }

            if (!initial.array().isFinite().all()) {
                ros_ptr_->error(" -- [TRAJ_GUARD_BRAKE] invalid initial state; "
                                "normal publication remains suppressed");
                return false;
            }
            if (!std::isfinite(initial_yaw)) initial_yaw = 0.0;

            // 2026-08-18: tried a CIRI-corridor-based known-free guarantee
            // here (buildEmergencyStopPolytope, matching the SUPER paper's
            // actual backup-trajectory mechanism), first sourced from the
            // committed map, then from an accumulated raw-scan window.
            // Every variant regressed, each in a different and worse way
            // (an actual collision; then a near-total liveness collapse
            // that still didn't prevent a collision; then a full pipeline
            // freeze -- map commits stuck for 8+ seconds, the new raw
            // cloud subscription never receiving a single message despite
            // reusing the map's own topic/QoS pattern, cause not yet
            // found). Reverted; see docs for what was tried. Back to the
            // raw-grid unknown_as_occupied check below.
            const double min_duration = std::max(0.05, cfg_.brake_min_duration_s);
            const double max_duration = std::max(min_duration,
                                                 cfg_.brake_max_duration_s);
            const double max_acc_limit = std::max(1.0e-3,
                                                  cfg_.brake_max_acc_mps2);
            const double max_jerk_limit = std::max(1.0e-3,
                                                   cfg_.brake_max_jerk_mps3);
            double duration = std::max({
                    min_duration,
                    1.5 * initial.col(1).norm() / max_acc_limit,
                    std::sqrt(6.0 * initial.col(1).norm() / max_jerk_limit),
                    2.0 * initial.col(2).norm() / max_jerk_limit});
            duration = std::min(duration, max_duration);
            const double start_wt = ros_ptr_->getSimTime();
            Trajectory brake_trajectory;
            double max_acc = 0.0;
            double max_jerk = 0.0;
            bool dynamics_ok = false;
            TrajectorySafetyResult brake_safety;
            bool certified_brake_found = false;
            double certified_map_age_s =
                    std::numeric_limits<double>::infinity();
            RawCloudSafetyStatus raw_brake_status =
                    RawCloudSafetyStatus::DISABLED;
            double raw_cloud_age_s =
                    std::numeric_limits<double>::infinity();
            std::uint64_t raw_cloud_sequence = 0;
            Vec3f raw_collision_position = Vec3f::Zero();
            Trajectory ciri_shadow_candidate;
            for (int attempt = 0; attempt < 30; ++attempt) {
                auto candidate = buildBrakeTrajectory(initial, duration, start_wt);
                dynamics_ok = brakeDynamicsWithinLimits(candidate,
                                                        max_acc, max_jerk);
                if (dynamics_ok) {
                    // Cheap copy only. Accumulation, voxelization and CIRI are
                    // performed later by the latest-only shadow worker.
                    ciri_shadow_candidate = candidate;
                    const auto health_before = map_ptr_->getMapHealthSnapshot();
                    double map_age_before_s;
                    if (!mapFreshForGuard(health_before, map_age_before_s)) {
                        brake_safety.status = TrajectorySafetyStatus::MAP_STALE;
                        brake_safety.map_version = health_before.map_version;
                        certified_map_age_s = map_age_before_s;
                        break;
                    }
                    brake_safety = planner_ptr_->validatePositionTrajectory(
                            candidate, 0.0, 0, false,
                            cfg_.trajectory_guard_unknown_as_occupied);
                    const auto health_after = map_ptr_->getMapHealthSnapshot();
                    double map_age_after_s;
                    const bool map_is_fresh =
                            mapFreshForGuard(health_after, map_age_after_s);
                    certified_map_age_s = map_age_after_s;
                    const bool certificate_is_current =
                            brake_safety.safe() &&
                            map_is_fresh &&
                            brake_safety.map_version == health_after.map_version;
                    raw_brake_status = validateTrajectoryAgainstRawCloud(
                            candidate, 0.0, raw_collision_position,
                            raw_cloud_age_s, raw_cloud_sequence);
                    // A stale supplemental cloud triggers an early map-only
                    // stop.  A fresh cloud that intersects the candidate is a
                    // hard rejection and causes the duration search to
                    // continue.
                    const bool raw_certificate_allows_brake =
                            raw_brake_status !=
                                    RawCloudSafetyStatus::OCCUPIED &&
                            raw_brake_status !=
                                    RawCloudSafetyStatus::EMPTY_TRAJECTORY;
                    if (certificate_is_current &&
                        raw_certificate_allows_brake) {
                        brake_trajectory = std::move(candidate);
                        certified_map_age_s = map_age_after_s;
                        certified_brake_found = true;
                        break;
                    }
                }
                if (duration >= max_duration - 1.0e-9) {
                    break;
                }
                duration = std::min(max_duration, duration * 1.15);
            }

            // Shadow-only: queue exactly one representative candidate per
            // brake activation. The worker owns all expensive accumulated-
            // cloud and CIRI work; this callback only reads the latest
            // completed result and never uses it in an accept/reject branch.
            const std::uint64_t ciri_shadow_queued_request =
                    enqueueCiriShadowCheck(
                            reason, initial.col(0),
                            std::move(ciri_shadow_candidate));
            const CiriShadowReadout ciri_shadow_readout =
                    latestCiriShadowReadout();

            if (!certified_brake_found) {
                ros_ptr_->error(
                        " -- [TRAJ_GUARD_BRAKE_REJECTED] trigger={} "
                        "searched=[{:.3f},{:.3f}]s speed0={:.3f} "
                        "initial_source={} cmd_age={:.3f}s "
                        "cmd_pos_err={:.3f} cmd_vel_err={:.3f} "
                        "motion_speed={:.3f} motion_dt={:.3f}s "
                        "last_dynamics_ok={} max_acc={:.3f} max_jerk={:.3f} "
                            "last_path_status={} last_map={} map_age={:.3f}s "
                            "raw_status={} raw_cloud={} raw_age={:.3f}s "
                            "ciri_shadow={} ciri_shadow_result={} "
                            "ciri_shadow_queued={} ciri_shadow_age={:.3f}s; "
                            "no brake command published",
                        reason, min_duration, max_duration,
                        initial.col(1).norm(), initial_source,
                        cached_command_age_s, cached_position_error_m,
                        cached_velocity_error_mps,
                        recovery_motion_velocity_valid_
                                ? recovery_motion_velocity_.norm()
                                : std::numeric_limits<double>::infinity(),
                        recovery_motion_dt_s,
                        dynamics_ok, max_acc, max_jerk,
                        trajectorySafetyStatusName(brake_safety.status),
                        brake_safety.map_version, certified_map_age_s,
                        rawCloudSafetyStatusName(raw_brake_status),
                        raw_cloud_sequence, raw_cloud_age_s,
                        ciriShadowStatusName(ciri_shadow_readout.status),
                        ciri_shadow_readout.request_id,
                        ciri_shadow_queued_request,
                        ciri_shadow_readout.age_s);
                // 2026-08-18: tried arming a topology-avoidance zone here
                // too (same mechanism a rejected PlanFromRest candidate
                // uses) so a persistently-blocked brake would push the next
                // replan toward a different direction instead of retrying
                // identically. Measured net negative on the seed1-10 sweep
                // (34/50 vs the 41-42/50 baseline, with two previously
                // reliable seeds dropping to 1-2/5) -- a brake candidate's
                // collision point reflects wherever the vehicle currently
                // is while moving, not a stable obstacle location the way
                // a stopped candidate's rejection point does, so this
                // ended up walling off the vehicle's own flight path.
                // Reverted; see docs for the corridor-containment approach
                // (buildEmergencyStopPolytope) that replaced it instead.
                ChangeState("TrajectoryGuardFailClosed", EMER_STOP);
                return false;
            }

            Eigen::Matrix<double, 3, 1> yaw_coeff;
            yaw_coeff.setZero();
            yaw_coeff(0, 0) = initial_yaw;
            Trajectory yaw_trajectory;
            yaw_trajectory.emplace_back(duration, yaw_coeff);
            yaw_trajectory.start_WT = start_wt;

            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                if (safety_brake_active_.load(std::memory_order_relaxed)) {
                    return false;
                }
                brake_pos_traj_ = brake_trajectory;
                brake_yaw_traj_ = yaw_trajectory;
                brake_start_wt_ = start_wt;
                brake_duration_s_ = duration;
                brake_yaw_ = initial_yaw;
                brake_reason_ = reason;
                brake_stop_position_ = brake_trajectory.getPos(duration);
                brake_stability_started_ = false;
                brake_recovery_last_attempt_wt_ = -
                        std::numeric_limits<double>::infinity();
                safety_brake_finished_.store(false, std::memory_order_release);
                safety_brake_active_.store(true, std::memory_order_release);
            }

            const Vec3f stop_position = brake_trajectory.getPos(duration);
            ros_ptr_->error(" -- [TRAJ_GUARD_BRAKE] trigger={} duration={:.3f}s "
                            "speed0={:.3f} initial_source={} cmd_age={:.3f}s "
                            "cmd_pos_err={:.3f} cmd_vel_err={:.3f} "
                            "motion_speed={:.3f} motion_dt={:.3f}s "
                            "max_acc={:.3f} max_jerk={:.3f} "
                            "dynamics_ok={} path_status={} map={} map_age={:.3f}s "
                            "raw_status={} raw_cloud={} raw_age={:.3f}s "
                            "ciri_shadow={} ciri_shadow_result={} "
                            "ciri_shadow_queued={} ciri_shadow_age={:.3f}s "
                            "stop=[{:.3f},{:.3f},{:.3f}]",
                            reason, duration, initial.col(1).norm(),
                            initial_source, cached_command_age_s,
                            cached_position_error_m,
                            cached_velocity_error_mps,
                            recovery_motion_velocity_valid_
                                    ? recovery_motion_velocity_.norm()
                                    : std::numeric_limits<double>::infinity(),
                            recovery_motion_dt_s, max_acc, max_jerk,
                            dynamics_ok, trajectorySafetyStatusName(brake_safety.status),
                            brake_safety.map_version, certified_map_age_s,
                            rawCloudSafetyStatusName(raw_brake_status),
                            raw_cloud_sequence, raw_cloud_age_s,
                            ciriShadowStatusName(ciri_shadow_readout.status),
                            ciri_shadow_readout.request_id,
                            ciri_shadow_queued_request,
                            ciri_shadow_readout.age_s,
                            stop_position.x(), stop_position.y(), stop_position.z());
            mars_quadrotor_msgs::msg::PolynomialTrajectory brake_message;
            fillPolynomialTrajectory(brake_trajectory, yaw_trajectory,
                                     brake_message, true);
            mpc_cmd_pub_->publish(brake_message);
            ChangeState("TrajectoryGuard", EMER_STOP);
            return true;
        }

        bool getBrakeSample(CmdTraj::Sample &sample) {
            std::lock_guard<std::mutex> lock(safety_mutex_);
            if (!safety_brake_active_.load(std::memory_order_relaxed) ||
                brake_pos_traj_.empty()) {
                return false;
            }
            const double raw_tt = ros_ptr_->getSimTime() - brake_start_wt_;
            const double eval_tt = std::clamp(raw_tt, 0.0, brake_duration_s_);
            sample = CmdTraj::Sample{};
            if (!brake_pos_traj_.getState(eval_tt, sample.pvaj)) {
                return false;
            }
            sample.start_wt = brake_start_wt_;
            sample.trajectory_time = eval_tt;
            sample.total_duration = brake_duration_s_;
            sample.finished = raw_tt >= brake_duration_s_;
            sample.on_backup = true;
            sample.yaw = brake_yaw_;
            sample.yaw_dot = 0.0;
            if (sample.finished) {
                sample.pvaj.col(1).setZero();
                sample.pvaj.col(2).setZero();
                sample.pvaj.col(3).setZero();
                safety_brake_finished_.store(true, std::memory_order_release);
            }
            return true;
        }

        bool tryRecoverFromEmergencyBrake() {
            if (!safety_brake_active_.load(std::memory_order_acquire) ||
                !safety_brake_finished_.load(std::memory_order_acquire)) {
                return false;
            }

            const auto health = map_ptr_->getMapHealthSnapshot();
            double map_age_s;
            if ((health.update_in_progress &&
                 !map_ptr_->immutablePlannerSnapshotEnabled()) ||
                !mapFreshForGuard(health, map_age_s)) {
                return false;
            }

            planner_ptr_->getRobotState(robot_state_);
            const double now_wt = ros_ptr_->getSimTime();
            const bool odom_ready = robot_state_.rcv &&
                    now_wt - robot_state_.rcv_time <= 0.1;
            if (!odom_ready ||
                (robot_state_.p - brake_stop_position_).norm() > 0.15) {
                brake_stability_started_ = false;
                return false;
            }
            if (!brake_stability_started_ ||
                (robot_state_.p - brake_stability_anchor_).norm() > 0.03) {
                brake_stability_anchor_ = robot_state_.p;
                brake_stability_start_wt_ = now_wt;
                brake_stability_started_ = true;
                return false;
            }
            if (now_wt - brake_stability_start_wt_ < 0.25) {
                return false;
            }

            // Keep publishing the certified terminal hold while retrying from
            // rest at a bounded rate. This gives map commits time to run in
            // the shared execution group and never exposes a rejected
            // candidate to the command publisher.
            if (now_wt - brake_recovery_last_attempt_wt_ < 0.5) {
                return false;
            }
            brake_recovery_last_attempt_wt_ = now_wt;
            // All checks above are part of the certified-stop boundary: the
            // map is fresh, the brake finished, odometry is current and the
            // vehicle has held the certified terminal position for 0.25 s.
            // PlanFromRest may now arm start-aware topology blockers even if
            // its separately sampled odometry speed is slightly above the
            // legacy scalar threshold.
            planner_ptr_->setCertifiedStopForReroute(true);
            const auto generation_before =
                    planner_ptr_->getCommittedTrajectoryGeneration();
            if (machine_state_ != GENERATE_TRAJ) {
                ChangeState("TrajectoryGuardRecovery", GENERATE_TRAJ);
            }
            callMainFsmOnce();
            const bool candidate_rejected =
                    planner_ptr_->consumeTrajectoryGuardRejection();
            const auto generation_after =
                    planner_ptr_->getCommittedTrajectoryGeneration();
            if (candidate_rejected || generation_after <= generation_before ||
                machine_state_ != FOLLOW_TRAJ ||
                !refreshSafetyCertificate("brake_recovery")) {
                return false;
            }

            const auto health_after = map_ptr_->getMapHealthSnapshot();
            double map_age_after_s;
            if (!mapFreshForGuard(health_after, map_age_after_s)) {
                return false;
            }
            TrajectorySafetyResult recovered_certificate;
            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                recovered_certificate = safety_certificate_;
            }
            CmdTraj::Sample recovered_sample;
            if (!recovered_certificate.safe() ||
                recovered_certificate.trajectory_generation != generation_after ||
                recovered_certificate.map_version != health_after.map_version ||
                !planner_ptr_->getOneCommandSample(recovered_sample,
                                                   generation_after) ||
                recovered_sample.finished) {
                return false;
            }
            publishPolyTraj();

            std::string recovered_reason;
            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                recovered_reason = brake_reason_;
                brake_pos_traj_ = Trajectory{};
                brake_yaw_traj_ = Trajectory{};
                brake_stability_started_ = false;
                safety_brake_finished_.store(false, std::memory_order_release);
                safety_brake_active_.store(false, std::memory_order_release);
            }
            ros_ptr_->info(" -- [TRAJ_GUARD_RECOVERED] trigger={} gen={} map={}",
                           recovered_reason,
                           planner_ptr_->getCommittedTrajectoryGeneration(),
                           health.map_version);
            return true;
        }

        void recordPublishedCommand(
                const mars_quadrotor_msgs::msg::PositionCommand &command) {
            std::lock_guard<std::mutex> lock(latest_cmd_mutex_);
            last_published_cmd_ = command;
            last_published_cmd_wt_ = ros_ptr_->getSimTime();
            last_published_cmd_valid_ = true;
        }

    public:
        FsmRos2() = default;

        ~FsmRos2() {
            if (ciri_shadow_uses_map_cloud_observer_ && map_ptr_) {
                map_ptr_->setAcceptedCloudObserver({});
            }
            stopCiriShadowWorker();
            saveReplanLogToFile();
        };

        typedef std::shared_ptr<FsmRos2> Ptr;

        void saveReplanLogToFile(const string &name = "") {
            // run statistic
            double total_length{0.0};
            int total_replan_num{0};
            double average_compt_t{0.0};
            Vec3f cur_p{0, 0, 0};
            for (auto rp: replan_logs_) {
                if (rp.getRetCode() > 0) {
                    if (cur_p.norm() < 1e-6) {
                        cur_p = rp.getRobotP();
                    } else {
                        total_length += (rp.getRobotP() - cur_p).norm();
                        cur_p = rp.getRobotP();
                    }
                    total_replan_num++;
                    average_compt_t += rp.getTotalCompT();
                }
            }


            fmt::print("Total replan num: {}, total length: {}, average computation time: {} ms\n",
                       total_replan_num, total_length,
                       average_compt_t / (total_replan_num == 0 ? 1 : total_replan_num) * 1000);


            const std::string save_path = name.empty()
                                          ? LOG_FILE_DIR(
                                                  "replan_logs/" + BinaryFileHandler<int>::getCurrentTimeStr() + ".bin")
                                          : LOG_FILE_DIR("replan_logs/" + name + ".bin");
            const std::string csv_path = name.empty()
                                         ? LOG_FILE_DIR(
                                                 "cmd_logs/" + BinaryFileHandler<int>::getCurrentTimeStr() + ".csv")
                                         : LOG_FILE_DIR("cmd_logs/" + name + ".csv");
            BinaryFileHandler<vector<LogOneReplan>>::save(save_path, replan_logs_);

            std::ofstream csv_writer;
            csv_writer.open(csv_path, std::ios::out | std::ios::trunc);
            csv_writer
                    << "time,posi_x,posi_y,posi_z,vel_x,vel_y,vel_z,acc_x,acc_y,acc_z,jerk_x,jerk_y,jerk_z,yaw,yaw_rate,backup"
                    << std::endl;
            csv_writer << std::fixed << std::setprecision(15);
            for (const auto &cmd: cmd_logs_) {
                const double timestamp = static_cast<double>(cmd.header.stamp.sec) +
                                         static_cast<double>(cmd.header.stamp.nanosec) * 1e-9;
                csv_writer << timestamp - system_start_time_
                           << "," << cmd.position.x << "," << cmd.position.y << ","
                           << cmd.position.z << ","
                           << cmd.velocity.x << "," << cmd.velocity.y << "," << cmd.velocity.z << ","
                           << cmd.acceleration.x << "," << cmd.acceleration.y << "," << cmd.acceleration.z << ","
                           << cmd.jerk.x << "," << cmd.jerk.y << "," << cmd.jerk.z << ","
                           << cmd.yaw << "," << cmd.yaw_dot << "," << static_cast<int>(cmd.trajectory_flag)
                           << std::endl;
            }
            csv_writer.close();
        }

        bool getPoseFromTraj(super_utils::Pose &pose) {
            if (machine_state_ != FOLLOW_TRAJ) {
                cout << YELLOW << "[Fsm] Not in FOLLOW_TRAJ state, can't get pose from traj." << RESET << endl;
                return false;
            }
            getOnePositionCommand(pid_cmd_, traj_finish_);
            if (traj_finish_) {
                cout << GREEN << " -- [Fsm] Traj finish." << RESET << endl;
                if (closeToGoal(0.1)) {
                    ChangeState("getPoseFromTraj", WAIT_GOAL);
                } else {
                    ChangeState("getPoseFromTraj", GENERATE_TRAJ);
                }
            }
            pose.first = Vec3f{pid_cmd_.position.x, pid_cmd_.position.y, pid_cmd_.position.z};
            pose.second = eulerToQuaternion(pid_cmd_.attitude.x, pid_cmd_.attitude.y, pid_cmd_.attitude.z);


            /// for checking the trajectory continuty
            static double max_delta_v{0.0};
            static double last_v = pid_cmd_.vel_norm;
            double delta_v = std::abs(pid_cmd_.vel_norm - last_v);
            last_v = pid_cmd_.vel_norm;
            if (delta_v > max_delta_v) {
                max_delta_v = delta_v;
            }
            fmt::print(" -- [Fsm] Cur vel: {}, delta_v: {}, max_delta_v: {}\n", pid_cmd_.vel_norm, delta_v,
                       max_delta_v);
            cmd_logs_.push_back(latest_cmd);
            return true;
        }

        void goalCallback(const geometry_msgs::msg::PoseStamped::SharedPtr msg) {
            super_utils::Vec3f goal_p = Vec3f{msg->pose.position.x, msg->pose.position.y, msg->pose.position.z};
            super_utils::Quatf goal_q = super_utils::Quatf{msg->pose.orientation.w, msg->pose.orientation.x,
                                                           msg->pose.orientation.y, msg->pose.orientation.z};
            enqueueGoal(goal_p, goal_q);
        }

        void init(const rclcpp::Node::SharedPtr nh, const std::string &cfg_path) {
            // TODO: The current implementation uses a lenient QoS configuration for message transmission.
            const rclcpp::QoS qos(rclcpp::QoS(1)
                                          .best_effort()
                                          .keep_last(1)
                                          .durability_volatile());

            // 初始化参数读取
            nh_ = nh;
            cfg_ = Config(cfg_path);
            // Keep map commits schedulable while planner optimization is
            // running. Planner map-reading frontends take an explicit shared
            // map transaction; the writer takes the matching exclusive lock.
            exec_cbk_group_ = nh_->create_callback_group(
                    rclcpp::CallbackGroupType::MutuallyExclusive);
            map_cbk_group_ = nh_->create_callback_group(
                    rclcpp::CallbackGroupType::MutuallyExclusive);
            map_ptr_ = std::make_shared<rog_map::ROGMapROS>(
                    nh_, cfg_path, map_cbk_group_);
            // 初始化Planner
            ros_ptr_ = std::make_shared<ros_interface::Ros2Interface>(nh_);
            planner_ptr_ = std::make_shared<SuperPlanner>(cfg_path, ros_ptr_, map_ptr_);
            if (cfg_.trajectory_guard_raw_cloud_en ||
                cfg_.trajectory_guard_raw_cloud_ciri_shadow_en) {
                const char *cloud_source = "map_observer";
                if (cfg_.trajectory_guard_raw_cloud_en) {
                    // The live raw-cloud guard owns a KD-tree snapshot and
                    // retains its existing independent callback group.
                    guard_cloud_cbk_group_ = nh_->create_callback_group(
                            rclcpp::CallbackGroupType::MutuallyExclusive);
                    rclcpp::SubscriptionOptions guard_cloud_options;
                    guard_cloud_options.callback_group =
                            guard_cloud_cbk_group_;
                    guard_cloud_sub_ = nh_->create_subscription<
                            sensor_msgs::msg::PointCloud2>(
                            map_ptr_->getMapConfig().cloud_topic, qos,
                            std::bind(&FsmRos2::guardCloudCallback, this,
                                      std::placeholders::_1),
                            guard_cloud_options);
                    cloud_source = "dedicated_subscription";
                } else {
                    // Shadow-only must not deserialize the same large scan a
                    // second time. ROG-Map hands off the SharedPtr for each
                    // scan it already accepted; this callback only stores it.
                    map_ptr_->setAcceptedCloudObserver(
                            [this](
                                    const sensor_msgs::msg::PointCloud2::SharedPtr
                                            &cloud_msg,
                                    const rog_map::MapHealthClock::time_point
                                            receive_time) {
                                cacheGuardCloud(cloud_msg, receive_time);
                            });
                    ciri_shadow_uses_map_cloud_observer_ = true;
                }
                ros_ptr_->info(
                        " -- [TRAJ_GUARD_RAW] enabled topic={} max_age={:.3f}s "
                        "clearance={:.3f}m ciri_shadow={} accum_window={:.3f}s "
                        "source={}",
                        map_ptr_->getMapConfig().cloud_topic,
                        cfg_.trajectory_guard_raw_cloud_max_age_s,
                        cfg_.trajectory_guard_raw_cloud_clearance_m,
                        cfg_.trajectory_guard_raw_cloud_ciri_shadow_en,
                        cfg_.trajectory_guard_raw_cloud_accum_window_s,
                        cloud_source);
            }
            if (cfg_.trajectory_guard_raw_cloud_ciri_shadow_en) {
                ciri_shadow_worker_ = std::thread(
                        &FsmRos2::ciriShadowWorkerLoop, this);
                ros_ptr_->info(
                        " -- [TRAJ_GUARD_RAW_CIRI_ASYNC] latest-only worker "
                        "started");
            }
            cmd_pub_ = nh_->create_publisher<mars_quadrotor_msgs::msg::PositionCommand>(cfg_.cmd_topic, qos);
            mpc_cmd_pub_ = nh_->create_publisher<mars_quadrotor_msgs::msg::PolynomialTrajectory>(cfg_.mpc_cmd_topic,
                                                                                                 qos);
            path_pub_ = nh_->create_publisher<nav_msgs::msg::Path>("fsm/path", qos);

            int cmd_cnt = 0;

            if (cfg_.click_goal_en) {
                goal_cbk_group_ = nh_->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
                rclcpp::SubscriptionOptions so;
                so.callback_group = goal_cbk_group_;
                goal_sub_ = nh_->create_subscription<geometry_msgs::msg::PoseStamped>(
                        cfg_.click_goal_topic,
                        qos,
                        std::bind(&FsmRos2::goalCallback, this, std::placeholders::_1),
                        so);
                cout << YELLOW << " -- [Fsm] CLICKGOAL ENABLE." << RESET << endl;
                cmd_cnt++;
            }

            if (cmd_cnt != 1) {
                cout << YELLOW << " -- [Fsm] CMD INPUT ERROR." << RESET << endl;
                exit(0);
            }

            if (cfg_.timer_en) {
                execution_timer_ = nh_->create_wall_timer(
                        std::chrono::milliseconds(10),
                        std::bind(&FsmRos2::mainFsmTimerCallback, this),
                        exec_cbk_group_
                );

                cmd_cbk_group_ = nh_->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
                cmd_timer_ = nh_->create_wall_timer(
                        std::chrono::milliseconds(10),
                        std::bind(&FsmRos2::pubCmdTimerCallback, this),
                        cmd_cbk_group_
                );
                const int replan_ratems = static_cast<int>(1.0 / cfg_.replan_rate * 1000);
                replan_cbk_group_ = nh_->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
                replan_timer_ = nh_->create_wall_timer(
                        std::chrono::milliseconds(replan_ratems),
                        std::bind(&FsmRos2::replanTimerCallback, this),
                        replan_cbk_group_
                );
            }

            write_time_.open(DEBUG_FILE_DIR("time_consuming.csv"), std::ios::out | std::ios::trunc);
            log_module_time.resize(9);
            for (int i = 0; i < 9; i++) {
                write_time_ << log_time_str[i];
                if (i != 8) {
                    write_time_ << ",";
                }
            }
            write_time_ << endl;
            machine_state_ = INIT;
            system_start_time_ = ros_ptr_->getSimTime();

            pid_cmd_.kx[0] = 5.7;
            pid_cmd_.kx[1] = 5.7;
            pid_cmd_.kx[2] = 4.2;

            pid_cmd_.kv[0] = 3.4;
            pid_cmd_.kv[1] = 3.4;
            pid_cmd_.kv[2] = 4.0;
        }

        void pubCmdTimerCallback() {
            if (stop) {
                return;
            }

            if (safety_brake_active_.load(std::memory_order_acquire)) {
                CmdTraj::Sample brake_sample;
                if (!getBrakeSample(brake_sample)) {
                    return;
                }
                mars_quadrotor_msgs::msg::PolynomialTrajectory heartbeat;
                getOneHeartBeatMsg(heartbeat, brake_sample, true);
                // 3 is reserved locally for the trajectory-guard emergency
                // brake; upstream uses 1 for exploratory and 2 for backup.
                fillPositionCommand(pid_cmd_, brake_sample, 3);
                mpc_cmd_pub_->publish(heartbeat);
                cmd_pub_->publish(pid_cmd_);
                recordPublishedCommand(pid_cmd_);
                return;
            }

            if (machine_state_ != FOLLOW_TRAJ && machine_state_ != EMER_STOP) {
                return;
            }

            CmdTraj::Sample command_sample;
            if (cfg_.trajectory_guard_en) {
                TrajectorySafetyResult certificate;
                bool certificate_valid;
                {
                    std::lock_guard<std::mutex> lock(safety_mutex_);
                    certificate = safety_certificate_;
                    certificate_valid = safety_certificate_valid_;
                }
                const auto health_before = map_ptr_->getMapHealthSnapshot();
                double map_age_s;
                if (!certificate_valid || !certificate.safe() ||
                    !mapFreshForGuard(health_before, map_age_s) ||
                    certificate.map_version != health_before.map_version ||
                    !planner_ptr_->getOneCommandSample(
                            command_sample, certificate.trajectory_generation)) {
                    safety_revalidation_requested_.store(true,
                                                         std::memory_order_release);
                    return;
                }
                const auto health_after = map_ptr_->getMapHealthSnapshot();
                if ((health_after.update_in_progress &&
                     !map_ptr_->immutablePlannerSnapshotEnabled()) ||
                    health_after.map_version != certificate.map_version) {
                    safety_revalidation_requested_.store(true,
                                                         std::memory_order_release);
                    return;
                }
            } else if (!planner_ptr_->getOneCommandSample(command_sample)) {
                return;
            }

            mars_quadrotor_msgs::msg::PolynomialTrajectory heartbeat;
            getOneHeartBeatMsg(heartbeat, command_sample);
            traj_finish_ = command_sample.finished;
            fillPositionCommand(pid_cmd_, command_sample);
            mpc_cmd_pub_->publish(heartbeat);
            cmd_pub_->publish(pid_cmd_);
            recordPublishedCommand(pid_cmd_);
            if (traj_finish_) {
                cout << GREEN << " -- [Fsm] Traj finish." << RESET << endl;
                if (closeToGoal(0.1)) {
                    ChangeState("PubCmdCallback", WAIT_GOAL);
                } else {
                    ChangeState("PubCmdCallback", GENERATE_TRAJ);
                }
            }
        }

        void replanTimerCallback() {
            if (safety_brake_active_.load(std::memory_order_acquire)) {
                return;
            }
            if (cfg_.trajectory_guard_en) {
                const auto health = map_ptr_->getMapHealthSnapshot();
                double map_age_s;
                const double replan_start_age_limit = std::max(
                        0.05, 0.5 * cfg_.trajectory_guard_max_map_age_s);
                if (safety_revalidation_requested_.load(std::memory_order_acquire) ||
                    !mapFreshForGuard(health, map_age_s) ||
                    map_age_s > replan_start_age_limit) {
                    return;
                }
            }
            callReplanOnce();
            const bool candidate_rejected = cfg_.trajectory_guard_en &&
                    planner_ptr_->consumeTrajectoryGuardRejection();
            if (candidate_rejected && machine_state_ != FOLLOW_TRAJ) {
                activateEmergencyBrake("candidate_rejected_without_safe_follow");
                return;
            }
            if (cfg_.trajectory_guard_en && machine_state_ == FOLLOW_TRAJ &&
                !safety_brake_active_.load(std::memory_order_acquire) &&
                !refreshSafetyCertificate("replan_post")) {
                activateEmergencyBrake("replan_post_uncertified");
            }
        }

        void mainFsmTimerCallback() {
            // 2026-08-19: isolated diagnostic, gated only on the subscription
            // existing (not on trajectory_guard_raw_cloud_en, which this
            // does not read or affect). Purely observational -- see the
            // raw_cloud_debug_last_log_ comment above.
            if (guard_cloud_sub_ ||
                ciri_shadow_uses_map_cloud_observer_) {
                const double since_log_s = std::chrono::duration<double>(
                        rog_map::MapHealthClock::now() -
                        raw_cloud_debug_last_log_).count();
                if (since_log_s >= 1.0) {
                    raw_cloud_debug_last_log_ = rog_map::MapHealthClock::now();
                    std::uint64_t seq;
                    double age_s;
                    {
                        std::lock_guard<std::mutex> lock(raw_cloud_mutex_);
                        seq = raw_cloud_snapshot_.sequence;
                        age_s = raw_cloud_snapshot_.sequence == 0
                                ? -1.0
                                : std::chrono::duration<double>(
                                        rog_map::MapHealthClock::now() -
                                        raw_cloud_snapshot_.receive_time)
                                          .count();
                    }
                    ros_ptr_->warn(
                            " -- [TRAJ_GUARD_RAW_DEBUG] sequence={} "
                            "latest_age_s={:.3f}",
                            seq, age_s);
                }
            }
            if (safety_brake_active_.load(std::memory_order_acquire)) {
                tryRecoverFromEmergencyBrake();
                return;
            }
            if (cfg_.trajectory_guard_shadow_en &&
                !cfg_.trajectory_guard_en && machine_state_ == FOLLOW_TRAJ) {
                const auto health = map_ptr_->getMapHealthSnapshot();
                if ((!health.update_in_progress ||
                     map_ptr_->immutablePlannerSnapshotEnabled()) &&
                    health.map_version != 0 &&
                    health.map_version != shadow_last_enqueued_map_version_ &&
                    planner_ptr_->enqueueCommittedTrajectoryShadowValidation(
                            "MAP_COMMIT")) {
                    shadow_last_enqueued_map_version_ = health.map_version;
                }
            }
            if (cfg_.trajectory_guard_en && machine_state_ == FOLLOW_TRAJ &&
                !rawCloudCommittedTrajectorySafe()) {
                activateEmergencyBrake("main_pre_raw_cloud");
                return;
            }
            if (cfg_.trajectory_guard_en && machine_state_ == FOLLOW_TRAJ &&
                !refreshSafetyCertificate("main_pre")) {
                activateEmergencyBrake("main_pre_uncertified");
                return;
            }
            callMainFsmOnce();
            const bool candidate_rejected = cfg_.trajectory_guard_en &&
                    planner_ptr_->consumeTrajectoryGuardRejection();
            if (candidate_rejected && machine_state_ != FOLLOW_TRAJ) {
                activateEmergencyBrake("candidate_rejected_without_safe_follow");
                return;
            }
            if (cfg_.trajectory_guard_en && machine_state_ == FOLLOW_TRAJ &&
                !safety_brake_active_.load(std::memory_order_acquire) &&
                !refreshSafetyCertificate("main_post")) {
                activateEmergencyBrake("main_post_uncertified");
            }
        }

    };
}

#endif //SRC_FSM_ROS1_HPP

#endif
