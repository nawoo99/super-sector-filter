// Standalone test of the proposed snapshot-pinned line traversal. Compile the
// production RayCaster unchanged; its common_lib.hpp is unused by RayCaster and
// may be suppressed via -DSUPER_UTILS_HEADER_TYPE_UTILS_HPP to avoid ROS/PCL.
#include <rog_map/snapshot_line_query.hpp>
#include <rog_map/rog_map_core/raycaster.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <random>
#include <stdexcept>
#include <string>
#include <thread>
#include <time.h>
#include <vector>

namespace {
using Point = Eigen::Vector3d;
using Index = Eigen::Vector3i;
using Neighbors = std::vector<Index>;
constexpr std::size_t kPageWords = 4096;
struct Page { std::array<std::uint64_t, kPageWords> words{}; };
struct Grid {
    Index size;
    Index half;
    Index origin;
    double resolution;
    double resolution_inv;
    double ground;
    double ceiling;
    int ground_index;
    int ceiling_index;
    int safe_margin;
    std::uint64_t version;
    std::vector<std::shared_ptr<const Page>> pages;
};
using Snapshot = std::shared_ptr<const Grid>;
struct Trace {
    std::uint64_t queries{0};
    std::uint64_t hash{1469598103934665603ULL};
    std::uint64_t loads{0};
    std::uint64_t final_checks{0};
    void record(const Index& index, const bool floating, const bool occupied) {
        ++queries;
        for (int d = 0; d < 3; ++d) {
            hash ^= static_cast<std::uint32_t>(index[d]);
            hash *= 1099511628211ULL;
        }
        hash ^= (floating ? 2U : 0U) | static_cast<unsigned>(occupied);
        hash *= 1099511628211ULL;
    }
};
struct Ray {
    Point start;
    Point end;
    double max_distance;
};

void require(const bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

Grid makeGrid(const Index& size, const Index& origin, const double resolution,
              const unsigned density_power, const std::uint64_t version,
              std::mt19937_64& random) {
    Grid grid;
    grid.size = size;
    grid.half = (size.array() - 1) / 2;
    grid.origin = origin;
    grid.resolution = resolution;
    grid.resolution_inv = 1.0 / resolution;
    grid.ground_index = origin.z() - grid.half.z() + 3;
    grid.ceiling_index = origin.z() + grid.half.z() - 3;
    grid.ground = grid.ground_index * resolution;
    grid.ceiling = (grid.ceiling_index + 1) * resolution;
    grid.safe_margin = 2;
    grid.version = version;
    const std::size_t cells = static_cast<std::size_t>(size.x()) * size.y() * size.z();
    const std::size_t words = (cells + 63U) / 64U;
    const std::size_t pages = (words + kPageWords - 1) / kPageWords;
    for (std::size_t p = 0; p < pages; ++p) {
        auto page = std::make_shared<Page>();
        for (auto& word : page->words) {
            word = ~std::uint64_t{0};
            if (density_power == 64) {
                word = 0;
            } else {
                for (unsigned n = 0; n < density_power; ++n) word &= random();
            }
        }
        grid.pages.push_back(std::move(page));
    }
    return grid;
}

// Independent scalar transcription of current snapshot predicates. Keep float
// division and integer-neighbor reciprocal multiplication intentionally distinct.
bool referenceOccupied(const Grid& grid, const Index& id, const Point* point) {
    for (int d = 0; d < 3; ++d) {
        if (std::abs(id[d] - grid.origin[d]) > grid.half[d]) return false;
    }
    if (point) {
        if (point->z() > grid.ceiling || point->z() < grid.ground) return true;
    } else if (id.z() > grid.ceiling_index ||
               id.z() < grid.ground_index + grid.safe_margin) {
        return true;
    }
    std::array<int, 3> local{};
    for (int d = 0; d < 3; ++d) {
        local[d] = id[d] % grid.size[d];
        if (local[d] > grid.half[d]) local[d] -= grid.size[d];
        else if (local[d] < -grid.half[d]) local[d] += grid.size[d];
        local[d] += grid.half[d];
    }
    const std::size_t hash = static_cast<std::size_t>(local[0]) * grid.size.y() * grid.size.z() +
                             local[1] * grid.size.z() + local[2];
    const std::size_t word_index = hash >> 6U;
    return ((grid.pages[word_index / kPageWords]->words[word_index % kPageWords] >>
             (hash & 63U)) & 1U) != 0;
}

Index referenceFloatIndex(const Point& point, const double resolution) {
    Index id;
    for (int d = 0; d < 3; ++d) id[d] = static_cast<int>(std::floor(point[d] / resolution));
    return id;
}

Index referenceNeighborIndex(const Point& point, const double reciprocal) {
    Index id;
    for (int d = 0; d < 3; ++d) id[d] = static_cast<int>(std::floor(point[d] * reciprocal));
    return id;
}

// Fast predicates use the production Eigen/index and ring-hash operations.
bool pinnedOccupied(const Grid& grid, const Index& id, const Point* point) {
    if (((id - grid.origin).cwiseAbs() - grid.half).maxCoeff() > 0) return false;
    if (point) {
        if (point->z() > grid.ceiling || point->z() < grid.ground) return true;
    } else if (id.z() > grid.ceiling_index ||
               id.z() < grid.ground_index + grid.safe_margin) {
        return true;
    }
    Index local;
    for (int d = 0; d < 3; ++d) {
        local[d] = id[d] % grid.size[d];
        if (local[d] > grid.half[d]) local[d] -= grid.size[d];
        else if (local[d] < -grid.half[d]) local[d] += grid.size[d];
        local[d] += grid.half[d];
    }
    const std::size_t hash = local.x() * grid.size.y() * grid.size.z() +
                             local.y() * grid.size.z() + local.z();
    const std::size_t word = hash >> 6U;
    return ((grid.pages[word / kPageWords]->words[word % kPageWords] >> (hash & 63U)) & 1U) != 0;
}

bool legacyLine(Snapshot& published, const Ray& input, const Neighbors& neighbors,
                const double resolution, Trace& trace) {
    rog_map::raycaster::RayCaster raycaster;
    raycaster.setResolution(resolution);
    raycaster.setInput(input.start, input.end);  // Deliberately preserve ignored return.
    Point point;
    while (raycaster.step(point)) {
        if (input.max_distance > 0 && (point - input.start).norm() > input.max_distance) return false;
        if (neighbors.empty()) {
            ++trace.loads;
            const auto snapshot = std::atomic_load(&published);
            const auto id = referenceFloatIndex(point, snapshot->resolution);
            const bool occupied = referenceOccupied(*snapshot, id, &point);
            trace.record(id, true, occupied);
            if (occupied) return false;
        } else {
            const auto id = referenceNeighborIndex(point, 1.0 / resolution);
            for (const auto& neighbor : neighbors) {
                const Index shifted = id + neighbor;
                ++trace.loads;
                const auto snapshot = std::atomic_load(&published);
                const bool occupied = referenceOccupied(*snapshot, shifted, nullptr);
                trace.record(shifted, false, occupied);
                if (occupied) return false;
            }
        }
    }
    return true;
}

template <typename Hook>
bool pinnedLine(Snapshot& published, const Ray& input, const Neighbors& neighbors,
                const double resolution, Trace& trace, Hook&& after_query) {
    ++trace.loads;
    const auto pinned = std::atomic_load(&published);
    rog_map::raycaster::RayCaster raycaster;
    raycaster.setResolution(resolution);
    raycaster.setInput(input.start, input.end);
    return rog_map::snapshot_line_query::isLineFree(
        raycaster, input.start, input.max_distance, neighbors,
        [&](const Point& point) {
            const Index id = (point.array() / pinned->resolution).floor().cast<int>();
            const bool occupied = pinnedOccupied(*pinned, id, &point);
            trace.record(id, true, occupied);
            after_query(trace.queries);
            return occupied;
        },
        [&](const Point& point) -> Index {
            return (point.array() * (1.0 / resolution)).floor().cast<int>();
        },
        [&](const Index& id) {
            const bool occupied = pinnedOccupied(*pinned, id, nullptr);
            trace.record(id, false, occupied);
            after_query(trace.queries);
            return occupied;
        },
        [&] {
            ++trace.loads;
            ++trace.final_checks;
            const auto current = std::atomic_load(&published);
            return current && current.get() == pinned.get() && current->version == pinned->version;
        });
}

Neighbors productionNeighbors() {
    Neighbors result;
    for (int x = -4; x <= 4; ++x)
        for (int y = -4; y <= 4; ++y)
            for (int z = -4; z <= 4; ++z)
                if (x * x + y * y + z * z <= 16) result.emplace_back(x, y, z);
    std::stable_sort(result.begin(), result.end(), [](const Index& a, const Index& b) {
        return a.squaredNorm() < b.squaredNorm();
    });
    require(result.size() == 257, "production sphere must contain 257 neighbors");
    return result;
}

std::uint64_t quiescentCorpus() {
    std::mt19937_64 random(0x53534c51ULL);
    const std::array<Neighbors, 4> neighbor_sets{
        Neighbors{}, Neighbors{Index(0, 0, 0)}, productionNeighbors(),
        Neighbors{Index(4, -1, 2), Index(0, 0, 0), Index(-7, 2, -4), Index(1, 3, 2)}};
    std::uint64_t cases = 0;
    std::uint64_t queries = 0;
    for (const double resolution : {0.05, 0.1, 0.2, 0.3}) {
        for (const unsigned density : {0U, 5U, 11U, 64U}) {
            const Index origin(-37, 18, -9);
            Snapshot published = std::make_shared<Grid>(makeGrid(
                Index(101, 103, 105), origin, resolution, density, ++cases, random));
            const auto& grid = *published;
            std::vector<Ray> rays;
            const Point center = (origin.cast<double>().array() + 0.5) * resolution;
            for (int d = 0; d < 3; ++d) {
                Point offset = Point::Zero();
                offset[d] = 70 * resolution;
                rays.push_back({center - offset, center + offset, 0});
                rays.push_back({center + offset, center - offset, -1});
                rays.push_back({center, center + offset, 14 * resolution});
                rays.push_back({center, center + offset, std::nextafter(14 * resolution, 0.0)});
                rays.push_back({center, center + offset, std::nextafter(14 * resolution, 100.0)});
            }
            rays.push_back({center, center, 0});
            rays.push_back({center, center + Point::Constant(0.001 * resolution), 0});
            for (const double height : {grid.ground, grid.ceiling,
                     grid.ground + 0.5 * resolution,
                     (grid.ground_index + grid.safe_margin + 0.5) * resolution,
                     (grid.ceiling_index + 0.5) * resolution,
                     (origin.z() + grid.half.z() + 1.5) * resolution}) {
                Point start = center;
                start.z() = height;
                rays.push_back({start, start + Point(15 * resolution, 0, 0), 0});
            }
            for (unsigned i = 0; i < 240; ++i) {
                Point start;
                Point end;
                for (int d = 0; d < 3; ++d) {
                    start[d] = (origin[d] + static_cast<int>(random() % 143) - 71 + 0.5) * resolution;
                    end[d] = (origin[d] + static_cast<int>(random() % 143) - 71 + 0.5) * resolution;
                    if ((i % 7) == 0) start[d] = std::nextafter(start[d], end[d]);
                }
                const double limit = (i % 3) ? 0.0 : (random() % 100) * resolution;
                rays.push_back({start, end, limit});
            }
            for (const auto& neighbors : neighbor_sets) {
                for (const auto& ray : rays) {
                    Trace legacy;
                    Trace fast;
                    const bool expected = legacyLine(published, ray, neighbors, resolution, legacy);
                    const bool actual = pinnedLine(published, ray, neighbors, resolution, fast,
                                                   [](std::uint64_t) {});
                    ++cases;
                    queries += legacy.queries;
                    require(expected == actual, "quiescent boolean mismatch at case " + std::to_string(cases));
                    require(legacy.queries == fast.queries && legacy.hash == fast.hash,
                            "quiescent ordered predicate trace mismatch at case " + std::to_string(cases));
                    require(fast.loads == (actual ? 2U : 1U), "pin count must be one plus accepted-line final check");
                    require(fast.final_checks == (actual ? 1U : 0U), "final check count mismatch");
                }
            }
        }
    }
    std::cout << "quiescent_cases=" << cases - 16 << " ordered_occupancy_queries=" << queries << '\n';
    return cases - 16;
}

void predicateEdges() {
    std::mt19937_64 random(3);
    auto grid = makeGrid(Index(101, 103, 105), Index(-37, 18, -9), 0.05, 64, 1, random);
    std::uint64_t differences = 0;
    for (const double resolution : {0.05, 0.1, 0.2, 0.3}) {
        for (int value = -100; value <= 100; ++value) {
            const double boundary = value * resolution;
            for (const double coordinate : {boundary, std::nextafter(boundary, -1000.0),
                                            std::nextafter(boundary, 1000.0)}) {
                const Point point(coordinate, coordinate, coordinate);
                const auto divide = referenceFloatIndex(point, resolution);
                const auto multiply = referenceNeighborIndex(point, 1.0 / resolution);
                if (divide != multiply) ++differences;
                const Index fast_divide = (point.array() / resolution).floor().cast<int>();
                const Index fast_multiply = (point.array() * (1.0 / resolution)).floor().cast<int>();
                require(divide == fast_divide && multiply == fast_multiply, "conversion edge mismatch");
            }
        }
    }
    require(differences > 0, "fixture must expose division/reciprocal distinctions");
    const auto center = grid.origin;
    for (const double height : {grid.ground, std::nextafter(grid.ground, -1000.0),
                               grid.ceiling, std::nextafter(grid.ceiling, 1000.0)}) {
        const Point point(center.x() * grid.resolution, center.y() * grid.resolution, height);
        const auto id = referenceFloatIndex(point, grid.resolution);
        const bool expected = height < grid.ground || height > grid.ceiling;
        require(referenceOccupied(grid, id, &point) == expected, "physical boundary oracle mismatch");
        require(pinnedOccupied(grid, id, &point) == expected, "physical boundary predicate mismatch");
    }
    for (const int z : {grid.ground_index + grid.safe_margin - 1,
                        grid.ground_index + grid.safe_margin, grid.ceiling_index,
                        grid.ceiling_index + 1}) {
        const Index id(center.x(), center.y(), z);
        const bool expected = z < grid.ground_index + grid.safe_margin || z > grid.ceiling_index;
        require(referenceOccupied(grid, id, nullptr) == expected, "integer virtual boundary oracle mismatch");
        require(pinnedOccupied(grid, id, nullptr) == expected, "integer virtual boundary predicate mismatch");
    }
    for (int d = 0; d < 3; ++d) {
        for (const int direction : {-1, 1}) {
            Index id = center;
            id[d] += direction * (grid.half[d] + 1);
            const Point point = (id.cast<double>().array() + 0.5) * grid.resolution;
            require(!referenceOccupied(grid, id, nullptr) && !pinnedOccupied(grid, id, nullptr),
                    "outside-map integer query must remain false");
            require(!referenceOccupied(grid, id, &point) && !pinnedOccupied(grid, id, &point),
                    "outside-map float query must remain false");
        }
    }
    // Exercise exact word/page edges without relying on random rays visiting them.
    // Disable virtual obstacles here so the asserted true result must be the bit.
    grid.ground_index = grid.origin.z() - grid.half.z() - grid.safe_margin - 1;
    grid.ceiling_index = grid.origin.z() + grid.half.z() + 1;
    for (const std::size_t hash : {0U, 63U, 64U, 262143U, 262144U, 262145U}) {
        auto page = std::make_shared<Page>(*grid.pages[(hash >> 6U) / kPageWords]);
        page->words[(hash >> 6U) % kPageWords] |= std::uint64_t{1} << (hash & 63U);
        grid.pages[(hash >> 6U) / kPageWords] = page;
        const int x = hash / (grid.size.y() * grid.size.z());
        const int y = (hash / grid.size.z()) % grid.size.y();
        const int z = hash % grid.size.z();
        Index id = Index(x, y, z) - grid.half;
        for (int d = 0; d < 3; ++d) {
            while (id[d] < grid.origin[d] - grid.half[d]) id[d] += grid.size[d];
            while (id[d] > grid.origin[d] + grid.half[d]) id[d] -= grid.size[d];
        }
        require(referenceOccupied(grid, id, nullptr) && pinnedOccupied(grid, id, nullptr),
                "word/page boundary occupied bit mismatch");
    }
    std::cout << "conversion_boundary_distinctions=" << differences << " predicate_edges=PASS\n";
}

void publicationCorpus() {
    std::mt19937_64 random(9);
    const auto original = std::make_shared<const Grid>(makeGrid(
        Index(151, 41, 41), Index(0, 0, 0), 0.05, 64, 1, random));
    const auto newer = std::make_shared<const Grid>(makeGrid(
        Index(151, 41, 41), Index(0, 0, 0), 0.05, 64, 2, random));
    const Ray free_ray{Point(-3.0, 0.02, 0.02), Point(3.0, 0.02, 0.02), 0};
    unsigned rejected = 0;
    for (const auto& neighbors : {Neighbors{}, Neighbors{Index(0, 0, 0)}, productionNeighbors()}) {
        for (const std::uint64_t switch_at : {1U, 5U, 50U}) {
            Snapshot published = original;
            Trace trace;
            const bool result = pinnedLine(published, free_ray, neighbors, 0.05, trace,
                [&](const std::uint64_t count) {
                    if (count == switch_at) std::atomic_store(&published, newer);
                });
            require(!result && trace.final_checks == 1, "changed publication must reject free pinned ray");
            require(published == newer, "publication hook did not run");
            ++rejected;
        }
    }
    // Real writer thread, deterministic rendezvous while the reader pins old data.
    Snapshot published = original;
    std::atomic<int> phase{0};
    std::thread writer([&] {
        while (phase.load(std::memory_order_acquire) != 1) std::this_thread::yield();
        std::atomic_store(&published, newer);
        phase.store(2, std::memory_order_release);
    });
    Trace trace;
    const bool result = pinnedLine(published, free_ray, productionNeighbors(), 0.05, trace,
        [&](const std::uint64_t count) {
            if (count == 10) {
                phase.store(1, std::memory_order_release);
                while (phase.load(std::memory_order_acquire) != 2) std::this_thread::yield();
            }
        });
    writer.join();
    require(!result && trace.final_checks == 1, "concurrent publication must reject pinned ray");
    // Empty traversal retains legacy zero-length acceptance unless version stale.
    Trace empty;
    const Ray zero{free_ray.start, free_ray.start, 0};
    require(pinnedLine(published, zero, Neighbors{}, 0.05, empty, [](std::uint64_t) {}),
            "zero-length legacy acceptance changed");
    require(empty.queries == 0 && empty.final_checks == 1, "empty traversal checks mismatch");
    std::cout << "publication_change_rejections=" << rejected + 1 << " writer_thread=PASS\n";
}

double threadCpuSeconds() {
    timespec now{};
    require(clock_gettime(CLOCK_THREAD_CPUTIME_ID, &now) == 0, "thread CPU clock failed");
    return now.tv_sec + now.tv_nsec * 1e-9;
}

void benchmark() {
    std::mt19937_64 random(17);
    Snapshot published = std::make_shared<Grid>(makeGrid(
        Index(301, 101, 101), Index(0, 0, 0), 0.05, 64, 1, random));
    const auto neighbors = productionNeighbors();
    const Ray ray{Point(-3.0, 0.025, 0.025), Point(3.0, 0.025, 0.025), 6.0};
    constexpr unsigned repeats = 300;
    Trace legacy;
    Trace fast;
    unsigned legacy_true = 0;
    unsigned fast_true = 0;
    const double begin_legacy = threadCpuSeconds();
    for (unsigned i = 0; i < repeats; ++i) legacy_true += legacyLine(published, ray, neighbors, 0.05, legacy);
    const double legacy_cpu = threadCpuSeconds() - begin_legacy;
    const double begin_fast = threadCpuSeconds();
    for (unsigned i = 0; i < repeats; ++i)
        fast_true += pinnedLine(published, ray, neighbors, 0.05, fast, [](std::uint64_t) {});
    const double fast_cpu = threadCpuSeconds() - begin_fast;
    require(legacy_true == repeats && fast_true == repeats, "benchmark ray unexpectedly blocked");
    require(legacy.queries == fast.queries && legacy.hash == fast.hash, "benchmark ordered query trace mismatch");
    std::cout << std::setprecision(9)
              << "benchmark_repeats=" << repeats << " queries=" << legacy.queries
              << " baseline_atomic_loads=" << legacy.loads << " pinned_atomic_loads=" << fast.loads
              << " baseline_cpu_s=" << legacy_cpu << " pinned_cpu_s=" << fast_cpu
              << " synthetic_speedup=" << legacy_cpu / fast_cpu << '\n';
}
}  // namespace

int main(int argc, char** argv) {
    try {
        predicateEdges();
        quiescentCorpus();
        publicationCorpus();
        if (argc > 1 && std::string(argv[1]) == "--benchmark") benchmark();
        std::cout << "snapshot_line_query_corpus=PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "snapshot_line_query_corpus=FAIL reason=" << error.what() << '\n';
        return 1;
    }
}
