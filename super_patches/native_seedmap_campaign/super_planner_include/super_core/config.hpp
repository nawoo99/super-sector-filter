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


#ifndef SUPER_PLANNER_CONFIG_HPP
#define SUPER_PLANNER_CONFIG_HPP

#include <rog_map/rog_map_core/config.hpp>
#include <traj_opt/config.hpp>
#include <utils/header/yaml_loader.hpp>
#include <algorithm>
#include <cmath>

namespace super_planner {
    using namespace traj_opt;
    using std::cout;
    using std::endl;

    class Config {
    public:
        enum YawMode{
            YAW_TO_VEL = 1,
            YAW_TO_GOAL = 2
        };

        traj_opt::Config exp_traj_cfg, back_traj_cfg;

        // Bool Params
        bool visualization_en{true};
        bool detailed_log_en{false};
        bool backup_traj_en;
        bool use_fov_cut, print_log;
        bool goal_vel_en,goal_yaw_en;
        bool visual_process;
        bool frontend_in_known_free;
        bool trajectory_guard_en{false};
        // Validate and log candidate trajectories without rejecting or changing
        // command publication. Enforcement wins if both flags are true.
        bool trajectory_guard_shadow_en{false};

        double resolution;
        double planning_horizon;
        double receding_dis;
        double safe_corridor_line_max_length;
        // for fov cut
        double sensing_horizon;
        // horizontal FoV cut (deg half-angle; <=0 disables). Restricts backup corridor to +-angle
        // around the sensing direction so unsensed directions stay UNKNOWN (conservative, not free).
        double fov_horizontal_angle;
        // true = center the horizontal cut on body HEADING (models heading-locked sector filter);
        // false = center on the guide direction (models sensing toward where the planner wants to go)
        bool fov_center_heading;

