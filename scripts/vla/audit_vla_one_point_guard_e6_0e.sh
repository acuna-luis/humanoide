#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_one_point_guard_e6_0e.sh --check
  ./scripts/vla/audit_vla_one_point_guard_e6_0e.sh --run

Prueba el guard E6.0E sólo como preview en memoria. No usa red, ROS, estado
del robot, publicadores ni movimiento, y nunca autoriza ejecución física.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly MODULE="$SCRIPT_DIR/runtime/vla_one_point_guard.py"
readonly RUNNER="$SCRIPT_DIR/test_vla_one_point_guard_e6_0e.py"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_profile.json"
readonly TEMPORAL="$SCRIPT_DIR/runtime/cruzr_s2_vla_temporal_contract_e3_3.json"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly E6_0A_RUN="${VLA_E6_0A_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093145_E6.0A}"
readonly E6_0D_RUN="${VLA_E6_0D_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T101730_E6.0D}"
readonly READY_CONTRACT="$E6_0A_RUN/p14-ready-recovery-contract.json"
readonly GUARD_CONTRACT="$E6_0D_RUN/offline-executor-guard-contract.json"

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in cp find jq python3 readlink sha256sum sort tee xargs; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta herramienta: $tool" >&2; exit 1; }
done
for required in "$MODULE" "$RUNNER" "$PROFILE" "$TEMPORAL" \
  "$EVIDENCE_SCRIPT" "$READY_CONTRACT" "$GUARD_CONTRACT"; do
  test -s "$required" || { echo "ERROR: falta fuente: $required" >&2; exit 1; }
done
for evidence_dir in "$E6_0A_RUN" "$E6_0D_RUN"; do
  (cd "$evidence_dir" && sha256sum -c evidence.sha256 >/dev/null)
done

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$MODULE" "$RUNNER"
PYTHONDONTWRITEBYTECODE=1 python3 - "$MODULE" <<'PY'
import ast
import pathlib
import sys
for raw in sys.argv[1:]:
    path = pathlib.Path(raw)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    assert not imports & {"rclpy", "rosa", "socket", "requests", "subprocess", "urllib"}
    assert not names & {"create_client", "create_publisher", "publish", "send_goal_async"}
    assert "/mc/sdk/robot_command" not in source
print("E6.0E_STATIC_SAFETY_OK=ros:none,network:none,publisher:none,physical-topic:none")
PY

args=(
  --guard-contract "$GUARD_CONTRACT"
  --profile "$PROFILE"
  --ready-contract "$READY_CONTRACT"
  --temporal-contract "$TEMPORAL"
)

if [[ "$MODE" == "check" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$RUNNER" "${args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0E)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
mkdir -p "$RUN_DIR/runtime"
cp -- "$MODULE" "$RUN_DIR/runtime/"
cp -- "$RUNNER" "$PROFILE" "$TEMPORAL" "$RUN_DIR/"
printf '%s\n' "$E6_0A_RUN" "$E6_0D_RUN" > "$RUN_DIR/source_runs.txt"
sha256sum "$MODULE" "$RUNNER" "$PROFILE" "$TEMPORAL" \
  "$READY_CONTRACT" "$GUARD_CONTRACT" > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/$(basename -- "$RUNNER")" \
  "${args[@]}" --output "$RUN_DIR/one-point-guard-campaign.json" \
  2>&1 | tee "$RUN_DIR/guard-campaign.log"

jq -e '
  .schema == "cruzr-s2-vla-one-point-guard-campaign-e6.0e-v1"
  and .experiment_id == "E6.0E"
  and .message_case_count == 35
  and .contract_tamper_case_count == 7
  and .contract_tamper_rejected_count == 7
  and .failed_expectation_count == 0
  and .all_expectations_passed == true
  and .valid_preview_count == 2
  and .physical_authorization_count == 0
  and .physical_publisher_count == 0
  and .static_safety.safe == true
  and .physical_execution_authorized == false
  and .robot_state_read == false
  and .network_calls == 0
  and .physical_movement_commanded == false
' "$RUN_DIR/one-point-guard-campaign.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0E
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_OFFLINE_ONE_POINT_GUARD_MATRIX_PHYSICAL_BLOCKED
mode: local_in_memory_preview_no_robot_no_network_no_ros_no_publisher
message_cases: 35
contract_tamper_cases: 7
failed_expectations: 0
valid_previews: 2
physical_authorizations: 0
physical_publishers: 0
robot_state_read: false
network_calls: 0
physical_movement_commanded: false
physical_execution_authorized: false
next_safe_work: OFFLINE_CLOSURE_AUDIT_AND_PHYSICAL_SCENARIO_DEFINITION
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0E_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0E_PHYSICAL_AUTHORIZED=0\n'
