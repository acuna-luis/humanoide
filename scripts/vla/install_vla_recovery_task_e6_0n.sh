#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/install_vla_recovery_task_e6_0n.sh --check
  ./scripts/vla/install_vla_recovery_task_e6_0n.sh --install-on-disk

Instala de forma mínima y atómica el XML y MetaMove del recovery E6.0, y su
entrada exacta en task_list.yaml. Exige al menos un E-stop accionado, cargador
fuera, VLA detenido y cero publicadores. Respalda y revierte ante fallo. No
recarga, reinicia, llama la tarea, publica ni mueve el robot.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly LIVE_AUDITOR="$SCRIPT_DIR/audit_vla_live_preflight_e6_0g.sh"
readonly SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly SOURCE_XML="$SCRIPT_DIR/runtime/tasks/s2_vla_e6_0_exact_recovery.xml"
readonly SOURCE_META="$SCRIPT_DIR/runtime/meta_move/clamp_s2_vla_e6_0_exact_recovery.yaml"
readonly EXPECTED_XML_SHA256="9e47b6ee37f83f75036c203b809e9a93284d459316764615496a872ca3b4fbcc"
readonly EXPECTED_META_SHA256="bd5f588a4e69c3f5fc38796cccc1adffded293bc5355b67ee18d54f321b6e3b0"
readonly EXPECTED_TASK_LIST_BEFORE_SHA256="e4ac5e43e09dd87afb5f6c504f1e2686bd18ae94c7dc47bdcf0391dbe254def7"
readonly EXPECTED_TASK_LIST_AFTER_SHA256="0d24122cceaf64e9923cae38f251b25db4874f14c907b50725506fde81964957"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly MOTION_CONTAINER="walker-motion.manipulation_robot_app-1"
readonly TASK_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly META_ROOT="/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config"
readonly TASK_LIST="$TASK_ROOT/task_list.yaml"
readonly RECOVERY_KEY="s2_vla_e6_0_exact_recovery"
readonly RECOVERY_XML="$TASK_ROOT/s2_bio_vla/s2_vla_e6_0_exact_recovery.xml"
readonly RECOVERY_META="$META_ROOT/meta_move/clamp_s2_vla_e6_0_exact_recovery.yaml"

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
for required in "$LIVE_AUDITOR" "$SHADOW_SCRIPT" "$EVIDENCE_SCRIPT" \
  "$SOURCE_XML" "$SOURCE_META"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
[[ "$(sha256sum "$SOURCE_XML" | awk '{print $1}')" == "$EXPECTED_XML_SHA256" ]] || {
  printf 'ERROR: cambió el XML recovery local.\n' >&2; exit 1;
}
[[ "$(sha256sum "$SOURCE_META" | awk '{print $1}')" == "$EXPECTED_META_SHA256" ]] || {
  printf 'ERROR: cambió el MetaMove recovery local.\n' >&2; exit 1;
}

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

run_scp() {
  CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" setsid -w scp "${ssh_options[@]}" \
    "$1" "$ROBOT_USER@$MOTION_HOST:$2"
}

nc -z -w3 "$MOTION_HOST" 22 || {
  printf 'ERROR: Motion no es alcanzable en %s:22\n' "$MOTION_HOST" >&2
  exit 1
}

preflight="$($LIVE_AUDITOR --check --expect-active-estop)"
grep -Eq '^ESTOP_KEY=1$|^SERVO_ESTOP_KEY=1$' <<<"$preflight"
grep -Fq 'CHARGER=0' <<<"$preflight"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$preflight"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$preflight"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$preflight"
printf '%s\n' "$preflight"

remote_state="$(run_ssh bash -s -- "$MOTION_CONTAINER" "$TASK_LIST" \
  "$RECOVERY_KEY" "$RECOVERY_XML" "$RECOVERY_META" <<'REMOTE'
