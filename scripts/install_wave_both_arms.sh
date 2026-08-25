#!/usr/bin/env bash

set -Eeuo pipefail

# Instala de forma idempotente la tarea cruzr/wave_both_arms.
# Solo mueve el robot cuando se solicita expresamente con --run o --voice.

readonly MOTION_HOST="192.168.11.2"
readonly VISION_HOST="192.168.11.3"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly MOTION_CONTAINER="walker-motion.manipulation_robot_app-1"
readonly ROS_CONTAINER="walker-ros.ros2-1"
readonly EXPECTED_HW_TYPE="cruzr_s2_v1"
readonly EXPECTED_IMAGE_FRAGMENT="utars-integration:zs2_motion-v0.2.0"
readonly ACTION_NAME="/mc/manipulation/action"
readonly ACTION_TYPE="mc_task_msgs/action/ArmTask"
readonly VOICE_COMMAND="Please wave"
readonly VOICE_TIMEOUT_SECONDS=10
readonly CONFIG_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly SOURCE_TASK="$CONFIG_ROOT/cruzr/wave_arm.xml"
readonly DESTINATION_TASK="$CONFIG_ROOT/cruzr/wave_both_arms.xml"
readonly SOURCE_SHA256="1066811bea5ec8de2e88d0dfb35dba61364b707545254dcba55b8284e156a098"
readonly TEMPLATE_SHA256="09ab80a84a64c7beee1a38718f385af3030fa62a7daa422081f93fd5c0545593"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
VOICE_GUI=0

# ssh/scp invocan este mismo archivo como proveedor de contrasena.
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

SCRIPT_PATH="$(readlink -f -- "$0")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly TEMPLATE="$SCRIPT_DIR/custom_tasks/wave_both_arms.xml"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/install_wave_both_arms.sh             # valida e instala si no existe
  ./scripts/install_wave_both_arms.sh --install   # equivalente al comando anterior
  ./scripts/install_wave_both_arms.sh --check     # solo comprueba; no instala
  ./scripts/install_wave_both_arms.sh --run       # instala si hace falta y ejecuta una vez
  ./scripts/install_wave_both_arms.sh --voice     # ejecuta una vez al oir "Please wave"
  ./scripts/install_wave_both_arms.sh --voice-gui # igual que --voice, con confirmacion grafica
  ./scripts/install_wave_both_arms.sh --voice-check # verifica la voz; nunca mueve el robot
  ./scripts/install_wave_both_arms.sh --help

La instalacion crea la tarea:
  cruzr/wave_both_arms

--install y --check no mueven el robot. --run, --voice y --voice-gui realizan
comprobaciones de seguridad y exigen una confirmacion fisica interactiva o
grafica. La voz se arma una sola vez, acepta exclusivamente la orden inglesa
"Please wave" y se desarma tras ejecutar o al vencer 10 segundos. --voice-check
prueba la misma entrada de voz, pero nunca ejecuta movimientos. El script nunca
reinicia contenedores. Si ya existe un archivo diferente con el mismo nombre,
se niega a sobrescribirlo.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

