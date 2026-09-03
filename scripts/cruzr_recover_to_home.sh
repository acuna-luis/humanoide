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
readonly MOTION_CONTAINER="walker-motion.manipulation_robot_app-1"
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
readonly POSTURE_GATE="$SCRIPT_DIR/lib/cruzr_home_posture_gate.py"

# No mover por omisión. El incidente del 28-08 demostró que una clasificación
# histórica correcta (teleoperated_pose) no basta para elegir una trayectoria.
MODE="check"
YES=0
FAST=0
FORCE_HELD_HOME=0
TASK_LOCKED=""
RESET_SERVICE_AVAILABLE=""
RETREAT_REQUIRED=""
MANIPULATION_STATE=""
HISTORICAL_STATE=""
MEASURED_HOME=""
UNSAFE_EVENT_LINE="0"
UNSAFE_EVENT="none"
UNSAFE_AFTER_STATE=""
HOME_ACTION_REQUIRED=""
VISION_HOST=""

usage() {
  cat <<'EOF'
Uso:
  ./scripts/cruzr_recover_to_home.sh
  ./scripts/cruzr_recover_to_home.sh --check
  ./scripts/cruzr_recover_to_home.sh --run [--yes] [--fast]
  ./scripts/cruzr_recover_to_home.sh --self-test

Modos:
  sin opción
           Equivale a --check. Nunca mueve por omisión.
  --check  Comprueba conexión, paros, batería, cargador y servicios. No
           cambia estados ni mueve el robot. Además exige una muestra fresca
           de los 20 ejes y clasifica la ruta de recuperación.
  --run    Sólo ejecuta movimiento si la muestra fresca ya es home o el último
           estado pertenece al ciclo de caja conocido. Una postura PICO,
           indeterminada, con autocolisión, fuerza o fault queda bloqueada.
  --self-test
           Ejecuta regresiones locales del gate; no conecta con el robot.

Opciones:
  --yes    Omite sólo la pregunta interactiva en un flujo exterior ya
           confirmado. Nunca omite el gate de postura, actuadores o eventos.
  --fast   Compatibilidad con flujos exteriores. Ya no omite ninguna auditoría
           de seguridad de return-to-home.
  --force-held-home
           Retirado: el incidente real demostró que la apertura vendor puede
           aumentar el contacto desde una postura PICO cruzada.
  --help   Muestra esta ayuda.

Antes de --run:
  - Si caja y mesa siguen delante, deben permanecer estables y sin personas.
  - Debe haber al menos 1,50 m libres detrás del robot.
  - Mantén a todas las personas fuera del alcance de brazos, cabeza,
    cintura y elevador.
  - Las abrazaderas deben estar vacías y con espacio libre debajo y a ambos
    lados durante la ruta restringida del ciclo de caja.
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
    --self-test)
      MODE="self-test"
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

((FORCE_HELD_HOME == 0)) || \
  die "--force-held-home fue retirado: desde una postura PICO cruzada produjo sobreesfuerzo y faults."

