#!/usr/bin/env bash

set -Eeuo pipefail

# Recupera el Cruzr S2 de un estado de misión retenido (por ejemplo,
# "coger caja") y, después de resetear la máquina de tareas, ejecuta la
# trayectoria oficial cruzr/home. Se lanza desde el PC Ubuntu.

readonly VISION_HOST_DIRECT="192.168.11.3"
readonly VISION_HOST_WIFI="192.168.42.2"
readonly MOTION_HOST="192.168.11.2"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly SYSTEM_CONTAINER="walker-system.backend_service-1"
readonly RESET_COMMAND="9"
readonly CYCLE_SCRIPT_NAME="cruzr_blue_workbin_cycle.sh"
readonly CARRY_SCRIPT_NAME="cruzr_blue_workbin_carry_back.sh"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD

if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

SCRIPT_PATH="$(readlink -f -- "$0")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly SCRIPT_PATH SCRIPT_DIR
readonly CYCLE_SCRIPT="$SCRIPT_DIR/$CYCLE_SCRIPT_NAME"
readonly CARRY_SCRIPT="$SCRIPT_DIR/$CARRY_SCRIPT_NAME"

# El uso normal sin argumentos ejecuta la recuperación. El diagnóstico sin
# movimiento queda disponible de forma explícita mediante --check.
MODE="run"
YES=0
FAST=0
FORCE_HELD_HOME=0
TASK_LOCKED=""
RESET_SERVICE_AVAILABLE=""
RETREAT_REQUIRED=""
MANIPULATION_STATE=""
VISION_HOST=""

usage() {
  cat <<'EOF'
Uso:
  ./scripts/cruzr_recover_to_home.sh
  ./scripts/cruzr_recover_to_home.sh --check
  ./scripts/cruzr_recover_to_home.sh --run [--yes] [--fast]
  ./scripts/cruzr_recover_to_home.sh --run --force-held-home [--yes]

Modos:
  sin opción
           Equivale a --run y solicita la confirmación física antes de mover.
  --check  Comprueba conexión, paros, batería, cargador y servicios. No
           cambia estados ni mueve el robot.
  --run    Detecta si los brazos quedaron junto a la mesa. Si hace falta,
           retrocede 0,50 m; después abre los brazos antes de completar home.

Opciones:
  --yes    Omite la confirmación física inicial.
  --fast   Omite auditorías repetidas y usa las validaciones ya realizadas
           por el transporte; conserva detección de postura y resultados.
  --force-held-home
           Recuperación explícita del propietario desde una postura PICO no
           reconocida o con una caja prescindible posiblemente sujeta. Omite
           sólo la clasificación histórica, no paros, batería, cargador,
           servidor de manipulación, hashes ni resultados. No mueve el chasis:
           separa primero los brazos, por lo que la caja puede caer, y después
           ejecuta home. Es incompatible con --fast.
  --help   Muestra esta ayuda.

Antes de --run:
  - Si caja y mesa siguen delante, deben permanecer estables y sin personas.
  - Debe haber al menos 1,50 m libres detrás del robot.
  - Mantén a todas las personas fuera del alcance de brazos, cabeza,
    cintura y elevador.
  - Las abrazaderas deben estar vacías y con espacio libre debajo y a ambos
    lados durante la apertura previa, salvo con --force-held-home. En ese modo
    la caja debe ser prescindible y toda la zona de caída debe estar libre de
    personas, pies, cables, mesas y objetos que puedan salir despedidos.
  - Robot desenchufado del cargador y paro de emergencia preparado.

El script puede retroceder el chasis, pero nunca vuelve hacia la mesa. No
desactiva servos ni reinicia Docker.
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
    --check)
      MODE="check"
      ;;
    --run)
      MODE="run"
      ;;
    --yes)
      YES=1
      ;;
    --fast)
      FAST=1
      ;;
    --force-held-home)
      FORCE_HELD_HOME=1
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

if ((FORCE_HELD_HOME == 1)); then
  [[ "$MODE" == "run" ]] || \
    die "--force-held-home sólo es válido con --run."
  ((FAST == 0)) || \
    die "--force-held-home exige el preflight completo; no puede combinarse con --fast."
fi

require_local_tools() {
  local command_name
  for command_name in ssh setsid nc flock readlink grep; do
    command -v "$command_name" >/dev/null 2>&1 || \
      die "Falta el comando local '$command_name'."
  done
  [[ -x "$CYCLE_SCRIPT" ]] || \
    die "No existe o no es ejecutable: $CYCLE_SCRIPT"
  [[ -x "$CARRY_SCRIPT" ]] || \
    die "No existe o no es ejecutable: $CARRY_SCRIPT"
}