ssh_host() {
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

ssh_robot() {
  ssh_host "$MOTION_HOST" "$@"
}

scp_robot() {
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w scp \
    -o ConnectTimeout=6 \
    -o ConnectionAttempts=1 \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -o NumberOfPasswordPrompts=1 \
    -o StrictHostKeyChecking=accept-new \
    "$@"
}

ensure_local_network() {
  command -v ssh >/dev/null 2>&1 || die "No esta instalado ssh."
  command -v scp >/dev/null 2>&1 || die "No esta instalado scp."
  command -v setsid >/dev/null 2>&1 || die "No esta instalado setsid."
  command -v sha256sum >/dev/null 2>&1 || die "No esta instalado sha256sum."
  command -v python3 >/dev/null 2>&1 || die "No esta instalado python3."

  if ! ip route get "$MOTION_HOST" 2>/dev/null | grep -qE 'dev eno1( |$)'; then
    info "Activando la conexion Ethernet cruzr-s2..."
    nmcli connection up cruzr-s2 >/dev/null || \
      die "No se pudo activar la conexion NetworkManager cruzr-s2."
  fi

  ip route get "$MOTION_HOST" 2>/dev/null | grep -qE 'dev eno1( |$)' || \
    die "La ruta hacia $MOTION_HOST no utiliza eno1."
  ip route get "$VISION_HOST" 2>/dev/null | grep -qE 'dev eno1( |$)' || \
    die "La ruta hacia $VISION_HOST no utiliza eno1."
}

validate_local_template() {
  local actual_hash

  [[ -f "$TEMPLATE" ]] || die "No existe la plantilla: $TEMPLATE"
  actual_hash="$(sha256sum "$TEMPLATE" | awk '{print $1}')"
  [[ "$actual_hash" == "$TEMPLATE_SHA256" ]] || \
    die "La plantilla local fue modificada (SHA-256: $actual_hash)."

  python3 - "$TEMPLATE" <<'PY'
import math
import sys
import xml.etree.ElementTree as ET

path = sys.argv[1]
root = ET.parse(path).getroot()
parallels = list(root.iter("Parallel"))
if len(parallels) != 3:
    raise SystemExit(f"Se esperaban 3 bloques Parallel; hay {len(parallels)}")

joint_limits = [
    (-2.83, 2.83),
    (-1.86, 0.08),
    (-2.92, 2.92),
    (-2.60, 0.02),
    (-2.88, 2.88),
    (-1.60, 1.57),
    (-1.98, 1.98),
]

for index, parallel in enumerate(parallels, start=1):
    if parallel.attrib != {"threshold": "2"}:
        raise SystemExit(f"Parallel {index} no exige completar ambos brazos")
    actions = list(parallel)
    if len(actions) != 2:
        raise SystemExit(f"Parallel {index} no contiene exactamente dos acciones")
    by_side = {action.attrib.get("location"): action for action in actions}
    if set(by_side) != {"left", "right"}:
        raise SystemExit(f"Parallel {index} no contiene left y right")

    parsed = {}
    for side, action in by_side.items():
        attrs = action.attrib
        if attrs.get("ID") != "MetaMove" or attrs.get("type") != "arm":
            raise SystemExit(f"Accion no permitida en Parallel {index}: {attrs}")
        if set(attrs) != {"ID", "type", "location", "joint_angles", "duration"}:
            raise SystemExit(f"Campos inesperados en Parallel {index}: {attrs}")
        values = [float(value.strip()) for value in attrs["joint_angles"].split(";")]
        if len(values) != 7:
            raise SystemExit(f"El brazo {side} de Parallel {index} no tiene 7 valores")
        if any(not math.isfinite(value) or not (low <= value <= high)
               for value, (low, high) in zip(values, joint_limits)):
            raise SystemExit(f"Limite articular excedido en {side}, Parallel {index}")
        duration = float(attrs["duration"])
        if not math.isclose(duration, 10.0, rel_tol=0.0, abs_tol=1e-12):
            raise SystemExit(f"Duracion no permitida en Parallel {index}: {duration}")
        parsed[side] = values

    if by_side["left"].attrib["duration"] != by_side["right"].attrib["duration"]:
        raise SystemExit(f"Duraciones distintas en Parallel {index}")

    right = parsed["right"]
    expected_left = [-right[0], right[1], -right[2], right[3],
                     -right[4], -right[5], right[6]]
    if any(not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12)
           for actual, expected in zip(parsed["left"], expected_left)):
        raise SystemExit(f"La pose izquierda {index} no es el reflejo de la derecha")

last_actions = list(parallels[-1])
for action in last_actions:
    values = [float(value.strip()) for value in action.attrib["joint_angles"].split(";")]
    if any(abs(value) > 1e-12 for value in values):
        raise SystemExit("La trayectoria no termina con ambos brazos a cero")

expected_right = [
    [-0.423274, -0.336362, 1.27774, -1.20528,
     1.28694, 0.376621, -1.38568],
    [-0.488406, -0.165349, 1.16067, -0.923343,
     1.11991, 0.473442, -1.16333],
]
for index, expected in enumerate(expected_right):
    right = [float(value.strip()) for value in
             list(parallels[index])[1].attrib["joint_angles"].split(";")]
    if any(not math.isclose(actual, wanted, rel_tol=0.0, abs_tol=1e-6)
           for actual, wanted in zip(right, expected)):
        raise SystemExit(f"La pose derecha {index + 1} no coincide con wave_arm v0.2.0")

print("Plantilla local valida: 2 poses oficiales v0.2.0 y retorno bilateral a cero")
PY
}

