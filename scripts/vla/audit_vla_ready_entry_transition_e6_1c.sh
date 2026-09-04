#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_ready_entry_transition_e6_1c.sh --check
  ./scripts/vla/audit_vla_ready_entry_transition_e6_1c.sh --run

Audita offline la transición reducida READY <-> ENTRY de E6.1C. Conserva los
14 ejes de brazo en READY y mueve sólo cabeza, elevador y cintura. No conecta
al robot/red, no usa ROS/contenedores, no instala tareas y no mueve.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_ready_entry_transition_e6_1c.py"
readonly STATE_GATE="$SCRIPT_DIR/check_vla_ready_entry_state_e6_1c.py"
readonly TESTER="$SCRIPT_DIR/test_vla_ready_entry_state_e6_1c.py"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_ready_entry_transition_e6_1c.json"
readonly ENTRY_CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_task0_entry_recovery_e6_1b.json"
readonly ENTRY_XML="$SCRIPT_DIR/runtime/tasks/s2_vla_e6_1c_ready_to_entry_preview.xml"
readonly RECOVERY_XML="$SCRIPT_DIR/runtime/tasks/s2_vla_e6_1c_entry_to_ready_preview.xml"
readonly NEW_EVIDENCE="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly FK_HELPER="$SCRIPT_DIR/analyze_vla_fixture_collision_e4_1c.py"
readonly PATH_HELPER="$SCRIPT_DIR/analyze_vla_self_collision_e6_0b.py"
readonly MESH_HELPER="$SCRIPT_DIR/analyze_vla_near_pair_mesh_e6_0c.py"
readonly GEOMETRY_HELPER="$SCRIPT_DIR/analyze_vla_document_proxy_clamp_e6_0j.py"
readonly E60Z="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260904T094803_E6.0Z"
readonly E61A="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260904T103516_E6.1A"
readonly E41C="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093408_E4.1C"
readonly E60J="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T120626_E6.0J"
readonly READY_SOURCE="$E60Z/failed-canary-input-state.json"
readonly E61A_REPORT="$E61A/task0-entry-path-report.json"
readonly SDK_URDF="$E41C/artifacts/vendor_cruzr_s2_v1.urdf"
readonly SDK_URDF_ZIP="$REPO_ROOT/Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip"
readonly DOCUMENT_PROXY_REPORT="$E60J/document-proxy-clamp-report.json"

MODE=check
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in cp find jq python3 readlink sha256sum sort tee xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta herramienta: %s\n' "$tool" >&2; exit 1; }
done
sources=(
  "$SCRIPT_PATH" "$ANALYZER" "$STATE_GATE" "$TESTER" "$CONTRACT"
  "$ENTRY_CONTRACT" "$ENTRY_XML" "$RECOVERY_XML" "$NEW_EVIDENCE"
  "$READY_SOURCE" "$E61A_REPORT" "$SDK_URDF" "$SDK_URDF_ZIP"
  "$DOCUMENT_PROXY_REPORT" "$FK_HELPER" "$PATH_HELPER" "$MESH_HELPER"
  "$GEOMETRY_HELPER"
)
for source in "${sources[@]}"; do
  test -s "$source" || { printf 'ERROR: falta fuente E6.1C: %s\n' "$source" >&2; exit 1; }
done
for evidence in "$E60Z" "$E61A" "$E41C" "$E60J"; do
  test -s "$evidence/evidence.sha256"
  (cd "$evidence" && sha256sum -c evidence.sha256 >/dev/null)
done

jq -e '
  .schema == "cruzr-s2-vla-ready-entry-transition-e6.1c-v1"
  and .candidate_episode == "episode_000040"
  and .candidate_frame == 0
  and (.joint_order | length) == 20
  and (.commanded_joint_names | length) == 6
  and (.uncommanded_arm_joint_names | length) == 14
  and .trajectory_design.entry_duration_seconds == 12.0
  and .trajectory_design.recovery_to_ready_duration_seconds == 12.0
  and .trajectory_design.maximum_velocity_rad_s == 0.15
  and .trajectory_design.maximum_acceleration_rad_s2 == 0.5
  and .trajectory_design.runtime_law_equivalence_demonstrated == false
  and .trajectory_design.owner_accepted_for_physical_e6_1c == false
  and .fixture_transition_policy.reconstructed_pose_ready_entry_obb_candidates == {"support":0,"box":0}
  and .persistent_install_implemented == false
  and .physical_execution_authorized == false
  and .physical_publisher_implemented == false
