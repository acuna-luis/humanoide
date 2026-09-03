#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_physical_executor_e6_0l.sh --check
  ./scripts/vla/audit_vla_physical_executor_e6_0l.sh --run

Valida localmente el núcleo temporal de un único punto. El nombre de
compatibilidad "physical_executor" no implica transporte: no usa robot, red,
ROS ni publicador y deja la ejecución física explícitamente bloqueada.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly MODULE="$SCRIPT_DIR/runtime/cruzr_s2_vla_physical_executor.py"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_one_point_canary_contract_e6_0l.json"
readonly RUNNER="$SCRIPT_DIR/test_vla_physical_executor_e6_0l.py"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_profile.json"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly E6_0A_RUN="${VLA_E6_0A_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093145_E6.0A}"
readonly E6_0D_RUN="${VLA_E6_0D_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T101730_E6.0D}"
readonly READY_CONTRACT="$E6_0A_RUN/p14-ready-recovery-contract.json"
readonly GUARD_CONTRACT="$E6_0D_RUN/offline-executor-guard-contract.json"

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
for required in "$MODULE" "$CONTRACT" "$RUNNER" "$PROFILE" \
  "$EVIDENCE_SCRIPT" "$READY_CONTRACT" "$GUARD_CONTRACT"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
for evidence_dir in "$E6_0A_RUN" "$E6_0D_RUN"; do
  (cd "$evidence_dir" && sha256sum -c evidence.sha256 >/dev/null)
done

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$MODULE" "$RUNNER"
args=(
  --contract "$CONTRACT"
  --guard-contract "$GUARD_CONTRACT"
  --profile "$PROFILE"
  --ready-contract "$READY_CONTRACT"
)

if [[ "$MODE" == check ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$RUNNER" "${args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0L)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "$MODULE" "$CONTRACT" "$RUNNER" "$PROFILE" "$RUN_DIR/"
printf '%s\n' "$E6_0A_RUN" "$E6_0D_RUN" > "$RUN_DIR/source_runs.txt"
sha256sum "$MODULE" "$CONTRACT" "$RUNNER" "$PROFILE" \
  "$READY_CONTRACT" "$GUARD_CONTRACT" > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$RUNNER" "${args[@]}" \
  --output "$RUN_DIR/one-point-canary-control-core.json" \
  2>&1 | tee "$RUN_DIR/control-core.log"

jq -e '
  .schema == "cruzr-s2-vla-one-point-canary-control-core-e6.0l-v1"
  and .status == "PASS_ONE_POINT_CANARY_CONTROL_CORE_OFFLINE_PHYSICAL_TRANSPORT_BLOCKED"
  and .failed_expectation_count == 0
  and .all_expectations_passed == true
  and .static_safety.safe == true
  and .accepted_source_point_indices == [0]
  and .maximum_preview_intent_count == 1
  and .replay_count == 0
  and .vendor_end_flag_used == false
  and .physical_transport_implemented == false
  and .physical_stop_transport_implemented == false
  and .physical_execution_authorized == false
  and .physical_publisher_count == 0
  and .robot_state_read == false
  and .network_calls == 0
  and .physical_movement_commanded == false
' "$RUN_DIR/one-point-canary-control-core.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0L
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_ONE_POINT_CANARY_CONTROL_CORE_OFFLINE_PHYSICAL_TRANSPORT_BLOCKED
mode: local_in_memory_no_robot_no_network_no_ros_no_publisher
accepted_source_point_indices: 0
maximum_preview_intent_count: 1
replay_count: 0
vendor_end_flag_used: false
physical_transport_implemented: false
physical_stop_transport_implemented: false
physical_execution_authorized: false
physical_publishers: 0
robot_state_read: false
network_calls: 0
physical_movement_commanded: false
next_work: IMPLEMENT_REVIEWED_TRANSPORT_ONLY_AFTER_RECOVERY_AND_ACCELERATION_GATES
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0L_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0L_PHYSICAL_AUTHORIZED=0\n'
