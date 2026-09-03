#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_vla_shadow_matrix_e5_1.sh --check
  ./scripts/vla/run_vla_shadow_matrix_e5_1.sh --run

Ejecuta E5.1 completa: 4 tasks × 8 perfiles × 5 salidas C0 congeladas = 160
bundles. Las máscaras se aplican al mismo conjunto base por perfil para aislar
su efecto. Todo es replay shadow local; no conecta ni mueve el robot.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly MATRIX_CELL="$SCRIPT_DIR/run_vla_shadow_matrix.sh"
readonly BUILDER="$SCRIPT_DIR/build_vla_shadow_matrix_e5_1.py"
readonly SINK="$SCRIPT_DIR/runtime/vla_executor_sink.py"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_profile.json"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly SOURCE_CAMPAIGN="${VLA_E5_1_SOURCE_CAMPAIGN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260828T114346_E3.0}"
readonly PROFILES=(P14_A P15_AW P16_AH P17_AL P17_AHW P18_ALW P19_AHL P20_AHLW)

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in cmp cp find jq python3 readlink sha256sum sort xargs; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta herramienta: $tool" >&2; exit 1; }
done
for required in "$MATRIX_CELL" "$BUILDER" "$SINK" "$PROFILE" "$EVIDENCE_SCRIPT" "$SOURCE_CAMPAIGN/evidence.sha256"; do
  test -s "$required" || { echo "ERROR: falta $required" >&2; exit 1; }
done

PYTHONDONTWRITEBYTECODE=1 python3 - "$BUILDER" "$SINK" <<'PY'
import ast
import pathlib
import sys
for value in sys.argv[1:]:
    path = pathlib.Path(value)
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    tree = ast.parse(source)
    imports = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            calls.add(node.func.attr)
    assert not imports & {"rclpy", "rosa", "socket", "requests", "subprocess", "urllib"}
    assert not calls & {"create_client", "create_publisher", "publish", "send_goal_async"}
    assert "/mc/sdk/robot_command" not in source
print("E5.1_STATIC_SAFETY_OK=ros:none,network:none,publisher_api:none,physical_topic:none")
PY
(
  cd "$SOURCE_CAMPAIGN"
  sha256sum -c evidence.sha256 >/dev/null
)
cmp -s "$SOURCE_CAMPAIGN/checkpoint_before.sha256" "$SOURCE_CAMPAIGN/checkpoint_after.sha256"
for task_id in 0 1 2 3; do
  for seed in 0 1 2 3 4; do
    test -s "$SOURCE_CAMPAIGN/results/runs/task${task_id}_seed${seed}_rep0.json"
  done
done
printf 'E5.1_SOURCE_OK=E3.0-hashes-valid,checkpoint-unchanged,base-inferences:20\n'
printf 'E5.1_CHECK_OK=tasks:4,profiles:8,repetitions:5,bundles:160,robot:none,network:none,publishers:0\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E5.1)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E5.1
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
status: FAIL_BEFORE_COMPLETE_REPLAY_MATRIX
robot_state_read_live: false
network_calls: 0
physical_movement_commanded: false
recovery_or_stop: LOCAL_PROCESS_TERMINATED_NO_PHYSICAL_EXECUTOR_EXISTED
EOF
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

mkdir -p "$RUN_DIR/artifacts" "$RUN_DIR/results"
cp -- "$MATRIX_CELL" "$BUILDER" "$SINK" "$PROFILE" "$RUN_DIR/artifacts/"
cp -- "$SOURCE_CAMPAIGN/checkpoint_before.sha256" "$RUN_DIR/source_checkpoint.sha256"
sha256sum "$SOURCE_CAMPAIGN/evidence.sha256" > "$RUN_DIR/source_evidence_manifest.sha256"

for task_id in 0 1 2 3; do
  case "$task_id" in
    0) scenario=SUPPORTED_LOW ;;
    1) scenario=HELD_LOW ;;
    2) scenario=SUPPORTED_MIDDLE ;;
    3) scenario=HELD_MIDDLE ;;
  esac
  for axis_profile in "${PROFILES[@]}"; do
    cell_dir="$RUN_DIR/results/task${task_id}/$axis_profile"
    "$MATRIX_CELL" \
      --source-campaign "$SOURCE_CAMPAIGN" \
      --scenario "$scenario" \
      --task-id "$task_id" \
      --axis-profile "$axis_profile" \
      --repetitions 5 \
      --output "$cell_dir" \
      > "$RUN_DIR/task${task_id}_${axis_profile}.log" 2>&1
    tail -n 1 "$RUN_DIR/task${task_id}_${axis_profile}.log"
  done
