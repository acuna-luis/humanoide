#!/usr/bin/env bash

set -Eeuo pipefail

# Perfil temporal de tránsito con el workbin sujeto. Durante la navegación
# desvía exclusivamente las tres nubes RGB-D/estéreo que alimentan la capa
# STVL del costmap. La capa obstacle_layer/base_scan (LiDAR frontal), el mapa,
# la localización, la odometría, los bumpers y los paros permanecen activos.
# La configuración original se conserva byte a byte y se restaura al terminar.

readonly ROBOT_USER="walker"
readonly WIFI_GATEWAY="192.168.42.2"
readonly VISION_HOST="192.168.11.3"
readonly DEFAULT_PASSWORD="aa"
readonly PERCEPTION_CONTAINER="walker-nav.vnav_perception-1"
readonly NAV_CONTAINER="walker-nav.nav_taskmanager-1"
readonly FREEPNC_CONTAINER="walker-nav.freepnc_task-1"
readonly PERCEPTION_CONFIG="/opt/walker/nav_perception2d_config_utars/share/nav_perception2d_config_utars/config/perception/perception_params.yaml"
readonly LIDAR_CONFIG="/opt/walker/nav_freepnc_config_utars/share/nav_freepnc_config_utars/config/costmap/global_costmap_params.yaml"
readonly PERCEPTION_ACTION="/vnav/action/perception"
readonly PERCEPTION_TYPE="vnav_task_msgs/action/VnavCommand"
readonly WAIST_TOPIC="/upub_od_waistpc"
readonly BOTTOM_TOPIC="/upub_od_bottompc"
readonly HEAD_TOPIC="/upub_od_headpc"
readonly WAIST_SUPPRESSED="/cruzr/cargo_transit/waistpc_suppressed"
readonly BOTTOM_SUPPRESSED="/cruzr/cargo_transit/bottompc_suppressed"
readonly HEAD_SUPPRESSED="/cruzr/cargo_transit/headpc_suppressed"
# La capa STVL usa voxel_decay=5 s. Siete segundos limpian observaciones de
# cámara previas antes de autorizar el movimiento.
readonly PRIME_SECONDS="7"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD

if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_PATH

MODE="check"
VISION_SSH_HOST=""
CONTROL_INTERFACE=""

