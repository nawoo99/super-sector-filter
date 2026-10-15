/**
* This file is part of ROG-Map
*
* Copyright 2024 Yunfan REN, MaRS Lab, University of Hong Kong, <mars.hku.hk>
* Developed by Yunfan REN <renyf at connect dot hku dot hk>
* for more information see <https://github.com/hku-mars/ROG-Map>.
* If you use this code, please cite the respective publications as
* listed on the above website.
*
* ROG-Map is free software: you can redistribute it and/or modify
* it under the terms of the GNU Lesser General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* ROG-Map is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU Lesser General Public License
* along with ROG-Map. If not, see <http://www.gnu.org/licenses/>.
*/

#include "rog_map/rog_map.h"
#include "rog_map/diagnostic_trace.hpp"
#include "rog_map/occupied_box_scan.hpp"
#include "rog_map/snapshot_line_query.hpp"
#include "rog_map/snapshot_neighborhood_cache.hpp"

#include <cstdlib>
#include <cstring>
#include <limits>
#include <fstream>

namespace {
bool fastOccupiedBoxScanEnabled() {
    static const bool enabled = [] {
        const char *setting = std::getenv("SUPER_FAST_OCCUPIED_BOX_SCAN");
        return setting && std::strcmp(setting, "1") == 0;
    }();
    return enabled;
}

bool compareOccupiedBoxScanEnabled() {
    static const bool enabled = [] {
        const char *setting = std::getenv("SUPER_COMPARE_OCCUPIED_BOX_SCAN");
        return setting && std::strcmp(setting, "1") == 0;
    }();
    return enabled;
}

bool snapshotLineQueryEnabled() {
    static const bool enabled = [] {
        const char *setting = std::getenv("SUPER_SNAPSHOT_LINE_QUERY");
        return setting && std::strcmp(setting, "1") == 0;
    }();
    return enabled;
}

bool snapshotNeighborCacheEnabled() {
    static const bool enabled = [] {
        const char *setting = std::getenv("SUPER_SNAPSHOT_NEIGHBOR_CACHE");
        return setting && std::strcmp(setting, "1") == 0;
    }();
    return enabled;
}
}  // namespace

using namespace rog_map;
using namespace super_utils;
void ROGMap::init() {

    initProbMap();

    immutable_snapshot_enabled_ = !cfg_.map_sliding_en &&
                                  !cfg_.raycasting_en &&
                                  !cfg_.unk_inflation_en;

    map_info_log_file_.open(DEBUG_FILE_DIR("rm_info_log.csv"), std::ios::out | std::ios::trunc);
    time_log_file_.open(DEBUG_FILE_DIR("rm_performance_log.csv"), std::ios::out | std::ios::trunc);


    robot_state_.p = cfg_.fix_map_origin;
    robot_state_.v.setZero();
    robot_state_.a.setZero();
    robot_state_.j.setZero();

    if (cfg_.map_sliding_en) {
        mapSliding(Vec3f(0, 0, 0));
        inf_map_->mapSliding(Vec3f(0, 0, 0));
    }
    else {
        /// if disable map sliding, fix map origin to (0,0,0)
        /// update the local map bound as
        local_map_bound_min_d_ = -cfg_.half_map_size_d + cfg_.fix_map_origin;
        local_map_bound_max_d_ = cfg_.half_map_size_d + cfg_.fix_map_origin;
        mapSliding(cfg_.fix_map_origin);
        inf_map_->mapSliding(cfg_.fix_map_origin);
    }

    writeMapInfoToLog(map_info_log_file_);
    map_info_log_file_.close();
    for (int i = 0; i < time_consuming_name_.size(); i++) {
        time_log_file_ << time_consuming_name_[i];
        if (i != time_consuming_name_.size() - 1) {
            time_log_file_ << ", ";
        }
    }
    time_log_file_ << endl;


    if (cfg_.load_pcd_en) {
        string pcd_path = cfg_.pcd_name;
        PointCloud::Ptr pcd_map(new PointCloud);
        if (pcl::io::loadPCDFile(pcd_path, *pcd_map) == -1) {
            cout << YELLOW << "Load pcd file at: ["<<cfg_.pcd_name<<"] failed!" << RESET << endl;
            exit(-1);
        }
        Pose cur_pose;
        cur_pose.first = Vec3f(0, 0, 0);
        updateOccPointCloud(*pcd_map);
        if(cfg_.esdf_en) {
            esdf_map_->updateESDF3D(robot_state_.p);
        }
        cout << BLUE << " -- [ROGMap]Load pcd file success with " << pcd_map->size() << " pts." << RESET << endl;
        map_empty_ = false;
    }

    publishCommittedSnapshot(0);
    if (immutable_snapshot_enabled_) {
        fmt::print(fg(fmt::color::green),
                   " -- [ROGMap] Immutable planner snapshot enabled "
                   "(fixed occupancy-only map).\n");
    }
    fmt::print(" -- [ROG_MAP_OCCUPIED_BOX_SCAN] fast={} compare={} immutable={} "
               "comparison_overhead={}\n",
               fastOccupiedBoxScanEnabled(), compareOccupiedBoxScanEnabled(),
               immutable_snapshot_enabled_,
               immutable_snapshot_enabled_ && fastOccupiedBoxScanEnabled() &&
                       compareOccupiedBoxScanEnabled());
    fmt::print(" -- [ROG_MAP_SNAPSHOT_LINE_QUERY] enabled={} immutable={} active={} "
               "changed_publication=reject\n",
               snapshotLineQueryEnabled(), immutable_snapshot_enabled_,
               immutable_snapshot_enabled_ && snapshotLineQueryEnabled());
    fmt::print(" -- [ROG_MAP_SNAPSHOT_NEIGHBOR_CACHE] enabled={} immutable={} "
               "line_query={} active={} entries=4096 max_neighbors=512 bytes_per_thread={} "
               "publication_check=required\n",
               snapshotNeighborCacheEnabled(), immutable_snapshot_enabled_,
               snapshotLineQueryEnabled(),
               immutable_snapshot_enabled_ && snapshotLineQueryEnabled() &&
                       snapshotNeighborCacheEnabled(),
               sizeof(snapshot_neighborhood_cache::Cache<>));
}

