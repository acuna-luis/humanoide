#!/usr/bin/env bash

set -Eeuo pipefail

vision_ip="${CRUZR_VISION_IP:-192.168.11.3}"
pico_ip="${PICO_IP:-}"
pico_serial="${PICO_SERIAL:-PA94Y0MGKB070822G}"
pico_adb_target="${PICO_ADB_TARGET:-}"
pico_port="${PICO_CAMERA_PORT:-12345}"
camera="${CRUZR_PICO_CAMERA:-main}"
camera_topic="${CRUZR_PICO_CAMERA_TOPIC:-}"
camera_width="${PICO_CAMERA_WIDTH:-640}"
camera_height="${PICO_CAMERA_HEIGHT:-400}"
camera_fps="${PICO_CAMERA_FPS:-12}"
camera_wait_seconds="${PICO_CAMERA_WAIT_SECONDS:-60}"
robot_user="${CRUZR_ROBOT_USER:-walker}"
ros_container="${CRUZR_VISION_ROS_CONTAINER:-walker-ros.ros2-1}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
relay="$script_dir/pico_camera_relay.py"
askpass="$script_dir/../cruzr_blue_workbin_cycle.sh"
mode="--check"

stream_started=0
cleanup_done=0
heartbeat_pid=""
heartbeat_log=""
local_ready_file=""
ready_file="${PICO_CAMERA_READY_FILE:-}"
stream_url=""
heartbeat_topic=""
source_url=""

progress() {
  printf '[%(%H:%M:%S)T] CAMERA: %s\n' -1 "$*"
}

die() {
  printf '[%(%H:%M:%S)T] CAMERA ERROR: %s\n' -1 "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Uso:
  ./scripts/teleoperation/cruzr_pico_camera.sh --check [opciones]
  ./scripts/teleoperation/cruzr_pico_camera.sh --run [opciones]
  ./scripts/teleoperation/cruzr_pico_camera.sh --stop [opciones]

Opciones:
  --camera NOMBRE     main (predeterminada), stereo-right, waist o chassis.
  --topic TOPIC       Fuente ROS explícita; prevalece sobre --camera.
  --pico-ip IP        IP del PICO. Si se omite, se descubre wlan0 por ADB.
  --port PUERTO       Listener H.264 de XRoboToolkit (predeterminado 12345).
  --wait SEGUNDOS     Espera 1..600 s a «Request PC camera data».

--run inicia únicamente vídeo: abre el stream SRS de la cámara elegida,
mantiene su heartbeat propio y reenvía H.264 al visor. No arma ni mueve el
robot. Ctrl+C cierra el relay, el heartbeat y el stream que abrió.

Fuentes configurables equivalentes:
  CRUZR_PICO_CAMERA=main|stereo-right|waist|chassis
  CRUZR_PICO_CAMERA_TOPIC=/sensor/camera/.../raw
EOF
}

while (($#)); do
  case "$1" in
    --check|--run|--stop)
      mode="$1"
      shift
      ;;
    --camera)
      (($# >= 2)) || die "Falta el valor de --camera."
      camera="$2"
      shift 2
      ;;
    --topic)
      (($# >= 2)) || die "Falta el valor de --topic."
      camera_topic="$2"
      shift 2
      ;;
    --pico-ip)
      (($# >= 2)) || die "Falta el valor de --pico-ip."
      pico_ip="$2"
      shift 2
      ;;
    --port)
      (($# >= 2)) || die "Falta el valor de --port."
      pico_port="$2"
      shift 2
      ;;
    --wait)
      (($# >= 2)) || die "Falta el valor de --wait."
      camera_wait_seconds="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      die "Opción desconocida: $1"
      ;;
  esac
done

discover_pico_ip() {
  local candidate reported_serial
  command -v adb >/dev/null || die "Falta adb para descubrir la IP del PICO."
  if [[ -z "$pico_adb_target" ]]; then
    while read -r candidate state _; do
      [[ "$state" == "device" ]] || continue
      reported_serial="$(
        timeout 3s adb -s "$candidate" shell getprop ro.serialno 2>/dev/null |
          tr -d '\r'
      )"
      if [[ "$reported_serial" == "$pico_serial" ]]; then
        pico_adb_target="$candidate"
        break
      fi
    done < <(adb devices -l | tail -n +2)
  fi
  [[ -n "$pico_adb_target" ]] ||
    die "No se encontró por ADB el PICO $pico_serial para descubrir su IP."

  pico_ip="$(
    timeout 4s adb -s "$pico_adb_target" shell \
      'ip -4 -o addr show wlan0 2>/dev/null' |
      awk '{split($4,address,"/"); print address[1]; exit}' |
      tr -d '\r'
  )"
  if [[ -z "$pico_ip" ]]; then
    pico_ip="$(
      timeout 4s adb -s "$pico_adb_target" shell \
        'ip -4 -o addr show usb0 2>/dev/null' |
        awk '{split($4,address,"/"); print address[1]; exit}' |
        tr -d '\r'
    )"
  fi
  [[ -n "$pico_ip" ]] || die "ADB no devolvió una IP wlan0/usb0 del PICO."
  printf 'PICO_CAMERA_IP_DISCOVERED=%s (adb=%s)\n' "$pico_ip" "$pico_adb_target"
}

[[ -n "$pico_ip" ]] || discover_pico_ip

if [[ -z "$camera_topic" ]]; then
  case "$camera" in
    main)
      camera_topic="/sensor/camera/stereo_left/image/raw"
      ;;
    stereo-right)
      camera_topic="/sensor/camera/stereo_right/image/raw"
      ;;
    waist)
      camera_topic="/sensor/camera/waist_front_rgbd/color/raw"
      ;;
    chassis)
      camera_topic="/sensor/camera/chassis_front_rgbd/color/raw"
      ;;
    *)
      die "Cámara desconocida '$camera'; use main, stereo-right, waist o chassis."
      ;;
  esac
