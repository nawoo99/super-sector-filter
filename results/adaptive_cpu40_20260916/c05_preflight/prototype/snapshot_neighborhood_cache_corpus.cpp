// Standalone prototype: production RayCaster + C4 traversal are unchanged.
// See commands.sh for the ROS/PCL-free test build.
#include <rog_map/snapshot_neighborhood_cache.hpp>
#include <rog_map/snapshot_line_query.hpp>
#include <rog_map/rog_map_core/raycaster.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <iomanip>
#include <memory>
#include <new>
#include <stdexcept>
#include <string>
#include <time.h>
#include <type_traits>
#include <vector>

namespace {
namespace nc = rog_map::snapshot_neighborhood_cache;
using Cache = nc::Cache<>;
using Index = nc::Index;
using Point = Eigen::Vector3d;
using EigenIndex = Eigen::Vector3i;
using Neighbors = std::vector<EigenIndex>;
struct Snapshot {
    explicit Snapshot(std::uint64_t v = 1, std::uint32_t s = 0, bool f = true,
                      int* destroyed_counter = nullptr)
        : version(v), salt(s), free(f), destroyed(destroyed_counter) {}
    ~Snapshot() { if (destroyed) ++*destroyed; }
    std::uint64_t version;
    std::uint32_t salt;
    bool free;
    int* destroyed;
};
using SnapshotPtr = std::shared_ptr<const Snapshot>;

void require(bool value, const std::string& reason) {
    if (!value) throw std::runtime_error(reason);
}

Index indexOf(const EigenIndex& index) { return {index.x(), index.y(), index.z()}; }

Neighbors sphere() {
    Neighbors out;
    for (int x = -4; x <= 4; ++x)
        for (int y = -4; y <= 4; ++y)
            for (int z = -4; z <= 4; ++z)
                if (x * x + y * y + z * z <= 16) out.emplace_back(x, y, z);
    std::stable_sort(out.begin(), out.end(), [](const EigenIndex& a, const EigenIndex& b) {
        return a.squaredNorm() < b.squaredNorm();
    });
    require(out.size() == 257, "production sphere size");
    return out;
}

void cacheStateTests() {
    static_assert(sizeof(Cache) < 96 * 1024, "default cache exceeds bounded per-thread budget");
    Cache cache;
    auto snapshot = std::make_shared<const Snapshot>();
    int map_a = 0;
    int map_b = 0;
    nc::PredicateIdentity identity{&map_a, -30, 30, 2};
    Neighbors neighbors{EigenIndex(0, 0, 0), EigenIndex(1, 0, 0)};
    const Index center{1, -2, 3};
    std::uint64_t evaluations = 0;
    auto query = [&](bool answer) {
        return cache.anyOccupied(center, [&] { ++evaluations; return answer; });
    };
    require(cache.beginLine(snapshot, 1, identity, neighbors), "first context active");
    require(!query(false) && !query(true) && evaluations == 1, "miss then exact false hit");
    require(snapshot.use_count() == 1, "cache must not retain strong map ownership");
    const Neighbors equal_neighbors = neighbors;
    require(cache.beginLine(snapshot, 1, identity, equal_neighbors), "equal copy active");
    require(!query(true) && evaluations == 1, "equal-content new vector should retain hit");

    // Same vector/storage, changed contents must invalidate.
    const auto* old_address = neighbors.data();
    neighbors[0].x() = -3;
    require(neighbors.data() == old_address, "fixture unexpectedly reallocated");
    cache.beginLine(snapshot, 1, identity, neighbors);
    require(query(true) && evaluations == 2, "same-pointer neighbor mutation invalidation");
    require(query(false) && evaluations == 2, "exact occupied=true hit must avoid evaluation");
    std::swap(neighbors[0], neighbors[1]);
    cache.beginLine(snapshot, 1, identity, neighbors);
    require(!query(false) && evaluations == 3, "ordered neighbor identity invalidation");
    cache.beginLine(snapshot, 2, identity, neighbors);
    require(query(true) && evaluations == 4, "version invalidation");
    identity.map_instance = &map_b;
    cache.beginLine(snapshot, 2, identity, neighbors);
    require(!query(false) && evaluations == 5, "map identity invalidation");
    ++identity.ground_index;
    cache.beginLine(snapshot, 2, identity, neighbors);
    require(query(true) && evaluations == 6, "ground predicate invalidation");
    --identity.ceiling_index;
    cache.beginLine(snapshot, 2, identity, neighbors);
    require(!query(false) && evaluations == 7, "ceiling predicate invalidation");
    ++identity.safe_margin;
    cache.beginLine(snapshot, 2, identity, neighbors);
    require(query(true) && evaluations == 8, "margin predicate invalidation");
    auto replacement = std::make_shared<const Snapshot>(2);
    cache.beginLine(replacement, 2, identity, neighbors);
    require(!query(false) && evaluations == 9, "new snapshot owner with same version");

    // Direct-mapped collision must recompute, never reuse another center's value.
    Index collision = center;
    do { ++collision[0]; } while (Cache::bucketFor(collision) != Cache::bucketFor(center));
    require(cache.anyOccupied(collision, [&] { ++evaluations; return true; }), "collision insert");
    require(!query(false) && evaluations == 11, "collision replacement must miss old center");

    Neighbors oversized(Cache::max_neighbors + 1, EigenIndex::Zero());
    require(!cache.beginLine(snapshot, 2, identity, oversized), "oversized list bypass");
    require(query(true) && !query(false) && evaluations == 13, "bypass evaluates every call");
    require(!cache.beginLine(snapshot, 2, identity, Neighbors{}), "empty list bypass");
    require(!cache.beginLine(SnapshotPtr{}, 2, identity, neighbors), "null snapshot bypass");
    cache.beginLine(replacement, 2, identity, neighbors);
    require(query(true) && evaluations == 14, "return from bypass must recompute old context");
    auto full_neighbors = sphere();
    cache.beginLine(snapshot, 2, identity, full_neighbors);
    require(!query(false) && evaluations == 15, "full neighbor list initial miss");
    full_neighbors[128].z() += 1;
    cache.beginLine(snapshot, 2, identity, full_neighbors);
    require(query(true) && evaluations == 16, "middle of full neighbor list mutation");
    full_neighbors.back().y() -= 1;
    cache.beginLine(snapshot, 2, identity, full_neighbors);
    require(!query(false) && evaluations == 17, "last full neighbor list mutation");
    std::cout << "state_tests=PASS cache_bytes=" << sizeof(Cache)
              << " capacity=" << Cache::capacity << " max_neighbors=" << Cache::max_neighbors
              << " evaluations=" << evaluations << '\n';
}

void ownershipAndEpochTests() {
    nc::Cache<16, 8> cache;
    const Neighbors neighbors{EigenIndex::Zero()};
    int map = 0;
    const nc::PredicateIdentity identity{&map, -20, 20, 1};
    const Index center{-5, 2, 7};
    int destroyed = 0;
    typename std::aligned_storage<sizeof(Snapshot), alignof(Snapshot)>::type storage;
    auto deleter = [](const Snapshot* value) { value->~Snapshot(); };
    SnapshotPtr original(new (&storage) Snapshot(7, 0, true, &destroyed), deleter);
    const void* address = original.get();
    std::weak_ptr<const Snapshot> weak = original;
    cache.beginLine(original, 7, identity, neighbors);
    require(!cache.anyOccupied(center, [] { return false; }), "old owner cached false");
    original.reset();
    require(weak.expired() && destroyed == 1, "weak cache must allow old map destruction");
    SnapshotPtr replacement(new (&storage) Snapshot(7, 1, true, &destroyed), deleter);
    require(replacement.get() == address, "ABA fixture must reuse exact object address");
    cache.beginLine(replacement, 7, identity, neighbors);
    unsigned evaluations = 0;
    require(cache.anyOccupied(center, [&] { ++evaluations; return true; }) && evaluations == 1,
            "new control block at same object address/version must invalidate");
    replacement.reset();
    require(destroyed == 2, "replacement object lifetime retained by cache");

    // Also distinguish different aliased objects sharing one ownership block.
    auto owner = std::make_shared<std::array<Snapshot, 2>>();
    SnapshotPtr alias_a(owner, &(*owner)[0]);
    SnapshotPtr alias_b(owner, &(*owner)[1]);
    cache.beginLine(alias_a, 1, identity, neighbors);
    require(!cache.anyOccupied(center, [] { return false; }), "alias A cached false");
    cache.beginLine(alias_b, 1, identity, neighbors);
    require(cache.anyOccupied(center, [] { return true; }), "same-owner different object invalidation");

    nc::Cache<16, 8, std::uint8_t> narrow_epoch;
    narrow_epoch.beginLine(alias_a, 1, identity, neighbors);  // epoch 2
    require(!narrow_epoch.anyOccupied(center, [] { return false; }), "old epoch false insert");
    for (std::uint64_t version = 2; version <= 256; ++version) {
        narrow_epoch.beginLine(alias_a, version, identity, neighbors);
    }
    // Epoch is 2 again; the old entry must have been cleared during wrap.
    require(narrow_epoch.anyOccupied(center, [] { return true; }), "epoch wrap must clear old entry");
    std::cout << "owner_control_block_ABA=PASS alias_identity=PASS epoch_wrap=PASS\n";
}

bool occupied(const Snapshot& snapshot, const EigenIndex& id,
              const nc::PredicateIdentity& identity, std::uint64_t& queries) {
    ++queries;
    if (std::abs(id.x()) > 128 || std::abs(id.y()) > 128 || std::abs(id.z()) > 40) return false;
    if (id.z() > identity.ceiling_index || id.z() < identity.ground_index + identity.safe_margin) return true;
    if (snapshot.free) return false;
    std::uint32_t hash = static_cast<std::uint32_t>(id.x()) * 73856093U ^
                         static_cast<std::uint32_t>(id.y()) * 19349663U ^
                         static_cast<std::uint32_t>(id.z()) * 83492791U ^ snapshot.salt;
    hash ^= hash >> 16U;
    return (hash & 4095U) == 0;
}

struct Ray { Point start; Point end; double max_distance; };

bool runLine(const Ray& ray, SnapshotPtr& published, const Neighbors& neighbors,
             const nc::PredicateIdentity& identity, Cache* cache, std::uint64_t& queries,
             bool publish_during_query = false) {
    const auto snapshot = published;
    rog_map::raycaster::RayCaster raycaster;
    raycaster.setResolution(0.05);
    raycaster.setInput(ray.start, ray.end);
    unsigned centers = 0;
    auto point_to_index = [&](const Point& point) -> EigenIndex {
        if (publish_during_query && ++centers == 3) published = std::make_shared<const Snapshot>(snapshot->version + 1);
        return (point.array() * 20.0).floor().cast<int>();
    };
    auto float_occupied = [&](const Point& point) {
        const EigenIndex index = (point.array() / 0.05).floor().cast<int>();
        return occupied(*snapshot, index, identity, queries);
    };
    auto integer_occupied = [&](const EigenIndex& index) { return occupied(*snapshot, index, identity, queries); };
    auto still_current = [&] { return published.get() == snapshot.get() && published->version == snapshot->version; };
    if (!cache) {
        return rog_map::snapshot_line_query::isLineFree(raycaster, ray.start, ray.max_distance,
            neighbors, float_occupied, point_to_index, integer_occupied, still_current);
    }
    cache->beginLine(snapshot, snapshot->version, identity, neighbors);
    auto neighborhood_occupied = [&](const EigenIndex& center) {
        return cache->anyOccupied(indexOf(center), [&] {
            for (const auto& neighbor : neighbors) {
                const EigenIndex shifted = center + neighbor;
                if (integer_occupied(shifted)) return true;
            }
            return false;
        });
    };
    return nc::isLineFree(raycaster, ray.start, ray.max_distance, !neighbors.empty(),
                         float_occupied, point_to_index, neighborhood_occupied, still_current);
}

void rayCorpus() {
    Cache cache;
    int map = 0;
    const nc::PredicateIdentity identity{&map, -30, 30, 2};
    const std::array<Neighbors, 4> neighbor_sets{
        Neighbors{}, Neighbors{EigenIndex::Zero()}, sphere(),
        Neighbors{EigenIndex(4, 0, 0), EigenIndex(-2, 3, -1)}};
    std::vector<Ray> rays;
    const Point start(-3.0, 0.025, 0.025);
    for (int x = -20; x <= 20; x += 2) {
        for (int y = -10; y <= 10; y += 2) {
            const Point end(3.0 + x * 0.05, y * 0.05 + 0.025, 0.025);
            rays.push_back({start, end, 0});
            rays.push_back({end, start, 6.0});
        }
    }
    rays.push_back({start, start, 0});
    rays.push_back({start, start + Point(0.001, 0.001, 0.001), -1});
    rays.push_back({Point(-8, 0.025, 0.025), Point(8, 0.025, 0.025), 0});
    rays.push_back({Point(0.025, 0.025, -1.5), Point(1.025, 0.025, -1.5), 0});
    std::uint64_t cases = 0;
    std::uint64_t uncached_queries = 0;
    std::uint64_t cached_queries = 0;
    for (unsigned generation = 0; generation < 4; ++generation) {
        SnapshotPtr published = std::make_shared<const Snapshot>(generation + 1, generation * 31, generation < 2);
        for (const auto& neighbors : neighbor_sets) {
            for (const auto& ray : rays) {
                const bool expected = runLine(ray, published, neighbors, identity, nullptr, uncached_queries);
                const bool actual = runLine(ray, published, neighbors, identity, &cache, cached_queries);
                require(expected == actual, "cached ray mismatch at " + std::to_string(cases));
                ++cases;
            }
        }
    }
    // Pre-populate hits, then change publication mid-ray before final true.
    SnapshotPtr published = std::make_shared<const Snapshot>();
    const auto neighbors = sphere();
    const Ray free_ray{start, Point(3, 0.025, 0.025), 0};
    require(runLine(free_ray, published, neighbors, identity, &cache, cached_queries), "warmup ray free");
    require(!runLine(free_ray, published, neighbors, identity, &cache, cached_queries, true),
            "cached free hits must not bypass final publication rejection");
    require(cached_queries < uncached_queries, "corpus must actually exercise cache reuse");
    std::cout << "ray_cases=" << cases << " baseline_queries=" << uncached_queries
              << " cached_queries=" << cached_queries << " final_publication_rejection=PASS\n";
}

double cpuSeconds() {
    timespec time{};
    require(clock_gettime(CLOCK_THREAD_CPUTIME_ID, &time) == 0, "CPU clock");
    return time.tv_sec + time.tv_nsec * 1e-9;
}

void benchmark() {
    Cache cache;
    int map = 0;
    const nc::PredicateIdentity identity{&map, -30, 30, 2};
    SnapshotPtr published = std::make_shared<const Snapshot>();
    const auto neighbors = sphere();
    const Ray ray{Point(-3, 0.025, 0.025), Point(3, 0.025, 0.025), 6.0};
    std::uint64_t uncached_queries = 0;
    std::uint64_t cached_queries = 0;
    constexpr unsigned repeats = 1000;
    const auto begin_uncached = cpuSeconds();
    for (unsigned n = 0; n < repeats; ++n)
        require(runLine(ray, published, neighbors, identity, nullptr, uncached_queries), "benchmark uncached free");
    const auto uncached_cpu = cpuSeconds() - begin_uncached;
    const auto begin_cached = cpuSeconds();
    for (unsigned n = 0; n < repeats; ++n)
        require(runLine(ray, published, neighbors, identity, &cache, cached_queries), "benchmark cached free");
    const auto cached_cpu = cpuSeconds() - begin_cached;
    std::cout << std::setprecision(9) << "benchmark_repeats=" << repeats
              << " baseline_queries=" << uncached_queries << " cached_queries=" << cached_queries
              << " baseline_cpu_s=" << uncached_cpu << " cached_cpu_s=" << cached_cpu
              << " synthetic_speedup=" << uncached_cpu / cached_cpu << '\n';
}
}  // namespace

int main(int argc, char** argv) {
    try {
        cacheStateTests();
        ownershipAndEpochTests();
        rayCorpus();
        if (argc > 1 && std::string(argv[1]) == "--benchmark") benchmark();
        std::cout << "snapshot_neighborhood_cache_corpus=PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "snapshot_neighborhood_cache_corpus=FAIL reason=" << error.what() << '\n';
        return 1;
    }
}
