#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_home_entry_e6_0i.sh --check
  ./scripts/vla/audit_vla_home_entry_e6_0i.sh --run

Captura una muestra articular fresca de sólo lectura y cubre offline el tramo
omitido measured-home <-> preposición vendor. No llama acciones, no crea
publicadores, no inicia VLA y no mueve el robot.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_home_entry_e6_0i.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly RECOVERY_SCRIPT="$REPO_ROOT/scripts/cruzr_recover_to_home.sh"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly MOTION_CONTAINER="walker-motion.manipulation_robot_app-1"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly E6A="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093145_E6.0A"
readonly E6B="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T094547_E6.0B"
readonly E6C="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T095600_E6.0C"
readonly E6D="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T101730_E6.0D"
readonly E4C="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093408_E4.1C"
readonly READY="$E6A/p14-ready-recovery-contract.json"
readonly BROAD="$E6B/self-collision-report.json"
readonly NARROW="$E6C/near-pair-mesh-report.json"
readonly CLEARANCE="$E6D/clearance-report.json"
readonly URDF="$E4C/artifacts/vendor_cruzr_s2_v1.urdf"
readonly URDF_ZIP="$REPO_ROOT/Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip"
readonly FK_HELPER="$SCRIPT_DIR/analyze_vla_fixture_collision_e4_1c.py"
readonly PATH_HELPER="$SCRIPT_DIR/analyze_vla_self_collision_e6_0b.py"
readonly MESH_HELPER="$SCRIPT_DIR/analyze_vla_near_pair_mesh_e6_0c.py"
readonly DISTANCE_HELPER="$SCRIPT_DIR/analyze_vla_clearance_guards_e6_0d.py"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in cp find jq nc python3 readlink setsid sha256sum sort ssh tee xargs; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta herramienta: $tool" >&2; exit 1; }
done
for source in "$ANALYZER" "$EVIDENCE_SCRIPT" "$SHADOW_SCRIPT" "$RECOVERY_SCRIPT" \
  "$READY" "$BROAD" "$NARROW" "$CLEARANCE" "$URDF" "$URDF_ZIP" \
  "$FK_HELPER" "$PATH_HELPER" "$MESH_HELPER" "$DISTANCE_HELPER"; do
  test -s "$source" || { echo "ERROR: falta fuente: $source" >&2; exit 1; }
done
for evidence in "$E6A" "$E6B" "$E6C" "$E6D" "$E4C"; do
  (cd "$evidence" && sha256sum -c evidence.sha256 >/dev/null)
done

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
print("E6.0I_STATIC_SAFETY_OK=ros:none,network:none,publisher:none,physical-topic:none")
PY

printf 'E6.0I_SOURCES_OK=E6.0A,E6.0B,E6.0C,E6.0D,E4.1C\n'
[[ "$MODE" == "run" ]] || {
  printf 'E6.0I_CHECK_OK=no-robot,no-publisher,no-movement\n'
  exit 0
}

shadow="$($SHADOW_SCRIPT --status)"
grep -Fq 'INFERENCE_CONTAINER=exited' <<<"$shadow"
grep -Fq 'CONTROL_CONTAINER=exited' <<<"$shadow"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$shadow"

preflight="$($RECOVERY_SCRIPT --check)"
grep -Fq 'MEASURED_HOME=1' <<<"$preflight"
grep -Fq 'RECOVERY_ROUTE=already-home,no-motion' <<<"$preflight"
grep -Fq 'RECOVERY_CHECK_OK: no se cambió ningún estado ni se movió el robot.' <<<"$preflight"

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0I)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0I
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: FAIL_SAFE_BEFORE_HOME_ENTRY_AUDIT_COMPLETION
mode: fresh_state_read_then_local_analysis_no_publisher_no_movement
physical_publishers: 0
physical_movement_commanded: false
physical_authorized: false
recovery_or_stop: NOT_APPLICABLE_NO_COMMAND_PATH
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

printf '%s\n' "$shadow" > "$RUN_DIR/vla-status.log"
printf '%s\n' "$preflight" > "$RUN_DIR/home-preflight.log"

