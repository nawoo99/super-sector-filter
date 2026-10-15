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
#include "fsm/startup_recovery_completion_policy.hpp"
#include "fsm/async_certified_recovery.hpp"
#include "fsm/async_from_rest_planning.hpp"
#include "fsm/brake_motion_estimate_policy.hpp"
#include "fsm/active_yaw_scan_policy.hpp"
#include "fsm/command_publication_policy.hpp"
#include "fsm/path_publication_policy.hpp"
#include <super_utils/thread_cpu_profile.hpp>
#include <super_utils/callback_timing_trace.hpp>
#include <rog_map/diagnostic_trace.hpp>

#include <rclcpp/rclcpp.hpp>
#include <ros_interface/ros2/ros2_interface.hpp>
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "nav_msgs/msg/path.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "mars_quadrotor_msgs/msg/position_command.hpp"
#include "mars_quadrotor_msgs/msg/polynomial_trajectory.hpp"
#include "mars_quadrotor_msgs/msg/trajectory_risk_verdict.hpp"
#include "std_msgs/msg/bool.hpp"
#include "std_msgs/msg/u_int64.hpp"
#include "std_msgs/msg/u_int64_multi_array.hpp"
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl_conversions/pcl_conversions.h>
#include <utils/optimization/polynomial_interpolation.h>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <limits>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_set>


namespace fsm {
    namespace demand_policy = super_planner::demand_replan;
    namespace startup_recovery = super_planner::startup_recovery;
    namespace async_recovery = super_planner::async_recovery;
    namespace async_from_rest = super_planner::async_from_rest;
    class FsmRos2 : public Fsm {

        rclcpp::Node::SharedPtr nh_;
        rclcpp::Publisher<mars_quadrotor_msgs::msg::PositionCommand>::SharedPtr cmd_pub_;
        rclcpp::Publisher<mars_quadrotor_msgs::msg::PolynomialTrajectory>::SharedPtr mpc_cmd_pub_;
        rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_pub_;
        rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr
                trajectory_guard_recovery_pub_;
        rclcpp::Subscription<std_msgs::msg::UInt64MultiArray>::SharedPtr
                full_refresh_request_sub_;
        rclcpp::Subscription<std_msgs::msg::UInt64MultiArray>::SharedPtr
                cloud_process_ack_sub_;
        rclcpp::Subscription<std_msgs::msg::UInt64>::SharedPtr event_recovery_request_sub_;
        std::atomic<std::uint64_t> event_recovery_requested_{0};
        std::atomic<std::uint64_t> event_recovery_completed_{0};
        std::uint64_t event_recovery_handled_{0};
        std::uint64_t event_recovery_min_map_version_{0};
        std::uint64_t event_recovery_not_before_stamp_ns_{0};
        std::atomic<std::uint64_t> goal_change_full_refresh_requested_{0};
        std::uint64_t goal_change_full_refresh_handled_{0};
        std::atomic<std::uint64_t> active_yaw_scan_goal_requested_{0};
        std::uint64_t active_yaw_scan_goal_handled_{0};
        rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr goal_sub_;
        rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr
                guard_cloud_sub_;
        rclcpp::Subscription<
                mars_quadrotor_msgs::msg::TrajectoryRiskVerdict>::SharedPtr
                frontend_risk_verdict_sub_;
        bool raw_cloud_shadow_uses_map_cloud_observer_{false};
        bool raw_cloud_in_process_injection_en_{false};

        rclcpp::TimerBase::SharedPtr execution_timer_, replan_timer_, cmd_timer_;
        super_utils::callback_timing_trace::State main_trace_, replan_trace_, command_trace_;
        rclcpp::CallbackGroup::SharedPtr exec_cbk_group_, map_cbk_group_, replan_cbk_group_, cmd_cbk_group_, goal_cbk_group_;
        rclcpp::CallbackGroup::SharedPtr guard_cloud_cbk_group_;
        rclcpp::CallbackGroup::SharedPtr frontend_risk_cbk_group_;
        rclcpp::CallbackGroup::SharedPtr refresh_ack_cbk_group_;

        mars_quadrotor_msgs::msg::PositionCommand pid_cmd_;
        rog_map::ROGMapROS::Ptr map_ptr_;
        mars_quadrotor_msgs::msg::PositionCommand latest_cmd;
        nav_msgs::msg::Path path;

        vector<mars_quadrotor_msgs::msg::PositionCommand> cmd_logs_;

        mutable std::mutex safety_mutex_;
        TrajectorySafetyResult safety_certificate_{};
        bool safety_certificate_valid_{false};
        // Both counters are protected by safety_mutex_. Completion order must
        // not let an earlier validation replace a later published result.
        std::uint64_t safety_validation_started_{0};
        std::uint64_t safety_certificate_validation_{0};
        std::atomic_bool safety_brake_active_{false};
        std::atomic_bool safety_brake_finished_{false};
        std::atomic_bool safety_revalidation_requested_{false};
        // Replanning faster than the committed-map cadence used to generate
        // several new polynomials from the same immutable map snapshot.  A
        // successful replan leaves a guarded trajectory in charge, so the
        // opt-in policy suppresses only immediate timer-tick duplicates.
        // Progress replanning resumes after a bounded interval even if the
        // map is unchanged. Failed replans are deliberately not recorded, so
        // topology recovery and liveness retries remain unchanged.
        std::uint64_t last_successful_replan_map_version_{0};
        std::uint64_t last_successful_replan_generation_{0};
        rog_map::MapHealthClock::time_point last_successful_replan_time_{};
        std::uint64_t same_map_replan_skips_{0};
        // Replan-callback-owned bookkeeping; no new timer or worker.
        bool demand_has_ordinary_success_{false};
        bool demand_failure_since_success_{true};
        std::uint64_t demand_success_generation_{0};
        GoalDemandSnapshot demand_success_goal_{};
        std::uint64_t demand_success_event_request_{0};
        rog_map::MapHealthClock::time_point demand_success_dispatch_{};
        demand_policy::StopViabilityReceipt demand_viability_receipt_{};
        std::uint64_t demand_checks_{0}, demand_skips_{0}, demand_renewals_{0};
        demand_policy::DecisionCounters demand_decision_counters_{};
        rog_map::MapHealthClock::time_point demand_last_report_{};
        double demand_last_observed_sim_wt_{std::numeric_limits<double>::quiet_NaN()};
        std::uint64_t shadow_last_enqueued_map_version_{0};
        Trajectory brake_pos_traj_{};
        Trajectory brake_yaw_traj_{};
        double brake_start_wt_{0.0};
        double brake_duration_s_{0.0};
        double brake_velocity_limit_mps_{0.0};
        std::uint64_t brake_source_generation_{0};
        std::uint64_t brake_command_revision_{0};  // protected by safety_mutex_
        double brake_yaw_{0.0};
        std::string brake_reason_{};
        // Default-off fixed-Sector ablation.  A certified stop keeps the same
        // position while yawing the vehicle so the physically limited sensor
        // can acquire a new wedge before PlanFromRest is allowed to retry.
        // Protected by safety_mutex_.
        struct ActiveYawScanState {
            bool episode_active{false};
            bool command_active{false};
            bool rotation_started{false};
            bool target_reached{false};
            bool recovery_ready{false};
            unsigned attempt{0};
            std::uint64_t episode{0};
            std::uint64_t start_map_version{0};
            std::uint64_t required_map_version{0};
            std::uint64_t start_processed_scan_count{0};
            std::uint64_t required_processed_scan_count{0};
            double goal_bearing{0.0};
            double start_yaw{0.0};
            double target_yaw{0.0};
            double start_wt{0.0};
            double settle_not_before_wt{0.0};
        } active_yaw_scan_;
        std::uint64_t active_yaw_scan_arms_{0};
        std::uint64_t active_yaw_scan_map_acks_{0};
        // A fresh current-body hazard may shorten one already-active brake.
        // Limit this to one replacement per episode to prevent 10 Hz verdicts
        // from continually resetting the stop trajectory.
        bool active_brake_body_replaced_{false};
        Vec3f brake_stop_position_{Vec3f::Zero()};
        Vec3f brake_stability_anchor_{Vec3f::Zero()};
        double brake_stability_start_wt_{0.0};
        bool brake_stability_started_{false};
        double brake_recovery_last_attempt_wt_{-
                std::numeric_limits<double>::infinity()};
        double brake_activation_retry_last_wt_{-
                std::numeric_limits<double>::infinity()};
        Vec3f brake_passive_stability_anchor_{Vec3f::Zero()};
        double brake_passive_stability_start_wt_{0.0};
        bool brake_passive_stability_started_{false};
        std::atomic_bool trajectory_guard_recovery_announced_{false};
        // A certified PlanFromRest path may intentionally begin inside the
        // conservative inflated clearance margin and prove a bounded escape
        // from it. Keep the front-end in Full acquisition until that escape
        // prefix has actually executed and a current, ordinary (non-escape)
        // certificate covers the vehicle. Closing Full when the path is only
        // committed exposes the prefix to a Sector-updated map and can
        // immediately fail-close before the vehicle has moved.
        // Protected by safety_mutex_.
        bool recovery_escape_hold_pending_{false};
        std::uint64_t recovery_escape_hold_generation_{0};
        double recovery_escape_hold_release_wt_{-
                std::numeric_limits<double>::infinity()};
        // Protected by brake_activation_mutex_. This is only the pre-first-path
        // state-selection failure, not an alternative active-brake completion.
        std::uint64_t brake_activation_revision_{0};
        bool startup_recovery_pending_{false};

        struct AsyncRecoveryRequest {
            async_recovery::Identity identity;
            Vec3f goal{Vec3f::Zero()};
            double goal_yaw{NAN};
            bool new_goal{false};
        };
        struct AsyncRecoveryResult {
            AsyncRecoveryRequest request;
            int ret_code{super_utils::FAILED};
            bool goal_valid{false}, rejected{true}, computed{false};
            std::uint64_t generation_after{0};
        };
        async_recovery::SingleFlight<AsyncRecoveryRequest, AsyncRecoveryResult>
                async_recovery_slot_;
        std::uint64_t async_recovery_next_id_{0};  // main-callback-owned
        std::uint64_t async_recovery_dispatched_{0}, async_recovery_completed_{0},
                async_recovery_discarded_{0};

        static bool asyncCertifiedRecoveryEnabled() {
            static const bool enabled = async_recovery::enabledSetting(
                    std::getenv("SUPER_ASYNC_CERTIFIED_RECOVERY"));
            return enabled;
        }

        static bool asyncGenerateSettingEnabled() {
            static const bool enabled = async_from_rest::enabledSetting(
                    std::getenv("SUPER_ASYNC_GENERATE_TRAJ"));
            return enabled;
        }

        bool asyncGenerateEnabled() const {
            return asyncGenerateSettingEnabled() && cfg_.trajectory_guard_en;
        }

        static bool stoppedDepartureV4SettingEnabled() {
            static const bool enabled = async_from_rest::enabledSetting(
                    std::getenv("SUPER_STOPPED_DEPARTURE_V4"));
            return enabled;
        }

        bool stoppedDepartureV4Enabled() const {
            return stoppedDepartureV4SettingEnabled() &&
                    asyncGenerateEnabled() &&
                    asyncCertifiedRecoveryEnabled();
        }

        static bool stoppedHoldV5SettingEnabled() {
            static const bool enabled = async_from_rest::enabledSetting(
                    std::getenv("SUPER_STOPPED_HOLD_V5"));
            return enabled;
        }

        bool stoppedHoldV5Enabled() const {
            return stoppedHoldV5SettingEnabled() &&
                    stoppedDepartureV4Enabled();
        }

        static bool goalChangeFullRefreshV6SettingEnabled() {
            static const bool enabled = async_from_rest::enabledSetting(
                    std::getenv("SUPER_GOAL_CHANGE_FULL_REFRESH_V6"));
            return enabled;
        }

        bool goalChangeFullRefreshV6Enabled() const {
            return goalChangeFullRefreshV6SettingEnabled() &&
                    cfg_.event_recovery_en && stoppedDepartureV4Enabled();
        }

        static bool activeYawScanSettingEnabled() {
            static const bool enabled = active_yaw_scan::enabledSetting(
                    std::getenv("SUPER_SECTOR_ACTIVE_YAW_SCAN"));
            return enabled;
        }

        bool activeYawScanEnabled() const {
            return activeYawScanSettingEnabled() &&
                    !cfg_.event_recovery_en && stoppedDepartureV4Enabled();
        }

        void onGoalQueuedLocked(const bool distinct_identity) override {
            if (!distinct_identity) return;
            if (activeYawScanEnabled()) {
                auto request = active_yaw_scan_goal_requested_.fetch_add(
                        1, std::memory_order_acq_rel) + 1;
                if (request == 0) {
                    active_yaw_scan_goal_requested_.store(
                            1, std::memory_order_release);
                }
            }
            if (goalChangeFullRefreshV6Enabled() &&
                machine_state_.load(std::memory_order_acquire) == FOLLOW_TRAJ) {
                auto request = goal_change_full_refresh_requested_.fetch_add(
                        1, std::memory_order_acq_rel) + 1;
                if (request == 0) {
                    goal_change_full_refresh_requested_.store(
                            1, std::memory_order_release);
                }
            }
        }

        void refreshMainRobotState() override {
            if (asyncGenerateEnabled() &&
                async_generate_quarantine_.load(std::memory_order_acquire)) {
                robot_state_ = map_ptr_->getRobotState();
            } else {
                planner_ptr_->getRobotState(robot_state_);
            }
        }

        struct AsyncGenerateRequest {
            async_from_rest::Identity identity;
            Vec3f goal{Vec3f::Zero()};
            double goal_yaw{NAN};
            bool new_goal{false};
            goal_retransmit::Request raw_goal;
            startup_recovery::Before startup;
        };
        struct AsyncGenerateResult {
            AsyncGenerateRequest request;
            int ret_code{super_utils::FAILED};
            bool computed{false}, goal_valid{false}, rejected{true};
            std::uint64_t generation_after{0};
            const char* reason{"dispatch_not_eligible"};
        };
        async_recovery::SingleFlight<AsyncGenerateRequest, AsyncGenerateResult>
                async_generate_slot_;
        std::uint64_t async_generate_next_id_{0}, async_generate_requests_{0},
                async_generate_completed_{0}, async_generate_discarded_{0};
        // Quarantine outlives a discarded slot because PlanFromRest commits
        // internally. Only main's certified publication transaction releases it.
        std::atomic_bool async_generate_quarantine_{false};
        // Following hold/request fields are protected by safety_mutex_.
        std::uint64_t async_generate_hold_revision_{0};
        CmdTraj::SharedSnapshot async_generate_previous_;
        CmdTraj::Sample async_generate_hold_sample_;
        Trajectory async_generate_hold_geometry_;
        TrajectorySafetyResult async_generate_hold_certificate_;
        bool async_generate_hold_certificate_valid_{false};
        double async_generate_hold_since_{0.0};
        std::optional<AsyncGenerateRequest> async_generate_request_identity_;
        std::uint64_t async_generate_exact_replays_{0};

        struct RefreshProcessAck {
            std::uint64_t stamp_ns{0};
            std::uint64_t map_version{0};
        };

        mutable std::mutex full_refresh_mutex_;
        bool full_refresh_gate_advertised_{false};
        std::uint64_t latest_full_refresh_request_seq_{0};
        std::uint64_t latest_full_refresh_request_stamp_ns_{0};
        bool latest_full_refresh_request_acked_{false};
        rog_map::MapHealthClock::time_point
                full_refresh_unacked_since_time_{};
        std::uint64_t full_refresh_timeout_handled_seq_{0};
        std::uint64_t required_full_refresh_min_seq_{0};
        std::uint64_t required_full_refresh_target_seq_{0};
        std::uint64_t required_full_refresh_stamp_ns_{0};
        std::uint64_t required_full_refresh_ack_map_version_{0};
        bool required_full_refresh_acked_{false};
        std::deque<RefreshProcessAck> recent_refresh_process_acks_;

        bool findRefreshAckLocked(const std::uint64_t stamp_ns,
                                  std::uint64_t &map_version) const {
            for (auto it = recent_refresh_process_acks_.rbegin();
                 it != recent_refresh_process_acks_.rend(); ++it) {
                if (it->stamp_ns == stamp_ns) {
                    map_version = it->map_version;
                    return true;
                }
            }
            return false;
        }

        void armFullRefreshRecoveryGate() {
            if (cfg_.trajectory_guard_full_refresh_ack_sla_s <= 0.0) {
                return;
            }
            const auto event_map_version = cfg_.event_recovery_en
                    ? map_ptr_->getMapHealthSnapshot().map_version : 0;
            std::lock_guard<std::mutex> lock(full_refresh_mutex_);
            if (!full_refresh_gate_advertised_ && !cfg_.event_recovery_en) {
                return;
            }
            event_recovery_min_map_version_ = event_map_version;
            if (cfg_.event_recovery_en)
                event_recovery_not_before_stamp_ns_ = nh_->get_clock()->now().nanoseconds();
            required_full_refresh_min_seq_ =
                    latest_full_refresh_request_seq_ + 1;
            required_full_refresh_target_seq_ = 0;
            required_full_refresh_stamp_ns_ = 0;
            required_full_refresh_ack_map_version_ = 0;
            required_full_refresh_acked_ = false;
            ros_ptr_->info(
                    " -- [FULL_REFRESH_RECOVERY_GATE_ARM] min_request_seq={}",
                    required_full_refresh_min_seq_);
        }

        void clearFullRefreshRecoveryGateLocked() {
            required_full_refresh_min_seq_ = 0;
            required_full_refresh_target_seq_ = 0;
            required_full_refresh_stamp_ns_ = 0;
            required_full_refresh_ack_map_version_ = 0;
            required_full_refresh_acked_ = false;
        }

        void clearFullRefreshRecoveryGate() {
            std::lock_guard<std::mutex> lock(full_refresh_mutex_);
            clearFullRefreshRecoveryGateLocked();
        }

        void fullRefreshRequestCallback(
                const std_msgs::msg::UInt64MultiArray::SharedPtr msg) {
            if (msg->data.size() < 3) {
                ros_ptr_->warn(
                        " -- [FULL_REFRESH_REQUEST] malformed size={}",
                        msg->data.size());
                return;
            }
            const std::uint64_t request_seq = msg->data[0];
            const std::uint64_t stamp_ns = msg->data[1];
            bool target_selected = false;
            bool target_acked = false;
            std::uint64_t target_map_version = 0;
            {
                std::lock_guard<std::mutex> lock(full_refresh_mutex_);
                full_refresh_gate_advertised_ = true;
                if (request_seq == 0 ||
                    request_seq <= latest_full_refresh_request_seq_) {
                    return;
                }
                if (cfg_.event_recovery_en && required_full_refresh_min_seq_ != 0 &&
                    stamp_ns <= event_recovery_not_before_stamp_ns_) {
                    return;  // Delayed Full token from an earlier recovery cycle.
                }
                const bool unresolved_chain_active =
                        latest_full_refresh_request_seq_ != 0 &&
                        !latest_full_refresh_request_acked_;
                if (!unresolved_chain_active) {
                    full_refresh_unacked_since_time_ =
                            rog_map::MapHealthClock::now();
                }
                latest_full_refresh_request_seq_ = request_seq;
                latest_full_refresh_request_stamp_ns_ = stamp_ns;
                latest_full_refresh_request_acked_ =
                        findRefreshAckLocked(stamp_ns, target_map_version);
                if (required_full_refresh_min_seq_ != 0 &&
                    !required_full_refresh_acked_ &&
                    request_seq >= required_full_refresh_min_seq_) {
                    // latest-only recovery: a best-effort cloud can be lost
                    // after its reliable request token arrives. In that case
                    // a later full generation may supersede the missing one,
                    // but recovery still requires an exact ACK for the newly
                    // selected timestamp before replanning.
                    required_full_refresh_target_seq_ = request_seq;
                    required_full_refresh_stamp_ns_ = stamp_ns;
                    required_full_refresh_acked_ =
                            latest_full_refresh_request_acked_;
                    required_full_refresh_ack_map_version_ =
                            latest_full_refresh_request_acked_
                                    ? target_map_version : 0;
                    target_selected = true;
                    target_acked = required_full_refresh_acked_;
                }
            }
            if (target_selected) {
                ros_ptr_->info(
                        " -- [FULL_REFRESH_RECOVERY_TARGET] request_seq={} "
                        "stamp_ns={} already_acked={} map={}",
                        request_seq, stamp_ns, target_acked,
                        target_map_version);
            }
        }

        void cloudProcessAckCallback(
                const std_msgs::msg::UInt64MultiArray::SharedPtr msg) {
            if (msg->data.size() < 4) {
                ros_ptr_->warn(
                        " -- [CLOUD_PROCESS_ACK] malformed size={}",
                        msg->data.size());
                return;
            }
            const std::uint64_t stamp_ns = msg->data[1];
            const std::uint64_t map_version = msg->data[2];
            std::uint64_t satisfied_seq = 0;
            {
                std::lock_guard<std::mutex> lock(full_refresh_mutex_);
                // Processed is not the same as committed. Event-only recovery
                // requires a new Full observation that really advanced the map.
                if (cfg_.event_recovery_en &&
                    (msg->data[3] == 0 || map_version <= event_recovery_min_map_version_)) {
                    return;
                }
                recent_refresh_process_acks_.push_back(
                        RefreshProcessAck{stamp_ns, map_version});
                while (recent_refresh_process_acks_.size() > 64) {
                    recent_refresh_process_acks_.pop_front();
                }
                if (latest_full_refresh_request_seq_ != 0 &&
                    latest_full_refresh_request_stamp_ns_ == stamp_ns) {
                    latest_full_refresh_request_acked_ = true;
                    full_refresh_unacked_since_time_ =
                            rog_map::MapHealthClock::time_point{};
                }
                if (required_full_refresh_target_seq_ != 0 &&
                    required_full_refresh_stamp_ns_ == stamp_ns) {
                    required_full_refresh_acked_ = true;
                    required_full_refresh_ack_map_version_ = map_version;
                    satisfied_seq = required_full_refresh_target_seq_;
                }
            }
            if (satisfied_seq != 0) {
                ros_ptr_->info(
                        " -- [FULL_REFRESH_RECOVERY_ACK] request_seq={} "
                        "stamp_ns={} map={} committed={}",
                        satisfied_seq, stamp_ns, map_version, msg->data[3]);
            }
        }

        bool fullRefreshRecoveryGateSatisfied(
                const rog_map::MapHealthSnapshot &health) const {
            std::lock_guard<std::mutex> lock(full_refresh_mutex_);
            if (required_full_refresh_min_seq_ == 0) {
                return true;
            }
            return required_full_refresh_target_seq_ >=
                           required_full_refresh_min_seq_ &&
                    required_full_refresh_acked_ &&
                    health.map_version >=
                           required_full_refresh_ack_map_version_;
        }

        bool consumeFullRefreshAckSlaTimeout(
                std::uint64_t &request_seq, double &age_s) {
            if (cfg_.trajectory_guard_full_refresh_ack_sla_s <= 0.0) {
                return false;
            }
            std::lock_guard<std::mutex> lock(full_refresh_mutex_);
            if (!full_refresh_gate_advertised_ ||
                latest_full_refresh_request_seq_ == 0 ||
                latest_full_refresh_request_acked_ ||
                full_refresh_timeout_handled_seq_ >=
                        latest_full_refresh_request_seq_) {
                return false;
            }
            age_s = std::chrono::duration<double>(
                    rog_map::MapHealthClock::now() -
                    full_refresh_unacked_since_time_).count();
            if (age_s < cfg_.trajectory_guard_full_refresh_ack_sla_s) {
                return false;
            }
            request_seq = latest_full_refresh_request_seq_;
            full_refresh_timeout_handled_seq_ = request_seq;
            return true;
        }

        void publishTrajectoryGuardRecoveryState(const bool active) {
            if (!trajectory_guard_recovery_pub_) {
                return;
            }
            bool expected = !active;
            if (!trajectory_guard_recovery_announced_.compare_exchange_strong(
                        expected, active, std::memory_order_acq_rel)) {
                return;
            }
            if (active) {
                armFullRefreshRecoveryGate();
            }
            std_msgs::msg::Bool message;
            message.data = active;
            trajectory_guard_recovery_pub_->publish(message);
            if (!active) {
                clearFullRefreshRecoveryGate();
            }
            ros_ptr_->info(
                    " -- [TRAJ_GUARD_RECOVERY_SIGNAL] active={}", active);
        }

        static bool needsRecoveryEscapeHold(
                const TrajectorySafetyResult &certificate,
                const CmdTraj::Sample &sample) {
            if (!certificate.safe() ||
                (!certificate.used_clearance_escape &&
                 !certificate.used_initial_footprint_egress)) {
                return false;
            }
            return std::isfinite(certificate.clearance_escape_completed_tt) &&
                    certificate.clearance_escape_completed_tt >= 0.0 &&
                    sample.trajectory_time + 1.0e-6 <
                            certificate.clearance_escape_completed_tt;
        }

        // Called from the main FSM callback after refreshSafetyCertificate
        // has accepted the current committed trajectory against the current
        // map. The Full->Sector edge is released only when the certified
        // escape prefix is in the past and the live certificate no longer
        // consumes an escape exception.
        bool tryCompleteRecoveryEscapeHold() {
            bool released = false;
            std::uint64_t generation = 0;
            std::uint64_t escape_generation = 0;
            std::uint64_t map_version = 0;
            double trajectory_time = 0.0;
            double release_wt = 0.0;
            {
                // Match the recovery-completion lock order.
                std::lock_guard<std::mutex> refresh(full_refresh_mutex_);
                std::lock_guard<std::mutex> safety(safety_mutex_);
                if (!recovery_escape_hold_pending_) return false;

                const auto snapshot =
                        planner_ptr_->getCommittedSharedTrajectorySnapshot();
                const auto health = map_ptr_->getMapHealthSnapshot();
                CmdTraj::Sample sample;
                if (snapshot.empty ||
                    !planner_ptr_->getOneCommandSample(
                            sample, snapshot.generation) ||
                    sample.finished ||
                    !sample.pvaj.array().isFinite().all() ||
                    ros_ptr_->getSimTime() + 1.0e-6 <
                            recovery_escape_hold_release_wt_ ||
                    !safety_certificate_valid_ ||
                    !safety_certificate_.safe() ||
                    safety_certificate_.trajectory_generation !=
                            snapshot.generation ||
                    safety_certificate_.map_version != health.map_version ||
                    safety_revalidation_requested_.load(
                            std::memory_order_acquire) ||
                    safety_certificate_.checked_from_tt >
                            sample.trajectory_time ||
                    safety_certificate_.checked_to_tt <
                            sample.trajectory_time ||
                    safety_certificate_.used_clearance_escape ||
                    safety_certificate_.used_initial_footprint_egress) {
                    return false;
                }

                bool expected = true;
                if (!trajectory_guard_recovery_announced_.compare_exchange_strong(
                            expected, false, std::memory_order_acq_rel)) {
                    return false;
                }
                generation = snapshot.generation;
                escape_generation = recovery_escape_hold_generation_;
                map_version = health.map_version;
                trajectory_time = sample.trajectory_time;
                release_wt = recovery_escape_hold_release_wt_;
                recovery_escape_hold_pending_ = false;
                recovery_escape_hold_generation_ = 0;
                recovery_escape_hold_release_wt_ =
                        -std::numeric_limits<double>::infinity();
                clearFullRefreshRecoveryGateLocked();
                released = true;
            }
            if (released) {
                std_msgs::msg::Bool inactive;
                inactive.data = false;
                trajectory_guard_recovery_pub_->publish(inactive);
                ros_ptr_->info(
                        " -- [EVENT_RECOVERY_ESCAPE_RELEASE] escape_gen={} "
                        "current_gen={} map={} trajectory_tt={:.3f} "
                        "release_wt={:.3f}",
                        escape_generation, generation, map_version,
                        trajectory_time, release_wt);
                ros_ptr_->info(
                        " -- [TRAJ_GUARD_RECOVERY_SIGNAL] active=false");
            }
            return released;
        }

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
        std::atomic_uint64_t raw_cloud_received_messages_total_{0};
        std::atomic_uint64_t raw_cloud_received_payload_bytes_total_{0};

