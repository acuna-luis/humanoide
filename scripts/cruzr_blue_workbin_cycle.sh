#!/usr/bin/env bash

set -Eeuo pipefail

# Ciclo autónomo para el contenedor azul 600 x 400 x 220 mm del Cruzr S2.
# Se ejecuta desde el PC Ubuntu y no mueve el chasis.

readonly MOTION_HOST="192.168.11.2"
readonly WIFI_GATEWAY="192.168.42.2"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly MOTION_CONTAINER="walker-motion.manipulation_robot_app-1"
readonly ROS_CONTAINER="walker-ros.ros2-1"
readonly EXPECTED_HW_TYPE="cruzr_s2_v1"
readonly EXPECTED_IMAGE_FRAGMENT="zs2_motion-v0.26.10"
readonly CONFIG_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly META_ROOT="/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config"
readonly MIN_BATTERY_SOC="30"
readonly DEFAULT_HOLD_SECONDS="5"
readonly ACTION_NAME="/mc/manipulation/action"
readonly ACTION_TYPE="mc_task_msgs/action/ArmTask"
readonly VISION_ACTION="/cv/task/transport_action"
readonly VISION_TYPE="cv_task_msgs/action/VisionActionTask"

readonly HEAD_LOWER_TASK="cruzr/move_head_lower"
readonly ARMS_READY_TASK="transport/clamp_ready_cruzr"
readonly DETECT_TASK="cruzr/blue_workbin_detect_only"
readonly CLAMP_TASK="cruzr/blue_workbin_clamp_only"
readonly DEPOSIT_TASK="cruzr/blue_workbin_auto_deposit"
readonly HOME_TASK="cruzr/home"

readonly HEAD_LOWER_SHA="f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1"
readonly ARMS_READY_SHA="1527ca90105d70d7c8acda3310d15cec1a354a9938e8f30d11e11d2e923f4be7"
readonly HOME_SHA="50d819d6d6190280c6efee1dc275877362c3f7c807ec733fbc3c7ed217daed88"
readonly CLAMP_META_SHA="e8ec65bc73ac15b06977425778363b1cfb5258c64d08eb36b2d55422b198166e"
readonly DEPOSIT_META_SHA="c2fd11113b8acc21eb970519c6e6679a3666dfa42fe3e98a005f2b404b38aa07"
readonly OPEN_META_SHA="c0265aad37fc5f42f4b260a9707f6393a34607b9fb1919a9d5b5db381b2999eb"

readonly DETECT_TEMPLATE_SHA="cf32fbeb905e8fe7f7a3c3c58429044cc96ee79956c8c1060a6787b201028a4b"
readonly CLAMP_TEMPLATE_SHA="76509f5694f0d73d71f65c59f12abc8f4e7740f3704cfdda7b56eca5d6dc0209"
readonly DEPOSIT_TEMPLATE_SHA="b6b1fbf078b0d8447078b49853d698fd39ffbe6250184b221d1e0b448ebc1f5b"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD

# ssh/scp usan este mismo archivo como proveedor de contraseña.
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

SCRIPT_PATH="$(readlink -f -- "$0")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly SCRIPT_PATH SCRIPT_DIR
readonly TEMPLATE_DIR="$SCRIPT_DIR/custom_tasks"
readonly DETECT_TEMPLATE="$TEMPLATE_DIR/test_blue_workbin_detect_only.xml"
readonly CLAMP_TEMPLATE="$TEMPLATE_DIR/test_blue_workbin_clamp_only.xml"
readonly DEPOSIT_TEMPLATE="$TEMPLATE_DIR/blue_workbin_auto_deposit.xml"

MODE="check"
YES=0
FAST=0
FLUID_MODE="${CRUZR_FLUID_MODE:-0}"
HOLD_SECONDS="$DEFAULT_HOLD_SECONDS"
CONNECTION_MODE=""
GRASP_REPORT=""
declare -a ROUTE_ARGS=()
declare -a VISION_SAMPLES=()

