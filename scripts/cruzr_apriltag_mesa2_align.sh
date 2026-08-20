#!/usr/bin/env bash

set -Eeuo pipefail

# Alineación fina del chasis con la mesa 2 mediante el AprilTag 113. La pose
# objetivo procede de tres aproximaciones físicas independientes validadas el
# 14-08-2026. Este script nunca mueve los brazos ni abre los cogedores.

readonly ROBOT_USER="walker"
readonly WIFI_GATEWAY="192.168.42.2"
readonly VISION_HOST="192.168.11.3"
readonly MOTION_HOST="192.168.11.2"
readonly DEFAULT_PASSWORD="aa"
readonly ROS_CONTAINER="walker-ros.ros2-1"
readonly TAG_TOPIC="/sensor/camera/stereo/april_tag/results"
readonly TAG_SERVICE="/apriltag/start_detecting"
readonly TAG_TYPE="sensor_task_msgs/msg/AprilTagDetectionArray"
readonly TAG_ID="113"
readonly TAG_SIZE="0.0735"
readonly TAG_FRAME="mesa2_tag113"
readonly CAMERA_FRAME="stereo_left_rectified_optical_frame"

readonly TARGET_X="-0.027403734"
readonly TARGET_Y="0.021092044"
readonly TARGET_Z="1.138346576"
readonly TARGET_QX="-0.976405603"
readonly TARGET_QY="0.011121442"
readonly TARGET_QZ="-0.014522428"
readonly TARGET_QW="0.215168563"

# Referencia provisional con el contenedor sujeto. Se obtuvo en la misma pose
# física de depósito, con un error de mapa de 4,0 mm y 0,32 grados, usando 20
# detecciones estables. Debe repetirse en ciclos posteriores antes de elevarla
# a referencia definitiva de producción.
readonly HELD_TARGET_X="-0.022617825"
readonly HELD_TARGET_Y="-0.122600795"
readonly HELD_TARGET_Z="0.803420107"
readonly HELD_TARGET_QX="-0.975321264"
readonly HELD_TARGET_QY="0.009621669"
readonly HELD_TARGET_QZ="-0.004721560"
readonly HELD_TARGET_QW="0.220530186"

FLUID_MODE="${CRUZR_FLUID_MODE:-0}"
[[ "$FLUID_MODE" == "0" || "$FLUID_MODE" == "1" ]] || {
  echo "CRUZR_FLUID_MODE debe ser 0 o 1" >&2
  exit 2
}
if ((FLUID_MODE == 1)); then
  POSITION_TOLERANCE="0.050"
  SWING_TOLERANCE_DEG="3.5"
  MAX_FORWARD_STEP="0.18"
  MAX_ITERATIONS="4"
  SAMPLE_COUNT="3"
  ALIGNMENT_SETTLE_SECONDS="0.20"
else
  POSITION_TOLERANCE="0.035"
  SWING_TOLERANCE_DEG="2.0"
  MAX_FORWARD_STEP="0.12"
  MAX_ITERATIONS="8"
  SAMPLE_COUNT="7"
  ALIGNMENT_SETTLE_SECONDS="0.80"
fi
readonly FLUID_MODE POSITION_TOLERANCE SWING_TOLERANCE_DEG \
  MAX_FORWARD_STEP MAX_ITERATIONS SAMPLE_COUNT \
  ALIGNMENT_SETTLE_SECONDS
readonly VERTICAL_TOLERANCE="0.030"
readonly YAW_TOLERANCE_DEG="2.0"
readonly MAX_SWING_DEG="5.0"
readonly MAX_VERTICAL_ERROR="0.050"
# Con move_head_lower, un avance horizontal aparece en la cámara como una
# variación acoplada Y/Z. La pendiente corresponde a una inclinación de unos
# 25 grados y fue confirmada entre MESA2_PRE y MESA2_DROP_TARGET.
readonly GROUND_Y_PER_Z="0.466"
APRILTAG_EXTENDED="${CRUZR_APRILTAG_EXTENDED:-0}"
[[ "$APRILTAG_EXTENDED" == "0" || "$APRILTAG_EXTENDED" == "1" ]] || {
  echo "CRUZR_APRILTAG_EXTENDED debe ser 0 o 1" >&2
  exit 2
}
if ((APRILTAG_EXTENDED == 1)); then
  # La corrección lateral de una base diferencial necesita crear primero un
  # arco con un pequeño retroceso. El presupuesto cuenta recorrido absoluto,
  # no desplazamiento neto, por lo que 0,75 m interrumpía ciclos convergentes.
  MAX_TRANSLATION_TOTAL="1.10"
  if ((FLUID_MODE == 1)); then
    ALIGNMENT_MAX_ITERATIONS="8"
  else
    ALIGNMENT_MAX_ITERATIONS="12"
  fi
else
  MAX_TRANSLATION_TOTAL="0.45"
  ALIGNMENT_MAX_ITERATIONS="$MAX_ITERATIONS"
