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

#include <iostream>
#include <fstream>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <limits>
#include <optional>
#include <string>
#include <thread>
#include "Eigen/Eigen"


#include <super_core/config.hpp>
#include <ros_interface/ros1/ros1_interface.hpp>
#include <data_structure/base/trajectory.h>

#include <data_structure/base/polytope.h>


#include "traj_opt/exp_traj_optimizer_s4.h"
#include "traj_opt/backup_traj_optimizer_s4.h"
#include "path_search/astar.h"
#include "rog_map/rog_map.h"
#include "super_core/corridor_generator.h"
#include "super_core/fov_checker.h"

#include "traj_opt/yaw_traj_opt.h"
#include "super_core/super_ret_code.hpp"
#include "utils/header/fmt_eigen.hpp"

#include <super_core/log_utils.hpp>
#include <data_structure/exp_traj.h>
#include <data_structure/cmd_traj.h>
#include <data_structure/backup_traj.h>


namespace super_planner {
    using namespace color_text;
    using namespace geometry_utils;

    enum class TrajectorySafetyStatus : std::uint8_t {
        DISABLED = 0,
        SAFE,
        EMPTY_TRAJECTORY,
        INVALID_TRAJECTORY,
        MAP_NOT_COMMITTED,
        MAP_UPDATING,
        MAP_STALE,
        OCCUPIED,
        CLEARANCE_MARGIN,
        // Distinct from CLEARANCE_MARGIN: the point isn't near a detected
        // obstacle at all, it has simply never been swept by the sensor.
        // Only produced when a caller opts in via
        // validatePositionTrajectory's unknown_as_occupied parameter.
        UNOBSERVED,
        OUT_OF_MAP,
        VERSION_CHANGED
    };

    struct TrajectorySafetyResult {
        TrajectorySafetyStatus status{TrajectorySafetyStatus::INVALID_TRAJECTORY};
        std::uint64_t trajectory_generation{0};
        std::uint64_t map_version{0};
        double checked_from_tt{0.0};
        double checked_to_tt{0.0};
        double first_collision_tt{-1.0};
        Vec3f first_collision_pos{Vec3f::Zero()};
        std::size_t checked_samples{0};
        double map_wait_ms{0.0};
        double map_query_ms{0.0};
        double trajectory_eval_ms{0.0};
        double voxelize_ms{0.0};
        bool used_clearance_escape{false};
        double clearance_escape_completed_tt{-1.0};

        bool safe() const {
            return status == TrajectorySafetyStatus::SAFE ||
                   status == TrajectorySafetyStatus::DISABLED;
        }
    };

    const char *trajectorySafetyStatusName(TrajectorySafetyStatus status);

    class SuperPlanner {
        LogOneReplan latest_replan;
        super_planner::Config cfg_;
        rog_map::ROGMapROS::Ptr map_ptr_;
        CorridorGenerator::Ptr cg_ptr_;
        CorridorGenerator::Ptr cg_guard_retry_ptr_;
        // Paper-faithful (theorem 1) CIRI instance: raw points, no map
        // inflation, margin matching cg_ptr_'s own (not the tight retry
        // generator's near-zero margin). Used only by
        // checkKnownFreeViaCloud, currently called shadow-only from
        // activateEmergencyBrake.
        CorridorGenerator::Ptr cg_brake_ptr_;
        path_search::Astar::Ptr astar_ptr_;
        ros_interface::RosInterface::Ptr ros_ptr_;
        Vec3f shifted_sfc_start_pt_;

        traj_opt::ExpTrajOpt::Ptr exp_traj_opt_;
        traj_opt::BackupTrajOpt::Ptr back_traj_opt_;
        traj_opt::YawTrajOpt::Ptr yaw_traj_opt_;

        CIRI::Ptr ciri_;

        super_utils::RobotState robot_state_;

        std::mutex drone_state_mutex_;
        std::mutex replan_lock_;

        Vec3f local_start_p_;

        std::atomic_bool robot_on_backup_traj_{false};
        // use negative value to indicate the traj is not available
        double on_backup_start_WT{-1}, on_backup_end_WT{-1};

        double planner_process_start_WT_;