usage() {
  cat <<'EOF'
Uso:
  ./scripts/cruzr_blue_workbin_cycle.sh --check
  ./scripts/cruzr_blue_workbin_cycle.sh --install
  ./scripts/cruzr_blue_workbin_cycle.sh --run [--hold SEGUNDOS] [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_cycle.sh --grasp [--yes]
  ./scripts/cruzr_blue_workbin_cycle.sh --verify-grasp
  ./scripts/cruzr_blue_workbin_cycle.sh --deposit-held [--yes]
  ./scripts/cruzr_blue_workbin_cycle.sh --home [--yes]
  ./scripts/cruzr_blue_workbin_cycle.sh --prepare-vision [--yes]
  ./scripts/cruzr_blue_workbin_cycle.sh --measure-box
  ./scripts/cruzr_blue_workbin_cycle.sh --measure-box-fast
  ./scripts/cruzr_blue_workbin_cycle.sh --grasp-after-approach [--yes]

Modos:
  --check    Comprueba PC, robot, versión, acciones, paros y batería. No mueve
             ni instala nada.
  --install  Valida e instala las tres tareas auxiliares. No mueve el robot.
  --run      Ejecuta sin pausas intermedias: cabeza abajo, brazos preparados,
             dos detecciones, agarre/elevación, espera, depósito por contacto
             con la mesa y apertura BYD. Nunca mueve el chasis.
  --grasp    Ejecuta detección, agarre y elevación, y termina manteniendo la
             caja sujeta. No mueve el chasis ni deposita la caja.
  --verify-grasp
             Comprueba en el registro actual que el último agarre terminó con
             contacto válido y que después no se ordenó abrir, depositar o home.
  --deposit-held
             Verifica un agarre vigente, baja hasta contacto con el apoyo y
             abre los cogedores. No mueve el chasis.
  --home     Devuelve brazos, cabeza, cintura y elevador a cero. Úsese solo
             después de retirar caja y mesa.
  --prepare-vision
             Baja únicamente la cabeza para observar la caja; no mueve brazos
             ni chasis.
  --measure-box
             Obtiene tres poses estables de la caja; no mueve el robot.
  --measure-box-fast
             Obtiene dos poses estables sin repetir el diagnóstico completo;
             está reservado al bucle de aproximación y no mueve el robot.
  --grasp-after-approach
             Prepara brazos, revalida la caja y ejecuta el agarre. Presupone
             que --prepare-vision y la aproximación del chasis ya terminaron.

Opciones:
  --hold N   Mantiene la caja elevada N segundos (0-30; por defecto 5).
  --yes      Omite la única confirmación inicial. Implica que la zona está
             despejada, las manos están fuera y el paro está preparado.
  --fast     Omite diagnósticos, hashes e instalación repetidos. Úsese solo
             cuando el flujo exterior ya validó paros y cargador.
  --help     Muestra esta ayuda.

Preparación física para --run:
  - Robot inicialmente en home y desconectado del cargador.
  - Contenedor rígido 600 x 400 x 220 mm, vacío y estable sobre una mesa.
  - Lado de 600 mm paralelo a los hombros; caja centrada frente al robot.
  - Ninguna persona ni objeto dentro de la envolvente de brazos o de caída.
  - Paro de emergencia accesible durante todo el ciclo.

El ciclo termina con los cogedores abiertos junto a la caja. No vuelve a home
automáticamente porque la mesa sigue ocupando la trayectoria de los brazos.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

warn() {
  printf 'AVISO: %s\n' "$*" >&2
}

while (($#)); do
  case "$1" in
    --check|--install|--run|--grasp|--verify-grasp|--deposit-held|--home|--prepare-vision|--measure-box|--measure-box-fast|--grasp-after-approach)
      MODE="${1#--}"
      ;;
    --hold)
      shift
      (($#)) || die "--hold requiere un valor."
      HOLD_SECONDS="$1"
      ;;
    --yes)
      YES=1
      ;;
    --fast)
      FAST=1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "Opción desconocida: $1"
      ;;
  esac
  shift
done

[[ "$HOLD_SECONDS" =~ ^[0-9]+$ ]] || die "--hold debe ser un entero."
((HOLD_SECONDS >= 0 && HOLD_SECONDS <= 30)) || \
  die "--hold debe estar entre 0 y 30 segundos."

require_local_tools() {
  local command_name
  for command_name in ssh scp setsid sha256sum python3 nc flock readlink; do
    command -v "$command_name" >/dev/null 2>&1 || \
      die "Falta el comando local '$command_name'."
  done
}

select_connection() {
  if nc -z -w2 "$MOTION_HOST" 22 >/dev/null 2>&1; then
    CONNECTION_MODE="directa a motion"
    ROUTE_ARGS=()
  elif nc -z -w2 "$WIFI_GATEWAY" 22 >/dev/null 2>&1; then
    CONNECTION_MODE="Wi-Fi mediante vision"
    ROUTE_ARGS=(
      -o "ProxyCommand=ssh -o ConnectTimeout=6 -o ConnectionAttempts=1 -o PreferredAuthentications=password -o PubkeyAuthentication=no -o NumberOfPasswordPrompts=1 -o StrictHostKeyChecking=accept-new -W %h:%p $ROBOT_USER@$WIFI_GATEWAY"
    )
  else
    die "No se alcanza motion ($MOTION_HOST) ni la pasarela Wi-Fi ($WIFI_GATEWAY)."
  fi
  info "Conexión: $CONNECTION_MODE"
}

ssh_motion() {
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
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
    "${ROUTE_ARGS[@]}" \
    "$ROBOT_USER@$MOTION_HOST" "$@"
}

scp_motion() {
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w scp \
    -o ConnectTimeout=8 \
    -o ConnectionAttempts=1 \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -o NumberOfPasswordPrompts=2 \
    -o StrictHostKeyChecking=accept-new \
    "${ROUTE_ARGS[@]}" "$@"
}

validate_templates() {
  [[ "$(sha256sum "$DETECT_TEMPLATE" | awk '{print $1}')" == "$DETECT_TEMPLATE_SHA" ]] || \
    die "La plantilla de detección no coincide con su SHA-256 esperado."
  [[ "$(sha256sum "$CLAMP_TEMPLATE" | awk '{print $1}')" == "$CLAMP_TEMPLATE_SHA" ]] || \
    die "La plantilla de agarre no coincide con su SHA-256 esperado."
  [[ "$(sha256sum "$DEPOSIT_TEMPLATE" | awk '{print $1}')" == "$DEPOSIT_TEMPLATE_SHA" ]] || \
    die "La plantilla de depósito no coincide con su SHA-256 esperado."

  python3 - "$DETECT_TEMPLATE" "$CLAMP_TEMPLATE" "$DEPOSIT_TEMPLATE" <<'PY'
import sys
import xml.etree.ElementTree as ET

detect_path, clamp_path, deposit_path = sys.argv[1:]

def actions(path):
    root = ET.parse(path).getroot()
    return [element.attrib for element in root.iter("Action")]

detect = actions(detect_path)
clamp = actions(clamp_path)
deposit = actions(deposit_path)

if len(detect) != 2 or detect[0].get("start_vision_mode") != "transport_vision":
    raise SystemExit("Plantilla de detección inesperada")
if detect[1].get("task_type") != "transport" or detect[1].get("box_size") != "0.60;0.40;0.22":
    raise SystemExit("Dimensiones o acción de detección inesperadas")
if len(clamp) != 3 or clamp[-1] != {"ID": "MetaClamp", "name": "clamp_cruzr_byd_large"}:
    raise SystemExit("Plantilla de agarre inesperada")
if deposit != [
    {"ID": "MetaClamp", "name": "put_collision_cruzr"},
    {"ID": "MetaClamp", "name": "byd/open_arm_cruzr"},
]:
    raise SystemExit("Plantilla de depósito inesperada")
print("Plantillas XML locales válidas")
PY
}

remote_preflight() {
  ssh_motion bash -s -- \
    "$MOTION_CONTAINER" "$ROS_CONTAINER" "$EXPECTED_HW_TYPE" \
    "$EXPECTED_IMAGE_FRAGMENT" "$HEAD_LOWER_SHA" "$ARMS_READY_SHA" \
    "$HOME_SHA" "$CLAMP_META_SHA" "$DEPOSIT_META_SHA" "$OPEN_META_SHA" \
    "$MIN_BATTERY_SOC" <<'REMOTE'
set -Eeuo pipefail
motion_container="$1"
ros_container="$2"
expected_hw="$3"
expected_image="$4"
head_sha="$5"
ready_sha="$6"
home_sha="$7"
clamp_meta_sha="$8"
deposit_meta_sha="$9"
open_meta_sha="${10}"
min_soc="${11}"

[[ "$(hostname)" == "motion" ]] || {
  echo "HOST_ERROR=$(hostname)"
  exit 20
}

for container in "$motion_container" "$ros_container"; do
  [[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || {
    echo "CONTAINER_ERROR=$container"
    exit 21
  }
done

image="$(docker inspect --format '{{.Config.Image}}' "$motion_container")"
[[ "$image" == *"$expected_image"* ]] || {
  echo "IMAGE_ERROR=$image"
  exit 22
}

environment="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$motion_container")"
hw_type="$(awk -F= '$1=="HW_TYPE" {print substr($0,index($0,"=")+1)}' <<<"$environment")"
[[ "$hw_type" == "$expected_hw" ]] || {
  echo "HW_TYPE_ERROR=$hw_type"
  exit 23
}

check_hash() {
  local expected="$1"
  local path="$2"
  local actual
  actual="$(docker exec "$motion_container" sha256sum "$path" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || {
    echo "HASH_ERROR=$path:$actual"
    exit 24
  }
}

task_root="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
meta_root="/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config"
check_hash "$head_sha" "$task_root/cruzr/move_head_lower.xml"
check_hash "$ready_sha" "$task_root/transport/clamp_ready_cruzr.xml"
check_hash "$home_sha" "$task_root/cruzr/home.xml"
check_hash "$clamp_meta_sha" "$meta_root/meta_clamp/clamp_cruzr_byd_large.yaml"
check_hash "$deposit_meta_sha" "$meta_root/meta_clamp/put_collision_cruzr.yaml"
check_hash "$open_meta_sha" "$meta_root/meta_clamp/byd/open_arm_cruzr.yaml"

motion_info="$(docker exec "$motion_container" bash -lc 'source /opt/walker/setup.bash; rosa action info /mc/manipulation/action')"
vision_info="$(docker exec "$motion_container" bash -lc 'source /opt/walker/setup.bash; rosa action info /cv/task/transport_action')"
grep -q 'Action server count: 1' <<<"$motion_info" || exit 25
grep -q 'Action server count: 1' <<<"$vision_info" || exit 26
grep -q 'Action client count: 0' <<<"$motion_info" || {
  echo "ACTION_BUSY=motion"
  exit 27
}

topic_once() {
  local topic="$1"
  docker exec "$ros_container" bash -lc \
    "source /opt/ros/humble/setup.bash; timeout 8 ros2 topic echo --no-daemon --once '$topic'"
}

estop="$(topic_once /emb/estop_key_state)"
servo_estop="$(topic_once /emb/servo_estop_key_state)"
[[ "$(awk '/data:/ {print $2; exit}' <<<"$estop")" == "0" ]] || exit 28
[[ "$(awk '/data:/ {print $2; exit}' <<<"$servo_estop")" == "0" ]] || exit 29

battery="$(topic_once /emb/battery_state)"
mapfile -t socs < <(awk '/batsoc:/ {print $2}' <<<"$battery")
[[ "${#socs[@]}" == "2" ]] || exit 30
for soc in "${socs[@]}"; do
  awk -v soc="$soc" -v minimum="$min_soc" 'BEGIN {exit !(soc >= minimum)}' || {
    echo "BATTERY_LOW=$soc"
    exit 31
  }
done

charge="$(topic_once /emb/chrg_input_status)"
[[ "$(awk '/data:/ {print $2; exit}' <<<"$charge")" == "0" ]] || {
  echo "CHARGER_CONNECTED=1"
  exit 32
}

printf 'HOST=motion\nIMAGE=%s\nHW_TYPE=%s\n' "$image" "$hw_type"
printf 'BATTERY_1=%s\nBATTERY_2=%s\n' "${socs[0]}" "${socs[1]}"
printf 'ESTOPS=0,0\nCHARGER=disconnected\nACTIONS=ready\n'
REMOTE
}

install_one_template() {
  local source_path="$1"
  local destination_relative="$2"
  local expected_hash="$3"
  local staged="/tmp/cruzr_blue_workbin_${$}_$(basename -- "$source_path")"

  scp_motion "$source_path" "$ROBOT_USER@$MOTION_HOST:$staged" >/dev/null
  ssh_motion bash -s -- "$MOTION_CONTAINER" "$staged" \
    "$CONFIG_ROOT/$destination_relative" "$expected_hash" <<'REMOTE'
set -Eeuo pipefail
container="$1"
staged="$2"
destination="$3"
expected="$4"
trap 'rm -f -- "$staged"' EXIT

staged_hash="$(sha256sum "$staged" | awk '{print $1}')"
[[ "$staged_hash" == "$expected" ]] || exit 40

if docker exec "$container" test -e "$destination"; then
  actual="$(docker exec "$container" sha256sum "$destination" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || {
    echo "DESTINATION_CONFLICT=$destination:$actual"
    exit 41
  }
  echo "TASK_PRESENT=$destination"
  exit 0
fi

docker exec "$container" mkdir -p "$(dirname -- "$destination")"
docker cp "$staged" "$container:$destination"
actual="$(docker exec "$container" sha256sum "$destination" | awk '{print $1}')"
[[ "$actual" == "$expected" ]] || exit 42
echo "TASK_INSTALLED=$destination"
REMOTE
}

install_templates() {
  install_one_template "$DETECT_TEMPLATE" "cruzr/blue_workbin_detect_only.xml" "$DETECT_TEMPLATE_SHA"
  install_one_template "$CLAMP_TEMPLATE" "cruzr/blue_workbin_clamp_only.xml" "$CLAMP_TEMPLATE_SHA"
  install_one_template "$DEPOSIT_TEMPLATE" "cruzr/blue_workbin_auto_deposit.xml" "$DEPOSIT_TEMPLATE_SHA"
}

run_motion_task() {
  local task="$1"
  local limit="$2"
  ssh_motion bash -s -- "$MOTION_CONTAINER" "$task" "$limit" <<'REMOTE'
set -Eeuo pipefail
container="$1"
task="$2"
limit="$3"

output="$(docker exec -i "$container" bash -s -- "$task" "$limit" <<'INNER'
set -Eeo pipefail
# El setup de UBTECH consulta variables opcionales que pueden no existir.
# Activamos nounset solo despues de cargar el entorno del fabricante.
set +u
source /opt/walker/setup.bash
set -u
task="$1"
limit="$2"
timeout "$limit" rosa action send_goal /mc/manipulation/action \
  mc_task_msgs/action/ArmTask \
  "{\"task_name\":\"$task\",\"yaml_args\":\"{}\"}"
INNER
)"
printf '%s\n' "$output"
grep -q "'desc': 'SUCCEED'" <<<"$output" || exit 50
grep -q 'status=4' <<<"$output" || exit 51
REMOTE
}