ssh_vision() {
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
    "$ROBOT_USER@$VISION_HOST" "$@"
}

select_vision_host() {
  if nc -z -w2 "$VISION_HOST_DIRECT" 22 >/dev/null 2>&1; then
    VISION_HOST="$VISION_HOST_DIRECT"
  elif nc -z -w2 "$VISION_HOST_WIFI" 22 >/dev/null 2>&1; then
    VISION_HOST="$VISION_HOST_WIFI"
  else
    die "No se alcanza Vision por Ethernet ($VISION_HOST_DIRECT:22) ni por Wi-Fi ($VISION_HOST_WIFI:22)."
  fi
  info "VISION_CONNECTION=$VISION_HOST"
}

ssh_motion() {
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
    "$ROBOT_USER@$MOTION_HOST" "$@"
}

detect_manipulation_state() {
  local output

  output="$(ssh_motion bash -s <<'REMOTE'
set -Eeuo pipefail
latest="$(find /etc/walker/log/motion -maxdepth 1 -type f \
  -name 'robot_app*.log' -printf '%T@ %p\n' | sort -nr | head -n1 | cut -d' ' -f2-)"
[[ -n "$latest" && -f "$latest" ]] || exit 51

last_line() {
  local pattern="$1"
  grep -nF "$pattern" "$latest" | tail -n1 | cut -d: -f1 || true
}

home_line="$(last_line "BTree task: 'cruzr/home' is start")"
safe_home_line="$(last_line "BTree task: 'cruzr/open_arm_before_home' is start")"
teleop_line="$(last_line "BTree task: 'teleoperation/cruzr_clamp_pico_teleoperation' is start")"
ready_line="$(last_line "BTree task: 'transport/clamp_ready_cruzr' is start")"
clamp_line="$(last_line "BTree task: 'cruzr/blue_workbin_clamp_only' is start")"
deposit_line="$(last_line "BTree task: 'cruzr/blue_workbin_auto_deposit' is start")"
open_line="$(last_line 'Start MetaClamp: byd/open_arm_cruzr')"

home_line="${home_line:-0}"
safe_home_line="${safe_home_line:-0}"
teleop_line="${teleop_line:-0}"
ready_line="${ready_line:-0}"
clamp_line="${clamp_line:-0}"
deposit_line="${deposit_line:-0}"
open_line="${open_line:-0}"

printf 'MOTION_LOG=%s\n' "$latest"
printf 'HOME_LINE=%s\nSAFE_HOME_LINE=%s\nTELEOP_LINE=%s\nREADY_LINE=%s\nCLAMP_LINE=%s\nDEPOSIT_LINE=%s\nOPEN_LINE=%s\n' \
  "$home_line" "$safe_home_line" "$teleop_line" "$ready_line" "$clamp_line" "$deposit_line" "$open_line"

((safe_home_line > home_line)) && home_line="$safe_home_line"

latest_extended="$ready_line"
((clamp_line > latest_extended)) && latest_extended="$clamp_line"
((deposit_line > latest_extended)) && latest_extended="$deposit_line"
((teleop_line > latest_extended)) && latest_extended="$teleop_line"

if ((home_line > latest_extended)); then
  echo 'MANIPULATION_STATE=home'
  echo 'RETREAT_REQUIRED=false'
elif ((teleop_line > home_line && teleop_line >= ready_line && teleop_line >= clamp_line && teleop_line >= deposit_line)); then
  echo 'MANIPULATION_STATE=teleoperated_pose'
  echo 'RETREAT_REQUIRED=false'
elif ((deposit_line > home_line && open_line > deposit_line)); then
  echo 'MANIPULATION_STATE=deposited_open_near_table'
  echo 'RETREAT_REQUIRED=true'
elif ((clamp_line > home_line && clamp_line > deposit_line)); then
  echo 'MANIPULATION_STATE=box_may_be_held'
  echo 'RETREAT_REQUIRED=unsafe'
elif ((ready_line > home_line)); then
  echo 'MANIPULATION_STATE=arms_extended_near_table'
  echo 'RETREAT_REQUIRED=true'
else
  echo 'MANIPULATION_STATE=unknown'
  echo 'RETREAT_REQUIRED=unsafe'
fi
REMOTE
)" || die "No se pudo determinar la postura actual desde el registro de motion."

  printf '%s\n' "$output"
  MANIPULATION_STATE="$(awk -F= '/^MANIPULATION_STATE=/ {print $2; exit}' <<<"$output")"
  RETREAT_REQUIRED="$(awk -F= '/^RETREAT_REQUIRED=/ {print $2; exit}' <<<"$output")"
  [[ -n "$MANIPULATION_STATE" && -n "$RETREAT_REQUIRED" ]] || \
    die "El registro no produjo un estado de manipulación válido."
  if ((FORCE_HELD_HOME == 1)); then
    info "FORCE_HELD_HOME_SOURCE_STATE=$MANIPULATION_STATE"
    MANIPULATION_STATE="owner_forced_held_or_teleop_pose"
    RETREAT_REQUIRED="false"
    info "FORCE_HELD_HOME_ACCEPTED=1; no se moverá el chasis y la apertura previa puede soltar la caja."
  else
    [[ "$RETREAT_REQUIRED" != "unsafe" ]] || \
      die "Estado '$MANIPULATION_STATE': no es seguro ejecutar home automáticamente."
  fi
}

