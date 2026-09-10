#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/teleoperation/cruzr_pico_to_home_owner.sh --check
  ./scripts/teleoperation/cruzr_pico_to_home_owner.sh --install
  ./scripts/teleoperation/cruzr_pico_to_home_owner.sh --reload
  ./scripts/teleoperation/cruzr_pico_to_home_owner.sh --preflight
  ./scripts/teleoperation/cruzr_pico_to_home_owner.sh --run
  ./scripts/teleoperation/cruzr_pico_to_home_owner.sh --run --speed 3
  ./scripts/teleoperation/cruzr_pico_to_home_owner.sh --run --speed 4

--check      Pruebas locales; no conecta ni mueve.
--install    Instala tarea y entrada en task_list con un E-stop accionado.
--reload     Reinicia sólo manipulation_task_manager con un E-stop accionado.
             No recupera Motion después de un paro ni autoriza liberarlo.
--preflight  Lectura en vivo; exige tarea cargada y una referencia PICO inmóvil.
--run        Repite preflight, exige confirmación humana exacta, ejecuta una vez
             y comprueba HOME con una muestra nueva. Nunca reintenta.
             Si ambas lecturas frescas ya demuestran HOME, termina sin mover.
--speed N    Perfil 1 (original), 3 o 4 (predeterminado); válido en todos los modos.
             Movimiento nominal: 80 s, 26,666 s o 20 s, respectivamente.
             Los perfiles 3/4 se instalan por separado con --install --speed N
             y deben estar cargados antes de ejecutar --run --speed N.

Perfil 1 de referencia, cuatro etapas (80 s nominales; perfil 4 divide por cuatro):
1. Abre los hombros hacia fuera a -0,60 rad: 10 s.
2. Baja los brazos manteniendo esa apertura: 40 s.
3. Lleva cabeza/elevador/cintura a cero con brazos aún abiertos: 15 s.
4. Cierra únicamente los hombros de los brazos ya bajados hacia HOME: 15 s.
Esta revisión debe instalarse y recargarse: no ejecuta la tarea antigua.
Prepare la instalación con los brazos abajo y vacíos antes de pasar a PICO.
Tras el E-stop, siga la recuperación de arranque documentada antes del preflight.
Reconoce dos referencias completas: brazos PICO con cuerpo flexionado original
o brazos PICO con cabeza/elevador/cintura a cero. Tolerancia: 0,02 rad por eje;
no admite posiciones corporales intermedias ni cualquier postura de teleoperación.
Los perfiles rápidos conservan objetivos/orden; sólo dividen las duraciones.
Conserva las protecciones Motion. No certifica el interpolador ni la parada;
el éxito del perfil original no valida el seguimiento a mayor velocidad.
EOF
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly PATH_MODEL="$SCRIPT_DIR/cruzr_pico_home_open_path.py"
readonly ENDPOINT_GATE="$SCRIPT_DIR/cruzr_pico_to_home_owner_gate.py"
readonly HOME_GATE="$REPO_ROOT/scripts/lib/cruzr_home_posture_gate.py"
readonly LIVE_AUDITOR="$REPO_ROOT/scripts/vla/audit_vla_live_preflight_e6_0g.sh"
readonly NEW_EVIDENCE="$REPO_ROOT/scripts/vla/new_vla_evidence_run.sh"
readonly CONTACT_LOCK="$REPO_ROOT/scripts/lib/cruzr_contact_motion_lock.sh"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly CONTAINER="walker-motion.manipulation_robot_app-1"
readonly TASK_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly TASK_LIST="$TASK_ROOT/task_list.yaml"
readonly INSTALL_CONFIRMATION="INSTALO PICO A HOME: E-STOP ACCIONADO, BRAZOS ABAJO, ABRAZADERAS VACIAS, ROBOT ESTABLE, CARGADOR DESCONECTADO Y ZONA DESPEJADA"
readonly RELOAD_CONFIRMATION="RECARGO PICO A HOME: E-STOP ACCIONADO, BRAZOS ABAJO, ABRAZADERAS VACIAS, ROBOT ESTABLE, CARGADOR DESCONECTADO Y ZONA DESPEJADA"
readonly BASE_RUN_CONFIRMATION="EJECUTO PICO A HOME BAJO MI SUPERVISION: POSTURA PICO MEDIDA, ABRAZADERAS VACIAS, SIN CONTACTO, ZONA COMPLETA DESPEJADA, CARGADOR DESCONECTADO, RUEDAS BLOQUEADAS, OTROS MANDOS DETENIDOS Y MANO EN E-STOP; ACEPTO INTERPOLADOR Y PARADA NO CERTIFICADOS"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == 1 ]]; then
  exec python3 "$REPO_ROOT/scripts/lib/cruzr_ssh_askpass.py"
