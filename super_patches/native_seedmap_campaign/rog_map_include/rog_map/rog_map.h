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

#pragma once

#include <chrono>
#include <array>
#include <atomic>
#include <cstdint>
#include <mutex>
#include <memory>
#include <optional>
#include <shared_mutex>
#include <thread>
#include <unordered_map>
#include <vector>

#include <rog_map/prob_map.h>
#include <rog_map/rog_map_core/common_lib.hpp>
#include <super_utils/type_utils.hpp>
#include <fmt/color.h>

namespace rog_map {
    using namespace std;
    using super_utils::vec_Vec3i;
    using super_utils::RobotState;

    typedef pcl::PointXYZI PointType;
    typedef pcl::PointCloud<PointType> PointCloudXYZIN;

    using MapHealthClock = std::chrono::steady_clock;

    struct MapHealthSnapshot {
        std::uint64_t accepted_scan_count{0};
        std::uint64_t processed_scan_count{0};
        std::uint64_t committed_scan_count{0};
        std::uint64_t map_version{0};
        std::uint64_t latest_accepted_scan_seq{0};
        std::uint64_t latest_committed_scan_seq{0};
        std::uint64_t dropped_scan_count{0};
        MapHealthClock::time_point first_accepted_scan_time{};
        MapHealthClock::time_point latest_accepted_scan_time{};
        MapHealthClock::time_point latest_processed_scan_rx_time{};
        MapHealthClock::time_point latest_scan_process_time{};
        MapHealthClock::time_point latest_committed_scan_rx_time{};
        MapHealthClock::time_point latest_map_commit_time{};
        std::int64_t latest_source_stamp_ns{0};
        bool update_in_progress{false};
    };

    class ROGMap : public ProbMap {
        const bool IS = true;
        const bool NOT = false;

        virtual const double getSystemWalltimeNow() = 0;

    public:
        EIGEN_MAKE_ALIGNED_OPERATOR_NEW

        class MapReadTransaction {
        public:
            MapReadTransaction() = default;
            explicit MapReadTransaction(std::shared_mutex& mutex) : lock_(std::in_place, mutex) {}
            MapReadTransaction(MapReadTransaction&&) noexcept = default;
            MapReadTransaction& operator=(MapReadTransaction&&) noexcept = default;
            MapReadTransaction(const MapReadTransaction&) = delete;
            MapReadTransaction& operator=(const MapReadTransaction&) = delete;

            void unlock() {
                if (lock_ && lock_->owns_lock()) {
                    lock_->unlock();
                }
            }

        private:
            std::optional<std::shared_lock<std::shared_mutex>> lock_;
        };
        using MapWriteTransaction = std::unique_lock<std::shared_mutex>;

        explicit ROGMap() = default;

        void init();

        ~ROGMap() override = default;

        const rog_map::Config &getMapConfig() const {
            return cfg_;
        }

        // Fixed, occupancy-only maps publish compact immutable bitsets.  All
        // planner queries below then read one atomic snapshot and never block
        // the cloud writer. Other ROG-Map modes retain the original lock path.
        bool immutablePlannerSnapshotEnabled() const {
            return immutable_snapshot_enabled_;
        }

        bool insideLocalMap(const Vec3f& pos) const;

        bool insideLocalMap(const Vec3i& id_g) const;

        bool isOccupied(const Vec3f& pos) const;

        bool isOccupied(const Vec3i& id_g) const;

        bool isUnknown(const Vec3f& pos) const;

        bool isKnownFree(const Vec3f& pos) const;

        bool isOccupiedInflate(const Vec3f& pos) const;

        bool isUnknownInflate(const Vec3f& pos) const;

        bool isKnownFreeInflate(const Vec3f& pos) const;

        GridType getGridType(Vec3i& id_g) const;

        GridType getGridType(const Vec3f& pos) const;

        GridType getInfGridType(const Vec3f& pos) const;

        void boxSearch(const Vec3f& box_min, const Vec3f& box_max,
                       const GridType& gt, vec_E<Vec3f>& out_points) const;

        void boxSearchInflate(const Vec3f& box_min, const Vec3f& box_max,
                              const GridType& gt, vec_E<Vec3f>& out_points) const;

        void boundBoxByLocalMap(Vec3f& box_min, Vec3f& box_max) const;

        bool publishedMapEmpty() const;


        bool isLineFree(const Vec3f& start_pt, const Vec3f& end_pt,
                        const double& max_dis = 999999,
                        const vec_Vec3i& neighbor_list = vec_Vec3i{}) const;

        bool isLineFree(const Vec3f& start_pt, const Vec3f& end_pt,
                        Vec3f& free_local_goal, const double& max_dis = 999999,
                        const vec_Vec3i& neighbor_list = vec_Vec3i{}) const;

        bool isLineFree(const Vec3f& start_pt, const Vec3f& end_pt,
                        const bool& use_inf_map = false,
                        const bool& use_unk_as_occ = false) const;

        bool getNearestCellIs(const GridType& target_type,
                                const Vec3f& start_pos,
                                Vec3f& nearest_pt, const double& max_dis) const {
            return findNearestCellThat(IS, target_type, start_pos, nearest_pt, max_dis);
        }

        bool getNearestCellNot(const GridType& target_type,
                             const Vec3f& start_pos,
                             Vec3f& nearest_pt, const double& max_dis) const {
            return findNearestCellThat(NOT, target_type, start_pos, nearest_pt, max_dis);
        }

        bool getNearestInfCellIs(const GridType& target_type,
                           const Vec3f& start_pos,
                           Vec3f& nearest_pt, const double& max_dis) const {
            return findNearestInfCellThat(IS, target_type, start_pos, nearest_pt, max_dis);
        }