fi
readonly APRILTAG_EXTENDED MAX_TRANSLATION_TOTAL ALIGNMENT_MAX_ITERATIONS
readonly COARSE_CAPTURE_DZ="0.40"
# La alineación fina admite pasos de 0,12/0,18 m. Un margen de entrada de
# 0,05 m evita ordenar un tramo mínimo de 0,10 m solo por ruido o por la
# tolerancia de parada odométrica cuando dz está apenas sobre 0,40 m.
readonly COARSE_CAPTURE_HYSTERESIS="0.05"
readonly COARSE_POSITION_STD_MAX="0.010"
readonly COARSE_MAX_TOTAL="1.20"
readonly COARSE_MAX_ITERATIONS="5"
readonly MAX_AMBIGUOUS_ORIENTATION_SAMPLES="3"

readonly CARRY_SCRIPT_NAME="cruzr_blue_workbin_carry_back.sh"
readonly CYCLE_SCRIPT_NAME="cruzr_blue_workbin_cycle.sh"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD

if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

SCRIPT_PATH="$(readlink -f -- "$0")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly SCRIPT_PATH SCRIPT_DIR
readonly CARRY_SCRIPT="$SCRIPT_DIR/$CARRY_SCRIPT_NAME"
readonly CYCLE_SCRIPT="$SCRIPT_DIR/$CYCLE_SCRIPT_NAME"

MODE="check"
YES=0
FAST=0
CONTROL_INTERFACE=""
VISION_SSH_HOST=""
DETECTOR_STARTED=0

usage() {
  cat <<'EOF'
Uso:
  ./scripts/cruzr_apriltag_mesa2_align.sh --check
  ./scripts/cruzr_apriltag_mesa2_align.sh --check-visible
  ./scripts/cruzr_apriltag_mesa2_align.sh --measure
  ./scripts/cruzr_apriltag_mesa2_align.sh --measure-held
  ./scripts/cruzr_apriltag_mesa2_align.sh --measure-held-target [--fast]
  ./scripts/cruzr_apriltag_mesa2_align.sh --align-empty [--yes] [--fast]
  ./scripts/cruzr_apriltag_mesa2_align.sh --align-held [--yes] [--fast]
  ./scripts/cruzr_apriltag_mesa2_align.sh --coarse-held [--yes] [--fast]

Modos:
  --check       Comprueba contenedor, servicio y tópico AprilTag. No mueve.
  --check-visible
                Confirma una detección estable del tag 113 sin compararla con
                una pose objetivo. No mueve el robot.
  --measure     Mide el tag 113 y muestra el error respecto al objetivo. No mueve.
  --measure-held
                Mide el error respecto al objetivo calibrado con la caja
                sujeta. No mueve el robot ni modifica la calibración.
  --measure-held-target
                Verifica un agarre vigente y registra 20 muestras como
                candidata de calibración con carga. No mueve.
  --align-empty Alinea solamente el chasis durante las pruebas sin caja.
  --align-held  Exige un agarre vigente antes y después de alinear el chasis.
  --coarse-held Con la caja sujeta, usa el tag para avanzar solamente lo que
                falta hasta dejar el error frontal dentro de 0,40 m. No abre
                los cogedores y no sustituye la alineación fina posterior.

La cabeza debe encontrarse en la misma postura move_head_lower utilizada en
la calibración. El script nunca mueve los brazos ni ordena abrir los cogedores.
Cada corrección queda limitada a 4 grados, 0,12 m de avance, 0,05 m lateral
o 0,10 m de retroceso. Si el tag desaparece o el error deja de converger, el
robot se detiene y una posible caja permanece sujeta.
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
    --check|--check-visible|--measure|--measure-held|--measure-held-target|--align-empty|--align-held|--coarse-held)
      MODE="${1#--}"
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
  for command_name in ssh setsid nc ip readlink flock python3 awk; do
    command -v "$command_name" >/dev/null 2>&1 || \
      die "Falta el comando local '$command_name'."
  done
  [[ -x "$CARRY_SCRIPT" ]] || die "No existe o no es ejecutable: $CARRY_SCRIPT"
  [[ -x "$CYCLE_SCRIPT" ]] || die "No existe o no es ejecutable: $CYCLE_SCRIPT"
}

route_interface() {
  ip -o route get "$1" 2>/dev/null | \
    awk '{for (i=1; i<=NF; i++) if ($i=="dev") {print $(i+1); exit}}'
}

is_wireless_interface() {
  [[ -n "$1" && -d "/sys/class/net/$1/wireless" ]]
}

select_connection() {
  local interface
  if nc -z -w2 "$WIFI_GATEWAY" 22 >/dev/null 2>&1; then
    interface="$(route_interface "$WIFI_GATEWAY")"
    if is_wireless_interface "$interface"; then
      VISION_SSH_HOST="$WIFI_GATEWAY"
      CONTROL_INTERFACE="$interface"
      info "Conexión: Wi-Fi mediante vision ($CONTROL_INTERFACE)"
      return
    fi
  fi
  if nc -z -w2 "$VISION_HOST" 22 >/dev/null 2>&1; then
    VISION_SSH_HOST="$VISION_HOST"
    CONTROL_INTERFACE="$(route_interface "$VISION_HOST")"
    info "Conexión: directa a vision ($CONTROL_INTERFACE)"
    return
  fi
  die "No se alcanza vision por $WIFI_GATEWAY ni $VISION_HOST."
}

