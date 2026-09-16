enum class TrajectorySafetyStatus : std::uint8_t {
        DISABLED = 0,
        SAFE,
        EMPTY_TRAJECTORY,
        INVALID_TRAJECTORY,
        MAP_NOT_COMMITTED,
        MAP_UPDATING,
        MAP_STALE,
        OCCUPIED,
        CLEARANCE_MARGIN,
        // Distinct from CLEARANCE_MARGIN: the point isn't near a detected
        // obstacle at all, it has simply never been swept by the sensor.
        // Only produced when a caller opts in via
        // validatePositionTrajectory's unknown_as_occupied parameter.
        UNOBSERVED,
        OUT_OF_MAP,
        VERSION_CHANGED
    };
struct TrajectorySafetyResult {
        TrajectorySafetyStatus status{TrajectorySafetyStatus::INVALID_TRAJECTORY};
        std::uint64_t trajectory_generation{0};
        std::uint64_t map_version{0};
        double checked_from_tt{0.0};
        double checked_to_tt{0.0};
        double first_collision_tt{-1.0};
        Vec3f first_collision_pos{Vec3f::Zero()};
        std::size_t checked_samples{0};
        double map_wait_ms{0.0};
        double map_query_ms{0.0};
        double trajectory_eval_ms{0.0};
        double voxelize_ms{0.0};
        bool used_clearance_escape{false};
        bool used_initial_footprint_egress{false};
        double clearance_escape_completed_tt{-1.0};

        bool safe() const {
            return status == TrajectorySafetyStatus::SAFE ||
                   status == TrajectorySafetyStatus::DISABLED;
        }
    };

