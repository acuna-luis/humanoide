#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/calibrate_vla_fixture_e4_1.sh --check
  ./scripts/vla/calibrate_vla_fixture_e4_1.sh --run

Captura CameraInfo, TF y 20 muestras AprilTag sin mover el robot. Después
deriva offline la pose métrica del fixture del episodio 90. Nunca inicia VLA,
no crea publicadores físicos y no autoriza movimiento.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly SOLVER="$SCRIPT_DIR/derive_vla_fixture_pose.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly TAG_SCRIPT="$REPO_ROOT/scripts/cruzr_apriltag_mesa2_align.sh"
readonly VISION_HOST="${CRUZR_VISION_HOST:-192.168.11.3}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly ROSA_CONTAINER="walker-system.static_tf_node-1"
readonly CAMERA_CONTAINER="walker-stereo.stereo_depth_estimation-1"
readonly DATASET_REL="cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319"
readonly SDK_URDF_ZIP_REL="Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip"
readonly EVIDENCE_ROOT="${VLA_EVIDENCE_ROOT:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence}"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}" ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

for tool in cp dirname find jq nc python3 readlink setsid sha256sum sort ssh tee timeout unzip wc; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta herramienta: %s\n' "$tool" >&2; exit 1; }
done
for required in "$SOLVER" "$EVIDENCE_SCRIPT" "$SHADOW_SCRIPT" "$TAG_SCRIPT" \
  "$REPO_ROOT/$DATASET_REL/meta/info.json" \
  "$REPO_ROOT/$DATASET_REL/meta/episodes_stats.jsonl" \
  "$REPO_ROOT/$SDK_URDF_ZIP_REL"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
python3 -m py_compile "$SOLVER"
nc -z -w3 "$VISION_HOST" 22 || { printf 'ERROR: Vision no responde en %s:22\n' "$VISION_HOST" >&2; exit 1; }

ssh_options=(
  -o ConnectTimeout=10
  -o ConnectionAttempts=1
  -o PreferredAuthentications=password
  -o PubkeyAuthentication=no
  -o NumberOfPasswordPrompts=2
  -o StrictHostKeyChecking=accept-new
)

run_ssh() {
  CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
    DISPLAY="${DISPLAY:-:0}" setsid -w ssh "${ssh_options[@]}" "$ROBOT_USER@$VISION_HOST" "$@"
}

status_before="$($SHADOW_SCRIPT --status)"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$status_before"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$status_before"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$status_before"

latest_e4_2="$(find "$EVIDENCE_ROOT" -mindepth 2 -maxdepth 2 -type f \
  -path '*_E4.2/actual_result.yaml' -printf '%T@ %h\n' | sort -nr | \
  awk 'NR==1 {$1=""; sub(/^ /, ""); print; exit}')"
test -n "$latest_e4_2" || { echo 'ERROR: no existe evidencia E4.2' >&2; exit 1; }
(
  cd "$latest_e4_2"
  sha256sum -c evidence.sha256 >/dev/null
)
reference_frame="$latest_e4_2/representative_frames/profile_100_task_2_episode_000090_start.png"
test -s "$reference_frame"

printf '%s\n' "$status_before"
printf 'E4.1_CHECK_OK=vision:%s,tag:113,episode:90,mode:no-motion\n' "$VISION_HOST"
printf 'SOURCE_E4.2=%s\n' "$latest_e4_2"
printf 'INFERENCE_STARTED=0; PUBLISHERS_CREATED=0; MOVEMENT_COMMANDS=0\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E4.1)"
mkdir -- "$RUN_DIR/artifacts" "$RUN_DIR/results"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.1
run_id: $(basename -- "$RUN_DIR")
status: FAIL_BEFORE_COMPLETING_METRIC_CALIBRATION
physical_movement_commanded: false
physical_publisher_created: false
inference_started: false
recovery_or_stop: NOT_APPLICABLE_NO_COMMAND_PATH
EOF
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf '%s\n' "$status_before" > "$RUN_DIR/status_before.log"
printf '%s\n' "$latest_e4_2" > "$RUN_DIR/e4_2_source_path.txt"
cp -- "$reference_frame" "$RUN_DIR/artifacts/episode_000090_start.png"
cp -- "$REPO_ROOT/$DATASET_REL/meta/info.json" "$RUN_DIR/artifacts/dataset_info.json"
cp -- "$REPO_ROOT/$DATASET_REL/meta/episodes_stats.jsonl" "$RUN_DIR/artifacts/episodes_stats.jsonl"
cp -- "$SOLVER" "$RUN_DIR/artifacts/derive_vla_fixture_pose.py"
unzip -p "$REPO_ROOT/$SDK_URDF_ZIP_REL" '*/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf' \
  > "$RUN_DIR/artifacts/cruzr_s2_v1.urdf"
unzip -p "$REPO_ROOT/$SDK_URDF_ZIP_REL" '*/meshes/cruzr_s2_v1/base_link.STL' \
  > "$RUN_DIR/artifacts/base_link.STL"

run_ssh "docker exec '$CAMERA_CONTAINER' bash -lc '
  set -Eeo pipefail
  set +u
  source /opt/walker/setup.bash
  set -u
  export ROS2CLI_DISABLE_DAEMON=1
  timeout 12 rosa topic echo --once --no-daemon --qos-reliability reliable --qos-durability transient_local /sensor/camera/stereo/color/info
