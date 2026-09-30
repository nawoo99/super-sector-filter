# Excluded stale-install pilot

The first attempted c39 launch stopped after only Map1 Full run96010. The
flight itself completed in53.28s with zero static-PCD contacts, but the process
resolved `perfect_drone_full_node` from `/root/super_ws/install` instead of the
declared Active-Yaw overlay. Consequently the bounded recovery, async/source
and Active-Yaw runtime contracts were absent and the fail-closed child returned
1 before Sector or Adaptive started.

This is an infrastructure pilot, not one of the210 production observations. It
is not retried, replaced or pooled. The fresh campaign uses a new output root
and run range beginning at96210. The launcher now leaves the overlay unloaded
in the outer process so the child can establish base-then-overlay precedence,
and the v13 preflight refuses any outer environment that already contains the
overlay.