active_wired_motion_interface() {
  local interface=""
  if nc -z -w1 "$MOTION_HOST" 22 >/dev/null 2>&1; then
    interface="$(route_interface "$MOTION_HOST")"
    if [[ -n "$interface" ]] && ! is_wireless_interface "$interface" && \
       [[ "$(cat "/sys/class/net/$interface/carrier" 2>/dev/null || true)" == "1" ]]; then
      printf '%s\n' "$interface"
      return 0
    fi
  fi
  return 1
}

require_wireless_run() {
  local interface=""
  is_wireless_interface "$CONTROL_INTERFACE" || \
    die "La ruta de control no usa Wi-Fi; desconecta Ethernet."
  if interface="$(active_wired_motion_interface)"; then
    die "Se detecta Ethernet activo en $interface; desconecta físicamente el cable."
  fi
}

ssh_vision() {
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w ssh \
    -o ConnectTimeout=8 \
    -o ConnectionAttempts=1 \
    -o ServerAliveInterval=4 \
    -o ServerAliveCountMax=3 \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -o NumberOfPasswordPrompts=2 \
    -o StrictHostKeyChecking=accept-new \
    "$ROBOT_USER@$VISION_SSH_HOST" "$@"
}

carry_args() {
  local -a args=("$@")
  ((FAST == 1)) && args+=(--fast)
  "$CARRY_SCRIPT" "${args[@]}"
}

cycle_args() {
  local -a args=("$@")
  ((FAST == 1)) && args+=(--fast)
  "$CYCLE_SCRIPT" "${args[@]}"
}

