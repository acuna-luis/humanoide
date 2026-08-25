#!/usr/bin/env bash

set -Eeuo pipefail

# Recoge la caja usando el flujo visual ya validado, recorre test_route_01
# según el perfil completo o corto, regresa a la pose exacta de recogida,
# deposita la caja y termina mediante cruzr/home.

readonly MAP_NAME="test_route_01"
readonly ROBOT_USER="walker"
readonly WIFI_GATEWAY="192.168.42.2"
readonly VISION_HOST="192.168.11.3"
readonly MOTION_HOST="192.168.11.2"
readonly DEFAULT_PASSWORD="aa"
readonly NAV_CONTAINER="walker-nav.nav_taskmanager-1"
readonly FREEPNC_CONTAINER="walker-nav.freepnc_task-1"
readonly ROS_CONTAINER="walker-ros.ros2-1"
readonly POSE_TOPIC="/mc/odom"
readonly MAP_POSE_TOPIC="/nav/robot_pose"
readonly CARRY_SCRIPT_NAME="cruzr_blue_workbin_carry_back.sh"
readonly GRASP_SCRIPT_NAME="cruzr_blue_workbin_cycle.sh"
readonly RECOVERY_SCRIPT_NAME="cruzr_recover_to_home.sh"
readonly ROUTE_ACTION="/vnav/task/command"
readonly ROUTE_TYPE="unav_task_msgs/action/Task"
readonly START_POSITION_TOLERANCE="0.45"
readonly START_YAW_TOLERANCE="0.35"
readonly STAGING_POSITION_TOLERANCE="0.12"
readonly STAGING_YAW_TOLERANCE="0.14"
readonly MIN_BATTERY_SOC="30.0"
readonly RETURN_MIN_BATTERY_SOC="25.0"

