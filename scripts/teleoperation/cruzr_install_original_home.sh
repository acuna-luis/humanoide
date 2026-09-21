#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/teleoperation/cruzr_install_original_home.sh --check
  ./scripts/teleoperation/cruzr_install_original_home.sh --status
  ./scripts/teleoperation/cruzr_install_original_home.sh --install
  ./scripts/teleoperation/cruzr_install_original_home.sh --reload

Instala el HOME original de fábrica (SHA 50d819d6…) como tarea adicional
cruzr/originalhome. No toca cruzr/home (el HOME propio instalado).

--check    Comprobación local del XML; no conecta.
--status   Lectura del robot: XML, entrada en task_list y orden de carga.
--install  Copia el XML y añade la entrada en task_list con un E-stop accionado.
--reload   Reinicia sólo manipulation_task_manager con un E-stop accionado.
           No recupera Motion después de un paro ni autoriza liberarlo.

Este script nunca envía la tarea. El HOME original mueve cabeza, elevador,
cintura y ambos brazos a cero en paralelo en 6 s: es la trayectoria directa
que acercó los brazos al cuerpo (MOT-01). No lo ejecute con carga, con
brazos cruzados/delante del torso ni fuera de un ensayo supervisado.
EOF
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly LIVE_AUDITOR="$REPO_ROOT/scripts/vla/audit_vla_live_preflight_e6_0g.sh"
readonly NEW_EVIDENCE="$REPO_ROOT/scripts/vla/new_vla_evidence_run.sh"
readonly CONTACT_LOCK="$REPO_ROOT/scripts/lib/cruzr_contact_motion_lock.sh"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly CONTAINER="walker-motion.manipulation_robot_app-1"
readonly TASK_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly TASK_LIST="$TASK_ROOT/task_list.yaml"
readonly XML_SOURCE="$SCRIPT_DIR/tasks/cruzr_home_original_factory.xml"
readonly XML_SHA="50d819d6d6190280c6efee1dc275877362c3f7c807ec733fbc3c7ed217daed88"
readonly TASK_KEY="cruzr_originalhome"
readonly TASK_NAME="cruzr/originalhome"
readonly XML_TARGET="$TASK_ROOT/$TASK_NAME.xml"
# Mismos json_args que la entrada de fábrica cruzr_home.
readonly JSON_ARGS='{"Reverse": false,"TimeRatio": 0.5}'
readonly INSTALL_CONFIRMATION="INSTALO HOME ORIGINAL COMO CRUZR/ORIGINALHOME: E-STOP ACCIONADO, BRAZOS ABAJO, ABRAZADERAS VACIAS, ROBOT ESTABLE Y CARGADOR DESCONECTADO"
readonly RELOAD_CONFIRMATION="RECARGO MANIPULACION PARA CRUZR/ORIGINALHOME: E-STOP ACCIONADO, BRAZOS ABAJO, ABRAZADERAS VACIAS, ROBOT ESTABLE Y CARGADOR DESCONECTADO"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == 1 ]]; then
  exec python3 "$REPO_ROOT/scripts/lib/cruzr_ssh_askpass.py"
fi

