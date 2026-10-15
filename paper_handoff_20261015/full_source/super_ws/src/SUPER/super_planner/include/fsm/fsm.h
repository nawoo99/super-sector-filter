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


#pragma once

#include <atomic>
#include <cstdint>
#include <deque>
#include <queue>
#include <memory>
#include <mutex>
#include <fstream>
#include <fmt/color.h>
#include <cereal/archives/binary_file_handler.hpp>
#include <fsm/config.hpp>
#include <fsm/goal_retransmit_policy.hpp>
#include <cstdlib>
#include <functional>
#include <super_core/super_planner.h>


#ifndef LOG_FILE_DIR
#define LOG_FILE_DIR(name) (string(string(ROOT_DIR) + "log/"+name))
#endif

namespace fsm {
    class Fsm {
    protected:
        std::atomic_bool stop{false};


        vector<string> log_time_str{
                "TIME_STAMPE", "EPX_TRAJ_FRONTEND",
                "EXP_TRAJ_OPT", "GENERATE_EXP_TRAJ",
                "BACK_TRAJ_FRONTEND", "BACK_TRAJ_OPT",
                "GENERATE_BACK_TRAJ", "TOTAL_REPLAN", "VISUALIZATION"
        };
        Config cfg_;
        // map, checker, planner
        super_planner::SuperPlanner::Ptr planner_ptr_;
        ros_interface::RosInterface::Ptr ros_ptr_;

        std::ofstream write_time_;
        vector<double> log_module_time;
        double yaw_{0}, yaw_dot_{0};

        rog_map::RobotState robot_state_;

        // params
        std::atomic_bool started_{false};
        std::atomic_bool plan_from_rest_{false};

        struct GoalInfo {
            bool new_goal{false};
            Vec3f goal_p{Vec3f::Zero()};
            double goal_yaw{NAN};
        } gi_;

        struct PendingGoal {
            Vec3f goal_p{Vec3f::Zero()};
            Quatf goal_q{Quatf::Identity()};
            bool valid{false};
            std::string frame;
            std::int64_t creation_stamp_ns{0};
            std::uint64_t source_revision{0};
        } pending_goal_;
        mutable std::mutex pending_goal_mutex_;
        std::uint64_t queued_goal_revision_{0};
        std::uint64_t accepted_goal_revision_{0};
        bool goal_update_in_progress_{false};
        goal_retransmit::Request accepted_raw_goal_request_{};
        std::uint64_t accepted_raw_goal_source_revision_{0};
        std::uint64_t goal_retransmit_epoch_{0};
        std::uint64_t goal_retransmit_coalesced_{0};

        struct GoalRetransmissionToken {
            bool valid{false};
            std::uint64_t epoch{0}, generation{0};
            std::uint64_t queued_revision{0}, accepted_revision{0};
            std::uint64_t brake_revision{0}, event_request{0}, full_request{0};
        } goal_retransmit_token_;

        static bool goalRetransmitIdentityEnabled() {
            static const bool enabled = goal_retransmit::enabledSetting(
                    std::getenv("SUPER_GOAL_RETRANSMIT_IDENTITY"));
            return enabled;
        }

        static goal_retransmit::Request rawGoalRequest(
                const Vec3f& p, const Quatf& q, const std::string& frame,
                const std::int64_t stamp) {
            return {{p.x(), p.y(), p.z()}, {q.w(), q.x(), q.y(), q.z()}, frame, stamp};
        }

        void invalidateGoalRetransmissionTokenLocked() {
            goal_retransmit_token_.valid = false;
            ++goal_retransmit_epoch_;
        }

        void invalidateGoalRetransmissionToken() {
            if (!goalRetransmitIdentityEnabled()) return;
            std::lock_guard<std::mutex> lock(pending_goal_mutex_);
            invalidateGoalRetransmissionTokenLocked();
        }

        std::uint64_t goalRetransmissionEpoch() const {
            std::lock_guard<std::mutex> lock(pending_goal_mutex_);
            return goal_retransmit_epoch_;
        }