check_reset_service() {
  local output
  select_vision_host

  output="$(ssh_vision bash -s -- "$SYSTEM_CONTAINER" <<'REMOTE'
set -Eeuo pipefail
container="$1"
docker inspect "$container" >/dev/null

docker exec -i "$container" bash -s <<'INNER'
set -Eeo pipefail
set +u
source /opt/walker/setup.bash
set -u

info="$(rosa service info /sys/task/remote_command 2>/dev/null || true)"
if grep -q 'Service server count: 1' <<<"$info"; then
  type="$(rosa service type /sys/task/remote_command)"
  [[ "$type" == "sys_task_msgs/srv/RemoteCommand" ]] || exit 31

  iface="$(rosa msg show sys_task_msgs/srv/RemoteCommand)"
  grep -q 'uint8 RECOVER_ARM = 3' <<<"$iface" || exit 33
  grep -q 'uint8 STOP_ROBOT = 7' <<<"$iface" || exit 34
  grep -q 'uint8 DO_RESET = 9' <<<"$iface" || exit 35
  printf 'RESET_SERVICE=ready\n'
else
  # El backend v0.2.0 no anuncia este servidor en la configuración actual.
  # Un estado libre puede continuar sin reset; uno bloqueado debe detenerse.
  printf 'RESET_SERVICE=unavailable\n'
fi

lock="$(timeout 6 rosa topic echo --once /sys/state/module_lock_info)"
printf '%s\n' "$lock"
INNER
REMOTE
)" || die "El servicio interno de recuperación no superó la comprobación."

  printf '%s\n' "$output"
  if grep -q '^RESET_SERVICE=ready$' <<<"$output"; then
    RESET_SERVICE_AVAILABLE="true"
  elif grep -q '^RESET_SERVICE=unavailable$' <<<"$output"; then
    RESET_SERVICE_AVAILABLE="false"
  else
    die "No se pudo determinar la disponibilidad de DO_RESET."
  fi

  if grep -Eq '"locked"[[:space:]]*:[[:space:]]*true' <<<"$output"; then
    TASK_LOCKED="true"
  elif grep -Eq '"locked"[[:space:]]*:[[:space:]]*false' <<<"$output"; then
    TASK_LOCKED="false"
  else
    die "No se pudo determinar si la máquina interna está bloqueada."
  fi

  if [[ "$TASK_LOCKED" == "true" && "$RESET_SERVICE_AVAILABLE" != "true" ]]; then
    die "La máquina de tareas está bloqueada y v0.2.0 no anuncia DO_RESET; no se enviará home."
  fi
}

preflight() {
  info "Comprobando manipulación, batería, paros y cargador..."
  "$CYCLE_SCRIPT" --check
  info "Comprobando la máquina interna de tareas..."
  check_reset_service
  info "Determinando si los brazos necesitan separarse de la mesa..."
  detect_manipulation_state
  if [[ "$RETREAT_REQUIRED" == "true" ]]; then
    info "Comprobando el canal autónomo de separación de la mesa..."
    "$CARRY_SCRIPT" --check
  fi
  info "RECOVERY_CHECK_OK: no se cambió ningún estado ni se movió el robot."
}

confirm_run() {
  ((YES == 0)) || return 0
  if ((FORCE_HELD_HOME == 1)); then
    cat <<'EOF'

RECUPERACIÓN FORZADA CON POSIBLE CAÍDA DE LA CAJA
La secuencia NO moverá el chasis. Separará primero ambos brazos durante 3 s;
la caja puede caer inmediatamente. Después moverá brazos, cabeza, cintura y
elevador hasta home.

Confirma AHORA que la caja es prescindible, la zona completa debajo y alrededor
está libre de personas, pies, cables, mesas y objetos, el robot está estable,
el cargador está desconectado y una persona atiende el paro.

Escribe exactamente SOLTAR CAJA Y RECUPERAR A HOME para continuar:
EOF
    local force_answer
    read -r force_answer
    [[ "$force_answer" == "SOLTAR CAJA Y RECUPERAR A HOME" ]] || \
      die "Recuperación forzada cancelada."
    return 0
  fi
  cat <<'EOF'

La recuperación puede retroceder el chasis 0,50 m y después mover brazos,
cabeza, cintura y elevador hasta home. Confirma que hay 1,50 m libres detrás,
que nadie está junto al robot ni la mesa y que el paro está preparado.

Escribe RECUPERAR A HOME para continuar:
EOF
  local answer
  read -r answer
  [[ "$answer" == "RECUPERAR A HOME" ]] || die "Recuperación cancelada."
}

