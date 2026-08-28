#!/usr/bin/env bash

set -Eeuo pipefail

readonly MOTION_HOST="${CRUZR_MOTION_IP:-192.168.11.2}"
readonly ROBOT_USER="${CRUZR_ROBOT_USER:-walker}"
readonly CONTAINER="walker-motion.manipulation_robot_app-1"
readonly CONFIG_PATH="/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_teleoperation/cruzr_clamp_pico_tele.yaml"
readonly TASK_NAME="teleoperation/cruzr_clamp_pico_teleoperation"
readonly ORIGINAL_SHA256="5f08b30cd5032a9fccd6b3becd933ff3884d9795d02f98cc2433fc0da33fc62a"
readonly ARMS_ONLY_SHA256="4e8d79a40e8b1f1fa5915de27ef60676fce4c9b5cec41cacfc0a1d9a7d117a44"
readonly BACKEND_UNIT="ubt-controller.service"
readonly BACKEND_LOG="/opt/ubt/ubt_controller/logs/ubt_controller.log"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly MOTION_ASKPASS="$SCRIPT_DIR/../cruzr_blue_workbin_cycle.sh"

mode="${1:---check}"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/teleoperation/install_cruzr_pico_arms_only.sh --check
  ./scripts/teleoperation/install_cruzr_pico_arms_only.sh --install
  ./scripts/teleoperation/install_cruzr_pico_arms_only.sh --rollback

--check     Sólo lectura. Informa si la tarea PICO instalada y la tarea viva
            tienen cintura/elevador desactivados.
--install   Con el backend PC en STOP, conserva un backup persistente y cambia
            exclusivamente waist_mode 1->0 y leg_mode 2->0 en la tarea clamp
            PICO. No reinicia contenedores, no cambia de modo y no mueve.
--rollback  Restaura byte a byte el YAML vendor respaldado. Tampoco reinicia
            ni mueve.

La instalación no afecta una tarea ya cargada. Después hace falta salir de
TeleopMode y volver a entrar, con preflight físico, para que Motion decodifique
los modos nuevos. El lanzador físico exige evidencia del YAML cargado. El
backup y el overlay quedan en el host Motion; si Docker recrea el contenedor,
el YAML puede volver al vendor y debe repetirse --check/--install.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

case "$mode" in
  --check|--install|--rollback) ;;
  --help|-h)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

require_pc_stop() {
  systemctl is-active --quiet "$BACKEND_UNIT" ||
    die "$BACKEND_UNIT no está activo; no se puede demostrar STOP."
  if pgrep -x pico_control >/dev/null 2>&1; then
    die "pico_control sigue ejecutándose; termine la sesión antes de cambiar configuración."
  fi
  local backend_start_text backend_start_ts operation_type
  backend_start_text="$(
    timeout 5s systemctl show "$BACKEND_UNIT" -p ActiveEnterTimestamp --value
  )" || die "No se pudo obtener el arranque vigente de $BACKEND_UNIT."
  backend_start_ts="$(date -d "$backend_start_text" '+%Y-%m-%d:%H:%M:%S')" ||
    die "Timestamp de arranque inválido para $BACKEND_UNIT."
  operation_type="$(
  BACKEND_LOG_PATH="$BACKEND_LOG" BACKEND_START_TS="$backend_start_ts" \
      timeout 5s python3 - <<'PY'
import json
import os

path = os.environ["BACKEND_LOG_PATH"]
start_ts = os.environ["BACKEND_START_TS"]
operation_type = None

with open(path, "r", encoding="utf-8", errors="replace") as stream:
    lines = stream.readlines()

for line in reversed(lines):
    if len(line) >= 19 and line[:19] < start_ts:
        break
    if "Pico publisher stop" in line:
        operation_type = 1
        break
    if "Pico publisher start" in line:
        operation_type = 2
        break
    raw_json = None
    marker = 'Send message to client: {"type":"detect"'
    if marker in line:
        raw_json = line.split("Send message to client: ", 1)[1]
    elif "Pico connect state from " in line and " changed to {" in line:
        raw_json = line.split(" changed to ", 1)[1].rsplit(", broadcast it", 1)[0]
    if raw_json is not None:
        try:
            message = json.loads(raw_json)
        except json.JSONDecodeError:
            continue
        value = message.get("content", {}).get("operation_type")
        if value in (1, 2):
            operation_type = value
            break

print(operation_type if operation_type is not None else "unknown")
PY
  )" || die "No se pudo reconstruir pasivamente el estado del backend."
  [[ "$operation_type" == "1" ]] ||
    die "El backend no está en STOP (operation_type=$operation_type)."
  printf 'PC_TELEOP_STOP_CONFIRMED=1,source=passive-log\n'
}

ssh_motion() {
  [[ -x "$MOTION_ASKPASS" ]] ||
    die "No existe el proveedor SSH local requerido: $MOTION_ASKPASS"
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$MOTION_ASKPASS" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w timeout 25s ssh \
    -o ConnectTimeout=6 \
    -o ConnectionAttempts=1 \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -o NumberOfPasswordPrompts=1 \
    -o StrictHostKeyChecking=accept-new \
    "$ROBOT_USER@$MOTION_HOST" "$@"
}

if [[ "$mode" != "--check" ]]; then
  require_pc_stop
fi

ssh_motion bash -s -- \
  "$mode" "$CONTAINER" "$CONFIG_PATH" "$TASK_NAME" \
  "$ORIGINAL_SHA256" "$ARMS_ONLY_SHA256" <<'REMOTE'
