#include <mission_planner/sensor_acquisition.hpp>
#include <cassert>
#include <iostream>

int main() {
  using native_sector::SensorAcquisition;
  assert(!SensorAcquisition{}.matches(false, 0));
  const SensorAcquisition sector{true, false, 0, 0.0, 45.0};
  assert(sector.matches(false, 0));
  assert(!sector.matches(true, 1)); // Sector render straddled Full request.
  const SensorAcquisition full{true, true, 1, 0.0, 45.0};
  assert(full.matches(true, 1));
  assert(!full.matches(false, 1)); // Full render straddled Sector release.
  assert(!full.matches(true, 2)); // Previous episode's scan is not new evidence.
  const SensorAcquisition sector_after{true, false, 1, 1.5, 45.0};
  assert(sector_after.matches(false, 1));
  assert(!sector_after.matches(true, 2));
  std::cout << "sensor acquisition: typed source mode and cycle boundary checks passed\n";
}
