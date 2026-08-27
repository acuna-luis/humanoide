#!/usr/bin/env bash

set -Eeuo pipefail

motion_ip="${CRUZR_MOTION_IP:-192.168.11.2}"
vision_ip="${CRUZR_VISION_IP:-192.168.11.3}"
pico_ip="${PICO_IP:-}"
pc_pico_ip="${PICO_PC_IP:-}"
pico_serial="${PICO_SERIAL:-PA94Y0MGKB070822G}"
pico_adb_target="${PICO_ADB_TARGET:-}"
robot_iface="${CRUZR_IFACE:-}"
robot_pc_ip="${CRUZR_PC_IP:-}"
robot_wifi_ssid="${CRUZR_ROBOT_WIFI_SSID:-Cruzr S2-0669}"
robot_link_kind=""
robot_connection_name=""
backend_unit="ubt-controller.service"
ui_unit="ubt-remote-control.service"
backend_log="/opt/ubt/ubt_controller/logs/ubt_controller.log"
required_arm="clamp"
all_controls_seconds="${PICO_ALL_CONTROLS_SECONDS:-120}"
official_teleop_seconds="${PICO_OFFICIAL_TELEOP_SECONDS:-300}"
allow_bimanual="${PICO_ALLOW_BIMANUAL:-1}"
expected_backend_version="4.7.0"
expected_ui_version="4.1.0"
expected_backend_sha256="e88b83b7936a13f5fb71b99416e0d6bcc844b9361524ef709f87fd04ed449d16"
expected_pico_control_sha256="46323392cacf3935c20ccbd535fb7609f71169fa48081e423a2f3b78db97b425"
backend_executable="/opt/ubt/ubt_controller/ubt_controller"
pico_control_executable="/usr/local/bin/pico_control"
command_timeout_seconds=5
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
motion_askpass="$script_dir/../cruzr_blue_workbin_cycle.sh"
camera_script="$script_dir/cruzr_pico_camera.sh"
teleop_camera="${PICO_TELEOP_CAMERA:-main}"
camera_pid=""
camera_ready_file=""
official_client_pid=""
official_cleanup_done=0
robot_user="${CRUZR_ROBOT_USER:-walker}"
motion_ros_container="walker-ros.ros2-1"
motion_app_container="walker-motion.manipulation_robot_app-1"
expected_teleop_task="teleoperation/cruzr_clamp_pico_teleoperation"
arms_only_config_path="/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_teleoperation/cruzr_clamp_pico_tele.yaml"
arms_only_config_sha256="4e8d79a40e8b1f1fa5915de27ef60676fce4c9b5cec41cacfc0a1d9a7d117a44"
minimum_battery_soc=30

if [[ "${CRUZR_TELEOP_DEBUG:-0}" == "1" ]]; then
  PS4='+ ${BASH_SOURCE##*/}:${LINENO}: '
  set -x
fi

progress() {
  printf '[%(%H:%M:%S)T] %s\n' -1 "$*"
}

discover_robot_link_route() {
  local route_line detected_iface detected_src connection_name active_type active_ssid
  route_line="$(ip -4 route get "$motion_ip" 2>/dev/null | head -n1)" ||
    die "No existe una ruta IPv4 hacia Motion $motion_ip."
  detected_iface="$(
    awk '{for (i=1; i<=NF; i++) if ($i=="dev") {print $(i+1); exit}}' \
      <<<"$route_line"
  )"
  detected_src="$(
    awk '{for (i=1; i<=NF; i++) if ($i=="src") {print $(i+1); exit}}' \
      <<<"$route_line"
  )"
  [[ -n "$detected_iface" && -n "$detected_src" ]] ||
    die "No se pudo resolver interfaz/origen para Motion: $route_line"

  if [[ -n "$robot_iface" && "$robot_iface" != "$detected_iface" ]]; then
    die "Motion usa $detected_iface, no la interfaz Cruzr esperada $robot_iface."
  fi
  if [[ -n "$robot_pc_ip" && "$robot_pc_ip" != "$detected_src" ]]; then
    die "Motion usa origen $detected_src, no la IP Cruzr esperada $robot_pc_ip."
  fi
  robot_iface="$detected_iface"
  robot_pc_ip="$detected_src"

  active_type="$(nmcli -g GENERAL.TYPE device show "$robot_iface" 2>/dev/null)" ||
    die "NetworkManager no reconoce la interfaz robot $robot_iface."
  connection_name="$(
    nmcli -g GENERAL.CONNECTION device show "$robot_iface" 2>/dev/null
  )" || die "No se pudo leer la conexión activa de $robot_iface."
  robot_connection_name="$connection_name"
  case "$active_type" in
    wifi)
      active_ssid="$(
        nmcli -g 802-11-wireless.ssid connection show "$connection_name" 2>/dev/null
      )" || die "No se pudo leer el SSID de $connection_name."
      [[ "$active_ssid" == "$robot_wifi_ssid" ]] ||
        die "La ruta del robot usa SSID '$active_ssid', no '$robot_wifi_ssid'."
      robot_link_kind="wifi"
      ;;
    ethernet)
      robot_link_kind="ethernet"
      ;;
    *)
      die "La ruta del robot usa $robot_iface con tipo no admitido '$active_type'."
      ;;
  esac
}

robot_link_runtime_ok() {
  [[ -n "$robot_iface" && -n "$robot_pc_ip" ]] || return 1
  [[ -d "/sys/class/net/$robot_iface" ]] || return 1
  [[ -r "/sys/class/net/$robot_iface/carrier" ]] || return 1
  [[ "$(<"/sys/class/net/$robot_iface/carrier")" == "1" ]] || return 1
  ip -4 -o addr show dev "$robot_iface" 2>/dev/null |
    grep -q " $robot_pc_ip/" || return 1
  ip -4 route get "$motion_ip" 2>/dev/null |
    grep -q "dev $robot_iface" || return 1
}

check_robot_arms_only_loaded() {
  ensure_cmd ssh
  ensure_cmd setsid
  [[ -x "$motion_askpass" ]] ||
    die "No existe el proveedor SSH local requerido: $motion_askpass"
  discover_robot_link_route

  local output
  if ! output="$({
    CRUZR_INTERNAL_ASKPASS=1 \
    SSH_ASKPASS="$motion_askpass" \
    SSH_ASKPASS_REQUIRE=force \
    DISPLAY="${DISPLAY:-:0}" \
    setsid -w timeout 20s ssh \
      -o ConnectTimeout=6 \
      -o ConnectionAttempts=1 \
      -o PreferredAuthentications=password \
      -o PubkeyAuthentication=no \
      -o NumberOfPasswordPrompts=1 \
      -o StrictHostKeyChecking=accept-new \
      "$robot_user@$motion_ip" bash -s -- \
        "$motion_app_container" "$arms_only_config_path" \
        "$arms_only_config_sha256" "$expected_teleop_task" <<'REMOTE'
set -Eeuo pipefail
container="$1"
config_path="$2"
expected_sha="$3"
task_name="$4"

[[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || exit 31
actual_sha="$(docker exec "$container" sha256sum "$config_path" | awk '{print $1}')"
[[ "$actual_sha" == "$expected_sha" ]] || {
  printf 'ARMS_ONLY_CONFIG_SHA_ERROR=%s\n' "$actual_sha"
  exit 32
}

latest="$(find /etc/walker/log/motion -maxdepth 1 -type f -name 'robot_app*.log' -printf '%T@ %p\n' | sort -nr | sed -n '1p' | cut -d' ' -f2-)"
last_start="$(grep -n "BTree task: '$task_name' is start" "$latest" | tail -n1 | cut -d: -f1 || true)"
[[ -n "$last_start" ]] || exit 33
block="$(sed -n "${last_start},$((last_start + 79))p" "$latest")"
waist="$(sed -nE 's/.*Waist tele mode: ([0-9]+).*/\1/p' <<<"$block" | sed -n '1p')"
leg="$(sed -nE 's/.*Leg tele mode: ([0-9]+).*/\1/p' <<<"$block" | sed -n '1p')"
hand="$(sed -nE 's/.*Hand type: ([^ ]+).*/\1/p' <<<"$block" | sed -n '1p')"
[[ "$waist" == "0" && "$leg" == "0" && "$hand" == "clamp" ]] || {
  printf 'ARMS_ONLY_NOT_LOADED=hand:%s,waist:%s,leg:%s\n' \
    "${hand:-unknown}" "${waist:-unknown}" "${leg:-unknown}"
  exit 34
}
printf 'ARMS_ONLY_CONFIG_SHA256=%s\n' "$actual_sha"
printf 'ARMS_ONLY_LOADED=hand:%s,waist:%s,leg:%s\n' "$hand" "$waist" "$leg"
REMOTE
  } 2>&1)"; then
    printf '%s\n' "$output" >&2
    die "Motion todavía no ejecuta el perfil arms-only; salga de TeleopMode, vuelva a entrar y repita sólo --check-arms-only."
  fi
  printf '%s\n' "$output"
}

pico_camera_runtime_ok() {
  [[ "$teleop_camera" == "off" ]] && return 0
  [[ -n "$camera_pid" && -n "$camera_ready_file" ]] || return 1
  kill -0 "$camera_pid" 2>/dev/null || return 1
  [[ -s "$camera_ready_file" ]] || return 1
  local modified now
  modified="$(stat -c %Y "$camera_ready_file" 2>/dev/null)" || return 1
  now="$(date +%s)"
  ((now - modified <= 5)) || return 1
}

assert_runtime_links() {
  local detect_json="$1"
  local phase="$2"
  local vr_status

  if ! robot_link_runtime_ok; then
    stop_all
    die "Se perdió el enlace del robot ($robot_link_kind/$robot_iface) $phase; STOP solicitado."
  fi
  if ! pico_camera_runtime_ok; then
    stop_all
    die "Se perdió el stream de cámara PICO $phase; STOP solicitado."
  fi
  vr_status="$(jq -r '.content.vr_status' <<<"$detect_json")"
  if [[ "$vr_status" != "1" ]]; then
    stop_all
    die "Se perdió HEAD+CONTROLLERS del PICO $phase (vr_status=$vr_status); STOP enviado."
  fi
}