fi

MODE=""
SPEED=4
SPEED_SET=0
while (($#)); do
  case "$1" in
    --check|--install|--reload|--preflight|--run)
      [[ -z "$MODE" ]] || die "indique un solo modo"
      MODE="${1#--}"
      ;;
    --speed)
      [[ $# -ge 2 && "$SPEED_SET" == 0 ]] || die "--speed exige un valor y no puede repetirse"
      case "$2" in 1|3|4) SPEED="$2" ;; *) die "--speed sólo admite 1, 3 o 4" ;; esac
      SPEED_SET=1
      shift
      ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; die "argumento desconocido: $1" ;;
  esac
  shift
done
[[ -n "$MODE" ]] || MODE=check
readonly SPEED
case "$SPEED" in
  1)
    XML_SOURCE="$SCRIPT_DIR/tasks/cruzr_pico_to_home_owner.xml"
    XML_SHA="6b8309f3c29025baf4d7116888c4f64a4f3a86f0cd74e226642203c194dd6999"
    TASK_KEY="pico_to_home_open_v2"
    RUN_CONFIRMATION="$BASE_RUN_CONFIRMATION"
    ;;
  3)
    XML_SOURCE="$SCRIPT_DIR/tasks/cruzr_pico_to_home_open_v2_3x.xml"
    XML_SHA="f66e53b2d2d582ab48d0468ceb621c620c846201ec5fd5087d7c52870218d8da"
    TASK_KEY="pico_to_home_open_v2_3x"
    RUN_CONFIRMATION="$BASE_RUN_CONFIRMATION; VELOCIDAD=3X"
    ;;
  4)
    XML_SOURCE="$SCRIPT_DIR/tasks/cruzr_pico_to_home_open_v2_4x.xml"
    XML_SHA="6dd482a70e8ec55e02f125eb442b483a12a7c591959e72965214fcc9e02027dc"
    TASK_KEY="pico_to_home_open_v2_4x"
    RUN_CONFIRMATION="$BASE_RUN_CONFIRMATION; VELOCIDAD=4X"
    ;;
esac
readonly XML_SOURCE XML_SHA TASK_KEY RUN_CONFIRMATION
readonly TASK_NAME="cruzr/$TASK_KEY"
readonly XML_TARGET="$TASK_ROOT/cruzr/$TASK_KEY.xml"

for tool in awk cp date find flock grep nc python3 readlink scp setsid sha256sum sort ssh tee timeout xargs; do
  command -v "$tool" >/dev/null || die "falta herramienta local: $tool"
done
for required in "$XML_SOURCE" "$PATH_MODEL" "$ENDPOINT_GATE" "$HOME_GATE" "$LIVE_AUDITOR" \
  "$NEW_EVIDENCE" "$CONTACT_LOCK"; do
  [[ -s "$required" ]] || die "falta archivo: $required"
done
[[ "$(sha256sum "$XML_SOURCE" | awk '{print $1}')" == "$XML_SHA" ]] || \
  die "el XML local no coincide con el hash revisado"
python3 - "$SCRIPT_DIR" "$XML_SOURCE" "$SPEED" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from cruzr_pico_home_open_path import validate_xml, stage_durations, STAGE_NAMES, task_key
speed = int(sys.argv[3])
validate_xml(sys.argv[2], speed)
durations = stage_durations(speed)
print(f'SPEED_FACTOR={speed}')
print(f'TASK_NAME=cruzr/{task_key(speed)}')
print(f'NOMINAL_MOVEMENT_SECONDS={sum(durations):.3f}')
print('TRAJECTORY=' + ','.join(f'{name}:{duration:g}s' for name,duration in zip(STAGE_NAMES,durations)))
PY

