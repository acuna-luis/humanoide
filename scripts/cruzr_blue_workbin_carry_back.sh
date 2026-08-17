#!/usr/bin/env bash

set -Eeuo pipefail

# Agarra el contenedor azul, retrocede 0,50 m, vuelve a la pose inicial y
# deposita la caja de nuevo en el mismo apoyo.
# El retroceso usa un único tramo cerrado de 0,50 m, medido mediante la
# odometría del chasis y enviado por el monitor de velocidad de UBTECH.

readonly MOTION_HOST="192.168.11.2"
readonly VISION_HOST="192.168.11.3"
readonly WIFI_GATEWAY="192.168.42.2"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly NAV_CONTAINER="walker-nav.freepnc_task-1"
readonly ROS_CONTAINER="walker-ros.ros2-1"
readonly POSE_TOPIC="/mc/odom"
readonly TOTAL_DISTANCE="0.50"
readonly RETURN_MAX_SPEED="0.08"
FLUID_MODE="${CRUZR_FLUID_MODE:-0}"
if [[ "$FLUID_MODE" == "1" ]]; then
  BACKWARD_MAX_SPEED="0.08"
  APPROACH_MAX_SPEED="0.12"
  APPROACH_DEPTH_TOLERANCE="0.050"
  APPROACH_CENTER_TOLERANCE="0.035"
  APPROACH_MAX_STEP="0.42"
  APPROACH_MAX_ITERATIONS="5"
  APPROACH_SETTLE_SECONDS="0.20"
else
  BACKWARD_MAX_SPEED="0.05"
  APPROACH_MAX_SPEED="0.08"
  APPROACH_DEPTH_TOLERANCE="0.020"
  APPROACH_CENTER_TOLERANCE="0.030"
  APPROACH_MAX_STEP="0.30"
  APPROACH_MAX_ITERATIONS="8"
  APPROACH_SETTLE_SECONDS="0.60"
fi
readonly FLUID_MODE BACKWARD_MAX_SPEED APPROACH_MAX_SPEED \
  APPROACH_DEPTH_TOLERANCE APPROACH_CENTER_TOLERANCE APPROACH_MAX_STEP \
  APPROACH_MAX_ITERATIONS APPROACH_SETTLE_SECONDS
readonly APPROACH_MAX_TOTAL="1.20"
# La detección que produjo el agarre estable midió z=0,966 m. En este mensaje
# z es la profundidad óptica; la distancia euclídea no sirve como consigna
# porque también contiene la altura de la cámara sobre la caja.
readonly APPROACH_TARGET_DEPTH="0.966"
readonly APPROACH_MAX_LATERAL_STEP="0.10"
readonly APPROACH_BACKOFF_CLEARANCE="0.12"
readonly APPROACH_YAW_TOLERANCE_DEG="2.0"
readonly RETURN_POSITION_TOLERANCE="0.03"
readonly RETURN_YAW_TOLERANCE="0.0524"
readonly GRASP_SCRIPT_NAME="cruzr_blue_workbin_cycle.sh"
readonly RECOVERY_SCRIPT_NAME="cruzr_recover_to_home.sh"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD

# ssh usa este mismo archivo como proveedor de contraseña.
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

SCRIPT_PATH="$(readlink -f -- "$0")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly SCRIPT_PATH SCRIPT_DIR
readonly GRASP_SCRIPT="$SCRIPT_DIR/$GRASP_SCRIPT_NAME"
readonly RECOVERY_SCRIPT="$SCRIPT_DIR/$RECOVERY_SCRIPT_NAME"

# Sin opciones se ejecuta el ciclo completo, con confirmación física. El modo
# de diagnóstico sin movimiento debe solicitarse explícitamente con --check.
MODE="run"
YES=0
FAST=0
CONNECTION_MODE=""
CONTROL_TARGET=""
CONTROL_INTERFACE=""
VISION_SSH_HOST=""
LAST_SEGMENT_DISTANCE=""
INITIAL_POSE=""
RETURN_TARGET_POSE=""
ADVANCE_DISTANCE=""
RELATIVE_MOVE=""
RELATIVE_ROTATION=""
BACKWARD_DISTANCE=""

