TrajectorySafetyResult SuperPlanner::validateCommittedTrajectory(
            const double now_wt,
            const std::chrono::steady_clock::time_point deadline) const {
        const auto snapshot = cmd_traj_info_.snapshot();
        if (snapshot.empty) {
            TrajectorySafetyResult result;
            result.status = trajectoryValidationEnabled()
                    ? TrajectorySafetyStatus::EMPTY_TRAJECTORY
                    : TrajectorySafetyStatus::DISABLED;
            result.trajectory_generation = snapshot.generation;
            return result;
        }
        const double checked_from_tt = now_wt - snapshot.start_wt;
        auto result = validatePositionTrajectory(snapshot.pos_traj,
                                                 checked_from_tt,
                                                 snapshot.generation,
                                                 true, false, nullptr, false,
                                                 nullptr, deadline);
        if (trajectoryValidationEnabled() &&
            cmd_traj_info_.generation() != snapshot.generation &&
            result.status == TrajectorySafetyStatus::SAFE) {
            // Never replace a real geometry failure or timeout with a
            // retryable version-change status.
            result.status = TrajectorySafetyStatus::VERSION_CHANGED;
        }
        return result;
    }
