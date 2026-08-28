#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_vla_offline_ood_e3_1.sh --check
  ./scripts/vla/run_vla_offline_ood_e3_1.sh --run

E3.1 evalúa sensibilidad offline de tasks 0/2 cambiando sólo RGB mediante
tres proxies globales reproducibles: desplazamiento horizontal, zoom y
perspectiva. La parrilla métrica en metros/yaw de objeto permanece bloqueada
porque el dataset no contiene RGB-D, calibración, máscara ni geometría 3D.

Usa un contenedor NVIDIA transitorio con --network none y checkpoint read-only.
No inicia ROS, no lee el robot y no publica comandos.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly BASE_EVALUATOR="$SCRIPT_DIR/evaluate_checkpoint_offline.py"
readonly OOD_EVALUATOR="$SCRIPT_DIR/evaluate_vla_ood_e3_1.py"
readonly BASE_TEST="$SCRIPT_DIR/runtime/test_evaluate_checkpoint_offline.py"
readonly OOD_TEST="$SCRIPT_DIR/runtime/test_evaluate_vla_ood_e3_1.py"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_profile.json"
readonly SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly DATASET="$REPO_ROOT/cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319"
readonly CHECKPOINT="$REPO_ROOT/cruzrss2_vla_pack-002/weight/checkpoint-40000"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly INFERENCE_IMAGE="vla_inference_node_sdk:latest"
readonly REMOTE_ADDITIONAL="/home/walker/cruzr-vla/additional"

MODE="check"
CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD

if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in cmp df dirname find head jq ln nc python3 readlink rsync setsid sha256sum sort ssh tail tee tr wc xargs; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta herramienta: $tool" >&2; exit 1; }
done
for required in \
  "$BASE_EVALUATOR" "$OOD_EVALUATOR" "$BASE_TEST" "$OOD_TEST" \
  "$PROFILE" "$SHADOW_SCRIPT" "$EVIDENCE_SCRIPT"; do
  test -s "$required" || { echo "ERROR: falta $required" >&2; exit 1; }
done
test -d "$DATASET"
test -s "$CHECKPOINT/config.json"
test -s "$CHECKPOINT/model.safetensors.index.json"

for evaluator in "$BASE_EVALUATOR" "$OOD_EVALUATOR"; do
  if grep -Eq '^[[:space:]]*(from|import)[[:space:]].*(rclpy|rosa|RobotCommand)' "$evaluator"; then
    echo "ERROR: dependencia ROS/RobotCommand en $evaluator" >&2
    exit 1
  fi
done
python3 -m py_compile "$BASE_EVALUATOR" "$OOD_EVALUATOR" "$BASE_TEST" "$OOD_TEST"
python3 "$BASE_TEST"
python3 "$OOD_TEST"

available_kib="$(df --output=avail "$REPO_ROOT" | tail -n 1 | tr -d ' ')"
[[ "$available_kib" =~ ^[0-9]+$ ]] || { echo "ERROR: no se pudo medir espacio local" >&2; exit 1; }
((available_kib >= 512000)) || { echo "ERROR: se requieren al menos 500 MiB libres" >&2; exit 1; }

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
  local host="$1"
  shift
  CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
    DISPLAY="${DISPLAY:-:0}" setsid -w ssh -n "${ssh_options[@]}" "$ROBOT_USER@$host" "$@"
}

run_rsync() {
  local source_path="$1"
  local host="$2"
  local destination_path="$3"
  local ssh_command="ssh"
  local option
  for option in "${ssh_options[@]}"; do
    printf -v ssh_command '%s %q' "$ssh_command" "$option"
  done
  CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
    DISPLAY="${DISPLAY:-:0}" setsid -w rsync --archive -e "$ssh_command" \
    "$source_path" "$ROBOT_USER@$host:$destination_path"
}

if [[ -n "${CRUZR_VISION_HOST:-}" ]]; then
  VISION_HOST="$CRUZR_VISION_HOST"
elif nc -z -w2 192.168.11.3 22; then
  VISION_HOST=192.168.11.3
elif nc -z -w2 192.168.42.2 22; then
  VISION_HOST=192.168.42.2
else
  echo "ERROR: Vision no es accesible" >&2
  exit 1
fi
readonly VISION_HOST

