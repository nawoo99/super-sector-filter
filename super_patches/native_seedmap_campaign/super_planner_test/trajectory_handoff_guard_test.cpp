#include <fsm/trajectory_handoff_guard.hpp>

#include <array>
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>

namespace guard = super_planner::trajectory_handoff;

struct State {
    std::array<std::array<double, 3>, 3> values{};
    double operator()(int axis, int order) const { return values[axis][order]; }
    double& operator()(int axis, int order) { return values[axis][order]; }
};

int main() {
    State old{}, next{};
    assert(guard::comparePva(old, next).continuous);
    next(0, 0) = guard::kPositionToleranceM;
    next(1, 1) = guard::kVelocityToleranceMps;
    next(2, 2) = guard::kAccelerationToleranceMps2;
    assert(guard::comparePva(old, next).continuous);
    next(0, 0) *= 1.01;
    assert(!guard::comparePva(old, next).continuous);
    next = old;
    next(0, 1) = 0.011;
    assert(!guard::comparePva(old, next).continuous);
    next = old;
    next(0, 2) = 0.101;
    assert(!guard::comparePva(old, next).continuous);
    next(0, 2) = std::numeric_limits<double>::quiet_NaN();
    assert(!guard::comparePva(old, next).continuous);
    next(0, 2) = std::numeric_limits<double>::infinity();
    assert(!guard::comparePva(old, next).continuous);

    // The r08 discontinuity is much larger than one command tick's travel.
    old = State{};
    next = State{};
    old(0, 0) = -29.072573655882827;
    old(1, 0) = -5.316053867764609;
    old(2, 0) = 0.5641840882253297;
    next(0, 0) = -28.17867162909539;
    next(1, 0) = -5.158378508577309;
    next(2, 0) = 0.6582948792096839;
    const auto jump = guard::comparePva(old, next);
    assert(!jump.continuous && jump.position_error_m > 0.9);

    const auto linear = [](double epoch, double scale) {
        return [=](double now, State& state) {
            state(0, 0) = (now - epoch) / scale;
            state(0, 1) = 1.0 / scale;
            return true;
        };
    };
    // A previously slowed command cannot switch back to its unscaled EXP at
    // the same old start_WT. Even if the handoff occurs at its start position,
    // the velocity mismatch must reject it.
    assert(!guard::compareAt<State>(1000.599, linear(1000.0, 1.25),
                                   linear(1000.0, 1.0)).continuous);
    assert(!guard::compareAt<State>(1000.0, linear(1000.0, 1.25),
                                   linear(1000.0, 1.0)).continuous);
    assert(guard::compareAt<State>(1000.599, linear(1000.0, 1.25),
                                  linear(1000.0, 1.25)).continuous);
    assert(!guard::compareAt<State>(1000.599, linear(1000.0, 1.0),
                                   [](double, State&) { return false; }).continuous);
    assert(!guard::compareAt<State>(std::numeric_limits<double>::infinity(),
                                   linear(1000.0, 1.0),
                                   linear(1000.0, 1.0)).continuous);

    // Reparameterizing a retained prefix to a new trajectory start must pass:
    // equal local times would be wrong, but equal ABSOLUTE time is correct.
    for (int i = 0; i != 10000; ++i) {
        const double now = 1000.0 + i * 0.0001;
        const auto previous = [](double wt, State& s) {
            const double t = wt - 1000.0;
            s(0, 0) = t * t;
            s(0, 1) = 2.0 * t;
            s(0, 2) = 2.0;
            return true;
        };
        const auto rebased = [](double wt, State& s) {
            const double local = wt - 1000.25;
            s(0, 0) = local * local + 0.5 * local + 0.0625;
            s(0, 1) = 2.0 * local + 0.5;
            s(0, 2) = 2.0;
            return true;
        };
        assert(guard::compareAt<State>(now, previous, rebased).continuous);
    }
    std::cout << "trajectory_handoff_guard_test: PASS\n";
}
