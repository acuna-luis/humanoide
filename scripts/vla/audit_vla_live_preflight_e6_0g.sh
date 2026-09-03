#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_live_preflight_e6_0g.sh --check
  ./scripts/vla/audit_vla_live_preflight_e6_0g.sh --run
  ./scripts/vla/audit_vla_live_preflight_e6_0g.sh --run --expect-released

Audita en vivo y sólo en lectura el escenario E6.0 NO_BOX_READY: paros,
baterías, cargador, contenedores VLA, ausencia de publicadores y presencia del
task S2 ready. No instala, recarga, reinicia, publica ni mueve.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly MANIPULATION_CHECK="$REPO_ROOT/scripts/cruzr_blue_workbin_cycle.sh"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly ROS_CONTAINER="walker-ros.ros2-1"
readonly MOTION_CONTAINER="walker-motion.manipulation_robot_app-1"
readonly TASK_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly READY_KEY="s2_vla_pick_large_teleop_ready"
readonly READY_XML="$TASK_ROOT/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml"
readonly EXPECTED_VENDOR_READY_SHA256="f4025124491eba995ec824db3e3be91875f781a4b4e98928654bde9a021d8323"
readonly EXPECTED_S2_READY_SHA256="c767f7396a325d375752fbce2351837e7f5e0c750902e4815ddd7acb24e2a9b2"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE="check"
EXPECT_ESTOP="active"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --expect-active-estop) EXPECT_ESTOP="active"; shift ;;
    --expect-released) EXPECT_ESTOP="released"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in awk date find grep nc readlink setsid sha256sum sort ssh tee xargs; do
  command -v "$tool" >/dev/null || {
    printf 'ERROR: falta herramienta: %s\n' "$tool" >&2
    exit 1
  }
done
for required in "$EVIDENCE_SCRIPT" "$SHADOW_SCRIPT" "$MANIPULATION_CHECK"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done

ssh_options=(
  -o ConnectTimeout=10
  -o ConnectionAttempts=1
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
  -o PreferredAuthentications=password
  -o PubkeyAuthentication=no
  -o NumberOfPasswordPrompts=2
  -o StrictHostKeyChecking=accept-new
)

run_ssh() {
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w ssh "${ssh_options[@]}" "$ROBOT_USER@$MOTION_HOST" "$@"
}

capture_motion_snapshot() {
  run_ssh bash -s -- "$ROS_CONTAINER" "$MOTION_CONTAINER" "$TASK_ROOT" \
    "$READY_KEY" "$READY_XML" "$EXPECTED_VENDOR_READY_SHA256" \
    "$EXPECTED_S2_READY_SHA256" <<'REMOTE'
set -Eeuo pipefail
ros_container="$1"
motion_container="$2"
task_root="$3"
ready_key="$4"
ready_xml="$5"
expected_vendor_ready_sha="$6"
expected_s2_ready_sha="$7"

for container in "$ros_container" "$motion_container"; do
  test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
done

environment="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$motion_container")"
hw_type="$(awk -F= '$1=="HW_TYPE" {print substr($0,index($0,"=")+1)}' <<<"$environment")"
printf 'MOTION_CONTAINER=running\nROS_CONTAINER=running\nHW_TYPE=%s\n' "$hw_type"

topic_scalar() {
  local topic="$1"
  docker exec "$ros_container" bash -lc \
    "source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 8 ros2 topic echo --once --no-daemon '$topic'" |
    awk '$1=="data:" {print $2; found=1; exit} END {exit !found}'
}

printf 'ESTOP_KEY=%s\n' "$(topic_scalar /emb/estop_key_state)"
printf 'SERVO_ESTOP_KEY=%s\n' "$(topic_scalar /emb/servo_estop_key_state)"
printf 'CHARGER=%s\n' "$(topic_scalar /emb/chrg_input_status)"

battery="$(docker exec "$ros_container" bash -lc '
  source /opt/ros/humble/setup.bash
  export ROS2CLI_DISABLE_DAEMON=1
  timeout 8 ros2 topic echo --once --no-daemon /emb/battery_state
')"
mapfile -t socs < <(awk '/batsoc:/ {print $2}' <<<"$battery")
test "${#socs[@]}" -eq 2
printf 'BATTERY_1=%s\nBATTERY_2=%s\n' "${socs[0]}" "${socs[1]}"

topic_list="$(docker exec "$ros_container" bash -lc '
  source /opt/ros/humble/setup.bash
  export ROS2CLI_DISABLE_DAEMON=1
  timeout 8 ros2 topic list
')"
if grep -Fxq '/mc/whole_joint_states' <<<"$topic_list"; then
  printf 'WHOLE_JOINT_STATES=advertised\n'
