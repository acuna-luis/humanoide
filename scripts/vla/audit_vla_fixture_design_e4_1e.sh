#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_fixture_design_e4_1e.sh --check
  ./scripts/vla/audit_vla_fixture_design_e4_1e.sh --run

Busca offline una pose alternativa del tablero manteniendo fija la pose de B0
y deriva muescas para el barrido conocido de muñeca/sensor. No conecta con el
robot, no inicia inferencia, no publica, no mueve y no autoriza fabricar ni
acercar el fixture.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_fixture_design_e4_1e.py"
readonly GEOMETRY_LIBRARY="$SCRIPT_DIR/analyze_vla_fixture_collision_e4_1c.py"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_fixture_design_contract_e4_1e.yaml"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly EVIDENCE_ROOT="${VLA_EVIDENCE_ROOT:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence}"
readonly SDK_ZIP_REL="Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip"
readonly SDK_ZIP_SHA256="7cb7f856223ce99a86d44349be475a2b5925d57ca694ee069a96c808802e297e"

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in awk cp dirname find grep jq mkdir python3 readlink sha256sum sort tee unzip xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta herramienta local: %s\n' "$tool" >&2; exit 1; }
done
for required in "$ANALYZER" "$GEOMETRY_LIBRARY" "$CONTRACT" "$EVIDENCE_SCRIPT" "$REPO_ROOT/$SDK_ZIP_REL"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
python3 -m py_compile "$ANALYZER" "$GEOMETRY_LIBRARY"
python3 -c 'import numpy, yaml'

cd "$REPO_ROOT"
[[ "$(sha256sum "$SDK_ZIP_REL" | awk '{print $1}')" == "$SDK_ZIP_SHA256" ]] || {
  echo 'ERROR: cambió el ZIP URDF del SDK' >&2; exit 1;
}

latest_run() {
  local experiment="$1"
  find "$EVIDENCE_ROOT" -mindepth 2 -maxdepth 2 -type f \
    -path "*_${experiment}/actual_result.yaml" -printf '%T@ %h\n' | sort -nr | \
    awk 'NR==1 {$1=""; sub(/^ /, ""); print; exit}'
}

latest_e4_0="$(latest_run 'E4.0')"
latest_e4_1="$(latest_run 'E4.1')"
latest_e4_1d="$(latest_run 'E4.1D')"
for source in "$latest_e4_0" "$latest_e4_1" "$latest_e4_1d"; do
  test -n "$source" || { echo 'ERROR: falta una evidencia fuente E4.0/E4.1/E4.1D' >&2; exit 1; }
  (
    cd "$source"
    sha256sum -c evidence.sha256 >/dev/null
  )
done
grep -Fq 'status: PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE' "$latest_e4_0/actual_result.yaml"
grep -Fq 'status: METRIC_FIXTURE_CANDIDATE_RESOLVED_PHYSICAL_GATES_OPEN' "$latest_e4_1/actual_result.yaml"
grep -Fq 'status: PGC_NOT_INSTALLED_EFFECTOR_SOLID_TABLETOP_STILL_REJECTED_BY_UPSTREAM_ARM_SWEEP' "$latest_e4_1d/actual_result.yaml"
test -s "$latest_e4_0/summary.json"
test -s "$latest_e4_1/results/summary.json"
test -s "$latest_e4_1d/results/summary.json"

printf 'E4.1E_CHECK_OK=local-only,B0-fixed,solid-pose-search,upstream-cutouts\n'
printf 'E4.1E_SOURCES=E4.0:%s,E4.1:%s,E4.1D:%s\n' "$latest_e4_0" "$latest_e4_1" "$latest_e4_1d"
printf 'ROBOT_CONNECTIONS=0; INFERENCE_STARTED=0; PUBLISHERS_CREATED=0; MOVEMENT_COMMANDS=0\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E4.1E)"
mkdir -- "$RUN_DIR/artifacts" "$RUN_DIR/results"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.1E
run_id: $(basename -- "$RUN_DIR")
status: FAIL_BEFORE_COMPLETING_LOCAL_FIXTURE_DESIGN
robot_connections: 0
inference_started: false
physical_publisher_created: false
physical_movement_commanded: false
physical_test_authorized: false
recovery_or_stop: NOT_APPLICABLE_LOCAL_ONLY
EOF
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cp -- "$ANALYZER" "$RUN_DIR/artifacts/analyze_vla_fixture_design_e4_1e.py"
cp -- "$GEOMETRY_LIBRARY" "$RUN_DIR/artifacts/analyze_vla_fixture_collision_e4_1c.py"
cp -- "$CONTRACT" "$RUN_DIR/artifacts/cruzr_s2_fixture_design_contract_e4_1e.yaml"
cp -- "$latest_e4_0/summary.json" "$RUN_DIR/artifacts/e4_0_summary.json"
cp -- "$latest_e4_1/results/summary.json" "$RUN_DIR/artifacts/e4_1_summary.json"
cp -- "$latest_e4_1d/results/summary.json" "$RUN_DIR/artifacts/e4_1d_summary.json"
unzip -p "$SDK_ZIP_REL" '*/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf' \
  > "$RUN_DIR/artifacts/vendor_cruzr_s2_v1.urdf"
