#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_task_entry_path_e6_1a.sh --check
  ./scripts/vla/audit_vla_task_entry_path_e6_1a.sh --run

Congela y audita offline una transición 20D HOME -> ENTRY task 0 -> HOME,
incluidos límites articulares, dinámica minimum-jerk, mallas del robot,
proxies documentales de las abrazaderas y fixture SUPPORTED_LOW reconstruido.

No conecta al robot ni a la red, no usa ROS, no inicia contenedores, no crea
publicadores y no autoriza movimiento físico.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_task_entry_path_e6_1a.py"
readonly ENTRY_CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_task0_entry_e6_1a.json"
readonly TASK_CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_task_entry_contract_e6_0z.json"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly FK_HELPER="$SCRIPT_DIR/analyze_vla_fixture_collision_e4_1c.py"
readonly PATH_HELPER="$SCRIPT_DIR/analyze_vla_self_collision_e6_0b.py"
readonly MESH_HELPER="$SCRIPT_DIR/analyze_vla_near_pair_mesh_e6_0c.py"
readonly GEOMETRY_HELPER="$SCRIPT_DIR/analyze_vla_document_proxy_clamp_e6_0j.py"
readonly FIXTURE_HELPER="$SCRIPT_DIR/derive_vla_fixture_pose.py"

readonly E6Z="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260904T094803_E6.0Z"
readonly E6I="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T115129_E6.0I"
readonly E41="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260901T084855_E4.1"
readonly E41C="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093408_E4.1C"
readonly E60J="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T120626_E6.0J"
readonly E60K="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T121338_E6.0K"

readonly CANDIDATE="$E6Z/task0-nearest-entry-candidate.json"
readonly CANDIDATE_RGB="$E6Z/task0-nearest-entry-candidate.png"
readonly DATASET_ENTRY_REPORT="$E6Z/dataset-entry-states.json"
readonly DATASET_INFO="$REPO_ROOT/cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319/meta/info.json"
readonly HISTORICAL_HOME="$E6I/actuator-state.json"
readonly CAMERA_INFO="$E41/artifacts/camera_info.json"
readonly TF_STATIC="$E41/artifacts/tf_static.jsonstream"
readonly METRIC_FIXTURE_SUMMARY="$E41/results/summary.json"
readonly SDK_URDF="$E41C/artifacts/vendor_cruzr_s2_v1.urdf"
readonly SDK_URDF_ZIP="$REPO_ROOT/Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip"
readonly DOCUMENT_PROXY_REPORT="$E60J/document-proxy-clamp-report.json"
readonly OBSERVED_CLAMP_REPORT="$E60K/observed-clamp-containment-report.json"

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in cp find jq python3 readlink sha256sum sort tee xargs; do
  command -v "$tool" >/dev/null || {
    echo "ERROR: falta herramienta local: $tool" >&2
    exit 1
  }
done

sources=(
  "$ANALYZER" "$ENTRY_CONTRACT" "$TASK_CONTRACT" "$EVIDENCE_SCRIPT"
  "$CANDIDATE" "$CANDIDATE_RGB" "$DATASET_ENTRY_REPORT" "$DATASET_INFO"
  "$HISTORICAL_HOME" "$CAMERA_INFO" "$TF_STATIC" "$METRIC_FIXTURE_SUMMARY"
  "$SDK_URDF" "$SDK_URDF_ZIP" "$DOCUMENT_PROXY_REPORT"
  "$OBSERVED_CLAMP_REPORT" "$FK_HELPER" "$PATH_HELPER" "$MESH_HELPER"
  "$GEOMETRY_HELPER" "$FIXTURE_HELPER"
)
for source in "${sources[@]}"; do
  test -s "$source" || {
    echo "ERROR: falta fuente E6.1A: $source" >&2
    exit 1
  }
done

for evidence in "$E6Z" "$E6I" "$E41" "$E41C" "$E60J" "$E60K"; do
  test -s "$evidence/evidence.sha256" || {
    echo "ERROR: falta manifiesto: $evidence/evidence.sha256" >&2
    exit 1
  }
  (cd "$evidence" && sha256sum -c evidence.sha256 >/dev/null)
done

jq -e '
  .schema == "cruzr-s2-vla-task0-entry-e6.1a-v1"
  and .task_id == 0
  and .scenario == "SUPPORTED_LOW"
  and (.joint_order | length) == 20
  and .physical_execution_authorized == false
  and .trajectory_design.manufacturer_certified == false
  and .trajectory_design.owner_accepted_for_physical_e6_1 == false
' "$ENTRY_CONTRACT" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 - "$ANALYZER" <<'PY'
import ast
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
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
print("E6.1A_STATIC_SAFETY_OK=ros:none,network:none,container:none,publisher:none,movement:none")
PY

analyzer_args=(
  --entry-contract "$ENTRY_CONTRACT"
  --candidate "$CANDIDATE"
  --candidate-rgb "$CANDIDATE_RGB"
  --dataset-entry-report "$DATASET_ENTRY_REPORT"
  --dataset-info "$DATASET_INFO"
  --task-contract "$TASK_CONTRACT"
  --historical-home "$HISTORICAL_HOME"
  --camera-info "$CAMERA_INFO"
  --tf-static "$TF_STATIC"
  --metric-fixture-summary "$METRIC_FIXTURE_SUMMARY"
  --sdk-urdf "$SDK_URDF"
  --sdk-urdf-zip "$SDK_URDF_ZIP"
  --document-proxy-report "$DOCUMENT_PROXY_REPORT"
  --observed-clamp-report "$OBSERVED_CLAMP_REPORT"
  --fk-helper "$FK_HELPER"
  --path-helper "$PATH_HELPER"
  --mesh-helper "$MESH_HELPER"
  --geometry-helper "$GEOMETRY_HELPER"
  --fixture-pose-helper "$FIXTURE_HELPER"
)