else
  printf 'WHOLE_JOINT_STATES=absent\n'
fi
if grep -Fxq '/mc/actuator_state' <<<"$topic_list"; then
  printf 'ACTUATOR_STATE=advertised\n'
else
  printf 'ACTUATOR_STATE=absent\n'
fi

action_info="$(docker exec "$motion_container" bash -lc '
  set +u
  source /opt/walker/setup.bash
  set -u
  timeout 8 rosa action info /mc/manipulation/action 2>/dev/null || true
')"
action_servers="$(awk '/Action server count:/ {print $4; found=1} END {if (!found) print 0}' <<<"$action_info")"
printf 'MANIPULATION_ACTION_SERVERS=%s\n' "$action_servers"

process_started_at="$(docker inspect --format '{{.State.StartedAt}}' "$motion_container")"
process_started_epoch="$(date -d "$process_started_at" +%s)"
task_list_mtime_epoch="$(docker exec "$motion_container" stat -c %Y "$task_root/task_list.yaml")"
printf 'MOTION_PROCESS_STARTED_AT=%s\n' "$process_started_at"
printf 'TASK_LIST_MTIME_EPOCH=%s\n' "$task_list_mtime_epoch"
if ((process_started_epoch > task_list_mtime_epoch)); then
  printf 'READY_RUNTIME_LOAD_ORDER=process_started_after_task_list\n'
else
  printf 'READY_RUNTIME_LOAD_ORDER=process_not_started_after_task_list\n'
fi

task_list="$task_root/task_list.yaml"
printf 'TASK_LIST_SHA256=%s\n' "$(docker exec "$motion_container" sha256sum "$task_list" | awk '{print $1}')"
if docker exec "$motion_container" grep -Fqx "$ready_key:" "$task_list"; then
  printf 'READY_TASK_REGISTERED=1\n'
else
  printf 'READY_TASK_REGISTERED=0\n'
fi
if docker exec "$motion_container" test -f "$ready_xml"; then
  ready_sha="$(docker exec "$motion_container" sha256sum "$ready_xml" | awk '{print $1}')"
  printf 'READY_XML_PRESENT=1\nREADY_XML_SHA256=%s\n' "$ready_sha"
  if [[ "$ready_sha" == "$expected_vendor_ready_sha" ]]; then
    printf 'READY_XML_VARIANT=vendor-incompatible-waist-2d\n'
  elif [[ "$ready_sha" == "$expected_s2_ready_sha" ]]; then
    printf 'READY_XML_VARIANT=s2-waist-1d-overlay\n'
  else
    printf 'READY_XML_VARIANT=unknown\n' >&2
    exit 42
  fi
else
  printf 'READY_XML_PRESENT=0\nREADY_XML_SHA256=absent\n'
fi
REMOTE
}

validate_snapshot() {
  local snapshot="$1"
  local estop servo_estop charger battery_1 battery_2
  grep -Fq 'MOTION_CONTAINER=running' <<<"$snapshot"
  grep -Fq 'ROS_CONTAINER=running' <<<"$snapshot"
  grep -Fq 'HW_TYPE=cruzr_s2_v1' <<<"$snapshot"
  estop="$(awk -F= '$1=="ESTOP_KEY" {print $2}' <<<"$snapshot")"
  servo_estop="$(awk -F= '$1=="SERVO_ESTOP_KEY" {print $2}' <<<"$snapshot")"
  charger="$(awk -F= '$1=="CHARGER" {print $2}' <<<"$snapshot")"
  [[ "$estop" =~ ^[01]$ && "$servo_estop" =~ ^[01]$ ]]
  if [[ "$EXPECT_ESTOP" == "active" ]]; then
    ((estop == 1 || servo_estop == 1)) || {
      echo 'ERROR: se esperaba al menos un E-stop accionado.' >&2
      return 1
    }
  else
    ((estop == 0 && servo_estop == 0)) || {
      echo 'ERROR: se esperaban ambos E-stop liberados.' >&2
      return 1
    }
  fi
  [[ "$charger" == "0" ]] || { echo 'ERROR: cargador conectado.' >&2; return 1; }
  battery_1="$(awk -F= '$1=="BATTERY_1" {print $2}' <<<"$snapshot")"
  battery_2="$(awk -F= '$1=="BATTERY_2" {print $2}' <<<"$snapshot")"
  awk -v a="$battery_1" -v b="$battery_2" 'BEGIN {exit !(a >= 30 && b >= 30)}'
}

nc -z -w3 "$MOTION_HOST" 22 || {
  printf 'ERROR: Motion no es alcanzable en %s:22\n' "$MOTION_HOST" >&2
  exit 1
}

snapshot="$(capture_motion_snapshot)"
validate_snapshot "$snapshot"
shadow_status="$($SHADOW_SCRIPT --status)"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$shadow_status"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$shadow_status"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$shadow_status"

