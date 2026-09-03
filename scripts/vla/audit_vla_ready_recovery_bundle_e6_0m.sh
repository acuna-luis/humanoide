#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_ready_recovery_bundle_e6_0m.sh --check
  ./scripts/vla/audit_vla_ready_recovery_bundle_e6_0m.sh --run

Comprueba localmente el bundle determinista home→ready→home. No conecta al
robot, no instala, no usa ROS, no crea publicadores y no mueve.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_ready_recovery_bundle_e6_0m.py"
readonly READY_SCRIPT="$SCRIPT_DIR/cruzr_vla_ready_pose.sh"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly VENDOR_READY="$REPO_ROOT/cruzrss2_vla_pack-002/codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml"
readonly RECOVERY_XML="$SCRIPT_DIR/runtime/tasks/s2_vla_e6_0_exact_recovery.xml"
readonly RECOVERY_YAML="$SCRIPT_DIR/runtime/meta_move/clamp_s2_vla_e6_0_exact_recovery.yaml"
readonly E4_0_RUN="${VLA_E4_0_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260901T075728_E4.0}"
readonly E6_0A_RUN="${VLA_E6_0A_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T093145_E6.0A}"
readonly E6_0I_RUN="${VLA_E6_0I_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T115129_E6.0I}"
readonly E6_0J_RUN="${VLA_E6_0J_RUN:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T120626_E6.0J}"
readonly FORWARD_YAML="$E4_0_RUN/artifacts/remote_clamp_s2_joints_trajectory.yaml"
readonly READY_CONTRACT="$E6_0A_RUN/p14-ready-recovery-contract.json"
readonly HOME_ENTRY_REPORT="$E6_0I_RUN/home-entry-report.json"
readonly CLAMP_PROXY_REPORT="$E6_0J_RUN/document-proxy-clamp-report.json"

MODE=check
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in cp find jq python3 readlink sha256sum sort tee xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
for required in "$ANALYZER" "$READY_SCRIPT" "$EVIDENCE_SCRIPT" \
  "$VENDOR_READY" "$FORWARD_YAML" "$RECOVERY_XML" "$RECOVERY_YAML" \
  "$READY_CONTRACT" "$HOME_ENTRY_REPORT" "$CLAMP_PROXY_REPORT"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
for evidence_dir in "$E4_0_RUN" "$E6_0A_RUN" "$E6_0I_RUN" "$E6_0J_RUN"; do
  (cd "$evidence_dir" && sha256sum -c evidence.sha256 >/dev/null)
done

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$ANALYZER"
"$READY_SCRIPT" --check >/dev/null
"$READY_SCRIPT" --dry-plan >/dev/null
for blocked_mode in --install --run-ready --run-recover --stop; do
  set +e
  "$READY_SCRIPT" "$blocked_mode" >/dev/null 2>&1
  rc=$?
  set -e
  [[ "$rc" == 3 ]] || {
    printf 'ERROR: %s debía bloquear antes de acceso físico (rc=%s)\n' "$blocked_mode" "$rc" >&2
    exit 1
  }
done

args=(
  --vendor-ready "$VENDOR_READY"
  --forward-yaml "$FORWARD_YAML"
  --recovery-xml "$RECOVERY_XML"
  --recovery-yaml "$RECOVERY_YAML"
  --ready-contract "$READY_CONTRACT"
  --home-entry-report "$HOME_ENTRY_REPORT"
  --clamp-proxy-report "$CLAMP_PROXY_REPORT"
)
if [[ "$MODE" == check ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${args[@]}"
  exit 0
fi

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0M)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "$ANALYZER" "$READY_SCRIPT" "$VENDOR_READY" "$FORWARD_YAML" \
  "$RECOVERY_XML" "$RECOVERY_YAML" "$RUN_DIR/"
printf '%s\n' "$E4_0_RUN" "$E6_0A_RUN" "$E6_0I_RUN" "$E6_0J_RUN" \
  > "$RUN_DIR/source_runs.txt"
sha256sum "$ANALYZER" "$READY_SCRIPT" "$VENDOR_READY" "$FORWARD_YAML" \
  "$RECOVERY_XML" "$RECOVERY_YAML" "$READY_CONTRACT" \
  "$HOME_ENTRY_REPORT" "$CLAMP_PROXY_REPORT" > "$RUN_DIR/source_hashes.sha256"
PYTHONDONTWRITEBYTECODE=1 python3 "$ANALYZER" "${args[@]}" \
  --output "$RUN_DIR/ready-recovery-bundle.json" \
  2>&1 | tee "$RUN_DIR/bundle-audit.log"

jq -e '
  .schema == "cruzr-s2-vla-ready-recovery-bundle-e6.0m-v1"
  and .status == "PASS_EXACT_RECOVERY_BUNDLE_LOCAL_ACTIVE_MODES_BLOCKED_PENDING_PHYSICAL_VALIDATION"
  and .recovery.named_segment_is_exact_reverse == true
  and .recovery.final_parallel_returns_head_waist_and_both_arms_to_numeric_home == true
  and .sampled_vendor_model_and_document_proxy_path_covered == true
  and .active_modes_implemented == false
  and .installed_on_robot == false
  and .physically_validated == false
  and .physical_execution_authorized == false
  and .physical_publisher_count == 0
  and .robot_state_read == false
  and .network_calls == 0
  and .physical_movement_commanded == false
' "$RUN_DIR/ready-recovery-bundle.json" >/dev/null

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0M
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_EXACT_RECOVERY_BUNDLE_LOCAL_ACTIVE_MODES_BLOCKED_PENDING_PHYSICAL_VALIDATION
mode: local_artifact_validation_no_robot_no_network_no_ros_no_publisher
exact_named_reverse: true
full_sequence: home_to_staging_to_A_to_B_to_A_to_staging_to_home
active_modes_implemented: false
installed_on_robot: false
physically_validated: false
physical_execution_authorized: false
physical_publishers: 0
robot_state_read: false
network_calls: 0
physical_movement_commanded: false
next_work: SUPERVISED_DETERMINISTIC_READY_RECOVERY_VALIDATION_BEFORE_CHECKPOINT
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0M_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E6.0M_PHYSICAL_AUTHORIZED=0\n'