detector_preflight() {
  ssh_vision bash -s -- "$ROS_CONTAINER" "$TAG_SERVICE" "$TAG_TOPIC" "$TAG_TYPE" <<'REMOTE'
set -Eeuo pipefail
container="$1"
service="$2"
topic="$3"
expected_type="$4"
[[ "$(hostname)" == "vision" ]] || exit 30
[[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || exit 31
docker exec -i "$container" bash -s -- "$service" "$topic" "$expected_type" <<'INNER'
set -Eeo pipefail
set +u
source /opt/ros/humble/setup.bash
set -u
export ROS2CLI_DISABLE_DAEMON=1
service="$1"
topic="$2"
expected_type="$3"
timeout 10 ros2 service type "$service" | grep -q '^sensor_task_msgs/srv/AprilTagStartDetecting$'
actual_type="$(timeout 10 ros2 topic type "$topic")"
[[ "$actual_type" == "$expected_type" ]]
python3 -c 'import rclpy; from sensor_task_msgs.msg import AprilTagDetectionArray'
printf 'APRILTAG_SERVICE=%s\nAPRILTAG_TOPIC=%s\nAPRILTAG_TYPE=%s\n' \
  "$service" "$topic" "$actual_type"
INNER
REMOTE
}

set_detector() {
  local enabled="$1"
  local output
  output="$(ssh_vision bash -s -- "$ROS_CONTAINER" "$enabled" "$TAG_SERVICE" \
    "$TAG_ID" "$TAG_SIZE" "$TAG_FRAME" <<'REMOTE'
set -Eeuo pipefail
container="$1"
enabled="$2"
service="$3"
tag_id="$4"
tag_size="$5"
tag_frame="$6"
docker exec -i "$container" bash -s -- "$enabled" "$service" "$tag_id" \
  "$tag_size" "$tag_frame" <<'INNER'
set -Eeo pipefail
set +u
source /opt/ros/humble/setup.bash
set -u
export ROS2CLI_DISABLE_DAEMON=1
enabled="$1"
service="$2"
tag_id="$3"
tag_size="$4"
tag_frame="$5"
request="{start_detecting: $enabled, img_topic_name: '/sensor/camera/stereo/color/raw', tag_id: $tag_id, tag_size: $tag_size, tag_frame: '$tag_frame'}"
output="$(timeout 15 ros2 service call "$service" \
  sensor_task_msgs/srv/AprilTagStartDetecting "$request")"
printf '%s\n' "$output"
grep -Eq 'ok=True|ok:[[:space:]]*true' <<<"$output"
INNER
REMOTE
)"
  printf '%s\n' "$output"
  if [[ "$enabled" == "true" ]]; then
    DETECTOR_STARTED=1
  else
    DETECTOR_STARTED=0
  fi
}

stop_detector_silent() {
  ((DETECTOR_STARTED == 1)) || return 0
  set +e
  set_detector false >/dev/null 2>&1
  set -e
}

measure_tag_pose() {
  local count="${1:-$SAMPLE_COUNT}"
  local allow_orientation_ambiguity="${2:-0}"
  local position_std_max="${3:-0.004}"
  [[ "$allow_orientation_ambiguity" == "0" || "$allow_orientation_ambiguity" == "1" ]] || \
    die "allow_orientation_ambiguity debe ser 0 o 1."
  python3 - "$position_std_max" <<'PY' >/dev/null
import math
import sys
value = float(sys.argv[1])
if not math.isfinite(value) or not 0.004 <= value <= 0.010:
    raise SystemExit("position_std_max debe estar entre 0.004 y 0.010 m")
PY
  ssh_vision bash -s -- "$ROS_CONTAINER" "$TAG_TOPIC" "$TAG_ID" "$TAG_SIZE" \
    "$TAG_FRAME" "$CAMERA_FRAME" "$count" "$allow_orientation_ambiguity" \
    "$position_std_max" <<'REMOTE'
set -Eeuo pipefail
container="$1"
shift
timeout 28 docker exec -i "$container" bash -s -- "$@" <<'INNER'
set -Eeo pipefail
set +u
source /opt/ros/humble/setup.bash
set -u
python3 - "$@" <<'PY'
import math
import statistics
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_task_msgs.msg import AprilTagDetectionArray

(
    topic,
    expected_id,
    expected_size,
    expected_tag_frame,
    expected_camera_frame,
    count,
    allow_orientation_ambiguity,
    position_std_max,
) = sys.argv[1:]
expected_id = int(expected_id)
expected_size = float(expected_size)
count = int(count)
allow_orientation_ambiguity = bool(int(allow_orientation_ambiguity))
position_std_max = float(position_std_max)


class Collector(Node):
    def __init__(self):
        super().__init__("cruzr_mesa2_apriltag_collector")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.samples = []
        self.stamps = set()
        self.subscription = self.create_subscription(
            AprilTagDetectionArray, topic, self.callback, qos
        )

    def callback(self, message):
        for detection in message.detections:
            if int(detection.id) != expected_id:
                continue
            if detection.family != "tag36h11" or int(detection.hamming) != 0:
                continue
            if abs(float(detection.size) - expected_size) > 0.0002:
                continue
            if detection.frame != expected_tag_frame:
                continue
            if detection.pose.header.frame_id != expected_camera_frame:
                continue
            stamp = detection.pose.header.stamp
            key = (int(stamp.sec), int(stamp.nanosec))
            if key in self.stamps:
                continue
            p = detection.pose.pose.pose.position
            q = detection.pose.pose.pose.orientation
            values = (p.x, p.y, p.z, q.x, q.y, q.z, q.w, detection.decision_margin)
            if not all(math.isfinite(float(value)) for value in values):
                continue
            if float(detection.decision_margin) < 100.0:
                continue
            norm = math.sqrt(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w)
            if abs(norm - 1.0) > 0.03:
                continue
            self.stamps.add(key)
            self.samples.append(tuple(float(value) for value in values))


def normalize(q):
    norm = math.sqrt(sum(value*value for value in q))
    return tuple(value/norm for value in q)


rclpy.init()
node = Collector()
try:
    started = time.monotonic()
    while len(node.samples) < count and time.monotonic() - started < 20.0:
        rclpy.spin_once(node, timeout_sec=0.15)
    if len(node.samples) < count:
        raise RuntimeError(
            f"Solo se recibieron {len(node.samples)}/{count} detecciones válidas del tag {expected_id}"
        )
    samples = node.samples[:count]
finally:
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()

positions = [sample[:3] for sample in samples]
reference = samples[0][3:7]
quaternions = []
for sample in samples:
    q = sample[3:7]
    if sum(a*b for a, b in zip(reference, q)) < 0.0:
        q = tuple(-value for value in q)
    quaternions.append(q)

position = tuple(statistics.median(p[index] for p in positions) for index in range(3))
quaternion = normalize(tuple(
    statistics.median(q[index] for q in quaternions) for index in range(4)
))
std = tuple(statistics.pstdev(p[index] for p in positions) for index in range(3))
angles = []
for q in quaternions:
    q = normalize(q)
    dot = min(1.0, abs(sum(a*b for a, b in zip(quaternion, q))))
    angles.append(math.degrees(2.0 * math.acos(dot)))
margin_min = min(sample[7] for sample in samples)

if max(std) > position_std_max:
    raise RuntimeError(
        "Pose AprilTag inestable: desviación="
        + ",".join(f"{v*1000:.2f}" for v in std)
        + f" mm; límite={position_std_max*1000:.1f} mm"
    )
if max(angles) > 2.0 and not allow_orientation_ambiguity:
    raise RuntimeError(f"Orientación AprilTag inestable: {max(angles):.2f} grados")

print(
    "TAG_POSE="
    + " ".join(f"{value:.9f}" for value in (*position, *quaternion))
)
print(
    f"TAG_QUALITY=samples:{count},std_mm:"
    + ",".join(f"{value*1000:.3f}" for value in std)
    + f",max_angle_deg:{max(angles):.3f},margin_min:{margin_min:.3f}"
)
if max(angles) > 2.0:
    print(
        "TAG_ORIENTATION_AMBIGUOUS="
        f"spread_deg:{max(angles):.3f},policy:position_only_candidate"
    )
PY
INNER
REMOTE
}

compute_plan() {
  local pose="$1"
  local orientation_fallback="${2:-0}"
  local target_x="$TARGET_X"
  local target_y="$TARGET_Y"
  local target_z="$TARGET_Z"
  local target_qx="$TARGET_QX"
  local target_qy="$TARGET_QY"
  local target_qz="$TARGET_QZ"
  local target_qw="$TARGET_QW"

  if [[ "$MODE" == "align-held" || "$MODE" == "measure-held" || "$MODE" == "coarse-held" ]]; then
    target_x="$HELD_TARGET_X"
    target_y="$HELD_TARGET_Y"
    target_z="$HELD_TARGET_Z"
    target_qx="$HELD_TARGET_QX"
    target_qy="$HELD_TARGET_QY"
    target_qz="$HELD_TARGET_QZ"
    target_qw="$HELD_TARGET_QW"
  fi

  python3 - "$pose" "$target_x" "$target_y" "$target_z" \
    "$target_qx" "$target_qy" "$target_qz" "$target_qw" \
    "$POSITION_TOLERANCE" "$VERTICAL_TOLERANCE" "$YAW_TOLERANCE_DEG" \
    "$SWING_TOLERANCE_DEG" "$MAX_SWING_DEG" "$MAX_VERTICAL_ERROR" \
    "$GROUND_Y_PER_Z" "$MAX_FORWARD_STEP" "$orientation_fallback" <<'PY'
import math
import sys

current = tuple(map(float, sys.argv[1].split()))
target = tuple(map(float, sys.argv[2:9]))
(
    pos_tol,
    vertical_tol,
    yaw_tol,
    swing_tol,
    max_swing,
    max_vertical,
    ground_y_per_z,
    max_forward_step,
) = map(float, sys.argv[9:-1])
orientation_fallback = int(sys.argv[-1])
if len(current) != 7:
    raise SystemExit("TAG_POSE debe contener posición y cuaternión")


def wxyz(q):
    x, y, z, w = q
    return w, x, y, z


def multiply(a, b):
    w, x, y, z = a
    W, X, Y, Z = b
    return (
        w*W - x*X - y*Y - z*Z,
        w*X + x*W + y*Z - z*Y,
        w*Y - x*Z + y*W + z*X,
        w*Z + x*Y - y*X + z*W,
    )


def conjugate(q):
    return q[0], -q[1], -q[2], -q[3]


def normalize(q):
    norm = math.sqrt(sum(value*value for value in q))
    return tuple(value/norm for value in q)


cx, cy, cz = current[:3]
tx, ty, tz = target[:3]
cq = normalize(wxyz(current[3:]))
tq = normalize(wxyz(target[3:]))
if sum(a*b for a, b in zip(cq, tq)) < 0.0:
    tq = tuple(-value for value in tq)

# inv(R_actual) * R_objetivo expresa el error en los ejes del tag. El giro
# del chasis alrededor de la normal del tag aparece como twist Z local y con
# signo contrario al giro que debe ejecutar la base.
relative = normalize(multiply(conjugate(cq), tq))
if relative[0] < 0.0:
    relative = tuple(-value for value in relative)
twist_norm = math.hypot(relative[0], relative[3])
if twist_norm < 1e-8:
    raise SystemExit("No se pudo separar el giro normal del AprilTag")
twist = (relative[0]/twist_norm, 0.0, 0.0, relative[3]/twist_norm)
swing = normalize(multiply(relative, conjugate(twist)))
tag_twist_deg = math.degrees(2.0 * math.atan2(twist[3], twist[0]))
base_yaw_deg = -tag_twist_deg
swing_deg = math.degrees(2.0 * math.acos(min(1.0, abs(swing[0]))))

dx, dy, dz = cx-tx, cy-ty, cz-tz
planar = math.hypot(dx, dz)
# La base se desplaza horizontalmente y la cámara está inclinada. Por tanto,
# dy varía de forma previsible mientras se corrige dz. Solo la componente
# perpendicular a esa dirección indica altura/postura incompatibles.
vertical_residual = dy + ground_y_per_z*dz
print(
    f"TAG_ERROR=x_mm:{dx*1000:.2f},y_mm:{dy*1000:.2f},z_mm:{dz*1000:.2f},"
    f"planar_mm:{planar*1000:.2f},base_yaw_deg:{base_yaw_deg:.3f},"
    f"swing_deg:{swing_deg:.3f},vertical_residual_mm:{vertical_residual*1000:.2f}"
)

if orientation_fallback:
    # La PnP de un único marcador plano puede alternar entre dos soluciones
    # angulares aun cuando la traslación sea estable. En fallback no se envía
    # ningún giro derivado de ese cuaternión ambiguo.
    base_yaw_deg = 0.0
    print("ORIENTATION_POLICY=position_vertical_fallback")

if swing_deg > max_swing and not orientation_fallback:
    print("PLAN=FAIL_HEAD 0 0")
elif abs(vertical_residual) > max_vertical:
    print("PLAN=FAIL_VERTICAL 0 0")
elif (
    planar <= pos_tol
    and abs(dx) <= pos_tol
    and abs(dz) <= pos_tol
    and abs(vertical_residual) <= vertical_tol
    and abs(base_yaw_deg) <= yaw_tol
    and (swing_deg <= swing_tol or orientation_fallback)
):
    print("PLAN=READY 0 0")
elif abs(base_yaw_deg) > yaw_tol:
    rotation = max(-4.0, min(4.0, base_yaw_deg))
    print(f"PLAN=ROTATE {rotation:.6f} 0")
else:
    lateral = -dx
    forward = dz
    required_forward = max(0.035, 2.0*abs(lateral))
    if forward < -pos_tol:
        backoff = max(0.025, min(0.10, -forward))
        print(f"PLAN=BACKOFF {backoff:.6f} 0")
    # Aunque cada eje esté apenas dentro de su tolerancia, el error planar
    # combinado puede seguir fuera. Una base diferencial no debe intentar una
    # microcorrección casi lateral: primero crea longitud de arco suficiente.
    elif planar > pos_tol and abs(lateral) > 0.5*pos_tol and forward < required_forward:
        backoff = max(0.025, min(0.10, required_forward-forward))
        print(f"PLAN=BACKOFF {backoff:.6f} 0")
    else:
        forward = max(0.025, min(max_forward_step, forward))
        lateral = max(-0.05, min(0.05, lateral))
        if abs(lateral) > forward:
            lateral = math.copysign(forward, lateral)
        print(f"PLAN=MOVE {forward:.6f} {lateral:.6f}")
PY
}

confirm_alignment() {
  ((YES == 1)) && return 0
  cat <<'EOF'

CONFIRMACIÓN DE ALINEACIÓN APRILTAG
El chasis realizará correcciones pequeñas frente a la mesa 2. Confirma que:
  - la cabeza mantiene la postura move_head_lower de la calibración;
  - Ethernet y cargador están desconectados;
  - la envolvente del robot y de la caja está despejada;
  - el tag 113 está fijo y visible;
  - otra persona mantiene el paro preparado.

Escribe ALINEAR MESA2 para continuar:
EOF
  local answer
  read -r answer
  [[ "$answer" == "ALINEAR MESA2" ]] || die "Alineación cancelada."
}

run_measurement() {
  local output
  local pose
  local plan
  local action
  set_detector true
  trap 'stop_detector_silent' EXIT INT TERM HUP
  output="$(measure_tag_pose)"
  printf '%s\n' "$output"
  pose="$(awk -F= '/^TAG_POSE=/ {print $2; exit}' <<<"$output")"
  [[ -n "$pose" ]] || die "No se obtuvo TAG_POSE."
  plan="$(compute_plan "$pose")"
  printf '%s\n' "$plan"
  action="$(awk -F= '/^PLAN=/ {print $2; exit}' <<<"$plan" | awk '{print $1}')"
  stop_detector_silent
  trap - EXIT INT TERM HUP
  case "$action" in
    FAIL_HEAD)
      die "La medición indica una postura de cabeza distinta de move_head_lower."
      ;;
    FAIL_VERTICAL)
      die "La medición presenta un error vertical no corregible con el chasis."
      ;;
  esac
}

