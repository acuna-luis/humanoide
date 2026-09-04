#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_active_launcher_e6_0y.sh --check
  ./scripts/vla/audit_vla_active_launcher_e6_0y.sh --run

Prueba offline gates, grant efímero y estructura del lanzador E6.0Y. No se
conecta al robot, no importa ROS y no crea publicadores.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly TEST="$SCRIPT_DIR/test_vla_active_launcher_e6_0y.py"
readonly RUNTIME="$SCRIPT_DIR/runtime"
readonly LAUNCHER="$SCRIPT_DIR/run_vla_canary_physical_e6_0y.sh"
readonly NEW_EVIDENCE="$SCRIPT_DIR/new_vla_evidence_run.sh"
MODE=""
while (($#)); do
  case "$1" in
    --check|--run) MODE="$1"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; exit 2 ;;
  esac
done
[[ -n "$MODE" ]] || { printf 'ERROR: falta modo\n' >&2; exit 2; }
for required in "$TEST" "$LAUNCHER" "$NEW_EVIDENCE"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
output="$(python3 "$TEST" --runtime-dir "$RUNTIME" --launcher "$LAUNCHER")"
printf '%s\n' "$output"
grep -Fq 'E6.0Y_FAILED_EXPECTATIONS=0' <<<"$output"
grep -Fq 'E6.0Y_ROBOT_ACCESSED=0' <<<"$output"
[[ "$MODE" == --run ]] || { printf 'E6.0Y_CHECK_OK=offline-only\n'; exit 0; }
run_dir="$("$NEW_EVIDENCE" --experiment E6.0Y-OFFLINE)"
printf '%s\n' "$output" > "$run_dir/offline-test.log"
cp -- "$SCRIPT_PATH" "$TEST" "$LAUNCHER" "$run_dir/"
sha256sum "$SCRIPT_PATH" "$TEST" "$LAUNCHER" "$RUNTIME"/*.py "$RUNTIME"/*.json \
  > "$run_dir/source_hashes.sha256"
cat > "$run_dir/actual_result.yaml" <<EOF
experiment_id: E6.0Y-OFFLINE
run_id: $(basename -- "$run_dir")
status: PASS_ACTIVE_LAUNCHER_FAIL_CLOSED_OFFLINE
robot_accessed: false
ros_imported: false
physical_publisher_created: false
physical_movement_commanded: false
active_path_default: disabled
next_gate: RUN_SPECIFIC_READY_MOVEMENT_AUTHORIZATION
EOF
(
  cd "$run_dir"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$run_dir/evidence.sha256"
(cd "$run_dir" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0Y_OFFLINE_EVIDENCE_OK=%s\n' "$run_dir"
