bool refreshSafetyCertificate(const char *trigger) {
            const super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::GuardCertificate);
            if (!cfg_.trajectory_guard_en) {
                return true;
            }
            const auto health = map_ptr_->getMapHealthSnapshot();
            const auto generation = planner_ptr_->getCommittedTrajectoryGeneration();
            double map_age_s;
            double map_age_limit_s;
            double motion_speed_mps;
            // Do not wait until the map is already too old to certify a stop.
            // The lower motion threshold reserves time for constructing and
            // atomically certifying the brake against a still-valid snapshot.
            const bool map_fresh = mapFreshEnoughForMotion(
                    health, map_age_s, map_age_limit_s, motion_speed_mps);

            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                if (map_fresh && safety_certificate_valid_ &&
                    safety_certificate_.safe() &&
                    safety_certificate_.trajectory_generation == generation &&
                    safety_certificate_.map_version == health.map_version &&
                    !safety_revalidation_requested_.load(std::memory_order_acquire)) {
                    return true;
                }
            }

            TrajectorySafetyResult result;
            if (!map_fresh) {
                result.status = TrajectorySafetyStatus::MAP_STALE;
                result.trajectory_generation = generation;
                result.map_version = health.map_version;
            } else {
                result = planner_ptr_->validateCommittedTrajectory(
                        ros_ptr_->getSimTime());
            }

            bool changed;
            {
                std::lock_guard<std::mutex> lock(safety_mutex_);
                changed = !safety_certificate_valid_ ||
                          safety_certificate_.status != result.status ||
                          safety_certificate_.trajectory_generation !=
                                  result.trajectory_generation ||
                          safety_certificate_.map_version != result.map_version;
                safety_certificate_ = result;
                safety_certificate_valid_ = true;
            }
            safety_revalidation_requested_.store(false, std::memory_order_release);

            if (changed) {
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
