#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_sdk_transport_e6_0r.sh --check
  ./scripts/vla/audit_vla_sdk_transport_e6_0r.sh --run

Prueba localmente el adaptador SDK P14, su interpolación y STOP con un backend
en memoria. No usa red, ROS ni robot y no crea publicadores. El backend ROS
queda implementado como componente sin launcher ni autoarranque.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly RUNTIME="$SCRIPT_DIR/runtime/cruzr_s2_vla_sdk_transport.py"
readonly ROS_BACKEND="$SCRIPT_DIR/runtime/cruzr_s2_vla_ros_sdk_backend.py"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_sdk_transport_contract_e6_0r.json"
readonly LIMITS="$SCRIPT_DIR/runtime/cruzr_s2_vla_canary_engineering_limits_e6_0s.json"
readonly TESTER="$SCRIPT_DIR/test_vla_sdk_transport_e6_0r.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly VENDOR_ROOT="$REPO_ROOT/cruzrss2_vla_pack-002/codes-S2/motion/rosa_vla_additional/vla-motionx86"
readonly VENDOR_EXECUTOR="$VENDOR_ROOT/src/vla_executor/vla_executor/executor_node_sdk.py"
readonly JOINT_CMD_MSG="$VENDOR_ROOT/src/mc_task_msgs/msg/JointCmd.msg"
readonly ROBOT_COMMAND_MSG="$VENDOR_ROOT/src/mc_task_msgs/msg/RobotCommand.msg"

MODE=check
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in cp find jq python3 readlink sha256sum sort tee xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
for required in "$RUNTIME" "$ROS_BACKEND" "$CONTRACT" "$LIMITS" "$TESTER" \
  "$EVIDENCE_SCRIPT" "$VENDOR_EXECUTOR" "$JOINT_CMD_MSG" "$ROBOT_COMMAND_MSG"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$RUNTIME" "$ROS_BACKEND" "$TESTER"
args=(
  --contract "$CONTRACT"
  --limits "$LIMITS"
  --vendor-executor "$VENDOR_EXECUTOR"
  --joint-cmd-msg "$JOINT_CMD_MSG"
  --robot-command-msg "$ROBOT_COMMAND_MSG"
)

if [[ "$MODE" == check ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$TESTER" "${args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0R)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "$RUNTIME" "$ROS_BACKEND" "$CONTRACT" "$LIMITS" "$TESTER" "$RUN_DIR/"
sha256sum "$RUNTIME" "$ROS_BACKEND" "$CONTRACT" "$LIMITS" "$TESTER" \
  "$VENDOR_EXECUTOR" "$JOINT_CMD_MSG" "$ROBOT_COMMAND_MSG" > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$TESTER" "${args[@]}" \
  --output "$RUN_DIR/sdk-transport-audit.json" \
  2>&1 | tee "$RUN_DIR/sdk-transport-audit.log"

jq -e '
  .schema == "cruzr-s2-vla-sdk-transport-audit-e6.0r-v1"
  and .status == "PASS_SDK_TRANSPORT_IMPLEMENTED_OFFLINE_ACTIVE_LAUNCHER_BLOCKED"
  and .failed_expectation_count == 0
  and .all_expectations_passed == true
  and .source_audit.all_passed == true
  and .command_topic == "/mc/sdk/robot_command"
  and .command_message_type == "mc_task_msgs/msg/RobotCommand"
  and .commanded_axis_count == 14
  and .locked_axis_count == 6
  and .maximum_source_point_count == 1
  and .software_stop_implemented == true
  and .software_stop_is_hardware_estop == false
  and .ros_backend_code_present == true
  and .active_launcher_implemented == false
  and .engineering_limits_manufacturer_certified == false
  and .engineering_limits_owner_accepted == false
  and .physical_execution_authorized == false
  and .physical_publisher_count == 0
  and .network_calls == 0
  and .physical_movement_commanded == false
' "$RUN_DIR/sdk-transport-audit.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0R
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_SDK_TRANSPORT_IMPLEMENTED_OFFLINE_ACTIVE_LAUNCHER_BLOCKED
mode: local_memory_transport_no_robot_no_network_no_ros_no_publisher
command_topic: /mc/sdk/robot_command
command_message_type: mc_task_msgs/msg/RobotCommand
commanded_axis_count: 14
locked_axis_count: 6
software_stop_implemented: true
software_stop_is_hardware_estop: false
ros_backend_code_present: true
active_launcher_implemented: false
engineering_limits_manufacturer_certified: false
engineering_limits_owner_accepted: false
physical_execution_authorized: false
physical_publishers: 0
network_calls: 0
physical_movement_commanded: false
next_work: AUDIT_LIVE_SDK_GRAPH_READ_ONLY_AND_REQUIRE_OWNER_ACCEPTANCE_OF_PROJECT_ACCELERATION_ENVELOPE
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0R_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0R_PHYSICAL_AUTHORIZED=0\n'
