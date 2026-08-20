#!/usr/bin/env bash

# Cruzr S2 v0.2.0 cross-computer boot readiness guard.
#
# This script is intended to run on the Vision computer.  It does not modify
# uDoke or Docker Compose.  It waits for the Motion computer's ROS graph and
# only recovers the known v0.2.0 boot race when Control Center's latest state
# is exactly Fault.

set -Eeuo pipefail

CONTROL_CENTER_CONTAINER="${CONTROL_CENTER_CONTAINER:-walker-system.control_center-1}"
ROS_CONTAINER="${ROS_CONTAINER:-walker-ros.ros2-1}"
EXPECTED_VERSION="${EXPECTED_VERSION:-v0.2.0}"
READY_TIMEOUT_SECONDS="${READY_TIMEOUT_SECONDS:-420}"
VERSION_TIMEOUT_SECONDS="${VERSION_TIMEOUT_SECONDS:-120}"
STATE_TIMEOUT_SECONDS="${STATE_TIMEOUT_SECONDS:-75}"
RECOVERY_TIMEOUT_SECONDS="${RECOVERY_TIMEOUT_SECONDS:-150}"
POLL_SECONDS="${POLL_SECONDS:-5}"
X86_PROBE_COUNT="${X86_PROBE_COUNT:-3}"
X86_PROBE_INTERVAL_SECONDS="${X86_PROBE_INTERVAL_SECONDS:-15}"
AUTO_HEAD_HOME="${AUTO_HEAD_HOME:-1}"

MODE="${1:---check}"

case "$MODE" in
  --check|--run)
    ;;
  *)
    echo "Usage: $0 [--check|--run]" >&2
    exit 2
    ;;
esac

log() {
  printf 'CRUZR_BOOT_GUARD %s\n' "$*"
}

die() {
  log "ERROR=$*" >&2
  exit 1
}

container_running() {
  [[ "$(docker inspect --format '{{.State.Running}}' "$1" 2>/dev/null || true)" == "true" ]]
}

wait_for_containers() {
  local deadline=$((SECONDS + READY_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    if container_running "$CONTROL_CENTER_CONTAINER" && container_running "$ROS_CONTAINER"; then
      return 0
    fi
    sleep "$POLL_SECONDS"
  done
  return 1
}

control_center_logs() {
  local started_at
  started_at="$(docker inspect --format '{{.State.StartedAt}}' "$CONTROL_CENTER_CONTAINER" 2>/dev/null)" || return 1
  docker logs --since "$started_at" "$CONTROL_CENTER_CONTAINER" 2>&1 |
    sed -r 's/\x1B\[[0-9;]*[mK]//g'
}

system_version() {
  control_center_logs |
    sed -nE 's/.*system version: ([^[:space:]]+).*/\1/p' |
    tail -n 1
}

wait_for_version() {
  local deadline=$((SECONDS + VERSION_TIMEOUT_SECONDS))
  local version
  while (( SECONDS < deadline )); do
    version="$(system_version || true)"
    if [[ -n "$version" ]]; then
      printf '%s\n' "$version"
      return 0
    fi
    sleep "$POLL_SECONDS"
  done
  return 1
}

control_state() {
  control_center_logs |
    sed -nE 's/.*sm state changed: .*-> ([[:alnum:]_]+).*/\1/p' |
    tail -n 1
}

ros_graph() {
  timeout 15 docker exec "$ROS_CONTAINER" bash -lc '
    source /opt/ros/humble/setup.bash
    export ROS2CLI_DISABLE_DAEMON=1
    ros2 service list
    ros2 action list
  ' 2>/dev/null
}

graph_is_advertised() {
  local graph
  graph="$(ros_graph)" || return 1
  grep -qx '/self_check/x86/file_presence_check' <<<"$graph" &&
    grep -qx '/self_check/x86/system_check' <<<"$graph" &&
    grep -qx '/mc/t800_mc_server/start_mc' <<<"$graph" &&
    grep -qx '/mc/manipulation/action' <<<"$graph"
}

x86_file_service_responds() {
  local output
  output="$(timeout 15 docker exec "$ROS_CONTAINER" bash -lc '
    source /opt/ros/humble/setup.bash
    export ROS2CLI_DISABLE_DAEMON=1
    timeout 12 ros2 service call \
      /self_check/x86/file_presence_check \
      sys_task_msgs/srv/SelfCheckTask \
      "{param: \"{}\"}"
  ' 2>/dev/null)" || return 1
  grep -q 'SelfCheckTask_Response(passed=True' <<<"$output"
}

wait_for_graph() {
  local deadline=$((SECONDS + READY_TIMEOUT_SECONDS))
  local consecutive=0
  while (( SECONDS < deadline )); do
    if graph_is_advertised && x86_file_service_responds; then
      consecutive=$((consecutive + 1))
      log "X86_READINESS_PROBE=$consecutive/$X86_PROBE_COUNT"
      if (( consecutive >= X86_PROBE_COUNT )); then
        return 0
      fi
      sleep "$X86_PROBE_INTERVAL_SECONDS"
    else
      consecutive=0
      sleep "$POLL_SECONDS"
    fi
  done
  return 1
}

topic_data() {
  local topic="$1"
  timeout 8 docker exec "$ROS_CONTAINER" bash -lc "
    source /opt/ros/humble/setup.bash
    export ROS2CLI_DISABLE_DAEMON=1
    timeout 5 ros2 topic echo --once '$topic'
  " 2>/dev/null |
    awk '/^[[:space:]]*data:/ {print $2; exit}'
}

read_safe_startup_state() {
  local attempt estop servo_estop charger
  for attempt in 1 2 3; do
    estop="$(topic_data /emb/estop_key_state || true)"
    servo_estop="$(topic_data /emb/servo_estop_key_state || true)"
    charger="$(topic_data /emb/chrg_input_status || true)"
    if [[ "$estop" =~ ^[01]$ && "$servo_estop" =~ ^[01]$ && "$charger" =~ ^[01]$ ]]; then
      printf '%s %s %s\n' "$estop" "$servo_estop" "$charger"
      return 0
    fi
    sleep 2
  done
  return 1
}

wait_for_terminal_control_state() {
  local deadline=$((SECONDS + STATE_TIMEOUT_SECONDS))
  local state
  while (( SECONDS < deadline )); do
    state="$(control_state || true)"
    case "$state" in
      Fault|JoystickMode)
        printf '%s\n' "$state"
        return 0
        ;;
    esac
    sleep "$POLL_SECONDS"
  done
  return 1
}

wait_for_recovery() {
  local deadline=$((SECONDS + RECOVERY_TIMEOUT_SECONDS))
  local state logs
  while (( SECONDS < deadline )); do
    state="$(control_state || true)"
    logs="$(control_center_logs || true)"
    if [[ "$state" == "JoystickMode" ]] &&
       grep -q 'selfcheck result: {"passed":true}' <<<"$logs" &&
       grep -q 'action finished: .*StartMotion() succ' <<<"$logs"; then
      return 0
    fi
    if [[ "$state" == "Fault" ]] && grep -q 'selfcheck failed' <<<"$logs"; then
      return 2
    fi
    sleep "$POLL_SECONDS"
  done
  return 1
}

head_home() {
  local output
  output="$(timeout 30 docker exec "$ROS_CONTAINER" bash -lc '
    source /opt/ros/humble/setup.bash
    export ROS2CLI_DISABLE_DAEMON=1
    ros2 action send_goal \
      /mc/manipulation/action \
      mc_task_msgs/action/ArmTask \
      "{task_name: cruzr/move_head_home, yaml_args: \"{}\"}"
  ' 2>&1)" || {
    printf '%s\n' "$output" >&2
    return 1
  }
  printf '%s\n' "$output"
  grep -Eq "status:[[:space:]]*4|desc:[[:space:]]*'?SUCCEED'?" <<<"$output"
}