        struct GoalInfo {
            Vec3f goal_p{0, 0, 0};
            double goal_yaw{0};
            bool new_goal{true};
            bool goal_valid{true};
        } gi_;

        FOVChecker::Ptr fov_checker_;

        CmdTraj cmd_traj_info_;
        ExpTraj last_exp_traj_info_;
        std::atomic_bool trajectory_guard_rejection_pending_{false};
        std::atomic_bool guard_corridor_retry_pending_{false};
        // Consecutive corridor searches done in retry mode since the last
        // successful commit. Used to periodically alternate back to the
        // normal corridor generator instead of staying locked into the
        // tight-margin retry generator for the whole stall.
        std::atomic_int guard_corridor_retry_attempts_{0};
        vec_E<Vec3f> guard_topology_avoidance_centers_;
        std::vector<double> guard_topology_avoidance_radii_;
        // One fixed XY direction and current chain depth per rejected-route
        // branch.  A genuinely new outgoing direction gets its own blocker
        // next to the stopped pose instead of extending an unrelated chain.
        vec_E<Vec3f> guard_topology_branch_directions_;
        std::vector<int> guard_topology_branch_depths_;
        int guard_topology_no_path_failures_{0};
        int guard_topology_base_no_path_recoveries_{0};
        int guard_topology_saturation_recoveries_{0};
        int guard_topology_local_escape_recoveries_{0};
        int guard_topology_corridor_failures_{0};
        // Consecutive failures after A* and CIRI have both succeeded.  A
        // virtual blocker can leave a geometrically valid corridor whose
        // MINCO boundary-value problem is infeasible from a later certified
        // stop; that failure needs the same bounded epoch reseed as NO_PATH.
        int guard_topology_post_corridor_failures_{0};
        std::uint64_t guard_topology_epoch_{0};
        Vec3f guard_topology_goal_{Vec3f::Zero()};
        bool guard_topology_goal_valid_{false};
        std::uint64_t guard_topology_stall_generation_{0};
        Vec3f guard_topology_stall_collision_{Vec3f::Zero()};
        int guard_topology_stall_rejects_{0};
        std::atomic_bool guard_certified_stop_for_reroute_{false};
        std::atomic_bool guard_local_escape_pending_{false};
        Vec3f guard_local_escape_direction_{Vec3f::Zero()};
        std::atomic_bool guard_vertical_recovery_pending_{false};
        // Suppress the periodic moving-state replanner until a short
        // rest-to-rest recovery (vertical lift or direct final connection)
        // completes; otherwise it can replace the recovery on the next 15 Hz
        // tick and can splice incompatible polynomial orders.
        double guard_rest_to_rest_hold_until_wt_{-
                std::numeric_limits<double>::infinity()};

        struct ShadowValidationJob {
            CmdTraj::SharedSnapshot trajectory;
            std::string phase;
        };
        std::mutex shadow_worker_mutex_;
        std::condition_variable shadow_worker_cv_;
        std::optional<ShadowValidationJob> pending_shadow_job_;
        bool stop_shadow_worker_{false};
        std::thread shadow_worker_;
        std::chrono::steady_clock::time_point last_shadow_validation_time_{};
        vec_E<Vec3f> trajectory_guard_clearance_offsets_;
        vec_E<Vec3f> trajectory_physical_clearance_offsets_;
        double trajectory_guard_hard_clearance_m_{0.0};

        vector<double> time_consuming_;

    public:
        EIGEN_MAKE_ALIGNED_OPERATOR_NEW

        explicit SuperPlanner(const std::string &cfg_path,
                              const ros_interface::RosInterface::Ptr &ros_ptr,
                              const rog_map::ROGMapROS::Ptr &map_ptr);

        ~SuperPlanner();

        void lockCommittedTraj() {
            cmd_traj_info_.lock();
        }

        void unlockCommittedTraj() {
            cmd_traj_info_.unlock();
        }

        bool goalValid() const {
            return gi_.goal_valid;
        }

        typedef std::shared_ptr<SuperPlanner> Ptr;

        void getOneHeartbeatTime(double &start_WT_pos, bool &traj_finish);

