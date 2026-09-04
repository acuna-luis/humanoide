#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_canary_readiness_e6_0.sh --check
  ./scripts/vla/audit_vla_canary_readiness_e6_0.sh --run

Audita localmente los gates del canary E6.0 sin caja. No conecta al robot,
no usa ROS, no crea publicadores y no envía movimiento. Un resultado correcto
puede ser BLOCKED: significa que el auditor detectó de forma reproducible los
requisitos todavía abiertos.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_canary_readiness_e6_0.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_profile.json"
readonly PHYSICAL_EXECUTOR="$SCRIPT_DIR/runtime/cruzr_s2_vla_physical_executor.py"
readonly STATE_MONITOR="$SCRIPT_DIR/runtime/cruzr_s2_vla_measured_state_monitor.py"
readonly RUNTIME_PROCESS="$SCRIPT_DIR/runtime/cruzr_s2_vla_ros_one_point_process.py"
readonly ACTIVATION_TEMPLATE="$SCRIPT_DIR/runtime/cruzr_s2_vla_canary_activation_template_e6_0w.json"
readonly READY_SCRIPT="$SCRIPT_DIR/cruzr_vla_ready_pose.sh"
readonly E3_3_RUN="${VLA_E3_3_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260828T124011_E3.3}"
readonly E4_0_RUN="${VLA_E4_0_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260901T075728_E4.0}"
readonly E4_1C_RUN="${VLA_E4_1C_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093408_E4.1C}"
readonly E4_1F_RUN="${VLA_E4_1F_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T085912_E4.1F}"
readonly E5_0_RUN="${VLA_E5_0_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T090355_E5.0}"
readonly E5_2_RUN="${VLA_E5_2_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T091901_E5.2}"
readonly E6_0A_RUN="${VLA_E6_0A_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093145_E6.0A}"
readonly E6_0B_RUN="${VLA_E6_0B_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T094547_E6.0B}"
readonly E6_0C_RUN="${VLA_E6_0C_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T095600_E6.0C}"
readonly E6_0D_RUN="${VLA_E6_0D_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T101730_E6.0D}"
readonly E6_0E_RUN="${VLA_E6_0E_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T102652_E6.0E}"
readonly E6_0F_RUN="${VLA_E6_0F_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T102931_E6.0F}"
readonly E6_0G_RUN="${VLA_E6_0G_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T113216_E6.0G}"
readonly E6_0H_RUN="${VLA_E6_0H_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T104552_E6.0H}"
readonly E6_0I_RUN="${VLA_E6_0I_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T115129_E6.0I}"
readonly E6_0J_RUN="${VLA_E6_0J_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T120626_E6.0J}"
readonly E6_0K_RUN="${VLA_E6_0K_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T121338_E6.0K}"
readonly E6_0L_RUN="${VLA_E6_0L_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T122501_E6.0L}"
readonly E6_0M_RUN="${VLA_E6_0M_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T122502_E6.0M}"
readonly E6_0N_RUN="${VLA_E6_0N_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T123940_E6.0N}"
readonly E6_0O_RUN="${VLA_E6_0O_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T124843_E6.0O}"
readonly E6_0Q_RUN="${VLA_E6_0Q_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T135236_E6.0Q}"
readonly E6_0R_RUN="${VLA_E6_0R_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T142823_E6.0R}"
readonly E6_0S_RUN="${VLA_E6_0S_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T144344_E6.0S}"
readonly E6_0T_RUN="${VLA_E6_0T_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T143529_E6.0T}"
readonly E6_0U_RUN="${VLA_E6_0U_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260904T073609_E6.0U}"
readonly E6_0V_RUN="${VLA_E6_0V_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260904T073852_E6.0V}"
readonly E6_0W_RUN="${VLA_E6_0W_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260904T074537_E6.0W}"
readonly E6_0X_RUN="${VLA_E6_0X_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260904T075519_E6.0X}"

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
for required in "$ANALYZER" "$EVIDENCE_SCRIPT" "$PROFILE" "$PHYSICAL_EXECUTOR" "$STATE_MONITOR" "$RUNTIME_PROCESS" "$ACTIVATION_TEMPLATE" "$READY_SCRIPT"; do
  test -s "$required" || { echo "ERROR: falta $required" >&2; exit 1; }
