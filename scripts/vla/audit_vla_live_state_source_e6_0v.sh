#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_live_state_source_e6_0v.sh --check
  ./scripts/vla/audit_vla_live_state_source_e6_0v.sh --run

Resuelve en vivo y sólo lectura la fuente de estado para el monitor E6.0U.
Consulta QoS y toma una sola muestra; no crea publicadores ni inicia VLA.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_measured_state_monitor_contract_e6_0u.json"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly ROS_CONTAINER="walker-ros.ros2-1"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE=check
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in awk cp find grep jq nc readlink setsid sha256sum sort ssh tee xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
for required in "$CONTRACT" "$EVIDENCE_SCRIPT" "$SHADOW_SCRIPT"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
jq -e '
  .physical_execution_default == false
  and .active_launcher_implemented == false
  and .physical_execution_authorized == false
  and ([.commanded_joint_names[], .locked_joint_names[]] | length) == 20
' "$CONTRACT" >/dev/null
printf 'E6.0V_LOCAL_CHECK_OK=read-only-state-source-contract\n'
[[ "$MODE" == run ]] || exit 0

nc -z -w3 "$MOTION_HOST" 22 || {
  printf 'ERROR: Motion no responde en %s:22\n' "$MOTION_HOST" >&2
  exit 1
}
ssh_options=(
  -o ConnectTimeout=10
  -o ConnectionAttempts=1
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
  -o PreferredAuthentications=password
  -o PubkeyAuthentication=no
  -o NumberOfPasswordPrompts=1
  -o StrictHostKeyChecking=accept-new
)
run_ssh() {
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w ssh "${ssh_options[@]}" "$ROBOT_USER@$MOTION_HOST" "$@"
}

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0V)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0V
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: FAIL_LIVE_STATE_SOURCE_AUDIT_INCOMPLETE
physical_publishers_created: 0
physical_movement_commanded: false
physical_execution_authorized: false
EOF
    (
      cd "$RUN_DIR"
      find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
    ) > "$RUN_DIR/evidence.sha256"
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cp -- "$SCRIPT_PATH" "$CONTRACT" "$RUN_DIR/"
sha256sum "$SCRIPT_PATH" "$CONTRACT" > "$RUN_DIR/source_hashes.sha256"
shadow_status="$($SHADOW_SCRIPT --status)"
printf '%s\n' "$shadow_status" > "$RUN_DIR/vla-status.log"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$shadow_status"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$shadow_status"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$shadow_status"

run_ssh bash -s -- "$ROS_CONTAINER" > "$RUN_DIR/state-source.log" <<'REMOTE'
set -Eeuo pipefail
ros_container="$1"
docker container inspect "$ros_container" >/dev/null
docker exec "$ros_container" bash -lc '
set -Eeo pipefail
source /opt/ros/humble/setup.bash
source /opt/ubt_3rdparty/setup.bash
set -u
export ROS2CLI_DISABLE_DAEMON=1

printf "===SDK_COMMAND_INFO===\n"
timeout 8 ros2 topic info -v /mc/sdk/robot_command
printf "===SDK_STATE_INFO===\n"
timeout 8 ros2 topic info -v /mc/sdk/robot_state
printf "===WHOLE_STATE_INFO===\n"
timeout 8 ros2 topic info -v /mc/whole_joint_states
printf "===SDK_STATE_SAMPLE===\n"
set +e
timeout 3 ros2 topic echo --once --no-daemon /mc/sdk/robot_state mc_state_msgs/msg/RobotState --full-length
sdk_status=$?
set -e
printf "SDK_SAMPLE_EXIT=%s\n" "$sdk_status"
printf "===WHOLE_STATE_SAMPLE===\n"
timeout 8 ros2 topic echo --once --no-daemon /mc/whole_joint_states sensor_msgs/msg/JointState --full-length
'
REMOTE

extract_block() {
  local start="$1" end="$2" source="$3"
  awk -v start="$start" -v end="$end" '
    $0 == start {inside=1; next}
    $0 == end {inside=0}
    inside {print}
  ' "$source"
}
extract_block '===SDK_COMMAND_INFO===' '===SDK_STATE_INFO===' "$RUN_DIR/state-source.log" \
  > "$RUN_DIR/sdk-command-info.log"
