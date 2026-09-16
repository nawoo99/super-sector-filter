TrajectorySafetyResult SuperPlanner::validateCommittedTrajectory(
            const double now_wt) const {
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
                                                 true);
        if (trajectoryValidationEnabled() &&
            cmd_traj_info_.generation() != snapshot.generation) {
            result.status = TrajectorySafetyStatus::VERSION_CHANGED;
        }
        return result;
    }
