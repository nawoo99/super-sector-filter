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
#include <utils/optimization/polynomial_interpolation.h>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <string>


namespace fsm {
    class FsmRos2 : public Fsm {

        rclcpp::Node::SharedPtr nh_;
        rclcpp::Publisher<mars_quadrotor_msgs::msg::PositionCommand>::SharedPtr cmd_pub_;
        rclcpp::Publisher<mars_quadrotor_msgs::msg::PolynomialTrajectory>::SharedPtr mpc_cmd_pub_;
        rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_pub_;
        rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr goal_sub_;

        rclcpp::TimerBase::SharedPtr execution_timer_, replan_timer_, cmd_timer_;
        rclcpp::CallbackGroup::SharedPtr exec_cbk_group_, replan_cbk_group_, cmd_cbk_group_, goal_cbk_group_;

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

        mutable std::mutex latest_cmd_mutex_;
        mars_quadrotor_msgs::msg::PositionCommand last_published_cmd_{};
        bool last_published_cmd_valid_{false};

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
            map_age_s = std::chrono::duration<double>(
                    rog_map::MapHealthClock::now() -
                    health.latest_map_commit_time).count();
            return !health.update_in_progress &&
                   std::isfinite(map_age_s) && map_age_s >= 0.0 &&
                   map_age_s <= cfg_.trajectory_guard_max_map_age_s;
        }

        bool refreshSafetyCertificate(const char *trigger) {
            if (!cfg_.trajectory_guard_en) {
                return true;
            }
            const auto health = map_ptr_->getMapHealthSnapshot();
            const auto generation = planner_ptr_->getCommittedTrajectoryGeneration();
            double map_age_s;
            const bool map_fresh = mapFreshForGuard(health, map_age_s);

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

        void activateEmergencyBrake(const std::string &reason) {
            if (!cfg_.trajectory_guard_en ||
                safety_brake_active_.load(std::memory_order_acquire)) {
                return;
            }

            mars_quadrotor_msgs::msg::PositionCommand start_command;
            bool have_start_command;
            {
                std::lock_guard<std::mutex> lock(latest_cmd_mutex_);
                have_start_command = last_published_cmd_valid_;
                if (have_start_command) {
                    start_command = last_published_cmd_;
                }
            }

            StatePVAJ initial;
            initial.setZero();
            double initial_yaw = 0.0;
            if (have_start_command) {
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
            } else {
                CmdTraj::Sample current_sample;
                if (!planner_ptr_->getOneCommandSample(current_sample)) {
                    initial.col(0) = robot_state_.p;
                    initial.col(1) = robot_state_.v;
                    initial.col(2).setZero();
                    initial.col(3).setZero();
                    initial_yaw = robot_state_.yaw;
                } else {
                    initial = current_sample.pvaj;
                    initial_yaw = current_sample.yaw;
                }
            }

            if (!initial.array().isFinite().all()) {
                ros_ptr_->error(" -- [TRAJ_GUARD_BRAKE] invalid initial state; "
                                "normal publication remains suppressed");
                return;
            }
            if (!std::isfinite(initial_yaw)) initial_yaw = 0.0;

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
            for (int attempt = 0; attempt < 30; ++attempt) {
                brake_trajectory = buildBrakeTrajectory(initial, duration, start_wt);
                dynamics_ok = brakeDynamicsWithinLimits(brake_trajectory,
                                                        max_acc, max_jerk);
                if (dynamics_ok || duration >= max_duration - 1.0e-9) {
                    break;
                }
                duration = std::min(max_duration, duration * 1.15);
            }

            Eigen::Matrix<double, 3, 1> yaw_coeff;
            yaw_coeff.setZero();
            yaw_coeff(0, 0) = initial_yaw;
            Trajectory yaw_trajectory;
            yaw_trajectory.emplace_back(duration, yaw_coeff);
            yaw_trajectory.start_WT = start_wt;

            const auto brake_safety = planner_ptr_->validatePositionTrajectory(
                    brake_trajectory, 0.0, 0);
            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                if (safety_brake_active_.load(std::memory_order_relaxed)) {
                    return;
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
                            "speed0={:.3f} max_acc={:.3f} max_jerk={:.3f} "
                            "dynamics_ok={} path_status={} stop=[{:.3f},{:.3f},{:.3f}]",
                            reason, duration, initial.col(1).norm(), max_acc, max_jerk,
                            dynamics_ok, trajectorySafetyStatusName(brake_safety.status),
                            stop_position.x(), stop_position.y(), stop_position.z());
            if (!brake_safety.safe()) {
                ros_ptr_->error(" -- [TRAJ_GUARD_BRAKE_PATH_UNSAFE] status={} "
                                "collision_tt={:.3f} p=[{:.3f},{:.3f},{:.3f}]; "
                                "executing shortest bounded stop",
                                trajectorySafetyStatusName(brake_safety.status),
                                brake_safety.first_collision_tt,
                                brake_safety.first_collision_pos.x(),
                                brake_safety.first_collision_pos.y(),
                                brake_safety.first_collision_pos.z());
            }
            mars_quadrotor_msgs::msg::PolynomialTrajectory brake_message;
            fillPolynomialTrajectory(brake_trajectory, yaw_trajectory,
                                     brake_message, true);
            mpc_cmd_pub_->publish(brake_message);
            ChangeState("TrajectoryGuard", EMER_STOP);
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
            if (health.update_in_progress ||
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
            last_published_cmd_valid_ = true;
        }

    public:
        FsmRos2() = default;

        ~FsmRos2() {
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
            // Map commits and all planner/map queries share one mutually
            // exclusive group. Odom/cloud callbacks only stage snapshots and
            // remain independent, so long map writes cannot race planning.
            exec_cbk_group_ = nh_->create_callback_group(
                    rclcpp::CallbackGroupType::MutuallyExclusive);
            map_ptr_ = std::make_shared<rog_map::ROGMapROS>(
                    nh_, cfg_path, exec_cbk_group_);
            // 初始化Planner
            ros_ptr_ = std::make_shared<ros_interface::Ros2Interface>(nh_);
            planner_ptr_ = std::make_shared<SuperPlanner>(cfg_path, ros_ptr_, map_ptr_);
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
                if (health_after.update_in_progress ||
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
            if (safety_brake_active_.load(std::memory_order_acquire)) {
                tryRecoverFromEmergencyBrake();
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
