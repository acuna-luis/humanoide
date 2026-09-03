#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_document_proxy_clamp_e6_0j.sh --check
  ./scripts/vla/audit_vla_document_proxy_clamp_e6_0j.sh --run

Audita offline la trayectoria NO_BOX_READY completa con un proxy conservador
documental del clamp. No conecta al robot, no usa ROS, no crea publicadores y
no envía movimiento.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_document_proxy_clamp_e6_0j.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly PROXY_CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_document_proxy_clamp_e6_0j.json"
readonly OFFICIAL_CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_official_geometry_contract_e4_1f.yaml"
readonly E6A="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093145_E6.0A"
readonly E6I="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T115129_E6.0I"
readonly E4C="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093408_E4.1C"
readonly READY="$E6A/p14-ready-recovery-contract.json"
readonly ACTUATOR_STATE="$E6I/actuator-state.json"
readonly URDF="$E4C/artifacts/vendor_cruzr_s2_v1.urdf"
readonly URDF_ZIP="$REPO_ROOT/Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip"
readonly FK_HELPER="$SCRIPT_DIR/analyze_vla_fixture_collision_e4_1c.py"
readonly PATH_HELPER="$SCRIPT_DIR/analyze_vla_self_collision_e6_0b.py"
readonly MESH_HELPER="$SCRIPT_DIR/analyze_vla_near_pair_mesh_e6_0c.py"
readonly HOME_HELPER="$SCRIPT_DIR/analyze_vla_home_entry_e6_0i.py"

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
for source in "$ANALYZER" "$EVIDENCE_SCRIPT" "$PROXY_CONTRACT" "$OFFICIAL_CONTRACT" \
  "$READY" "$ACTUATOR_STATE" "$URDF" "$URDF_ZIP" "$FK_HELPER" "$PATH_HELPER" \
  "$MESH_HELPER" "$HOME_HELPER"; do
  test -s "$source" || { echo "ERROR: falta fuente: $source" >&2; exit 1; }
done
for evidence in "$E6A" "$E6I" "$E4C"; do
  (cd "$evidence" && sha256sum -c evidence.sha256 >/dev/null)
done
jq -e '
  .schema == "cruzr-s2-document-proxy-clamp/e6.0j-v1"
  and .decision.scope == "offline_no_box_self_collision_audit_only"
  and .limitations.authorizes_physical_movement == false
' "$PROXY_CONTRACT" >/dev/null

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
assert "/mc/sdk/robot_command" not in source
print("E6.0J_STATIC_SAFETY_OK=ros:none,network:none,publisher:none,physical-topic:none")
PY

analyzer_args=(
  --proxy-contract "$PROXY_CONTRACT"
  --official-contract "$OFFICIAL_CONTRACT"
  --actuator-state "$ACTUATOR_STATE"
  --ready-contract "$READY"
  --sdk-urdf "$URDF"
  --sdk-urdf-zip "$URDF_ZIP"
  --fk-helper "$FK_HELPER"
  --path-helper "$PATH_HELPER"
  --mesh-helper "$MESH_HELPER"
  --home-helper "$HOME_HELPER"
)

if [[ "$MODE" == "check" ]]; then
  printf 'E6.0J_CHECK_OK=local-only,no-robot,no-network,no-ros,no-publisher,no-movement\n'
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0J)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    local failure_status="FAIL_SAFE_BEFORE_DOCUMENT_PROXY_AUDIT_COMPLETION"
    local exact_intersections="unknown"
    if [[ -s "$RUN_DIR/document-proxy-clamp-report.json" ]]; then
      failure_status="$(jq -r '.status // "FAIL_SAFE_DOCUMENT_PROXY_AUDIT"' "$RUN_DIR/document-proxy-clamp-report.json")"
      exact_intersections="$(jq -r '.collision_audit.exact_intersection_count // "unknown"' "$RUN_DIR/document-proxy-clamp-report.json")"
    fi
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0J
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: $failure_status
mode: local_only_no_robot_no_network_no_ros_no_publisher
robot_state_read: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
physical_authorized: false
exact_intersections: $exact_intersections
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

cp -- "$ANALYZER" "$RUN_DIR/analyze_vla_document_proxy_clamp_e6_0j.py"
cp -- "$PROXY_CONTRACT" "$RUN_DIR/document-proxy-contract.json"
printf '%s\n' "$E6A" "$E6I" "$E4C" > "$RUN_DIR/source_runs.txt"
sha256sum "$OFFICIAL_CONTRACT" "$READY" "$ACTUATOR_STATE" "$URDF" "$URDF_ZIP" \
  "$FK_HELPER" "$PATH_HELPER" "$MESH_HELPER" "$HOME_HELPER" \
  > "$RUN_DIR/source_hashes.sha256"

PYTHONDONTWRITEBYTECODE=1 python3 "$RUN_DIR/analyze_vla_document_proxy_clamp_e6_0j.py" \
  "${analyzer_args[@]}" --output "$RUN_DIR/document-proxy-clamp-report.json" \
  2>&1 | tee "$RUN_DIR/analyzer.log"

jq -e '
  .schema == "cruzr-s2-vla-document-proxy-clamp-e6.0j-v1"
  and .status == "PASS_DOCUMENT_PROXY_SAMPLED_SWEEP_ASSUMPTION_ACCEPTED_PHYSICAL_NOT_CERTIFIED"
  and .trajectory.sample_count == 1201
  and .trajectory.joint_limit_violations == []
  and .collision_audit.exact_intersection_count == 0
  and .interpretation.sampled_document_proxy_clear == true
  and .interpretation.installed_clamp_geometry_certified == false
  and .robot_state_read == false
  and .network_calls == 0
  and .physical_publishers == 0
  and .physical_movement_commanded == false
  and .physical_authorized == false
' "$RUN_DIR/document-proxy-clamp-report.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0J
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_DOCUMENT_PROXY_SAMPLED_SWEEP_ASSUMPTION_ACCEPTED_PHYSICAL_NOT_CERTIFIED
mode: local_document_proxy_sweep_no_robot_no_network_no_ros_no_publisher
owner_assumption: use_documented_dimensions_without_manual_measurement
trajectory_samples: 1201
exact_intersections: 0
robot_state_read: false
network_calls: 0
physical_publishers: 0
physical_movement_commanded: false
physical_authorized: false
next_work: CONSUME_PROXY_RESULT_IN_E6_0_READINESS_WITH_DYNAMICS_RECOVERY_EXECUTOR_STILL_BLOCKED
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0J_EVIDENCE_OK=%s\n' "$RUN_DIR"
