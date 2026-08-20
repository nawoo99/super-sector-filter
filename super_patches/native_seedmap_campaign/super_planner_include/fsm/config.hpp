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


#ifndef SUPER_FSM_CONFIG_HPP
#define SUPER_FSM_CONFIG_HPP


#include <super_core/config.hpp>
#include <algorithm>
#include <cmath>
#include <vector>
#include <cstring>
#include <utils/header/yaml_loader.hpp>

namespace fsm {
    using namespace traj_opt;
    using namespace super_planner;
    static constexpr int MPC_PVAJ_MODE = 1;
    static constexpr int MPC_POLYTRAJ_MODE = 2;

    class Config {
    public:
        bool timer_en{true};

        // Fsm Params
        bool click_goal_en{},visualization_en{};
        double replan_rate{}, resolution{};
        double click_height{};

        bool click_yaw_en{};
        string cmd_topic, mpc_cmd_topic, click_goal_topic;
        double yaw_dot_max{};

        // Startup map-readiness gate. Disabled by default for backwards
        // compatibility with existing configurations.
        bool map_readiness_en{false};
        int map_readiness_min_accepted_scans{5};
        int map_readiness_min_committed_scans{5};
        int map_readiness_max_commit_lag_scans{5};
        double map_readiness_min_scan_span_s{1.0};
        double map_readiness_max_cloud_age_s{0.75};
        double map_readiness_max_map_age_s{0.75};

        // Runtime certification of the committed composite trajectory and a
        // sticky, continuous emergency brake when certification is lost.
        bool trajectory_guard_en{false};
        // Planner-side candidate validation/logging only. This never suppresses
        // publication or activates the emergency brake.
        bool trajectory_guard_shadow_en{false};
        double trajectory_guard_max_map_age_s{0.75};
        // Start a certified stop before the map reaches max_map_age_s.  A
        // negative/zero value inherits max_map_age_s for legacy profiles.
        double trajectory_guard_brake_trigger_map_age_s{0.75};
        // Optional low-latency supplement to the committed occupancy map.
        // It checks the registered sensor cloud without waiting for a full
        // ROG-map update and is disabled for legacy profiles.
        bool trajectory_guard_raw_cloud_en{false};
        double trajectory_guard_raw_cloud_max_age_s{0.3};
        double trajectory_guard_raw_cloud_clearance_m{0.3};
        double trajectory_guard_validation_sample_dt_s{0.01};
        double trajectory_guard_shadow_min_interval_s{0.0};
        double trajectory_guard_additional_clearance_m{0.0};
        double brake_min_duration_s{0.4};
        double brake_max_duration_s{2.0};
        double brake_max_acc_mps2{15.0};
        double brake_max_jerk_mps3{120.0};
        // A cached PositionCommand is useful for command-continuous braking,
        // but only while it still represents the state the vehicle is
        // tracking.  Once guard suppression stops command publication, an
        // unbounded cache becomes a permanently stale brake initial state.
        double brake_command_max_age_s{0.1};
        double brake_command_max_position_error_m{0.5};
        double brake_command_max_velocity_error_mps{2.0};
        // See super_planner::Config::trajectory_guard_unknown_as_occupied
        // for the rationale; only the emergency-brake candidate check reads
        // this flag.
        bool trajectory_guard_unknown_as_occupied{false};
        // 2026-08-19: paper-faithful (theorem 1) accumulated-raw-cloud CIRI
        // check, shadow-only -- computed and logged alongside the live
        // brake decision in activateEmergencyBrake, never used to accept or
        // reject a candidate. See docs/
        // viability_guard_ciri_avoidance_2026-08-15.md 8.10 before ever
        // promoting this to enforce; three earlier live-wired attempts at
        // this same mechanism each regressed differently (a real collision;
        // a near-total liveness collapse; an unexplained subscription/
        // freeze bug), so this stays shadow-only until it has its own
        // multi-run track record.
        bool trajectory_guard_raw_cloud_ciri_shadow_en{false};
        double trajectory_guard_raw_cloud_accum_window_s{1.5};
        // Below this many points in the pruned accumulation window, the
        // shadow check reports INSUFFICIENT_DATA instead of treating a
        // sparse/empty local box as confirmed-open space -- theorem 1's
        // known-free guarantee is conditioned on the input depth image
        // being "sufficiently dense" (see the paper's Materials and
        // Methods), which this cannot verify per-box the way it can verify
        // accumulator-wide.
        int trajectory_guard_raw_cloud_ciri_min_points{200};
        // 2026-08-19: voxel-downsample the accumulated cloud to at most one
        // point per cell of this size before it reaches CIRI. Measured
        // necessary -- an undownsampled 1.5s window held 30k-80k points and
        // caused 15-40ms decomposition spikes on a shared executor thread.
        double trajectory_guard_raw_cloud_ciri_voxel_m{0.1};

        Config() = default;

