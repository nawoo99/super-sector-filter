#include <data_structure/base/polytope.h>
#include <fmt/color.h>
namespace super_planner {
using super_utils::Vec3f;
using super_utils::StatePVAJ;
using geometry_utils::Polytope;
}
#include <data_structure/cmd_traj.h>

#include <cmath>
#include <cstdlib>
#include <iostream>

#define REQUIRE(condition) do { if (!(condition)) { \
    std::cerr << "requirement failed at line " << __LINE__ << ": " \
              << #condition << "\n"; std::abort(); } } while (false)

static super_planner::CmdTraj::Candidate makeCandidate() {
    super_planner::CmdTraj::Candidate candidate;
    Eigen::MatrixXd position = Eigen::MatrixXd::Zero(3, 6);
    position.col(4) << 0.2, -0.1, 0.05;
    position.col(5) << 1.0, 2.0, 1.5;
    candidate.pos_traj.emplace_back(2.0, position);
    candidate.pos_traj.start_WT = 10.0;
    Eigen::MatrixXd yaw = Eigen::MatrixXd::Zero(1, 6);
    yaw(0, 5) = 0.3;
    candidate.yaw_traj.emplace_back(2.0, yaw);
    candidate.yaw_traj.start_WT = 10.0;
    candidate.initial_egress.origin = {1.0, 2.0, 1.5};
    candidate.initial_egress.start_wt = 10.0;
    candidate.initial_egress.from_tt = 0.0;
    candidate.initial_egress.until_tt = 0.25;
    candidate.initial_egress.radius = 0.2;
    candidate.initial_egress.retain({1.1, 2.0, 1.5});
    return candidate;
}

int main() {
    super_planner::CmdTraj commands;
    const auto generation = commands.commitCandidate(makeCandidate());
    const auto old = commands.sharedSnapshot();
    super_planner::StatePVAJ zero_before;
    REQUIRE(old.pos_traj->getState(0.0, zero_before));

    REQUIRE(!commands.rebaseStoppedCandidate(generation + 1, 20.0));
    REQUIRE(!commands.rebaseStoppedCandidate(generation, NAN));
    REQUIRE(commands.rebaseStoppedCandidate(generation, 20.0));
    const auto current = commands.sharedSnapshot();
    REQUIRE(current.generation == generation);
    REQUIRE(current.start_wt == 20.0);
    REQUIRE(current.pos_traj->start_WT == 20.0);
    REQUIRE(current.yaw_traj->start_WT == 20.0);
    REQUIRE(current.initial_egress.usable(generation, 20.0, 0.0));
    REQUIRE(old.start_wt == 10.0);  // immutable pre-release evidence
    REQUIRE(old.initial_egress.usable(generation, 10.0, 0.0));
    super_planner::StatePVAJ zero_after;
    REQUIRE(current.pos_traj->getState(0.0, zero_after));
    REQUIRE((zero_before - zero_after).norm() < 1.0e-12);
    std::cout << "stopped_departure_clock_test: PASS\n";
}
