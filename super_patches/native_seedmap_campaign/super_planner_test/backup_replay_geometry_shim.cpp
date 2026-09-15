// TEST ONLY. Link with --wrap on the no-interior enumerateVs overload.
// Axis-aligned fixture boxes use their analytic center, avoiding shared SDLP
// random state. The real explicit-interior vertex enumeration remains in use.
// This object is never linked into the production planner or simulator.

#include <utils/geometry/geometry_utils.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>

namespace {
std::size_t geometry_calls = 0;
}

extern "C" std::size_t backup_equivalence_wrapped_geometry_calls() {
  return geometry_calls;
}

extern "C" bool
__wrap__ZN14geometry_utils11enumerateVsERKN5Eigen6MatrixIdLin1ELi4ELi0ELin1ELi4EEERNS1_IdLi3ELin1ELi0ELi3ELin1EEEd(
    const Eigen::MatrixX4d &planes, Eigen::Matrix3Xd &vertices,
    const double epsilon) {
  if (planes.rows() != 6 || !planes.allFinite())
    throw std::runtime_error("test geometry shim accepts finite six-face boxes only");
  Eigen::Vector3d minimum = Eigen::Vector3d::Constant(
      -std::numeric_limits<double>::infinity());
  Eigen::Vector3d maximum = Eigen::Vector3d::Constant(
      std::numeric_limits<double>::infinity());
  for (Eigen::Index row = 0; row < planes.rows(); ++row) {
    Eigen::Index axis = 0;
    planes.row(row).head<3>().cwiseAbs().maxCoeff(&axis);
    const double normal = planes(row, axis);
    if (std::abs(normal) < 0.5)
      throw std::runtime_error("test geometry shim received degenerate face");
    for (Eigen::Index other = 0; other < 3; ++other)
      if (other != axis && std::abs(planes(row, other)) > 1.0e-12)
        throw std::runtime_error("test geometry shim received non-axis-aligned face");
    const double coordinate = -planes(row, 3) / normal;
    if (normal > 0) maximum(axis) = std::min(maximum(axis), coordinate);
    else minimum(axis) = std::max(minimum(axis), coordinate);
  }
  if (!minimum.allFinite() || !maximum.allFinite() ||
      (maximum.array() <= minimum.array()).any())
    throw std::runtime_error("test geometry shim received unbounded/empty box");
  ++geometry_calls;
  geometry_utils::enumerateVs(planes, 0.5 * (minimum + maximum), vertices,
                              epsilon);
  return true;
}