std::shared_ptr<const ROGMap::PublishedMapSnapshot> ROGMap::loadPublishedSnapshot() const {
    return std::atomic_load_explicit(&published_snapshot_, std::memory_order_acquire);
}

ROGMap::PlannerSnapshotDump ROGMap::capturePlannerSnapshotForDiagnostic() const {
    if (!immutable_snapshot_enabled_) return {};
    const auto snapshot = loadPublishedSnapshot();
    if (!snapshot) return {};
    return {snapshot->version, [snapshot](const std::string& path) {
        // v1 little-endian host format: magic, version, empty; then raw and
        // inflated grids (resolution, half-size, size, origin, bounds), then
        // occupied and known page words. No padding/struct-layout dependency.
        std::ofstream output(path, std::ios::binary);
        const auto scalar = [&](const auto& value) {
            output.write(reinterpret_cast<const char*>(&value), sizeof(value));
        };
        output.write("ROGDIAG1", 8);
        scalar(snapshot->version);
        scalar(std::uint64_t(snapshot->map_empty));
        for (const auto* grid : {&snapshot->probability, &snapshot->inflation}) {
            scalar(grid->resolution);
            for (const auto* indices : {&grid->half_size_i, &grid->size_i, &grid->origin_i})
                for (int i = 0; i < 3; ++i) scalar(std::int32_t((*indices)(i)));
            for (const auto* bounds : {&grid->bound_min_d, &grid->bound_max_d})
                for (int i = 0; i < 3; ++i) scalar((*bounds)(i));
            for (const auto* pages : {&grid->occupied_pages, &grid->known_pages}) {
                scalar(std::uint64_t(pages->size() * SNAPSHOT_PAGE_WORDS));
                for (const auto& page : *pages)
                    output.write(reinterpret_cast<const char*>(page->words.data()),
                                 page->words.size() * sizeof(std::uint64_t));
            }
        }
        output.flush();
        return output.good();
    }};
}

void ROGMap::snapshotPosToGlobalIndex(const Vec3f& pos, const double resolution, Vec3i& id_g) {
    id_g = (pos.array() / resolution).floor().cast<int>();
}

void ROGMap::snapshotGlobalIndexToPos(const Vec3i& id_g, const double resolution, Vec3f& pos) {
    pos = (id_g.cast<double>() + Vec3f::Constant(0.5)) * resolution;
}

bool ROGMap::snapshotInside(const SnapshotGrid& grid, const Vec3i& id_g) {
    return (((id_g - grid.origin_i).cwiseAbs() - grid.half_size_i).maxCoeff() <= 0);
}

int ROGMap::snapshotHash(const SnapshotGrid& grid, const Vec3i& id_g) {
    Vec3i id_l;
    for (int i = 0; i < 3; ++i) {
        id_l(i) = id_g(i) % grid.size_i(i);
        if (id_l(i) > grid.half_size_i(i)) {
            id_l(i) -= grid.size_i(i);
        }
        else if (id_l(i) < -grid.half_size_i(i)) {
            id_l(i) += grid.size_i(i);
        }
    }
    const Vec3i id = id_l + grid.half_size_i;
    return id(0) * grid.size_i(1) * grid.size_i(2) +
           id(1) * grid.size_i(2) + id(2);
}

bool ROGMap::snapshotBit(
        const std::vector<std::shared_ptr<const SnapshotBitPage>>& pages,
        const int hash_id) {
    const std::size_t word_id = static_cast<std::size_t>(hash_id) >> 6U;
    const std::size_t page_id = word_id / SNAPSHOT_PAGE_WORDS;
    const std::size_t page_word_id = word_id % SNAPSHOT_PAGE_WORDS;
    return (pages[page_id]->words[page_word_id] &
            (std::uint64_t{1} << (hash_id & 63))) != 0;
}

void ROGMap::setSnapshotBit(
                            std::vector<std::shared_ptr<const SnapshotBitPage>>& pages,
                            std::unordered_map<std::size_t, std::shared_ptr<SnapshotBitPage>>& mutable_pages,
                            const int hash_id,
                            const bool value) {
    const std::size_t word_id = static_cast<std::size_t>(hash_id) >> 6U;
    const std::size_t page_id = word_id / SNAPSHOT_PAGE_WORDS;
    const std::size_t page_word_id = word_id % SNAPSHOT_PAGE_WORDS;
    auto page_it = mutable_pages.find(page_id);
    if (page_it == mutable_pages.end()) {
        auto mutable_page = std::make_shared<SnapshotBitPage>(*pages[page_id]);
        pages[page_id] = mutable_page;
        page_it = mutable_pages.emplace(page_id, std::move(mutable_page)).first;
    }
    std::uint64_t& word = page_it->second->words[page_word_id];
    const std::uint64_t mask = std::uint64_t{1} << (hash_id & 63);
    if (value) {
        word |= mask;
    }
    else {
        word &= ~mask;
    }
}