vision_sample() {
  local output
  output="$(ssh_motion bash -s -- "$MOTION_CONTAINER" <<'REMOTE'
set -Eeuo pipefail
container="$1"
docker exec -i "$container" bash -s <<'INNER'
set -Eeo pipefail
# El setup de UBTECH consulta variables opcionales que pueden no existir.
# Activamos nounset solo despues de cargar el entorno del fabricante.
set +u
source /opt/walker/setup.bash
set -u
timeout 20 rosa action send_goal /cv/task/transport_action \
  cv_task_msgs/action/VisionActionTask \
  '{"task_type":"transport","trans_inputs":{"camera_name":"head","task_stage":"grasp","box_size":{"x":0.60,"y":0.40,"z":0.22}}}'
INNER
REMOTE
)"

  python3 -c '
import re
import sys

text = sys.stdin.read()
if "status=4" not in text or "result={\x27ok\x27: True" not in text:
    raise SystemExit("La acción de visión no devolvió ok=True")
if "\x27object_name\x27: \x27workbin\x27" not in text:
    raise SystemExit("El objeto detectado no es workbin")

marker = "\x27box_pose\x27: {\x27header\x27:"
index = text.find(marker)
if index < 0:
    raise SystemExit("No se encontró box_pose")
segment = text[index:]
orientation = re.search(
    r"\x27orientation\x27: \{\x27w\x27: ([^,}]+), \x27x\x27: ([^,}]+), "
    r"\x27y\x27: ([^,}]+), \x27z\x27: ([^,}]+)\}", segment)
