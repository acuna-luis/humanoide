#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_vla_offline_campaign_e3_0.sh --check
  ./scripts/vla/run_vla_offline_campaign_e3_0.sh --run

E3.0 evalúa checkpoint-40000 offline sobre tasks 0–3. Selecciona cinco
episodios distintos por task y frames en fases 0/25/50/75/100 %, y ejecuta
cinco veces el seed 0 por task (36 inferencias totales).

El checkpoint se monta read-only en un contenedor NVIDIA transitorio con
--network none. No inicia ROS, no lee estado vivo y no importa ni publica
RobotCommand. PASS no significa éxito físico de PICK/PLACE ni generalización.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly EVALUATOR="$SCRIPT_DIR/evaluate_checkpoint_offline.py"
readonly TEST_SCRIPT="$SCRIPT_DIR/runtime/test_evaluate_checkpoint_offline.py"
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

for tool in cmp df find jq nc python3 readlink rsync setsid sha256sum sort ssh tee xargs; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta herramienta: $tool" >&2; exit 1; }
done
for required in "$EVALUATOR" "$TEST_SCRIPT" "$PROFILE" "$SHADOW_SCRIPT" "$EVIDENCE_SCRIPT"; do
  test -s "$required" || { echo "ERROR: falta $required" >&2; exit 1; }
done
test -d "$DATASET"
test -s "$CHECKPOINT/config.json"
test -s "$CHECKPOINT/model.safetensors.index.json"

if grep -Eq '^[[:space:]]*(from|import)[[:space:]].*(rclpy|rosa|RobotCommand)' "$EVALUATOR"; then
  echo "ERROR: el evaluador offline contiene una dependencia ROS/RobotCommand" >&2
  exit 1
fi
python3 -m py_compile "$EVALUATOR" "$TEST_SCRIPT"
python3 "$TEST_SCRIPT"

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
    DISPLAY="${DISPLAY:-:0}" setsid -w ssh "${ssh_options[@]}" "$ROBOT_USER@$host" "$@"
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
printf 'E3.0_CHECK_OK=mode:offline,network:none,ros:none,robot-command:none\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$("$EVIDENCE_SCRIPT" --experiment E3.0)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
python3 "$EVALUATOR" campaign \
  --dataset "$DATASET" \
  --seed0-repetitions 5 \
  --output-dir "$RUN_DIR/campaign" \
  2>&1 | tee "$RUN_DIR/selection.log"

jq -e '
  .campaign_id == "E3.0"
  and .unique_sample_count == 20
  and .expected_inference_run_count == 36
  and .tasks == [0,1,2,3]
  and .seeds == [0,1,2,3,4]
  and .seed0_total_repetitions_per_task == 5
' "$RUN_DIR/campaign/campaign.json" >/dev/null
jq -e '
  .global_train_test_overlap == []
  and .selected_episodes_all_in_project_test == true
  and .selected_test_episode_count == 20
  and .checkpoint_training_membership_known == false
' "$RUN_DIR/campaign/split_audit.json" >/dev/null

remote_run_dir="$(run_ssh "$VISION_HOST" "mktemp -d /tmp/cruzr-vla-e3.0.XXXXXXXX")"
[[ "$remote_run_dir" =~ ^/tmp/cruzr-vla-e3[.]0[.][A-Za-z0-9]+$ ]] || {
  echo "ERROR: ruta temporal remota inesperada: $remote_run_dir" >&2
  exit 1
}
remote_cleanup_required=1
cleanup_remote_run_dir() {
  run_ssh "$VISION_HOST" "case '$remote_run_dir' in
    /tmp/cruzr-vla-e3.0.*)
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
experiment_id: E3.0
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
status: FAIL_BEFORE_CERTIFIED_E3_0_COMPLETION
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

run_ssh "$VISION_HOST" "install -d '$remote_run_dir/samples'"
run_rsync "$EVALUATOR" "$VISION_HOST" "$remote_run_dir/evaluate_checkpoint_offline.py"
run_rsync "$PROFILE" "$VISION_HOST" "$remote_run_dir/cruzr_s2_vla_profile.json"
run_rsync "$RUN_DIR/campaign/" "$VISION_HOST" "$remote_run_dir/samples/"

while IFS= read -r relative_manifest; do
  local_manifest="$RUN_DIR/campaign/$relative_manifest"
  remote_sample_dir="$remote_run_dir/samples/$(dirname -- "$relative_manifest")"
  parquet_path="$(jq -r '.source.parquet' "$local_manifest")"
  video_path="$(jq -r '.source.video' "$local_manifest")"
  test -f "$parquet_path"
  test -f "$video_path"
  run_rsync "$parquet_path" "$VISION_HOST" "$remote_sample_dir/episode.parquet"
  run_rsync "$video_path" "$VISION_HOST" "$remote_sample_dir/episode.mp4"
done < <(jq -r '.sample_manifests[].manifest' "$RUN_DIR/campaign/campaign.json")

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

printf 'E3.0_CHECKPOINT_HASHING=before\n'
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
    export PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/cruzr-vla-e3.0-pycache
    python3 /offline/evaluate_checkpoint_offline.py infer \
      --checkpoint /home/ubt/additional/checkpoint-40000 \
      --profile /offline/cruzr_s2_vla_profile.json \
      --override-parent /home/ubt/additional/safe-runtime/vendor-overrides \
      --campaign-manifest /offline/samples/campaign.json \
      --output-dir /offline/results \
      --seed 0
  '" 2>&1 | tee "$RUN_DIR/inference.log"

