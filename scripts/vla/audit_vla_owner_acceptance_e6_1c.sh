#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_owner_acceptance_e6_1c.sh --check
  ./scripts/vla/audit_vla_owner_acceptance_e6_1c.sh --run

Valida y registra localmente la aceptación del propietario para los límites
provisionales de la transición E6.1C READY<->ENTRY. No conecta al robot, no
usa ROS, no instala, no publica y no autoriza una ejecución física concreta.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly ACCEPTANCE="$SCRIPT_DIR/runtime/cruzr_s2_vla_owner_acceptance_e6_1c.json"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_ready_entry_transition_e6_1c.json"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"

MODE=check
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in awk cp date find jq readlink sha256sum sort xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
for required in "$ACCEPTANCE" "$CONTRACT" "$EVIDENCE_SCRIPT"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done

contract_sha="$(sha256sum "$CONTRACT" | awk '{print $1}')"
jq -e --arg contract_sha "$contract_sha" '
  .schema == "cruzr-s2-vla-owner-acceptance-e6.1c-v1"
  and .experiment_id == "E6.1C"
  and .accepted_by_role == "project_owner"
  and .acceptance_source == "explicit_confirmation_in_project_session"
  and .scope == "E6.1C_READY_ENTRY_LOCKED_AXES_ONLY"
  and .transition_contract_sha256 == $contract_sha
  and .commanded_joint_groups == ["head","lifter","waist"]
  and .arm_joints_commanded == 0
  and .duration_seconds_each_direction == 12.0
  and .maximum_velocity_rad_s == 0.15
  and .maximum_acceleration_rad_s2 == 0.5
  and .runtime_law_equivalence_demonstrated == false
  and .manufacturer_certified == false
  and .owner_accepted == true
  and .acceptance_is_entry_authorization == false
  and .acceptance_is_publisher_authorization == false
  and .requires_run_specific_fresh_preflight == true
  and .requires_run_specific_physical_confirmation == true
  and .physical_execution_authorized == false
' "$ACCEPTANCE" >/dev/null

printf 'E6.1C_OWNER_ACCEPTANCE_VALID=1\n'
printf 'E6.1C_SCOPE=READY_ENTRY_LOCKED_AXES_ONLY,arms-commanded:0\n'
printf 'E6.1C_LIMITS=velocity:0.15rad_s,acceleration:0.5rad_s2,vendor-certified:no\n'
printf 'E6.1C_ACCEPTANCE_IS_ENTRY_AUTHORIZATION=0\n'
printf 'E6.1C_ACCEPTANCE_IS_PUBLISHER_AUTHORIZATION=0\n'
[[ "$MODE" == run ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.1C-ACCEPTANCE)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "$SCRIPT_PATH" "$ACCEPTANCE" "$CONTRACT" "$RUN_DIR/"
sha256sum "$SCRIPT_PATH" "$ACCEPTANCE" "$CONTRACT" > "$RUN_DIR/source_hashes.sha256"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.1C-ACCEPTANCE
run_id: $(basename -- "$RUN_DIR")
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_OWNER_ACCEPTED_PROVISIONAL_E6_1C_LIMITS
scope: E6.1C_READY_ENTRY_LOCKED_AXES_ONLY
maximum_velocity_rad_s: 0.15
maximum_acceleration_rad_s2: 0.5
manufacturer_certified: false
entry_authorized: false
publisher_authorized: false
robot_accessed: false
physical_movement_commanded: false
next_gate: ACTIVE_ESTOP_INSTALL_AND_RELOAD_THEN_FRESH_RUN_SPECIFIC_ENTRY_CONFIRMATION
EOF
(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.1C_ACCEPTANCE_EVIDENCE_OK=%s\n' "$RUN_DIR"