position = re.search(
    r"\x27position\x27: \{\x27x\x27: ([^,}]+), \x27y\x27: ([^,}]+), "
    r"\x27z\x27: ([^,}]+)\}", segment)
if not orientation or not position:
    raise SystemExit("No se pudo analizar la pose de la caja")

qw, qx, qy, qz = map(float, orientation.groups())
x, y, z = map(float, position.groups())
print(x, y, z, qx, qy, qz, qw)
' <<<"$output"
}

validate_detection_samples() {
  python3 - "$@" <<'PY'
import math
import sys

samples = [[float(value) for value in sample.split()] for sample in sys.argv[1:]]
if len(samples) not in (2, 3) or any(len(sample) != 7 for sample in samples):
    raise SystemExit("Se requieren dos o tres poses de visión")

for index, (x, y, z, qx, qy, qz, qw) in enumerate(samples, 1):
    if abs(x) > 0.035:
        raise SystemExit(
            f"Muestra {index}: caja descentrada después de la aproximación "
            f"(x={x:.3f} m; máximo ±0.035 m)"
        )
    if not (0.20 <= y <= 0.75 and 0.65 <= z <= 1.15):
        raise SystemExit(f"Muestra {index}: caja fuera de la ventana validada (y={y:.3f}, z={z:.3f})")
    norm = math.sqrt(qx*qx + qy*qy + qz*qz + qw*qw)
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=0.03):
        raise SystemExit(f"Muestra {index}: cuaternión inválido")
    # El lado de 600 mm debe quedar paralelo a los hombros. Estos límites
    # corresponden a la cámara después de ejecutar move_head_lower, que es el
    # estado usado en el agarre que ya se validó físicamente. Se usan valores
    # absolutos porque q y -q representan exactamente la misma orientación.
    if not (
        abs(qx) >= 0.75
        and abs(qy) <= 0.20
        and abs(qz) <= 0.20
        and 0.35 <= abs(qw) <= 0.75
    ):
        raise SystemExit(
            f"Muestra {index}: orientación del contenedor no permitida "
            f"(qx={qx:.4f}, qy={qy:.4f}, qz={qz:.4f}, qw={qw:.4f})"
        )

