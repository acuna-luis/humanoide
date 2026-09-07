#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/reload_vla_ready_entry_tasks_e6_1c.sh --check
  ./scripts/vla/reload_vla_ready_entry_tasks_e6_1c.sh --reload

Recarga sólo manipulation_task_manager para leer las dos tareas E6.1C ya
instaladas. Exige E-stop activo, cargador fuera, VLA detenido, cero
publicadores y confirmación física exacta. No llama tareas ni mueve el robot.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly LIVE_AUDITOR="$SCRIPT_DIR/audit_vla_live_preflight_e6_0g.sh"
readonly ACCEPTANCE_AUDITOR="$SCRIPT_DIR/audit_vla_owner_acceptance_e6_1c.sh"
readonly SHADOW="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly NEW_EVIDENCE="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly CONTAINER="walker-motion.manipulation_robot_app-1"
readonly TASK_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly TASK_LIST="$TASK_ROOT/task_list.yaml"
readonly KEY_A="s2_vla_e6_1c_ready_to_entry"
readonly KEY_B="s2_vla_e6_1c_entry_to_ready"
readonly XML_A="$TASK_ROOT/s2_bio_vla/s2_vla_e6_1c_ready_to_entry.xml"
readonly XML_B="$TASK_ROOT/s2_bio_vla/s2_vla_e6_1c_entry_to_ready.xml"
readonly EXPECTED_TASK_SHA="224c6fca013e59b5dd36ef54cccd732fa48991962b143138e31e1268ba9fac1b"
readonly EXPECTED_XML_A_SHA="c1880ccf9b2826a1d5b7b35e38eea8bfbedaab91eb78d6688d414d6701f31fd1"
readonly EXPECTED_XML_B_SHA="0eee4cbc179ef5d0481eed8a52e35209eb6010bc23a56adc9e1b7c2b638c2bd8"
readonly EXPECTED_CONFIRMATION="AUTORIZO RECARGA E6.1C: AMBOS PAROS ACCIONADOS, ROBOT ESTABLE, CARGADOR DESCONECTADO, ZONA DESPEJADA Y DOS PERSONAS PRESENTES"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == 1 ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE=check
while (($#)); do
  case "$1" in
    --check|--reload) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done
if [[ "$MODE" == reload ]]; then
  bash "$SCRIPT_DIR/../lib/cruzr_contact_motion_lock.sh" "E6.1C:reload" || exit $?
fi
for tool in awk cp date find grep nc readlink setsid sha256sum sort ssh tee timeout xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
for required in "$LIVE_AUDITOR" "$ACCEPTANCE_AUDITOR" "$SHADOW" "$NEW_EVIDENCE"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
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
validate_barriers() {
  local value="$1"
  grep -Eq '^ESTOP_KEY=1$|^SERVO_ESTOP_KEY=1$' <<<"$value"
  grep -Fq 'CHARGER=0' <<<"$value"
  grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$value"
  grep -Fq 'CONTROL_CONTAINER=exited' <<<"$value"
  grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$value"
}
remote_state() {
  run_ssh bash -s -- "$CONTAINER" "$TASK_LIST" "$KEY_A" "$KEY_B" \
    "$XML_A" "$XML_B" "$EXPECTED_TASK_SHA" "$EXPECTED_XML_A_SHA" \
    "$EXPECTED_XML_B_SHA" <<'REMOTE'
set -Eeuo pipefail
container="$1"; task_list="$2"; key_a="$3"; key_b="$4"; xml_a="$5"; xml_b="$6"
expected_task="$7"; expected_a="$8"; expected_b="$9"
test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
task_sha="$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')"
xml_a_sha="$(docker exec "$container" sha256sum "$xml_a" | awk '{print $1}')"
xml_b_sha="$(docker exec "$container" sha256sum "$xml_b" | awk '{print $1}')"
test "$task_sha" = "$expected_task"
test "$xml_a_sha" = "$expected_a"
test "$xml_b_sha" = "$expected_b"
test "$(docker exec "$container" grep -Fxc "$key_a:" "$task_list")" -eq 1
test "$(docker exec "$container" grep -Fxc "$key_b:" "$task_list")" -eq 1
started_at="$(docker inspect --format '{{.State.StartedAt}}' "$container")"
started_epoch="$(date -d "$started_at" +%s)"
task_mtime="$(docker exec "$container" stat -c %Y "$task_list")"
process_count="$(docker top "$container" -eo pid,cmd | awk '
  NR > 1 && $0 ~ /\/opt\/walker\/manipulation_task_manager\/lib\/manipulation_task_manager\/robot_app$/ {count++}
  END {print count + 0}
')"
test "$process_count" -eq 1
printf 'CONTAINER_STATUS=running\nCONTAINER_STARTED_AT=%s\nTASK_LIST_MTIME_EPOCH=%s\n' "$started_at" "$task_mtime"
if ((started_epoch > task_mtime)); then
  printf 'E6.1C_RUNTIME_LOAD_ORDER=process_started_after_config\n'
else
  printf 'E6.1C_RUNTIME_LOAD_ORDER=process_not_started_after_config\n'
fi
printf 'TASK_LIST_SHA256=%s\nXML_A_SHA256=%s\nXML_B_SHA256=%s\nROBOT_APP_PROCESS_COUNT=%s\n' \
  "$task_sha" "$xml_a_sha" "$xml_b_sha" "$process_count"
REMOTE
}

nc -z -w3 "$MOTION_HOST" 22 || { printf 'ERROR: Motion no responde.\n' >&2; exit 1; }
preflight="$($LIVE_AUDITOR --check --expect-active-estop)"
validate_barriers "$preflight"
printf '%s\n' "$preflight"
before="$(remote_state)"
printf '%s\n' "$before"
if [[ "$MODE" == check ]]; then
  printf 'E6.1C_RELOAD_CHECK_OK=exact-config,active-estop,charger-off,vla-stopped,publishers-0\n'
  exit 0
fi

confirmation="${E6_1C_RELOAD_CONFIRMATION:-}"
if [[ -z "$confirmation" && -t 0 ]]; then
  printf 'Escriba exactamente: %s\n' "$EXPECTED_CONFIRMATION"
  IFS= read -r confirmation
fi
[[ "$confirmation" == "$EXPECTED_CONFIRMATION" ]] || {
  printf 'ERROR: confirmación incorrecta; no se recargó.\n' >&2
  exit 2
}

RUN_DIR="$($NEW_EVIDENCE --experiment E6.1C-RELOAD)"
START_TIME="$(date --iso-8601=seconds)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
printf '%s\n' "$preflight" > "$RUN_DIR/preflight-before.log"
printf '%s\n' "$before" > "$RUN_DIR/runtime-before.log"
cp -- "$SCRIPT_PATH" "$RUN_DIR/"
reload_result="$(run_ssh bash -s -- "$CONTAINER" <<'REMOTE'
set -Eeuo pipefail
container="$1"
old="$(docker inspect --format '{{.State.StartedAt}}' "$container")"
timeout 30 docker restart --time 10 "$container" >/dev/null
test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
new="$(docker inspect --format '{{.State.StartedAt}}' "$container")"
test "$new" != "$old"
printf 'CONTAINER_STARTED_BEFORE=%s\nCONTAINER_STARTED_AFTER=%s\n' "$old" "$new"
printf 'TASKS_INVOKED=0\nMOVEMENT_COMMANDS_PUBLISHED=0\n'
REMOTE
)"
printf '%s\n' "$reload_result" | tee "$RUN_DIR/reload-result.log"
sleep 3
after="$(remote_state)"
printf '%s\n' "$after" | tee "$RUN_DIR/runtime-after.log"
grep -Fq 'E6.1C_RUNTIME_LOAD_ORDER=process_started_after_config' <<<"$after"
preflight_after="$($LIVE_AUDITOR --check --expect-active-estop)"
validate_barriers "$preflight_after"
printf '%s\n' "$preflight_after" > "$RUN_DIR/preflight-after.log"
shadow_after="$($SHADOW --status)"
printf '%s\n' "$shadow_after" > "$RUN_DIR/vla-status-after.log"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$shadow_after"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.1C-RELOAD
run_id: $(basename -- "$RUN_DIR")
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_E6_1C_TASK_MANAGER_RELOADED_UNDER_ESTOP
task_list_sha256: $EXPECTED_TASK_SHA
runtime_load_order: process_started_after_config
estop_active_before_and_after: true
tasks_invoked: false
physical_movement_commanded: false
physical_publishers: 0
next_gate: RELEASE_ESTOP_THEN_FRESH_READY_GATE_AND_ENTRY_SPECIFIC_CONFIRMATION
EOF
(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.1C_RELOAD_EVIDENCE_OK=%s\n' "$RUN_DIR"
