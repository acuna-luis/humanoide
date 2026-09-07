#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_vla_ready_entry_transition_e6_1c.sh --check
  ./scripts/vla/run_vla_ready_entry_transition_e6_1c.sh --entry
  ./scripts/vla/run_vla_ready_entry_transition_e6_1c.sh --recover-ready

Ejecuta una sola transición E6.1C entre READY y ENTRY mediante tareas Motion
preinstaladas. Exige estado 20D fresco, preflight físico liberado, configuración
runtime exacta y confirmación específica. No arranca el checkpoint, no crea
publicadores VLA y nunca reintenta automáticamente.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_ready_entry_transition_e6_1c.json"
readonly ENTRY_CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_task0_entry_recovery_e6_1b.json"
readonly ACCEPTANCE_AUDITOR="$SCRIPT_DIR/audit_vla_owner_acceptance_e6_1c.sh"
readonly TRANSITION_AUDITOR="$SCRIPT_DIR/audit_vla_ready_entry_transition_e6_1c.sh"
readonly LIVE_PREFLIGHT="$SCRIPT_DIR/audit_vla_live_preflight_e6_0g.sh"
readonly NORMALIZER="$SCRIPT_DIR/normalize_vla_joint_state_e6_1b.py"
readonly STATE_GATE="$SCRIPT_DIR/check_vla_ready_entry_state_e6_1c.py"
readonly NEW_EVIDENCE="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly CONTAINER="walker-motion.manipulation_robot_app-1"
readonly TASK_ROOT="/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config"
readonly TASK_LIST="$TASK_ROOT/task_list.yaml"
readonly EXPECTED_TASK_SHA="224c6fca013e59b5dd36ef54cccd732fa48991962b143138e31e1268ba9fac1b"
readonly ENTRY_TASK="s2_bio_vla/s2_vla_e6_1c_ready_to_entry"
readonly RECOVERY_TASK="s2_bio_vla/s2_vla_e6_1c_entry_to_ready"
readonly ENTRY_CONFIRMATION="AUTORIZO READY A ENTRY E6.1C: READY MEDIDO, CLAMPS VACIOS, AMBAS CLAMPS EN ORIENTACION DE FABRICA Y CON HOLGURA VISIBLE AL TORSO, MESA Y B0 FUERA DE TODA TRAYECTORIA, CARGADOR DESCONECTADO, RUEDAS BLOQUEADAS, AMBOS PAROS LIBERADOS, ROBOT ESTABLE, DOS PERSONAS Y MANO EN E-STOP"
readonly RECOVERY_CONFIRMATION="AUTORIZO ENTRY A READY E6.1C: ENTRY MEDIDO, CLAMPS VACIOS, AMBAS CLAMPS EN ORIENTACION DE FABRICA Y CON HOLGURA VISIBLE AL TORSO, MESA Y B0 RETIRADOS, CARGADOR DESCONECTADO, RUEDAS BLOQUEADAS, AMBOS PAROS LIBERADOS, ROBOT ESTABLE, DOS PERSONAS Y MANO EN E-STOP"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == 1 ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE=""
while (($#)); do
  case "$1" in
    --check|--entry|--recover-ready)
      [[ -z "$MODE" ]] || { printf 'ERROR: indique un solo modo.\n' >&2; exit 2; }
      MODE="$1"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ -n "$MODE" ]] || { printf 'ERROR: falta modo.\n' >&2; usage >&2; exit 2; }

if [[ "$MODE" != --check ]]; then
  bash "$SCRIPT_DIR/../lib/cruzr_contact_motion_lock.sh" "E6.1C:$MODE" || exit $?
fi

for tool in awk basename cp date find grep jq nc python3 readlink setsid sha256sum sort ssh tee timeout xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
for source in "$CONTRACT" "$ENTRY_CONTRACT" "$ACCEPTANCE_AUDITOR" \
  "$TRANSITION_AUDITOR" "$LIVE_PREFLIGHT" "$NORMALIZER" "$STATE_GATE" "$NEW_EVIDENCE"; do
  test -s "$source" || { printf 'ERROR: falta %s\n' "$source" >&2; exit 1; }
