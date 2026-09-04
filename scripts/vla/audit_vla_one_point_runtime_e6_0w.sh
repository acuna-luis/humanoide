#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_one_point_runtime_e6_0w.sh --check
  ./scripts/vla/audit_vla_one_point_runtime_e6_0w.sh --run

Prueba el coordinador y proceso ROS E6.0W sólo offline. Verifica además que
la plantilla versionada rechace --run antes de importar ROS o crear endpoints.
No usa red ni estado real y no crea publicadores.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly TEST="$SCRIPT_DIR/test_vla_one_point_runtime_e6_0w.py"
readonly RUNTIME="$SCRIPT_DIR/runtime/cruzr_s2_vla_one_point_runtime.py"
readonly PROCESS="$SCRIPT_DIR/runtime/cruzr_s2_vla_ros_one_point_process.py"
readonly MONITOR="$SCRIPT_DIR/runtime/cruzr_s2_vla_measured_state_monitor.py"
readonly TRANSPORT="$SCRIPT_DIR/runtime/cruzr_s2_vla_sdk_transport.py"
readonly ROS_BACKEND="$SCRIPT_DIR/runtime/cruzr_s2_vla_ros_sdk_backend.py"
readonly ACTIVATION="$SCRIPT_DIR/runtime/cruzr_s2_vla_canary_activation_template_e6_0w.json"
readonly MONITOR_CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_measured_state_monitor_contract_e6_0u.json"
readonly TRANSPORT_CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_sdk_transport_contract_e6_0r.json"
readonly LIMITS="$SCRIPT_DIR/runtime/cruzr_s2_vla_canary_engineering_limits_e6_0s.json"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_profile.json"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"

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
files=(
  "$TEST" "$RUNTIME" "$PROCESS" "$MONITOR" "$TRANSPORT" "$ROS_BACKEND"
  "$ACTIVATION" "$MONITOR_CONTRACT" "$TRANSPORT_CONTRACT" "$LIMITS" "$PROFILE"
)
for required in "${files[@]}" "$EVIDENCE_SCRIPT"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  "$TEST" "$RUNTIME" "$PROCESS" "$MONITOR" "$TRANSPORT" "$ROS_BACKEND"
test_args=(
  --runtime "$RUNTIME"
  --monitor "$MONITOR"
  --transport "$TRANSPORT"
  --activation "$ACTIVATION"
  --monitor-contract "$MONITOR_CONTRACT"
  --transport-contract "$TRANSPORT_CONTRACT"
  --limits "$LIMITS"
  --profile "$PROFILE"
  --ros-process "$PROCESS"
  --ros-backend "$ROS_BACKEND"
)
process_args=(
  --activation "$ACTIVATION"
  --runtime "$RUNTIME"
  --monitor "$MONITOR"
  --transport "$TRANSPORT"
  --ros-backend "$ROS_BACKEND"
  --monitor-contract "$MONITOR_CONTRACT"
  --transport-contract "$TRANSPORT_CONTRACT"
  --limits "$LIMITS"
  --profile "$PROFILE"
)

run_checks() {
  local output="${1:-}"
  if [[ -n "$output" ]]; then
    PYTHONDONTWRITEBYTECODE=1 python3 "$TEST" "${test_args[@]}" --output "$output"
  else
    PYTHONDONTWRITEBYTECODE=1 python3 "$TEST" "${test_args[@]}"
  fi
  PYTHONDONTWRITEBYTECODE=1 python3 "$PROCESS" --check "${process_args[@]}"
  set +e
  disabled_output="$(PYTHONDONTWRITEBYTECODE=1 python3 "$PROCESS" --run "${process_args[@]}" 2>&1)"
  disabled_status=$?
  set -e
  printf '%s\n' "$disabled_output"
  [[ "$disabled_status" -eq 3 ]]
  grep -Fq 'E6.0W_ACTIVE_LAUNCHER_ENABLED=0' <<<"$disabled_output"
  grep -Fq 'E6.0W_PHYSICAL_AUTHORIZED=0' <<<"$disabled_output"
}

if [[ "$MODE" == check ]]; then
  run_checks
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0W)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "${files[@]}" "$RUN_DIR/"
sha256sum "${files[@]}" > "$RUN_DIR/source_hashes.sha256"
run_checks "$RUN_DIR/one-point-runtime-audit.json" \
  2>&1 | tee "$RUN_DIR/one-point-runtime-audit.log"

jq -e '
  .schema == "cruzr-s2-vla-one-point-runtime-audit-e6.0w-v1"
  and .status == "PASS_RUNTIME_CORE_OFFLINE_PRODUCTION_ACTIVATION_BLOCKED"
  and .all_expectations_passed == true
  and .failed_case_count == 0
  and .failed_activation_case_count == 0
  and .runtime_core_implemented == true
  and .ros_process_implemented == true
  and .active_launcher_enabled == false
  and .owner_accepted_engineering_limits == false
  and .physical_execution_authorized == false
  and .physical_publisher_count == 0
  and .network_calls == 0
  and .robot_state_read == false
  and .physical_movement_commanded == false
' "$RUN_DIR/one-point-runtime-audit.json" >/dev/null

case_count="$(jq -r '.case_count' "$RUN_DIR/one-point-runtime-audit.json")"
activation_count="$(jq -r '.activation_case_count' "$RUN_DIR/one-point-runtime-audit.json")"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0W
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_RUNTIME_CORE_AND_ROS_PROCESS_OFFLINE_PRODUCTION_ACTIVATION_BLOCKED
mode: local_memory_only_no_robot_no_network_no_ros_no_publisher
case_count: $case_count
activation_case_count: $activation_count
failed_expectations: 0
runtime_core_implemented: true
ros_process_implemented: true
selected_state_topic: /mc/whole_joint_states
command_topic: /mc/sdk/robot_command
command_publisher_creation: lazy_after_ready_and_valid_chunk
active_launcher_enabled: false
owner_accepted_engineering_limits: false
physical_execution_authorized: false
physical_publishers: 0
network_calls: 0
robot_state_read: false
physical_movement_commanded: false
next_work: INTEGRATE_E6_0R_S_T_U_V_W_IN_READINESS_THEN_REQUEST_OWNER_LIMIT_ACCEPTANCE
EOF
(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0W_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0W_ACTIVE_LAUNCHER_ENABLED=0\n'
printf 'E6.0W_PHYSICAL_AUTHORIZED=0\n'