ssh_command="ssh"
for option in "${ssh_options[@]}"; do
  printf -v ssh_command '%s %q' "$ssh_command" "$option"
done
CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" setsid -w rsync --archive -e "$ssh_command" \
  "$ROBOT_USER@$VISION_HOST:$remote_run_dir/results/" "$RUN_DIR/results/"

test -s "$RUN_DIR/results/summary.json"
test "$(find "$RUN_DIR/results/runs" -maxdepth 1 -type f -name '*.json' | wc -l)" -eq 36
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
  .schema == "cruzr-s2-vla-offline-e3.0-v1"
  and .campaign_id == "E3.0"
  and .mode == "offline_network_none_no_ros_no_robot"
  and .physical_movement_commanded == false
  and .robot_state_read == false
  and .network_available == false
  and .generalization_claim_allowed == false
  and .split_train_test_overlap == []
  and .unique_sample_count == 20
  and .inference_run_count == 36
  and .seed0_total_repetitions_per_task == 5
  and (.samples | length) == 36
  and ([.samples[].task_id] | unique) == [0,1,2,3]
  and ([.samples[] | select(.repetition_index == 0) | .seed] | unique) == [0,1,2,3,4]
  and ([.samples[].predicted_action_10x20 | length] | all(. == 10))
  and ([.samples[].predicted_action_10x20[] | length] | all(. == 20))
  and .checkpoint.config_sha256 == $checkpoint_config_sha
  and .checkpoint.index_sha256 == $checkpoint_index_sha
  and .profile_sha256 == $profile_sha
  and (.aggregates | keys) == ["0","1","2","3"]
' "$RUN_DIR/results/summary.json" >/dev/null

for task_id in 0 1 2 3; do
  jq -e --arg task "$task_id" '
    [.samples[] | select((.task_id | tostring) == $task)] as $rows
    | ($rows | length) == 9
    and ([$rows[] | select(.seed == 0)] | length) == 5
    and ([$rows[] | select(.seed != 0)] | length) == 4
    and ([$rows[] | select(.repetition_index == 0) | .episode_index] | unique | length) == 5
  ' "$RUN_DIR/results/summary.json" >/dev/null
done

printf 'E3.0_CHECKPOINT_HASHING=after\n'
remote_checkpoint_manifest > "$RUN_DIR/checkpoint_after.sha256"
cmp -s "$RUN_DIR/checkpoint_before.sha256" "$RUN_DIR/checkpoint_after.sha256"

final_status="$("$SHADOW_SCRIPT" --status)"
printf '%s\n' "$final_status" | tee "$RUN_DIR/final_status.log"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$final_status"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$final_status"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$final_status"

cleanup_remote_run_dir
remote_cleanup_required=0

baseline_range_violation_samples="$(
  jq '[.aggregates[].baseline_runs_with_range_violations] | add' \
    "$RUN_DIR/results/summary.json"
)"
baseline_first_delta_violation_samples="$(
  jq '[.aggregates[].baseline_runs_with_first_point_delta_violations] | add' \
    "$RUN_DIR/results/summary.json"
)"
campaign_status="PASS_OFFLINE_CAMPAIGN_ONLY"
if ((baseline_range_violation_samples > 0 || baseline_first_delta_violation_samples > 0)); then
  campaign_status="PASS_OFFLINE_CAMPAIGN_WITH_CONSERVATIVE_VIOLATIONS"
fi

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E3.0
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: $campaign_status
mode: offline_network_none_no_ros_no_robot
split: project_stratified_tail_15_percent_not_vendor_split
unique_samples: 20
inference_runs: 36
task0_mean_mae: $(jq -r '.aggregates["0"].baseline_mae.mean' "$RUN_DIR/results/summary.json")
task1_mean_mae: $(jq -r '.aggregates["1"].baseline_mae.mean' "$RUN_DIR/results/summary.json")
task2_mean_mae: $(jq -r '.aggregates["2"].baseline_mae.mean' "$RUN_DIR/results/summary.json")
task3_mean_mae: $(jq -r '.aggregates["3"].baseline_mae.mean' "$RUN_DIR/results/summary.json")
task0_seed0_max_repeat_diff: $(jq -r '.aggregates["0"].seed0_repeatability.max_abs_prediction_difference' "$RUN_DIR/results/summary.json")
task1_seed0_max_repeat_diff: $(jq -r '.aggregates["1"].seed0_repeatability.max_abs_prediction_difference' "$RUN_DIR/results/summary.json")
task2_seed0_max_repeat_diff: $(jq -r '.aggregates["2"].seed0_repeatability.max_abs_prediction_difference' "$RUN_DIR/results/summary.json")
task3_seed0_max_repeat_diff: $(jq -r '.aggregates["3"].seed0_repeatability.max_abs_prediction_difference' "$RUN_DIR/results/summary.json")
baseline_range_violation_samples: $baseline_range_violation_samples
baseline_first_point_delta_violation_samples: $baseline_first_delta_violation_samples
checkpoint_content_hashes_unchanged: true
project_train_test_episode_overlap: 0
checkpoint_training_membership_known: false
generalization_claim_allowed: false
physical_task_success_evaluated: false
physical_movement_commanded: false
robot_state_read: false
inference_container_final: exited
control_container_final: exited
command_publishers_final: 0
recovery_or_stop: OFFLINE_CONTAINER_REMOVED_AND_VLA_REMAINED_STOPPED
next_experiment_authorized: REVIEW_E3.0_AND_START_E3.1_OFFLINE_ONLY
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

printf 'E3.0_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E3.0_RESULT=PASS_OFFLINE_CAMPAIGN_NOT_PHYSICAL_TASK_SUCCESS\n'