status_output="$("$SHADOW_SCRIPT" --status)"
printf '%s\n' "$status_output"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$status_output"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$status_output"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$status_output"
run_ssh "$VISION_HOST" "
  docker image inspect '$INFERENCE_IMAGE' >/dev/null
  test -s '$REMOTE_ADDITIONAL/checkpoint-40000/config.json'
  test -s '$REMOTE_ADDITIONAL/checkpoint-40000/model-00001-of-00002.safetensors'
  test -s '$REMOTE_ADDITIONAL/checkpoint-40000/model-00002-of-00002.safetensors'
  test -d '$REMOTE_ADDITIONAL/safe-runtime/vendor-overrides/gr00t'
  available_kib=\$(df --output=avail /tmp | tail -n 1 | tr -d ' ')
  test \"\$available_kib\" -ge 524288
"
printf 'E3.1_CHECK_OK=mode:image-proxy,metric-grid:blocked,network:none,robot-command:none\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$("$EVIDENCE_SCRIPT" --experiment E3.1)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
python3 "$OOD_EVALUATOR" campaign \
  --dataset "$DATASET" \
  --output-dir "$RUN_DIR/campaign" \
  2>&1 | tee "$RUN_DIR/selection.log"
jq -e '
  .campaign_id == "E3.1"
  and .tasks == [0,2]
  and .unique_source_frame_count == 2
  and .variant_count == 26
  and .metric_grid_status == "BLOCKED_MISSING_RGBD_CALIBRATION_MASK_AND_SCENE_GEOMETRY"
  and .one_proxy_variable_changed_per_sample == true
  and .generalization_claim_allowed == false
' "$RUN_DIR/campaign/campaign.json" >/dev/null

remote_run_dir="$(run_ssh "$VISION_HOST" "mktemp -d /tmp/cruzr-vla-e3.1.XXXXXXXX")"
[[ "$remote_run_dir" =~ ^/tmp/cruzr-vla-e3[.]1[.][A-Za-z0-9]+$ ]] || {
  echo "ERROR: ruta temporal remota inesperada: $remote_run_dir" >&2
  exit 1
}
remote_cleanup_required=1
cleanup_remote_run_dir() {
  run_ssh "$VISION_HOST" "case '$remote_run_dir' in
    /tmp/cruzr-vla-e3.1.*)
      docker run --rm --network none --entrypoint find \
        -v '$remote_run_dir:/offline:rw' \
        '$INFERENCE_IMAGE' /offline -mindepth 1 -delete >/dev/null &&
      rmdir -- '$remote_run_dir'
      ;;
    *) exit 90 ;;
  esac"
}
cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((remote_cleanup_required)); then
    cleanup_remote_run_dir || true
  fi
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E3.1
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
status: FAIL_BEFORE_CERTIFIED_E3_1_COMPLETION
metric_grid_status: BLOCKED_MISSING_RGBD_CALIBRATION_MASK_AND_SCENE_GEOMETRY
physical_movement_commanded: false
robot_state_read: false
recovery_or_stop: REMOTE_TEMP_CLEANUP_ATTEMPTED_AND_PERSISTENT_VLA_WAS_NOT_STARTED
EOF
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

run_ssh "$VISION_HOST" "install -d '$remote_run_dir/samples' '$remote_run_dir/sources/task0' '$remote_run_dir/sources/task2'"
run_rsync "$BASE_EVALUATOR" "$VISION_HOST" "$remote_run_dir/evaluate_checkpoint_offline.py"
run_rsync "$OOD_EVALUATOR" "$VISION_HOST" "$remote_run_dir/evaluate_vla_ood_e3_1.py"
run_rsync "$PROFILE" "$VISION_HOST" "$remote_run_dir/cruzr_s2_vla_profile.json"
run_rsync "$RUN_DIR/campaign/" "$VISION_HOST" "$remote_run_dir/samples/"

for task_id in 0 2; do
  first_manifest_rel="$(
    jq -r --argjson task_id "$task_id" \
      '.sample_manifests[] | select(.task_id == $task_id) | .manifest' \
      "$RUN_DIR/campaign/campaign.json" | head -n 1
  )"
  first_manifest="$RUN_DIR/campaign/$first_manifest_rel"
  parquet_path="$(jq -r '.source.parquet' "$first_manifest")"
  video_path="$(jq -r '.source.video' "$first_manifest")"
  run_rsync "$parquet_path" "$VISION_HOST" "$remote_run_dir/sources/task${task_id}/episode.parquet"
  run_rsync "$video_path" "$VISION_HOST" "$remote_run_dir/sources/task${task_id}/episode.mp4"