fi

[[ "$camera_topic" =~ ^/[A-Za-z0-9_/]+$ ]] ||
  die "Topic de cámara inválido: $camera_topic"
[[ "$vision_ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] ||
  die "CRUZR_VISION_IP no es una IPv4 válida."
[[ "$pico_ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] ||
  die "PICO_IP no es una IPv4 válida."
[[ "$pico_port" =~ ^[0-9]+$ ]] && ((pico_port >= 1 && pico_port <= 65535)) ||
  die "PICO_CAMERA_PORT debe estar entre 1 y 65535."
[[ "$camera_wait_seconds" =~ ^[0-9]+$ ]] &&
  ((camera_wait_seconds >= 1 && camera_wait_seconds <= 600)) ||
  die "PICO_CAMERA_WAIT_SECONDS debe estar entre 1 y 600."
[[ "$camera_width" =~ ^[0-9]+$ ]] && ((camera_width >= 320 && camera_width <= 1920)) ||
  die "PICO_CAMERA_WIDTH debe estar entre 320 y 1920."
[[ "$camera_height" =~ ^[0-9]+$ ]] && ((camera_height >= 240 && camera_height <= 1080)) ||
  die "PICO_CAMERA_HEIGHT debe estar entre 240 y 1080."
[[ "$camera_fps" =~ ^[0-9]+$ ]] && ((camera_fps >= 5 && camera_fps <= 30)) ||
  die "PICO_CAMERA_FPS debe estar entre 5 y 30."

ssh_base=(
  ssh
  -o ConnectTimeout=5
  -o ConnectionAttempts=1
  -o PreferredAuthentications=password
  -o PubkeyAuthentication=no
  -o NumberOfPasswordPrompts=1
  -o StrictHostKeyChecking=accept-new
  -o ServerAliveInterval=3
  -o ServerAliveCountMax=2
  "$robot_user@$vision_ip"
)

run_vision_ssh() {
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$askpass" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
    setsid -w timeout 20s "${ssh_base[@]}" "$@"
}

check_tcp() {
  local host="$1"
  shift
  CHECK_HOST="$host" CHECK_PORTS="$*" python3 - <<'PY'
import os
import socket

host = os.environ["CHECK_HOST"]
for raw in os.environ["CHECK_PORTS"].split():
    port = int(raw)
    with socket.create_connection((host, port), timeout=3):
        pass
    print(f"TCP_OK={host}:{port}")
PY
}

check_camera_source() {
  command -v python3 >/dev/null || die "Falta python3."
  command -v ssh >/dev/null || die "Falta ssh."
  command -v setsid >/dev/null || die "Falta setsid."
  command -v timeout >/dev/null || die "Falta timeout."
  command -v curl >/dev/null || die "Falta curl."
  [[ -x "$relay" ]] || die "No se puede ejecutar $relay"
  [[ -x "$askpass" ]] || die "No existe el proveedor SSH local $askpass"

  progress "comprobando Vision/SRS y fuente $camera_topic"
  check_tcp "$vision_ip" 22 1935 1985 8080
  local topic_type
  topic_type="$({
    run_vision_ssh bash -s -- "$ros_container" "$camera_topic" <<'REMOTE'
set -Eeuo pipefail
container="$1"
topic="$2"
docker exec -i "$container" bash -s -- "$topic" <<'INNER'
set -Eeo pipefail
topic="$1"
source /opt/ros/humble/setup.bash
export ROS2CLI_DISABLE_DAEMON=1
timeout 8 ros2 topic list -t | awk -v topic="$topic" '
  $1 == topic {
    type=$2
    gsub(/^\[/, "", type)
    gsub(/\]$/, "", type)
    print type
    found=1
  }
  END {exit !found}
'
INNER
REMOTE
  } 2>&1)" || {
    printf '%s\n' "$topic_type" >&2
    die "No se pudo demostrar el topic de cámara en Vision."
  }
  topic_type="$(tail -n1 <<<"$topic_type")"
  [[ "$topic_type" == shm_msgs/msg/Image* || "$topic_type" == sensor_msgs/msg/Image ]] ||
    die "Tipo de cámara inesperado para $camera_topic: $topic_type"
  printf 'CAMERA_SOURCE_OK=%s,%s\n' "$camera_topic" "$topic_type"
  printf 'CAMERA_PROFILE=%s,%sx%s@%sfps\n' "$camera" "$camera_width" "$camera_height" "$camera_fps"

  local pico_route
  pico_route="$(ip -4 route get "$pico_ip" 2>/dev/null | head -n1)" ||
    die "No existe ruta IPv4 hacia el PICO $pico_ip."
  printf 'PICO_CAMERA_ROUTE=%s\n' "$pico_route"
  # No haga un connect de prueba: MediaDecoder acepta una sola conexión y un
  # probe vacío consumiría la sesión que debe usar el relay H.264 real.
  printf 'PICO_CAMERA_LISTENER=not_probed,%s:%s (el relay hará la única conexión)\n' \
    "$pico_ip" "$pico_port"
}

start_camera_stream() {
  local response code
  progress "abriendo stream SRS; esto no inicia teleoperación"
  response="$({
    run_vision_ssh bash -s -- \
      "$ros_container" "$vision_ip" "$camera_topic" \
      "$camera_width" "$camera_height" "$camera_fps" <<'REMOTE'
set -Eeuo pipefail
container="$1"
vision_ip="$2"
topic="$3"
width="$4"
height="$5"
fps="$6"
docker exec -i "$container" bash -s -- \
  "$vision_ip" "$topic" "$width" "$height" "$fps" <<'INNER'
set -Eeo pipefail
vision_ip="$1"
topic="$2"
width="$3"
height="$4"
fps="$5"
source /opt/ros/humble/setup.bash
export ROS2CLI_DISABLE_DAEMON=1
timeout 12 ros2 service call /streaming/start rosa_msgs/srv/VideoStream \
  "{srs_url: '$vision_ip:1935', topic_name: '$topic', topic_type: 'sensor_msgs::msg::Image', encode_width: $width, encode_height: $height, capture_fps: $fps, encode_fps: $fps, gop_size: $((fps * 2)), codec_name: 'h264_nvmpi'}"
INNER
REMOTE
  } 2>&1)" || {
    printf '%s\n' "$response" >&2
    die "Vision rechazó el inicio del stream de cámara."
  }
  printf '%s\n' "$response"
  code="$(sed -nE 's/.*code=([-0-9]+).*/\1/p' <<<"$response" | tail -n1)"
  stream_url="$(sed -nE "s/.*stream_url='([^']+)'.*/\1/p" <<<"$response" | tail -n1)"
  heartbeat_topic="$(sed -nE "s/.*heartbeat_topic='([^']+)'.*/\1/p" <<<"$response" | tail -n1)"
  [[ "$code" == "0" && "$stream_url" == webrtc://* && "$heartbeat_topic" == /* ]] ||
    die "Respuesta VideoStream incompleta (code=${code:-?})."
  stream_started=1
  source_url="$(sed -E "s#^webrtc://[^/]+#http://$vision_ip:8080#" <<<"$stream_url").flv"
  printf 'ROBOT_CAMERA_STREAM=%s\n' "$stream_url"
  printf 'ROBOT_CAMERA_HTTP_FLV=%s\n' "$source_url"
}

start_camera_heartbeat() {
  heartbeat_log="$(mktemp --tmpdir humanoide-pico-camera-heartbeat.XXXXXX.log)"
  progress "manteniendo heartbeat exclusivo de vídeo en $heartbeat_topic"
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$askpass" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
    setsid "${ssh_base[@]}" bash -s -- \
      "$ros_container" "$heartbeat_topic" \
      >"$heartbeat_log" 2>&1 <<'REMOTE' &
set -Eeuo pipefail
container="$1"
heartbeat="$2"
exec docker exec -i "$container" bash -s -- "$heartbeat" <<'INNER'
set -Eeo pipefail
heartbeat="$1"
source /opt/ros/humble/setup.bash
export ROS2CLI_DISABLE_DAEMON=1
exec timeout 900 ros2 topic pub --rate 2 "$heartbeat" std_msgs/msg/Empty '{}'
INNER
REMOTE
  heartbeat_pid=$!
  sleep 1
  if ! kill -0 "$heartbeat_pid" 2>/dev/null; then
    wait "$heartbeat_pid" || true
    [[ -f "$heartbeat_log" ]] && tail -40 "$heartbeat_log" >&2
    die "No se pudo iniciar el heartbeat de vídeo."
  fi
  printf 'ROBOT_CAMERA_HEARTBEAT=live,%s\n' "$heartbeat_topic"
}

stop_camera_heartbeat() {
  [[ -n "$heartbeat_topic" ]] || return 0
  local output
  output="$({
    run_vision_ssh bash -s -- "$ros_container" "$heartbeat_topic" <<'REMOTE'
set -Eeuo pipefail
container="$1"
heartbeat="$2"
docker exec -i "$container" bash -s -- "$heartbeat" <<'INNER'
set -Eeo pipefail
heartbeat="$1"
mapfile -t pids < <(
  pgrep -f "^/usr/bin/python3 /opt/ros/humble/bin/ros2 topic pub --rate 2 ${heartbeat} " || true
  pgrep -f "^timeout 900 ros2 topic pub --rate 2 ${heartbeat} " || true
)
if ((${#pids[@]})); then
  kill -TERM "${pids[@]}" 2>/dev/null || true
  sleep 0.2
  for pid in "${pids[@]}"; do
    kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null || true
  done
fi
printf 'VIDEO_HEARTBEAT_PROCESSES_STOPPED=%s\n' "${#pids[@]}"
INNER
REMOTE
  } 2>&1)" || {
    printf '%s\n' "$output" >&2
    return 1
  }
  printf '%s\n' "$output"
}

stop_camera_stream() {
  local output
  output="$({
    run_vision_ssh bash -s -- "$ros_container" "$camera_topic" <<'REMOTE'
set -Eeuo pipefail
container="$1"
topic="$2"
docker exec -i "$container" bash -s -- "$topic" <<'INNER'
set -Eeo pipefail
topic="$1"
source /opt/ros/humble/setup.bash
export ROS2CLI_DISABLE_DAEMON=1
timeout 12 ros2 service call /streaming/stop rosa_msgs/srv/VideoStream \
  "{topic_name: '$topic'}"
INNER
REMOTE
  } 2>&1)" || {
    printf '%s\n' "$output" >&2
    return 1
  }
  printf '%s\n' "$output"
  printf 'ROBOT_CAMERA_STREAM_STOPPED=%s\n' "$camera_topic"
}

