#!/usr/bin/env python3
"""Exercise exact production zone rollback and exhaustion code with A* fixtures.

The map and A* outcomes are fixtures. This verifies transactional recovery
state, not physical geometry or closed-loop flight safety.
"""
from pathlib import Path
import re
import subprocess
import tempfile


def extract(text, signature):
    begin = text.index(signature)
    masked = re.sub(r'''//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*' ''',
                    lambda match: " " * len(match.group()), text, flags=re.S | re.X)
    brace = masked.index("{", begin)
    depth, end = 1, brace + 1
    while depth:
        depth += (masked[end] == "{") - (masked[end] == "}")
        end += 1
    return text[begin:end]


def main():
    package = Path(__file__).resolve().parents[1]
    source = (package / "src/super_core/super_planner.cpp").read_text()
    exhausted = extract(source, "void SuperPlanner::markTopologyRecoveryExhausted(")
    begin = source.index("        const bool had_topology_zones =")
    end = source.index("        // Explicit one-shot regression hook", begin)
    rollback = source[begin:end]
    astar_recovery = source[source.index(
        "} else if (guarded_astar_failure_with_zones"):]
    escape_condition = re.search(
        r"const bool arm_local_escape =.*?;", astar_recovery, re.S).group()
    plan = extract(source, "SuperPlanner::PlanFromRest(")
    assert plan.index("if (guard_topology_recovery_exhausted_)") < plan.index(
        "tryCommitCertifiedLocalEscape(recovery_start)")
    assert "guard_topology_recovery_exhausted_ = false;" in extract(
        source, "void SuperPlanner::resetTopologyRecoveryState(")
    assert "guard_topology_recovery_exhausted_ = false;" not in extract(
        source, "void SuperPlanner::clearTopologyRecoverySearchState(")
    assert "guard_topology_recovery_exhausted_ = false;" in extract(
        source, "bool SuperPlanner::commitTrajectoryCandidate(")
    # The fresh-scan reconstruction must never become a production switch or
    # an A*/certificate-result override. It is only stationary, once, at the
    # recorded pose. Unit fixtures below still test the real recovery code.
    hook_begin = source.index("        const char *forest_state_test =")
    hook_end = source.index("        if (cfg_.guard_topology_reroute_en &&", hook_begin)
    hook = source[hook_begin:hook_end]
    for token in ('SUPER_TEST_FOREST_TOPOLOGY_STATE', 'planning_from_rest',
                  'robot_state_.v.norm() <= 0.05', 'forest_logged_stop).norm() <= 0.15',
                  '!guard_test_forest_topology_state_injected_',
                  'historical_map_replay=false forced_search_result=false'):
        assert token in hook, token
    assert 'ret_code =' not in hook and 'commitTrajectoryCandidate' not in hook
    assert 'guard_test_forest_topology_state_injected_' not in extract(
        source, 'void SuperPlanner::resetTopologyRecoveryState(')

    fixture = r'''
#include <atomic>
#include <cassert>
#include <iostream>
#include <memory>
#include <utility>
#include <vector>
struct Vec3f { double v[3]{1,2,3};
 double x() const {return v[0];} double y() const {return v[1];}
 double z() const {return v[2];} };
using vec_Vec3f = std::vector<Vec3f>;
enum RET_CODE { NO_PATH, TIME_OUT, INIT_ERROR, REACH_GOAL, REACH_HORIZON };
struct Astar { RET_CODE result=REACH_GOAL; int calls=0; size_t centers=99;
 RET_CODE pointToPointPathSearch(const Vec3f&,const Vec3f&,int,double,
   vec_Vec3f& path,const vec_Vec3f& c,const std::vector<double>& r) {
   ++calls; centers=c.size(); assert(c.size()==r.size());
   path.push_back(Vec3f{}); return result; } };
struct Logger {int warnings=0;
 template<class... Args> void warn(const char*,Args...) {++warnings;} };
struct SuperPlanner {
 struct Config { bool guard_topology_local_escape_en=true;
   int guard_topology_reroute_no_path_reset_attempts=3;
   int guard_topology_local_escape_attempts=4;
   int guard_topology_saturation_vertical_attempts=1; } cfg_;
 vec_Vec3f guard_topology_avoidance_centers_;
 std::vector<double> guard_topology_avoidance_radii_;
 int guard_topology_no_path_failures_=0;
 int guard_topology_local_escape_recoveries_=4;
 int guard_topology_saturation_recoveries_=1;
 bool guard_topology_recovery_exhausted_=false;
 std::atomic_bool guard_corridor_retry_pending_{true};
 std::atomic_bool guard_local_escape_pending_{true};
 std::atomic_bool guard_vertical_recovery_pending_{true};
 std::shared_ptr<Astar> astar_ptr_=std::make_shared<Astar>();
 std::shared_ptr<Logger> ros_ptr_=std::make_shared<Logger>();
 void markTopologyRecoveryExhausted(const char*, const Vec3f&);
 bool canEscape(bool local_escape_direction_valid) const {
ESCAPE_CONDITION
   return arm_local_escape;
 }
 std::pair<bool,RET_CODE> probe(bool planning_from_rest, RET_CODE ret_code) {
   Vec3f temp_start_point,goal; int flag=1; double temp_plannning_horizon=10;
   vec_Vec3f path;
ROLLBACK
   assert(path.empty()); // trial guide must not escape to the real output.
   return {had_topology_zones,ret_code};
 }
};
EXHAUSTED
int main() {
 for (auto success : {REACH_GOAL,REACH_HORIZON}) {
   SuperPlanner p; p.guard_topology_avoidance_centers_.resize(2);
   p.guard_topology_avoidance_radii_.resize(2,0.8);
   p.astar_ptr_->result=success;
   const auto result=p.probe(true,NO_PATH);
   assert(result.first && result.second==NO_PATH);
   assert(p.astar_ptr_->calls==1 && p.astar_ptr_->centers==1);
   assert(p.guard_topology_avoidance_centers_.size()==1);
   assert(p.guard_topology_avoidance_radii_.size()==1);
   assert(p.guard_topology_no_path_failures_==2);
 }
 for (auto failed : {NO_PATH,TIME_OUT,INIT_ERROR}) {
   SuperPlanner p; p.guard_topology_avoidance_centers_.resize(2);
   p.guard_topology_avoidance_radii_.resize(2,0.8);
   p.astar_ptr_->result=failed; p.probe(true,NO_PATH);
   assert(p.astar_ptr_->calls==1);
   assert(p.guard_topology_avoidance_centers_.size()==2);
   assert(p.guard_topology_no_path_failures_==0);
 }
 for (int kind=0;kind<4;++kind) {
   SuperPlanner p; p.guard_topology_avoidance_centers_.resize(kind==0?0:2);
   p.guard_topology_avoidance_radii_.resize(kind==0?0:2,0.8);
   if (kind==1) p.guard_topology_no_path_failures_=1;
   p.probe(kind!=2,kind==3?TIME_OUT:NO_PATH);
   assert(p.astar_ptr_->calls==0);
 }
 SuperPlanner p; p.markTopologyRecoveryExhausted("fixture",Vec3f{});
 assert(p.guard_topology_recovery_exhausted_);
 assert(!p.guard_corridor_retry_pending_ && !p.guard_local_escape_pending_);
 assert(!p.guard_vertical_recovery_pending_ && p.ros_ptr_->warnings==1);
 p.markTopologyRecoveryExhausted("same_fixture",Vec3f{});
 assert(p.ros_ptr_->warnings==1);
 p.guard_topology_local_escape_recoveries_=0;
 assert(p.canEscape(true)); // non-adjacent rejection must use remaining budget.
 assert(!p.canEscape(false));
 p.cfg_.guard_topology_local_escape_en=false; assert(!p.canEscape(true));
 p.cfg_.guard_topology_local_escape_en=true;
 p.guard_topology_local_escape_recoveries_=4; assert(!p.canEscape(true));
 std::cout << "PASS: exact production rollback, fail-closed comparison, "
              "exhaustion idempotence, and caller reset contracts\n";
}
'''
    fixture = fixture.replace("ROLLBACK", rollback).replace("EXHAUSTED", exhausted)
    fixture = fixture.replace("ESCAPE_CONDITION", escape_condition)
    with tempfile.TemporaryDirectory(prefix="super_topology_liveness_test_") as temporary:
        executable = Path(temporary) / "test"
        subprocess.run(["g++", "-std=c++17", "-O1", "-Wall", "-Wextra",
                        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                        "-x", "c++", "-", "-o", str(executable)],
                       input=fixture, text=True, check=True)
        subprocess.run([str(executable)], check=True, timeout=30)


if __name__ == "__main__":
    main()