die() {
  printf '[%(%H:%M:%S)T] ERROR: %s\n' -1 "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

usage() {
  cat <<'EOF'
Uso:
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check-arms-only
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check-reload-ready
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check-motion-ready
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --teleoperate
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --open-ui
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --gate-local
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --move-left-arm
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --move-right-arm
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --all-controls
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --run
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --stop

--check    Sólo lectura; valida PC, red, PICO y backend mostrando 7 etapas.
--check-arms-only
           Sólo lectura; demuestra hash y modos cargados de la tarea Motion.
--check-reload-ready
           Sólo lectura; comprueba seguridad Motion sin depender del visor.
--check-motion-ready
           Sólo lectura; añade paros, batería, cargador, efector, tarea PICO,
           acción activa esperada y velocidad articular inmóvil.
--teleoperate
           Teleoperación oficial de brazos, incluido control bimanual. Sólo
           inicia si Motion demuestra que la tarea clamp viva cargó
           waist_mode=0 y leg_mode=0. PICO_ALLOW_BIMANUAL=0 restaura el gate
           estricto de un brazo. Cualquier otro fallo sigue enviando STOP.
--open-ui  Abre la interfaz después del backend. No inicia la publicación.
--gate-local
           Gate interactivo local recomendado. Exige confirmación física,
           arma el backend con arm_type=clamp, emite una campana y
           muestra TOQUE AHORA, abre una ventana diagnóstica de 60 s y envía
           STOP siempre al completar o fallar. Actualmente se bloquea antes
           de START hasta validar el protocolo oficial de enable de 4.7.0.
           Debe ejecutarse directamente en el terminal del PC; no coordinar
           el toque mediante chat o acceso remoto.
--move-left-arm / --move-right-arm
           Bloqueados en 4.7.0 hasta validar Y/enable. Solicitan STOP y salen
           antes de cualquier START.
--all-controls
           Bloqueado por el mismo gate de 4.7.0; no envía START.
--run      Alias compatible de --gate-local.
--stop     Solicita EXIT_REMOTE_CONTROL y cierra la interfaz.

Cuando el protocolo 4.7.0 quede validado, las pruebas exigirán primero la
cámara principal del robot en XRoboToolkit. PICO_TELEOP_CAMERA conserva las
fuentes main, stereo-right, waist, chassis u off.

Este script sólo cambia/ejecuta componentes del PC. Con 4.7.0 conserva el
binario oficial sin alterar heartbeat, enable ni selección de efector.

Diagnóstico detallado opcional:
  CRUZR_TELEOP_DEBUG=1 ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check

PICO_ADB_TARGET puede fijar explícitamente el transporte ADB (serial USB o
IP:puerto). Si se omite, el script identifica el mismo visor por ro.serialno.
Con PICO_TELEOP_CAMERA=off, --check puede continuar sin ADB sólo si demuestra
simultáneamente peer XR 63901, serial esperado en el backend y vr_status=1.
EOF
}

check_robot_teleop_safety() {
  progress "MOVIMIENTO 1/2: revalidando enlace físico PC -> Motion"
  ensure_cmd ssh
  ensure_cmd setsid
  [[ -x "$motion_askpass" ]] ||
    die "No existe el proveedor SSH local requerido: $motion_askpass"

  discover_robot_link_route

  local carrier="unknown"
  if [[ -r "/sys/class/net/$robot_iface/carrier" ]]; then
    carrier="$(<"/sys/class/net/$robot_iface/carrier")"
  fi
  [[ "$carrier" == "1" ]] ||
    die "$robot_iface no tiene enlace del robot (carrier=$carrier)."
  ip -4 -o addr show dev "$robot_iface" | grep -q " $robot_pc_ip/" ||
    die "$robot_iface perdió $robot_pc_ip antes del preflight Motion."
  ip route get "$motion_ip" | grep -q "dev $robot_iface" ||
    die "La ruta a Motion $motion_ip ya no usa $robot_iface; no se enviará START."
  ping -c 1 -W 1 "$motion_ip" >/dev/null ||
    die "Motion $motion_ip dejó de responder antes del preflight físico."
  MOTION_IP="$motion_ip" python3 - <<'PY' ||
import os
import socket

with socket.create_connection((os.environ["MOTION_IP"], 22), timeout=3):
    pass
PY
    die "Motion $motion_ip no acepta SSH TCP 22 por $robot_link_kind/$robot_iface; revise enlace, ruta, arranque y servicio."

  progress "MOVIMIENTO 2/2: comprobando paros, batería, cargador, efector, tarea y velocidad articular"

  local output
  if ! output="$({
    CRUZR_INTERNAL_ASKPASS=1 \
    SSH_ASKPASS="$motion_askpass" \
    SSH_ASKPASS_REQUIRE=force \
    DISPLAY="${DISPLAY:-:0}" \
    setsid -w timeout 35s ssh \
      -o ConnectTimeout=6 \
      -o ConnectionAttempts=1 \
      -o PreferredAuthentications=password \
      -o PubkeyAuthentication=no \
      -o NumberOfPasswordPrompts=1 \
      -o StrictHostKeyChecking=accept-new \
      "$robot_user@$motion_ip" bash -s -- \
        "$motion_ros_container" "$motion_app_container" \
        "$expected_teleop_task" "$minimum_battery_soc" <<'REMOTE'
set -Eeuo pipefail
ros_container="$1"
motion_container="$2"
expected_task="$3"
minimum_soc="$4"

for container in "$ros_container" "$motion_container"; do
  [[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || {
    printf 'CONTAINER_NOT_RUNNING=%s\n' "$container"
    exit 21
  }
done

environment="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$motion_container")"
hw_type="$(awk -F= '$1=="HW_TYPE" {print substr($0,index($0,"=")+1)}' <<<"$environment")"
tele_device="$(awk -F= '$1=="TELE_DEVICE" {print substr($0,index($0,"=")+1)}' <<<"$environment")"
transmit="$(awk -F= '$1=="transmit" {print substr($0,index($0,"=")+1)}' <<<"$environment")"
[[ "$hw_type" == "cruzr_s2_v1" ]] || { printf 'HW_TYPE_ERROR=%s\n' "$hw_type"; exit 22; }
[[ "$tele_device" == "pico" ]] || { printf 'TELE_DEVICE_ERROR=%s\n' "$tele_device"; exit 23; }
[[ "$transmit" == "local" ]] || { printf 'TRANSMIT_ERROR=%s\n' "$transmit"; exit 24; }

latest="$(find /etc/walker/log/motion -maxdepth 1 -type f \
  -name 'robot_app*.log' -printf '%T@ %p\n' | sort -nr | head -n1 | cut -d' ' -f2-)"
[[ -n "$latest" && -f "$latest" ]] || exit 25
last_task_line="$(grep "BTree task: '" "$latest" | tail -n1 || true)"
last_task="$(sed -E "s/.*BTree task: '([^']+)'.*/\1/" <<<"$last_task_line")"
[[ "$last_task" == "$expected_task" ]] || {
  printf 'ACTIVE_TASK_ERROR=%s\n' "${last_task:-unknown}"
  exit 26
}

docker exec -i "$ros_container" bash -s -- "$minimum_soc" <<'INNER'
set -Eeo pipefail
minimum_soc="$1"
source /opt/ros/humble/setup.bash
export ROS2CLI_DISABLE_DAEMON=1

topic_once() {
  timeout 8 ros2 topic echo --once "$1"
}

estop="$(topic_once /emb/estop_key_state)"
servo_estop="$(topic_once /emb/servo_estop_key_state)"
[[ "$(awk '/data:/ {print $2; exit}' <<<"$estop")" == "0" ]] || exit 31
[[ "$(awk '/data:/ {print $2; exit}' <<<"$servo_estop")" == "0" ]] || exit 32

battery="$(topic_once /emb/battery_state)"
mapfile -t socs < <(awk '/batsoc:/ {print $2}' <<<"$battery")
[[ "${#socs[@]}" == "2" ]] || exit 33
for soc in "${socs[@]}"; do
  awk -v soc="$soc" -v minimum="$minimum_soc" \
    'BEGIN {exit !(soc >= minimum)}' || exit 34
done

charge="$(topic_once /emb/chrg_input_status)"
[[ "$(awk '/data:/ {print $2; exit}' <<<"$charge")" == "0" ]] || exit 35

lock="$(topic_once /sys/state/module_lock_info)"
grep -Eq 'locked:[[:space:]]+false' <<<"$lock" || exit 36

action_status="$(timeout 8 ros2 topic echo --once /mc/manipulation/action/_action/status)"
active_count="$(awk '$1 == "status:" && ($2 == 1 || $2 == 2 || $2 == 3) {count++} END {print count+0}' <<<"$action_status")"
[[ "$active_count" == "1" ]] || exit 37

joints="$(topic_once /mc/joint_states)"
awk '
  /^velocity:/ {in_velocity=1; next}
  /^effort:/ {in_velocity=0}
  in_velocity && $1 == "-" {
    value=$2+0
    if (value < 0) value=-value
    if (value > 0.02) moving=1
    count++
  }
  END {exit !(count > 0 && !moving)}
' <<<"$joints" || exit 38

printf 'ESTOPS=0,0\n'
printf 'BATTERY_1=%s\nBATTERY_2=%s\n' "${socs[0]}" "${socs[1]}"
printf 'CHARGER=disconnected\n'
printf 'JOINT_VELOCITY=stationary\n'
printf 'ACTIVE_ACTIONS=%s\n' "$active_count"
INNER

printf 'HW_TYPE=%s\nTELE_DEVICE=%s\nTRANSMIT=%s\n' \
  "$hw_type" "$tele_device" "$transmit"
printf 'ACTIVE_TASK=%s\n' "$last_task"
REMOTE
  } 2>&1)"; then
    printf '%s\n' "$output" >&2
    die "El preflight Motion no permite una prueba física. No se enviará START."
  fi
  printf '%s\n' "$output"
  info "ROBOT_TELEOP_SAFETY_OK=1"
}

grip_state_seen_since() {
  local first_line="$1"
  local hand_label="$2"
  local state="$3"
  awk -v first="$first_line" -v label="$hand_label hand state:" \
    -v needle="\"squeeze\":$state" '
      NR >= first && index($0, label) && index($0, needle) {found=1; exit}
      END {exit !found}
    ' "$backend_log"
}

first_grip_state_line() {
  local first_line="$1"
  local hand_label="$2"
  local state="$3"
  awk -v first="$first_line" -v label="$hand_label hand state:" \
    -v needle="\"squeeze\":$state" '
      NR >= first && index($0, label) && index($0, needle) {print NR; exit}
    ' "$backend_log"
}

both_grips_currently_pressed_since() {
  local first_line="$1"
  awk -v first="$first_line" '
    NR < first {next}
    /Left hand state:/ {
      left = index($0, "\"squeeze\":true") ? 1 : 0
      seen_left = 1
    }
    /Right hand state:/ {
      right = index($0, "\"squeeze\":true") ? 1 : 0
      seen_right = 1
    }
    END {exit !(seen_left && seen_right && left && right)}
  ' "$backend_log"
}

check_controller_inputs_neutral() {
  local first_line="$1"
  local deadline=$((SECONDS + 3))

  until awk -v first="$first_line" '
    NR >= first && /Left hand state:/ {left=1}
    NR >= first && /Right hand state:/ {right=1}
    END {exit !(left && right)}
  ' "$backend_log"; do
    if ((SECONDS >= deadline)); then
      stop_all
      die "No llegaron muestras nuevas de ambos mandos dentro de 3 s; STOP enviado."
    fi
    sleep 0.05
  done

  if ! BACKEND_LOG="$backend_log" FIRST_LINE="$first_line" python3 - <<'PY'
import json
import os

path = os.environ["BACKEND_LOG"]
first_line = int(os.environ["FIRST_LINE"])

latest = {}
with open(path, "r", encoding="utf-8", errors="replace") as handle:
    fresh = [line for number, line in enumerate(handle, 1) if number >= first_line]

for line in reversed(fresh):
    for side in ("Left", "Right"):
        if side in latest or f"{side} hand state:" not in line:
            continue
        try:
            latest[side] = json.loads(line[line.index("{"):])
        except (ValueError, json.JSONDecodeError):
            pass
    if len(latest) == 2:
        break

errors = []
for side in ("Left", "Right"):
    state = latest.get(side)
    if state is None:
        errors.append(f"{side}=sin_muestra")
        continue
    for field in ("trigger", "squeeze", "thumbstick", "a_button", "b_button"):
        if bool(state.get(field, False)):
            errors.append(f"{side}.{field}=true")
    for field in ("trigger_value", "squeeze_value"):
        if abs(float(state.get(field, 0.0))) > 0.1:
            errors.append(f"{side}.{field}={state.get(field)}")
    axes = state.get("thumbstick_value", [0.0, 0.0])
    if not isinstance(axes, list) or len(axes) < 2:
        errors.append(f"{side}.thumbstick_value=invalido")
    elif any(abs(float(value)) > 0.15 for value in axes[:2]):
        errors.append(f"{side}.thumbstick_value={axes[:2]}")

if errors:
    print("CONTROLLER_INPUTS_NOT_NEUTRAL=" + ",".join(errors))
    raise SystemExit(1)
print("CONTROLLER_INPUTS_FRESH=1")
print("CONTROLLER_INPUTS_NEUTRAL=1")
PY
  then
    stop_all
    die "Las muestras nuevas no están neutras; suelte grips, gatillos, botones y joysticks. STOP enviado."
  fi
}

