bool refreshSafetyCertificate(const char *trigger) {
            const super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::GuardCertificate);
            if (!cfg_.trajectory_guard_en) {
                return true;
            }
            const auto retry_deadline = std::chrono::steady_clock::now() +
                    std::chrono::milliseconds(4);
            double map_age_s = 0.0, map_age_limit_s = 0.0, motion_speed_mps = 0.0;
            TrajectorySafetyResult result;
            bool changed = false;
            unsigned attempt = 0;
            for (; attempt < 2; ++attempt) {
                std::uint64_t validation;
                bool map_fresh;
                {
                    std::lock_guard<std::mutex> lock(safety_mutex_);
                    const auto health = map_ptr_->getMapHealthSnapshot();
                    const auto generation = planner_ptr_->getCommittedTrajectoryGeneration();
                    map_fresh = mapFreshEnoughForMotion(
                            health, map_age_s, map_age_limit_s, motion_speed_mps);
                    if (map_fresh && safety_certificate_valid_ &&
                        safety_certificate_.safe() &&
                        safety_certificate_.trajectory_generation == generation &&
                        safety_certificate_.map_version == health.map_version &&
                        !safety_revalidation_requested_.load(std::memory_order_acquire)) {
                        if (attempt) fmt::print(" -- [TRAJ_GUARD_REFRESH] trigger={} outcome=current_cache retry={}\n", trigger, attempt);
                        return true;
                    }
                    validation = ++safety_validation_started_;
                    // Consume only requests preceding this check. A request
                    // arriving while geometry is checked must not be lost.
                    safety_revalidation_requested_.exchange(false, std::memory_order_acq_rel);
                    result.trajectory_generation = generation;
                    result.map_version = health.map_version;
                }
                if (!map_fresh) {
                    result.status = TrajectorySafetyStatus::MAP_STALE;
                } else {
                    result = planner_ptr_->validateCommittedTrajectory(
                            ros_ptr_->getSimTime(), attempt == 0
                                    ? std::chrono::steady_clock::time_point::max()
                                    : retry_deadline);
                }
                {
                    std::lock_guard<std::mutex> lock(safety_mutex_);
                    const auto health = map_ptr_->getMapHealthSnapshot();
                    const auto generation = planner_ptr_->getCommittedTrajectoryGeneration();
                    map_fresh = mapFreshEnoughForMotion(
                            health, map_age_s, map_age_limit_s, motion_speed_mps);
                    const bool current = result.trajectory_generation == generation &&
                                         result.map_version == health.map_version;
                    const bool cache_current = safety_certificate_valid_ &&
                            safety_certificate_.trajectory_generation == generation &&
                            safety_certificate_.map_version == health.map_version;
                    if (attempt && result.safe() &&
                        std::chrono::steady_clock::now() >= retry_deadline) {
                        result.status = TrajectorySafetyStatus::VALIDATION_TIMEOUT;
                    }
                    if (result.safe() && !map_fresh) result.status = TrajectorySafetyStatus::MAP_STALE;
                    if (result.safe() && !current) result.status = TrajectorySafetyStatus::VERSION_CHANGED;
                    if ((result.status == TrajectorySafetyStatus::VERSION_CHANGED || result.safe()) &&
                        validation < safety_certificate_validation_ && cache_current) {
                        if (map_fresh && safety_certificate_.safe() &&
                            !safety_revalidation_requested_.load(std::memory_order_acquire)) {
                            fmt::print(" -- [TRAJ_GUARD_REFRESH] trigger={} outcome=newer_certificate retry={}\n", trigger, attempt);
                            return true;
                        }
                        // A newer explicit failure must not be replaced by an
                        // older SAFE result or retried away in this invocation.
                        if (!safety_certificate_.safe()) result = safety_certificate_;
                    }
                    if (result.safe() && validation < safety_certificate_validation_) {
                        // We could not reuse the newer publication above.
                        // Do not report success with no usable shared receipt.
                        result.status = TrajectorySafetyStatus::VERSION_CHANGED;
                    }
                    if (current && validation >= safety_certificate_validation_ &&
                        result.status != TrajectorySafetyStatus::VERSION_CHANGED) {
                        changed = !safety_certificate_valid_ ||
                                  safety_certificate_.status != result.status ||
                                  safety_certificate_.trajectory_generation != result.trajectory_generation ||
                                  safety_certificate_.map_version != result.map_version;
                        safety_certificate_ = result;
                        safety_certificate_valid_ = true;
                        safety_certificate_validation_ = validation;
                    }
                }
                if (result.status != TrajectorySafetyStatus::VERSION_CHANGED) break;
                fmt::print(" -- [TRAJ_GUARD_REFRESH] trigger={} outcome=version_changed retry={} gen={} map={}\n",
                           trigger, attempt, result.trajectory_generation, result.map_version);
                if (attempt != 0 || std::chrono::steady_clock::now() >= retry_deadline ||
                    !map_ptr_->immutablePlannerSnapshotEnabled()) break;
            }
            if (!result.safe()) safety_revalidation_requested_.store(true, std::memory_order_release);
            if (attempt) fmt::print(" -- [TRAJ_GUARD_REFRESH] trigger={} outcome={} retry={}\n",
                                   trigger, trajectorySafetyStatusName(result.status), attempt);

            if (changed || result.status == TrajectorySafetyStatus::VERSION_CHANGED ||
                result.status == TrajectorySafetyStatus::VALIDATION_TIMEOUT) {
                const auto snapshot = planner_ptr_->getCommittedTrajectorySnapshot();
                const double current_tt = snapshot.empty
                        ? 0.0 : ros_ptr_->getSimTime() - snapshot.start_wt;
                const double ttc = result.first_collision_tt >= 0.0
                        ? result.first_collision_tt - current_tt : -1.0;
                fmt::print(" -- [TRAJ_GUARD_CERT] trigger={} status={} gen={} map={} "
                           "map_age={:.3f}s map_age_limit={:.3f}s motion_speed={:.3f}mps "
                           "samples={} range=[{:.3f},{:.3f}] "
                           "collision_tt={:.3f} ttc={:.3f} p=[{:.3f},{:.3f},{:.3f}]\n",
                           trigger, trajectorySafetyStatusName(result.status),
                           result.trajectory_generation, result.map_version,
                           map_age_s, map_age_limit_s, motion_speed_mps,
                           result.checked_samples,
                           result.checked_from_tt, result.checked_to_tt,
                           result.first_collision_tt, ttc,
                           result.first_collision_pos.x(),
                           result.first_collision_pos.y(),
                           result.first_collision_pos.z());
            }
            return result.safe();
        }