usage() {
  cat <<'EOF'
Uso:
  ./scripts/cruzr_blue_workbin_carry_back.sh
  ./scripts/cruzr_blue_workbin_carry_back.sh --check
  ./scripts/cruzr_blue_workbin_carry_back.sh --run [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_carry_back.sh --align-only [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_carry_back.sh --move-held [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_carry_back.sh --retreat-only [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_carry_back.sh --grasp-only [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_carry_back.sh --return-held-to-pose "X Y YAW" [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_carry_back.sh --advance-held-distance METROS [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_carry_back.sh --move-relative "AVANCE LATERAL" [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_carry_back.sh --rotate-relative GRADOS [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_carry_back.sh --backward-distance METROS [--yes] [--fast]

Modos:
  sin opción     Equivale a --run y solicita confirmación antes de mover.
  --check       Comprueba manipulación y navegación. No mueve ni instala nada.
  --run         Localiza la caja con los brazos recogidos, corrige centrado y
                distancia, agarra, retrocede 0,50 m, vuelve al punto de agarre
                y la deposita sobre el mismo apoyo. Inmediatamente después,
                se separa de la mesa y ejecuta cruzr/home sin preguntar.
  --align-only  Corrige centrado y distancia, pero termina sin mover los
                brazos. Sirve para validar una colocación nueva.
  --move-held   Hace el recorrido de ida y vuelta, deposita una caja que ya
                está agarrada y termina automáticamente en home.
  --retreat-only
                Retrocede 0,50 m y se detiene. No mueve brazos ni regresa.
  --grasp-only  Centra, sujeta y eleva la caja; termina manteniéndola agarrada.
  --return-held-to-pose "X Y YAW"
                Con una caja ya agarrada, vuelve a esa pose de /mc/odom y se
                detiene sin depositarla. Uso interno para recorridos largos.
  --advance-held-distance METROS
                Con una caja ya agarrada, avanza esa distancia desde la pose
                actual y se detiene sin depositarla (máximo 0,65 m).
  --move-relative "AVANCE LATERAL"
                Corrección local pequeña mediante un arco frontal y termina
                con el rumbo inicial. No mueve los brazos (uso interno).
  --rotate-relative GRADOS
                Gira localmente un máximo de 10 grados. No mueve los brazos
                (uso interno del alineador AprilTag).
  --backward-distance METROS
                Retrocede entre 0,02 y 0,15 m. No mueve los brazos (uso
                interno del alineador AprilTag).

Opciones:
  --yes         Omite la única confirmación inicial.
  --fast        Evita diagnósticos completos repetidos durante el flujo. Se
                mantienen paros, cargador, odometría y resultados de acciones.
  --help        Muestra esta ayuda.

Condiciones obligatorias para mover la base:
  - control exclusivamente por Wi-Fi; Ethernet y cargador desconectados;
  - caja rígida azul de 600 x 400 x 220 mm, vacía y visible de frente;
  - suelo plano, seco y sin desniveles;
  - trayecto frontal, 0,50 m a cada lado y 1,50 m detrás libres;
  - la mesa original inmóvil, estable y sin personas alrededor;
  - ninguna persona junto al robot y paro de emergencia preparado.

Tras soltar la caja, la recuperación retrocede 0,50 m para separar los brazos
de la mesa y ejecuta la tarea oficial cruzr/home. Si el robot no vuelve a la
mesa dentro de 3 cm y 3 grados, no intenta depositar ni ejecutar home.
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
    --check|--run|--align-only|--move-held|--retreat-only|--grasp-only)
      MODE="${1#--}"
      ;;
    --return-held-to-pose)
      (($# >= 2)) || die "--return-held-to-pose necesita una pose entre comillas: X Y YAW"
      MODE="return-held-to-pose"
      RETURN_TARGET_POSE="$2"
      shift
      ;;
    --advance-held-distance)
      (($# >= 2)) || die "--advance-held-distance necesita una distancia en metros"
      MODE="advance-held-distance"
      ADVANCE_DISTANCE="$2"
      shift
      ;;
    --move-relative)
      (($# >= 2)) || die "--move-relative necesita \"AVANCE LATERAL\" en metros"
      MODE="move-relative"
      RELATIVE_MOVE="$2"
      shift
      ;;
    --rotate-relative)
      (($# >= 2)) || die "--rotate-relative necesita un ángulo en grados"
      MODE="rotate-relative"
      RELATIVE_ROTATION="$2"
      shift
      ;;
    --backward-distance)
      (($# >= 2)) || die "--backward-distance necesita una distancia en metros"
      MODE="backward-distance"
      BACKWARD_DISTANCE="$2"
      shift
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

require_local_tools() {
  local command_name
  for command_name in ssh setsid nc ip readlink flock python3; do
    command -v "$command_name" >/dev/null 2>&1 || \
      die "Falta el comando local '$command_name'."
  done
  [[ -x "$GRASP_SCRIPT" ]] || \
    die "No existe o no es ejecutable: $GRASP_SCRIPT"
  [[ -x "$RECOVERY_SCRIPT" ]] || \
    die "No existe o no es ejecutable: $RECOVERY_SCRIPT"
}

run_grasp_script() {
  local -a extra_args=()
  ((FAST == 1)) && extra_args+=(--fast)
  "$GRASP_SCRIPT" "$@" "${extra_args[@]}"
}

flow_safety_check() {
  if ((FAST == 1)); then
    runtime_safety_check
  else
    nav_preflight
  fi
}

route_interface() {
  local target="$1"
  ip -o route get "$target" 2>/dev/null | \
    awk '{for (i=1; i<=NF; i++) if ($i=="dev") {print $(i+1); exit}}'
}

is_wireless_interface() {
  local interface="$1"
  [[ -n "$interface" && -d "/sys/class/net/$interface/wireless" ]]
}

select_connection() {
  local interface

  # Se prefiere siempre la pasarela Wi-Fi del robot.
  if nc -z -w2 "$WIFI_GATEWAY" 22 >/dev/null 2>&1; then
    interface="$(route_interface "$WIFI_GATEWAY")"
    if is_wireless_interface "$interface"; then
      CONNECTION_MODE="Wi-Fi mediante vision"
      CONTROL_TARGET="$WIFI_GATEWAY"
      CONTROL_INTERFACE="$interface"
      VISION_SSH_HOST="$WIFI_GATEWAY"
      info "Conexión: $CONNECTION_MODE ($CONTROL_INTERFACE)"
      return
    fi
  fi

  if nc -z -w2 "$VISION_HOST" 22 >/dev/null 2>&1; then
    CONTROL_TARGET="$VISION_HOST"
    CONTROL_INTERFACE="$(route_interface "$VISION_HOST")"
    VISION_SSH_HOST="$VISION_HOST"
    if is_wireless_interface "$CONTROL_INTERFACE"; then
      CONNECTION_MODE="Wi-Fi directa a vision"
    else
      CONNECTION_MODE="directa a vision"
    fi
    info "Conexión: $CONNECTION_MODE ($CONTROL_INTERFACE)"
    return
  fi

  die "No se alcanza vision ($VISION_HOST) ni la pasarela Wi-Fi ($WIFI_GATEWAY)."
}

require_wireless_run() {
  local direct_interface=""

  is_wireless_interface "$CONTROL_INTERFACE" || die \
    "La ruta de control usa '$CONTROL_INTERFACE', que no es Wi-Fi. Desconecta Ethernet y conéctate al hotspot del robot."

  if direct_interface="$(active_wired_motion_interface)"; then
    die "Se detecta enlace Ethernet activo por '$direct_interface'. Desconecta físicamente el cable antes de mover la base."
  fi
}

active_wired_motion_interface() {
  local direct_interface=""

  if nc -z -w1 "$MOTION_HOST" 22 >/dev/null 2>&1; then
    direct_interface="$(route_interface "$MOTION_HOST")"
    if [[ -n "$direct_interface" ]] && \
       ! is_wireless_interface "$direct_interface" && \
       [[ "$(cat "/sys/class/net/$direct_interface/carrier" 2>/dev/null || true)" == "1" ]]; then
      printf '%s\n' "$direct_interface"
      return 0
    fi
  fi
  return 1
}

ssh_vision() {
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w ssh \
    -o ConnectTimeout=8 \
    -o ConnectionAttempts=1 \
    -o ServerAliveInterval=3 \
    -o ServerAliveCountMax=2 \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -o NumberOfPasswordPrompts=2 \
    -o StrictHostKeyChecking=accept-new \
    "$ROBOT_USER@$VISION_SSH_HOST" "$@"
}

nav_preflight() {
  ssh_vision bash -s -- "$NAV_CONTAINER" "$ROS_CONTAINER" "$POSE_TOPIC" <<'REMOTE'
set -Eeuo pipefail
nav_container="$1"
ros_container="$2"
pose_topic="$3"

[[ "$(hostname)" == "vision" ]] || exit 20
for container in "$nav_container" "$ros_container"; do
  [[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || {
    echo "CONTAINER_ERROR=$container"
    exit 21
  }
done

topic_once() {
  local topic="$1"
  docker exec "$ros_container" bash -lc \
    "source /opt/ros/humble/setup.bash; timeout 8 ros2 topic echo --no-daemon --once '$topic'"
}

safety_tmp="$(mktemp -d)"
trap 'rm -rf -- "$safety_tmp"' EXIT
topic_once /emb/estop_key_state >"$safety_tmp/estop" & estop_pid=$!
topic_once /emb/servo_estop_key_state >"$safety_tmp/servo" & servo_pid=$!
topic_once /emb/chrg_input_status >"$safety_tmp/charge" & charge_pid=$!
wait "$estop_pid"
wait "$servo_pid"
wait "$charge_pid"
estop="$(<"$safety_tmp/estop")"
servo_estop="$(<"$safety_tmp/servo")"
charge="$(<"$safety_tmp/charge")"
[[ "$(awk '/data:/ {print $2; exit}' <<<"$estop")" == "0" ]] || exit 24
[[ "$(awk '/data:/ {print $2; exit}' <<<"$servo_estop")" == "0" ]] || exit 25
[[ "$(awk '/data:/ {print $2; exit}' <<<"$charge")" == "0" ]] || {
  echo 'CHARGER_CONNECTED=1'
  exit 26
}

cmd_info="$(docker exec "$ros_container" bash -lc \
  "source /opt/ros/humble/setup.bash; ros2 topic info --no-daemon /cmd_vel_navi")"
grep -q 'Type: geometry_msgs/msg/TwistStamped' <<<"$cmd_info" || exit 27
grep -Eq 'Subscription count: [1-9][0-9]*' <<<"$cmd_info" || exit 28

monitored_cmd_info="$(docker exec "$ros_container" bash -lc \
  "source /opt/ros/humble/setup.bash; ros2 topic info --no-daemon /mc/cmd_vel")"
grep -q 'Type: geometry_msgs/msg/TwistStamped' <<<"$monitored_cmd_info" || exit 29
grep -Eq 'Subscription count: [1-9][0-9]*' <<<"$monitored_cmd_info" || exit 30

pose_info="$(docker exec "$ros_container" bash -lc \
  "source /opt/ros/humble/setup.bash; ros2 topic info --no-daemon '$pose_topic'")"
grep -q 'Type: nav_msgs/msg/Odometry' <<<"$pose_info" || exit 31
grep -q 'Publisher count: 1' <<<"$pose_info" || exit 32

pose_sample="$(topic_once "$pose_topic")" || {
  echo "POSE_SAMPLE_ERROR=$pose_topic"
  exit 33
}
grep -q 'position:' <<<"$pose_sample" || {
  echo "POSE_SAMPLE_INVALID=$pose_topic"
  exit 34
}

printf 'POSE_SOURCE=%s\n' "$pose_topic"
printf 'DRIVE_PATH=/cmd_vel_navi->UBTECH-monitor->/mc/cmd_vel\n'
printf 'ESTOPS=0,0\nCHARGER=disconnected\nNAVIGATION=ready\n'
REMOTE
}

runtime_safety_check() {
  local attempt
  local output=""

  for attempt in 1 2 3; do
    if output="$(ssh_vision bash -s -- "$ROS_CONTAINER" <<'REMOTE'
set -Eeuo pipefail
container="$1"
topic_once() {
  docker exec "$container" bash -lc \
    "source /opt/ros/humble/setup.bash; timeout 8 ros2 topic echo --no-daemon --once '$1' std_msgs/msg/UInt8"
}
safety_tmp="$(mktemp -d)"
trap 'rm -rf -- "$safety_tmp"' EXIT
topic_once /emb/estop_key_state >"$safety_tmp/estop" & estop_pid=$!
topic_once /emb/servo_estop_key_state >"$safety_tmp/servo" & servo_pid=$!
topic_once /emb/chrg_input_status >"$safety_tmp/charge" & charge_pid=$!
wait "$estop_pid"
wait "$servo_pid"
wait "$charge_pid"
estop="$(<"$safety_tmp/estop")"
servo_estop="$(<"$safety_tmp/servo")"
charge="$(<"$safety_tmp/charge")"
estop_value="$(awk '/data:/ {print $2; exit}' <<<"$estop")"
servo_value="$(awk '/data:/ {print $2; exit}' <<<"$servo_estop")"
charge_value="$(awk '/data:/ {print $2; exit}' <<<"$charge")"
[[ "$estop_value" == "0" ]] || { echo "ESTOP_VALUE=${estop_value:-missing}"; exit 24; }
[[ "$servo_value" == "0" ]] || { echo "SERVO_ESTOP_VALUE=${servo_value:-missing}"; exit 25; }
[[ "$charge_value" == "0" ]] || { echo "CHARGER_VALUE=${charge_value:-missing}"; exit 26; }
printf 'RUNTIME_SAFETY=estops:0,0;charger:disconnected\n'
REMOTE
)"; then
      printf '%s\n' "$output"
      return 0
    fi
    warn "Comprobación de seguridad transitoria fallida (intento $attempt/3): ${output:-sin muestra}."
  done

  die "No se pudieron confirmar paros y cargador tras tres intentos; el chasis queda detenido."
}

read_map_pose() {
  local output

  output="$(ssh_vision bash -s -- "$ROS_CONTAINER" "$POSE_TOPIC" <<'REMOTE'
set -Eeuo pipefail
container="$1"
pose_topic="$2"
docker exec -i "$container" bash -s -- "$pose_topic" <<'INNER'
set -Eeo pipefail
set +u
source /opt/ros/humble/setup.bash
set -u
timeout 8 ros2 topic echo --no-daemon --once "$1" --field pose.pose
INNER
REMOTE
)"

  python3 -c '
import math
import re
import sys

text = sys.stdin.read()
position = re.search(
    r"position:\s+x:\s*([-+0-9.eE]+)\s+y:\s*([-+0-9.eE]+)", text
)
orientation = re.search(
    r"orientation:\s+x:\s*[-+0-9.eE]+\s+y:\s*[-+0-9.eE]+\s+"
    r"z:\s*([-+0-9.eE]+)\s+w:\s*([-+0-9.eE]+)", text
)
if not position or not orientation:
    raise SystemExit("No se pudo analizar la odometría del chasis")
x, y = map(float, position.groups())
qz, qw = map(float, orientation.groups())
yaw = math.atan2(2.0 * qw * qz, 1.0 - 2.0 * qz * qz)
print(f"{x:.9f} {y:.9f} {yaw:.9f}")
' <<<"$output"
}

capture_initial_pose() {
  local sample
  local -a samples=()

  if ((FAST == 1)); then
    INITIAL_POSE="$(read_map_pose)"
    info "POSE_INICIAL=$INITIAL_POSE (fast: muestra única)"
    return 0
  fi

  for _ in 1 2 3; do
    sample="$(read_map_pose)"
    samples+=("$sample")
  done

  INITIAL_POSE="$(python3 - "${samples[@]}" <<'PY'
import math
import sys

samples = [tuple(map(float, value.split())) for value in sys.argv[1:]]
if len(samples) != 3 or any(len(sample) != 3 for sample in samples):
    raise SystemExit("Se requieren tres muestras de localización")

xs = [sample[0] for sample in samples]
ys = [sample[1] for sample in samples]
yaws = [sample[2] for sample in samples]

def angle_error(first, second):
    return math.atan2(math.sin(first - second), math.cos(first - second))

if max(xs) - min(xs) > 0.010 or max(ys) - min(ys) > 0.010:
    raise SystemExit("La localización inicial no es estable en posición")
if max(abs(angle_error(yaw, yaws[0])) for yaw in yaws[1:]) > 0.010:
    raise SystemExit("La localización inicial no es estable en orientación")

x = sum(xs) / len(xs)
y = sum(ys) / len(ys)
sin_mean = sum(math.sin(yaw) for yaw in yaws) / len(yaws)
cos_mean = sum(math.cos(yaw) for yaw in yaws) / len(yaws)
yaw = math.atan2(sin_mean, cos_mean)
print(f"{x:.9f} {y:.9f} {yaw:.9f}")
PY
)"
  info "POSE_INICIAL=$INITIAL_POSE"
}

stop_base() {
  ssh_vision bash -s -- "$ROS_CONTAINER" <<'REMOTE'
set -Eeuo pipefail
container="$1"
docker exec -i "$container" bash -lc \
  'source /opt/ros/humble/setup.bash; timeout 4 ros2 topic pub --once /cmd_vel_navi geometry_msgs/msg/TwistStamped "{header: {frame_id: base_footprint}, twist: {linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}" >/dev/null'
REMOTE
}

stop_base_silent() {
  set +e
  stop_base >/dev/null 2>&1
  set -e
}

run_backward_segment() {
  local target_distance="${1:-$TOTAL_DISTANCE}"
  local max_speed="${2:-$BACKWARD_MAX_SPEED}"
  local output
  local measured

  output="$(ssh_vision bash -s -- "$ROS_CONTAINER" "$POSE_TOPIC" \
    "$target_distance" "$max_speed" <<'REMOTE'
set -Eeuo pipefail
container="$1"
pose_topic="$2"
distance="$3"
max_speed="$4"

timeout 24 docker exec -i "$container" bash -s -- \
  "$pose_topic" "$distance" "$max_speed" <<'INNER'
set -Eeo pipefail
set +u
source /opt/ros/humble/setup.bash
set -u
python3 - "$@" <<'PY'
import math
import signal
import sys
import time

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

pose_topic = sys.argv[1]
target_distance = float(sys.argv[2])
max_speed = float(sys.argv[3])
distance_tolerance = 0.008
max_runtime = max(12.0, target_distance / max_speed * 2.6)
max_lateral_error = 0.040
max_yaw_error = math.radians(5.0)
min_speed = 0.020


def wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


class BackwardController(Node):
    def __init__(self):
        super().__init__("cruzr_loaded_backward_controller")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.publisher = self.create_publisher(TwistStamped, "/cmd_vel_navi", qos)
        self.subscription = self.create_subscription(
            Odometry, pose_topic, self.pose_callback, qos
        )
        self.pose = None
        self.last_pose_time = 0.0

    def pose_callback(self, message):
        position = message.pose.pose.position
        orientation = message.pose.pose.orientation
        yaw = math.atan2(
            2.0 * (orientation.w * orientation.z + orientation.x * orientation.y),
            1.0 - 2.0 * (orientation.y * orientation.y + orientation.z * orientation.z),
        )
        self.pose = (position.x, position.y, yaw)
        self.last_pose_time = time.monotonic()

    def command(self, linear):
        message = TwistStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = "base_footprint"
        message.twist.linear.x = float(linear)
        message.twist.angular.z = 0.0
        self.publisher.publish(message)

    def stop(self):
        for _ in range(10):
            self.command(0.0)
            rclpy.spin_once(self, timeout_sec=0.02)


rclpy.init()
node = BackwardController()


def abort(_signum=None, _frame=None):
    node.stop()
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, abort)
signal.signal(signal.SIGINT, abort)

try:
    wait_started = time.monotonic()
    while node.pose is None and time.monotonic() - wait_started < 5.0:
        rclpy.spin_once(node, timeout_sec=0.1)
    if node.pose is None:
        raise RuntimeError(f"No se recibió {pose_topic}")

    start_x, start_y, start_yaw = node.pose
    forward_x = math.cos(start_yaw)
    forward_y = math.sin(start_yaw)
    started = time.monotonic()
    last_progress_time = started
    best_progress = 0.0

    while True:
        rclpy.spin_once(node, timeout_sec=0.03)
        now = time.monotonic()
        if node.pose is None or now - node.last_pose_time > 0.6:
            raise RuntimeError("La odometría del chasis dejó de actualizarse")

        x, y, yaw = node.pose
        dx = x - start_x
        dy = y - start_y
        progress = -(forward_x * dx + forward_y * dy)
        lateral = -forward_y * dx + forward_x * dy
        yaw_error = wrap(yaw - start_yaw)
        remaining = target_distance - progress

        if progress >= target_distance - distance_tolerance:
            node.stop()
            print(
                f"BACKWARD_OK distance={progress:.6f} "
                f"lateral={lateral:.6f} yaw_deg={math.degrees(yaw_error):.3f}"
            )
            break

        if progress < -0.015:
            raise RuntimeError(
                f"Movimiento en sentido contrario: {progress:.3f} m"
            )
        if abs(lateral) > max_lateral_error:
            raise RuntimeError(f"Desviación lateral excesiva: {lateral:.3f} m")
        if abs(yaw_error) > max_yaw_error:
            raise RuntimeError(
                f"Desviación angular excesiva: {math.degrees(yaw_error):.2f} grados"
            )
        if now - started > max_runtime:
            raise RuntimeError("Tiempo máximo de retroceso agotado")

        if progress > best_progress + 0.004:
            best_progress = progress
            last_progress_time = now
        elif now - last_progress_time > 3.0:
            raise RuntimeError(
                "Sin progreso durante 3 s; posible obstáculo o bloqueo del monitor"
            )

        speed = min(max_speed, max(min_speed, 0.55 * remaining))
        node.command(-speed)

except BaseException as error:
    node.stop()
    if isinstance(error, KeyboardInterrupt):
        print("BACKWARD_ABORTED: señal recibida", file=sys.stderr)
    else:
        print(f"BACKWARD_ERROR: {error}", file=sys.stderr)
    raise
finally:
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
PY
INNER
REMOTE
)"

  printf '%s\n' "$output"
  measured="$(python3 -c '
import re
import sys

text = sys.stdin.read()
match = re.search(r"^BACKWARD_OK distance=([-+0-9.eE]+)", text, re.MULTILINE)
if not match:
    raise SystemExit("El controlador no confirmó el retroceso")
distance = float(match.group(1))
target = float(sys.argv[1])
if abs(distance - target) > 0.015:
    raise SystemExit(f"Distancia informada fuera de rango: {distance:.3f} m")
print(f"{distance:.6f}")
' "$target_distance" <<<"$output")"

  stop_base
  LAST_SEGMENT_DISTANCE="$measured"
  info "SEGMENT_DISTANCE=${LAST_SEGMENT_DISTANCE} m"
}

return_to_initial_pose() {
  local goal_x
  local goal_y
  local goal_yaw
  local output
  local max_speed="${1:-$RETURN_MAX_SPEED}"
  local position_tolerance="${2:-$RETURN_POSITION_TOLERANCE}"

  read -r goal_x goal_y goal_yaw <<<"$INITIAL_POSE"
  [[ -n "$goal_x" && -n "$goal_y" && -n "$goal_yaw" ]] || \
    die "No existe una pose inicial válida para el retorno."

  output="$(ssh_vision bash -s -- "$ROS_CONTAINER" "$POSE_TOPIC" "$goal_x" "$goal_y" \
    "$goal_yaw" "$max_speed" "$position_tolerance" \
    "$RETURN_YAW_TOLERANCE" <<'REMOTE'
set -Eeuo pipefail
container="$1"
pose_topic="$2"
goal_x="$3"
goal_y="$4"
goal_yaw="$5"
max_speed="$6"
position_tolerance="$7"
yaw_tolerance="$8"

timeout 30 docker exec -i "$container" bash -s -- \
  "$pose_topic" "$goal_x" "$goal_y" "$goal_yaw" "$max_speed" \
  "$position_tolerance" "$yaw_tolerance" <<'INNER'
set -Eeo pipefail
set +u
source /opt/ros/humble/setup.bash
set -u
python3 - "$@" <<'PY'
import math
import signal
import sys
import time

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

pose_topic = sys.argv[1]
goal_x, goal_y, goal_yaw, max_speed, pos_tol, yaw_tol = map(float, sys.argv[2:])
max_runtime = 20.0
max_angular_speed = 0.10
min_linear_speed = 0.025


def wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


class ReturnController(Node):
    def __init__(self):
        super().__init__("cruzr_loaded_return_controller")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.publisher = self.create_publisher(TwistStamped, "/cmd_vel_navi", qos)
        self.subscription = self.create_subscription(
            Odometry, pose_topic, self.pose_callback, qos
        )
        self.pose = None
        self.last_pose_time = 0.0

    def pose_callback(self, message):
        position = message.pose.pose.position
        orientation = message.pose.pose.orientation
        yaw = math.atan2(
            2.0 * (orientation.w * orientation.z + orientation.x * orientation.y),
            1.0 - 2.0 * (orientation.y * orientation.y + orientation.z * orientation.z),
        )
        self.pose = (position.x, position.y, yaw)
        self.last_pose_time = time.monotonic()

    def command(self, linear, angular):
        message = TwistStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = "base_footprint"
        message.twist.linear.x = float(linear)
        message.twist.angular.z = float(angular)
        self.publisher.publish(message)

    def stop(self):
        for _ in range(8):
            self.command(0.0, 0.0)
            rclpy.spin_once(self, timeout_sec=0.02)


rclpy.init()
node = ReturnController()


def abort(_signum=None, _frame=None):
    node.stop()
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, abort)
signal.signal(signal.SIGINT, abort)

try:
    wait_started = time.monotonic()
    while node.pose is None and time.monotonic() - wait_started < 5.0:
        rclpy.spin_once(node, timeout_sec=0.1)
    if node.pose is None:
        raise RuntimeError(f"No se recibió {pose_topic}")

    x, y, yaw = node.pose
    initial_distance = math.hypot(goal_x - x, goal_y - y)
    if initial_distance > 0.70:
        raise RuntimeError(
            f"Distancia inicial de retorno inesperada: {initial_distance:.3f} m"
        )

    started = time.monotonic()
    last_progress = started
    best_distance = initial_distance

    while True:
        rclpy.spin_once(node, timeout_sec=0.04)
        now = time.monotonic()
        if node.pose is None or now - node.last_pose_time > 1.0:
            raise RuntimeError("La odometría del chasis dejó de actualizarse")

        x, y, yaw = node.pose
        dx = goal_x - x
        dy = goal_y - y
        distance = math.hypot(dx, dy)
        yaw_error = wrap(goal_yaw - yaw)
        forward_x = math.cos(goal_yaw)
        forward_y = math.sin(goal_yaw)
        along_error = forward_x * dx + forward_y * dy
        lateral_error = -forward_y * dx + forward_x * dy

        if distance <= pos_tol:
            node.stop()
            if abs(yaw_error) > yaw_tol:
                raise RuntimeError(
                    f"Posición recuperada pero error angular excesivo: "
                    f"{math.degrees(yaw_error):.2f} grados"
                )
            print(
                f"RETURN_OK distance_error={distance:.4f} "
                f"yaw_error_deg={math.degrees(yaw_error):.3f} "
                f"start_distance={initial_distance:.4f}"
            )
            break

        if along_error <= -0.02:
            raise RuntimeError("El robot sobrepasó la pose inicial")
        if abs(lateral_error) > 0.08:
            raise RuntimeError(
                f"Desviación lateral excesiva: {lateral_error:.3f} m"
            )
        if now - started > max_runtime:
            raise RuntimeError("Tiempo máximo de retorno agotado")

        if distance < best_distance - 0.008:
            best_distance = distance
            last_progress = now
        elif now - last_progress > 4.0:
            raise RuntimeError(
                "Sin progreso durante 4 s; posible obstáculo o bloqueo del monitor"
            )

        linear = min(max_speed, max(min_linear_speed, 0.50 * along_error))
        angular = 1.5 * yaw_error + 0.8 * lateral_error
        angular = max(-max_angular_speed, min(max_angular_speed, angular))
        node.command(linear, angular)

except BaseException as error:
    node.stop()
    if isinstance(error, KeyboardInterrupt):
        print("RETURN_ABORTED: señal recibida", file=sys.stderr)
    else:
        print(f"RETURN_ERROR: {error}", file=sys.stderr)
    raise
finally:
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
PY
INNER
REMOTE
)"

  printf '%s\n' "$output"
  grep -q '^RETURN_OK ' <<<"$output" || \
    die "El controlador no confirmó el regreso a la pose inicial."
}

measure_box_pose() {
  local output
  local pose

  if ! output="$(run_grasp_script --measure-box-fast)"; then
    [[ -n "$output" ]] && printf '%s\n' "$output" >&2
    return 1
  fi
  printf '%s\n' "$output" >&2
  pose="$(awk -F= '/^BOX_POSE_CAMERA=/ {print $2; exit}' <<<"$output")"
  if [[ -z "$pose" ]]; then
    warn "La visión no devolvió BOX_POSE_CAMERA."
    return 1
  fi
  printf '%s\n' "$pose"
}

set_relative_goal() {
  local forward="$1"
  local lateral="$2"
  local current_x
  local current_y
  local current_yaw

  read -r current_x current_y current_yaw <<<"$INITIAL_POSE"
  INITIAL_POSE="$(python3 - "$current_x" "$current_y" "$current_yaw" \
    "$forward" "$lateral" <<'PY'
import math
import sys

x, y, yaw, forward, lateral = map(float, sys.argv[1:])
goal_x = x + math.cos(yaw) * forward - math.sin(yaw) * lateral
goal_y = y + math.sin(yaw) * forward + math.cos(yaw) * lateral
print(f"{goal_x:.9f} {goal_y:.9f} {yaw:.9f}")
PY
)"
  info "APPROACH_ODOM_GOAL=$INITIAL_POSE"
}

rotate_base_relative() {
  local angle_deg="$1"
  local output

  output="$(ssh_vision bash -s -- "$ROS_CONTAINER" "$POSE_TOPIC" "$angle_deg" <<'REMOTE'
set -Eeuo pipefail
container="$1"
pose_topic="$2"
angle_deg="$3"
timeout 20 docker exec -i "$container" bash -s -- "$pose_topic" "$angle_deg" <<'INNER'
set -Eeo pipefail
set +u
source /opt/ros/humble/setup.bash
set -u
python3 - "$@" <<'PY'
import math
import signal
import sys
import time

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

pose_topic = sys.argv[1]
requested = math.radians(float(sys.argv[2]))
if abs(requested) > math.radians(55.0):
    raise RuntimeError("Giro visual solicitado fuera del límite de 55 grados")


def wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


class RotateController(Node):
    def __init__(self):
        super().__init__("cruzr_visual_yaw_controller")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.publisher = self.create_publisher(TwistStamped, "/cmd_vel_navi", qos)
        self.subscription = self.create_subscription(Odometry, pose_topic, self.pose_cb, qos)
        self.yaw = None
        self.last_pose_time = 0.0

    def pose_cb(self, message):
        q = message.pose.pose.orientation
        self.yaw = math.atan2(
            2.0 * (q.w*q.z + q.x*q.y),
            1.0 - 2.0 * (q.y*q.y + q.z*q.z),
        )
        self.last_pose_time = time.monotonic()

    def command(self, angular):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_footprint"
        msg.twist.angular.z = float(angular)
        self.publisher.publish(msg)

    def stop(self):
        for _ in range(8):
            self.command(0.0)
            rclpy.spin_once(self, timeout_sec=0.02)


rclpy.init()
node = RotateController()


def abort(_signum=None, _frame=None):
    node.stop()
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, abort)
signal.signal(signal.SIGINT, abort)

try:
    started = time.monotonic()
    while node.yaw is None and time.monotonic() - started < 4.0:
        rclpy.spin_once(node, timeout_sec=0.1)
    if node.yaw is None:
        raise RuntimeError(f"No se recibió {pose_topic}")
    target = wrap(node.yaw + requested)
    started = time.monotonic()
    while True:
        rclpy.spin_once(node, timeout_sec=0.03)
        now = time.monotonic()
        if now - node.last_pose_time > 0.8:
            raise RuntimeError("La odometría dejó de actualizarse")
        error = wrap(target - node.yaw)
        if abs(error) <= math.radians(0.7):
            node.stop()
            print(f"ROTATE_OK error_deg={math.degrees(error):.3f}")
            break
        if now - started > 12.0:
            raise RuntimeError("Tiempo máximo de giro agotado")
        speed = max(-0.22, min(0.22, 1.4 * error))
        if abs(speed) < 0.035:
            speed = math.copysign(0.035, speed)
        node.command(speed)
finally:
    node.stop()
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
PY
INNER
REMOTE
)"
  printf '%s\n' "$output"
  grep -q '^ROTATE_OK ' <<<"$output" || die "No se confirmó la realineación angular."
}

run_forward_arc_to_goal() {
  local goal_x
  local goal_y
  local goal_yaw
  local max_speed="${1:-$APPROACH_MAX_SPEED}"
  local position_tolerance="${2:-0.015}"
  local output

  read -r goal_x goal_y goal_yaw <<<"$INITIAL_POSE"
  [[ -n "$goal_x" && -n "$goal_y" && -n "$goal_yaw" ]] || \
    die "No existe una pose objetivo válida para la aproximación."

  output="$(ssh_vision bash -s -- "$ROS_CONTAINER" "$POSE_TOPIC" "$goal_x" \
    "$goal_y" "$goal_yaw" "$max_speed" "$position_tolerance" <<'REMOTE'
set -Eeuo pipefail
container="$1"
pose_topic="$2"
goal_x="$3"
goal_y="$4"
goal_yaw="$5"
max_speed="$6"
position_tolerance="$7"

timeout 35 docker exec -i "$container" bash -s -- "$pose_topic" "$goal_x" \
  "$goal_y" "$goal_yaw" "$max_speed" "$position_tolerance" <<'INNER'
set -Eeo pipefail
set +u
source /opt/ros/humble/setup.bash
set -u
python3 - "$@" <<'PY'
import math
import signal
import sys
import time

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

pose_topic = sys.argv[1]
goal_x, goal_y, goal_yaw, max_speed, pos_tol = map(float, sys.argv[2:])
max_runtime = 25.0
max_angular_speed = 0.30
min_linear_speed = 0.012
yaw_tolerance = math.radians(1.0)


def wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


class ArcController(Node):
    def __init__(self):
        super().__init__("cruzr_visual_approach_controller")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.publisher = self.create_publisher(TwistStamped, "/cmd_vel_navi", qos)
        self.subscription = self.create_subscription(
            Odometry, pose_topic, self.pose_callback, qos
        )
        self.pose = None
        self.last_pose_time = 0.0

    def pose_callback(self, message):
        p = message.pose.pose.position
        q = message.pose.pose.orientation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )
        self.pose = (p.x, p.y, yaw)
        self.last_pose_time = time.monotonic()

    def command(self, linear, angular):
        message = TwistStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = "base_footprint"
        message.twist.linear.x = float(linear)
        message.twist.angular.z = float(angular)
        self.publisher.publish(message)

    def stop(self):
        for _ in range(10):
            self.command(0.0, 0.0)
            rclpy.spin_once(self, timeout_sec=0.02)


rclpy.init()
node = ArcController()


def abort(_signum=None, _frame=None):
    node.stop()
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, abort)
signal.signal(signal.SIGINT, abort)

try:
    wait_started = time.monotonic()
    while node.pose is None and time.monotonic() - wait_started < 5.0:
        rclpy.spin_once(node, timeout_sec=0.1)
    if node.pose is None:
        raise RuntimeError(f"No se recibió {pose_topic}")

    start_x, start_y, start_yaw = node.pose
    start_distance = math.hypot(goal_x - start_x, goal_y - start_y)
    if not 0.015 <= start_distance <= 0.75:
        raise RuntimeError(
            f"Desplazamiento visual inesperado: {start_distance:.3f} m"
        )

    started = time.monotonic()
    last_progress = started
    best_distance = start_distance

    while True:
        rclpy.spin_once(node, timeout_sec=0.035)
        now = time.monotonic()
        if node.pose is None or now - node.last_pose_time > 0.8:
            raise RuntimeError("La odometría del chasis dejó de actualizarse")

        x, y, yaw = node.pose
        dx = goal_x - x
        dy = goal_y - y
        distance = math.hypot(dx, dy)
        final_yaw_error = wrap(goal_yaw - yaw)

        if distance <= pos_tol:
            if abs(final_yaw_error) <= yaw_tolerance:
                node.stop()
                print(
                    f"APPROACH_MOVE_OK distance_error={distance:.4f} "
                    f"yaw_error_deg={math.degrees(final_yaw_error):.3f} "
                    f"start_distance={start_distance:.4f}"
                )
                break

            # Una corrección angular residual de 3 grados desplaza la caja
            # unos 5 cm en la imagen a un metro. Terminamos con un giro fino
            # en el sitio antes de volver a medir.
            angular = max(-0.12, min(0.12, 1.8 * final_yaw_error))
            node.command(0.0, angular)
            last_progress = now
            continue

        # Control de pose para una base diferencial. alpha dirige el chasis al
        # punto y beta recupera el rumbo final; el resultado es una S suave
        # que desplaza lateralmente y vuelve a dejar el robot paralelo.
        bearing_error = wrap(math.atan2(dy, dx) - yaw)
        beta = wrap(goal_yaw - yaw - bearing_error)

        if distance > pos_tol and abs(bearing_error) > math.radians(75.0):
            raise RuntimeError(
                f"Objetivo fuera del arco frontal: {math.degrees(bearing_error):.1f} grados"
            )
        if now - started > max_runtime:
            raise RuntimeError("Tiempo máximo de aproximación agotado")

        if distance < best_distance - 0.004:
            best_distance = distance
            last_progress = now
        elif now - last_progress > 4.0:
            raise RuntimeError(
                "Sin progreso durante 4 s; posible obstáculo o bloqueo del monitor"
            )

        linear = min(max_speed, max(min_linear_speed, 0.70 * distance))
        if abs(bearing_error) > math.radians(25.0):
            linear = min(linear, 0.035)
        angular = max(
            -max_angular_speed,
            min(max_angular_speed, 1.8 * bearing_error - 0.6 * beta),
        )
        node.command(linear, angular)

except BaseException as error:
    if isinstance(error, KeyboardInterrupt):
        node.stop()
        print("APPROACH_MOVE_ABORTED: señal recibida", file=sys.stderr)
    else:
        # Si la geometría deja de ser alcanzable durante una curva, recuperar
        # el rumbo objetivo antes de abortar. Así el siguiente ciclo conserva
        # la caja dentro del campo frontal de visión.
        recovery_started = time.monotonic()
        recovered = False
        while node.pose is not None and time.monotonic() - recovery_started < 8.0:
            rclpy.spin_once(node, timeout_sec=0.03)
            if time.monotonic() - node.last_pose_time > 0.8:
                break
            current_yaw = node.pose[2]
            recovery_error = wrap(goal_yaw - current_yaw)
            if abs(recovery_error) <= math.radians(1.0):
                recovered = True
                break
            recovery_speed = max(-0.16, min(0.16, 1.5 * recovery_error))
            if abs(recovery_speed) < 0.035:
                recovery_speed = math.copysign(0.035, recovery_speed)
            node.command(0.0, recovery_speed)
        node.stop()
        print(
            "APPROACH_HEADING_RECOVERY=" + ("OK" if recovered else "FAILED"),
            file=sys.stderr,
        )
        print(f"APPROACH_MOVE_ERROR: {error}", file=sys.stderr)
    raise
finally:
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
PY
INNER
REMOTE
)"

  printf '%s\n' "$output"
  grep -q '^APPROACH_MOVE_OK ' <<<"$output" || \
    die "El controlador no confirmó la corrección visual."
}

approach_box_before_arms() {
  local pose
  local camera_x
  local camera_y
  local camera_z
  local camera_yaw_deg
  local plan
  local action
  local forward
  local lateral
  local measured_depth
  local total="0.0"
  local iteration
  local displacement
  local measurement_attempt
  local measurement_ok

  trap 'stop_base_silent' EXIT INT TERM HUP

  info "[APROXIMACIÓN 1/3] Bajando únicamente la cabeza..."
  run_grasp_script --prepare-vision --yes

  for ((iteration=1; iteration<=APPROACH_MAX_ITERATIONS; iteration++)); do
    info "[APROXIMACIÓN 2/3] Midiendo caja (iteración $iteration/$APPROACH_MAX_ITERATIONS)..."
    measurement_ok=0
    for measurement_attempt in 1 2 3; do
      if pose="$(measure_box_pose)"; then
        measurement_ok=1
        break
      fi
      warn "Par visual transitorio descartado (intento ${measurement_attempt}/3)."
      if ((measurement_attempt < 3)); then
        sleep "$APPROACH_SETTLE_SECONDS"
      fi
    done
    ((measurement_ok == 1)) || \
      die "La detección visual de la caja no fue estable tras tres pares nuevos."
    read -r camera_x camera_y camera_z camera_yaw_deg <<<"$pose"
    [[ -n "$camera_x" && -n "$camera_y" && -n "$camera_z" && -n "$camera_yaw_deg" ]] || \
      die "La pose visual de la caja está incompleta."
    info "BOX_POSE_USED=x=${camera_x},y=${camera_y},z=${camera_z} m,yaw=${camera_yaw_deg} deg"

    plan="$(python3 - "$camera_x" "$camera_y" "$camera_z" "$camera_yaw_deg" \
      "$APPROACH_TARGET_DEPTH" "$APPROACH_DEPTH_TOLERANCE" \
      "$APPROACH_CENTER_TOLERANCE" "$APPROACH_MAX_STEP" \
      "$APPROACH_MAX_LATERAL_STEP" "$APPROACH_BACKOFF_CLEARANCE" \
      "$APPROACH_YAW_TOLERANCE_DEG" "$APPROACH_MAX_TOTAL" "$total" <<'PY'
import math
import sys

(
    x,
    y,
    z,
    yaw_deg,
    target,
    tolerance,
    center_tolerance,
    max_step,
    max_lateral,
    backoff_clearance,
    yaw_tolerance_deg,
    max_total,
    total,
) = map(float, sys.argv[1:])
depth_error = z - target
lateral_error = -x  # cámara +X=derecha; base +Y=izquierda

if abs(yaw_deg) > yaw_tolerance_deg:
    print(f"ROTATE {yaw_deg:.6f} 0.000000 {z:.6f}")
elif abs(depth_error) <= tolerance and abs(x) <= center_tolerance:
    if not (0.20 <= y <= 0.75 and 0.65 <= z <= 1.15):
        raise SystemExit(
            f"Pose centrada pero fuera de la ventana de agarre: "
            f"y={y:.3f}, z={z:.3f} m"
        )
    print(f"READY 0.000000 0.000000 {z:.6f}")
else:
    # La base no puede trasladarse de lado. Si está demasiado cerca para una
    # curva de centrado, primero crea espacio retrocediendo.
    required_forward = max(backoff_clearance, 2.0 * abs(lateral_error))
    if abs(x) > center_tolerance and depth_error < required_forward:
        backoff = max(0.04, min(max_step, required_forward - depth_error))
        action, forward, lateral = "BACKOFF", backoff, 0.0
        displacement = backoff
    elif depth_error < -tolerance:
        backoff = max(0.04, min(max_step, -depth_error))
        action, forward, lateral = "BACKOFF", backoff, 0.0
        displacement = backoff
    else:
        action = "MOVE"
        forward = max(0.0, min(max_step, depth_error))
        lateral = 0.0 if abs(x) <= center_tolerance else max(
            -max_lateral, min(max_lateral, lateral_error)
        )
        displacement = math.hypot(forward, lateral)
        if forward < 0.03 and abs(lateral) > center_tolerance:
            raise SystemExit("No existe profundidad suficiente para centrar en avance")

    if total + displacement > max_total + 1e-6:
        raise SystemExit(
            f"La aproximación requerida supera {max_total:.2f} m"
        )
    print(f"{action} {forward:.6f} {lateral:.6f} {z:.6f}")
PY
)" || die "La caja no permite una aproximación automática segura."

    read -r action forward lateral measured_depth <<<"$plan"
    info "BOX_DEPTH=${measured_depth} m; BOX_CENTER_ERROR=${camera_x} m"
    if [[ "$action" == "READY" ]]; then
      info "APPROACH_READY: profundidad=${camera_z} m, centrado=${camera_x} m."
      stop_base
      trap - EXIT INT TERM HUP
      info "[APROXIMACIÓN 3/3] Distancia y orientación validadas antes de extender brazos."
      return 0
    fi
    case "$action" in
      ROTATE)
        info "Realineando chasis con la caja: giro=${forward} grados..."
        rotate_base_relative "$forward"
        displacement="0.000000"
        ;;
      BACKOFF)
        info "Creando espacio para centrar: retroceso=${forward} m..."
        run_backward_segment "$forward" "$APPROACH_MAX_SPEED"
        displacement="$forward"
        ;;
      MOVE)
        info "Corrección visual: avance=${forward} m, lateral=${lateral} m, velocidad máxima=${APPROACH_MAX_SPEED} m/s..."
        capture_initial_pose
        set_relative_goal "$forward" "$lateral"
        run_forward_arc_to_goal "$APPROACH_MAX_SPEED" "0.015"
        displacement="$(python3 -c 'import math,sys; print(f"{math.hypot(float(sys.argv[1]), float(sys.argv[2])):.6f}")' \
          "$forward" "$lateral")"
        ;;
      *)
        die "Decisión de aproximación desconocida: $action"
        ;;
    esac
    stop_base
    # Permite que la base y la imagen se estabilicen antes de comparar el
    # siguiente par de poses. No se reutiliza una lectura tomada durante el
    # final de la corrección anterior.
    sleep "$APPROACH_SETTLE_SECONDS"
    total="$(python3 -c 'import sys; print(f"{float(sys.argv[1]) + float(sys.argv[2]):.6f}")' \
      "$total" "$displacement")"
    info "APPROACH_ACCUMULATED=${total} m"
    if ((FAST == 0)); then
      runtime_safety_check
    fi
  done

  die "No se alcanzó la pose de agarre tras ${APPROACH_MAX_ITERATIONS} correcciones visuales."
}

