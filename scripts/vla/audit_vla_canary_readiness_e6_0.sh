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
readonly READY_SCRIPT="$SCRIPT_DIR/cruzr_vla_ready_pose.sh"
readonly E3_3_RUN="${VLA_E3_3_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260828T124011_E3.3}"
readonly E4_0_RUN="${VLA_E4_0_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260901T075728_E4.0}"
readonly E4_1C_RUN="${VLA_E4_1C_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093408_E4.1C}"
readonly E4_1F_RUN="${VLA_E4_1F_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T085912_E4.1F}"
readonly E5_0_RUN="${VLA_E5_0_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T090355_E5.0}"
readonly E5_2_RUN="${VLA_E5_2_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T091901_E5.2}"
readonly E6_0A_RUN="${VLA_E6_0A_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093145_E6.0A}"
readonly E6_0B_RUN="${VLA_E6_0B_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T094547_E6.0B}"

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
for required in "$ANALYZER" "$EVIDENCE_SCRIPT" "$PROFILE"; do
  test -s "$required" || { echo "ERROR: falta $required" >&2; exit 1; }
done
for run_dir in "$E3_3_RUN" "$E4_0_RUN" "$E4_1C_RUN" "$E4_1F_RUN" "$E5_0_RUN" "$E5_2_RUN" "$E6_0A_RUN" "$E6_0B_RUN"; do
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
  --profile "$PROFILE"
  --physical-executor "$PHYSICAL_EXECUTOR"
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
  "$E3_3_RUN" "$E4_0_RUN" "$E4_1C_RUN" "$E4_1F_RUN" "$E5_0_RUN" "$E5_2_RUN" "$E6_0A_RUN" "$E6_0B_RUN" \
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
  > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/analyze_vla_canary_readiness_e6_0.py" \
  "${analyzer_args[@]}" --output "$RUN_DIR/canary-readiness.json" \
  2>&1 | tee "$RUN_DIR/readiness.log"

jq -e '
  .schema == "cruzr-s2-vla-canary-readiness-e6.0-check-v1"
  and .requested_canary.task_id == 0
  and .requested_canary.axis_profile == "P14_A"
  and .requested_canary.scenario == "NO_BOX_READY"
  and .blocking_gate_count == 6
  and .e6_0_physical_authorized == false
  and .physical_publishers == 0
  and .robot_state_read == false
  and .network_calls == 0
  and .physical_movement_commanded == false
  and ([.gates[] | select(.id == "fixture_e4_4") | .status] == ["NOT_APPLICABLE"])
  and ([.gates[] | select(.status == "BLOCKED")] | length == 6)
' "$RUN_DIR/canary-readiness.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0-CHECK
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_READINESS_AUDIT_E6_0_PHYSICAL_BLOCKED
mode: local_read_only_evidence_audit_no_robot_no_ros_no_publisher
requested_task_id: 0
requested_axis_profile: P14_A
requested_scenario: NO_BOX_READY
fixture_e4_4_required_for_e6_0: false
fixture_e4_4_required_for_e7_plus: true
blocking_gate_count: 6
blocking_gates: s2_ready_task,recovery,self_collision_sweep,physical_executor,acceleration,physical_temporal_semantics
robot_state_read: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
physical_executor_authorized: false
e6_0_physical_authorized: false
recovery_or_stop: NOT_APPLICABLE_LOCAL_ONLY_NO_EXECUTOR_EXISTED
next_work: READY_RECOVERY_AND_OFFLINE_EXECUTOR_REMEDIATION_ONLY
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0_CHECK_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0_CHECK_RESULT=PASS_READINESS_AUDIT_E6_0_PHYSICAL_BLOCKED\n'