        // Planning Params
        int obs_skip_num;
        double corridor_bound_dis, corridor_line_max_length;
        double replan_forward_dt;
        double sample_traj_dt;
        double robot_r;
        bool corridor_use_inflated_obstacles;
        // Seed-line visibility may use the operationally inflated map even
        // when CIRI itself is built from raw occupied points.
        bool corridor_use_inflated_seed_lines;
        // After a raw-corridor EXP candidate is rejected by the operational
        // guard, retry the next plan with an inflated-map corridor.
        bool corridor_guard_retry_inflated;
        // Once guard-corridor retry mode is entered it stays on until a
        // candidate finally commits, so a persistently rejected point is
        // permanently retried with the same tight-margin corridor generator.
        // Every Nth consecutive retry-mode attempt, fall back to the normal
        // (raw-obstacle, wider-margin) generator instead, so the search
        // isn't locked into one geometry the whole time. <=0 disables
        // alternation (always use the retry generator, prior behavior).
        int guard_corridor_retry_alternate_every{4};
        // While stopped under the certified guard hold, force subsequent A*
        // searches away from geometric rejection points instead of retrying
        // the same shortest-path topology.
        bool guard_topology_reroute_en{false};
        double guard_topology_reroute_radius_m{0.8};
        double guard_topology_reroute_growth_m{0.25};
        double guard_topology_reroute_max_radius_m{1.8};
        int guard_topology_reroute_max_zones{4};
        double guard_topology_reroute_max_stop_speed_mps{0.2};
        // A single collision-centred exclusion zone can contain the stopped
        // vehicle and still leave A* on the same route. Place vertical XY
        // cylinders ahead of the stopped pose instead, then extend that
        // blocked route after each bounded cluster of identical rejects.
        int guard_topology_reroute_escalate_every_rejects{3};
        double guard_topology_reroute_collision_merge_m{0.5};
        double guard_topology_reroute_start_clearance_m{0.05};
        double guard_topology_reroute_block_spacing_m{1.0};
        // Rejected routes that differ by more than this XY angle start a new
        // blocker branch at the stopped pose.  Without branch tracking, a
        // newly-selected detour inherited the old branch's forward index and
        // its first blocker could be several metres away, leaving the same
        // start-adjacent guard violation completely unblocked.
        double guard_topology_reroute_direction_merge_angle_deg{30.0};
        // A set of virtual blockers can itself make the certified-stop start
        // disconnected. After this many consecutive A* NO_PATH results,
        // discard that finite search epoch and rebuild topology from fresh
        // guarded candidates.
        int guard_topology_reroute_no_path_reset_attempts{3};
        // A saturated set of horizontal route blockers cannot resolve a
        // rejection caused by the floor immediately below a certified stop.
        // In that narrowly-detected case, allow one guarded rest-to-rest
        // vertical lift before rebuilding horizontal topology.
        bool guard_topology_vertical_recovery_en{false};
        double guard_topology_vertical_recovery_lift_m{0.6};
        double guard_topology_vertical_recovery_trigger_distance_m{0.75};
        // Once every configured horizontal blocker slot has been consumed,
        // allow a bounded number of guarded vertical topology changes per
        // mission goal.  The lift is still committed only if the unchanged
        // geometric and stop-viability guards certify it.
        int guard_topology_saturation_vertical_attempts{1};
        // A stopped search can return NO_PATH before any rejected trajectory
        // exists, so there is no collision point from which to build a
        // horizontal blocker. Allow a small, explicitly bounded number of
        // guarded lifts for that base-NO_PATH case per mission goal.
        int guard_topology_base_no_path_vertical_attempts{1};
        // If the corridor/MINCO stack repeatedly cannot optimize the final
        // short connection from an already-certified stop, try one direct
        // rest-to-rest polynomial. It is still committed only through the
        // normal geometric guard and sampled stop-viability checks.
        bool guard_direct_goal_fallback_en{false};
        double guard_direct_goal_fallback_max_distance_m{3.0};
        double guard_direct_goal_fallback_min_duration_s{1.0};
        // Before committing a candidate, require that a certified emergency
        // stop (built the same way the runtime guard brake is built) exists
        // from several sampled states along the candidate. If not, the
        // candidate is time-scaled (slowed down, same geometric path) and
        // re-checked instead of being committed at full speed. This targets
        // the failure mode where the vehicle reaches a state from which no
        // certified brake exists.
        bool guard_viability_en{false};
        double guard_viability_horizon_s{2.0};
        double guard_viability_sample_dt_s{0.3};
        double guard_viability_brake_max_acc_mps2{15.0};
        double guard_viability_brake_max_jerk_mps3{120.0};
        double guard_viability_brake_min_duration_s{0.4};
        double guard_viability_brake_max_duration_s{2.0};
        int guard_viability_brake_attempts{12};
        double guard_viability_speed_scale_step{1.25};
        double guard_viability_speed_scale_max{3.0};
        int guard_viability_max_retries{4};
        // Minimum operational SFC clearance can be stricter than the physical
        // robot radius without changing physical-contact accounting.
        double corridor_min_margin;
        // Preferred corridor clearance used when there is additional room.
        double corridor_pref_margin;
        double trajectory_guard_sample_dt_s{0.01};
        double trajectory_guard_shadow_min_interval_s{0.0};
        // Extra radial clearance checked around the already-inflated map.
        // Zero preserves the upstream map's collision boundary.
        double trajectory_guard_additional_clearance_m{0.0};
        double trajectory_guard_escape_max_duration_s{1.0};
        double trajectory_guard_escape_entry_grace_s{0.0};
        // Reject an emergency-brake candidate (only -- NOT normal EXP/backup
        // candidates, which must be free to extend into never-yet-observed
        // space or the vehicle could never explore) that falls in
        // never-observed raw-grid space, not just confirmed-occupied space.
        // A stale-but-fresh-enough map can still have real, unswept gaps
        // right along the flight path; isOccupiedInflate() alone treats
        // those identically to confirmed-free space. First tried applied to
        // every guard check (EXP/backup too): caused total liveness loss at
        // mission start, since the area right around the spawn point is
        // still almost entirely unobserved at t=0.
        bool trajectory_guard_unknown_as_occupied{false};
        int iris_iter_num;

        int mpc_horizon{};

        double yaw_dot_max;
        // Yaw mode: 1 heading to velocity, 2 heading to goal
        int yaw_mode = YAW_TO_VEL;

        rog_map::vec_E<rog_map::Vec3i> seed_line_neighbour;