wait_for_containers || die "containers_not_ready"

version="$(wait_for_version || true)"
if [[ -z "$version" ]]; then
  die "system_version_not_published_after_${VERSION_TIMEOUT_SECONDS}s"
fi
if [[ "$version" != "$EXPECTED_VERSION" ]]; then
  log "SKIP_VERSION=$version expected=$EXPECTED_VERSION"
  exit 0
fi

wait_for_graph || die "motion_graph_not_ready_after_${READY_TIMEOUT_SECONDS}s"

state="$(wait_for_terminal_control_state || true)"
safety="$(read_safe_startup_state || true)"

log "VERSION=$version"
log "CONTROL_STATE=${state:-unknown}"
log "GRAPH_READY=1 functional_x86_probes=$X86_PROBE_COUNT"
log "SAFETY_STATE=${safety:-unknown} format=estop,servo_estop,charger"

if [[ "$MODE" == "--check" ]]; then
  log "CHECK_ONLY=1 movement=none restart=none"
  exit 0
fi

if [[ "$state" == "JoystickMode" ]]; then
  log "NO_ACTION=already_healthy"
  exit 0
fi

if [[ "$state" != "Fault" ]]; then
  die "unexpected_control_state_${state:-unknown}"
fi

if [[ "$safety" != "0 0 0" ]]; then
  die "unsafe_or_unknown_startup_state_${safety:-unknown}"
fi

log "RECOVERY_MATCH=v0.2.0_ready_graph_fault"
log "RESTARTING=$CONTROL_CENTER_CONTAINER"
docker restart "$CONTROL_CENTER_CONTAINER" >/dev/null

if wait_for_recovery; then
  :
else
  result=$?
  die "control_center_recovery_failed_result_$result"
fi

log "CONTROL_STATE=JoystickMode"
log "SELFCHECK=passed"
log "START_MOTION=success"

if [[ "$AUTO_HEAD_HOME" == "1" ]]; then
  safety="$(read_safe_startup_state || true)"
  if [[ "$safety" != "0 0 0" ]]; then
    die "head_home_blocked_by_safety_state_${safety:-unknown}"
  fi
  head_home || die "head_home_failed"
  log "HEAD_HOME=success"
else
  log "HEAD_HOME=disabled"
fi

log "RECOVERY_COMPLETE=1"