remote_probe() {
  ssh_robot bash -s -- \
    "$MOTION_CONTAINER" "$EXPECTED_HW_TYPE" "$EXPECTED_IMAGE_FRAGMENT" \
    "$SOURCE_TASK" "$SOURCE_SHA256" "$DESTINATION_TASK" "$TEMPLATE_SHA256" <<'REMOTE'
set -Eeuo pipefail
container="$1"
expected_hw="$2"
expected_image_fragment="$3"
source_task="$4"
source_hash_expected="$5"
destination_task="$6"
template_hash_expected="$7"

[[ "$(hostname)" == "motion" ]] || {
  printf 'HOST_ERROR=%s\n' "$(hostname)"
  exit 20
}
[[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || {
  printf 'CONTAINER_ERROR=not_running\n'
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

source_hash="$(docker exec "$container" sha256sum "$source_task" | awk '{print $1}')"
[[ "$source_hash" == "$source_hash_expected" ]] || {
  printf 'SOURCE_HASH_ERROR=%s\n' "$source_hash"
  exit 24
}

printf 'HOSTNAME=%s\n' "$(hostname)"
printf 'IMAGE=%s\n' "$image"
printf 'HW_TYPE=%s\n' "$hw_type"
printf 'SOURCE_VALID=cruzr/wave_arm\n'

if docker exec "$container" test -e "$destination_task"; then
  destination_hash="$(docker exec "$container" sha256sum "$destination_task" | awk '{print $1}')"
  if [[ "$destination_hash" == "$template_hash_expected" ]]; then
    printf 'DESTINATION=same:%s\n' "$destination_hash"
  else
    printf 'DESTINATION=conflict:%s\n' "$destination_hash"
    exit 25
  fi
else
  printf 'DESTINATION=absent\n'
fi
REMOTE
}

install_task() {
  local staged="/tmp/cruzr_wave_both_arms_$$.xml"
  local report

  info "Copiando la plantilla al PC motion..."
  scp_robot "$TEMPLATE" "$ROBOT_USER@$MOTION_HOST:$staged" >/dev/null || \
    die "No se pudo copiar la plantilla al PC motion."

  report="$(ssh_robot bash -s -- \
    "$MOTION_CONTAINER" "$staged" "$DESTINATION_TASK" "$TEMPLATE_SHA256" <<'REMOTE'
set -Eeuo pipefail
container="$1"
staged="$2"
destination="$3"
expected_hash="$4"
candidate="${destination}.installing.$$"

cleanup() {
  rm -f -- "$staged"
  docker exec "$container" rm -f -- "$candidate" >/dev/null 2>&1 || true
}
trap cleanup EXIT

[[ -f "$staged" ]] || {
  printf 'STAGE_ERROR=missing\n'
  exit 30
}
stage_hash="$(sha256sum "$staged" | awk '{print $1}')"
[[ "$stage_hash" == "$expected_hash" ]] || {
  printf 'STAGE_HASH_ERROR=%s\n' "$stage_hash"
  exit 31
}

if docker exec "$container" test -e "$destination"; then
  existing_hash="$(docker exec "$container" sha256sum "$destination" | awk '{print $1}')"
  if [[ "$existing_hash" == "$expected_hash" ]]; then
    printf 'INSTALLATION=already_present:%s\n' "$existing_hash"
    exit 0
  fi
  printf 'INSTALLATION=conflict:%s\n' "$existing_hash"
  exit 32
fi

docker cp "$staged" "$container:$candidate"
docker exec "$container" python3 -c \
  'import sys, xml.etree.ElementTree as ET; ET.parse(sys.argv[1])' "$candidate"
candidate_hash="$(docker exec "$container" sha256sum "$candidate" | awk '{print $1}')"
[[ "$candidate_hash" == "$expected_hash" ]] || {
  printf 'CANDIDATE_HASH_ERROR=%s\n' "$candidate_hash"
  exit 33
}

# El enlace duro falla atomicamente si otro proceso crea el destino.
docker exec "$container" chmod 0644 "$candidate"
if ! docker exec "$container" ln "$candidate" "$destination"; then
  if docker exec "$container" test -e "$destination"; then
    existing_hash="$(docker exec "$container" sha256sum "$destination" | awk '{print $1}')"
    [[ "$existing_hash" == "$expected_hash" ]] || {
      printf 'INSTALLATION=conflict_after_race:%s\n' "$existing_hash"
      exit 34
    }
    printf 'INSTALLATION=already_present:%s\n' "$existing_hash"
    exit 0
  fi
  printf 'INSTALLATION=link_failed\n'
  exit 35
fi

installed_hash="$(docker exec "$container" sha256sum "$destination" | awk '{print $1}')"
[[ "$installed_hash" == "$expected_hash" ]] || {
  printf 'INSTALLATION=final_hash_error:%s\n' "$installed_hash"
  exit 36
}
printf 'INSTALLATION=created:%s\n' "$installed_hash"
REMOTE
)" || die "La instalacion fallo; no se ha sobrescrito ninguna tarea existente."

  printf '%s\n' "$report"
}

check_vision_safety_state() {
  local state

  info "Comprobando cargador, paradas de emergencia y alimentacion..."
  state="$(ssh_host "$VISION_HOST" bash -s -- "$ROS_CONTAINER" <<'REMOTE'
set -Eeuo pipefail
container="$1"

[[ "$(hostname)" == "vision" ]] || {
  printf 'HOST_ERROR=%s\n' "$(hostname)"
  exit 40
}
[[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || {
  printf 'ROS_CONTAINER_ERROR=not_running\n'
  exit 41
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

check_action_server() {
  local report

  info "Comprobando el servidor de movimiento..."
  report="$(ssh_robot bash -s -- \
    "$MOTION_CONTAINER" "$ROS_CONTAINER" "$DESTINATION_TASK" "$TEMPLATE_SHA256" <<'REMOTE'
set -Eeuo pipefail
container="$1"
ros_container="$2"
task_file="$3"
expected_hash="$4"

actual_hash="$(docker exec "$container" sha256sum "$task_file" | awk '{print $1}')"
[[ "$actual_hash" == "$expected_hash" ]] || {
  printf 'TASK_HASH_ERROR=%s\n' "$actual_hash"
  exit 42
}
printf 'TASK_HASH_VALID=%s\n' "$actual_hash"
docker exec "$container" bash -lc \
  'source /opt/walker/setup.bash && rosa action info /mc/manipulation/action'

action_status="$(docker exec "$ros_container" bash -lc '
  source /opt/ros/humble/setup.bash
  export ROS2CLI_DISABLE_DAEMON=1
  timeout 8 ros2 topic echo --once /mc/manipulation/action/_action/status
')"
if awk '$1 == "status:" && ($2 == 1 || $2 == 2 || $2 == 3) {busy=1} END {exit !busy}' \
    <<<"$action_status"; then
  echo ACTION_BUSY=motion_goal_active
  exit 44
fi
echo ACTION_STATUS_IDLE=1
REMOTE
)" || die "No fue posible validar el servidor de movimiento."

  printf '%s\n' "$report"
  grep -q '^TASK_HASH_VALID=' <<<"$report" || \
    die "La tarea instalada no coincide con la version validada."
  grep -q 'Action server count: 1' <<<"$report" || \
    die "El servidor $ACTION_NAME no esta disponible."
  grep -q '^ACTION_STATUS_IDLE=1$' <<<"$report" || \
    die "Hay un objetivo activo en el servidor de movimiento."
}

confirm_physical_safety() {
  local confirmation_mode="${1:-manual}"
  local answer
  local expected_answer="MOVER AMBOS BRAZOS"

  if [[ "$confirmation_mode" == "voice-gui" ]]; then
    command -v zenity >/dev/null 2>&1 || die "No esta instalado zenity."
    zenity --question \
      --title="Armar movimiento de brazos del Cruzr S2" \
      --width=620 \
      --ok-label="Armar durante 10 segundos" \
      --cancel-label="Cancelar" \
      --text=$'Confirma antes de continuar:\n\n• El robot sigue SIN MANOS y los conectores están tapados.\n• El cargador está físicamente desconectado.\n• El homing se completó correctamente.\n• Hay 1,5 m libres alrededor y sobre los brazos.\n• Nadie está dentro del alcance.\n• Una persona está junto a la parada de emergencia.\n• El cable Ethernet está sujeto y la base permanecerá inmóvil.\n\nDespués de armar, di exactamente: Please wave' || \
      die "Operacion cancelada por el usuario."
    return
  fi

  if [[ "$confirmation_mode" == "voice" ]]; then
    expected_answer="ARMAR VOZ"
  fi

  [[ -t 0 ]] || die "La ejecucion requiere una terminal interactiva."
  cat <<'EOF'

CONFIRMACION FISICA OBLIGATORIA
  - El robot sigue SIN MANOS y los conectores de muneca estan tapados.
  - El cargador esta fisicamente desconectado.
  - El robot completo el homing con F abajo + D.
  - Hay al menos 1,5 m libres delante, a ambos lados y sobre los brazos.
  - Nadie esta dentro del alcance de los brazos.
  - Una persona esta preparada junto a la parada de emergencia trasera.
  - El cable Ethernet esta sujeto y la base permanecera inmovil.

La tarea movera los dos brazos durante unos 30 segundos y deberia devolverlos
a cero. Detencion normal: H centrado + A. Ante peligro: parada fisica.
EOF
  if [[ "$confirmation_mode" == "voice" ]]; then
    cat <<EOF
  - Despues de armarse escuchara durante $VOICE_TIMEOUT_SECONDS segundos.
  - Solo aceptara la orden inglesa: $VOICE_COMMAND
  - La transcripcion debe coincidir exactamente con "please wave".
  - Se desarmara automaticamente despues de una unica ejecucion.
EOF
  fi
  read -r -p "Escribe exactamente $expected_answer para continuar: " answer
  [[ "$answer" == "$expected_answer" ]] || die "Operacion cancelada por el usuario."
}

start_voice_session() {
  info "Preparando ASR ingles sin conectar la salida al LLM averiado..."
  ssh_host "$VISION_HOST" bash -s -- "$ROS_CONTAINER" <<'REMOTE'
set -Eeuo pipefail
container="$1"

call_bool() {
  local service="$1"
  local value="$2"
  local output

  output="$(docker exec "$container" bash -lc \
    "source /opt/ros/humble/setup.bash && ros2 service call '$service' std_srvs/srv/SetBool '{data: $value}'")"
  printf '%s\n' "$output"
  grep -Eq 'success=(True|true)' <<<"$output" || \
    grep -Eqi 'already (enabled|disabled)' <<<"$output"
}

# Estado aislado que ya fue validado manualmente en esta unidad.
call_bool /sys/run_chatting/enable false
call_bool /sys/llm_in/enable false
call_bool /sys/llm_out/enable false
call_bool /sys/asr/enable true
call_bool /sys/run_chatting/enable true
REMOTE
}

stop_voice_session() {
  info "Desarmando el reconocimiento de voz..."
  ssh_host "$VISION_HOST" bash -s -- "$ROS_CONTAINER" <<'REMOTE'
set +e
container="$1"

call_bool() {
  local service="$1"
  local value="$2"
  docker exec "$container" bash -lc \
    "source /opt/ros/humble/setup.bash && ros2 service call '$service' std_srvs/srv/SetBool '{data: $value}'" \
    >/dev/null 2>&1
}

call_bool /sys/run_chatting/enable false
# Restaurar los valores predeterminados; con run_chatting=false no se inicia el LLM.
call_bool /sys/llm_in/enable true
call_bool /sys/llm_out/enable true
REMOTE
}

relay_voice_output() {
  local line

  while IFS= read -r line; do
    printf '%s\n' "$line"
    if [[ "$VOICE_GUI" -eq 1 && "$line" == VOICE_LISTENER_READY:* ]]; then
      notify-send -u critical -t 10000 "Cruzr S2: voz armada" \
        "Di ahora: Please wave" || true
    fi
  done
}

listen_for_voice_command() {
  info "Escuchando: $VOICE_COMMAND"
  ssh_host "$VISION_HOST" bash -s -- \
    "$ROS_CONTAINER" "$VOICE_TIMEOUT_SECONDS" <<'REMOTE' | relay_voice_output
set -Eeuo pipefail
container="$1"
timeout_seconds="$2"

speech_log="$(find /etc/walker/log/voice_client -maxdepth 1 -type f \
  -name 'speech_service.*.log' -printf '%T@ %p\n' 2>/dev/null | \
  sort -nr | head -n 1 | cut -d' ' -f2-)"
[[ -n "$speech_log" && -r "$speech_log" ]] || {
  printf 'VOICE_ASR_ENGINE_LOG: no disponible\n' >&2
  exit 48
}
speech_log_offset="$(stat -c '%s' "$speech_log")"

wake_output="$(docker exec "$container" bash -lc \
  "source /opt/ros/humble/setup.bash && timeout 8 ros2 service call \
  /sys/wake/enable std_srvs/srv/SetBool '{data: true}'")" || {
  printf '%s\n' "$wake_output" >&2
  printf 'WAKE_ERROR: no se pudo activar la escucha\n' >&2
  exit 45
}
printf '%s\n' "$wake_output"
grep -Eq 'success=(True|true)' <<<"$wake_output" || {
  printf 'WAKE_ERROR: respuesta sin confirmacion\n' >&2
  exit 47
}

printf 'WAKE_OK: alarm wake\n'
printf "VOICE_LISTENER_READY: diga ahora 'please wave'\n"

python3 - "$speech_log" "$speech_log_offset" "$timeout_seconds" <<'PY'
import os
import re
import sys
import time
import unicodedata

log_path = sys.argv[1]
offset = int(sys.argv[2])
timeout_seconds = float(sys.argv[3])
initial_offset = offset
pattern = re.compile(r"\[sp_service_asr\.cpp:76:asrCallback\]: query:(.*)$")
buffer = ""
events = 0


def normalize(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[^a-z]+", " ", text)
    return " ".join(text.split())


def process(line):
    global events
    match = pattern.search(line)
    if not match:
        return False
    raw = match.group(1).strip()
    heard = normalize(raw)
    events += 1
    print(f"VOICE_ASR_ENGINE_HEARD: {raw}", flush=True)
    if heard == "please wave":
        print(
            "VOICE_COMMAND_MATCH=wave_both_arms "
            "[source=asr-engine-log asr=please_wave]",
            flush=True,
        )
        return True
    print("IGNORED: el motor ASR no entendio exactamente 'please wave'", flush=True)
    return False


# El wake permanece abierto 10 s. Se concede un pequeno margen para que glog
# escriba el resultado final, pero se retorna en cuanto aparece la orden exacta.
deadline = time.monotonic() + timeout_seconds + 2.0
with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
    handle.seek(offset)
    while time.monotonic() < deadline:
        size = os.path.getsize(log_path)
        if size < offset:
            print("VOICE_ASR_ENGINE_LOG: truncado durante la escucha", file=sys.stderr)
            raise SystemExit(49)

        chunk = handle.read()
        offset = handle.tell()
        if chunk:
            buffer += chunk
            lines = buffer.split("\n")
            buffer = lines.pop()
            for line in lines:
                if process(line):
                    raise SystemExit(0)
        time.sleep(0.1)

if buffer and process(buffer):
    raise SystemExit(0)

print(f"VOICE_ASR_ENGINE_EVENTS={events}", file=sys.stderr, flush=True)
print(f"VOICE_ASR_ENGINE_LOG_BYTES={offset - initial_offset}", file=sys.stderr, flush=True)
print("VOICE_TIMEOUT: no se recibio la orden esperada", file=sys.stderr, flush=True)
raise SystemExit(44)
PY
REMOTE
}

run_task() {
  local result

  info "Ejecutando una sola vez: cruzr/wave_both_arms"
  result="$(ssh_robot bash -s -- \
    "$MOTION_CONTAINER" "$DESTINATION_TASK" "$TEMPLATE_SHA256" \
    "$ACTION_NAME" "$ACTION_TYPE" <<'REMOTE'
set -Eeuo pipefail
container="$1"
task_file="$2"
expected_hash="$3"
action_name="$4"
action_type="$5"

# Verificacion final inmediatamente antes de enviar el objetivo.
actual_hash="$(docker exec "$container" sha256sum "$task_file" | awk '{print $1}')"
[[ "$actual_hash" == "$expected_hash" ]] || {
  printf 'TASK_HASH_ERROR=%s\n' "$actual_hash"
  exit 43
}

docker exec "$container" bash -lc \
  "source /opt/walker/setup.bash && rosa action send_goal '$action_name' '$action_type' '{\"task_name\":\"cruzr/wave_both_arms\",\"yaml_args\":\"\"}'"
REMOTE
)" || die "La orden fallo. No se repetira automaticamente."

  printf '%s\n' "$result"
  grep -q "desc': 'SUCCEED'" <<<"$result" && grep -q 'status=4' <<<"$result" || \
    die "La accion no devolvio SUCCEED/status=4. No la repitas."
  info "Movimiento completado: cruzr/wave_both_arms"
}

main() {
  local mode="${1:---install}"
  local probe

  case "$mode" in
    --help|-h)
      usage
      exit 0
      ;;
    --check|--install|--run|--voice|--voice-gui|--voice-check)
      [[ $# -le 1 ]] || die "Demasiados argumentos."
      ;;
    *)
      usage
      exit 2
      ;;
  esac

  if [[ "$mode" == "--voice-gui" ]]; then
    VOICE_GUI=1
    command -v zenity >/dev/null 2>&1 || die "No esta instalado zenity."
    command -v notify-send >/dev/null 2>&1 && \
      notify-send "Cruzr S2" "Comprobando el robot antes de armar la voz..." || true
  fi

  ensure_local_network

  if [[ "$mode" == "--voice-check" ]]; then
    start_voice_session || die "No se pudo preparar el reconocimiento de voz."
    trap 'stop_voice_session >/dev/null 2>&1 || true' EXIT INT TERM
    listen_for_voice_command || die "No se recibio la frase exacta."
    stop_voice_session
    trap - EXIT INT TERM
    info "Voz validada correctamente. No se ha ejecutado ningun movimiento."
    exit 0
  fi

  validate_local_template

  info "Comprobando el PC motion y la tarea oficial cruzr/wave_arm..."
  probe="$(remote_probe)" || \
    die "La comprobacion remota fallo. No se realizo ningun cambio."
  printf '%s\n' "$probe"

  if grep -q '^DESTINATION=same:' <<<"$probe"; then
    info "La tarea cruzr/wave_both_arms ya esta instalada y coincide con la plantilla."
  else
    grep -q '^DESTINATION=absent$' <<<"$probe" || \
      die "Estado de destino inesperado. No se realizo ningun cambio."

    if [[ "$mode" == "--check" ]]; then
      info "Comprobacion superada: la tarea no existe y esta lista para instalarse."
      exit 0
    fi

    install_task

    info "Verificando la instalacion final..."
    probe="$(remote_probe)" || die "No se pudo verificar la instalacion final."
    printf '%s\n' "$probe"
    grep -q '^DESTINATION=same:' <<<"$probe" || \
      die "La tarea instalada no coincide con la plantilla validada."
    info "Tarea instalada: cruzr/wave_both_arms"
  fi

  if [[ "$mode" != "--run" && "$mode" != "--voice" && "$mode" != "--voice-gui" ]]; then
    info "No se ha ejecutado ningun movimiento."
    exit 0
  fi

  check_vision_safety_state
  check_action_server

  if [[ "$mode" == "--voice" || "$mode" == "--voice-gui" ]]; then
    if [[ "$mode" == "--voice-gui" ]]; then
      confirm_physical_safety voice-gui
    else
      confirm_physical_safety voice
    fi
    start_voice_session || die "No se pudo preparar el reconocimiento de voz."
    trap 'stop_voice_session >/dev/null 2>&1 || true' EXIT INT TERM
    listen_for_voice_command || die "No se recibio la frase exacta; no se movera el robot."
    stop_voice_session
    trap - EXIT INT TERM

    info "Orden de voz validada. Repitiendo comprobaciones antes del movimiento..."
    check_vision_safety_state
    check_action_server
  else
    confirm_physical_safety manual
  fi

  run_task
}

main "$@"