# Una ruta completa puede necesitar varios minutos, pero los orquestadores que
# conocen la distancia pueden reducir este límite mediante el entorno.  El
# valor se valida antes de enviar cualquier objetivo para evitar que un error
# permanente del planificador quede oculto tras un "context canceled" tardío.
NAVIGATION_TIMEOUT_SECONDS="${CRUZR_NAV_TIMEOUT_SECONDS:-420}"
[[ "$NAVIGATION_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] && \
  ((NAVIGATION_TIMEOUT_SECONDS >= 30 && NAVIGATION_TIMEOUT_SECONDS <= 900)) || {
  printf 'ERROR: CRUZR_NAV_TIMEOUT_SECONDS debe estar entre 30 y 900.\n' >&2
  exit 1
}
readonly NAVIGATION_TIMEOUT_SECONDS

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
readonly GRASP_SCRIPT="$SCRIPT_DIR/$GRASP_SCRIPT_NAME"
readonly RECOVERY_SCRIPT="$SCRIPT_DIR/$RECOVERY_SCRIPT_NAME"

MODE="run"
ROUTE_PROFILE="full"
YES=0
FAST=0
FLUID_MODE="${CRUZR_FLUID_MODE:-0}"
ROUTE_CONTEXT="${CRUZR_ROUTE_CONTEXT:-map-round-trip}"
[[ "$ROUTE_CONTEXT" == "map-round-trip" || "$ROUTE_CONTEXT" == "table-transfer" ]] || {
  printf 'ERROR: CRUZR_ROUTE_CONTEXT debe ser map-round-trip o table-transfer.\n' >&2
  exit 2
}
RESUME_STAGING_MAP_POSE=""
RESUME_APPROACH_DISTANCE=""
NAVIGATE_WAYPOINT=""
NAVIGATE_BACKOFF_DISTANCE=""
CONNECTION_MODE=""
CONTROL_INTERFACE=""
VISION_SSH_HOST=""
TABLE_POSE=""
TABLE_MAP_POSE=""
TABLE_STAGING_MAP_POSE=""
TABLE_STAGING_ODOM_POSE=""
TABLE_APPROACH_DISTANCE=""
START_POSE=""

usage() {
  cat <<'EOF'
Uso:
  ./scripts/cruzr_blue_workbin_map_route.sh --check [--fast]
  ./scripts/cruzr_blue_workbin_map_route.sh --run [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_map_route.sh --run --short [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_map_route.sh --navigate-waypoint PUNTO \
    [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_map_route.sh --navigate-waypoint-backoff PUNTO METROS \
    [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_map_route.sh --resume-to-table \
    --staging-map-pose "X Y YAW" --approach-distance METROS [--yes] [--fast]

Flujo completo de --run:
  1. Localiza, centra, sujeta y eleva la caja azul.
  2. Guarda la pose de la mesa en mapa y odometría.
  3. Se separa 0,50 m y guarda esa pose despejada de aproximación.
  4. Va a START y navega: PASO1 -> PASO2 -> PASO 3 -> PASO4 -> FINISH.
  5. Regresa: PASO4 -> PASO 3 -> PASO2 -> PASO1 -> START.
  6. Navega de START a la pose despejada frente a la mesa, recupera la pose
     exacta mediante odometría, deposita la caja y ejecuta home.

Flujo de --run --short:
  caja -> START -> PASO1 -> mesa -> depósito -> home.
  Desde PASO1 regresa directamente a la mesa, sin pasar otra vez por START.

La navegación usa la acción interna /vnav/task/command. No depende de que el
navegador web permanezca abierto. Los puntos se leen del mapa instalado en el
robot; el script no contiene coordenadas copiadas ni modifica el mapa.

Opciones:
  --check  Activa test_route_01 si hace falta y comprueba mapa, localización,
           navegación y scripts. No mueve físicamente el robot.
  --run    Ejecuta el ciclo completo; es el modo predeterminado.
  --short  Usa START -> PASO1 y desde PASO1 regresa directamente
           a la mesa; no vuelve por los puntos del mapa.
  --resume-to-table
           No repite el agarre. Lleva una caja ya sujeta a la premesa
           indicada, la deposita y termina en home.
  --navigate-waypoint PUNTO
           Sin mover los brazos, sincroniza automáticamente el mapa instalado,
           comprueba seguridad y navega al waypoint indicado.
  --navigate-waypoint-backoff PUNTO METROS
           Navega a una pose libre situada METROS detrás del waypoint según
           su orientación. Evita usar como objetivo el área inflada de una
           mesa; no realiza la aproximación final ni mueve los brazos.
  --staging-map-pose "X Y YAW"
           Pose de premesa registrada por la ejecución interrumpida.
  --approach-distance METROS
           Avance corto desde la premesa hasta el apoyo original.
  --yes    Omite la confirmación única inicial.
  --fast   Omite diagnósticos repetidos, manteniendo las comprobaciones críticas.
  --help   Muestra esta ayuda.

Condiciones obligatorias:
  - hotspot Wi-Fi del robot activo; Ethernet y cargador desconectados;
  - robot localizado en test_route_01 y situado frente a la caja de la mesa;
  - recorrido elegido y regreso directo a la mesa autorizados y supervisados;
  - caja vacía, rígida y compatible con el agarre ya probado;
  - pasillos, giros, START y mesa despejados para la anchura total de la caja;
  - paro de emergencia en manos de una segunda persona durante todo el ciclo.
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
    --check|--run)
      MODE="${1#--}"
      ;;
    --resume-to-table)
      MODE="resume-to-table"
      ROUTE_PROFILE="short"
      ;;
    --navigate-waypoint)
      (($# >= 2)) || die "--navigate-waypoint necesita el nombre de un punto"
      MODE="navigate-waypoint"
      NAVIGATE_WAYPOINT="$2"
      shift
      ;;
    --navigate-waypoint-backoff)
      (($# >= 3)) || die "--navigate-waypoint-backoff necesita PUNTO y METROS"
      MODE="navigate-waypoint-backoff"
      NAVIGATE_WAYPOINT="$2"
      NAVIGATE_BACKOFF_DISTANCE="$3"
      shift 2
      ;;
    --yes)
      YES=1
      ;;
    --short)
      ROUTE_PROFILE="short"
      ;;
    --staging-map-pose)
      (($# >= 2)) || die "--staging-map-pose necesita una pose entre comillas: X Y YAW"
      RESUME_STAGING_MAP_POSE="$2"
      shift
      ;;
    --approach-distance)
      (($# >= 2)) || die "--approach-distance necesita una distancia en metros"
      RESUME_APPROACH_DISTANCE="$2"
      shift
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
  for command_name in ssh setsid nc ip readlink flock python3 base64; do
    command -v "$command_name" >/dev/null 2>&1 || \
      die "Falta el comando local '$command_name'."
  done
  for script in "$CARRY_SCRIPT" "$GRASP_SCRIPT" "$RECOVERY_SCRIPT"; do
    [[ -x "$script" ]] || die "No existe o no es ejecutable: $script"
  done
}

route_interface() {
  ip -o route get "$1" 2>/dev/null | \
    awk '{for (i=1; i<=NF; i++) if ($i=="dev") {print $(i+1); exit}}'
}

is_wireless_interface() {
  [[ -n "$1" && -d "/sys/class/net/$1/wireless" ]]
}

select_connection() {
  if nc -z -w2 "$WIFI_GATEWAY" 22 >/dev/null 2>&1; then
    CONTROL_INTERFACE="$(route_interface "$WIFI_GATEWAY")"
    if is_wireless_interface "$CONTROL_INTERFACE"; then
      CONNECTION_MODE="Wi-Fi mediante vision"
      VISION_SSH_HOST="$WIFI_GATEWAY"
      info "Conexión: $CONNECTION_MODE ($CONTROL_INTERFACE)"
      return
    fi
  fi

  if nc -z -w2 "$VISION_HOST" 22 >/dev/null 2>&1; then
    CONTROL_INTERFACE="$(route_interface "$VISION_HOST")"
    VISION_SSH_HOST="$VISION_HOST"
    CONNECTION_MODE="directa a vision"
    is_wireless_interface "$CONTROL_INTERFACE" && CONNECTION_MODE="Wi-Fi directa a vision"
    info "Conexión: $CONNECTION_MODE ($CONTROL_INTERFACE)"
    return
  fi
  die "No se alcanza vision por Wi-Fi."
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
    -o ServerAliveInterval=5 \
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

grasp_args() {
  local -a args=("$@")
  ((FAST == 1)) && args+=(--fast)
  "$GRASP_SCRIPT" "${args[@]}"
}

read_odom_pose() {
  local output
  output="$(ssh_vision bash -s -- "$ROS_CONTAINER" "$POSE_TOPIC" <<'REMOTE'
set -Eeuo pipefail
docker exec -i "$1" bash -s -- "$2" <<'INNER'
set -Eeo pipefail
set +u
source /opt/ros/humble/setup.bash
set -u
export ROS2CLI_DISABLE_DAEMON=1
timeout 8 ros2 topic echo --once "$1" --field pose.pose
INNER
REMOTE
)"
  python3 -c '
import math, re, sys
text=sys.stdin.read()
p=re.search(r"position:\s+x:\s*([-+0-9.eE]+)\s+y:\s*([-+0-9.eE]+)",text)
q=re.search(r"orientation:\s+x:\s*[-+0-9.eE]+\s+y:\s*[-+0-9.eE]+\s+z:\s*([-+0-9.eE]+)\s+w:\s*([-+0-9.eE]+)",text)
if not p or not q: raise SystemExit("No se pudo analizar /mc/odom")
x,y=map(float,p.groups()); qz,qw=map(float,q.groups())
yaw=math.atan2(2*qw*qz,1-2*qz*qz)
print(f"{x:.9f} {y:.9f} {yaw:.9f}")
' <<<"$output"
}

read_map_localization_pose() {
  local output
  output="$(ssh_vision bash -s -- "$ROS_CONTAINER" "$MAP_POSE_TOPIC" <<'REMOTE'
set -Eeuo pipefail
docker exec -i "$1" bash -s -- "$2" <<'INNER'
set -Eeo pipefail
set +u
source /opt/ros/humble/setup.bash
set -u
export ROS2CLI_DISABLE_DAEMON=1
timeout 8 ros2 topic echo --once "$1" --field pose
INNER
REMOTE
)"
  python3 -c '
import math, re, sys
text=sys.stdin.read()
p=re.search(r"position:\s+x:\s*([-+0-9.eE]+)\s+y:\s*([-+0-9.eE]+)",text)
q=re.search(r"orientation:\s+x:\s*[-+0-9.eE]+\s+y:\s*[-+0-9.eE]+\s+z:\s*([-+0-9.eE]+)\s+w:\s*([-+0-9.eE]+)",text)
if not p or not q: raise SystemExit("No se pudo analizar /nav/robot_pose")
x,y=map(float,p.groups()); qz,qw=map(float,q.groups())
yaw=math.atan2(2*qw*qz,1-2*qz*qz)
print(f"{x:.9f} {y:.9f} {yaw:.9f}")
' <<<"$output"
}

capture_table_pose() {
  TABLE_POSE="$(read_odom_pose)"
  [[ -n "$TABLE_POSE" ]] || die "No se pudo guardar la pose de la mesa."
  TABLE_MAP_POSE="$(read_map_localization_pose)"
  [[ -n "$TABLE_MAP_POSE" ]] || die "No se pudo guardar la pose de mapa de la mesa."
  info "TABLE_ODOM_POSE=$TABLE_POSE"
  info "TABLE_MAP_POSE=$TABLE_MAP_POSE"
}

capture_table_staging_pose() {
  TABLE_STAGING_MAP_POSE="$(read_map_localization_pose)"
  [[ -n "$TABLE_STAGING_MAP_POSE" ]] || \
    die "No se pudo guardar la pose despejada frente a la mesa."
  TABLE_STAGING_ODOM_POSE="$(read_odom_pose)"
  [[ -n "$TABLE_STAGING_ODOM_POSE" ]] || \
    die "No se pudo medir mediante odometría la separación de la mesa."
  info "TABLE_STAGING_MAP_POSE=$TABLE_STAGING_MAP_POSE"
  info "TABLE_STAGING_ODOM_POSE=$TABLE_STAGING_ODOM_POSE"
  TABLE_APPROACH_DISTANCE="$(python3 - "$TABLE_POSE" "$TABLE_STAGING_ODOM_POSE" <<'PY'
import math, sys
table=tuple(map(float, sys.argv[1].split()))
staging=tuple(map(float, sys.argv[2].split()))
distance=math.hypot(table[0]-staging[0], table[1]-staging[1])
yaw=math.atan2(math.sin(table[2]-staging[2]), math.cos(table[2]-staging[2]))
if not 0.38 <= distance <= 0.65:
    raise SystemExit(f"Separación premesa inesperada: {distance:.3f} m")
if abs(yaw) > math.radians(8.0):
    raise SystemExit(f"Orientación premesa inesperada: {math.degrees(yaw):.1f} grados")
print(f"{distance:.6f}")
PY
)"
  info "TABLE_STAGING_OK distance=${TABLE_APPROACH_DISTANCE} m"
}

stop_navigation() {
  set +e
  ssh_vision bash -s -- "$NAV_CONTAINER" <<'REMOTE' >/dev/null 2>&1
set -Eeo pipefail
docker exec "$1" bash -lc 'source /opt/walker/setup.bash; timeout 8 rosa action send_goal /vnav/task/command unav_task_msgs/action/Task '\''{"command":"navigation_stop","arg_json":"{}"}'\''' >/dev/null 2>&1 || true
REMOTE
  set -e
}

navigation_failure_diagnostic() {
  local since_epoch="$1"
  local point="$2"
  local logs=""
  local current_pose=""

  set +e
  logs="$(ssh_vision docker logs --since "$since_epoch" "$FREEPNC_CONTAINER" 2>&1)"
  current_pose="$(read_map_localization_pose 2>/dev/null)"
  set -e

  # Quita únicamente códigos ANSI; se conservan los textos exactos del
  # planificador para que soporte pueda correlacionarlos con sus estados.
  logs="$(sed -r 's/\x1B\[[0-9;]*[mK]//g' <<<"$logs")"
  [[ -n "$current_pose" ]] && info "NAV_FAILURE_MAP_POSE=$current_pose"

  if grep -q 'LOCATE_LOST' <<<"$logs"; then
    info "NAV_FAILURE_CLASS=LOCALIZATION_LOST"
    return 0
  fi
  if grep -Eq 'GOAL_ON_DYNAMIC_OBSTACLE|GOAL_ONDYNAMICOBSTACLE|7214003' <<<"$logs"; then
    info "NAV_FAILURE_CLASS=DYNAMIC_OBSTACLE"
    info "NAV_FAILURE_DETAIL=goal_or_path_blocked_by_dynamic_costmap"
    return 0
  fi
  if grep -Eq 'START_ONOBSTACLE|7218011|起点有静态障碍物' <<<"$logs"; then
    info "NAV_FAILURE_CLASS=START_ON_STATIC_OBSTACLE"
    return 0
  fi
  if grep -Eq 'controller failed to compute velocity commands|failed to find a plan' <<<"$logs"; then
    info "NAV_FAILURE_CLASS=PLANNER_NO_PATH"
    return 0
  fi
  info "NAV_FAILURE_CLASS=UNKNOWN"
  info "NAV_FAILURE_POINT=$point"
}

ensure_map_active() {
  info "[MAPA] Comprobando si '$MAP_NAME' está activo..."
  ssh_vision bash -s -- "$NAV_CONTAINER" "$FREEPNC_CONTAINER" "$MAP_NAME" \
    "$ROUTE_ACTION" "$ROUTE_TYPE" <<'REMOTE'
set -Eeuo pipefail
nav_container="$1"
freepnc_container="$2"
map_name="$3"
route_action="$4"
route_type="$5"
map_dir="/etc/walker/map/$map_name"

[[ "$(hostname)" == "vision" ]] || {
  echo "MAP_PREPARE_ERROR: el host remoto no es vision" >&2
  exit 40
}
for container in "$nav_container" "$freepnc_container"; do
  [[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || {
    echo "MAP_PREPARE_ERROR: el contenedor '$container' no está activo" >&2
    exit 41
  }
done
[[ -r "$map_dir/umap/umap.json" && -r "$map_dir/user/task.json" ]] || {
  echo "MAP_PREPARE_ERROR: faltan los archivos de $map_name" >&2
  exit 42
}

nav_action() {
  local command="$1" arg_json="$2" timeout_seconds="${3:-45}" payload
  payload="$(python3 - "$command" "$arg_json" <<'PY'
import json, sys
json.loads(sys.argv[2])
print(json.dumps({"command":sys.argv[1],"arg_json":sys.argv[2]},separators=(",",":")))
PY
)"
  docker exec -i "$nav_container" bash -s -- \
    "$route_action" "$route_type" "$payload" "$timeout_seconds" <<'INNER'
set -Eeo pipefail
set +u
source /opt/walker/setup.bash
set -u
timeout "$4" rosa action send_goal "$1" "$2" "$3"
INNER
}

action_succeeded() {
  grep -q 'Goal accepted' <<<"$1" &&
    grep -q 'status=4' <<<"$1" &&
    ! grep -Eqi "(FAILED|FAILURE|ABORTED|'desc': 'ERROR')" <<<"$1"
}

map_output="$(nav_action get_map_name '{}')"
action_succeeded "$map_output" || {
  echo "$map_output"
  echo "MAP_PREPARE_ERROR: no se pudo consultar el mapa activo" >&2
  exit 43
}

map_fingerprint="$(
  sha256sum "$map_dir/umap/umap.json" "$map_dir/user/task.json" |
    sha256sum | awk '{print $1}'
)"
nav_instance="$(
  docker inspect --format '{{.Id}}|{{.State.StartedAt}}' \
    "$nav_container" "$freepnc_container" | sha256sum | awk '{print $1}'
)"
cache_key="$(printf '%s' "$map_name" | sha256sum | awk '{print $1}')"
runtime_cache="/tmp/cruzr_map_runtime_${cache_key}.state"
runtime_signature="${nav_instance}|${map_fingerprint}"
cached_signature="$(cat "$runtime_cache" 2>/dev/null || true)"
map_is_active=0
grep -Fq "\"map_name\" : \"$map_name\"" <<<"$map_output" && map_is_active=1

if ((map_is_active == 1)); then
  set +e
  state_output="$(nav_action check_state '{}' 8 2>&1)"
  state_status=$?
  set -e

  if ((state_status == 0)) && grep -q 'status=4' <<<"$state_output" && \
     grep -q 'FSM_WAITNAVIGATE' <<<"$state_output"; then
    cache_tmp="${runtime_cache}.$$"
    printf '%s\n' "$runtime_signature" >"$cache_tmp"
    mv -f -- "$cache_tmp" "$runtime_cache"
    echo "MAP_ALREADY_ACTIVE=$map_name"
    echo "MAP_FINGERPRINT=$map_fingerprint"
    echo "NAV_STATE=FSM_WAITNAVIGATE"
    exit 0
  fi

  if grep -q 'FSM_RELOCATING' <<<"$state_output"; then
    echo "$state_output"
    echo "MAP_LOCALIZATION_REQUIRED: el mapa está cargado, pero el robot sigue sin pose." >&2
    echo "Use Localización forzada en la interfaz web y marque la pose y orientación reales del robot." >&2
    exit 48
  fi
fi

if ((map_is_active == 1)); then
  echo "MAP_RELOAD=$map_name"
  if [[ -z "$cached_signature" ]]; then
    echo "MAP_SYNC_REASON=runtime-not-yet-verified"
  else
    echo "MAP_SYNC_REASON=map-files-or-navigation-runtime-changed"
  fi
elif grep -Eq '\"map_name\"[[:space:]]*:[[:space:]]*\"[^\"]+\"' <<<"$map_output"; then
  previous_map="$(sed -n 's/.*\"map_name\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p' <<<"$map_output" | head -n1)"
  echo "MAP_SWITCH=$previous_map->$map_name"
else
  echo "MAP_NOT_ACTIVE: cargando $map_name"
fi

map_arg="$(python3 - "$map_name" <<'PY'
import json, sys
print(json.dumps({"map_name":sys.argv[1]},separators=(",",":")))
PY
)"
map_set_output="$(nav_action map_set "$map_arg" 60)"
echo "$map_set_output"
action_succeeded "$map_set_output" || {
  echo "MAP_PREPARE_ERROR: map_set no terminó correctamente" >&2
  exit 44
}

relocation_arg="$(python3 - "$map_name" <<'PY'
import json, sys
print(json.dumps({
  "map_name":sys.argv[1],
  "target_point":{"mode":"global"},
},separators=(",",":")))
PY
)"
set +e
relocation_output="$(nav_action relocation_start "$relocation_arg" 60 2>&1)"
relocation_status=$?
set -e
echo "$relocation_output"
if ((relocation_status != 0)) || ! action_succeeded "$relocation_output"; then
  state_output="$(nav_action check_state '{}' 8 2>&1 || true)"
  echo "$state_output"
  if grep -q 'FSM_RELOCATING' <<<"$state_output"; then
    echo "MAP_LOCALIZATION_REQUIRED: la relocalización global continúa sin obtener una pose." >&2
    echo "Use Localización forzada en la interfaz web y marque la pose y orientación reales del robot." >&2
    exit 48
  fi
  echo "MAP_PREPARE_ERROR: la relocalización global no terminó correctamente" >&2
  exit 45
fi

ready=0
for _ in $(seq 1 20); do
  state_output="$(nav_action check_state '{}' 8)" || true
  if grep -q 'status=4' <<<"$state_output" && grep -q 'FSM_WAITNAVIGATE' <<<"$state_output"; then
    ready=1
    break
  fi
  sleep 1
done
if ((ready == 0)); then
  echo "$state_output"
  echo "MAP_PREPARE_ERROR: el navegador no llegó a FSM_WAITNAVIGATE" >&2
  exit 46
fi

map_output="$(nav_action get_map_name '{}')"
if ! action_succeeded "$map_output" || \
   ! grep -Fq "\"map_name\" : \"$map_name\"" <<<"$map_output"; then
  echo "$map_output"
  echo "MAP_PREPARE_ERROR: el mapa activo no quedó confirmado" >&2
  exit 47
fi
cache_tmp="${runtime_cache}.$$"
printf '%s\n' "$runtime_signature" >"$cache_tmp"
mv -f -- "$cache_tmp" "$runtime_cache"
echo "MAP_ACTIVATED=$map_name"
echo "MAP_FINGERPRINT=$map_fingerprint"
echo "MAP_LOCALIZATION=global"
echo "NAV_STATE=FSM_WAITNAVIGATE"
REMOTE
}