confirm_once() {
  ((YES == 1)) && return 0
  cat <<'EOF'

CONFIRMACIÓN ÚNICA
La orden moverá físicamente brazos y/o chasis sin nuevas preguntas. Confirma:
  - Ethernet y cargador están físicamente desconectados;
  - la aproximación frontal y 1,50 m detrás están despejados;
  - la caja está vacía, estable, visible y paralela a los hombros;
  - la zona frontal y lateral de corrección está libre;
  - la mesa original permanece inmóvil y estable en la posición de recogida;
  - el paro de emergencia está en manos de otra persona preparada.

Escribe TRANSPORTAR CAJA para continuar:
EOF
  local answer
  read -r answer
  [[ "$answer" == "TRANSPORTAR CAJA" ]] || die "Transporte cancelado."
}

verify_grasp() {
  run_grasp_script --verify-grasp
}

run_round_trip() {
  local total

  trap 'stop_base_silent' EXIT INT TERM HUP

  info "[1/5] Guardando la pose inicial estable..."
  capture_initial_pose

  info "[2/5] Retrocediendo en un único tramo odométrico de ${TOTAL_DISTANCE} m..."
  run_backward_segment "$TOTAL_DISTANCE" "$BACKWARD_MAX_SPEED"
  total="$LAST_SEGMENT_DISTANCE"
  stop_base
  info "RETROCESO_COMPLETADO=${total} m"

  info "[3/5] Confirmando que el agarre continúa vigente..."
  verify_grasp
  flow_safety_check

  info "[4/5] Regresando a la pose inicial a un máximo de ${RETURN_MAX_SPEED} m/s..."
  return_to_initial_pose
  stop_base
  trap - EXIT INT TERM HUP

  info "[5/5] Depositando sobre la mesa original y abriendo los cogedores..."
  if ((FAST == 0)); then
    verify_grasp
  else
    info "FAST_MODE: se omite la verificación duplicada; deposit-held valida el agarre."
  fi
  run_grasp_script --deposit-held --yes

  cat <<EOF

CICLO DE IDA Y VUELTA COMPLETADO
Retroceso solicitado: ${TOTAL_DISTANCE} m.
Retroceso acumulado informado: ${total} m.
El robot volvió a la pose inicial, depositó la caja por contacto y abrió los
cogedores. La base está detenida y la caja ya está libre.
EOF
}

