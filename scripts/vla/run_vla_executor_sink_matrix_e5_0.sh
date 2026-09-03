#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_vla_executor_sink_matrix_e5_0.sh --check
  ./scripts/vla/run_vla_executor_sink_matrix_e5_0.sh --run

E5.0 ejecuta localmente la fault suite completa y una prueba explícita de
máscara/hold para 8 perfiles × 2 fixtures sintéticos. No usa el robot, red,
ROS, inferencia ni publicadores físicos. No requiere caja ni plataforma.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly RUNNER="$SCRIPT_DIR/test_vla_executor_sink.py"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_sink_matrix_e5_0.py"
readonly SINK_MODULE="$SCRIPT_DIR/runtime/vla_executor_sink.py"
readonly UNIT_TEST="$SCRIPT_DIR/runtime/test_vla_executor_sink.py"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_profile.json"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly PROFILES=(P14_A P15_AW P16_AH P17_AL P17_AHW P18_ALW P19_AHL P20_AHLW)
readonly FIXTURES=(low middle)

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in cp find jq mkdir python3 readlink sha256sum sort xargs; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta herramienta: $tool" >&2; exit 1; }
done
for required in "$RUNNER" "$ANALYZER" "$SINK_MODULE" "$UNIT_TEST" "$PROFILE" "$EVIDENCE_SCRIPT"; do
  test -s "$required" || { echo "ERROR: falta $required" >&2; exit 1; }
done

PYTHONDONTWRITEBYTECODE=1 python3 - "$RUNNER" "$ANALYZER" "$SINK_MODULE" "$UNIT_TEST" <<'PY'
import pathlib
import sys
for value in sys.argv[1:]:
    path = pathlib.Path(value)
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
print("E5.0_PYTHON_SYNTAX_OK=1")
PY
PYTHONDONTWRITEBYTECODE=1 python3 "$UNIT_TEST"
PYTHONDONTWRITEBYTECODE=1 python3 - "$SINK_MODULE" <<'PY'
import ast
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)
imports = set()
calls = set()
names = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])
    elif isinstance(node, ast.Name):
        names.add(node.id)
    elif isinstance(node, ast.Attribute):
        names.add(node.attr)
        if isinstance(node.ctx, ast.Load):
            calls.add(node.attr)
forbidden_imports = {"action_msgs", "mc_command_msgs", "mc_state_msgs", "rclpy", "requests", "rosa", "socket", "subprocess", "urllib", "vla_msgs"}
forbidden_calls = {"create_client", "create_publisher", "publish", "send_goal_async"}
forbidden_names = {"RobotCommand", "Gr00tMotionChunk"}
assert not imports & forbidden_imports, imports & forbidden_imports
assert not calls & forbidden_calls, calls & forbidden_calls
assert not names & forbidden_names, names & forbidden_names
assert "/mc/sdk/robot_command" not in source
print("E5.0_STATIC_SAFETY_OK=ros:none,network:none,publisher_api:none,physical_topic:none")
PY
printf 'E5.0_CHECK_OK=profiles:8,fixtures:2,cells:16,robot:none,network:none,movement:none,publishers:0\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E5.0)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E5.0
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
status: FAIL_BEFORE_CERTIFIED_E5_0_COMPLETION
robot_state_read: false
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

mkdir -p "$RUN_DIR/artifacts/runtime" "$RUN_DIR/results"
cp -- "$RUNNER" "$RUN_DIR/artifacts/test_vla_executor_sink.py"
cp -- "$ANALYZER" "$RUN_DIR/artifacts/analyze_vla_sink_matrix_e5_0.py"
cp -- "$SINK_MODULE" "$RUN_DIR/artifacts/runtime/vla_executor_sink.py"
cp -- "$UNIT_TEST" "$RUN_DIR/artifacts/runtime/test_vla_executor_sink.py"
cp -- "$PROFILE" "$RUN_DIR/artifacts/runtime/cruzr_s2_vla_profile.json"

PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/artifacts/runtime/test_vla_executor_sink.py" \
  > "$RUN_DIR/unit_tests.log" 2>&1
printf 'E5.0_UNIT_TESTS=PASS\n'

for axis_profile in "${PROFILES[@]}"; do
  for fixture in "${FIXTURES[@]}"; do
    cell_dir="$RUN_DIR/results/$axis_profile/$fixture"
    mkdir -p "$cell_dir"
    if PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/artifacts/test_vla_executor_sink.py" \
      --axis-profile "$axis_profile" \
      --fixture "$fixture" \
      --fault-suite all \
      --profile "$RUN_DIR/artifacts/runtime/cruzr_s2_vla_profile.json" \
      --output "$cell_dir" \
      > "$cell_dir/fault_suite.log" 2>&1; then
      printf 'E5.0_CELL=%s/%s PASS cases:34\n' "$axis_profile" "$fixture"
    else
      printf 'E5.0_CELL=%s/%s FAIL; vea %s\n' "$axis_profile" "$fixture" "$cell_dir/fault_suite.log" >&2
      exit 1
    fi
  done
done

PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/artifacts/analyze_vla_sink_matrix_e5_0.py" \
  --results "$RUN_DIR/results" \
  --sink "$RUN_DIR/artifacts/runtime/vla_executor_sink.py" \
  --profile "$RUN_DIR/artifacts/runtime/cruzr_s2_vla_profile.json" \
  --output "$RUN_DIR/matrix_summary.json" \
  | tee "$RUN_DIR/matrix_analysis.log"

jq -e '
  .schema == "cruzr-s2-vla-executor-sink-matrix-e5.0-v1"
  and .experiment_id == "E5.0"
  and .mode == "local_pure_python_no_robot_no_network_no_ros_no_publisher"
  and .totals.matrix_cell_count == 16
  and .totals.matrix_cell_pass_count == 16
  and .totals.fault_case_count == 544
  and .totals.valid_case_accepted_count == 32
  and .totals.invalid_case_rejected_count == 512
  and .totals.failed_expectation_count == 0
  and .totals.mask_probe_count == 16
  and .totals.mask_probe_pass_count == 16
  and ([.cells[].passed] | all(. == true))
  and ([.mask_probes[].passed] | all(. == true))
  and .all_expectations_passed == true
  and .robot_state_read == false
  and .network_calls == 0
  and .physical_publishers == 0
  and .physical_movement_commanded == false
  and .physical_executor_authorized == false
' "$RUN_DIR/matrix_summary.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E5.0
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_COMPLETE_SINK_MATRIX_OFFLINE
mode: local_pure_python_no_robot_no_network_no_ros_no_publisher
profiles: 8
fixtures: 2
matrix_cells: 16
fault_cases: 544
valid_cases_accepted: 32
invalid_cases_rejected: 512
failed_expectations: 0
mask_probes_passed: 16
hold_source: synthetic_fixture_midpoint_not_live_robot_state
robot_state_read: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
physical_executor_authorized: false
recovery_or_stop: LOCAL_PROCESS_EXITED_NO_PHYSICAL_EXECUTOR_EXISTED
next_experiment_authorized: E5.1_SHADOW_ONLY
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
printf 'E5.0_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E5.0_RESULT=PASS_COMPLETE_SINK_MATRIX_OFFLINE\n'
