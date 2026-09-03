#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_effector_geometry_e4_1d.sh --check
  ./scripts/vla/audit_vla_effector_geometry_e4_1d.sh --run

Compara offline la topología PGC/finger del URDF/SDK con el contrato verificado
de las abrazaderas instaladas y separa los cruces E4.1C del efector de los de
muñeca/sensor. No conecta con el robot, no inicia inferencia, no publica y no
mueve.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_effector_geometry_e4_1d.py"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_effector_contract_e4_1d.yaml"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly EVIDENCE_ROOT="${VLA_EVIDENCE_ROOT:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence}"
readonly SDK_ZIP_REL="Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip"
readonly SDK_PDF_REL="Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/Cruzr S2 优必选SDK二次开发文档【对外】6.24.pdf"
readonly SDK_ZIP_SHA256="7cb7f856223ce99a86d44349be475a2b5925d57ca694ee069a96c808802e297e"
readonly SDK_PDF_SHA256="4cf441de24c0328a7fc4e991f41cbaa17239e9d9eb7bb6a19e8715c0591a30bd"

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in awk cp dirname find grep jq mkdir pdftotext python3 readlink sed sha256sum sort tee unzip xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta herramienta local: %s\n' "$tool" >&2; exit 1; }
done
for required in "$ANALYZER" "$CONTRACT" "$EVIDENCE_SCRIPT" "$REPO_ROOT/$SDK_ZIP_REL" "$REPO_ROOT/$SDK_PDF_REL"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
python3 -m py_compile "$ANALYZER"
python3 -c 'import yaml'

cd "$REPO_ROOT"
[[ "$(sha256sum "$SDK_ZIP_REL" | awk '{print $1}')" == "$SDK_ZIP_SHA256" ]] || {
  echo 'ERROR: cambió el ZIP URDF del SDK' >&2; exit 1;
}
[[ "$(sha256sum "$SDK_PDF_REL" | awk '{print $1}')" == "$SDK_PDF_SHA256" ]] || {
  echo 'ERROR: cambió el PDF del SDK' >&2; exit 1;
}
grep -Fq '| Efector actual | abrazaderas laterales | **VERIFICADO** |' \
  docs/teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md
grep -Fq '| Efector actual | abrazaderas laterales pasivas | Verificado |' \
  docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md

latest_e4_1c="$(find "$EVIDENCE_ROOT" -mindepth 2 -maxdepth 2 -type f \
  -path '*_E4.1C/actual_result.yaml' -printf '%T@ %h\n' | sort -nr | \
  awk 'NR==1 {$1=""; sub(/^ /, ""); print; exit}')"
test -n "$latest_e4_1c" || { echo 'ERROR: no se encontró evidencia E4.1C' >&2; exit 1; }
grep -Fq 'status: SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP' \
  "$latest_e4_1c/actual_result.yaml"
test -s "$latest_e4_1c/results/summary.json"
(
  cd "$latest_e4_1c"
  sha256sum -c evidence.sha256 >/dev/null
)

printf 'E4.1D_CHECK_OK=local-only,installed:passive-clamp,vendor:PGC-140-50,source:E4.1C\n'
printf 'E4.1D_SOURCE_E4.1C=%s\n' "$latest_e4_1c"
printf 'ROBOT_CONNECTIONS=0; INFERENCE_STARTED=0; PUBLISHERS_CREATED=0; MOVEMENT_COMMANDS=0\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E4.1D)"
mkdir -- "$RUN_DIR/artifacts" "$RUN_DIR/results"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.1D
run_id: $(basename -- "$RUN_DIR")
status: FAIL_BEFORE_COMPLETING_LOCAL_EFFECTOR_AUDIT
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

cp -- "$ANALYZER" "$RUN_DIR/artifacts/analyze_vla_effector_geometry_e4_1d.py"
cp -- "$CONTRACT" "$RUN_DIR/artifacts/cruzr_s2_effector_contract_e4_1d.yaml"
cp -- "$latest_e4_1c/results/summary.json" "$RUN_DIR/artifacts/e4_1c_summary.json"
cp -- "$latest_e4_1c/actual_result.yaml" "$RUN_DIR/artifacts/e4_1c_actual_result.yaml"
unzip -p "$SDK_ZIP_REL" '*/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf' \
  > "$RUN_DIR/artifacts/vendor_cruzr_s2_v1.urdf"
pdftotext -layout "$SDK_PDF_REL" "$RUN_DIR/artifacts/sdk.txt"
sed -n '289,298p;864,871p' docs/teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md \
  > "$RUN_DIR/artifacts/installed_effector_teleop_excerpt.txt"