wait_for_left_trigger_release() {
  local first_line="$1"
  local deadline=$((SECONDS + 3))
  until awk -v first="$first_line" '
    NR >= first && /Left hand state:/ && /"trigger_value":0([.]0+)?[,}]/ {
      found=1
      exit
    }
    END {exit !found}
  ' "$backend_log"; do
    ((SECONDS < deadline)) || return 1
    sleep 0.05
  done
}

ensure_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Falta el comando requerido: $1"
}

resolve_pico_adb_target() {
  local candidate candidate_state reported_serial

  if [[ -n "$pico_adb_target" ]]; then
    candidate_state="$(
      timeout "${command_timeout_seconds}s" adb devices |
        awk -v target="$pico_adb_target" '$1 == target {print $2; exit}'
    )"
    if [[ "$candidate_state" != "device" && "$pico_adb_target" == *:* ]]; then
      progress "ADB: reabriendo transporte Wi-Fi explícito $pico_adb_target"
      timeout "${command_timeout_seconds}s" adb disconnect "$pico_adb_target" \
        >/dev/null 2>&1 || true
      timeout "${command_timeout_seconds}s" adb connect "$pico_adb_target" \
        >/dev/null 2>&1 || true
      candidate_state="$(
        timeout "${command_timeout_seconds}s" adb devices |
          awk -v target="$pico_adb_target" '$1 == target {print $2; exit}'
      )"
    fi
    [[ -n "$candidate_state" ]] || return 1
    if [[ "$candidate_state" == "device" ]]; then
      reported_serial="$(
        timeout "${command_timeout_seconds}s" \
          adb -s "$pico_adb_target" shell getprop ro.serialno 2>/dev/null |
          tr -d '\r'
      )" || return 1
      [[ "$reported_serial" == "$pico_serial" ]] || return 1
    fi
    return 0
  fi

  candidate_state="$(
    timeout "${command_timeout_seconds}s" adb devices |
      awk -v serial="$pico_serial" '$1 == serial {print $2; exit}'
  )"
  if [[ -n "$candidate_state" ]]; then
    pico_adb_target="$pico_serial"
    return 0
  fi

  while read -r candidate; do
    [[ -n "$candidate" ]] || continue
    reported_serial="$(
      timeout "${command_timeout_seconds}s" \
        adb -s "$candidate" shell getprop ro.serialno 2>/dev/null |
        tr -d '\r'
    )" || continue
    if [[ "$reported_serial" == "$pico_serial" ]]; then
      pico_adb_target="$candidate"
      return 0
    fi
  done < <(
    timeout "${command_timeout_seconds}s" adb devices |
      awk '$2 == "device" {print $1}'
  )

  # En el transporte XR directo no hay reverse ADB. El peer TCP 63901 permite
  # redescubrir la IP tras un sleep/reinicio sin fijarla en el repositorio.
  # Sólo se acepta la reconexión tras validar el serial físico del visor.
  if discover_pico_stream; then
    candidate="${pico_ip}:5555"
    progress "ADB: intentando reconexión Wi-Fi al peer XR $candidate"
    timeout "${command_timeout_seconds}s" adb connect "$candidate" \
      >/dev/null 2>&1 || true
    candidate_state="$(
      timeout "${command_timeout_seconds}s" adb devices |
        awk -v target="$candidate" '$1 == target {print $2; exit}'
    )"
    if [[ "$candidate_state" == "device" ]]; then
      reported_serial="$(
        timeout "${command_timeout_seconds}s" \
          adb -s "$candidate" shell getprop ro.serialno 2>/dev/null |
          tr -d '\r'
      )" || reported_serial=""
      if [[ "$reported_serial" == "$pico_serial" ]]; then
        pico_adb_target="$candidate"
        return 0
      fi
    fi
  fi

  return 1
}

adb_state() {
  timeout "${command_timeout_seconds}s" adb devices |
    awk -v target="$pico_adb_target" '$1 == target {print $2; exit}'
}

endpoint_ip() {
  sed -E \
    -e 's/^\[::ffff:([^]]+)\]:[0-9]+$/\1/' \
    -e 's/^([^:]+):[0-9]+$/\1/' <<<"$1"
}

discover_pico_stream() {
  local endpoints local_endpoint peer_endpoint detected_pc_ip detected_pico_ip
  endpoints="$(ss -Htn | awk '
    $1 == "ESTAB" && $4 ~ /:63901$/ {print $4, $5; exit}
  ')"
  [[ -n "$endpoints" ]] || return 1
  read -r local_endpoint peer_endpoint <<<"$endpoints"
  detected_pc_ip="$(endpoint_ip "$local_endpoint")"
  detected_pico_ip="$(endpoint_ip "$peer_endpoint")"
  [[ "$detected_pc_ip" =~ ^[0-9]+(\.[0-9]+){3}$ ]] || return 1
  [[ "$detected_pico_ip" =~ ^[0-9]+(\.[0-9]+){3}$ ]] || return 1

  if [[ -n "$pc_pico_ip" && "$pc_pico_ip" != "$detected_pc_ip" ]]; then
    die "PICO_PC_IP=$pc_pico_ip no coincide con el stream activo $detected_pc_ip."
  fi
  if [[ -n "$pico_ip" && "$pico_ip" != "$detected_pico_ip" ]]; then
    die "PICO_IP=$pico_ip no coincide con el stream activo $detected_pico_ip."
  fi
  pc_pico_ip="$detected_pc_ip"
  pico_ip="$detected_pico_ip"
}

has_established_pico_stream() {
  ss -Htn | awk -v local_ip="$pc_pico_ip" -v peer_ip="$pico_ip" '
    $1 == "ESTAB" && index($4, local_ip) && $4 ~ /:63901$/ && index($5, peer_ip) {found=1}
    END {exit !found}
  '
}

latest_log_has_pico() {
  local start_text recent_journal
  start_text="$(
    timeout "${command_timeout_seconds}s" \
      systemctl show "$backend_unit" -p ActiveEnterTimestamp --value
  )" || return 1
  recent_journal="$(
    timeout "${command_timeout_seconds}s" \
      journalctl -u "$backend_unit" --since "$start_text" --no-pager -n 2000 \
      2>/dev/null
  )" || return 1
  grep -qE 'device found|PA94Y0MGKB070822G' <<<"$recent_journal"
}

latest_log_has_expected_pico_serial() {
  local start_text recent_journal
  start_text="$(
    timeout "${command_timeout_seconds}s" \
      systemctl show "$backend_unit" -p ActiveEnterTimestamp --value
  )" || return 1
  recent_journal="$(
    timeout "${command_timeout_seconds}s" \
      journalctl -u "$backend_unit" --since "$start_text" --no-pager -n 2000 \
      2>/dev/null
  )" || return 1
  grep -Fq "$pico_serial" <<<"$recent_journal"
}

backend_detect_json() {
  # En 4.7.0 esto NO es una lectura pasiva: si el broadcast periódico coincide
  # con un cliente WebSocket y PICO está online, el backend puede arrancar el
  # publisher. Usar sólo después del START autorizado; para preflight/STOP use
  # backend_passive_state_json().
  timeout "${command_timeout_seconds}s" python3 - <<'PY'
import websocket

ws = websocket.create_connection("ws://127.0.0.1:8082", timeout=3)
try:
    print(ws.recv())
finally:
    ws.close()
PY
}

backend_passive_state_json() {
  local backend_start_text backend_start_ts
  backend_start_text="$(
    timeout "${command_timeout_seconds}s" \
      systemctl show "$backend_unit" -p ActiveEnterTimestamp --value
  )" || return 1
  backend_start_ts="$(date -d "$backend_start_text" '+%Y-%m-%d:%H:%M:%S')" ||
    return 1

  BACKEND_LOG="$backend_log" BACKEND_START_TS="$backend_start_ts" \
    timeout "${command_timeout_seconds}s" python3 - <<'PY'
import json
import os
import sys

path = os.environ["BACKEND_LOG"]
start_ts = os.environ["BACKEND_START_TS"]


def reverse_lines(file_path, block_size=65536):
    with open(file_path, "rb") as stream:
        stream.seek(0, 2)
        position = stream.tell()
        remainder = b""
        while position:
            size = min(block_size, position)
            position -= size
            stream.seek(position)
            parts = (stream.read(size) + remainder).split(b"\n")
            remainder = parts[0]
            for raw_line in reversed(parts[1:]):
                yield raw_line.decode("utf-8", errors="replace")
        if remainder:
            yield remainder.decode("utf-8", errors="replace")


snapshot = None
operation_type = None
for line in reverse_lines(path):
    # Las líneas comienzan por YYYY-MM-DD:HH:MM:SS.mmm. No reutilizar eventos
    # de una ejecución anterior del servicio.
    if len(line) >= 19 and line[:19] < start_ts:
        break

    if operation_type is None:
        if "Pico publisher stop" in line:
            operation_type = 1
        elif "Pico publisher start" in line:
            operation_type = 2

    if snapshot is None:
        raw_json = None
        marker = 'Send message to client: {"type":"detect"'
        if marker in line:
            raw_json = line.split("Send message to client: ", 1)[1]
        elif "Pico connect state from " in line and " changed to {" in line:
            raw_json = line.split(" changed to ", 1)[1]
            raw_json = raw_json.rsplit(", broadcast it", 1)[0]
        if raw_json is not None:
            try:
                candidate = json.loads(raw_json)
            except json.JSONDecodeError:
                candidate = None
            if isinstance(candidate, dict) and candidate.get("type") == "detect":
                snapshot = candidate

    if snapshot is not None and operation_type is not None:
        break

if snapshot is None:
    print("No current passive backend snapshot", file=sys.stderr)
    raise SystemExit(2)

content = snapshot.setdefault("content", {})
if operation_type is None:
    operation_type = content.get("operation_type", 1)
content["operation_type"] = operation_type
if operation_type == 1:
    content["robot_sn"] = ""
print(json.dumps(snapshot, separators=(",", ":")))
PY
}