require_local_tools() {
  local command_name
  for command_name in ssh setsid nc flock readlink grep python3; do
    command -v "$command_name" >/dev/null 2>&1 || \
      die "Falta el comando local '$command_name'."
  done
  [[ -x "$CYCLE_SCRIPT" ]] || \
    die "No existe o no es ejecutable: $CYCLE_SCRIPT"
  [[ -x "$CARRY_SCRIPT" ]] || \
    die "No existe o no es ejecutable: $CARRY_SCRIPT"
  [[ -r "$POSTURE_GATE" ]] || \
    die "No existe el gate de postura: $POSTURE_GATE"
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

last_regex_record() {
  local pattern="$1"
  grep -nE "$pattern" "$latest" | tail -n1 || true
}

home_line="$(last_line "BTree task: 'cruzr/home' is start")"
safe_home_line="$(last_line "BTree task: 'cruzr/open_arm_before_home' is start")"
teleop_line="$(last_line "BTree task: 'teleoperation/cruzr_clamp_pico_teleoperation' is start")"
ready_line="$(last_line "BTree task: 'transport/clamp_ready_cruzr' is start")"
clamp_line="$(last_line "BTree task: 'cruzr/blue_workbin_clamp_only' is start")"
deposit_line="$(last_line "BTree task: 'cruzr/blue_workbin_auto_deposit' is start")"
open_line="$(last_line 'Start MetaClamp: byd/open_arm_cruzr')"
unsafe_record="$(last_regex_record 'Excessive force|Self collision between|Collision detected, command not sent|MoveToGoalFailed|Operation disabled unexpected|SAFEOP ERROR|servo [0-9]+ error code:0x(1001|1003|2007)')"

home_line="${home_line:-0}"
safe_home_line="${safe_home_line:-0}"
teleop_line="${teleop_line:-0}"
ready_line="${ready_line:-0}"
clamp_line="${clamp_line:-0}"
deposit_line="${deposit_line:-0}"
open_line="${open_line:-0}"
unsafe_line="${unsafe_record%%:*}"
[[ "$unsafe_line" =~ ^[0-9]+$ ]] || unsafe_line=0

unsafe_event=none
if [[ "$unsafe_record" == *"Excessive force"* ]]; then
  unsafe_event=excessive_force
elif [[ "$unsafe_record" == *"Self collision between"* || "$unsafe_record" == *"Collision detected, command not sent"* ]]; then
  unsafe_event=self_collision
elif [[ "$unsafe_record" == *"MoveToGoalFailed"* ]]; then
  unsafe_event=move_to_goal_failed
elif [[ "$unsafe_record" == *"Operation disabled unexpected"* || "$unsafe_record" == *"error code:0x"* ]]; then
  unsafe_event=servo_fault
elif [[ "$unsafe_record" == *"SAFEOP ERROR"* ]]; then
  unsafe_event=ethercat_safeop
fi

printf 'MOTION_LOG=%s\n' "$latest"
printf 'HOME_LINE=%s\nSAFE_HOME_LINE=%s\nTELEOP_LINE=%s\nREADY_LINE=%s\nCLAMP_LINE=%s\nDEPOSIT_LINE=%s\nOPEN_LINE=%s\n' \
  "$home_line" "$safe_home_line" "$teleop_line" "$ready_line" "$clamp_line" "$deposit_line" "$open_line"
printf 'UNSAFE_EVENT_LINE=%s\nUNSAFE_EVENT=%s\n' "$unsafe_line" "$unsafe_event"

home_attempt_line="$home_line"
((safe_home_line > home_attempt_line)) && home_attempt_line="$safe_home_line"
latest_state_line="$home_attempt_line"
historical_state=home_attempted_unverified

if ((teleop_line > latest_state_line)); then
  latest_state_line="$teleop_line"
  historical_state=teleoperated_pose
fi
if ((ready_line > latest_state_line)); then
  latest_state_line="$ready_line"
  historical_state=arms_extended_near_table
fi
if ((clamp_line > latest_state_line)); then
  latest_state_line="$clamp_line"
  historical_state=box_may_be_held
fi
if ((deposit_line > latest_state_line)); then
  latest_state_line="$deposit_line"
  if ((open_line > deposit_line)); then
    historical_state=deposited_open_near_table
  else
    historical_state=deposit_result_unverified
  fi
fi
if ((latest_state_line == 0)); then
  historical_state=unknown
fi

unsafe_after_state=0
if ((unsafe_line > latest_state_line)); then
  unsafe_after_state=1
fi
printf 'LATEST_STATE_LINE=%s\nHISTORICAL_STATE=%s\nUNSAFE_AFTER_STATE=%s\n' \
  "$latest_state_line" "$historical_state" "$unsafe_after_state"
REMOTE
)" || die "No se pudo determinar la postura actual desde el registro de motion."

  printf '%s\n' "$output"
  HISTORICAL_STATE="$(awk -F= '/^HISTORICAL_STATE=/ {print $2; exit}' <<<"$output")"
  UNSAFE_EVENT_LINE="$(awk -F= '/^UNSAFE_EVENT_LINE=/ {print $2; exit}' <<<"$output")"
  UNSAFE_EVENT="$(awk -F= '/^UNSAFE_EVENT=/ {print $2; exit}' <<<"$output")"
  UNSAFE_AFTER_STATE="$(awk -F= '/^UNSAFE_AFTER_STATE=/ {print $2; exit}' <<<"$output")"
  [[ -n "$HISTORICAL_STATE" && "$UNSAFE_AFTER_STATE" =~ ^[01]$ ]] || \
    die "El registro no produjo una clasificación histórica válida."
}