for axis, name in enumerate(("x", "y", "z")):
    values = [sample[axis] for sample in samples]
    spread = max(values) - min(values)
    if spread > 0.020:
        raise SystemExit(f"Detección inestable en {name}: dispersión {spread:.3f} m")

for first, second in zip(samples, samples[1:]):
    dot = abs(sum(a*b for a, b in zip(first[3:], second[3:])))
    if dot < 0.98:
        raise SystemExit("Orientación inestable entre muestras")

means = [sum(sample[axis] for sample in samples) / len(samples) for axis in range(3)]
print(f"Detección validada: cámara x={means[0]:.3f}, y={means[1]:.3f}, z={means[2]:.3f} m")
PY
}

collect_detection_samples() {
  local count="${1:-3}"
  local attempt
  local detected
  local sample
  local index

  VISION_SAMPLES=()
  for ((index = 1; index <= count; index++)); do
    detected=0
    for attempt in 1 2 3; do
      if sample="$(vision_sample)"; then
        detected=1
        break
      fi
      warn "La detección no produjo una pose válida (intento $attempt/3)."
    done
    ((detected == 1)) || die "No se obtuvo una pose válida tras tres intentos."
    VISION_SAMPLES+=("$sample")
  done
}

validate_approach_samples() {
  python3 - "$@" <<'PY'
import math
import sys

samples = [[float(value) for value in sample.split()] for sample in sys.argv[1:]]
if len(samples) not in (1, 2, 3) or any(len(sample) != 7 for sample in samples):
    raise SystemExit("Se requieren entre una y tres poses de visión")

for index, (x, y, z, qx, qy, qz, qw) in enumerate(samples, 1):
    if abs(x) > 0.55:
        raise SystemExit(f"Muestra {index}: caja demasiado descentrada (x={x:.3f} m)")
    # Ventana amplia usada solamente mientras los brazos siguen recogidos y
    # el chasis aún está lejos. La ventana estrecha se revalida obligatoriamente
    # justo antes del agarre.
    if not (0.10 <= y <= 1.10 and 0.65 <= z <= 1.80):
        raise SystemExit(
            f"Muestra {index}: caja fuera de la ventana de aproximación "
            f"(y={y:.3f}, z={z:.3f})"
        )
    norm = math.sqrt(qx*qx + qy*qy + qz*qz + qw*qw)
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=0.03):
        raise SystemExit(f"Muestra {index}: cuaternión inválido")

