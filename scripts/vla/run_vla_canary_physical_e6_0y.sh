#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_vla_canary_physical_e6_0y.sh --check
  ./scripts/vla/run_vla_canary_physical_e6_0y.sh --ready
  ./scripts/vla/run_vla_canary_physical_e6_0y.sh --one-point
  ./scripts/vla/run_vla_canary_physical_e6_0y.sh --recover
  ./scripts/vla/run_vla_canary_physical_e6_0y.sh --stop

E6.0Y se conserva únicamente para diagnóstico, STOP y recuperación histórica.
--ready y --one-point están retirados: task 0 exige una caja en repisa baja y
un estado inicial 20D compatible con el dataset; NO_BOX_READY no cumple ese
contrato. --recover sólo acepta READY medido y vuelve a HOME.

No se arranca el ejecutor físico entregado por UBTECH. El STOP software no
equivale al E-stop; una persona debe permanecer junto al E-stop principal.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly RUNTIME_DIR="$SCRIPT_DIR/runtime"
readonly LIVE_PREFLIGHT="$SCRIPT_DIR/audit_vla_live_preflight_e6_0g.sh"
readonly SHADOW="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly NEW_EVIDENCE="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly HOME_GATE="$REPO_ROOT/scripts/lib/cruzr_home_posture_gate.py"
readonly READY_GATE="$RUNTIME_DIR/cruzr_s2_vla_ready_state_gate.py"
readonly TRANSPORT_CONTRACT="$RUNTIME_DIR/cruzr_s2_vla_sdk_transport_contract_e6_0r.json"
readonly ENTRY_CONTRACT="$RUNTIME_DIR/cruzr_s2_vla_task_entry_contract_e6_0z.json"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly VISION_HOST="${CRUZR_VISION_HOST:-192.168.11.3}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly MOTION_CONTAINER="walker-motion.manipulation_robot_app-1"
readonly RECOVERY_TASK="s2_bio_vla/s2_vla_e6_0_exact_recovery"
readonly RECOVERY_CONFIRMATION="AUTORIZO RECOVERY E6.0 A HOME: READY MEDIDO, CLAMPS VACIOS, ZONA 1.5 M VACIA, DOS PERSONAS Y MANO EN E-STOP"
readonly READY_BLOCK_REASON="E6.0 NO_BOX retirado: no se enviará HOME->READY sin un sucesor task-matched con contrato 20D"
readonly ONE_POINT_BLOCK_REASON="E6.0 NO_BOX retirado: task 0 exige caja/estante y un estado 20D compatible; no se aumentará el límite de 0.1 rad"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == 1 ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE=""
while (($#)); do
  case "$1" in
    --check|--ready|--one-point|--recover|--stop)
      [[ -z "$MODE" ]] || { printf 'ERROR: indique un solo modo\n' >&2; exit 2; }
      MODE="$1"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'ERROR: argumento desconocido: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done
[[ -n "$MODE" ]] || { printf 'ERROR: falta modo\n' >&2; usage >&2; exit 2; }

for tool in awk find grep nc python3 readlink setsid sha256sum sort ssh tee timeout xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
for required in "$LIVE_PREFLIGHT" "$SHADOW" "$NEW_EVIDENCE" "$HOME_GATE" \
  "$READY_GATE" "$TRANSPORT_CONTRACT" "$ENTRY_CONTRACT"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done

ssh_options=(
  -o ConnectTimeout=10
  -o ConnectionAttempts=1
  -o ServerAliveInterval=10
  -o ServerAliveCountMax=2
  -o PreferredAuthentications=password
  -o PubkeyAuthentication=no
  -o NumberOfPasswordPrompts=1
  -o StrictHostKeyChecking=accept-new
)

run_ssh() {
  local host="$1"
  shift
  CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
    DISPLAY="${DISPLAY:-:0}" setsid -w ssh "${ssh_options[@]}" \
    "$ROBOT_USER@$host" "$@"
}

capture_actuator_json() {
  run_ssh "$MOTION_HOST" \
    "docker exec '$MOTION_CONTAINER' bash -lc 'set +u; source /opt/walker/setup.bash; set -u; timeout 8 rosa topic echo --once --no-daemon /mc/actuator_state'"
}

capture_whole_joint_json() {
  run_ssh "$MOTION_HOST" \
    "docker exec '$MOTION_CONTAINER' bash -lc 'set +u; source /opt/walker/setup.bash; set -u; timeout 8 rosa topic echo --once --no-daemon /mc/whole_joint_states'"
}

capture_ready() {
  local actuator_health named_ready
  actuator_health="$(capture_actuator_json | python3 "$HOME_GATE")"
  named_ready="$(capture_whole_joint_json | python3 "$READY_GATE" --contract "$TRANSPORT_CONTRACT")"
  printf 'READY_ACTUATOR_HEALTH=passed\n%s\n%s\n' "$actuator_health" "$named_ready"
}

read_confirmation() {
  local expected="$1" variable_name="$2" confirmation
  confirmation="${!variable_name:-}"
  if [[ -z "$confirmation" && -t 0 ]]; then
    printf '\nEscriba exactamente:\n%s\n' "$expected"
    IFS= read -r confirmation
  fi
  [[ "$confirmation" == "$expected" ]] || {
    printf 'ERROR: confirmación exacta ausente; no se envió movimiento.\n' >&2
    return 2
  }
}

released_preflight() {
  "$LIVE_PREFLIGHT" --check --expect-released
}

run_motion_task() {
  local task="$1" limit="$2"
  run_ssh "$MOTION_HOST" bash -s -- "$MOTION_CONTAINER" "$task" "$limit" <<'REMOTE'
set -Eeuo pipefail
container="$1"
task="$2"
limit="$3"
output="$(docker exec -i "$container" bash -s -- "$task" "$limit" <<'INNER'
set -Eeo pipefail
set +u
source /opt/walker/setup.bash
set -u
task="$1"
limit="$2"
timeout "$limit" rosa action send_goal /mc/manipulation/action \
  mc_task_msgs/action/ArmTask \
  "{\"task_name\":\"$task\",\"yaml_args\":\"{}\"}"
INNER
)"
printf '%s\n' "$output"
grep -q "'desc': 'SUCCEED'" <<<"$output"
grep -q 'status=4' <<<"$output"
REMOTE
}

