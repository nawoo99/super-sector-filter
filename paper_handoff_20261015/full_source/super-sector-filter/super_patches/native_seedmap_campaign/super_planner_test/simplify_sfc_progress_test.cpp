// Offline regression for corridor simplification progress and rejection.
// Links the real polytope, geometry and SDLP implementations; no ROS or flight.
#ifdef SIMPLIFY_SFC_TEST_HEADER
#include SIMPLIFY_SFC_TEST_HEADER
#else
#include <data_structure/base/polytope.h>
#endif

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using geometry_utils::Polytope;
using geometry_utils::PolytopeVec;
using geometry_utils::SimplifySFC;
using super_utils::MatD4f;
using super_utils::Vec3f;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

Polytope box(double minimum_x, double maximum_x) {
    MatD4f planes(6, 4);
    planes << 1, 0, 0, -maximum_x, -1, 0, 0, minimum_x,
              0, 1, 0, -1, 0, -1, 0, -1,
              0, 0, 1, -1, 0, 0, -1, -1;
    Polytope result(planes);
    result.SetFaceObstacleFlags({1, 0, 1, 0, 1, 0});
    result.SetSeedLine({Vec3f(minimum_x, 0, 0), Vec3f(maximum_x, 0, 0)}, .2);
    result.overlap_depth_with_last_one = minimum_x;
    return result;
}

void same_corridor(const PolytopeVec& actual, const PolytopeVec& expected) {
    require(actual.size() == expected.size(), "corridor size changed unexpectedly");
    for (std::size_t index = 0; index < actual.size(); ++index) {
        require((actual[index].GetPlanes().array() == expected[index].GetPlanes().array()).all(),
                "corridor planes changed");
        require(actual[index].GetFaceObstacleFlags() == expected[index].GetFaceObstacleFlags(),
                "obstacle face metadata changed");
        require(actual[index].seed_line == expected[index].seed_line &&
                actual[index].robot_r == expected[index].robot_r &&
                actual[index].HaveSeedLine() == expected[index].HaveSeedLine() &&
                actual[index].overlap_depth_with_last_one == expected[index].overlap_depth_with_last_one,
                "corridor seed/overlap metadata changed");
    }
}

void reject_unchanged(PolytopeVec corridor, double start, double finish) {
    const auto original = corridor;
    require(!SimplifySFC(Vec3f(start, 0, 0), Vec3f(finish, 0, 0), corridor),
            "disconnected or touching corridor must be rejected");
    same_corridor(corridor, original);
}

void valid_cases() {
    auto chain = PolytopeVec{box(0, 2), box(1, 3), box(2.5, 4.5)};
    const auto chain_expected = chain;
    require(SimplifySFC(Vec3f(.5, 0, 0), Vec3f(4, 0, 0), chain), "valid bridge rejected");
    same_corridor(chain, chain_expected);

    auto shortcut = PolytopeVec{box(0, 3), box(1, 4), box(2, 5), box(4, 7)};
    const auto shortcut_expected = PolytopeVec{shortcut[0], shortcut[2], shortcut[3]};
    require(SimplifySFC(Vec3f(.5, 0, 0), Vec3f(6.5, 0, 0), shortcut), "valid shortcut rejected");
    same_corridor(shortcut, shortcut_expected);

    auto trimmed = PolytopeVec{box(-5, -.5), box(0, 3), box(1, 4), box(2, 5), box(4, 7), box(7, 9)};
    const auto trimmed_expected = PolytopeVec{trimmed[1], trimmed[3], trimmed[4]};
    require(SimplifySFC(Vec3f(.5, 0, 0), Vec3f(6.5, 0, 0), trimmed), "valid trimmed chain rejected");
    same_corridor(trimmed, trimmed_expected);

    auto common = PolytopeVec{box(-3, -1), box(0, 3), box(4, 6)};
    const auto common_expected = PolytopeVec{common[1]};
    require(SimplifySFC(Vec3f(.5, 0, 0), Vec3f(2.5, 0, 0), common), "single selected corridor rejected");
    same_corridor(common, common_expected);
    std::cout << "valid corridors: bridge=3 shortcut=3 trimmed=3 common=1; metadata unchanged\n";
}
}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--valid-only") {
            valid_cases();
            return 0;
        }
        // This is the original unbounded-growth path: anchor 0 cannot reach
        // polytope 2, so it switches to 1; 1 also cannot reach 2. Retrying 2
        // without advancing 1 formerly appended polytope 1 indefinitely.
        reject_unchanged({box(0, 2), box(1, 3), box(4, 6)}, .5, 5);
        if (argc == 2 && std::string(argv[1]) == "--disconnected-only") {
            std::cout << "disconnected corridor rejected without modifying input\n";
            return 0;
        }
        reject_unchanged({box(0, 2), box(1, 3), box(3, 5)}, .5, 4);
        reject_unchanged({box(0, 1), box(2, 3), box(2.5, 4)}, .5, 3.5);
        reject_unchanged({box(0, 1), box(1, 3), box(2, 4)}, .5, 3.5);
        reject_unchanged({box(0, 2), box(1, 3), box(2, 4), box(5, 7)}, .5, 6);
        valid_cases();
        for (int iteration = 0; iteration < 1000; ++iteration) {
            reject_unchanged({box(0, 2), box(1, 3), box(4, 6)}, .5, 5);
        }
        std::cout << "PASS: disconnected/touching/repeated recovery inputs terminate; valid selection preserved\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