handoff_to_automatic_home() {
  info "[HOME AUTOMÁTICO] Caja liberada; transfiriendo el control a la recuperación..."

  # recover_to_home puede invocar este mismo script con --retreat-only. Hay
  # que liberar primero el flock del ciclo exterior para evitar un interbloqueo.
  flock -u 9
  if ((FAST == 1)); then
    exec "$RECOVERY_SCRIPT" --run --yes --fast
  else
    exec "$RECOVERY_SCRIPT" --run --yes
  fi
}

run_retreat_only() {
  local total

  trap 'stop_base_silent' EXIT INT TERM HUP

  info "[1/4] Confirmando odometría estable..."
  capture_initial_pose

  info "[2/4] Separándose de la mesa en un único tramo odométrico de ${TOTAL_DISTANCE} m..."
  run_backward_segment "$TOTAL_DISTANCE" "$BACKWARD_MAX_SPEED"
  total="$LAST_SEGMENT_DISTANCE"
  stop_base
  trap - EXIT INT TERM HUP

  info "[3/4] Retroceso verificado continuamente por odometría."
  info "[4/4] RETREAT_COMPLETED=${total} m"
  info "La base quedó detenida detrás de la pose inicial; no se movieron los brazos."
}

validate_return_target_pose() {
  python3 - "$RETURN_TARGET_POSE" <<'PY'
import math
import sys

try:
    pose = tuple(map(float, sys.argv[1].split()))
except ValueError as exc:
    raise SystemExit(f"Pose de retorno inválida: {exc}")
if len(pose) != 3 or not all(math.isfinite(value) for value in pose):
    raise SystemExit("La pose de retorno debe contener tres números finitos: X Y YAW")
print("RETURN_TARGET_POSE_VALID")
PY
}

