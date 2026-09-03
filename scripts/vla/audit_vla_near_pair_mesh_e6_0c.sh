#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_near_pair_mesh_e6_0c.sh --check
  ./scripts/vla/audit_vla_near_pair_mesh_e6_0c.sh --run

Clasifica los 58 pares cercanos E6.0B y comprueba por BVH + SAT de triángulos
los cuatro pares móviles upstream. Todo es local: no usa red, ROS, estado vivo,
publicadores ni movimiento. No modela las abrazaderas pasivas ausentes.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_near_pair_mesh_e6_0c.py"
readonly FK_HELPER="$SCRIPT_DIR/analyze_vla_fixture_collision_e4_1c.py"
readonly PATH_HELPER="$SCRIPT_DIR/analyze_vla_self_collision_e6_0b.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly READY_RUN="${VLA_E6_0A_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093145_E6.0A}"
readonly BROAD_RUN="${VLA_E6_0B_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T094547_E6.0B}"
readonly E4_1C_RUN="${VLA_E4_1C_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093408_E4.1C}"
readonly READY_CONTRACT="$READY_RUN/p14-ready-recovery-contract.json"
readonly BROAD_REPORT="$BROAD_RUN/self-collision-report.json"
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

for tool in cp find jq python3 readlink sha256sum sort tee xargs; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta herramienta: $tool" >&2; exit 1; }
done
for required in "$ANALYZER" "$FK_HELPER" "$PATH_HELPER" "$EVIDENCE_SCRIPT" \
  "$READY_CONTRACT" "$BROAD_REPORT" "$SDK_URDF" "$SDK_ZIP"; do
  test -s "$required" || { echo "ERROR: falta fuente: $required" >&2; exit 1; }
done
for evidence_dir in "$READY_RUN" "$BROAD_RUN" "$E4_1C_RUN"; do
  test -s "$evidence_dir/evidence.sha256" || { echo "ERROR: falta hash: $evidence_dir" >&2; exit 1; }
  (cd "$evidence_dir" && sha256sum -c evidence.sha256 >/dev/null)
done

PYTHONDONTWRITEBYTECODE=1 python3 - "$ANALYZER" "$FK_HELPER" "$PATH_HELPER" <<'PY'
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
print("E6.0C_STATIC_SAFETY_OK=ros:none,network:none,publisher:none,physical-topic:none")
PY

args=(
  --e6-0b-report "$BROAD_REPORT"
  --ready-contract "$READY_CONTRACT"
  --sdk-urdf "$SDK_URDF"
  --sdk-urdf-zip "$SDK_ZIP"
  --fk-helper "$FK_HELPER"
  --path-helper "$PATH_HELPER"
)

if [[ "$MODE" == "check" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0C)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "$ANALYZER" "$FK_HELPER" "$PATH_HELPER" "$RUN_DIR/"
printf '%s\n' "$READY_RUN" "$BROAD_RUN" "$E4_1C_RUN" > "$RUN_DIR/source_runs.txt"
sha256sum "$READY_CONTRACT" "$BROAD_REPORT" "$SDK_URDF" "$SDK_ZIP" \
  "$FK_HELPER" "$PATH_HELPER" > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/$(basename -- "$ANALYZER")" \
  "${args[@]}" --output "$RUN_DIR/near-pair-mesh-report.json" \
  2>&1 | tee "$RUN_DIR/analyzer.log"

jq -e '
  .schema == "cruzr-s2-vla-near-pair-mesh-e6.0c-v1"
  and .trajectory_sample_count == 401
  and .near_pair_partition.total == 58
  and (.near_pair_partition.direct_joint_structural | length) == 40
  and (.near_pair_partition.static_outside_p14 | length) == 12
  and (.near_pair_partition.pgc_not_installed | length) == 2
  and (.near_pair_partition.moving_upstream_exactly_tested | length) == 4
  and (.near_pair_partition.unexpected | length) == 0
  and .exact_mesh_sweep.triangle_sat_self_tests_passed == 4
  and (.exact_mesh_sweep.collision_samples | length) == 0
  and .self_collision_gate_closed == true
  and .physical_authorized == false
  and .robot_state_read == false
  and .network_calls == 0
  and .physical_publishers == 0
  and .physical_movement_commanded == false
' "$RUN_DIR/near-pair-mesh-report.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0C
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_VENDOR_UPSTREAM_NEAR_PAIR_MESH_SWEEP_PHYSICAL_BLOCKED_CLAMP_CLEARANCE_AND_POLICY
mode: local_exact_mesh_no_robot_no_network_no_ros_no_publisher
trajectory_samples: 401
near_pair_partition: direct=40,static=12,pgc=2,exact=4
exact_mesh_intersection_samples: 0
blocking_gates: installed_passive_clamp_collision_geometry,reviewed_runtime_collision_pair_policy,minimum_clearance_with_model_and_calibration_tolerance,physical_validation
self_collision_gate_closed: true
robot_state_read: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
physical_authorized: false
next_safe_work: derive_minimum_clearance_bounds_and_offline_executor_guards
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0C_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0C_PHYSICAL_AUTHORIZED=0\n'