void ROGMap::publishCommittedSnapshot(const std::uint64_t version) {
    const auto raw_dirty = consumeSnapshotDirtyHashes();
    const auto inf_dirty = inf_map_->consumeSnapshotDirtyHashes();
    if (!immutable_snapshot_enabled_) {
        return;
    }

    const auto previous = loadPublishedSnapshot();
    auto next = previous ? std::make_shared<PublishedMapSnapshot>(*previous)
                         : std::make_shared<PublishedMapSnapshot>();

    if (!previous) {
        next->probability.resolution = cfg_.resolution;
        next->probability.resolution_inv = 1.0 / cfg_.resolution;
        next->probability.half_size_i = cfg_.half_map_size_i;
        next->probability.size_i = 2 * cfg_.half_map_size_i + Vec3i::Ones();
        const std::size_t raw_voxels = static_cast<std::size_t>(next->probability.size_i.prod());
        const std::size_t raw_words = (raw_voxels + 63U) / 64U;
        const std::size_t raw_pages =
                (raw_words + SNAPSHOT_PAGE_WORDS - 1U) / SNAPSHOT_PAGE_WORDS;
        const auto zero_page = std::make_shared<const SnapshotBitPage>();
        next->probability.occupied_pages.assign(raw_pages, zero_page);
        next->probability.known_pages.assign(raw_pages, zero_page);

        next->inflation.resolution = cfg_.inflation_resolution;
        next->inflation.resolution_inv = 1.0 / cfg_.inflation_resolution;
        next->inflation.half_size_i = cfg_.inf_half_map_size_i;
        next->inflation.size_i = 2 * cfg_.inf_half_map_size_i + Vec3i::Ones();
        const std::size_t inf_voxels = static_cast<std::size_t>(next->inflation.size_i.prod());
        const std::size_t inf_words = (inf_voxels + 63U) / 64U;
        const std::size_t inf_pages =
                (inf_words + SNAPSHOT_PAGE_WORDS - 1U) / SNAPSHOT_PAGE_WORDS;
        next->inflation.occupied_pages.assign(inf_pages, zero_page);
    }

    next->probability.origin_i = local_map_origin_i_;
    next->probability.bound_min_d = local_map_bound_min_d_;
    next->probability.bound_max_d = local_map_bound_max_d_;
    snapshotPosToGlobalIndex(local_map_origin_d_, cfg_.inflation_resolution,
                             next->inflation.origin_i);
    next->inflation.bound_min_d = local_map_bound_min_d_;
    next->inflation.bound_max_d = local_map_bound_max_d_;

    std::unordered_map<std::size_t, std::shared_ptr<SnapshotBitPage>> raw_mutable_pages;
    std::unordered_map<std::size_t, std::shared_ptr<SnapshotBitPage>> raw_known_mutable_pages;
    std::unordered_map<std::size_t, std::shared_ptr<SnapshotBitPage>> inf_mutable_pages;
    // 2026-08-18: tried widening "known" into a neighbor splat here at
    // write time (once per dirty cell per scan, radius 3 and 6 both
    // tried), to move the coverage-density fix off the read path (see
    // isUnknown()'s own history below). Both were worse than the plain
    // read-side radius-3 neighbor search on the seed1-10 sweep (37-41/50
    // vs 42/50 waypoints, with brake attempts/rejections 3-5x higher) --
    // the vehicle keeps generating newly-free dirty cells throughout a
    // mission (not just at start), and splatting from each one scatters
    // writes across many distinct 32 KB snapshot pages, which
    // setSnapshotBit copy-on-write's in full on first touch each commit.
    // Reverted to no splat; isUnknown() does the neighbor search on read.
    for (const int hash_id : raw_dirty) {
        const double prob = static_cast<double>(occupancy_buffer_[hash_id]);
        setSnapshotBit(next->probability.occupied_pages, raw_mutable_pages, hash_id,
                       ProbMap::isOccupied(prob));
        // Resolved means the cell has left the unknown probability band --
        // it may still flip between occupied and confirmed-free later, but
        // it is no longer "never observed".
        setSnapshotBit(next->probability.known_pages, raw_known_mutable_pages, hash_id,
                       !ProbMap::isUnknown(prob));
        if (contact_trace::enabled()) {
            Vec3f position;
            hashIdToPos(hash_id, position);
            if (contact_trace::inRoi(position.x(), position.y(), position.z())) {
                try {
                    auto fields = contact_trace::stream();
                    fields << "\"map_version\":" << version
                           << ",\"hash_id\":" << hash_id
                           << ",\"position\":["
                           << contact_trace::number(position.x()) << ','
                           << contact_trace::number(position.y()) << ','
                           << contact_trace::number(position.z()) << ']'
                           << ",\"log_odds\":" << contact_trace::number(prob)
                           << ",\"occupied\":"
                           << (ProbMap::isOccupied(prob) ? "true" : "false")
                           << ",\"known\":"
                           << (!ProbMap::isUnknown(prob) ? "true" : "false");
                    contact_trace::submit("map_snapshot_raw_delta", fields.str());
                } catch (...) {
                }
            }
        }
    }
    for (const int hash_id : inf_dirty) {
        setSnapshotBit(next->inflation.occupied_pages, inf_mutable_pages, hash_id,
                       inf_map_->isOccupiedInflateHash(hash_id));
    }
    next->version = version;
    next->map_empty = map_empty_;
    std::shared_ptr<const PublishedMapSnapshot> immutable_next = next;
    std::atomic_store_explicit(&published_snapshot_, immutable_next, std::memory_order_release);
    if (contact_trace::enabled()) {
        try {
            auto fields = contact_trace::stream();
            fields << "\"map_version\":" << version
                   << ",\"raw_dirty\":" << raw_dirty.size()
                   << ",\"inflation_dirty\":" << inf_dirty.size()
                   << ",\"map_empty\":" << (map_empty_ ? "true" : "false");
            contact_trace::submit("map_snapshot_commit", fields.str());
        } catch (...) {
        }
    }
}

bool ROGMap::insideLocalMap(const Vec3f& pos) const {
    if (!immutable_snapshot_enabled_) {
        return ProbMap::insideLocalMap(pos);
    }
    const auto snapshot = loadPublishedSnapshot();
    Vec3i id_g;
    snapshotPosToGlobalIndex(pos, snapshot->probability.resolution, id_g);
    return snapshotInside(snapshot->probability, id_g);
}

bool ROGMap::insideLocalMap(const Vec3i& id_g) const {
    if (!immutable_snapshot_enabled_) {
        return ProbMap::insideLocalMap(id_g);
    }
    const auto snapshot = loadPublishedSnapshot();
    return snapshotInside(snapshot->probability, id_g);
}