MODE=""
while (($#)); do
  case "$1" in
    --check|--status|--install|--reload)
      [[ -z "$MODE" ]] || die "indique un solo modo"
      MODE="${1#--}"
      ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; die "argumento desconocido: $1" ;;
  esac
  shift
done
[[ -n "$MODE" ]] || MODE=check

[[ -s "$XML_SOURCE" ]] || die "falta archivo: $XML_SOURCE"
[[ "$(sha256sum "$XML_SOURCE" | awk '{print $1}')" == "$XML_SHA" ]] || \
  die "el XML local no coincide con el HOME original de fábrica"
python3 - "$XML_SOURCE" <<'PY'
import sys, xml.etree.ElementTree as ET
actions = ET.parse(sys.argv[1]).getroot().findall('.//Action')
assert len(actions) == 5 and all(a.get('ID') == 'MetaMove' for a in actions)
assert {a.get('type') for a in actions} == {'lifter', 'arm', 'waist', 'head'}
PY

if [[ "$MODE" == check ]]; then
  printf 'LOCAL_CHECK_OK=factory-home-exact\nTASK_NAME=%s\nXML_SHA256=%s\nMOVEMENT_COMMANDS=0\n' \
    "$TASK_NAME" "$XML_SHA"
  exit 0
fi

for tool in awk cp date find flock grep nc python3 scp setsid sort ssh tee timeout xargs; do
  command -v "$tool" >/dev/null || die "falta herramienta local: $tool"
done
for required in "$LIVE_AUDITOR" "$NEW_EVIDENCE" "$CONTACT_LOCK"; do
  [[ -s "$required" ]] || die "falta archivo: $required"
done

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
  grep -Eq '^ESTOP_KEY=1$|^SERVO_ESTOP_KEY=1$' <<<"$value" &&
    grep -Fxq 'CHARGER=0' <<<"$value" &&
    grep -Fxq 'COMMAND_PATH_SAFE=publishers:0' <<<"$value" || {
      printf '%s\n' "$value"; return 1;
    }
  printf '%s\n' "$value"
}
remote_state() {
  run_ssh bash -s -- "$CONTAINER" "$TASK_LIST" "$TASK_KEY" "$XML_TARGET" "$XML_SHA" "$TASK_NAME" <<'REMOTE'
set -Eeuo pipefail
container="$1"; task_list="$2"; key="$3"; xml="$4"; expected_xml="$5"; task_name="$6"
test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
task_sha="$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')"
count="$(docker exec "$container" grep -Fxc "$key:" "$task_list" || true)"
motion_refs="$(docker exec "$container" grep -Fc "motion_id: \"$task_name\"" "$task_list" || true)"
home_sha="$(docker exec "$container" sha256sum "$(dirname -- "$xml")/home.xml" | awk '{print $1}')"
if docker exec "$container" test -f "$xml"; then
  present=1; xml_sha="$(docker exec "$container" sha256sum "$xml" | awk '{print $1}')"
else
  present=0; xml_sha=absent
fi
started="$(date -d "$(docker inspect --format '{{.State.StartedAt}}' "$container")" +%s)"
mtime="$(docker exec "$container" stat -c %Y "$task_list")"
printf 'TASK_LIST_SHA256=%s\nTASK_COUNT=%s\nMOTION_ID_REFS=%s\nXML_PRESENT=%s\nXML_SHA256=%s\n' \
  "$task_sha" "$count" "$motion_refs" "$present" "$xml_sha"
printf 'CRUZR_HOME_SHA256=%s\nTASK_LIST_MTIME=%s\nPROCESS_STARTED_EPOCH=%s\n' "$home_sha" "$mtime" "$started"
if [[ "$count" == 0 && "$motion_refs" == 0 && "$present" == 0 ]]; then
  printf 'INSTALL_STATE=absent\n'
elif [[ "$count" == 1 && "$motion_refs" == 1 && "$present" == 1 && "$xml_sha" == "$expected_xml" ]]; then
  printf 'INSTALL_STATE=exact\n'
  if ((started > mtime)); then
    printf 'TASK_PROCESS_ORDER=after-task-list\n'
  else
    printf 'TASK_PROCESS_ORDER=reload-required\n'
  fi
else
  printf 'INSTALL_STATE=conflict\n'; exit 40
fi
REMOTE
}
finalize_evidence() {
  local directory="$1"
  (cd "$directory" && find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum) >"$directory/evidence.sha256"
  (cd "$directory" && sha256sum -c evidence.sha256 >/dev/null)
}

nc -z -w3 "$MOTION_HOST" 22 || die "Motion no responde en $MOTION_HOST:22"

if [[ "$MODE" == status ]]; then
  remote_state
  exit 0
fi

bash "$CONTACT_LOCK" "original-home:$MODE" || exit $?
exec 9>"/tmp/cruzr-original-home.lock"
flock -n 9 || die "ya hay otro flujo local de instalación en curso"

preflight="$(active_estop_preflight)" || {
  status=$?; printf '%s\n' "$preflight"; exit "$status";
}
printf '%s\n' "$preflight"
before="$(remote_state)"; printf '%s\n' "$before"

