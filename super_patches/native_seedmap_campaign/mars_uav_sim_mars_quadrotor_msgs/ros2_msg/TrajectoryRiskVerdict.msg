std_msgs/Header header

uint8 DISABLED=0
uint8 STALE=1
uint8 INSUFFICIENT_DATA=2
uint8 EMPTY_TRAJECTORY=3
uint8 NO_HIT=4
uint8 EGRESS=5
uint8 OCCUPIED=6

# Latest-only front-end result identity. A consumer must match the trajectory
# generation and validate both publication age and source-cloud age before it
# treats this verdict as current evidence.
uint64 request_id
uint64 trajectory_generation
uint64 cloud_sequence
uint64 source_cloud_stamp_ns
uint8 status

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