if [[ "$MODE" == check ]]; then
  python3 -m unittest "$SCRIPT_DIR/test_cruzr_pico_to_home_owner_gate.py"
  printf 'LOCAL_CHECK_OK=xml-exact,endpoint-gate-tests-pass,default-no-motion\n'
  printf 'EXECUTION=not-started\n'
  exit 0
fi

bash "$CONTACT_LOCK" "pico-to-home-owner:$MODE" || exit $?
exec 9>"/tmp/cruzr-pico-to-home-owner.lock"
flock -n 9 || die "ya hay otro flujo local de movimiento en curso"

ssh_options=(
  -o ConnectTimeout=10 -o ConnectionAttempts=1
  -o ServerAliveInterval=10 -o ServerAliveCountMax=2
  -o PreferredAuthentications=password -o PubkeyAuthentication=no
  -o NumberOfPasswordPrompts=2 -o StrictHostKeyChecking=accept-new
)
run_ssh() {
  CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
    DISPLAY="${DISPLAY:-:0}" setsid -w ssh "${ssh_options[@]}" \
    "$ROBOT_USER@$MOTION_HOST" "$@"
}
run_scp() {
  CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
    DISPLAY="${DISPLAY:-:0}" setsid -w scp "${ssh_options[@]}" \
    "$1" "$ROBOT_USER@$MOTION_HOST:$2"
}
read_confirmation() {
  local expected="$1" answer
  [[ -t 0 ]] || die "este modo exige una terminal y confirmación humana directa"
  printf '\nEscriba exactamente:\n%s\n' "$expected"
  IFS= read -r answer
  [[ "$answer" == "$expected" ]] || die "confirmación incorrecta; operación cancelada"
}
active_estop_preflight() {
  local value status
  value="$("$LIVE_AUDITOR" --check --expect-active-estop)" || {
    status=$?; printf '%s\n' "$value"; return "$status";
  }
  # Bash clears errexit in command substitutions: every required check must
  # return explicitly instead of letting the final printf hide its failure.
  grep -Eq '^ESTOP_KEY=1$|^SERVO_ESTOP_KEY=1$' <<<"$value" &&
    grep -Fxq 'CHARGER=0' <<<"$value" &&
    grep -Fxq 'COMMAND_PATH_SAFE=publishers:0' <<<"$value" || {
      printf '%s\n' "$value"; return 1;
    }
  printf '%s\n' "$value"
}
released_preflight() {
  local value status
  value="$("$LIVE_AUDITOR" --check --expect-released)" || {
    status=$?; printf '%s\n' "$value"; return "$status";
  }
  grep -Fxq 'ESTOP_KEY=0' <<<"$value" &&
    grep -Fxq 'SERVO_ESTOP_KEY=0' <<<"$value" &&
    grep -Fxq 'CHARGER=0' <<<"$value" &&
    grep -Fxq 'COMMAND_PATH_SAFE=publishers:0' <<<"$value" &&
    grep -Fxq 'CANONICAL_MANIPULATION_PREFLIGHT=passed-read-only' <<<"$value" || {
      printf '%s\n' "$value"; return 1;
    }
  printf '%s\n' "$value"
}
remote_state() {
  run_ssh bash -s -- "$CONTAINER" "$TASK_LIST" "$TASK_KEY" "$XML_TARGET" "$XML_SHA" <<'REMOTE'
set -Eeuo pipefail
container="$1"; task_list="$2"; key="$3"; xml="$4"; expected_xml="$5"
test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
task_sha="$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')"
count="$(docker exec "$container" grep -Fxc "$key:" "$task_list" || true)"
if docker exec "$container" test -f "$xml"; then
  present=1; xml_sha="$(docker exec "$container" sha256sum "$xml" | awk '{print $1}')"
else
  present=0; xml_sha=absent
fi
started="$(date -d "$(docker inspect --format '{{.State.StartedAt}}' "$container")" +%s)"
mtime="$(docker exec "$container" stat -c %Y "$task_list")"
action_info="$(docker exec "$container" bash -lc 'set +u; source /opt/walker/setup.bash; set -u; timeout 8 rosa action info /mc/manipulation/action' 2>/dev/null || true)"
servers="$(awk '/Action server count:/ {print $4; found=1} END {if (!found) print 0}' <<<"$action_info")"
printf 'TASK_LIST_SHA256=%s\nTASK_COUNT=%s\nXML_PRESENT=%s\nXML_SHA256=%s\n' "$task_sha" "$count" "$present" "$xml_sha"
printf 'TASK_LIST_MTIME=%s\nPROCESS_STARTED_EPOCH=%s\nACTION_SERVERS=%s\n' "$mtime" "$started" "$servers"
if [[ "$count" == 0 && "$present" == 0 ]]; then
  printf 'INSTALL_STATE=absent\n'
elif [[ "$count" == 1 && "$present" == 1 && "$xml_sha" == "$expected_xml" ]]; then
  printf 'INSTALL_STATE=exact\n'
  if ((started > mtime)); then
    printf 'TASK_PROCESS_ORDER=after-task-list\n'
  else
    printf 'TASK_PROCESS_ORDER=reload-required\n'
  fi
  if [[ "$servers" == 1 ]]; then
    printf 'RUNTIME_STATE=action-server-ready\n'
  else
    printf 'RUNTIME_STATE=action-server-unavailable\n'
  fi
else
  printf 'INSTALL_STATE=conflict\n'; exit 40
fi
REMOTE
}
capture_state() {
  local joint_file="$1" actuator_file="$2"
  run_ssh "docker exec '$CONTAINER' bash -lc 'set +u; source /opt/walker/setup.bash; set -u; timeout 8 rosa topic echo --once --no-daemon /mc/whole_joint_states'" >"$joint_file" || return $?
  run_ssh "docker exec '$CONTAINER' bash -lc 'set +u; source /opt/walker/setup.bash; set -u; timeout 8 rosa topic echo --once --no-daemon /mc/actuator_state'" >"$actuator_file" || return $?
}
gate_live_state() {
  local directory="$1" expected="$2" label="$3"
  capture_state "$directory/$label-joints.yaml" "$directory/$label-actuators.json"
  python3 "$HOME_GATE" <"$directory/$label-actuators.json" | tee "$directory/$label-actuator-gate.log"
  python3 "$ENDPOINT_GATE" --input "$directory/$label-joints.yaml" --expect "$expected" \
    --output "$directory/$label-endpoint-gate.json" | tee "$directory/$label-endpoint-gate.log"
}
already_home_check() {
  local directory="$1" status
  # The no-op requires a fresh actuator health gate plus the independent
  # JointState endpoint check; never infer HOME from an earlier log.
  capture_state "$directory/initial-joints.yaml" "$directory/initial-actuators.json" || return $?
  python3 "$HOME_GATE" --home-tolerance 0.005 <"$directory/initial-actuators.json" \
    >"$directory/initial-actuator-gate.log" || return $?
  if python3 "$ENDPOINT_GATE" --input "$directory/initial-joints.yaml" --expect home \
    --output "$directory/initial-home-gate.json" >"$directory/initial-home-gate.log"; then
    grep -Fxq 'MEASURED_HOME=1' "$directory/initial-actuator-gate.log" || return 3
    python3 - "$directory/initial-home-gate.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
ok=(r.get('qualified') is True and r['maximum_position_error_rad'] <= .005
    and r['maximum_absolute_velocity_rad_s'] <= .002)
raise SystemExit(0 if ok else 3)
PY
  else
    status=$?
    # 3 means a valid sample is outside HOME. Malformed/missing data aborts.
    return "$status"
  fi
}
finalize_evidence() {
  local directory="$1"
  (cd "$directory" && find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum) >"$directory/evidence.sha256"
  (cd "$directory" && sha256sum -c evidence.sha256 >/dev/null)
}