'" > "$RUN_DIR/artifacts/camera_info.json"
jq -e '
  .width == 960 and .height == 576
  and .header.frame_id == "stereo_left_rectified_optical_frame"
  and (.k | length) == 9
' "$RUN_DIR/artifacts/camera_info.json" >/dev/null

capture_tf() {
  local topic="$1"
  local output="$2"
  local qos="$3"
  local return_code
  set +e
  run_ssh "docker exec '$ROSA_CONTAINER' bash -lc '
    set +u
    source /opt/walker/setup.bash
    set -u
    export ROS2CLI_DISABLE_DAEMON=1
    timeout 8 rosa topic echo --no-daemon $qos $topic
  '" > "$output" 2> "$output.stderr"
  return_code=$?
  set -e
  [[ "$return_code" == "0" || "$return_code" == "124" ]]
  test -s "$output"
}

capture_tf /tf "$RUN_DIR/artifacts/tf.jsonstream" ""
capture_tf /tf_static "$RUN_DIR/artifacts/tf_static.jsonstream" \
  "--qos-reliability reliable --qos-durability transient_local"

"$TAG_SCRIPT" --measure-calibration-target 2>&1 | tee "$RUN_DIR/artifacts/tag_113_20_samples.log"
grep -Fq 'TAG_QUALITY=samples:20' "$RUN_DIR/artifacts/tag_113_20_samples.log"

python3 "$SOLVER" \
  --urdf "$RUN_DIR/artifacts/cruzr_s2_v1.urdf" \
  --tf-static "$RUN_DIR/artifacts/tf_static.jsonstream" \
  --tf-live "$RUN_DIR/artifacts/tf.jsonstream" \
  --camera-info "$RUN_DIR/artifacts/camera_info.json" \
  --dataset-info "$RUN_DIR/artifacts/dataset_info.json" \
  --episode-stats "$RUN_DIR/artifacts/episodes_stats.jsonl" \
  --reference-frame "$RUN_DIR/artifacts/episode_000090_start.png" \
  --tag-log "$RUN_DIR/artifacts/tag_113_20_samples.log" \
  --base-mesh "$RUN_DIR/artifacts/base_link.STL" \
  --output-dir "$RUN_DIR/results" \
  --episode 90 --rim-pixels 307,293,713,293 \
  --box-lwh 0.603,0.397,0.217 --table-wh 1.800,0.800 \
  --platform-height 1.000 --box-front-clearance 0.050 \
  2>&1 | tee "$RUN_DIR/solver.log"

jq -e '
  .experiment_id == "E4.1"
  and .status == "METRIC_FIXTURE_CANDIDATE_RESOLVED_PHYSICAL_GATES_OPEN"
  and .gates.metric_width_residual_within_5mm == true
  and .gates.live_tag_20_samples_stable == true
  and .gates.physical_test_authorized == false
  and (.fixture.width_residual_mm | fabs) <= 5
' "$RUN_DIR/results/summary.json" >/dev/null

status_after="$($SHADOW_SCRIPT --status)"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$status_after"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$status_after"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$status_after"
printf '%s\n' "$status_after" > "$RUN_DIR/status_after.log"

END_TIME="$(date --iso-8601=seconds)"
platform_pose="$(jq -r '[.platform_in_base.x_m,.platform_in_base.y_m,.platform_in_base.z_m,.platform_in_base.roll_rad,.platform_in_base.pitch_rad,.platform_in_base.yaw_rad] | @csv' "$RUN_DIR/results/summary.json")"
bumper_distance="$(jq -r '.D_BUMPER_PLATFORM.signed_m' "$RUN_DIR/results/summary.json")"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.1
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $END_TIME
status: METRIC_FIXTURE_CANDIDATE_RESOLVED_PHYSICAL_GATES_OPEN
scenario_id: MESA_T1_EPISODE_90_METRIC_RECONSTRUCTION
platform_in_base_csv: '$platform_pose'
D_BUMPER_PLATFORM_signed_m: $bumper_distance
camera_model: stereo_left_rectified_optical_frame,960x576
tag_validation: id113,20-samples,current-safe-far-pose
historical_rim_pixels: '307,293,713,293'
physical_movement_commanded: false
physical_publisher_created: false
inference_started: false
physical_test_authorized: false
blocking_gates:
  - canonical_ready_and_inverse_incomplete
  - swept_volume_and_table_collision_not_validated
  - negative_bumper_projection_requires_physical_geometry_review
final_robot_state: NOT_CHANGED_BY_THIS_READ_ONLY_CALIBRATION
recovery_or_stop: NOT_APPLICABLE_NO_COMMAND_PATH
next_experiment_authorized: E4.1_REVIEW_AND_COLLISION_MODELING_ONLY
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(
  cd "$RUN_DIR"
  sha256sum -c evidence.sha256 >/dev/null
)

printf 'E4.1_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E4.1_RESULT=METRIC_FIXTURE_CANDIDATE_RESOLVED_PHYSICAL_GATES_OPEN\n'
printf 'PHYSICAL_TEST_AUTHORIZED=0\n'
