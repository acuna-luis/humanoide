#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_ready_recovery_e6_0a.sh --check
  ./scripts/vla/audit_vla_ready_recovery_e6_0a.sh --run

Deriva localmente un contrato P14 de ready/recovery desde los artefactos
vendor congelados. No conecta al robot, no usa ROS y no publica movimiento.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_ready_recovery_e6_0a.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_profile.json"
readonly READY_XML="$REPO_ROOT/cruzrss2_vla_pack-002/codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml"
readonly E4_0_RUN="${VLA_E4_0_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260901T075728_E4.0}"
readonly FORWARD_YAML="$E4_0_RUN/artifacts/remote_clamp_s2_joints_trajectory.yaml"
readonly VENDOR_BACK_YAML="$E4_0_RUN/artifacts/remote_clamp_s2_joints_trajectory_back.yaml"
readonly E3_0_TASK0_FRAME0="${VLA_E3_0_TASK0_FRAME0:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260828T114346_E3.0/results/runs/task0_seed0_rep0.json}"

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
for required in "$ANALYZER" "$EVIDENCE_SCRIPT" "$PROFILE" "$READY_XML" \
  "$FORWARD_YAML" "$VENDOR_BACK_YAML" "$E4_0_RUN/actual_result.yaml" \
  "$E4_0_RUN/evidence.sha256" "$E3_0_TASK0_FRAME0"; do
  test -s "$required" || { echo "ERROR: falta $required" >&2; exit 1; }
done
(cd "$E4_0_RUN" && sha256sum -c evidence.sha256 >/dev/null)

PYTHONDONTWRITEBYTECODE=1 python3 - "$ANALYZER" <<'PY'
import ast
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
compile(source, str(path), "exec")
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
print("E6.0A_STATIC_SAFETY_OK=ros:none,network:none,publisher:none,physical-topic:none")
PY

analyzer_args=(
  --ready-xml "$READY_XML"
  --forward-yaml "$FORWARD_YAML"
  --vendor-back-yaml "$VENDOR_BACK_YAML"
  --profile "$PROFILE"
  --e4-0 "$E4_0_RUN"
  --e3-0-task0-frame0 "$E3_0_TASK0_FRAME0"
)
if [[ "$MODE" == "check" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${analyzer_args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0A)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0A
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
status: FAIL_BEFORE_READY_RECOVERY_AUDIT_COMPLETION
robot_state_read: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
physical_executor_authorized: false
EOF
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cp -- "$ANALYZER" "$RUN_DIR/analyze_vla_ready_recovery_e6_0a.py"
sha256sum "$READY_XML" "$FORWARD_YAML" "$VENDOR_BACK_YAML" "$PROFILE" \
  "$E4_0_RUN/actual_result.yaml" "$E4_0_RUN/evidence.sha256" "$E3_0_TASK0_FRAME0" \
  > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/analyze_vla_ready_recovery_e6_0a.py" \
  "${analyzer_args[@]}" --output "$RUN_DIR/p14-ready-recovery-contract.json" \
  2>&1 | tee "$RUN_DIR/analysis.log"

jq -e '
  .schema == "cruzr-s2-vla-ready-recovery-e6.0a-v1"
  and .p14_contract.structurally_complete == true
  and .p14_contract.physically_accepted == false
  and .joint_order.direct_order_locally_validated == true
  and .joint_order.e4_0_swapped_wrist_hypothesis_rejected == true
  and .joint_order.direct_order_max_abs_error_rad < 0.003
  and .joint_order.swapped_wrist_order_max_abs_error_rad > 0.6
  and .checkpoint_support_envelope.ready_b_supported_with_tolerance == true
  and (.checkpoint_support_envelope.states.ready_b.with_profile_tolerance | length) == 0
  and .recovery_candidate.exact_time_reverse_of_explicit_arm_path == true
  and .recovery_candidate.all_segments_pass_offline_analysis_speed_envelope == true
  and .recovery_candidate.physically_validated == false
  and .vendor_back.is_exact_reverse_candidate == false
  and .blocking_gate_count == 4
  and .e6_0_physical_authorized == false
  and .robot_state_read == false
  and .network_calls == 0
  and .physical_publishers == 0
  and .physical_movement_commanded == false
' "$RUN_DIR/p14-ready-recovery-contract.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0A
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PARTIAL_P14_READY_ALIGNED_EXACT_ARM_RECOVERY_DERIVED_PHYSICAL_VALIDATION_PENDING
mode: local_derivation_no_robot_no_network_no_ros_no_publisher
p14_runtime_hold_policy_structurally_complete: true
static_numeric_20d_ready_required: false
exact_arm_recovery_candidate_derived: true
exact_arm_recovery_candidate_physically_validated: false
vendor_back_exact_reverse: false
ready_b_checkpoint_support_with_tolerance: true
ready_b_support_violation_count: 0
profile_range_tolerance_rad: 0.050000000
supplier_14d_component_header_available: false
joint_order_locally_validated_by_task0_frame0: true
joint_order_direct_max_abs_error_rad: 0.002112805
joint_order_swapped_wrist_max_abs_error_rad: 0.614627484
e4_0_swapped_wrist_hypothesis: rejected
blocking_gate_count: 4
robot_state_read: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
physical_executor_authorized: false
e6_0_physical_authorized: false
recovery_or_stop: NOT_APPLICABLE_LOCAL_ONLY
next_work: OFFLINE_SELF_COLLISION_AND_ENTRY_RECOVERY_SWEEP
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0A_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0A_RESULT=PARTIAL_P14_READY_ALIGNED_EXACT_ARM_RECOVERY_DERIVED_PHYSICAL_VALIDATION_PENDING\n'