reset_task_state() {
  local output
  [[ "$RESET_SERVICE_AVAILABLE" == "true" ]] || \
    die "DO_RESET no está disponible en v0.2.0; no se enviará una orden inexistente."
  output="$(ssh_vision bash -s -- "$SYSTEM_CONTAINER" "$RESET_COMMAND" <<'REMOTE'
set -Eeuo pipefail
container="$1"
reset_command="$2"

docker exec -i "$container" bash -s -- "$reset_command" <<'INNER'
set -Eeo pipefail
set +u
source /opt/walker/setup.bash
set -u
reset_command="$1"

output="$(timeout 12 rosa service call /sys/task/remote_command \
  sys_task_msgs/srv/RemoteCommand \
  "{\"cmd\":${reset_command}}")"
printf '%s\n' "$output"
grep -Eq 'ok[=: ]+True|"ok"[[:space:]]*:[[:space:]]*true' <<<"$output" || exit 41
INNER
REMOTE
)" || die "DO_RESET no fue aceptado; no se enviará home."

  printf '%s\n' "$output"
  info "TASK_RESET_OK: la máquina de tareas aceptó DO_RESET=9."
}

run_recovery() {
  if ((FAST == 1)); then
    info "FAST_MODE: omitiendo auditorías completas previas a la recuperación."
    if [[ "${CRUZR_AFTER_DEPOSIT:-0}" == "1" ]]; then
      RETREAT_REQUIRED="true"
      info "AFTER_DEPOSIT: depósito confirmado por el flujo exterior; se omite el análisis duplicado del registro."
    else
      detect_manipulation_state
    fi
    # v0.2.0 puede no publicar /sys/task/remote_command. Incluso en modo
    # rápido se consulta el lock real y solo se exige DO_RESET si está activo.
    check_reset_service
  else
    preflight
  fi
  confirm_run

  if [[ "$RETREAT_REQUIRED" == "true" ]]; then
    info "[1/4] Separando el robot 0,50 m de la mesa..."
    if ((FAST == 1)); then
      "$CARRY_SCRIPT" --retreat-only --yes --fast
    else
      "$CARRY_SCRIPT" --retreat-only --yes
    fi
  else
    if [[ "$MANIPULATION_STATE" == "home" ]]; then
      info "[1/4] El robot ya consta en home; no es necesario mover el chasis."
    else
      info "[1/4] Postura $MANIPULATION_STATE: no se moverá el chasis."
    fi
  fi

  if [[ "$TASK_LOCKED" == "true" ]]; then
    info "[2/4] Saliendo del estado de misión mediante DO_RESET=9..."
    reset_task_state
  else
    info "[2/4] Máquina de tareas libre; se omite DO_RESET=9."
  fi

  # Repetimos el preflight después del retroceso/reset. Así no se manda home
  # si durante la transición apareció un paro o se conectó el cargador.
  if ((FAST == 0)); then
    info "[3/4] Verificando que manipulación sigue disponible..."
    "$CYCLE_SCRIPT" --check
  else
    info "[3/4] FAST_MODE: verificación completa posterior omitida."
  fi

  info "[4/4] Abriendo primero los brazos y ejecutando después home..."
  if ((FAST == 1)); then
    "$CYCLE_SCRIPT" --home --yes --fast
  else
    "$CYCLE_SCRIPT" --home --yes
  fi

  cat <<'EOF'

RECUPERACIÓN COMPLETADA
La máquina de tareas salió del estado anterior y la secuencia protegida de
apertura previa más home terminó con éxito.
Si los brazos estaban junto a la mesa, el chasis quedó 0,50 m más atrás. No se
reinició ningún contenedor.
EOF
}

main() {
  require_local_tools
  exec 9>"/tmp/cruzr_recover_to_home.lock"
  flock -n 9 || die "Ya hay otra recuperación local en ejecución."

  case "$MODE" in
    check)
      preflight
      ;;
    run)
      run_recovery
      ;;
    *)
      die "Modo interno desconocido: $MODE"
      ;;
  esac
}

main