query_current_posture() {
  local actuator_json
  local output

  actuator_json="$(ssh_motion bash -s -- "$MOTION_CONTAINER" <<'REMOTE'
set -Eeuo pipefail
container="$1"
[[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]]
docker exec "$container" bash -lc '
  source /opt/walker/setup.bash
  timeout 8 rosa topic echo --once --no-daemon /mc/actuator_state
'
REMOTE
)" || die "No se obtuvo una muestra fresca de /mc/actuator_state."

  if ! output="$(python3 "$POSTURE_GATE" <<<"$actuator_json" 2>&1)"; then
    printf '%s\n' "$output" >&2
    die "La muestra fresca de actuadores no permite seleccionar una ruta de home."
  fi
  printf '%s\n' "$output"
  MEASURED_HOME="$(awk -F= '/^MEASURED_HOME=/ {print $2; exit}' <<<"$output")"
  [[ "$MEASURED_HOME" =~ ^[01]$ ]] || \
    die "El gate de postura no devolvió MEASURED_HOME válido."
}

select_recovery_route() {
  if [[ "$MEASURED_HOME" == "1" ]]; then
    MANIPULATION_STATE="home_measured"
    RETREAT_REQUIRED="false"
    HOME_ACTION_REQUIRED="false"
    info "RECOVERY_ROUTE=already-home,no-motion"
    return 0
  fi

  if [[ "$UNSAFE_AFTER_STATE" == "1" ]]; then
    die "Evento inseguro '$UNSAFE_EVENT' posterior al último estado conocido; no se enviará ninguna trayectoria."
  fi

  case "$HISTORICAL_STATE" in
    deposited_open_near_table|arms_extended_near_table)
      MANIPULATION_STATE="$HISTORICAL_STATE"
      RETREAT_REQUIRED="true"
      HOME_ACTION_REQUIRED="true"
      info "RECOVERY_ROUTE=known-workbin,retreat-then-vendor-home"
      ;;
    teleoperated_pose)
      die "Postura PICO no home: open_arm_before_home está prohibido desde este estado. Vuelva a home dentro de PICO antes de STOP o use recuperación controlada sin otra trayectoria."
      ;;
    box_may_be_held|deposit_result_unverified)
      die "El registro no demuestra abrazaderas vacías y depósito completado; no se enviará home."
      ;;
    home_attempted_unverified)
      die "Existe un intento de home, pero los 20 ejes no están en cero; no se repetirá la trayectoria."
      ;;
    unknown|*)
      die "Estado histórico '$HISTORICAL_STATE' y postura no home: no existe una trayectoria automática demostrada."
      ;;
  esac
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
  info "Clasificando el último estado y buscando fuerza, autocolisión o faults..."
  detect_manipulation_state
  info "Comprobando postura 20D, velocidad y consignas mediante una muestra fresca..."
  query_current_posture
  select_recovery_route
  if [[ "$RETREAT_REQUIRED" == "true" ]]; then
    info "Comprobando el canal autónomo de separación de la mesa..."
    "$CARRY_SCRIPT" --check
  fi
  info "RECOVERY_CHECK_OK: no se cambió ningún estado ni se movió el robot."
}