bool ROGMap::isOccupied(const Vec3f& pos) const {
    if (!immutable_snapshot_enabled_) {
        return ProbMap::isOccupied(pos);
    }
    const auto snapshot = loadPublishedSnapshot();
    Vec3i id_g;
    snapshotPosToGlobalIndex(pos, snapshot->probability.resolution, id_g);
    if (!snapshotInside(snapshot->probability, id_g)) {
        return false;
    }
    if (pos.z() > cfg_.virtual_ceil_height || pos.z() < cfg_.virtual_ground_height) {
        return true;
    }
    return snapshotBit(snapshot->probability.occupied_pages,
                       snapshotHash(snapshot->probability, id_g));
}

bool ROGMap::isOccupied(const Vec3i& id_g) const {
    if (!immutable_snapshot_enabled_) {
        return ProbMap::isOccupied(id_g);
    }
    const auto snapshot = loadPublishedSnapshot();
    if (!snapshotInside(snapshot->probability, id_g)) {
        return false;
    }
    if (id_g.z() > sc_.virtual_ceil_height_id_g ||
        id_g.z() < sc_.virtual_ground_height_id_g + sc_.safe_margin_i) {
        return true;
    }
    return snapshotBit(snapshot->probability.occupied_pages,
                       snapshotHash(snapshot->probability, id_g));
}

bool ROGMap::isUnknown(const Vec3f& pos) const {
    if (!immutable_snapshot_enabled_) {
        return ProbMap::isUnknown(pos);
    }
    const auto snapshot = loadPublishedSnapshot();
    Vec3i id_g;
    snapshotPosToGlobalIndex(pos, snapshot->probability.resolution, id_g);
    if (!snapshotInside(snapshot->probability, id_g)) {
        return true;
    }
    if (pos.z() > cfg_.virtual_ceil_height || pos.z() < cfg_.virtual_ground_height) {
        return false;
    }
    // A single LiDAR return only marks a thin ray-line of raw cells as
    // observed (see raycastProcess's !raycasting_en branch), so at raw
    // resolution the cells immediately beside that line stay technically
    // unmarked even in well-swept open space. Treat the point as known if
    // any cell in a small neighborhood is, rather than requiring an exact
    // hit -- this is a coverage-density fix, not a safety-margin relaxation
    // (isOccupiedInflate's own inflation margin still applies separately).
    //
    // 2026-08-18: tried moving this widening to *write* time instead (a
    // splat in publishCommittedSnapshot, radius 3 and 6 both tried), to
    // avoid paying neighbor-search cost on every guard-validation sample.
    // Both write-side variants did WORSE on the seed1-10 sweep than this
    // plain read-side radius-3 search (37-41/50 waypoints vs 42/50, with
    // 3-5x more brake attempts/rejections) -- the vehicle keeps generating
    // newly-free dirty cells throughout a mission, not just at start, and
    // splatting from each one scatters writes across many distinct 32 KB
    // snapshot pages that get copy-on-write'd in full. This read-side
    // radius-3 search remains the best-performing configuration found so
    // far; a radius-6 read-side variant was also tried and was worse for
    // the same reason as the write-side one (more cost per guard-check
    // sample this time, not more touched pages).
    for (int dx = -kObservedNeighborRadiusCells; dx <= kObservedNeighborRadiusCells; ++dx) {
        for (int dy = -kObservedNeighborRadiusCells; dy <= kObservedNeighborRadiusCells; ++dy) {
            for (int dz = -kObservedNeighborRadiusCells; dz <= kObservedNeighborRadiusCells; ++dz) {
                const Vec3i neighbor_id_g = id_g + Vec3i(dx, dy, dz);
                if (!snapshotInside(snapshot->probability, neighbor_id_g)) {
                    continue;
                }
                if (snapshotBit(snapshot->probability.known_pages,
                                snapshotHash(snapshot->probability, neighbor_id_g))) {
                    return false;
                }
            }
        }
    }
    return true;
}

bool ROGMap::isKnownFree(const Vec3f& pos) const {
    if (!immutable_snapshot_enabled_) {
        return ProbMap::isKnownFree(pos);
    }
    return !isOccupied(pos) && !isUnknown(pos);
}

bool ROGMap::isOccupiedInflate(const Vec3f& pos) const {
    if (!immutable_snapshot_enabled_) {
        return ProbMap::isOccupiedInflate(pos);
    }
    const auto snapshot = loadPublishedSnapshot();
    Vec3i id_g;
    snapshotPosToGlobalIndex(pos, snapshot->inflation.resolution, id_g);
    if (!snapshotInside(snapshot->inflation, id_g)) {
        return false;
    }
    if (pos.z() > cfg_.virtual_ceil_height || pos.z() < cfg_.virtual_ground_height) {
        return true;
    }
    return snapshotBit(snapshot->inflation.occupied_pages,
                       snapshotHash(snapshot->inflation, id_g));
}

bool ROGMap::isUnknownInflate(const Vec3f& pos) const {
    if (!immutable_snapshot_enabled_) {
        return ProbMap::isUnknownInflate(pos);
    }
    // Unlike the raw-resolution grid (see isUnknown()), the inflation grid's
    // snapshot only carries an occupied bit, not a known/unknown one, so
    // this still can't distinguish "confirmed free" from "never observed"
    // at inflated resolution. Callers that need that distinction should use
    // isUnknown() on the raw grid instead.
    (void) pos;
    return false;
}

bool ROGMap::isKnownFreeInflate(const Vec3f& pos) const {
    if (!immutable_snapshot_enabled_) {
        return ProbMap::isKnownFreeInflate(pos);
    }
    return !isOccupiedInflate(pos);
}