nc -z -w3 "$MOTION_HOST" 22 || die "Motion no responde en $MOTION_HOST:22"

if [[ "$MODE" == install ]]; then
  preflight="$(active_estop_preflight)" || {
    status=$?; printf '%s\n' "$preflight"; exit "$status";
  }
  printf '%s\n' "$preflight"
  before="$(remote_state)"; printf '%s\n' "$before"
  grep -Fq 'INSTALL_STATE=exact' <<<"$before" && {
    printf 'INSTALL_NOOP=already-exact\n'; exit 0;
  }
  grep -Fq 'INSTALL_STATE=absent' <<<"$before" || die "estado remoto no instalable"
  read_confirmation "$INSTALL_CONFIRMATION"
  run_dir="$($NEW_EVIDENCE --experiment PICO-HOME-OWNER-INSTALL)"
  printf '%s\n' "$preflight" >"$run_dir/preflight.log"
  printf '%s\n' "$before" >"$run_dir/remote-before.log"
  cp -- "$SCRIPT_PATH" "$XML_SOURCE" "$ENDPOINT_GATE" "$PATH_MODEL" "$run_dir/"
  token="$(date -u +%Y%m%dT%H%M%S)-$$"
  stage="/home/walker/cruzr-owner-staging/$token"
  backup="/home/walker/cruzr-owner-backups/$token"
  run_ssh "install -d '$stage' '$backup'"
  run_scp "$XML_SOURCE" "$stage/task.xml"
  before_sha="$(awk -F= '$1=="TASK_LIST_SHA256" {print $2}' <<<"$before")"
  install_result="$(run_ssh bash -s -- "$CONTAINER" "$TASK_LIST" "$TASK_KEY" \
    "$TASK_NAME" "$XML_TARGET" "$XML_SHA" "$before_sha" "$stage" "$backup" <<'REMOTE'