publisher_count() {
  run_ssh "$MOTION_HOST" "docker exec walker-ros.ros2-1 bash -lc '
    source /opt/ros/humble/setup.bash
    export ROS2CLI_DISABLE_DAEMON=1
    output=\$(timeout 8 ros2 topic info /mc/sdk/robot_command 2>&1) || true
    awk '\''/Publisher count:/ {print \$3; found=1} END {if (!found) print 0}'\'' <<<\"\$output\"
  '"
}

assert_runtime_sources() {
  python3 -m py_compile "$READY_GATE"
  python3 - "$ENTRY_CONTRACT" <<'PY'
import json
import sys

contract = json.load(open(sys.argv[1], encoding="utf-8"))
assert contract["physical_execution_authorized"] is False
assert contract["action_semantics"] == "absolute_joint_position_rad"
assert contract["tasks"]["0"]["required_scenario"] == "SUPPORTED_LOW"
PY
  printf 'E6.0Y_CHECK_OK=retired-no-box-entry,local-only,no-robot,no-ros,no-publisher,no-movement\n'
}

finalize_evidence() {
  local run_dir="$1"
  (
    cd "$run_dir"
    find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
  ) > "$run_dir/evidence.sha256"
  (cd "$run_dir" && sha256sum -c evidence.sha256 >/dev/null)
}

case "$MODE" in
  --check)
    assert_runtime_sources
    exit 0
    ;;
  --ready)
    printf 'E6.0Y_READY_RETIRED=1\n' >&2
    printf 'ERROR: %s\n' "$READY_BLOCK_REASON" >&2
    printf 'NEXT_GATE=task-matched-scene,task-matched-20D-entry,five-fresh-shadow-chunks\n' >&2
    exit 3
    ;;
  --one-point)
    printf 'E6.0Y_ONE_POINT_RETIRED=1\n' >&2
    printf 'ERROR: %s\n' "$ONE_POINT_BLOCK_REASON" >&2
    printf 'NEXT_GATE=task-matched-scene,task-matched-20D-entry,five-fresh-shadow-chunks\n' >&2
    exit 3
    ;;
  --stop)
    "$SHADOW" --stop
    [[ "$(publisher_count)" == 0 ]] || {
      printf 'ERROR: aún existe un publicador de mando; accione E-stop.\n' >&2
      exit 1
    }
    printf 'E6.0Y_STOPPED=containers-exited,publishers-0\n'
    exit 0
    ;;
esac

nc -z -w3 "$MOTION_HOST" 22 || { printf 'ERROR: Motion no responde.\n' >&2; exit 1; }
nc -z -w3 "$VISION_HOST" 22 || { printf 'ERROR: Vision no responde.\n' >&2; exit 1; }
assert_runtime_sources

preflight="$(released_preflight)"
ready="$(capture_ready)"
grep -Fq 'MEASURED_READY=1' <<<"$ready" || {
  printf '%s\nERROR: recovery E6.0 sólo admite READY medido; no se movió.\n' "$ready" >&2
  exit 1
}
printf '%s\n%s\n' "$preflight" "$ready"
read_confirmation "$RECOVERY_CONFIRMATION" E6_0Y_RECOVERY_CONFIRMATION
run_dir="$("$NEW_EVIDENCE" --experiment E6.0Y-RECOVERY)"
printf '%s\n' "$preflight" > "$run_dir/preflight-before.log"
printf '%s\n' "$ready" > "$run_dir/ready-before.log"
if ! run_motion_task "$RECOVERY_TASK" 120 | tee "$run_dir/recovery-action.log"; then
  printf 'ERROR: recovery falló; no repita y accione E-stop ante contacto.\n' >&2
  exit 1
fi
home="$(capture_actuator_json | python3 "$HOME_GATE")"
printf '%s\n' "$home" | tee "$run_dir/home-after.log"
grep -Fq 'MEASURED_HOME=1' <<<"$home"
printf '%s\n' \
  "experiment_id: E6.0Y-RECOVERY" \
  "run_id: $(basename -- "$run_dir")" \
  "status: PASS_READY_TO_HOME_MEASURED" \
  "physical_movement_commanded: true" \
  "task: $RECOVERY_TASK" \
  "measured_home: true" \
  > "$run_dir/actual_result.yaml"
finalize_evidence "$run_dir"
printf 'E6.0Y_RECOVERY_EVIDENCE_OK=%s\n' "$run_dir"