map_preflight() {
  local minimum_soc="${1:-$MIN_BATTERY_SOC}"
  local remote_status=0
  ssh_vision bash -s -- "$NAV_CONTAINER" "$ROS_CONTAINER" "$MAP_NAME" \
    "$ROUTE_ACTION" "$ROUTE_TYPE" "$minimum_soc" <<'REMOTE' || remote_status=$?
set -Eeuo pipefail
nav_container="$1"
ros_container="$2"
map_name="$3"
route_action="$4"
route_type="$5"
min_battery_soc="$6"
map_dir="/etc/walker/map/$map_name"

[[ "$(hostname)" == "vision" ]] || exit 20
for container in "$nav_container" "$ros_container"; do
  [[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || exit 21
done
[[ -r "$map_dir/umap/umap.json" && -r "$map_dir/user/task.json" ]] || exit 22

python3 - "$map_dir/umap/umap.json" "$map_dir/user/task.json" <<'PY'
import json, math, sys
umap=json.load(open(sys.argv[1], encoding="utf-8"))
task=json.load(open(sys.argv[2], encoding="utf-8"))
expected=["START","PASO1","PASO2","PASO 3","PASO4","FINISH"]
points=umap.get("target_points",[])
by_id={p.get("id"):p for p in points}
task_ids=[p.get("id") for p in task.get("target_points",[])]
if task_ids[:len(expected)] != expected:
    raise SystemExit(f"Secuencia base de task.json inesperada: {task_ids}")
if any(point not in by_id for point in task_ids):
    raise SystemExit("Hay puntos de task.json ausentes en umap.json")
for point in task_ids:
    p=by_id[point]
    if p.get("mode") != "logo_nav": raise SystemExit(f"{point}: modo no permitido")
    if not all(math.isfinite(float(p[key])) for key in ("point_x","point_y","point_yaw")):
        raise SystemExit(f"{point}: coordenadas inválidas")
print("MAP_POINTS_AVAILABLE="+" -> ".join(task_ids))
PY

action_info="$(docker exec "$nav_container" bash -lc "source /opt/walker/setup.bash; rosa action info '$route_action'; rosa action type '$route_action'")"
grep -q "$route_type" <<<"$action_info" || exit 23

map_output="$(docker exec "$nav_container" bash -lc \
  "source /opt/walker/setup.bash; timeout 8 rosa action send_goal '$route_action' '$route_type' '{\"command\":\"get_map_name\",\"arg_json\":\"{}\"}'")"
grep -Fq "\"map_name\" : \"$map_name\"" <<<"$map_output" || {
  echo "$map_output"
  exit 24
}
grep -q 'status=4' <<<"$map_output" || exit 25

state_output="$(docker exec "$nav_container" bash -lc \
  "source /opt/walker/setup.bash; timeout 8 rosa action send_goal '$route_action' '$route_type' '{\"command\":\"check_state\",\"arg_json\":\"{}\"}'")"
grep -q 'FSM_WAITNAVIGATE' <<<"$state_output" || {
  echo "$state_output"
  exit 29
}
grep -q 'status=4' <<<"$state_output" || exit 30

safety_dir="$(mktemp -d)"
trap 'rm -rf -- "$safety_dir"' EXIT
topic_once() {
  docker exec "$ros_container" bash -lc \
    "source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 8 ros2 topic echo --once '$1'"
}
topic_once /emb/estop_key_state >"$safety_dir/estop" & p1=$!
topic_once /emb/servo_estop_key_state >"$safety_dir/servo" & p2=$!
topic_once /emb/chrg_input_status >"$safety_dir/charge" & p3=$!
topic_once /emb/battery_state >"$safety_dir/battery" & p4=$!
wait "$p1"; wait "$p2"; wait "$p3"; wait "$p4"
[[ "$(awk '/data:/ {print $2; exit}' "$safety_dir/estop")" == "0" ]] || exit 26
[[ "$(awk '/data:/ {print $2; exit}' "$safety_dir/servo")" == "0" ]] || exit 27
[[ "$(awk '/data:/ {print $2; exit}' "$safety_dir/charge")" == "0" ]] || exit 28

python3 - "$safety_dir/battery" "$min_battery_soc" <<'PY'
import re, sys
text=open(sys.argv[1], encoding="utf-8").read()
values=[float(value) for value in re.findall(r"^\s*batsoc:\s*([-+0-9.eE]+)", text, re.M)]
minimum=float(sys.argv[2])
if len(values) != 2: raise SystemExit("No se obtuvieron los dos SOC")
if min(values) < minimum: raise SystemExit(f"SOC insuficiente para la ruta larga: {values}")
print("BATTERY_SOC="+",".join(f"{value:.1f}" for value in values))
PY

printf 'MAP_NAME=%s\nROUTE_ACTION=%s\nNAV_STATE=FSM_WAITNAVIGATE\nESTOPS=0,0\nCHARGER=disconnected\nMAP_NAVIGATION=ready\n' \
  "$map_name" "$route_action"
REMOTE
  if ((remote_status != 0)); then
    die "La comprobación de mapa/navegación falló (código remoto $remote_status). El robot no recibió una orden de movimiento."
  fi
}

read_start_pose() {
  START_POSE="$(ssh_vision python3 - "$MAP_NAME" <<'PY'
import json, sys
p=f"/etc/walker/map/{sys.argv[1]}/umap/umap.json"
d=json.load(open(p, encoding="utf-8"))
s=next((x for x in d["target_points"] if x["id"]=="START"),None)
if not s: raise SystemExit("START no existe")
print(f'{float(s["point_x"]):.9f} {float(s["point_y"]):.9f} {float(s["point_yaw"]):.9f}')
PY
)"
  info "MAP_START_POSE=$START_POSE"
}

assert_near_pose() {
  local label="$1" current="$2" reference="$3" pos_tol="$4" yaw_tol="$5"
  python3 - "$label" "$current" "$reference" "$pos_tol" "$yaw_tol" <<'PY'
import math, sys
label=sys.argv[1]
current=tuple(map(float,sys.argv[2].split()))
reference=tuple(map(float,sys.argv[3].split()))
pos_tol=float(sys.argv[4]); yaw_tol=float(sys.argv[5])
distance=math.hypot(current[0]-reference[0],current[1]-reference[1])
yaw=math.atan2(math.sin(current[2]-reference[2]),math.cos(current[2]-reference[2]))
if distance>pos_tol or abs(yaw)>yaw_tol:
    raise SystemExit(f"{label}: distancia={distance:.3f} m, yaw={math.degrees(yaw):.1f} grados")
print(f"{label}_OK distance={distance:.3f} yaw_deg={math.degrees(yaw):.1f}")
PY
}

verify_start_area() {
  local current
  read_start_pose
  current="$(read_map_localization_pose)"
  assert_near_pose "START_AREA" "$current" "$START_POSE" \
    "$START_POSITION_TOLERANCE" "$START_YAW_TOLERANCE"
}

navigation_to_point() {
  local point="$1" direction="$2" output encoded_point nav_started_epoch
  info "[$direction] Navegando a '$point'..."
  nav_started_epoch="$(date +%s)"
  encoded_point="$(printf '%s' "$point" | base64 -w0)"
  output="$(ssh_vision bash -s -- "$NAV_CONTAINER" "$MAP_NAME" "$encoded_point" \
    "$NAVIGATION_TIMEOUT_SECONDS" <<'REMOTE'
set -Eeuo pipefail
container="$1"
map_name="$2"
point="$(printf '%s' "$3" | base64 -d)"
timeout_seconds="$4"
payload="$(python3 - "$map_name" "$point" <<'PY'
import json, sys
print(json.dumps({
  "command":"navigation_start",
  "arg_json":json.dumps({
    "target_point":{"map_name":sys.argv[1],"mode":"logo_nav","id":sys.argv[2]},
  },separators=(",",":")),
},separators=(",",":")))
PY
)"
timeout "$timeout_seconds" docker exec "$container" bash -lc \
  "source /opt/walker/setup.bash; rosa action send_goal /vnav/task/command unav_task_msgs/action/Task '$payload'"
REMOTE
)" || {
    printf '%s\n' "$output" >&2
    stop_navigation
    navigation_failure_diagnostic "$nav_started_epoch" "$point"
    die "La navegación a '$point' falló. La caja permanece sujeta."
  }
  printf '%s\n' "$output"
  grep -q 'Goal accepted' <<<"$output" || die "Objetivo '$point' no aceptado."
  grep -q 'status=4' <<<"$output" || die "Objetivo '$point' no terminó con status=4."
  grep -Eq "navigation_start SUCCEEDED|'desc': '(SUCCESS|SUCCEED)'" <<<"$output" || \
    die "El servidor no confirmó éxito para '$point'."
  info "ROUTE_POINT_OK=$point"
}