set -Eeuo pipefail
container="$1"; task_list="$2"; key="$3"; task_name="$4"; xml="$5"
xml_sha="$6"; before="$7"; stage="$8"; backup="$9"
new_list="$backup/task_list.with-pico-home.yaml"; list_replaced=0; xml_installed=0
rollback() {
  rc=$?; trap - EXIT
  if ((rc != 0)); then
    if ((list_replaced)); then
      docker cp "$backup/task_list.yaml" "$container:/tmp/task_list.pico-home.rollback" >/dev/null
      docker exec "$container" mv /tmp/task_list.pico-home.rollback "$task_list"
    fi
    ((xml_installed == 0)) || docker exec "$container" rm -f -- "$xml"
  fi
  exit "$rc"
}
trap rollback EXIT
test "$(sha256sum "$stage/task.xml" | awk '{print $1}')" = "$xml_sha"
test "$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')" = "$before"
test "$(docker exec "$container" grep -Fxc "$key:" "$task_list" || true)" -eq 0
! docker exec "$container" test -e "$xml"
docker cp "$container:$task_list" "$backup/task_list.yaml" >/dev/null
test "$(sha256sum "$backup/task_list.yaml" | awk '{print $1}')" = "$before"
mode="$(docker exec "$container" stat -c '%a' "$task_list")"
uid="$(docker exec "$container" stat -c '%u' "$task_list")"
gid="$(docker exec "$container" stat -c '%g' "$task_list")"
cp -- "$backup/task_list.yaml" "$new_list"
printf '\n%s:\n  motion_id: "%s"\n  json_args: '\''{"Reverse": false,"TimeRatio": 1.0}'\''\n  cmd: "start"\n' "$key" "$task_name" >>"$new_list"
docker exec "$container" install -d "$(dirname -- "$xml")"
docker cp "$stage/task.xml" "$container:/tmp/pico_to_home_owner.xml" >/dev/null
docker exec "$container" chmod 0644 /tmp/pico_to_home_owner.xml
docker exec "$container" mv /tmp/pico_to_home_owner.xml "$xml"; xml_installed=1
docker cp "$new_list" "$container:/tmp/task_list.pico-home.new" >/dev/null
docker exec "$container" chown "$uid:$gid" /tmp/task_list.pico-home.new
docker exec "$container" chmod "$mode" /tmp/task_list.pico-home.new
docker exec "$container" mv /tmp/task_list.pico-home.new "$task_list"; list_replaced=1
test "$(docker exec "$container" sha256sum "$xml" | awk '{print $1}')" = "$xml_sha"
printf 'REMOTE_BACKUP=%s\nINSTALL_OK=1\nTASK_MANAGER_RELOADED=0\nMOVEMENT_COMMANDS=0\n' "$backup"
trap - EXIT
REMOTE
)" || die "falló la instalación; se intentó rollback"
  printf '%s\n' "$install_result" | tee "$run_dir/install.log"
  after="$(remote_state)"; printf '%s\n' "$after" | tee "$run_dir/remote-after.log"
  grep -Fq 'INSTALL_STATE=exact' <<<"$after"
  finalize_evidence "$run_dir"
  printf 'INSTALL_EVIDENCE=%s\nNEXT=mantenga E-stop; prepare la carga del perfil --speed %s conforme a la guía de arranque.\n' "$run_dir" "$SPEED"
  exit 0