cleanup() {
  local status="${1:-0}"
  ((cleanup_done == 0)) || return "$status"
  cleanup_done=1
  trap - EXIT INT TERM
  if [[ -n "$heartbeat_pid" ]] && kill -0 "$heartbeat_pid" 2>/dev/null; then
    kill -TERM "$heartbeat_pid" 2>/dev/null || true
    wait "$heartbeat_pid" 2>/dev/null || true
  fi
  stop_camera_heartbeat || true
  if ((stream_started == 1)); then
    stop_camera_stream || true
  fi
  if [[ -n "$heartbeat_log" && -f "$heartbeat_log" ]]; then
    rm -f -- "$heartbeat_log"
  fi
  if [[ -n "$local_ready_file" && -f "$local_ready_file" ]]; then
    rm -f -- "$local_ready_file"
  fi
  return "$status"
}

case "$mode" in
  --check)
    check_camera_source
    printf 'PICO_CAMERA_CHECK_OK=1; no se abrió stream ni se movió el robot.\n'
    ;;
  --stop)
    check_camera_source
    heartbeat_topic="${camera_topic%/raw}/heartbeat"
    stop_camera_heartbeat || true
    stop_camera_stream
    ;;
  --run)
    check_camera_source
    if [[ -z "$ready_file" ]]; then
      local_ready_file="$(mktemp --tmpdir humanoide-pico-camera-ready.XXXXXX)"
      ready_file="$local_ready_file"
      rm -f -- "$ready_file"
    fi
    trap 'status=$?; cleanup "$status"; exit "$status"' EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    cat <<EOF

VISTA DE CÁMARA EN XRoboToolkit

En el PICO abra el panel Camera y active «Request PC camera data». Mantenga
Head + Controllers y Send data/Working activos. El visor abrirá su listener
$pico_ip:$pico_port; este proceso esperará ${camera_wait_seconds}s.

Fuente seleccionada: $camera_topic ($camera, ${camera_width}x${camera_height}@${camera_fps}).
Esto sólo transmite vídeo y no envía START ni órdenes al robot.

EOF
    start_camera_stream
    start_camera_heartbeat
    "$relay" \
      --source "$source_url" \
      --pico-ip "$pico_ip" \
      --port "$pico_port" \
      --wait-seconds "$camera_wait_seconds" \
      --ready-file "$ready_file"
    ;;
esac