assert_waypoint_available() {
  local point="$1"
  ssh_vision python3 - "$MAP_NAME" "$point" <<'PY'
import json, math, sys

map_name, requested = sys.argv[1:]
path = f"/etc/walker/map/{map_name}/umap/umap.json"
with open(path, encoding="utf-8") as stream:
    data = json.load(stream)

points = {point.get("id"): point for point in data.get("target_points", [])}
if requested not in points:
    raise SystemExit(f"Waypoint no encontrado en {path}: {requested}")

point = points[requested]
if point.get("mode") != "logo_nav":
    raise SystemExit(f"Waypoint con modo no permitido: {point.get('mode')}")
values = [float(point[key]) for key in ("point_x", "point_y", "point_yaw")]
if not all(math.isfinite(value) for value in values):
    raise SystemExit("Waypoint con coordenadas no finitas")
print(
    f"WAYPOINT_AVAILABLE={requested} "
    f"x={values[0]:.6f} y={values[1]:.6f} yaw={values[2]:.6f}"
)
PY
}

waypoint_backoff_pose() {
  local point="$1" distance="$2"
  ssh_vision python3 - "$MAP_NAME" "$point" "$distance" <<'PY'
import json, math, sys

map_name, requested, raw_distance = sys.argv[1:]
distance = float(raw_distance)
if not math.isfinite(distance) or not 0.50 <= distance <= 2.00:
    raise SystemExit("El retroceso de waypoint debe estar entre 0,50 y 2,00 m")

path = f"/etc/walker/map/{map_name}/umap/umap.json"
with open(path, encoding="utf-8") as stream:
    data = json.load(stream)
point = next((item for item in data.get("target_points", [])
              if item.get("id") == requested), None)
if point is None:
    raise SystemExit(f"Waypoint no encontrado: {requested}")
x = float(point["point_x"])
y = float(point["point_y"])
yaw = float(point["point_yaw"])
values = (x, y, yaw)
if not all(math.isfinite(value) for value in values):
    raise SystemExit("Waypoint con coordenadas no finitas")
safe_x = x - distance * math.cos(yaw)
safe_y = y - distance * math.sin(yaw)
print(f"{safe_x:.9f} {safe_y:.9f} {yaw:.9f}")
PY
}

