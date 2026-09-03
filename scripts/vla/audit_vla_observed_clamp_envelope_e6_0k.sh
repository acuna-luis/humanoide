#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_observed_clamp_envelope_e6_0k.sh --check
  ./scripts/vla/audit_vla_observed_clamp_envelope_e6_0k.sh --run

Comprueba localmente que la envolvente observada del clamp cabe dentro del
proxy E6.0J ya barrido. No conecta al robot ni envía movimiento.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_observed_clamp_envelope_e6_0k.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly OBSERVED="$SCRIPT_DIR/runtime/cruzr_s2_observed_clamp_envelope_e6_0k.json"
readonly E6J="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T120626_E6.0J"
readonly PROXY_REPORT="$E6J/document-proxy-clamp-report.json"

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
for source in "$ANALYZER" "$EVIDENCE_SCRIPT" "$OBSERVED" "$PROXY_REPORT"; do
  test -s "$source" || { echo "ERROR: falta fuente: $source" >&2; exit 1; }
done
(cd "$E6J" && sha256sum -c evidence.sha256 >/dev/null)

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
assert not imports & {"rclpy", "rosa", "socket", "requests", "subprocess", "urllib"}
assert not names & {"create_client", "create_publisher", "publish", "send_goal_async"}
print("E6.0K_STATIC_SAFETY_OK=ros:none,network:none,publisher:none")
PY

args=(--observed-contract "$OBSERVED" --document-proxy-report "$PROXY_REPORT")
if [[ "$MODE" == "check" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0K)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "$ANALYZER" "$RUN_DIR/"
cp -- "$OBSERVED" "$RUN_DIR/observed-clamp-envelope.json"
printf '%s\n' "$E6J" > "$RUN_DIR/source_runs.txt"
sha256sum "$PROXY_REPORT" "$E6J/evidence.sha256" > "$RUN_DIR/source_hashes.sha256"

PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/$(basename -- "$ANALYZER")" \
  "${args[@]}" --output "$RUN_DIR/observed-clamp-containment-report.json" \
  2>&1 | tee "$RUN_DIR/analyzer.log"

jq -e '
  .status == "PASS_OBSERVED_CLAMP_ENVELOPE_CONTAINED_IN_E6_0J_PROXY"
  and ([.containment[].contained] | all)
  and .proof.e6_0j_sample_count == 1201
  and .proof.e6_0j_exact_intersections == 0
  and .physical_authorized == false
  and .physical_publishers == 0
  and .physical_movement_commanded == false
' "$RUN_DIR/observed-clamp-containment-report.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0K
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_OBSERVED_CLAMP_ENVELOPE_CONTAINED_IN_E6_0J_PROXY
mode: local_containment_proof_no_robot_no_network_no_ros_no_publisher
observed_raw_xyz_m: 0.120,0.052,0.105
conservative_xyz_m: 0.140,0.072,0.125
document_proxy_xyz_m: 0.145,0.142,0.330
contained_both_sides_under_symmetry_assumption: true
physical_publishers: 0
physical_movement_commanded: false
physical_authorized: false
next_work: KEEP_REMAINING_RECOVERY_EXECUTOR_ACCELERATION_TEMPORAL_GATES_CLOSED
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0K_EVIDENCE_OK=%s\n' "$RUN_DIR"
