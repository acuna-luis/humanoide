#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/install_vla_ready_task_e6_0h.sh --check
  ./scripts/vla/install_vla_ready_task_e6_0h.sh --install-on-disk

Instala de forma mínima y atómica sólo el XML S2 VLA-ready y su entrada en
task_list.yaml. Exige un E-stop accionado, VLA detenido y cero publicadores.
Respalda el task_list vivo y revierte ante fallo. No recarga, reinicia, llama
la tarea, publica ni mueve; el registro runtime queda sin validar.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly LIVE_AUDITOR="$SCRIPT_DIR/audit_vla_live_preflight_e6_0g.sh"
readonly SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly SOURCE_XML="$REPO_ROOT/cruzrss2_vla_pack-002/codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml"
readonly EXPECTED_XML_SHA256="f4025124491eba995ec824db3e3be91875f781a4b4e98928654bde9a021d8323"
readonly EXPECTED_TASK_LIST_SHA256="c03ea6a74677e1a639b4439d353d9ef3cb2c353955d6c5e1b2aebae4e8821a44"
readonly EXPECTED_TASK_LIST_AFTER_SHA256="e4ac5e43e09dd87afb5f6c504f1e2686bd18ae94c7dc47bdcf0391dbe254def7"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly MOTION_CONTAINER="walker-motion.manipulation_robot_app-1"
readonly TASK_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly TASK_LIST="$TASK_ROOT/task_list.yaml"
readonly READY_KEY="s2_vla_pick_large_teleop_ready"
readonly READY_XML="$TASK_ROOT/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE="check"
while (($#)); do
  case "$1" in
    --check|--install-on-disk) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in awk cp date find grep jq nc readlink scp setsid sha256sum sort ssh tee xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
for required in "$LIVE_AUDITOR" "$SHADOW_SCRIPT" "$EVIDENCE_SCRIPT" "$SOURCE_XML"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
[[ "$(sha256sum "$SOURCE_XML" | awk '{print $1}')" == "$EXPECTED_XML_SHA256" ]] || {
  echo 'ERROR: cambió el XML vendor ready.' >&2
  exit 1
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

preflight="$($LIVE_AUDITOR --check)"
grep -Eq '^ESTOP_KEY=1$|^SERVO_ESTOP_KEY=1$' <<<"$preflight"
grep -Fq 'CHARGER=0' <<<"$preflight"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$preflight"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$preflight"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$preflight"
printf '%s\n' "$preflight"
live_task_list_sha="$(awk -F= '$1=="TASK_LIST_SHA256" {print $2}' <<<"$preflight")"
live_ready_registered="$(awk -F= '$1=="READY_TASK_REGISTERED" {print $2}' <<<"$preflight")"
live_ready_present="$(awk -F= '$1=="READY_XML_PRESENT" {print $2}' <<<"$preflight")"
live_ready_sha="$(awk -F= '$1=="READY_XML_SHA256" {print $2}' <<<"$preflight")"
if [[ "$live_task_list_sha" == "$EXPECTED_TASK_LIST_SHA256" &&
      "$live_ready_registered" == "0" && "$live_ready_present" == "0" ]]; then
  install_state="absent"
elif [[ "$live_task_list_sha" == "$EXPECTED_TASK_LIST_AFTER_SHA256" &&
        "$live_ready_registered" == "1" && "$live_ready_present" == "1" &&
        "$live_ready_sha" == "$EXPECTED_XML_SHA256" ]]; then
  install_state="installed-on-disk-not-reloaded"
else
  printf 'ERROR: estado ready no reconocido; task_list=%s registered=%s present=%s xml=%s\n' \
    "$live_task_list_sha" "$live_ready_registered" "$live_ready_present" "$live_ready_sha" >&2
  exit 1
fi
printf 'E6.0H_CHECK_STATE=%s\n' "$install_state"
printf 'E6.0H_PRECONDITIONS_OK=active-estop,charger-off,vla-stopped,publishers-0\n'
[[ "$MODE" == "install-on-disk" ]] || exit 0
[[ "$install_state" == "absent" ]] || {
  echo 'ERROR: ready ya está instalado en disco; no se repetirá ni sobrescribirá.' >&2
  exit 1
}

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0H)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
remote_token="$(basename -- "$RUN_DIR")"
remote_staged="/home/walker/cruzr-vla/staging/${remote_token}_ready.xml"
remote_backup="/home/walker/cruzr-vla/backups/${remote_token}"
printf '%s\n' "$preflight" > "$RUN_DIR/preflight-before.log"
cp -- "$SOURCE_XML" "$RUN_DIR/vendor-ready.xml"
cp -- "$SCRIPT_PATH" "$RUN_DIR/"

run_ssh "install -d /home/walker/cruzr-vla/staging /home/walker/cruzr-vla/backups"
run_scp "$SOURCE_XML" "$remote_staged"

install_result="$(run_ssh bash -s -- \
  "$MOTION_CONTAINER" "$TASK_LIST" "$READY_KEY" "$READY_XML" \
  "$EXPECTED_XML_SHA256" "$EXPECTED_TASK_LIST_SHA256" \
  "$remote_staged" "$remote_backup" <<'REMOTE'
set -Eeuo pipefail
container="$1"
task_list="$2"
ready_key="$3"
ready_xml="$4"
expected_xml_sha="$5"
expected_task_list_sha="$6"
staged="$7"
backup_dir="$8"
target_dir="$(dirname -- "$ready_xml")"
new_task_list="$backup_dir/task_list.with_ready.yaml"
task_list_replaced=0
xml_installed=0

rollback_partial() {
  local exit_code=$?
  trap - EXIT
  if ((exit_code != 0)); then
    if ((task_list_replaced == 1)); then
      docker cp "$backup_dir/task_list.yaml" "$container:/tmp/task_list.e6_0h.rollback.yaml" >/dev/null
      docker exec "$container" mv /tmp/task_list.e6_0h.rollback.yaml "$task_list"
    fi
    if ((xml_installed == 1)); then
      current="$(docker exec "$container" sha256sum "$ready_xml" 2>/dev/null | awk '{print $1}' || true)"
      if [[ "$current" == "$expected_xml_sha" ]]; then
        docker exec "$container" rm -f -- "$ready_xml"
      fi
    fi
  fi
  rm -f -- "$staged"
  exit "$exit_code"
}
trap rollback_partial EXIT

test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
test "$(sha256sum "$staged" | awk '{print $1}')" = "$expected_xml_sha"
current_task_list_sha="$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')"
test "$current_task_list_sha" = "$expected_task_list_sha"
! docker exec "$container" grep -Fqx "$ready_key:" "$task_list"
! docker exec "$container" test -e "$ready_xml"

install -d -m 0750 "$backup_dir"
docker cp "$container:$task_list" "$backup_dir/task_list.yaml" >/dev/null
test "$(sha256sum "$backup_dir/task_list.yaml" | awk '{print $1}')" = "$expected_task_list_sha"
task_mode="$(docker exec "$container" stat -c '%a' "$task_list")"
task_uid="$(docker exec "$container" stat -c '%u' "$task_list")"
task_gid="$(docker exec "$container" stat -c '%g' "$task_list")"
cp -- "$backup_dir/task_list.yaml" "$new_task_list"
printf '\n%s:\n  motion_id: "s2_bio_vla/%s"\n  json_args: '\''{"Reverse": false,"TimeRatio": 0.5}'\''\n  cmd: "start"\n' \
  "$ready_key" "$ready_key" >> "$new_task_list"
test "$(grep -Fxc "$ready_key:" "$new_task_list")" -eq 1

docker exec "$container" install -d "$target_dir"
docker cp "$staged" "$container:/tmp/e6_0h_ready.xml" >/dev/null
docker exec "$container" test "$(docker exec "$container" sha256sum /tmp/e6_0h_ready.xml | awk '{print $1}')" = "$expected_xml_sha"
docker exec "$container" mv /tmp/e6_0h_ready.xml "$ready_xml"
xml_installed=1

docker cp "$new_task_list" "$container:/tmp/task_list.e6_0h.new.yaml" >/dev/null
docker exec "$container" chown "$task_uid:$task_gid" /tmp/task_list.e6_0h.new.yaml
docker exec "$container" chmod "$task_mode" /tmp/task_list.e6_0h.new.yaml
docker exec "$container" mv /tmp/task_list.e6_0h.new.yaml "$task_list"
task_list_replaced=1

test "$(docker exec "$container" sha256sum "$ready_xml" | awk '{print $1}')" = "$expected_xml_sha"
test "$(docker exec "$container" grep -Fxc "$ready_key:" "$task_list")" -eq 1
post_task_list_sha="$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')"
printf 'REMOTE_BACKUP=%s\n' "$backup_dir"
printf 'TASK_LIST_BEFORE_SHA256=%s\n' "$expected_task_list_sha"
printf 'TASK_LIST_AFTER_SHA256=%s\n' "$post_task_list_sha"
printf 'READY_XML_SHA256=%s\n' "$expected_xml_sha"
printf 'READY_ON_DISK_INSTALLED=1\nREADY_ON_DISK_REGISTERED=1\n'
printf 'TASK_MANAGER_RELOADED=0\nMOVEMENT_COMMANDS_PUBLISHED=0\n'

rm -f -- "$staged"
trap - EXIT
REMOTE
)"
printf '%s\n' "$install_result" | tee "$RUN_DIR/install-result.log"
grep -Fq 'READY_ON_DISK_INSTALLED=1' <<<"$install_result"
grep -Fq 'READY_ON_DISK_REGISTERED=1' <<<"$install_result"
grep -Fq 'TASK_MANAGER_RELOADED=0' <<<"$install_result"
grep -Fq 'MOVEMENT_COMMANDS_PUBLISHED=0' <<<"$install_result"