GridType ROGMap::getGridType(Vec3i& id_g) const {
    if (!immutable_snapshot_enabled_) {
        return ProbMap::getGridType(id_g);
    }
    if (id_g.z() <= sc_.virtual_ground_height_id_g ||
        id_g.z() >= sc_.virtual_ceil_height_id_g - sc_.safe_margin_i) {
        return OCCUPIED;
    }
    if (!insideLocalMap(id_g)) {
        return OUT_OF_MAP;
    }
    return isOccupied(id_g) ? OCCUPIED : UNKNOWN;
}

GridType ROGMap::getGridType(const Vec3f& pos) const {
    if (!immutable_snapshot_enabled_) {
        return ProbMap::getGridType(pos);
    }
    if (pos.z() <= cfg_.virtual_ground_height || pos.z() >= cfg_.virtual_ceil_height) {
        return OCCUPIED;
    }
    if (!insideLocalMap(pos)) {
        return OUT_OF_MAP;
    }
    return isOccupied(pos) ? OCCUPIED : UNKNOWN;
}

GridType ROGMap::getInfGridType(const Vec3f& pos) const {
    if (!immutable_snapshot_enabled_) {
        return ProbMap::getInfGridType(pos);
    }
    if (!insideLocalMap(pos)) {
        return OUT_OF_MAP;
    }
    if (pos.z() >= cfg_.virtual_ceil_height -
                   cfg_.inflation_resolution * (1 + cfg_.inflation_step) ||
        pos.z() <= cfg_.virtual_ground_height +
                   cfg_.inflation_resolution * (1 + cfg_.inflation_step)) {
        return OCCUPIED;
    }
    return isOccupiedInflate(pos) ? OCCUPIED : KNOWN_FREE;
}

void ROGMap::boundBoxByLocalMap(Vec3f& box_min, Vec3f& box_max) const {
    if (!immutable_snapshot_enabled_) {
        ProbMap::boundBoxByLocalMap(box_min, box_max);
        return;
    }
    if ((box_max - box_min).minCoeff() <= 0) {
        box_min = box_max;
        return;
    }
    const auto snapshot = loadPublishedSnapshot();
    box_min = box_min.cwiseMax(snapshot->probability.bound_min_d);
    box_max = box_max.cwiseMin(snapshot->probability.bound_max_d);
    box_max.z() = std::min(box_max.z(), cfg_.virtual_ceil_height);
    box_min.z() = std::max(box_min.z(), cfg_.virtual_ground_height);
}

void ROGMap::boxSearch(const Vec3f& input_min, const Vec3f& input_max,
                       const GridType& gt, vec_E<Vec3f>& out_points) const {
    if (!immutable_snapshot_enabled_) {
        ProbMap::boxSearch(input_min, input_max, gt, out_points);
        return;
    }
    out_points.clear();
    const auto snapshot = loadPublishedSnapshot();
    if (snapshot->map_empty || gt == FRONTIER) {
        return;
    }
    Vec3f box_min = input_min;
    Vec3f box_max = input_max;
    boundBoxByLocalMap(box_min, box_max);
    if ((box_max - box_min).minCoeff() <= 0) {
        return;
    }
    Vec3i min_id, max_id;
    snapshotPosToGlobalIndex(box_min, snapshot->probability.resolution, min_id);
    snapshotPosToGlobalIndex(box_max, snapshot->probability.resolution, max_id);
    if (gt == OCCUPIED && fastOccupiedBoxScanEnabled()) {
        const auto &grid = snapshot->probability;
        const occupied_box_scan::Index begin{{min_id.x() + 1,
                                              min_id.y() + 1,
                                              min_id.z() + 1}};
        const occupied_box_scan::Index end{{max_id.x(), max_id.y(), max_id.z()}};
        const occupied_box_scan::Index size{{grid.size_i.x(), grid.size_i.y(),
                                             grid.size_i.z()}};
        const occupied_box_scan::Index half{{grid.half_size_i.x(),
                                             grid.half_size_i.y(),
                                             grid.half_size_i.z()}};
        occupied_box_scan::forEachOccupied(
                begin, end, size, half,
                [&grid](const std::size_t word_id) {
                    return grid.occupied_pages[word_id / SNAPSHOT_PAGE_WORDS]
                            ->words[word_id % SNAPSHOT_PAGE_WORDS];
                },
                [&grid, &out_points](const int i, const int j, const int k) {
                    const Vec3i id_g(i, j, k);
                    Vec3f pos;
                    snapshotGlobalIndexToPos(id_g, grid.resolution, pos);
                    out_points.push_back(pos);
                });
        if (compareOccupiedBoxScanEnabled()) {
            // Diagnostic only: both loops consume the SAME captured snapshot
            // and the SAME once-computed bounds. Do not call boxSearch again:
            // that would acquire a different snapshot. The original bounding
            // helper's independent snapshot load above remains unchanged.
            vec_E<Vec3f> baseline_points;
            for (int i = min_id.x() + 1; i < max_id.x(); ++i) {
                for (int j = min_id.y() + 1; j < max_id.y(); ++j) {
                    for (int k = min_id.z() + 1; k < max_id.z(); ++k) {
                        const Vec3i id_g(i, j, k);
                        if (snapshotBit(grid.occupied_pages,
                                        snapshotHash(grid, id_g))) {
                            Vec3f pos;
                            snapshotGlobalIndexToPos(id_g, grid.resolution, pos);
                            baseline_points.push_back(pos);
                        }
                    }
                }
            }
            const std::size_t common_size = std::min(out_points.size(),
                                                      baseline_points.size());
            std::size_t first_difference = 0;
            while (first_difference < common_size &&
                   std::memcmp(out_points[first_difference].data(),
                               baseline_points[first_difference].data(),
                               3 * sizeof(double)) == 0) {
                ++first_difference;
            }
            const bool equal = out_points.size() == baseline_points.size() &&
                               first_difference == common_size;
            static std::atomic_uint64_t comparison_checks{0};
            static std::atomic_uint64_t comparison_mismatches{0};
            if (!equal) {
                comparison_mismatches.fetch_add(1, std::memory_order_relaxed);
                const Vec3f unavailable = Vec3f::Constant(
                        std::numeric_limits<double>::quiet_NaN());
                const Vec3f fast_point = first_difference < out_points.size()
                        ? out_points[first_difference] : unavailable;
                const Vec3f baseline_point = first_difference < baseline_points.size()
                        ? baseline_points[first_difference] : unavailable;
                fmt::print(" -- [ROG_MAP_OCCUPIED_BOX_SCAN_MISMATCH] map={} "
                           "fast_points={} baseline_points={} first_difference={} "
                           "input_min=[{},{},{}] input_max=[{},{},{}] "
                           "begin=[{},{},{}] end=[{},{},{}] "
                           "fast=[{},{},{}] baseline=[{},{},{}] "
                           "action=return_baseline candidate_rejected=true\n",
                           snapshot->version, out_points.size(), baseline_points.size(),
                           first_difference, input_min.x(), input_min.y(), input_min.z(),
                           input_max.x(), input_max.y(), input_max.z(),
                           begin[0], begin[1], begin[2], end[0], end[1], end[2],
                           fast_point.x(), fast_point.y(), fast_point.z(),
                           baseline_point.x(), baseline_point.y(), baseline_point.z());
                out_points.swap(baseline_points);
            }
            const auto checks = comparison_checks.fetch_add(
                    1, std::memory_order_relaxed) + 1;
            if (checks == 1 || checks % 256 == 0 || !equal) {
                fmt::print(" -- [ROG_MAP_OCCUPIED_BOX_SCAN_COMPARE] checks={} "
                           "mismatches={} map={} comparison_overhead=true "
                           "cpu_candidate=false\n",
                           checks, comparison_mismatches.load(std::memory_order_relaxed),
                           snapshot->version);
            }
        }
        return;
    }
    for (int i = min_id.x() + 1; i < max_id.x(); ++i) {
        for (int j = min_id.y() + 1; j < max_id.y(); ++j) {
            for (int k = min_id.z() + 1; k < max_id.z(); ++k) {
                const Vec3i id_g(i, j, k);
                const bool occupied = snapshotBit(snapshot->probability.occupied_pages,
                                                  snapshotHash(snapshot->probability, id_g));
                if ((gt == OCCUPIED && occupied) || (gt == UNKNOWN && !occupied)) {
                    Vec3f pos;
                    snapshotGlobalIndexToPos(id_g, snapshot->probability.resolution, pos);
                    out_points.push_back(pos);
                }
            }
        }
    }
}