        Config() = default;
        Config(const std::string & cfg_path) {
            yaml_loader::YamlLoader loader(cfg_path);
            exp_traj_cfg = traj_opt::Config(cfg_path, "exp_traj");
            back_traj_cfg = traj_opt::Config(cfg_path, "backup_traj");
            loader.LoadParam("super_planner/print_log", print_log, false);
            loader.LoadParam("super_planner/detailed_log_en", detailed_log_en, false);
            loader.LoadParam("super_planner/visualization_en", visualization_en, false);
            loader.LoadParam("super_planner/backup_traj_en", backup_traj_en, false);
            loader.LoadParam("super_planner/goal_vel_en", goal_vel_en, false);
            loader.LoadParam("super_planner/goal_yaw_en", goal_yaw_en, false);
            loader.LoadParam("super_planner/visual_process", visual_process, false);
            loader.LoadParam("super_planner/use_fov_cut", use_fov_cut, false);
            loader.LoadParam("super_planner/fov_horizontal_angle", fov_horizontal_angle, -1.0);
            loader.LoadParam("super_planner/fov_center_heading", fov_center_heading, false);
            loader.LoadParam("super_planner/frontend_in_known_free", frontend_in_known_free, false);
            loader.LoadParam("fsm/trajectory_guard/enable", trajectory_guard_en, false);
            loader.LoadParam("fsm/trajectory_guard/shadow", trajectory_guard_shadow_en, false);
            loader.LoadParam("fsm/trajectory_guard/validation_sample_dt_s",
                             trajectory_guard_sample_dt_s, 0.01);
            loader.LoadParam("fsm/trajectory_guard/shadow_min_interval_s",
                             trajectory_guard_shadow_min_interval_s, 0.0);
            loader.LoadParam("fsm/trajectory_guard/additional_clearance_m",
                             trajectory_guard_additional_clearance_m, 0.0);
            loader.LoadParam("fsm/trajectory_guard/escape_max_duration_s",
                             trajectory_guard_escape_max_duration_s, 1.0);
            loader.LoadParam("fsm/trajectory_guard/unknown_as_occupied",
                             trajectory_guard_unknown_as_occupied, false);
            loader.LoadParam("fsm/trajectory_guard/escape_entry_grace_s",
                             trajectory_guard_escape_entry_grace_s, 0.0);
            loader.LoadParam("super_planner/safe_corridor_line_max_length", safe_corridor_line_max_length, 3.0);
            loader.LoadParam("super_planner/sensing_horizon", sensing_horizon, 3.0);
            loader.LoadParam("super_planner/obs_skip_num", obs_skip_num, 1);
            loader.LoadParam("super_planner/replan_forward_dt", replan_forward_dt, 0.3);
            loader.LoadParam("super_planner/corridor_bound_dis", corridor_bound_dis, 3.0);
            loader.LoadParam("super_planner/corridor_line_max_length", corridor_line_max_length, 3.0);
            loader.LoadParam("super_planner/planning_horizon", planning_horizon, 10.0);
            loader.LoadParam("super_planner/receding_dis", receding_dis, 5.0);
            loader.LoadParam("super_planner/robot_r", robot_r, 0.3);
            loader.LoadParam("super_planner/corridor_use_inflated_obstacles",
                             corridor_use_inflated_obstacles, false);
            loader.LoadParam("super_planner/corridor_use_inflated_seed_lines",
                             corridor_use_inflated_seed_lines,
                             corridor_use_inflated_obstacles);
            loader.LoadParam("super_planner/corridor_guard_retry_inflated",
                             corridor_guard_retry_inflated, false);
            loader.LoadParam("super_planner/guard_corridor_retry_alternate_every",
                             guard_corridor_retry_alternate_every, 4);
            loader.LoadParam("super_planner/guard_topology_reroute/enable",
                             guard_topology_reroute_en, false);
            loader.LoadParam("super_planner/guard_topology_reroute/radius_m",
                             guard_topology_reroute_radius_m, 0.8);
            loader.LoadParam("super_planner/guard_topology_reroute/growth_m",
                             guard_topology_reroute_growth_m, 0.25);
            loader.LoadParam("super_planner/guard_topology_reroute/max_radius_m",
                             guard_topology_reroute_max_radius_m, 1.8);
            loader.LoadParam("super_planner/guard_topology_reroute/max_zones",
                             guard_topology_reroute_max_zones, 4);
            loader.LoadParam("super_planner/guard_topology_reroute/max_stop_speed_mps",
                             guard_topology_reroute_max_stop_speed_mps, 0.2);
            loader.LoadParam(
                    "super_planner/guard_topology_reroute/escalate_every_rejects",
                    guard_topology_reroute_escalate_every_rejects, 3);
            loader.LoadParam("super_planner/guard_topology_reroute/collision_merge_m",
                             guard_topology_reroute_collision_merge_m, 0.5);
            loader.LoadParam("super_planner/guard_topology_reroute/start_clearance_m",
                             guard_topology_reroute_start_clearance_m, 0.05);
            loader.LoadParam("super_planner/guard_topology_reroute/block_spacing_m",
                             guard_topology_reroute_block_spacing_m, 1.0);
            loader.LoadParam(
                    "super_planner/guard_topology_reroute/direction_merge_angle_deg",
                    guard_topology_reroute_direction_merge_angle_deg, 30.0);
            loader.LoadParam(
                    "super_planner/guard_topology_reroute/no_path_reset_attempts",
                    guard_topology_reroute_no_path_reset_attempts, 3);
            loader.LoadParam(
                    "super_planner/guard_topology_reroute/vertical_recovery_enable",
                    guard_topology_vertical_recovery_en, false);
            loader.LoadParam(
                    "super_planner/guard_topology_reroute/vertical_recovery_lift_m",
                    guard_topology_vertical_recovery_lift_m, 0.6);
            loader.LoadParam(
                    "super_planner/guard_topology_reroute/vertical_recovery_trigger_distance_m",
                    guard_topology_vertical_recovery_trigger_distance_m, 0.75);
            loader.LoadParam(
                    "super_planner/guard_topology_reroute/saturation_vertical_attempts",
                    guard_topology_saturation_vertical_attempts, 1);
            loader.LoadParam(
                    "super_planner/guard_topology_reroute/base_no_path_vertical_attempts",
                    guard_topology_base_no_path_vertical_attempts, 1);
            loader.LoadParam(
                    "super_planner/guard_direct_goal_fallback/enable",
                    guard_direct_goal_fallback_en, false);
            loader.LoadParam(
                    "super_planner/guard_direct_goal_fallback/max_distance_m",
                    guard_direct_goal_fallback_max_distance_m, 3.0);
            loader.LoadParam(
                    "super_planner/guard_direct_goal_fallback/min_duration_s",
                    guard_direct_goal_fallback_min_duration_s, 1.0);
            loader.LoadParam("super_planner/guard_viability/enable",
                             guard_viability_en, false);
            loader.LoadParam("super_planner/guard_viability/horizon_s",
                             guard_viability_horizon_s, 2.0);
            loader.LoadParam("super_planner/guard_viability/sample_dt_s",
                             guard_viability_sample_dt_s, 0.3);
            loader.LoadParam("super_planner/guard_viability/brake_max_acc_mps2",
                             guard_viability_brake_max_acc_mps2, 15.0);
            loader.LoadParam("super_planner/guard_viability/brake_max_jerk_mps3",
                             guard_viability_brake_max_jerk_mps3, 120.0);
            loader.LoadParam("super_planner/guard_viability/brake_min_duration_s",
                             guard_viability_brake_min_duration_s, 0.4);
            loader.LoadParam("super_planner/guard_viability/brake_max_duration_s",
                             guard_viability_brake_max_duration_s, 2.0);
            loader.LoadParam("super_planner/guard_viability/brake_attempts",
                             guard_viability_brake_attempts, 12);
            loader.LoadParam("super_planner/guard_viability/speed_scale_step",
                             guard_viability_speed_scale_step, 1.25);
            loader.LoadParam("super_planner/guard_viability/speed_scale_max",
                             guard_viability_speed_scale_max, 3.0);
            loader.LoadParam("super_planner/guard_viability/max_retries",
                             guard_viability_max_retries, 4);
            loader.LoadParam("super_planner/corridor_min_margin", corridor_min_margin, robot_r);
            if (!corridor_use_inflated_obstacles && corridor_min_margin < robot_r) {
                corridor_min_margin = robot_r;
            }
            loader.LoadParam("super_planner/corridor_pref_margin", corridor_pref_margin, -1.0);
            if (corridor_pref_margin < corridor_min_margin) {
                corridor_pref_margin = corridor_min_margin;
            }
            loader.LoadParam("super_planner/iris_iter_num", iris_iter_num, 1);
            loader.LoadParam("super_planner/yaw_mode", yaw_mode, 1);
            loader.LoadParam("super_planner/mpc_horizon", mpc_horizon, 1);
            loader.LoadParam("super_planner/yaw_dot_max", yaw_dot_max, 3.14);

            loader.LoadParam("rog_map/resolution", resolution, 0.01, true);

            guard_topology_reroute_radius_m = std::max(
                    resolution, guard_topology_reroute_radius_m);
            guard_topology_reroute_growth_m = std::max(
                    0.0, guard_topology_reroute_growth_m);
            guard_topology_reroute_max_radius_m = std::max(
                    guard_topology_reroute_radius_m,
                    guard_topology_reroute_max_radius_m);
            guard_topology_reroute_max_zones = std::max(
                    1, guard_topology_reroute_max_zones);
            guard_topology_reroute_max_stop_speed_mps = std::max(
                    0.0, guard_topology_reroute_max_stop_speed_mps);
            guard_topology_reroute_escalate_every_rejects = std::max(
                    1, guard_topology_reroute_escalate_every_rejects);
            guard_topology_reroute_collision_merge_m = std::max(
                    resolution, guard_topology_reroute_collision_merge_m);
            guard_topology_reroute_start_clearance_m = std::max(
                    resolution, guard_topology_reroute_start_clearance_m);
            guard_topology_reroute_block_spacing_m = std::max(
                    resolution, guard_topology_reroute_block_spacing_m);
            guard_topology_reroute_direction_merge_angle_deg = std::clamp(
                    guard_topology_reroute_direction_merge_angle_deg,
                    1.0, 89.0);
            guard_topology_reroute_no_path_reset_attempts = std::max(
                    1, guard_topology_reroute_no_path_reset_attempts);
            guard_topology_vertical_recovery_lift_m = std::max(
                    resolution, guard_topology_vertical_recovery_lift_m);
            guard_topology_vertical_recovery_trigger_distance_m = std::max(
                    resolution,
                    guard_topology_vertical_recovery_trigger_distance_m);
            guard_topology_saturation_vertical_attempts = std::max(
                    0, guard_topology_saturation_vertical_attempts);
            guard_topology_base_no_path_vertical_attempts = std::max(
                    0, guard_topology_base_no_path_vertical_attempts);
            guard_direct_goal_fallback_max_distance_m = std::max(
                    resolution, guard_direct_goal_fallback_max_distance_m);
            guard_direct_goal_fallback_min_duration_s = std::max(
                    0.1, guard_direct_goal_fallback_min_duration_s);

            guard_viability_horizon_s = std::max(0.0, guard_viability_horizon_s);
            guard_viability_sample_dt_s = std::max(0.01, guard_viability_sample_dt_s);
            guard_viability_brake_max_acc_mps2 = std::max(
                    1.0e-3, guard_viability_brake_max_acc_mps2);
            guard_viability_brake_max_jerk_mps3 = std::max(
                    1.0e-3, guard_viability_brake_max_jerk_mps3);
            guard_viability_brake_min_duration_s = std::max(
                    0.05, guard_viability_brake_min_duration_s);
            guard_viability_brake_max_duration_s = std::max(
                    guard_viability_brake_min_duration_s,
                    guard_viability_brake_max_duration_s);
            guard_viability_brake_attempts = std::max(
                    1, guard_viability_brake_attempts);
            guard_viability_speed_scale_step = std::max(
                    1.001, guard_viability_speed_scale_step);
            guard_viability_speed_scale_max = std::max(
                    1.0, guard_viability_speed_scale_max);
            guard_viability_max_retries = std::max(
                    0, guard_viability_max_retries);

            sample_traj_dt = resolution / exp_traj_cfg.max_vel;
            if (!std::isfinite(trajectory_guard_sample_dt_s) ||
                trajectory_guard_sample_dt_s <= 0.0) {
                trajectory_guard_sample_dt_s = sample_traj_dt;
            }
            if (!std::isfinite(trajectory_guard_shadow_min_interval_s) ||
                trajectory_guard_shadow_min_interval_s < 0.0) {
                trajectory_guard_shadow_min_interval_s = 0.0;
            }
            if (!std::isfinite(trajectory_guard_additional_clearance_m) ||
                trajectory_guard_additional_clearance_m < 0.0) {
                trajectory_guard_additional_clearance_m = 0.0;
            }
            if (!std::isfinite(trajectory_guard_escape_max_duration_s) ||
                trajectory_guard_escape_max_duration_s <= 0.0) {
                trajectory_guard_escape_max_duration_s = 1.0;
            }

            int step = ceil(robot_r / resolution);
            for (int x = -step; x <= step; x++) {
                for (int y = -step; y <= step; y++) {
                    for (int z = -step; z <= step; z++) {
                        if (x * x + y * y + z * z <= step * step) {
                            seed_line_neighbour.push_back({x, y, z});
                        }
                    }
                }
            }
            std::sort(seed_line_neighbour.begin(), seed_line_neighbour.end(),
                      [](const auto& a, const auto& b) {
                          return a[0] * a[0] + a[1] * a[1] + a[2] * a[2] < b[0] * b[0] + b[1] * b[1] + b[2] * b[2];
                      });
        }


    };
}

#endif