        Trajectory getCommittedPositionTrajectory();

        Trajectory getCommittedYawTrajectory();

        void getOneCommandFromTraj(StatePVAJ &pvaj,
                                   double &yaw,
                                   double &yaw_dot,
                                   bool &on_backup_traj,
                                   bool &traj_finish);

        bool getOneCommandSample(CmdTraj::Sample &sample,
                                 std::uint64_t expected_generation = 0) const;

        CmdTraj::Snapshot getCommittedTrajectorySnapshot() const;

        std::uint64_t getCommittedTrajectoryGeneration() const;

        bool trajectoryGuardEnabled() const {
            return cfg_.trajectory_guard_en;
        }

        bool trajectoryGuardShadowEnabled() const {
            return cfg_.trajectory_guard_shadow_en &&
                   !cfg_.trajectory_guard_en;
        }

        bool consumeTrajectoryGuardRejection() {
            return trajectory_guard_rejection_pending_.exchange(
                    false, std::memory_order_acq_rel);
        }

        // The FSM owns the emergency-brake certificate and is the only layer
        // that knows the brake has finished at a fresh-map-certified terminal
        // hold. Expose that fact to PlanFromRest recovery instead of inferring
        // it from a separately sampled odometry speed.
        void setCertifiedStopForReroute(const bool active) {
            guard_certified_stop_for_reroute_.store(
                    active, std::memory_order_release);
        }

        // Paper-faithful (theorem 1) known-free check: builds a CIRI
        // polytope from the caller-supplied accumulated raw cloud, seeded
        // on the line from the current position to seed_far_pt, and
        // reports whether every sample of candidate (from checked_from_tt
        // onward) lies inside every one of the polytope's half-spaces. The
        // caller (fsm_ros2.hpp) is responsible for the accumulator-health
        // check (recency, point count) before calling this -- an empty
        // local cloud is treated as open space here (matching
        // GeneratePolytopeFromLine's convention), which is only a sound
        // reading of theorem 1 if the input truly was "sufficiently
        // dense" per the paper's own precondition.
        bool checkKnownFreeViaCloud(const Vec3f &seed_near_pt,
                                    const Vec3f &seed_far_pt,
                                    const vec_E<Vec3f> &accumulated_cloud,
                                    const Trajectory &candidate,
                                    double checked_from_tt,
                                    Vec3f &first_violation_pos);

        // unknown_as_occupied is a per-call override, not the general
        // cfg_.trajectory_guard_unknown_as_occupied: normal EXP/backup
        // candidates must be allowed to extend into never-yet-observed
        // space (that's inherent to exploring with a live sensor), so only
        // the emergency-brake candidate in fsm_ros2.hpp's
        // activateEmergencyBrake() passes true here. A brake target should
        // never rely on space nobody has actually looked at yet.
        TrajectorySafetyResult validatePositionTrajectory(
                const Trajectory &trajectory,
                double checked_from_tt,
                std::uint64_t trajectory_generation = 0,
                bool allow_initial_clearance_escape = false,
                bool unknown_as_occupied = false,
                const Vec3f *hard_current_pose = nullptr) const;

        TrajectorySafetyResult validateCommittedTrajectory(double now_wt) const;

        // Shadow mode must re-check the trajectory already being executed
        // when a newer map commit becomes visible, not only when a candidate
        // trajectory is first committed.
        bool enqueueCommittedTrajectoryShadowValidation(const char *phase);

        void getModuleTimeConsuming(vector<double> &time);

        /* Tow type of replan strategy */
        RET_CODE PlanFromRest(const Vec3f &goal_p,
                              const double &goal_yaw,
                              const bool &new_goal);

        RET_CODE
        ReplanOnce(const Vec3f &goal_p,
                   const double &goal_yaw,
                   const bool &new_goal);

    private:
        bool trajectoryValidationEnabled() const {
            return cfg_.trajectory_guard_en || cfg_.trajectory_guard_shadow_en;
        }

        bool commitTrajectoryCandidate(
                CmdTraj::Candidate candidate, const char *phase,
                std::string *rejected_segment_out = nullptr);