if [[ "$MODE" == "check" ]]; then
  printf 'E6.1A_CHECK_OK=local-only,no-robot,no-network,no-ros,no-container,no-publisher,no-movement\n'
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.1A)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    local report_status="FAIL_SAFE_BEFORE_E6_1A_COMPLETION"
    if [[ -s "$RUN_DIR/task0-entry-path-report.json" ]]; then
      report_status="$(jq -r '.status // "FAIL_SAFE_E6_1A"' "$RUN_DIR/task0-entry-path-report.json")"
    fi
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.1A
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: $report_status
mode: local_offline_no_robot_no_network_no_ros_no_container_no_publisher
robot_accessed: false
persistent_container_started: false
physical_publishers: 0
physical_movement_commanded: false
physical_authorized: false
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

cp -- "$ANALYZER" "$RUN_DIR/analyze_vla_task_entry_path_e6_1a.py"
cp -- "$ENTRY_CONTRACT" "$RUN_DIR/task0-entry-contract.json"
cp -- "$CANDIDATE" "$RUN_DIR/task0-entry-candidate.json"
cp -- "$CANDIDATE_RGB" "$RUN_DIR/task0-entry-candidate.png"
printf '%s\n' "$E6Z" "$E6I" "$E41" "$E41C" "$E60J" "$E60K" \
  > "$RUN_DIR/source_runs.txt"
sha256sum "${sources[@]}" > "$RUN_DIR/source_hashes.sha256"

PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/analyze_vla_task_entry_path_e6_1a.py" \
  "${analyzer_args[@]}" --output "$RUN_DIR/task0-entry-path-report.json" \
  2>&1 | tee "$RUN_DIR/analyzer.log"

jq -e '
  .schema == "cruzr-s2-vla-task0-entry-path-e6.1a-v1"
  and .status == "PASS_OFFLINE_TASK0_ENTRY_CANDIDATE_PHYSICAL_AND_SHADOW_STILL_BLOCKED"
  and .candidate.episode == "episode_000040"
  and .candidate.task == 0
  and .candidate.scenario == "SUPPORTED_LOW"
  and .candidate.maximum_absolute_first_action_delta_rad <= 0.1
  and .trajectory.joint_limit_violations == []
  and .trajectory.dynamics.passes_design_envelope == true
  and .self_collision.exact_intersections == []
  and .self_collision.proxy_robot_exact_intersections == []
  and .self_collision.proxy_proxy_obb_candidate_samples == []
  and .fixture_screen.central_support_obb_candidates == []
  and .fixture_screen.central_box_outer_obb_candidates == []
  and .fixture_screen.pixel_uncertainty_obb_candidates == []
  and .fixture_screen.existing_table_usable_for_candidate == false
  and .gates.physical_execution_authorized == false
  and .robot_accessed == false
  and .persistent_container_started == false
  and .ros_imported == false
  and .physical_publisher_created == false
  and .physical_movement_commanded == false
  and .physical_execution_authorized == false
' "$RUN_DIR/task0-entry-path-report.json" >/dev/null

jq -r --arg run_id "$(basename -- "$RUN_DIR")" \
  --arg operator "${USER:-unknown}" --arg start "$START_TIME" \
  --arg end "$(date --iso-8601=seconds)" '
  "experiment_id: E6.1A",
  "run_id: \($run_id)",
  "operator: \($operator)",
  "start_time: \($start)",
  "end_time: \($end)",
  "status: \(.status)",
  "mode: \(.mode)",
  "candidate_episode: \(.candidate.episode)",
  "candidate_task: \(.candidate.task)",
  "scenario: \(.candidate.scenario)",
  "first_action_delta_rad: \(.candidate.maximum_absolute_first_action_delta_rad)",
  "entry_duration_seconds: \(.trajectory.dynamics.duration_seconds_each_direction)",
  "maximum_target_delta_rad: \(.trajectory.dynamics.maximum_absolute_target_delta_rad)",
  "maximum_target_delta_joint: \(.trajectory.dynamics.maximum_delta_joint)",
  "joint_limit_violations: \(.trajectory.joint_limit_violations | length)",
  "exact_self_collision_hits: \(.self_collision.exact_intersections | length)",
  "exact_clamp_proxy_hits: \(.self_collision.proxy_robot_exact_intersections | length)",
  "support_height_floor_inferred_m: \(.scene_reconstruction.inferred_support_surface_height_floor_m)",
  "pixel_uncertainty_fixture_candidates: \(.fixture_screen.pixel_uncertainty_obb_candidates | length)",
  "existing_table_usable: \(.fixture_screen.existing_table_usable_for_candidate)",
  "robot_accessed: \(.robot_accessed)",
  "persistent_container_started: \(.persistent_container_started)",
  "physical_publishers: 0",
  "physical_movement_commanded: \(.physical_movement_commanded)",
  "physical_authorized: \(.physical_execution_authorized)",
  "next_gate: \(.next_gate)"
' "$RUN_DIR/task0-entry-path-report.json" > "$RUN_DIR/actual_result.yaml"

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.1A_EVIDENCE_OK=%s\n' "$RUN_DIR"