check_pc() {
  progress "CHECK 1/7: comprobando herramientas locales"
  ensure_cmd adb
  ensure_cmd ip
  ensure_cmd ping
  ensure_cmd ss
  ensure_cmd systemctl
  ensure_cmd timeout
  ensure_cmd python3
  ensure_cmd jq
  ensure_cmd sha256sum
  ensure_cmd nmcli
  ensure_cmd dpkg-query
  ensure_cmd stat
  ensure_cmd date

  progress "CHECK 2/7: comprobando ADB y XRoboToolkit en el PICO (timeout ${command_timeout_seconds}s)"
  local current_adb_state pico_identity_source="adb" pico_adb_available=0
  if resolve_pico_adb_target; then
    if ! current_adb_state="$(adb_state)"; then
      die "ADB no respondió dentro de ${command_timeout_seconds}s."
    fi
    [[ "$current_adb_state" == "device" ]] ||
      die "PICO no autorizado por ADB ($pico_adb_target; estado=${current_adb_state:-ausente})."
    timeout "${command_timeout_seconds}s" \
      adb -s "$pico_adb_target" shell pidof com.xrobotoolkit.client \
      >/dev/null 2>&1 ||
      die "XRoboToolkit no está abierto en el PICO."
    pico_adb_available=1
  else
    [[ "$teleop_camera" == "off" ]] ||
      die "No se encontró por ADB el PICO físico $pico_serial; la cámara '$teleop_camera' mantiene ADB obligatorio."
    timeout "${command_timeout_seconds}s" \
      systemctl is-active --quiet "$backend_unit" ||
      die "Sin ADB no se puede validar el PICO: $backend_unit no está activo."
    ss -Hlnt | grep -q ':63901 ' ||
      die "Sin ADB no se puede validar el PICO: XR no escucha en TCP 63901."
    discover_pico_stream ||
      die "Sin ADB no se encontró un peer XR activo hacia TCP 63901."
    has_established_pico_stream ||
      die "Sin ADB no se confirmó el flujo XR $pico_ip->$pc_pico_ip:63901."
    latest_log_has_expected_pico_serial ||
      die "Sin ADB, el backend no demostró el serial esperado $pico_serial en esta ejecución."
    pico_identity_source="xr-backend"
    info "PICO_ADB_UNAVAILABLE=1; CAMERA=off; CONTINUING_WITH_STRICT_XR_IDENTITY=1"
  fi

  progress "CHECK 3/7: comprobando enlace Cruzr, rutas y hosts Motion/Vision"
  discover_robot_link_route
  ip -4 -o addr show dev "$robot_iface" | grep -q " $robot_pc_ip/" ||
    die "$robot_iface no tiene $robot_pc_ip."
  ip route get "$motion_ip" | grep -q "dev $robot_iface" ||
    die "La ruta a motion no usa $robot_iface."
  ip route get "$vision_ip" | grep -q "dev $robot_iface" ||
    die "La ruta a vision no usa $robot_iface."
  if [[ "$robot_link_kind" == "wifi" ]]; then
    ensure_cmd iw
    iw dev "$robot_iface" get power_save 2>/dev/null | grep -q 'Power save: off' ||
      die "$robot_iface mantiene ahorro Wi-Fi activo; reactive el perfil $robot_wifi_ssid con powersave=disable."
  fi
  ping -c 1 -W 1 "$motion_ip" >/dev/null || die "Motion $motion_ip no responde."
  ping -c 1 -W 1 "$vision_ip" >/dev/null || die "Vision $vision_ip no responde."

  progress "CHECK 4/7: comprobando servicios y listeners 8082/63901"
  timeout "${command_timeout_seconds}s" \
    systemctl is-active --quiet "$backend_unit" ||
    die "$backend_unit no está activo o systemd no respondió."
  ss -Hlnt | grep -q ':8082 ' || die "El backend no escucha en TCP 8082."
  ss -Hlnt | grep -q ':63901 ' || die "XRoboToolkit PC Service no escucha en TCP 63901."

  progress "CHECK 5/7: comprobando stream PICO y discovery del backend"
  discover_pico_stream || die "PICO no mantiene ningún flujo TCP hacia el servicio XR en 63901."
  has_established_pico_stream || die "PICO no mantiene el flujo TCP hacia $pc_pico_ip:63901."
  latest_log_has_pico ||
    die "No se encontró discovery del PICO en el journal reciente o la consulta agotó ${command_timeout_seconds}s."

  progress "CHECK 6/7: comprobando baseline oficial 4.7.0, arm=clamp y binario sin parches"
  local environment backend_sha256 pico_control_sha256 backend_version ui_version
  environment="$(
    timeout "${command_timeout_seconds}s" \
      systemctl show "$backend_unit" -p Environment --value
  )" || die "systemd no devolvió el entorno del backend dentro de ${command_timeout_seconds}s."
  [[ " $environment " == *" arm=$required_arm "* ]] ||
    die "El backend no está fijado a arm=$required_arm; reinstale el drop-in del PC."
  [[ " $environment " == *" LC_NUMERIC=C "* ]] ||
    die "El backend no fija LC_NUMERIC=C; reinstale el drop-in de locale numérico."
  backend_version="$(dpkg-query -W -f='${Version}' ubt-controller 2>/dev/null)" ||
    die "No se pudo consultar la versión instalada de ubt-controller."
  [[ "$backend_version" == "$expected_backend_version" ]] ||
    die "Se requiere ubt-controller $expected_backend_version; está instalado $backend_version."
  ui_version="$(dpkg-query -W -f='${Version}' ubt-remote-control 2>/dev/null)" ||
    die "No se pudo consultar la versión instalada de ubt-remote-control."
  [[ "$ui_version" == "$expected_ui_version" ]] ||
    die "Se requiere ubt-remote-control $expected_ui_version; está instalado $ui_version."
  backend_sha256="$(sha256sum "$backend_executable" | awk '{print $1}')"
  [[ "$backend_sha256" == "$expected_backend_sha256" ]] ||
    die "El binario 4.7.0 no coincide con el DEB oficial recibido (SHA-256=$backend_sha256)."
  [[ -x "$pico_control_executable" ]] ||
    die "El paquete 4.7.0 no dejó ejecutable $pico_control_executable."
  pico_control_sha256="$(sha256sum "$pico_control_executable" | awk '{print $1}')"
  [[ "$pico_control_sha256" == "$expected_pico_control_sha256" ]] ||
    die "pico_control no coincide con el DEB 4.7.0 (SHA-256=$pico_control_sha256)."
  "$pico_control_executable" --help 2>&1 | grep -q -- '--arm_type {hand,clamp,gripper}' ||
    die "pico_control 4.7.0 no anuncia arm_type=clamp en su ayuda."

  progress "CHECK 7/7: comprobando estado pasivo del backend (sin abrir WebSocket)"
  local detect_json vr_status operation_type
  if ! detect_json="$(backend_passive_state_json)"; then
    die "No se pudo reconstruir pasivamente el estado actual del backend."
  fi
  vr_status="$(jq -r 'select(.type == "detect") | .content.vr_status' <<<"$detect_json")"
  operation_type="$(jq -r 'select(.type == "detect") | .content.operation_type' <<<"$detect_json")"
  [[ "$vr_status" == "1" ]] ||
    die "XRoboToolkit no envía HEAD+CONTROLLERS (vr_status=$vr_status). Active Send data/Working en el PICO."
  [[ "$operation_type" == "1" ]] ||
    die "El backend ya está en operación remota (operation_type=$operation_type); ejecute --stop antes de iniciar."

  info "PC_ROBOT_LINK_OK=$robot_link_kind,$robot_connection_name,$robot_iface:$robot_pc_ip"
  if [[ "$robot_link_kind" == "wifi" ]]; then
    info "ROBOT_WIFI_POWERSAVE=off"
  fi
  info "ROBOT_LINK_OK=motion:$motion_ip,vision:$vision_ip"
  if ((pico_adb_available == 1)); then
    info "PICO_ADB_OK=$pico_adb_target (device=$pico_serial)"
  else
    info "PICO_ADB_OPTIONAL_FOR_CAMERA_OFF=unavailable"
  fi
  info "PICO_IDENTITY_OK=$pico_serial,source:$pico_identity_source"
  info "PICO_STREAM_OK=$pico_ip->$pc_pico_ip:63901"
  info "PICO_TRACKING_OK=vr_status:$vr_status"
  info "BACKEND_OK=ubt-controller:$backend_version,arm:$required_arm,ws:8082"
  info "OFFICIAL_COMPATIBILITY_BASELINE_OK=robot-v0.2.0/controller-$backend_version/ui-$ui_version"
  info "BACKEND_VENDOR_BINARY_SHA256_OK=$backend_sha256"
  info "PICO_CONTROL_VENDOR_CLI_OK=$pico_control_sha256,arm_type=clamp"
  info "HEARTBEAT_WATCHDOG=vendor-default-unmodified"
  info "PICO_ENABLE_PROTOCOL=verified-live-vendor-Y->Left.b_button->tele_operation.enable:1"
  info "PICO_ARM_SELECTION_LIVE=requested:clamp,pc-observed:gripper,motion-hand:clamp,pc-label-pending"
  info "PICO_STOP_PROTOCOL=verified-official-client->operation_type:1"
  info "BACKEND_STATE_SOURCE=passive-log-no-websocket"
  info "STOP_DIAGNOSTIC_NOTE=preflight-and-final-verification-do-not-open-websocket"
  info "LEGACY_PHYSICAL_GATES_BLOCKED=1"
  info "UI_PACKAGE_OK=ubt-remote-control:$ui_version"
  progress "CHECK COMPLETADO"
}

send_local_message() {
  local payload="$1"
  PAYLOAD="$payload" python3 - <<'PY'
import json
import os
import sys
import time
import websocket

ws = websocket.create_connection("ws://127.0.0.1:8082", timeout=3)
try:
    # The backend sends its current state immediately after accepting a client.
    # Consume that snapshot so a later collect response cannot be mistaken for
    # the pre-command state.
    try:
        ws.recv()
    except Exception:
        pass
    ws.send(os.environ["PAYLOAD"])
    deadline = time.monotonic() + 3
    messages = []
    while time.monotonic() < deadline:
        try:
            raw = ws.recv()
        except Exception:
            break
        messages.append(raw)
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if data.get("type") in {"detect", "error"}:
            print(raw)
            break
    if not messages:
        print("LOCAL_WS_SENT_NO_RESPONSE", file=sys.stderr)
finally:
    ws.close()
PY
}

open_ui() {
  check_pc
  progress "UI: iniciando $ui_unit"
  systemctl --user reset-failed "$ui_unit" >/dev/null 2>&1 || true
  if ! systemctl --user is-active --quiet "$ui_unit"; then
    systemctl --user start "$ui_unit"
  fi

  local deadline=$((SECONDS + 20))
  until ss -Htn | grep -qE '127\.0\.0\.1:[0-9]+ +127\.0\.0\.1:8082'; do
    ((SECONDS < deadline)) || die "La interfaz no conectó al backend TCP 8082."
    progress "UI: esperando conexión local a 8082 ($((deadline - SECONDS))s restantes)"
    sleep 1
  done
  sleep 2
  local detect_json operation_type enable_control
  detect_json="$(backend_detect_json)"
  operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
  enable_control="$(jq -r 'if .content | has("enable_control") then .content.enable_control else "absent" end' <<<"$detect_json")"
  if [[ "$operation_type" != "1" || ("$enable_control" != "absent" && "$enable_control" != "0") ]]; then
    stop_all
    die "La UI alteró el estado remoto al abrirse; STOP enviado (operation_type=$operation_type, enable_control=$enable_control)."
  fi
  info "UI_CONNECTED=local-ws:8082"
  info "UI_NOTE=no pulse todavía el botón chino de inicio ni Y"
}

stop_pico_camera() {
  if [[ -n "$camera_pid" ]] && kill -0 "$camera_pid" 2>/dev/null; then
    kill -TERM "$camera_pid" 2>/dev/null || true
    wait "$camera_pid" 2>/dev/null || true
  fi
  camera_pid=""
  if [[ -n "$camera_ready_file" && -f "$camera_ready_file" ]]; then
    rm -f -- "$camera_ready_file"
  fi
  camera_ready_file=""
  info "PICO_CAMERA_STOPPED=1"
}

start_pico_camera() {
  if [[ "$teleop_camera" == "off" ]]; then
    info "PICO_CAMERA_DISABLED_EXPLICITLY=1"
    return 0
  fi
  case "$teleop_camera" in
    main|stereo-right|waist|chassis)
      ;;
    *)
      die "PICO_TELEOP_CAMERA debe ser main, stereo-right, waist, chassis u off."
      ;;
  esac
  [[ -x "$camera_script" ]] ||
    die "No se puede ejecutar el puente de cámara: $camera_script"

  camera_ready_file="$(mktemp --tmpdir humanoide-teleop-camera-ready.XXXXXX)"
  rm -f -- "$camera_ready_file"
  cat <<EOF

VÍDEO OBLIGATORIO ANTES DE START
En el PICO abra Camera y active «Request PC camera data». No cierre
XRoboToolkit ni desactive Head + Controllers / Send data / Working. El robot
seguirá desarmado hasta recibir el primer keyframe de la cámara '$teleop_camera'.