set -Eeuo pipefail
container="$1"
task_list="$2"
recovery_key="$3"
recovery_xml="$4"
recovery_meta="$5"
test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
printf 'TASK_LIST_SHA256=%s\n' "$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')"
printf 'RECOVERY_TASK_COUNT=%s\n' "$(docker exec "$container" grep -Fxc "$recovery_key:" "$task_list" || true)"
for pair in "XML:$recovery_xml" "META:$recovery_meta"; do
  label="${pair%%:*}"
  path="${pair#*:}"
  if docker exec "$container" test -f "$path"; then
    printf 'RECOVERY_%s_PRESENT=1\nRECOVERY_%s_SHA256=%s\n' \
      "$label" "$label" "$(docker exec "$container" sha256sum "$path" | awk '{print $1}')"
  else
    printf 'RECOVERY_%s_PRESENT=0\nRECOVERY_%s_SHA256=absent\n' "$label" "$label"
  fi
done
REMOTE
)"
printf '%s\n' "$remote_state"
task_sha="$(awk -F= '$1=="TASK_LIST_SHA256" {print $2}' <<<"$remote_state")"
task_count="$(awk -F= '$1=="RECOVERY_TASK_COUNT" {print $2}' <<<"$remote_state")"
xml_present="$(awk -F= '$1=="RECOVERY_XML_PRESENT" {print $2}' <<<"$remote_state")"
xml_sha="$(awk -F= '$1=="RECOVERY_XML_SHA256" {print $2}' <<<"$remote_state")"
meta_present="$(awk -F= '$1=="RECOVERY_META_PRESENT" {print $2}' <<<"$remote_state")"
meta_sha="$(awk -F= '$1=="RECOVERY_META_SHA256" {print $2}' <<<"$remote_state")"
runtime_load_order="$(awk -F= '$1=="READY_RUNTIME_LOAD_ORDER" {print $2}' <<<"$preflight")"

if [[ "$task_sha" == "$EXPECTED_TASK_LIST_BEFORE_SHA256" && "$task_count" == 0 &&
      "$xml_present" == 0 && "$meta_present" == 0 ]]; then
  install_state=absent
elif [[ "$task_sha" == "$EXPECTED_TASK_LIST_AFTER_SHA256" && "$task_count" == 1 &&
        "$xml_present" == 1 && "$xml_sha" == "$EXPECTED_XML_SHA256" &&
        "$meta_present" == 1 && "$meta_sha" == "$EXPECTED_META_SHA256" ]]; then
  if [[ "$runtime_load_order" == process_started_after_task_list ]]; then
    install_state=installed-on-disk-process-started-after-config
  else
    install_state=installed-on-disk-not-reloaded
  fi
else
  printf 'ERROR: estado recovery no reconocido; task=%s count=%s xml=%s/%s meta=%s/%s\n' \
    "$task_sha" "$task_count" "$xml_present" "$xml_sha" \
    "$meta_present" "$meta_sha" >&2
  exit 1
fi
printf 'E6.0N_CHECK_STATE=%s\n' "$install_state"
printf 'E6.0N_PRECONDITIONS_OK=active-estop,charger-off,vla-stopped,publishers-0\n'
[[ "$MODE" == install-on-disk ]] || exit 0
[[ "$install_state" == absent ]] || {
  printf 'ERROR: recovery ya está instalado; no se sobrescribirá.\n' >&2
  exit 1
}

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0N)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
remote_token="$(basename -- "$RUN_DIR")"
remote_xml="/home/walker/cruzr-vla/staging/${remote_token}_recovery.xml"
remote_meta="/home/walker/cruzr-vla/staging/${remote_token}_recovery.yaml"
remote_backup="/home/walker/cruzr-vla/backups/${remote_token}"
printf '%s\n' "$preflight" > "$RUN_DIR/preflight-before.log"
printf '%s\n' "$remote_state" > "$RUN_DIR/remote-state-before.log"
cp -- "$SOURCE_XML" "$SOURCE_META" "$SCRIPT_PATH" "$RUN_DIR/"

run_ssh "install -d /home/walker/cruzr-vla/staging /home/walker/cruzr-vla/backups"
run_scp "$SOURCE_XML" "$remote_xml"
run_scp "$SOURCE_META" "$remote_meta"

