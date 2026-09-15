// Deterministic state-leakage regression for the discarded backup replay.
// A runs operational optimize + diagnostic replay; B only operational optimize.
// No ROS executor, renderer, planner loop or flight is involved.

#include <traj_opt/backup_traj_optimizer_s4.h>

#include <algorithm>
#include <cmath>
#include <iostream>
#include <iomanip>
#include <limits>
#include <memory>
#include <stdexcept>
#include <sstream>
#include <string>
#include <vector>

#ifdef BACKUP_TEST_DETERMINISTIC_GEOMETRY
extern "C" std::size_t backup_equivalence_wrapped_geometry_calls();
#endif

namespace {
using namespace super_utils;
using namespace geometry_utils;

class QuietRos final : public ros_interface::RosInterface {
 public:
  void debug(const std::string &) override {}
  void info(const std::string &) override {}
  void warn(const std::string &) override {}
  void error(const std::string &) override {}
  void fatal(const std::string &) override {}
  void setSimTime(const double &) override {}
  double getSimTime() override { return 0.0; }
  void getSimTime(int32_t &sec, uint32_t &nsec) override { sec = 0; nsec = 0; }
  void vizExpTraj(const Trajectory &, const std::string &) override {}
  void vizBackupTraj(const Trajectory &) override {}
  void vizFrontendPath(const vec_Vec3f &) override {}
  void vizExpSfc(const PolytopeVec &) override {}
  void vizBackupSfc(const Polytope &) override {}
  void vizGoalPath(const vec_Vec3f &) override {}
  void vizCommittedTraj(const Trajectory &, const double &) override {}
  void vizYawTraj(const Trajectory &, const Trajectory &) override {}
  void pubReplanStatus(const bool &) override {}
  void vizAstarBoundingBox(const Vec3f &, const Vec3f &) override {}
  void vizAstarPoints(const Vec3f &, const Color &, const std::string &,
                      const double &, const int &) override {}
  void vizReplanLog(const Trajectory &, const Trajectory &, const Trajectory &,
                    const Trajectory &, const PolytopeVec &, const Polytope &,
                    const vec_Vec3f &, const int &) override {}
  void vizCiriSeedLine(const Vec3f &, const Vec3f &, const double &) override {}
  void vizCiriEllipsoid(const Ellipsoid &) override {}
  void vizCiriInfeasiblePoint(const Vec3f) override {}
  void vizCiriPolytope(const Polytope &, const std::string &) override {}
  void vizCiriPointCloud(const vec_Vec3f &) override {}
};

void require(bool condition, const std::string &message) {
  if (!condition) throw std::runtime_error(message);
}

struct Comparison {
  double maximum_error{0.0};
  std::size_t scalar_checks{0};
  void scalar(double first, double second, const std::string &label) {
    ++scalar_checks;
    require(std::isfinite(first) && std::isfinite(second),
            label + ": non-finite operational/initialization output");
    const double error = std::abs(first - second);
    maximum_error = std::max(maximum_error, error);
    const double scale = std::max({1.0, std::abs(first), std::abs(second)});
    std::ostringstream detail;
    detail << std::setprecision(17) << label << ": numerical mismatch first="
           << first << " second=" << second << " absolute_error=" << error
           << " relative_error=" << error / scale;
    require(error <= 1.0e-10 * scale, detail.str());
  }
  template <typename First, typename Second>
  void matrix(const Eigen::MatrixBase<First> &first,
              const Eigen::MatrixBase<Second> &second,
              const std::string &label) {
    require(first.rows() == second.rows() && first.cols() == second.cols(),
            label + ": dimension mismatch");
    for (Eigen::Index row = 0; row < first.rows(); ++row)
      for (Eigen::Index col = 0; col < first.cols(); ++col)
        scalar(first(row, col), second(row, col), label);
  }
};

Trajectory referenceTrajectory(const Vec3f &origin, const Vec3f &velocity,
                               const Vec3f &acceleration) {
  Eigen::MatrixXd coefficients = Eigen::MatrixXd::Zero(3, 8);
  coefficients.col(7) = origin;
  coefficients.col(6) = velocity;
  coefficients.col(5) = 0.5 * acceleration;
  Trajectory trajectory;
  trajectory.emplace_back(6.0, coefficients);
  return trajectory;
}

Polytope box(const Vec3f &minimum, const Vec3f &maximum) {
  MatD4f planes(6, 4);
  planes << 1, 0, 0, -maximum.x(), -1, 0, 0, minimum.x(),
            0, 1, 0, -maximum.y(), 0, -1, 0, minimum.y(),
            0, 0, 1, -maximum.z(), 0, 0, -1, minimum.z();
  Polytope corridor(planes);
  corridor.SetFaceObstacleFlags({1, 1, 1, 1, 0, 0});
  return corridor;
}

struct Fixture {
  std::string name;
  Trajectory reference;
  Polytope corridor;
  double t0{0.1};
  double te{2.5};
  double heuristic_start{1.5};
  double heuristic_duration{1.0};
  bool nan_rejection{false};
  bool must_fail{false};
};

std::vector<Fixture> fixtures(bool unique_center_cubes) {
  // Equal axis extents give a unique Chebyshev center. This optional state-
  // isolation control prevents SDLP's shared random plane permutation from
  // choosing different equally valid centers for a rectangular corridor.
  // The unmodified rectangular fixtures remain available as a production-
  // geometry observation; no optimizer tolerance is relaxed for that case.
  const auto open = unique_center_cubes
      ? box(Vec3f(-8, -8, -7), Vec3f(8, 8, 9))
      : box(Vec3f(-8, -8, -2), Vec3f(8, 8, 6));
  const auto straight = referenceTrajectory(Vec3f(0, 0, 1),
      Vec3f(1.0, 0.0, 0.0), Vec3f::Zero());
  const auto diagonal = referenceTrajectory(Vec3f(-1, -1, 1),
      Vec3f(0.8, 0.6, 0.1), Vec3f(0.1, -0.05, 0.0));
  const auto reverse = referenceTrajectory(Vec3f(1, 1, 1.4),
      Vec3f(-0.7, -0.2, -0.05), Vec3f(0.0, 0.04, 0.02));
  const auto impossible = box(Vec3f(50, 50, 0),
      Vec3f(52, 52, unique_center_cubes ? 2 : 3));
  auto nan_planes = open.GetPlanes();
  nan_planes(0, 0) = std::numeric_limits<double>::quiet_NaN();
  return {
      {"straight", straight, open},
      {"diagonal_accelerating", diagonal, open, 0.2, 2.8, 1.7, 1.2},
      {"reverse_curved", reverse, open, 0.15, 2.3, 1.4, 0.9},
      // Valid convex setup but the entire permitted start interval lies far
      // outside the corridor: penalties must reject this operational solve.
      {"infeasible_head", straight, impossible, 0.1, 2.5, 1.5, 1.0,
       false, true},
      {"after_infeasible_head", straight, open},
      // Early failure is safe only after prior initialized solves. Do not call
      // the old replay with undefined/empty initialization on this case.
      {"nan_corridor", diagonal, Polytope(nan_planes), 0.1, 2.5, 1.5,
       1.0, true, true},
      {"after_nan_corridor", straight, open},
  };
}

struct Init {
  double start{0};
  VecDf times;
  vec_Vec3f points;
};

Init getInit(traj_opt::BackupTrajOpt &optimizer) {
  Init value;
  optimizer.getInitValue(value.start, value.times, value.points);
  return value;
}

void compareInit(const Init &first, const Init &second, Comparison &comparison,
                 const std::string &label) {
  comparison.scalar(first.start, second.start, label + " init_ts");
  comparison.matrix(first.times, second.times, label + " init_times");
  require(first.points.size() == second.points.size(),
          label + " init point count mismatch");
  for (std::size_t i = 0; i < first.points.size(); ++i)
    comparison.matrix(first.points[i], second.points[i], label + " init_point");
}

void runSuite(traj_opt::Config config, bool uniform, int pieces,
              Comparison &comparison, bool enable_replay,
              bool unique_center_cubes) {
  config.uniform_time_en = uniform;
  config.piece_num = pieces;
  config.save_log_en = false;
  config.print_optimizer_log = false;
  config.passage_center_log_en = false;
  // Keep the configured production iteration bound (currently 2048); earlier
  // 512-iteration trial evidence is retained separately and is not a pass.
  const auto ros = std::make_shared<QuietRos>();
  traj_opt::BackupTrajOpt with_replay(config, ros);
  traj_opt::BackupTrajOpt without_replay(config, ros);
  std::size_t successes = 0;
  std::size_t failures = 0;
  std::size_t replay_calls = 0;
  bool prior_failure = false;
  std::size_t recovered_successes = 0;
  for (const auto &fixture : fixtures(unique_center_cubes)) {
    const std::string label = std::string(uniform ? "uniform" : "nonuniform") +
        "/pieces" + std::to_string(pieces) + "/" + fixture.name;
    double duration_a = fixture.heuristic_duration;
    double duration_b = fixture.heuristic_duration;
    double start_a = -77.0, start_b = -77.0;
    Trajectory result_a, result_b;
    const VecDf end_position = fixture.reference.getPos(fixture.te);
    const bool ok_a = with_replay.optimize(fixture.reference, fixture.t0,
        fixture.te, fixture.heuristic_start, end_position, duration_a,
        fixture.corridor, result_a, start_a);
    const bool ok_b = without_replay.optimize(fixture.reference, fixture.t0,
        fixture.te, fixture.heuristic_start, end_position, duration_b,
        fixture.corridor, result_b, start_b);
    require(ok_a == ok_b, label + ": operational result mismatch");
    if (fixture.must_fail)
      require(!ok_a, label + ": deliberately infeasible fixture succeeded");
    comparison.scalar(start_a, start_b, label + " out_ts");
    comparison.scalar(duration_a, duration_b, label + " heuristic_duration");
    require(result_a.getPieceNum() == result_b.getPieceNum(),
            label + ": trajectory piece count mismatch");
    comparison.matrix(result_a.getDurations(), result_b.getDurations(),
                       label + " durations");
    for (int piece = 0; piece < result_a.getPieceNum(); ++piece)
      comparison.matrix(result_a[piece].getCoeffMat(),
                         result_b[piece].getCoeffMat(), label + " coefficients");
    const auto initial_a = getInit(with_replay);
    const auto initial_b = getInit(without_replay);
    compareInit(initial_a, initial_b, comparison, label);
    if (ok_a) {
      ++successes;
      if (prior_failure) ++recovered_successes;
      require(!result_a.empty(), label + ": successful solve has empty output");
    } else {
      ++failures;
    }
    prior_failure = !ok_a;
    if (!fixture.nan_rejection && enable_replay) {
      require(initial_a.times.size() == pieces &&
                  initial_a.points.size() == static_cast<std::size_t>(pieces),
              label + ": cannot safely exercise replay without valid init");
      require(initial_a.times.allFinite() && initial_a.times.minCoeff() > 0,
              label + ": replay initial durations invalid");
      Trajectory ignored_trajectory;
      double ignored_start = -77.0;
      (void)with_replay.optimize(fixture.reference, fixture.t0, fixture.te,
          initial_a.start, fixture.corridor, initial_a.times, initial_a.points,
          ignored_trajectory, ignored_start);
      ++replay_calls;
    }
    std::cout << "CASE " << label << " operational_ok=" << ok_a
              << " pieces=" << result_a.getPieceNum()
              << " out_ts=" << start_a << '\n';
  }
  require(successes >= 3, "suite failed to exercise sufficient successful solves");
  require(failures >= 2 && recovered_successes >= 2,
          "suite failed to exercise failure -> success state resets");
  std::cout << "PASS suite uniform=" << uniform << " pieces=" << pieces
            << " max_iterations=" << config.max_iterations
            << " successes=" << successes << " failures=" << failures
            << " failure_to_success=" << recovered_successes
            << " discarded_replays=" << replay_calls << '\n';
}
}  // namespace