printf '%s\n%s\n%s\n' "$latest_e4_0" "$latest_e4_1" "$latest_e4_1d" > "$RUN_DIR/source_paths.txt"
printf '%s  %s\n' "$SDK_ZIP_SHA256" "$SDK_ZIP_REL" > "$RUN_DIR/vendor_sources.sha256"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$RUN_DIR/artifacts" \
  python3 "$RUN_DIR/artifacts/analyze_vla_fixture_design_e4_1e.py" \
  --contract "$RUN_DIR/artifacts/cruzr_s2_fixture_design_contract_e4_1e.yaml" \
  --urdf "$RUN_DIR/artifacts/vendor_cruzr_s2_v1.urdf" \
  --sdk-urdf-zip "$SDK_ZIP_REL" \
  --e4-0-summary "$RUN_DIR/artifacts/e4_0_summary.json" \
  --e4-1-summary "$RUN_DIR/artifacts/e4_1_summary.json" \
  --e4-1d-summary "$RUN_DIR/artifacts/e4_1d_summary.json" \
  --output-dir "$RUN_DIR/results" 2>&1 | tee "$RUN_DIR/analyzer.log"

jq -e '
  .experiment_id == "E4.1E"
  and .status == "UPSTREAM_CUTOUT_CANDIDATE_DERIVED_SOLID_ALIGNED_POSE_NOT_FOUND_CLAMP_AND_RECOVERY_UNRESOLVED"
  and .trajectory.unique_samples == 401
  and .solid_table_pose_search.aligned_envelope.collision_free_grid_candidates == 0
  and .upstream_cutout_candidate.overlaps_required_B0_support == false
  and .upstream_cutout_candidate.includes_actual_clamp_geometry == false
  and .gates.upstream_only_cutout_candidate_found == true
  and .gates.physical_test_authorized == false
' "$RUN_DIR/results/summary.json" >/dev/null

left_cutout="$(jq -c '.upstream_cutout_candidate.left_bounds_m' "$RUN_DIR/results/summary.json")"
right_cutout="$(jq -c '.upstream_cutout_candidate.right_bounds_m' "$RUN_DIR/results/summary.json")"
applied_margin="$(jq -r '.uncertainty_and_clearance.applied_xy_margin_m' "$RUN_DIR/results/summary.json")"
global_yaw="$(jq -r '.solid_table_pose_search.global_reference_only.best_refined_candidate.yaw_delta_deg' "$RUN_DIR/results/summary.json")"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.1E
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: UPSTREAM_CUTOUT_CANDIDATE_DERIVED_SOLID_ALIGNED_POSE_NOT_FOUND_CLAMP_AND_RECOVERY_UNRESOLVED
mode: local_read_only_no_robot_no_inference_no_publisher
trajectory_samples: 401
plane_height_offsets_m: [-0.01, 0.0, 0.01]
applied_xy_margin_m: $applied_margin
aligned_solid_table_candidates: 0
global_reference_yaw_delta_deg: $global_yaw
left_open_front_notch_bounds_m: '$left_cutout'
right_open_front_notch_bounds_m: '$right_cutout'
actual_clamp_geometry_included: false
box_was_required_or_placed: false
table_was_approached_or_modified: false
robot_connections: 0
inference_started: false
physical_publisher_created: false
physical_movement_commanded: false
physical_test_authorized: false
recovery_or_stop: NOT_APPLICABLE_LOCAL_ONLY
next_experiment_authorized: AUDIT_OFFICIAL_SUPPLIER_CLAMP_GEOMETRY_OFFLINE_ONLY
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(
  cd "$RUN_DIR"
  sha256sum -c evidence.sha256 >/dev/null
)

printf 'E4.1E_STATUS=UPSTREAM_CUTOUT_CANDIDATE_DERIVED_SOLID_ALIGNED_POSE_NOT_FOUND_CLAMP_AND_RECOVERY_UNRESOLVED\n'
printf 'ALIGNED_SOLID_TABLE_CANDIDATES=0\n'
printf 'UPSTREAM_CUTOUTS=left:%s,right:%s\n' "$left_cutout" "$right_cutout"
printf 'BOX_WAS_REQUIRED_OR_PLACED=0\n'
printf 'PHYSICAL_TEST_AUTHORIZED=0\n'
printf 'E4.1E_EVIDENCE_OK=%s\n' "$RUN_DIR"