        // Pulls the current window (pruned to accumulation_window_s) plus
        // health info the caller must check before trusting an empty
        // result as "open space" (theorem 1's own "sufficiently dense"
        // precondition -- see corridor_generator.cpp's
        // GeneratePolytopeFromLineAndCloud).
        void getAccumulatedCloudForShadow(
                double accumulation_window_s, double voxel_m,
                const rog_map::MapHealthClock::time_point &cutoff_time,
                vec_E<Vec3f> &out_cloud, double &time_since_last_msg_s,
                std::size_t &batch_count, std::size_t &source_point_count,
                const Vec3f *crop_min = nullptr,
                const Vec3f *crop_max = nullptr) const {
            out_cloud.clear();
            std::deque<RawCloudWindowBatch> window_copy;
            {
                std::lock_guard<std::mutex> lock(raw_cloud_window_mutex_);
                window_copy = raw_cloud_window_;
            }
            time_since_last_msg_s = std::numeric_limits<double>::infinity();
            batch_count = 0;
            source_point_count = 0;
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
            const bool downsample = voxel_m > 0.0;
            const double voxel = downsample ? std::max(0.005, voxel_m) : 1.0;
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
                        cutoff_time - batch.receive_time).count();
                if (age_s < 0.0 || age_s > accumulation_window_s ||
                    (!batch.cloud_msg && !batch.converted_cloud)) {
                    continue;
                }
                time_since_last_msg_s = std::min(
                        time_since_last_msg_s, age_s);
                ++batch_count;
                pcl::PointCloud<rog_map::PointType> converted;
                const pcl::PointCloud<rog_map::PointType> *cloud =
                        batch.converted_cloud.get();
                if (!cloud) {
                    pcl::fromROSMsg(*batch.cloud_msg, converted);
                    cloud = &converted;
                }
                source_point_count += cloud->size();
                for (const auto &pt : *cloud) {
                    const Vec3f p(pt.x, pt.y, pt.z);
                    if (crop_min && crop_max &&
                        ((p.array() < crop_min->array()).any() ||
                         (p.array() > crop_max->array()).any())) {
                        continue;
                    }
                    if (!downsample ||
                        seen_voxels.insert(voxel_key(p)).second) {
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
            std::size_t source_point_count{0};
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
                    cfg_.trajectory_guard_raw_cloud_accum_window_s,
                    cfg_.trajectory_guard_raw_cloud_ciri_voxel_m,
                    rog_map::MapHealthClock::now(), out.cloud,
                    out.latest_cloud_age_s, out.batch_count,
                    out.source_point_count);
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

        // Shadow-only recent-hit witness for the committed body and a bounded
        // short tail. This is deliberately simpler than the paper-faithful
        // CIRI experiment: an observed raw point either intersects the body
        // radius or it does not. The check runs on an as-of-enqueue cloud
        // window so a result cannot be explained by a scan received after the
        // candidate was committed.
        enum class NearFieldShadowStatus {
            DISABLED,
            STALE,
            INSUFFICIENT_DATA,
            EMPTY_TRAJECTORY,
            NO_HIT,
            EGRESS,
            OCCUPIED
        };

        static const char *nearFieldShadowStatusName(
                const NearFieldShadowStatus status) {
            switch (status) {
                case NearFieldShadowStatus::DISABLED: return "DISABLED";
                case NearFieldShadowStatus::STALE: return "STALE";
                case NearFieldShadowStatus::INSUFFICIENT_DATA:
                    return "INSUFFICIENT_DATA";
                case NearFieldShadowStatus::EMPTY_TRAJECTORY:
                    return "EMPTY_TRAJECTORY";
                case NearFieldShadowStatus::NO_HIT: return "NO_HIT";
                case NearFieldShadowStatus::EGRESS: return "EGRESS";
                case NearFieldShadowStatus::OCCUPIED: return "OCCUPIED";
            }
            return "UNKNOWN";
        }

        struct NearFieldShadowJob {
            std::uint64_t request_id{0};
            std::uint64_t generation{0};
            std::uint64_t cloud_sequence{0};
            std::string trigger;
            Trajectory candidate;
            double checked_from_tt{0.0};
            double checked_to_tt{0.0};
            rog_map::MapHealthClock::time_point enqueue_time{};
        };

        struct NearFieldShadowResult {
            std::uint64_t request_id{0};
            std::uint64_t generation{0};
            std::uint64_t cloud_sequence{0};
            NearFieldShadowStatus status{NearFieldShadowStatus::DISABLED};
            Vec3f witness_position{Vec3f::Zero()};
            double witness_tt{-1.0};
            double minimum_distance_m{
                    std::numeric_limits<double>::infinity()};
            double body_distance_m{
                    std::numeric_limits<double>::infinity()};
            double end_distance_m{
                    std::numeric_limits<double>::infinity()};
            double checked_from_tt{0.0};
            double checked_to_tt{0.0};
            rog_map::MapHealthClock::time_point completion_time{};
        };

        mutable std::mutex near_field_shadow_worker_mutex_;
        std::condition_variable near_field_shadow_worker_cv_;
        std::optional<NearFieldShadowJob> pending_near_field_shadow_job_;
        std::optional<NearFieldShadowResult> latest_near_field_shadow_result_;
        std::optional<NearFieldShadowResult>
                pending_near_field_shadow_occupied_result_;
        bool stop_near_field_shadow_worker_{false};
        std::thread near_field_shadow_worker_;
        std::uint64_t next_near_field_shadow_request_id_{1};
        std::uint64_t near_field_shadow_last_enqueued_generation_{0};
        std::uint64_t near_field_shadow_last_enqueued_cloud_sequence_{0};
        rog_map::MapHealthClock::time_point
                near_field_shadow_last_enqueue_time_{};
        std::atomic_uint64_t near_field_shadow_no_hit_total_{0};
        std::atomic_uint64_t near_field_shadow_occupied_total_{0};
        std::atomic_uint64_t near_field_shadow_egress_total_{0};
        std::atomic_uint64_t near_field_shadow_unavailable_total_{0};
        std::atomic_bool near_field_shadow_test_replay_injected_{false};

        std::uint64_t enqueueNearFieldShadowCheck(
                const std::string &trigger, const std::uint64_t generation,
                const std::uint64_t cloud_sequence, Trajectory candidate,
                const double checked_from_tt,
                const rog_map::MapHealthClock::time_point enqueue_time) {
            if (!cfg_.trajectory_guard_raw_cloud_near_field_shadow_en ||
                candidate.empty() || generation == 0) {
                return 0;
            }
            const double checked_to_tt = std::min(
                    candidate.getTotalDuration(),
                    checked_from_tt +
                            cfg_.trajectory_guard_raw_cloud_near_field_horizon_s);
            std::optional<std::uint64_t> replaced_request;
            std::uint64_t request_id;
            {
                std::lock_guard<std::mutex> lock(
                        near_field_shadow_worker_mutex_);
                request_id = next_near_field_shadow_request_id_++;
                if (pending_near_field_shadow_job_) {
                    replaced_request =
                            pending_near_field_shadow_job_->request_id;
                }
                pending_near_field_shadow_job_ = NearFieldShadowJob{
                        request_id, generation, cloud_sequence, trigger,
                        std::move(candidate), checked_from_tt,
                        checked_to_tt,
                        enqueue_time};
            }
            if (replaced_request) {
                ros_ptr_->info(
                        " -- [TRAJ_GUARD_NEAR_FIELD_SHADOW_SKIPPED] "
                        "request={} reason=LATEST_ONLY replacement={}",
                        *replaced_request, request_id);
            }
            near_field_shadow_worker_cv_.notify_one();
            return request_id;
        }

        void enqueueCommittedNearFieldShadowIfNeeded() {
            if (!cfg_.trajectory_guard_raw_cloud_near_field_shadow_en) {
                return;
            }
            const auto snapshot =
                    planner_ptr_->getCommittedTrajectorySnapshot();
            if (snapshot.empty || snapshot.pos_traj.empty() ||
                snapshot.generation == 0) {
                return;
            }
            std::uint64_t cloud_sequence = 0;
            {
                std::lock_guard<std::mutex> lock(raw_cloud_mutex_);
                cloud_sequence = raw_cloud_snapshot_.sequence;
            }
            const auto now = rog_map::MapHealthClock::now();
            const bool new_generation = snapshot.generation !=
                    near_field_shadow_last_enqueued_generation_;
            const bool new_scan = cloud_sequence != 0 &&
                    cloud_sequence !=
                            near_field_shadow_last_enqueued_cloud_sequence_;
            const double since_last_enqueue_s =
                    near_field_shadow_last_enqueue_time_.time_since_epoch()
                                    .count() == 0
                            ? std::numeric_limits<double>::infinity()
                            : std::chrono::duration<double>(
                                      now - near_field_shadow_last_enqueue_time_)
                                      .count();
            if (!new_generation &&
                (!new_scan || since_last_enqueue_s <
                         cfg_.trajectory_guard_raw_cloud_near_field_min_interval_s)) {
                return;
            }
            const double checked_from_tt = std::clamp(
                    ros_ptr_->getSimTime() - snapshot.start_wt,
                    0.0, snapshot.pos_traj.getTotalDuration());
            if (enqueueNearFieldShadowCheck(
                        new_generation ? "NEW_GENERATION" : "NEW_SCAN",
                        snapshot.generation, cloud_sequence,
                        snapshot.pos_traj, checked_from_tt, now) == 0) {
                return;
            }
            near_field_shadow_last_enqueued_generation_ =
                    snapshot.generation;
            near_field_shadow_last_enqueued_cloud_sequence_ = cloud_sequence;
            near_field_shadow_last_enqueue_time_ = now;
        }

        NearFieldShadowStatus checkCandidateAgainstNearFieldCloud(
                const vec_E<Vec3f> &cloud, const double latest_cloud_age_s,
                const std::size_t source_point_count,
                const Trajectory &candidate, const double checked_from_tt,
                Vec3f &witness_position, double &witness_tt,
                double &minimum_distance_m, double &body_distance_m,
                double &end_distance_m, double &tree_ms,
                double &query_ms) const {
            tree_ms = 0.0;
            query_ms = 0.0;
            minimum_distance_m = std::numeric_limits<double>::infinity();
            body_distance_m = std::numeric_limits<double>::infinity();
            end_distance_m = std::numeric_limits<double>::infinity();
            witness_tt = -1.0;
            if (!cfg_.trajectory_guard_raw_cloud_near_field_shadow_en) {
                return NearFieldShadowStatus::DISABLED;
            }
            if (!std::isfinite(latest_cloud_age_s) ||
                latest_cloud_age_s < 0.0 ||
                latest_cloud_age_s >
                        cfg_.trajectory_guard_raw_cloud_max_age_s) {
                return NearFieldShadowStatus::STALE;
            }
            if (candidate.empty()) {
                return NearFieldShadowStatus::EMPTY_TRAJECTORY;
            }
            const double total_duration = candidate.getTotalDuration();
            const double from_tt = std::clamp(
                    checked_from_tt, 0.0, total_duration);
            const double to_tt = std::min(
                    total_duration,
                    from_tt +
                            cfg_.trajectory_guard_raw_cloud_near_field_horizon_s);
            const double sample_dt =
                    cfg_.trajectory_guard_raw_cloud_near_field_sample_dt_s;
            const double clearance =
                    cfg_.trajectory_guard_raw_cloud_near_field_clearance_m;
            if (static_cast<int>(source_point_count) <
                cfg_.trajectory_guard_raw_cloud_near_field_min_points) {
                return NearFieldShadowStatus::INSUFFICIENT_DATA;
            }
            // An empty crop means no observed hit can intersect any of the
            // sampled body spheres. Global source density was checked above;
            // this is a one-sided hit witness, not a known-free certificate.
            if (cloud.empty()) {
                return NearFieldShadowStatus::NO_HIT;
            }

            const auto tree_start = rog_map::MapHealthClock::now();
            auto pcl_cloud = std::make_shared<
                    pcl::PointCloud<rog_map::PointType>>();
            pcl_cloud->reserve(cloud.size());
            for (const auto &point : cloud) {
                rog_map::PointType pcl_point;
                pcl_point.x = static_cast<float>(point.x());
                pcl_point.y = static_cast<float>(point.y());
                pcl_point.z = static_cast<float>(point.z());
                pcl_point.intensity = 0.0F;
                pcl_cloud->push_back(pcl_point);
            }
            pcl_cloud->width = static_cast<std::uint32_t>(pcl_cloud->size());
            pcl_cloud->height = 1;
            pcl_cloud->is_dense = true;
            pcl::KdTreeFLANN<rog_map::PointType> tree;
            tree.setInputCloud(pcl_cloud);
            tree_ms = std::chrono::duration<double, std::milli>(
                    rog_map::MapHealthClock::now() - tree_start).count();

            std::vector<int> indices(1);
            std::vector<float> squared_distances(1);
            const auto query_start = rog_map::MapHealthClock::now();
            bool first_sample = true;
            bool body_starts_inside = false;
            bool egress_exited_clearance = false;
            double previous_distance_m =
                    std::numeric_limits<double>::infinity();
            for (double tt = from_tt;;
                 tt = std::min(to_tt, tt + sample_dt)) {
                const Vec3f position = candidate.getPos(tt);
                if (!position.array().isFinite().all()) {
                    witness_position = position;
                    witness_tt = tt;
                    query_ms = std::chrono::duration<double, std::milli>(
                            rog_map::MapHealthClock::now() - query_start)
                                       .count();
                    return NearFieldShadowStatus::OCCUPIED;
                }
                rog_map::PointType query;
                query.x = static_cast<float>(position.x());
                query.y = static_cast<float>(position.y());
                query.z = static_cast<float>(position.z());
                query.intensity = 0.0F;
                if (tree.nearestKSearch(
                            query, 1, indices, squared_distances) > 0) {
                    const double distance = std::sqrt(std::max(
                            0.0F, squared_distances.front()));
                    minimum_distance_m = std::min(
                            minimum_distance_m, distance);
                    end_distance_m = distance;
                    if (first_sample) {
                        body_distance_m = distance;
                        body_starts_inside = distance <= clearance;
                        if (body_starts_inside) {
                            witness_position = position;
                            witness_tt = tt;
                        }
                    } else if (body_starts_inside &&
                               !egress_exited_clearance &&
                               distance +
                                       cfg_.trajectory_guard_raw_cloud_near_field_egress_tolerance_m <
                                       previous_distance_m) {
                        // Once the body sphere already contains a hit, only
                        // a distance-monotonic escape is allowed. Moving
                        // closer again (including toward a different nearest
                        // hit) is conservatively blocked.
                        witness_position = position;
                        witness_tt = tt;
                        query_ms =
                                std::chrono::duration<double, std::milli>(
                                        rog_map::MapHealthClock::now() -
                                        query_start).count();
                        return NearFieldShadowStatus::OCCUPIED;
                    } else if (body_starts_inside &&
                               egress_exited_clearance &&
                               distance <= clearance) {
                        // A path may curve after it has cleared the witness;
                        // only an actual re-entry into the body radius is a
                        // new hazard beyond that point.
                        witness_position = position;
                        witness_tt = tt;
                        query_ms =
                                std::chrono::duration<double, std::milli>(
                                        rog_map::MapHealthClock::now() -
                                        query_start).count();
                        return NearFieldShadowStatus::OCCUPIED;
                    } else if (!body_starts_inside && distance <= clearance) {
                        witness_position = position;
                        witness_tt = tt;
                        query_ms =
                                std::chrono::duration<double, std::milli>(
                                        rog_map::MapHealthClock::now() -
                                        query_start).count();
                        return NearFieldShadowStatus::OCCUPIED;
                    }
                    if (body_starts_inside &&
                        !egress_exited_clearance &&
                        distance > clearance +
                                cfg_.trajectory_guard_raw_cloud_near_field_egress_tolerance_m) {
                        egress_exited_clearance = true;
                    }
                    previous_distance_m = distance;
                }
                first_sample = false;
                if (tt >= to_tt) {
                    break;
                }
            }
            query_ms = std::chrono::duration<double, std::milli>(
                    rog_map::MapHealthClock::now() - query_start).count();
            if (body_starts_inside) {
                const bool made_progress = std::isfinite(body_distance_m) &&
                        std::isfinite(end_distance_m) &&
                        end_distance_m - body_distance_m >=
                                cfg_.trajectory_guard_raw_cloud_near_field_egress_min_progress_m;
                return made_progress && egress_exited_clearance
                        ? NearFieldShadowStatus::EGRESS
                        : NearFieldShadowStatus::OCCUPIED;
            }
            return NearFieldShadowStatus::NO_HIT;
        }

        void nearFieldShadowWorkerLoop() {
            while (true) {
                NearFieldShadowJob job;
                {
                    std::unique_lock<std::mutex> lock(
                            near_field_shadow_worker_mutex_);
                    near_field_shadow_worker_cv_.wait(lock, [this] {
                        return stop_near_field_shadow_worker_ ||
                               pending_near_field_shadow_job_.has_value();
                    });
                    if (stop_near_field_shadow_worker_) {
                        return;
                    }
                    job = std::move(*pending_near_field_shadow_job_);
                    pending_near_field_shadow_job_.reset();
                }

                const auto work_start = rog_map::MapHealthClock::now();
                vec_E<Vec3f> cloud;
                double latest_cloud_age_s =
                        std::numeric_limits<double>::infinity();
                std::size_t batch_count = 0;
                std::size_t source_point_count = 0;
                const double candidate_total_duration =
                        job.candidate.getTotalDuration();
                const double crop_from_tt = std::clamp(
                        job.checked_from_tt, 0.0,
                        candidate_total_duration);
                const double crop_to_tt = std::min(
                        candidate_total_duration,
                        crop_from_tt +
                                cfg_.trajectory_guard_raw_cloud_near_field_horizon_s);
                Vec3f crop_min = job.candidate.getPos(crop_from_tt);
                Vec3f crop_max = crop_min;
                const double crop_sample_dt =
                        cfg_.trajectory_guard_raw_cloud_near_field_sample_dt_s;
                for (double tt = crop_from_tt;;
                     tt = std::min(crop_to_tt, tt + crop_sample_dt)) {
                    const Vec3f position = job.candidate.getPos(tt);
                    crop_min = crop_min.cwiseMin(position);
                    crop_max = crop_max.cwiseMax(position);
                    if (tt >= crop_to_tt) {
                        break;
                    }
                }
                const Vec3f crop_padding = Vec3f::Constant(
                        cfg_.trajectory_guard_raw_cloud_near_field_clearance_m);
                crop_min -= crop_padding;
                crop_max += crop_padding;
                const auto accumulation_start =
                        rog_map::MapHealthClock::now();
                getAccumulatedCloudForShadow(
                        cfg_.trajectory_guard_raw_cloud_accum_window_s,
                        cfg_.trajectory_guard_raw_cloud_near_field_voxel_m,
                        job.enqueue_time, cloud, latest_cloud_age_s,
                        batch_count, source_point_count, &crop_min, &crop_max);
                const double accumulation_ms =
                        std::chrono::duration<double, std::milli>(
                                rog_map::MapHealthClock::now() -
                                accumulation_start).count();
                const int replay_mode =
                        cfg_.trajectory_guard_raw_cloud_near_field_test_replay_mode;
                if (replay_mode != 0 &&
                    !near_field_shadow_test_replay_injected_.exchange(
                            true, std::memory_order_acq_rel)) {
                    const double replay_tt = replay_mode == 1
                            ? std::min(crop_to_tt, crop_from_tt + 0.25)
                            : crop_from_tt;
                    const Vec3f replay_point = job.candidate.getPos(replay_tt);
                    cloud.push_back(replay_point);
                    ros_ptr_->warn(
                            " -- [TRAJ_GUARD_NEAR_FIELD_TEST_REPLAY] "
                            "request={} gen={} cloud_seq={} mode={} tt={:.3f} "
                            "p=[{:.3f},{:.3f},{:.3f}]",
                            job.request_id, job.generation,
                            job.cloud_sequence,
                            replay_mode == 1 ? "FUTURE_TAIL" : "BODY",
                            replay_tt, replay_point.x(), replay_point.y(),
                            replay_point.z());
                }
                Vec3f witness_position = Vec3f::Zero();
                double witness_tt = -1.0;
                double minimum_distance_m =
                        std::numeric_limits<double>::infinity();
                double body_distance_m =
                        std::numeric_limits<double>::infinity();
                double end_distance_m =
                        std::numeric_limits<double>::infinity();
                double tree_ms = 0.0;
                double query_ms = 0.0;
                const auto status = checkCandidateAgainstNearFieldCloud(
                        cloud, latest_cloud_age_s, source_point_count,
                        job.candidate,
                        job.checked_from_tt, witness_position, witness_tt,
                        minimum_distance_m, body_distance_m,
                        end_distance_m, tree_ms, query_ms);
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
                            near_field_shadow_worker_mutex_);
                    const NearFieldShadowResult result{
                            job.request_id, job.generation,
                            job.cloud_sequence, status,
                            witness_position, witness_tt,
                            minimum_distance_m, body_distance_m,
                            end_distance_m, job.checked_from_tt,
                            job.checked_to_tt, completion_time};
                    latest_near_field_shadow_result_ = result;
                    // Preserve an OCCUPIED event until the 100 Hz FSM has
                    // consumed it. A later NO_HIT must not erase a hazard
                    // merely because the worker completed twice in one tick.
                    if (status == NearFieldShadowStatus::OCCUPIED &&
                        !pending_near_field_shadow_occupied_result_) {
                        pending_near_field_shadow_occupied_result_ = result;
                    }
                }
                if (status == NearFieldShadowStatus::NO_HIT) {
                    near_field_shadow_no_hit_total_.fetch_add(
                            1, std::memory_order_relaxed);
                } else if (status == NearFieldShadowStatus::OCCUPIED) {
                    near_field_shadow_occupied_total_.fetch_add(
                            1, std::memory_order_relaxed);
                } else if (status == NearFieldShadowStatus::EGRESS) {
                    near_field_shadow_egress_total_.fetch_add(
                            1, std::memory_order_relaxed);
                } else {
                    near_field_shadow_unavailable_total_.fetch_add(
                            1, std::memory_order_relaxed);
                }
                ros_ptr_->warn(
                        " -- [TRAJ_GUARD_NEAR_FIELD_SHADOW_RESULT] "
                        "request={} gen={} cloud_seq={} trigger={} status={} crop_pts={} "
                        "source_pts={} batches={} cloud_age={:.3f}s from_tt={:.3f} "
                        "to_tt={:.3f} min_dist={:.4f}m body_dist={:.4f}m "
                        "end_dist={:.4f}m witness_tt={:.3f} "
                        "p=[{:.3f},{:.3f},{:.3f}] queue_ms={:.3f} "
                        "accum_ms={:.3f} tree_ms={:.3f} query_ms={:.3f} "
                        "total_ms={:.3f}",
                        job.request_id, job.generation, job.cloud_sequence,
                        job.trigger,
                        nearFieldShadowStatusName(status), cloud.size(),
                        source_point_count, batch_count, latest_cloud_age_s,
                        job.checked_from_tt, job.checked_to_tt,
                        minimum_distance_m, body_distance_m,
                        end_distance_m, witness_tt,
                        witness_position.x(), witness_position.y(),
                        witness_position.z(), queue_ms, accumulation_ms,
                        tree_ms, query_ms, total_ms);
            }
        }

        bool consumeFreshNearFieldOccupiedResult() {
            if (!cfg_.trajectory_guard_raw_cloud_near_field_enforce_en) {
                return false;
            }
            std::optional<NearFieldShadowResult> result;
            {
                std::lock_guard<std::mutex> lock(
                        near_field_shadow_worker_mutex_);
                if (!pending_near_field_shadow_occupied_result_) {
                    return false;
                }
                result = *pending_near_field_shadow_occupied_result_;
                pending_near_field_shadow_occupied_result_.reset();
            }
            const auto snapshot =
                    planner_ptr_->getCommittedTrajectorySnapshot();
            std::uint64_t current_cloud_sequence = 0;
            {
                std::lock_guard<std::mutex> lock(raw_cloud_mutex_);
                current_cloud_sequence = raw_cloud_snapshot_.sequence;
            }
            const auto now = rog_map::MapHealthClock::now();
            const double result_age_s = std::chrono::duration<double>(
                    now - result->completion_time).count();
            const double current_tt = snapshot.empty ||
                                              snapshot.pos_traj.empty()
                    ? std::numeric_limits<double>::infinity()
                    : std::clamp(
                              ros_ptr_->getSimTime() - snapshot.start_wt,
                              0.0, snapshot.pos_traj.getTotalDuration());
            const bool generation_matches = !snapshot.empty &&
                    snapshot.generation == result->generation;
            const bool result_is_fresh = std::isfinite(result_age_s) &&
                    result_age_s >= 0.0 &&
                    result_age_s <=
                            cfg_.trajectory_guard_raw_cloud_near_field_result_max_age_s;
            const bool sequence_is_current = result->cloud_sequence != 0 &&
                    current_cloud_sequence >= result->cloud_sequence &&
                    current_cloud_sequence - result->cloud_sequence <=
                            static_cast<std::uint64_t>(
                                    cfg_.trajectory_guard_raw_cloud_near_field_max_sequence_lag);
            const double tt_tolerance = 2.0 *
                    cfg_.trajectory_guard_raw_cloud_near_field_sample_dt_s;
            const bool time_is_covered = std::isfinite(current_tt) &&
                    current_tt + tt_tolerance >= result->checked_from_tt &&
                    current_tt <= result->checked_to_tt + tt_tolerance;
            if (!generation_matches || !result_is_fresh ||
                !sequence_is_current || !time_is_covered) {
                ros_ptr_->warn(
                        " -- [TRAJ_GUARD_NEAR_FIELD_ENFORCE] action=IGNORE "
                        "request={} result_gen={} current_gen={} "
                        "result_seq={} current_seq={} age={:.3f}s "
                        "result_tt=[{:.3f},{:.3f}] current_tt={:.3f} "
                        "generation_match={} fresh={} sequence_current={} "
                        "time_covered={}",
                        result->request_id, result->generation,
                        snapshot.generation, result->cloud_sequence,
                        current_cloud_sequence, result_age_s,
                        result->checked_from_tt, result->checked_to_tt,
                        current_tt, generation_matches, result_is_fresh,
                        sequence_is_current, time_is_covered);
                return false;
            }
            ros_ptr_->error(
                    " -- [TRAJ_GUARD_NEAR_FIELD_ENFORCE] action=BRAKE "
                    "request={} gen={} cloud_seq={} age={:.3f}s "
                    "current_tt={:.3f} witness_tt={:.3f} "
                    "min_dist={:.4f}m body_dist={:.4f}m end_dist={:.4f}m",
                    result->request_id, result->generation,
                    result->cloud_sequence, result_age_s, current_tt,
                    result->witness_tt, result->minimum_distance_m,
                    result->body_distance_m, result->end_distance_m);
            return true;
        }

        mutable std::mutex frontend_risk_mutex_;
        mars_quadrotor_msgs::msg::TrajectoryRiskVerdict::SharedPtr
                pending_frontend_occupied_verdict_;
        mars_quadrotor_msgs::msg::TrajectoryRiskVerdict::SharedPtr
                pending_frontend_body_occupied_verdict_;
        uint64_t frontend_body_latest_clear_request_id_{0};
        uint64_t frontend_risk_latest_occupied_request_id_{0};
        uint64_t frontend_body_latest_occupied_request_id_{0};
        std::atomic_uint64_t frontend_risk_received_total_{0};
        std::atomic_uint64_t frontend_risk_occupied_total_{0};
        std::atomic_uint64_t frontend_risk_ignored_total_{0};
        std::atomic_uint64_t frontend_risk_enforced_total_{0};
        std::atomic_uint64_t frontend_body_received_total_{0};
        std::atomic_uint64_t frontend_body_occupied_total_{0};
        std::atomic_uint64_t frontend_body_ignored_total_{0};
        std::atomic_uint64_t frontend_body_enforced_total_{0};
        std::atomic_uint64_t frontend_body_clear_total_{0};

        void frontendRiskVerdictCallback(
                const mars_quadrotor_msgs::msg::TrajectoryRiskVerdict::SharedPtr
                        msg) {
            using Verdict =
                    mars_quadrotor_msgs::msg::TrajectoryRiskVerdict;
            frontend_risk_received_total_.fetch_add(
                    1, std::memory_order_relaxed);
            const bool current_body = msg->scope == Verdict::CURRENT_BODY;
            if (current_body) {
                frontend_body_received_total_.fetch_add(
                        1, std::memory_order_relaxed);
            }
            if (msg->status != Verdict::OCCUPIED) {
                if (current_body &&
                    cfg_.trajectory_guard_frontend_body_enforce_en &&
                    (msg->status == Verdict::NO_HIT ||
                     msg->status == Verdict::EGRESS) &&
                    safety_brake_active_.load(std::memory_order_acquire)) {
                    std::lock_guard<std::mutex> lock(frontend_risk_mutex_);
                    frontend_body_latest_clear_request_id_ = std::max(
                            frontend_body_latest_clear_request_id_,
                            msg->request_id);
                    if (pending_frontend_body_occupied_verdict_ &&
                        pending_frontend_body_occupied_verdict_->request_id <
                                frontend_body_latest_clear_request_id_) {
                        pending_frontend_body_occupied_verdict_.reset();
                    }
                    frontend_body_clear_total_.fetch_add(
                            1, std::memory_order_relaxed);
                }
                return;
            }
            frontend_risk_occupied_total_.fetch_add(
                    1, std::memory_order_relaxed);
            if (current_body) {
                frontend_body_occupied_total_.fetch_add(
                        1, std::memory_order_relaxed);
            }
            const bool enforce = current_body
                    ? cfg_.trajectory_guard_frontend_body_enforce_en
                    : cfg_.trajectory_guard_frontend_risk_enforce_en;
            if (enforce) {
                std::lock_guard<std::mutex> lock(frontend_risk_mutex_);
                // Preserve one hazard until the 100 Hz FSM consumes it. A
                // later NO_HIT verdict cannot erase an OCCUPIED edge.
                auto &pending = current_body
                        ? pending_frontend_body_occupied_verdict_
                        : pending_frontend_occupied_verdict_;
                auto &latest_occupied_request_id = current_body
                        ? frontend_body_latest_occupied_request_id_
                        : frontend_risk_latest_occupied_request_id_;
                if (msg->request_id > latest_occupied_request_id) {
                    pending = msg;
                    latest_occupied_request_id = msg->request_id;
                }
            }
            ros_ptr_->warn(
                    " -- [{}] request={} gen={} cloud={} status=OCCUPIED "
                    "source_age={:.3f}s compute={:.3f}ms min_dist={:.4f}m "
                    "body_dist={:.4f}m end_dist={:.4f}m witness_tt={:.3f}",
                    current_body ? "FRONTEND_BODY_VERDICT"
                                 : "FRONTEND_RISK_VERDICT",
                    msg->request_id, msg->trajectory_generation,
                    msg->cloud_sequence, msg->source_cloud_age_s,
                    msg->compute_ms, msg->minimum_distance_m,
                    msg->body_distance_m, msg->end_distance_m,
                    msg->witness_tt);
        }

