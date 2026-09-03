#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_engineering_limits_e6_0s.sh --check
  ./scripts/vla/audit_vla_engineering_limits_e6_0s.sh --run

Valida matemáticamente el límite conservador de velocidad/aceleración del
canary E6.0. Es un límite de ingeniería del proyecto, reemplazable y aún no
aceptado por el propietario; no se presenta como certificación del fabricante.
No accede al robot ni crea publicadores.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_engineering_limits_e6_0s.py"
readonly LIMITS="$SCRIPT_DIR/runtime/cruzr_s2_vla_canary_engineering_limits_e6_0s.json"
readonly TRANSPORT="$SCRIPT_DIR/runtime/cruzr_s2_vla_sdk_transport.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly VENDOR_ROOT="$REPO_ROOT/cruzrss2_vla_pack-002/codes-S2/motion/rosa_vla_additional/vla-motionx86"
readonly VENDOR_DIRECT="$VENDOR_ROOT/install/vla_executor/lib/python3.10/site-packages/vla_executor/executor_node.py"
readonly VENDOR_SDK="$VENDOR_ROOT/src/vla_executor/vla_executor/executor_node_sdk.py"
readonly JOINT_CMD_MSG="$VENDOR_ROOT/src/mc_task_msgs/msg/JointCmd.msg"

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
for required in "$ANALYZER" "$LIMITS" "$TRANSPORT" "$EVIDENCE_SCRIPT" \
  "$VENDOR_DIRECT" "$VENDOR_SDK" "$JOINT_CMD_MSG"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$ANALYZER" "$TRANSPORT"
args=(
  --limits "$LIMITS"
  --transport "$TRANSPORT"
  --vendor-direct-executor "$VENDOR_DIRECT"
  --vendor-sdk-executor "$VENDOR_SDK"
  --joint-cmd-msg "$JOINT_CMD_MSG"
)
if [[ "$MODE" == check ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0S)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "$ANALYZER" "$LIMITS" "$TRANSPORT" "$RUN_DIR/"
sha256sum "$ANALYZER" "$LIMITS" "$TRANSPORT" "$VENDOR_DIRECT" "$VENDOR_SDK" \
  "$JOINT_CMD_MSG" > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${args[@]}" \
  --output "$RUN_DIR/engineering-limits-audit.json" \
  2>&1 | tee "$RUN_DIR/engineering-limits-audit.log"

jq -e '
  .schema == "cruzr-s2-vla-engineering-limits-audit-e6.0s-v1"
  and .status == "PASS_PROJECT_ENGINEERING_ENVELOPE_OFFLINE_PENDING_OWNER_ACCEPTANCE"
  and .all_expectations_passed == true
  and .directed_case_count == 28
  and .directed_failed_count == 0
  and .random_case_count == 2000
  and .random_failed_count == 0
  and .configured_maximum_velocity_rad_s == 0.15
  and .configured_maximum_acceleration_rad_s2 == 0.5
  and .configured_maximum_target_delta_rad == 0.1
  and .manufacturer_certified == false
  and .owner_acceptance_required == true
  and .owner_accepted == false
  and .measured_physical_acceleration_validated == false
  and .runtime_measured_acceleration_monitor_implemented == false
  and .physical_execution_authorized == false
  and .physical_publisher_count == 0
  and .network_calls == 0
  and .physical_movement_commanded == false
' "$RUN_DIR/engineering-limits-audit.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0S
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_PROJECT_ENGINEERING_ENVELOPE_OFFLINE_PENDING_OWNER_ACCEPTANCE
mode: local_math_only_no_robot_no_network_no_ros_no_publisher
maximum_target_delta_rad: 0.1
maximum_velocity_rad_s: 0.15
maximum_acceleration_rad_s2: 0.5
sample_period_seconds: 0.01
manufacturer_certified: false
owner_acceptance_required: true
owner_accepted: false
measured_physical_acceleration_validated: false
runtime_measured_acceleration_monitor_implemented: false
physical_execution_authorized: false
physical_publishers: 0
network_calls: 0
physical_movement_commanded: false
next_work: IMPLEMENT_RUNTIME_MEASURED_ACCELERATION_MONITOR_THEN_REQUEST_OWNER_ACCEPTANCE_FOR_NO_BOX_CANARY_ONLY
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0S_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0S_PHYSICAL_AUTHORIZED=0\n'
