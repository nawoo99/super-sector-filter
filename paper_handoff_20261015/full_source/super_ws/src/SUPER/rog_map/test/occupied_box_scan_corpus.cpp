// Standalone: compile this file with g++ -std=c++17 -O3 -Irog_map/include.
// No ROS, Eigen, runtime integration, or production configuration is needed.
#include <rog_map/occupied_box_scan.hpp>

#include <array>
#include <cmath>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <memory>
#include <random>
#include <stdexcept>
#include <string>
#include <time.h>
#include <vector>

namespace {
using Index = rog_map::occupied_box_scan::Index;
using Point = std::array<double, 3>;
constexpr std::size_t kPageWords = 4096;
struct Page { std::array<std::uint64_t, kPageWords> words{}; };
struct Grid {
    Index size;
    Index half;
    Index origin;
    double resolution;
    Point bound_min;
    Point bound_max;
    double ground;
    double ceiling;
    bool empty{false};
    std::vector<std::shared_ptr<const Page>> pages;

    std::uint64_t word(const std::size_t id) const {
        return pages[id / kPageWords]->words[id % kPageWords];
    }
};
struct Box { Point min; Point max; };

Grid makeGrid(const Index size, const Index origin, const double resolution,
              const unsigned density_power, std::mt19937_64 &random) {
    Grid grid{};
    grid.size = size;
    grid.origin = origin;
    grid.resolution = resolution;
    for (int d = 0; d < 3; ++d) {
        grid.half[d] = (size[d] - 1) / 2;
        grid.bound_min[d] = (origin[d] - grid.half[d]) * resolution;
        grid.bound_max[d] = (origin[d] + grid.half[d] + 1) * resolution;
    }
    grid.ground = grid.bound_min[2];
    grid.ceiling = grid.bound_max[2];
    const std::size_t voxels = static_cast<std::size_t>(size[0]) * size[1] * size[2];
    const std::size_t words = (voxels + 63U) / 64U;
    const std::size_t pages = (words + kPageWords - 1) / kPageWords;
    for (std::size_t p = 0; p < pages; ++p) {
        auto page = std::make_shared<Page>();
        for (std::size_t w = 0; w < kPageWords; ++w) {
            std::uint64_t bits = ~std::uint64_t{0};
            if (density_power == 64) {
                bits = 0;
            } else {
                for (unsigned n = 0; n < density_power; ++n) bits &= random();
            }
            page->words[w] = bits;
        }
        grid.pages.emplace_back(std::move(page));
    }
    return grid;
}

// Intentionally transcribe the existing signed modulo + half-offset hash,
// rather than calling the new helper's coordinate function in the oracle.
int baselineHash(const Grid &grid, const Index &global) {
    Index local{};
    for (int d = 0; d < 3; ++d) {
        local[d] = global[d] % grid.size[d];
        if (local[d] > grid.half[d]) local[d] -= grid.size[d];
        else if (local[d] < -grid.half[d]) local[d] += grid.size[d];
        local[d] += grid.half[d];
    }
    return local[0] * grid.size[1] * grid.size[2] +
           local[1] * grid.size[2] + local[2];
}

// Match raw boxSearch's existing box handling and strictly interior index
// bounds. Conversion remains division, not multiplication by reciprocal.
bool rawBounds(const Grid &grid, const Box &input, Index &begin, Index &end) {
    if (grid.empty) return false;
    Point min = input.min;
    Point max = input.max;
    for (int d = 0; d < 3; ++d) if (max[d] - min[d] <= 0) return false;
    for (int d = 0; d < 3; ++d) {
        min[d] = std::max(min[d], grid.bound_min[d]);
        max[d] = std::min(max[d], grid.bound_max[d]);
    }
    min[2] = std::max(min[2], grid.ground);
    max[2] = std::min(max[2], grid.ceiling);
    for (int d = 0; d < 3; ++d) {
        if (max[d] - min[d] <= 0) return false;
        begin[d] = static_cast<int>(std::floor(min[d] / grid.resolution)) + 1;
        end[d] = static_cast<int>(std::floor(max[d] / grid.resolution));
    }
    return true;
}

Point center(const Grid &grid, const int i, const int j, const int k) {
    return {{(static_cast<double>(i) + 0.5) * grid.resolution,
             (static_cast<double>(j) + 0.5) * grid.resolution,
             (static_cast<double>(k) + 0.5) * grid.resolution}};
}

std::vector<Point> baselineQuery(const Grid &grid, const Box &box) {
    std::vector<Point> out;
    Index begin{}, end{};
    if (!rawBounds(grid, box, begin, end)) return out;
    for (int i = begin[0]; i < end[0]; ++i) {
        for (int j = begin[1]; j < end[1]; ++j) {
            for (int k = begin[2]; k < end[2]; ++k) {
                const int hash = baselineHash(grid, {{i, j, k}});
                if ((grid.word(static_cast<std::size_t>(hash) >> 6U) &
                     (std::uint64_t{1} << (hash & 63))) != 0) {
                    out.push_back(center(grid, i, j, k));
                }
            }
        }
    }
    return out;
}

std::vector<Point> fastQuery(const Grid &grid, const Box &box) {
    std::vector<Point> out;
    Index begin{}, end{};
    if (!rawBounds(grid, box, begin, end)) return out;
    rog_map::occupied_box_scan::forEachOccupied(
            begin, end, grid.size, grid.half,
            [&grid](const std::size_t word) { return grid.word(word); },
            [&grid, &out](const int i, const int j, const int k) {
                out.push_back(center(grid, i, j, k));
            });
    return out;
}

void compare(const Grid &grid, const Box &box, std::size_t &queries) {
    const auto expected = baselineQuery(grid, box);
    const auto actual = fastQuery(grid, box);
    if (expected.size() != actual.size()) {
        throw std::runtime_error("occupied vector length mismatch at query " +
                                 std::to_string(queries));
    }
    for (std::size_t n = 0; n < actual.size(); ++n) {
        for (int d = 0; d < 3; ++d) {
            if (std::memcmp(&actual[n][d], &expected[n][d], sizeof(double)) != 0) {
                throw std::runtime_error("ordered coordinate mismatch at query " +
                                         std::to_string(queries));
            }
        }
    }
    ++queries;
}

Box indexBox(const Grid &grid, const Index &first, const Index &last,
             const double fraction = 0.0) {
    Box out{};
    for (int d = 0; d < 3; ++d) {
        out.min[d] = (first[d] + fraction) * grid.resolution;
        out.max[d] = (last[d] + fraction) * grid.resolution;
    }
    return out;
}

void differentialCorpus() {
    std::mt19937_64 random(0x786bc901ULL);
    std::size_t queries = 0;
    // Odd z lengths straddle 64-bit words; large grids also span 4096-word
    // pages. Origins intentionally lie outside the canonical ring interval.
    const std::vector<Index> sizes{{{1, 1, 1}}, {{3, 5, 7}}, {{9, 11, 63}},
                                   {{17, 19, 65}}, {{83, 97, 129}}};
    const std::vector<Index> origins{{{0, 0, 0}}, {{-59, 107, -131}},
                                     {{127, -137, 271}}};
    for (const auto &size : sizes) {
        for (const auto &origin : origins) {
            for (const unsigned density : {64U, 0U, 1U, 4U, 10U}) {
                auto grid = makeGrid(size, origin, 0.05, density, random);
                const Box full{grid.bound_min, grid.bound_max};
                compare(grid, full, queries);
                for (int n = 0; n < 250; ++n) {
                    Box box{};
                    for (int d = 0; d < 3; ++d) {
                        const int extent = grid.size[d] * 2 + 7;
                        const double a = static_cast<double>(random() % extent) - extent / 2.0;
                        const double width = static_cast<double>(random() % (grid.size[d] + 5));
                        const double frac = (n % 3 == 0) ? 0.0 : 0.314159;
                        box.min[d] = (origin[d] + a + frac) * grid.resolution;
                        box.max[d] = (origin[d] + a + width + frac) * grid.resolution;
                    }
                    if (n % 17 == 0) std::swap(box.min[1], box.max[1]);
                    compare(grid, box, queries);
                }
                // Clip virtual height through cell interiors, not grid edges.
                grid.ground += 0.37 * grid.resolution;
                grid.ceiling -= 0.21 * grid.resolution;
                compare(grid, full, queries);
                grid.empty = true;
                compare(grid, full, queries);
            }
        }
    }

    // Explicit word/page boundaries, including occupied padding beyond the
    // queried span. These grids are full so incorrectly unmasked bits show.
    auto boundary = makeGrid({{83, 97, 129}}, {{0, 0, 0}}, 0.1, 0, random);
    const int yz = boundary.size[1] * boundary.size[2];
    const int voxel_count = boundary.size[0] * yz;
    for (const int hash : {63, 64, 127, 128, 262143, 262144, 524287, 524288}) {
        if (hash >= voxel_count) continue;
        Index center_id{{hash / yz - boundary.half[0],
                         (hash % yz) / boundary.size[2] - boundary.half[1],
                         hash % boundary.size[2] - boundary.half[2]}};
        Index first = center_id, last = center_id;
        for (int d = 0; d < 3; ++d) { first[d] -= 2; last[d] += 3; }
        compare(boundary, indexBox(boundary, first, last), queries);
        compare(boundary, indexBox(boundary, first, last, 0.125), queries);
    }
    // Direct iterator tests extend beyond a complete ring and compare each
    // emitted global index, protecting repeated-wrap traversal independently
    // of the production box clipper.
    auto ring = makeGrid({{3, 5, 7}}, {{0, 0, 0}}, 1.0, 1, random);
    for (int n = 0; n < 200; ++n) {
        Index begin{}, end{};
        for (int d = 0; d < 3; ++d) {
            begin[d] = static_cast<int>(random() % 61) - 30;
            end[d] = begin[d] + static_cast<int>(random() % 25);
        }
        std::vector<Index> expected, actual;
        for (int i = begin[0]; i < end[0]; ++i)
            for (int j = begin[1]; j < end[1]; ++j)
                for (int k = begin[2]; k < end[2]; ++k) {
                    const int hash = baselineHash(ring, {{i, j, k}});
                    if ((ring.word(static_cast<std::size_t>(hash) >> 6U) &
                         (std::uint64_t{1} << (hash & 63))) != 0)
                        expected.push_back({{i, j, k}});
                }
        rog_map::occupied_box_scan::forEachOccupied(
                begin, end, ring.size, ring.half,
                [&ring](const std::size_t word) { return ring.word(word); },
                [&actual](const int i, const int j, const int k) {
                    actual.push_back({{i, j, k}});
                });
        if (expected != actual) throw std::runtime_error("repeated-ring mismatch");
        ++queries;
    }
    std::cout << "PASS ordered occupied-box corpus: " << queries << " queries\n";
}

double cpuSeconds() {
    timespec now{};
    if (clock_gettime(CLOCK_THREAD_CPUTIME_ID, &now) != 0)
        throw std::runtime_error("thread CPU clock unavailable");
    return static_cast<double>(now.tv_sec) + now.tv_nsec * 1.0e-9;
}

using Query = std::vector<Point> (*)(const Grid &, const Box &);
volatile std::size_t benchmark_sink = 0;
double measure(const Grid &grid, const std::vector<Box> &boxes,
               const Query query, const int repetitions) {
    std::size_t checksum = 0;
    const double start = cpuSeconds();
    for (int repeat = 0; repeat < repetitions; ++repeat) {
        for (const auto &box : boxes) {
            // Whole query: clipping, floor division, occupancy scan, point
            // conversion, vector allocation/growth and destruction included.
            const auto points = query(grid, box);
            checksum += points.size();
            if (!points.empty()) checksum += points.front()[0] > 0.0;
        }
    }
    const double elapsed = cpuSeconds() - start;
    benchmark_sink = checksum;
    return elapsed;
}

void benchmark() {
    std::mt19937_64 random(0x17ed682cULL);
    for (const unsigned density : {64U, 10U, 7U, 4U, 1U, 0U}) {
        auto grid = makeGrid({{401, 401, 121}}, {{0, 0, 0}}, 0.05, density, random);
        std::vector<Box> boxes;
        // Raw resolution .05 m, corridor padding .8 m, seed length <=1 m,
        // matching the active profile's box geometry without loading a map.
        for (int n = 0; n < 64; ++n) {
            Box box{};
            for (int d = 0; d < 3; ++d) {
                const double coordinate = (static_cast<int>(random() % 800) - 400) * 0.01;
                const double position = d == 2 ? coordinate * 0.2 : coordinate;
                box.min[d] = position - 0.8;
                box.max[d] = position + 0.8 + (d == n % 3 ? 1.0 : 0.0);
            }
            boxes.push_back(box);
        }
        std::size_t count = 0;
        for (const auto &box : boxes) compare(grid, box, count);
        // Warm both, alternate order, then report the median paired timings.
        measure(grid, boxes, baselineQuery, 1);
        measure(grid, boxes, fastQuery, 1);
        std::vector<double> baseline_times, fast_times;
        constexpr int repetitions = 8;
        for (int round = 0; round < 5; ++round) {
            if (round % 2 == 0) {
                baseline_times.push_back(measure(grid, boxes, baselineQuery, repetitions));
                fast_times.push_back(measure(grid, boxes, fastQuery, repetitions));
            } else {
                fast_times.push_back(measure(grid, boxes, fastQuery, repetitions));
                baseline_times.push_back(measure(grid, boxes, baselineQuery, repetitions));
            }
        }
        std::sort(baseline_times.begin(), baseline_times.end());
        std::sort(fast_times.begin(), fast_times.end());
        const double baseline = baseline_times[2];
        const double fast = fast_times[2];
        const double micros_per_query = 1.0e6 / (boxes.size() * repetitions);
        const double probability = density == 64 ? 0.0 : std::ldexp(1.0, -static_cast<int>(density));
        std::cout << std::fixed << std::setprecision(3)
                  << "BENCH occupancy=" << probability * 100.0 << "% baseline_us="
                  << baseline * micros_per_query << " fast_us="
                  << fast * micros_per_query << " speedup=" << baseline / fast << "x\n";
    }
}
}  // namespace

int main(const int argc, char **argv) {
    try {
        differentialCorpus();
        if (argc > 1 && std::string(argv[1]) == "--benchmark") benchmark();
    } catch (const std::exception &error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
