#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_vla_profile_selection_e5_2.sh --check
  ./scripts/vla/run_vla_profile_selection_e5_2.sh --run

Analiza la matriz E5.1 y elige de forma preliminar el perfil mínimo por task.
Es totalmente local: no usa el robot, red, ROS ni publicadores.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_campaign.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly SOURCE_RUN="${VLA_E5_2_SOURCE_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T091319_E5.1}"

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in cp jq python3 readlink sha256sum; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta herramienta: $tool" >&2; exit 1; }
done
for required in "$ANALYZER" "$EVIDENCE_SCRIPT" "$SOURCE_RUN/matrix_summary.json" "$SOURCE_RUN/bundles.jsonl" "$SOURCE_RUN/evidence.sha256"; do
  test -s "$required" || { echo "ERROR: falta $required" >&2; exit 1; }
done

PYTHONDONTWRITEBYTECODE=1 python3 - "$ANALYZER" <<'PY'
import ast
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
compile(source, str(path), "exec")
tree = ast.parse(source)
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])
assert not imports & {"rclpy", "rosa", "socket", "requests", "subprocess", "urllib"}
assert "/mc/sdk/robot_command" not in source
print("E5.2_STATIC_SAFETY_OK=ros:none,network:none,physical_topic:none")
PY
(
  cd "$SOURCE_RUN"
  sha256sum -c evidence.sha256 >/dev/null
)
jq -e '
  .schema == "cruzr-s2-vla-shadow-matrix-e5.1-v1"
  and .totals.cell_count == 32
  and .totals.bundle_count == 160
  and .totals.mask_contract_pass_count == 160
  and .physical_publishers == 0
  and .physical_movement_commanded == false
' "$SOURCE_RUN/matrix_summary.json" >/dev/null
printf 'E5.2_SOURCE_OK=E5.1-hashes-valid,cells:32,bundles:160\n'
printf 'E5.2_CHECK_OK=mode:offline-analysis,robot:none,network:none,publishers:0\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E5.2)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E5.2
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
status: FAIL_BEFORE_PRELIMINARY_SELECTION
robot_state_read_live: false
network_calls: 0
physical_movement_commanded: false
recovery_or_stop: LOCAL_PROCESS_TERMINATED_NO_PHYSICAL_EXECUTOR_EXISTED
EOF
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cp -- "$ANALYZER" "$RUN_DIR/analyze_vla_campaign.py"
sha256sum "$SOURCE_RUN/matrix_summary.json" "$SOURCE_RUN/bundles.jsonl" \
  > "$RUN_DIR/source_e5_1.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/analyze_vla_campaign.py" \
  --input "$SOURCE_RUN" \
  --select-minimal-profile \
  --output "$RUN_DIR/shadow-profile-selection.json" \
  | tee "$RUN_DIR/selection.log"

jq -e '
  .schema == "cruzr-s2-vla-preliminary-profile-selection-e5.2-v1"
  and .source_bundle_count == 160
  and .overall_preliminary_profile == "P14_A"
  and ([.task_selections[].selected_profile] | length == 4 and all(. == "P14_A"))
  and .group_findings.H.tasks_with_material_improvement == 0
  and .group_findings.W.tasks_with_material_improvement == 0
  and .group_findings.L.tasks_with_material_improvement == 0
  and .lifter_all_profiles.bundle_count == 80
  and .lifter_all_profiles.rejected_safe_count == 12
  and .physical_task_success_evaluated == false
  and .robot_state_read_live == false
  and .network_calls == 0
  and .physical_publishers == 0
  and .physical_movement_commanded == false
  and .physical_executor_authorized == false
  and .e6_0_authorized == false
' "$RUN_DIR/shadow-profile-selection.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E5.2
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_PRELIMINARY_P14_ALL_TASKS_PHYSICAL_BLOCKED
mode: offline_analysis_no_robot_no_ros_no_publisher
source_run: $SOURCE_RUN
source_bundles: 160
selected_profile_task_0: $(jq -r '.task_selections["0"].selected_profile' "$RUN_DIR/shadow-profile-selection.json")
selected_profile_task_1: $(jq -r '.task_selections["1"].selected_profile' "$RUN_DIR/shadow-profile-selection.json")
selected_profile_task_2: $(jq -r '.task_selections["2"].selected_profile' "$RUN_DIR/shadow-profile-selection.json")
selected_profile_task_3: $(jq -r '.task_selections["3"].selected_profile' "$RUN_DIR/shadow-profile-selection.json")
head_material_improvement_tasks: 0
waist_material_improvement_tasks: 0
lifter_material_improvement_tasks: 0
lifter_rejected_safe_bundles: 12/80
physical_task_success_evaluated: false
robot_state_read_live: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
physical_executor_authorized: false
e6_0_authorized: false
blocking_gates: E4.4_fixture,VLA_ready,physical_executor,acceleration,vendor_timeline
recovery_or_stop: LOCAL_PROCESS_EXITED_NO_PHYSICAL_EXECUTOR_EXISTED
next_work: RESOLVE_E4.4_AND_EXECUTOR_GATES_BEFORE_ANY_E6_CANARY
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(
  cd "$RUN_DIR"
  sha256sum -c evidence.sha256
) >/dev/null
printf 'E5.2_SELECTION=P14_A,task0:P14_A,task1:P14_A,task2:P14_A,task3:P14_A\n'
printf 'E5.2_PHYSICAL_AUTHORIZED=0\n'
printf 'E5.2_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E5.2_RESULT=PASS_PRELIMINARY_P14_ALL_TASKS_PHYSICAL_BLOCKED\n'