extract_block '===SDK_STATE_INFO===' '===WHOLE_STATE_INFO===' "$RUN_DIR/state-source.log" \
  > "$RUN_DIR/sdk-state-info.log"
extract_block '===WHOLE_STATE_INFO===' '===SDK_STATE_SAMPLE===' "$RUN_DIR/state-source.log" \
  > "$RUN_DIR/whole-state-info.log"
extract_block '===SDK_STATE_SAMPLE===' '===WHOLE_STATE_SAMPLE===' "$RUN_DIR/state-source.log" \
  > "$RUN_DIR/sdk-state-sample.log"
extract_block '===WHOLE_STATE_SAMPLE===' '__END_NEVER__' "$RUN_DIR/state-source.log" \
  > "$RUN_DIR/whole-state-sample.log"

grep -Fxq 'Publisher count: 0' "$RUN_DIR/sdk-command-info.log"
test "$(grep -c '^  Reliability: BEST_EFFORT$' "$RUN_DIR/sdk-command-info.log")" -eq 2
grep -Fxq 'Publisher count: 2' "$RUN_DIR/sdk-state-info.log"
grep -Fxq 'Publisher count: 1' "$RUN_DIR/whole-state-info.log"
grep -Fxq '  Reliability: RELIABLE' "$RUN_DIR/whole-state-info.log"

mapfile -t required_joints < <(jq -r '.commanded_joint_names[], .locked_joint_names[]' "$CONTRACT")
for joint in "${required_joints[@]}"; do
  grep -Fxq -- "- $joint" "$RUN_DIR/whole-state-sample.log" || {
    printf 'ERROR: falta joint requerido en whole state: %s\n' "$joint" >&2
    exit 1
  }
done
section_count() {
  local section="$1" source="$2"
  awk -v section="$section" '
    $0 == section ":" {inside=1; next}
    inside && /^[a-zA-Z_][a-zA-Z0-9_]*:/ {inside=0}
    inside && /^- / {count++}
    END {print count+0}
  ' "$source"
}
name_count="$(section_count name "$RUN_DIR/whole-state-sample.log")"
position_count="$(section_count position "$RUN_DIR/whole-state-sample.log")"
velocity_count="$(section_count velocity "$RUN_DIR/whole-state-sample.log")"
((name_count >= 20 && position_count == name_count && velocity_count == name_count))

sdk_payload=absent_within_3s
selected_topic=/mc/whole_joint_states
if grep -q '^  joint_states:' "$RUN_DIR/sdk-state-sample.log"; then
  sdk_payload=present
  selected_topic=/mc/sdk/robot_state
fi

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0V
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_LIVE_STATE_SOURCE_READ_ONLY_SELECTED
mode: live_read_only_state_subscription_no_publisher_no_movement
sdk_command_publishers: 0
sdk_command_subscriber_reliability: BEST_EFFORT
sdk_state_publishers: 2
sdk_state_payload: $sdk_payload
whole_state_publishers: 1
whole_state_reliability: RELIABLE
whole_state_name_count: $name_count
whole_state_position_count: $position_count
whole_state_velocity_count: $velocity_count
selected_state_topic: $selected_topic
vla_inference_container: exited
vla_control_container: exited
physical_publishers_created: 0
physical_movement_commanded: false
physical_execution_authorized: false
next_work: USE_SELECTED_SOURCE_IN_EXPLICIT_INACTIVE_LAUNCHER
EOF

tee "$RUN_DIR/state-source-summary.log" <<EOF
E6.0V_SDK_STATE_PAYLOAD=$sdk_payload
E6.0V_WHOLE_STATE_COUNTS=names:$name_count,positions:$position_count,velocities:$velocity_count
E6.0V_SELECTED_STATE_TOPIC=$selected_topic
E6.0V_COMMAND_QOS=BEST_EFFORT,KEEP_LAST:5,VOLATILE
E6.0V_PHYSICAL_PUBLISHERS=0
EOF
(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
cat "$RUN_DIR/state-source-summary.log"
printf 'E6.0V_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0V_PHYSICAL_AUTHORIZED=0\n'
trap - EXIT INT TERM