EOF
  local camera_pico_ip
  camera_pico_ip="${PICO_CAMERA_PICO_IP:-}"
  if [[ -z "$camera_pico_ip" ]]; then
    camera_pico_ip="$(
      timeout "${command_timeout_seconds}s" adb -s "$pico_adb_target" shell \
        'ip -4 -o addr show wlan0 2>/dev/null' |
        awk '{split($4,address,"/"); print address[1]; exit}' |
        tr -d '\r'
    )"
  fi
  [[ "$camera_pico_ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] ||
    camera_pico_ip="$pico_ip"
  info "PICO_CAMERA_TARGET_DISCOVERED=$camera_pico_ip"

  PICO_IP="$camera_pico_ip" \
    PICO_ADB_TARGET="$pico_adb_target" \
    PICO_CAMERA_READY_FILE="$camera_ready_file" \
    "$camera_script" --run --camera "$teleop_camera" &
  camera_pid=$!

  local deadline=$((SECONDS + 75)) next_notice=$SECONDS
  while [[ ! -s "$camera_ready_file" ]]; do
    if ! kill -0 "$camera_pid" 2>/dev/null; then
      wait "$camera_pid" || true
      camera_pid=""
      rm -f -- "$camera_ready_file"
      camera_ready_file=""
      die "La cámara PICO terminó antes de mostrar vídeo; no se enviará START."
    fi
    if ((SECONDS >= deadline)); then
      stop_pico_camera
      die "La cámara PICO no recibió un keyframe en 75 s; no se enviará START."
    fi
    if ((SECONDS >= next_notice)); then
      progress "CÁMARA: esperando Request PC camera data / primer keyframe ($((deadline - SECONDS))s)"
      next_notice=$((SECONDS + 5))
    fi
    sleep 0.25
  done
  info "PICO_CAMERA_REQUIRED=1"
  info "PICO_CAMERA_SOURCE=$teleop_camera"
  info "PICO_CAMERA_LIVE_BEFORE_START=1"
  info "Vuelva a dejar cabeza, botones, gatillos, grips y joysticks neutros."
}

stop_all() {
  if systemctl is-active --quiet "$backend_unit" && ss -Hlnt | grep -q ':8082 '; then
    send_local_message '{"type":"collect","content":{"operation_type":1}}' || true
  fi
  systemctl --user stop "$ui_unit" >/dev/null 2>&1 || true
  info "TELEOPERATION_STOP_REQUESTED=1"
  info "UI_STOPPED=1"
  stop_pico_camera
}

require_official_enable_protocol_validation() {
  stop_all
  die "Movimiento bloqueado en este gate legado: Y y el STOP oficial de 4.7.0 ya se validaron, pero este flujo todavía depende del campo enable_control ausente y no usa el cliente pico_control del proveedor. Use --check; adapte el gate al cliente oficial antes de otro START automatizado."
}

wait_for_pico_tracking_ready() {
  local deadline=$((SECONDS + 30)) next_notice=$SECONDS detect_json vr_status
  systemctl is-active --quiet "$backend_unit" ||
    die "$backend_unit no está activo antes de esperar al PICO."
  ss -Hlnt | grep -q ':8082 ' ||
    die "El backend no escucha en TCP 8082 antes de esperar al PICO."

  while ((SECONDS < deadline)); do
    detect_json="$(backend_passive_state_json 2>/dev/null || true)"
    vr_status="$(jq -r '.content.vr_status // "unknown"' <<<"$detect_json" 2>/dev/null || true)"
    if [[ "$vr_status" == "1" ]]; then
      info "PICO_TRACKING_READY_BEFORE_PREFLIGHT=1"
      return 0
    fi
    if ((SECONDS >= next_notice)); then
      progress "PICO: active Head + Controllers y Send data / Working (${deadline-SECONDS}s restantes; vr_status=$vr_status)"
      next_notice=$((SECONDS + 5))
    fi
    sleep 1
  done
  die "XRoboToolkit sigue en vr_status=$vr_status tras 30 s; active Head + Controllers / Send data / Working."
}

cleanup_official_teleop() {
  ((official_cleanup_done == 0)) || return 0
  official_cleanup_done=1
  trap - ERR INT TERM EXIT

  if [[ -n "$official_client_pid" ]] && kill -0 "$official_client_pid" 2>/dev/null; then
    kill -INT "$official_client_pid" 2>/dev/null || true
    wait "$official_client_pid" 2>/dev/null || true
  fi
  official_client_pid=""

  # pico_control envía operation_type=1 al recibir SIGINT. Verificarlo desde el
  # log: abrir otro WebSocket sólo para leer puede volver a arrancar 4.7.0 si
  # coincide con su broadcast periódico y PICO continúa online.
  systemctl --user stop "$ui_unit" >/dev/null 2>&1 || true
  stop_pico_camera
  info "TELEOPERATION_STOP_REQUESTED=1"
  info "UI_STOPPED=1"

  local detect_json operation_type attempt
  operation_type="unknown"
  for attempt in {1..15}; do
    detect_json="$(backend_passive_state_json 2>/dev/null || true)"
    operation_type="$(jq -r '.content.operation_type // "unknown"' <<<"$detect_json" 2>/dev/null || true)"
    [[ "$operation_type" == "1" ]] && break
    sleep 0.2
  done

  # Sólo la ausencia del STOP del cliente oficial justifica abrir un cliente
  # de emergencia que envíe STOP. No se usa para una comprobación ordinaria.
  if [[ "$operation_type" != "1" ]]; then
    info "OFFICIAL_STOP_NOT_OBSERVED_PASSIVELY=1; sending emergency STOP"
    stop_all || true
    for attempt in {1..10}; do
      detect_json="$(backend_passive_state_json 2>/dev/null || true)"
      operation_type="$(jq -r '.content.operation_type // "unknown"' <<<"$detect_json" 2>/dev/null || true)"
      [[ "$operation_type" == "1" ]] && break
      sleep 0.2
    done
  fi
  info "OFFICIAL_TELEOP_FINAL_OPERATION_TYPE=$operation_type"
  info "OFFICIAL_TELEOP_STOP_CONFIRMED=$([[ "$operation_type" == "1" ]] && printf 1 || printf 0)"
}

run_official_arm_teleop() {
  [[ -t 0 && -t 1 ]] ||
    die "La teleoperación física debe ejecutarse directamente en el terminal local del PC."
  [[ "$official_teleop_seconds" =~ ^[0-9]+$ ]] ||
    die "PICO_OFFICIAL_TELEOP_SECONDS debe ser un entero entre 120 y 300."
  ((official_teleop_seconds >= 120 && official_teleop_seconds <= 300)) ||
    die "PICO_OFFICIAL_TELEOP_SECONDS debe estar entre 120 y 300."
  [[ "$allow_bimanual" == "0" || "$allow_bimanual" == "1" ]] ||
    die "PICO_ALLOW_BIMANUAL debe ser 0 o 1."

  official_cleanup_done=0
  trap cleanup_official_teleop EXIT
  trap 'printf "\nABORT_REQUESTED=INT\n" >&2; exit 130' INT
  trap 'printf "\nABORT_REQUESTED=TERM\n" >&2; exit 143' TERM

  # Este gate es independiente del visor y debe fallar primero: evita esperar
  # 30 s por Working cuando Motion aún conserva el perfil de cuerpo completo.
  check_robot_arms_only_loaded
  wait_for_pico_tracking_ready
  check_pc
  systemctl --user is-active --quiet "$ui_unit" &&
    die "$ui_unit está activo; ciérrelo para conservar un solo cliente de control."

  cat <<EOF

TELEOPERACIÓN OFICIAL 4.7.0 — BRAZOS, ${official_teleop_seconds} SEGUNDOS

Esta ventana permite mover uno o ambos brazos con sus grips después de pulsar
Y una vez. El perfil arms-only mantiene cintura y elevador fuera del control.
Con ambos brazos use recorridos pequeños, sincronizados y dentro del alcance;
suelte los grips ante resistencia, retraso o cualquier movimiento del torso.
No use gatillos, joysticks, clicks, X/A/B ni comandos de chasis/elevador.
Confirme ahora: abrazaderas vacías, postura actual despejada, cargador fuera,
paros liberados, persona junto al paro y nadie dentro de la trayectoria.

Escriba exactamente: INICIAR TELEOPERACION OFICIAL DE BRAZOS
EOF
  local confirmation
  read -r confirmation
  [[ "$confirmation" == "INICIAR TELEOPERACION OFICIAL DE BRAZOS" ]] ||
    die "Confirmación incorrecta; no se enviará START."

  start_pico_camera
  check_robot_teleop_safety
  info "Deje cabeza, grips, gatillos, botones y joysticks completamente neutros."

  local start_line enable_line deadline next_progress detect_json operation_type
  start_line="$(($(wc -l < "$backend_log") + 1))"
  "$pico_control_executable" \
    --websocket_url ws://127.0.0.1:8082 \
    --arm_type clamp --enable_hand_pose 0 --push_rate 90 &
  official_client_pid=$!

  deadline=$((SECONDS + 10))
  operation_type="unknown"
  while ((SECONDS < deadline)); do
    kill -0 "$official_client_pid" 2>/dev/null ||
      die "pico_control terminó durante START."
    detect_json="$(backend_detect_json)"
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    [[ "$operation_type" == "2" ]] && break
    sleep 0.1
  done
  [[ "$operation_type" == "2" ]] || die "pico_control no confirmó operation_type=2."

  check_controller_inputs_neutral "$start_line"
  enable_line="$(($(wc -l < "$backend_log") + 1))"
  cat <<'EOF'

========== PULSE Y IZQUIERDO UNA VEZ Y SUÉLTELO ==========
No toque grips ni mueva las manos hasta ver ENABLE_OFICIAL_CONFIRMADO=1.
EOF

  deadline=$((SECONDS + 15))
  while ! tail -n "+$enable_line" "$backend_log" |
    grep -q 'Callback received data:.*"enable":1'; do
    kill -0 "$official_client_pid" 2>/dev/null ||
      die "pico_control terminó antes de Y/enable."
    ((SECONDS < deadline)) || die "No se observó Y/enable=1 dentro de 15 s."
    sleep 0.05
  done
  info "ENABLE_OFICIAL_CONFIRMADO=1"
  info "BIMANUAL_CONTROL_ENABLED=$allow_bimanual"
  if [[ "$allow_bimanual" == "1" ]]; then
    info "UNO_O_AMBOS_BRAZOS=1; mantenga cada grip sólo durante su movimiento"
  else
    info "MUEVA_UN_BRAZO_POR_VEZ=1; ambos grips solicitarán STOP"
  fi

  local active_start=$SECONDS active_deadline=$((SECONDS + official_teleop_seconds))
  local bimanual_active=0
  next_progress=$SECONDS
  while ((SECONDS < active_deadline)); do
    kill -0 "$official_client_pid" 2>/dev/null ||
      die "pico_control terminó durante la ventana activa."
    detect_json="$(backend_detect_json)"
    robot_link_runtime_ok || die "Se perdió el enlace del robot durante la teleoperación oficial."
    pico_camera_runtime_ok || die "Se perdió la cámara principal durante la teleoperación oficial."
    [[ "$(jq -r '.content.vr_status' <<<"$detect_json")" == "1" ]] ||
      die "Se perdió HEAD+CONTROLLERS durante la teleoperación oficial."
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    [[ "$operation_type" == "2" ]] || die "La sesión perdió operation_type=2."
    if tail -n "+$enable_line" "$backend_log" |
      grep 'Callback received data:.*"enable":[01]' | tail -n1 |
      grep -q '"enable":0'; then
      die "Y deshabilitó la sesión; se solicitará STOP."
    fi
    if tail -n "+$start_line" "$backend_log" |
      grep -qE 'No heartbeat for .+ seconds, stoping operation'; then
      die "El watchdog oficial perdió heartbeat; se solicitará STOP."
    fi
    if both_grips_currently_pressed_since "$start_line"; then
      if [[ "$allow_bimanual" == "0" ]]; then
        die "Se detectaron ambos grips y PICO_ALLOW_BIMANUAL=0; se solicitará STOP."
      fi
      if ((bimanual_active == 0)); then
        info "BIMANUAL_GRIPS_ACTIVE=1"
        bimanual_active=1
      fi
    elif ((bimanual_active == 1)); then
      info "BIMANUAL_GRIPS_ACTIVE=0"
      bimanual_active=0
    fi
    if ((SECONDS >= next_progress)); then
      info "OFFICIAL_TELEOP_LIVE=1 ELAPSED=$((SECONDS - active_start))s REMAINING=$((active_deadline - SECONDS))s"
      next_progress=$((SECONDS + 5))
    fi
    sleep 0.5
  done

  cleanup_official_teleop
  info "OFFICIAL_TELEOP_WINDOW_COMPLETED=${official_teleop_seconds}s"
  trap - ERR INT TERM EXIT
}

abort_gate() {
  local signal="${1:-INT}"
  local exit_code=130
  [[ "$signal" == "TERM" ]] && exit_code=143

  # El handler anterior sólo ejecutaba STOP y después devolvía el control al
  # read interrumpido. Desactivar primero los traps evita recursión y garantiza
  # que Ctrl+C/TERM terminen la prueba después del STOP.
  trap - ERR INT TERM
  printf '\nABORT_REQUESTED=%s\n' "$signal" >&2
  stop_all || true
  printf 'ERROR: Prueba abortada por el operador; no se continuará.\n' >&2
  exit "$exit_code"
}

gate_error() {
  local status="$1"
  local line="$2"
  local command="$3"
  trap - ERR INT TERM
  printf '[%(%H:%M:%S)T] ERROR inesperado en línea %s (status=%s): %s\n' \
    -1 "$line" "$status" "$command" >&2
  stop_all || true
  exit "$status"
}

run_arm_motion_test() {
  local side="$1"
  local hand_label opposite_label side_es side_es_upper confirmation_expected
  case "$side" in
    left)
      hand_label="Left"
      opposite_label="Right"
      side_es="izquierdo"
      side_es_upper="IZQUIERDO"
      ;;
    right)
      hand_label="Right"
      opposite_label="Left"
      side_es="derecho"
      side_es_upper="DERECHO"
      ;;
    *)
      die "Brazo de prueba desconocido: $side"
      ;;
  esac

  require_official_enable_protocol_validation
  [[ -t 0 && -t 1 ]] ||
    die "La prueba de movimiento exige un terminal interactivo local."
  check_pc
  if systemctl --user is-active --quiet "$ui_unit"; then
    die "$ui_unit está activo; ejecute --stop antes de mover para conservar un solo cliente."
  fi

  confirmation_expected="MOVER SOLO BRAZO $side_es_upper EN ZONA DESPEJADA"
  cat <<EOF

