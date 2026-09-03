#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_clearance_guards_e6_0d.sh --check
  ./scripts/vla/audit_vla_clearance_guards_e6_0d.sh --run

Mide localmente la holgura muestreada de las cuatro parejas E6.0C y deriva un
contrato de guards deshabilitado. No usa red, ROS, estado vivo, publicadores ni
movimiento. No certifica trayecto continuo ni modela las abrazaderas pasivas.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_clearance_guards_e6_0d.py"
readonly FK_HELPER="$SCRIPT_DIR/analyze_vla_fixture_collision_e4_1c.py"
readonly PATH_HELPER="$SCRIPT_DIR/analyze_vla_self_collision_e6_0b.py"
readonly MESH_HELPER="$SCRIPT_DIR/analyze_vla_near_pair_mesh_e6_0c.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_profile.json"
readonly READY_RUN="${VLA_E6_0A_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093145_E6.0A}"
readonly MESH_RUN="${VLA_E6_0C_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T095600_E6.0C}"
readonly E4_1C_RUN="${VLA_E4_1C_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093408_E4.1C}"
readonly READY_CONTRACT="$READY_RUN/p14-ready-recovery-contract.json"
readonly MESH_REPORT="$MESH_RUN/near-pair-mesh-report.json"
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
for required in "$ANALYZER" "$FK_HELPER" "$PATH_HELPER" "$MESH_HELPER" \
  "$EVIDENCE_SCRIPT" "$PROFILE" "$READY_CONTRACT" "$MESH_REPORT" "$SDK_URDF" "$SDK_ZIP"; do
  test -s "$required" || { echo "ERROR: falta fuente: $required" >&2; exit 1; }
done
for evidence_dir in "$READY_RUN" "$MESH_RUN" "$E4_1C_RUN"; do
  test -s "$evidence_dir/evidence.sha256" || { echo "ERROR: falta hash: $evidence_dir" >&2; exit 1; }
  (cd "$evidence_dir" && sha256sum -c evidence.sha256 >/dev/null)
done

PYTHONDONTWRITEBYTECODE=1 python3 - "$ANALYZER" "$FK_HELPER" "$PATH_HELPER" "$MESH_HELPER" <<'PY'
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
print("E6.0D_STATIC_SAFETY_OK=ros:none,network:none,publisher:none,physical-topic:none")
PY

args=(
  --e6-0c-report "$MESH_REPORT"
  --ready-contract "$READY_CONTRACT"
  --profile "$PROFILE"
  --sdk-urdf "$SDK_URDF"
  --sdk-urdf-zip "$SDK_ZIP"
  --fk-helper "$FK_HELPER"
  --path-helper "$PATH_HELPER"
  --mesh-helper "$MESH_HELPER"
)

if [[ "$MODE" == "check" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0D)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "$ANALYZER" "$FK_HELPER" "$PATH_HELPER" "$MESH_HELPER" "$RUN_DIR/"
printf '%s\n' "$READY_RUN" "$MESH_RUN" "$E4_1C_RUN" > "$RUN_DIR/source_runs.txt"
sha256sum "$READY_CONTRACT" "$MESH_REPORT" "$PROFILE" "$SDK_URDF" "$SDK_ZIP" \
  "$FK_HELPER" "$PATH_HELPER" "$MESH_HELPER" > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/$(basename -- "$ANALYZER")" \
  "${args[@]}" --output "$RUN_DIR/clearance-report.json" \
  --guard-output "$RUN_DIR/offline-executor-guard-contract.json" \
  2>&1 | tee "$RUN_DIR/analyzer.log"

jq -e '
  .schema == "cruzr-s2-vla-clearance-guards-e6.0d-v1"
  and .status == "PASS_VENDOR_MESH_SAMPLED_CLEARANCE_QUANTIFIED_PHYSICAL_BLOCKED"
  and .trajectory_sample_count == 401
  and .unique_state_count_computed == 201
  and .triangle_distance_self_tests_passed == 4
  and .triangle_distance_randomized_reference_tests_passed == 300
  and (.pairs | length) == 4
  and ([.pairs[].zero_or_epsilon_clearance_sample_count] | add) == 0
  and .overall_minimum_sampled_vendor_mesh_clearance_m > .epsilon_m
  and .interpretation.continuous_path_certified == false
  and .interpretation.physical_clearance_certified == false
  and .guard_contract.physical_execution_enabled == false
  and .guard_contract.maximum_acceleration_rad_s2 == null
  and .physical_authorized == false
  and .robot_state_read == false
  and .network_calls == 0
  and .physical_publishers == 0
  and .physical_movement_commanded == false
' "$RUN_DIR/clearance-report.json" >/dev/null
jq -e '
  .schema == "cruzr-s2-vla-offline-executor-guard-contract-e6.0d-v1"
  and .state == "SPECIFICATION_ONLY_FAIL_CLOSED"
  and .physical_execution_enabled == false
  and .publisher_or_command_topic == null
  and .maximum_canary_point_count == 1
  and .maximum_acceleration_rad_s2 == null
  and .continuous_path_certified == false
  and .installed_passive_clamp_geometry_present == false
' "$RUN_DIR/offline-executor-guard-contract.json" >/dev/null

minimum="$(jq -r '.overall_minimum_sampled_vendor_mesh_clearance_m' "$RUN_DIR/clearance-report.json")"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0D
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_VENDOR_MESH_SAMPLED_CLEARANCE_QUANTIFIED_PHYSICAL_BLOCKED
mode: local_exact_distance_and_guard_derivation_no_robot_no_network_no_ros_no_publisher
trajectory_samples: 401
unique_states_computed: 201
monitored_pair_count: 4
overall_minimum_sampled_vendor_mesh_clearance_m: $minimum
continuous_path_certified: false
physical_clearance_certified: false
installed_passive_clamps_modeled: false
guard_contract_state: SPECIFICATION_ONLY_FAIL_CLOSED
maximum_acceleration_rad_s2: null
physical_authorized: false
robot_state_read: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
next_safe_work: COMPLETE_MISSING_CLAMP_TOLERANCE_DYNAMICS_AND_IMPLEMENT_OFFLINE_GUARD_EVALUATOR
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0D_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0D_PHYSICAL_AUTHORIZED=0\n'