done

while IFS=$'\t' read -r task_id relative_manifest; do
  remote_sample_dir="$remote_run_dir/samples/$(dirname -- "$relative_manifest")"
  run_ssh "$VISION_HOST" "
    set -Eeuo pipefail
    test -d '$remote_sample_dir'
    ln '$remote_run_dir/sources/task${task_id}/episode.parquet' '$remote_sample_dir/episode.parquet'
    ln '$remote_run_dir/sources/task${task_id}/episode.mp4' '$remote_sample_dir/episode.mp4'
  "
done < <(jq -r '.sample_manifests[] | [.task_id,.manifest] | @tsv' "$RUN_DIR/campaign/campaign.json")

remote_checkpoint_manifest() {
  run_ssh "$VISION_HOST" "
    cd '$REMOTE_ADDITIONAL/checkpoint-40000'
    sha256sum \
      config.json \
      model.safetensors.index.json \
      model-00001-of-00002.safetensors \
      model-00002-of-00002.safetensors \
      experiment_cfg/metadata.json \
      experiment_cfg/metadata_cyf.json
  "
}

printf 'E3.1_CHECKPOINT_HASHING=before\n'
remote_checkpoint_manifest > "$RUN_DIR/checkpoint_before.sha256"
run_ssh "$VISION_HOST" "docker run --rm --network none --runtime nvidia --entrypoint bash \
  -v '$REMOTE_ADDITIONAL:/home/ubt/additional:ro' \
  -v '/dev/shm:/dev/shm:rw' \
  -v '/tmp:/tmp:rw' \
  -v '$remote_run_dir:/offline:rw' \
  '$INFERENCE_IMAGE' -lc '
    set -Eeuo pipefail
    set +u
    source /home/ubt/additional/vla-onboard/install/setup.bash
    set -u
    export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
    export PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/cruzr-vla-e3.1-pycache
    python3 /offline/evaluate_vla_ood_e3_1.py infer \
      --checkpoint /home/ubt/additional/checkpoint-40000 \
      --profile /offline/cruzr_s2_vla_profile.json \
      --override-parent /home/ubt/additional/safe-runtime/vendor-overrides \
      --campaign-manifest /offline/samples/campaign.json \
      --output-dir /offline/results
  '" 2>&1 | tee "$RUN_DIR/inference.log"

ssh_command="ssh"
for option in "${ssh_options[@]}"; do
  printf -v ssh_command '%s %q' "$ssh_command" "$option"
done
CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" setsid -w rsync --archive -e "$ssh_command" \
  "$ROBOT_USER@$VISION_HOST:$remote_run_dir/results/" "$RUN_DIR/results/"

test -s "$RUN_DIR/results/summary.json"
test "$(find "$RUN_DIR/results/runs" -maxdepth 1 -type f -name '*.json' | wc -l)" -eq 26
test "$(find "$RUN_DIR/results/previews" -maxdepth 1 -type f -name '*.png' | wc -l)" -eq 26
checkpoint_config_sha="$(sha256sum "$CHECKPOINT/config.json")"
checkpoint_config_sha="${checkpoint_config_sha%% *}"
checkpoint_index_sha="$(sha256sum "$CHECKPOINT/model.safetensors.index.json")"
checkpoint_index_sha="${checkpoint_index_sha%% *}"
profile_sha="$(sha256sum "$PROFILE")"
profile_sha="${profile_sha%% *}"
jq -e \
  --arg checkpoint_config_sha "$checkpoint_config_sha" \
  --arg checkpoint_index_sha "$checkpoint_index_sha" \
  --arg profile_sha "$profile_sha" '
  .schema == "cruzr-s2-vla-offline-e3.1-image-proxy-v1"
  and .campaign_id == "E3.1"
  and .mode == "offline_network_none_no_ros_no_robot_image_proxy"
  and .variant_count == 26
  and (.samples | length) == 26
  and ([.samples[].task_id] | unique) == [0,2]
  and ([.samples[].transform.axis] | unique | length) == 3
  and ([.samples[].predicted_action_10x20 | length] | all(. == 10))
  and ([.samples[].predicted_action_10x20[] | length] | all(. == 20))
  and .metric_grid_status == "BLOCKED_MISSING_RGBD_CALIBRATION_MASK_AND_SCENE_GEOMETRY"
  and .one_proxy_variable_changed_per_sample == true
  and .metric_scene_transform_evaluated == false
  and .physical_movement_commanded == false
  and .robot_state_read == false
  and .network_available == false
  and .generalization_claim_allowed == false
  and .checkpoint.config_sha256 == $checkpoint_config_sha
  and .checkpoint.index_sha256 == $checkpoint_index_sha
  and .profile_sha256 == $profile_sha
  and (.aggregates | keys) == ["0","2"]
  and ([.aggregates[].nominal_cross_axis_max_abs_prediction_difference] | all(. == 0))