void ROGMap::boxSearchInflate(const Vec3f& box_min, const Vec3f& box_max,
                              const GridType& gt, vec_E<Vec3f>& out_points) const {
    if (!immutable_snapshot_enabled_) {
        ProbMap::boxSearchInflate(box_min, box_max, gt, out_points);
        return;
    }
    out_points.clear();
    if (gt != OCCUPIED) {
        return;
    }
    const auto snapshot = loadPublishedSnapshot();
    Vec3i min_id, max_id;
    snapshotPosToGlobalIndex(box_min, snapshot->inflation.resolution, min_id);
    snapshotPosToGlobalIndex(box_max, snapshot->inflation.resolution, max_id);
    for (int i = min_id.x(); i <= max_id.x(); ++i) {
        for (int j = min_id.y(); j <= max_id.y(); ++j) {
            for (int k = min_id.z(); k <= max_id.z(); ++k) {
                const Vec3i id_g(i, j, k);
                if (!snapshotInside(snapshot->inflation, id_g)) {
                    continue;
                }
                if (snapshotBit(snapshot->inflation.occupied_pages,
                                snapshotHash(snapshot->inflation, id_g))) {
                    Vec3f pos;
                    snapshotGlobalIndexToPos(id_g, snapshot->inflation.resolution, pos);
                    out_points.push_back(pos);
                }
            }
        }
    }
}

bool ROGMap::publishedMapEmpty() const {
    if (!immutable_snapshot_enabled_) {
        return map_empty_;
    }
    const auto snapshot = loadPublishedSnapshot();
    return !snapshot || snapshot->map_empty;
}

bool ROGMap::findNearestCellThat(const bool & is, const GridType& target_type,
    const Vec3f & start_pos, Vec3f& nearest_pt, const double & max_dis) const {

    Vec3i start_id;
    posToGlobalIndex(start_pos, start_id);
    nearest_pt.setConstant(NAN);


    for(const auto & nei_id: cfg_.spherical_neighbor) {
        const Vec3i q_id =start_id + nei_id;
        Vec3f q_pos;
        globalIndexToPos(q_id, q_pos);
        if((q_pos - start_pos).norm() > max_dis) {
            return false;
        }

        if((getGridType(q_pos) == target_type) == is) {
            nearest_pt = q_pos;
            return true;
        }
    }

   return false;
}

bool ROGMap::findNearestInfCellThat(const bool & is, const GridType& target_type,
    const Vec3f & start_pos, Vec3f& nearest_pt, const double & max_dis) const {

    Vec3i start_id;
    posToGlobalIndex(start_pos, start_id);
    nearest_pt.setConstant(NAN);


    for(const auto & nei_id: cfg_.spherical_neighbor) {
        const Vec3i q_id = start_id + nei_id;
        Vec3f q_pos;
        globalIndexToPos(q_id, q_pos);
        if((q_pos - start_pos).norm() > max_dis) {
            return false;
        }

        if((getInfGridType(q_pos) == target_type) == is) {
            nearest_pt = q_pos;
            return true;
        }
    }
    fmt::print(fg(fmt::color::yellow), " -- [ROGMap] findNearestInfCellThat failed to find all {} neighbors at start_pos: {}, target_type: {}, is: {}\n",
               cfg_.spherical_neighbor.size(), start_pos.transpose(), target_type, is);
    return false;
}