for axis, name in enumerate(("x", "y", "z")):
    values = [sample[axis] for sample in samples]
    spread = max(values) - min(values)
    if spread > 0.025:
        raise SystemExit(f"Detección inestable en {name}: dispersión {spread:.3f} m")

for first, second in zip(samples, samples[1:]):
    dot = abs(sum(a*b for a, b in zip(first[3:], second[3:])))
    if dot < 0.98:
        raise SystemExit("Orientación inestable entre muestras")

means = [sum(sample[axis] for sample in samples) / len(samples) for axis in range(3)]

# Orientación de referencia medida con el chasis paralelo a una caja que ya
# fue agarrada correctamente. conj(reference) * measured separa el giro de
# guiñada producido por el chasis de la inclinación fija de la cámara.
reference = (0.5425, 0.8397, -0.0185, 0.0185)  # w, x, y, z

def multiply(first, second):
    w, x, y, z = first
    W, X, Y, Z = second
    return (
        w*W - x*X - y*Y - z*Z,
        w*X + x*W + y*Z - z*Y,
        w*Y - x*Z + y*W + z*X,
        w*Z + x*Y - y*X + z*W,
    )

reference_conjugate = (reference[0], -reference[1], -reference[2], -reference[3])
yaws = []
for _, _, _, qx, qy, qz, qw in samples:
    relative = multiply(reference_conjugate, (qw, qx, qy, qz))
    rw, rx, ry, rz = relative
    yaw = math.atan2(2.0 * (rw*rz + rx*ry), 1.0 - 2.0 * (ry*ry + rz*rz))
    yaws.append(yaw)

if max(yaws) - min(yaws) > math.radians(3.0):
    raise SystemExit("Orientación de la caja inestable entre muestras")
yaw_mean = math.atan2(
    sum(math.sin(value) for value in yaws),
    sum(math.cos(value) for value in yaws),
)
if abs(yaw_mean) > math.radians(55.0):
    raise SystemExit(
        f"Caja fuera del margen angular de recuperación ({math.degrees(yaw_mean):.1f} grados)"
    )

print(
    f"BOX_POSE_CAMERA={means[0]:.6f} {means[1]:.6f} {means[2]:.6f} "
    f"{math.degrees(yaw_mean):.6f}"
)
PY
}