fi

if [[ "$MODE" == reload ]]; then
  preflight="$(active_estop_preflight)" || {
    status=$?; printf '%s\n' "$preflight"; exit "$status";
  }
  printf '%s\n' "$preflight"
  before="$(remote_state)"; printf '%s\n' "$before"
  grep -Fq 'INSTALL_STATE=exact' <<<"$before" || die "falta el perfil $TASK_NAME: prepare --install --speed $SPEED con brazos abajo y E-stop accionado; no se sustituye por otro perfil"
  if grep -Fxq 'TASK_PROCESS_ORDER=after-task-list' <<<"$before"; then
    printf 'RELOAD_NOOP=process-already-started-after-task-list\n'
    printf 'NEXT=No repita --reload. La recarga no recupera Motion tras el E-stop; siga la guía de arranque y compruebe la postura antes de liberar o reiniciar.\n'
    exit 0
  fi
  read_confirmation "$RELOAD_CONFIRMATION"
  run_dir="$($NEW_EVIDENCE --experiment PICO-HOME-OWNER-RELOAD)"
  printf '%s\n' "$preflight" >"$run_dir/preflight-before.log"
  printf '%s\n' "$before" >"$run_dir/runtime-before.log"
  run_ssh bash -s -- "$CONTAINER" <<'REMOTE' | tee "$run_dir/reload.log"
set -Eeuo pipefail
container="$1"; old="$(docker inspect --format '{{.State.StartedAt}}' "$container")"
timeout 30 docker restart --time 10 "$container" >/dev/null
test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
new="$(docker inspect --format '{{.State.StartedAt}}' "$container")"; test "$new" != "$old"
printf 'PROCESS_RESTARTED=1\nMOVEMENT_COMMANDS=0\nSTARTED_BEFORE=%s\nSTARTED_AFTER=%s\n' "$old" "$new"
REMOTE
  sleep 3
  after="$(remote_state)"; printf '%s\n' "$after" | tee "$run_dir/runtime-after.log"
  grep -Fxq 'TASK_PROCESS_ORDER=after-task-list' <<<"$after"
  active_estop_preflight >"$run_dir/preflight-after.log"
  finalize_evidence "$run_dir"
  printf 'RELOAD_EVIDENCE=%s\n' "$run_dir"
  printf 'NEXT=Mantenga E-stop: reiniciar este proceso no recupera Motion. Siga docs/guides/CRUZR_V020_BOOT_GUARD.md; sólo tras recuperar el arranque y verificar la postura, ejecute --preflight --speed %s.\n' "$SPEED"
  printf 'PICO_CAUTION=Si los brazos siguen elevados en PICO, no libere ni reinicie para probar: el HOME interno puede usar otra trayectoria.\n'
  exit 0
fi

temporary=""
if [[ "$MODE" == preflight ]]; then
  temporary="$(mktemp -d /tmp/cruzr-pico-home-preflight.XXXXXX)"
  trap 'rm -r -- "$temporary"' EXIT
  work_dir="$temporary"
else
  work_dir="$($NEW_EVIDENCE --experiment PICO-HOME-OWNER-RUN)"
fi
printf 'SPEED_FACTOR=%s\nTASK_NAME=%s\nXML_SHA256=%s\n' "$SPEED" "$TASK_NAME" "$XML_SHA" >"$work_dir/speed-profile.log"
if [[ "$MODE" == run ]]; then
  cp -- "$SCRIPT_PATH" "$XML_SOURCE" "$PATH_MODEL" "$work_dir/"
fi
preflight="$(released_preflight)" || {
  status=$?
  printf '%s\n' "$preflight" | tee "$work_dir/preflight-before.log"
  printf 'PREFLIGHT_FAILED=1; no se consultará ni enviará la trayectoria.\n' >&2
  [[ "$MODE" != run ]] || finalize_evidence "$work_dir"
  exit "$status"
}
printf '%s\n' "$preflight" | tee "$work_dir/preflight-before.log"
if already_home_check "$work_dir"; then
  printf 'RESULT=ALREADY_HOME_MEASURED\nMOVEMENT_COMMANDS=0\n' | tee "$work_dir/result.log"
  [[ "$MODE" != run ]] || finalize_evidence "$work_dir"
  exit 0
