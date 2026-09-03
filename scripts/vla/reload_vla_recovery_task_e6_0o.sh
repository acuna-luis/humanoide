#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/reload_vla_recovery_task_e6_0o.sh --check
  ./scripts/vla/reload_vla_recovery_task_e6_0o.sh --reload

Recarga exclusivamente el contenedor dedicado manipulation_task_manager para
que lea el recovery E6.0N ya instalado. Exige E-stop activo, cargador fuera,
VLA detenido, cero publicadores y confirmación física exacta. No llama ninguna
tarea, no libera paros y no publica movimiento.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly LIVE_AUDITOR="$SCRIPT_DIR/audit_vla_live_preflight_e6_0g.sh"
readonly SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly CONTAINER="walker-motion.manipulation_robot_app-1"
readonly TASK_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly META_ROOT="/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config"
readonly TASK_LIST="$TASK_ROOT/task_list.yaml"
readonly RECOVERY_KEY="s2_vla_e6_0_exact_recovery"
readonly RECOVERY_XML="$TASK_ROOT/s2_bio_vla/s2_vla_e6_0_exact_recovery.xml"
readonly RECOVERY_META="$META_ROOT/meta_move/clamp_s2_vla_e6_0_exact_recovery.yaml"
readonly EXPECTED_TASK_SHA="0d24122cceaf64e9923cae38f251b25db4874f14c907b50725506fde81964957"
readonly EXPECTED_XML_SHA="9e47b6ee37f83f75036c203b809e9a93284d459316764615496a872ca3b4fbcc"
readonly EXPECTED_META_SHA="bd5f588a4e69c3f5fc38796cccc1adffded293bc5355b67ee18d54f321b6e3b0"
readonly EXPECTED_CONFIRMATION="AUTORIZO RECARGA CONTROLADA: AMBOS PAROS ACCIONADOS, ROBOT ESTABLE, CARGADOR DESCONECTADO, ZONA DESPEJADA Y DOS PERSONAS PRESENTES"

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

for tool in awk date grep nc readlink setsid sha256sum sort ssh tee timeout xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
for required in "$LIVE_AUDITOR" "$SHADOW_SCRIPT" "$EVIDENCE_SCRIPT"; do
  test -x "$required" || { printf 'ERROR: falta ejecutable %s\n' "$required" >&2; exit 1; }
done

ssh_options=(
  -o ConnectTimeout=10
  -o ConnectionAttempts=1
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
  -o PreferredAuthentications=password
  -o PubkeyAuthentication=no
  -o NumberOfPasswordPrompts=2
  -o StrictHostKeyChecking=accept-new
)

run_ssh() {
  CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" setsid -w ssh "${ssh_options[@]}" \
    "$ROBOT_USER@$MOTION_HOST" "$@"
}

validate_live_barriers() {
  local snapshot="$1"
  grep -Eq '^ESTOP_KEY=1$|^SERVO_ESTOP_KEY=1$' <<<"$snapshot"
  grep -Fq 'CHARGER=0' <<<"$snapshot"
  grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$snapshot"
  grep -Fq 'CONTROL_CONTAINER=exited' <<<"$snapshot"
  grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$snapshot"
}

remote_state() {
  run_ssh bash -s -- "$CONTAINER" "$TASK_LIST" "$RECOVERY_KEY" \
    "$RECOVERY_XML" "$RECOVERY_META" "$EXPECTED_TASK_SHA" \
    "$EXPECTED_XML_SHA" "$EXPECTED_META_SHA" <<'REMOTE'
set -Eeuo pipefail
container="$1"
task_list="$2"
recovery_key="$3"
recovery_xml="$4"
recovery_meta="$5"
expected_task="$6"
expected_xml="$7"
expected_meta="$8"

test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
task_sha="$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')"
xml_sha="$(docker exec "$container" sha256sum "$recovery_xml" | awk '{print $1}')"
meta_sha="$(docker exec "$container" sha256sum "$recovery_meta" | awk '{print $1}')"
task_count="$(docker exec "$container" grep -Fxc "$recovery_key:" "$task_list" || true)"
test "$task_sha" = "$expected_task"
test "$xml_sha" = "$expected_xml"
test "$meta_sha" = "$expected_meta"
test "$task_count" -eq 1

started_at="$(docker inspect --format '{{.State.StartedAt}}' "$container")"
started_epoch="$(date -d "$started_at" +%s)"
task_mtime="$(docker exec "$container" stat -c %Y "$task_list")"
robot_app_count="$(docker top "$container" -eo pid,cmd | awk '
  NR > 1 && $0 ~ /\/opt\/walker\/manipulation_task_manager\/lib\/manipulation_task_manager\/robot_app$/ {count++}
  END {print count + 0}
')"
test "$robot_app_count" -eq 1

printf 'CONTAINER_STATUS=running\n'
printf 'CONTAINER_STARTED_AT=%s\n' "$started_at"
printf 'TASK_LIST_MTIME_EPOCH=%s\n' "$task_mtime"
if ((started_epoch > task_mtime)); then
  printf 'RECOVERY_RUNTIME_LOAD_ORDER=process_started_after_recovery_config\n'
else
  printf 'RECOVERY_RUNTIME_LOAD_ORDER=process_not_started_after_recovery_config\n'
fi
printf 'TASK_LIST_SHA256=%s\n' "$task_sha"
printf 'RECOVERY_TASK_COUNT=%s\n' "$task_count"
printf 'RECOVERY_XML_SHA256=%s\n' "$xml_sha"
printf 'RECOVERY_META_SHA256=%s\n' "$meta_sha"
printf 'ROBOT_APP_PROCESS_COUNT=%s\n' "$robot_app_count"
REMOTE
}

