# Preserved launch-style attempt cleanup finding

Message identity, raw payload, 1Hz retransmission and RCLCPP_INFO marker capture
checks passed. Parent launch PID2960225 exited0, but `mission.log:19` reports
waypoint PID2960226 exited-2. Both processes are gone (`pgrep` after exit1).

The initial harness sent SIGINT to the entire process group. ROS launch also
forwards SIGINT to its child, causing two signals; this is a fixture cleanup
defect, not evidence of a producer runtime failure during message processing.
The original `result.json` considered only parent exit and incorrectly retained
`valid=true`; do not use that aggregate boolean as all-checks-pass evidence.

Original files are preserved. The fixture is corrected for future invocations
to signal only the launch parent first and to reject child-error exit log lines.
No automatic retry or runtime source change was performed. Marker visibility
under actual `output='log'` is directly proven by all ten expected markers.