int main(int argc, char **argv) {
  try {
    const std::string config_path = argc > 1 ? argv[1] :
        "/root/super_ws/src/SUPER/super_planner/config/"
        "static_seedmaps_guard_viability_tight_v7.yaml";
    traj_opt::Config config(config_path, "backup_traj");
    bool enable_replay = true;
    bool unique_center_cubes = false;
    for (int i = 2; i < argc; ++i) {
      const std::string argument(argv[i]);
      if (argument == "--control-no-replay") enable_replay = false;
      else if (argument == "--unique-center-cubes") unique_center_cubes = true;
      else throw std::runtime_error("unrecognized argument: " + argument);
    }
    std::cout << "COMPARISON_MODE "
              << (enable_replay ? "operational_plus_replay_vs_operational_only"
                                : "operational_only_vs_operational_only")
              << " unique_center_cubes=" << unique_center_cubes << '\n';
    Comparison comparison;
    for (const bool uniform : {true, false})
      for (const int pieces : {2, 3})
        runSuite(config, uniform, pieces, comparison, enable_replay,
                 unique_center_cubes);
    std::cout << "PASS backup replay equivalence: scalar_checks="
              << comparison.scalar_checks << " maximum_absolute_error="
              << comparison.maximum_error << " tolerance=1e-10_relative\n";
#ifdef BACKUP_TEST_DETERMINISTIC_GEOMETRY
    require(backup_equivalence_wrapped_geometry_calls() > 0,
            "test-only deterministic geometry wrapper did not execute");
    std::cout << "TEST_ONLY_ANALYTIC_BOX_GEOMETRY calls="
              << backup_equivalence_wrapped_geometry_calls()
              << " production_geometry_rng_not_covered=1\n";
#endif
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "FAIL backup replay equivalence: " << error.what() << '\n';
    return 1;
  }
}
