#pragma once

#include <condition_variable>
#include <cstdlib>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <thread>
#include <data_structure/base/trajectory.h>
#include <data_structure/base/polytope.h>
#include <rog_map/rog_map.h>

namespace super_planner {
// Opt-in input evidence, not a planning policy or a performance benchmark.
// Disk IO and bitset serialization are off the planning/FSM threads. Bounded
// queue and capture count prevent instrumentation from exhausting memory.
class PlannerFailureCapture {
public:
    struct Frame {
        std::uint64_t id{0}, frontend_end{0}, guard_before{0}, guard_after{0};
        rog_map::ROGMap::PlannerSnapshotDump frontend_map, guard_map;
        super_utils::vec_Vec3f guide, cloud, zones;
        std::vector<double> radii;
        std::vector<double> guide_stamps;
        super_utils::VecDf init_times;
        super_utils::vec_Vec3f init_positions;
        geometry_utils::PolytopeVec corridors;
        super_utils::StatePVAJ initial, final;
        geometry_utils::Trajectory optimized, candidate;
        std::string stage, status, phase;
        double collision_tt{-1.0}, body_radius{0.0}, inflation_radius{0.0};
        super_utils::Vec3f collision{super_utils::Vec3f::Zero()};
        bool optimizer_success{false};
    };
    PlannerFailureCapture() {
        const char* directory = std::getenv("SUPER_PLANNER_FAILURE_CAPTURE_DIR");
        if (!directory || directory[0] != '/') return;
        directory_ = directory;
        worker_ = std::thread([this] { loop(); });
    }
    ~PlannerFailureCapture() {
        { std::lock_guard<std::mutex> lock(mutex_); stopped_ = true; }
        cv_.notify_all();
        if (worker_.joinable()) worker_.join();
    }
    std::shared_ptr<Frame> begin() {
        if (directory_.empty() || next_ >= 32) return {};
        auto frame = std::make_shared<Frame>();
        frame->id = ++next_;
        frame->initial.setZero(); frame->final.setZero();
        return frame;
    }
    void submit(Frame frame) {
        { std::lock_guard<std::mutex> lock(mutex_);
          if (queue_.size() >= 4) {
              std::cerr << "[PLANNER_INPUT_CAPTURE] dropped id=" << frame.id
                        << " reason=bounded_queue_full\n";
              return;
          }
          queue_.push_back(std::move(frame)); }
        cv_.notify_one();
    }
private:
    std::string directory_;
    std::uint64_t next_{0};
    std::mutex mutex_;
    std::condition_variable cv_;
    std::deque<Frame> queue_;
    std::thread worker_;
    bool stopped_{false};
    static void points(const std::filesystem::path& path,
                       const super_utils::vec_Vec3f& values) {
        std::ofstream out(path); out << std::setprecision(17) << "x,y,z\n";
        for (const auto& p : values) out << p.x() << ',' << p.y() << ',' << p.z() << '\n';
        if (!out.good()) throw std::runtime_error("point write failed");
    }
    static void trajectory(const std::filesystem::path& path,
                           const geometry_utils::Trajectory& trajectory) {
        std::ofstream out(path); out << std::setprecision(17)
            << "piece,duration_s,axis,power,coefficient,start_wt\n";
        for (int i = 0; i < trajectory.getPieceNum(); ++i) {
            const auto& coefficients = trajectory[i].getCoeffMat();
            for (int axis = 0; axis < coefficients.rows(); ++axis)
                for (int j = 0; j < coefficients.cols(); ++j)
                    out << i << ',' << trajectory[i].getDuration() << ',' << axis
                        << ',' << coefficients.cols()-1-j << ',' << coefficients(axis,j)
                        << ',' << trajectory.start_WT << '\n';
        }
        if (!out.good()) throw std::runtime_error("trajectory write failed");
    }
    void write(const Frame& frame) {
        const auto path = std::filesystem::path(directory_) / std::to_string(frame.id);
        if (!std::filesystem::create_directory(path))
            throw std::runtime_error("capture directory already exists or parent missing");
        points(path/"guide.csv", frame.guide); points(path/"ciri_cloud.csv", frame.cloud);
        points(path/"zones.csv", frame.zones);
        points(path/"optimizer_init_positions.csv", frame.init_positions);
        std::ofstream times(path/"timings.csv"); times << std::setprecision(17)
            << "type,index,value\n";
        for (std::size_t i = 0; i < frame.guide_stamps.size(); ++i)
            times << "guide_stamp," << i << ',' << frame.guide_stamps[i] << '\n';
        for (int i = 0; i < frame.init_times.size(); ++i)
            times << "optimizer_init_time," << i << ',' << frame.init_times(i) << '\n';
        for (std::size_t i = 0; i < frame.radii.size(); ++i)
            times << "zone_radius," << i << ',' << frame.radii[i] << '\n';
        trajectory(path/"optimized.csv", frame.optimized);
        trajectory(path/"candidate.csv", frame.candidate);
        std::ofstream planes(path/"corridors.csv"); planes << std::setprecision(17)
            << "corridor,face,nx,ny,nz,d,obstacle_face\n";
        for (std::size_t i = 0; i < frame.corridors.size(); ++i) {
            const auto matrix = frame.corridors[i].GetPlanes();
            const auto& flags = frame.corridors[i].GetFaceObstacleFlags();
            for (int j = 0; j < matrix.rows(); ++j)
                planes << i << ',' << j << ',' << matrix(j,0) << ',' << matrix(j,1)
                       << ',' << matrix(j,2) << ',' << matrix(j,3) << ','
                       << (j < int(flags.size()) ? int(flags[j]) : -1) << '\n';
        }
        std::ofstream pva(path/"boundary.csv"); pva << std::setprecision(17)
            << "boundary,axis,derivative,value\n";
        for (int side = 0; side < 2; ++side) {
            const auto& state = side ? frame.final : frame.initial;
            for (int axis = 0; axis < 3; ++axis)
                for (int j = 0; j < state.cols(); ++j)
                    pva << side << ',' << axis << ',' << j << ',' << state(axis,j) << '\n';
        }
        const bool front_written = frame.frontend_map.write &&
                frame.frontend_map.write((path/"frontend.map").string());
        const bool guard_written = frame.guard_map.write &&
                frame.guard_map.write((path/"guard.map").string());
        std::ofstream meta(path/"metadata.txt"); meta << std::setprecision(17)
            << "id=" << frame.id << "\nstage=" << frame.stage << "\nphase=" << frame.phase
            << "\nstatus=" << frame.status << "\nfrontend_start=" << frame.frontend_map.version
            << "\nfrontend_end=" << frame.frontend_end << "\nguard_before=" << frame.guard_before
            << "\nguard_snapshot=" << frame.guard_map.version << "\nguard_after=" << frame.guard_after
            << "\nfrontend_map_written=" << front_written << "\nguard_map_written=" << guard_written
            << "\noptimizer_success=" << frame.optimizer_success
            << "\nbody_radius=" << frame.body_radius << "\ninflation_radius=" << frame.inflation_radius
            << "\ncollision_tt=" << frame.collision_tt << "\ncollision_x=" << frame.collision.x()
            << "\ncollision_y=" << frame.collision.y() << "\ncollision_z=" << frame.collision.z() << '\n';
        if (!planes.good() || !pva.good() || !meta.good())
            throw std::runtime_error("capture metadata write failed");
        // Consumers accept only frames containing this final completion marker.
        std::ofstream complete(path/"COMPLETE"); complete << "diagnostic_only\n";
        std::cerr << "[PLANNER_INPUT_CAPTURE] written id=" << frame.id << " stage="
                  << frame.stage << " status=" << frame.status << '\n';
    }
    void loop() {
        for (;;) {
            Frame frame;
            { std::unique_lock<std::mutex> lock(mutex_);
              cv_.wait(lock, [this] { return stopped_ || !queue_.empty(); });
              if (queue_.empty()) return;
              frame = std::move(queue_.front()); queue_.pop_front(); }
            try { write(frame); }
            catch (const std::exception& error) {
                std::cerr << "[PLANNER_INPUT_CAPTURE] failed id=" << frame.id
                          << " error=" << error.what() << '\n';
            }
        }
    }
};
}
