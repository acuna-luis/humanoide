#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_ready_e4_0.sh --check
  ./scripts/vla/audit_vla_ready_e4_0.sh --run

E4.0 resuelve artefactos de la postura VLA-ready suministrada mediante lectura
local y SSH pasivo de Motion. No arranca contenedores, no lee estado articular,
no crea publicadores y no manda tareas ni movimiento. El gate previo/final usa
únicamente `ros2 topic info` para demostrar cero publicadores de mando.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_ready_e4_0.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly EVIDENCE_ROOT="${VLA_EVIDENCE_ROOT:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence}"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly SUPPLIED_XML_REL="cruzrss2_vla_pack-002/codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml"
readonly SUPPLIED_LOADER_REL="cruzrss2_vla_pack-002/codes-S2/motion/s2_vla_scripts/auto_load_vla_scripts_new.sh"
readonly NON_S2_READY_REL="cruzrss2_vla_pack-002/codes/motion/cruzr_vla_scripts/cruzr_bio_vla/cruzr_vla_pick_large_teleop_ready.xml"
readonly NON_S2_55_READY_REL="cruzrss2_vla_pack-002/codes/motion/cruzr_vla_scripts/cruzr_bio_vla/cruzr_vla_pick_large_55_ready.xml"
readonly S2_EXECUTOR_REL="cruzrss2_vla_pack-002/codes-S2/motion/rosa_vla_additional/vla-motionx86/src/vla_executor/vla_executor/executor_node_sdk.py"
readonly S2_EXECUTOR_CONFIG_REL="cruzrss2_vla_pack-002/codes-S2/motion/rosa_vla_additional/vla-motionx86/src/vla_executor/configs/utars_clamp_and_place_large_bio_box_in_test_field.yaml"
readonly S2_GENERIC_EXECUTOR_REL="cruzrss2_vla_pack-002/codes-S2/motion/rosa_vla_additional/vla-motionx86/install/vla_executor/lib/python3.10/site-packages/vla_executor/executor_7dof_node.py"
readonly DATASET_ROOT_REL="cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319"
readonly SDK_URDF_ZIP_REL="Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip"
readonly SDK_PDF_REL="Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/Cruzr S2 优必选SDK二次开发文档【对外】6.24.pdf"
readonly SDK_UPGRADE_REL="Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/Upgrade package/utars-udoke-config-v0.2.0.tar.gz"
readonly EXPECTED_XML_SHA256="f4025124491eba995ec824db3e3be91875f781a4b4e98928654bde9a021d8323"
readonly EXPECTED_FORWARD_SHA256="7722b73457a89d6448954944af98ff50b24f586113f6ec7014dd31b1efdef7f6"
readonly EXPECTED_BACK_SHA256="ee39039cfddd24eaf8602c3eb5fa3418eaeee519ed1ca42b584191bb6582f389"
readonly TASK_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly META_ROOT="/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in docker find grep jq nc pdftotext python3 readlink sed setsid sha256sum sort ssh tee unzip xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta herramienta: %s\n' "$tool" >&2; exit 1; }
done
for required in "$ANALYZER" "$EVIDENCE_SCRIPT" "$SHADOW_SCRIPT"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done

cd "$REPO_ROOT"
for required in \
  "$SUPPLIED_XML_REL" "$SUPPLIED_LOADER_REL" "$NON_S2_READY_REL" \
  "$NON_S2_55_READY_REL" "$S2_EXECUTOR_REL" "$S2_EXECUTOR_CONFIG_REL" \
  "$S2_GENERIC_EXECUTOR_REL" "$DATASET_ROOT_REL/meta/info.json" \
  "$DATASET_ROOT_REL/meta/episodes.jsonl" \
  "$DATASET_ROOT_REL/meta/episodes_stats.jsonl" "$SDK_URDF_ZIP_REL" \
  "$SDK_PDF_REL" "$SDK_UPGRADE_REL"; do
  test -s "$required" || { printf 'ERROR: falta artefacto vendor: %s\n' "$required" >&2; exit 1; }
