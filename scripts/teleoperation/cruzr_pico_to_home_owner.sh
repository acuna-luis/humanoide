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

--check      Pruebas locales; no conecta ni mueve.
--install    Instala tarea y entrada en task_list con un E-stop accionado.
--reload     Reinicia sólo manipulation_task_manager con un E-stop accionado.
--preflight  Lectura en vivo; exige tarea cargada y una referencia PICO inmóvil.
--run        Repite preflight, exige confirmación humana exacta, ejecuta una vez
             y comprueba HOME con una muestra nueva. Nunca reintenta.

Revisión open_v2, cuatro etapas (80 s nominales):
1. Abre los hombros hacia fuera a -0,60 rad: 10 s.
2. Baja los brazos manteniendo esa apertura: 40 s.
3. Lleva cabeza/elevador/cintura a cero con brazos aún abiertos: 15 s.
4. Cierra únicamente los hombros de los brazos ya bajados hacia HOME: 15 s.
Esta revisión debe instalarse y recargarse: no ejecuta la tarea antigua.
Reconoce dos referencias completas: brazos PICO con cuerpo flexionado original
o brazos PICO con cabeza/elevador/cintura a cero. Tolerancia: 0,02 rad por eje;
no admite posiciones corporales intermedias ni cualquier postura de teleoperación.
Conserva las protecciones Motion. No certifica el interpolador ni la parada.
EOF
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly XML_SOURCE="$SCRIPT_DIR/tasks/cruzr_pico_to_home_owner.xml"
readonly XML_SHA="6b8309f3c29025baf4d7116888c4f64a4f3a86f0cd74e226642203c194dd6999"
readonly PATH_MODEL="$SCRIPT_DIR/cruzr_pico_home_open_path.py"
readonly ENDPOINT_GATE="$SCRIPT_DIR/cruzr_pico_to_home_owner_gate.py"
readonly HOME_GATE="$REPO_ROOT/scripts/lib/cruzr_home_posture_gate.py"
readonly LIVE_AUDITOR="$REPO_ROOT/scripts/vla/audit_vla_live_preflight_e6_0g.sh"
readonly NEW_EVIDENCE="$REPO_ROOT/scripts/vla/new_vla_evidence_run.sh"
readonly CONTACT_LOCK="$REPO_ROOT/scripts/lib/cruzr_contact_motion_lock.sh"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly CONTAINER="walker-motion.manipulation_robot_app-1"
readonly TASK_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly TASK_LIST="$TASK_ROOT/task_list.yaml"
readonly TASK_KEY="pico_to_home_open_v2"
readonly TASK_NAME="cruzr/pico_to_home_open_v2"
readonly XML_TARGET="$TASK_ROOT/cruzr/pico_to_home_open_v2.xml"
readonly INSTALL_CONFIRMATION="INSTALO PICO A HOME: E-STOP ACCIONADO, ROBOT ESTABLE, CARGADOR DESCONECTADO Y ZONA DESPEJADA"
readonly RELOAD_CONFIRMATION="RECARGO PICO A HOME: E-STOP ACCIONADO, ROBOT ESTABLE, CARGADOR DESCONECTADO Y ZONA DESPEJADA"
readonly RUN_CONFIRMATION="EJECUTO PICO A HOME BAJO MI SUPERVISION: POSTURA PICO MEDIDA, ABRAZADERAS VACIAS, SIN CONTACTO, ZONA COMPLETA DESPEJADA, CARGADOR DESCONECTADO, RUEDAS BLOQUEADAS, OTROS MANDOS DETENIDOS Y MANO EN E-STOP; ACEPTO INTERPOLADOR Y PARADA NO CERTIFICADOS"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == 1 ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE=""
while (($#)); do
  case "$1" in
    --check|--install|--reload|--preflight|--run)
      [[ -z "$MODE" ]] || die "indique un solo modo"
      MODE="${1#--}"
      ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; die "argumento desconocido: $1" ;;
  esac
  shift
done
[[ -n "$MODE" ]] || MODE=check

for tool in awk cp date find flock grep nc python3 readlink scp setsid sha256sum sort ssh tee timeout xargs; do
  command -v "$tool" >/dev/null || die "falta herramienta local: $tool"
done
for required in "$XML_SOURCE" "$PATH_MODEL" "$ENDPOINT_GATE" "$HOME_GATE" "$LIVE_AUDITOR" \
  "$NEW_EVIDENCE" "$CONTACT_LOCK"; do
  [[ -s "$required" ]] || die "falta archivo: $required"
done
[[ "$(sha256sum "$XML_SOURCE" | awk '{print $1}')" == "$XML_SHA" ]] || \
  die "el XML local no coincide con el hash revisado"
python3 - "$SCRIPT_DIR" "$XML_SOURCE" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from cruzr_pico_home_open_path import validate_xml
validate_xml(sys.argv[2])
PY

if [[ "$MODE" == check ]]; then
  python3 -m unittest "$SCRIPT_DIR/test_cruzr_pico_to_home_owner_gate.py"
  printf 'LOCAL_CHECK_OK=xml-exact,endpoint-gate-tests-pass,default-no-motion\n'
  printf 'TRAJECTORY=open-10s,lower-open-40s,body-home-open-15s,close-lowered-arms-15s\n'
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
  local value
  value="$($LIVE_AUDITOR --check --expect-active-estop)"
  grep -Eq '^ESTOP_KEY=1$|^SERVO_ESTOP_KEY=1$' <<<"$value"
  grep -Fq 'CHARGER=0' <<<"$value"
  grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$value"
  printf '%s\n' "$value"
}
released_preflight() {
  local value
  value="$($LIVE_AUDITOR --check --expect-released)"
  grep -Fq 'ESTOP_KEY=0' <<<"$value"
  grep -Fq 'SERVO_ESTOP_KEY=0' <<<"$value"
  grep -Fq 'CHARGER=0' <<<"$value"
  grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$value"
  grep -Fq 'CANONICAL_MANIPULATION_PREFLIGHT=passed-read-only' <<<"$value"
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
  if ((started > mtime)); then printf 'RUNTIME_STATE=loaded\n'; else printf 'RUNTIME_STATE=reload-required\n'; fi
else
  printf 'INSTALL_STATE=conflict\n'; exit 40
fi
REMOTE
}
capture_state() {
  local joint_file="$1" actuator_file="$2"
  run_ssh "docker exec '$CONTAINER' bash -lc 'set +u; source /opt/walker/setup.bash; set -u; timeout 8 rosa topic echo --once --no-daemon /mc/whole_joint_states'" >"$joint_file"
  run_ssh "docker exec '$CONTAINER' bash -lc 'set +u; source /opt/walker/setup.bash; set -u; timeout 8 rosa topic echo --once --no-daemon /mc/actuator_state'" >"$actuator_file"
}
gate_live_state() {
  local directory="$1" expected="$2" label="$3"
  capture_state "$directory/$label-joints.yaml" "$directory/$label-actuators.json"
  python3 "$HOME_GATE" <"$directory/$label-actuators.json" | tee "$directory/$label-actuator-gate.log"
  python3 "$ENDPOINT_GATE" --input "$directory/$label-joints.yaml" --expect "$expected" \
    --output "$directory/$label-endpoint-gate.json" | tee "$directory/$label-endpoint-gate.log"
}
finalize_evidence() {
  local directory="$1"
  (cd "$directory" && find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum) >"$directory/evidence.sha256"
  (cd "$directory" && sha256sum -c evidence.sha256 >/dev/null)
}

