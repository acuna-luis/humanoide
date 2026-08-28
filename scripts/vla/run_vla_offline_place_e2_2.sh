#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_vla_offline_place_e2_2.sh --check
  ./scripts/vla/run_vla_offline_place_e2_2.sh --run [--seed 0]

Selecciona un episodio HELD reproducible para PLACE bajo (task 1) y medio
(task 3), carga checkpoint-40000 una sola vez dentro de un contenedor NVIDIA
con --network none y compara cada predicción 10x20 con la acción real.

No inicia ROS, no lee estado vivo y no importa ni publica RobotCommand.
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
SEED=0
CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD

if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --seed)
      (($# >= 2)) || { echo "ERROR: --seed requiere entero" >&2; exit 2; }
      SEED="$2"
      shift 2
      ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$SEED" =~ ^[0-9]+$ ]] || { echo "ERROR: --seed debe ser entero no negativo" >&2; exit 2; }
for tool in jq nc python3 readlink rsync setsid sha256sum ssh tee; do
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

run_ssh "$VISION_HOST" "docker image inspect '$INFERENCE_IMAGE' >/dev/null; test -s '$REMOTE_ADDITIONAL/checkpoint-40000/config.json'; test -d '$REMOTE_ADDITIONAL/safe-runtime/vendor-overrides/gr00t'"
printf 'E2.2_CHECK_OK=mode:offline,network:none,ros:none,robot-command:none\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$("$EVIDENCE_SCRIPT" --experiment E2.2)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

for task_id in 1 3; do
  task_dir="$RUN_DIR/task${task_id}"
  mkdir -p "$task_dir"
  python3 "$EVALUATOR" select \
    --dataset "$DATASET" \
    --task-id "$task_id" \
    --split test \
    --seed "$SEED" \
    --frame-index 0 \
    --output "$task_dir/selection.json" \
    2>&1 | tee "$task_dir/selection.log"
done

remote_run_dir="$(run_ssh "$VISION_HOST" "mktemp -d /tmp/cruzr-vla-e2.2.XXXXXXXX")"
[[ "$remote_run_dir" =~ ^/tmp/cruzr-vla-e2[.]2[.][A-Za-z0-9]+$ ]] || {
  echo "ERROR: ruta temporal remota inesperada: $remote_run_dir" >&2
  exit 1
}
remote_cleanup_required=1
cleanup_remote_run_dir() {
  # Los procesos del contenedor escriben como root. Borrar primero el
  # contenido desde otro contenedor sin red evita dejar artefactos root-owned
  # y permite después eliminar el directorio, que sí pertenece a walker.
  run_ssh "$VISION_HOST" "case '$remote_run_dir' in
    /tmp/cruzr-vla-e2.2.*)
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
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

run_ssh "$VISION_HOST" "install -d '$remote_run_dir/task1' '$remote_run_dir/task3'"
run_rsync "$EVALUATOR" "$VISION_HOST" "$remote_run_dir/evaluate_checkpoint_offline.py"
run_rsync "$PROFILE" "$VISION_HOST" "$remote_run_dir/cruzr_s2_vla_profile.json"

for task_id in 1 3; do
  task_dir="$RUN_DIR/task${task_id}"
  parquet_path="$(jq -r '.source.parquet' "$task_dir/selection.json")"
  video_path="$(jq -r '.source.video' "$task_dir/selection.json")"
  test -f "$parquet_path"
  test -f "$video_path"
  run_rsync "$task_dir/selection.json" "$VISION_HOST" "$remote_run_dir/task${task_id}/selection.json"
  run_rsync "$parquet_path" "$VISION_HOST" "$remote_run_dir/task${task_id}/episode.parquet"
  run_rsync "$video_path" "$VISION_HOST" "$remote_run_dir/task${task_id}/episode.mp4"
done

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
    export PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/cruzr-vla-e2.2-pycache
    python3 /offline/evaluate_checkpoint_offline.py infer \
      --checkpoint /home/ubt/additional/checkpoint-40000 \
      --profile /offline/cruzr_s2_vla_profile.json \
      --override-parent /home/ubt/additional/safe-runtime/vendor-overrides \
      --sample-manifest /offline/task1/selection.json \
      --sample-manifest /offline/task3/selection.json \
      --output-dir /offline/results \
      --seed $SEED
  '" 2>&1 | tee "$RUN_DIR/inference.log"

# Download with the same authenticated SSH transport; source is remote here.
ssh_command="ssh"
for option in "${ssh_options[@]}"; do
  printf -v ssh_command '%s %q' "$ssh_command" "$option"
done
CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" setsid -w rsync --archive -e "$ssh_command" \
  "$ROBOT_USER@$VISION_HOST:$remote_run_dir/results/" "$RUN_DIR/results/"

test -s "$RUN_DIR/results/summary.json"
checkpoint_config_sha="$(sha256sum "$CHECKPOINT/config.json")"
checkpoint_config_sha="${checkpoint_config_sha%% *}"
checkpoint_index_sha="$(sha256sum "$CHECKPOINT/model.safetensors.index.json")"
checkpoint_index_sha="${checkpoint_index_sha%% *}"
profile_sha="$(sha256sum "$PROFILE")"
profile_sha="${profile_sha%% *}"
for task_id in 1 3; do
  test -s "$RUN_DIR/results/task${task_id}_result.json"
  jq -e --argjson task_id "$task_id" \
    '.task_id == $task_id and .physical_task_success_evaluated == false and (.predicted_action_10x20|length) == 10 and ([.predicted_action_10x20[]|length]|all(. == 20))' \
    "$RUN_DIR/results/task${task_id}_result.json" >/dev/null
done
jq -e \
  --arg checkpoint_config_sha "$checkpoint_config_sha" \
  --arg checkpoint_index_sha "$checkpoint_index_sha" \
  --arg profile_sha "$profile_sha" \
  '.mode == "offline_network_none_no_ros_no_robot"
    and .physical_movement_commanded == false
    and .robot_state_read == false
    and .network_available == false
    and (.samples|length) == 2
    and .checkpoint.config_sha256 == $checkpoint_config_sha
    and .checkpoint.index_sha256 == $checkpoint_index_sha
    and .profile_sha256 == $profile_sha' \
  "$RUN_DIR/results/summary.json" >/dev/null

final_status="$("$SHADOW_SCRIPT" --status)"
printf '%s\n' "$final_status" | tee "$RUN_DIR/final_status.log"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$final_status"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$final_status"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$final_status"

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E2.2
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_OFFLINE_INFERENCE_ONLY
mode: offline_network_none_no_ros_no_robot
split: project_stratified_tail_15_percent_not_vendor_split
seed: $SEED
task1_episode: $(jq -r '.episode_index' "$RUN_DIR/task1/selection.json")
task3_episode: $(jq -r '.episode_index' "$RUN_DIR/task3/selection.json")
task1_verdict: $(jq -r '.verdict' "$RUN_DIR/results/task1_result.json")
task3_verdict: $(jq -r '.verdict' "$RUN_DIR/results/task3_result.json")
task1_mae: $(jq -r '.metrics.mae' "$RUN_DIR/results/task1_result.json")
task3_mae: $(jq -r '.metrics.mae' "$RUN_DIR/results/task3_result.json")
physical_task_success_evaluated: false
physical_movement_commanded: false
robot_state_read: false
inference_container_final: exited
control_container_final: exited
command_publishers_final: 0
recovery_or_stop: OFFLINE_CONTAINER_REMOVED_AND_VLA_REMAINED_STOPPED
next_experiment_authorized: REVIEW_E2.2_AND_START_E3_OFFLINE_ONLY
EOF

(
  cd "$RUN_DIR"
  sha256sum \
    task1/selection.json task1/selection.log \
    task3/selection.json task3/selection.log \
    inference.log final_status.log \
    results/summary.json results/task1_result.json results/task3_result.json \
    actual_result.yaml
) > "$RUN_DIR/evidence.sha256"
(
  cd "$RUN_DIR"
  sha256sum -c evidence.sha256
)

cleanup_remote_run_dir
remote_cleanup_required=0
printf 'E2.2_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E2.2_RESULT=PASS_OFFLINE_INFERENCE_NOT_PHYSICAL_PLACE_SUCCESS\n'