done
actual_xml_sha="$(sha256sum "$SUPPLIED_XML_REL" | awk '{print $1}')"
[[ "$actual_xml_sha" == "$EXPECTED_XML_SHA256" ]] || {
  printf 'ERROR: hash inesperado del XML S2: %s\n' "$actual_xml_sha" >&2
  exit 1
}
python3 -m py_compile "$ANALYZER"

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
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w ssh "${ssh_options[@]}" "$ROBOT_USER@$MOTION_HOST" "$@"
}

nc -z -w3 "$MOTION_HOST" 22 || {
  printf 'ERROR: Motion no es alcanzable en %s:22\n' "$MOTION_HOST" >&2
  exit 1
}

latest_e3_3=""
if [[ -d "$EVIDENCE_ROOT" ]]; then
  latest_e3_3="$(find "$EVIDENCE_ROOT" -mindepth 2 -maxdepth 2 -type f \
    -path '*_E3.3/actual_result.yaml' -printf '%T@ %h\n' | sort -nr | awk 'NR==1 {$1=""; sub(/^ /, ""); print; exit}')"
fi
test -n "$latest_e3_3" || { echo 'ERROR: no se encontró evidencia E3.3' >&2; exit 1; }
grep -Fq 'status: PASS_LOCAL_TEMPORAL_FAIL_CLOSED_VENDOR_SEMANTICS_UNRESOLVED' \
  "$latest_e3_3/actual_result.yaml" || {
  printf 'ERROR: E3.3 previo no tiene el estado esperado: %s\n' "$latest_e3_3" >&2
  exit 1
}
(
  cd "$latest_e3_3"
  sha256sum -c evidence.sha256 >/dev/null
)

status_before="$($SHADOW_SCRIPT --status)"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$status_before"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$status_before"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$status_before"

manipulation_container="$(run_ssh \
  'docker ps --format "{{.Names}}" | grep -E "manipulation_robot_app" | head -n1')"
test -n "$manipulation_container" || {
  echo 'ERROR: no se encontró manipulation_robot_app en ejecución' >&2
  exit 1
}
remote_forward_sha="$(run_ssh "docker exec '$manipulation_container' sha256sum '$META_ROOT/meta_move/clamp_s2_joints_trajectory.yaml'" | awk '{print $1}')"
remote_back_sha="$(run_ssh "docker exec '$manipulation_container' sha256sum '$META_ROOT/meta_move/clamp_s2_joints_trajectory_back.yaml'" | awk '{print $1}')"
[[ "$remote_forward_sha" == "$EXPECTED_FORWARD_SHA256" ]] || {
  printf 'ERROR: hash inesperado de la primitiva forward: %s\n' "$remote_forward_sha" >&2
  exit 1
}
[[ "$remote_back_sha" == "$EXPECTED_BACK_SHA256" ]] || {
  printf 'ERROR: hash inesperado de la primitiva back: %s\n' "$remote_back_sha" >&2
  exit 1
}