nc -z -w3 "$MOTION_HOST" 22 || die "Motion no responde en $MOTION_HOST:22"

if [[ "$MODE" == install ]]; then
  preflight="$(active_estop_preflight)"; printf '%s\n' "$preflight"
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
  printf 'INSTALL_EVIDENCE=%s\nNEXT=mantenga E-stop y ejecute --reload\n' "$run_dir"
  exit 0
fi

if [[ "$MODE" == reload ]]; then
  preflight="$(active_estop_preflight)"; printf '%s\n' "$preflight"
  before="$(remote_state)"; printf '%s\n' "$before"
  grep -Fq 'INSTALL_STATE=exact' <<<"$before" || die "falta la revisión open_v2: use --install y --reload con E-stop accionado; la tarea antigua no se reutiliza"
  if grep -Fq 'RUNTIME_STATE=loaded' <<<"$before"; then
    printf 'RELOAD_NOOP=already-loaded\n'; exit 0
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
printf 'RELOAD_OK=1\nMOVEMENT_COMMANDS=0\nSTARTED_BEFORE=%s\nSTARTED_AFTER=%s\n' "$old" "$new"
REMOTE
  sleep 3
  after="$(remote_state)"; printf '%s\n' "$after" | tee "$run_dir/runtime-after.log"
  grep -Fq 'RUNTIME_STATE=loaded' <<<"$after"
  active_estop_preflight >"$run_dir/preflight-after.log"
  finalize_evidence "$run_dir"
  printf 'RELOAD_EVIDENCE=%s\nNEXT=libere E-stop bajo supervisión y ejecute --preflight\n' "$run_dir"
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
preflight="$(released_preflight)"; printf '%s\n' "$preflight" | tee "$work_dir/preflight-before.log"
runtime="$(remote_state)"; printf '%s\n' "$runtime" | tee "$work_dir/runtime-before.log"
grep -Fq 'INSTALL_STATE=exact' <<<"$runtime" || die "falta la revisión open_v2: use --install y --reload con E-stop accionado; la tarea antigua no se reutiliza"
grep -Fq 'RUNTIME_STATE=loaded' <<<"$runtime" || die "la tarea necesita --reload con E-stop"
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
La revisión del modelo es offline; la trayectoria nueva aún necesita ensayo
físico. El interpolador Motion y la distancia real de parada no están certificados. El operador decide iniciar
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
