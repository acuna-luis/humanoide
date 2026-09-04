#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_task_entry_recovery_e6_1b.sh --check
  ./scripts/vla/audit_vla_task_entry_recovery_e6_1b.sh --run

Audita offline los previews separados ENTRY/recovery de episode_000040, el
gate exacto de fixture+estado 20D y el perfil P14 de cinco shadow. No instala
ni registra tareas, no usa robot/red/ROS/contenedores y no mueve.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_task_entry_recovery_e6_1b.py"
readonly CHECKER="$SCRIPT_DIR/check_vla_task0_entry_e6_1b.py"
readonly TESTER="$SCRIPT_DIR/test_vla_task0_entry_e6_1b.py"
readonly STATE_NORMALIZER="$SCRIPT_DIR/normalize_vla_joint_state_e6_1b.py"
readonly SHADOW_SUMMARIZER="$SCRIPT_DIR/summarize_vla_task0_shadow_e6_1b.py"
readonly SHADOW_TESTER="$SCRIPT_DIR/test_vla_task0_shadow_e6_1b.py"
readonly SHADOW_RUNNER="$SCRIPT_DIR/run_vla_task0_shadow_e6_1b.sh"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_task0_entry_recovery_e6_1b.json"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_task0_p14_shadow_e6_1b.json"
readonly FIXTURE_EXAMPLE="$SCRIPT_DIR/runtime/cruzr_s2_vla_supported_low_fixture_e6_1b.example.json"
readonly FIXTURE="$SCRIPT_DIR/runtime/cruzr_s2_vla_supported_low_fixture_e6_1b.json"
readonly ENTRY_XML="$SCRIPT_DIR/runtime/tasks/s2_vla_e6_1_task0_entry_preview.xml"
readonly RECOVERY_XML="$SCRIPT_DIR/runtime/tasks/s2_vla_e6_1_task0_recovery_preview.xml"
readonly NEW_EVIDENCE="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly E61A="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260904T103516_E6.1A"
readonly E60Z="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260904T094803_E6.0Z"
readonly E61A_REPORT="$E61A/task0-entry-path-report.json"
readonly CANDIDATE="$E60Z/task0-nearest-entry-candidate.json"
readonly DATASET_REPORT="$E60Z/dataset-entry-states.json"

MODE=check
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in cp find jq mktemp python3 readlink rm sha256sum sort tee xargs; do
  command -v "$tool" >/dev/null || {
    printf 'ERROR: falta herramienta local: %s\n' "$tool" >&2
    exit 1
  }
done
sources=(
  "$SCRIPT_PATH" "$ANALYZER" "$CHECKER" "$TESTER" "$STATE_NORMALIZER"
  "$SHADOW_SUMMARIZER" "$SHADOW_TESTER" "$SHADOW_RUNNER" "$CONTRACT" "$PROFILE"
  "$FIXTURE_EXAMPLE" "$FIXTURE" "$ENTRY_XML" "$RECOVERY_XML" "$NEW_EVIDENCE"
  "$E61A_REPORT" "$CANDIDATE" "$DATASET_REPORT"
)
for source in "${sources[@]}"; do
  test -s "$source" || { printf 'ERROR: falta fuente E6.1B: %s\n' "$source" >&2; exit 1; }
done
for evidence in "$E61A" "$E60Z"; do
  test -s "$evidence/evidence.sha256"
  (cd "$evidence" && sha256sum -c evidence.sha256 >/dev/null)
done

jq -e '
  .schema == "cruzr-s2-vla-task0-entry-recovery-e6.1b-v1"
  and .task_id == 0
  and .scenario == "SUPPORTED_LOW"
  and .candidate.episode == "episode_000040"
  and .candidate.frame == 0
  and (.candidate.joint_order | length) == 20
  and (.candidate.entry_state_20d_rad | length) == 20
  and .entry_gate.same_frozen_frame_required == true
  and .shadow_gate.independent_repetitions == 5
  and .shadow_gate.axis_profile == "P14_A"
  and .shadow_gate.maximum_p14_first_point_delta_rad == 0.1
  and .available_table_observation.surface_width_depth_height_floor_m == [0.838, 0.84, 0.77]
  and .available_table_observation.measured_thickness_m == 0.038
  and .available_table_observation.thickness_physically_measured == true
  and .available_table_observation.support_and_box_obb_candidates == [20, 44]
  and .available_table_observation.actual_dimensions_offline_screen_obb_candidates == 44
  and .available_table_observation.actual_dimensions_offline_screen_exact_robot_or_clamp_hits == 0
  and .available_table_observation.qualified_for_home_entry_with_table_present == false
  and .available_table_observation.eligible_for_stationary_shadow_after_measured_manifest == true
  and .trajectory_preview.install_or_run_interface_present == false
  and .physical_execution_authorized == false
  and .physical_publisher_implemented == false
  and .persistent_install_implemented == false
' "$CONTRACT" >/dev/null
jq -e '
  .profile == "cruzr_s2_task0_episode40_p14_shadow_e6_1b_v1"
  and .action_dim == 20
  and (.commanded_joint_names | length) == 14
  and (.locked_joint_names | length) == 6
  and (.max_first_point_delta[0:14] | all(. == 0.1))
  and .state_defaults == {}
' "$PROFILE" >/dev/null
jq -e '
  .physical_fixture_frozen == false
  and .movement_authorized == false
  and .entry_recovery_with_fixture_authorized == false
  and .support.surface_height_floor_m == 0.77
  and .support.width_m == 0.838
  and .support.depth_m == 0.84
  and .support.thickness_m == null