        bool consumeFreshFrontendOccupiedVerdict(
                bool current_body_only = false,
                bool require_predicted_ahead = false) {
            if ((current_body_only &&
                 !cfg_.trajectory_guard_frontend_body_enforce_en) ||
                (!current_body_only &&
                 !cfg_.trajectory_guard_frontend_risk_enforce_en &&
                 !cfg_.trajectory_guard_frontend_body_enforce_en)) {
                return false;
            }
            mars_quadrotor_msgs::msg::TrajectoryRiskVerdict::SharedPtr result;
            {
                std::lock_guard<std::mutex> lock(frontend_risk_mutex_);
                if (pending_frontend_body_occupied_verdict_) {
                    result = std::move(
                            pending_frontend_body_occupied_verdict_);
                } else if (!current_body_only &&
                           pending_frontend_occupied_verdict_) {
                    result = std::move(pending_frontend_occupied_verdict_);
                } else {
                    return false;
                }
            }
            using Verdict =
                    mars_quadrotor_msgs::msg::TrajectoryRiskVerdict;
            const bool current_body = result->scope == Verdict::CURRENT_BODY;
            const auto snapshot =
                    planner_ptr_->getCommittedTrajectorySnapshot();
            const double now_wt = ros_ptr_->getSimTime();
            const double result_wt =
                    static_cast<double>(result->header.stamp.sec) +
                    1e-9 * static_cast<double>(result->header.stamp.nanosec);
            const double result_age_s = now_wt - result_wt;
            const double effective_source_age_s =
                    result->source_cloud_age_s + std::max(0.0, result_age_s);
            const double current_tt = snapshot.empty ||
                                              snapshot.pos_traj.empty()
                    ? std::numeric_limits<double>::infinity()
                    : std::clamp(now_wt - snapshot.start_wt, 0.0,
                                 snapshot.pos_traj.getTotalDuration());
            const bool generation_matches = current_body ||
                    (!snapshot.empty &&
                     snapshot.generation == result->trajectory_generation);
            const double result_max_age_s = current_body
                    ? cfg_.trajectory_guard_frontend_body_result_max_age_s
                    : cfg_.trajectory_guard_frontend_risk_result_max_age_s;
            const double source_max_age_s = current_body
                    ? cfg_.trajectory_guard_frontend_body_source_max_age_s
                    : cfg_.trajectory_guard_frontend_risk_source_max_age_s;
            const bool result_is_fresh = std::isfinite(result_age_s) &&
                    result_age_s >= 0.0 &&
                    result_age_s <= result_max_age_s;
            const bool source_is_fresh =
                    result->source_cloud_stamp_ns != 0 &&
                    std::isfinite(effective_source_age_s) &&
                    effective_source_age_s >= 0.0 &&
                    effective_source_age_s <= source_max_age_s;
            const double tt_tolerance = 0.02;
            const bool time_is_covered = current_body ||
                    (std::isfinite(current_tt) &&
                     current_tt + tt_tolerance >= result->checked_from_tt &&
                     current_tt <= result->checked_to_tt + tt_tolerance);
            if (!generation_matches || !result_is_fresh ||
                !source_is_fresh || !time_is_covered) {
                frontend_risk_ignored_total_.fetch_add(
                        1, std::memory_order_relaxed);
                if (current_body) {
                    frontend_body_ignored_total_.fetch_add(
                            1, std::memory_order_relaxed);
                }
                ros_ptr_->warn(
                        " -- [{}] action=IGNORE "
                        "request={} result_gen={} current_gen={} age={:.3f}s "
                        "source_age={:.3f}s result_tt=[{:.3f},{:.3f}] "
                        "current_tt={:.3f} generation_match={} fresh={} "
                        "source_fresh={} time_covered={}",
                        current_body ? "FRONTEND_BODY_ENFORCE"
                                     : "FRONTEND_RISK_ENFORCE",
                        result->request_id, result->trajectory_generation,
                        snapshot.generation, result_age_s,
                        effective_source_age_s, result->checked_from_tt,
                        result->checked_to_tt, current_tt,
                        generation_matches, result_is_fresh,
                        source_is_fresh, time_is_covered);
                return false;
            }
            if (require_predicted_ahead &&
                (!current_body || !std::isfinite(result->witness_tt) ||
                 result->witness_tt <= 0.01 ||
                 !std::isfinite(result->body_distance_m) ||
                 !std::isfinite(result->minimum_distance_m) ||
                 result->body_distance_m <=
                         result->minimum_distance_m + 0.02)) {
                ros_ptr_->warn(
                        " -- [FRONTEND_BODY_ACTIVE_BRAKE] action=KEEP "
                        "request={} witness_tt={:.3f} body_dist={:.4f}m "
                        "min_dist={:.4f}m reason=not_ahead_of_current_body",
                        result->request_id, result->witness_tt,
                        result->body_distance_m,
                        result->minimum_distance_m);
                return false;
            }
            frontend_risk_enforced_total_.fetch_add(
                    1, std::memory_order_relaxed);
            if (current_body) {
                frontend_body_enforced_total_.fetch_add(
                        1, std::memory_order_relaxed);
            }
            ros_ptr_->error(
                    " -- [{}] action=BRAKE request={} "
                    "gen={} cloud={} age={:.3f}s source_age={:.3f}s "
                    "current_tt={:.3f} witness_tt={:.3f} min_dist={:.4f}m",
                    current_body ? "FRONTEND_BODY_ENFORCE"
                                 : "FRONTEND_RISK_ENFORCE",
                    result->request_id, result->trajectory_generation,
                    result->cloud_sequence, result_age_s,
                    effective_source_age_s, current_tt,
                    result->witness_tt, result->minimum_distance_m);
            return true;
        }

        void stopNearFieldShadowWorker() {
            {
                std::lock_guard<std::mutex> lock(
                        near_field_shadow_worker_mutex_);
                stop_near_field_shadow_worker_ = true;
                pending_near_field_shadow_job_.reset();
                pending_near_field_shadow_occupied_result_.reset();
            }
            near_field_shadow_worker_cv_.notify_all();
            if (near_field_shadow_worker_.joinable()) {
                near_field_shadow_worker_.join();
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
        std::uint64_t recovery_motion_last_generation_{0};
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
            if (cfg_.trajectory_guard_raw_cloud_ciri_shadow_en ||
                cfg_.trajectory_guard_raw_cloud_near_field_shadow_en) {
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
            {
                std::lock_guard<std::mutex> lock(raw_cloud_mutex_);
                // Publish the accepted sequence only after the corresponding
                // batch is visible in the accumulation window. A scan-driven
                // job tagged with this sequence therefore cannot race ahead
                // of its own source data.
                if (tree) {
                    raw_cloud_snapshot_.tree = std::move(tree);
                }
                raw_cloud_snapshot_.receive_time = receive_time;
                ++raw_cloud_snapshot_.sequence;
            }
        }

        void guardCloudCallback(
                const sensor_msgs::msg::PointCloud2::SharedPtr cloud_msg) {
            injectGuardCloud(cloud_msg);
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
            const super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::PlannerVisualizePath);
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
            static const bool skip_unobserved_publication = [] {
                const char *setting = std::getenv(
                        "SUPER_SKIP_UNOBSERVED_PATH_PUBLICATION");
                return setting && std::strcmp(setting, "1") == 0;
            }();
            // Preserve every pose even while this volatile visualization
            // topic has no readers. A newly matched reader gets the entire
            // path on the next tick, at the unchanged publication cadence.
            if (skip_unobserved_publication &&
                !visualizedPathPublicationAllowed(
                        true, path_pub_->get_subscription_count(),
                        path_pub_->get_intra_process_subscription_count())) {
                return;
            }
            path_pub_->publish(path);
        }

        void fillPolynomialTrajectory(
                const Trajectory &pos_traj,
                const Trajectory &yaw_traj,
                mars_quadrotor_msgs::msg::PolynomialTrajectory &cmd_traj,
                const bool emergency = false,
                const std::uint64_t trajectory_generation = 0) {
            cmd_traj = mars_quadrotor_msgs::msg::PolynomialTrajectory{};
            ros_ptr_->getSimTime(cmd_traj.header.stamp.sec,
                                 cmd_traj.header.stamp.nanosec);
            cmd_traj.header.frame_id = "world";
            cmd_traj.trajectory_generation = trajectory_generation;
            cmd_traj.trajectory_id = static_cast<std::uint32_t>(
                    trajectory_generation &
                    std::numeric_limits<std::uint32_t>::max());
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
            const super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::FsmPolyPublish);
            if (asyncGenerateEnabled() &&
                async_generate_quarantine_.load(std::memory_order_acquire)) return;
            if (cfg_.event_recovery_en &&
                safety_brake_active_.load(std::memory_order_acquire)) return;
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
            if (cfg_.trajectory_guard_en) {
                const double velocity_limit =
                        planner_ptr_->getConfiguredMaxVelocity();
                const double max_velocity = [&] {
                    const super_utils::thread_cpu_profile::Scope velocity_cpu_scope(
                            super_utils::thread_cpu_profile::Stage::PlannerVelocityExtrema);
                    return snapshot.pos_traj.getMaxVelRate();
                }();
                if (!std::isfinite(velocity_limit) ||
                    velocity_limit <= 0.0 ||
                    !std::isfinite(max_velocity) ||
                    max_velocity > velocity_limit * 1.001) {
                    ros_ptr_->error(
                            " -- [TRAJ_VELOCITY_REJECT] source=poly_publish "
                            "gen={} max_vel={:.6f} limit={:.6f}",
                            snapshot.generation, max_velocity,
                            velocity_limit);
                    safety_revalidation_requested_.store(
                            true, std::memory_order_release);
                    return;
                }
            }
            mars_quadrotor_msgs::msg::PolynomialTrajectory cmd_traj;
            fillPolynomialTrajectory(snapshot.pos_traj, snapshot.yaw_traj,
                                     cmd_traj, false,
                                     snapshot.generation);
            std::unique_lock<std::mutex> publication(safety_mutex_, std::defer_lock);
            if (asyncGenerateEnabled()) {
                publication.lock();
                if (async_generate_quarantine_.load(std::memory_order_acquire) ||
                    safety_brake_active_.load(std::memory_order_acquire)) return;
            }
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
            heartbeat.trajectory_generation = sample.generation;
            heartbeat.trajectory_id = static_cast<std::uint32_t>(
                    sample.generation &
                    std::numeric_limits<std::uint32_t>::max());
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
            fillPolynomialTrajectory(snapshot.pos_traj, snapshot.yaw_traj,
                                     cmd_traj, false,
                                     snapshot.generation);
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
            pos_cmd.trajectory_id = sample.generation;
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

        bool commandVelocityWithinLimit(
                const CmdTraj::Sample &sample,
                const char *source,
                const double velocity_limit) const {
            const Vec3f velocity = sample.pvaj.col(1);
            const double speed = velocity.norm();
            if (std::isfinite(velocity_limit) && velocity_limit > 0.0 &&
                velocity.array().isFinite().all() &&
                std::isfinite(speed) &&
                speed <= velocity_limit * 1.001) {
                return true;
            }
            ros_ptr_->error(
                    " -- [TRAJ_VELOCITY_REJECT] source={} gen={} "
                    "tt={:.6f} speed={:.6f} limit={:.6f} "
                    "vel=[{:.6f},{:.6f},{:.6f}] backup={}",
                    source, sample.generation, sample.trajectory_time,
                    speed, velocity_limit,
                    velocity.x(), velocity.y(), velocity.z(),
                    sample.on_backup);
            return false;
        }

        void getOnePositionCommand(mars_quadrotor_msgs::msg::PositionCommand &pos_cmd,
                                   bool &traj_finish) {
            if (asyncGenerateEnabled() &&
                async_generate_quarantine_.load(std::memory_order_acquire)) {
                traj_finish = false;
                return;
            }
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
                double &map_age_s,
                double &map_age_limit_s,
                double &motion_speed_mps) const {
            map_age_limit_s = cfg_.trajectory_guard_brake_trigger_map_age_s;
            motion_speed_mps = 0.0;
            const double low_speed =
                    cfg_.trajectory_guard_brake_trigger_low_speed_mps;
            const double high_speed =
                    cfg_.trajectory_guard_brake_trigger_high_speed_mps;
            const double high_speed_limit =
                    cfg_.trajectory_guard_brake_trigger_high_speed_map_age_s;
            if (high_speed > low_speed + 1.0e-9 &&
                high_speed_limit < map_age_limit_s - 1.0e-9) {
                // ROG's legacy RobotState carries pose but its velocity is
                // unset in the perfect-tracking benchmark.  Prefer the latest
                // command that was actually published.  The command and FSM
                // timers are independent, though: publication can be skipped
                // briefly while a map-version revalidation is pending, so a
                // hard 0.1 s cache cutoff used to report zero speed while the
                // vehicle was still following the committed polynomial.  For
                // freshness only, retain the last published velocity for at
                // most the low-speed map-age budget, then sample the immutable
                // committed trajectory if even that cache has expired.  The
                // longer window is never used as a brake initial state.
                mars_quadrotor_msgs::msg::PositionCommand command;
                bool command_valid;
                double command_wt;
                {
                    std::lock_guard<std::mutex> lock(latest_cmd_mutex_);
                    command_valid = last_published_cmd_valid_;
                    command_wt = last_published_cmd_wt_;
                    if (command_valid) {
                        command = last_published_cmd_;
                    }
                }
                const double command_age_s = command_valid
                        ? ros_ptr_->getSimTime() - command_wt
                        : std::numeric_limits<double>::infinity();
                const Vec3f command_velocity(command.velocity.x,
                                             command.velocity.y,
                                             command.velocity.z);
                const double freshness_velocity_max_age_s = std::max(
                        cfg_.brake_command_max_age_s,
                        cfg_.trajectory_guard_brake_trigger_map_age_s);
                if (command_valid && std::isfinite(command_age_s) &&
                    command_age_s >= 0.0 &&
                    command_age_s <= freshness_velocity_max_age_s &&
                    command_velocity.array().isFinite().all()) {
                    motion_speed_mps = command_velocity.norm();
                } else {
                    const auto snapshot =
                            planner_ptr_->getCommittedTrajectorySnapshot();
                    if (!snapshot.empty && !snapshot.pos_traj.empty() &&
                        std::isfinite(snapshot.start_wt) &&
                        std::isfinite(snapshot.total_duration) &&
                        snapshot.total_duration >= 0.0) {
                        const double trajectory_tt = std::clamp(
                                ros_ptr_->getSimTime() - snapshot.start_wt,
                                0.0, snapshot.total_duration);
                        const Vec3f trajectory_velocity =
                                snapshot.pos_traj.getVel(trajectory_tt);
                        if (trajectory_velocity.array().isFinite().all()) {
                            motion_speed_mps = trajectory_velocity.norm();
                        }
                    }
                }
                const double alpha = std::clamp(
                        (motion_speed_mps - low_speed) /
                                (high_speed - low_speed),
                        0.0, 1.0);
                map_age_limit_s += alpha *
                        (high_speed_limit - map_age_limit_s);
            }
            return mapFreshForGuard(health, map_age_s) &&
                   map_age_s <= map_age_limit_s;
        }

        bool refreshSafetyCertificate(const char *trigger) {
            const super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::GuardCertificate);
            if (!cfg_.trajectory_guard_en) {
                return true;
            }
            const auto retry_deadline = std::chrono::steady_clock::now() +
                    std::chrono::milliseconds(4);
            double map_age_s = 0.0, map_age_limit_s = 0.0, motion_speed_mps = 0.0;
            TrajectorySafetyResult result;
            bool changed = false;
            unsigned attempt = 0;
            for (; attempt < 2; ++attempt) {
                std::uint64_t validation;
                bool map_fresh;
                {
                    std::lock_guard<std::mutex> lock(safety_mutex_);
                    const auto health = map_ptr_->getMapHealthSnapshot();
                    const auto generation = planner_ptr_->getCommittedTrajectoryGeneration();
                    map_fresh = mapFreshEnoughForMotion(
                            health, map_age_s, map_age_limit_s, motion_speed_mps);
                    if (map_fresh && safety_certificate_valid_ &&
                        safety_certificate_.safe() &&
                        safety_certificate_.trajectory_generation == generation &&
                        safety_certificate_.map_version == health.map_version &&
                        !safety_revalidation_requested_.load(std::memory_order_acquire)) {
                        if (attempt) fmt::print(" -- [TRAJ_GUARD_REFRESH] trigger={} outcome=current_cache retry={}\n", trigger, attempt);
                        return true;
                    }
                    validation = ++safety_validation_started_;
                    // Consume only requests preceding this check. A request
                    // arriving while geometry is checked must not be lost.
                    safety_revalidation_requested_.exchange(false, std::memory_order_acq_rel);
                    result.trajectory_generation = generation;
                    result.map_version = health.map_version;
                }
                if (!map_fresh) {
                    result.status = TrajectorySafetyStatus::MAP_STALE;
                } else {
                    result = planner_ptr_->validateCommittedTrajectory(
                            ros_ptr_->getSimTime(), attempt == 0
                                    ? std::chrono::steady_clock::time_point::max()
                                    : retry_deadline);
                }
                {
                    std::lock_guard<std::mutex> lock(safety_mutex_);
                    const auto health = map_ptr_->getMapHealthSnapshot();
                    const auto generation = planner_ptr_->getCommittedTrajectoryGeneration();
                    map_fresh = mapFreshEnoughForMotion(
                            health, map_age_s, map_age_limit_s, motion_speed_mps);
                    const bool current = result.trajectory_generation == generation &&
                                         result.map_version == health.map_version;
                    const bool cache_current = safety_certificate_valid_ &&
                            safety_certificate_.trajectory_generation == generation &&
                            safety_certificate_.map_version == health.map_version;
                    if (attempt && result.safe() &&
                        std::chrono::steady_clock::now() >= retry_deadline) {
                        result.status = TrajectorySafetyStatus::VALIDATION_TIMEOUT;
                    }
                    if (result.safe() && !map_fresh) result.status = TrajectorySafetyStatus::MAP_STALE;
                    if (result.safe() && !current) result.status = TrajectorySafetyStatus::VERSION_CHANGED;
                    if ((result.status == TrajectorySafetyStatus::VERSION_CHANGED || result.safe()) &&
                        validation < safety_certificate_validation_ && cache_current) {
                        if (map_fresh && safety_certificate_.safe() &&
                            !safety_revalidation_requested_.load(std::memory_order_acquire)) {
                            fmt::print(" -- [TRAJ_GUARD_REFRESH] trigger={} outcome=newer_certificate retry={}\n", trigger, attempt);
                            return true;
                        }
                        // A newer explicit failure must not be replaced by an
                        // older SAFE result or retried away in this invocation.
                        if (!safety_certificate_.safe()) result = safety_certificate_;
                    }
                    if (result.safe() && validation < safety_certificate_validation_) {
                        // We could not reuse the newer publication above.
                        // Do not report success with no usable shared receipt.
                        result.status = TrajectorySafetyStatus::VERSION_CHANGED;
                    }
                    if (current && validation >= safety_certificate_validation_ &&
                        result.status != TrajectorySafetyStatus::VERSION_CHANGED) {
                        changed = !safety_certificate_valid_ ||
                                  safety_certificate_.status != result.status ||
                                  safety_certificate_.trajectory_generation != result.trajectory_generation ||
                                  safety_certificate_.map_version != result.map_version;
                        safety_certificate_ = result;
                        safety_certificate_valid_ = true;
                        safety_certificate_validation_ = validation;
                    }
                }
                if (result.status != TrajectorySafetyStatus::VERSION_CHANGED) break;
                fmt::print(" -- [TRAJ_GUARD_REFRESH] trigger={} outcome=version_changed retry={} gen={} map={}\n",
                           trigger, attempt, result.trajectory_generation, result.map_version);
                if (attempt != 0 || std::chrono::steady_clock::now() >= retry_deadline ||
                    !map_ptr_->immutablePlannerSnapshotEnabled()) break;
            }
            if (!result.safe()) safety_revalidation_requested_.store(true, std::memory_order_release);
            if (attempt) fmt::print(" -- [TRAJ_GUARD_REFRESH] trigger={} outcome={} retry={}\n",
                                   trigger, trajectorySafetyStatusName(result.status), attempt);

            if (changed || result.status == TrajectorySafetyStatus::VERSION_CHANGED ||
                result.status == TrajectorySafetyStatus::VALIDATION_TIMEOUT) {
                const auto snapshot = planner_ptr_->getCommittedTrajectorySnapshot();
                const double current_tt = snapshot.empty
                        ? 0.0 : ros_ptr_->getSimTime() - snapshot.start_wt;
                const double ttc = result.first_collision_tt >= 0.0
                        ? result.first_collision_tt - current_tt : -1.0;
                fmt::print(" -- [TRAJ_GUARD_CERT] trigger={} status={} gen={} map={} "
                           "map_age={:.3f}s map_age_limit={:.3f}s motion_speed={:.3f}mps "
                           "samples={} range=[{:.3f},{:.3f}] "
                           "collision_tt={:.3f} ttc={:.3f} p=[{:.3f},{:.3f},{:.3f}]\n",
                           trigger, trajectorySafetyStatusName(result.status),
                           result.trajectory_generation, result.map_version,
                           map_age_s, map_age_limit_s, motion_speed_mps,
                           result.checked_samples,
                           result.checked_from_tt, result.checked_to_tt,
                           result.first_collision_tt, ttc,
                           result.first_collision_pos.x(),
                           result.first_collision_pos.y(),
                           result.first_collision_pos.z());
            }
            return result.safe();
        }