' "$RUN_DIR/results/summary.json" >/dev/null

for task_id in 0 2; do
  jq -e --argjson task_id "$task_id" '
    [.samples[] | select(.task_id == $task_id)] as $rows
    | ($rows | length) == 13
    and ([$rows[] | select(.transform.is_nominal == true)] | length) == 3
    and ([$rows[].episode_index] | unique | length) == 1
    and ([$rows[].frame_index] | unique | length) == 1
    and ([$rows[].model_seed] | unique) == [0]
  ' "$RUN_DIR/results/summary.json" >/dev/null
done

printf 'E3.1_CHECKPOINT_HASHING=after\n'
remote_checkpoint_manifest > "$RUN_DIR/checkpoint_after.sha256"
cmp -s "$RUN_DIR/checkpoint_before.sha256" "$RUN_DIR/checkpoint_after.sha256"
final_status="$("$SHADOW_SCRIPT" --status)"
printf '%s\n' "$final_status" | tee "$RUN_DIR/final_status.log"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$final_status"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$final_status"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$final_status"
cleanup_remote_run_dir
remote_cleanup_required=0

rejected_variants="$(jq '[.samples[] | select(.verdict == "REJECT_CONSERVATIVE")] | length' "$RUN_DIR/results/summary.json")"
campaign_status="PASS_IMAGE_SPACE_PROXY_METRIC_GRID_BLOCKED"
if ((rejected_variants > 0)); then
  campaign_status="PASS_IMAGE_SPACE_PROXY_WITH_CONSERVATIVE_VIOLATIONS_METRIC_GRID_BLOCKED"
fi
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E3.1
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: $campaign_status
mode: offline_network_none_no_ros_no_robot_image_proxy
source_tasks: 0,2
unique_source_frames: 2
proxy_variants: 26
rejected_proxy_variants: $rejected_variants
metric_grid_status: BLOCKED_MISSING_RGBD_CALIBRATION_MASK_AND_SCENE_GEOMETRY
task0_horizontal_max_action_delta: $(jq -r '.aggregates["0"].axes.horizontal_frame_shift_fraction.max_abs_action_delta_across_grid' "$RUN_DIR/results/summary.json")
task0_zoom_max_action_delta: $(jq -r '.aggregates["0"].axes.global_zoom_factor.max_abs_action_delta_across_grid' "$RUN_DIR/results/summary.json")
task0_perspective_max_action_delta: $(jq -r '.aggregates["0"].axes.global_perspective_yaw_proxy_deg.max_abs_action_delta_across_grid' "$RUN_DIR/results/summary.json")
task2_horizontal_max_action_delta: $(jq -r '.aggregates["2"].axes.horizontal_frame_shift_fraction.max_abs_action_delta_across_grid' "$RUN_DIR/results/summary.json")
task2_zoom_max_action_delta: $(jq -r '.aggregates["2"].axes.global_zoom_factor.max_abs_action_delta_across_grid' "$RUN_DIR/results/summary.json")
task2_perspective_max_action_delta: $(jq -r '.aggregates["2"].axes.global_perspective_yaw_proxy_deg.max_abs_action_delta_across_grid' "$RUN_DIR/results/summary.json")
checkpoint_content_hashes_unchanged: true
checkpoint_training_membership_known: false
generalization_claim_allowed: false
metric_scene_transform_evaluated: false
physical_task_success_evaluated: false
physical_movement_commanded: false
robot_state_read: false
inference_container_final: exited
control_container_final: exited
command_publishers_final: 0
recovery_or_stop: OFFLINE_CONTAINER_REMOVED_AND_VLA_REMAINED_STOPPED
next_experiment_authorized: REVIEW_E3.1_AND_START_E3.2_OFFLINE_SINK_ONLY
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(
  cd "$RUN_DIR"
  sha256sum -c evidence.sha256
)
printf 'E3.1_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E3.1_RESULT=PASS_IMAGE_PROXY_NOT_METRIC_OR_PHYSICAL_OOD\n'