run_visibility_check() {
  local output
  local pose

  set_detector true
  trap 'stop_detector_silent' EXIT INT TERM HUP
  # Para visibilidad solo importan ID, frame, margen y traslación estable. Un
  # AprilTag plano puede alternar de rama angular sin dejar de ser visible.
  output="$(measure_tag_pose "$SAMPLE_COUNT" 1 "$COARSE_POSITION_STD_MAX")"
  printf '%s\n' "$output"
  pose="$(awk -F= '/^TAG_POSE=/ {print $2; exit}' <<<"$output")"
  [[ -n "$pose" ]] || die "El tag 113 no produjo una pose estable."
  stop_detector_silent
  trap - EXIT INT TERM HUP
  info "APRILTAG_VISIBLE_OK=tag:${TAG_ID},frame:${CAMERA_FRAME}"
}

run_held_target_measurement() {
  local output
  local pose

  cycle_args --verify-grasp
  set_detector true
  trap 'stop_detector_silent' EXIT INT TERM HUP
  output="$(measure_tag_pose 20)"
  printf '%s\n' "$output"
  pose="$(awk -F= '/^TAG_POSE=/ {print $2; exit}' <<<"$output")"
  [[ -n "$pose" ]] || die "No se obtuvo la candidata AprilTag con carga."
  info "MESA2_DROP_TARGET_HELD_CANDIDATE"
  info "POSITION_QUATERNION_XYZW=$pose"
  info "TAG_ID=$TAG_ID"
  info "TAG_SIZE_M=$TAG_SIZE"
  info "FRAME=$CAMERA_FRAME"
  stop_detector_silent
  trap - EXIT INT TERM HUP
}

