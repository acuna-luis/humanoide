#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/install_vla_ready_entry_tasks_e6_1c.sh --check
  ./scripts/vla/install_vla_ready_entry_tasks_e6_1c.sh --install-on-disk

Instala atómicamente los dos XML E6.1C y sus entradas exactas en task_list.
Exige un E-stop activo, cargador fuera, VLA detenido, cero publicadores y la
aceptación E6.1C válida. Respalda y revierte ante fallo. No recarga el task
manager, no llama tareas, no publica y no mueve el robot.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly LIVE_AUDITOR="$SCRIPT_DIR/audit_vla_live_preflight_e6_0g.sh"
readonly TRANSITION_AUDITOR="$SCRIPT_DIR/audit_vla_ready_entry_transition_e6_1c.sh"
readonly ACCEPTANCE_AUDITOR="$SCRIPT_DIR/audit_vla_owner_acceptance_e6_1c.sh"
readonly SHADOW="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly NEW_EVIDENCE="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly READY_TO_ENTRY_SOURCE="$SCRIPT_DIR/runtime/tasks/s2_vla_e6_1c_ready_to_entry_preview.xml"
readonly ENTRY_TO_READY_SOURCE="$SCRIPT_DIR/runtime/tasks/s2_vla_e6_1c_entry_to_ready_preview.xml"
readonly EXPECTED_READY_TO_ENTRY_SHA="c1880ccf9b2826a1d5b7b35e38eea8bfbedaab91eb78d6688d414d6701f31fd1"
readonly EXPECTED_ENTRY_TO_READY_SHA="0eee4cbc179ef5d0481eed8a52e35209eb6010bc23a56adc9e1b7c2b638c2bd8"
readonly EXPECTED_TASK_BEFORE_SHA="0d24122cceaf64e9923cae38f251b25db4874f14c907b50725506fde81964957"
readonly EXPECTED_TASK_AFTER_SHA="224c6fca013e59b5dd36ef54cccd732fa48991962b143138e31e1268ba9fac1b"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly CONTAINER="walker-motion.manipulation_robot_app-1"
readonly TASK_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly TASK_LIST="$TASK_ROOT/task_list.yaml"
readonly READY_TO_ENTRY_KEY="s2_vla_e6_1c_ready_to_entry"
readonly ENTRY_TO_READY_KEY="s2_vla_e6_1c_entry_to_ready"
readonly READY_TO_ENTRY_TARGET="$TASK_ROOT/s2_bio_vla/s2_vla_e6_1c_ready_to_entry.xml"
readonly ENTRY_TO_READY_TARGET="$TASK_ROOT/s2_bio_vla/s2_vla_e6_1c_entry_to_ready.xml"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == 1 ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE=check
while (($#)); do
  case "$1" in
    --check|--install-on-disk) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in awk cp date find grep nc readlink scp setsid sha256sum sort ssh tee xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
for source in "$LIVE_AUDITOR" "$TRANSITION_AUDITOR" "$ACCEPTANCE_AUDITOR" \
  "$SHADOW" "$NEW_EVIDENCE" "$READY_TO_ENTRY_SOURCE" "$ENTRY_TO_READY_SOURCE"; do
  test -s "$source" || { printf 'ERROR: falta %s\n' "$source" >&2; exit 1; }
done
[[ "$(sha256sum "$READY_TO_ENTRY_SOURCE" | awk '{print $1}')" == "$EXPECTED_READY_TO_ENTRY_SHA" ]]
[[ "$(sha256sum "$ENTRY_TO_READY_SOURCE" | awk '{print $1}')" == "$EXPECTED_ENTRY_TO_READY_SHA" ]]
"$TRANSITION_AUDITOR" --check >/dev/null
"$ACCEPTANCE_AUDITOR" --check >/dev/null

ssh_options=(
  -o ConnectTimeout=10 -o ConnectionAttempts=1
  -o ServerAliveInterval=15 -o ServerAliveCountMax=3
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

nc -z -w3 "$MOTION_HOST" 22 || { printf 'ERROR: Motion no responde.\n' >&2; exit 1; }
preflight="$($LIVE_AUDITOR --check --expect-active-estop)"
grep -Eq '^ESTOP_KEY=1$|^SERVO_ESTOP_KEY=1$' <<<"$preflight"
grep -Fq 'CHARGER=0' <<<"$preflight"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$preflight"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$preflight"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$preflight"
printf '%s\n' "$preflight"

remote_state="$(run_ssh bash -s -- "$CONTAINER" "$TASK_LIST" \
  "$READY_TO_ENTRY_KEY" "$ENTRY_TO_READY_KEY" \
  "$READY_TO_ENTRY_TARGET" "$ENTRY_TO_READY_TARGET" <<'REMOTE'
set -Eeuo pipefail
container="$1"; task_list="$2"; key_a="$3"; key_b="$4"; xml_a="$5"; xml_b="$6"
test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
printf 'TASK_LIST_SHA256=%s\n' "$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')"
for spec in "A:$key_a:$xml_a" "B:$key_b:$xml_b"; do
  label="${spec%%:*}"; rest="${spec#*:}"; key="${rest%%:*}"; xml="${rest#*:}"
  printf 'TASK_%s_COUNT=%s\n' "$label" "$(docker exec "$container" grep -Fxc "$key:" "$task_list" || true)"
  if docker exec "$container" test -f "$xml"; then
    printf 'XML_%s_PRESENT=1\nXML_%s_SHA256=%s\n' "$label" "$label" \
      "$(docker exec "$container" sha256sum "$xml" | awk '{print $1}')"
  else
    printf 'XML_%s_PRESENT=0\nXML_%s_SHA256=absent\n' "$label" "$label"
  fi
done
REMOTE
)"
printf '%s\n' "$remote_state"
task_sha="$(awk -F= '$1=="TASK_LIST_SHA256" {print $2}' <<<"$remote_state")"
count_a="$(awk -F= '$1=="TASK_A_COUNT" {print $2}' <<<"$remote_state")"
count_b="$(awk -F= '$1=="TASK_B_COUNT" {print $2}' <<<"$remote_state")"
present_a="$(awk -F= '$1=="XML_A_PRESENT" {print $2}' <<<"$remote_state")"
present_b="$(awk -F= '$1=="XML_B_PRESENT" {print $2}' <<<"$remote_state")"
sha_a="$(awk -F= '$1=="XML_A_SHA256" {print $2}' <<<"$remote_state")"
sha_b="$(awk -F= '$1=="XML_B_SHA256" {print $2}' <<<"$remote_state")"
if [[ "$task_sha" == "$EXPECTED_TASK_BEFORE_SHA" && "$count_a" == 0 && "$count_b" == 0 &&
      "$present_a" == 0 && "$present_b" == 0 ]]; then
  install_state=absent
elif [[ "$task_sha" == "$EXPECTED_TASK_AFTER_SHA" && "$count_a" == 1 && "$count_b" == 1 &&
        "$present_a" == 1 && "$present_b" == 1 &&
        "$sha_a" == "$EXPECTED_READY_TO_ENTRY_SHA" && "$sha_b" == "$EXPECTED_ENTRY_TO_READY_SHA" ]]; then
  install_state=installed-on-disk
else
  printf 'ERROR: estado E6.1C remoto no reconocido; no se tocará.\n%s\n' "$remote_state" >&2
  exit 1
fi
printf 'E6.1C_INSTALL_STATE=%s\n' "$install_state"
printf 'E6.1C_INSTALL_PRECONDITIONS_OK=active-estop,charger-off,vla-stopped,publishers-0,acceptance-valid\n'
[[ "$MODE" == install-on-disk ]] || exit 0
[[ "$install_state" == absent ]] || { printf 'ERROR: E6.1C ya está instalado; no se sobrescribe.\n' >&2; exit 1; }

RUN_DIR="$($NEW_EVIDENCE --experiment E6.1C-INSTALL)"
START_TIME="$(date --iso-8601=seconds)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
printf '%s\n' "$preflight" > "$RUN_DIR/preflight-before.log"
printf '%s\n' "$remote_state" > "$RUN_DIR/remote-state-before.log"
cp -- "$SCRIPT_PATH" "$READY_TO_ENTRY_SOURCE" "$ENTRY_TO_READY_SOURCE" "$RUN_DIR/"
token="$(basename -- "$RUN_DIR")"
remote_stage="/home/walker/cruzr-vla/staging/$token"
remote_backup="/home/walker/cruzr-vla/backups/$token"
run_ssh "install -d '$remote_stage' '$remote_backup'"
run_scp "$READY_TO_ENTRY_SOURCE" "$remote_stage/ready_to_entry.xml"
run_scp "$ENTRY_TO_READY_SOURCE" "$remote_stage/entry_to_ready.xml"

install_result="$(run_ssh bash -s -- "$CONTAINER" "$TASK_LIST" \
  "$READY_TO_ENTRY_KEY" "$ENTRY_TO_READY_KEY" \
  "$READY_TO_ENTRY_TARGET" "$ENTRY_TO_READY_TARGET" \
  "$EXPECTED_READY_TO_ENTRY_SHA" "$EXPECTED_ENTRY_TO_READY_SHA" \
  "$EXPECTED_TASK_BEFORE_SHA" "$EXPECTED_TASK_AFTER_SHA" \
  "$remote_stage" "$remote_backup" <<'REMOTE'
set -Eeuo pipefail
container="$1"; task_list="$2"; key_a="$3"; key_b="$4"; xml_a="$5"; xml_b="$6"
sha_a="$7"; sha_b="$8"; before="$9"; after="${10}"; stage="${11}"; backup="${12}"
new_list="$backup/task_list.with_e6_1c.yaml"
task_replaced=0; installed_a=0; installed_b=0
rollback() {
  rc=$?; trap - EXIT
  if ((rc != 0)); then
    if ((task_replaced)); then
      docker cp "$backup/task_list.yaml" "$container:/tmp/task_list.e6_1c.rollback" >/dev/null
      docker exec "$container" mv /tmp/task_list.e6_1c.rollback "$task_list"
    fi
    ((installed_a == 0)) || docker exec "$container" rm -f -- "$xml_a"
    ((installed_b == 0)) || docker exec "$container" rm -f -- "$xml_b"
  fi
  rm -rf -- "$stage"
  exit "$rc"
}
trap rollback EXIT
test "$(sha256sum "$stage/ready_to_entry.xml" | awk '{print $1}')" = "$sha_a"
test "$(sha256sum "$stage/entry_to_ready.xml" | awk '{print $1}')" = "$sha_b"
test "$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')" = "$before"
! docker exec "$container" grep -Fqx "$key_a:" "$task_list"
! docker exec "$container" grep -Fqx "$key_b:" "$task_list"
! docker exec "$container" test -e "$xml_a"
! docker exec "$container" test -e "$xml_b"
docker cp "$container:$task_list" "$backup/task_list.yaml" >/dev/null
test "$(sha256sum "$backup/task_list.yaml" | awk '{print $1}')" = "$before"
mode="$(docker exec "$container" stat -c '%a' "$task_list")"
uid="$(docker exec "$container" stat -c '%u' "$task_list")"
gid="$(docker exec "$container" stat -c '%g' "$task_list")"
cp -- "$backup/task_list.yaml" "$new_list"
printf '\n%s:\n  motion_id: "s2_bio_vla/%s"\n  json_args: '\''{"Reverse": false,"TimeRatio": 1.0}'\''\n  cmd: "start"\n\n%s:\n  motion_id: "s2_bio_vla/%s"\n  json_args: '\''{"Reverse": false,"TimeRatio": 1.0}'\''\n  cmd: "start"\n' \
  "$key_a" "$key_a" "$key_b" "$key_b" >> "$new_list"
test "$(sha256sum "$new_list" | awk '{print $1}')" = "$after"
docker exec "$container" install -d "$(dirname -- "$xml_a")"
docker cp "$stage/ready_to_entry.xml" "$container:/tmp/e6_1c_a.xml" >/dev/null
docker exec "$container" chmod 0644 /tmp/e6_1c_a.xml
docker exec "$container" mv /tmp/e6_1c_a.xml "$xml_a"; installed_a=1
docker cp "$stage/entry_to_ready.xml" "$container:/tmp/e6_1c_b.xml" >/dev/null
docker exec "$container" chmod 0644 /tmp/e6_1c_b.xml
docker exec "$container" mv /tmp/e6_1c_b.xml "$xml_b"; installed_b=1
docker cp "$new_list" "$container:/tmp/task_list.e6_1c.new" >/dev/null
docker exec "$container" chown "$uid:$gid" /tmp/task_list.e6_1c.new
docker exec "$container" chmod "$mode" /tmp/task_list.e6_1c.new
docker exec "$container" mv /tmp/task_list.e6_1c.new "$task_list"; task_replaced=1
test "$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')" = "$after"
test "$(docker exec "$container" sha256sum "$xml_a" | awk '{print $1}')" = "$sha_a"
test "$(docker exec "$container" sha256sum "$xml_b" | awk '{print $1}')" = "$sha_b"
printf 'REMOTE_BACKUP=%s\n' "$backup"
printf 'TASK_LIST_AFTER_SHA256=%s\n' "$after"
printf 'E6.1C_TASKS_INSTALLED_ON_DISK=1\nTASK_MANAGER_RELOADED=0\nMOVEMENT_COMMANDS_PUBLISHED=0\n'
rm -rf -- "$stage"; trap - EXIT
REMOTE
)"
printf '%s\n' "$install_result" | tee "$RUN_DIR/install-result.log"
grep -Fq 'E6.1C_TASKS_INSTALLED_ON_DISK=1' <<<"$install_result"
grep -Fq 'TASK_MANAGER_RELOADED=0' <<<"$install_result"
grep -Fq 'MOVEMENT_COMMANDS_PUBLISHED=0' <<<"$install_result"
shadow_after="$($SHADOW --status)"
printf '%s\n' "$shadow_after" > "$RUN_DIR/vla-status-after.log"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$shadow_after"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.1C-INSTALL
run_id: $(basename -- "$RUN_DIR")
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_E6_1C_TASKS_INSTALLED_ON_DISK_NOT_RELOADED
task_list_before_sha256: $EXPECTED_TASK_BEFORE_SHA
task_list_after_sha256: $EXPECTED_TASK_AFTER_SHA
ready_to_entry_xml_sha256: $EXPECTED_READY_TO_ENTRY_SHA
entry_to_ready_xml_sha256: $EXPECTED_ENTRY_TO_READY_SHA
remote_backup: $(awk -F= '$1=="REMOTE_BACKUP" {print $2}' <<<"$install_result")
task_manager_reloaded: false
physical_movement_commanded: false
physical_publishers: 0
next_gate: RELOAD_DEDICATED_TASK_MANAGER_UNDER_ACTIVE_ESTOP
EOF
(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.1C_INSTALL_EVIDENCE_OK=%s\n' "$RUN_DIR"