bool ROGMap::isLineFree(const rog_map::Vec3f& start_pt, const rog_map::Vec3f& end_pt,
                        const bool& use_inf_map, const bool& use_unk_as_occ) const {
    if (start_pt.array().isNaN().any() || end_pt.array().isNaN().any()) {
        cout << YELLOW << " -- [ROGMap] Call isLineFree with NaN in start or end pt, return false." << RESET << endl;
        return false;
    }
    raycaster::RayCaster raycaster;
    if (use_inf_map) {
        raycaster.setResolution(cfg_.inflation_resolution);
    }
    else {
        raycaster.setResolution(cfg_.resolution);
    }
    Vec3f ray_pt;
    raycaster.setInput(start_pt, end_pt);
    while (raycaster.step(ray_pt)) {
        if (!use_unk_as_occ) {
            // allow both unk and free
            if (use_inf_map) {
                if (isOccupiedInflate(ray_pt)) {
                    return false;
                }
            }
            else {
                if (isOccupied(ray_pt)) {
                    return false;
                }
            }
        }
        else {
            // only allow known free
            if (use_inf_map) {
                if ((isUnknownInflate(ray_pt) || isOccupiedInflate(ray_pt)))
                    return false;
            }
            else {
                if (!isKnownFree(ray_pt)) {
                    return false;
                }
            }
        }
    }
    return true;
}

bool ROGMap::isLineFree(const Vec3f& start_pt, const Vec3f& end_pt, const double& max_dis,
                        const vec_Vec3i& neighbor_list) const {
    if (immutable_snapshot_enabled_ && snapshotLineQueryEnabled()) {
        // Pin exactly one immutable publication for this line. The individual
        // float/integer predicates below deliberately preserve their different
        // index conversions and virtual-boundary rules from isOccupied().
        const auto snapshot = loadPublishedSnapshot();
        if (!snapshot) {
            return false;
        }
        raycaster::RayCaster raycaster;
        raycaster.setResolution(cfg_.resolution);
        raycaster.setInput(start_pt, end_pt);
        auto float_occupied = [&](const Vec3f& point) {
            Vec3i id_g;
            snapshotPosToGlobalIndex(point, snapshot->probability.resolution, id_g);
            if (!snapshotInside(snapshot->probability, id_g)) {
                return false;
            }
            if (point.z() > cfg_.virtual_ceil_height ||
                point.z() < cfg_.virtual_ground_height) {
                return true;
            }
            return snapshotBit(snapshot->probability.occupied_pages,
                               snapshotHash(snapshot->probability, id_g));
        };
        auto point_to_index = [&](const Vec3f& point) -> Vec3i {
            Vec3i id_g;
            posToGlobalIndex(point, id_g);
            return id_g;
        };
        auto integer_occupied = [&](const Vec3i& id_g) {
            if (!snapshotInside(snapshot->probability, id_g)) {
                return false;
            }
            if (id_g.z() > sc_.virtual_ceil_height_id_g ||
                id_g.z() < sc_.virtual_ground_height_id_g + sc_.safe_margin_i) {
                return true;
            }
            return snapshotBit(snapshot->probability.occupied_pages,
                               snapshotHash(snapshot->probability, id_g));
        };
        auto still_current = [&] {
            // A newer publication invalidates an otherwise-free result.
            // This is intentionally conservative, and never a long cache.
            const auto current = loadPublishedSnapshot();
            return current && current.get() == snapshot.get() &&
                   current->version == snapshot->version;
        };
        if (snapshotNeighborCacheEnabled() && !neighbor_list.empty()) {
            // Bounded, thread-confined memoization of this pure integer
            // neighborhood predicate. Context identity includes weak ownership
            // plus version and the full neighbor contents, never their address
            // alone. No obsolete snapshot pages are kept alive across lines.
            static thread_local snapshot_neighborhood_cache::Cache<> cache;
            const snapshot_neighborhood_cache::PredicateIdentity identity{
                this, sc_.virtual_ground_height_id_g, sc_.virtual_ceil_height_id_g,
                sc_.safe_margin_i};
            cache.beginLine(snapshot, snapshot->version, identity, neighbor_list);
            auto neighborhood_occupied = [&](const Vec3i& center) {
                const snapshot_neighborhood_cache::Index key{center.x(), center.y(), center.z()};
                return cache.anyOccupied(key, [&] {
                    for (const auto& neighbor : neighbor_list) {
                        const Vec3i shifted = center + neighbor;
                        if (integer_occupied(shifted)) {
                            return true;
                        }
                    }
                    return false;
                });
            };
            return snapshot_neighborhood_cache::isLineFree(
                raycaster, start_pt, max_dis, true, float_occupied, point_to_index,
                neighborhood_occupied, still_current);
        }
        return snapshot_line_query::isLineFree(
            raycaster, start_pt, max_dis, neighbor_list, float_occupied,
            point_to_index, integer_occupied, still_current);
    }
    raycaster::RayCaster raycaster;
    raycaster.setResolution(cfg_.resolution);
    Vec3f ray_pt;
    raycaster.setInput(start_pt, end_pt);
    while (raycaster.step(ray_pt)) {
        if (max_dis > 0 && (ray_pt - start_pt).norm() > max_dis) {
            return false;
        }

        if (neighbor_list.empty()) {
            if (isOccupied(ray_pt)) {
                return false;
            }
        }
        else {
            Vec3i ray_pt_id_g;
            posToGlobalIndex(ray_pt, ray_pt_id_g);
            for (const auto& nei : neighbor_list) {
                Vec3i shift_tmp = ray_pt_id_g + nei;
                if (isOccupied(shift_tmp)) {
                    return false;
                }
            }
        }
    }
    return true;
}

