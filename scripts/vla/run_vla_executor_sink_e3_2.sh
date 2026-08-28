#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_vla_executor_sink_e3_2.sh --check
  ./scripts/vla/run_vla_executor_sink_e3_2.sh --run

E3.2 ejecuta una suite de mensajes inválidos contra un sink Python local.
El sink no importa ROS, no usa red, no crea publicadores y no manda hardware.
El wrapper consulta antes/después que el VLA persistente siga detenido y con
cero publicadores; esa consulta es sólo lectura y no aporta estado al sink.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly RUNNER="$SCRIPT_DIR/test_vla_executor_sink.py"
readonly SINK_MODULE="$SCRIPT_DIR/runtime/vla_executor_sink.py"
readonly UNIT_TEST="$SCRIPT_DIR/runtime/test_vla_executor_sink.py"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_profile.json"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"

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
for required in \
  "$RUNNER" "$SINK_MODULE" "$UNIT_TEST" "$PROFILE" \
  "$EVIDENCE_SCRIPT" "$SHADOW_SCRIPT"; do
  test -s "$required" || { echo "ERROR: falta $required" >&2; exit 1; }
done

python3 -m py_compile "$RUNNER" "$SINK_MODULE" "$UNIT_TEST"
python3 "$UNIT_TEST"
python3 - "$SINK_MODULE" <<'PY'
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
forbidden_imports = {
    "action_msgs", "mc_command_msgs", "mc_state_msgs", "rclpy", "requests",
    "rosa", "socket", "subprocess", "urllib", "vla_msgs",
}
forbidden_calls = {"create_client", "create_publisher", "publish", "send_goal_async"}
forbidden_names = {"RobotCommand", "Gr00tMotionChunk"}
assert not imports & forbidden_imports, imports & forbidden_imports
assert not called & forbidden_calls, called & forbidden_calls
assert not names & forbidden_names, names & forbidden_names
assert "/mc/sdk/robot_command" not in source
print("E3.2_STATIC_SAFETY_OK=ros:none,network:none,publisher_api:none,physical_topic:none")
PY

status_before="$($SHADOW_SCRIPT --status)"
printf '%s\n' "$status_before"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$status_before"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$status_before"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$status_before"
printf 'E3.2_CHECK_OK=mode:local-sink,robot-state:none,movement:none,publishers:0\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E3.2)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E3.2
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
status: FAIL_BEFORE_CERTIFIED_E3_2_COMPLETION
physical_movement_commanded: false
robot_state_read: false
recovery_or_stop: LOCAL_SINK_TERMINATED_NO_PHYSICAL_EXECUTOR_EXISTED
EOF
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf '%s\n' "$status_before" > "$RUN_DIR/status_before.log"
python3 "$RUNNER" \
  --axis-profile P20_AHLW \
  --fixture low \
  --fault-suite all \
  --profile "$PROFILE" \
  --output "$RUN_DIR" \
  2>&1 | tee "$RUN_DIR/fault_suite.log"

profile_sha="$(sha256sum "$PROFILE")"
profile_sha="${profile_sha%% *}"
jq -e \
  --arg profile_sha "$profile_sha" '
  .schema == "cruzr-s2-vla-executor-sink-e3.2-v1"
  and .experiment_id == "E3.2"
  and .mode == "local_pure_python_sink_no_ros_no_hardware"
  and .axis_profile == "P20_AHLW"
  and .fixture == "low"
  and .fixture_state_semantics == "synthetic_profile_midpoint_not_physical_vla_ready"
  and .profile_sha256 == $profile_sha
  and .total_case_count == 34
  and .valid_case_count == 2
  and .valid_case_accepted_count == 2
  and .invalid_case_count == 32
  and .invalid_case_rejected_count == 32
  and .invalid_rejection_rate == 1
  and .failed_expectation_count == 0
  and .all_expectations_passed == true
  and .static_safety.safe == true
  and .static_safety.forbidden_imports_found == []
  and .static_safety.publisher_or_action_calls_found == []
  and .static_safety.physical_command_topic_literal_present == false
  and .sink_physical_publisher_count == 0
  and .sink_network_calls == 0
  and .robot_state_read == false
  and .physical_movement_commanded == false
  and .physical_executor_authorized == false
  and ([.cases[].passed] | all(. == true))
  and ([.cases[].physical_publisher_count] | all(. == 0))
' "$RUN_DIR/summary.json" >/dev/null
test "$(wc -l < "$RUN_DIR/cases.jsonl")" -eq 34

status_after="$($SHADOW_SCRIPT --status)"
printf '%s\n' "$status_after" | tee "$RUN_DIR/status_after.log"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$status_after"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$status_after"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$status_after"

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E3.2
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_LOCAL_SINK_ALL_INVALID_REJECTED
mode: local_pure_python_sink_no_ros_no_hardware
axis_profile: P20_AHLW
fixture: low
fixture_state_semantics: synthetic_profile_midpoint_not_physical_vla_ready
valid_cases: 2
valid_cases_accepted: 2
invalid_cases: 32
invalid_cases_rejected: 32
invalid_rejection_rate: 1.0
static_ros_imports: 0
static_network_imports: 0
static_publisher_or_action_calls: 0
sink_physical_publishers: 0
persistent_inference_container_final: exited
persistent_control_container_final: exited
command_publishers_final: 0
robot_state_read: false
physical_movement_commanded: false
acceleration_limit_status: NOT_TESTED_NO_CERTIFIED_LIMIT_IN_PROFILE
physical_executor_authorized: false
recovery_or_stop: LOCAL_SINK_EXITED_AND_PERSISTENT_VLA_REMAINED_STOPPED
next_experiment_authorized: E3.3_OFFLINE_TEMPORAL_CONTRACT_ONLY
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
printf 'E3.2_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E3.2_RESULT=PASS_LOCAL_SINK_ALL_INVALID_REJECTED\n'
