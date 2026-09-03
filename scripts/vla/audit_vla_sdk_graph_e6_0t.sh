#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_sdk_graph_e6_0t.sh --check
  ./scripts/vla/audit_vla_sdk_graph_e6_0t.sh --run

--check valida sólo los prerrequisitos locales. --run consulta por SSH el
grafo ROS 2 de Motion sin suscribirse ni publicar: tipos, endpoints SDK y
estado detenido de los contenedores VLA. No envía comandos ni mueve el robot.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly TRANSPORT_CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_sdk_transport_contract_e6_0r.json"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly VISION_HOST="${CRUZR_VISION_HOST:-192.168.11.3}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly ROS_CONTAINER="walker-ros.ros2-1"
readonly CONTROL_CONTAINER="cruzr-vla-control"
readonly INFERENCE_CONTAINER="cruzr-vla-inference"

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

for tool in awk find grep jq nc readlink setsid sha256sum sort ssh tee xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
test -x "$EVIDENCE_SCRIPT" || { printf 'ERROR: falta %s\n' "$EVIDENCE_SCRIPT" >&2; exit 1; }
test -s "$TRANSPORT_CONTRACT" || { printf 'ERROR: falta %s\n' "$TRANSPORT_CONTRACT" >&2; exit 1; }
jq -e '
  .command_topic == "/mc/sdk/robot_command"
  and .command_message_type == "mc_task_msgs/msg/RobotCommand"
  and .state_topic == "/mc/sdk/robot_state"
  and .state_message_type == "mc_state_msgs/msg/RobotState"
  and .physical_execution_default == false
  and .active_launcher_implemented == false
  and .physical_execution_authorized == false
' "$TRANSPORT_CONTRACT" >/dev/null
printf 'E6.0T_LOCAL_CHECK_OK=sdk-contract-fail-closed\n'
[[ "$MODE" == run ]] || exit 0

nc -z -w3 "$MOTION_HOST" 22 || {
  printf 'ERROR: Motion no responde en %s:22\n' "$MOTION_HOST" >&2
  exit 1
}
nc -z -w3 "$VISION_HOST" 22 || {
  printf 'ERROR: Vision no responde en %s:22\n' "$VISION_HOST" >&2
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
  local host="$1"
  shift
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w ssh "${ssh_options[@]}" "$ROBOT_USER@$host" "$@"
}

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0T)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0T
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: FAIL_LIVE_SDK_GRAPH_AUDIT_INCOMPLETE
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
cp -- "$TRANSPORT_CONTRACT" "$RUN_DIR/"
sha256sum "$TRANSPORT_CONTRACT" > "$RUN_DIR/source_hashes.sha256"

run_ssh "$MOTION_HOST" bash -s -- "$ROS_CONTAINER" "$CONTROL_CONTAINER" \
  > "$RUN_DIR/sdk-graph.log" <<'REMOTE'
set -Eeuo pipefail
ros_container="$1"
control_container="$2"

for container in "$ros_container" "$control_container"; do
  docker container inspect "$container" >/dev/null
done
printf 'CONTROL_CONTAINER=%s\n' "$(docker inspect "$control_container" --format '{{.State.Status}}')"

docker exec "$ros_container" bash -lc '
set -Eeo pipefail
source /opt/ros/humble/setup.bash
source /opt/ubt_3rdparty/setup.bash
set -u
export ROS2CLI_DISABLE_DAEMON=1

topic_record() {
  local label="$1" topic="$2" expected="$3"
  local type info publishers subscribers
  type="$(timeout 8 ros2 topic type "$topic")"
  [[ "$type" == "$expected" ]]
  info="$(timeout 8 ros2 topic info "$topic")"
  publishers="$(grep -E "^Publisher count:" <<<"$info" | cut -d: -f2 | tr -d " ")"
  subscribers="$(grep -E "^Subscription count:" <<<"$info" | cut -d: -f2 | tr -d " ")"
  printf "%s_TYPE=%s\\n" "$label" "$type"
  printf "%s_PUBLISHERS=%s\\n" "$label" "$publishers"
  printf "%s_SUBSCRIBERS=%s\\n" "$label" "$subscribers"
}

topic_record SDK_COMMAND /mc/sdk/robot_command mc_task_msgs/msg/RobotCommand
topic_record SDK_STATE /mc/sdk/robot_state mc_state_msgs/msg/RobotState

for side in left_arm right_arm; do
  topic="/mc/${side}/controller"
  if timeout 4 ros2 topic type "$topic" >/tmp/e6_0t_type 2>/dev/null; then
    printf "DIRECT_%s_TYPE=%s\\n" "${side^^}" "$(cat /tmp/e6_0t_type)"
  else
    printf "DIRECT_%s_TYPE=absent\\n" "${side^^}"
  fi
done
rm -f /tmp/e6_0t_type
'
REMOTE
run_ssh "$VISION_HOST" \
  "docker container inspect '$INFERENCE_CONTAINER' --format 'INFERENCE_CONTAINER={{.State.Status}}'" \
  >> "$RUN_DIR/sdk-graph.log"

tee "$RUN_DIR/sdk-graph.console.log" < "$RUN_DIR/sdk-graph.log"
grep -Fxq 'CONTROL_CONTAINER=exited' "$RUN_DIR/sdk-graph.log"
grep -Fxq 'INFERENCE_CONTAINER=exited' "$RUN_DIR/sdk-graph.log"
grep -Fxq 'SDK_COMMAND_TYPE=mc_task_msgs/msg/RobotCommand' "$RUN_DIR/sdk-graph.log"
grep -Fxq 'SDK_COMMAND_PUBLISHERS=0' "$RUN_DIR/sdk-graph.log"
grep -Eq '^SDK_COMMAND_SUBSCRIBERS=[1-9][0-9]*$' "$RUN_DIR/sdk-graph.log"
grep -Fxq 'SDK_STATE_TYPE=mc_state_msgs/msg/RobotState' "$RUN_DIR/sdk-graph.log"
grep -Eq '^SDK_STATE_PUBLISHERS=[1-9][0-9]*$' "$RUN_DIR/sdk-graph.log"
grep -Fxq 'DIRECT_LEFT_ARM_TYPE=absent' "$RUN_DIR/sdk-graph.log"
grep -Fxq 'DIRECT_RIGHT_ARM_TYPE=absent' "$RUN_DIR/sdk-graph.log"

command_subscribers="$(awk -F= '$1=="SDK_COMMAND_SUBSCRIBERS" {print $2}' "$RUN_DIR/sdk-graph.log")"
state_publishers="$(awk -F= '$1=="SDK_STATE_PUBLISHERS" {print $2}' "$RUN_DIR/sdk-graph.log")"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0T
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_LIVE_SDK_GRAPH_READ_ONLY_NO_PUBLISHER
mode: live_graph_read_only_no_subscription_no_publisher_no_movement
sdk_command_topic: /mc/sdk/robot_command
sdk_command_type: mc_task_msgs/msg/RobotCommand
sdk_command_publishers: 0
sdk_command_subscribers: $command_subscribers
sdk_state_topic: /mc/sdk/robot_state
sdk_state_type: mc_state_msgs/msg/RobotState
sdk_state_publishers: $state_publishers
direct_left_arm_topic: absent
direct_right_arm_topic: absent
vla_control_container: exited
vla_inference_container: exited
robot_state_payload_read: false
physical_publishers_created: 0
physical_movement_commanded: false
physical_execution_authorized: false
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0T_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0T_PHYSICAL_AUTHORIZED=0\n'
trap - EXIT INT TERM
