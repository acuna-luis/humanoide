#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_vla_temporal_contract_e3_3.sh --check
  ./scripts/vla/run_vla_temporal_contract_e3_3.sh --run

E3.3 audita estáticamente el timeline UBTECH y ejecuta un scheduler local
fail-closed. No importa ROS, no arranca contenedores, no lee estado del robot,
no crea publicadores y no manda hardware.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly RUNNER="$SCRIPT_DIR/test_vla_temporal_contract_e3_3.py"
readonly MODULE="$SCRIPT_DIR/runtime/vla_temporal_contract.py"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_temporal_contract_e3_3.json"
readonly UNIT_TEST="$SCRIPT_DIR/runtime/test_vla_temporal_contract.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly EVIDENCE_ROOT="${VLA_EVIDENCE_ROOT:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence}"

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in find jq python3 readlink sha256sum sort tee xargs; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta herramienta: $tool" >&2; exit 1; }
done
for required in "$RUNNER" "$MODULE" "$CONTRACT" "$UNIT_TEST" "$EVIDENCE_SCRIPT" "$SHADOW_SCRIPT"; do
  test -s "$required" || { echo "ERROR: falta $required" >&2; exit 1; }
done

python3 -m py_compile "$RUNNER" "$MODULE" "$UNIT_TEST"
python3 "$UNIT_TEST"
python3 - "$MODULE" <<'PY'
import ast
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)
imports = set()
called = set()
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
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        called.add(node.func.attr)
forbidden_imports = {"rclpy", "socket", "subprocess", "requests", "urllib", "vla_msgs", "mc_task_msgs"}
forbidden_calls = {"create_publisher", "publish", "send_goal_async", "create_client"}
forbidden_names = {"RobotCommand", "Gr00tMotionChunk"}
assert not imports & forbidden_imports, imports & forbidden_imports
assert not called & forbidden_calls, called & forbidden_calls
assert not names & forbidden_names, names & forbidden_names
assert "/mc/sdk/robot_command" not in source
print("E3.3_STATIC_SAFETY_OK=ros:none,network:none,publisher_api:none,physical_topic:none")
PY

status_before="$($SHADOW_SCRIPT --status)"
printf '%s\n' "$status_before"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$status_before"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$status_before"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$status_before"
printf 'E3.3_CHECK_OK=mode:offline-temporal,robot-state:none,movement:none,publishers:0\n'
[[ "$MODE" == "run" ]] || exit 0

e2_summary=""
if [[ -d "$EVIDENCE_ROOT" ]]; then
  e2_summary="$(find "$EVIDENCE_ROOT" -mindepth 2 -maxdepth 2 -type f \( -name repetitions_summary.json -o -name shadow_summary.json \) -printf '%T@ %p\n' | sort -nr | awk 'NR==1 {$1=""; sub(/^ /, ""); print; exit}')"
fi
test -n "$e2_summary" || { echo "ERROR: no se encontró evidencia E2 previa" >&2; exit 1; }
test -s "$e2_summary" || { echo "ERROR: evidencia E2 inválida: $e2_summary" >&2; exit 1; }

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E3.3)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E3.3
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
status: FAIL_BEFORE_CERTIFIED_E3_3_COMPLETION
physical_movement_commanded: false
robot_state_read: false
recovery_or_stop: LOCAL_SIMULATOR_TERMINATED_NO_PHYSICAL_EXECUTOR_EXISTED
EOF
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf '%s\n' "$status_before" > "$RUN_DIR/status_before.log"
printf '%s\n' "$e2_summary" > "$RUN_DIR/e2_source_path.txt"
python3 "$RUNNER" \
  --contract "$CONTRACT" \
  --e2-summary "$e2_summary" \
  --output "$RUN_DIR" \
  2>&1 | tee "$RUN_DIR/temporal_suite.log"

contract_sha="$(sha256sum "$CONTRACT")"
contract_sha="${contract_sha%% *}"
jq -e --arg contract_sha "$contract_sha" '
  .schema == "cruzr-s2-vla-temporal-contract-e3.3-v1"
  and .experiment_id == "E3.3"
  and .contract_sha256 == $contract_sha
  and .mode == "local_pure_python_temporal_simulation_plus_static_vendor_audit"
  and .case_count == 22
  and .passed_case_count == 22
  and .failed_case_count == 0
  and .all_expectations_passed == true
  and .static_safety.safe == true
  and .vendor_audit.vision_inference_hz == 0.2
  and .vendor_audit.vision_nominal_period_seconds == 5
  and .vendor_audit.chunk_point_count == 10
  and .vendor_audit.chunk_point_dt_seconds == 0.08
  and .vendor_audit.chunk_declared_horizon_seconds == 0.72
  and .vendor_audit.yaml_continuous_end_chunk_num == 5
  and .vendor_audit.vision_uses_single_end_flag_assignment == true
  and .vendor_audit.model_uses_strict_greater_than_threshold == true
  and .vendor_audit.continuous_end_chunk_num_referenced_by_runtime_python == false
  and .vendor_audit.source_executor_interpolation_seconds == 9
  and .vendor_audit.installed_executor_interpolation_seconds == 6
  and .vendor_audit.executor_copies_temporally_consistent == false
  and .e2_observations.available == true
  and .local_contract_status == "PASS_FAIL_CLOSED_OFFLINE"
  and .physical_executor_authorized == false
  and .physical_movement_commanded == false
  and .robot_state_read == false
  and .physical_publisher_count == 0
  and ([.cases[].passed] | all(. == true))
  and ([.cases[].physical_publisher_count] | all(. == 0))
' "$RUN_DIR/summary.json" >/dev/null
test "$(wc -l < "$RUN_DIR/cases.jsonl")" -eq 22

status_after="$($SHADOW_SCRIPT --status)"
printf '%s\n' "$status_after" | tee "$RUN_DIR/status_after.log"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$status_after"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$status_after"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$status_after"

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E3.3
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_LOCAL_TEMPORAL_FAIL_CLOSED_VENDOR_SEMANTICS_UNRESOLVED
mode: local_pure_python_temporal_simulation_plus_static_vendor_audit
cases: 22
cases_passed: 22
chunk_declared_timeline: 10_points_at_80ms_horizon_0.72s
vendor_inference_period: 5s
vendor_source_executor_interpolation: 9s
vendor_installed_executor_interpolation: 6s
vendor_end_behavior: single_flag_strictly_above_0.1
vendor_declared_but_unused_end_rule: 5_consecutive_chunks
local_candidate_end_rule: 5_consecutive_chunks_then_complete_after_final_endpoint
local_gap_policy: no_replay_timeout_after_0.5s
local_cancel_stop_fault_policy: immediate_queue_purge_in_same_logical_event
static_ros_imports: 0
static_network_imports: 0
static_publisher_or_action_calls: 0
physical_publishers: 0
persistent_inference_container_final: exited
persistent_control_container_final: exited
command_publishers_final: 0
robot_state_read: false
physical_movement_commanded: false
physical_executor_authorized: false
gate_vla_3_closed: false
recovery_or_stop: LOCAL_SIMULATOR_EXITED_AND_PERSISTENT_VLA_REMAINED_STOPPED
next_experiment_authorized: E4.0_READ_ONLY_ARTIFACT_RESOLUTION_ONLY
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(
  cd "$RUN_DIR"
  sha256sum -c evidence.sha256
)
printf 'E3.3_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E3.3_RESULT=PASS_LOCAL_TEMPORAL_FAIL_CLOSED_VENDOR_SEMANTICS_UNRESOLVED\n'