run_grasp_only() {
  nav_preflight
  confirm_once
  approach_box_before_arms
  flow_safety_check
  run_grasp_script --grasp-after-approach --yes
  if ((FAST == 0)); then
    verify_grasp
  fi
  flow_safety_check
  info "GRASP_ONLY_COMPLETED: la caja queda elevada y sujeta; la base no se ha retirado."
}

run_return_held_to_pose() {
  validate_return_target_pose
  verify_grasp
  flow_safety_check
  confirm_once
  INITIAL_POSE="$RETURN_TARGET_POSE"
  trap 'stop_base_silent' EXIT INT TERM HUP
  info "Regresando con la caja a la pose de mesa solicitada..."
  return_to_initial_pose
  stop_base
  trap - EXIT INT TERM HUP
  verify_grasp
  info "RETURN_HELD_TO_POSE_COMPLETED: pose recuperada; la caja continúa sujeta."
}

run_advance_held_distance() {
  ADVANCE_DISTANCE="$(python3 - "$ADVANCE_DISTANCE" <<'PY'
import math, sys
try:
    distance=float(sys.argv[1])
except ValueError as exc:
    raise SystemExit(f"Distancia de avance inválida: {exc}")
if not math.isfinite(distance) or not 0.10 <= distance <= 0.65:
    raise SystemExit("La distancia de avance debe estar entre 0,10 y 0,65 m")
print(f"{distance:.6f}")
PY
)"
  verify_grasp
  flow_safety_check
  confirm_once
  capture_initial_pose
  set_relative_goal "$ADVANCE_DISTANCE" 0
  trap 'stop_base_silent' EXIT INT TERM HUP
  info "Avanzando ${ADVANCE_DISTANCE} m con la caja sujeta..."
  return_to_initial_pose
  stop_base
  trap - EXIT INT TERM HUP
  verify_grasp
  info "ADVANCE_HELD_COMPLETED=${ADVANCE_DISTANCE} m; la caja continúa sujeta."
}

