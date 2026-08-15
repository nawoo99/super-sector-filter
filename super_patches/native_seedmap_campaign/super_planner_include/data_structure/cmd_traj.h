/**
* This file is part of SUPER
*
* Copyright 2025 Yunfan REN, MaRS Lab, University of Hong Kong, <mars.hku.hk>
* Developed by Yunfan REN <renyf at connect dot hku dot hk>
* for more information see <https://github.com/hku-mars/SUPER>.
* If you use this code, please cite the respective publications as
* listed on the above website.
*
* SUPER is free software: you can redistribute it and/or modify
* it under the terms of the GNU Lesser General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* SUPER is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU Lesser General Public License
* along with SUPER. If not, see <http://www.gnu.org/licenses/>.
*/


#ifndef CMD_TRAJ_H
#define CMD_TRAJ_H

#include <data_structure/exp_traj.h>
#include <data_structure/backup_traj.h>
#include <data_structure/base/trajectory.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <memory>
#include <mutex>


namespace super_planner {
    using geometry_utils::Trajectory;

    class CmdTraj{
    public:
        struct Candidate {
            Trajectory pos_traj{};
            Trajectory yaw_traj{};
            double backup_traj_start_tt{std::numeric_limits<double>::infinity()};
            double carry_backup_start_tt{-1.0};
            double carry_backup_end_tt{-1.0};
            bool has_appended_backup{false};
            bool has_carry_backup{false};
        };

        struct Snapshot {
            Trajectory pos_traj{};
            Trajectory yaw_traj{};
            std::uint64_t generation{0};
            double start_wt{0.0};
            double total_duration{0.0};
            double backup_traj_start_tt{std::numeric_limits<double>::infinity()};
            double carry_backup_start_tt{-1.0};
            double carry_backup_end_tt{-1.0};
            bool empty{true};
            bool has_appended_backup{false};
            bool has_carry_backup{false};
        };

        struct SharedSnapshot {
            std::shared_ptr<const Trajectory> pos_traj;
            std::shared_ptr<const Trajectory> yaw_traj;
            std::uint64_t generation{0};
            double start_wt{0.0};
            double total_duration{0.0};
            double backup_traj_start_tt{std::numeric_limits<double>::infinity()};
            double carry_backup_start_tt{-1.0};
            double carry_backup_end_tt{-1.0};
            bool empty{true};
            bool has_appended_backup{false};
            bool has_carry_backup{false};
        };

        struct Sample {
            StatePVAJ pvaj{StatePVAJ::Zero()};
            std::uint64_t generation{0};
            double start_wt{0.0};
            double trajectory_time{0.0};
            double total_duration{0.0};
            double yaw{0.0};
            double yaw_dot{0.0};
            bool on_backup{false};
            bool finished{false};
        };

    private:
        /* The update and query lock */
        mutable std::mutex mtx_;

        /* The optimized positional trajectory */
        std::shared_ptr<const Trajectory> pos_traj_{
                std::make_shared<const Trajectory>()};

        /* The optimized yaw trajectory */
        std::shared_ptr<const Trajectory> yaw_traj_{
                std::make_shared<const Trajectory>()};

        double start_WT_{0.0};
        double backup_traj_start_TT_{0.0};
        /* some part of exp traj may belong to last backup, record this */
        double on_backup_start_TT_{-1}, on_backup_end_TT_{-1};
        bool first_part_exp_has_backup_traj_{false};


        /* some flags */
        bool flag_empty_{true};
        bool flag_backup_traj_avilibale_{false};
        std::uint64_t generation_{0};

        static void setCarryBackupMetadata(const ExpTraj &exp, Candidate &candidate) {
            candidate.has_carry_backup = exp.getFirstPartBackupTraj(
                    candidate.carry_backup_start_tt,
                    candidate.carry_backup_end_tt);
            if (!candidate.has_carry_backup) {
                candidate.carry_backup_start_tt = -1.0;
                candidate.carry_backup_end_tt = -1.0;
            }
        }

        bool isTTOnBackupTrajUnlocked(const double check_tt) const {
            if (first_part_exp_has_backup_traj_ &&
                check_tt >= on_backup_start_TT_ && check_tt <= on_backup_end_TT_) {
                return true;
            }
            return flag_backup_traj_avilibale_ && check_tt >= backup_traj_start_TT_;
        }

    public:
        explicit  CmdTraj() = default;