if [[ "$MODE" == install ]]; then
  grep -Fq 'INSTALL_STATE=exact' <<<"$before" && {
    printf 'INSTALL_NOOP=already-exact\n'; exit 0;
  }
  grep -Fq 'INSTALL_STATE=absent' <<<"$before" || die "estado remoto no instalable"
  read_confirmation "$INSTALL_CONFIRMATION"
  run_dir="$($NEW_EVIDENCE --experiment ORIGINAL-HOME-INSTALL)"
  printf '%s\n' "$preflight" >"$run_dir/preflight.log"
  printf '%s\n' "$before" >"$run_dir/remote-before.log"
  cp -- "$SCRIPT_PATH" "$XML_SOURCE" "$run_dir/"
  token="$(date -u +%Y%m%dT%H%M%S)-$$"
  stage="/home/walker/cruzr-owner-staging/$token"
  backup="/home/walker/cruzr-owner-backups/$token-originalhome"
  run_ssh "install -d '$stage' '$backup'"
  run_scp "$XML_SOURCE" "$stage/task.xml"
  before_sha="$(awk -F= '$1=="TASK_LIST_SHA256" {print $2}' <<<"$before")"
  install_result="$(run_ssh bash -s -- "$CONTAINER" "$TASK_LIST" "$TASK_KEY" \
    "$TASK_NAME" "$XML_TARGET" "$XML_SHA" "$before_sha" "$stage" "$backup" "$JSON_ARGS" <<'REMOTE'
set -Eeuo pipefail
container="$1"; task_list="$2"; key="$3"; task_name="$4"; xml="$5"
xml_sha="$6"; before="$7"; stage="$8"; backup="$9"; json_args="${10}"
new_list="$backup/task_list.with-originalhome.yaml"; list_replaced=0; xml_installed=0
rollback() {
  rc=$?; trap - EXIT
  if ((rc != 0)); then
    if ((list_replaced)); then
      docker cp "$backup/task_list.yaml" "$container:/tmp/task_list.originalhome.rollback" >/dev/null
      docker exec "$container" mv /tmp/task_list.originalhome.rollback "$task_list"
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
printf '\n%s:\n  motion_id: "%s"\n  json_args: '\''%s'\''\n  cmd: "start"\n' "$key" "$task_name" "$json_args" >>"$new_list"
docker cp "$stage/task.xml" "$container:/tmp/originalhome.xml" >/dev/null
docker exec "$container" chmod 0644 /tmp/originalhome.xml
docker exec "$container" mv /tmp/originalhome.xml "$xml"; xml_installed=1
docker cp "$new_list" "$container:/tmp/task_list.originalhome.new" >/dev/null
docker exec "$container" chown "$uid:$gid" /tmp/task_list.originalhome.new
docker exec "$container" chmod "$mode" /tmp/task_list.originalhome.new
docker exec "$container" mv /tmp/task_list.originalhome.new "$task_list"; list_replaced=1
test "$(docker exec "$container" sha256sum "$xml" | awk '{print $1}')" = "$xml_sha"
printf 'REMOTE_BACKUP=%s\nINSTALL_OK=1\nTASK_MANAGER_RELOADED=0\nMOVEMENT_COMMANDS=0\n' "$backup"
trap - EXIT
REMOTE
)" || die "falló la instalación; se intentó rollback"
  printf '%s\n' "$install_result" | tee "$run_dir/install.log"
  after="$(remote_state)"; printf '%s\n' "$after" | tee "$run_dir/remote-after.log"
  grep -Fq 'INSTALL_STATE=exact' <<<"$after"
  finalize_evidence "$run_dir"
  printf 'INSTALL_EVIDENCE=%s\nNEXT=mantenga el E-stop y ejecute --reload para cargar %s.\n' "$run_dir" "$TASK_NAME"
  exit 0
fi

# reload
grep -Fq 'INSTALL_STATE=exact' <<<"$before" || die "instale primero con --install"
if grep -Fxq 'TASK_PROCESS_ORDER=after-task-list' <<<"$before"; then
  printf 'RELOAD_NOOP=process-already-started-after-task-list\n'
  exit 0
fi
read_confirmation "$RELOAD_CONFIRMATION"
run_dir="$($NEW_EVIDENCE --experiment ORIGINAL-HOME-RELOAD)"
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
printf 'NEXT=Mantenga el E-stop: reiniciar este proceso no recupera Motion. Siga docs/guides/CRUZR_V020_BOOT_GUARD.md.\n'
