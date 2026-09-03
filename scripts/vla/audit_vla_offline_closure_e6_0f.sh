#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_offline_closure_e6_0f.sh --check
  ./scripts/vla/audit_vla_offline_closure_e6_0f.sh --run

Congela el cierre de todo trabajo E6.0 demostrable sólo con fuentes locales,
genera el preview de instalación ready y define el primer escenario físico.
No usa red, ROS, estado vivo, publicadores ni movimiento.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_offline_closure_e6_0f.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly E3_3_RUN="${VLA_E3_3_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260828T124011_E3.3}"
readonly E4_0_RUN="${VLA_E4_0_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260901T075728_E4.0}"
readonly E6_0A_RUN="${VLA_E6_0A_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093145_E6.0A}"
readonly E6_0B_RUN="${VLA_E6_0B_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T094547_E6.0B}"
readonly E6_0C_RUN="${VLA_E6_0C_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T095600_E6.0C}"
readonly E6_0D_RUN="${VLA_E6_0D_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T101730_E6.0D}"
readonly E6_0E_RUN="${VLA_E6_0E_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T102652_E6.0E}"
readonly VENDOR_READY="$REPO_ROOT/cruzrss2_vla_pack-002/codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml"
readonly VENDOR_LOADER="$REPO_ROOT/cruzrss2_vla_pack-002/codes-S2/motion/s2_vla_scripts/auto_load_vla_scripts_new.sh"
readonly CAPTURED_TASK_LIST="$E4_0_RUN/artifacts/remote_task_list.yaml"

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
for required in "$ANALYZER" "$EVIDENCE_SCRIPT" "$VENDOR_READY" \
  "$VENDOR_LOADER" "$CAPTURED_TASK_LIST"; do
  test -s "$required" || { echo "ERROR: falta fuente: $required" >&2; exit 1; }
done
for run_dir in "$E3_3_RUN" "$E4_0_RUN" "$E6_0A_RUN" "$E6_0B_RUN" \
  "$E6_0C_RUN" "$E6_0D_RUN" "$E6_0E_RUN"; do
  (cd "$run_dir" && sha256sum -c evidence.sha256 >/dev/null)
done

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$ANALYZER"
PYTHONDONTWRITEBYTECODE=1 python3 - "$ANALYZER" <<'PY'
import ast
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
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
print("E6.0F_STATIC_SAFETY_OK=ros:none,network:none,publisher:none,physical-topic:none")
PY

args=(
  --e4-0 "$E4_0_RUN"
  --e3-3 "$E3_3_RUN"
  --e6-0a "$E6_0A_RUN"
  --e6-0b "$E6_0B_RUN"
  --e6-0c "$E6_0C_RUN"
  --e6-0d "$E6_0D_RUN"
  --e6-0e "$E6_0E_RUN"
  --vendor-ready-xml "$VENDOR_READY"
  --vendor-loader "$VENDOR_LOADER"
  --captured-task-list "$CAPTURED_TASK_LIST"
)

if [[ "$MODE" == "check" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0F)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "$ANALYZER" "$RUN_DIR/"
printf '%s\n' "$E3_3_RUN" "$E4_0_RUN" "$E6_0A_RUN" "$E6_0B_RUN" \
  "$E6_0C_RUN" "$E6_0D_RUN" "$E6_0E_RUN" > "$RUN_DIR/source_runs.txt"
sha256sum "$ANALYZER" "$VENDOR_READY" "$VENDOR_LOADER" "$CAPTURED_TASK_LIST" \
  > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/$(basename -- "$ANALYZER")" \
  "${args[@]}" --output-dir "$RUN_DIR" 2>&1 | tee "$RUN_DIR/closure.log"

jq -e '
  .schema == "cruzr-s2-vla-offline-closure-e6.0f-v1"
  and .status == "PASS_ALL_AVAILABLE_LOCAL_ONLY_E6_0_WORK_EXHAUSTED_PHYSICAL_BOUNDARY_REACHED"
  and (.gate_boundary | length) == 6
  and ([.gate_boundary[].local_work_complete] | all(. == true))
  and .remaining_local_only_actions_without_new_physical_or_certified_input == []
  and .next_required_boundary == "LIVE_ROBOT_OR_CERTIFIED_EXTERNAL_INPUT"
  and .deployment_preview.state == "PREVIEW_ONLY_NOT_APPLIED"
  and .deployment_preview.apply_command == null
  and .deployment_preview.robot_modified == false
  and .first_physical_scenario.scenario_id == "NO_BOX_READY_EMPTY_CELL"
  and .first_physical_scenario.fixture_required == false
  and .physical_authorized == false
  and .robot_state_read == false
  and .network_calls == 0
  and .physical_publishers == 0
  and .physical_movement_commanded == false
' "$RUN_DIR/offline-closure-report.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0F
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_ALL_AVAILABLE_LOCAL_ONLY_E6_0_WORK_EXHAUSTED_PHYSICAL_BOUNDARY_REACHED
mode: local_evidence_closure_no_robot_no_network_no_ros_no_publisher
local_gate_components_complete: 6
remaining_local_only_actions_without_new_input: 0
next_required_boundary: LIVE_ROBOT_OR_CERTIFIED_EXTERNAL_INPUT
ready_task_deployment_state: PREVIEW_ONLY_NOT_APPLIED
first_physical_scenario: NO_BOX_READY_EMPTY_CELL
fixture_required: false
robot_state_read: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
physical_authorized: false
next_safe_work: PREPARE_EMPTY_CELL_THEN_RUN_READ_ONLY_LIVE_PREFLIGHT
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0F_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0F_PHYSICAL_AUTHORIZED=0\n'