        bool matchesGoalRetransmissionLocked(
                const goal_retransmit::Request& request,
                const GoalRetransmissionToken& token) const {
            return goalRetransmitIdentityEnabled() && token.valid &&
                    goal_retransmit_token_.valid && token.epoch == goal_retransmit_epoch_ &&
                    token.epoch == goal_retransmit_token_.epoch &&
                    token.generation == goal_retransmit_token_.generation &&
                    token.brake_revision == goal_retransmit_token_.brake_revision &&
                    token.event_request == goal_retransmit_token_.event_request &&
                    token.full_request == goal_retransmit_token_.full_request &&
                    !pending_goal_.valid && !goal_update_in_progress_ &&
                    token.queued_revision == queued_goal_revision_ &&
                    token.accepted_revision == accepted_goal_revision_ &&
                    accepted_raw_goal_source_revision_ == queued_goal_revision_ &&
                    goal_retransmit::sameRequest(request, accepted_raw_goal_request_);
        }

        GoalRetransmissionToken goalRetransmissionCandidate(
                const goal_retransmit::Request& request) const {
            std::lock_guard<std::mutex> lock(pending_goal_mutex_);
            if (!matchesGoalRetransmissionLocked(request, goal_retransmit_token_)) return {};
            return goal_retransmit_token_;
        }

        bool tryCoalesceGoalRetransmission(
                const goal_retransmit::Request& request,
                const GoalRetransmissionToken& token,
                const std::function<bool()>& final_healthy) {
            std::lock_guard<std::mutex> lock(pending_goal_mutex_);
            if (!matchesGoalRetransmissionLocked(request, token) || !final_healthy()) return false;
            ++goal_retransmit_coalesced_;
            return true;  // No queue/revision/goal/lease update on a retransmission.
        }

        std::uint64_t goalRetransmissionCoalescedCount() const {
            std::lock_guard<std::mutex> lock(pending_goal_mutex_);
            return goal_retransmit_coalesced_;
        }

        struct GoalDemandSnapshot {
            std::uint64_t queued_revision{0};
            std::uint64_t accepted_revision{0};
            bool pending_or_updating{true};
        };

        GoalDemandSnapshot getGoalDemandSnapshot() const {
            std::lock_guard<std::mutex> lock(pending_goal_mutex_);
            return {queued_goal_revision_, accepted_goal_revision_,
                    pending_goal_.valid || goal_update_in_progress_};
        }

        bool publishGoalRetransmissionToken(
                const GoalDemandSnapshot& goal, const std::uint64_t epoch,
                const std::uint64_t generation, const std::uint64_t brake_revision,
                const std::uint64_t event_request, const std::uint64_t full_request,
                const std::function<bool()>& final_healthy) {
            if (!goalRetransmitIdentityEnabled()) return false;
            std::lock_guard<std::mutex> lock(pending_goal_mutex_);
            if (generation == 0 || epoch != goal_retransmit_epoch_ ||
                goal.pending_or_updating || pending_goal_.valid || goal_update_in_progress_ ||
                goal.queued_revision != queued_goal_revision_ ||
                goal.accepted_revision != accepted_goal_revision_ ||
                accepted_raw_goal_source_revision_ != queued_goal_revision_ ||
                !accepted_raw_goal_request_.validIdentity() || !final_healthy()) return false;
            goal_retransmit_token_ = {true, epoch, generation, queued_goal_revision_,
                                     accepted_goal_revision_, brake_revision,
                                     event_request, full_request};
            return true;
        }

        // Keeps the existing goal-processing work outside the queue mutex but
        // prevents its consume-to-accept gap from qualifying for a solver skip.
        struct GoalUpdateScope {
            Fsm& fsm;
            bool accepted{false};
            PendingGoal consumed{};
            ~GoalUpdateScope() {
                std::lock_guard<std::mutex> lock(fsm.pending_goal_mutex_);
                if (accepted) {
                    ++fsm.accepted_goal_revision_;
                    if (consumed.valid) {
                        auto& raw = fsm.accepted_raw_goal_request_;
                        raw.position = {consumed.goal_p.x(), consumed.goal_p.y(), consumed.goal_p.z()};
                        raw.quaternion = {consumed.goal_q.w(), consumed.goal_q.x(),
                                          consumed.goal_q.y(), consumed.goal_q.z()};
                        raw.frame = std::move(consumed.frame);
                        raw.creation_stamp_ns = consumed.creation_stamp_ns;
                        fsm.accepted_raw_goal_source_revision_ = consumed.source_revision;
                    } else {
                        fsm.accepted_raw_goal_source_revision_ = 0;
                    }
                }
                if (goalRetransmitIdentityEnabled()) fsm.invalidateGoalRetransmissionTokenLocked();
                fsm.goal_update_in_progress_ = false;
            }
        };

        mutable std::mutex map_readiness_log_mutex_;
        mutable rog_map::MapHealthClock::time_point last_map_readiness_log_time_{};
        mutable bool map_ready_logged_{false};