' "$FIXTURE_EXAMPLE" >/dev/null
jq -e '
  .fixture_id == "TABLE_77_B0_20260904"
  and .physical_fixture_frozen == true
  and .movement_authorized == false
  and .entry_recovery_with_fixture_authorized == false
  and .measurement_uncertainty_m == 0.005
  and .support.surface_height_floor_m == 0.77
  and .support.width_m == 0.838
  and .support.depth_m == 0.84
  and .support.thickness_m == 0.038
  and .box.color_family == "blue"
  and .box.empty == true
  and .box.open_top == true
  and (.evidence_files | length) == 2
' "$FIXTURE" >/dev/null

fixture_gate_tmp="$(mktemp)"
trap 'rm -f -- "$fixture_gate_tmp"' EXIT
PYTHONDONTWRITEBYTECODE=1 python3 "$CHECKER" \
  --contract "$CONTRACT" --dataset-report "$DATASET_REPORT" \
  --fixture-manifest "$FIXTURE" --output "$fixture_gate_tmp" >/dev/null
jq -e '
  .fixture_qualified == true
  and .entry_state_qualified == false
  and .qualified_for_five_shadow == false
  and .physical_execution_authorized == false
  and .fixture.visual_domain_shifts.color_family == {"reference":"gray","observed":"blue"}
' "$fixture_gate_tmp" >/dev/null
rm -f -- "$fixture_gate_tmp"
trap - EXIT

PYTHONDONTWRITEBYTECODE=1 python3 - "$ANALYZER" "$CHECKER" "$STATE_NORMALIZER" "$SHADOW_SUMMARIZER" <<'PY'
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
print("E6.1B_STATIC_SAFETY_OK=ros:none,network:none,container:none,publisher:none,movement:none")
PY

grep -Fq 'E6.1B_MOVEMENT_PATH=absent' "$SHADOW_RUNNER"
grep -Fq 'E6.1B_FIVE_SHADOW_CHECK_OK=offline-only' "$SHADOW_RUNNER"
! grep -Eq '/mc/sdk/robot_command|send_goal|publish\(' "$SHADOW_RUNNER"

PYTHONDONTWRITEBYTECODE=1 python3 "$TESTER"
PYTHONDONTWRITEBYTECODE=1 python3 "$SHADOW_TESTER"
analyzer_args=(
  --contract "$CONTRACT"
  --profile "$PROFILE"
  --entry-xml "$ENTRY_XML"
  --recovery-xml "$RECOVERY_XML"
  --e6-1a-report "$E61A_REPORT"
  --candidate "$CANDIDATE"
  --fixture-manifest "$FIXTURE"
)

if [[ "$MODE" == check ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${analyzer_args[@]}"
  printf 'E6.1B_CHECK_OK=offline-implementation,no-robot,no-network,no-ros,no-container,no-publisher,no-movement\n'
  exit 0
fi

RUN_DIR="$($NEW_EVIDENCE --experiment E6.1B)"
START_TIME="$(date --iso-8601=seconds)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.1B
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: FAIL_SAFE_OFFLINE_IMPLEMENTATION_INCOMPLETE
robot_accessed: false
physical_publishers: 0
physical_movement_commanded: false
physical_execution_authorized: false
EOF
    (
      cd "$RUN_DIR"
      find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
    ) > "$RUN_DIR/evidence.sha256"
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cp -- "$ANALYZER" "$CHECKER" "$TESTER" "$STATE_NORMALIZER" \
  "$SHADOW_SUMMARIZER" "$SHADOW_TESTER" "$SHADOW_RUNNER" "$CONTRACT" "$PROFILE" \
  "$FIXTURE_EXAMPLE" "$FIXTURE" "$ENTRY_XML" "$RECOVERY_XML" "$RUN_DIR/"
printf '%s\n' "$E61A" "$E60Z" > "$RUN_DIR/source_runs.txt"
sha256sum "${sources[@]}" > "$RUN_DIR/source_hashes.sha256"

PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${analyzer_args[@]}" \
  --output "$RUN_DIR/task0-entry-recovery-report.json" \
  2>&1 | tee "$RUN_DIR/analyzer.log"

jq -e '
  .status == "PASS_OFFLINE_IMPLEMENTATION_FIXTURE_FROZEN_LIVE_SHADOW_PENDING"
  and .candidate.episode == "episode_000040"
  and .candidate.maximum_p14_first_action_delta_rad <= 0.1
  and .entry_recovery_previews.endpoints_exact == true
  and .entry_recovery_previews.registered_or_installed == false
  and .entry_recovery_previews.runtime_law_equivalence_demonstrated == false
  and .fixture_gate.physical_fixture_frozen == true
  and .fixture_gate.evidence_photo_count == 2
  and .shadow_gate.independent_repetitions == 5
  and .physical_execution_authorized == false
  and .robot_accessed == false
  and .network_calls == 0
  and .ros_imported == false
  and .physical_publishers == 0
  and .physical_movement_commanded == false
' "$RUN_DIR/task0-entry-recovery-report.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.1B
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_OFFLINE_IMPLEMENTATION_FIXTURE_FROZEN_LIVE_SHADOW_PENDING
candidate_episode: episode_000040
candidate_frame: 0
scenario: SUPPORTED_LOW
entry_recovery_preview_endpoints_exact: true
entry_recovery_registered_or_installed: false
runtime_law_equivalence_demonstrated: false
fixture_physically_frozen: true
five_live_shadow_repetitions_completed: false
robot_accessed: false
persistent_container_started: false
physical_publishers: 0
physical_movement_commanded: false
physical_execution_authorized: false
next_gate: REVIEW_SEPARATE_PHYSICAL_ENTRY_THEN_RUN_FIVE_SHADOW
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.1B_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.1B_RESULT=PASS_OFFLINE_IMPLEMENTATION_FIXTURE_FROZEN_LIVE_SHADOW_PENDING\n'
