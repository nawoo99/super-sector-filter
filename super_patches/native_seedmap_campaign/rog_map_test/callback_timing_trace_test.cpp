#include <super_utils/callback_timing_trace.hpp>
#include <cassert>
#include <vector>
using namespace super_utils::callback_timing_trace;
struct Fake {
    static bool on;
    static int calls;
    static std::int64_t mono, epoch;
    static std::vector<Event> events;
    static bool enabled() { return on; }
    static std::int64_t now(clockid_t c) { ++calls; return c == CLOCK_MONOTONIC ? mono : epoch; }
    static long tid() { ++calls; return 7; }
    static void emit(const Event& e) { events.push_back(e); }
};
bool Fake::on = false;
int Fake::calls = 0;
std::int64_t Fake::mono = 1000000000, Fake::epoch = 9000000000;
std::vector<Event> Fake::events;
int main() {
    State state;
    { BasicScope<Fake> s(state, "disabled"); }
    assert(Fake::calls == 0 && state.last_begin == 0 && Fake::events.empty());
    Fake::on = true;
    { BasicScope<Fake> s(state, "fast"); Fake::mono += 1000000; }
    assert(Fake::events.empty());
    Fake::mono += 56000000;
    { BasicScope<Fake> s(state, "gap"); Fake::mono += 1000000; Fake::epoch -= 1000000000; }
    assert(Fake::events.size() == 1);
    auto e = Fake::events.back();
    assert(e.begin_ns - e.previous_begin_ns == 57000000);
    assert(e.end_ns - e.begin_ns == 1000000 && e.tid == 7);
    assert(e.epoch_end_ns < e.epoch_begin_ns); // Epoch jumps do not affect elapsed time.
    Fake::mono += 99000000;
    { BasicScope<Fake> s(state, "gap_disabled", 0); }
    assert(Fake::events.size() == 1);
    { BasicScope<Fake> s(state, "slow", 0); Fake::mono += 21000000; }
    assert(Fake::events.size() == 2);
    assert(Fake::events.back().end_ns - Fake::events.back().begin_ns == 21000000);
    State other;
    { BasicScope<Fake> s(other, "independent"); }
    assert(Fake::events.size() == 2);
    std::puts("callback timing trace: OFF/ON/threshold/clock-domain/instance tests passed");
}