verify_clamp_log() {
  local log_excerpt
  log_excerpt="$(ssh_motion bash -s -- <<'REMOTE'
set -Eeuo pipefail
marker="BTree task: 'cruzr/blue_workbin_clamp_only' is start"

# El proceso puede rotar robot_app.log justo entre el fin de la acción y esta
# comprobación. Además, algunas líneas tardan unos segundos en volcarse. Busca
# el último inicio de agarre en varios archivos consecutivos y espera a que las
# medidas finales estén disponibles antes de devolver el segmento completo.
for attempt in 1 2 3 4 5; do
  mapfile -t records < <(
    find /etc/walker/log/motion -maxdepth 1 -type f \
      -name 'robot_app*.log' -printf '%T@\t%p\n' |
      sort -n | tail -n 12
  )

  marker_index=-1
  marker_line=""
  for ((index=${#records[@]} - 1; index >= 0; index--)); do
    file="${records[index]#*$'\t'}"
    line="$(grep -nF "$marker" "$file" | tail -n1 | cut -d: -f1 || true)"
    if [[ -n "$line" ]]; then
      marker_index="$index"
      marker_line="$line"
      break
    fi
  done

  if ((marker_index >= 0)); then
    segment="$({
      file="${records[marker_index]#*$'\t'}"
      tail -n "+$marker_line" "$file"
      for ((index=marker_index + 1; index < ${#records[@]}; index++)); do
        file="${records[index]#*$'\t'}"
        cat "$file"
      done
    })"

    if grep -qF "left-right-arm tool's distance on base:" <<<"$segment" && \
       grep -qF "left_force_base" <<<"$segment"; then
      printf '__CRUZR_CLAMP_LOG_SEGMENT__\n%s\n' "$segment"
      exit 0
    fi
  fi

  ((attempt < 5)) && sleep 1
done

echo "No se encontró un registro completo del último agarre tras 5 intentos" >&2
exit 60
REMOTE
)"

  python3 -c '
import re
import sys

text = sys.stdin.read()
sentinel = "__CRUZR_CLAMP_LOG_SEGMENT__"
index = text.find(sentinel)
if index < 0:
    raise SystemExit("No se recibió el segmento completo del último agarre")
segment = text[index + len(sentinel):]

release_markers = (
    "Start MetaClamp: put_collision_cruzr",
    "Start MetaClamp: byd/open_arm_cruzr",
    "BTree task: \x27cruzr/blue_workbin_auto_deposit\x27 is start",
    "BTree task: \x27cruzr/blue_workbin_open_only\x27 is start",
    "BTree task: \x27cruzr/blue_workbin_release_only\x27 is start",
    "BTree task: \x27cruzr/home\x27 is start",
)
for release_marker in release_markers:
    if release_marker in segment:
        raise SystemExit(
            "Después del último agarre se ordenó una apertura, depósito o home"
        )

distance_matches = re.findall(
    r"left-right-arm tool\x27s distance on base:\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)",
    segment,
)
force_matches = re.findall(
    r"left_force_base\s*:\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)",
    segment,
)
if not distance_matches or not force_matches:
    raise SystemExit("Faltan medidas finales de agarre o fuerza")

dx, separation, dz = map(float, distance_matches[-1])
forces = [tuple(map(float, match)) for match in force_matches]
final_fx, final_fy, final_fz = forces[-1]
peak_fy = max(abs(force[1]) for force in forces)

if not (0.53 <= abs(separation) <= 0.60):
    raise SystemExit(f"Separación final anómala: {separation:.3f} m")
if abs(dz) > 0.030:
    raise SystemExit(f"Desnivel entre cogedores excesivo: {dz:.3f} m")
if abs(final_fy) < 5.0:
    raise SystemExit(f"No se confirma contacto lateral: Fy={final_fy:.1f} N")
if peak_fy > 80.0:
    raise SystemExit(f"Pico de fuerza fuera del límite: {peak_fy:.1f} N")

print(
    f"Agarre validado: separación={abs(separation):.3f} m, "
    f"Fy final={final_fy:.1f} N, Fz final={final_fz:.1f} N, "
    f"pico |Fy|={peak_fy:.1f} N"
)
if peak_fy > 45.0:
    print("HIGH_FORCE=1")
' <<<"$log_excerpt"
}

confirm_once() {
  ((YES == 1)) && return 0
  cat <<'EOF'

CONFIRMACIÓN ÚNICA
La orden iniciará movimientos físicos sin nuevas preguntas. Confirma que:
  - la caja y la mesa están colocadas como indica --help;
  - no hay personas ni objetos en la envolvente o zona de caída;
  - el robot está en home, desenchufado y el paro está preparado.

Escribe EJECUTAR CICLO para continuar:
EOF
  local answer
  read -r answer
  [[ "$answer" == "EJECUTAR CICLO" ]] || die "Ciclo cancelado."
}

grasp_box() {
  info "[1/4] Bajando la cabeza..."
  run_motion_task "$HEAD_LOWER_TASK" 15

  grasp_after_approach
}

grasp_after_approach() {
  info "[2/4] Preparando ambos brazos..."
  run_motion_task "$ARMS_READY_TASK" 20

  info "[3/4] Confirmando el contenedor con dos detecciones..."
  collect_detection_samples 2
  validate_detection_samples "${VISION_SAMPLES[@]}"

  info "[4/4] Sujetando y elevando con la primitiva BYD..."
  run_motion_task "$CLAMP_TASK" 35
  GRASP_REPORT="$(verify_clamp_log)"
  printf '%s\n' "$GRASP_REPORT"
}

run_cycle() {
  confirm_once
  grasp_box

  if grep -q '^HIGH_FORCE=1$' <<<"$GRASP_REPORT"; then
    warn "Fuerza elevada: se omite la espera y se deposita inmediatamente."
  elif ((HOLD_SECONDS > 0)); then
    info "[5/7] Manteniendo la caja elevada ${HOLD_SECONDS} s..."
    sleep "$HOLD_SECONDS"
  else
    info "[5/7] Espera omitida."
  fi

  info "[6/7] Descendiendo hasta contacto con la mesa..."
  info "[7/7] Abriendo los cogedores con la primitiva BYD..."
  run_motion_task "$DEPOSIT_TASK" 25

  cat <<'EOF'

CICLO COMPLETADO
La caja fue detectada, sujetada, elevada, depositada por contacto y liberada.
El chasis no se movió. Los brazos quedan abiertos junto a la caja.
Retira caja y mesa; después ejecuta:
  ./scripts/cruzr_blue_workbin_cycle.sh --home --yes
EOF
}

run_grasp() {
  confirm_once
  grasp_box
  cat <<'EOF'

AGARRE COMPLETADO
La caja queda elevada y sujeta. El chasis no se ha movido.
No te acerques a la caja ni a los brazos mientras permanezca suspendida.
EOF
}

run_deposit_held() {
  if ((YES == 0)); then
    cat <<'EOF'
Confirma que existe un apoyo estable justo debajo de la caja y que nadie está
en la envolvente de los brazos. Escribe DEPOSITAR CAJA para continuar:
EOF
    local answer
    read -r answer
    [[ "$answer" == "DEPOSITAR CAJA" ]] || die "Depósito cancelado."
  fi

  verify_clamp_log
  info "Descendiendo hasta contacto y abriendo los cogedores..."
  run_motion_task "$DEPOSIT_TASK" 25
  info "DEPÓSITO COMPLETADO: caja apoyada y cogedores abiertos; el chasis no se movió."
}

run_home() {
  if ((YES == 0)); then
    cat <<'EOF'
Confirma que caja y mesa ya fueron retiradas y la zona frontal está despejada.
Escribe EJECUTAR HOME para continuar:
EOF
    local answer
    read -r answer
    [[ "$answer" == "EJECUTAR HOME" ]] || die "Home cancelado."
  fi
  run_motion_task "$HOME_TASK" 20
  info "Robot devuelto a home; el chasis permaneció inmóvil."
}

main() {
  require_local_tools
  exec 9>"/tmp/cruzr_blue_workbin_cycle.lock"
  flock -n 9 || die "Ya hay otro ciclo local en ejecución."
  select_connection

  # La aproximación ya ejecutó sus comprobaciones generales. Este modo evita
  # repetir batería, acciones y hashes en cada corrección visual; aun así exige
  # dos detecciones coherentes en modo normal. El modo fluido usa una pose para
  # las correcciones intermedias; antes del agarre se conservan dos muestras.
  if [[ "$MODE" == "measure-box-fast" ]]; then
    if [[ "$FLUID_MODE" == "1" ]]; then
      collect_detection_samples 1
    else
      collect_detection_samples 2
    fi
    validate_approach_samples "${VISION_SAMPLES[@]}"
    exit 0
  fi

  if ((FAST == 0)); then
    validate_templates
    info "Comprobando versión, acciones, paros, batería y cargador..."
    remote_preflight
  else
    info "FAST_MODE: diagnóstico completo omitido; se conserva la validación del resultado de cada acción."
  fi

  case "$MODE" in
    check)
      info "CHECK_OK: no se instaló ni movió nada."
      ;;
    install)
      install_templates
      info "INSTALL_OK: tareas instaladas; no se movió el robot."
      ;;
    run)
      ((FAST == 1)) || install_templates
      run_cycle
      ;;
    grasp)
      ((FAST == 1)) || install_templates
      run_grasp
      ;;
    verify-grasp)
      verify_clamp_log
      info "VERIFY_GRASP_OK: el registro no contiene una liberación posterior."
      ;;
    deposit-held)
      ((FAST == 1)) || install_templates
      run_deposit_held
      ;;
    home)
      run_home
      ;;
    prepare-vision)
      confirm_once
      run_motion_task "$HEAD_LOWER_TASK" 15
      info "VISION_READY: cabeza preparada; brazos y chasis no se movieron."
      ;;
    measure-box)
      collect_detection_samples
      validate_approach_samples "${VISION_SAMPLES[@]}"
      ;;
    grasp-after-approach)
      ((FAST == 1)) || install_templates
      confirm_once
      grasp_after_approach
      cat <<'EOF'

AGARRE COMPLETADO DESPUÉS DE LA APROXIMACIÓN
La caja queda elevada y sujeta. El chasis no se movió durante el agarre.
EOF
      ;;
    *)
      die "Modo interno desconocido: $MODE"
      ;;
  esac
}

main
