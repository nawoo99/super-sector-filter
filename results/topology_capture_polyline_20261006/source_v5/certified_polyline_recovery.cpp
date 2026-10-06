#include <super_core/super_planner.h>
#include <utils/optimization/polynomial_interpolation.h>
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace super_planner {
using namespace super_utils;
bool SuperPlanner::tryCommitCertifiedPolylineRecovery(const Vec3f& start_p) {
    const char* option = std::getenv("SUPER_CERTIFIED_POLYLINE_RECOVERY");
    if (!option || std::string(option) != "1" ||
        !cfg_.guard_topology_reroute_en || !cfg_.guard_viability_en ||
        !guard_topology_recovery_exhausted_ ||
        guard_topology_polyline_attempts_ >= 1) return false;
    Vec3f held;
    double yaw, speed;
    { std::lock_guard<std::mutex> lock(drone_state_mutex_);
      held = robot_state_.p; yaw = robot_state_.yaw;
      speed = robot_state_.v.norm(); }
    if (!held.array().isFinite().all() || !std::isfinite(yaw) ||
        !std::isfinite(speed) || !start_p.array().isFinite().all() ||
        (held-start_p).norm() > 0.15 ||
        speed > cfg_.guard_topology_reroute_max_stop_speed_mps) return false;
    // One additional, explicitly selected topology strategy per episode.
    // No reset on short commits; no counterfactual-path reuse. A fresh search
    // has no artificial zones but still uses real inflated occupied cells.
    ++guard_topology_polyline_attempts_;
    auto transaction = map_ptr_->acquireMapReadTransaction();
    const auto version = map_ptr_->getMapHealthSnapshot().map_version;
    Vec3f seed;
    if (!map_ptr_->getNearestInfCellNot(OCCUPIED, held, seed, 0.5)) return false;
    vec_Vec3f path;
    const int flags = path_search::ON_INF_MAP | path_search::DONT_USE_INF_NEIGHBOR |
            (cfg_.frontend_in_known_free ? path_search::UNKNOWN_AS_OCCUPIED
                                         : path_search::UNKNOWN_AS_FREE);
    const auto result = astar_ptr_->pointToPointPathSearch(
            seed, gi_.goal_p, flags, std::min(4.0, cfg_.planning_horizon), path,
            vec_Vec3f{}, std::vector<double>{});
    if ((result != REACH_GOAL && result != REACH_HORIZON) || path.size() < 2) {
        ros_ptr_->warn(" -- [TRAJ_GUARD_POLYLINE_REJECT] reason=fresh_search result={}",
                       RET_CODE_STR[result]);
        return false;
    }
    // Monotone straight-line quintics with a physical stop at each corner.
    // This avoids global spline bowing. Shortcuts require inflated-map LOS;
    // held-to-seed egress still passes the existing bounded footprint guard.
    vec_Vec3f knots{held};
    if ((seed-held).norm() > 1.0e-6) knots.push_back(seed);
    std::size_t index = 0;
    while (index+1 < path.size() && knots.size() <= 24) {
        std::size_t next = index+1;
        for (std::size_t j = path.size()-1; j > index; --j) {
            if (map_ptr_->isLineFree(path[index], path[j], true,
                                    cfg_.frontend_in_known_free)) {
                next = j; break;
            }
        }
        if ((path[next]-knots.back()).norm() > 1.0e-6) knots.push_back(path[next]);
        index = next;
    }
    const double displacement = (knots.back().head<2>()-held.head<2>()).norm();
    if (index+1 != path.size() || knots.size() < 2 || knots.size() > 24 ||
        !std::isfinite(displacement) ||
        (displacement < cfg_.guard_topology_episode_progress_reset_m &&
         (knots.back()-gi_.goal_p).norm() > cfg_.resolution*2) ||
        map_ptr_->getMapHealthSnapshot().map_version != version) {
        ros_ptr_->warn(" -- [TRAJ_GUARD_POLYLINE_REJECT] reason=route_or_version knots={}",knots.size());
        return false;
    }
    transaction.unlock();
    Trajectory position, heading;
    const double velocity = std::max(1.0e-3, 0.8*cfg_.exp_traj_cfg.max_vel);
    const double acceleration = std::max(1.0e-3, 0.8*cfg_.exp_traj_cfg.max_acc);
    const double jerk = std::max(1.0e-3, 0.8*cfg_.exp_traj_cfg.max_jerk);
    for (std::size_t i = 1; i < knots.size(); ++i) {
        const double distance = (knots[i]-knots[i-1]).norm();
        const double duration = std::max({cfg_.guard_direct_goal_fallback_min_duration_s,
                1.875*distance/velocity, std::sqrt(5.774*distance/acceleration),
                std::cbrt(60.0*distance/jerk)});
        Eigen::Matrix<double,3,3> initial = Eigen::Matrix<double,3,3>::Zero();
        Eigen::Matrix<double,3,3> final = Eigen::Matrix<double,3,3>::Zero();
        initial.col(0) = knots[i-1]; final.col(0) = knots[i];
        Eigen::Matrix<double,3,Eigen::Dynamic> waypoints(3,0);
        VecDf times(1); times << duration;
        position.append(poly_interpo::minimumJerkInterpolation<3>(initial,final,waypoints,times));
        Eigen::Matrix<double,1,3> yaw_state = Eigen::Matrix<double,1,3>::Zero();
        yaw_state(0,0) = yaw;
        Eigen::Matrix<double,1,Eigen::Dynamic> yaw_knots(1,0);
        heading.append(poly_interpo::minimumJerkInterpolation<1>(yaw_state,yaw_state,yaw_knots,times));
    }
    const auto now = ros_ptr_->getSimTime();
    position.start_WT = heading.start_WT = now;
    ExpTraj recovery;
    recovery.setTrajectory(now,position,heading);
    recovery.setGoalConnectedFlag((knots.back()-gi_.goal_p).norm() < cfg_.resolution*2);
    CmdTraj::Candidate candidate;
    if (!CmdTraj::buildCandidate(recovery,candidate) ||
        !commitTrajectoryCandidate(std::move(candidate), "PlanFromRest/certified_polyline_recovery")) {
        ros_ptr_->warn(" -- [TRAJ_GUARD_POLYLINE_REJECT] reason=unchanged_certificate knots={}",knots.size());
        return false;
    }
    last_exp_traj_info_ = recovery;
    robot_on_backup_traj_ = false; gi_.new_goal = false;
    guard_rest_to_rest_hold_until_wt_ = now + cmd_traj_info_.getTotalDuration();
    ros_ptr_->vizCommittedTraj(cmd_traj_info_.posTraj(),-1);
    latest_replan.setRetCode(SUPER_RET_CODE::SUPER_SUCCESS_NO_BACKUP);
    ros_ptr_->warn(" -- [TRAJ_GUARD_POLYLINE_RECOVERY] action=commit attempt=1/1 "
                   "knots={} displacement={:.3f} duration={:.3f} map={} "
                   "artificial_zones_used=0 certificate=unchanged",
                   knots.size(),displacement,cmd_traj_info_.getTotalDuration(),version);
    return true;
}
}