manipulation_status='CANONICAL_MANIPULATION_PREFLIGHT=not-run-estop-active'
if [[ "$EXPECT_ESTOP" == "released" ]]; then
  if ! manipulation_status="$($MANIPULATION_CHECK --check 2>&1)"; then
    printf '%s\n%s\n%s\n' "$snapshot" "$shadow_status" "$manipulation_status"
    printf 'ERROR: preflight canónico no disponible. Si Control Center está en WaitStartMotion tras un E-stop, no pulse Power/KEY1 ni improvise StartMotion: aplique el ciclo completo supervisado de la guía v0.2.0. No se envió movimiento.\n' >&2
    exit 1
  fi
  grep -Fq 'ACTUATORS_OPERATION_ENABLED=1' <<<"$manipulation_status"
  grep -Fq 'ESTOPS=0,0' <<<"$manipulation_status"
  grep -Fq 'CHARGER=disconnected' <<<"$manipulation_status"
  grep -Fq 'ACTIONS=ready' <<<"$manipulation_status"
  grep -Fq 'CHECK_OK: no se instaló ni movió nada.' <<<"$manipulation_status"
  manipulation_status+=$'\nCANONICAL_MANIPULATION_PREFLIGHT=passed-read-only'
fi

printf '%s\n%s\n%s\n' "$snapshot" "$shadow_status" "$manipulation_status"
printf 'E6.0G_EXPECT_ESTOP=%s\n' "$EXPECT_ESTOP"
printf 'E6.0G_MODE=live-read-only,no-install,no-reload,no-publisher,no-movement\n'
printf 'E6.0G_RESULT=PASS_READ_ONLY_LIVE_AUDIT_PHYSICAL_GATES_REMAIN\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0G)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
printf '%s\n' "$snapshot" > "$RUN_DIR/motion-snapshot.log"
printf '%s\n' "$shadow_status" > "$RUN_DIR/vla-status.log"
printf '%s\n' "$manipulation_status" > "$RUN_DIR/manipulation-preflight.log"
cp -- "$SCRIPT_PATH" "$RUN_DIR/"
sha256sum "$SCRIPT_PATH" > "$RUN_DIR/source_hashes.sha256"

estop="$(awk -F= '$1=="ESTOP_KEY" {print $2}' <<<"$snapshot")"
servo_estop="$(awk -F= '$1=="SERVO_ESTOP_KEY" {print $2}' <<<"$snapshot")"
ready_registered="$(awk -F= '$1=="READY_TASK_REGISTERED" {print $2}' <<<"$snapshot")"
ready_present="$(awk -F= '$1=="READY_XML_PRESENT" {print $2}' <<<"$snapshot")"
joint_state="$(awk -F= '$1=="WHOLE_JOINT_STATES" {print $2}' <<<"$snapshot")"
action_servers="$(awk -F= '$1=="MANIPULATION_ACTION_SERVERS" {print $2}' <<<"$snapshot")"
runtime_load_order="$(awk -F= '$1=="READY_RUNTIME_LOAD_ORDER" {print $2}' <<<"$snapshot")"
if [[ "$EXPECT_ESTOP" == "active" ]]; then
  stationary_reason="state_topic_unavailable_while_estop_active"
  stationary_verified=false
  next_gate="RESTORE_MOTION_CONTROL_ONLY_THROUGH_SEPARATELY_CONFIRMED_FULL_RESTART"
else
  stationary_reason="canonical_manipulation_preflight_passed"
  stationary_verified=true
  next_gate="REVIEW_REMAINING_NON_PREFLIGHT_GATES_BEFORE_ANY_CANARY"
fi

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0G
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_READ_ONLY_LIVE_AUDIT_PHYSICAL_GATES_REMAIN
mode: live_read_only_no_install_no_reload_no_publisher_no_movement
expected_estop_state: $EXPECT_ESTOP
estop_key: $estop
servo_estop_key: $servo_estop
charger_connected: false
ready_task_registered_on_disk: $ready_registered
ready_xml_present_on_disk: $ready_present
whole_joint_states: $joint_state
manipulation_action_servers: $action_servers
ready_runtime_load_order: $runtime_load_order
vla_inference_container: exited
vla_control_container: exited
physical_publishers: 0
canonical_manipulation_preflight: $([[ "$EXPECT_ESTOP" == "released" ]] && printf passed || printf not_run_estop_active)
robot_state_stationary_verified: $stationary_verified
robot_state_stationary_reason: $stationary_reason
physical_movement_commanded: false
physical_authorized: false
next_gate: $next_gate
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0G_EVIDENCE_OK=%s\n' "$RUN_DIR"