navigation_to_free_pose() {
  local pose="$1" label="$2" output encoded_pose nav_started_epoch
  info "[$label] Navegando a la pose de mapa guardada..."
  nav_started_epoch="$(date +%s)"
  encoded_pose="$(printf '%s' "$pose" | base64 -w0)"
  output="$(ssh_vision bash -s -- "$NAV_CONTAINER" "$MAP_NAME" "$encoded_pose" \
    "$NAVIGATION_TIMEOUT_SECONDS" <<'REMOTE'
set -Eeuo pipefail
container="$1"
map_name="$2"
pose="$(printf '%s' "$3" | base64 -d)"
timeout_seconds="$4"
payload="$(python3 - "$map_name" "$pose" <<'PY'
import json, math, sys
values=tuple(map(float, sys.argv[2].split()))
if len(values) != 3 or not all(math.isfinite(v) for v in values):
    raise SystemExit("Pose free_nav inválida")
x,y,yaw=values
target={
  "map_name":sys.argv[1], "mode":"free_nav",
  "point_x":x, "point_y":y, "point_yaw":yaw,
  "level":1,
  "speed":{
    "linear":{"x":0.18,"y":0.01,"z":0.0},
    "angular":{"x":0.0,"y":0.0,"z":0.20},
  },
}
print(json.dumps({
  "command":"navigation_start",
  "arg_json":json.dumps({"target_point":target},separators=(",",":")),
},separators=(",",":")))
PY
)"
timeout "$timeout_seconds" docker exec "$container" bash -lc \
  "source /opt/walker/setup.bash; rosa action send_goal /vnav/task/command unav_task_msgs/action/Task '$payload'"