set -Eeuo pipefail

mode="$1"
container="$2"
config_path="$3"
task_name="$4"
original_sha="$5"
arms_only_sha="$6"
state_dir="$HOME/.local/share/cruzr-pico-arms-only"
backup="$state_dir/cruzr_clamp_pico_tele.vendor.yaml"
overlay="$state_dir/cruzr_clamp_pico_tele.arms-only.yaml"

[[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || {
  printf 'CONTAINER_NOT_RUNNING=%s\n' "$container" >&2
  exit 20
}

container_sha() {
  docker exec "$container" sha256sum "$config_path" | awk '{print $1}'
}

verify_overlay_semantics() {
  local file="$1"
  [[ "$(grep -c '^    waist_mode: 0$' "$file")" == "1" ]]
  [[ "$(grep -c '^    leg_mode: 0$' "$file")" == "1" ]]
  [[ "$(grep -c '^    limb_mode: 2$' "$file")" == "1" ]]
  [[ "$(grep -c '^  collision_detection: true$' "$file")" == "1" ]]
  [[ "$(grep -c '^  hand_type: "clamp"' "$file")" == "1" ]]
}

current_sha="$(container_sha)"
case "$current_sha" in
  "$original_sha") config_state="vendor-full-body" ;;
  "$arms_only_sha") config_state="arms-only" ;;
  *)
    printf 'UNEXPECTED_CONFIG_SHA256=%s\n' "$current_sha" >&2
    exit 21
    ;;
esac

if [[ "$mode" == "--install" ]]; then
  mkdir -p "$state_dir"
  if [[ ! -f "$backup" ]]; then
    [[ "$current_sha" == "$original_sha" ]] || {
      printf 'ORIGINAL_BACKUP_MISSING=1\n' >&2
      exit 22
    }
    docker cp "$container:$config_path" "$backup" >/dev/null
  fi
  [[ "$(sha256sum "$backup" | awk '{print $1}')" == "$original_sha" ]] || {
    printf 'INVALID_ORIGINAL_BACKUP=1\n' >&2
    exit 23
  }
  if [[ ! -f "$overlay" ]]; then
    cp -- "$backup" "$overlay"
    sed -i \
      -e 's/^    waist_mode: 1$/    waist_mode: 0/' \
      -e 's/^    leg_mode: 2$/    leg_mode: 0/' \
      "$overlay"
  fi
  [[ "$(sha256sum "$overlay" | awk '{print $1}')" == "$arms_only_sha" ]] || {
    printf 'INVALID_ARMS_ONLY_OVERLAY=1\n' >&2
    exit 24
  }
  verify_overlay_semantics "$overlay" || {
    printf 'INVALID_ARMS_ONLY_SEMANTICS=1\n' >&2
    exit 25
  }
  docker cp "$overlay" "$container:$config_path" >/dev/null
  current_sha="$(container_sha)"
  [[ "$current_sha" == "$arms_only_sha" ]] || exit 26
  config_state="arms-only"
  printf 'ARMS_ONLY_OVERLAY_INSTALLED=1\n'
  printf 'ACTIVE_TASK_RESTART_REQUIRED=1\n'
elif [[ "$mode" == "--rollback" ]]; then
  [[ -f "$backup" ]] || {
    printf 'ORIGINAL_BACKUP_MISSING=1\n' >&2
    exit 27
  }
  [[ "$(sha256sum "$backup" | awk '{print $1}')" == "$original_sha" ]] || exit 28
  docker cp "$backup" "$container:$config_path" >/dev/null
  current_sha="$(container_sha)"
  [[ "$current_sha" == "$original_sha" ]] || exit 29
  config_state="vendor-full-body"
  printf 'VENDOR_CONFIG_RESTORED=1\n'
  printf 'ACTIVE_TASK_RESTART_REQUIRED=1\n'
fi

printf 'PICO_TELEOP_CONFIG_STATE=%s\n' "$config_state"
printf 'PICO_TELEOP_CONFIG_SHA256=%s\n' "$current_sha"
printf 'VENDOR_SHA256=%s\nARMS_ONLY_SHA256=%s\n' "$original_sha" "$arms_only_sha"

latest="$(find /etc/walker/log/motion -maxdepth 1 -type f -name 'robot_app*.log' -printf '%T@ %p\n' | sort -nr | sed -n '1p' | cut -d' ' -f2-)"
last_start="$(grep -n "BTree task: '$task_name' is start" "$latest" | tail -n1 | cut -d: -f1 || true)"
loaded_waist="unknown"
loaded_leg="unknown"
if [[ -n "$last_start" ]]; then
  block="$(sed -n "${last_start},$((last_start + 79))p" "$latest")"
  loaded_waist="$(sed -nE 's/.*Waist tele mode: ([0-9]+).*/\1/p' <<<"$block" | sed -n '1p')"
  loaded_leg="$(sed -nE 's/.*Leg tele mode: ([0-9]+).*/\1/p' <<<"$block" | sed -n '1p')"
fi
printf 'LOADED_WAIST_MODE=%s\nLOADED_LEG_MODE=%s\n' \
  "${loaded_waist:-unknown}" "${loaded_leg:-unknown}"
if [[ "$current_sha" == "$arms_only_sha" && "$loaded_waist" == "0" && "$loaded_leg" == "0" ]]; then
  printf 'ARMS_ONLY_LOADED=1\n'
else
  printf 'ARMS_ONLY_LOADED=0\n'
fi
REMOTE