usage() {
  cat <<'EOF'
Uso:
  ./scripts/cruzr_cargo_perception_profile.sh --check
  ./scripts/cruzr_cargo_perception_profile.sh --enable
  ./scripts/cruzr_cargo_perception_profile.sh --restore

--check    Comprueba contenedores, LiDAR independiente y estado. No mueve.
--enable   Guarda la configuración original, desvía temporalmente las tres
           nubes de cámara del costmap y espera a que decaigan sus vóxeles.
--restore  Restaura byte a byte la configuración original y reinicia solamente
           vnav_perception. Es seguro repetirlo.

Este perfil se usa solo durante el tránsito con el workbin ya sujeto. Conserva
LiDAR, mapa, localización, odometría, bumpers y paros; reduce temporalmente la
percepción de obstáculos altos procedente de RGB-D/estéreo. Requiere una ruta
controlada y despejada, con una persona preparada junto al paro físico.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

while (($#)); do
  case "$1" in
    --check|--enable|--restore)
      MODE="${1#--}"
      ;;
    --fast)
      # Compatibilidad con el orquestador; estas comprobaciones son críticas.
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

route_interface() {
  ip -o route get "$1" 2>/dev/null |
    awk '{for (i=1; i<=NF; i++) if ($i=="dev") {print $(i+1); exit}}'
}

is_wireless_interface() {
  [[ -n "$1" && -d "/sys/class/net/$1/wireless" ]]
}

select_connection() {
  if nc -z -w2 "$WIFI_GATEWAY" 22 >/dev/null 2>&1; then
    CONTROL_INTERFACE="$(route_interface "$WIFI_GATEWAY")"
    is_wireless_interface "$CONTROL_INTERFACE" ||
      die "La ruta a $WIFI_GATEWAY no usa Wi-Fi."
    VISION_SSH_HOST="$WIFI_GATEWAY"
    info "Conexión: Wi-Fi mediante vision ($CONTROL_INTERFACE)"
    return
  fi

  if nc -z -w2 "$VISION_HOST" 22 >/dev/null 2>&1; then
    CONTROL_INTERFACE="$(route_interface "$VISION_HOST")"
    is_wireless_interface "$CONTROL_INTERFACE" ||
      die "La ruta a vision no usa Wi-Fi."
    VISION_SSH_HOST="$VISION_HOST"
    info "Conexión: Wi-Fi directa a vision ($CONTROL_INTERFACE)"
    return
  fi
  die "No se alcanza vision mediante la Wi-Fi del robot."
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

remote_profile() {
  ssh_vision bash -s -- "$MODE" "$PERCEPTION_CONTAINER" "$NAV_CONTAINER" \
    "$FREEPNC_CONTAINER" "$PERCEPTION_CONFIG" "$LIDAR_CONFIG" \
    "$PERCEPTION_ACTION" "$PERCEPTION_TYPE" "$PRIME_SECONDS" \
    "$WAIST_TOPIC" "$BOTTOM_TOPIC" "$HEAD_TOPIC" \
    "$WAIST_SUPPRESSED" "$BOTTOM_SUPPRESSED" "$HEAD_SUPPRESSED" <<'REMOTE'
set -Eeuo pipefail

mode="$1"
perception_container="$2"
nav_container="$3"
freepnc_container="$4"
config="$5"
lidar_config="$6"
perception_action="$7"
perception_type="$8"
prime_seconds="$9"
shift 9
waist_topic="$1"
bottom_topic="$2"
head_topic="$3"
waist_suppressed="$4"
bottom_suppressed="$5"
head_suppressed="$6"

state_dir="$HOME/.config/udoke/cruzr-cargo-perception-profile"
original="$state_dir/perception_params.yaml.original"
metadata="$state_dir/profile.state"

container_running() {
  [[ "$(docker inspect --format '{{.State.Running}}' "$1" 2>/dev/null)" == "true" ]]
}

config_hash() {
  docker exec "$perception_container" sha256sum "$config" | awk '{print $1}'
}

validate_lidar_layer() {
  docker exec "$freepnc_container" awk '
    /^obstacle_layer:/ {inside=1; next}
    inside && /^[^[:space:]]/ {inside=0}
    inside && /observation_sources:[[:space:]]+base_scan/ {source=1}
    inside && /sensor_frame:[[:space:]]+front_lidar_link/ {frame=1}
    inside && /marking:[[:space:]]+true/ {marking=1}
    END {exit !(source && frame && marking)}
  ' "$lidar_config"
}

topic_values() {
  docker exec "$perception_container" awk '
    /^[[:space:]]+obstacle_pointcloud_topic:/ {
      value=$2
      gsub(/"/, "", value)
      print value
    }
  ' "$config"
}

validate_original_topics() {
  [[ "$(topic_values)" == "$waist_topic"$'\n'"$bottom_topic"$'\n'"$head_topic" ]]
}

validate_suppressed_topics() {
  [[ "$(topic_values)" == "$waist_suppressed"$'\n'"$bottom_suppressed"$'\n'"$head_suppressed" ]]
}

wait_action_server() {
  local output=""
  for _ in $(seq 1 30); do
    if container_running "$perception_container"; then
      output="$(docker exec "$nav_container" bash -lc \
        "source /opt/walker/setup.bash; rosa action info '$perception_action'" 2>&1 || true)"
      grep -q 'Action server count: 1' <<<"$output" && return 0
    fi
    sleep 1
  done
  printf '%s\n' "$output" >&2
  return 1
}

restart_perception() {
  docker restart "$perception_container" >/dev/null
  wait_action_server || {
    echo "No reapareció el servidor de percepción tras reiniciarlo." >&2
    return 1
  }
}

start_and_prime() {
  local payload output
  payload='{"command":"start_perception","arg_json":"{}"}'
  output="$(docker exec "$nav_container" bash -lc \
    "source /opt/walker/setup.bash; timeout 20 rosa action send_goal '$perception_action' '$perception_type' '$payload'" 2>&1)"
  printf '%s\n' "$output"
  grep -q 'Goal accepted' <<<"$output" && grep -q 'status=4' <<<"$output" || {
    echo "vnav_perception no aceptó start_perception." >&2
    return 1
  }
  sleep "$prime_seconds"
}

for container in "$perception_container" "$nav_container" "$freepnc_container"; do
  container_running "$container" || {
    echo "El contenedor $container no está activo." >&2
    exit 20
  }
done
docker exec "$perception_container" test -r "$config" || {
  echo "No se encuentra la configuración $config." >&2
  exit 21
}
docker exec "$freepnc_container" test -r "$lidar_config" || {
  echo "No se encuentra la configuración LiDAR $lidar_config." >&2
  exit 22
}
validate_lidar_layer || {
  echo "No se confirmó obstacle_layer/base_scan con el LiDAR frontal activo." >&2
  exit 23
}

current_hash="$(config_hash)"
original_hash=""
profile_hash=""
profile_state=""
if [[ -r "$metadata" ]]; then
  original_hash="$(sed -n 's/^ORIGINAL_HASH=//p' "$metadata")"
  profile_hash="$(sed -n 's/^PROFILE_HASH=//p' "$metadata")"
  [[ -n "$profile_hash" ]] || profile_hash="$(sed -n 's/^CARGO_HASH=//p' "$metadata")"
  profile_state="$(sed -n 's/^STATE=//p' "$metadata")"
fi

case "$mode" in
  check)
    wait_action_server || exit 24
    if [[ "$profile_state" == "preparing" ]]; then
      echo "CARGO_PERCEPTION_PROFILE=interrupted-installation" >&2
      echo "Ejecute --restore antes de continuar." >&2
      exit 25
    elif [[ -n "$profile_hash" && "$current_hash" == "$profile_hash" ]]; then
      validate_suppressed_topics || {
        echo "El perfil activo no contiene exactamente los tres desvíos esperados." >&2
        exit 26
      }
      echo "CARGO_PERCEPTION_PROFILE=lidar-transit-enabled"
    elif [[ -n "$original_hash" && "$current_hash" == "$original_hash" ]]; then
      echo "CARGO_PERCEPTION_PROFILE=restored-pending-cleanup"
    elif [[ -r "$metadata" ]]; then
      echo "CARGO_PERCEPTION_PROFILE=unknown-modification" >&2
      exit 27
    else
      validate_original_topics || {
        echo "Las salidas de percepción originales no son las esperadas." >&2
        exit 28
      }
      echo "CARGO_PERCEPTION_PROFILE=disabled"
    fi
    echo "PERCEPTION_CONFIG_HASH=$current_hash"
    echo "CARGO_TRANSIT_SAFETY=lidar+odom+map+bumpers+estops"
    ;;

  enable)
    if [[ -n "$profile_hash" && "$current_hash" == "$profile_hash" ]]; then
      validate_suppressed_topics || exit 29
      echo "CARGO_PERCEPTION_PROFILE=already-enabled"
      start_and_prime
      echo "CARGO_PERCEPTION_PRIMED=${prime_seconds}s"
      exit 0
    fi
    if [[ -r "$metadata" ]]; then
      echo "Existe una transacción anterior; ejecute --restore antes de habilitar otra vez." >&2
      exit 30
    fi
    validate_original_topics || {
      echo "No se modificarán salidas de percepción desconocidas." >&2
      exit 31
    }

    mkdir -p "$state_dir"
    chmod 700 "$state_dir"
    docker cp "$perception_container:$config" "$original"
    chmod 600 "$original"
    original_hash="$(sha256sum "$original" | awk '{print $1}')"
    [[ "$original_hash" == "$current_hash" ]] || {
      rm -rf -- "$state_dir"
      echo "La copia original no coincide con la configuración del contenedor." >&2
      exit 32
    }
    {
      printf 'STATE=preparing\n'
      printf 'ORIGINAL_HASH=%s\n' "$original_hash"
      printf 'PROFILE_HASH=\n'
    } >"$metadata"
    chmod 600 "$metadata"

    if ! docker exec -u 0 "$perception_container" sed -i -E \
      -e "s|^([[:space:]]+obstacle_pointcloud_topic:[[:space:]]+\")${waist_topic}(\")|\1${waist_suppressed}\2|" \
      -e "s|^([[:space:]]+obstacle_pointcloud_topic:[[:space:]]+\")${bottom_topic}(\")|\1${bottom_suppressed}\2|" \
      -e "s|^([[:space:]]+obstacle_pointcloud_topic:[[:space:]]+\")${head_topic}(\")|\1${head_suppressed}\2|" \
      "$config"; then
      docker cp "$original" "$perception_container:$config" >/dev/null || true
      rm -rf -- "$state_dir"
      echo "El contenedor rechazó el perfil; se recuperó el original." >&2
      exit 33
    fi
    validate_suppressed_topics || {
      docker cp "$original" "$perception_container:$config" >/dev/null
      rm -rf -- "$state_dir"
      echo "No se aplicaron exactamente los tres desvíos; se restauró el original." >&2
      exit 34
    }
    profile_hash="$(config_hash)"
    {
      printf 'STATE=enabled\n'
      printf 'ORIGINAL_HASH=%s\n' "$original_hash"
      printf 'PROFILE_HASH=%s\n' "$profile_hash"
    } >"$metadata"
    chmod 600 "$metadata"

    if ! restart_perception; then
      docker cp "$original" "$perception_container:$config"
      restart_perception || true
      echo "Falló el reinicio con el perfil; se intentó restaurar el original." >&2
      exit 35
    fi
    start_and_prime || {
      docker cp "$original" "$perception_container:$config"
      restart_perception || true
      echo "Falló la estabilización; se restauró el original." >&2
      exit 36
    }
    echo "CARGO_PERCEPTION_PROFILE=lidar-transit-enabled"
    echo "CARGO_PERCEPTION_CONFIG_HASH=$profile_hash"
    echo "RGBD_COSTMAP=temporarily-suppressed"
    echo "CARGO_TRANSIT_SAFETY=lidar+odom+map+bumpers+estops"
    echo "CARGO_PERCEPTION_PRIMED=${prime_seconds}s"
    ;;

  restore)
    if [[ ! -r "$metadata" ]]; then
      echo "CARGO_PERCEPTION_PROFILE=already-disabled"
      exit 0
    fi
    [[ -r "$original" ]] || {
      echo "Falta la copia original $original; no se sobrescribirá la configuración." >&2
      exit 37
    }
    if [[ "$current_hash" != "$original_hash" && "$profile_state" != "preparing" && "$current_hash" != "$profile_hash" ]]; then
      echo "La configuración cambió después de habilitar el perfil; no se sobrescribirá automáticamente." >&2
      exit 38
    fi
    docker cp "$original" "$perception_container:$config"
    [[ "$(config_hash)" == "$original_hash" ]] || {
      echo "La restauración no coincide con el hash original." >&2
      exit 39
    }
    restart_perception || exit 40
    rm -rf -- "$state_dir"
    echo "CARGO_PERCEPTION_PROFILE=restored"
    echo "PERCEPTION_CONFIG_HASH=$original_hash"
    ;;
esac
REMOTE
}

main() {
  for command_name in ssh setsid nc ip readlink awk; do
    command -v "$command_name" >/dev/null 2>&1 ||
      die "Falta el comando local '$command_name'."
  done
  select_connection
  remote_profile
}

main