compute_coarse_plan() {
  local pose="$1"
  python3 - "$pose" "$HELD_TARGET_X" "$HELD_TARGET_Y" "$HELD_TARGET_Z" \
    "$GROUND_Y_PER_Z" "$COARSE_CAPTURE_DZ" "$COARSE_CAPTURE_HYSTERESIS" <<'PY'
import math
import sys

current = tuple(map(float, sys.argv[1].split()))
tx, ty, tz, ground_y_per_z, capture_dz, capture_hysteresis = map(float, sys.argv[2:])
if len(current) != 7:
    raise SystemExit("TAG_POSE debe contener siete valores")
cx, cy, cz = current[:3]
dx, dy, dz = cx - tx, cy - ty, cz - tz
vertical_residual = dy + ground_y_per_z * dz
print(
    f"COARSE_TAG_ERROR=x_mm:{dx*1000:.2f},y_mm:{dy*1000:.2f},"
    f"z_mm:{dz*1000:.2f},vertical_residual_mm:{vertical_residual*1000:.2f}"
)
if abs(dx) > 0.45:
    print("COARSE_PLAN=FAIL_LATERAL 0")
elif abs(vertical_residual) > 0.080:
    print("COARSE_PLAN=FAIL_VERTICAL 0")
elif dz < -0.05:
    print("COARSE_PLAN=FAIL_TOO_CLOSE 0")
elif dz <= capture_dz + capture_hysteresis:
    print("COARSE_PLAN=READY 0")
else:
    # Conserva capture_dz para que la alineación fina corrija el lateral y la
    # pose final. advance-held-distance admite como máximo 0,65 m por tramo.
    advance = max(0.10, min(0.65, dz - capture_dz))
    print(f"COARSE_PLAN=ADVANCE {advance:.6f}")
PY
}