else
  initial_state_rc=$?
  if ((initial_state_rc != 3)); then
    printf 'ERROR: no se pudo comprobar la postura inicial; no se enviará movimiento.\n' >&2
    [[ "$MODE" != run ]] || finalize_evidence "$work_dir"
    exit "$initial_state_rc"
  fi
fi
runtime="$(remote_state)"; printf '%s\n' "$runtime" | tee "$work_dir/runtime-before.log"
grep -Fq 'INSTALL_STATE=exact' <<<"$runtime" || die "falta el perfil $TASK_NAME: prepare --install --speed $SPEED con brazos abajo y E-stop accionado; no se sustituye por otro perfil"
grep -Fxq 'TASK_PROCESS_ORDER=after-task-list' <<<"$runtime" || die "la tarea necesita recarga; prepárela con brazos abajo siguiendo la guía, no improvise un E-stop/reinicio desde PICO"
grep -Fq 'ACTION_SERVERS=1' <<<"$runtime" || die "servidor de acciones no disponible"
gate_live_state "$work_dir" pico before
printf 'PICO_HOME_PREFLIGHT_OK=recognized-pico-reference,stationary,healthy,exclusive-control\n'
if [[ "$MODE" == preflight ]]; then
  printf 'MOVEMENT_COMMANDS=0\n'; exit 0
fi

cat <<'EOF'

ADVERTENCIA DEL EJECUTOR
La revisión open_v2 abre antes de bajar y mantiene los brazos abiertos al
recoger el cuerpo. El contacto anterior impide reutilizar la trayectoria antigua.
El operador ha comunicado que el perfil original funciona bien. Los perfiles
rápidos aún necesitan ensayo físico propio: conservar los objetivos no demuestra
el mismo seguimiento ni la misma parada a mayor velocidad.
El interpolador Motion y la distancia real de parada no están certificados. El operador decide iniciar
la prueba física, debe observar todo el recorrido y accionar inmediatamente el
E-stop ante aproximación, contacto, ruido, tirón o movimiento inesperado.
EOF
read_confirmation "$RUN_CONFIRMATION"
printf '%s\n' "$RUN_CONFIRMATION" >"$work_dir/operator-confirmation.txt"
gate_live_state "$work_dir" pico before-command
trap 'printf "INTERRUPCION: accione el E-stop; no se hará reintento.\n" >&2; exit 130' INT TERM
set +e
run_ssh bash -s -- "$CONTAINER" "$TASK_NAME" <<'REMOTE' | tee "$work_dir/action.log"
set -Eeuo pipefail
container="$1"; task="$2"
set +e
output="$(docker exec -i "$container" bash -s -- "$task" 2>&1 <<'INNER'
set -Eeo pipefail
set +u; source /opt/walker/setup.bash; set -u
task="$1"
timeout 120 rosa action send_goal /mc/manipulation/action mc_task_msgs/action/ArmTask \
  "{\"task_name\":\"$task\",\"yaml_args\":\"{}\"}"
INNER
)" 2>&1
rc=$?
set -e
printf '%s\n' "$output"
((rc == 0)) || exit "$rc"
grep -q "'desc': 'SUCCEED'" <<<"$output"
grep -q 'status=4' <<<"$output"
REMOTE
action_rc=${PIPESTATUS[0]}
set -e
if ((action_rc != 0)); then
  printf 'RESULT=ACTION_FAILED_NO_RETRY\nAccione el E-stop y diagnostique antes de cualquier otra orden.\n' | tee "$work_dir/result.log" >&2
  finalize_evidence "$work_dir"
  exit 1
fi
gate_live_state "$work_dir" home after
after_preflight="$(released_preflight)"; printf '%s\n' "$after_preflight" >"$work_dir/preflight-after.log"
printf 'RESULT=HOME_MEASURED\nAUTOMATIC_RETRY=0\n' | tee "$work_dir/result.log"
finalize_evidence "$work_dir"
printf 'PICO_TO_HOME_COMPLETED=1\nEVIDENCE=%s\n' "$work_dir"