confirm_run() {
  ((YES == 0)) || return 0
  cat <<'EOF'

RUTA RESTRINGIDA DEL CICLO DE CAJA
La recuperación retrocederá el chasis 0,50 m y sólo después ejecutará la
secuencia vendor desde una postura de caja reconocida. Confirma que la caja y
la mesa fueron retiradas, que las abrazaderas están vacías, que hay 1,50 m
libres detrás, que nadie está en la envolvente y que el paro está preparado.

Escribe RECUPERAR CICLO DE CAJA A HOME para continuar:
EOF
  local answer
  read -r answer
  [[ "$answer" == "RECUPERAR CICLO DE CAJA A HOME" ]] || die "Recuperación cancelada."
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
    info "FAST_COMPATIBILITY_ONLY=1; no se omite ningún gate de return-to-home."
  fi
  preflight

  if [[ "$HOME_ACTION_REQUIRED" == "false" ]]; then
    cat <<'EOF'

HOME YA VERIFICADO — CERO OBJETIVOS ENVIADOS
Los 20 ejes de cuerpo están inmóviles, sin fault, con consignas coincidentes y
abs(position)<0,02 rad. No se ejecutó reset, retroceso ni trayectoria home.
EOF
    return 0
  fi

  confirm_run

  if [[ "$RETREAT_REQUIRED" == "true" ]]; then
    info "[1/4] Separando el robot 0,50 m de la mesa..."
    "$CARRY_SCRIPT" --retreat-only --yes
  else
    if [[ "$MANIPULATION_STATE" == "home" ]]; then
      info "[1/4] El robot ya consta en home; no es necesario mover el chasis."
    else
      info "[1/4] Postura $MANIPULATION_STATE: no se moverá el chasis."
    fi
  fi

  info "[2/4] Releyendo el lock de tareas después del retroceso..."
  check_reset_service
  if [[ "$TASK_LOCKED" == "true" ]]; then
    info "[2/4] Saliendo del estado de misión mediante DO_RESET=9..."
    reset_task_state
    check_reset_service
    [[ "$TASK_LOCKED" == "false" ]] || \
      die "DO_RESET fue aceptado, pero la máquina de tareas continúa bloqueada."
  else
    info "[2/4] Máquina de tareas libre; se omite DO_RESET=9."
  fi

  # Repetimos todos los gates después del retroceso/reset. Así no se manda
  # home si durante la transición apareció un paro, fault, consigna latente o
  # evento de fuerza/colisión. --fast ya no puede omitir esta barrera.
  info "[3/4] Revalidando actuadores, registro y ruta después de la transición..."
  "$CYCLE_SCRIPT" --check
  detect_manipulation_state
  query_current_posture
  select_recovery_route
  if [[ "$HOME_ACTION_REQUIRED" == "false" ]]; then
    info "HOME_REACHED_DURING_TRANSITION=1; no se enviará una trayectoria redundante."
    return 0
  fi

  info "[4/4] Ejecutando home vendor sólo desde el estado conocido '$MANIPULATION_STATE'..."
  CRUZR_VALIDATED_HOME_STATE="$MANIPULATION_STATE" \
  CRUZR_VALIDATED_HOME_GATE="workbin-history-and-actuators-v1" \
    "$CYCLE_SCRIPT" --home-workbin-internal --yes

  info "Verificando el resultado físico articular, no sólo status=4..."
  "$CYCLE_SCRIPT" --check
  query_current_posture
  [[ "$MEASURED_HOME" == "1" ]] || \
    die "La acción terminó, pero la muestra 20D no demuestra home; no se repetirá."

  cat <<'EOF'

RECUPERACIÓN COMPLETADA Y MEDIDA
La máquina de tareas salió del estado anterior y la ruta vendor restringida al
ciclo de caja terminó con status de éxito y postura 20D < 0,02 rad.
Si los brazos estaban junto a la mesa, el chasis quedó 0,50 m más atrás. No se
reinició ningún contenedor.
EOF
}

make_test_snapshot() {
  local position="$1"
  local velocity="$2"
  local command_delta="$3"
  local fault_id="${4:-0}"
  local id_scheme="${5:-legacy}"
  python3 - "$position" "$velocity" "$command_delta" "$fault_id" "$id_scheme" <<'PY'
import json
import sys

position = float(sys.argv[1])
velocity = float(sys.argv[2])
command_delta = float(sys.argv[3])
fault_id = int(sys.argv[4])
id_scheme = sys.argv[5]
middle_ids = {
    "legacy": [2001, 2002, 2003, 3001],
    "v0.2.0": [11004, 11003, 11002, 11001],
}.get(id_scheme)
if middle_ids is None:
    raise SystemExit(f"unknown test id scheme: {id_scheme}")
ids = [1001, 1002, *middle_ids, *range(4001, 4008), *range(5001, 5008)]
items = []
for index, actuator_id in enumerate(ids):
    value = position if index == 0 else 0.0
    items.append({
        "id": actuator_id,
        "name": f"test_{actuator_id}",
        "error_code": 0x1003 if actuator_id == fault_id else 0,
        "status": 0x123f if actuator_id == fault_id else 0x1237,
        "position": value,
        "velocity": velocity if index == 0 else 0.0,
        "cmd_pos": value + (command_delta if index == 0 else 0.0),
    })
print(json.dumps({"act_item": items}))
PY
}

