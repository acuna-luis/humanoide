#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/patch_vla_ready_s2_waist_e6_0p.sh --check
  ./scripts/vla/patch_vla_ready_s2_waist_e6_0p.sh --apply-live
  ./scripts/vla/patch_vla_ready_s2_waist_e6_0p.sh --restore-vendor

Corrige únicamente el MetaMove de cintura del XML VLA-ready: el XML vendor
entrega dos valores, pero Cruzr S2 v0.2.0 expone un solo waist_yaw. Sustituye
el XML de forma atómica, conserva backup y no recarga, invoca tareas, publica
ni mueve. Exige home medido, acciones libres, cargador fuera, ambos paros
liberados, VLA detenido y cero publicadores.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly LIVE_AUDITOR="$SCRIPT_DIR/audit_vla_live_preflight_e6_0g.sh"
readonly SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly POSTURE_GATE="$REPO_ROOT/scripts/lib/cruzr_home_posture_gate.py"
readonly VENDOR_XML="$REPO_ROOT/cruzrss2_vla_pack-002/codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml"
readonly S2_XML="$SCRIPT_DIR/runtime/tasks/s2_vla_e6_0_ready_s2.xml"
readonly VENDOR_SHA="f4025124491eba995ec824db3e3be91875f781a4b4e98928654bde9a021d8323"
readonly S2_SHA="c767f7396a325d375752fbce2351837e7f5e0c750902e4815ddd7acb24e2a9b2"
readonly TASK_LIST_SHA="0d24122cceaf64e9923cae38f251b25db4874f14c907b50725506fde81964957"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly MOTION_CONTAINER="walker-motion.manipulation_robot_app-1"
readonly TASK_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly TASK_LIST="$TASK_ROOT/task_list.yaml"
readonly READY_KEY="s2_vla_pick_large_teleop_ready"
readonly READY_XML="$TASK_ROOT/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml"
readonly CONFIRMATION="APLICAR OVERLAY READY S2 SIN MOVER: HOME MEDIDO, CLAMPS VACIOS, ZONA DESPEJADA Y PERSONA JUNTO AL E-STOP"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == 1 ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE=check
while (($#)); do
  case "$1" in
    --check|--apply-live|--restore-vendor) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in awk cp date find grep nc python3 readlink scp setsid sha256sum sort ssh tee xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
for required in "$LIVE_AUDITOR" "$SHADOW_SCRIPT" "$EVIDENCE_SCRIPT" \
  "$POSTURE_GATE" "$VENDOR_XML" "$S2_XML"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
test "$(sha256sum "$VENDOR_XML" | awk '{print $1}')" = "$VENDOR_SHA"
test "$(sha256sum "$S2_XML" | awk '{print $1}')" = "$S2_SHA"
python3 - "$VENDOR_XML" "$S2_XML" <<'PY'
import sys
import xml.etree.ElementTree as ET

vendor = ET.parse(sys.argv[1]).getroot()
s2 = ET.parse(sys.argv[2]).getroot()
vendor_actions = list(vendor.iter("Action"))
s2_actions = list(s2.iter("Action"))
assert len(vendor_actions) == len(s2_actions)
differences = []
for index, (left, right) in enumerate(zip(vendor_actions, s2_actions, strict=True)):
    keys = set(left.attrib) | set(right.attrib)
    for key in keys:
        if left.attrib.get(key) != right.attrib.get(key):
            differences.append((index, left.attrib.get("type"), key, left.attrib.get(key), right.attrib.get(key)))
assert differences == [(0, "waist", "joint_angles", "-0.0; 0.0", "0.0")], differences
PY

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

capture_home() {
  run_ssh "docker exec $MOTION_CONTAINER bash -lc 'source /opt/walker/setup.bash; timeout 8 rosa topic echo --once --no-daemon /mc/actuator_state'" |
    python3 "$POSTURE_GATE"
}

nc -z -w3 "$MOTION_HOST" 22 || { printf 'ERROR: Motion no responde.\n' >&2; exit 1; }
preflight="$($LIVE_AUDITOR --check --expect-released)"
grep -Fq 'ESTOP_KEY=0' <<<"$preflight"
grep -Fq 'SERVO_ESTOP_KEY=0' <<<"$preflight"
grep -Fq 'CHARGER=0' <<<"$preflight"
grep -Fq 'MANIPULATION_ACTION_SERVERS=1' <<<"$preflight"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$preflight"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$preflight"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$preflight"
grep -Fq 'ACTIONS=ready' <<<"$preflight"
home_snapshot="$(capture_home)"
grep -Fq 'MEASURED_HOME=1' <<<"$home_snapshot"

live_sha="$(awk -F= '$1=="READY_XML_SHA256" {print $2}' <<<"$preflight")"
case "$live_sha" in
  "$VENDOR_SHA") live_variant=vendor-incompatible-waist-2d ;;
  "$S2_SHA") live_variant=s2-waist-1d-overlay ;;
  *) printf 'ERROR: hash ready vivo desconocido: %s\n' "$live_sha" >&2; exit 1 ;;