REMOTE
)" || {
    printf '%s\n' "$output" >&2
    stop_navigation
    navigation_failure_diagnostic "$nav_started_epoch" "free_pose:$label"
    die "La navegación a la pose de mesa falló. La caja permanece sujeta."
  }
  printf '%s\n' "$output"
  grep -q 'Goal accepted' <<<"$output" || die "La pose de mesa no fue aceptada."
  grep -q 'status=4' <<<"$output" || die "La pose de mesa no terminó con status=4."
  grep -Eq "navigation_start SUCCEEDED|'desc': '(SUCCESS|SUCCEED)'" <<<"$output" || \
    die "El servidor no confirmó la llegada a la pose de mesa."
  info "FREE_NAV_OK=$label"
}

verify_grasp() {
  grasp_args --verify-grasp
}

report_selected_route() {
  if [[ "$ROUTE_CONTEXT" == "table-transfer" ]]; then
    info "ROUTE_SELECTED=mesa1 -> MESA2_PRE (directo, sin PASO1) -> mesa2 -> home"
    return 0
  fi
  if [[ "$ROUTE_PROFILE" == "short" ]]; then
    info "ROUTE_SELECTED=START -> PASO1 -> mesa -> depósito -> home"
  else
    info "ROUTE_SELECTED=START -> PASO1 -> PASO2 -> PASO 3 -> PASO4 -> FINISH -> START -> mesa"
  fi
}