done
"$ACCEPTANCE_AUDITOR" --check >/dev/null
"$TRANSITION_AUDITOR" --check >/dev/null

if [[ "$MODE" == --check ]]; then
  printf 'E6.1C_RUNNER_CHECK_OK=local-only,one-transition,no-retry,exact-20D-gates\n'
  printf 'E6.1C_RUNNER_PUBLISHER=none\nE6.1C_RUNNER_CHECKPOINT=not-started\n'
  printf 'CONTACT_INCIDENT_LOCK=active;PHYSICAL_AUTHORIZED=0\n'
  exit 0
fi

ssh_options=(
  -o ConnectTimeout=10 -o ConnectionAttempts=1
  -o ServerAliveInterval=10 -o ServerAliveCountMax=2
  -o PreferredAuthentications=password -o PubkeyAuthentication=no
  -o NumberOfPasswordPrompts=1 -o StrictHostKeyChecking=accept-new
)
run_ssh() {
  CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" setsid -w ssh "${ssh_options[@]}" \
    "$ROBOT_USER@$MOTION_HOST" "$@"
}
capture_state() {
  local raw="$1" normalized="$2"
  run_ssh "docker exec '$CONTAINER' bash -lc 'set +u; source /opt/walker/setup.bash; set -u; timeout 8 rosa topic echo --once --no-daemon /mc/whole_joint_states'" > "$raw"
  PYTHONDONTWRITEBYTECODE=1 python3 "$NORMALIZER" --contract "$ENTRY_CONTRACT" \
    --input "$raw" --output "$normalized" >/dev/null
}
gate_state() {
  local normalized="$1" expected="$2" output="$3"
  PYTHONDONTWRITEBYTECODE=1 python3 "$STATE_GATE" --contract "$CONTRACT" \
    --state-json "$normalized" --expect "$expected" --require-fresh --output "$output"
}
assert_runtime() {
  run_ssh bash -s -- "$CONTAINER" "$TASK_LIST" "$EXPECTED_TASK_SHA" <<'REMOTE'
set -Eeuo pipefail
container="$1"; task_list="$2"; expected="$3"
test "$(docker inspect --format '{{.State.Status}}' "$container")" = running
test "$(docker exec "$container" sha256sum "$task_list" | awk '{print $1}')" = "$expected"
started="$(date -d "$(docker inspect --format '{{.State.StartedAt}}' "$container")" +%s)"
mtime="$(docker exec "$container" stat -c %Y "$task_list")"
test "$started" -gt "$mtime"
test "$(docker exec "$container" grep -Fxc 's2_vla_e6_1c_ready_to_entry:' "$task_list")" -eq 1
test "$(docker exec "$container" grep -Fxc 's2_vla_e6_1c_entry_to_ready:' "$task_list")" -eq 1
printf 'E6.1C_RUNTIME_CONFIG_OK=1\n'
REMOTE
}
run_task() {
  local task="$1"
  run_ssh bash -s -- "$CONTAINER" "$task" <<'REMOTE'
set -Eeuo pipefail
container="$1"; task="$2"
output="$(docker exec -i "$container" bash -s -- "$task" <<'INNER'
set -Eeo pipefail
set +u
source /opt/walker/setup.bash
set -u
task="$1"
timeout 60 rosa action send_goal /mc/manipulation/action mc_task_msgs/action/ArmTask \
  "{\"task_name\":\"$task\",\"yaml_args\":\"{}\"}"
INNER
)"
printf '%s\n' "$output"
grep -q "'desc': 'SUCCEED'" <<<"$output"
grep -q 'status=4' <<<"$output"
REMOTE
}
read_confirmation() {
  local expected="$1" variable="$2" value
  value="${!variable:-}"
  if [[ -z "$value" && -t 0 ]]; then
    printf '\nEscriba exactamente:\n%s\n' "$expected"
    IFS= read -r value
  fi
  [[ "$value" == "$expected" ]] || {
    printf 'ERROR: confirmación específica ausente; no se envió movimiento.\n' >&2
    return 2
  }
}
finalize() {
  local run_dir="$1"
  (cd "$run_dir" && find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum) > "$run_dir/evidence.sha256"
  (cd "$run_dir" && sha256sum -c evidence.sha256 >/dev/null)
}

