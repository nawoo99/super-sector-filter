#include <perfect_drone_sim/static_pc_durable_policy.hpp>

#include <iostream>
#include <stdexcept>

int main() {
    namespace policy = perfect_drone::static_pc_durable;
    int checks = 0;
    auto require = [&](bool value) {
        ++checks;
        if (!value) throw std::runtime_error("static-PC durable policy check failed");
    };
    auto rejects = [&](const char* value, int poll_ms, bool two_phase) {
        bool threw = false;
        try { (void)policy::parseEnabled(value, poll_ms, two_phase); }
        catch (const std::invalid_argument&) { threw = true; }
        require(threw);
    };
    require(!policy::parseEnabled(nullptr, 1, false));
    require(!policy::parseEnabled("0", 1, false));
    require(!policy::parseEnabled(nullptr, 100, false));
    require(!policy::parseEnabled("0", 1, true));
    require(policy::parseEnabled("1", 1, false));
    for (const char* value : {"", "true", "false", "01", "+1", "-1", " 1", "1 ", "2"}) {
        rejects(value, 1, false);
    }
    rejects("1", 100, false);
    rejects("1", 1, true);
    rejects("1", 100, true);
    rejects("1", 0, false);
    rejects("1", -1, false);
    std::cout << "PASS static-PC durable parser " << checks
              << " checks (not ROS delivery proof)\n";
}