run_map_round_trip() {
  local point
  local -a outbound=()
  local -a inbound=()

  if [[ "$ROUTE_PROFILE" == "short" ]]; then
    outbound=(PASO1)
    info "ROUTE_PROFILE=short: START -> PASO1 -> mesa"
  else
    outbound=(PASO1 PASO2 "PASO 3" PASO4 FINISH)
    inbound=(PASO4 "PASO 3" PASO2 PASO1 START)
    info "ROUTE_PROFILE=full: recorrido completo de test_route_01"
  fi

  trap 'stop_navigation' EXIT
  trap 'stop_navigation; exit 130' INT TERM HUP

  info "[RUTA 1/4] Confirmando agarre antes de salir..."
  verify_grasp
  navigation_to_point START IDA
  verify_start_area
  for point in "${outbound[@]}"; do
    navigation_to_point "$point" IDA
  done

  if [[ "$ROUTE_PROFILE" == "short" ]]; then
    info "[RUTA 2/4] PASO1 alcanzado; comprobando agarre..."
  else
    info "[RUTA 2/4] FINISH alcanzado; comprobando agarre..."
  fi
  verify_grasp
  map_preflight "$RETURN_MIN_BATTERY_SOC"

  if [[ "$ROUTE_PROFILE" == "short" ]]; then
    info "[RUTA 3/4] Ruta corta terminada en PASO1; regreso directo a la mesa."
    return 0
  fi

  info "[RUTA 3/4] Regresando por los mismos puntos hasta START..."
  for point in "${inbound[@]}"; do
    navigation_to_point "$point" VUELTA
  done

  info "[RUTA 4/4] START recuperado y caja aún sujeta."
  verify_grasp
}

return_to_table_and_deposit() {
  local current
  if [[ "$ROUTE_PROFILE" != "short" ]]; then
    current="$(read_map_localization_pose)"
    assert_near_pose "MAP_RETURN_START" "$current" "$START_POSE" \
      "$START_POSITION_TOLERANCE" "$START_YAW_TOLERANCE"
  fi

  info "[DEPÓSITO 1/4] Navegando a la pose despejada frente a la mesa..."
  navigation_to_free_pose "$TABLE_STAGING_MAP_POSE" PREMESA

  current="$(read_map_localization_pose)"
  assert_near_pose "TABLE_STAGING_RETURN" "$current" "$TABLE_STAGING_MAP_POSE" \
    "$STAGING_POSITION_TOLERANCE" "$STAGING_YAW_TOLERANCE"
  trap - EXIT INT TERM HUP

  info "[DEPÓSITO 2/4] Avanzando la separación medida hasta la pose de recogida..."
  carry_args --advance-held-distance "$TABLE_APPROACH_DISTANCE" --yes

  current="$(read_odom_pose)"
  info "TABLE_RETURN_ODOM=$current"

  info "[DEPÓSITO 3/4] Verificando agarre y depositando en la mesa inicial..."
  verify_grasp
  grasp_args --deposit-held --yes

  info "[DEPÓSITO 4/4] Caja liberada; ejecutando recuperación y home..."
  flock -u 9
  if ((FAST == 1)); then
    exec "$RECOVERY_SCRIPT" --run --yes --fast
  else
    exec "$RECOVERY_SCRIPT" --run --yes
  fi
}

confirm_once() {
  ((YES == 1)) && return 0
  if [[ "$ROUTE_PROFILE" == "short" ]]; then
    cat <<'EOF'

CONFIRMACIÓN ÚNICA — RUTA CORTA
El robot cogerá la caja y recorrerá:
  START -> PASO1
Desde PASO1 volverá directamente a esta mesa, depositará la caja y terminará
en home, sin regresar por START.
Confirma que todo ese recorrido está libre para la anchura de la caja,
Ethernet y cargador están desconectados y otra persona mantiene el paro listo.

Escribe EJECUTAR RUTA CON CAJA para continuar:
EOF
  else
    cat <<'EOF'

CONFIRMACIÓN ÚNICA
El robot cogerá la caja, recorrerá todo test_route_01 hasta FINISH, volverá
por los mismos puntos, depositará la caja en esta mesa y terminará en home.
Confirma que la ruta completa está libre para la anchura de la caja, Ethernet
y cargador están desconectados y otra persona mantiene preparado el paro.

Escribe EJECUTAR RUTA CON CAJA para continuar:
EOF
  fi
  local answer
  read -r answer
  [[ "$answer" == "EJECUTAR RUTA CON CAJA" ]] || die "Ciclo cancelado."
}

confirm_waypoint_navigation() {
  ((YES == 1)) && return 0
  cat <<EOF

CONFIRMACIÓN DE NAVEGACIÓN
El robot navegará sin mover los brazos hasta '$NAVIGATE_WAYPOINT'.
Confirma que está localizado, que el cargador y Ethernet están desconectados,
que el recorrido está despejado y que otra persona mantiene el paro preparado.

Escribe NAVEGAR A WAYPOINT para continuar:
EOF
  local answer
  read -r answer
  [[ "$answer" == "NAVEGAR A WAYPOINT" ]] || die "Navegación cancelada."
}