install_result="$(run_ssh bash -s -- "$MOTION_CONTAINER" "$TASK_LIST" \
  "$RECOVERY_KEY" "$RECOVERY_XML" "$RECOVERY_META" \
  "$EXPECTED_XML_SHA256" "$EXPECTED_META_SHA256" \
  "$EXPECTED_TASK_LIST_BEFORE_SHA256" "$EXPECTED_TASK_LIST_AFTER_SHA256" \
  "$remote_xml" "$remote_meta" "$remote_backup" <<'REMOTE'
set -Eeuo pipefail
container="$1"
task_list="$2"
recovery_key="$3"
recovery_xml="$4"
recovery_meta="$5"
expected_xml_sha="$6"
expected_meta_sha="$7"
expected_before="$8"
expected_after="$9"
staged_xml="${10}"
staged_meta="${11}"
backup_dir="${12}"
new_task_list="$backup_dir/task_list.with_recovery.yaml"
task_replaced=0
xml_installed=0
meta_installed=0

rollback_partial() {
  local exit_code=$?
  trap - EXIT
  if ((exit_code != 0)); then
    if ((task_replaced == 1)); then
      docker cp "$backup_dir/task_list.yaml" "$container:/tmp/task_list.e6_0n.rollback.yaml" >/dev/null
      docker exec "$container" mv /tmp/task_list.e6_0n.rollback.yaml "$task_list"
    fi
    if ((xml_installed == 1)); then
      current="$(docker exec "$container" sha256sum "$recovery_xml" 2>/dev/null | awk '{print $1}' || true)"
      [[ "$current" != "$expected_xml_sha" ]] || docker exec "$container" rm -f -- "$recovery_xml"
    fi
    if ((meta_installed == 1)); then
      current="$(docker exec "$container" sha256sum "$recovery_meta" 2>/dev/null | awk '{print $1}' || true)"
      [[ "$current" != "$expected_meta_sha" ]] || docker exec "$container" rm -f -- "$recovery_meta"
    fi
  fi
  rm -f -- "$staged_xml" "$staged_meta"
  exit "$exit_code"
}
trap rollback_partial EXIT

test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
test "$(sha256sum "$staged_xml" | awk '{print $1}')" = "$expected_xml_sha"
test "$(sha256sum "$staged_meta" | awk '{print $1}')" = "$expected_meta_sha"
test "$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')" = "$expected_before"
! docker exec "$container" grep -Fqx "$recovery_key:" "$task_list"
! docker exec "$container" test -e "$recovery_xml"
! docker exec "$container" test -e "$recovery_meta"

install -d -m 0750 "$backup_dir"
docker cp "$container:$task_list" "$backup_dir/task_list.yaml" >/dev/null
test "$(sha256sum "$backup_dir/task_list.yaml" | awk '{print $1}')" = "$expected_before"
task_mode="$(docker exec "$container" stat -c '%a' "$task_list")"
task_uid="$(docker exec "$container" stat -c '%u' "$task_list")"
task_gid="$(docker exec "$container" stat -c '%g' "$task_list")"
cp -- "$backup_dir/task_list.yaml" "$new_task_list"
printf '\n%s:\n  motion_id: "s2_bio_vla/%s"\n  json_args: '\''{"Reverse": false,"TimeRatio": 1.0}'\''\n  cmd: "start"\n' \
  "$recovery_key" "$recovery_key" >> "$new_task_list"
test "$(sha256sum "$new_task_list" | awk '{print $1}')" = "$expected_after"
test "$(grep -Fxc "$recovery_key:" "$new_task_list")" -eq 1

docker exec "$container" install -d "$(dirname -- "$recovery_xml")" "$(dirname -- "$recovery_meta")"
docker cp "$staged_xml" "$container:/tmp/e6_0n_recovery.xml" >/dev/null
docker exec "$container" chmod 0644 /tmp/e6_0n_recovery.xml
docker exec "$container" mv /tmp/e6_0n_recovery.xml "$recovery_xml"
xml_installed=1
docker cp "$staged_meta" "$container:/tmp/e6_0n_recovery.yaml" >/dev/null
docker exec "$container" chmod 0644 /tmp/e6_0n_recovery.yaml
docker exec "$container" mv /tmp/e6_0n_recovery.yaml "$recovery_meta"
meta_installed=1