run_self_test() {
  local output
  local snapshot

  snapshot="$(make_test_snapshot 0.0 0.0 0.0)"
  output="$(python3 "$POSTURE_GATE" <<<"$snapshot")"
  grep -q '^MEASURED_HOME=1$' <<<"$output" || die "self-test: home no reconocido."

  snapshot="$(make_test_snapshot 0.0 0.0 0.0 0 v0.2.0)"
  output="$(python3 "$POSTURE_GATE" <<<"$snapshot")"
  grep -q '^MEASURED_HOME=1$' <<<"$output" || die "self-test: IDs v0.2.0 no reconocidos."

  snapshot="$(make_test_snapshot 0.30 0.0 0.0)"
  output="$(python3 "$POSTURE_GATE" <<<"$snapshot")"
  grep -q '^MEASURED_HOME=0$' <<<"$output" || die "self-test: non-home no reconocido."

  snapshot="$(make_test_snapshot 0.0 0.0 0.10)"
  if python3 "$POSTURE_GATE" <<<"$snapshot" >/dev/null 2>&1; then
    die "self-test: una consigna latente fue aceptada."
  fi

  snapshot="$(make_test_snapshot 0.0 0.03 0.0)"
  if python3 "$POSTURE_GATE" <<<"$snapshot" >/dev/null 2>&1; then
    die "self-test: un actuador en movimiento fue aceptado."
  fi

  snapshot="$(make_test_snapshot 0.0 0.0 0.0 4003)"
  if python3 "$POSTURE_GATE" <<<"$snapshot" >/dev/null 2>&1; then
    die "self-test: un fault 4003 fue aceptado."
  fi

  snapshot="$(python3 -c 'import json,sys; data=json.load(sys.stdin); data["act_item"] = data["act_item"][:-1]; print(json.dumps(data))' <<<"$(make_test_snapshot 0.0 0.0 0.0)")"
  if python3 "$POSTURE_GATE" <<<"$snapshot" >/dev/null 2>&1; then
    die "self-test: una muestra 20D incompleta fue aceptada."
  fi

  if (MEASURED_HOME=0; HISTORICAL_STATE=teleoperated_pose; UNSAFE_AFTER_STATE=0; select_recovery_route) >/dev/null 2>&1; then
    die "self-test: una postura PICO no-home fue aceptada."
  fi
  if (MEASURED_HOME=0; HISTORICAL_STATE=deposited_open_near_table; UNSAFE_AFTER_STATE=1; UNSAFE_EVENT=excessive_force; select_recovery_route) >/dev/null 2>&1; then
    die "self-test: un evento de fuerza fue aceptado."
  fi
  if (MEASURED_HOME=0; HISTORICAL_STATE=home_attempted_unverified; UNSAFE_AFTER_STATE=1; UNSAFE_EVENT=excessive_force; select_recovery_route) >/dev/null 2>&1; then
    die "self-test: el incidente open_arm_before_home fue aceptado."
  fi
  (
    MEASURED_HOME=0
    HISTORICAL_STATE=deposited_open_near_table
    UNSAFE_AFTER_STATE=0
    select_recovery_route
    [[ "$HOME_ACTION_REQUIRED" == "true" && "$RETREAT_REQUIRED" == "true" ]]
  ) >/dev/null || die "self-test: la ruta conocida de caja fue rechazada."

  info "RECOVERY_SELF_TEST_OK=legacy-home,v0.2.0-home,non-home,latent-command,moving,fault,missing-axis,pico-block,failed-home-block,force-block,known-workbin"
}

main() {
  require_local_tools

  if [[ "$MODE" == "self-test" ]]; then
    run_self_test
    return 0
  fi

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