ssh_options=(
  -o ConnectTimeout=10
  -o PreferredAuthentications=password
  -o PubkeyAuthentication=no
  -o StrictHostKeyChecking=accept-new
)
CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" setsid -w ssh "${ssh_options[@]}" \
  "$ROBOT_USER@$MOTION_HOST" \
  "docker exec '$MOTION_CONTAINER' bash -lc 'source /opt/walker/setup.bash; timeout 8 rosa topic echo --once --no-daemon /mc/actuator_state'" \
  > "$RUN_DIR/actuator-state.json"
jq -e '.act_item | type == "array" and length >= 20' "$RUN_DIR/actuator-state.json" >/dev/null

cp -- "$ANALYZER" "$RUN_DIR/"
printf '%s\n' "$E6A" "$E6B" "$E6C" "$E6D" "$E4C" > "$RUN_DIR/source_runs.txt"
args=(
  --actuator-state "$RUN_DIR/actuator-state.json"
  --ready-contract "$READY"
  --e6-0b-report "$BROAD"
  --e6-0c-report "$NARROW"
  --e6-0d-report "$CLEARANCE"
  --sdk-urdf "$URDF"
  --sdk-urdf-zip "$URDF_ZIP"
  --fk-helper "$FK_HELPER"
  --path-helper "$PATH_HELPER"
  --mesh-helper "$MESH_HELPER"
  --distance-helper "$DISTANCE_HELPER"
  --output "$RUN_DIR/home-entry-report.json"
)
PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${args[@]}" 2>&1 | tee "$RUN_DIR/analyzer.log"

jq -e '
  .schema == "cruzr-s2-vla-home-entry-e6.0i-v1"
  and .fresh_home_snapshot.axis_count == 20
  and .trajectory.entry_sample_count == 101
  and (.trajectory.joint_limit_violations | length) == 0
  and (.broad_phase.new_near_pairs_vs_e6_0b | length) == 0
  and (.broad_phase.new_far_upstream_pairs_vs_e6_0b | length)
      == (.broad_phase.new_far_pairs_exactly_tested | length)
  and (.broad_phase.new_far_pairs_unresolved | length) == 0
  and (.exact_mesh.intersection_samples | length) == 0
  and .complete_vendor_model_path_covered == true
  and .physical_publishers == 0
  and .physical_movement_commanded == false
  and .physical_authorized == false
' "$RUN_DIR/home-entry-report.json" >/dev/null

minimum="$(jq -r '.exact_mesh.minimum_complete_sampled_vendor_clearance_m' "$RUN_DIR/home-entry-report.json")"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0I
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_HOME_STAGING_VENDOR_MODEL_SWEEP_PHYSICAL_BLOCKED_NO_CLAMP_OR_DYNAMICS
mode: fresh_state_read_then_local_analysis_no_publisher_no_movement
fresh_home_axes: 20
entry_samples: 101
complete_composite_samples: 601
new_near_pairs: 0
new_far_upstream_pairs: $(jq -r '.broad_phase.new_far_upstream_pairs_vs_e6_0b | length' "$RUN_DIR/home-entry-report.json")
new_far_pairs_exactly_tested: $(jq -r '.broad_phase.new_far_pairs_exactly_tested | length' "$RUN_DIR/home-entry-report.json")
exact_intersection_samples: 0
minimum_complete_sampled_vendor_clearance_m: $minimum
physical_publishers: 0
physical_movement_commanded: false
physical_authorized: false
next_gate: CLAMP_GEOMETRY_DYNAMICS_TEMPORAL_EXECUTOR_AND_PHYSICAL_VALIDATION
EOF
sha256sum "$ANALYZER" "$READY" "$BROAD" "$NARROW" "$CLEARANCE" \
  "$URDF" "$URDF_ZIP" "$FK_HELPER" "$PATH_HELPER" "$MESH_HELPER" \
  "$DISTANCE_HELPER" > "$RUN_DIR/source_hashes.sha256"
(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0I_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0I_PHYSICAL_AUTHORIZED=0\n'
