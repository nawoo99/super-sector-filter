// Compile twice: -DPROFILE_DSO_FIXTURE -shared -fPIC, then a linked executable.
// This matches the executable/component-library nesting used by acquisition.
#include <super_utils/thread_cpu_profile.hpp>
#include <cassert>
namespace p = super_utils::thread_cpu_profile;
#ifdef PROFILE_DSO_FIXTURE
extern "C" p::Registry *component_registry() { return &p::registry(); }
extern "C" p::Scope **component_stack() { return &p::activeScope(); }
extern "C" void component_work() {
    p::Scope scope(p::Stage::FrontendAcquisition);
    volatile unsigned value = 0;
    for (unsigned i = 0; i < 10000; ++i) value += i;
}
#else
extern "C" p::Registry *component_registry();
extern "C" p::Scope **component_stack();
extern "C" void component_work();
int main() {
    assert(component_registry() == &p::registry());
    assert(component_stack() == &p::activeScope());
    {
        p::Scope parent(p::Stage::SimRender);
        component_work();
    }
    auto &a = p::registry().counters[static_cast<unsigned>(p::Stage::SimRender)];
    auto &b = p::registry().counters[static_cast<unsigned>(p::Stage::FrontendAcquisition)];
    assert(a.calls.load() == (p::enabled() ? 1U : 0U));
    assert(b.calls.load() == a.calls.load());
    assert(a.inclusive_ns.load() == a.exclusive_ns.load() + b.inclusive_ns.load());
    assert(p::registry().clock_errors.load() == 0);
}
#endif
