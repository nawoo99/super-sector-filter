#include <perfect_drone_sim/static_pc_latched_policy.hpp>
#include <iostream>
#include <stdexcept>

int main() {
    namespace p = perfect_drone::static_pc_latched;
    int checks = 0;
    const auto require = [&](bool good) {
        ++checks;
        if (!good) throw std::runtime_error("latched static policy test failed");
    };
    const auto rejects = [&](auto function) {
        bool threw = false;
        try { function(); } catch (const std::exception&) { threw = true; }
        require(threw);
    };
    require(!p::parseEnabled(nullptr, false, 100, true, "1"));
    require(!p::parseEnabled("0", false, 100, true, "1"));
    require(p::parseEnabled("1", true, 1, false, nullptr));
    require(p::parseEnabled("1", true, 1, false, "0"));
    for (const char* s : {"", "01", " 1", "1 ", "true", "2", "-1"})
        rejects([&] { p::parseEnabled(s, true, 1, false, "0"); });
    rejects([] { p::parseEnabled("1", false, 1, false, "0"); });
    rejects([] { p::parseEnabled("1", true, 100, false, "0"); });
    rejects([] { p::parseEnabled("1", true, 1, true, "0"); });
    for (const char* s : {"", "1", "true"})
        rejects([&] { p::parseEnabled("1", true, 1, false, s); });
    p::Evidence evidence;
    require(evidence.publications == 0);
    require(evidence.points == 0 && evidence.bytes == 0 && evidence.stamp_ns == 0);
    p::Evidence sim_time_zero;
    sim_time_zero.published(1, 32, 0);
    require(sim_time_zero.publications == 1 && sim_time_zero.stamp_ns == 0);
    rejects([&] { evidence.published(0, 32, 1); });
    rejects([&] { evidence.published(1, 0, 1); });
    rejects([&] { evidence.published(1, 32, -1); });
    require(evidence.publications == 0);
    evidence.published(241490, 7727680, 12345);
    require(evidence.publications == 1 &&
            evidence.points == 241490 && evidence.bytes == 7727680 && evidence.stamp_ns == 12345);
    rejects([&] { evidence.published(241490, 7727680, 12345); });
    require(evidence.publications == 1 && evidence.stamp_ns == 12345 &&
            evidence.points == 241490 && evidence.bytes == 7727680);
    std::vector<std::uint8_t> wire(64);
    for (std::size_t i = 0; i < wire.size(); ++i) wire[i] = static_cast<std::uint8_t>(i + 1);
    const auto before = wire;
    p::canonicalizeXyziTailPadding(wire, 32);
    require(wire.size() == before.size());
    for (std::size_t base : {0, 32}) {
        require(std::equal(wire.begin() + base, wire.begin() + base + 20, before.begin() + base));
        require(std::all_of(wire.begin() + base + 20, wire.begin() + base + 32,
                           [](std::uint8_t value) { return value == 0; }));
    }
    const auto canonical = wire;
    p::canonicalizeXyziTailPadding(wire, 32);
    require(wire == canonical);
    rejects([&] { p::canonicalizeXyziTailPadding(wire, 16); });
    require(wire == canonical);
    std::vector<std::uint8_t> malformed(63, 42);
    rejects([&] { p::canonicalizeXyziTailPadding(malformed, 32); });
    require(malformed == std::vector<std::uint8_t>(63, 42));
    std::vector<std::uint8_t> empty;
    rejects([&] { p::canonicalizeXyziTailPadding(empty, 32); });
    rejects([&] { p::canonicalizeXyziTailPadding(wire, 0); });
    std::cout << "PASS latched static policy " << checks << " checks; not DDS delivery proof\n";
}
