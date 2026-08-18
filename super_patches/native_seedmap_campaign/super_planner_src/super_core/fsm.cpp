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

#include <fsm/fsm.h>
#include <algorithm>
#include <chrono>
#include <limits>
#include <memory>

using namespace super_utils;

namespace fsm {
    Fsm::~Fsm() {
        write_time_.close();
    }

    void Fsm::WriteTimeToLog() {
        write_time_ << (ros_ptr_->getSimTime() - system_start_time_) << ", ";
        for (long unsigned int i = 0; i < log_module_time.size(); i++) {
            write_time_ << log_module_time[i];
            if (i != log_module_time.size() - 1) {
                write_time_ << ", ";
            }
        }
        write_time_ << endl;
    }

    void Fsm::callReplanOnce() {
        if (stop) {
            return;
        }

        if (machine_state_ != FOLLOW_TRAJ) {
            return;
        }

        if (finish_plan) {
            return;
        }

        if (plan_from_rest_) {
            plan_from_rest_ = false;
            return;
        }

        planner_ptr_->getMap()->getNearestInfCellNot(GridType::OCCUPIED, gi_.goal_p, gi_.goal_p, 3.0);

        TimeConsuming replan_once_time("replan_once_time", false);

        RET_CODE ret_code = planner_ptr_->ReplanOnce(gi_.goal_p, gi_.goal_yaw, gi_.new_goal);
        ros_ptr_->pubReplanStatus(ret_code != FAILED && ret_code != EMER);
        if (ret_code == FAILED) {
//            cout << YELLOW << " -- [Fsm] ReplanOnce failed." << RESET << endl;
        } else { cout << GREEN << " -- [Fsm] ReplanOnce succeed." << RESET << endl; }

        if (ret_code == EMER) {
            ChangeState("ReplanTimerCallback", EMER_STOP);
        } else if (ret_code == NEW_TRAJ) {
            ChangeState("ReplanTimerCallback", GENERATE_TRAJ);
        } else if (ret_code == SUCCESS || ret_code == FINISH) {
            gi_.new_goal = false;
            publishPolyTraj();
        }

        planner_ptr_->getModuleTimeConsuming(log_module_time);
        log_module_time[log_module_time.size() - 2] = replan_once_time.stop();
        // save on log
        replan_logs_.push_back(planner_ptr_->getLatestReplanLog());
        WriteTimeToLog();
    }

    void Fsm::callMainFsmOnce() {
        if (stop) {
            return;
        }
        static double fsm_start_time = ros_ptr_->getSimTime();
        double cur_t = (ros_ptr_->getSimTime() - fsm_start_time);
        static double last_print_t = 0.0;
        planner_ptr_->getRobotState(robot_state_);

        const bool odom_ready = robot_state_.rcv &&
                                (ros_ptr_->getSimTime() - robot_state_.rcv_time) <= 0.1;

        if (cur_t - last_print_t > 1.0) {
            last_print_t = cur_t;
            if (!odom_ready) {
                cout << YELLOW << " -- [Fsm] No odom." << RESET << endl;
            }
            if (!started_) {
                cout << YELLOW << " -- [Fsm] Wait for goal." << RESET << endl;
            }
            cout << std::fixed << std::setprecision(3);
            cout << GREEN << " -- [Fsm " << cur_t << "] Current state: " << MACHINE_STATE_STR[machine_state_]
                 << RESET << endl;
        }

        if (!odom_ready) {
            return;
        }

        switch (machine_state_) {
            case INIT: {
                if (!started_) {
                    return;
                }
                ChangeState("MainFsmCallback", WAIT_GOAL);
                break;
            }
            case WAIT_GOAL: {
                if (!mapReadyForPlanning()) {
                    return;
                }
                tryConsumePendingGoal();
                if (!gi_.new_goal) {
                    return;
                } else {
                    ChangeState("MainFsmCallback", GENERATE_TRAJ);
                }
                resetVisualizedPath();
                break;
            }
            case GENERATE_TRAJ: {
                // Revalidate immediately before planning because readiness may
                // change after the WAIT_GOAL transition.
                if (!mapReadyForPlanning()) {
                    return;
                }
                tryConsumePendingGoal();
                if (closeToGoal(0.1)) {
                    ChangeState("MainFsmCallback", WAIT_GOAL);
                    gi_.new_goal = false;
                    finish_plan = true;
                    return;
                }
                int retcode = planner_ptr_->PlanFromRest(gi_.goal_p, gi_.goal_yaw, gi_.new_goal);
                if (!planner_ptr_->goalValid()) {
                    cout << YELLOW << " -- [Fsm] Goal is invalid, skip this goal." << RESET << endl;
                    gi_.new_goal = false;
                    ChangeState("MainFsmCallback", WAIT_GOAL);
                    return;
                }
                if (retcode == SUCCESS || retcode == FINISH) {
                    gi_.new_goal = false;
                    plan_from_rest_ = true;
                    finish_plan = false;
                    if (retcode == FINISH) {
                        finish_plan = true;
                    }

                    publishPolyTraj();

                    ChangeState("MainFsmCallback", FOLLOW_TRAJ);
                } else {
                    cout << YELLOW << " -- [Fsm] PlanFromRest failed, try replan." << RESET << endl;
                    // ros::Duration(0.1).sleep();
                }
                replan_logs_.push_back(planner_ptr_->getLatestReplanLog());
                break;
            }
            case FOLLOW_TRAJ: {
                // Preserve live goal updates while keeping pre-readiness goals
                // in the single-slot latest-wins queue.
                tryConsumePendingGoal();
                publishCurPoseToPath();
                break;
            }
            case EMER_STOP: {
                // 2026-08-18: used to always fall back to WAIT_GOAL here,
                // discarding gi_.goal_p/goal_yaw even though they're still
                // valid -- WAIT_GOAL then sits idle until
                // mission_planner's own goal-republish timer fires
                // (waypoint.yaml's publish_dt, 1 Hz), since the goal itself
                // never changed so nothing else re-enqueues it sooner.
                // Measured on seed9: 98 EMER_STOP entries in one 120 s
                // run, each paying up to ~1 s here for no reason, adding
                // up to the FSM spending 60% of 1 s sampled ticks in
                // WAIT_GOAL and only 19% actually in FOLLOW_TRAJ. Retrying
                // GENERATE_TRAJ directly with the already-known goal
                // instead lets recovery run at the FSM's own replan rate
                // (15 Hz) rather than mission_planner's unrelated 1 Hz
                // polling interval. If the goal was already reached,
                // GENERATE_TRAJ's own closeToGoal() check immediately
                // sends it back to WAIT_GOAL anyway, so this doesn't need
                // its own separate check for that case.
                if (started_) {
                    gi_.new_goal = true;
                    ChangeState("MainFsmCallback", GENERATE_TRAJ);
                } else {
                    ChangeState("MainFsmCallback", WAIT_GOAL);
                }
                break;
            }
            default:
                break;
        }
    }

