#include <super_utils/thread_cpu_profile.hpp>

#include <chrono>
#include <cstdlib>
#include <iostream>
#include <thread>
#include <vector>

namespace profile = super_utils::thread_cpu_profile;

static_assert(static_cast<std::size_t>(profile::Stage::MapCloudEnqueue) == 0);
static_assert(static_cast<std::size_t>(profile::Stage::FsmPolyPublish) == 26);
static_assert(static_cast<std::size_t>(profile::Stage::SimStaticCloud) == 27);
static_assert(static_cast<std::size_t>(profile::Stage::SimOdom) == 28);
static_assert(static_cast<std::size_t>(profile::Stage::SimRender) == 29);
static_assert(static_cast<std::size_t>(profile::Stage::Count) == 30);

void require(bool condition, const char *description) {
    if (!condition) {
        std::cerr << "FAIL: " << description << '\n';
        std::exit(1);
    }
}

void burn(unsigned iterations) {
    volatile std::uint64_t value = 1;
    for (unsigned i = 0; i < iterations; ++i) {
        value = value * 1664525ULL + 1013904223ULL;
    }
}

int main() {
    using profile::Stage;
    auto &state = profile::registry();
    {
        profile::Scope disabled_or_enabled(Stage::MapCloudEnqueue);
        burn(1000);
    }
    for (const auto stage :
            {Stage::SimStaticCloud, Stage::SimOdom, Stage::SimRender}) {
        profile::Scope callback(stage);
        burn(100);
    }
    profile::reportThreadRole("profiler_test_main");
    if (!profile::enabled()) {
        profile::report(true);
        for (const auto &counter : state.counters) {
            require(counter.calls.load() == 0, "disabled calls must stay zero");
            require(counter.inclusive_ns.load() == 0, "disabled timing must stay zero");
        }
        require(state.clock_errors.load() == 0, "disabled clock errors");
        std::cout << "PASS disabled profiler\n";
        return 0;
    }

    for (const auto stage :
            {Stage::SimStaticCloud, Stage::SimOdom, Stage::SimRender}) {
        const auto &counter = state.counters[static_cast<std::size_t>(stage)];
        require(counter.calls.load() == 1, "sim callback scope counted");
        require(counter.inclusive_ns.load() == counter.exclusive_ns.load(),
                "sim callback leaf accounting");
    }
    require(std::strcmp(profile::kStageNames[27],
                        "sim_static_cloud_callback") == 0 &&
            std::strcmp(profile::kStageNames[28], "sim_odom_callback") == 0 &&
            std::strcmp(profile::kStageNames[29], "sim_render_callback") == 0,
            "stable appended callback stage names");

    const auto wall_start = std::chrono::steady_clock::now();
    {
        profile::Scope parent(Stage::FsmMainCallback);
        burn(1000);
        {
            profile::Scope child(Stage::GuardCertificate);
            burn(2000);
            std::this_thread::sleep_for(std::chrono::milliseconds(40));
        }
        burn(1000);
    }
    const auto wall_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now() - wall_start).count();
    auto &parent = state.counters[static_cast<std::size_t>(Stage::FsmMainCallback)];
    auto &child = state.counters[static_cast<std::size_t>(Stage::GuardCertificate)];
    require(parent.calls.load() == 1 && child.calls.load() == 1,
            "nested scope call counts");
    require(parent.inclusive_ns.load() == parent.exclusive_ns.load() +
            child.inclusive_ns.load(), "nested exclusive accounting");
    require(child.inclusive_ns.load() == child.exclusive_ns.load(),
            "leaf exclusive accounting");
    require(parent.inclusive_ns.load() < static_cast<std::uint64_t>(wall_ns / 2),
            "thread CPU must exclude sleeping time");

    std::vector<std::thread> workers;
    for (int i = 0; i < 4; ++i) {
        workers.emplace_back([] {
            for (int j = 0; j < 1000; ++j) {
                profile::Scope worker(Stage::MapWorker);
                burn(100);
            }
        });
    }
    for (auto &worker : workers) {
        worker.join();
    }
    auto &concurrent = state.counters[static_cast<std::size_t>(Stage::MapWorker)];
    require(concurrent.calls.load() == 4000, "concurrent aggregate call count");
    require(concurrent.inclusive_ns.load() == concurrent.exclusive_ns.load(),
            "thread-local stacks must not overlap across threads");
    require(state.clock_errors.load() == 0, "thread CPU clock availability");
    profile::report(true);
    std::cout << "PASS enabled, nested, sleeping, concurrent profiler\n";
}
