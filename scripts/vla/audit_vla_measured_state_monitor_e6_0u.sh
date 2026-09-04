#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_measured_state_monitor_e6_0u.sh --check
  ./scripts/vla/audit_vla_measured_state_monitor_e6_0u.sh --run

Prueba en memoria el monitor de estado, velocidad, aceleración y ejes
bloqueados del canary E6.0. No usa red, ROS, estado real ni publicadores.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly TEST="$SCRIPT_DIR/test_vla_measured_state_monitor_e6_0u.py"
readonly MONITOR="$SCRIPT_DIR/runtime/cruzr_s2_vla_measured_state_monitor.py"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_measured_state_monitor_contract_e6_0u.json"
readonly LIMITS="$SCRIPT_DIR/runtime/cruzr_s2_vla_canary_engineering_limits_e6_0s.json"
readonly TRANSPORT="$SCRIPT_DIR/runtime/cruzr_s2_vla_sdk_transport.py"
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
for required in "$TEST" "$MONITOR" "$CONTRACT" "$LIMITS" "$TRANSPORT" "$EVIDENCE_SCRIPT"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$TEST" "$MONITOR" "$TRANSPORT"
args=(
  --monitor "$MONITOR"
  --contract "$CONTRACT"
  --limits "$LIMITS"
  --transport "$TRANSPORT"
)
if [[ "$MODE" == check ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$TEST" "${args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0U)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "$TEST" "$MONITOR" "$CONTRACT" "$LIMITS" "$TRANSPORT" "$RUN_DIR/"
sha256sum "$TEST" "$MONITOR" "$CONTRACT" "$LIMITS" "$TRANSPORT" \
  > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$TEST" "${args[@]}" \
  --output "$RUN_DIR/measured-state-monitor-audit.json" \
  2>&1 | tee "$RUN_DIR/measured-state-monitor-audit.log"

jq -e '
  .schema == "cruzr-s2-vla-measured-state-monitor-audit-e6.0u-v1"
  and .status == "PASS_MEASURED_STATE_MONITOR_OFFLINE_ACTIVE_LAUNCHER_BLOCKED"
  and .all_expectations_passed == true
  and .failed_case_count == 0
  and .failed_contract_tamper_count == 0
  and .runtime_measured_acceleration_monitor_implemented == true
  and .measured_physical_acceleration_validated == false
  and .active_launcher_implemented == false
  and .owner_accepted == false
  and .physical_execution_authorized == false
  and .physical_publisher_count == 0
  and .network_calls == 0
  and .robot_state_read == false
  and .physical_movement_commanded == false
' "$RUN_DIR/measured-state-monitor-audit.json" >/dev/null

case_count="$(jq -r '.case_count' "$RUN_DIR/measured-state-monitor-audit.json")"
tamper_count="$(jq -r '.contract_tamper_case_count' "$RUN_DIR/measured-state-monitor-audit.json")"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0U
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_MEASURED_STATE_MONITOR_OFFLINE_ACTIVE_LAUNCHER_BLOCKED
mode: local_memory_only_no_robot_no_network_no_ros_no_publisher
case_count: $case_count
contract_tamper_case_count: $tamper_count
failed_expectations: 0
runtime_measured_acceleration_monitor_implemented: true
measured_physical_acceleration_validated: false
active_launcher_implemented: false
owner_accepted: false
physical_execution_authorized: false
physical_publishers: 0
network_calls: 0
robot_state_read: false
physical_movement_commanded: false
next_work: IMPLEMENT_EXPLICIT_INACTIVE_LAUNCHER_AND_LIVE_READ_ONLY_STATE_SOURCE_AUDIT
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0U_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0U_PHYSICAL_AUTHORIZED=0\n'