done

find "$RUN_DIR/results" -type f -path '*/bundles/rep_*.json' -print0 \
  | sort -z \
  | xargs -0 -r jq -c '.' > "$RUN_DIR/bundles.jsonl"
mapfile -d '' summaries < <(find "$RUN_DIR/results" -type f -name cell_summary.json -print0 | sort -z)
[[ "${#summaries[@]}" -eq 32 ]]
jq -s '
  {
    schema: "cruzr-s2-vla-shadow-matrix-e5.1-v1",
    experiment_id: "E5.1",
    mode: "offline_shadow_replay_no_robot_no_ros_no_publisher",
    source_base_inference_count: 20,
    mask_profiles_per_base_inference: 8,
    cells: .,
    totals: {
      cell_count: length,
      bundle_count: (map(.bundle_count) | add),
      accepted_count: (map(.accepted_count) | add),
      rejected_safe_count: (map(.rejected_safe_count) | add),
      mask_contract_pass_count: (map(.mask_contract_pass_count) | add)
    },
    telemetry: {
      gpu_vram: "NOT_CAPTURED_BY_SOURCE_E3.0",
      runtime_frequency: "NOT_CAPTURED_BY_SOURCE_E3.0",
      flag_pred: "NOT_EMITTED_BY_SOURCE_E3.0"
    },
    scenario_semantics: "recorded_dataset_frames_not_live_fixture",
    physical_task_success_evaluated: false,
    live_fixture_evaluated: false,
    robot_state_read_live: false,
    network_calls: 0,
    physical_publishers: 0,
    physical_movement_commanded: false,
    physical_executor_authorized: false,
    next_experiment_authorized: "E5.2_OFFLINE_PRELIMINARY_SELECTION"
  }
' "${summaries[@]}" > "$RUN_DIR/matrix_summary.json"

jq -e '
  .schema == "cruzr-s2-vla-shadow-matrix-e5.1-v1"
  and .totals.cell_count == 32
  and .totals.bundle_count == 160
  and (.totals.accepted_count + .totals.rejected_safe_count == 160)
  and .totals.mask_contract_pass_count == 160
  and ([.cells[].bundle_count] | all(. == 5))
  and ([.cells[].all_bundles_accounted] | all(. == true))
  and .robot_state_read_live == false
  and .network_calls == 0
  and .physical_publishers == 0
  and .physical_movement_commanded == false
  and .physical_executor_authorized == false
' "$RUN_DIR/matrix_summary.json" >/dev/null
test "$(wc -l < "$RUN_DIR/bundles.jsonl")" -eq 160

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E5.1
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_COMPLETE_OFFLINE_SHADOW_REPLAY_MATRIX
mode: offline_shadow_replay_no_robot_no_ros_no_publisher
source_campaign: $SOURCE_CAMPAIGN
source_base_inferences: 20
profile_bundles_per_base_inference: 8
tasks: 4
profiles: 8
repetitions_per_cell: 5
cells: 32
bundles: 160
accepted_structural: $(jq -r '.totals.accepted_count' "$RUN_DIR/matrix_summary.json")
rejected_safe: $(jq -r '.totals.rejected_safe_count' "$RUN_DIR/matrix_summary.json")
mask_contract_passed: 160
scenario_semantics: recorded_dataset_frames_not_live_fixture
gpu_vram: NOT_CAPTURED_BY_SOURCE_E3.0
runtime_frequency: NOT_CAPTURED_BY_SOURCE_E3.0
flag_pred: NOT_EMITTED_BY_SOURCE_E3.0
physical_task_success_evaluated: false
live_fixture_evaluated: false
robot_state_read_live: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
physical_executor_authorized: false
recovery_or_stop: LOCAL_PROCESS_EXITED_NO_PHYSICAL_EXECUTOR_EXISTED
next_experiment_authorized: E5.2_OFFLINE_PRELIMINARY_SELECTION
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
) >/dev/null
printf 'E5.1_MATRIX=cells:32,bundles:160,accepted:%s,rejected_safe:%s,mask:160/160\n' \
  "$(jq -r '.totals.accepted_count' "$RUN_DIR/matrix_summary.json")" \
  "$(jq -r '.totals.rejected_safe_count' "$RUN_DIR/matrix_summary.json")"
printf 'E5.1_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E5.1_RESULT=PASS_COMPLETE_OFFLINE_SHADOW_REPLAY_MATRIX\n'
