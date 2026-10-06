#!/usr/bin/env python3
"""Compile real interpolation/piece/trajectory code and check recovery contracts."""
from pathlib import Path
import subprocess
import tempfile


def main():
    package = Path(__file__).resolve().parents[1]
    source = (package/'src/super_core/certified_polyline_recovery.cpp').read_text()
    main_source = (package/'src/super_core/super_planner.cpp').read_text()
    assert 'SUPER_CERTIFIED_POLYLINE_RECOVERY' in source
    assert 'guard_topology_polyline_attempts_ >= 1' in source
    assert 'guard_topology_recovery_exhausted_' in source
    assert 'speed > cfg_.guard_topology_reroute_max_stop_speed_mps' in source
    assert 'vec_Vec3f{}, std::vector<double>{}' in source
    assert 'map_ptr_->isLineFree(path[index], path[j], true,' in source
    assert 'map_ptr_->getMapHealthSnapshot().map_version != version' in source
    assert 'commitTrajectoryCandidate(std::move(candidate), "PlanFromRest/certified_polyline_recovery")' in source
    assert 'cmd_traj_info_.commitCandidate' not in source
    assert 'guard_rest_to_rest_hold_until_wt_ = now + cmd_traj_info_.getTotalDuration();' in source
    assert main_source.count('guard_topology_polyline_attempts_ = 0;') == 2
    assert 'phase_name == "PlanFromRest/certified_polyline_recovery"' in main_source
    # The actual template returns the coefficients consumed by Piece, not a
    # hand-written Python approximation. Verify straight-line monotonicity,
    # terminal stops, C2 junction continuity, and analytic dynamics bounds.
    fixture = r'''
#include <utils/optimization/polynomial_interpolation.h>
#include <cassert>
#include <cmath>
#include <iostream>
using namespace geometry_utils;
using namespace super_utils;
int main() {
    Trajectory joined;
    Vec3f start(8.6753022,18.9734347,2.685578);
    for (const Vec3f delta : {Vec3f(.1,.1,0),Vec3f(-1.7,.5,-.6),Vec3f(2.,0.,-.5)}) {
        const double length=delta.norm();
        const double T=std::max({1.0,1.875*length/5.6,
            std::sqrt(5.774*length/16.0),std::cbrt(60.*length/96.)});
        Eigen::Matrix<double,3,3> initial=Eigen::Matrix<double,3,3>::Zero();
        Eigen::Matrix<double,3,3> final=Eigen::Matrix<double,3,3>::Zero();
        initial.col(0)=start; final.col(0)=start+delta;
        Eigen::Matrix<double,3,Eigen::Dynamic> knots(3,0);
        VecDf times(1); times<<T;
        const auto piece=poly_interpo::minimumJerkInterpolation<3>(initial,final,knots,times);
        assert((piece.getPos(0)-start).norm()<1e-9);
        assert((piece.getPos(T)-start-delta).norm()<1e-8);
        assert(piece.getVel(0).norm()<1e-9 && piece.getVel(T).norm()<1e-8);
        assert(piece.getAcc(0).norm()<1e-9 && piece.getAcc(T).norm()<1e-8);
        double prior=-1.;
        for(int i=0;i<=1000;++i) {
            const double t=T*i/1000.;
            const Vec3f p=piece.getPos(t)-start;
            const double u=p.dot(delta)/delta.squaredNorm();
            assert(u>=prior-1e-10 && u>=-1e-9 && u<=1.+1e-9);
            assert((p-u*delta).norm()<1e-8); prior=u;
            assert(piece.getVel(t).norm()<=5.6+1e-8);
            assert(piece.getAcc(t).norm()<=16.+1e-8);
            assert(piece.getJer(t).norm()<=96.+1e-8);
        }
        if(!joined.empty()) {
            const double end=joined.getTotalDuration();
            assert((joined.getPos(end)-piece.getPos(0)).norm()<1e-8);
            assert((joined.getVel(end)-piece.getVel(0)).norm()<1e-8);
            assert((joined.getAcc(end)-piece.getAcc(0)).norm()<1e-8);
        }
        joined.append(piece); start+=delta;
    }
    assert(joined.getPieceNum()==3);
    std::cout<<"PASS: real quintic interpolation, monotone line containment, C2 stops and dynamics\n";
}
'''
    with tempfile.TemporaryDirectory(prefix='super-polyline-test-') as temporary:
        root=Path(temporary)
        (root/'fixture.cpp').write_text(fixture)
        subprocess.run(['g++','-std=c++17','-O1','-DUSE_ROS2','-I'+str(package/'include'),
                        '-I'+str(package.parent/'rog_map/include'),
                        *['-I/opt/ros/humble/include/'+name for name in
                          ('std_msgs','rosidl_runtime_cpp','rosidl_runtime_c','builtin_interfaces',
                           'rosidl_typesupport_interface')],
                        '-I/usr/include/eigen3',str(root/'fixture.cpp'),
                        str(package/'src/utils/piece.cpp'),str(package/'src/utils/trajectory.cpp'),
                        str(package/'src/utils/root_finder.cpp'),
                        str(package/'src/utils/polynomial_interpolation.cpp'),
                        str(package/'src/utils/banded_system.cpp'),
                        '-o',str(root/'fixture')],check=True)
        subprocess.run([str(root/'fixture')],check=True)
    print('PASS: bounded episode, physical-stop, fresh inflated search and unchanged commit contracts')


if __name__ == '__main__':
    main()
