const char *trajectorySafetyStatusName(const TrajectorySafetyStatus status) {
        switch (status) {
            case TrajectorySafetyStatus::DISABLED: return "DISABLED";
            case TrajectorySafetyStatus::SAFE: return "SAFE";
            case TrajectorySafetyStatus::EMPTY_TRAJECTORY: return "EMPTY_TRAJECTORY";
            case TrajectorySafetyStatus::INVALID_TRAJECTORY: return "INVALID_TRAJECTORY";
            case TrajectorySafetyStatus::MAP_NOT_COMMITTED: return "MAP_NOT_COMMITTED";
            case TrajectorySafetyStatus::MAP_UPDATING: return "MAP_UPDATING";
            case TrajectorySafetyStatus::MAP_STALE: return "MAP_STALE";
            case TrajectorySafetyStatus::OCCUPIED: return "OCCUPIED";
            case TrajectorySafetyStatus::CLEARANCE_MARGIN: return "CLEARANCE_MARGIN";
            case TrajectorySafetyStatus::UNOBSERVED: return "UNOBSERVED";
            case TrajectorySafetyStatus::OUT_OF_MAP: return "OUT_OF_MAP";
            case TrajectorySafetyStatus::VERSION_CHANGED: return "VERSION_CHANGED";
            case TrajectorySafetyStatus::VALIDATION_TIMEOUT: return "VALIDATION_TIMEOUT";
            default: return "UNKNOWN";
        }
    }