bool ROGMap::isLineFree(const Vec3f& start_pt, const Vec3f& end_pt, Vec3f& free_local_goal, const double& max_dis,
                        const vec_Vec3i& neighbor_list) const {
    raycaster::RayCaster raycaster;
    raycaster.setResolution(cfg_.resolution);
    Vec3f ray_pt;
    raycaster.setInput(start_pt, end_pt);
    free_local_goal = start_pt;
    while (raycaster.step(ray_pt)) {
        free_local_goal = ray_pt;
        if (max_dis > 0 && (ray_pt - start_pt).norm() > max_dis) {
            return false;
        }

        if (neighbor_list.empty()) {
            if (isOccupied(ray_pt)) {
                return false;
            }
        }
        else {
            Vec3i ray_pt_id_g;
            posToGlobalIndex(ray_pt, ray_pt_id_g);
            for (const auto& nei : neighbor_list) {
                Vec3i shift_tmp = ray_pt_id_g + nei;
                if (isOccupied(shift_tmp)) {
                    return false;
                }
            }
        }
    }
    free_local_goal = end_pt;
    return true;
}

void ROGMap::updateMap(const PointCloud& cloud, const Pose& pose) {
    TimeConsuming ssss("updateMap", true);
    if (cfg_.ros_callback_en) {
        std::cout << YELLOW << "ROS callback is enabled, can not insert map from updateMap API." << RESET
            << std::endl;
        return;
    }

    if (cloud.empty()) {
        static int local_cnt = 0;
        if (local_cnt++ > 100) {
            cout << YELLOW << "No cloud input, please check the input topic." << RESET << endl;
            local_cnt = 0;
        }
        return;
    }

    updateRobotState(pose);
    auto map_write_transaction = acquireMapWriteTransaction();
    const auto result = updateProbMap(cloud, pose);
    if (result.map_committed) {
        const auto snapshot = loadPublishedSnapshot();
        publishCommittedSnapshot(snapshot ? snapshot->version + 1 : 1);
    }


    writeTimeConsumingToLog(time_log_file_);
}

RobotState ROGMap::getRobotState() const {
    std::lock_guard<std::mutex> lock(robot_state_mutex_);
    return robot_state_;
}

void ROGMap::updateRobotState(const Pose& pose) {
    const double receive_time = getSystemWalltimeNow();
    const double yaw = get_yaw_from_quaternion<double>(pose.second);
    {
        std::lock_guard<std::mutex> lock(robot_state_mutex_);
        robot_state_.p = pose.first;
        robot_state_.q = pose.second;
        robot_state_.rcv_time = receive_time;
        robot_state_.rcv = true;
        robot_state_.yaw = yaw;
    }
    updateLocalBox(pose.first);
}

MapHealthSnapshot ROGMap::getMapHealthSnapshot() const {
    std::lock_guard<std::mutex> lock(map_health_mutex_);
    MapHealthSnapshot health = map_health_;
    if (immutable_snapshot_enabled_) {
        const auto snapshot = loadPublishedSnapshot();
        if (snapshot) {
            health.map_version = snapshot->version;
        }
    }
    return health;
}

std::uint64_t ROGMap::recordAcceptedScan(const MapHealthClock::time_point rx_time,
                                         const std::int64_t source_stamp_ns) {
    std::lock_guard<std::mutex> lock(map_health_mutex_);
    if (map_health_.accepted_scan_count == 0) {
        map_health_.first_accepted_scan_time = rx_time;
    }
    ++map_health_.accepted_scan_count;
    map_health_.latest_accepted_scan_seq = map_health_.accepted_scan_count;
    map_health_.latest_accepted_scan_time = rx_time;
    map_health_.latest_source_stamp_ns = source_stamp_ns;
    return map_health_.latest_accepted_scan_seq;
}

void ROGMap::recordDroppedScan() {
    std::lock_guard<std::mutex> lock(map_health_mutex_);
    ++map_health_.dropped_scan_count;
}

void ROGMap::recordMapUpdateStarted() {
    std::lock_guard<std::mutex> lock(map_health_mutex_);
    map_health_.update_in_progress = true;
}

void ROGMap::recordCommittedNoopScan(
        const std::uint64_t scan_seq,
        const std::int64_t source_stamp_ns,
        const MapHealthClock::time_point scan_rx_time) {
    const auto commit_time = MapHealthClock::now();
    std::lock_guard<std::mutex> lock(map_health_mutex_);
    ++map_health_.processed_scan_count;
    ++map_health_.committed_scan_count;
    map_health_.latest_processed_scan_rx_time = scan_rx_time;
    map_health_.latest_scan_process_time = commit_time;
    map_health_.latest_processed_source_stamp_ns = source_stamp_ns;
    map_health_.latest_committed_scan_seq = scan_seq;
    map_health_.latest_committed_scan_rx_time = scan_rx_time;
    map_health_.latest_map_commit_time = commit_time;
    map_health_.latest_committed_source_stamp_ns = source_stamp_ns;
}

void ROGMap::recordMapUpdateFinished(const std::uint64_t scan_seq,
                                     const std::int64_t source_stamp_ns,
                                     const MapHealthClock::time_point scan_rx_time,
                                     const ProbMapUpdateResult& result) {
    const auto commit_time = MapHealthClock::now();
    std::uint64_t committed_version{0};
    if (result.map_committed) {
        {
            std::lock_guard<std::mutex> lock(map_health_mutex_);
            committed_version = map_health_.map_version + 1;
        }
        publishCommittedSnapshot(committed_version);
    }
    std::lock_guard<std::mutex> lock(map_health_mutex_);
    if (result.scan_processed) {
        ++map_health_.processed_scan_count;
        map_health_.latest_processed_scan_rx_time = scan_rx_time;
        map_health_.latest_scan_process_time = commit_time;
        map_health_.latest_processed_source_stamp_ns = source_stamp_ns;
    }
    if (result.map_committed) {
        ++map_health_.committed_scan_count;
        map_health_.map_version = committed_version;
        map_health_.latest_committed_scan_seq = scan_seq;
        map_health_.latest_committed_scan_rx_time = scan_rx_time;
        map_health_.latest_map_commit_time = commit_time;
        map_health_.latest_committed_source_stamp_ns = source_stamp_ns;
    }
    map_health_.update_in_progress = false;
}