run_coarse_alignment() {
  local iteration output pose plan_output plan advance total="0.0"

  confirm_alignment
  carry_args --check
  cycle_args --verify-grasp
  set_detector true
  trap 'stop_detector_silent' EXIT INT TERM HUP

  for ((iteration=1; iteration<=COARSE_MAX_ITERATIONS; iteration++)); do
    info "[APRILTAG GRUESO] Medición ${iteration}/${COARSE_MAX_ITERATIONS}..."
    output="$(measure_tag_pose "$SAMPLE_COUNT" 1 "$COARSE_POSITION_STD_MAX")"
    printf '%s\n' "$output"
    pose="$(awk -F= '/^TAG_POSE=/ {print $2; exit}' <<<"$output")"
    [[ -n "$pose" ]] || die "No se obtuvo TAG_POSE durante la aproximación gruesa."
    plan_output="$(compute_coarse_plan "$pose")"
    printf '%s\n' "$plan_output"
    read -r plan advance <<<"$(awk -F= '/^COARSE_PLAN=/ {print $2; exit}' <<<"$plan_output")"

    case "$plan" in
      READY)
        stop_detector_silent
        trap - EXIT INT TERM HUP
        cycle_args --verify-grasp
        info "MESA2_APRILTAG_COARSE_OK=iterations:${iteration},translation:${total}m"
        return 0
        ;;
      ADVANCE)
        total="$(python3 - "$total" "$advance" "$COARSE_MAX_TOTAL" <<'PY'
import sys
total, advance, maximum = map(float, sys.argv[1:])
total += advance
if total > maximum + 1e-6:
    raise SystemExit(f"La aproximación gruesa superaría {maximum:.2f} m")
print(f"{total:.6f}")
PY
)"
        carry_args --advance-held-distance "$advance" --yes
        ;;
      FAIL_LATERAL)
        die "El tag está demasiado desplazado lateralmente para una aproximación recta."
        ;;
      FAIL_VERTICAL)
        die "La geometría vertical del tag no corresponde a la postura calibrada."
        ;;
      FAIL_TOO_CLOSE)
        die "El robot ya está más cerca de la mesa que la referencia de depósito."
        ;;
      *)
        die "Plan AprilTag grueso desconocido: $plan"
        ;;
    esac
    sleep "$ALIGNMENT_SETTLE_SECONDS"
  done
  die "La aproximación gruesa no entró en el rango fino tras ${COARSE_MAX_ITERATIONS} correcciones."
}

run_alignment() {
  local output
  local pose
  local plan_output
  local plan
  local value1
  local value2
  local iteration
  local translation_total="0.0"
  local previous_yaw=""
  local current_yaw
  local last_action=""
  local ambiguous_orientation_samples=0
  local orientation_fallback=0

  confirm_alignment
  # Valida una vez odometría, monitor de velocidad, paros y cargador. Las
  # primitivas posteriores repiten las comprobaciones críticas en cada paso.
  if ((FLUID_MODE == 1)) && [[ "${CRUZR_DRIVE_PREFLIGHT_DONE:-0}" == "1" ]]; then
    info "FLUID_MODE: canal de movimiento ya validado durante la recogida."
  else
    carry_args --check
  fi
  if [[ "$MODE" == "align-held" ]]; then
    cycle_args --verify-grasp
  fi

  set_detector true
  trap 'stop_detector_silent' EXIT INT TERM HUP

  for ((iteration=1; iteration<=ALIGNMENT_MAX_ITERATIONS; iteration++)); do
    while :; do
      info "[APRILTAG] Medición ${iteration}/${ALIGNMENT_MAX_ITERATIONS}..."
      output="$(measure_tag_pose "$SAMPLE_COUNT" 1)"
      printf '%s\n' "$output"
      pose="$(awk -F= '/^TAG_POSE=/ {print $2; exit}' <<<"$output")"
      [[ -n "$pose" ]] || die "No se obtuvo TAG_POSE. La base queda detenida."
      if [[ "$orientation_fallback" == "0" ]] && \
         grep -q '^TAG_ORIENTATION_AMBIGUOUS=' <<<"$output"; then
        orientation_fallback=1
        warn "El propio lote contiene las dos ramas PnP del tag: se usarán posición y residual vertical; no se enviarán giros derivados del cuaternión."
      fi
      plan_output="$(compute_plan "$pose" "$orientation_fallback")"
      printf '%s\n' "$plan_output"
      read -r plan value1 value2 <<<"$(awk -F= '/^PLAN=/ {print $2; exit}' <<<"$plan_output")"
      [[ -n "$plan" ]] || die "No se obtuvo un plan de corrección."

      if [[ "$plan" != "FAIL_HEAD" || "$orientation_fallback" == "1" ]]; then
        break
      fi

      ambiguous_orientation_samples=$((ambiguous_orientation_samples + 1))
      if ((ambiguous_orientation_samples < MAX_AMBIGUOUS_ORIENTATION_SAMPLES)); then
        warn "Solución angular AprilTag ambigua descartada (${ambiguous_orientation_samples}/${MAX_AMBIGUOUS_ORIENTATION_SAMPLES}); adquiriendo una muestra nueva."
        sleep "$ALIGNMENT_SETTLE_SECONDS"
        continue
      fi

      orientation_fallback=1
      warn "Tres soluciones angulares alternativas consecutivas: se conservan posición y residual vertical; no se enviarán giros derivados del tag planar."
      plan_output="$(compute_plan "$pose" "$orientation_fallback")"
      printf '%s\n' "$plan_output"
      read -r plan value1 value2 <<<"$(awk -F= '/^PLAN=/ {print $2; exit}' <<<"$plan_output")"
      [[ -n "$plan" && "$plan" != "FAIL_HEAD" ]] || \
        die "No se pudo resolver la ambigüedad angular AprilTag."
      break
    done

    current_yaw="$(sed -n 's/.*base_yaw_deg:\([-+0-9.]*\).*/\1/p' <<<"$plan_output")"
    if [[ "$last_action" == "ROTATE" && -n "$previous_yaw" && -n "$current_yaw" ]]; then
      python3 - "$previous_yaw" "$current_yaw" <<'PY'
import sys
before, after = map(abs, map(float, sys.argv[1:]))
if after > before + 0.7:
    raise SystemExit(
        f"El error angular aumentó de {before:.2f} a {after:.2f} grados; se aborta sin invertir a ciegas"
    )
PY
    fi

    case "$plan" in
      READY)
        if [[ "$MODE" == "align-held" && "$FLUID_MODE" == "0" ]]; then
          cycle_args --verify-grasp
        elif [[ "$MODE" == "align-held" ]]; then
          info "FLUID_MODE: deposit-held verificará inmediatamente el agarre; se omite la lectura duplicada."
        fi
        stop_detector_silent
        trap - EXIT INT TERM HUP
        info "MESA2_APRILTAG_ALIGNMENT_OK=tag:${TAG_ID},iterations:${iteration}"
        return 0
        ;;
      FAIL_HEAD)
        die "La postura observada no es compatible con move_head_lower."
        ;;
      FAIL_VERTICAL)
        die "El error vertical del tag supera ${MAX_VERTICAL_ERROR} m; no se corregirá con el chasis."
        ;;
      ROTATE)
        previous_yaw="$current_yaw"
        carry_args --rotate-relative "$value1" --yes
        ;;
      BACKOFF)
        translation_total="$(python3 - "$translation_total" "$value1" "$MAX_TRANSLATION_TOTAL" <<'PY'
