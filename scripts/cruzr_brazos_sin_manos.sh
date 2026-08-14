#!/usr/bin/env bash

set -Eeuo pipefail

# Cliente seguro para las pruebas de brazos del Cruzr S2 sin manos.
# La contrasena se deja como valor predeterminado por peticion expresa del usuario.
# Puede sustituirse temporalmente con: CRUZR_SSH_PASSWORD='...' ./script ...

readonly MOTION_HOST="192.168.11.2"
readonly VISION_HOST="192.168.11.3"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly MOTION_CONTAINER="walker-motion.manipulation_robot_app-1"
readonly ROS_CONTAINER="walker-ros.ros2-1"
readonly EXPECTED_HW_TYPE="cruzr_s2_v1"
readonly EXPECTED_IMAGE_FRAGMENT="zs2_motion-v0.26.10"
readonly ACTION_NAME="/mc/manipulation/action"
readonly ACTION_TYPE="mc_task_msgs/action/ArmTask"
readonly CONFIG_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly FIST_XML_SHA256="b9af1013372dee7182f44497b31d1f0f931e188fb44602e19612e2e9101ee430"
readonly WAVE_XML_SHA256="b7024a2721d8d6ee4f4898557a9d8c6d891837495921b784cdd4a226b07c44b7"

readonly -a ALLOWED_TASKS=(
  "fist_up_s2"
  "cruzr/wave_arm"
)

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD

# ssh invoca este mismo archivo como proveedor de contrasena.
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

SCRIPT_PATH="$(readlink -f -- "$0")"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/cruzr_brazos_sin_manos.sh --list
  ./scripts/cruzr_brazos_sin_manos.sh --check
  ./scripts/cruzr_brazos_sin_manos.sh --run fist_up_s2
  ./scripts/cruzr_brazos_sin_manos.sh --run cruzr/wave_arm
  ./scripts/cruzr_brazos_sin_manos.sh --run-all

Opciones:
  --list            Muestra la lista blanca; no conecta ni mueve el robot.
  --check           Ejecuta comprobaciones remotas; no mueve el robot.
  --run TAREA       Ejecuta una sola tarea incluida en la lista blanca.
  --run-all         Ejecuta una vez cada tarea de la lista blanca.
  -h, --help        Muestra esta ayuda.

fist_up_s2 ya se ha ejecutado correctamente en esta unidad. cruzr/wave_arm
es una rutina oficial instalada, exclusivamente de brazo derecho y con retorno
a cero; su primera ejecucion fisica sigue pendiente.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

is_allowed_task() {
  local requested="$1"
  local allowed
  for allowed in "${ALLOWED_TASKS[@]}"; do
    [[ "$requested" == "$allowed" ]] && return 0
  done
  return 1
}

ssh_robot() {
  local host="$1"
  shift

  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w ssh \
    -o ConnectTimeout=6 \
    -o ConnectionAttempts=1 \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -o NumberOfPasswordPrompts=1 \
    -o StrictHostKeyChecking=accept-new \
    "$ROBOT_USER@$host" "$@"
}

ensure_local_network() {
  command -v ssh >/dev/null 2>&1 || die "No esta instalado el cliente ssh."
  command -v setsid >/dev/null 2>&1 || die "No esta instalado setsid (paquete util-linux)."

  if ! ip route get "$MOTION_HOST" 2>/dev/null | grep -qE 'dev eno1( |$)'; then
    info "Activando la conexion Ethernet cruzr-s2..."
    nmcli connection up cruzr-s2 >/dev/null || \
      die "No se pudo activar la conexion NetworkManager cruzr-s2."
  fi

  ip route get "$MOTION_HOST" 2>/dev/null | grep -qE 'dev eno1( |$)' || \
    die "La ruta hacia $MOTION_HOST no utiliza eno1."
}