nc -z -w3 "$MOTION_HOST" 22 || {
  printf 'ERROR: Motion no es alcanzable en %s:22\n' "$MOTION_HOST" >&2
  exit 1
}

preflight="$($LIVE_AUDITOR --check --expect-active-estop)"
validate_live_barriers "$preflight"
printf '%s\n' "$preflight"

state_before="$(remote_state)"
printf '%s\n' "$state_before"
if [[ "$MODE" == check ]]; then
  printf 'E6.0O_CHECK_OK=exact-config,active-estop,charger-off,vla-stopped,publishers-0\n'
  exit 0
fi

confirmation="${E6_0O_OPERATOR_CONFIRMATION:-}"
if [[ -z "$confirmation" ]]; then
  printf 'Escriba exactamente: %s\n' "$EXPECTED_CONFIRMATION"
  IFS= read -r confirmation
fi
[[ "$confirmation" == "$EXPECTED_CONFIRMATION" ]] || {
  printf 'ERROR: confirmación física incorrecta; no se recargó.\n' >&2
  exit 2
}

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0O)"
START_TIME="$(date --iso-8601=seconds)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
printf '%s\n' "$preflight" > "$RUN_DIR/preflight-before.log"
printf '%s\n' "$state_before" > "$RUN_DIR/runtime-before.log"
cp -- "$SCRIPT_PATH" "$RUN_DIR/"

reload_result="$(run_ssh bash -s -- "$CONTAINER" <<'REMOTE'
set -Eeuo pipefail
container="$1"
old_started="$(docker inspect --format '{{.State.StartedAt}}' "$container")"
test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
timeout 30 docker restart --time 10 "$container" >/dev/null
for _ in $(seq 1 20); do
  status="$(docker inspect --format '{{.State.Status}}' "$container")"
  [[ "$status" != running ]] || break
  sleep 1
done
test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
new_started="$(docker inspect --format '{{.State.StartedAt}}' "$container")"
test "$new_started" != "$old_started"
printf 'RELOADED_CONTAINER=%s\n' "$container"
printf 'CONTAINER_STARTED_BEFORE=%s\n' "$old_started"
printf 'CONTAINER_STARTED_AFTER=%s\n' "$new_started"
printf 'TASKS_INVOKED=0\nMOVEMENT_COMMANDS_PUBLISHED=0\n'
REMOTE
)"
printf '%s\n' "$reload_result" | tee "$RUN_DIR/reload-result.log"

sleep 3
state_after="$(remote_state)"
printf '%s\n' "$state_after" | tee "$RUN_DIR/runtime-after.log"
grep -Fq 'RECOVERY_RUNTIME_LOAD_ORDER=process_started_after_recovery_config' <<<"$state_after"

preflight_after="$($LIVE_AUDITOR --check --expect-active-estop)"
validate_live_barriers "$preflight_after"
printf '%s\n' "$preflight_after" | tee "$RUN_DIR/preflight-after.log"

shadow_after="$($SHADOW_SCRIPT --status)"
printf '%s\n' "$shadow_after" | tee "$RUN_DIR/vla-status-after.log"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$shadow_after"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$shadow_after"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$shadow_after"

container_started_after="$(awk -F= '$1=="CONTAINER_STARTED_AFTER" {print $2}' <<<"$reload_result")"
test -n "$container_started_after"
run_ssh "docker logs --since '$container_started_after' --tail 240 '$CONTAINER' 2>&1" \
  > "$RUN_DIR/container-startup.log"
if grep -Eiq 'segmentation fault|terminate called|yaml::|parse[^[:alnum:]]+error|fatal error' \
  "$RUN_DIR/container-startup.log"; then
  printf 'ERROR: el arranque registró un error fatal/parse; mantenga E-stop.\n' >&2
  exit 1
fi

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0O
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_DEDICATED_TASK_MANAGER_RELOADED_UNDER_ESTOP
mode: guarded_single_container_reload_no_task_no_publisher_no_movement
task_list_sha256: $EXPECTED_TASK_SHA
recovery_xml_sha256: $EXPECTED_XML_SHA
recovery_meta_sha256: $EXPECTED_META_SHA
runtime_load_order: process_started_after_recovery_config
estop_active_before_and_after: true
chassis_estop_software_confirmed: false
task_invoked: false
physical_movement_commanded: false
vla_inference_container: exited
vla_control_container: exited
physical_publishers: 0
physical_authorized: false
next_gate: SUPERVISED_RUNTIME_REGISTRATION_AND_RECOVERY_VALIDATION_WITH_ESTOP_PROCEDURE
EOF
(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0O_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0O_MOVEMENT_COMMANDS_PUBLISHED=0\n'
printf 'E6.0O_PHYSICAL_AUTHORIZED=0\n'