import sys
total, increment, maximum = map(float, sys.argv[1:])
total += increment
if total > maximum:
    raise SystemExit(f"La alineación superaría {maximum:.2f} m acumulados")
print(f"{total:.6f}")
PY
)"
        carry_args --backward-distance "$value1" --yes
        ;;
      MOVE)
        translation_total="$(python3 - "$translation_total" "$value1" "$value2" \
          "$MAX_TRANSLATION_TOTAL" <<'PY'
import math
import sys
total, forward, lateral, maximum = map(float, sys.argv[1:])
total += math.hypot(forward, lateral)
if total > maximum:
    raise SystemExit(f"La alineación superaría {maximum:.2f} m acumulados")
print(f"{total:.6f}")
PY
)"
        carry_args --move-relative "$value1 $value2" --yes
        ;;
      *)
        die "Plan AprilTag desconocido: $plan"
        ;;
    esac
    last_action="$plan"
    sleep "$ALIGNMENT_SETTLE_SECONDS"
  done

  die "No se alcanzó MESA2_DROP_TARGET tras ${ALIGNMENT_MAX_ITERATIONS} correcciones."
}

main() {
  require_local_tools
  exec 9>"/tmp/cruzr_apriltag_mesa2_align.lock"
  flock -n 9 || die "Ya hay otra alineación AprilTag en ejecución."
  select_connection

  case "$MODE" in
    check)
      detector_preflight
      info "TARGET_POSITION_M=$TARGET_X $TARGET_Y $TARGET_Z"
      info "TARGET_QUATERNION_XYZW=$TARGET_QX $TARGET_QY $TARGET_QZ $TARGET_QW"
      info "HELD_TARGET_POSITION_M=$HELD_TARGET_X $HELD_TARGET_Y $HELD_TARGET_Z"
      info "HELD_TARGET_QUATERNION_XYZW=$HELD_TARGET_QX $HELD_TARGET_QY $HELD_TARGET_QZ $HELD_TARGET_QW"
      info "CHECK_OK: detector y referencia disponibles; no se movió el robot."
      ;;
    check-visible)
      detector_preflight
      run_visibility_check
      ;;
    measure|measure-held)
      detector_preflight
      run_measurement
      ;;
    measure-held-target)
      detector_preflight
      run_held_target_measurement
      ;;
    align-empty|align-held)
      require_wireless_run
      if ((FLUID_MODE == 1)) && [[ "${CRUZR_TRANSFER_PREFLIGHT_DONE:-0}" == "1" ]]; then
        info "FLUID_MODE: detector AprilTag ya validado en el preflight general."
      else
        detector_preflight
      fi
      run_alignment
      ;;
    coarse-held)
      require_wireless_run
      detector_preflight
      run_coarse_alignment
      ;;
    *)
      die "Modo interno desconocido: $MODE"
      ;;
  esac
}

main