nc -z -w3 "$MOTION_HOST" 22 || { printf 'ERROR: Motion no responde.\n' >&2; exit 1; }
preflight="$($LIVE_PREFLIGHT --check --expect-released)"
grep -Fq 'CHARGER=0' <<<"$preflight"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' <<<"$preflight"
grep -Fq 'CANONICAL_MANIPULATION_PREFLIGHT=passed-read-only' <<<"$preflight"
runtime="$(assert_runtime)"
printf '%s\n%s\n' "$preflight" "$runtime"

if [[ "$MODE" == --entry ]]; then
  experiment="E6.1C-ENTRY"; source_endpoint=ready; target_endpoint=entry
  task="$ENTRY_TASK"; expected_confirmation="$ENTRY_CONFIRMATION"; confirmation_var=E6_1C_ENTRY_CONFIRMATION
else
  experiment="E6.1C-RECOVER-READY"; source_endpoint=entry; target_endpoint=ready
  task="$RECOVERY_TASK"; expected_confirmation="$RECOVERY_CONFIRMATION"; confirmation_var=E6_1C_RECOVERY_CONFIRMATION
fi
run_dir="$($NEW_EVIDENCE --experiment "$experiment")"
printf 'VLA_RUN_DIR=%s\n' "$run_dir"
printf '%s\n' "$preflight" > "$run_dir/preflight-before.log"
printf '%s\n' "$runtime" > "$run_dir/runtime-before.log"
capture_state "$run_dir/state-before.raw.yaml" "$run_dir/state-before.json"
gate_state "$run_dir/state-before.json" "$source_endpoint" "$run_dir/source-gate.json" | tee "$run_dir/source-gate.log"
jq -e '.qualified == true' "$run_dir/source-gate.json" >/dev/null
read_confirmation "$expected_confirmation" "$confirmation_var"
printf '%s\n' "$expected_confirmation" > "$run_dir/operator-confirmation.txt"
if ! run_task "$task" | tee "$run_dir/action.log"; then
  printf 'ERROR: la transición falló; no se repetirá automáticamente.\n' >&2
  cat > "$run_dir/actual_result.yaml" <<EOF
experiment_id: $experiment
status: FAIL_ACTION_NO_AUTOMATIC_RETRY
task: $task
physical_movement_commanded: true
automatic_retry_executed: false
checkpoint_started: false
physical_publishers: 0
EOF
  finalize "$run_dir"
  exit 1
fi
capture_state "$run_dir/state-after.raw.yaml" "$run_dir/state-after.json"
gate_state "$run_dir/state-after.json" "$target_endpoint" "$run_dir/target-gate.json" | tee "$run_dir/target-gate.log"
jq -e '.qualified == true' "$run_dir/target-gate.json" >/dev/null
cat > "$run_dir/actual_result.yaml" <<EOF
experiment_id: $experiment
run_id: $(basename -- "$run_dir")
start_endpoint: $source_endpoint
target_endpoint: $target_endpoint
status: PASS_SINGLE_TRANSITION_MEASURED
task: $task
action_result: SUCCEED
action_status: 4
target_max_error_rad: $(jq -r '.maximum_chebyshev_distance_rad' "$run_dir/target-gate.json")
target_max_velocity_rad_s: $(jq -r '.maximum_absolute_velocity_rad_s' "$run_dir/target-gate.json")
physical_movement_commanded: true
automatic_retry_executed: false
checkpoint_started: false
physical_publishers: 0
next_gate: OPERATOR_VISUAL_CONFIRMATION_BEFORE_FIXTURE_OR_NEXT_TRANSITION
EOF
finalize "$run_dir"
printf 'E6.1C_TRANSITION_EVIDENCE_OK=%s\n' "$run_dir"
