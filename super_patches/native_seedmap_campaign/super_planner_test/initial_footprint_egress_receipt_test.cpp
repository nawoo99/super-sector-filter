#include <fsm/initial_footprint_egress_receipt.hpp>
#include <cassert>
#include <iostream>
#include <limits>

using super_planner::initial_egress::Receipt;

int main() {
    Receipt r;
    assert(!r.valid() && !r.usable(1, 100.0, .05));
    r.generation = 42;
    r.origin = {1.0, 2.0, 1.5};
    r.start_wt = 100.0;
    r.from_tt = .05;
    r.until_tt = .28;
    r.radius = .2;
    r.retain({1.15, 2.0, 1.5});
    r.retain({1.15, 2.0, 1.5});
    assert(r.occupied_centres.size() == 1 && r.valid());
    assert(r.usable(42, 100.0, .05) && r.usable(42, 100.0, .28));
    assert(!r.usable(43, 100.0, .1));
    assert(!r.usable(42, 100.01, .1));
    assert(!r.usable(42, 100.0, .049));
    assert(!r.usable(42, 100.0, .281));
    assert(!r.usable(42, 100.0, std::numeric_limits<double>::quiet_NaN()));
    assert(r.contains({1.15, 2.0, 1.5}));
    // Even a newly observed voxel inside the old footprint is NOT authorized.
    assert(!r.contains({1.10, 2.0, 1.5}));
    const auto bound = r;
    for (int tick = 0; tick <= 1000; ++tick) {
        const double tt = tick * .001;
        assert(r.usable(42, 100.0, tt) == (tt >= .05 && tt <= .28));
        assert(r.until_tt == bound.until_tt); // refresh cannot slide the window
    }
    r.until_tt = r.from_tt;
    assert(!r.valid());
    r = bound;
    r.retain({2.0, 2.0, 1.5});
    assert(!r.valid()); // no point outside the original body may be masked
    r = bound;
    r.origin[0] = std::numeric_limits<double>::infinity();
    assert(!r.valid());
    r = bound;
    r.occupied_centres.clear();
    assert(!r.valid());
    std::cout << "initial footprint egress receipt: PASS\n";
}