esac
printf '%s\n%s\n' "$preflight" "$home_snapshot"
printf 'E6.0P_READY_VARIANT=%s\n' "$live_variant"
printf 'E6.0P_CHECK_OK=home-measured,actions-ready,vla-stopped,publishers-0\n'
[[ "$MODE" != check ]] || exit 0

confirmation="${E6_0P_CONFIRMATION:-}"
if [[ -z "$confirmation" && -t 0 ]]; then
  printf 'Escriba exactamente: %s\n' "$CONFIRMATION"
  read -r confirmation
fi
[[ "$confirmation" == "$CONFIRMATION" ]] || {
  printf 'ERROR: falta confirmación exacta; no se modificó el robot.\n' >&2
  exit 2
}

if [[ "$MODE" == apply-live ]]; then
  test "$live_sha" = "$VENDOR_SHA" || {
    printf 'ERROR: el overlay ya está aplicado o el estado no es vendor.\n' >&2
    exit 1
  }
  source_xml="$S2_XML"
  source_sha="$S2_SHA"
  expected_before="$VENDOR_SHA"
  final_variant=s2-waist-1d-overlay
  result_status=PASS_S2_WAIST_1D_OVERLAY_APPLIED_NO_RELOAD_NO_MOVEMENT
else
  test "$live_sha" = "$S2_SHA" || {
    printf 'ERROR: el overlay no está aplicado; no hay nada que restaurar.\n' >&2
    exit 1
  }
  source_xml="$VENDOR_XML"
  source_sha="$VENDOR_SHA"
  expected_before="$S2_SHA"
  final_variant=vendor-incompatible-waist-2d
  result_status=PASS_VENDOR_READY_RESTORED_NO_RELOAD_NO_MOVEMENT
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0P)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
remote_token="$(basename -- "$RUN_DIR")"
remote_stage="/home/walker/cruzr-vla/staging/${remote_token}_ready.xml"
remote_backup="/home/walker/cruzr-vla/backups/${remote_token}"
printf '%s\n' "$preflight" > "$RUN_DIR/preflight-before.log"
printf '%s\n' "$home_snapshot" > "$RUN_DIR/home-before.log"
cp -- "$source_xml" "$RUN_DIR/target-ready.xml"
cp -- "$SCRIPT_PATH" "$RUN_DIR/"

run_ssh 'install -d /home/walker/cruzr-vla/staging /home/walker/cruzr-vla/backups'
run_scp "$source_xml" "$remote_stage"
install_result="$(run_ssh bash -s -- "$MOTION_CONTAINER" "$TASK_LIST" "$READY_KEY" \
  "$READY_XML" "$TASK_LIST_SHA" "$expected_before" "$source_sha" \
  "$remote_stage" "$remote_backup" <<'REMOTE'
set -Eeuo pipefail
container="$1"
task_list="$2"
ready_key="$3"
ready_xml="$4"
expected_task_sha="$5"
expected_before="$6"
target_sha="$7"
staged="$8"
backup_dir="$9"

