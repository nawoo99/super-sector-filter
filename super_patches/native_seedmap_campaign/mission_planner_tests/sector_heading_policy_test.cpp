#include <mission_planner/sector_heading_policy.hpp>
#include <cassert>
#include <cmath>
#include <iostream>

int main() {
  using namespace native_sector;
  assert(!exactBodyHeadingOptIn(nullptr));
  for (const char* value : {"", "0", "true", "01", "1 "})
    assert(!exactBodyHeadingOptIn(value));
  assert(exactBodyHeadingOptIn("1"));
  int checks = 7;
  for (int i = -5000; i <= 5000; ++i) {
    const double body = i / 1592.0, velocity = -body + 0.4;
    for (bool body_aligned : {false, true}) {
      // Fixed Sector is unchanged, including when the process inherits opt-in.
      assert(sectorHeading(false, body_aligned, velocity, body) == body);
      assert(sectorHeading(true, body_aligned, std::nullopt, body) == body);
      checks += 2;
    }
    // Legacy Adaptive/velocity mode remains exact when opt-in is absent.
    assert(sectorHeading(true, false, velocity, body) == velocity);
    // The candidate must not retain old velocity heading after a direction
    // change or a certified stop; both narrow modes now share the body axis.
    assert(sectorHeading(true, true, velocity, body) == body);
    checks += 2;
  }
  std::cout << "sector heading policy: " << checks << " checks passed\n";
}