TELEOPERACIÓN FÍSICA REAL — SÓLO BRAZO $side_es_upper

Esta prueba puede mover físicamente brazo, cabeza y otros ejes que el modo
PICO tenga asociados. Antes de continuar confirme AHORA, no por recuerdo:

- abrazaderas instaladas, firmes, vacías y sin objeto sujeto;
- postura home comprobada visualmente y brazo $side_es libre de mesa/caja;
- batería suficiente y cargador desconectado;
- ambos paros liberados, chasis inmóvil y ruedas bloqueadas para modo en sitio;
- web en 遥操模式 / Remote control mode y ningún otro cliente de mando;
- envolvente completa despejada y una segunda persona junto al paro físico;
- ambos mandos neutros, cabeza quieta, grips/gatillos/joysticks libres.

El script verificará además paros, batería, cargador, HW_TYPE, tarea PICO y
velocidad articular antes de START. Primero mantendrá 60 s sin maniobra. Luego
permitirá únicamente el grip $side_es durante 5 s como máximo.

Escriba exactamente: $confirmation_expected
EOF
  local confirmation
  read -r confirmation
  [[ "$confirmation" == "$confirmation_expected" ]] ||
    die "Confirmación incorrecta; no se inició la publicación."

  cat <<EOF

PREPARACIÓN INMEDIATA
Mantenga cabeza y ambos mandos quietos. No toque todavía ningún grip ni
gatillo. La persona del terminal debe permanecer junto a Ctrl+C y la segunda
persona junto al paro físico. Pulse Enter para ejecutar el último preflight
Motion y armar exclusivamente esta prueba del brazo $side_es.
EOF
  read -r _

  # La cámara debe estar viva antes del snapshot físico final para que la
  # espera/interacción del visor no vuelva obsoleto ese preflight.
  start_pico_camera

  # Se ejecuta después de la cámara y de la confirmación humana para reducir
  # el intervalo entre el snapshot de seguridad del robot y el START real.
  check_robot_teleop_safety

  local start_line
  start_line="$(wc -l < "$backend_log")"
  progress "MOVIMIENTO: enviando START local con arm_type=clamp"
  send_local_message '{"type":"collect","content":{"arm_type":"clamp","operation_type":2}}'

  local deadline=$((SECONDS + 8))
  progress "MOVIMIENTO: esperando confirmación arm=clamp (máximo 8 s)"
  until tail -n "+$((start_line + 1))" "$backend_log" | grep -q 'Arm type is: clamp'; do
    if tail -n "+$((start_line + 1))" "$backend_log" | grep -q 'Arm type is: gripper'; then
      stop_all
      die "El backend seleccionó gripper; STOP enviado."
    fi
    ((SECONDS < deadline)) || {
      stop_all
      die "No se confirmó arm_type=clamp; STOP enviado."
    }
    sleep 0.25
  done

  info "ARM_TYPE_CONFIRMED=clamp"
  check_controller_inputs_neutral "$((start_line + 1))"
  info "PUBLISHER_ARMED=1"
  printf '\a\n'
  info "========== TOQUE AHORA: GATILLO IZQUIERDO UNA VEZ Y SUÉLTELO =========="
  info "NO USE GRIP TODAVÍA; NO VUELVA A TOCAR EL GATILLO"

  local enabled=0 detect_json operation_type enable_control
  local enable_deadline=$((SECONDS + 8))
  while ((SECONDS < enable_deadline)); do
    detect_json="$(backend_detect_json)"
    assert_runtime_links "$detect_json" "antes de habilitar el brazo $side_es"
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    enable_control="$(jq -r '.content.enable_control' <<<"$detect_json")"
    if [[ "$operation_type" == "2" && "$enable_control" == "1" ]]; then
      enabled=1
      break
    fi
    if [[ "$operation_type" == "1" ]]; then
      stop_all
      die "El robot cerró la sesión antes de habilitar; STOP confirmado."
    fi
    sleep 0.25
  done
  if [[ "$enabled" != "1" ]]; then
    stop_all
    die "No se detectó el toque único/enable_control=1; STOP enviado."
  fi
  info "ENABLE_CONTROL_CONFIRMED=1"
  local release_line
  release_line="$(wc -l < "$backend_log")"
  if ! wait_for_left_trigger_release "$((release_line + 1))"; then
    stop_all
    die "El gatillo izquierdo no quedó liberado dentro de 3 s; STOP enviado."
  fi
  info "LEFT_TRIGGER_RELEASE_CONFIRMED=1"

  # Antes de una maniobra real se exige una ventana completa sin grips. Esto
  # prueba estabilidad del enlace, no la presencia del heartbeat del proveedor.
  info "STABILITY_WINDOW=60s; MANDOS Y CABEZA QUIETOS; GRIPS LIBRES"
  local stability_start=$SECONDS
  local stability_deadline=$((stability_start + 60))
  local next_progress=$stability_start
  while ((SECONDS < stability_deadline)); do
    if awk -v first="$((start_line + 1))" '
      NR >= first && /No heartbeat for .+ seconds, stoping operation/ {found=1; exit}
      END {exit !found}
    ' "$backend_log"; then
      stop_all
      die "El watchdog cerró el enlace durante estabilidad; STOP enviado."
    fi
    if grip_state_seen_since "$((start_line + 1))" "Left" true ||
       grip_state_seen_since "$((start_line + 1))" "Right" true; then
      stop_all
      die "Se pulsó un grip antes de la fase de movimiento; STOP enviado."
    fi

    detect_json="$(backend_detect_json)"
    assert_runtime_links "$detect_json" "durante la estabilidad del brazo $side_es"
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    enable_control="$(jq -r '.content.enable_control' <<<"$detect_json")"
    if [[ "$operation_type" != "2" || "$enable_control" != "1" ]]; then
      stop_all
      die "Se perdió habilitación durante estabilidad (operation_type=$operation_type, enable_control=$enable_control)."
    fi
    if ((SECONDS >= next_progress)); then
      info "STABILITY_LIVE=1 ELAPSED=$((SECONDS - stability_start))s REMAINING=$((stability_deadline - SECONDS))s"
      next_progress=$((SECONDS + 5))
    fi
    sleep 1
  done
  info "STABILITY_COMPLETED=60s"

  local grip_prompt_line
  grip_prompt_line="$(wc -l < "$backend_log")"
  printf '\a\n'
  cat <<EOF

========== MUEVA SÓLO EL BRAZO $side_es_upper ==========
1. Mantenga apretado únicamente el GRIP $side_es.
2. Desplace ese mando MUY LENTAMENTE 2-3 cm hacia arriba y fuera del torso.
3. Vuelva esos mismos 2-3 cm al punto inicial, todavía con el grip apretado.
4. Suelte el grip. No toque gatillos, joysticks ni otros botones.

Tiene 8 s para iniciar y 5 s como máximo desde que se detecte el grip.
Soltar el grip provoca STOP inmediato del PC. Ctrl+C o el paro físico abortan.
EOF

  local grip_true_line=""
  local grip_wait_deadline=$((SECONDS + 8))
  while ((SECONDS < grip_wait_deadline)); do
    if grip_state_seen_since "$((grip_prompt_line + 1))" "$opposite_label" true; then
      stop_all
      die "Se pulsó el grip opuesto; STOP enviado."
    fi
    if grip_state_seen_since "$((grip_prompt_line + 1))" "$hand_label" true; then
      grip_true_line="$(first_grip_state_line "$((grip_prompt_line + 1))" "$hand_label" true)"
      break
    fi
    detect_json="$(backend_detect_json)"
    assert_runtime_links "$detect_json" "esperando el grip $side_es"
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    enable_control="$(jq -r '.content.enable_control' <<<"$detect_json")"
    if [[ "$operation_type" != "2" || "$enable_control" != "1" ]]; then
      stop_all
      die "Se perdió habilitación esperando el grip; STOP enviado."
    fi
    sleep 0.1
  done
  if [[ -z "$grip_true_line" ]]; then
    stop_all
    die "No se detectó el grip $side_es dentro de 8 s; STOP enviado."
  fi

  info "${side_es_upper}_GRIP_CONFIRMED=1"
  info "PHYSICAL_MOTION_WINDOW=5s_MAX"
  local motion_start=$SECONDS
  local motion_deadline=$((motion_start + 5))
  local released=0
  next_progress=$motion_start
  while ((SECONDS < motion_deadline)); do
    if grip_state_seen_since "$grip_true_line" "$opposite_label" true; then
      stop_all
      die "Se pulsó el grip opuesto durante el gesto; STOP enviado."
    fi
    if grip_state_seen_since "$((grip_true_line + 1))" "$hand_label" false; then
      released=1
      break
    fi
    detect_json="$(backend_detect_json)"
    assert_runtime_links "$detect_json" "durante el gesto del brazo $side_es"
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    enable_control="$(jq -r '.content.enable_control' <<<"$detect_json")"
    if [[ "$operation_type" != "2" || "$enable_control" != "1" ]]; then
      stop_all
      die "Se perdió habilitación durante el gesto; STOP enviado."
    fi
    if ((SECONDS >= next_progress)); then
      info "MOTION_LIVE=1 REMAINING=$((motion_deadline - SECONDS))s; SUELTE GRIP PARA STOP"
      next_progress=$((SECONDS + 1))
    fi
    sleep 0.1
  done

  stop_all
  if [[ "$released" != "1" ]]; then
    die "El grip no se soltó dentro de 5 s; se forzó STOP. Suéltelo físicamente ahora."
  fi

  local stopped_json stopped_operation stopped_enable
  stopped_json="$(backend_detect_json)"
  stopped_operation="$(jq -r '.content.operation_type' <<<"$stopped_json")"
  stopped_enable="$(jq -r '.content.enable_control' <<<"$stopped_json")"
  if [[ "$stopped_operation" != "1" || "$stopped_enable" != "0" ]]; then
    die "STOP no dejó el backend desarmado (operation_type=$stopped_operation, enable_control=$stopped_enable)."
  fi

  info "ARM_MOTION_TEST_COMPLETED=$side"
  info "GRIP_RELEASE_CONFIRMED=1"
  info "TELEOPERATION_STOPPED_AFTER_MOTION=1"
  cat <<'EOF'