check_vision_safety_state() {
  local state

  info "Comprobando alimentacion y paradas desde PC vision..."
  state="$(ssh_robot "$VISION_HOST" bash -s -- "$ROS_CONTAINER" <<'REMOTE'
set -Eeuo pipefail
container="$1"

[[ "$(hostname)" == "vision" ]] || {
  printf 'HOST_ERROR=%s\n' "$(hostname)"
  exit 10
}

[[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || {
  printf 'ROS_CONTAINER_ERROR=not_running\n'
  exit 11
}

read_topic() {
  local topic="$1"
  docker exec "$container" bash -lc \
    "source /opt/ros/humble/setup.bash && timeout 8 ros2 topic echo --once '$topic'"
}

printf '%s\n' 'CHARGE_BEGIN'
read_topic /emb/chrg_input_status
printf '%s\n' 'CHARGE_END'
printf '%s\n' 'ESTOP_BEGIN'
read_topic /emb/estop_key_state
printf '%s\n' 'ESTOP_END'
printf '%s\n' 'SERVO_ESTOP_BEGIN'
read_topic /emb/servo_estop_key_state
printf '%s\n' 'SERVO_ESTOP_END'
printf '%s\n' 'POWER_BEGIN'
read_topic /emb/emb_power_state
printf '%s\n' 'POWER_END'
REMOTE
)" || die "No fue posible consultar los estados de seguridad en PC vision."

  printf '%s\n' "$state"

  awk '/CHARGE_BEGIN/{inside=1; next} /CHARGE_END/{inside=0} inside && $1=="data:" && $2==0 {ok=1} END{exit !ok}' \
    <<<"$state" || die "El cargador aparece conectado o su estado no pudo verificarse."
  awk '/ESTOP_BEGIN/{inside=1; next} /ESTOP_END/{inside=0} inside && $1=="data:" && $2==0 {ok=1} END{exit !ok}' \
    <<<"$state" || die "La parada de emergencia trasera no aparece liberada."
  awk '/SERVO_ESTOP_BEGIN/{inside=1; next} /SERVO_ESTOP_END/{inside=0} inside && $1=="data:" && $2==0 {ok=1} END{exit !ok}' \
    <<<"$state" || die "La parada de emergencia de servos no aparece liberada."
  awk '/POWER_BEGIN/{inside=1; next} /POWER_END/{inside=0} inside && $1=="data:" && $2==1 {ok=1} END{exit !ok}' \
    <<<"$state" || die "La alimentacion del robot no aparece activa."
}

check_motion_stack() {
  local report

  info "Comprobando PC motion, contenedor, configuracion y servidor de acciones..."
  report="$(ssh_robot "$MOTION_HOST" bash -s -- \
    "$MOTION_CONTAINER" "$EXPECTED_HW_TYPE" "$EXPECTED_IMAGE_FRAGMENT" \
    "$CONFIG_ROOT/fist_up_s2.xml" "$FIST_XML_SHA256" \
    "$CONFIG_ROOT/cruzr/wave_arm.xml" "$WAVE_XML_SHA256" <<'REMOTE'
set -Eeuo pipefail
container="$1"
expected_hw="$2"
expected_image_fragment="$3"
fist_xml="$4"
expected_fist_hash="$5"
wave_xml="$6"
expected_wave_hash="$7"

[[ "$(hostname)" == "motion" ]] || {
  printf 'HOST_ERROR=%s\n' "$(hostname)"
  exit 20
}

[[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || {
  printf 'MOTION_CONTAINER_ERROR=not_running\n'
  exit 21
}

image="$(docker inspect --format '{{.Config.Image}}' "$container")"
[[ "$image" == *"$expected_image_fragment"* ]] || {
  printf 'IMAGE_ERROR=%s\n' "$image"
  exit 22
}

environment="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$container")"
hw_type="$(awk -F= '$1=="HW_TYPE" {print substr($0, index($0,"=")+1)}' <<<"$environment")"
[[ "$hw_type" == "$expected_hw" ]] || {
  printf 'HW_TYPE_ERROR=%s\n' "$hw_type"
  exit 23
}

# Se bloquea la ejecucion si cualquiera de los XML cambia respecto al auditado.
fist_hash="$(docker exec "$container" sha256sum "$fist_xml" | awk '{print $1}')"
wave_hash="$(docker exec "$container" sha256sum "$wave_xml" | awk '{print $1}')"
[[ "$fist_hash" == "$expected_fist_hash" ]] || {
  printf 'XML_HASH_ERROR=fist_up_s2:%s\n' "$fist_hash"
  exit 24
}
[[ "$wave_hash" == "$expected_wave_hash" ]] || {
  printf 'XML_HASH_ERROR=cruzr/wave_arm:%s\n' "$wave_hash"
  exit 25
}

# Validacion estructural estricta de los XML autorizados. No modifica el robot.
docker exec -i "$container" python3 - "$fist_xml" "$wave_xml" <<'PY'
import math
import sys
import xml.etree.ElementTree as ET

fist_path, wave_path = sys.argv[1:3]
root = ET.parse(fist_path).getroot()
actions = list(root.iter("Action"))

if len(actions) != 4:
    raise SystemExit(f"XML_ERROR=expected_4_actions_got_{len(actions)}")

first = actions[0].attrib
if first != {"ID": "MetaMove", "name": "fist_up_s2"}:
    raise SystemExit(f"XML_ERROR=unexpected_first_action:{first}")

expected = [
    ([-0.11600455542759326, -0.22284199027757054, 1.6370140823263726,
      -2.0491041854479053, -0.12125678074787709, -0.24685907372635257,
      0.5248155226510438], 1.0),
    ([0.11600455542759326, -0.22284199027757054, 1.6370140823263726,
      0.0, -0.12125678074787709, -0.24685907372635257,
      0.5248155226510438], 2.0),
    ([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 5.0),
]

for index, (action, (expected_angles, expected_duration)) in enumerate(
        zip(actions[1:], expected), start=1):
    attrs = action.attrib
    if attrs.get("ID") != "MetaMove" or attrs.get("type") != "arm" or attrs.get("location") != "right":
        raise SystemExit(f"XML_ERROR=unexpected_action_{index}:{attrs}")
    if set(attrs) != {"ID", "type", "location", "joint_angles", "duration"}:
        raise SystemExit(f"XML_ERROR=unexpected_fields_{index}:{attrs}")
    angles = [float(value.strip()) for value in attrs["joint_angles"].split(";") if value.strip()]
    if len(angles) != len(expected_angles) or any(
            not math.isclose(actual, wanted, rel_tol=0.0, abs_tol=1e-12)
            for actual, wanted in zip(angles, expected_angles)):
        raise SystemExit(f"XML_ERROR=unexpected_angles_{index}:{angles}")
    if not math.isclose(float(attrs["duration"]), expected_duration, rel_tol=0.0, abs_tol=1e-12):
        raise SystemExit(f"XML_ERROR=unexpected_duration_{index}:{attrs['duration']}")

print("XML_VALID=fist_up_s2")

wave_root = ET.parse(wave_path).getroot()
wave_actions = list(wave_root.iter("Action"))
if len(wave_actions) != 11:
    raise SystemExit(f"XML_ERROR=wave_expected_11_actions_got_{len(wave_actions)}")

# Limites articulares del brazo derecho publicados en el SDK, en radianes.
joint_limits = [
    (-2.83, 2.83),
    (-1.86, 0.08),
    (-2.92, 2.92),
    (-2.60, 0.02),
    (-2.88, 2.88),
    (-1.60, 1.57),
    (-1.98, 1.98),
]

for index, action in enumerate(wave_actions, start=1):
    attrs = action.attrib
    if attrs.get("ID") != "MetaMove" or attrs.get("type") != "arm" or attrs.get("location") != "right":
        raise SystemExit(f"XML_ERROR=wave_unexpected_action_{index}:{attrs}")
    if set(attrs) != {"ID", "type", "location", "joint_angles", "duration"}:
        raise SystemExit(f"XML_ERROR=wave_unexpected_fields_{index}:{attrs}")
    angles = [float(value.strip()) for value in attrs["joint_angles"].split(";") if value.strip()]
    if len(angles) != 7:
        raise SystemExit(f"XML_ERROR=wave_bad_angle_count_{index}:{angles}")
    if any(not math.isfinite(value) or not (low <= value <= high)
           for value, (low, high) in zip(angles, joint_limits)):
        raise SystemExit(f"XML_ERROR=wave_joint_limit_{index}:{angles}")
    duration = float(attrs["duration"])
    if not math.isfinite(duration) or duration <= 0.0 or duration > 2.0:
        raise SystemExit(f"XML_ERROR=wave_duration_{index}:{duration}")

last_angles = [float(value.strip()) for value in wave_actions[-1].attrib["joint_angles"].split(";")]
if any(abs(value) > 1e-12 for value in last_angles):
    raise SystemExit(f"XML_ERROR=wave_does_not_return_zero:{last_angles}")

print("XML_VALID=cruzr/wave_arm")
PY

printf 'HOSTNAME=%s\n' "$(hostname)"
printf 'IMAGE=%s\n' "$image"
printf 'HW_TYPE=%s\n' "$hw_type"
docker exec "$container" bash -lc \
  'source /opt/walker/setup.bash && rosa action info /mc/manipulation/action'
REMOTE
)" || die "Fallo la validacion del sistema de movimiento. No se ejecutara ninguna accion."

  printf '%s\n' "$report"
  grep -q '^XML_VALID=fist_up_s2$' <<<"$report" || \
    die "La trayectoria fist_up_s2 no coincide con la version validada."
  grep -q '^XML_VALID=cruzr/wave_arm$' <<<"$report" || \
    die "La trayectoria cruzr/wave_arm no coincide con la version validada."
  grep -q 'Action server count: 1' <<<"$report" || \
    die "El servidor /mc/manipulation/action no esta disponible."
  grep -q 'Action client count: 0' <<<"$report" || \
    die "Hay otro cliente conectado al servidor de movimiento."
}

preflight() {
  ensure_local_network
  check_vision_safety_state
  check_motion_stack
  info "Comprobaciones de software superadas."
}

physical_confirmation() {
  local task="$1"
  local answer
  local expected_answer="MOVER"

  if [[ "$task" == "cruzr/wave_arm" ]]; then
    expected_answer="MOVER WAVE"
  fi

  [[ -t 0 ]] || die "La ejecucion de movimientos requiere una terminal interactiva."
  cat <<EOF

CONFIRMACION FISICA OBLIGATORIA
  - Siguiente tarea: $task
  - El robot sigue SIN MANOS y HW_TYPE=cruzr_s2_v1.
  - El cargador esta fisicamente desconectado.
  - Los conectores de muneca estan tapados y los cables sujetos.
  - El robot completo el homing con F abajo + D.
  - Hay al menos 1,5 m libres y nadie esta delante o a la derecha.
  - Tambien hay espacio libre por encima del brazo derecho.
  - Una persona esta preparada junto a la parada de emergencia trasera.
  - El cable Ethernet esta sujeto y la base no se movera.

La detencion normal es H centrado + A. Ante peligro, usa la parada fisica.
EOF
  read -r -p "Escribe exactamente $expected_answer para continuar: " answer
  [[ "$answer" == "$expected_answer" ]] || die "Operacion cancelada por el usuario."
}

run_task() {
  local task="$1"
  local result

  is_allowed_task "$task" || die "Tarea no autorizada: $task"

  info "Ejecutando una sola vez: $task"
  result="$(ssh_robot "$MOTION_HOST" bash -s -- \
    "$MOTION_CONTAINER" "$task" "$ACTION_NAME" "$ACTION_TYPE" <<'REMOTE'
set -Eeuo pipefail
container="$1"
task="$2"
action_name="$3"
action_type="$4"

docker exec "$container" bash -lc \
  "source /opt/walker/setup.bash && rosa action send_goal '$action_name' '$action_type' '{\"task_name\":\"$task\",\"yaml_args\":\"\"}'"
REMOTE
)" || die "La orden fallo. No se repetira automaticamente."

  printf '%s\n' "$result"
  grep -q "desc': 'SUCCEED'" <<<"$result" && grep -q 'status=4' <<<"$result" || \
    die "La accion no devolvio SUCCEED/status=4. No se ejecutaran mas movimientos."

  info "Movimiento completado correctamente: $task"
}

list_tasks() {
  printf 'Tareas validadas sin manos:\n'
  printf '  %s - brazo derecho arriba y retorno automatico a cero\n' "${ALLOWED_TASKS[0]}"
  printf '  %s - saludo amplio con el brazo derecho y retorno a cero; primera prueba pendiente\n' "${ALLOWED_TASKS[1]}"
  printf '\nLas rutinas no incluidas quedan bloqueadas.\n'
}

main() {
  local mode="${1:-}"

  case "$mode" in
    --list)
      [[ $# -eq 1 ]] || die "--list no acepta argumentos."
      list_tasks
      ;;
    --check)
      [[ $# -eq 1 ]] || die "--check no acepta argumentos."
      preflight
      ;;
    --run)
      [[ $# -eq 2 ]] || die "Uso: $0 --run TAREA"
      is_allowed_task "$2" || die "Tarea no incluida en la lista blanca: $2"
      preflight
      physical_confirmation "$2"
      run_task "$2"
      ;;
    --run-all)
      [[ $# -eq 1 ]] || die "--run-all no acepta argumentos."
      local task
      for task in "${ALLOWED_TASKS[@]}"; do
        preflight
        physical_confirmation "$task"
        run_task "$task"
      done
      ;;
    -h|--help)
      usage
      ;;
    *)
      usage
      exit 2
      ;;
  esac
}

main "$@"
