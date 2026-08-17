#!/usr/bin/env bash

# Biblioteca compartida por las demostraciones de manos Cruzr S2.
# No debe ejecutarse directamente.

readonly HANDS_MOTION_HOST="192.168.11.2"
readonly HANDS_VISION_HOST="192.168.11.3"
readonly HANDS_WIFI_GATEWAY="192.168.42.2"
readonly HANDS_ROBOT_USER="walker"
readonly HANDS_DEFAULT_PASSWORD="aa"
readonly HANDS_MOTION_CONTAINER="walker-motion.manipulation_robot_app-1"
readonly HANDS_ROS_CONTAINER="walker-ros.ros2-1"
readonly HANDS_CONFIG_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly HANDS_META_ROOT="/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_move"
readonly HANDS_ACTION_NAME="/mc/manipulation/action"
readonly HANDS_ACTION_TYPE="mc_task_msgs/action/ArmTask"
readonly HANDS_MIN_SOC="30"

HANDS_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly HANDS_DIR
readonly HANDS_MANIFEST="$HANDS_DIR/factory_tasks.sha256"
readonly HANDS_META_MANIFEST="$HANDS_DIR/factory_meta.sha256"
HANDS_CALLER_PATH="$(readlink -f -- "$0")"
readonly HANDS_CALLER_PATH

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$HANDS_DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD

if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

HANDS_CONNECTION_MODE=""
HANDS_VISION_SSH_HOST=""
HANDS_DETECTED_MODEL=""
declare -a HANDS_MOTION_ROUTE_ARGS=()
declare -A HANDS_VALIDATED_TASKS=()

hands_die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

hands_info() {
  printf '%s\n' "$*"
}

hands_warn() {
  printf 'AVISO: %s\n' "$*" >&2
}

hands_require_tools() {
  local tool
  for tool in ssh scp setsid nc flock python3 awk sha256sum readlink; do
    command -v "$tool" >/dev/null 2>&1 || hands_die "Falta el comando local '$tool'."
  done
  [[ -r "$HANDS_MANIFEST" ]] || hands_die "No se encuentra $HANDS_MANIFEST"
  [[ -r "$HANDS_META_MANIFEST" ]] || hands_die "No se encuentra $HANDS_META_MANIFEST"
}

hands_select_connection() {
  hands_require_tools
  HANDS_MOTION_ROUTE_ARGS=()

  if nc -z -w2 "$HANDS_MOTION_HOST" 22 >/dev/null 2>&1 && \
     nc -z -w2 "$HANDS_VISION_HOST" 22 >/dev/null 2>&1; then
    HANDS_CONNECTION_MODE="directa"
    HANDS_VISION_SSH_HOST="$HANDS_VISION_HOST"
  elif nc -z -w2 "$HANDS_WIFI_GATEWAY" 22 >/dev/null 2>&1; then
    HANDS_CONNECTION_MODE="wifi"
    HANDS_VISION_SSH_HOST="$HANDS_WIFI_GATEWAY"
    HANDS_MOTION_ROUTE_ARGS=(
      -o "ProxyCommand=ssh -o ConnectTimeout=6 -o ConnectionAttempts=1 -o PreferredAuthentications=password -o PubkeyAuthentication=no -o NumberOfPasswordPrompts=1 -o StrictHostKeyChecking=accept-new -W %h:%p $HANDS_ROBOT_USER@$HANDS_WIFI_GATEWAY"
    )
  else
    hands_die "No se alcanza el robot por Ethernet ni por su Wi-Fi."
  fi
  hands_info "CONTROL_LINK=$HANDS_CONNECTION_MODE"
}

hands_ssh_motion() {
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$HANDS_CALLER_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w ssh \
    -o ConnectTimeout=8 \
    -o ConnectionAttempts=1 \
    -o ServerAliveInterval=5 \
    -o ServerAliveCountMax=2 \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -o NumberOfPasswordPrompts=2 \
    -o StrictHostKeyChecking=accept-new \
    "${HANDS_MOTION_ROUTE_ARGS[@]}" \
    "$HANDS_ROBOT_USER@$HANDS_MOTION_HOST" "$@"
}

hands_scp_motion() {
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$HANDS_CALLER_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w scp \
    -o ConnectTimeout=8 \
    -o ConnectionAttempts=1 \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -o NumberOfPasswordPrompts=2 \
    -o StrictHostKeyChecking=accept-new \
    "${HANDS_MOTION_ROUTE_ARGS[@]}" \
    "$@"
}