printf '%s\n' "$status_before"
printf 'E4.0_CHECK_OK=read-only,motion:%s,container:%s,primitive-forward:%s,primitive-back:%s\n' \
  "$MOTION_HOST" "$manipulation_container" "$remote_forward_sha" "$remote_back_sha"
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E4.0)"
mkdir -- "$RUN_DIR/artifacts"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.0
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
status: FAIL_BEFORE_COMPLETING_READ_ONLY_ARTIFACT_AUDIT
physical_movement_commanded: false
robot_state_read: false
physical_publisher_created: false
recovery_or_stop: NO_PHYSICAL_EXECUTOR_EXISTED
EOF
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf '%s\n' "$status_before" > "$RUN_DIR/status_before.log"
printf '%s\n' "$latest_e3_3" > "$RUN_DIR/e3_3_source_path.txt"
cp -- "$SUPPLIED_XML_REL" "$RUN_DIR/artifacts/vendor_s2_vla_pick_large_teleop_ready.xml"
cp -- "$SUPPLIED_LOADER_REL" "$RUN_DIR/artifacts/vendor_s2_auto_load_vla_scripts_new.sh"
cp -- "$NON_S2_READY_REL" "$RUN_DIR/artifacts/vendor_non_s2_vla_pick_large_teleop_ready.xml"
cp -- "$NON_S2_55_READY_REL" "$RUN_DIR/artifacts/vendor_non_s2_vla_pick_large_55_ready.xml"
cp -- "$S2_EXECUTOR_REL" "$RUN_DIR/artifacts/vendor_s2_executor_node_sdk.py"
cp -- "$S2_EXECUTOR_CONFIG_REL" "$RUN_DIR/artifacts/vendor_s2_executor_config.yaml"
cp -- "$S2_GENERIC_EXECUTOR_REL" "$RUN_DIR/artifacts/vendor_s2_generic_executor_7dof.py"
cp -- "$DATASET_ROOT_REL/meta/info.json" "$RUN_DIR/artifacts/vendor_dataset_info.json"
cp -- "$DATASET_ROOT_REL/meta/episodes.jsonl" "$RUN_DIR/artifacts/vendor_dataset_episodes.jsonl"
cp -- "$DATASET_ROOT_REL/meta/episodes_stats.jsonl" "$RUN_DIR/artifacts/vendor_dataset_episode_stats.jsonl"
unzip -p "$SDK_URDF_ZIP_REL" \
  '*/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf' \
  > "$RUN_DIR/artifacts/vendor_cruzr_s2_v1.urdf"
pdftotext "$SDK_PDF_REL" - > "$RUN_DIR/artifacts/vendor_sdk_manual.txt"
tar -tzf "$SDK_UPGRADE_REL" > "$RUN_DIR/artifacts/vendor_v020_upgrade_file_list.txt"
sha256sum "$SDK_URDF_ZIP_REL" "$SDK_PDF_REL" "$SDK_UPGRADE_REL" \
  > "$RUN_DIR/artifacts/vendor_source_packages.sha256"
sha256sum "$SUPPLIED_XML_REL" > "$RUN_DIR/artifacts/vendor_s2_ready.sha256"

capture_remote_file() {
  local remote_path="$1"
  local output_name="$2"
  local remote_sha local_sha
  remote_sha="$(run_ssh "docker exec '$manipulation_container' sha256sum '$remote_path'" | awk '{print $1}')"
  run_ssh "docker exec '$manipulation_container' cat '$remote_path'" \
    > "$RUN_DIR/artifacts/$output_name"
  local_sha="$(sha256sum "$RUN_DIR/artifacts/$output_name" | awk '{print $1}')"
  [[ "$remote_sha" == "$local_sha" ]] || {
    printf 'ERROR: hash no coincide al capturar %s\n' "$remote_path" >&2
    return 1
  }
  printf '%s  %s\n' "$remote_sha" "$remote_path" \
    > "$RUN_DIR/artifacts/${output_name%.*}.sha256"
}

capture_remote_file "$META_ROOT/meta_move/clamp_s2_joints_trajectory.yaml" \
  remote_clamp_s2_joints_trajectory.yaml
capture_remote_file "$META_ROOT/meta_move/clamp_s2_joints_trajectory_back.yaml" \
  remote_clamp_s2_joints_trajectory_back.yaml
capture_remote_file "$TASK_ROOT/task_list.yaml" remote_task_list.yaml
capture_remote_file "$TASK_ROOT/cruzr_vla/clamp_ready.xml" remote_cruzr_vla_clamp_ready.xml
capture_remote_file "$TASK_ROOT/transport/clamp_ready_s2.xml" remote_transport_clamp_ready_s2.xml
capture_remote_file "$TASK_ROOT/transport/clamp_ready.xml" remote_transport_clamp_ready.xml
capture_remote_file "$TASK_ROOT/transport/clamp_ready_cruzr.xml" remote_transport_clamp_ready_cruzr.xml

run_ssh "docker inspect '$manipulation_container' --format 'name={{.Name}} image={{.Config.Image}} image_id={{.Image}} status={{.State.Status}} started={{.State.StartedAt}}'" \
  > "$RUN_DIR/artifacts/remote_manipulation_container.txt"