PRUEBA TERMINADA Y PC DESARMADO
No repita con el otro brazo ni envíe home desde una postura dudosa. Compruebe
visualmente la postura final y comunique si el brazo siguió el gesto, cuánto se
movió y si apareció voz, resistencia, vibración o alarma.
EOF
}

summarize_all_controls() {
  local first_line="$1"
  FIRST_LINE="$first_line" BACKEND_LOG="$backend_log" python3 - <<'PY'
import json
import os

first_line = int(os.environ["FIRST_LINE"])
path = os.environ["BACKEND_LOG"]
sides = {
    "Left": {"previous": {}, "edges": {}, "axis_x": 0.0, "axis_y": 0.0,
             "trigger_value": 0.0, "squeeze_value": 0.0},
    "Right": {"previous": {}, "edges": {}, "axis_x": 0.0, "axis_y": 0.0,
              "trigger_value": 0.0, "squeeze_value": 0.0},
}
boolean_fields = ("trigger", "squeeze", "thumbstick", "a_button", "b_button")

with open(path, "r", encoding="utf-8", errors="replace") as handle:
    for number, line in enumerate(handle, 1):
        if number < first_line:
            continue
        side = next((name for name in sides if f"{name} hand state:" in line), None)
        if side is None:
            continue
        try:
            payload = json.loads(line[line.index("{"):])
        except (ValueError, json.JSONDecodeError):
            continue
        state = sides[side]
        for field in boolean_fields:
            value = bool(payload.get(field, False))
            previous = bool(state["previous"].get(field, False))
            if value and not previous:
                state["edges"][field] = state["edges"].get(field, 0) + 1
            state["previous"][field] = value
        axes = payload.get("thumbstick_value", [0.0, 0.0])
        if isinstance(axes, list) and len(axes) >= 2:
            state["axis_x"] = max(state["axis_x"], abs(float(axes[0])))
            state["axis_y"] = max(state["axis_y"], abs(float(axes[1])))
        state["trigger_value"] = max(
            state["trigger_value"], abs(float(payload.get("trigger_value", 0.0)))
        )
        state["squeeze_value"] = max(
            state["squeeze_value"], abs(float(payload.get("squeeze_value", 0.0)))
        )

left = sides["Left"]
right = sides["Right"]
edges = lambda state, field: int(state["edges"].get(field, 0))
observed = {
    "ENABLE_LEFT_TRIGGER": edges(left, "b_button") >= 1,
    "X_INPUT_EVEN_PAIR": edges(left, "a_button") >= 2 and edges(left, "a_button") % 2 == 0,
    "A_UPPER_BODY_RESET": edges(right, "a_button") >= 1,
    "B_INPUT_EVEN_PAIR": edges(right, "b_button") >= 2 and edges(right, "b_button") % 2 == 0,
    "LEFT_GRIP": edges(left, "squeeze") >= 1 or left["squeeze_value"] >= 0.5,
    "RIGHT_GRIP": edges(right, "squeeze") >= 1 or right["squeeze_value"] >= 0.5,
    "RIGHT_TRIGGER": edges(right, "trigger") >= 1 or right["trigger_value"] >= 0.5,
    "LEFT_JOYSTICK_XY": left["axis_x"] >= 0.25 and left["axis_y"] >= 0.25,
    "RIGHT_JOYSTICK_XY": right["axis_x"] >= 0.25 and right["axis_y"] >= 0.25,
    "LEFT_FORCE_CLICK_EVEN_PAIR": edges(left, "thumbstick") >= 2 and edges(left, "thumbstick") % 2 == 0,
    "RIGHT_FORCE_CLICK_EVEN_PAIR": edges(right, "thumbstick") >= 2 and edges(right, "thumbstick") % 2 == 0,
}
for name, value in observed.items():
    print(f"CONTROL_{name}={int(value)}")
print(f"CONTROL_X_EDGES={edges(left, 'a_button')}")
print(f"CONTROL_B_EDGES={edges(right, 'b_button')}")
print(f"CONTROL_LEFT_FORCE_CLICK_EDGES={edges(left, 'thumbstick')}")
print(f"CONTROL_RIGHT_FORCE_CLICK_EDGES={edges(right, 'thumbstick')}")
print(f"CONTROL_LEFT_JOYSTICK_MAX={left['axis_x']:.3f},{left['axis_y']:.3f}")
print(f"CONTROL_RIGHT_JOYSTICK_MAX={right['axis_x']:.3f},{right['axis_y']:.3f}")
print(f"ALL_REQUIRED_CONTROLLER_INPUTS_OBSERVED={int(all(observed.values()))}")
print("CONTROL_LEFT_TRIGGER_NOTE=legacy-5.3-workaround-disabled-on-4.7")
print("CONTROL_EFFECTS_MACHINE_VERIFIED=0")
print("FINAL_STATIONARY_MODE_MACHINE_VERIFIED=0")
PY
}

run_all_controls_test() {
  require_official_enable_protocol_validation
  [[ "$all_controls_seconds" =~ ^[0-9]+$ ]] ||
    die "PICO_ALL_CONTROLS_SECONDS debe ser un entero entre 120 y 180."
  ((all_controls_seconds >= 120 && all_controls_seconds <= 180)) ||
    die "PICO_ALL_CONTROLS_SECONDS debe estar entre 120 y 180; recibido $all_controls_seconds."
  [[ -t 0 && -t 1 ]] ||
    die "La prueba integral exige un terminal interactivo local."

  check_pc
  if systemctl --user is-active --quiet "$ui_unit"; then
    die "$ui_unit está activo; ejecute --stop para conservar un solo cliente."
  fi

  local confirmation_expected
  confirmation_expected="PROBAR TODOS LOS CONTROLES ${all_controls_seconds} SEGUNDOS EN ZONA DESPEJADA"
  cat <<EOF

TELEOPERACIÓN FÍSICA INTEGRAL — ${all_controls_seconds} SEGUNDOS ACTIVOS

Este modo permite brazos, cintura, elevador, cabeza y chasis. Antes de
continuar confirme AHORA:

- abrazaderas firmes, vacías y robot visualmente en home;
- cargador desconectado, ambos paros liberados y batería suficiente;
- envolvente completa de brazos y recorrido 360° del chasis despejados;
- suelo llano, ruedas preparadas para movimiento y velocidad mínima;
- una persona con acceso inmediato al paro y otra atendiendo el terminal;
- web en 遥操模式, un solo cliente y PICO en Head + Controllers / Working;
- no hay caja, mesa, cable USB ni persona dentro de ninguna trayectoria.

Habrá 60 s neutros y luego ${all_controls_seconds} s de control. El STOP es
automático al terminar, al pulsar Ctrl+C, al perder enable o al actuar el
watchdog. El script no elimina colisiones, límites, paros ni watchdog.

Escriba exactamente: $confirmation_expected
EOF
  local confirmation
  read -r confirmation
  [[ "$confirmation" == "$confirmation_expected" ]] ||
    die "Confirmación incorrecta; no se inició la publicación."

  cat <<'EOF'

PREPARACIÓN INMEDIATA
Este gate legado no se ejecuta con 4.7.0 hasta validar el botón Y oficial y
una señal observable de habilitación.
EOF
  read -r _
  start_pico_camera
  check_robot_teleop_safety

  local start_line
  start_line="$(wc -l < "$backend_log")"
  progress "TODOS: enviando START local con arm_type=clamp"
  send_local_message '{"type":"collect","content":{"arm_type":"clamp","operation_type":2}}'

  local deadline=$((SECONDS + 8))
  progress "TODOS: esperando confirmación arm=clamp (máximo 8 s)"
  until tail -n "+$((start_line + 1))" "$backend_log" | grep -q 'Arm type is: clamp'; do
    if tail -n "+$((start_line + 1))" "$backend_log" | grep -q 'Arm type is: gripper'; then
      stop_all
      die "El backend seleccionó gripper; STOP enviado."
    fi
    ((SECONDS < deadline)) || { stop_all; die "No se confirmó arm_type=clamp; STOP enviado."; }
    sleep 0.25
  done

  info "ARM_TYPE_CONFIRMED=clamp"
  check_controller_inputs_neutral "$((start_line + 1))"
  printf '\a\n'
  info "========== TOQUE AHORA: GATILLO IZQUIERDO UNA VEZ Y SUÉLTELO =========="
  info "EL BACKEND PUBLICA SÓLO EL FLANCO; NO VUELVA A TOCARLO"

  local enabled=0 detect_json operation_type enable_control
  local enable_deadline=$((SECONDS + 8))
  while ((SECONDS < enable_deadline)); do
    detect_json="$(backend_detect_json)"
    assert_runtime_links "$detect_json" "antes de habilitar la prueba integral"
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    enable_control="$(jq -r '.content.enable_control' <<<"$detect_json")"
    if [[ "$operation_type" == "2" && "$enable_control" == "1" ]]; then
      enabled=1
      break
    fi
    if [[ "$operation_type" == "1" ]]; then
      stop_all
      die "El robot cerró la sesión antes de habilitar; STOP confirmado."
    fi
    sleep 0.25
  done
  if [[ "$enabled" != "1" ]]; then
    stop_all
    die "No se detectó enable_control=1; STOP enviado."
  fi
  info "ENABLE_CONTROL_CONFIRMED=1"
  local release_line
  release_line="$(wc -l < "$backend_log")"
  if ! wait_for_left_trigger_release "$((release_line + 1))"; then
    stop_all
    die "El gatillo izquierdo no quedó liberado dentro de 3 s; STOP enviado."
  fi
  info "LEFT_TRIGGER_RELEASE_CONFIRMED=1"

  info "STABILITY_WINDOW=60s; TODO NEUTRO"
  local stability_start=$SECONDS
  local stability_deadline=$((stability_start + 60))
  local next_progress=$stability_start
  while ((SECONDS < stability_deadline)); do
    if awk -v first="$((start_line + 1))" '
      NR >= first && /No heartbeat for .+ seconds, stoping operation/ {found=1; exit}
      END {exit !found}
    ' "$backend_log"; then
      stop_all
      die "El watchdog cerró el enlace durante estabilidad; STOP enviado."
    fi
    if grip_state_seen_since "$((start_line + 1))" "Left" true ||
       grip_state_seen_since "$((start_line + 1))" "Right" true; then
      stop_all
      die "Se pulsó un grip durante la fase neutra; STOP enviado."
    fi
    detect_json="$(backend_detect_json)"
    assert_runtime_links "$detect_json" "durante la estabilidad integral"
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    enable_control="$(jq -r '.content.enable_control' <<<"$detect_json")"
    if [[ "$operation_type" != "2" || "$enable_control" != "1" ]]; then
      stop_all
      die "Se perdió habilitación durante estabilidad; STOP enviado."
    fi
    if ((SECONDS >= next_progress)); then
      info "STABILITY_LIVE=1 REMAINING=$((stability_deadline - SECONDS))s"
      next_progress=$((SECONDS + 5))
    fi
    sleep 1
  done
  info "STABILITY_COMPLETED=60s"

  printf '\a\n'
  cat <<EOF

========== VENTANA INTEGRAL ACTIVA: ${all_controls_seconds} s ==========

Puede probar los comandos documentados, con movimientos lentos y pequeños:

- cabeza: giro/inclinación suave;
- grips izquierdo/derecho: seguimiento de cada brazo y cintura;
- joystick izquierdo: cintura en modo en sitio; avance/retroceso en móvil;
- joystick derecho: elevador en sitio; giro del chasis en móvil;
- X: entrar en modo móvil y pulsarlo de nuevo para VOLVER A MODO EN SITIO;
- A: reset de brazos/cintura sólo con toda su trayectoria despejada;
- B: iniciar captura y pulsarlo de nuevo para CERRAR la captura;
- trigger derecho: comando de mano (sin actuador útil con abrazaderas);
- click de cada joystick: conmuta protección de fuerza; si se prueba, hacer
  dos clicks completos y separados para RESTAURAR el estado inicial.

El mapeo legado del gatillo izquierdo está desactivado en 4.7.0. Antes de los últimos 30 s deje
X en modo en sitio, B cerrado, clicks restaurados y todos los mandos neutros.
EOF

  local control_start=$SECONDS
  local control_deadline=$((control_start + all_controls_seconds))
  local return_deadline=$((control_deadline - 30))
  local neutral_deadline=$((control_deadline - 10))
  local return_warned=0 neutral_warned=0
  next_progress=$control_start
  while ((SECONDS < control_deadline)); do
    if awk -v first="$((start_line + 1))" '
      NR >= first && /No heartbeat for .+ seconds, stoping operation/ {found=1; exit}
      END {exit !found}
    ' "$backend_log"; then
      stop_all
      die "El watchdog cerró la ventana integral; STOP enviado."
    fi
    detect_json="$(backend_detect_json)"
    assert_runtime_links "$detect_json" "durante la ventana integral"
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    enable_control="$(jq -r '.content.enable_control' <<<"$detect_json")"
    if [[ "$operation_type" != "2" || "$enable_control" != "1" ]]; then
      stop_all
      die "Se perdió habilitación durante la ventana integral; STOP enviado."
    fi
    if ((SECONDS >= return_deadline && return_warned == 0)); then
      printf '\a\n'
      info "REGRESO OBLIGATORIO: X A MODO EN SITIO; B CERRADO; CLICKS RESTAURADOS"
      return_warned=1
    fi
    if ((SECONDS >= neutral_deadline && neutral_warned == 0)); then
      printf '\a\n'
      info "FINAL EN 10 s: TODO NEUTRO Y SUELTO; MODO EN SITIO"
      neutral_warned=1
    fi
    if ((SECONDS >= next_progress)); then
      info "ALL_CONTROLS_LIVE=1 ELAPSED=$((SECONDS - control_start))s REMAINING=$((control_deadline - SECONDS))s"
      next_progress=$((SECONDS + 5))
    fi
    sleep 1
  done

  local summary
  summary="$(summarize_all_controls "$((start_line + 1))")"
  stop_all

  local stopped_json stopped_operation stopped_enable
  stopped_json="$(backend_detect_json)"
  stopped_operation="$(jq -r '.content.operation_type' <<<"$stopped_json")"
  stopped_enable="$(jq -r '.content.enable_control' <<<"$stopped_json")"
  if [[ "$stopped_operation" != "1" || "$stopped_enable" != "0" ]]; then
    die "STOP no dejó el backend desarmado (operation_type=$stopped_operation, enable_control=$stopped_enable)."
  fi

  printf '%s\n' "$summary"
  info "ALL_CONTROLS_WINDOW_COMPLETED=${all_controls_seconds}s"
  info "TELEOPERATION_STOPPED_AFTER_ALL_CONTROLS=1"
  cat <<'EOF'

PRUEBA INTEGRAL TERMINADA Y PC DESARMADO
No repita controles marcados con 0 sin revisar antes el resumen, la postura,
el modo final y los logs. Los pares de entradas no demuestran por sí solos el
efecto final. Verifique visualmente que el robot está inmóvil y en modo en
sitio; use la recuperación oficial antes de home si la postura no es conocida.
EOF
}