        bool refreshStoppedDepartureCertificate(
                const std::uint64_t generation,
                const std::uint64_t map_version,
                const char *trigger) {
            TrajectorySafetyResult staged;
            if (!stoppedDepartureV4Enabled() ||
                !planner_ptr_->getStoppedDepartureCertificate(
                        generation, map_version, staged)) {
                return false;
            }
            std::lock_guard<std::mutex> lock(safety_mutex_);
            const auto health = map_ptr_->getMapHealthSnapshot();
            if (health.map_version != map_version ||
                (health.update_in_progress &&
                 !map_ptr_->immutablePlannerSnapshotEnabled()) ||
                planner_ptr_->getCommittedTrajectoryGeneration() != generation ||
                !staged.safe() || staged.checked_from_tt > 0.0) {
                return false;
            }
            safety_certificate_ = staged;
            safety_certificate_valid_ = true;
            safety_certificate_validation_ = ++safety_validation_started_;
            safety_revalidation_requested_.store(false,
                                                   std::memory_order_release);
            ros_ptr_->info(
                    " -- [STOPPED_DEPARTURE_CERTIFICATE] trigger={} "
                    "gen={} map={} range=[{:.3f},{:.3f}] samples={}",
                    trigger, generation, map_version,
                    staged.checked_from_tt, staged.checked_to_tt,
                    staged.checked_samples);
            return true;
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
                                       const double max_velocity_limit,
                                       double &max_velocity,
                                       double &max_acc,
                                       double &max_jerk) const {
            max_velocity = 0.0;
            max_acc = 0.0;
            max_jerk = 0.0;
            if (trajectory.empty()) {
                return false;
            }
            max_velocity = trajectory.getMaxVelRate();
            if (!std::isfinite(max_velocity) ||
                max_velocity > max_velocity_limit * 1.001) {
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

        void clearActiveYawScanLocked() {
            active_yaw_scan_ = ActiveYawScanState{};
        }

        void armActiveYawScanLocked(const double start_yaw,
                                    const Vec3f& stop_position,
                                    const Vec3f& goal_position,
                                    const std::uint64_t map_version,
                                    const std::uint64_t processed_scan_count,
                                    const unsigned attempt,
                                    const bool new_episode) {
            if (!activeYawScanEnabled()) return;
            const Vec3f delta = goal_position - stop_position;
            const double goal_bearing = delta.head<2>().norm() > 1.0e-3
                    ? std::atan2(delta.y(), delta.x())
                    : start_yaw;
            if (new_episode) {
                clearActiveYawScanLocked();
                active_yaw_scan_.episode_active = true;
                active_yaw_scan_.episode = ++active_yaw_scan_arms_;
                if (active_yaw_scan_.episode == 0) {
                    active_yaw_scan_.episode = ++active_yaw_scan_arms_;
                }
                active_yaw_scan_.goal_bearing = goal_bearing;
            }
            active_yaw_scan_.attempt = attempt;
            active_yaw_scan_.command_active = true;
            active_yaw_scan_.rotation_started = false;
            active_yaw_scan_.target_reached = false;
            active_yaw_scan_.recovery_ready = false;
            active_yaw_scan_.start_map_version = map_version;
            active_yaw_scan_.required_map_version = 0;
            active_yaw_scan_.start_processed_scan_count =
                    processed_scan_count;
            active_yaw_scan_.required_processed_scan_count =
                    processed_scan_count ==
                            std::numeric_limits<std::uint64_t>::max()
                    ? processed_scan_count : processed_scan_count + 1;
            active_yaw_scan_.start_yaw = active_yaw_scan::wrapAngle(start_yaw);
            active_yaw_scan_.target_yaw = active_yaw_scan::targetForAttempt(
                    active_yaw_scan_.goal_bearing, attempt);
            active_yaw_scan_.start_wt =
                    std::numeric_limits<double>::quiet_NaN();
            active_yaw_scan_.settle_not_before_wt =
                    std::numeric_limits<double>::infinity();
            const auto command = active_yaw_scan::command(
                    active_yaw_scan_.start_yaw,
                    active_yaw_scan_.target_yaw, 0.0,
                    40.0 * active_yaw_scan::kPi / 180.0);
            ros_ptr_->info(
                    " -- [ACTIVE_YAW_SCAN_ARM] episode={} attempt={} "
                    "start_deg={:.1f} target_deg={:.1f} goal_deg={:.1f} "
                    "duration={:.3f}s start_map={} start_processed_scan={} "
                    "default_off=true",
                    active_yaw_scan_.episode, attempt,
                    active_yaw_scan_.start_yaw * 180.0 / active_yaw_scan::kPi,
                    active_yaw_scan_.target_yaw * 180.0 / active_yaw_scan::kPi,
                    active_yaw_scan_.goal_bearing * 180.0 / active_yaw_scan::kPi,
                    command.duration, map_version, processed_scan_count);
        }

        bool activeYawScanRecoveryReady() {
            if (!activeYawScanEnabled()) return true;
            const auto health = map_ptr_->getMapHealthSnapshot();
            const auto odom = map_ptr_->getRobotState();
            const double now_wt = ros_ptr_->getSimTime();
            double map_age_s = std::numeric_limits<double>::infinity();
            const bool map_fresh = mapFreshForGuard(health, map_age_s);
            bool log_reached = false;
            bool log_ready = false;
            std::uint64_t episode = 0, start_map = 0, required_map = 0,
                    current_map = 0;
            std::uint64_t required_processed = 0, current_processed = 0;
            unsigned attempt = 0;
            double measured_yaw = std::numeric_limits<double>::quiet_NaN();
            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                if (!safety_brake_active_.load(std::memory_order_relaxed)) {
                    return true;
                }
                if (!active_yaw_scan_.episode_active) {
                    // The opt-in contract requires every recovery attempt to
                    // have an explicit yaw acquisition boundary.
                    return false;
                }
                if (active_yaw_scan_.recovery_ready) return true;
                if (!safety_brake_finished_.load(
                            std::memory_order_relaxed) ||
                    !active_yaw_scan_.rotation_started ||
                    !std::isfinite(active_yaw_scan_.start_wt)) {
                    return false;
                }
                const auto command = active_yaw_scan::command(
                        active_yaw_scan_.start_yaw,
                        active_yaw_scan_.target_yaw,
                        now_wt - active_yaw_scan_.start_wt,
                        40.0 * active_yaw_scan::kPi / 180.0);
                if (!command.complete || !odom.rcv ||
                    !std::isfinite(odom.rcv_time) ||
                    now_wt < odom.rcv_time || now_wt - odom.rcv_time > 0.1 ||
                    !std::isfinite(odom.yaw) ||
                    std::abs(active_yaw_scan::wrapAngle(
                            odom.yaw - active_yaw_scan_.target_yaw)) >
                            8.0 * active_yaw_scan::kPi / 180.0) {
                    return false;
                }
                measured_yaw = odom.yaw;
                if (!active_yaw_scan_.target_reached) {
                    active_yaw_scan_.target_reached = true;
                    active_yaw_scan_.required_map_version =
                            health.map_version ==
                                    std::numeric_limits<std::uint64_t>::max()
                            ? health.map_version : health.map_version + 1;
                    active_yaw_scan_.settle_not_before_wt = now_wt + 0.20;
                    log_reached = true;
                }
                // The ordinary stopped guard allows a 0.55 s map age.  That
                // is too loose for a 40 deg/s acquisition sweep: a boundary
                // frame could have been observed roughly 22 degrees before
                // the commanded view and expire before the async recovery
                // request is submitted.  At 10 Hz, 0.35 s still covers one
                // target-view frame plus the 0.20 s settle window and normal
                // scheduling jitter.
                constexpr double kActiveYawViewMaxAgeS = 0.35;
                const bool observation_ready =
                        health.processed_scan_count >=
                                active_yaw_scan_.required_processed_scan_count &&
                        map_fresh && map_age_s <= kActiveYawViewMaxAgeS;
                if (now_wt < active_yaw_scan_.settle_not_before_wt ||
                    health.update_in_progress) {
                    episode = active_yaw_scan_.episode;
                    attempt = active_yaw_scan_.attempt;
                    start_map = active_yaw_scan_.start_map_version;
                    required_map = active_yaw_scan_.required_map_version;
                    current_map = health.map_version;
                    required_processed =
                            active_yaw_scan_.required_processed_scan_count;
                    current_processed = health.processed_scan_count;
                } else if (!observation_ready) {
                    const auto skipped_episode = active_yaw_scan_.episode;
                    const auto skipped_attempt = active_yaw_scan_.attempt;
                    const auto skipped_required =
                            active_yaw_scan_.required_processed_scan_count;
                    if (active_yaw_scan_.attempt >= 3) {
                        active_yaw_scan_.command_active = false;
                        active_yaw_scan_.episode_active = false;
                        ros_ptr_->warn(
                                " -- [ACTIVE_YAW_SCAN_EXHAUSTED] episode={} "
                                "views=4 reason=no_fresh_view_observation "
                                "min_processed_scan={} current_processed_scan={} "
                                "map_age_s={:.3f} "
                                "action=retain_certified_hold",
                                skipped_episode, skipped_required,
                                health.processed_scan_count, map_age_s);
                    } else {
                        const unsigned next_attempt =
                                active_yaw_scan_.attempt + 1;
                        const Vec3f synthetic_stop = Vec3f::Zero();
                        const Vec3f synthetic_goal(
                                std::cos(active_yaw_scan_.goal_bearing),
                                std::sin(active_yaw_scan_.goal_bearing), 0.0);
                        ros_ptr_->warn(
                                " -- [ACTIVE_YAW_SCAN_VIEW_EMPTY] episode={} "
                                "attempt={} min_processed_scan={} "
                                "current_processed_scan={} map_age_s={:.3f} "
                                "action=next_view",
                                skipped_episode, skipped_attempt,
                                skipped_required,
                                health.processed_scan_count, map_age_s);
                        armActiveYawScanLocked(
                                odom.yaw, synthetic_stop, synthetic_goal,
                                health.map_version,
                                health.processed_scan_count,
                                next_attempt, false);
                    }
                    return false;
                } else {
                    active_yaw_scan_.command_active = false;
                    active_yaw_scan_.recovery_ready = true;
                    ++active_yaw_scan_map_acks_;
                    log_ready = true;
                    episode = active_yaw_scan_.episode;
                    attempt = active_yaw_scan_.attempt;
                    start_map = active_yaw_scan_.start_map_version;
                    required_map = active_yaw_scan_.required_map_version;
                    current_map = health.map_version;
                    required_processed =
                            active_yaw_scan_.required_processed_scan_count;
                    current_processed = health.processed_scan_count;
                }
            }
            if (log_reached) {
                ros_ptr_->info(
                        " -- [ACTIVE_YAW_SCAN_TARGET_REACHED] episode={} "
                        "attempt={} yaw_deg={:.1f} min_processed_scan={} "
                        "current_processed_scan={} start_map={} current_map={} "
                        "next_map_if_changed={}",
                        episode, attempt,
                        measured_yaw * 180.0 / active_yaw_scan::kPi,
                        required_processed, current_processed, start_map,
                        current_map, required_map);
            }
            if (log_ready) {
                ros_ptr_->info(
                        " -- [ACTIVE_YAW_SCAN_MAP_READY] episode={} attempt={} "
                        "min_processed_scan={} current_processed_scan={} "
                        "start_map={} current_map={} next_map_if_changed={} "
                        "completed_total={}",
                        episode, attempt, required_processed,
                        current_processed, start_map, current_map, required_map,
                        active_yaw_scan_map_acks_);
                return true;
            }
            return false;
        }

        void armNextActiveYawScanAfterPlanningFailure(
                const std::uint64_t brake_revision) {
            if (!activeYawScanEnabled()) return;
            const auto health = map_ptr_->getMapHealthSnapshot();
            const auto odom = map_ptr_->getRobotState();
            std::lock_guard<std::mutex> lock(safety_mutex_);
            if (!safety_brake_active_.load(std::memory_order_relaxed) ||
                brake_revision != brake_activation_revision_ ||
                !active_yaw_scan_.episode_active) return;
            if (active_yaw_scan_.attempt >= 3) {
                active_yaw_scan_.command_active = false;
                active_yaw_scan_.recovery_ready = true;
                ros_ptr_->warn(
                        " -- [ACTIVE_YAW_SCAN_EXHAUSTED] episode={} views=4 "
                        "action=retain_certified_hold_and_retry_accumulated_map",
                        active_yaw_scan_.episode);
                return;
            }
            const unsigned next_attempt = active_yaw_scan_.attempt + 1;
            const double start_yaw = odom.rcv && std::isfinite(odom.yaw)
                    ? odom.yaw : active_yaw_scan_.target_yaw;
            const Vec3f synthetic_stop = Vec3f::Zero();
            const Vec3f synthetic_goal(
                    std::cos(active_yaw_scan_.goal_bearing),
                    std::sin(active_yaw_scan_.goal_bearing), 0.0);
            armActiveYawScanLocked(start_yaw, synthetic_stop, synthetic_goal,
                                   health.map_version,
                                   health.processed_scan_count,
                                   next_attempt, false);
        }

        bool activateEmergencyBrake(const std::string &reason,
                                    bool replace_active_body_brake = false) {
            const super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::GuardBrake);
            if (!cfg_.trajectory_guard_en) {
                return false;
            }
            // Adaptive sensing must react to the guard event itself, not infer
            // it later from a streak of planning failures. Keep this latched
            // across brake construction/retry; the filter applies its own
            // post-recovery quiet-period hold before closing again.
            std::lock_guard<std::mutex> activation_lock(
                    brake_activation_mutex_);
            ++brake_activation_revision_;
            if (brake_activation_revision_ == 0) ++brake_activation_revision_;
            startup_recovery_pending_ = false;
            // Serialize the true edge with startup completion. Publishing before
            // this lock let completion erase a newer waiting activator's edge.
            publishTrajectoryGuardRecoveryState(true);
            if (safety_brake_active_.load(std::memory_order_acquire)) {
                if (!replace_active_body_brake) {
                    return false;
                }
                std::lock_guard<std::mutex> lock(safety_mutex_);
                if (active_brake_body_replaced_) {
                    return false;
                }
            }
            // A new brake is not a terminal hold until its trajectory has
            // finished and the stability checks in tryRecoverFromEmergencyBrake
            // pass. Never carry a previous recovery certificate into it.
            planner_ptr_->setCertifiedStopForReroute(false);
            if (machine_state_ != EMER_STOP) {
                // A new guard event starts a new passive-stop observation.
                // Reusing an old anchor would let a later return to roughly
                // the same point appear stable immediately.
                brake_passive_stability_started_ = false;
            }

            // Refresh odometry before selecting a brake initial state. A
            // PositionCommand is command-continuous only while it is recent
            // and still agrees with the tracked vehicle. Guard suppression
            // deliberately stops normal command publication, so a boolean
            // "was ever published" flag alone is not a validity condition.
            if (asyncCertifiedRecoveryEnabled() || asyncGenerateEnabled()) {
                // The stopped recovery optimizer owns the planner's mutable
                // RobotState. Brake selection needs only its own odometry
                // copy and must not overwrite that planner cache mid-solve.
                robot_state_ = map_ptr_->getRobotState();
            } else {
                planner_ptr_->getRobotState(robot_state_);
            }
            const double selection_wt = ros_ptr_->getSimTime();
            const bool odom_position_ready = robot_state_.rcv &&
                    std::isfinite(robot_state_.rcv_time) &&
                    selection_wt - robot_state_.rcv_time >= 0.0 &&
                    selection_wt - robot_state_.rcv_time <= 0.1 &&
                    robot_state_.p.array().isFinite().all();
            double recovery_motion_dt_s =
                    std::numeric_limits<double>::infinity();
            const double configured_motion_velocity_limit = std::max(
                    1.0e-3, planner_ptr_->getConfiguredMaxVelocity());
            const std::uint64_t recovery_motion_generation =
                    planner_ptr_->getCommittedTrajectoryGeneration();
            const std::uint64_t recovery_motion_anchor_generation =
                    recovery_motion_last_generation_;
            const bool recovery_motion_generation_continuous =
                    std::isfinite(recovery_motion_last_wt_) &&
                    recovery_motion_generation ==
                            recovery_motion_anchor_generation;
            const char *recovery_motion_source = "none";
            double recovery_pose_difference_speed =
                    std::numeric_limits<double>::infinity();
            double recovery_odom_twist_speed =
                    std::numeric_limits<double>::infinity();
            double recovery_pose_twist_disagreement =
                    std::numeric_limits<double>::infinity();
            recovery_motion_velocity_valid_ = false;
            if (odom_position_ready) {
                Vec3f odom_twist = Vec3f::Zero();
                double odom_twist_receive_time = 0.0;
                const bool odom_twist_ready = map_ptr_->getLatestOdomTwist(
                        odom_twist, odom_twist_receive_time) &&
                        std::isfinite(odom_twist_receive_time) &&
                        selection_wt - odom_twist_receive_time >= 0.0 &&
                        selection_wt - odom_twist_receive_time <= 0.1 &&
                        odom_twist.array().isFinite().all();
                const double recovery_motion_anchor_dt_s =
                        robot_state_.rcv_time - recovery_motion_last_wt_;
                Vec3f position_difference_velocity = Vec3f::Zero();
                const bool position_difference_available =
                        std::isfinite(recovery_motion_last_wt_) &&
                        recovery_motion_anchor_dt_s >= 0.005 &&
                        recovery_motion_anchor_dt_s <= 0.5 &&
                        recovery_motion_generation_continuous;
                if (position_difference_available) {
                    position_difference_velocity =
                            (robot_state_.p - recovery_motion_last_position_) /
                            recovery_motion_anchor_dt_s;
                }
                recovery_pose_difference_speed =
                        position_difference_available
                        ? position_difference_velocity.norm()
                        : std::numeric_limits<double>::infinity();
                recovery_odom_twist_speed = odom_twist_ready
                        ? odom_twist.norm()
                        : std::numeric_limits<double>::infinity();
                recovery_pose_twist_disagreement =
                        odom_twist_ready && position_difference_available
                        ? (odom_twist - position_difference_velocity).norm()
                        : std::numeric_limits<double>::infinity();
                const bool odom_twist_corroborated = odom_twist_ready &&
                        position_difference_available &&
                        position_difference_velocity.array().isFinite().all() &&
                        directOdomTwistEstimateAllowed(
                                recovery_odom_twist_speed,
                                recovery_pose_difference_speed,
                                recovery_pose_twist_disagreement,
                                cfg_.brake_command_max_velocity_error_mps,
                                recovery_motion_generation_continuous);
                if (odom_twist_corroborated) {
                    recovery_motion_velocity_ = odom_twist;
                    recovery_motion_velocity_valid_ = true;
                    recovery_motion_dt_s =
                            selection_wt - odom_twist_receive_time;
                    recovery_motion_source = "odom_twist";
                } else if (position_difference_available) {
                    recovery_motion_velocity_valid_ =
                            position_difference_velocity.array().isFinite().all() &&
                            positionDifferenceMotionEstimateAllowed(
                                    recovery_pose_difference_speed,
                                    configured_motion_velocity_limit,
                                    recovery_motion_generation_continuous);
                    if (recovery_motion_velocity_valid_) {
                        recovery_motion_velocity_ =
                                position_difference_velocity;
                        recovery_motion_dt_s =
                                recovery_motion_anchor_dt_s;
                        recovery_motion_source = "position_difference";
                    }
                }
                if (!std::isfinite(recovery_motion_last_wt_) ||
                    recovery_motion_anchor_dt_s >= 0.005 ||
                    recovery_motion_anchor_dt_s < 0.0) {
                    recovery_motion_last_position_ = robot_state_.p;
                    // These are odometry positions. Divide them by the
                    // odometry receive-time delta, not by the times at which
                    // asynchronous guard callbacks happened to inspect them.
                    // The callback-time denominator produced a 10.055 m/s
                    // estimate from a 6.323 m/s command when retries were
                    // only 6 ms apart, then published a brake from that false
                    // initial velocity.
                    recovery_motion_last_wt_ = robot_state_.rcv_time;
                    recovery_motion_last_generation_ =
                            recovery_motion_generation;
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
                initial_source = recovery_motion_source;
            } else {
                CmdTraj::Sample current_sample;
                if (!getExecutableSampleForBrake(current_sample)) {
                    const auto snapshot = planner_ptr_->getCommittedSharedTrajectorySnapshot();
                    const auto state = machine_state_.load(std::memory_order_acquire);
                    startup_recovery_pending_ = !cached_command_valid &&
                            snapshot.empty && snapshot.generation == 0 &&
                            !safety_brake_active_.load(std::memory_order_acquire) &&
                            (state == INIT || state == WAIT_GOAL || state == GENERATE_TRAJ);
                    if (startup_recovery_pending_) {
                        ros_ptr_->info(" -- [TRAJ_GUARD_STARTUP_PENDING] revision={} generation=0",
                                       brake_activation_revision_);
                    }
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

            // Command suppression after an uncertified brake is fail-closed,
            // and the controller can bring the vehicle to rest before a
            // fresh-map brake candidate becomes available.  Track that fact
            // from independent odometry.  It does not certify any movement;
            // it only enables the zero-displacement hold special case below.
            bool passive_stop_stable = false;
            if (odom_position_ready && recovery_motion_velocity_valid_ &&
                recovery_motion_velocity_.norm() <= 0.05) {
                if (!brake_passive_stability_started_ ||
                    (robot_state_.p - brake_passive_stability_anchor_).norm() >
                            0.03) {
                    brake_passive_stability_anchor_ = robot_state_.p;
                    brake_passive_stability_start_wt_ = selection_wt;
                    brake_passive_stability_started_ = true;
                }
                passive_stop_stable = selection_wt -
                        brake_passive_stability_start_wt_ >= 0.25;
            } else {
                brake_passive_stability_started_ = false;
            }

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
            const double configured_velocity_limit = std::max(
                    1.0e-3, planner_ptr_->getConfiguredMaxVelocity());
            // If an external disturbance already put the vehicle over the
            // configured limit, braking must remain possible. The brake may
            // start at that measured speed but must not create a new maximum.
            const double brake_velocity_limit = std::max(
                    configured_velocity_limit, initial.col(1).norm());
            double max_velocity = 0.0;
            double max_acc = 0.0;
            double max_jerk = 0.0;
            bool dynamics_ok = false;
            TrajectorySafetyResult brake_safety;
            bool certified_brake_found = false;
            double certified_map_age_s =
                    std::numeric_limits<double>::infinity();
            RawCloudSafetyStatus raw_brake_status =
                    RawCloudSafetyStatus::DISABLED;
            bool certified_stationary_hold = false;
            bool certified_stationary_margin_hold = false;
            bool active_yaw_stale_stationary_hold = false;
            double raw_cloud_age_s =
                    std::numeric_limits<double>::infinity();
            std::uint64_t raw_cloud_sequence = 0;
            Vec3f raw_collision_position = Vec3f::Zero();
            Trajectory ciri_shadow_candidate;
            for (int attempt = 0; attempt < 30; ++attempt) {
                auto candidate = buildBrakeTrajectory(initial, duration, start_wt);
                dynamics_ok = brakeDynamicsWithinLimits(candidate,
                                                        brake_velocity_limit,
                                                        max_velocity,
                                                        max_acc, max_jerk);
                if (dynamics_ok) {
                    const double hold_displacement =
                            (candidate.getPos(candidate.getTotalDuration()) -
                             initial.col(0)).norm();
                    const bool stationary_candidate =
                            initial.col(1).norm() <= 0.05 &&
                            std::isfinite(hold_displacement) &&
                            hold_displacement <= 0.03;
                    // Cheap copy only. Accumulation, voxelization and CIRI are
                    // performed later by the latest-only shadow worker.
                    ciri_shadow_candidate = candidate;
                    const auto health_before = map_ptr_->getMapHealthSnapshot();
                    double map_age_before_s;
                    if (!mapFreshForGuard(health_before, map_age_before_s)) {
                        brake_safety.status = TrajectorySafetyStatus::MAP_STALE;
                        brake_safety.map_version = health_before.map_version;
                        certified_map_age_s = map_age_before_s;
                        // An active-yaw acquisition can be needed precisely
                        // because the current 45-degree view contains no
                        // returns and therefore cannot refresh ROG-Map. Once
                        // independent odometry proves that the vehicle has
                        // not translated for 0.25 s, a constant-position hold
                        // plus yaw-only rotation does not introduce a swept
                        // translational volume. Check the last immutable map
                        // and supplemental raw cloud for an explicit hard
                        // conflict, but do not require that old snapshot to
                        // become fresh before rotating toward a useful view.
                        if (activeYawScanEnabled() &&
                            reason == "sector_active_yaw_goal_change" &&
                            stationary_candidate && passive_stop_stable) {
                            const auto hold_safety =
                                    planner_ptr_->validatePositionTrajectory(
                                            candidate, 0.0, 0, false, false);
                            raw_brake_status =
                                    validateTrajectoryAgainstRawCloud(
                                            candidate, 0.0,
                                            raw_collision_position,
                                            raw_cloud_age_s,
                                            raw_cloud_sequence);
                            const bool no_known_map_conflict =
                                    hold_safety.status ==
                                            TrajectorySafetyStatus::SAFE ||
                                    hold_safety.status ==
                                            TrajectorySafetyStatus::UNOBSERVED ||
                                    hold_safety.status ==
                                            TrajectorySafetyStatus::
                                                    CLEARANCE_MARGIN;
                            const bool no_raw_conflict =
                                    raw_brake_status !=
                                            RawCloudSafetyStatus::OCCUPIED &&
                                    raw_brake_status !=
                                            RawCloudSafetyStatus::
                                                    EMPTY_TRAJECTORY;
                            if (no_known_map_conflict && no_raw_conflict) {
                                brake_safety = hold_safety;
                                brake_trajectory = std::move(candidate);
                                certified_stationary_hold = true;
                                active_yaw_stale_stationary_hold = true;
                                certified_brake_found = true;
                            }
                        }
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
                    bool certificate_is_current =
                            brake_safety.safe() &&
                            map_is_fresh &&
                            brake_safety.map_version == health_after.map_version;
                    // A zero-displacement candidate is a terminal hold, not a
                    // moving brake.  Do not accept it until independent
                    // odometry has proved 0.25 s of physical stability.  Once
                    // stable, a strict SAFE result certifies the hold
                    // immediately; this avoids replaying a nominal 0.4 s
                    // brake plus another stability wait on every map-stale
                    // recovery.  The LiDAR blind region can label the current
                    // robot centre UNOBSERVED forever, so that one status is
                    // re-checked without treating unknown as occupied.
                    // OCCUPIED and clearance failures still reject, and moving
                    // brakes retain the strict unknown-as-occupied rule.
                    if (stationary_candidate && !passive_stop_stable) {
                        // All later duration attempts describe the same
                        // stationary point, so retrying them cannot improve
                        // the certificate.  Leave EMER_STOP fail-closed and
                        // let the bounded outer retry accumulate odometry
                        // stability instead.
                        certificate_is_current = false;
                        break;
                    }
                    if (stationary_candidate && certificate_is_current) {
                        certified_stationary_hold = true;
                    } else if (stoppedHoldV5Enabled() &&
                               stationary_candidate && passive_stop_stable &&
                               (brake_safety.status ==
                                        TrajectorySafetyStatus::CLEARANCE_MARGIN ||
                                brake_safety.status ==
                                        TrajectorySafetyStatus::UNOBSERVED)) {
                        // A stopped vehicle can be physically clear while its
                        // centre remains either unobserved or inside the
                        // larger planning-inflation shell.  The old relaxed
                        // UNOBSERVED retry accepted SAFE only, so a positive
                        // body clearance plus CLEARANCE_MARGIN could never
                        // enter recovery.  Re-run the entire stationary hold
                        // with the stop-only deferred-margin policy.  This
                        // still rejects every hard condition (raw OCCUPIED,
                        // out of map, version/deadline failure).  Unknown is
                        // relaxed only when it was the strict rejection.
                        const bool relaxed_unknown_as_occupied =
                                brake_safety.status !=
                                        TrajectorySafetyStatus::UNOBSERVED;
                        const auto hold_safety =
                                planner_ptr_->validatePositionTrajectory(
                                        candidate, 0.0, 0, false,
                                        relaxed_unknown_as_occupied,
                                        nullptr, false, nullptr,
                                        std::chrono::steady_clock::time_point::max(),
                                        nullptr,
                                        stop_margin::ValidationPolicy::
                                                DeferSoftMarginUntilHardChecksComplete);
                        const auto hold_health_after =
                                map_ptr_->getMapHealthSnapshot();
                        double hold_map_age_s;
                        const bool hold_map_is_fresh = mapFreshForGuard(
                                hold_health_after, hold_map_age_s);
                        const bool hold_is_admissible =
                                stop_margin::admissibleStop(
                                        hold_safety.safe(),
                                        hold_safety.status ==
                                                TrajectorySafetyStatus::
                                                        CLEARANCE_MARGIN,
                                        hold_safety.hard_checks_complete);
                        if (hold_is_admissible && hold_map_is_fresh &&
                            hold_safety.map_version ==
                                    hold_health_after.map_version) {
                            brake_safety = hold_safety;
                            certified_map_age_s = hold_map_age_s;
                            certificate_is_current = true;
                            certified_stationary_hold = true;
                            certified_stationary_margin_hold =
                                    hold_safety.status ==
                                            TrajectorySafetyStatus::
                                                    CLEARANCE_MARGIN;
                        }
                    } else if (stationary_candidate && passive_stop_stable &&
                               brake_safety.status ==
                                       TrajectorySafetyStatus::CLEARANCE_MARGIN &&
                               map_is_fresh &&
                               brake_safety.map_version ==
                                       health_after.map_version) {
                        // CLEARANCE_MARGIN is returned only after the
                        // validator has rejected unknown space and confirmed
                        // that the robot_r body offsets contain no raw
                        // occupied voxel.  For a physically stable,
                        // zero-displacement hold, requiring the larger 0.3 m
                        // planning inflation forever creates a liveness trap:
                        // the vehicle is safely stopped but can never enter
                        // the recovery planner.  Accept that margin-only case
                        // here; OCCUPIED, UNOBSERVED and moving candidates are
                        // unchanged.
                        certificate_is_current = true;
                        certified_stationary_hold = true;
                        certified_stationary_margin_hold = true;
                    } else if (stationary_candidate && passive_stop_stable &&
                               brake_safety.status ==
                                       TrajectorySafetyStatus::UNOBSERVED) {
                        const auto hold_safety =
                                planner_ptr_->validatePositionTrajectory(
                                        candidate, 0.0, 0, false, false);
                        const auto hold_health_after =
                                map_ptr_->getMapHealthSnapshot();
                        double hold_map_age_s;
                        const bool hold_map_is_fresh = mapFreshForGuard(
                                hold_health_after, hold_map_age_s);
                        if (hold_safety.safe() && hold_map_is_fresh &&
                            hold_safety.map_version ==
                                    hold_health_after.map_version) {
                            brake_safety = hold_safety;
                            certified_map_age_s = hold_map_age_s;
                            certificate_is_current = true;
                            certified_stationary_hold = true;
                        }
                    }
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
                        "motion_pose_speed={:.3f} motion_twist_speed={:.3f} "
                        "motion_disagreement={:.3f} "
                        "motion_source={} motion_gen={}/{} "
                        "motion_gen_continuous={} "
                        "last_dynamics_ok={} max_vel={:.3f} "
                        "vel_limit={:.3f} max_acc={:.3f} max_jerk={:.3f} "
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
                        recovery_pose_difference_speed,
                        recovery_odom_twist_speed,
                        recovery_pose_twist_disagreement,
                        recovery_motion_source,
                        recovery_motion_generation,
                        recovery_motion_anchor_generation,
                        recovery_motion_generation_continuous,
                        dynamics_ok, max_velocity, brake_velocity_limit,
                        max_acc, max_jerk,
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
                {
                    // Pair with pubCmdTimerCallback's final publication
                    // critical section.  Once this transition completes, an
                    // already-prepared ordinary command cannot be published.
                    std::lock_guard<std::mutex> lock(safety_mutex_);
                    if (machine_state_ != EMER_STOP) {
                        ChangeState("TrajectoryGuardFailClosed", EMER_STOP);
                    }
                }
                return false;
            }

            if (certified_stationary_hold) {
                ros_ptr_->warn(
                        " -- [TRAJ_GUARD_STATIONARY_HOLD] trigger={} "
                        "stable_for={:.3f}s displacement={:.3f}m "
                        "action={}",
                        reason,
                        selection_wt - brake_passive_stability_start_wt_,
                        (brake_trajectory.getPos(
                                 brake_trajectory.getTotalDuration()) -
                         initial.col(0)).norm(),
                        active_yaw_stale_stationary_hold
                                ? "publish_stale_map_yaw_only_hold"
                        : certified_stationary_margin_hold
                                ? "publish_physically_clear_margin_hold"
                                : "publish_certified_hold");
            }

            Eigen::Matrix<double, 3, 1> yaw_coeff;
            yaw_coeff.setZero();
            yaw_coeff(0, 0) = initial_yaw;
            Trajectory yaw_trajectory;
            yaw_trajectory.emplace_back(duration, yaw_coeff);
            yaw_trajectory.start_WT = start_wt;

            Vec3f active_scan_goal = gi_.goal_p;
            {
                std::lock_guard<std::mutex> goal_lock(pending_goal_mutex_);
                if (pending_goal_.valid) {
                    active_scan_goal = pending_goal_.goal_p;
                }
            }
            const auto active_scan_health =
                    map_ptr_->getMapHealthSnapshot();

            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                if (safety_brake_active_.load(std::memory_order_relaxed) &&
                    !replace_active_body_brake) {
                    return false;
                }
                brake_pos_traj_ = brake_trajectory;
                ++brake_command_revision_;
                if (brake_command_revision_ == 0) ++brake_command_revision_;
                brake_yaw_traj_ = yaw_trajectory;
                // A stationary fallback has already satisfied the same
                // odometry position/stability predicates required below.
                // Backdate its constant trajectory and carry that stability
                // certificate forward instead of replaying a redundant 0.4 s
                // zero-motion polynomial followed by another 0.25 s wait.
                // If recovery planning fails, getBrakeSample continues to
                // publish the terminal hold indefinitely.
                brake_start_wt_ = certified_stationary_hold
                        ? start_wt - duration : start_wt;
                brake_duration_s_ = duration;
                brake_velocity_limit_mps_ = brake_velocity_limit;
                brake_source_generation_ =
                        planner_ptr_->getCommittedTrajectoryGeneration();
                brake_yaw_ = initial_yaw;
                brake_reason_ = reason;
                active_brake_body_replaced_ = replace_active_body_brake;
                brake_stop_position_ = brake_trajectory.getPos(duration);
                if (certified_stationary_hold) {
                    brake_stability_anchor_ = brake_stop_position_;
                    brake_stability_start_wt_ =
                            brake_passive_stability_start_wt_;
                    brake_stability_started_ = true;
                } else {
                    brake_stability_started_ = false;
                }
                brake_passive_stability_started_ = false;
                brake_recovery_last_attempt_wt_ = -
                        std::numeric_limits<double>::infinity();
                safety_brake_finished_.store(certified_stationary_hold,
                                              std::memory_order_release);
                safety_brake_active_.store(true, std::memory_order_release);
                armActiveYawScanLocked(
                        initial_yaw, brake_stop_position_, active_scan_goal,
                        active_scan_health.map_version,
                        active_scan_health.processed_scan_count, 0, true);
            }

            const Vec3f stop_position = brake_trajectory.getPos(duration);
            ros_ptr_->error(" -- [TRAJ_GUARD_BRAKE] trigger={} duration={:.3f}s "
                            "speed0={:.3f} initial_source={} cmd_age={:.3f}s "
                            "cmd_pos_err={:.3f} cmd_vel_err={:.3f} "
                            "motion_speed={:.3f} motion_dt={:.3f}s "
                            "motion_pose_speed={:.3f} motion_twist_speed={:.3f} "
                            "motion_disagreement={:.3f} "
                            "motion_source={} motion_gen={}/{} "
                            "motion_gen_continuous={} "
                            "max_vel={:.3f} vel_limit={:.3f} "
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
                            recovery_motion_dt_s,
                            recovery_pose_difference_speed,
                            recovery_odom_twist_speed,
                            recovery_pose_twist_disagreement,
                            recovery_motion_source,
                            recovery_motion_generation,
                            recovery_motion_anchor_generation,
                            recovery_motion_generation_continuous,
                            max_velocity, brake_velocity_limit,
                            max_acc, max_jerk,
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
                                     brake_message, true,
                                     brake_source_generation_);
            mpc_cmd_pub_->publish(brake_message);
            ChangeState("TrajectoryGuard", EMER_STOP);
            return true;
        }

        bool getBrakeSample(CmdTraj::Sample &sample,
                            async_recovery::BrakeCommandIdentity* identity = nullptr,
                            double* velocity_limit = nullptr) {
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
            sample.generation = brake_source_generation_;
            sample.trajectory_time = eval_tt;
            sample.total_duration = brake_duration_s_;
            sample.finished = raw_tt >= brake_duration_s_;
            sample.on_backup = true;
            if (activeYawScanEnabled() &&
                active_yaw_scan_.episode_active &&
                active_yaw_scan_.command_active) {
                if (sample.finished &&
                    !active_yaw_scan_.rotation_started) {
                    active_yaw_scan_.rotation_started = true;
                    active_yaw_scan_.start_wt = ros_ptr_->getSimTime();
                }
                if (active_yaw_scan_.rotation_started) {
                    const auto yaw_command = active_yaw_scan::command(
                            active_yaw_scan_.start_yaw,
                            active_yaw_scan_.target_yaw,
                            ros_ptr_->getSimTime() -
                                    active_yaw_scan_.start_wt,
                            40.0 * active_yaw_scan::kPi / 180.0);
                    sample.yaw = yaw_command.yaw;
                    sample.yaw_dot = yaw_command.yaw_rate;
                } else {
                    sample.yaw = brake_yaw_;
                    sample.yaw_dot = 0.0;
                }
            } else {
                sample.yaw = activeYawScanEnabled() &&
                        active_yaw_scan_.episode_active
                        ? active_yaw_scan_.target_yaw : brake_yaw_;
                sample.yaw_dot = 0.0;
            }
            if (identity) *identity = {brake_command_revision_, brake_source_generation_, brake_start_wt_};
            if (velocity_limit) *velocity_limit = brake_velocity_limit_mps_;
            if (sample.finished) {
                sample.pvaj.col(1).setZero();
                sample.pvaj.col(2).setZero();
                sample.pvaj.col(3).setZero();
                safety_brake_finished_.store(true, std::memory_order_release);
            }
            return true;
        }

        double getBrakeVelocityLimit() const {
            std::lock_guard<std::mutex> lock(safety_mutex_);
            return brake_velocity_limit_mps_;
        }

        bool getExecutableSampleForBrake(CmdTraj::Sample& sample) const {
            if (!asyncGenerateEnabled()) return planner_ptr_->getOneCommandSample(sample);
            std::lock_guard<std::mutex> safety(safety_mutex_);
            if (async_generate_quarantine_.load(std::memory_order_acquire)) {
                if (!async_generate_hold_certificate_valid_ ||
                    !asyncGenerateHoldPoseValidLocked() ||
                    !async_from_rest::mayUsePlannerSampleForBrake(true,
                            async_generate_hold_sample_.generation,
                            async_generate_hold_sample_.generation)) return false;
                sample = async_generate_hold_sample_;
                return true;
            }
            return planner_ptr_->getOneCommandSample(sample);
        }

        // Caller owns activation -> refresh -> safety -> goal locks.
        async_from_rest::Identity asyncGenerateIdentityLocked(
                const std::uint64_t id, const std::uint64_t generation_before) const {
            async_from_rest::Identity identity;
            identity.id = id;
            identity.hold_revision = async_generate_hold_revision_;
            identity.generation_before = generation_before;
            identity.goal_queued = queued_goal_revision_;
            identity.goal_accepted = accepted_goal_revision_;
            identity.brake_revision = brake_activation_revision_;
            identity.event_requested = event_recovery_requested_.load(std::memory_order_acquire);
            identity.event_completed = event_recovery_completed_.load(std::memory_order_acquire);
            if (required_full_refresh_min_seq_ != 0 ||
                trajectory_guard_recovery_announced_.load(std::memory_order_acquire)) {
                identity.ack = startupRecoveryAckLocked();
            } else {
                // Configuring event recovery does not require a Full burst for
                // every ordinary PlanFromRest. Only an armed gate requires ACK.
                identity.ack.supported = true;
                identity.ack.required = false;
                identity.ack.advertised_or_event = false;
            }
            return identity;
        }

        bool asyncGenerateStationaryTwist(const double now) const {
            Vec3f velocity = Vec3f::Zero();
            double receive_time = std::numeric_limits<double>::quiet_NaN();
            const bool available = map_ptr_->getLatestOdomTwist(velocity, receive_time);
            // getLatestOdomTwist timestamps receipt on the ROS node clock,
            // which is also the clock returned by ros_ptr_->getSimTime().
            return velocity.array().isFinite().all() &&
                    async_from_rest::freshStationaryTwist(
                            available, velocity.norm(), receive_time, now);
        }

        bool asyncGenerateHoldPoseValidLocked(const bool require_stability = true) const {
            const auto odom = map_ptr_->getRobotState();
            const double now = ros_ptr_->getSimTime();
            return async_generate_quarantine_.load(std::memory_order_acquire) &&
                    odom.rcv && std::isfinite(odom.rcv_time) && std::isfinite(now) &&
                    now >= odom.rcv_time && now - odom.rcv_time <= 0.1 &&
                    odom.p.array().isFinite().all() &&
                    asyncGenerateStationaryTwist(now) &&
                    (odom.p - async_generate_hold_sample_.pvaj.col(0)).norm() <= 0.03 &&
                    now >= async_generate_hold_since_ &&
                    (!require_stability || now - async_generate_hold_since_ >= 0.25);
        }

        // The pinned stationary point is rechecked against new committed maps.
        // This reads map geometry, not the optimizer's mutable RobotState/cache.
        bool refreshAsyncGenerateHold() {
            Trajectory geometry;
            std::uint64_t revision = 0, generation = 0;
            const auto health = map_ptr_->getMapHealthSnapshot();
            double age = 0.0;
            {
                std::lock_guard<std::mutex> safety(safety_mutex_);
                if (!asyncGenerateHoldPoseValidLocked(false) ||
                    !mapFreshForGuard(health, age)) return false;
                if (async_generate_hold_certificate_valid_ &&
                    async_generate_hold_certificate_.safe() &&
                    async_generate_hold_certificate_.map_version == health.map_version) return true;
                geometry = async_generate_hold_geometry_;
                revision = async_generate_hold_revision_;
                generation = async_generate_hold_sample_.generation;
            }
            const auto certificate = planner_ptr_->validatePositionTrajectory(
                    geometry, geometry.getTotalDuration(), generation, false, false);
            const auto after = map_ptr_->getMapHealthSnapshot();
            std::lock_guard<std::mutex> safety(safety_mutex_);
            if (!async_generate_quarantine_.load(std::memory_order_acquire) ||
                revision != async_generate_hold_revision_) return false;
            async_generate_hold_certificate_ = certificate;
            async_generate_hold_certificate_valid_ = certificate.safe() &&
                    certificate.map_version == after.map_version && mapFreshForGuard(after, age) &&
                    asyncGenerateHoldPoseValidLocked(false);
            return async_generate_hold_certificate_valid_;
        }

        // Called with safety_mutex_: a failed/discarded receipt must NOT call
        // this, because its internal committed path is still unpublished.
        void clearAsyncGenerateQuarantineLocked() {
            async_generate_request_identity_.reset();
            async_generate_hold_certificate_valid_ = false;
            async_generate_previous_ = CmdTraj::SharedSnapshot{};
            async_generate_hold_geometry_ = Trajectory{};
            async_generate_quarantine_.store(false, std::memory_order_release);
        }

        bool dispatchGenerateTrajectoryAsync() override {
            if (!asyncGenerateEnabled()) return false;
            // The legacy certified-brake path remains synchronous when its
            // separate async option is disabled; it already owns a safe hold.
            if (safety_brake_active_.load(std::memory_order_acquire)) return false;
            if (async_generate_slot_.busy() || async_recovery_slot_.busy()) return true;
            bool startup_wait = false;
            auto startup = captureStartupRecoveryBeforeMain(startup_wait);
            if (startup_wait) return true;
            std::unique_lock<std::mutex> activation(brake_activation_mutex_, std::try_to_lock);
            if (!activation || stop.load(std::memory_order_acquire) ||
                safety_brake_active_.load(std::memory_order_acquire) ||
                machine_state_.load(std::memory_order_acquire) != GENERATE_TRAJ) return true;
            const auto odom = map_ptr_->getRobotState();
            const double now = ros_ptr_->getSimTime();
            if (!odom.rcv || !std::isfinite(now) || !std::isfinite(odom.rcv_time) ||
                now < odom.rcv_time || now - odom.rcv_time > 0.1 ||
                !odom.p.array().isFinite().all()) return true;
            bool needs_stop = !asyncGenerateStationaryTwist(now);
            {
                std::lock_guard<std::mutex> safety(safety_mutex_);
                if (!async_generate_quarantine_.load(std::memory_order_acquire)) {
                    const auto previous = planner_ptr_->getCommittedSharedTrajectorySnapshot();
                    CmdTraj::Sample held;
                    if (!previous.empty) {
                        if (!planner_ptr_->getOneCommandSample(held, previous.generation) ||
                            !held.finished || !held.pvaj.array().isFinite().all() ||
                            held.pvaj.col(1).norm() > 0.05 ||
                            (held.pvaj.col(0) - odom.p).norm() > 0.03) {
                            needs_stop = true;
                        }
                    } else {
                        held.pvaj.setZero();
                        held.pvaj.col(0) = odom.p;
                        held.yaw = std::isfinite(odom.yaw) ? odom.yaw : 0.0;
                        held.finished = true;
                    }
                    if (!needs_stop) {
                        // A finished polynomial's higher derivatives are not
                        // a stationary command; pin its exact terminal position.
                        held.pvaj.col(1).setZero();
                        held.pvaj.col(2).setZero();
                        held.pvaj.col(3).setZero();
                        held.yaw_dot = 0.0;
                        async_generate_previous_ = previous;
                        async_generate_hold_sample_ = held;
                        Eigen::MatrixXd coefficients = Eigen::MatrixXd::Zero(3, 6);
                        coefficients.col(5) = held.pvaj.col(0);
                        async_generate_hold_geometry_.clear();
                        async_generate_hold_geometry_.emplace_back(0.01, coefficients);
                        async_generate_hold_geometry_.start_WT = now;
                        async_generate_hold_since_ = now;
                        ++async_generate_hold_revision_;
                        if (async_generate_hold_revision_ == 0) ++async_generate_hold_revision_;
                        async_generate_hold_certificate_valid_ = false;
                        async_generate_quarantine_.store(true, std::memory_order_release);
                    }
                }
            }
            if (needs_stop) {
                activation.unlock();
                activateEmergencyBrake("async_generate_requires_certified_stop");
                return true;
            }
            if (!refreshAsyncGenerateHold()) {
                activation.unlock();
                activateEmergencyBrake("async_generate_hold_uncertified");
                return true;
            }
            AsyncGenerateRequest request;
            {
                std::lock_guard<std::mutex> refresh(full_refresh_mutex_);
                std::lock_guard<std::mutex> safety(safety_mutex_);
                std::lock_guard<std::mutex> goal(pending_goal_mutex_);
                if (!asyncGenerateHoldPoseValidLocked() || pending_goal_.valid ||
                    goal_update_in_progress_) return true;
                request.identity = asyncGenerateIdentityLocked(
                        ++async_generate_next_id_, planner_ptr_->getCommittedTrajectoryGeneration());
                if (!async_from_rest::ready(request.identity)) return true;
                request.goal = gi_.goal_p;
                request.goal_yaw = gi_.goal_yaw;
                request.new_goal = gi_.new_goal;
                request.raw_goal = accepted_raw_goal_request_;
                request.startup = startup;
                if (startup.armed && async_generate_previous_.empty &&
                    async_generate_previous_.generation == 0) {
                    // A discarded internally committed startup result is not
                    // a previously executable path. Retain the original empty
                    // publication history for the startup completion contract.
                    request.startup.empty_snapshot = true;
                    request.startup.generation = 0;
                }
                if (!async_generate_slot_.submit(request)) return true;
                async_generate_request_identity_ = request;
                ++async_generate_requests_;
            }
            ros_ptr_->info(" -- [ASYNC_GENERATE_REQUEST] id={} hold_revision={} generation_before={} "
                           "goal_queued={} goal_accepted={} ack_required={} ack_map={}",
                           request.identity.id, request.identity.hold_revision,
                           request.identity.generation_before, request.identity.goal_queued,
                           request.identity.goal_accepted, request.identity.ack.required,
                           request.identity.ack.map);
            return true;
        }

        bool serviceAsyncGenerateTrajectory() {
            if (!asyncGenerateEnabled()) return false;
            const auto request = async_generate_slot_.begin();
            if (!request) return async_generate_slot_.busy();
            AsyncGenerateResult result;
            result.request = *request;
            bool may_compute = false;
            {
                std::unique_lock<std::mutex> activation(brake_activation_mutex_, std::try_to_lock);
                if (activation) {
                    const auto health = map_ptr_->getMapHealthSnapshot();
                    double age = 0.0;
                    std::lock_guard<std::mutex> refresh(full_refresh_mutex_);
                    std::lock_guard<std::mutex> safety(safety_mutex_);
                    std::lock_guard<std::mutex> goal(pending_goal_mutex_);
                    const auto current = asyncGenerateIdentityLocked(
                            request->identity.id, request->identity.generation_before);
                    may_compute = async_from_rest::sameDemand(request->identity, current) &&
                            !stop.load(std::memory_order_acquire) &&
                            !safety_brake_active_.load(std::memory_order_acquire) &&
                            machine_state_.load(std::memory_order_acquire) == GENERATE_TRAJ &&
                            !pending_goal_.valid && !goal_update_in_progress_ &&
                            asyncGenerateHoldPoseValidLocked() && mapFreshForGuard(health, age) &&
                            (!health.update_in_progress || map_ptr_->immutablePlannerSnapshotEnabled()) &&
                            (!current.ack.required || health.map_version >= current.ack.map) &&
                            planner_ptr_->getCommittedTrajectoryGeneration() == request->identity.generation_before;
                }
            }
            if (may_compute) {
                try {
                    const super_utils::thread_cpu_profile::Scope compute_scope(
                            super_utils::thread_cpu_profile::Stage::FsmReplanCore);
                    rog_map::RobotState optimizer_state;
                    planner_ptr_->getRobotState(optimizer_state);
                    result.ret_code = planner_ptr_->PlanFromRest(
                            request->goal, request->goal_yaw, request->new_goal);
                    result.computed = true;
                    result.goal_valid = planner_ptr_->goalValid();
                    result.rejected = planner_ptr_->consumeTrajectoryGuardRejection();
                    result.generation_after = planner_ptr_->getCommittedTrajectoryGeneration();
                    result.reason = "computed";
                    recordLatestReplanLog();
                } catch (const std::exception& error) {
                    result.reason = "compute_exception";
                    ros_ptr_->error(" -- [ASYNC_GENERATE_EXCEPTION] id={} what={} action=retain_hold",
                                    request->identity.id, error.what());
                }
            }
            async_generate_slot_.finish(std::move(result));
            return true;
        }

        // Return true when this receipt was drained, not when it was accepted.
        bool finishAsyncGenerateTrajectory(const AsyncGenerateResult& result) {
            const auto& before = result.request.identity;
            std::unique_lock<std::mutex> activation(brake_activation_mutex_, std::try_to_lock);
            if (!activation) return false;
            bool eligible = false;
            StatePVAJ held_pva = StatePVAJ::Zero();
            std::uint64_t release_map_version = 0;
            {
                std::lock_guard<std::mutex> refresh(full_refresh_mutex_);
                std::lock_guard<std::mutex> safety(safety_mutex_);
                std::lock_guard<std::mutex> goal(pending_goal_mutex_);
                eligible = async_from_rest::sameDemand(before,
                        asyncGenerateIdentityLocked(before.id, before.generation_before)) &&
                        !pending_goal_.valid && !goal_update_in_progress_ &&
                        !stop.load(std::memory_order_acquire) &&
                        !safety_brake_active_.load(std::memory_order_acquire) &&
                        machine_state_.load(std::memory_order_acquire) == GENERATE_TRAJ &&
                        asyncGenerateHoldPoseValidLocked();
                if (eligible) {
                    held_pva = async_generate_hold_sample_.pvaj;
                    release_map_version =
                            map_ptr_->getMapHealthSnapshot().map_version;
                }
            }
            const bool worker_success = eligible && result.computed &&
                    result.goal_valid && !result.rejected &&
                    (result.ret_code == super_utils::SUCCESS ||
                     result.ret_code == super_utils::FINISH);
            StoppedDepartureRelease stopped_release;
            bool release_ready = !stoppedDepartureV4Enabled();
            bool refreshed = worker_success && refreshAsyncGenerateHold() &&
                    (stoppedDepartureV4Enabled()
                            ? refreshStoppedDepartureCertificate(
                                    result.generation_after,
                                    release_map_version,
                                    "async_generate_complete")
                            : refreshSafetyCertificate(
                                    "async_generate_complete"));
            const auto snapshot = planner_ptr_->getCommittedSharedTrajectorySnapshot();
            CmdTraj::Sample sample;
            bool sample_valid = false;
            if (stoppedDepartureV4Enabled() && !snapshot.empty &&
                snapshot.generation == result.generation_after &&
                snapshot.pos_traj && !snapshot.pos_traj->empty()) {
                sample = CmdTraj::Sample{};
                sample_valid = snapshot.pos_traj->getState(0.0, sample.pvaj);
                sample.generation = snapshot.generation;
                sample.start_wt = snapshot.start_wt;
                sample.trajectory_time = 0.0;
                sample.total_duration = snapshot.total_duration;
                sample.finished = false;
                if (snapshot.yaw_traj && !snapshot.yaw_traj->empty()) {
                    sample.yaw = snapshot.yaw_traj->getPos(0.0)[0];
                    sample.yaw_dot = snapshot.yaw_traj->getVel(0.0)[0];
                }
            } else sample_valid = !snapshot.empty &&
                    planner_ptr_->getOneCommandSample(sample, result.generation_after);
            sample_valid = sample_valid &&
                    sample.pvaj.array().isFinite().all() && std::isfinite(sample.trajectory_time) &&
                    std::isfinite(sample.start_wt) && std::isfinite(sample.yaw) &&
                    std::isfinite(sample.yaw_dot);
            mars_quadrotor_msgs::msg::PolynomialTrajectory message;
            bool velocity_valid = false;
            if (refreshed && sample_valid && !sample.finished && snapshot.pos_traj && snapshot.yaw_traj) {
                const double limit = planner_ptr_->getConfiguredMaxVelocity();
                const double maximum = snapshot.pos_traj->getMaxVelRate();
                velocity_valid = std::isfinite(limit) && limit > 0.0 &&
                        std::isfinite(maximum) && maximum <= limit * 1.001;
                if (velocity_valid) fillPolynomialTrajectory(
                        *snapshot.pos_traj, *snapshot.yaw_traj, message, false, snapshot.generation);
            }
            bool completed = false;
            super_planner::trajectory_handoff::Result handoff;
            double handoff_wt = std::numeric_limits<double>::quiet_NaN();
            {
                std::lock_guard<std::mutex> refresh(full_refresh_mutex_);
                std::lock_guard<std::mutex> safety(safety_mutex_);
                std::lock_guard<std::mutex> goal(pending_goal_mutex_);
                const auto current = asyncGenerateIdentityLocked(before.id, before.generation_before);
                const auto health = map_ptr_->getMapHealthSnapshot();
                double age = 0.0;
                // Sample at final publication time, under the same lock as
                // held-command publication/release. Do not use an earlier
                // pre-serialization sample to authorize a solve-start clock.
                handoff_wt = ros_ptr_->getSimTime();
                if (stoppedDepartureV4Enabled()) {
                    const bool final_identity_current =
                            async_from_rest::sameDemand(before, current) &&
                            !pending_goal_.valid && !goal_update_in_progress_ &&
                            !stop.load(std::memory_order_acquire) &&
                            !safety_brake_active_.load(std::memory_order_acquire) &&
                            machine_state_.load(std::memory_order_acquire) == GENERATE_TRAJ &&
                            asyncGenerateHoldPoseValidLocked() &&
                            health.map_version == release_map_version;
                    if (refreshed && final_identity_current) {
                        stopped_release = planner_ptr_->releaseStoppedDeparture(
                                result.generation_after,
                                release_map_version, handoff_wt, held_pva);
                    }
                    release_ready = stopped_release.accepted;
                    handoff_wt = stopped_release.release_wt;
                    if (release_ready) {
                        message.start_wt_pos = handoff_wt;
                        if (snapshot.yaw_traj && !snapshot.yaw_traj->empty()) {
                            message.start_wt_yaw = handoff_wt;
                        }
                        ros_ptr_->getSimTime(message.header.stamp.sec,
                                             message.header.stamp.nanosec);
                        sample.start_wt = handoff_wt;
                        sample.trajectory_time = 0.0;
                    }
                }
                if (stoppedDepartureV4Enabled()) {
                    handoff.continuous = stopped_release.accepted;
                    handoff.reason = stopped_release.accepted
                            ? "CONTINUOUS" : stopped_release.reason.c_str();
                    handoff.position_error_m = stopped_release.position_error_m;
                    handoff.velocity_error_mps = stopped_release.velocity_error_mps;
                    handoff.acceleration_error_mps2 =
                            stopped_release.acceleration_error_mps2;
                } else handoff = super_planner::trajectory_handoff::compareAt<StatePVAJ>(
                        handoff_wt,
                        [&](double, StatePVAJ& state) {
                            state = async_generate_hold_sample_.pvaj;
                            return asyncGenerateHoldPoseValidLocked();
                        },
                        [&](const double wt, StatePVAJ& state) {
                            if (!snapshot.pos_traj || snapshot.empty) return false;
                            const double tt = wt - snapshot.start_wt;
                            if (!std::isfinite(tt) || tt < 0.0 || tt >= snapshot.total_duration ||
                                !snapshot.pos_traj->getState(tt, state)) return false;
                            sample.pvaj = state;
                            sample.trajectory_time = tt;
                            sample.finished = false;
                            return state.array().isFinite().all();
                        });
                async_from_rest::Completion proof;
                proof.successful = result.computed &&
                        (result.ret_code == super_utils::SUCCESS || result.ret_code == super_utils::FINISH) &&
                        release_ready;
                proof.rejected = result.rejected;
                proof.goal_valid = result.goal_valid;
                proof.generating = machine_state_.load(std::memory_order_acquire) == GENERATE_TRAJ;
                proof.no_active_brake = !safety_brake_active_.load(std::memory_order_acquire);
                proof.hold_current = asyncGenerateHoldPoseValidLocked() &&
                        async_generate_hold_certificate_valid_ &&
                        async_generate_hold_certificate_.map_version == health.map_version;
                proof.no_pending_goal = !pending_goal_.valid && !goal_update_in_progress_;
                proof.not_stopped = !stop.load(std::memory_order_acquire);
                proof.map_fresh = mapFreshForGuard(health, age) &&
                        (!health.update_in_progress || map_ptr_->immutablePlannerSnapshotEnabled()) &&
                        (!stoppedDepartureV4Enabled() ||
                         health.map_version == stopped_release.map_version);
                proof.certificate_safe = refreshed && safety_certificate_valid_ && safety_certificate_.safe();
                proof.certificate_current = safety_certificate_.trajectory_generation == result.generation_after &&
                        safety_certificate_.map_version == health.map_version &&
                        !safety_revalidation_requested_.load(std::memory_order_acquire) &&
                        safety_certificate_.checked_from_tt <= sample.trajectory_time &&
                        safety_certificate_.checked_to_tt >= sample.trajectory_time;
                proof.sample_valid = sample_valid && snapshot.generation == result.generation_after;
                proof.sample_finished = sample.finished;
                proof.velocity_valid = velocity_valid;
                proof.handoff_continuous = handoff.continuous;
                proof.result_generation = result.generation_after;
                proof.current_generation = planner_ptr_->getCommittedTrajectoryGeneration();
                proof.current_map = health.map_version;
                completed = async_from_rest::mayComplete(before, current, proof);
                if (completed) {
                    gi_.new_goal = false;
                    plan_from_rest_.store(true, std::memory_order_release);
                    finish_plan.store(result.ret_code == super_utils::FINISH, std::memory_order_release);
                    if (goalRetransmitIdentityEnabled()) invalidateGoalRetransmissionTokenLocked();
                    machine_state_.store(FOLLOW_TRAJ, std::memory_order_release);
                    clearAsyncGenerateQuarantineLocked();
                    mpc_cmd_pub_->publish(message);
                } else {
                    async_generate_request_identity_.reset();
                }
            }
            async_generate_slot_.release(before.id);
            if (completed) ++async_generate_completed_;
            else ++async_generate_discarded_;
            if (eligible && result.computed && !result.rejected && !handoff.continuous) {
                ros_ptr_->warn(" -- [ASYNC_GENERATE_HANDOFF_REJECT] id={} reason={} wt={:.9f} "
                               "generation={} position_error_m={:.9f} velocity_error_mps={:.9f} "
                               "acceleration_error_mps2={:.9f} action=retain_hold",
                               before.id, handoff.reason, handoff_wt, result.generation_after,
                               handoff.position_error_m, handoff.velocity_error_mps,
                               handoff.acceleration_error_mps2);
            }
            ros_ptr_->info(" -- [ASYNC_GENERATE_RESULT] id={} computed={} completed={} reason={} "
                           "generation_before={} generation_after={} dispatched_total={} "
                           "completed_total={} discarded_total={}",
                           before.id, result.computed, completed, result.reason,
                           before.generation_before, result.generation_after, async_generate_requests_,
                           async_generate_completed_, async_generate_discarded_);
            activation.unlock();
            if (result.computed) ros_ptr_->pubReplanStatus(completed);
            if (completed) {
                tryCompleteStartupRecovery(result.request.startup);
            } else if (eligible && result.computed && result.rejected) {
                activateEmergencyBrake("candidate_rejected_without_safe_follow");
            } else if (eligible && result.computed && !result.goal_valid) {
                gi_.new_goal = false;
                ChangeState("AsyncGenerateInvalidGoal", WAIT_GOAL);
            }
            return true;
        }

        bool ignoreExactInFlightGenerateReplay(const goal_retransmit::Request& incoming) {
            if (!asyncGenerateEnabled() || !async_generate_slot_.busy()) return false;
            std::unique_lock<std::mutex> activation(brake_activation_mutex_, std::try_to_lock);
            if (!activation) return false;
            std::lock_guard<std::mutex> refresh(full_refresh_mutex_);
            std::lock_guard<std::mutex> safety(safety_mutex_);
            std::lock_guard<std::mutex> goal(pending_goal_mutex_);
            if (!async_generate_request_identity_) return false;
            const auto& request = *async_generate_request_identity_;
            const auto current = asyncGenerateIdentityLocked(request.identity.id,
                                                             request.identity.generation_before);
            if (!async_from_rest::mayIgnoreExactInFlightReplay(
                        async_generate_slot_.busy(), !pending_goal_.valid && !goal_update_in_progress_,
                        accepted_raw_goal_source_revision_ == queued_goal_revision_,
                        request.identity, current, request.raw_goal, accepted_raw_goal_request_, incoming)) return false;
            ++async_generate_exact_replays_;
            ros_ptr_->info(" -- [ASYNC_GENERATE_EXACT_GOAL_REPLAY] id={} stamp_ns={} count={}",
                           request.identity.id, incoming.creation_stamp_ns, async_generate_exact_replays_);
            return true;
        }

        // Caller owns activation -> full-refresh -> safety -> pending-goal
        // locks, or (for read-only fields) the corresponding earlier locks.
        async_recovery::Identity asyncRecoveryIdentityLocked(
                const std::uint64_t id, const std::uint64_t generation_before) const {
            async_recovery::Identity identity;
            identity.id = id;
            identity.brake_revision = brake_activation_revision_;
            identity.generation_before = generation_before;
            identity.goal_queued = queued_goal_revision_;
            identity.goal_accepted = accepted_goal_revision_;
            identity.event_requested = event_recovery_requested_.load(std::memory_order_acquire);
            identity.event_completed = event_recovery_completed_.load(std::memory_order_acquire);
            identity.ack = startupRecoveryAckLocked();
            return identity;
        }

        // No planner getRobotState(): that legacy accessor also writes the
        // optimizer's mutable cache. This read is safe while its solve runs.
        bool asyncRecoveryStablePoseLocked() const {
            const auto odom = map_ptr_->getRobotState();
            const double now = ros_ptr_->getSimTime();
            return odom.rcv && std::isfinite(odom.rcv_time) &&
                    now >= odom.rcv_time && now - odom.rcv_time <= 0.1 &&
                    odom.p.array().isFinite().all() &&
                    (odom.p - brake_stop_position_).norm() <= 0.15 &&
                    brake_stability_started_ &&
                    (odom.p - brake_stability_anchor_).norm() <= 0.03 &&
                    now >= brake_stability_start_wt_ &&
                    now - brake_stability_start_wt_ >= 0.25;
        }

        // Runs inside the EXISTING mutually-exclusive replan callback, after
        // its CPU/timing scopes. It never changes the FSM state, clears a brake,
        // emits a command polynomial, or closes Full sensing. Planner
        // visualization remains unchanged. Committed candidates remain
        // inaccessible to ordinary commands because the certified hold stays
        // active until main-side finalization, and Ready reserves this executor.
        bool serviceAsyncCertifiedRecovery() {
            if (!asyncCertifiedRecoveryEnabled()) return false;
            const auto request = async_recovery_slot_.begin();
            if (!request) return async_recovery_slot_.busy();
            AsyncRecoveryResult result;
            result.request = *request;
            bool may_compute = false;
            {
                std::unique_lock<std::mutex> activation(brake_activation_mutex_, std::try_to_lock);
                if (activation) {
                    const auto health = map_ptr_->getMapHealthSnapshot();
                    double age = 0.0;
                    std::lock_guard<std::mutex> refresh(full_refresh_mutex_);
                    std::lock_guard<std::mutex> safety(safety_mutex_);
                    std::lock_guard<std::mutex> goal(pending_goal_mutex_);
                    const auto current = asyncRecoveryIdentityLocked(
                            request->identity.id, request->identity.generation_before);
                    may_compute = async_recovery::sameDemand(request->identity, current) &&
                            !stop.load(std::memory_order_acquire) &&
                            safety_brake_active_.load(std::memory_order_acquire) &&
                            safety_brake_finished_.load(std::memory_order_acquire) &&
                            !pending_goal_.valid && !goal_update_in_progress_ &&
                            asyncRecoveryStablePoseLocked() && mapFreshForGuard(health, age) &&
                            (!health.update_in_progress || map_ptr_->immutablePlannerSnapshotEnabled()) &&
                            (!current.ack.required || health.map_version >= current.ack.map) &&
                            planner_ptr_->getCommittedTrajectoryGeneration() ==
                                    request->identity.generation_before;
                    if (may_compute) planner_ptr_->setCertifiedStopForReroute(true);
                }
            }
            if (may_compute) {
                try {
                    const super_utils::thread_cpu_profile::Scope compute_scope(
                            super_utils::thread_cpu_profile::Stage::FsmReplanCore);
                    rog_map::RobotState optimizer_state;
                    planner_ptr_->getRobotState(optimizer_state);
                    result.ret_code = planner_ptr_->PlanFromRest(
                            request->goal, request->goal_yaw, request->new_goal);
                    result.computed = true;
                    result.goal_valid = planner_ptr_->goalValid();
                    result.rejected = planner_ptr_->consumeTrajectoryGuardRejection();
                    result.generation_after = planner_ptr_->getCommittedTrajectoryGeneration();
                    // This executor is the sole planner/log writer during the
                    // reservation; no result contains an unbounded SFC cloud.
                    recordLatestReplanLog();
                } catch (const std::exception& error) {
                    result.ret_code = super_utils::FAILED;
                    result.rejected = true;
                    ros_ptr_->error(" -- [ASYNC_RECOVERY_RESULT] id={} exception={} action=retain_hold",
                                    request->identity.id, error.what());
                }
            }
            async_recovery_slot_.finish(std::move(result));
            return true;
        }

        bool finishAsyncCertifiedRecovery(const AsyncRecoveryResult& result) {
            const auto& before = result.request.identity;
            std::unique_lock<std::mutex> activation(brake_activation_mutex_, std::try_to_lock);
            if (!activation) return false;  // Retry this receipt; do not wait on brake construction.

            CmdTraj::Sample brake_hold;
            const bool brake_hold_valid = !stoppedDepartureV4Enabled() ||
                    getBrakeSample(brake_hold);
            const auto release_health = map_ptr_->getMapHealthSnapshot();
            const bool worker_success = result.computed &&
                    (result.ret_code == super_utils::SUCCESS ||
                     result.ret_code == super_utils::FINISH) &&
                    result.goal_valid && !result.rejected &&
                    before.brake_revision == brake_activation_revision_ &&
                    safety_brake_active_.load(std::memory_order_acquire) &&
                    safety_brake_finished_.load(std::memory_order_acquire) &&
                    asyncRecoveryStablePoseLocked() && brake_hold_valid;
            StoppedDepartureRelease stopped_release;
            bool release_ready = !stoppedDepartureV4Enabled();
            // Only main performs the live geometric certificate refresh. No
            // success from an old worker is substituted for current evidence.
            bool refreshed = false;
            if (worker_success) {
                refreshed = stoppedDepartureV4Enabled()
                        ? refreshStoppedDepartureCertificate(
                                result.generation_after,
                                release_health.map_version,
                                "async_brake_recovery")
                        : refreshSafetyCertificate("async_brake_recovery");
            }
            const auto snapshot = planner_ptr_->getCommittedSharedTrajectorySnapshot();
            CmdTraj::Sample sample;
            bool sample_valid = false;
            if (stoppedDepartureV4Enabled() && !snapshot.empty &&
                snapshot.generation == result.generation_after &&
                snapshot.pos_traj && !snapshot.pos_traj->empty()) {
                sample = CmdTraj::Sample{};
                sample_valid = snapshot.pos_traj->getState(0.0, sample.pvaj);
                sample.generation = snapshot.generation;
                sample.start_wt = snapshot.start_wt;
                sample.trajectory_time = 0.0;
                sample.total_duration = snapshot.total_duration;
                sample.finished = false;
                if (snapshot.yaw_traj && !snapshot.yaw_traj->empty()) {
                    sample.yaw = snapshot.yaw_traj->getPos(0.0)[0];
                    sample.yaw_dot = snapshot.yaw_traj->getVel(0.0)[0];
                }
            } else sample_valid = !snapshot.empty &&
                    planner_ptr_->getOneCommandSample(sample,
                                                      result.generation_after);
            sample_valid = sample_valid &&
                    sample.pvaj.array().isFinite().all() &&
                    std::isfinite(sample.trajectory_time) && std::isfinite(sample.start_wt) &&
                    std::isfinite(sample.yaw) && std::isfinite(sample.yaw_dot);
            mars_quadrotor_msgs::msg::PolynomialTrajectory message;
            bool velocity_valid = false;
            if (refreshed && sample_valid && !sample.finished && snapshot.pos_traj && snapshot.yaw_traj) {
                const double limit = planner_ptr_->getConfiguredMaxVelocity();
                const double maximum = snapshot.pos_traj->getMaxVelRate();
                velocity_valid = std::isfinite(limit) && limit > 0.0 &&
                        std::isfinite(maximum) && maximum <= limit * 1.001;
                if (velocity_valid) fillPolynomialTrajectory(
                        *snapshot.pos_traj, *snapshot.yaw_traj, message, false, snapshot.generation);
            }
            bool completed = false;
            std::string recovered_reason;
            std::uint64_t certified_map = 0;
            {
                std::lock_guard<std::mutex> refresh(full_refresh_mutex_);
                std::lock_guard<std::mutex> safety(safety_mutex_);
                std::lock_guard<std::mutex> goal(pending_goal_mutex_);
                const auto current = asyncRecoveryIdentityLocked(before.id, before.generation_before);
                const auto health = map_ptr_->getMapHealthSnapshot();
                double age = 0.0;
                if (stoppedDepartureV4Enabled()) {
                    const bool final_identity_current =
                            async_recovery::sameDemand(before, current) &&
                            safety_brake_active_.load(std::memory_order_acquire) &&
                            safety_brake_finished_.load(std::memory_order_acquire) &&
                            asyncRecoveryStablePoseLocked() &&
                            !pending_goal_.valid && !goal_update_in_progress_ &&
                            !stop.load(std::memory_order_acquire) &&
                            health.map_version == release_health.map_version;
                    if (refreshed && final_identity_current) {
                        stopped_release = planner_ptr_->releaseStoppedDeparture(
                                result.generation_after,
                                release_health.map_version,
                                ros_ptr_->getSimTime(), brake_hold.pvaj);
                    }
                    release_ready = stopped_release.accepted;
                    if (release_ready) {
                        message.start_wt_pos = stopped_release.release_wt;
                        if (snapshot.yaw_traj && !snapshot.yaw_traj->empty()) {
                            message.start_wt_yaw = stopped_release.release_wt;
                        }
                        ros_ptr_->getSimTime(message.header.stamp.sec,
                                             message.header.stamp.nanosec);
                        sample.start_wt = stopped_release.release_wt;
                        sample.trajectory_time = 0.0;
                    }
                }
                async_recovery::Completion proof;
                proof.successful = result.computed &&
                        (result.ret_code == super_utils::SUCCESS || result.ret_code == super_utils::FINISH) &&
                        release_ready;
                proof.rejected = result.rejected;
                proof.goal_valid = result.goal_valid;
                proof.brake_active = safety_brake_active_.load(std::memory_order_acquire);
                proof.brake_finished = safety_brake_finished_.load(std::memory_order_acquire);
                proof.stable_pose = asyncRecoveryStablePoseLocked();
                proof.no_pending_goal = !pending_goal_.valid && !goal_update_in_progress_;
                proof.not_stopped = !stop.load(std::memory_order_acquire);
                proof.map_fresh = mapFreshForGuard(health, age) &&
                        (!health.update_in_progress || map_ptr_->immutablePlannerSnapshotEnabled()) &&
                        (!stoppedDepartureV4Enabled() ||
                         health.map_version == stopped_release.map_version);
                proof.certificate_safe = refreshed && safety_certificate_valid_ && safety_certificate_.safe();
                proof.certificate_current = safety_certificate_.trajectory_generation == result.generation_after &&
                        safety_certificate_.map_version == health.map_version &&
                        !safety_revalidation_requested_.load(std::memory_order_acquire) &&
                        safety_certificate_.checked_from_tt <= sample.trajectory_time &&
                        safety_certificate_.checked_to_tt >= sample.trajectory_time;
                proof.sample_valid = sample_valid && snapshot.generation == result.generation_after;
                proof.sample_finished = sample.finished;
                proof.velocity_valid = velocity_valid;
                proof.result_generation = result.generation_after;
                proof.current_generation = planner_ptr_->getCommittedTrajectoryGeneration();
                proof.current_map = health.map_version;
                completed = async_recovery::mayComplete(before, current, proof);
                if (completed) {
                    recovered_reason = brake_reason_;
                    certified_map = health.map_version;
                    gi_.new_goal = false;
                    plan_from_rest_.store(true, std::memory_order_release);
                    finish_plan.store(result.ret_code == super_utils::FINISH, std::memory_order_release);
                    // ChangeState itself relocks pending_goal_mutex_. Preserve
                    // its invalidation inside this already-owned transaction.
                    if (goalRetransmitIdentityEnabled()) invalidateGoalRetransmissionTokenLocked();
                    machine_state_.store(FOLLOW_TRAJ, std::memory_order_release);
                    brake_pos_traj_ = Trajectory{};
                    brake_yaw_traj_ = Trajectory{};
                    brake_velocity_limit_mps_ = 0.0;
                    brake_source_generation_ = 0;
                    brake_stability_started_ = false;
                    safety_brake_finished_.store(false, std::memory_order_release);
                    safety_brake_active_.store(false, std::memory_order_release);
                    active_brake_body_replaced_ = false;
                    clearActiveYawScanLocked();
                    if (asyncGenerateEnabled()) clearAsyncGenerateQuarantineLocked();
                    // Command publication uses this same safety lock. The
                    // exact certified path is published before releasing it.
                    mpc_cmd_pub_->publish(message);
                    if (cfg_.event_recovery_en) {
                        ros_ptr_->info(
                                " -- [EVENT_RECOVERY_PATH_READY] request_seq={} stamp_ns={} "
                                "ack_map={} certified_map={} generation_before={} generation_after={}",
                                current.ack.target, current.ack.stamp, current.ack.map,
                                certified_map, before.generation_before, result.generation_after);
                    }
                    if (needsRecoveryEscapeHold(safety_certificate_, sample)) {
                        recovery_escape_hold_pending_ = true;
                        recovery_escape_hold_generation_ =
                                result.generation_after;
                        recovery_escape_hold_release_wt_ = sample.start_wt +
                                safety_certificate_.clearance_escape_completed_tt;
                        ros_ptr_->info(
                                " -- [EVENT_RECOVERY_ESCAPE_HOLD] gen={} map={} "
                                "trajectory_tt={:.3f} release_wt={:.3f} "
                                "action=retain_full_until_ordinary_certificate",
                                result.generation_after, certified_map,
                                sample.trajectory_time,
                                recovery_escape_hold_release_wt_);
                    } else {
                        bool expected = true;
                        if (trajectory_guard_recovery_announced_.compare_exchange_strong(
                                    expected, false, std::memory_order_acq_rel)) {
                            clearFullRefreshRecoveryGateLocked();
                            std_msgs::msg::Bool inactive;
                            inactive.data = false;
                            trajectory_guard_recovery_pub_->publish(inactive);
                            ros_ptr_->info(" -- [TRAJ_GUARD_RECOVERY_SIGNAL] active=false");
                        }
                    }
                }
            }
            if (completed) {
                ++async_recovery_completed_;
                ros_ptr_->pubReplanStatus(true);
                ros_ptr_->info(" -- [TRAJ_GUARD_RECOVERED] trigger={} gen={} map={}",
                               recovered_reason, result.generation_after, certified_map);
            } else {
                ++async_recovery_discarded_;
                if (result.computed) ros_ptr_->pubReplanStatus(false);
            }
            ros_ptr_->info(" -- [ASYNC_RECOVERY_RESULT] id={} computed={} completed={} "
                           "revision={} generation_before={} generation_after={} "
                           "dispatched_total={} completed_total={} discarded_total={}",
                           before.id, result.computed, completed, before.brake_revision,
                           before.generation_before, result.generation_after,
                           async_recovery_dispatched_, async_recovery_completed_, async_recovery_discarded_);
            if (stoppedDepartureV4Enabled() && worker_success &&
                !stopped_release.accepted) {
                ros_ptr_->warn(
                        " -- [STOPPED_DEPARTURE_RECOVERY_REJECT] id={} "
                        "reason={} generation={} map={} action=retain_brake",
                        before.id, stopped_release.reason,
                        result.generation_after, release_health.map_version);
            }
            const bool planning_failure = result.computed &&
                    ((result.ret_code != super_utils::SUCCESS &&
                      result.ret_code != super_utils::FINISH) ||
                     !result.goal_valid || result.rejected);
            if (!completed && planning_failure) {
                armNextActiveYawScanAfterPlanningFailure(
                        before.brake_revision);
            }
            async_recovery_slot_.release(before.id);
            return completed;
        }

        bool tryAsyncCertifiedRecovery() {
            if (asyncGenerateEnabled() && async_generate_slot_.busy()) return false;
            if (const auto result = async_recovery_slot_.completed())
                return finishAsyncCertifiedRecovery(*result);
            if (async_recovery_slot_.busy()) return false;
            if (!activeYawScanRecoveryReady()) return false;
            std::unique_lock<std::mutex> activation(brake_activation_mutex_, std::try_to_lock);
            if (!activation || stop.load(std::memory_order_acquire) ||
                !safety_brake_active_.load(std::memory_order_acquire) ||
                !safety_brake_finished_.load(std::memory_order_acquire)) return false;
            const auto health = map_ptr_->getMapHealthSnapshot();
            double age = 0.0;
            if (!mapFreshForGuard(health, age) ||
                (health.update_in_progress && !map_ptr_->immutablePlannerSnapshotEnabled()) ||
                !fullRefreshRecoveryGateSatisfied(health)) return false;
            robot_state_ = map_ptr_->getRobotState();
            const double now = ros_ptr_->getSimTime();
            if (!robot_state_.rcv || !std::isfinite(robot_state_.rcv_time) ||
                now < robot_state_.rcv_time || now - robot_state_.rcv_time > 0.1 ||
                !robot_state_.p.array().isFinite().all() ||
                (robot_state_.p - brake_stop_position_).norm() > 0.15) {
                brake_stability_started_ = false;
                return false;
            }
            if (!brake_stability_started_ ||
                (robot_state_.p - brake_stability_anchor_).norm() > 0.03) {
                brake_stability_anchor_ = robot_state_.p;
                brake_stability_start_wt_ = now;
                brake_stability_started_ = true;
                return false;
            }
            if (now - brake_stability_start_wt_ < 0.25 ||
                now - brake_recovery_last_attempt_wt_ < 0.5 || !mapReadyForPlanning()) return false;
            // Same pending-goal admission as the old GENERATE_TRAJ branch,
            // performed by main, never by the optimizer executor.
            tryConsumePendingGoal();
            if (closeToGoal(0.1)) return false;
            AsyncRecoveryRequest request;
            {
                std::lock_guard<std::mutex> refresh(full_refresh_mutex_);
                std::lock_guard<std::mutex> safety(safety_mutex_);
                std::lock_guard<std::mutex> goal(pending_goal_mutex_);
                if (pending_goal_.valid || goal_update_in_progress_) return false;
                request.identity = asyncRecoveryIdentityLocked(
                        ++async_recovery_next_id_, planner_ptr_->getCommittedTrajectoryGeneration());
                if (!async_recovery::ready(request.identity)) return false;
                request.goal = gi_.goal_p;
                request.goal_yaw = gi_.goal_yaw;
                request.new_goal = gi_.new_goal;
                if (!async_recovery_slot_.submit(request)) return false;
                brake_recovery_last_attempt_wt_ = now;
                ++async_recovery_dispatched_;
            }
            ros_ptr_->info(" -- [ASYNC_RECOVERY_REQUEST] id={} revision={} generation_before={} "
                           "request_seq={} stamp_ns={} ack_map={}",
                           request.identity.id, request.identity.brake_revision,
                           request.identity.generation_before, request.identity.ack.target,
                           request.identity.ack.stamp, request.identity.ack.map);
            return false;
        }

        bool tryRecoverFromEmergencyBrake() {
            const super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::GuardRecover);
            if (asyncGenerateEnabled() && async_generate_slot_.busy()) return false;
            if (asyncCertifiedRecoveryEnabled()) return tryAsyncCertifiedRecovery();
            if (!safety_brake_active_.load(std::memory_order_acquire) ||
                !safety_brake_finished_.load(std::memory_order_acquire)) {
                return false;
            }
            if (!activeYawScanRecoveryReady()) return false;

            const auto health = map_ptr_->getMapHealthSnapshot();
            double map_age_s;
            if ((health.update_in_progress &&
                 !map_ptr_->immutablePlannerSnapshotEnabled()) ||
                !mapFreshForGuard(health, map_age_s)) {
                return false;
            }
            // For an advertised Adaptive generation stream, do not plan from
            // rest until ROG-Map has acknowledged the exact full cloud sent
            // after this guard edge. The fresh-map replan and safety
            // certificate below therefore necessarily occur after that ACK.
            if (!fullRefreshRecoveryGateSatisfied(health)) {
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
            {
                const super_utils::thread_cpu_profile::Scope main_cpu_scope(
                        super_utils::thread_cpu_profile::Stage::FsmMainCore);
                callMainFsmOnce();
            }
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
            if (!cfg_.event_recovery_en && !asyncGenerateEnabled()) publishPolyTraj();

            std::string recovered_reason;
            const bool defer_escape_release =
                    needsRecoveryEscapeHold(
                            recovered_certificate, recovered_sample);
            const double escape_release_wt = defer_escape_release
                    ? recovered_sample.start_wt +
                            recovered_certificate.clearance_escape_completed_tt
                    : -std::numeric_limits<double>::infinity();
            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                recovered_reason = brake_reason_;
                brake_pos_traj_ = Trajectory{};
                brake_yaw_traj_ = Trajectory{};
                brake_velocity_limit_mps_ = 0.0;
                brake_source_generation_ = 0;
                brake_stability_started_ = false;
                safety_brake_finished_.store(false, std::memory_order_release);
                safety_brake_active_.store(false, std::memory_order_release);
                active_brake_body_replaced_ = false;
                clearActiveYawScanLocked();
                if (asyncGenerateEnabled()) clearAsyncGenerateQuarantineLocked();
                if (defer_escape_release) {
                    recovery_escape_hold_pending_ = true;
                    recovery_escape_hold_generation_ = generation_after;
                    recovery_escape_hold_release_wt_ = escape_release_wt;
                }
            }
            if (!cfg_.event_recovery_en && asyncGenerateEnabled()) publishPolyTraj();
            if (cfg_.event_recovery_en) {
                publishPolyTraj();
                std::lock_guard<std::mutex> lock(full_refresh_mutex_);
                ros_ptr_->info(
                        " -- [EVENT_RECOVERY_PATH_READY] request_seq={} stamp_ns={} "
                        "ack_map={} certified_map={} generation_before={} generation_after={}",
                        required_full_refresh_target_seq_, required_full_refresh_stamp_ns_,
                        required_full_refresh_ack_map_version_, recovered_certificate.map_version,
                        generation_before, generation_after);
            }
            if (defer_escape_release) {
                ros_ptr_->info(
                        " -- [EVENT_RECOVERY_ESCAPE_HOLD] gen={} map={} "
                        "trajectory_tt={:.3f} release_wt={:.3f} "
                        "action=retain_full_until_ordinary_certificate",
                        generation_after, recovered_certificate.map_version,
                        recovered_sample.trajectory_time,
                        escape_release_wt);
            } else {
                publishTrajectoryGuardRecoveryState(false);
            }
            ros_ptr_->info(" -- [TRAJ_GUARD_RECOVERED] trigger={} gen={} map={}",
                           recovered_reason,
                           planner_ptr_->getCommittedTrajectoryGeneration(),
                           health.map_version);
            return true;
        }

        void recordPublishedCommand(
                const mars_quadrotor_msgs::msg::PositionCommand &command) {
            {
                std::lock_guard<std::mutex> lock(latest_cmd_mutex_);
                last_published_cmd_ = command;
                last_published_cmd_wt_ = ros_ptr_->getSimTime();
                last_published_cmd_valid_ = true;
            }
            // Called only after cmd_pub_->publish(), so this row describes a
            // command that was actually handed to ROS rather than a prepared
            // sample later rejected by a safety transaction.
            if (rog_map::contact_trace::enabled()) {
                try {
                    const auto health = map_ptr_->getMapHealthSnapshot();
                    auto fields = rog_map::contact_trace::stream();
                    fields << "\"stamp_sec\":" << command.header.stamp.sec
                           << ",\"stamp_nanosec\":" << command.header.stamp.nanosec
                           << ",\"trajectory_id\":" << command.trajectory_id
                           << ",\"trajectory_flag\":"
                           << static_cast<unsigned int>(command.trajectory_flag)
                           << ",\"committed_generation_now\":"
                           << planner_ptr_->getCommittedTrajectoryGeneration()
                           << ",\"map_version_now\":" << health.map_version
                           << ",\"map_update_in_progress\":"
                           << (health.update_in_progress ? "true" : "false")
                           << ",\"position\":["
                           << rog_map::contact_trace::number(command.position.x) << ','
                           << rog_map::contact_trace::number(command.position.y) << ','
                           << rog_map::contact_trace::number(command.position.z) << ']'
                           << ",\"velocity\":["
                           << rog_map::contact_trace::number(command.velocity.x) << ','
                           << rog_map::contact_trace::number(command.velocity.y) << ','
                           << rog_map::contact_trace::number(command.velocity.z) << ']'
                           << ",\"acceleration\":["
                           << rog_map::contact_trace::number(command.acceleration.x) << ','
                           << rog_map::contact_trace::number(command.acceleration.y) << ','
                           << rog_map::contact_trace::number(command.acceleration.z) << ']'
                           << ",\"yaw\":"
                           << rog_map::contact_trace::number(command.yaw)
                           << ",\"yaw_dot\":"
                           << rog_map::contact_trace::number(command.yaw_dot);
                    rog_map::contact_trace::submit("published_position_command", fields.str());
                } catch (...) {
                }
            }
        }

    public:
        // Experimental same-process source handoff. The C++ filter already
        // owns the sole DDS raw-cloud subscription, so pass its received
        // SharedPtr directly into the guard window without republishing a
        // second PointCloud2. Call enable before init().
        void enableInProcessGuardCloudInjection() {
            raw_cloud_in_process_injection_en_ = true;
        }

        void injectGuardCloud(
                const sensor_msgs::msg::PointCloud2::SharedPtr &cloud_msg) {
            raw_cloud_received_messages_total_.fetch_add(
                    1, std::memory_order_relaxed);
            raw_cloud_received_payload_bytes_total_.fetch_add(
                    cloud_msg ? cloud_msg->data.size() : 0,
                    std::memory_order_relaxed);
            cacheGuardCloud(cloud_msg, rog_map::MapHealthClock::now());
        }

        // Experimental Full-mode transport bypass. This does not change the
        // cloud contents or map algorithm: ROGMapROS performs the same
        // admission checks and hands the SharedPtr to its existing
        // latest-only update worker. Call only after init().
        void injectMapCloud(
                const sensor_msgs::msg::PointCloud2::SharedPtr &cloud_msg) {
            if (map_ptr_) {
                map_ptr_->injectCloud(cloud_msg);
            }
        }

        FsmRos2() = default;

        ~FsmRos2() {
            if (ros_ptr_ &&
                cfg_.trajectory_guard_same_map_replan_coalesce_en) {
                ros_ptr_->info(
                        " -- [REPLAN_SAME_MAP_COALESCE_SUMMARY] skipped={} "
                        "last_map={} last_generation={}",
                        same_map_replan_skips_,
                        last_successful_replan_map_version_,
                        last_successful_replan_generation_);
            }
            if (raw_cloud_shadow_uses_map_cloud_observer_ && map_ptr_) {
                map_ptr_->setAcceptedCloudObserver({});
            }
            stopNearFieldShadowWorker();
            stopCiriShadowWorker();
            if (cfg_.trajectory_guard_raw_cloud_near_field_shadow_en &&
                ros_ptr_) {
                ros_ptr_->info(
                        " -- [TRAJ_GUARD_NEAR_FIELD_SHADOW_SUMMARY] "
                        "no_hit={} egress={} occupied={} unavailable={}",
                        near_field_shadow_no_hit_total_.load(
                                std::memory_order_relaxed),
                        near_field_shadow_egress_total_.load(
                                std::memory_order_relaxed),
                        near_field_shadow_occupied_total_.load(
                                std::memory_order_relaxed),
                        near_field_shadow_unavailable_total_.load(
                                std::memory_order_relaxed));
            }
            if (cfg_.trajectory_guard_frontend_risk_shadow_en && ros_ptr_) {
                ros_ptr_->info(
                        " -- [FRONTEND_RISK_SUMMARY] received={} occupied={} "
                        "ignored={} enforced={}",
                        frontend_risk_received_total_.load(
                                std::memory_order_relaxed),
                        frontend_risk_occupied_total_.load(
                                std::memory_order_relaxed),
                        frontend_risk_ignored_total_.load(
                                std::memory_order_relaxed),
                        frontend_risk_enforced_total_.load(
                                std::memory_order_relaxed));
                ros_ptr_->info(
                        " -- [FRONTEND_BODY_SUMMARY] received={} occupied={} "
                        "ignored={} enforced={} clear_while_braking={}",
                        frontend_body_received_total_.load(
                                std::memory_order_relaxed),
                        frontend_body_occupied_total_.load(
                                std::memory_order_relaxed),
                        frontend_body_ignored_total_.load(
                                std::memory_order_relaxed),
                        frontend_body_enforced_total_.load(
                                std::memory_order_relaxed),
                        frontend_body_clear_total_.load(
                                std::memory_order_relaxed));
            }
            saveReplanLogToFile();
        };

        typedef std::shared_ptr<FsmRos2> Ptr;

        void saveReplanLogToFile(const string &name = "") {
            // run statistic
            double total_length{0.0};
            int total_replan_num{0};
            double average_compt_t{0.0};
            Vec3f cur_p{0, 0, 0};
            for (const auto &rp: replan_logs_) {
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


            fmt::print("Retained replan num: {}, total recorded: {}, dropped: {}, "
                       "retained length: {}, average retained computation time: {} ms\n",
                       total_replan_num, replan_log_total_count_,
                       replan_log_dropped_count_, total_length,
                       average_compt_t / (total_replan_num == 0 ? 1 : total_replan_num) * 1000);


            const std::string save_path = name.empty()
                                          ? LOG_FILE_DIR(
                                                  "replan_logs/" + BinaryFileHandler<int>::getCurrentTimeStr() + ".bin")
                                          : LOG_FILE_DIR("replan_logs/" + name + ".bin");
            const std::string csv_path = name.empty()
                                         ? LOG_FILE_DIR(
                                                 "cmd_logs/" + BinaryFileHandler<int>::getCurrentTimeStr() + ".csv")
                                         : LOG_FILE_DIR("cmd_logs/" + name + ".csv");
            const vector<LogOneReplan> persisted_logs(
                    replan_logs_.begin(), replan_logs_.end());
            BinaryFileHandler<vector<LogOneReplan>>::save(save_path,
                                                           persisted_logs);

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
            if (asyncGenerateEnabled() &&
                async_generate_quarantine_.load(std::memory_order_acquire)) return false;
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

        // Caller holds activation -> full-refresh -> safety locks, then enters
        // the short base goal transaction. This path is read-only: it never
        // refreshes certificates, changes recovery state, or extends a lease.
        bool healthyGoalRetransmissionLocked(
                const std::uint64_t generation, const std::uint64_t brake_revision,
                const std::uint64_t event_request, const std::uint64_t full_request,
                std::uint64_t* map_out = nullptr) {
            goal_retransmit::HealthyFollow proof;
            const auto health = map_ptr_->getMapHealthSnapshot();
            proof.guard_enabled = cfg_.trajectory_guard_en;
            proof.ordinary_follow = machine_state_.load(std::memory_order_acquire) == FOLLOW_TRAJ;
            proof.stopped_finished_or_from_rest = stop.load(std::memory_order_acquire) ||
                    finish_plan.load(std::memory_order_acquire) ||
                    plan_from_rest_.load(std::memory_order_acquire);
            proof.brake_or_revalidation = safety_brake_active_.load(std::memory_order_acquire) ||
                    safety_revalidation_requested_.load(std::memory_order_acquire);
            proof.recovery_or_refresh_pending =
                    trajectory_guard_recovery_announced_.load(std::memory_order_acquire) ||
                    brake_activation_revision_ != brake_revision ||
                    event_recovery_requested_.load(std::memory_order_acquire) != event_request ||
                    (cfg_.event_recovery_en &&
                     event_recovery_requested_.load(std::memory_order_acquire) >
                     event_recovery_completed_.load(std::memory_order_acquire)) ||
                    latest_full_refresh_request_seq_ != full_request ||
                    required_full_refresh_min_seq_ != 0 ||
                    (full_refresh_gate_advertised_ && latest_full_refresh_request_seq_ != 0 &&
                     !latest_full_refresh_request_acked_);
            proof.failure_or_rejection = planner_ptr_->trajectoryGuardRejectionPending() ||
                    planner_ptr_->topologyRetryPending();
            proof.immutable_map = map_ptr_->immutablePlannerSnapshotEnabled();
            double map_age = std::numeric_limits<double>::infinity();
            // Conservative speed-independent limit avoids taking the command
            // cache lock while holding the certificate transaction.
            const double low_limit = cfg_.trajectory_guard_brake_trigger_map_age_s;
            const double high_limit = cfg_.trajectory_guard_brake_trigger_high_speed_map_age_s;
            const double age_limit = std::min(low_limit, high_limit);
            proof.map_fresh = std::isfinite(low_limit) && low_limit > 0.0 &&
                    std::isfinite(high_limit) && high_limit > 0.0 &&
                    mapFreshForGuard(health, map_age) && map_age <= age_limit;
            proof.generation = generation;
            proof.map_version = health.map_version;
            proof.explicitly_safe = safety_certificate_valid_ &&
                    safety_certificate_.status == TrajectorySafetyStatus::SAFE;
            proof.special_escape = safety_certificate_.used_clearance_escape ||
                    safety_certificate_.used_initial_footprint_egress;
            proof.certificate_generation = safety_certificate_.trajectory_generation;
            proof.certificate_map_version = safety_certificate_.map_version;
            proof.certificate_from_tt = safety_certificate_.checked_from_tt;
            proof.certificate_until_tt = safety_certificate_.checked_to_tt;
            CmdTraj::Sample sample;
            proof.sample_valid_finite = planner_ptr_->getOneCommandSample(sample, generation) &&
                    sample.generation == generation && sample.pvaj.array().isFinite().all() &&
                    std::isfinite(sample.start_wt) && std::isfinite(sample.trajectory_time) &&
                    std::isfinite(sample.yaw) && std::isfinite(sample.yaw_dot);
            proof.sample_finished = sample.finished;
            proof.sample_on_backup = sample.on_backup;
            proof.sample_tt = sample.trajectory_time;
            proof.final_evidence_current =
                    planner_ptr_->getCommittedTrajectoryGeneration() == generation &&
                    map_ptr_->getMapHealthSnapshot().map_version == health.map_version &&
                    machine_state_.load(std::memory_order_acquire) == FOLLOW_TRAJ &&
                    !stop.load(std::memory_order_acquire) &&
                    !finish_plan.load(std::memory_order_acquire) &&
                    !plan_from_rest_.load(std::memory_order_acquire) &&
                    !safety_brake_active_.load(std::memory_order_acquire) &&
                    !safety_revalidation_requested_.load(std::memory_order_acquire) &&
                    !trajectory_guard_recovery_announced_.load(std::memory_order_acquire) &&
                    !planner_ptr_->trajectoryGuardRejectionPending() &&
                    !planner_ptr_->topologyRetryPending();
            if (map_out) *map_out = health.map_version;
            return goal_retransmit::eligible(proof);
        }

        bool coalesceExplicitGoalRetransmission(const goal_retransmit::Request& request) {
            if (!goalRetransmitIdentityEnabled() || !demandReplanEnabled()) return false;
            const auto token = goalRetransmissionCandidate(request);
            if (!token.valid) return false;
            // Never wait behind brake construction/certificate work to optimize
            // a 1 Hz retransmission. Contention follows the original queue.
            std::unique_lock<std::mutex> activation(brake_activation_mutex_, std::try_to_lock);
            if (!activation) return false;
            std::unique_lock<std::mutex> refresh(full_refresh_mutex_, std::try_to_lock);
            if (!refresh) return false;
            std::unique_lock<std::mutex> safety(safety_mutex_, std::try_to_lock);
            if (!safety) return false;
            std::uint64_t map_version = 0;
            const bool coalesced = tryCoalesceGoalRetransmission(request, token, [&] {
                return healthyGoalRetransmissionLocked(
                        token.generation, token.brake_revision, token.event_request,
                        token.full_request, &map_version);
            });
            safety.unlock();
            refresh.unlock();
            activation.unlock();
            if (coalesced) {
                ros_ptr_->info(
                        " -- [GOAL_RETRANSMIT_COALESCED] stamp_ns={} generation={} map={} "
                        "queued_revision={} accepted_revision={} coalesced_total={}",
                        request.creation_stamp_ns, token.generation, map_version,
                        token.queued_revision, token.accepted_revision,
                        goalRetransmissionCoalescedCount());
            }
            return coalesced;
        }

        void recordGoalRetransmissionOwnCommit(
                const GoalDemandSnapshot& goal, const std::uint64_t epoch,
                const std::uint64_t generation) {
            if (!goalRetransmitIdentityEnabled()) return;
            std::unique_lock<std::mutex> activation(brake_activation_mutex_, std::try_to_lock);
            if (!activation) return;
            std::unique_lock<std::mutex> refresh(full_refresh_mutex_, std::try_to_lock);
            if (!refresh) return;
            std::unique_lock<std::mutex> safety(safety_mutex_, std::try_to_lock);
            if (!safety) return;
            const auto brake_revision = brake_activation_revision_;
            const auto event_request = event_recovery_requested_.load(std::memory_order_acquire);
            const auto full_request = latest_full_refresh_request_seq_;
            publishGoalRetransmissionToken(goal, epoch, generation, brake_revision,
                                           event_request, full_request, [&] {
                return healthyGoalRetransmissionLocked(
                        generation, brake_revision, event_request, full_request);
            });
        }

        void goalCallback(const geometry_msgs::msg::PoseStamped::SharedPtr msg) {
            super_utils::Vec3f goal_p = Vec3f{msg->pose.position.x, msg->pose.position.y, msg->pose.position.z};
            super_utils::Quatf goal_q = super_utils::Quatf{msg->pose.orientation.w, msg->pose.orientation.x,
                                                           msg->pose.orientation.y, msg->pose.orientation.z};
            const auto creation_stamp = goal_retransmit::canonicalPositiveStamp(
                    msg->header.stamp.sec, msg->header.stamp.nanosec);
            const auto request = rawGoalRequest(goal_p, goal_q, msg->header.frame_id, creation_stamp);
            if (ignoreExactInFlightGenerateReplay(request)) return;
            if (!coalesceExplicitGoalRetransmission(request)) {
                enqueueGoal(goal_p, goal_q, msg->header.frame_id, creation_stamp);
            }
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
            if (cfg_.event_recovery_en &&
                (!cfg_.trajectory_guard_en || cfg_.trajectory_guard_full_refresh_ack_sla_s <= 0.0)) {
                throw std::runtime_error("Event recovery requires certified guard and Full commit ACK");
            }
            if (asyncCertifiedRecoveryEnabled() && !cfg_.trajectory_guard_en) {
                throw std::runtime_error("Async certified recovery requires trajectory guard");
            }
            if (asyncGenerateSettingEnabled() && !cfg_.trajectory_guard_en) {
                throw std::runtime_error("Async ordinary generation requires trajectory guard");
            }
            if (stoppedDepartureV4SettingEnabled() &&
                (!cfg_.trajectory_guard_en ||
                 !asyncGenerateSettingEnabled() ||
                 !asyncCertifiedRecoveryEnabled())) {
                throw std::runtime_error(
                        "Stopped departure v4 requires guard plus both async planners");
            }
            if (stoppedHoldV5SettingEnabled() &&
                !stoppedDepartureV4SettingEnabled()) {
                throw std::runtime_error(
                        "Stopped hold v5 requires stopped departure v4");
            }
            if (goalChangeFullRefreshV6SettingEnabled() &&
                (!cfg_.event_recovery_en ||
                 !stoppedDepartureV4SettingEnabled())) {
                throw std::runtime_error(
                        "Goal-change Full refresh v6 requires event recovery and stopped departure v4");
            }
            if (activeYawScanSettingEnabled() &&
                (cfg_.event_recovery_en ||
                 !cfg_.trajectory_guard_en ||
                 !stoppedDepartureV4SettingEnabled())) {
                throw std::runtime_error(
                        "Sector active yaw scan requires fixed-Sector guard plus stopped departure v4");
            }
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
            ros_ptr_->info(" -- [ASYNC_CERTIFIED_RECOVERY] enabled={} executor=existing_replan "
                           "main_finalization=true default_off=true", asyncCertifiedRecoveryEnabled());
            ros_ptr_->info(" -- [ASYNC_GENERATE_TRAJ] enabled={} executor=existing_replan "
                           "main_finalization=true default_off=true", asyncGenerateEnabled());
            ros_ptr_->info(" -- [STOPPED_DEPARTURE_V4] enabled={} "
                           "physical_origin=true prefix_from_zero=true shared_release=true "
                           "default_off=true", stoppedDepartureV4Enabled());
            ros_ptr_->info(" -- [STOPPED_HOLD_V5] enabled={} "
                           "stationary_only=true deferred_soft_margin=true "
                           "hard_checks_required=true default_off=true",
                           stoppedHoldV5Enabled());
            ros_ptr_->info(" -- [GOAL_CHANGE_FULL_REFRESH_V6] enabled={} "
                           "distinct_identity_only=true following_only=true "
                           "stop_before_full_ack=true certified_release=true "
                           "default_off=true",
                           goalChangeFullRefreshV6Enabled());
            ros_ptr_->info(
                    " -- [ACTIVE_YAW_SCAN] enabled={} mode=fixed_sector "
                    "trigger=distinct_goal_or_failed_stopped_plan "
                    "sequence=stop_yaw_fresh_map_replan rate_deg_s=40.0 "
                    "yaw_tolerance_deg=8.0 settle_s=0.20 default_off=true",
                    activeYawScanEnabled());
            if (cfg_.trajectory_guard_en) {
                const rclcpp::QoS guard_recovery_qos(
                        rclcpp::QoS(1).reliable().keep_last(1)
                                .transient_local());
                rclcpp::PublisherOptions guard_recovery_options;
                guard_recovery_options.use_intra_process_comm =
                        rclcpp::IntraProcessSetting::Disable;
                trajectory_guard_recovery_pub_ =
                        nh_->create_publisher<std_msgs::msg::Bool>(
                                "/planning/trajectory_guard_recovery_active",
                                guard_recovery_qos,
                                guard_recovery_options);
                // Give a late-starting Adaptive filter an explicit initial
                // state through the transient-local publisher.
                std_msgs::msg::Bool inactive;
                inactive.data = false;
                trajectory_guard_recovery_pub_->publish(inactive);
                if (cfg_.trajectory_guard_full_refresh_ack_sla_s > 0.0) {
                    refresh_ack_cbk_group_ = nh_->create_callback_group(
                            rclcpp::CallbackGroupType::MutuallyExclusive);
                    rclcpp::SubscriptionOptions refresh_options;
                    refresh_options.callback_group = refresh_ack_cbk_group_;
                    refresh_options.use_intra_process_comm =
                            rclcpp::IntraProcessSetting::Disable;
                    const auto request_qos = rclcpp::QoS(
                            rclcpp::KeepLast(16)).reliable()
                                    .transient_local();
                    const auto ack_qos = rclcpp::QoS(
                            rclcpp::KeepLast(16)).reliable()
                                    .durability_volatile();
                    full_refresh_request_sub_ = nh_->create_subscription<
                            std_msgs::msg::UInt64MultiArray>(
                                    "/sector/full_refresh_request",
                                    request_qos,
                                    std::bind(
                                            &FsmRos2::fullRefreshRequestCallback,
                                            this, std::placeholders::_1),
                                    refresh_options);
                    cloud_process_ack_sub_ = nh_->create_subscription<
                            std_msgs::msg::UInt64MultiArray>(
                                    "/rog_map/cloud_process_ack", ack_qos,
                                    std::bind(
                                            &FsmRos2::cloudProcessAckCallback,
                                            this, std::placeholders::_1),
                                    refresh_options);
                    if (cfg_.event_recovery_en) {
                        event_recovery_request_sub_ = nh_->create_subscription<std_msgs::msg::UInt64>(
                            "/sector/event_recovery_request", request_qos,
                            [this](const std_msgs::msg::UInt64::SharedPtr request) {
                                // Startup completion consumes its exact ACK gate
                                // and false edge under this same short mutex.
                                std::lock_guard<std::mutex> lock(full_refresh_mutex_);
                                const auto old = event_recovery_requested_.load();
                                if (request->data > old) event_recovery_requested_.store(request->data);
                            }, refresh_options);
                    }
                    ros_ptr_->info(
                            " -- [FULL_REFRESH_ACK_GATE] listening sla={:.3f}s",
                            cfg_.trajectory_guard_full_refresh_ack_sla_s);
                }
            }
            if (cfg_.trajectory_guard_raw_cloud_en ||
                cfg_.trajectory_guard_raw_cloud_ciri_shadow_en ||
                cfg_.trajectory_guard_raw_cloud_near_field_shadow_en) {
                const std::string map_cloud_topic =
                        map_ptr_->getMapConfig().cloud_topic;
                const std::string guard_cloud_topic =
                        cfg_.trajectory_guard_raw_cloud_source_topic.empty()
                                ? map_cloud_topic
                                : cfg_.trajectory_guard_raw_cloud_source_topic;
                const bool needs_dedicated_subscription =
                        cfg_.trajectory_guard_raw_cloud_en ||
                        guard_cloud_topic != map_cloud_topic;
                const char *cloud_source = "map_observer";
                if (raw_cloud_in_process_injection_en_) {
                    cloud_source = "in_process_filter_handoff";
                } else if (needs_dedicated_subscription) {
                    // The live raw-cloud guard owns a KD-tree snapshot and
                    // retains its existing independent callback group. A
                    // shadow/enforce witness may also select a pre-filter
                    // topic while ROG-Map continues to consume /cloud_sector.
                    guard_cloud_cbk_group_ = nh_->create_callback_group(
                            rclcpp::CallbackGroupType::MutuallyExclusive);
                    rclcpp::SubscriptionOptions guard_cloud_options;
                    guard_cloud_options.callback_group =
                            guard_cloud_cbk_group_;
                    guard_cloud_sub_ = nh_->create_subscription<
                            sensor_msgs::msg::PointCloud2>(
                            guard_cloud_topic, qos,
                            std::bind(&FsmRos2::guardCloudCallback, this,
                                      std::placeholders::_1),
                            guard_cloud_options);
                    cloud_source = guard_cloud_topic == map_cloud_topic
                                           ? "dedicated_map_subscription"
                                           : "dedicated_pre_filter_subscription";
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
                    raw_cloud_shadow_uses_map_cloud_observer_ = true;
                }
                ros_ptr_->info(
                        " -- [TRAJ_GUARD_RAW] enabled topic={} max_age={:.3f}s "
                        "clearance={:.3f}m ciri_shadow={} "
                        "near_field_shadow={} accum_window={:.3f}s source={}",
                        guard_cloud_topic,
                        cfg_.trajectory_guard_raw_cloud_max_age_s,
                        cfg_.trajectory_guard_raw_cloud_clearance_m,
                        cfg_.trajectory_guard_raw_cloud_ciri_shadow_en,
                        cfg_.trajectory_guard_raw_cloud_near_field_shadow_en,
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
            if (cfg_.trajectory_guard_raw_cloud_near_field_shadow_en) {
                near_field_shadow_worker_ = std::thread(
                        &FsmRos2::nearFieldShadowWorkerLoop, this);
                ros_ptr_->info(
                        " -- [TRAJ_GUARD_NEAR_FIELD_SHADOW] latest-only "
                        "worker started clearance={:.3f}m horizon={:.3f}s "
                        "sample_dt={:.3f}s min_interval={:.3f}s voxel={:.3f}m "
                        "enforce={}",
                        cfg_.trajectory_guard_raw_cloud_near_field_clearance_m,
                        cfg_.trajectory_guard_raw_cloud_near_field_horizon_s,
                        cfg_.trajectory_guard_raw_cloud_near_field_sample_dt_s,
                        cfg_.trajectory_guard_raw_cloud_near_field_min_interval_s,
                        cfg_.trajectory_guard_raw_cloud_near_field_voxel_m,
                        cfg_.trajectory_guard_raw_cloud_near_field_enforce_en);
                if (cfg_.trajectory_guard_raw_cloud_near_field_test_replay_mode !=
                    0) {
                    ros_ptr_->warn(
                            " -- [TRAJ_GUARD_NEAR_FIELD_TEST_REPLAY] armed "
                            "mode={} TEST_ONLY",
                            cfg_.trajectory_guard_raw_cloud_near_field_test_replay_mode);
                }
            }
            if (cfg_.trajectory_guard_frontend_risk_shadow_en) {
                frontend_risk_cbk_group_ = nh_->create_callback_group(
                        rclcpp::CallbackGroupType::MutuallyExclusive);
                rclcpp::SubscriptionOptions verdict_options;
                verdict_options.callback_group = frontend_risk_cbk_group_;
                const auto verdict_qos = rclcpp::QoS(
                        rclcpp::KeepLast(4)).reliable()
                                .durability_volatile();
                frontend_risk_verdict_sub_ = nh_->create_subscription<
                        mars_quadrotor_msgs::msg::TrajectoryRiskVerdict>(
                                cfg_.trajectory_guard_frontend_risk_topic,
                                verdict_qos,
                                std::bind(
                                        &FsmRos2::frontendRiskVerdictCallback,
                                        this, std::placeholders::_1),
                                verdict_options);
                ros_ptr_->info(
                        " -- [FRONTEND_RISK] listening topic={} "
                        "result_max_age={:.3f}s source_max_age={:.3f}s "
                        "enforce={} body_result_max_age={:.3f}s "
                        "body_source_max_age={:.3f}s body_enforce={}",
                        cfg_.trajectory_guard_frontend_risk_topic,
                        cfg_.trajectory_guard_frontend_risk_result_max_age_s,
                        cfg_.trajectory_guard_frontend_risk_source_max_age_s,
                        cfg_.trajectory_guard_frontend_risk_enforce_en,
                        cfg_.trajectory_guard_frontend_body_result_max_age_s,
                        cfg_.trajectory_guard_frontend_body_source_max_age_s,
                        cfg_.trajectory_guard_frontend_body_enforce_en);
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

            if (goalRetransmitIdentityEnabled()) {
                if (!demandReplanEnabled()) {
                    throw std::invalid_argument(
                            "SUPER_GOAL_RETRANSMIT_IDENTITY=1 requires SUPER_GUARDED_DEMAND_REPLAN=1");
                }
                ros_ptr_->info(
                        " -- [GOAL_RETRANSMIT_IDENTITY] enabled=true role=receiver "
                        "guarded_demand=true identity=creation_stamp_raw_pose_frame default_off=true");
            }
            if (demandReplanEnabled()) {
                ros_ptr_->info(
                        " -- [GUARDED_DEMAND_REPLAN] enabled=true max_dispatch_interval={} "
                        "demand_timer_hz={} guard_command_hz=100 legacy_coalescer=bypassed "
                        "stop_policy=sampled_unknown_allowed_soft_margin_after_complete_hard_checks "
                        "stop_policy_revision={}",
                        demandReplanBasePolicy().max_dispatch_interval_s, cfg_.replan_rate,
                        planner_ptr_->stopViabilityPolicyRevision());
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
            const super_utils::callback_timing_trace::Scope wall_trace(command_trace_, "FsmCommand");
            const super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::FsmCommandCallback);
            if (stop) {
                return;
            }

            if (safety_brake_active_.load(std::memory_order_acquire)) {
                CmdTraj::Sample brake_sample;
                async_recovery::BrakeCommandIdentity brake_identity;
                double sampled_brake_limit = 0.0;
                const bool async_handoff = asyncCertifiedRecoveryEnabled() || asyncGenerateEnabled();
                if (!getBrakeSample(brake_sample,
                                    async_handoff ? &brake_identity : nullptr,
                                    async_handoff ? &sampled_brake_limit : nullptr)) {
                    return;
                }
                if (!commandVelocityWithinLimit(
                            brake_sample, "emergency_brake",
                            async_handoff ? sampled_brake_limit : getBrakeVelocityLimit())) {
                    return;
                }
                // A worker result can become a fresh ordinary path between
                // sampling this brake and publication. Pair the final check
                // and both messages with main's recovery-release transaction.
                // A replacement brake can share source generation/start time,
                // hence the separate monotonic, safety-lock-owned revision.
                std::unique_lock<std::mutex> publication_lock(safety_mutex_, std::defer_lock);
                if (async_handoff) {
                    publication_lock.lock();
                    if (!async_recovery::mayPublishBrake(
                                safety_brake_active_.load(std::memory_order_relaxed),
                                brake_identity,
                                {brake_command_revision_, brake_source_generation_, brake_start_wt_})) return;
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

            // The worker may have internally committed a candidate, but the
            // only executable ordinary state during quarantine is the pinned
            // terminal hold. Initial no-path startup publishes no fabricated
            // generation. Keep the safety lock through both publications.
            if (asyncGenerateEnabled() &&
                async_generate_quarantine_.load(std::memory_order_acquire)) {
                std::lock_guard<std::mutex> publication(safety_mutex_);
                const auto health = map_ptr_->getMapHealthSnapshot();
                double age = 0.0;
                const auto& held = async_generate_hold_sample_;
                if (safety_brake_active_.load(std::memory_order_acquire) ||
                    !async_from_rest::mayPublishPinnedHold(
                            async_generate_quarantine_.load(std::memory_order_acquire),
                            async_generate_hold_revision_, async_generate_hold_revision_,
                            held.generation, held.generation,
                            async_generate_hold_certificate_valid_ &&
                            async_generate_hold_certificate_.safe() &&
                            async_generate_hold_certificate_.map_version == health.map_version &&
                            mapFreshForGuard(health, age) &&
                            asyncGenerateHoldPoseValidLocked())) return;
                mars_quadrotor_msgs::msg::PolynomialTrajectory heartbeat;
                getOneHeartBeatMsg(heartbeat, held);
                fillPositionCommand(pid_cmd_, held);
                mpc_cmd_pub_->publish(heartbeat);
                cmd_pub_->publish(pid_cmd_);
                recordPublishedCommand(pid_cmd_);
                return;
            }

            const auto command_machine_state =
                    machine_state_.load(std::memory_order_acquire);
            const auto command_publication_state =
                    command_machine_state == FOLLOW_TRAJ
                    ? OrdinaryCommandState::FOLLOW_TRAJECTORY
                    : command_machine_state == EMER_STOP
                      ? OrdinaryCommandState::EMERGENCY_STOP
                      : OrdinaryCommandState::OTHER;
            if (!ordinaryCommandPublicationAllowed(
                        cfg_.trajectory_guard_en,
                        command_publication_state,
                        false)) {
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

            if (cfg_.trajectory_guard_en &&
                !commandVelocityWithinLimit(
                        command_sample, "position_command",
                        planner_ptr_->getConfiguredMaxVelocity())) {
                safety_revalidation_requested_.store(
                        true, std::memory_order_release);
                activateEmergencyBrake("command_velocity_limit");
                return;
            }

            // mainFsmTimerCallback and this timer use different callback
            // groups.  Serialize the final state/brake check with brake
            // activation so a command prepared in FOLLOW_TRAJ cannot leak
            // after another thread has entered guarded EMER_STOP.
            std::lock_guard<std::mutex> publication_lock(safety_mutex_);
            const auto publish_machine_state =
                    machine_state_.load(std::memory_order_acquire);
            const auto publish_state = publish_machine_state == FOLLOW_TRAJ
                    ? OrdinaryCommandState::FOLLOW_TRAJECTORY
                    : publish_machine_state == EMER_STOP
                      ? OrdinaryCommandState::EMERGENCY_STOP
                      : OrdinaryCommandState::OTHER;
            if (!ordinaryCommandPublicationAllowed(
                        cfg_.trajectory_guard_en,
                        publish_state,
                        safety_brake_active_.load(
                                std::memory_order_relaxed))) {
                return;
            }
            if (asyncGenerateEnabled() &&
                async_generate_quarantine_.load(std::memory_order_acquire)) return;

            if (asyncGenerateEnabled()) {
                // A delayed old sample can span FOLLOW -> quarantine ->
                // accepted FOLLOW. State alone cannot identify its path.
                const auto current = planner_ptr_->getCommittedSharedTrajectorySnapshot();
                const auto health = map_ptr_->getMapHealthSnapshot();
                double map_age_s = 0.0;
                const bool current_certificate = !current.empty &&
                        safety_certificate_valid_ && safety_certificate_.safe() &&
                        !safety_revalidation_requested_.load(std::memory_order_acquire) &&
                        mapFreshForGuard(health, map_age_s) &&
                        (!health.update_in_progress || map_ptr_->immutablePlannerSnapshotEnabled()) &&
                        safety_certificate_.map_version == health.map_version;
                if (!async_from_rest::mayPublishOrdinarySample(
                            command_sample.generation, command_sample.start_wt,
                            current.generation, current.start_wt,
                            safety_certificate_.trajectory_generation,
                            command_sample.trajectory_time,
                            safety_certificate_.checked_from_tt,
                            safety_certificate_.checked_to_tt, current_certificate)) {
                    // Do not invalidate a newly accepted certificate merely
                    // because this older command callback lost the handoff race.
                    return;
                }
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

        static bool demandReplanEnabled() {
            static const bool enabled = [] {
                const char* setting = std::getenv("SUPER_GUARDED_DEMAND_REPLAN");
                return setting && std::strcmp(setting, "1") == 0;
            }();
            return enabled;
        }

        static demand_policy::Policy demandReplanBasePolicy() {
            static const auto policy = demand_policy::policyForExactExtendedOptIn(
                    demandReplanEnabled(), std::getenv("SUPER_GUARDED_DEMAND_EXTENDED_LEASE"));
            return policy;
        }

        bool demandRefreshPending() const {
            std::lock_guard<std::mutex> lock(full_refresh_mutex_);
            return required_full_refresh_min_seq_ != 0 ||
                    (full_refresh_gate_advertised_ &&
                     latest_full_refresh_request_seq_ != 0 &&
                     !latest_full_refresh_request_acked_);
        }

        bool demandEventPending() const {
            return cfg_.event_recovery_en &&
                    event_recovery_requested_.load(std::memory_order_acquire) >
                    event_recovery_completed_.load(std::memory_order_acquire);
        }

        static bool sameGoalDemand(const GoalDemandSnapshot& a,
                                   const GoalDemandSnapshot& b) {
            return !a.pending_or_updating && !b.pending_or_updating &&
                    a.queued_revision == b.queued_revision &&
                    a.accepted_revision == b.accepted_revision;
        }

        demand_policy::Evidence collectDemandEvidence() {
            demand_policy::Evidence e;
            const double now_wt = ros_ptr_->getSimTime();
            e.simulation_clock_monotonic = std::isfinite(now_wt) &&
                    (!std::isfinite(demand_last_observed_sim_wt_) ||
                     now_wt >= demand_last_observed_sim_wt_);
            if (!e.simulation_clock_monotonic) {
                demand_has_ordinary_success_ = false;
                demand_failure_since_success_ = true;
                demand_viability_receipt_.valid = false;
            }
            if (std::isfinite(now_wt)) demand_last_observed_sim_wt_ = now_wt;
            const auto goal = getGoalDemandSnapshot();
            const auto event_request = event_recovery_requested_.load(std::memory_order_acquire);
            const auto snapshot = planner_ptr_->getCommittedSharedTrajectorySnapshot();
            const auto health = map_ptr_->getMapHealthSnapshot();
            TrajectorySafetyResult certificate;
            bool certificate_valid;
            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                certificate = safety_certificate_;
                certificate_valid = safety_certificate_valid_;
            }
            double map_age, map_limit, speed;
            e.map_fresh_for_motion = mapFreshEnoughForMotion(health, map_age, map_limit, speed);
            e.enforcement_enabled = cfg_.trajectory_guard_en;
            e.viability_enabled = planner_ptr_->stopViabilityEnabled();
            e.ordinary_follow = machine_state_.load(std::memory_order_acquire) == FOLLOW_TRAJ;
            e.stop_finished_or_plan_from_rest = stop.load(std::memory_order_acquire) ||
                    finish_plan.load(std::memory_order_acquire) ||
                    plan_from_rest_.load(std::memory_order_acquire);
            e.pending_or_updating_goal = goal.pending_or_updating;
            e.goal_matches_successful_commit = sameGoalDemand(goal, demand_success_goal_);
            e.recovery_pending = trajectory_guard_recovery_announced_.load(std::memory_order_acquire) ||
                    event_request != demand_success_event_request_ ||
                    demandEventPending() || demandRefreshPending();
            e.brake_or_revalidation_pending = safety_brake_active_.load(std::memory_order_acquire) ||
                    safety_revalidation_requested_.load(std::memory_order_acquire);
            e.failure_or_rejection_since_success = demand_failure_since_success_ ||
                    planner_ptr_->trajectoryGuardRejectionPending() ||
                    planner_ptr_->topologyRetryPending();
            e.special_escape_certificate = certificate.used_clearance_escape ||
                    certificate.used_initial_footprint_egress;
            e.certificate_explicitly_safe = certificate_valid &&
                    certificate.status == TrajectorySafetyStatus::SAFE;
            e.certificate_generation = certificate.trajectory_generation;
            e.certificate_map_version = certificate.map_version;
            e.certificate_from_tt = certificate.checked_from_tt;
            e.certificate_until_tt = certificate.checked_to_tt;
            e.has_successful_ordinary_commit = demand_has_ordinary_success_;
            e.last_successful_generation = demand_success_generation_;
            e.generation = snapshot.generation;
            e.map_version = health.map_version;
            e.steady_now_s = std::chrono::duration<double>(
                    rog_map::MapHealthClock::now().time_since_epoch()).count();
            e.last_successful_dispatch_steady_s = std::chrono::duration<double>(
                    demand_success_dispatch_.time_since_epoch()).count();
            e.trajectory_start_wt = snapshot.start_wt;
            e.trajectory_time_s = now_wt - snapshot.start_wt;
            e.trajectory_duration_s = snapshot.empty ? 0.0 : snapshot.total_duration;
            e.has_appended_backup = snapshot.has_appended_backup;
            e.appended_backup_start_tt = snapshot.backup_traj_start_tt;
            e.has_carry_backup = snapshot.has_carry_backup;
            e.carry_backup_start_tt = snapshot.carry_backup_start_tt;
            e.carry_backup_end_tt = snapshot.carry_backup_end_tt;
            CmdTraj::Sample sample;
            if (!snapshot.empty &&
                planner_ptr_->getOneCommandSample(sample, snapshot.generation)) {
                e.sample_finished = sample.finished;
                e.sample_on_backup = sample.on_backup;
            }
            e.receipt = demand_viability_receipt_;
            const auto final_health = map_ptr_->getMapHealthSnapshot();
            e.final_evidence_current = final_health.map_version == health.map_version &&
                    planner_ptr_->getCommittedTrajectoryGeneration() == snapshot.generation &&
                    sameGoalDemand(goal, getGoalDemandSnapshot()) &&
                    event_recovery_requested_.load(std::memory_order_acquire) == event_request &&
                    machine_state_.load(std::memory_order_acquire) == FOLLOW_TRAJ &&
                    !stop.load(std::memory_order_acquire) &&
                    !finish_plan.load(std::memory_order_acquire) &&
                    !plan_from_rest_.load(std::memory_order_acquire) &&
                    !safety_brake_active_.load(std::memory_order_acquire) &&
                    !safety_revalidation_requested_.load(std::memory_order_acquire) &&
                    !trajectory_guard_recovery_announced_.load(std::memory_order_acquire) &&
                    !planner_ptr_->trajectoryGuardRejectionPending() &&
                    !planner_ptr_->topologyRetryPending() &&
                    !demandEventPending() && !demandRefreshPending();
            return e;
        }

        bool tryDeferOrdinaryReplan() {
            if (!demandReplanEnabled()) return false;
            auto policy = demandReplanBasePolicy();
            policy.demand_timer_period_s = cfg_.replan_rate > 0.0
                    ? std::floor(1000.0 / cfg_.replan_rate) / 1000.0 : 0.0;
            policy.solve_budget_s = planner_ptr_->configuredReplanForwardDt();
            policy.viability_sample_dt_s = planner_ptr_->stopViabilitySampleDt();
            policy.viability_policy_revision = planner_ptr_->stopViabilityPolicyRevision();
            auto evidence = collectDemandEvidence();
            auto decision = demand_policy::decide(policy, evidence);
            ++demand_checks_;
            if (decision.needsRenewal()) {
                ++demand_renewals_;
                demand_viability_receipt_ = planner_ptr_->renewCommittedStopViability(
                        ros_ptr_->getSimTime(), evidence.generation, evidence.map_version,
                        decision.required_until_tt);
                evidence = collectDemandEvidence();
                evidence.renewal_attempted = true;
                decision = demand_policy::decide(policy, evidence);
            }
            if (decision.skip()) ++demand_skips_;
            demand_decision_counters_.record(decision.reason);
            const auto now = rog_map::MapHealthClock::now();
            if (demand_last_report_.time_since_epoch().count() == 0 ||
                std::chrono::duration<double>(now - demand_last_report_).count() >= 5.0) {
                demand_last_report_ = now;
                ros_ptr_->info(
                        " -- [DEMAND_REPLAN] checks={} skips={} renewals={} "
                        "reason={} gen={} map={} required_until={:.3f} checked_until={:.3f}",
                        demand_checks_, demand_skips_, demand_renewals_,
                        demand_policy::reasonName(decision.reason), evidence.generation,
                        evidence.map_version, decision.required_until_tt,
                        evidence.receipt.checked_until_tt);
                // Cumulative final outcomes after renewal, not all timer ticks.
                // Formatting/allocation is limited to this existing 5 s report.
                std::string reasons;
                for (std::size_t i = 0; i < demand_policy::DecisionCounters::size; ++i) {
                    if (i != 0) reasons += ',';
                    const auto reason = static_cast<demand_policy::Reason>(i);
                    reasons += demand_policy::reasonName(reason);
                    reasons += '=';
                    reasons += std::to_string(demand_decision_counters_.count(reason));
                }
                ros_ptr_->info(
                        " -- [DEMAND_REPLAN_REASONS] checks={} counted={} max_dispatch_interval={} final_counts={}",
                        demand_checks_, demand_decision_counters_.total(),
                        policy.max_dispatch_interval_s, reasons);
            }
            return decision.skip();
        }

        void recordDemandReplanOutcome(
                const MovingReplanOutcome& outcome, const bool candidate_rejected,
                const GoalDemandSnapshot& goal_before,
                const std::uint64_t event_before,
                const rog_map::MapHealthClock::time_point dispatch,
                const std::uint64_t retransmit_epoch) {
            // Do not manufacture a lease from SUCCESS/NO_NEED, an unrelated
            // concurrent PlanFromRest commit, or a goal/recovery update.
            const double dispatch_to_commit_s = std::chrono::duration<double>(
                    outcome.committed_time - dispatch).count();
            if (!outcome.attempted || !outcome.successful || outcome.finished ||
                outcome.committed_generation == 0 || candidate_rejected ||
                outcome.committed_time.time_since_epoch().count() == 0 ||
                !std::isfinite(dispatch_to_commit_s) || dispatch_to_commit_s < 0.0 ||
                dispatch_to_commit_s > planner_ptr_->configuredReplanForwardDt() ||
                planner_ptr_->getCommittedTrajectoryGeneration() != outcome.committed_generation ||
                !sameGoalDemand(goal_before, getGoalDemandSnapshot()) ||
                event_recovery_requested_.load(std::memory_order_acquire) != event_before ||
                machine_state_.load(std::memory_order_acquire) != FOLLOW_TRAJ ||
                stop.load(std::memory_order_acquire) || finish_plan.load(std::memory_order_acquire) ||
                plan_from_rest_.load(std::memory_order_acquire) ||
                safety_brake_active_.load(std::memory_order_acquire) ||
                safety_revalidation_requested_.load(std::memory_order_acquire) ||
                trajectory_guard_recovery_announced_.load(std::memory_order_acquire) ||
                planner_ptr_->trajectoryGuardRejectionPending() ||
                planner_ptr_->topologyRetryPending() ||
                demandEventPending() || demandRefreshPending()) {
                return;
            }
            demand_has_ordinary_success_ = true;
            demand_failure_since_success_ = false;
            demand_success_generation_ = outcome.committed_generation;
            demand_success_goal_ = goal_before;
            demand_success_event_request_ = event_before;
            demand_success_dispatch_ = dispatch;
            recordGoalRetransmissionOwnCommit(goal_before, retransmit_epoch,
                                              outcome.committed_generation);
        }

        void replanTimerCallback() {
            const super_utils::callback_timing_trace::Scope wall_trace(replan_trace_, "FsmReplan", 0);
            const super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::FsmReplanCallback);
            if (serviceAsyncGenerateTrajectory()) return;
            if (serviceAsyncCertifiedRecovery()) return;
            if (safety_brake_active_.load(std::memory_order_acquire)) {
                return;
            }
            rog_map::MapHealthSnapshot replan_health;
            std::uint64_t generation_before = 0;
            if (cfg_.trajectory_guard_en) {
                replan_health = map_ptr_->getMapHealthSnapshot();
                double map_age_s;
                const double replan_start_age_limit = std::max(
                        0.05, 0.5 * cfg_.trajectory_guard_max_map_age_s);
                if (safety_revalidation_requested_.load(std::memory_order_acquire) ||
                    !mapFreshForGuard(replan_health, map_age_s) ||
                    map_age_s > replan_start_age_limit) {
                    return;
                }
                generation_before =
                        planner_ptr_->getCommittedTrajectoryGeneration();
                const auto replan_now = rog_map::MapHealthClock::now();
                const double since_success_s =
                        last_successful_replan_time_.time_since_epoch().count() == 0
                                ? std::numeric_limits<double>::infinity()
                                : std::chrono::duration<double>(
                                          replan_now -
                                          last_successful_replan_time_).count();
                if (demandReplanEnabled() && tryDeferOrdinaryReplan()) {
                    return;
                }
                // The new policy replaces, not stacks with, the weaker legacy
                // map/generation/age-only coalescer while explicitly enabled.
                if (!demandReplanEnabled() &&
                    cfg_.trajectory_guard_same_map_replan_coalesce_en &&
                    cfg_.trajectory_guard_same_map_replan_min_interval_s > 0.0 &&
                    replan_health.map_version != 0 &&
                    last_successful_replan_map_version_ ==
                            replan_health.map_version &&
                    last_successful_replan_generation_ == generation_before &&
                    since_success_s <
                            cfg_.trajectory_guard_same_map_replan_min_interval_s) {
                    ++same_map_replan_skips_;
                    ros_ptr_->info(
                            " -- [REPLAN_SAME_MAP_COALESCED] map={} "
                            "generation={} age={:.3f}s min_interval={:.3f}s "
                            "skipped_total={}",
                            replan_health.map_version, generation_before,
                            since_success_s,
                            cfg_.trajectory_guard_same_map_replan_min_interval_s,
                            same_map_replan_skips_);
                    return;
                }
            }
            const bool demand_enabled = demandReplanEnabled();
            const auto demand_goal_before = demand_enabled
                    ? getGoalDemandSnapshot() : GoalDemandSnapshot{};
            const auto demand_event_before = demand_enabled
                    ? event_recovery_requested_.load(std::memory_order_acquire) : 0;
            const auto demand_dispatch = demand_enabled
                    ? rog_map::MapHealthClock::now() : rog_map::MapHealthClock::time_point{};
            const auto retransmit_epoch = goalRetransmitIdentityEnabled()
                    ? goalRetransmissionEpoch() : 0;
            MovingReplanOutcome demand_outcome;
            {
                const super_utils::thread_cpu_profile::Scope replan_cpu_scope(
                        super_utils::thread_cpu_profile::Stage::FsmReplanCore);
                demand_outcome = callReplanOnce();
            }
            if (goalRetransmitIdentityEnabled() &&
                planner_ptr_->trajectoryGuardRejectionPending()) {
                // Invalidate before consuming the flag, so clearing it cannot
                // make a failed candidate briefly resemble a healthy retry.
                invalidateGoalRetransmissionToken();
            }
            const bool candidate_rejected = cfg_.trajectory_guard_en &&
                    planner_ptr_->consumeTrajectoryGuardRejection();
            if (demand_enabled) {
                // Pessimistic until all existing post-replan safety checks pass.
                // A failed/absent commit never updates the dispatch timestamp.
                demand_has_ordinary_success_ = false;
                demand_failure_since_success_ = true;
                demand_viability_receipt_.valid = false;
            }
            if (candidate_rejected && machine_state_ != FOLLOW_TRAJ) {
                activateEmergencyBrake("candidate_rejected_without_safe_follow");
                return;
            }
            if (cfg_.trajectory_guard_en && machine_state_ == FOLLOW_TRAJ &&
                !safety_brake_active_.load(std::memory_order_acquire) &&
                !refreshSafetyCertificate("replan_post")) {
                activateEmergencyBrake("replan_post_uncertified");
                return;
            }
            if (demand_enabled) {
                recordDemandReplanOutcome(demand_outcome, candidate_rejected,
                                          demand_goal_before, demand_event_before,
                                          demand_dispatch, retransmit_epoch);
            }
            if (cfg_.trajectory_guard_en &&
                cfg_.trajectory_guard_same_map_replan_coalesce_en &&
                !candidate_rejected &&
                machine_state_ == FOLLOW_TRAJ &&
                !safety_brake_active_.load(std::memory_order_acquire)) {
                const std::uint64_t generation_after =
                        planner_ptr_->getCommittedTrajectoryGeneration();
                if (generation_after > generation_before) {
                    last_successful_replan_map_version_ =
                            replan_health.map_version;
                    last_successful_replan_generation_ = generation_after;
                    last_successful_replan_time_ =
                            rog_map::MapHealthClock::now();
                }
            }
        }

        // Caller holds full_refresh_mutex_. Legacy non-event advertised ACKs
        // do not retain committed=1 evidence, so this new completion excludes
        // them rather than interpreting a merely processed scan as committed.
        startup_recovery::Ack startupRecoveryAckLocked() const {
            startup_recovery::Ack ack;
            ack.supported = cfg_.event_recovery_en || !full_refresh_gate_advertised_;
            ack.advertised_or_event = cfg_.event_recovery_en || full_refresh_gate_advertised_;
            ack.required = ack.advertised_or_event;
            ack.minimum = required_full_refresh_min_seq_;
            ack.target = required_full_refresh_target_seq_;
            ack.stamp = required_full_refresh_stamp_ns_;
            ack.map = required_full_refresh_ack_map_version_;
            ack.boundary_map = event_recovery_min_map_version_;
            ack.target_acked = required_full_refresh_acked_;
            ack.latest_target = latest_full_refresh_request_seq_;
            ack.latest_acked = latest_full_refresh_request_acked_;
            return ack;
        }

        startup_recovery::Before captureStartupRecoveryBeforeMain(bool& wait_for_ack) {
            wait_for_ack = false;
            startup_recovery::Before before;
            std::unique_lock<std::mutex> activation_lock(
                    brake_activation_mutex_, std::try_to_lock);
            if (!activation_lock) {
                // A competing activator may not have published its true edge
                // or armed the Full-ACK gate yet. Do not start the first path
                // in that gap; never block this timer on the brake search.
                const auto snapshot = planner_ptr_->getCommittedSharedTrajectorySnapshot();
                wait_for_ack = startup_recovery::mustWaitForActivation(
                        machine_state_.load(std::memory_order_acquire) == GENERATE_TRAJ,
                        snapshot.empty, snapshot.generation);
                return before;
            }
            if (!startup_recovery_pending_) return before;
            before.armed = true;
            before.announced = trajectory_guard_recovery_announced_.load(std::memory_order_acquire);
            before.revision = brake_activation_revision_;
            before.generating_from_rest = machine_state_.load(std::memory_order_acquire) == GENERATE_TRAJ;
            const auto snapshot = planner_ptr_->getCommittedSharedTrajectorySnapshot();
            before.empty_snapshot = snapshot.empty;
            before.generation = snapshot.generation;
            before.no_active_brake = !safety_brake_active_.load(std::memory_order_acquire);
            {
                std::lock_guard<std::mutex> lock(latest_cmd_mutex_);
                before.no_prior_command = !last_published_cmd_valid_;
            }
            const auto goal = getGoalDemandSnapshot();
            before.goal_queued = goal.queued_revision;
            before.goal_accepted = goal.accepted_revision;
            before.no_pending_goal = !goal.pending_or_updating;
            double map_age, map_limit, speed;
            before.map_fresh = mapFreshEnoughForMotion(
                    map_ptr_->getMapHealthSnapshot(), map_age, map_limit, speed);
            // The expected corridor retry is consumed by PlanFromRest. It must
            // be clear AFTER success, not be forbidden before that work runs.
            before.no_recovery_demand = !stop.load(std::memory_order_acquire) &&
                    !finish_plan.load(std::memory_order_acquire) &&
                    !safety_revalidation_requested_.load(std::memory_order_acquire);
            {
                std::lock_guard<std::mutex> lock(full_refresh_mutex_);
                before.ack = startupRecoveryAckLocked();
                before.event_requested = event_recovery_requested_.load(std::memory_order_acquire);
                before.event_completed = event_recovery_completed_.load(std::memory_order_acquire);
            }
            // Invalid goal/topology evidence cannot suppress the very main-FSM
            // work needed to consume it. Only the supported missing Full ACK
            // holds the no-trajectory solver, establishing ACK-before-planning.
            wait_for_ack = startup_recovery::mustWaitForAck(before);
            return before;
        }

        void tryCompleteStartupRecovery(const startup_recovery::Before& before) {
            if (!startup_recovery::mayPlan(before)) return;
            std::unique_lock<std::mutex> activation_lock(
                    brake_activation_mutex_, std::try_to_lock);
            if (!activation_lock || !startup_recovery_pending_ ||
                brake_activation_revision_ != before.revision ||
                !trajectory_guard_recovery_pub_) return;
            startup_recovery::After after;
            after.armed = startup_recovery_pending_;
            after.announced = trajectory_guard_recovery_announced_.load(std::memory_order_acquire);
            after.revision = brake_activation_revision_;
            after.following = machine_state_.load(std::memory_order_acquire) == FOLLOW_TRAJ;
            after.no_active_brake = !safety_brake_active_.load(std::memory_order_acquire);
            after.no_recovery_demand = !stop.load(std::memory_order_acquire) &&
                    !finish_plan.load(std::memory_order_acquire) &&
                    !safety_revalidation_requested_.load(std::memory_order_acquire) &&
                    !planner_ptr_->trajectoryGuardRejectionPending() &&
                    !planner_ptr_->topologyRetryPending();
            const auto snapshot = planner_ptr_->getCommittedSharedTrajectorySnapshot();
            const auto health = map_ptr_->getMapHealthSnapshot();
            after.generation = snapshot.generation;
            after.map = health.map_version;
            after.immutable_map = map_ptr_->immutablePlannerSnapshotEnabled();
            double map_age, map_limit, speed;
            after.map_fresh = mapFreshEnoughForMotion(health, map_age, map_limit, speed);
            CmdTraj::Sample sample;
            after.valid_current_sample = !snapshot.empty &&
                    planner_ptr_->getOneCommandSample(sample, snapshot.generation);
            after.sample_finite = after.valid_current_sample &&
                    sample.pvaj.array().isFinite().all() && std::isfinite(sample.trajectory_time) &&
                    std::isfinite(sample.start_wt) && sample.start_wt == snapshot.start_wt;
            after.sample_finished = sample.finished;
            after.sample_on_backup = sample.on_backup;
            TrajectorySafetyResult certificate;
            bool certificate_valid;
            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                certificate = safety_certificate_;
                certificate_valid = safety_certificate_valid_;
            }
            after.explicit_safe = certificate_valid &&
                    certificate.status == TrajectorySafetyStatus::SAFE &&
                    !certificate.used_clearance_escape && !certificate.used_initial_footprint_egress;
            after.exact_current_certificate = certificate.trajectory_generation == snapshot.generation &&
                    certificate.map_version == health.map_version &&
                    std::isfinite(certificate.checked_from_tt) &&
                    std::isfinite(certificate.checked_to_tt) &&
                    certificate.checked_from_tt <= sample.trajectory_time &&
                    certificate.checked_to_tt >= sample.trajectory_time;

            // This short transaction pairs with exact ACK/request callbacks and
            // event-request publication. Do not retain safety_mutex_ here.
            std::lock_guard<std::mutex> refresh_lock(full_refresh_mutex_);
            after.ack = startupRecoveryAckLocked();
            after.event_requested = event_recovery_requested_.load(std::memory_order_acquire);
            after.event_completed = event_recovery_completed_.load(std::memory_order_acquire);
            const auto goal = getGoalDemandSnapshot();
            after.goal_queued = goal.queued_revision;
            after.goal_accepted = goal.accepted_revision;
            after.no_pending_goal = !goal.pending_or_updating;
            after.final_evidence_current =
                    planner_ptr_->getCommittedTrajectoryGeneration() == snapshot.generation &&
                    map_ptr_->getMapHealthSnapshot().map_version == health.map_version &&
                    machine_state_.load(std::memory_order_acquire) == FOLLOW_TRAJ &&
                    !safety_brake_active_.load(std::memory_order_acquire) &&
                    !safety_revalidation_requested_.load(std::memory_order_acquire) &&
                    !stop.load(std::memory_order_acquire) && !finish_plan.load(std::memory_order_acquire) &&
                    !planner_ptr_->trajectoryGuardRejectionPending() &&
                    !planner_ptr_->topologyRetryPending();
            if (!startup_recovery::mayComplete(before, after)) return;

            bool expected = true;
            if (!trajectory_guard_recovery_announced_.compare_exchange_strong(
                        expected, false, std::memory_order_acq_rel)) return;
            startup_recovery_pending_ = false;
            if (cfg_.event_recovery_en) {
                ros_ptr_->info(
                        " -- [EVENT_RECOVERY_PATH_READY] request_seq={} stamp_ns={} "
                        "ack_map={} certified_map={} generation_before=0 generation_after={}",
                        after.ack.target, after.ack.stamp, after.ack.map,
                        after.map, after.generation);
            }
            clearFullRefreshRecoveryGateLocked();
            std_msgs::msg::Bool inactive;
            inactive.data = false;
            trajectory_guard_recovery_pub_->publish(inactive);
            ros_ptr_->info(" -- [TRAJ_GUARD_RECOVERY_SIGNAL] active=false");
            ros_ptr_->info(" -- [TRAJ_GUARD_STARTUP_RECOVERED] revision={} gen={} map={} ack_required={}",
                           after.revision, after.generation, after.map, after.ack.required);
        }

        void mainFsmTimerCallback() {
            const super_utils::callback_timing_trace::Scope wall_trace(main_trace_, "FsmMain");
            super_utils::thread_cpu_profile::report();
            const super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::FsmMainCallback);
            // Drain even if an intervening event has activated a brake. The
            // stale result cannot release it; leaving Ready reserved forever
            // would prevent the recovery executor from progressing.
            if (asyncGenerateEnabled()) {
                if (const auto completed = async_generate_slot_.completed())
                    finishAsyncGenerateTrajectory(*completed);
            }
            if (activeYawScanEnabled()) {
                const auto request = active_yaw_scan_goal_requested_.load(
                        std::memory_order_acquire);
                if (request > active_yaw_scan_goal_handled_) {
                    const auto state = machine_state_.load(
                            std::memory_order_acquire);
                    if (safety_brake_active_.load(
                                std::memory_order_acquire)) {
                        active_yaw_scan_goal_handled_ = request;
                        ros_ptr_->info(
                                " -- [ACTIVE_YAW_SCAN_GOAL_REQUEST] request={} "
                                "action=merge_with_existing_stop state={}",
                                request, MACHINE_STATE_STR[state]);
                    } else if (started_ && state != INIT) {
                        const double now_wt = ros_ptr_->getSimTime();
                        if (std::isfinite(brake_activation_retry_last_wt_) &&
                            now_wt - brake_activation_retry_last_wt_ <
                                    cfg_.brake_retry_interval_s) {
                            return;
                        }
                        brake_activation_retry_last_wt_ = now_wt;
                        ros_ptr_->info(
                                " -- [ACTIVE_YAW_SCAN_GOAL_REQUEST] request={} "
                                "action=certified_stop_then_yaw_fresh_map_reroute",
                                request);
                        if (activateEmergencyBrake(
                                    "sector_active_yaw_goal_change")) {
                            active_yaw_scan_goal_handled_ = request;
                        }
                        return;
                    } else {
                        // Preserve the request across INIT so the first route
                        // is never generated from an unturned body-forward
                        // Sector.  Do not gate this branch on
                        // mapReadyForPlanning(): a forward view with zero
                        // returns is exactly the case where the map becomes
                        // stale and a proven stationary yaw-only acquisition
                        // is required to recover visibility.  The brake
                        // selector and recovery planner retain their own hard
                        // conflict and fresh-map checks.
                        // INIT itself must still execute once to enter
                        // WAIT_GOAL; the pending request intercepts the next
                        // tick before WAIT_GOAL can consume/plan the goal.
                        if (state != INIT) return;
                    }
                }
            }
            if (goalChangeFullRefreshV6Enabled()) {
                const auto request =
                        goal_change_full_refresh_requested_.load(
                                std::memory_order_acquire);
                if (request > goal_change_full_refresh_handled_) {
                    goal_change_full_refresh_handled_ = request;
                    const auto state = machine_state_.load(
                            std::memory_order_acquire);
                    if (started_ && state != WAIT_GOAL && state != INIT &&
                        !safety_brake_active_.load(
                                std::memory_order_acquire)) {
                        ros_ptr_->info(
                                " -- [GOAL_CHANGE_FULL_REFRESH_REQUEST] "
                                "request={} action=certified_stop_then_full_ack_reroute",
                                request);
                        activateEmergencyBrake(
                                "goal_change_full_refresh");
                        return;
                    }
                    ros_ptr_->info(
                            " -- [GOAL_CHANGE_FULL_REFRESH_REQUEST] request={} "
                            "action=merge_with_existing_stop_or_idle state={}",
                            request, MACHINE_STATE_STR[state]);
                }
            }
            if (cfg_.event_recovery_en) {
                const auto request = event_recovery_requested_.load(std::memory_order_acquire);
                if (request > event_recovery_handled_) {
                    event_recovery_handled_ = request;
                    if (started_ && machine_state_ != WAIT_GOAL && machine_state_ != INIT &&
                        !safety_brake_active_.load(std::memory_order_acquire)) {
                        ros_ptr_->info(" -- [EVENT_RECOVERY_STOP_REQUEST] request={}", request);
                        activateEmergencyBrake("event_recovery_request");
                        event_recovery_completed_.store(request, std::memory_order_release);
                        return;
                    }
                    event_recovery_completed_.store(request, std::memory_order_release);
                }
            }
            // 2026-08-19: isolated diagnostic, gated only on the subscription
            // existing (not on trajectory_guard_raw_cloud_en, which this
            // does not read or affect). Purely observational -- see the
            // raw_cloud_debug_last_log_ comment above.
            if (guard_cloud_sub_ ||
                raw_cloud_shadow_uses_map_cloud_observer_ ||
                raw_cloud_in_process_injection_en_) {
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
                            "latest_age_s={:.3f} dedicated_messages={} "
                            "dedicated_payload_bytes={}",
                            seq, age_s,
                            raw_cloud_received_messages_total_.load(
                                    std::memory_order_relaxed),
                            raw_cloud_received_payload_bytes_total_.load(
                                    std::memory_order_relaxed));
                }
            }
            if (!safety_brake_active_.load(std::memory_order_acquire)) {
                std::uint64_t timed_out_request_seq = 0;
                double full_refresh_ack_age_s = 0.0;
                if (consumeFullRefreshAckSlaTimeout(
                            timed_out_request_seq,
                            full_refresh_ack_age_s)) {
                    ros_ptr_->error(
                            " -- [FULL_REFRESH_ACK_TIMEOUT] request_seq={} "
                            "age={:.3f}s sla={:.3f}s "
                            "action=certified_stop_then_fresh_reroute",
                            timed_out_request_seq,
                            full_refresh_ack_age_s,
                            cfg_.trajectory_guard_full_refresh_ack_sla_s);
                    activateEmergencyBrake("full_refresh_ack_timeout");
                    return;
                }
            }
            if (safety_brake_active_.load(std::memory_order_acquire)) {
                if (consumeFreshFrontendOccupiedVerdict(true, true)) {
                    activateEmergencyBrake(
                            "frontend_body_active_brake", true);
                    return;
                }
                tryRecoverFromEmergencyBrake();
                return;
            }
            if (cfg_.trajectory_guard_en && machine_state_ == EMER_STOP) {
                // A rejected brake used to fall through to callMainFsmOnce,
                // whose legacy EMER_STOP transition immediately entered
                // GENERATE_TRAJ.  That invoked PlanFromRest while the vehicle
                // was still moving and reproduced as thousands of identical
                // MINCO or CIRI/polytope failures on seeds 3/6/7/9.  A stale
                // map is a temporary inability to certify a stop, not proof
                // that planning from rest is valid.  Hold publication
                // fail-closed, let map/odom callbacks progress, and retry the
                // brake at a bounded cadence.  Only
                // tryRecoverFromEmergencyBrake may leave this state after a
                // real brake and stable terminal hold have been certified.
                const double now_wt = ros_ptr_->getSimTime();
                if (!std::isfinite(brake_activation_retry_last_wt_) ||
                    now_wt - brake_activation_retry_last_wt_ >=
                            cfg_.brake_retry_interval_s) {
                    brake_activation_retry_last_wt_ = now_wt;
                    activateEmergencyBrake("emergency_stop_retry");
                }
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
            if (machine_state_ == FOLLOW_TRAJ) {
                enqueueCommittedNearFieldShadowIfNeeded();
            }
            if (machine_state_ == FOLLOW_TRAJ &&
                consumeFreshNearFieldOccupiedResult()) {
                activateEmergencyBrake("near_field_occupied");
                return;
            }
            if (machine_state_ == FOLLOW_TRAJ &&
                consumeFreshFrontendOccupiedVerdict()) {
                activateEmergencyBrake("frontend_risk_occupied");
                return;
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
            if (cfg_.trajectory_guard_en && machine_state_ == FOLLOW_TRAJ) {
                tryCompleteRecoveryEscapeHold();
            }
            if (asyncGenerateEnabled() &&
                async_generate_quarantine_.load(std::memory_order_acquire)) {
                if (!refreshAsyncGenerateHold()) {
                    activateEmergencyBrake("async_generate_hold_uncertified");
                    return;
                }
                // Legacy callMainFsmOnce refreshes the optimizer's mutable
                // RobotState and would also consume goals while the solve runs.
                // Main still performed its real event/hold safety checks above.
                if (async_generate_slot_.busy()) return;
            }
            bool startup_wait_for_ack = false;
            const auto startup_before = captureStartupRecoveryBeforeMain(startup_wait_for_ack);
            if (startup_wait_for_ack) return;
            {
                const super_utils::thread_cpu_profile::Scope main_cpu_scope(
                        super_utils::thread_cpu_profile::Stage::FsmMainCore);
                callMainFsmOnce();
            }
            if (asyncGenerateEnabled() && async_generate_slot_.busy()) return;
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
                return;
            }
            tryCompleteStartupRecovery(startup_before);
        }

    };
}

#endif //SRC_FSM_ROS1_HPP

#endif