cleanup() { rm -f -- "$staged"; }
trap cleanup EXIT
test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
test "$(sha256sum "$staged" | awk '{print $1}')" = "$target_sha"
test "$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')" = "$expected_task_sha"
test "$(docker exec "$container" grep -Fxc "$ready_key:" "$task_list")" -eq 1
test "$(docker exec "$container" sha256sum "$ready_xml" | awk '{print $1}')" = "$expected_before"

install -d -m 0750 "$backup_dir"
docker cp "$container:$ready_xml" "$backup_dir/ready-before.xml" >/dev/null
docker cp "$container:$task_list" "$backup_dir/task_list.yaml" >/dev/null
test "$(sha256sum "$backup_dir/ready-before.xml" | awk '{print $1}')" = "$expected_before"
test "$(sha256sum "$backup_dir/task_list.yaml" | awk '{print $1}')" = "$expected_task_sha"

mode="$(docker exec "$container" stat -c %a "$ready_xml")"
uid="$(docker exec "$container" stat -c %u "$ready_xml")"
gid="$(docker exec "$container" stat -c %g "$ready_xml")"
docker cp "$staged" "$container:/tmp/e6_0p_ready.xml" >/dev/null
docker exec "$container" chown "$uid:$gid" /tmp/e6_0p_ready.xml
docker exec "$container" chmod "$mode" /tmp/e6_0p_ready.xml
docker exec "$container" test "$(docker exec "$container" sha256sum /tmp/e6_0p_ready.xml | awk '{print $1}')" = "$target_sha"
docker exec "$container" mv /tmp/e6_0p_ready.xml "$ready_xml"
test "$(docker exec "$container" sha256sum "$ready_xml" | awk '{print $1}')" = "$target_sha"
test "$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')" = "$expected_task_sha"

printf 'REMOTE_BACKUP=%s\n' "$backup_dir"
printf 'READY_BEFORE_SHA256=%s\n' "$expected_before"
printf 'READY_AFTER_SHA256=%s\n' "$target_sha"
printf 'TASK_MANAGER_RELOADED=0\n'
printf 'MOVEMENT_COMMANDS_PUBLISHED=0\n'
REMOTE
)"
printf '%s\n' "$install_result" | tee "$RUN_DIR/install-result.log"
grep -Fq "READY_AFTER_SHA256=$source_sha" <<<"$install_result"
grep -Fq 'TASK_MANAGER_RELOADED=0' <<<"$install_result"
grep -Fq 'MOVEMENT_COMMANDS_PUBLISHED=0' <<<"$install_result"

postflight="$($LIVE_AUDITOR --check --expect-released)"
grep -Fq "READY_XML_SHA256=$source_sha" <<<"$postflight"
grep -Fq "READY_XML_VARIANT=$final_variant" <<<"$postflight"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$postflight"
home_after="$(capture_home)"
grep -Fq 'MEASURED_HOME=1' <<<"$home_after"
printf '%s\n' "$postflight" > "$RUN_DIR/preflight-after.log"
printf '%s\n' "$home_after" > "$RUN_DIR/home-after.log"

backup_path="$(awk -F= '$1=="REMOTE_BACKUP" {print $2}' <<<"$install_result")"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0P
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: $result_status
ready_variant_before: $live_variant
ready_variant_after: $final_variant
ready_sha256_before: $expected_before
ready_sha256_after: $source_sha
remote_backup: $backup_path
task_manager_reloaded: false
physical_movement_commanded: false
vla_started: false
physical_publishers: 0
robot_home_before_after: true
rollback: run_this_script_restore_vendor_with_same_guards
next_gate: SUPERVISED_READY_THEN_RECOVERY_RETRY_SEPARATE_FROM_VLA_INFERENCE
EOF
sha256sum "$SCRIPT_PATH" "$VENDOR_XML" "$S2_XML" > "$RUN_DIR/source_hashes.sha256"
(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0P_RESULT=%s\n' "$result_status"
printf 'E6.0P_EVIDENCE_OK=%s\n' "$RUN_DIR"