hands_ssh_vision() {
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$HANDS_CALLER_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w ssh \
    -o ConnectTimeout=8 \
    -o ConnectionAttempts=1 \
    -o ServerAliveInterval=5 \
    -o ServerAliveCountMax=2 \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -o NumberOfPasswordPrompts=2 \
    -o StrictHostKeyChecking=accept-new \
    "$HANDS_ROBOT_USER@$HANDS_VISION_SSH_HOST" "$@"
}

hands_check_safety() {
  local report
  report="$(hands_ssh_vision bash -s -- "$HANDS_ROS_CONTAINER" <<'REMOTE'
set -Eeuo pipefail
container="$1"
[[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || exit 20

read_topic() {
  docker exec "$container" bash -lc \
    "source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 8 ros2 topic echo --once '$1'"
}

echo CHARGER_BEGIN
read_topic /emb/chrg_input_status
echo CHARGER_END
echo ESTOP_BEGIN
read_topic /emb/estop_key_state
echo ESTOP_END
echo SERVO_ESTOP_BEGIN
read_topic /emb/servo_estop_key_state
echo SERVO_ESTOP_END
echo POWER_BEGIN
read_topic /emb/emb_power_state
echo POWER_END
echo BATTERY_BEGIN
read_topic /emb/battery_state
echo BATTERY_END
REMOTE
)" || hands_die "No se pudieron consultar paros, alimentación y batería."

  awk '/CHARGER_BEGIN/{on=1;next}/CHARGER_END/{on=0}on&&$1=="data:"&&$2==0{ok=1}END{exit !ok}' \
    <<<"$report" || hands_die "El cargador aparece conectado o sin estado válido."
  awk '/ESTOP_BEGIN/{on=1;next}/ESTOP_END/{on=0}on&&$1=="data:"&&$2==0{ok=1}END{exit !ok}' \
    <<<"$report" || hands_die "La parada trasera no aparece liberada."
  awk '/SERVO_ESTOP_BEGIN/{on=1;next}/SERVO_ESTOP_END/{on=0}on&&$1=="data:"&&$2==0{ok=1}END{exit !ok}' \
    <<<"$report" || hands_die "La parada de servos no aparece liberada."
  awk '/POWER_BEGIN/{on=1;next}/POWER_END/{on=0}on&&$1=="data:"&&$2==1{ok=1}END{exit !ok}' \
    <<<"$report" || hands_die "La alimentación del robot no aparece activa."

  local soc_values
  soc_values="$(awk '/BATTERY_BEGIN/{on=1;next}/BATTERY_END/{on=0}on&&$1=="batsoc:"{print $2}' <<<"$report")"
  [[ -n "$soc_values" ]] || hands_die "No se recibió el SOC de las baterías."
  python3 - "$HANDS_MIN_SOC" $soc_values <<'PY'
import math
import sys
minimum = float(sys.argv[1])
values = [float(value) for value in sys.argv[2:]]
if not values or any(not math.isfinite(value) for value in values):
    raise SystemExit("SOC inválido")
if min(values) < minimum:
    raise SystemExit(f"SOC insuficiente para demostración: {values}")
print("BATTERY_SOC=" + ",".join(f"{value:.1f}" for value in values))
PY
  hands_info "ESTOPS=0,0"
  hands_info "CHARGER=disconnected"
}

hands_check_motion_and_detect_model() {
  local report
  local expected_model="$1"

  report="$(hands_ssh_motion bash -s -- "$HANDS_MOTION_CONTAINER" "$HANDS_ROS_CONTAINER" <<'REMOTE'
set -Eeuo pipefail
motion_container="$1"
ros_container="$2"
[[ "$(docker inspect --format '{{.State.Running}}' "$motion_container" 2>/dev/null)" == "true" ]] || exit 30
[[ "$(docker inspect --format '{{.State.Running}}' "$ros_container" 2>/dev/null)" == "true" ]] || exit 31

environment="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$motion_container")"
hw_type="$(awk -F= '$1=="HW_TYPE"{print substr($0,index($0,"=")+1)}' <<<"$environment")"
echo "HW_TYPE=$hw_type"

action_info="$(docker exec "$motion_container" bash -lc \
  'source /opt/walker/setup.bash; rosa action info /mc/manipulation/action')"
printf '%s\n' "$action_info"

topics="$(docker exec "$ros_container" bash -lc \
  'source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; ros2 topic list')"
v3=0
v4=0
grep -qx '/mc/L_hand/joint_states' <<<"$topics" && grep -qx '/mc/R_hand/joint_states' <<<"$topics" && v3=1
grep -qx '/mc/left_hand/joint_states' <<<"$topics" && grep -qx '/mc/right_hand/joint_states' <<<"$topics" && v4=1

if ((v3 == 1 && v4 == 0)); then
  model=v3
  left=/mc/L_hand/joint_states
  right=/mc/R_hand/joint_states
elif ((v4 == 1 && v3 == 0)); then
  model=v4
  left=/mc/left_hand/joint_states
  right=/mc/right_hand/joint_states
elif ((v3 == 1 && v4 == 1)); then
  echo DETECTED_HAND_MODEL=ambiguous
  exit 32
else
  echo DETECTED_HAND_MODEL=none
  exit 33
fi

echo "DETECTED_HAND_MODEL=$model"
for topic in "$left" "$right"; do
  docker exec "$ros_container" bash -lc \
    "source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 8 ros2 topic echo --once '$topic' >/dev/null"
  echo "HAND_TOPIC_OK=$topic"
done
REMOTE
)" || hands_die "No se detectó una pareja inequívoca y activa de manos v3/v4."

  printf '%s\n' "$report"
  grep -q 'Action server count: 1' <<<"$report" || hands_die "No está disponible $HANDS_ACTION_NAME."
  grep -q 'Action client count: 0' <<<"$report" || hands_die "Hay otro cliente de manipulación conectado."
  HANDS_DETECTED_MODEL="$(awk -F= '$1=="DETECTED_HAND_MODEL"{print $2}' <<<"$report")"
  [[ "$HANDS_DETECTED_MODEL" == "v3" || "$HANDS_DETECTED_MODEL" == "v4" ]] || \
    hands_die "Modelo de manos no válido: ${HANDS_DETECTED_MODEL:-desconocido}"
  if [[ "$expected_model" != "auto" && "$expected_model" != "$HANDS_DETECTED_MODEL" ]]; then
    hands_die "Se solicitó $expected_model, pero el robot publica manos $HANDS_DETECTED_MODEL."
  fi
}