        Eigen::Vector3d auto_pilot_vel_w_;

        // execution states
        enum MACHINE_STATE {
            INIT = 0,
            WAIT_GOAL,
            YAWING,
            GENERATE_TRAJ,
            FOLLOW_TRAJ,
            EMER_STOP
        };

        vector<string> MACHINE_STATE_STR{
                "INIT",
                "WAIT_GOAL",
                "YAWING",
                "GENERATE_TRAJ",
                "FOLLOW_TRAJ", "EMER_STOP"
        };


        std::atomic<MACHINE_STATE> machine_state_{INIT};


    public:
        Fsm() = default;
        ~Fsm();

        void updateROGMap(const rog_map::PointCloud &cloud, const super_utils::Pose &pose) {
            planner_ptr_->updateROGMap(cloud, pose);
        }

        void callPlanOnce(const Vec3f &goal) {
            TimeConsuming tc("Call replan once time", true);
            fmt::print(" -- [Fsm] Call plan once, cur state {}.\n", MACHINE_STATE_STR[machine_state_]);
            // check current state;
            Quatf q(NAN, NAN, NAN, NAN);
            enqueueGoal(goal, q);

            callMainFsmOnce();
            if (machine_state_ == WAIT_GOAL) {
                callMainFsmOnce();
            }
            if (machine_state_ == GENERATE_TRAJ) {
                callMainFsmOnce();
            }

            if (machine_state_ == FOLLOW_TRAJ) {
                callReplanOnce();
            }

            // save on log
            const int ret_code = recordLatestReplanLog();
            fmt::print(fmt::fg(fmt::color::green), " -- Replan ID: {}, ret code: {}\n",
                       replan_log_total_count_ - 1, ret_code);
        }

        Eigen::Quaterniond eulerToQuaternion(double roll, double pitch, double yaw) {
            double half_roll = roll * 0.5;
            double half_pitch = pitch * 0.5;
            double half_yaw = yaw * 0.5;

            double sin_r = std::sin(half_roll);
            double cos_r = std::cos(half_roll);
            double sin_p = std::sin(half_pitch);
            double cos_p = std::cos(half_pitch);
            double sin_y = std::sin(half_yaw);
            double cos_y = std::cos(half_yaw);

            // 计算四元数分量
            Eigen::Quaterniond q;
            q.w() = cos_r * cos_p * cos_y + sin_r * sin_p * sin_y;
            q.x() = sin_r * cos_p * cos_y - cos_r * sin_p * sin_y;
            q.y() = cos_r * sin_p * cos_y + sin_r * cos_p * sin_y;
            q.z() = cos_r * cos_p * sin_y - sin_r * sin_p * cos_y;

            return q;
        }

    protected:
        std::deque<LogOneReplan> replan_logs_;
        std::size_t replan_log_total_count_{0};
        std::size_t replan_log_dropped_count_{0};

        int recordLatestReplanLog();
        /* Callback functions */
        std::atomic_bool finish_plan{false};
        double system_start_time_;

        bool traj_finish_{false};

        void WriteTimeToLog();

        struct MovingReplanOutcome {
            bool attempted{false};
            bool successful{false};
            bool finished{false};
            std::uint64_t committed_generation{0};
            rog_map::MapHealthClock::time_point committed_time{};
        };

        MovingReplanOutcome callReplanOnce();

        void callMainFsmOnce();

        // ROS2 may reserve the existing planning executor. Other frontends
        // retain the synchronous path unless they explicitly override this.
        virtual bool dispatchGenerateTrajectoryAsync() { return false; }

        virtual void refreshMainRobotState() {
            planner_ptr_->getRobotState(robot_state_);
        }

        // Runs while pending_goal_mutex_ protects the just-written latest
        // goal. ROS frontends may latch a lightweight event here, but must not
        // block, plan, publish, or reacquire pending_goal_mutex_.
        virtual void onGoalQueuedLocked(bool distinct_identity) {
            (void) distinct_identity;
        }

        bool closeToGoal(const double &thresh_dis);

        void enqueueGoal(const Vec3f &p, const Quatf &q,
                         const std::string& frame = {}, const std::int64_t creation_stamp_ns = 0);

        bool tryConsumePendingGoal();

        bool mapReadyForPlanning() const;

        void ChangeState(const string &call_func, const MACHINE_STATE &new_state);

        virtual void publishPolyTraj() = 0;

        virtual void publishCurPoseToPath() = 0;

        virtual void resetVisualizedPath() = 0;
    };
}
