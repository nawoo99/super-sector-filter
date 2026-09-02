std_msgs/Header header

uint8 DISABLED=0
uint8 STALE=1
uint8 INSUFFICIENT_DATA=2
uint8 EMPTY_TRAJECTORY=3
uint8 NO_HIT=4
uint8 EGRESS=5
uint8 OCCUPIED=6

# The future-trajectory tier is generation-bound.  The current-body tier is
# tied to a fresh source scan and measured odometry instead, so it remains
# actionable across a trajectory-generation change.
uint8 FUTURE_TRAJECTORY=0
uint8 CURRENT_BODY=1

# Latest-only front-end result identity. FUTURE_TRAJECTORY consumers must
# match the trajectory generation.  Both scopes must validate publication and
# source-cloud age before treating a verdict as current evidence.
uint64 request_id
uint64 trajectory_generation
uint64 cloud_sequence
uint64 source_cloud_stamp_ns
uint8 status
uint8 scope

float64 trajectory_start_wt
float64 checked_from_tt
float64 checked_to_tt
float64 witness_tt
geometry_msgs/Point witness_position
float64 minimum_distance_m
float64 body_distance_m
float64 end_distance_m
uint64 source_point_count
uint64 cropped_point_count
float64 source_cloud_age_s
float64 compute_ms