run_gate() {
  require_official_enable_protocol_validation
  [[ -t 0 && -t 1 ]] ||
    die "El gate requiere un terminal interactivo local; no lo ejecute mediante pipe o job en segundo plano."
  check_pc
  if systemctl --user is-active --quiet "$ui_unit"; then
    die "$ui_unit está activo; ejecute --stop antes del gate para evitar dos clientes de control."
  fi

  cat <<'EOF'

CONFIRMACIÓN FÍSICA OBLIGATORIA
El cargador debe estar desconectado; PICO y Ethernet conectados; abrazaderas
vacías; el robot debe haber partido de home y permanecer en la postura de
inicialización esperada de TeleopMode; controladores neutros; grip y gatillos
libres; nadie tocando el robot; toda la envolvente despejada y paro físico
preparado. La web 192.168.11.3 debe mostrar 遥操模式 (Remote control mode)
arriba.

El backend 4.7.0 conserva su binario y watchdog oficiales sin modificaciones.
Este gate legado permanece bloqueado hasta validar su protocolo de enable.

Escriba exactamente TELEOPERACION SEGURA Y MODO REMOTO para armar el flujo del PC:
EOF
  read -r confirmation
  [[ "$confirmation" == "TELEOPERACION SEGURA Y MODO REMOTO" ]] ||
    die "Confirmación incorrecta; no se inició la publicación."

  cat <<'EOF'

PREPARACIÓN INMEDIATA
Mantenga ambos controladores neutros y el gatillo izquierdo suelto. Pulse
Enter sólo cuando el operador del PICO y la persona del terminal estén listos.
El PC armará el publicador y, cuando esté preparado, emitirá una campana y
mostrará TOQUE AHORA. En ese instante apriete una sola vez el gatillo
izquierdo y suéltelo. El backend publicará sólo el flanco inicial y el script
comprobará la liberación; no vuelva a pulsarlo durante el gate.
EOF
  read -r _

  start_pico_camera

  local start_line
  start_line="$(wc -l < "$backend_log")"
  progress "GATE: enviando START local con arm_type=clamp"
  send_local_message '{"type":"collect","content":{"arm_type":"clamp","operation_type":2}}'

  local deadline=$((SECONDS + 8))
  progress "GATE: esperando confirmación arm=clamp (máximo 8 s)"
  until tail -n "+$((start_line + 1))" "$backend_log" | grep -q 'Arm type is: clamp'; do
    if tail -n "+$((start_line + 1))" "$backend_log" | grep -q 'Arm type is: gripper'; then
      stop_all
      die "El backend volvió a seleccionar gripper; publicación detenida."
    fi
    ((SECONDS < deadline)) || { stop_all; die "No se confirmó arm_type=clamp."; }
    sleep 0.25
  done

  info "ARM_TYPE_CONFIRMED=clamp"
  check_controller_inputs_neutral "$((start_line + 1))"
  info "PUBLISHER_ARMED=1"
  info "ENABLE_CONTROL_BEFORE_TRIGGER=0"
  printf '\a\n'
  info "========== TOQUE AHORA: GATILLO IZQUIERDO UNA VEZ Y SUÉLTELO =========="
  info "TAP_LEFT_TRIGGER_ONCE_NOW=1"

  local enabled=0 detect_json operation_type enable_control
  local enable_deadline=$((SECONDS + 8))
  while ((SECONDS < enable_deadline)); do
    detect_json="$(backend_detect_json)"
    assert_runtime_links "$detect_json" "antes de habilitar el gate"
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    enable_control="$(jq -r '.content.enable_control' <<<"$detect_json")"
    if [[ "$operation_type" == "2" && "$enable_control" == "1" ]]; then
      enabled=1
      break
    fi
    if [[ "$operation_type" == "1" ]]; then
      stop_all
      die "El robot cerró la sesión antes de detectar la habilitación."
    fi
    sleep 0.25
  done
  if [[ "$enabled" != "1" ]]; then
    stop_all
    die "No se detectó una nueva pulsación del gatillo/enable_control=1 dentro de 8 s."
  fi
  info "ENABLE_CONTROL_CONFIRMED=1"
  local release_line
  release_line="$(wc -l < "$backend_log")"
  if ! wait_for_left_trigger_release "$((release_line + 1))"; then
    stop_all
    die "El gatillo izquierdo no quedó liberado dentro de 3 s; STOP enviado."
  fi
  info "LEFT_TRIGGER_RELEASE_CONFIRMED=1"

  info "MONITORING_DIAGNOSTIC_WINDOW=60s"
  local monitor_start=$SECONDS
  local monitor_deadline=$((monitor_start + 60))
  local next_progress=$monitor_start
  while ((SECONDS < monitor_deadline)); do
    if tail -n "+$((start_line + 1))" "$backend_log" |
      grep -qE 'No heartbeat for .+ seconds, stoping operation'; then
      stop_all
      die "El watchdog no recibió heartbeat; STOP enviado y UI cerrada."
    fi
    detect_json="$(backend_detect_json)"
    assert_runtime_links "$detect_json" "durante el gate"
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    enable_control="$(jq -r '.content.enable_control' <<<"$detect_json")"
    if [[ "$operation_type" != "2" || "$enable_control" != "1" ]]; then
      stop_all
      die "La sesión perdió habilitación (operation_type=$operation_type, enable_control=$enable_control)."
    fi
    if ((SECONDS >= next_progress)); then
      info "GATE_LIVE=1 ELAPSED=$((SECONDS - monitor_start))s REMAINING=$((monitor_deadline - SECONDS))s"
      next_progress=$((SECONDS + 5))
    fi
    sleep 1
  done

  local response
  response="$(send_local_message '{"type":"detect","content":{}}' || true)"
  printf '%s\n' "$response"
  grep -q '"operation_type":2' <<<"$response" || {
    stop_all
    die "La operación no permaneció activa durante 60 s."
  }

  # El gate sólo demuestra estabilidad sin movimiento útil. Cerrar siempre la
  # sesión antes de anunciar el resultado evita dejar el publicador armado
  # entre el resultado del script y la siguiente decisión.
  stop_all
  local stopped_json stopped_operation stopped_enable
  stopped_json="$(backend_detect_json)"
  stopped_operation="$(jq -r '.content.operation_type' <<<"$stopped_json")"
  stopped_enable="$(jq -r '.content.enable_control' <<<"$stopped_json")"
  if [[ "$stopped_operation" != "1" || "$stopped_enable" != "0" ]]; then
    die "STOP no dejó el backend desarmado (operation_type=$stopped_operation, enable_control=$stopped_enable)."
  fi
  info "DIAGNOSTIC_WINDOW_COMPLETED=60s"
  info "HEARTBEAT_VALIDATED=0"
  info "HEARTBEAT_WATCHDOG=vendor-default-unmodified"
  info "WATCHDOG_TRIP=0"
  info "TELEOPERATION_STOPPED_AFTER_GATE=1"
  info "Gatillo liberable: la teleoperación queda desarmada tras el gate."
}

mode="${1:---check}"
case "$mode" in
  --check)
    check_pc
    ;;
  --check-arms-only)
    check_robot_arms_only_loaded
    ;;
  --check-reload-ready)
    check_robot_teleop_safety
    info "MOTION_RELOAD_READY_CHECK_OK=1; no se cambió de modo ni se envió movimiento."
    ;;
  --check-motion-ready)
    check_pc
    check_robot_teleop_safety
    info "MOTION_READY_CHECK_OK=1; no se envió START ni se movió el robot."
    ;;
  --teleoperate)
    run_official_arm_teleop
    ;;
  --open-ui)
    open_ui
    ;;
  --gate-local|--run)
    trap 'gate_error "$?" "$LINENO" "$BASH_COMMAND"' ERR
    trap 'abort_gate INT' INT
    trap 'abort_gate TERM' TERM
    run_gate
    trap - ERR INT TERM
    ;;
  --move-left-arm|--move-right-arm)
    trap 'gate_error "$?" "$LINENO" "$BASH_COMMAND"' ERR
    trap 'abort_gate INT' INT
    trap 'abort_gate TERM' TERM
    if [[ "$mode" == "--move-left-arm" ]]; then
      run_arm_motion_test left
    else
      run_arm_motion_test right
    fi
    trap - ERR INT TERM
    ;;
  --all-controls)
    trap 'gate_error "$?" "$LINENO" "$BASH_COMMAND"' ERR
    trap 'abort_gate INT' INT
    trap 'abort_gate TERM' TERM
    run_all_controls_test
    trap - ERR INT TERM
    ;;
  --stop)
    stop_all
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
