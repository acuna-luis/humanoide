#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_fixture_collision_e4_1c.sh --check
  ./scripts/vla/audit_vla_fixture_collision_e4_1c.sh --run

Reconstruye offline la secuencia vendor preposition -> forward -> back con el
URDF y sus meshes de colisión. La contrasta con el tablero sólido E4.1 y B0.
No conecta con el robot, no inicia inferencia, no crea publicadores y no mueve.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_fixture_collision_e4_1c.py"
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
  command -v "$tool" >/dev/null || {
    printf 'ERROR: falta herramienta local: %s\n' "$tool" >&2
    exit 1
  }
done
for required in "$ANALYZER" "$EVIDENCE_SCRIPT" "$REPO_ROOT/$SDK_ZIP_REL"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
python3 -m py_compile "$ANALYZER"
python3 -c 'import numpy, yaml'

cd "$REPO_ROOT"
actual_sdk_sha="$(sha256sum "$SDK_ZIP_REL" | awk '{print $1}')"
[[ "$actual_sdk_sha" == "$SDK_ZIP_SHA256" ]] || {
  printf 'ERROR: hash inesperado del URDF/meshes SDK: %s\n' "$actual_sdk_sha" >&2
  exit 1
}

latest_e4_0="$(find "$EVIDENCE_ROOT" -mindepth 2 -maxdepth 2 -type f \
  -path '*_E4.0/actual_result.yaml' -printf '%T@ %h\n' | sort -nr | \
  awk 'NR==1 {$1=""; sub(/^ /, ""); print; exit}')"
latest_e4_1="$(find "$EVIDENCE_ROOT" -mindepth 2 -maxdepth 2 -type f \
  -path '*_E4.1/actual_result.yaml' -printf '%T@ %h\n' | sort -nr | \
  awk 'NR==1 {$1=""; sub(/^ /, ""); print; exit}')"
test -n "$latest_e4_0" || { echo 'ERROR: no se encontró evidencia E4.0' >&2; exit 1; }
test -n "$latest_e4_1" || { echo 'ERROR: no se encontró evidencia E4.1' >&2; exit 1; }
grep -Fq 'status: PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE' \
  "$latest_e4_0/actual_result.yaml" || { echo 'ERROR: E4.0 no es la evidencia auditada' >&2; exit 1; }
grep -Fq 'status: METRIC_FIXTURE_CANDIDATE_RESOLVED_PHYSICAL_GATES_OPEN' \
  "$latest_e4_1/actual_result.yaml" || { echo 'ERROR: E4.1 no es la calibración métrica válida' >&2; exit 1; }
test -s "$latest_e4_0/summary.json"
test -s "$latest_e4_1/results/summary.json"
(
  cd "$latest_e4_0"
  sha256sum -c evidence.sha256 >/dev/null
)
(
  cd "$latest_e4_1"
  sha256sum -c evidence.sha256 >/dev/null
)

printf 'E4.1C_CHECK_OK=local-only,URDF-meshes:vendor,trajectory:E4.0,fixture:E4.1\n'
printf 'E4.1C_SOURCE_E4.0=%s\n' "$latest_e4_0"
printf 'E4.1C_SOURCE_E4.1=%s\n' "$latest_e4_1"
printf 'ROBOT_CONNECTIONS=0; INFERENCE_STARTED=0; PUBLISHERS_CREATED=0; MOVEMENT_COMMANDS=0\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E4.1C)"
mkdir -- "$RUN_DIR/artifacts" "$RUN_DIR/results"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.1C
run_id: $(basename -- "$RUN_DIR")
status: FAIL_BEFORE_COMPLETING_LOCAL_COLLISION_AUDIT
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

cp -- "$ANALYZER" "$RUN_DIR/artifacts/analyze_vla_fixture_collision_e4_1c.py"
cp -- "$latest_e4_0/summary.json" "$RUN_DIR/artifacts/e4_0_summary.json"
cp -- "$latest_e4_0/actual_result.yaml" "$RUN_DIR/artifacts/e4_0_actual_result.yaml"
cp -- "$latest_e4_1/results/summary.json" "$RUN_DIR/artifacts/e4_1_summary.json"
cp -- "$latest_e4_1/actual_result.yaml" "$RUN_DIR/artifacts/e4_1_actual_result.yaml"
unzip -p "$SDK_ZIP_REL" '*/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf' \
  > "$RUN_DIR/artifacts/vendor_cruzr_s2_v1.urdf"
printf '%s\n' "$latest_e4_0" > "$RUN_DIR/e4_0_source_path.txt"
printf '%s\n' "$latest_e4_1" > "$RUN_DIR/e4_1_source_path.txt"
printf '%s  %s\n' "$SDK_ZIP_SHA256" "$SDK_ZIP_REL" > "$RUN_DIR/vendor_sources.sha256"

python3 "$ANALYZER" \
  --urdf "$RUN_DIR/artifacts/vendor_cruzr_s2_v1.urdf" \
  --sdk-urdf-zip "$SDK_ZIP_REL" \
  --e4-0-summary "$RUN_DIR/artifacts/e4_0_summary.json" \
  --e4-1-summary "$RUN_DIR/artifacts/e4_1_summary.json" \
  --output-dir "$RUN_DIR/results" --samples-per-segment 31 \
  2>&1 | tee "$RUN_DIR/analyzer.log"

jq -e '
  .experiment_id == "E4.1C"
  and .status == "SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP"
  and .trajectory_scope.unique_samples == 121
  and .results.triangle_mesh_tabletop_surface_event_count > 0
  and (.results.triangle_mesh_tabletop_surface_links | length) > 0
  and .results.potential_B0_event_count == 0
  and .gates.tabletop_surface_clear_at_triangle_mesh_level == false
  and .gates.physical_test_authorized == false
' "$RUN_DIR/results/summary.json" >/dev/null

triangle_events="$(jq -r '.results.triangle_mesh_tabletop_surface_event_count' "$RUN_DIR/results/summary.json")"
triangle_links="$(jq -r '.results.triangle_mesh_tabletop_surface_links | join(",")' "$RUN_DIR/results/summary.json")"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.1C
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP
mode: local_read_only_no_robot_no_inference_no_publisher
trajectory_samples: 121
triangle_mesh_tabletop_surface_events: $triangle_events
triangle_mesh_tabletop_surface_links: '$triangle_links'
potential_B0_events: 0
box_was_required_or_placed: false
robot_connections: 0
inference_started: false
physical_publisher_created: false
physical_movement_commanded: false
physical_test_authorized: false
recovery_or_stop: NOT_APPLICABLE_LOCAL_ONLY
next_experiment_authorized: FIXTURE_REDESIGN_OR_ACTUAL_CLAMP_GEOMETRY_AUDIT_ONLY
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(
  cd "$RUN_DIR"
  sha256sum -c evidence.sha256 >/dev/null
)

printf 'E4.1C_STATUS=SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP\n'
printf 'TABLETOP_TRIANGLE_EVENTS=%s; LINKS=%s\n' "$triangle_events" "$triangle_links"
printf 'B0_WAS_REQUIRED_OR_PLACED=0\n'
printf 'PHYSICAL_TEST_AUTHORIZED=0\n'
printf 'E4.1C_EVIDENCE_OK=%s\n' "$RUN_DIR"