confirm_base_correction() {
  ((YES == 1)) && return 0
  cat <<'EOF'

CONFIRMACIÓN DE CORRECCIÓN LOCAL
La orden moverá solamente el chasis una distancia o un ángulo pequeños.
Confirma que Ethernet y cargador están desconectados, la envolvente completa
del robot y de una posible caja está despejada y el paro está preparado.

Escribe CORREGIR BASE para continuar:
EOF
  local answer
  read -r answer
  [[ "$answer" == "CORREGIR BASE" ]] || die "Corrección local cancelada."
}

run_move_relative() {
  local forward
  local lateral

  read -r forward lateral <<<"$RELATIVE_MOVE"
  [[ -n "$forward" && -n "$lateral" ]] || \
    die "--move-relative necesita exactamente dos valores: \"AVANCE LATERAL\"."
  RELATIVE_MOVE="$(python3 - "$forward" "$lateral" <<'PY'
import math
import sys

try:
    forward, lateral = map(float, sys.argv[1:])
except ValueError as exc:
    raise SystemExit(f"Corrección relativa inválida: {exc}")
distance = math.hypot(forward, lateral)
bearing = abs(math.atan2(lateral, forward))
if not all(math.isfinite(value) for value in (forward, lateral)):
    raise SystemExit("La corrección contiene un valor no finito")
if not 0.025 <= forward <= 0.20:
    raise SystemExit("El avance debe estar entre 0,025 y 0,20 m")
if abs(lateral) > 0.08:
    raise SystemExit("La corrección lateral supera 0,08 m")
if distance > 0.21 or bearing > math.radians(45.0):
    raise SystemExit("La corrección no pertenece al arco frontal permitido")
print(f"{forward:.6f} {lateral:.6f}")
PY
)"
  read -r forward lateral <<<"$RELATIVE_MOVE"

  flow_safety_check
  confirm_base_correction
  capture_initial_pose
  set_relative_goal "$forward" "$lateral"
  trap 'stop_base_silent' EXIT INT TERM HUP
  info "Corrigiendo base: avance=${forward} m, lateral=${lateral} m..."
  run_forward_arc_to_goal "0.05" "0.012"
  stop_base
  trap - EXIT INT TERM HUP
  info "RELATIVE_MOVE_COMPLETED=forward:${forward},lateral:${lateral}"
}