        void setEmpty() {
            std::lock_guard<std::mutex> lock(mtx_);
            flag_empty_ = true;
            ++generation_;
        }

        bool empty() const {
            std::lock_guard<std::mutex> lock(mtx_);
            return flag_empty_;
        }

        void lock() {
            mtx_.lock();
        }

        void unlock() {
            mtx_.unlock();
        }


        static bool buildCandidate(const ExpTraj &exp_traj,
                                   const BackupTraj &backup_traj,
                                   Candidate &candidate) {
            Trajectory tmp_pos_traj, tmp_yaw_traj;
            const double backup_start_tt = backup_traj.getStartTT();
            if (!std::isfinite(backup_start_tt) || backup_start_tt <= 0.0 ||
                !exp_traj.getPartialTrajectoryByTrajectoryTime(0, backup_start_tt,
                                                               tmp_pos_traj, tmp_yaw_traj)) {
                fmt::print(fg(fmt::color::indian_red)," -- [SUPER] in [PlanFromRest] getPartialTrajectoryByTime failed.\n");
                return false;
            }
            candidate = Candidate{};
            candidate.pos_traj = tmp_pos_traj + backup_traj.posTraj();
            candidate.yaw_traj = tmp_yaw_traj + backup_traj.yawTraj();
            candidate.backup_traj_start_tt = backup_start_tt;
            candidate.has_appended_backup = true;
            setCarryBackupMetadata(exp_traj, candidate);
            return true;
        }

        static bool buildCandidate(const ExpTraj &exp_traj, Candidate &candidate) {
            if (exp_traj.empty() || exp_traj.posTraj().empty()) {
                return false;
            }
            candidate = Candidate{};
            candidate.pos_traj = exp_traj.posTraj();
            candidate.yaw_traj = exp_traj.yawTraj();
            setCarryBackupMetadata(exp_traj, candidate);
            return true;
        }

        std::uint64_t commitCandidate(Candidate candidate) {
            auto new_pos_traj = std::make_shared<const Trajectory>(
                    std::move(candidate.pos_traj));
            auto new_yaw_traj = std::make_shared<const Trajectory>(
                    std::move(candidate.yaw_traj));
            std::lock_guard<std::mutex> lock(mtx_);
            pos_traj_ = std::move(new_pos_traj);
            yaw_traj_ = std::move(new_yaw_traj);
            start_WT_ = pos_traj_->start_WT;
            flag_empty_ = false;
            backup_traj_start_TT_ = candidate.backup_traj_start_tt;
            flag_backup_traj_avilibale_ = candidate.has_appended_backup;
            on_backup_start_TT_ = candidate.carry_backup_start_tt;
            on_backup_end_TT_ = candidate.carry_backup_end_tt;
            first_part_exp_has_backup_traj_ = candidate.has_carry_backup;
            return ++generation_;
        }

        bool setTrajectory(const ExpTraj &exp_traj, const BackupTraj &backup_traj) {
            Candidate candidate;
            if (!buildCandidate(exp_traj, backup_traj, candidate)) {
                return false;
            }
            commitCandidate(std::move(candidate));
            return true;
        }

        bool setTrajectory(const ExpTraj &exp_traj) {
            Candidate candidate;
            if (!buildCandidate(exp_traj, candidate)) {
                return false;
            }
            commitCandidate(std::move(candidate));
            return true;
        }

        bool isTTOnBackupTraj(const double & checkTT) const {
            std::lock_guard<std::mutex> lock(mtx_);
            return isTTOnBackupTrajUnlocked(checkTT);
        }

        bool backupTrajAvilibale() const {
            std::lock_guard<std::mutex> lock(mtx_);
            return flag_backup_traj_avilibale_;
        }

        std::uint64_t generation() const {
            std::lock_guard<std::mutex> lock(mtx_);
            return generation_;
        }

        Snapshot snapshot() const {
            std::lock_guard<std::mutex> lock(mtx_);
            Snapshot out;
            out.generation = generation_;
            out.empty = flag_empty_ || pos_traj_->empty();
            out.pos_traj = *pos_traj_;
            out.yaw_traj = *yaw_traj_;
            out.start_wt = pos_traj_->start_WT;
            out.total_duration = out.empty ? 0.0 : pos_traj_->getTotalDuration();
            out.backup_traj_start_tt = backup_traj_start_TT_;
            out.carry_backup_start_tt = on_backup_start_TT_;
            out.carry_backup_end_tt = on_backup_end_TT_;
            out.has_appended_backup = flag_backup_traj_avilibale_;
            out.has_carry_backup = first_part_exp_has_backup_traj_;
            return out;
        }