done
for run_dir in "$E3_3_RUN" "$E4_0_RUN" "$E4_1C_RUN" "$E4_1F_RUN" "$E5_0_RUN" "$E5_2_RUN" "$E6_0A_RUN" "$E6_0B_RUN" "$E6_0C_RUN" "$E6_0D_RUN" "$E6_0E_RUN" "$E6_0F_RUN" "$E6_0G_RUN" "$E6_0H_RUN" "$E6_0I_RUN" "$E6_0J_RUN" "$E6_0K_RUN" "$E6_0L_RUN" "$E6_0M_RUN" "$E6_0N_RUN" "$E6_0O_RUN" "$E6_0Q_RUN" "$E6_0R_RUN" "$E6_0S_RUN" "$E6_0T_RUN" "$E6_0U_RUN" "$E6_0V_RUN" "$E6_0W_RUN" "$E6_0X_RUN"; do
  test -s "$run_dir/actual_result.yaml" || { echo "ERROR: falta $run_dir/actual_result.yaml" >&2; exit 1; }
  test -s "$run_dir/evidence.sha256" || { echo "ERROR: falta $run_dir/evidence.sha256" >&2; exit 1; }
  (cd "$run_dir" && sha256sum -c evidence.sha256 >/dev/null)
done
test -s "$E5_2_RUN/shadow-profile-selection.json" || {
  echo "ERROR: falta selección E5.2" >&2
  exit 1
}

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
forbidden_imports = {"rclpy", "rosa", "socket", "requests", "subprocess", "urllib"}
forbidden_calls = {"create_client", "create_publisher", "publish", "send_goal_async"}
assert not imports & forbidden_imports, imports & forbidden_imports
assert not names & forbidden_calls, names & forbidden_calls
assert "/mc/sdk/robot_command" not in source
print("E6.0_CHECK_STATIC_SAFETY_OK=ros:none,network:none,publisher:none,physical-topic:none")
PY

analyzer_args=(
  --e3-3 "$E3_3_RUN"
  --e4-0 "$E4_0_RUN"
  --e4-1c "$E4_1C_RUN"
  --e4-1f "$E4_1F_RUN"
  --e5-0 "$E5_0_RUN"
  --e5-2 "$E5_2_RUN"
  --e6-0a "$E6_0A_RUN"
  --e6-0b "$E6_0B_RUN"
  --e6-0c "$E6_0C_RUN"
  --e6-0d "$E6_0D_RUN"
  --e6-0e "$E6_0E_RUN"
  --e6-0f "$E6_0F_RUN"
  --e6-0g "$E6_0G_RUN"
  --e6-0h "$E6_0H_RUN"
  --e6-0i "$E6_0I_RUN"
  --e6-0j "$E6_0J_RUN"
  --e6-0k "$E6_0K_RUN"
  --e6-0l "$E6_0L_RUN"
  --e6-0m "$E6_0M_RUN"
  --e6-0n "$E6_0N_RUN"
  --e6-0o "$E6_0O_RUN"
  --e6-0q "$E6_0Q_RUN"
  --e6-0r "$E6_0R_RUN"
  --e6-0s "$E6_0S_RUN"
  --e6-0t "$E6_0T_RUN"
  --e6-0u "$E6_0U_RUN"
  --e6-0v "$E6_0V_RUN"
  --e6-0w "$E6_0W_RUN"
  --e6-0x "$E6_0X_RUN"
  --profile "$PROFILE"
  --physical-executor "$PHYSICAL_EXECUTOR"
  --state-monitor "$STATE_MONITOR"
  --runtime-process "$RUNTIME_PROCESS"
  --activation-template "$ACTIVATION_TEMPLATE"
  --ready-script "$READY_SCRIPT"
)