run_rotate_relative_mode() {
  RELATIVE_ROTATION="$(python3 - "$RELATIVE_ROTATION" <<'PY'
import math
import sys

try:
    angle = float(sys.argv[1])
except ValueError as exc:
    raise SystemExit(f"Ángulo inválido: {exc}")
if not math.isfinite(angle) or not 0.7 <= abs(angle) <= 10.0:
    raise SystemExit("El giro debe estar entre 0,7 y 10 grados en valor absoluto")
print(f"{angle:.6f}")
PY
)"
  flow_safety_check
  confirm_base_correction
  trap 'stop_base_silent' EXIT INT TERM HUP
  info "Corrigiendo orientación de la base: ${RELATIVE_ROTATION} grados..."
  rotate_base_relative "$RELATIVE_ROTATION"
  stop_base
  trap - EXIT INT TERM HUP
  info "RELATIVE_ROTATION_COMPLETED=${RELATIVE_ROTATION} deg"
}

run_backward_distance_mode() {
  BACKWARD_DISTANCE="$(python3 - "$BACKWARD_DISTANCE" <<'PY'
import math
import sys

try:
    distance = float(sys.argv[1])
except ValueError as exc:
    raise SystemExit(f"Distancia inválida: {exc}")
if not math.isfinite(distance) or not 0.02 <= distance <= 0.15:
    raise SystemExit("El retroceso debe estar entre 0,02 y 0,15 m")
print(f"{distance:.6f}")
PY
)"
  flow_safety_check
  confirm_base_correction
  trap 'stop_base_silent' EXIT INT TERM HUP
  info "Creando espacio para la alineación: retroceso=${BACKWARD_DISTANCE} m..."
  run_backward_segment "$BACKWARD_DISTANCE" "0.04"
  stop_base
  trap - EXIT INT TERM HUP
  info "BACKWARD_DISTANCE_COMPLETED=${BACKWARD_DISTANCE} m"
}