navigate_waypoint_only() {
  assert_waypoint_available "$NAVIGATE_WAYPOINT"
  if [[ "$FLUID_MODE" == "1" && "${CRUZR_TRANSFER_PREFLIGHT_DONE:-0}" == "1" ]]; then
    info "FLUID_MODE: mapa, batería, paros y cargador ya validados en el preflight general."
  else
    map_preflight "$RETURN_MIN_BATTERY_SOC"
  fi
  confirm_waypoint_navigation
  trap 'stop_navigation' EXIT
  trap 'stop_navigation; exit 130' INT TERM HUP
  navigation_to_point "$NAVIGATE_WAYPOINT" WAYPOINT
  trap - EXIT INT TERM HUP
  info "WAYPOINT_NAVIGATION_OK=$NAVIGATE_WAYPOINT"
}

navigate_waypoint_backoff_only() {
  local safe_pose
  assert_waypoint_available "$NAVIGATE_WAYPOINT"
  safe_pose="$(waypoint_backoff_pose "$NAVIGATE_WAYPOINT" "$NAVIGATE_BACKOFF_DISTANCE")"
  info "WAYPOINT_BACKOFF_POSE=$safe_pose distance=${NAVIGATE_BACKOFF_DISTANCE}m"
  if [[ "$FLUID_MODE" == "1" && "${CRUZR_TRANSFER_PREFLIGHT_DONE:-0}" == "1" ]]; then
    info "FLUID_MODE: mapa, batería, paros y cargador ya validados en el preflight general."
  else
    map_preflight "$RETURN_MIN_BATTERY_SOC"
  fi
  confirm_waypoint_navigation
  trap 'stop_navigation' EXIT
  trap 'stop_navigation; exit 130' INT TERM HUP
  navigation_to_free_pose "$safe_pose" "BACKOFF_${NAVIGATE_WAYPOINT}"
  trap - EXIT INT TERM HUP
  info "WAYPOINT_BACKOFF_NAVIGATION_OK=${NAVIGATE_WAYPOINT}:${NAVIGATE_BACKOFF_DISTANCE}m"
}

run_cycle() {
  confirm_once

  info "[RECOGIDA] Centrando y agarrando la caja..."
  carry_args --grasp-only --yes
  verify_grasp
  capture_table_pose

  info "[SALIDA] Separándose 0,50 m de la mesa antes de iniciar la ruta..."
  carry_args --retreat-only --yes
  capture_table_staging_pose

  run_map_round_trip
  return_to_table_and_deposit
}

validate_resume_arguments() {
  [[ -n "$RESUME_STAGING_MAP_POSE" ]] || \
    die "Falta --staging-map-pose \"X Y YAW\"."
  [[ -n "$RESUME_APPROACH_DISTANCE" ]] || \
    die "Falta --approach-distance METROS."

  python3 - "$RESUME_STAGING_MAP_POSE" "$RESUME_APPROACH_DISTANCE" <<'PY'
import math, sys
try:
    pose=tuple(map(float, sys.argv[1].split()))
    distance=float(sys.argv[2])
except ValueError as exc:
    raise SystemExit(f"Argumento de reanudación inválido: {exc}")
if len(pose) != 3 or not all(math.isfinite(value) for value in pose):
    raise SystemExit("La pose de premesa debe contener tres números finitos")
if not math.isfinite(distance) or not 0.10 <= distance <= 0.65:
    raise SystemExit("La distancia de aproximación debe estar entre 0,10 y 0,65 m")
print("RESUME_ARGUMENTS_OK")
PY
}

resume_to_table() {
  validate_resume_arguments
  TABLE_STAGING_MAP_POSE="$RESUME_STAGING_MAP_POSE"
  TABLE_APPROACH_DISTANCE="$RESUME_APPROACH_DISTANCE"
  map_preflight "$RETURN_MIN_BATTERY_SOC"
  verify_grasp
  confirm_once
  trap 'stop_navigation' EXIT
  trap 'stop_navigation; exit 130' INT TERM HUP
  info "RESUME_MODE: no se repetirá el agarre ni el recorrido del mapa."
  return_to_table_and_deposit
}

main() {
  require_local_tools
  exec 9>"/tmp/cruzr_blue_workbin_map_route.lock"
  flock -n 9 || die "Ya hay otra ruta con caja en ejecución."
  select_connection

  case "$MODE" in
    check)
      ensure_map_active || die "No se pudo activar y localizar '$MAP_NAME'. El robot no se movió."
      map_preflight
      report_selected_route
      grasp_args --check
      TABLE_MAP_POSE="$(read_map_localization_pose)"
      info "CURRENT_MAP_POSE=$TABLE_MAP_POSE"
      info "CHECK_OK: mapa, localización y flujo disponibles; no se movió el robot."
      ;;
    run)
      require_wireless_run
      ensure_map_active || die "No se pudo activar y localizar '$MAP_NAME'. El robot no se movió."
      map_preflight
      report_selected_route
      run_cycle
      ;;
    resume-to-table)
      require_wireless_run
      ensure_map_active || die "No se pudo activar y localizar '$MAP_NAME'. El robot no se movió."
      resume_to_table
      ;;
    navigate-waypoint)
      require_wireless_run
      if [[ "$FLUID_MODE" == "1" && "${CRUZR_TRANSFER_PREFLIGHT_DONE:-0}" == "1" ]]; then
        info "FLUID_MODE: se reutiliza el mapa activo confirmado por el flujo exterior."
      else
        ensure_map_active || die "No se pudo sincronizar y localizar '$MAP_NAME'. El robot no se movió."
      fi
      navigate_waypoint_only
      ;;
    navigate-waypoint-backoff)
      require_wireless_run
      if [[ "$FLUID_MODE" == "1" && "${CRUZR_TRANSFER_PREFLIGHT_DONE:-0}" == "1" ]]; then
        info "FLUID_MODE: se reutiliza el mapa activo confirmado por el flujo exterior."
      else
        ensure_map_active || die "No se pudo sincronizar y localizar '$MAP_NAME'. El robot no se movió."
      fi
      navigate_waypoint_backoff_only
      ;;
    *)
      die "Modo interno desconocido: $MODE"
      ;;
  esac
}

main