    bool Fsm::closeToGoal(const double &thresh_dis) {
        /// The close to goal should consider the the local shift
        /// All goal should be in the known free on inf map.
        /// The intermedia points should be in free space.
        double dis = (robot_state_.p - gi_.goal_p).norm();
        return dis < thresh_dis;
    }

    void Fsm::enqueueGoal(const Vec3f &p, const Quatf &q) {
        {
            std::lock_guard<std::mutex> lock(pending_goal_mutex_);
            pending_goal_.goal_p = p;
            pending_goal_.goal_q = q;
            pending_goal_.valid = true;
        }
        started_.store(true, std::memory_order_release);
    }

    bool Fsm::tryConsumePendingGoal() {
        {
            std::lock_guard<std::mutex> lock(pending_goal_mutex_);
            if (!pending_goal_.valid) {
                return false;
            }
        }

        if (!mapReadyForPlanning()) {
            return false;
        }

        PendingGoal pending_goal;
        {
            std::lock_guard<std::mutex> lock(pending_goal_mutex_);
            if (!pending_goal_.valid) {
                return false;
            }
            pending_goal = pending_goal_;
            pending_goal_.valid = false;
        }

        auto click_point = pending_goal.goal_p;
        if (cfg_.click_height > -5) {
            click_point.z() = cfg_.click_height;
        }

        Vec3f goal_p;
        if (planner_ptr_->getMap()->getNearestInfCellNot(GridType::OCCUPIED, click_point, goal_p, 3.0)) {
            cout << GREEN << " -- [Fsm] Get goal at " << RESET << goal_p.transpose() << endl;
        } else {
            fmt::print(fg(fmt::color::indian_red), "Goal is deeply occupied, skip this goal.\n");
            return false;
        }

        if ((robot_state_.p - goal_p).norm() < 0.1) {
            //                print(fg(color::gray), " -- [Rviz] Too close to goal, skip this target.\n");
            return false;
        }

        double goal_yaw;
        if (cfg_.click_yaw_en) {
            const auto &q = pending_goal.goal_q;
            if (std::isnan(q.w()) || std::isnan(q.x()) || std::isnan(q.y()) || std::isnan(q.z())) {
                goal_yaw = NAN;
                ros_ptr_->info(" -- [Fsm] Receive click goal at: [{}, {}, {}]; goal yaw disabled",
                               goal_p.x(), goal_p.y(), goal_p.z());
            } else {
                goal_yaw = geometry_utils::get_yaw_from_quaternion(q);
                cout << GREEN << " -- [Fsm] Receive click goal at: [" << goal_p.transpose() << "]; goal yaw: "
                     << goal_yaw * 57.3 << " deg" << RESET << endl;
            }

        } else {
            goal_yaw = NAN;
            cout << GREEN << " -- [Fsm] Receive click goal at: [" << goal_p.transpose() << "]; goal yaw disabled"
                 << RESET << endl;
        }

        gi_.goal_p = goal_p;
        gi_.goal_yaw = goal_yaw;
        gi_.new_goal = true;
        finish_plan = false;
        plan_from_rest_ = false;
        return true;
    }