run_ssh "docker exec '$manipulation_container' find '$TASK_ROOT/s2_bio_vla' -maxdepth 1 -type f -printf '%f\\n' 2>/dev/null | sort || true" \
  > "$RUN_DIR/artifacts/remote_s2_bio_vla_file_list.txt"
run_ssh "docker exec '$manipulation_container' bash -lc 'grep -R -I -n -E \"clamp_s2_joints_trajectory|s2_vla_pick_large_teleop_ready|s2_bio_vla\" \"$TASK_ROOT\" \"$META_ROOT\" 2>/dev/null || true'" \
  > "$RUN_DIR/artifacts/remote_reference_matches.txt"
run_ssh "docker exec '$manipulation_container' bash -lc 'grep -n -A4 -B1 -E \"clamp_ready|s2_vla_pick_large_teleop_ready|s2_bio_vla|cruzr_vla\" \"$TASK_ROOT/task_list.yaml\" || true'" \
  > "$RUN_DIR/artifacts/remote_task_list_matches.txt"

python3 "$ANALYZER" --run-dir "$RUN_DIR" | tee "$RUN_DIR/analyzer.log"
jq -e '
  .experiment_id == "E4.0"
  and .installed_forward_primitive.found == true
  and .installed_forward_primitive.goals_shape == [2,14]
  and .installed_forward_primitive.nominal_duration_seconds == 2.5
  and .installed_back_primitive.found == true
  and .installed_back_primitive.exact_reverse_of_forward_goals == false
  and .supplied_s2.installed_directory_or_file_found == false
  and .supplied_s2.registered_in_task_list == false
  and .ready_state_candidate.fully_defined == false
  and .ready_state_candidate.undefined_indices == [16,17,18]
  and .ready_state_candidate.joint_order_20d[0] == "L_elbow_roll_joint"
  and .ready_state_candidate.values[0] == -1.383
  and .ready_state_candidate.values[2] == -0.296
  and .ready_state_candidate.values[19] == 0.0
  and .supplied_s2.waist_mapping_locally_resolved == true
  and .dataset_lifter_contract.single_numeric_ready_target_demonstrated == false
  and .executor_contract.drops_lifter_actions_20d_indices == [16,17,18]
  and .swept_volume.computed_in_e4_0 == false
  and .physical_ready_pass == false
  and .physical_movement_commanded == false
  and .robot_state_read == false
  and .status == "PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE"
' "$RUN_DIR/summary.json" >/dev/null

status_after="$($SHADOW_SCRIPT --status)"
printf '%s\n' "$status_after" | tee "$RUN_DIR/status_after.log"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$status_after"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$status_after"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$status_after"

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.0
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE
mode: local_and_remote_read_only_artifact_resolution
supplied_s2_xml_sha256: $actual_xml_sha
supplied_s2_task_installed: false
supplied_s2_task_registered: false
forward_primitive_installed: true
forward_primitive_sha256: $remote_forward_sha
forward_primitive_shape: 2x14
forward_primitive_nominal_duration_seconds: 2.5
back_primitive_installed: true
back_primitive_sha256: $remote_back_sha
back_primitive_shape: 2x14
back_primitive_exact_inverse: false
ready_20d_complete: false
undefined_ready_indices: [16, 17, 18]
ready_arm_values_reordered_to_checkpoint_contract: true
waist_mapping_locally_resolved: true
waist_ready_value: 0.0
lifter_ready_policy: inherited_current_state_no_numeric_target
dataset_lifter_single_numeric_ready_target_demonstrated: false
swept_volume_available: false
explicit_primitive_limits_available: false
physical_publishers_final: 0
persistent_inference_container_final: exited
persistent_control_container_final: exited
robot_state_read: false
physical_movement_commanded: false
physical_executor_authorized: false
recovery_or_stop: READ_ONLY_AUDIT_ENDED_AND_PERSISTENT_VLA_REMAINED_STOPPED
next_experiment_authorized: E4.0_READ_ONLY_REMEDIATION_OR_VENDOR_CLARIFICATION_ONLY
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(
  cd "$RUN_DIR"
  sha256sum -c evidence.sha256
)
printf 'E4.0_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E4.0_RESULT=PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE\n'