        // Record a stopped PlanFromRest geometric rejection and, on bounded
        // same-generation/same-location intervals, extend an exclusion
        // cylinder chain along the rejected route. The first blocker is placed far
        // enough ahead that the current pose remains outside it; this lets A*
        // and CIRI represent an actual detour instead of starting inside an
        // artificial obstacle centred on the collision point.
        void armTopologyRouteBlock(const CmdTraj::Candidate &candidate,
                                   const TrajectorySafetyResult &safety,
                                   std::uint64_t candidate_generation,
                                   const Vec3f &start_pos,
                                   double current_speed_mps,
                                   bool certified_stop,
                                   bool collision_on_exp);

        bool armTopologyRouteBlockFromGuidePath(
                const vec_Vec3f &guide_path,
                const Vec3f &start_pos,
                const char *reason);

        void resetTopologyRecoveryState();

        bool tryCommitCertifiedDirectGoalFallback(const Vec3f &start_p,
                                                  const Vec3f &goal_p);

        bool tryCommitCertifiedLocalEscape(const Vec3f &start_p);

        bool tryCommitCertifiedVerticalRecovery(const Vec3f &start_p);

        // Returns a new trajectory tracing the exact same spatial path but
        // slowed down by factor k>1 (duration *= k). Used by the viability
        // guard to reduce speed without re-invoking the trajectory optimizer.
        Trajectory timeScaleTrajectory(const Trajectory &traj,
                                       double k) const;

        // True if a dynamically-limited, map-certified stop exists from the
        // given state. Mirrors the runtime emergency-brake search so this
        // check predicts what activateEmergencyBrake() could actually do.
        bool certifiedStopExistsFrom(const StatePVAJ &state,
                                     std::uint64_t trajectory_generation) const;

        // True if a certified stop exists from every sampled state along
        // pos_traj within cfg_.guard_viability_horizon_s of checked_from_tt.
        bool candidateStopsViable(const Trajectory &pos_traj,
                                  double checked_from_tt,
                                  std::uint64_t trajectory_generation) const;

        void enqueueShadowValidation(CmdTraj::SharedSnapshot snapshot,
                                     const char *phase);

        void shadowValidationLoop();

        RET_CODE generateExpTraj(ExpTraj &last_exp_traj_info,
                                 ExpTraj &out_exp_traj_info);

        /* For Backup traj generation */
        RET_CODE generateBackupTrajectory(ExpTraj &ref_exp_traj, BackupTraj &back_traj_info);

        int getNearestFurtherGoalPoint(const vec_E<Vec3f> &goals, const Vec3f &start_pt);

        bool PathSearch(const Vec3f &start_pt, const Vec3f &goal,
                        const double &searching_horizon,
                        vec_Vec3f &path,
                        bool planning_from_rest);


    public:
        void getRobotState(rog_map::RobotState &out);

        bool isEasyGoal(const Vec3f &goal_position);

        rog_map::ROGMapROS::Ptr &getMap() {
            return map_ptr_;
        }

        double ft{0}, bt{0};
        int ft_cnt{0}, bt_cnt{0};

        double getFrontendTime() {
            if (ft_cnt == 0) return -1;
            double ave_t = ft / ft_cnt;
            ft = 0;
            ft_cnt = 0;
            return ave_t;
        }

        double getBackendTime() {
            if (bt_cnt == 0) return -1;
            double ave_t = bt / bt_cnt;
            bt = 0;
            bt_cnt = 0;
            return ave_t;
        }

        void updateROGMap(const rog_map::PointCloud &cloud, const super_utils::Pose &pose) const {
            map_ptr_->updateMap(cloud, pose);
        }

        LogOneReplan getLatestReplanLog(const bool include_sfc_cloud = true) {
            auto latest_cloud = cg_ptr_->getLatestCloud();
            if (include_sfc_cloud) {
                latest_replan.setSfcPc(std::move(latest_cloud));
            }
            else {
                // Always consume the generator cloud, but do not retain it in
                // normal campaign logs when detailed logging is disabled.
                latest_replan.clearSfcPc();
            }
            latest_replan.setComptT(time_consuming_);
            return latest_replan;
        }
    };
}