shadow_after="$($SHADOW_SCRIPT --status)"
printf '%s\n' "$shadow_after" | tee "$RUN_DIR/vla-status-after.log"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$shadow_after"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$shadow_after"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$shadow_after"

remote_backup_path="$(awk -F= '$1=="REMOTE_BACKUP" {print $2}' <<<"$install_result")"
task_list_after_sha="$(awk -F= '$1=="TASK_LIST_AFTER_SHA256" {print $2}' <<<"$install_result")"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0H
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_READY_INSTALLED_AND_REGISTERED_ON_DISK_NOT_RELOADED
mode: guarded_atomic_live_config_install_no_reload_no_publisher_no_movement
source_xml_sha256: $EXPECTED_XML_SHA256
task_list_before_sha256: $EXPECTED_TASK_LIST_SHA256
task_list_after_sha256: $task_list_after_sha
remote_backup: $remote_backup_path
ready_installed_on_disk: true
ready_registered_on_disk: true
task_manager_reloaded: false
runtime_registration_verified: false
vla_inference_container: exited
vla_control_container: exited
physical_publishers: 0
physical_movement_commanded: false
physical_authorized: false
rollback: restore_exact_task_list_backup_and_remove_only_hash_matched_ready_xml
next_gate: KEEP_ESTOP_ACTIVE_AND_REVIEW_RELOAD_SEMANTICS_BEFORE_ANY_RELOAD
EOF
sha256sum "$SCRIPT_PATH" "$SOURCE_XML" > "$RUN_DIR/source_hashes.sha256"
(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0H_EVIDENCE_OK=%s\n' "$RUN_DIR"
