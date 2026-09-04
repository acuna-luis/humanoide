#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_owner_acceptance_e6_0x.sh --check
  ./scripts/vla/audit_vla_owner_acceptance_e6_0x.sh --run

Valida y registra como evidencia local la aceptación del propietario para la
envolvente E6.0 NO_BOX de un punto. No conecta al robot, no usa ROS, no crea
publicadores y no convierte la aceptación en autorización de movimiento.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly ACCEPTANCE="$SCRIPT_DIR/runtime/cruzr_s2_vla_owner_acceptance_e6_0x.json"
readonly LIMITS="$SCRIPT_DIR/runtime/cruzr_s2_vla_canary_engineering_limits_e6_0s.json"
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
for required in "$ACCEPTANCE" "$LIMITS" "$EVIDENCE_SCRIPT"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done

limits_sha="$(sha256sum "$LIMITS" | awk '{print $1}')"
jq -e --arg limits_sha "$limits_sha" '
  .schema == "cruzr-s2-vla-owner-acceptance-e6.0x-v1"
  and .experiment_id == "E6.0X"
  and .accepted_by_role == "project_owner"
  and .acceptance_source == "explicit_confirmation_in_project_session"
  and .scope == "E6.0_NO_BOX_READY_TASK_0_P14_A_ONE_SOURCE_POINT_ONLY"
  and .engineering_limits_sha256 == $limits_sha
  and .maximum_target_delta_rad == 0.1
  and .maximum_velocity_rad_s == 0.15
  and .maximum_acceleration_rad_s2 == 0.5
  and .sample_period_seconds == 0.01
  and .manufacturer_certified == false
  and .owner_accepted == true
  and .acceptance_is_movement_authorization == false
  and .requires_run_specific_fresh_preflight == true
  and .requires_run_specific_activation_grant == true
  and .physical_execution_authorized == false
' "$ACCEPTANCE" >/dev/null
jq -e '
  .scope == "NO_BOX_READY_P14_A_ONE_SOURCE_POINT_ONLY"
  and .maximum_target_delta_rad == ([range(0;14)] | map(0.1))
  and .maximum_velocity_rad_s == ([range(0;14)] | map(0.15))
  and .maximum_acceleration_rad_s2 == ([range(0;14)] | map(0.5))
  and .sample_period_seconds == 0.01
  and .manufacturer_certified == false
  and .owner_acceptance_required == true
  and .physical_execution_authorized == false
' "$LIMITS" >/dev/null

printf 'E6.0X_OWNER_ACCEPTANCE_VALID=1\n'
printf 'E6.0X_SCOPE=NO_BOX_READY,task:0,profile:P14_A,source_points:1\n'
printf 'E6.0X_ACCEPTANCE_IS_MOVEMENT_AUTHORIZATION=0\n'
printf 'E6.0X_PHYSICAL_AUTHORIZED=0\n'
[[ "$MODE" == run ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E6.0X)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"
cp -- "$SCRIPT_PATH" "$ACCEPTANCE" "$LIMITS" "$RUN_DIR/"
sha256sum "$SCRIPT_PATH" "$ACCEPTANCE" "$LIMITS" > "$RUN_DIR/source_hashes.sha256"
cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.0X
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_OWNER_ACCEPTED_PROJECT_ENVELOPE_E6_0_NO_BOX_ONE_POINT_ONLY
mode: local_acceptance_record_no_robot_no_network_no_ros_no_publisher
accepted_by_role: project_owner
scope: E6.0_NO_BOX_READY_TASK_0_P14_A_ONE_SOURCE_POINT_ONLY
maximum_target_delta_rad: 0.1
maximum_velocity_rad_s: 0.15
maximum_acceleration_rad_s2: 0.5
sample_period_seconds: 0.01
manufacturer_certified: false
owner_accepted: true
acceptance_is_movement_authorization: false
run_specific_fresh_preflight_required: true
run_specific_activation_grant_required: true
physical_execution_authorized: false
physical_publishers: 0
network_calls: 0
robot_state_read: false
physical_movement_commanded: false
next_work: FRESH_RUN_SPECIFIC_PHYSICAL_PREFLIGHT_WITH_VLA_STOPPED_BEFORE_ANY_GRANT
EOF
(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.0X_EVIDENCE_OK=%s\n' "$RUN_DIR"
