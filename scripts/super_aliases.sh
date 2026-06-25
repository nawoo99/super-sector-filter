# super_aliases.sh — convenience launchers for the SUPER sector-filter campaign.
# Source this from ~/.bashrc:   source /path/to/scripts/super_aliases.sh
# (paths below assume the working tree at /root/commands/super_gazebo; adjust SUPER_DIR.)
#
#   super N        seed-N map, sector filter OFF (full 360 view baseline)
#   super_sec N    seed-N map, sector filter ON  (+/-60 horizontal cone)
#   super_watch N [mode]   HEADLESS sim + RViz + one perimeter loop to eyeball
#                          mode = full | sector | adaptive   (default adaptive)
# -----------------------------------------------------------------------------
SUPER_DIR="${SUPER_DIR:-/root/commands/super_gazebo}"
SUPER_WORLDS="${SUPER_WORLDS:-/root/px4/PX4-Autopilot/Tools/simulation/gz/worlds}"

_super_bringup() {  # $1=SECTOR(true|false)  $2=seed
  local sec="$1" seed="${2:-1}"
  local world="default_seed${seed}"
  if [ ! -f "${SUPER_WORLDS}/${world}.sdf" ]; then
    echo "[super] '${world}.sdf' not found — seeds are 1-12"; return 1
  fi
  SECTOR="$sec" bash "${SUPER_DIR}/g_bringup.sh" "$world"
}
super()     { _super_bringup false "$1"; }   # no sector filter (full 360)
super_sec() { _super_bringup true  "$1"; }   # sector filter ON (+/-60)

# watch ONE run with RViz (sim stays HEADLESS; you watch in RViz, which shows the
# sector-filtered cloud, ROG-Map occupancy, and SUPER's path/goal).
super_watch() { bash "${SUPER_DIR}/watch.sh" "${1:-11}" "${2:-adaptive}"; }