        SharedSnapshot sharedSnapshot() const {
            std::lock_guard<std::mutex> lock(mtx_);
            SharedSnapshot out;
            out.generation = generation_;
            out.empty = flag_empty_ || pos_traj_->empty();
            out.pos_traj = pos_traj_;
            out.yaw_traj = yaw_traj_;
            out.start_wt = pos_traj_->start_WT;
            out.total_duration = out.empty ? 0.0 : pos_traj_->getTotalDuration();
            out.backup_traj_start_tt = backup_traj_start_TT_;
            out.carry_backup_start_tt = on_backup_start_TT_;
            out.carry_backup_end_tt = on_backup_end_TT_;
            out.has_appended_backup = flag_backup_traj_avilibale_;
            out.has_carry_backup = first_part_exp_has_backup_traj_;
            return out;
        }

        bool evaluate(const double now_wt, Sample &sample,
                      const std::uint64_t expected_generation = 0) const {
            std::lock_guard<std::mutex> lock(mtx_);
            if (flag_empty_ || pos_traj_->empty() || !std::isfinite(now_wt) ||
                (expected_generation != 0 && generation_ != expected_generation)) {
                return false;
            }

            const double total_duration = pos_traj_->getTotalDuration();
            const double raw_tt = now_wt - pos_traj_->start_WT;
            if (!std::isfinite(total_duration) || total_duration < 0.0 ||
                !std::isfinite(raw_tt) || raw_tt < -1.0e-3) {
                return false;
            }
            const double eval_tt = std::clamp(raw_tt, 0.0, total_duration);
            StatePVAJ pvaj;
            if (!pos_traj_->getState(eval_tt, pvaj) || !pvaj.array().isFinite().all()) {
                return false;
            }

            sample = Sample{};
            sample.pvaj = pvaj;
            sample.generation = generation_;
            sample.start_wt = pos_traj_->start_WT;
            sample.trajectory_time = eval_tt;
            sample.total_duration = total_duration;
            sample.finished = raw_tt >= total_duration;
            sample.on_backup = isTTOnBackupTrajUnlocked(eval_tt);

            if (!yaw_traj_->empty()) {
                const double yaw_tt = std::clamp(eval_tt, 0.0, yaw_traj_->getTotalDuration());
                sample.yaw = yaw_traj_->getPos(yaw_tt)[0];
                sample.yaw_dot = yaw_traj_->getVel(yaw_tt)[0];
                if (!std::isfinite(sample.yaw)) sample.yaw = 0.0;
                if (!std::isfinite(sample.yaw_dot)) sample.yaw_dot = 0.0;
            }
            return true;
        }


        double getTotalDuration() const {
            return pos_traj_->getTotalDuration();
        }

        double getBackupTrajStartTT() const {
            return backup_traj_start_TT_;
        }

        Vec3f getPos(const double & t)const {
            return pos_traj_->getPos(t);
        }

        Vec3f getVel(const double & t)const {
            return pos_traj_->getVel(t);
        }

        Vec3f getYaw(const double & t)const {
            return yaw_traj_->getPos(t);
        }

        Vec3f getYawRate(const double & t)const {
            return yaw_traj_->getVel(t);
        }

        StatePVAJ getYawState(const double &t)const {
            return yaw_traj_->getState(t);
        }

        const Trajectory & posTraj() const {
            return *pos_traj_;
        }

        const Trajectory & yawTraj() const {
            return *yaw_traj_;
        }


        const double & getStartWallTime() const {
            return pos_traj_->start_WT;
        }

        bool getPartialTrajectoryByTrajectoryTime(const double & start_t,
            const double & end_t,
            Trajectory & partial_pos_traj,
            Trajectory & partial_yaw_traj) {

            if(!pos_traj_->getPartialTrajectoryByTime(start_t,end_t,partial_pos_traj)) {
                return false;
            }

            if(!yaw_traj_->getPartialTrajectoryByTime(start_t, end_t,partial_yaw_traj)) {
                return false;
            }

            return true;
        }

    };
}

#endif //EXP_TRAJ_H