docker cp "$new_task_list" "$container:/tmp/task_list.e6_0n.new.yaml" >/dev/null
docker exec "$container" chown "$task_uid:$task_gid" /tmp/task_list.e6_0n.new.yaml
docker exec "$container" chmod "$task_mode" /tmp/task_list.e6_0n.new.yaml
docker exec "$container" mv /tmp/task_list.e6_0n.new.yaml "$task_list"
task_replaced=1

test "$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')" = "$expected_after"
test "$(docker exec "$container" sha256sum "$recovery_xml" | awk '{print $1}')" = "$expected_xml_sha"
test "$(docker exec "$container" sha256sum "$recovery_meta" | awk '{print $1}')" = "$expected_meta_sha"
test "$(docker exec "$container" grep -Fxc "$recovery_key:" "$task_list")" -eq 1
printf 'REMOTE_BACKUP=%s\n' "$backup_dir"
printf 'TASK_LIST_BEFORE_SHA256=%s\nTASK_LIST_AFTER_SHA256=%s\n' "$expected_before" "$expected_after"
printf 'RECOVERY_XML_SHA256=%s\nRECOVERY_META_SHA256=%s\n' "$expected_xml_sha" "$expected_meta_sha"
printf 'RECOVERY_ON_DISK_INSTALLED=1\nRECOVERY_ON_DISK_REGISTERED=1\n'
printf 'TASK_MANAGER_RELOADED=0\nMOVEMENT_COMMANDS_PUBLISHED=0\n'

rm -f -- "$staged_xml" "$staged_meta"
trap - EXIT
REMOTE
)"
printf '%s\n' "$install_result" | tee "$RUN_DIR/install-result.log"
grep -Fq 'RECOVERY_ON_DISK_INSTALLED=1' <<<"$install_result"
grep -Fq 'RECOVERY_ON_DISK_REGISTERED=1' <<<"$install_result"
grep -Fq 'TASK_MANAGER_RELOADED=0' <<<"$install_result"
grep -Fq 'MOVEMENT_COMMANDS_PUBLISHED=0' <<<"$install_result"

shadow_after="$($SHADOW_SCRIPT --status)"
printf '%s\n' "$shadow_after" | tee "$RUN_DIR/vla-status-after.log"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$shadow_after"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$shadow_after"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$shadow_after"

remote_backup_path="$(awk -F= '$1=="REMOTE_BACKUP" {print $2}' <<<"$install_result")"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0N
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_RECOVERY_INSTALLED_AND_REGISTERED_ON_DISK_NOT_RELOADED
mode: guarded_atomic_live_config_install_no_reload_no_publisher_no_movement
source_xml_sha256: $EXPECTED_XML_SHA256
source_meta_sha256: $EXPECTED_META_SHA256
task_list_before_sha256: $EXPECTED_TASK_LIST_BEFORE_SHA256
task_list_after_sha256: $EXPECTED_TASK_LIST_AFTER_SHA256
remote_backup: $remote_backup_path
recovery_installed_on_disk: true
recovery_registered_on_disk: true
task_manager_reloaded: false
runtime_registration_verified: false
vla_inference_container: exited
vla_control_container: exited
physical_publishers: 0
physical_movement_commanded: false
physical_authorized: false
rollback: restore_exact_task_list_backup_and_remove_only_hash_matched_recovery_xml_and_meta
next_gate: KEEP_ESTOP_ACTIVE_AND_REVIEW_RELOAD_BEFORE_PHYSICAL_READY_RECOVERY_VALIDATION
EOF
sha256sum "$SCRIPT_PATH" "$SOURCE_XML" "$SOURCE_META" > "$RUN_DIR/source_hashes.sha256"
(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0N_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0N_PHYSICAL_AUTHORIZED=0\n'