' "$CONTRACT" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 - "$ANALYZER" "$STATE_GATE" <<'PY'
import ast
import pathlib
import sys

for raw in sys.argv[1:]:
    path = pathlib.Path(raw)
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    tree = ast.parse(source)
    imports = set()
    attributes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Attribute):
            attributes.add(node.attr)
    assert not imports & {"rclpy", "rosa", "socket", "requests", "subprocess", "urllib"}
    assert not attributes & {"create_client", "create_publisher", "publish", "send_goal_async"}
    assert "/mc/sdk/robot_command" not in source
print("E6.1C_STATIC_SAFETY_OK=ros:none,network:none,container:none,publisher:none,movement:none")
PY

! grep -Eq 'type="arm"|/mc/sdk/robot_command|send_goal|publish\(' "$ENTRY_XML" "$RECOVERY_XML"
PYTHONDONTWRITEBYTECODE=1 python3 "$TESTER"

analyzer_args=(
  --contract "$CONTRACT"
  --entry-contract "$ENTRY_CONTRACT"
  --ready-source "$READY_SOURCE"
  --entry-xml "$ENTRY_XML"
  --recovery-xml "$RECOVERY_XML"
  --e6-1a-report "$E61A_REPORT"
  --sdk-urdf "$SDK_URDF"
  --sdk-urdf-zip "$SDK_URDF_ZIP"
  --document-proxy-report "$DOCUMENT_PROXY_REPORT"
  --fk-helper "$FK_HELPER"
  --path-helper "$PATH_HELPER"
  --mesh-helper "$MESH_HELPER"
  --geometry-helper "$GEOMETRY_HELPER"
)

if [[ "$MODE" == check ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${analyzer_args[@]}"
  printf 'E6.1C_CHECK_OK=offline-only,arms-commanded:0,no-robot,no-network,no-ros,no-container,no-publisher,no-movement\n'
  exit 0
fi

RUN_DIR="$($NEW_EVIDENCE --experiment E6.1C)"
START_TIME="$(date --iso-8601=seconds)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat >"$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.1C
status: FAIL_SAFE_OFFLINE_REDUCED_TRANSITION
robot_accessed: false
physical_publishers: 0
physical_movement_commanded: false
physical_execution_authorized: false
EOF
    (cd "$RUN_DIR" && find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum) >"$RUN_DIR/evidence.sha256"
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cp -- "${sources[@]}" "$RUN_DIR/"
sha256sum "${sources[@]}" >"$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${analyzer_args[@]}" \
  --output "$RUN_DIR/ready-entry-transition-report.json" \
  2>&1 | tee "$RUN_DIR/analyzer.log"
jq -e '
  .status == "PASS_OFFLINE_REDUCED_READY_ENTRY_OWNER_ACCEPTANCE_PENDING"
  and .transition.uncommanded_arm_joint_count == 14
  and .transition.entry_distance_to_frozen_frame_rad <= 0.01
  and .joint_limit_violations == []
  and .self_collision_exact_hits == []
  and .clamp_robot_exact_hits == []
  and .clamp_clamp_obb_candidate_samples == []
  and .reconstructed_fixture_obb_candidates == {"box":[],"support":[]}
  and .gates.owner_accepted_for_physical_e6_1c == false
  and .gates.runtime_tasks_installed == false
  and .physical_execution_authorized == false
  and .robot_accessed == false
  and .physical_movement_commanded == false
' "$RUN_DIR/ready-entry-transition-report.json" >/dev/null

cat >"$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.1C
run_id: $(basename -- "$RUN_DIR")
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_OFFLINE_REDUCED_READY_ENTRY_OWNER_ACCEPTANCE_PENDING
candidate: episode_000040/frame_0
arm_joints_commanded: 0
locked_axes_commanded: 6
duration_seconds_each_direction: 12.0
joint_limit_violations: 0
self_collision_exact_hits: 0
clamp_robot_exact_hits: 0
fixture_obb_candidates: 0
runtime_law_equivalence_demonstrated: false
runtime_tasks_installed: false
robot_accessed: false
physical_publishers: 0
physical_movement_commanded: false
physical_execution_authorized: false
next_gate: OWNER_ACCEPT_E6_1C_TRANSITION_LIMITS_THEN_IMPLEMENT_SEPARATE_INSTALL_RELOAD_AND_RUN
EOF
(cd "$RUN_DIR" && find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum) >"$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.1C_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.1C_RESULT=PASS_OFFLINE_REDUCED_READY_ENTRY_OWNER_ACCEPTANCE_PENDING\n'