        Config(const std::string & cfg_path) {
            yaml_loader::YamlLoader loader(cfg_path);
            vector<double> tem_gain;
            loader.LoadParam("fsm/timer_en", timer_en, false);
            loader.LoadParam("fsm/click_goal_en", click_goal_en, false);
            loader.LoadParam("fsm/click_yaw_en", click_yaw_en, false);
            loader.LoadParam("fsm/replan_rate", replan_rate, 10.0);
            loader.LoadParam("fsm/click_height", click_height, 1.5);
            loader.LoadParam("fsm/cmd_topic", cmd_topic, string("/planning/pos_cmd"));
            loader.LoadParam("fsm/mpc_cmd_topic", mpc_cmd_topic, string("/planning_cmd/mpc"));
            loader.LoadParam("fsm/click_goal_topic", click_goal_topic, string("/planning/click_goal_topic"));
            loader.LoadParam("fsm/map_readiness/enable", map_readiness_en, false);
            loader.LoadParam("fsm/map_readiness/min_accepted_scans", map_readiness_min_accepted_scans, 5);
            loader.LoadParam("fsm/map_readiness/min_committed_scans", map_readiness_min_committed_scans, 5);
            loader.LoadParam("fsm/map_readiness/max_commit_lag_scans", map_readiness_max_commit_lag_scans, 5);
            loader.LoadParam("fsm/map_readiness/min_scan_span_s", map_readiness_min_scan_span_s, 1.0);
            loader.LoadParam("fsm/map_readiness/max_cloud_age_s", map_readiness_max_cloud_age_s, 0.75);
            loader.LoadParam("fsm/map_readiness/max_map_age_s", map_readiness_max_map_age_s, 0.75);
            loader.LoadParam("fsm/trajectory_guard/enable", trajectory_guard_en, false);
            loader.LoadParam("fsm/trajectory_guard/shadow",
                             trajectory_guard_shadow_en, false);
            loader.LoadParam("fsm/trajectory_guard/max_map_age_s",
                             trajectory_guard_max_map_age_s, 0.75);
            loader.LoadParam("fsm/trajectory_guard/brake_trigger_map_age_s",
                             trajectory_guard_brake_trigger_map_age_s, -1.0);
            if (!std::isfinite(trajectory_guard_brake_trigger_map_age_s) ||
                trajectory_guard_brake_trigger_map_age_s <= 0.0) {
                trajectory_guard_brake_trigger_map_age_s =
                        trajectory_guard_max_map_age_s;
            }
            trajectory_guard_brake_trigger_map_age_s = std::min(
                    trajectory_guard_brake_trigger_map_age_s,
                    trajectory_guard_max_map_age_s);
            loader.LoadParam("fsm/trajectory_guard/raw_cloud/enable",
                             trajectory_guard_raw_cloud_en, false);
            loader.LoadParam("fsm/trajectory_guard/raw_cloud/max_age_s",
                             trajectory_guard_raw_cloud_max_age_s, 0.3);
            loader.LoadParam("fsm/trajectory_guard/raw_cloud/clearance_m",
                             trajectory_guard_raw_cloud_clearance_m, 0.3);
            loader.LoadParam("fsm/trajectory_guard/validation_sample_dt_s",
                             trajectory_guard_validation_sample_dt_s, 0.01);
            loader.LoadParam("fsm/trajectory_guard/shadow_min_interval_s",
                             trajectory_guard_shadow_min_interval_s, 0.0);
            loader.LoadParam("fsm/trajectory_guard/additional_clearance_m",
                             trajectory_guard_additional_clearance_m, 0.0);
            loader.LoadParam("fsm/trajectory_guard/brake_min_duration_s",
                             brake_min_duration_s, 0.4);
            loader.LoadParam("fsm/trajectory_guard/brake_max_duration_s",
                             brake_max_duration_s, 2.0);
            loader.LoadParam("fsm/trajectory_guard/brake_max_acc_mps2",
                             brake_max_acc_mps2, 15.0);
            loader.LoadParam("fsm/trajectory_guard/brake_max_jerk_mps3",
                             brake_max_jerk_mps3, 120.0);
            loader.LoadParam("fsm/trajectory_guard/brake_command_max_age_s",
                             brake_command_max_age_s, 0.1);
            loader.LoadParam(
                    "fsm/trajectory_guard/brake_command_max_position_error_m",
                    brake_command_max_position_error_m, 0.5);
            loader.LoadParam(
                    "fsm/trajectory_guard/brake_command_max_velocity_error_mps",
                    brake_command_max_velocity_error_mps, 2.0);
            brake_command_max_age_s = std::max(0.0,
                                                brake_command_max_age_s);
            brake_command_max_position_error_m = std::max(
                    0.0, brake_command_max_position_error_m);
            brake_command_max_velocity_error_mps = std::max(
                    0.0, brake_command_max_velocity_error_mps);
            loader.LoadParam("fsm/trajectory_guard/unknown_as_occupied",
                             trajectory_guard_unknown_as_occupied, false);
            loader.LoadParam("fsm/trajectory_guard/raw_cloud/ciri_shadow_en",
                             trajectory_guard_raw_cloud_ciri_shadow_en, false);
            loader.LoadParam("fsm/trajectory_guard/raw_cloud/accum_window_s",
                             trajectory_guard_raw_cloud_accum_window_s, 1.5);
            loader.LoadParam("fsm/trajectory_guard/raw_cloud/ciri_min_points",
                             trajectory_guard_raw_cloud_ciri_min_points, 200);
            loader.LoadParam("fsm/trajectory_guard/raw_cloud/ciri_voxel_m",
                             trajectory_guard_raw_cloud_ciri_voxel_m, 0.1);


            loader.LoadParam("super_planner/yaw_dot_max", yaw_dot_max, 1.0, true);
            loader.LoadParam("super_planner/visualization_en", visualization_en, false, true);
            loader.LoadParam("rog_map/resolution", resolution, 0.1, true);

        }
    };
}

#endif //SUPER_FSM_CONFIG_H
