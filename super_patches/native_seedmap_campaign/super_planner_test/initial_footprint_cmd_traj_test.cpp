#include <data_structure/base/polytope.h>
#include <fmt/color.h>
// Match the planner's existing include environment without constructing ROS.
namespace super_planner {
using super_utils::Vec3f;
using super_utils::StatePVAJ;
using geometry_utils::Polytope;
}
#include <data_structure/cmd_traj.h>
#include <cassert>
#include <iostream>

super_planner::CmdTraj::Candidate candidate() {
    super_planner::CmdTraj::Candidate c;
    Eigen::MatrixXd coefficients = Eigen::MatrixXd::Zero(3, 6);
    coefficients.col(5) << 1., 2., 1.5;
    c.pos_traj.emplace_back(1.0, coefficients);
    c.pos_traj.start_WT = 100.;
    return c;
}

int main() {
    super_planner::CmdTraj commands;
    auto c = candidate();
    auto& e = c.initial_egress;
    e.origin = {1., 2., 1.5};
    e.start_wt = 100.;
    e.from_tt = .05;
    e.until_tt = .28;
    e.radius = .2;
    e.retain({1.15, 2., 1.5});
    e.generation = 999; // commit owns the true generation, not caller metadata
    const auto first = commands.commitCandidate(std::move(c));
    auto snapshot = commands.snapshot();
    const auto shared = commands.sharedSnapshot();
    assert(snapshot.initial_egress.usable(first, 100., .1));
    assert(shared.initial_egress.usable(first, 100., .1));
    snapshot.initial_egress.occupied_centres.clear();
    assert(commands.snapshot().initial_egress.valid());
    assert(shared.initial_egress.valid());
    commands.commitCandidate(candidate());
    assert(!commands.snapshot().initial_egress.valid());
    assert(!shared.initial_egress.usable(commands.generation(), 100., .1));
    assert(shared.initial_egress.usable(first, 100., .1)); // immutable old snapshot
    commands.setEmpty();
    assert(commands.snapshot().empty && !commands.snapshot().initial_egress.valid());
    std::cout << "CmdTraj generation-bound footprint metadata: PASS\n";
}