if [[ "$MODE" == "check" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${analyzer_args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0-CHECK)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0-CHECK
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
status: FAIL_BEFORE_READINESS_AUDIT_COMPLETION
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

cp -- "$ANALYZER" "$RUN_DIR/analyze_vla_canary_readiness_e6_0.py"
printf '%s\n' \
  "$E3_3_RUN" "$E4_0_RUN" "$E4_1C_RUN" "$E4_1F_RUN" "$E5_0_RUN" "$E5_2_RUN" "$E6_0A_RUN" "$E6_0B_RUN" "$E6_0C_RUN" "$E6_0D_RUN" "$E6_0E_RUN" "$E6_0F_RUN" "$E6_0G_RUN" "$E6_0H_RUN" "$E6_0I_RUN" "$E6_0J_RUN" "$E6_0K_RUN" "$E6_0L_RUN" "$E6_0M_RUN" "$E6_0N_RUN" "$E6_0O_RUN" "$E6_0Q_RUN" "$E6_0R_RUN" "$E6_0S_RUN" "$E6_0T_RUN" "$E6_0U_RUN" "$E6_0V_RUN" "$E6_0W_RUN" "$E6_0X_RUN" \
  > "$RUN_DIR/source_runs.txt"
sha256sum \
  "$E3_3_RUN/actual_result.yaml" "$E3_3_RUN/evidence.sha256" \
  "$E4_0_RUN/actual_result.yaml" "$E4_0_RUN/evidence.sha256" \
  "$E4_1C_RUN/actual_result.yaml" "$E4_1C_RUN/evidence.sha256" \
  "$E4_1F_RUN/actual_result.yaml" "$E4_1F_RUN/evidence.sha256" \
  "$E5_0_RUN/actual_result.yaml" "$E5_0_RUN/evidence.sha256" \
  "$E5_2_RUN/actual_result.yaml" "$E5_2_RUN/evidence.sha256" \
  "$E5_2_RUN/shadow-profile-selection.json" "$PROFILE" \
  "$E6_0A_RUN/actual_result.yaml" "$E6_0A_RUN/evidence.sha256" \
  "$E6_0B_RUN/actual_result.yaml" "$E6_0B_RUN/evidence.sha256" \
  "$E6_0C_RUN/actual_result.yaml" "$E6_0C_RUN/evidence.sha256" \
  "$E6_0D_RUN/actual_result.yaml" "$E6_0D_RUN/evidence.sha256" \
  "$E6_0D_RUN/clearance-report.json" "$E6_0D_RUN/offline-executor-guard-contract.json" \
  "$E6_0E_RUN/actual_result.yaml" "$E6_0E_RUN/evidence.sha256" \
  "$E6_0E_RUN/one-point-guard-campaign.json" \
  "$E6_0F_RUN/actual_result.yaml" "$E6_0F_RUN/evidence.sha256" \
  "$E6_0F_RUN/offline-closure-report.json" "$E6_0F_RUN/first-physical-scenario.json" \
  "$E6_0G_RUN/actual_result.yaml" "$E6_0G_RUN/evidence.sha256" \
  "$E6_0G_RUN/motion-snapshot.log" "$E6_0G_RUN/vla-status.log" \
  "$E6_0H_RUN/actual_result.yaml" "$E6_0H_RUN/evidence.sha256" \
  "$E6_0H_RUN/install-result.log" "$E6_0H_RUN/vla-status-after.log" \
  "$E6_0I_RUN/actual_result.yaml" "$E6_0I_RUN/evidence.sha256" \
  "$E6_0I_RUN/home-entry-report.json" \
  "$E6_0J_RUN/actual_result.yaml" "$E6_0J_RUN/evidence.sha256" \
  "$E6_0J_RUN/document-proxy-clamp-report.json" \
  "$E6_0K_RUN/actual_result.yaml" "$E6_0K_RUN/evidence.sha256" \
  "$E6_0K_RUN/observed-clamp-containment-report.json" \
  "$E6_0L_RUN/actual_result.yaml" "$E6_0L_RUN/evidence.sha256" \
  "$E6_0L_RUN/one-point-canary-control-core.json" \
  "$E6_0M_RUN/actual_result.yaml" "$E6_0M_RUN/evidence.sha256" \
  "$E6_0M_RUN/ready-recovery-bundle.json" \
  "$E6_0N_RUN/actual_result.yaml" "$E6_0N_RUN/evidence.sha256" \
  "$E6_0N_RUN/install-result.log" "$E6_0N_RUN/vla-status-after.log" \
  "$E6_0O_RUN/actual_result.yaml" "$E6_0O_RUN/evidence.sha256" \
  "$E6_0O_RUN/reload-result.log" "$E6_0O_RUN/runtime-after.log" \
  "$E6_0Q_RUN/actual_result.yaml" "$E6_0Q_RUN/evidence.sha256" \
  "$E6_0Q_RUN/action-result.log" "$E6_0Q_RUN/home-gate-final.log" \
  "$E6_0R_RUN/actual_result.yaml" "$E6_0R_RUN/evidence.sha256" \
  "$E6_0R_RUN/sdk-transport-audit.json" \
  "$E6_0S_RUN/actual_result.yaml" "$E6_0S_RUN/evidence.sha256" \
  "$E6_0S_RUN/engineering-limits-audit.json" \
  "$E6_0T_RUN/actual_result.yaml" "$E6_0T_RUN/evidence.sha256" \
  "$E6_0T_RUN/sdk-graph.log" \
  "$E6_0U_RUN/actual_result.yaml" "$E6_0U_RUN/evidence.sha256" \
  "$E6_0U_RUN/measured-state-monitor-audit.json" \
  "$E6_0V_RUN/actual_result.yaml" "$E6_0V_RUN/evidence.sha256" \
  "$E6_0V_RUN/state-source-summary.log" \
  "$E6_0W_RUN/actual_result.yaml" "$E6_0W_RUN/evidence.sha256" \
  "$E6_0W_RUN/one-point-runtime-audit.json" \
  "$E6_0X_RUN/actual_result.yaml" "$E6_0X_RUN/evidence.sha256" \
  "$E6_0X_RUN/cruzr_s2_vla_owner_acceptance_e6_0x.json" \
  "$PHYSICAL_EXECUTOR" "$STATE_MONITOR" "$RUNTIME_PROCESS" "$ACTIVATION_TEMPLATE" "$READY_SCRIPT" \
  > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/analyze_vla_canary_readiness_e6_0.py" \
  "${analyzer_args[@]}" --output "$RUN_DIR/canary-readiness.json" \
  2>&1 | tee "$RUN_DIR/readiness.log"

jq -e '
  .schema == "cruzr-s2-vla-canary-readiness-e6.0-check-v1"
  and .requested_canary.task_id == 0
  and .requested_canary.axis_profile == "P14_A"
  and .requested_canary.scenario == "NO_BOX_READY"
  and .blocking_gate_count == 0
  and .e6_0_physical_authorized == false
  and .physical_publishers == 0
  and .robot_state_read == false
  and .network_calls == 0
  and .physical_movement_commanded == false
  and ([.gates[] | select(.id == "fixture_e4_4") | .status] == ["NOT_APPLICABLE"])
  and ([.gates[] | select(.id == "s2_ready_task_installed_and_registered") | .status] == ["PASS"])
  and ([.gates[] | select(.id == "fresh_physical_preflight") | .status] == ["RUN_SPECIFIC_REQUIRED"])
  and ([.gates[] | select(.id == "no_box_self_collision_swept_volume") | .status] == ["PASS_WITH_DOCUMENT_PROXY_ASSUMPTION"])
  and ([.gates[] | select(.id == "physical_temporal_semantics") | .status] == ["PASS_PROJECT_ONE_POINT_CONTRACT"])
  and ([.gates[] | select(.id == "physical_executor_implemented_and_reviewed") | .status] == ["PASS_CODE_OFFLINE_ACTIVATION_GATED"])
  and ([.gates[] | select(.id == "project_engineering_envelope_owner_acceptance") | .status] == ["PASS"])
  and ([.gates[] | select(.id == "recovery_exact_and_validated") | .status] == ["PASS"])
  and ([.gates[] | select(.status == "BLOCKED")] | length == 0)
  and ([.gates[] | select(.status == "PENDING_REVIEW")] | length == 0)
  and .implementation.physical_runtime_implemented == true
  and .implementation.runtime_measured_acceleration_monitor_implemented == true
  and .implementation.live_state_source_verified == true
  and .implementation.one_point_ros_process_implemented == true
  and .implementation.active_launcher_enabled == false
  and .implementation.owner_acceptance_verified == true
  and .implementation.owner_acceptance_is_movement_authorization == false
  and .static_readiness_gates_closed == true
' "$RUN_DIR/canary-readiness.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0-CHECK
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_READINESS_AUDIT_E6_0_STATIC_GATES_CLOSED_PHYSICAL_PREFLIGHT_PENDING
mode: local_read_only_evidence_audit_no_robot_no_ros_no_publisher
requested_task_id: 0
requested_axis_profile: P14_A
requested_scenario: NO_BOX_READY
fixture_e4_4_required_for_e6_0: false
fixture_e4_4_required_for_e7_plus: true
blocking_gate_count: 0
blocking_gates: none
project_one_point_temporal_contract: passed
clamp_geometry_basis: owner_accepted_document_proxy_not_certified
physical_runtime_implemented_offline: true
runtime_measured_acceleration_monitor_implemented: true
live_state_source_selected: /mc/whole_joint_states
active_launcher_enabled: false
run_specific_fresh_preflight_required: true
owner_acceptance_verified: true
owner_acceptance_is_movement_authorization: false
robot_state_read: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
physical_executor_authorized: false
e6_0_physical_authorized: false
recovery_or_stop: NOT_APPLICABLE_LOCAL_ONLY_NO_PHYSICAL_TRANSPORT
next_work: KEEP_VLA_STOPPED_PERFORM_FRESH_PREFLIGHT_THEN_CREATE_SINGLE_RUN_GRANT
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0_CHECK_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0_CHECK_RESULT=PASS_READINESS_AUDIT_E6_0_STATIC_GATES_CLOSED_PHYSICAL_PREFLIGHT_PENDING\n'