main() {
  require_local_tools
  exec 9>"/tmp/cruzr_blue_workbin_carry_back.lock"
  flock -n 9 || die "Ya hay otro transporte local en ejecución."
  select_connection

  case "$MODE" in
    check)
      local wired_interface=""
      run_grasp_script --check
      nav_preflight
      capture_initial_pose
      if wired_interface="$(active_wired_motion_interface)"; then
        warn "--run se bloqueará hasta desconectar físicamente el Ethernet activo en $wired_interface."
        info "CONTROL_LINK=wifi:$CONTROL_INTERFACE;wired-tether:$wired_interface"
      elif is_wireless_interface "$CONTROL_INTERFACE"; then
        info "CONTROL_LINK=wifi:$CONTROL_INTERFACE"
      else
        warn "El chequeo es válido, pero --run se bloqueará mientras se use $CONTROL_INTERFACE."
        info "CONTROL_LINK=wired:$CONTROL_INTERFACE"
      fi
      info "CHECK_OK: no se instaló ni movió nada."
      ;;
    run)
      require_wireless_run
      nav_preflight
      confirm_once
      approach_box_before_arms
      flow_safety_check
      run_grasp_script --grasp-after-approach --yes
      if ((FAST == 0)); then
        verify_grasp
      else
        info "FAST_MODE: el propio agarre ya confirmó contacto y fuerzas; se omite la lectura duplicada."
      fi
      flow_safety_check
      run_round_trip
      handoff_to_automatic_home
      ;;
    align-only)
      require_wireless_run
      nav_preflight
      confirm_once
      approach_box_before_arms
      info "ALIGNMENT_OK: caja centrada y a profundidad de agarre; brazos recogidos."
      ;;
    move-held)
      require_wireless_run
      verify_grasp
      nav_preflight
      confirm_once
      run_round_trip
      handoff_to_automatic_home
      ;;
    retreat-only)
      require_wireless_run
      if ((FAST == 0)); then
        run_grasp_script --check
      fi
      flow_safety_check
      confirm_once
      run_retreat_only
      ;;
    grasp-only)
      require_wireless_run
      run_grasp_only
      ;;
    return-held-to-pose)
      require_wireless_run
      run_return_held_to_pose
      ;;
    advance-held-distance)
      require_wireless_run
      run_advance_held_distance
      ;;
    move-relative)
      require_wireless_run
      run_move_relative
      ;;
    rotate-relative)
      require_wireless_run
      run_rotate_relative_mode
      ;;
    backward-distance)
      require_wireless_run
      run_backward_distance_mode
      ;;
    *)
      die "Modo interno desconocido: $MODE"
      ;;
  esac
}

main