        bool getNearestInfCellNot(const GridType& target_type,
                             const Vec3f& start_pos,
                             Vec3f& nearest_pt, const double& max_dis) const {
            return findNearestInfCellThat(NOT, target_type, start_pos, nearest_pt, max_dis);
        }

        void probMapPosToGlobalIndex(const Vec3f & pos, Vec3i & id_g) const {
            snapshotPosToGlobalIndex(pos, cfg_.resolution, id_g);
        }

        void probMapGlobalIndexToPos(const Vec3i & id_g, Vec3f & pos) const {
            snapshotGlobalIndexToPos(id_g, cfg_.resolution, pos);
        }

        void infMapPosToGlobalIndex(const Vec3f & pos, Vec3i & id_g) const {
            snapshotPosToGlobalIndex(pos, cfg_.inflation_resolution, id_g);
        }

        void infMapGlobalIndexToPos(const Vec3i & id_g, Vec3f & pos) const {
            snapshotGlobalIndexToPos(id_g, cfg_.inflation_resolution, pos);
        }


        void updateMap(const PointCloud& cloud, const Pose& pose);

        RobotState getRobotState() const;

        MapHealthSnapshot getMapHealthSnapshot() const;

        // Keep all map queries in one validation pass on the same committed
        // occupancy state. Map writers take the matching exclusive lock.
        MapReadTransaction acquireMapReadTransaction() const {
            if (immutable_snapshot_enabled_) {
                return MapReadTransaction{};
            }
            // std::shared_mutex does not guarantee writer preference. Without
            // this gate, high-rate replans can continuously reacquire shared
            // ownership and starve map commits until the guard declares the
            // map stale.
            for (;;) {
                while (map_write_pending_.load(std::memory_order_acquire)) {
                    std::this_thread::yield();
                }
                MapReadTransaction transaction(map_data_mutex_);
                if (!map_write_pending_.load(std::memory_order_acquire)) {
                    return transaction;
                }
                transaction.unlock();
            }
        }

    protected:

        std::ofstream time_log_file_, map_info_log_file_;

        void updateRobotState(const Pose& pose);

        std::uint64_t recordAcceptedScan(MapHealthClock::time_point rx_time,
                                         std::int64_t source_stamp_ns);

        void recordDroppedScan();

        void recordMapUpdateStarted();

        void recordMapUpdateFinished(std::uint64_t scan_seq,
                                     MapHealthClock::time_point scan_rx_time,
                                     const ProbMapUpdateResult& result);

        void publishCommittedSnapshot(std::uint64_t version);

        MapWriteTransaction acquireMapWriteTransaction() {
            if (immutable_snapshot_enabled_) {
                return MapWriteTransaction(map_data_mutex_);
            }
            map_write_pending_.store(true, std::memory_order_release);
            MapWriteTransaction transaction(map_data_mutex_);
            map_write_pending_.store(false, std::memory_order_release);
            return transaction;
        }

        bool findNearestCellThat(const bool & is, const GridType& target_type,
            const Vec3f & start_pos, Vec3f& nearest_pt, const double & max_dis) const ;

        bool findNearestInfCellThat(const bool & is, const GridType& target_type,
          const Vec3f & start_pos, Vec3f& nearest_pt, const double & max_dis) const ;

        mutable std::mutex robot_state_mutex_;
        RobotState robot_state_;

        mutable std::mutex map_health_mutex_;
        MapHealthSnapshot map_health_;

        mutable std::shared_mutex map_data_mutex_;
        mutable std::atomic_bool map_write_pending_{false};

        static constexpr std::size_t SNAPSHOT_PAGE_WORDS = 4096;

        struct SnapshotBitPage {
            std::array<std::uint64_t, SNAPSHOT_PAGE_WORDS> words{};
        };

        struct SnapshotGrid {
            double resolution{0.0};
            double resolution_inv{0.0};
            Vec3i half_size_i{Vec3i::Zero()};
            Vec3i size_i{Vec3i::Zero()};
            Vec3i origin_i{Vec3i::Zero()};
            Vec3f bound_min_d{Vec3f::Zero()};
            Vec3f bound_max_d{Vec3f::Zero()};
            std::vector<std::shared_ptr<const SnapshotBitPage>> occupied_pages;
            // Set once a cell's probability has left the unknown band (i.e. it
            // is either occupied or confirmed free). Unset means the cell has
            // never been resolved either way -- distinct from confirmed-free.
            // Only populated for `probability` (raw-resolution); `inflation`
            // does not carry this bit.
            std::vector<std::shared_ptr<const SnapshotBitPage>> known_pages;
        };

        struct PublishedMapSnapshot {
            SnapshotGrid probability;
            SnapshotGrid inflation;
            std::uint64_t version{0};
            bool map_empty{true};
        };

        bool immutable_snapshot_enabled_{false};
        std::shared_ptr<const PublishedMapSnapshot> published_snapshot_;

        std::shared_ptr<const PublishedMapSnapshot> loadPublishedSnapshot() const;
        static void snapshotPosToGlobalIndex(const Vec3f& pos, double resolution, Vec3i& id_g);
        static void snapshotGlobalIndexToPos(const Vec3i& id_g, double resolution, Vec3f& pos);
        static int snapshotHash(const SnapshotGrid& grid, const Vec3i& id_g);
        static bool snapshotInside(const SnapshotGrid& grid, const Vec3i& id_g);
        static bool snapshotBit(
                const std::vector<std::shared_ptr<const SnapshotBitPage>>& pages,
                int hash_id);
        static void setSnapshotBit(
                std::vector<std::shared_ptr<const SnapshotBitPage>>& pages,
                std::unordered_map<std::size_t, std::shared_ptr<SnapshotBitPage>>& mutable_pages,
                int hash_id,
                bool value);
    };
}