hands_preflight() {
  local expected_model="${1:-auto}"
  [[ "$expected_model" == "auto" || "$expected_model" == "v3" || "$expected_model" == "v4" ]] || \
    hands_die "Modelo inválido: $expected_model"

  hands_select_connection
  hands_check_safety
  hands_check_motion_and_detect_model "$expected_model"
  hands_info "HANDS_PREFLIGHT_OK=model:$HANDS_DETECTED_MODEL"
}

hands_manifest_hash() {
  local rel="$1"
  awk -v wanted="$rel" '$2==wanted{print $1; found=1} END{exit !found}' "$HANDS_MANIFEST"
}

hands_validate_tasks() {
  (($# > 0)) || hands_die "No se proporcionaron tareas para validar."
  local task rel expected
  local -a arguments=()
  local -a meta_arguments=()
  local needs_fist_meta=0
  local needs_remote_forward=0
  local needs_remote_backward=0

  for task in "$@"; do
    rel="$task.xml"
    expected="$(hands_manifest_hash "$rel")" || hands_die "Tarea fuera del manifiesto: $task"
    arguments+=("$rel" "$expected")
    [[ "$task" == fist_up_s2 || \
       "$task" == production_movie/cheer_up_s2_v3hand || \
       "$task" == production_movie/cheer_up_s2_v4hand ]] && needs_fist_meta=1
    [[ "$task" == production_movie/press_the_remote_control ]] && needs_remote_forward=1
    [[ "$task" == production_movie/press_the_remote_control_down ]] && needs_remote_backward=1
  done

  hands_ssh_motion bash -s -- "$HANDS_MOTION_CONTAINER" "$HANDS_CONFIG_ROOT" "${arguments[@]}" <<'REMOTE'
set -Eeuo pipefail
container="$1"
root="$2"
shift 2
while (($#)); do
  rel="$1"
  expected="$2"
  shift 2
  path="$root/$rel"
  actual="$(docker exec "$container" sha256sum "$path" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || {
    echo "TASK_HASH_MISMATCH=$rel:$actual" >&2
    exit 40
  }
  echo "TASK_VALID=$rel"
done
REMOTE

  if ((needs_fist_meta == 1)); then
    meta_arguments+=("fist_up_s2.yaml" "$(awk '$2=="fist_up_s2.yaml"{print $1}' "$HANDS_META_MANIFEST")")
  fi
  if ((needs_remote_forward == 1)); then
    meta_arguments+=("production_movie/press_the_remote_control_forward.yaml" \
      "$(awk '$2=="production_movie/press_the_remote_control_forward.yaml"{print $1}' "$HANDS_META_MANIFEST")")
  fi
  if ((needs_remote_backward == 1)); then
    meta_arguments+=("production_movie/press_the_remote_control_backward.yaml" \
      "$(awk '$2=="production_movie/press_the_remote_control_backward.yaml"{print $1}' "$HANDS_META_MANIFEST")")
  fi

  if ((${#meta_arguments[@]} > 0)); then
    hands_ssh_motion bash -s -- "$HANDS_MOTION_CONTAINER" "$HANDS_META_ROOT" "${meta_arguments[@]}" <<'REMOTE'
set -Eeuo pipefail
container="$1"
root="$2"
shift 2
while (($#)); do
  rel="$1"
  expected="$2"
  shift 2
  actual="$(docker exec "$container" sha256sum "$root/$rel" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || {
    echo "META_HASH_MISMATCH=$rel:$actual" >&2
    exit 41
  }
  echo "META_VALID=$rel"
done
REMOTE
  fi

  for task in "$@"; do
    HANDS_VALIDATED_TASKS["$task"]=1
  done
}

hands_run_task() {
  local task="$1"
  local output
  [[ "${HANDS_VALIDATED_TASKS[$task]:-0}" == "1" ]] || hands_die "Tarea no validada: $task"

  hands_info "TASK_START=$task"
  output="$(hands_ssh_motion bash -s -- "$HANDS_MOTION_CONTAINER" "$task" <<'REMOTE'
set -Eeuo pipefail
container="$1"
task="$2"
docker exec "$container" bash -lc \
  "source /opt/walker/setup.bash; timeout 150 rosa action send_goal /mc/manipulation/action mc_task_msgs/action/ArmTask '{\"task_name\":\"$task\",\"yaml_args\":\"{}\"}'"
REMOTE
)" || hands_die "Falló la tarea $task; no se continuará automáticamente."
  printf '%s\n' "$output"
  grep -q "desc': 'SUCCEED'" <<<"$output" && grep -q 'status=4' <<<"$output" || \
    hands_die "La tarea $task no devolvió SUCCEED/status=4."
  hands_info "TASK_OK=$task"
}

hands_lock() {
  exec 9>"/tmp/cruzr_hands_demo.lock"
  flock -n 9 || hands_die "Ya hay otra demostración de manos en ejecución."
}

hands_confirm_empty_demo() {
  local title="$1"
  [[ "${CRUZR_HANDS_CONFIRMED:-0}" == "1" ]] && return 0
  [[ -t 0 ]] || hands_die "La confirmación física requiere una terminal interactiva."
  cat <<EOF

CONFIRMACIÓN — $title
  - Manos $HANDS_DETECTED_MODEL instaladas, fijadas, cableadas y homed.
  - Ambas manos están vacías y los brazos parten de home.
  - Cargador desconectado; paros liberados; base inmóvil.
  - Hay 1,5 m libres alrededor y sobre ambos brazos.
  - Nadie está dentro del alcance y otra persona sostiene el paro físico.
  - La tarea se detendrá ante ruido, tirones, asimetría o error.

Escribe DEMO MANOS para continuar:
EOF
  local answer
  read -r answer
  [[ "$answer" == "DEMO MANOS" ]] || hands_die "Demostración cancelada."
}

hands_parse_common_args() {
  HANDS_MODE="check"
  HANDS_REQUESTED_MODEL="auto"
  HANDS_YES=0
  while (($#)); do
    case "$1" in
      --check) HANDS_MODE="check" ;;
      --run) HANDS_MODE="run" ;;
      --model)
        shift
        (($#)) || hands_die "--model requiere auto, v3 o v4."
        HANDS_REQUESTED_MODEL="$1"
        ;;
      --yes) HANDS_YES=1 ;;
      *) hands_die "Opción desconocida: $1" ;;
    esac
    shift
  done
  [[ "$HANDS_REQUESTED_MODEL" == "auto" || "$HANDS_REQUESTED_MODEL" == "v3" || "$HANDS_REQUESTED_MODEL" == "v4" ]] || \
    hands_die "Modelo inválido: $HANDS_REQUESTED_MODEL"
  if ((HANDS_YES == 1)); then
    export CRUZR_HANDS_CONFIRMED=1
  fi
}