sed -n '65,73p' docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md \
  > "$RUN_DIR/artifacts/installed_effector_vla_excerpt.txt"
printf '%s\n' "$latest_e4_1c" > "$RUN_DIR/e4_1c_source_path.txt"
printf '%s  %s\n%s  %s\n' \
  "$SDK_ZIP_SHA256" "$SDK_ZIP_REL" "$SDK_PDF_SHA256" "$SDK_PDF_REL" \
  > "$RUN_DIR/vendor_sources.sha256"

python3 "$ANALYZER" \
  --contract "$RUN_DIR/artifacts/cruzr_s2_effector_contract_e4_1d.yaml" \
  --urdf "$RUN_DIR/artifacts/vendor_cruzr_s2_v1.urdf" \
  --sdk-text "$RUN_DIR/artifacts/sdk.txt" \
  --e4-1c-summary "$RUN_DIR/artifacts/e4_1c_summary.json" \
  --output-dir "$RUN_DIR/results" 2>&1 | tee "$RUN_DIR/analyzer.log"

jq -e '
  .experiment_id == "E4.1D"
  and .status == "PGC_NOT_INSTALLED_EFFECTOR_SOLID_TABLETOP_STILL_REJECTED_BY_UPSTREAM_ARM_SWEEP"
  and .e4_1c_collision_partition.total_triangle_surface_events > 0
  and .e4_1c_collision_partition.vendor_pgc_or_finger_events >= 0
  and .e4_1c_collision_partition.upstream_wrist_or_force_sensor_events > 0
  and .e4_1c_collision_partition.other_events == 0
  and (.e4_1c_collision_partition.vendor_pgc_or_finger_events
       + .e4_1c_collision_partition.upstream_wrist_or_force_sensor_events
       + .e4_1c_collision_partition.other_events
       == .e4_1c_collision_partition.total_triangle_surface_events)
  and .vendor_pgc.mechanism_topology_matches_installed_effector == false
  and .conclusions.solid_tabletop_rejection_remains_when_pgc_and_fingers_are_excluded == true
  and .gates.physical_e4_3_or_e4_4_authorized == false
' "$RUN_DIR/results/summary.json" >/dev/null

total_events="$(jq -r '.e4_1c_collision_partition.total_triangle_surface_events' "$RUN_DIR/results/summary.json")"
pgc_events="$(jq -r '.e4_1c_collision_partition.vendor_pgc_or_finger_events' "$RUN_DIR/results/summary.json")"
upstream_events="$(jq -r '.e4_1c_collision_partition.upstream_wrist_or_force_sensor_events' "$RUN_DIR/results/summary.json")"

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.1D
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PGC_NOT_INSTALLED_EFFECTOR_SOLID_TABLETOP_STILL_REJECTED_BY_UPSTREAM_ARM_SWEEP
mode: local_read_only_no_robot_no_inference_no_publisher
installed_effector: passive_lateral_clamps
installed_hw_type: cruzr_s2_v1
vendor_effector_model: Dahuan_PGC-140-50
vendor_pgc_hw_type: cruzr_s2_v1_gripper
total_triangle_surface_events: $total_events
vendor_pgc_or_finger_events: $pgc_events
upstream_wrist_or_force_sensor_events: $upstream_events
pgc_mesh_equivalence_to_clamps: NOT_DEMONSTRATED
solid_tabletop_e4_1_authorized: false
box_was_required_or_placed: false
robot_connections: 0
inference_started: false
physical_publisher_created: false
physical_movement_commanded: false
physical_test_authorized: false
recovery_or_stop: NOT_APPLICABLE_LOCAL_ONLY
next_experiment_authorized: OFFLINE_FIXTURE_CUTOUT_OR_ALTERNATE_POSE_DESIGN_ONLY
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(
  cd "$RUN_DIR"
  sha256sum -c evidence.sha256 >/dev/null
)

printf 'E4.1D_STATUS=PGC_NOT_INSTALLED_EFFECTOR_SOLID_TABLETOP_STILL_REJECTED_BY_UPSTREAM_ARM_SWEEP\n'
printf 'COLLISION_PARTITION=total:%s,pgc-finger:%s,upstream-wrist-force:%s\n' \
  "$total_events" "$pgc_events" "$upstream_events"
printf 'BOX_WAS_REQUIRED_OR_PLACED=0\n'
printf 'PHYSICAL_TEST_AUTHORIZED=0\n'
printf 'E4.1D_EVIDENCE_OK=%s\n' "$RUN_DIR"
