#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_self_collision_e6_0b.sh --check
  ./scripts/vla/audit_vla_self_collision_e6_0b.sh --run

Barrido FK/OBB completamente local de la entrada y recuperación P14. No usa
red, ROS, estado vivo, publicadores ni movimiento. Un PASS es sólo broad phase
upstream; el gate físico queda cerrado sin ACM/SRDF y geometría clamp real.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_self_collision_e6_0b.py"
readonly FK_HELPER="$SCRIPT_DIR/analyze_vla_fixture_collision_e4_1c.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly READY_RUN="${VLA_E6_0A_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093145_E6.0A}"
readonly E4_1C_RUN="${VLA_E4_1C_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093408_E4.1C}"
readonly READY_CONTRACT="$READY_RUN/p14-ready-recovery-contract.json"
readonly SDK_URDF="$E4_1C_RUN/artifacts/vendor_cruzr_s2_v1.urdf"
readonly SDK_ZIP="$REPO_ROOT/Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip"

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in find jq python3 readlink sha256sum sort tee xargs; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta herramienta: $tool" >&2; exit 1; }
done
for required in "$ANALYZER" "$FK_HELPER" "$EVIDENCE_SCRIPT" "$READY_CONTRACT" "$SDK_URDF" "$SDK_ZIP"; do
  test -s "$required" || { echo "ERROR: falta fuente: $required" >&2; exit 1; }
done
for evidence_dir in "$READY_RUN" "$E4_1C_RUN"; do
  test -s "$evidence_dir/evidence.sha256" || { echo "ERROR: falta hash de evidencia: $evidence_dir" >&2; exit 1; }
  (cd "$evidence_dir" && sha256sum -c evidence.sha256 >/dev/null)
done

PYTHONDONTWRITEBYTECODE=1 python3 - "$ANALYZER" "$FK_HELPER" <<'PY'
import ast
import pathlib
import sys
for raw in sys.argv[1:]:
    path = pathlib.Path(raw)
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
    assert "/mc/sdk/robot_command" not in source
print("E6.0B_STATIC_SAFETY_OK=ros:none,network:none,publisher:none,physical-topic:none")
PY

args=(
  --ready-contract "$READY_CONTRACT"
  --sdk-urdf "$SDK_URDF"
  --sdk-urdf-zip "$SDK_ZIP"
  --fk-helper "$FK_HELPER"
)

if [[ "$MODE" == "check" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0B)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "$ANALYZER" "$FK_HELPER" "$RUN_DIR/"
printf '%s\n' "$READY_RUN" "$E4_1C_RUN" > "$RUN_DIR/source_runs.txt"
sha256sum "$READY_CONTRACT" "$SDK_URDF" "$SDK_ZIP" "$FK_HELPER" \
  > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/$(basename -- "$ANALYZER")" \
  "${args[@]}" --output "$RUN_DIR/self-collision-report.json" \
  2>&1 | tee "$RUN_DIR/analyzer.log"

jq -e '
  .schema == "cruzr-s2-vla-self-collision-e6.0b-v1"
  and .trajectory.sample_count == 401
  and (.trajectory.joint_limit_violations | length) == 0
  and (.collision_model.far_overlapping_pairs_upstream_without_pgc_finger | length) == 0
  and .e6_0_self_collision_gate_closed == true
  and .physical_authorized == false
  and .robot_state_read == false
  and .network_calls == 0
  and .physical_publishers == 0
  and .physical_movement_commanded == false
' "$RUN_DIR/self-collision-report.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0B
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_UPSTREAM_FAR_LINK_OBB_SWEEP_PARTIAL_SELF_COLLISION_BLOCKED_NO_ACM_OR_CLAMP_GEOMETRY
mode: local_fk_obb_no_robot_no_network_no_ros_no_publisher
trajectory_samples: 401
far_upstream_obb_overlapping_pairs: 0
joint_limit_violations: 0
blocking_gates: allowed_collision_matrix_or_srdf,installed_clamp_collision_geometry,physical_clearance_and_dynamics
robot_state_read: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
physical_authorized: false
next_safe_work: derive_reviewable_ACM_and_obtain_installed_clamp_collision_geometry
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0B_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0B_PHYSICAL_AUTHORIZED=0\n'