    bool Fsm::mapReadyForPlanning() const {
        if (!cfg_.map_readiness_en) {
            return true;
        }

        const auto health = planner_ptr_->getMap()->getMapHealthSnapshot();
        const auto now = rog_map::MapHealthClock::now();

        const auto min_accepted_scans = static_cast<std::uint64_t>(
                std::max(0, cfg_.map_readiness_min_accepted_scans));
        const auto min_committed_scans = static_cast<std::uint64_t>(
                std::max(0, cfg_.map_readiness_min_committed_scans));
        const auto max_commit_lag_scans = static_cast<std::uint64_t>(
                std::max(0, cfg_.map_readiness_max_commit_lag_scans));

        const double infinity = std::numeric_limits<double>::infinity();
        const double scan_span_s = health.accepted_scan_count > 0
                ? std::chrono::duration<double>(health.latest_accepted_scan_time -
                                                health.first_accepted_scan_time).count()
                : 0.0;
        const double accepted_cloud_age_s = health.accepted_scan_count > 0
                ? std::chrono::duration<double>(now - health.latest_accepted_scan_time).count()
                : infinity;
        const double committed_cloud_age_s = health.committed_scan_count > 0
                ? std::chrono::duration<double>(now - health.latest_committed_scan_rx_time).count()
                : infinity;
        const bool immutable_snapshot =
                planner_ptr_->getMap()->immutablePlannerSnapshotEnabled();
        const auto freshness_time = immutable_snapshot &&
                                    health.processed_scan_count > 0
                ? health.latest_scan_process_time
                : health.latest_map_commit_time;
        const double map_age_s = health.map_version > 0
                ? std::chrono::duration<double>(now - freshness_time).count()
                : infinity;

        const std::uint64_t commit_lag_scans =
                health.latest_accepted_scan_seq > health.latest_committed_scan_seq
                ? health.latest_accepted_scan_seq - health.latest_committed_scan_seq
                : 0;

        bool ready = true;
        std::string reasons;
        const auto fail = [&ready, &reasons](const char *reason) {
            ready = false;
            if (!reasons.empty()) {
                reasons += ',';
            }
            reasons += reason;
        };
        if (health.accepted_scan_count < min_accepted_scans) fail("accepted_count");
        if (health.committed_scan_count < min_committed_scans) fail("committed_count");
        if (health.map_version == 0) fail("map_version");
        if (scan_span_s < cfg_.map_readiness_min_scan_span_s) fail("scan_span");
        if (accepted_cloud_age_s < 0.0 ||
            accepted_cloud_age_s > cfg_.map_readiness_max_cloud_age_s) {
            fail("accepted_cloud_age");
        }
        if (committed_cloud_age_s < 0.0 ||
            committed_cloud_age_s > cfg_.map_readiness_max_cloud_age_s) {
            fail("committed_cloud_age");
        }
        if (map_age_s < 0.0 || map_age_s > cfg_.map_readiness_max_map_age_s) fail("map_age");
        if (commit_lag_scans > max_commit_lag_scans) fail("commit_lag");
        if (health.update_in_progress &&
            !planner_ptr_->getMap()->immutablePlannerSnapshotEnabled()) {
            fail("update_in_progress");
        }

        {
            std::lock_guard<std::mutex> lock(map_readiness_log_mutex_);
            if (ready && !map_ready_logged_) {
                map_ready_logged_ = true;
                fmt::print(" -- [Fsm] MAP_READY accepted={} committed={} version={} lag={} "
                           "span={:.3f}s cloud_age={:.3f}s committed_cloud_age={:.3f}s "
                           "commit_age={:.3f}s in_progress={}\n",
                           health.accepted_scan_count, health.committed_scan_count, health.map_version,
                           commit_lag_scans, scan_span_s, accepted_cloud_age_s, committed_cloud_age_s,
                           map_age_s, health.update_in_progress);
            } else if (!ready &&
                       now - last_map_readiness_log_time_ >= std::chrono::seconds(1)) {
                last_map_readiness_log_time_ = now;
                fmt::print(" -- [Fsm] MAP_NOT_READY reason={} accepted={} committed={} version={} lag={} "
                           "span={:.3f}s cloud_age={:.3f}s committed_cloud_age={:.3f}s "
                           "commit_age={:.3f}s in_progress={}\n",
                           reasons, health.accepted_scan_count, health.committed_scan_count,
                           health.map_version, commit_lag_scans, scan_span_s, accepted_cloud_age_s,
                           committed_cloud_age_s, map_age_s, health.update_in_progress);
            }
        }
        return ready;
    }

    void Fsm::ChangeState(const string &call_func, const MACHINE_STATE &new_state) {
        const MACHINE_STATE old_state = machine_state_.load(std::memory_order_acquire);
        fmt::print(fg(fmt::color::green), " -- [Fsm]: [{}] change state from [{}] to [{}].\n", call_func,
                   MACHINE_STATE_STR[int(old_state)], MACHINE_STATE_STR[int(new_state)]);
        machine_state_.store(new_state, std::memory_order_release);
    }
}
