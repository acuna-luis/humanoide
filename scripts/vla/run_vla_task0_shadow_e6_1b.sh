#!/usr/bin/env bash
set -Eeuo pipefail

# E6.1B never creates a RobotCommand publisher and never moves to ENTRY.  Its
# live mode only accepts a robot already measured at the frozen 20D ENTRY and
# performs five independently stopped task-0 inference/validator sessions.

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_vla_task0_shadow_e6_1b.sh --check
  ./scripts/vla/run_vla_task0_shadow_e6_1b.sh --run --fixture-manifest FILE.json

--check es estrictamente local/offline. --run es una futura validación shadow
de sólo lectura: exige fixture SUPPORTED_LOW congelado y robot ya situado en
la ENTRY 20D exacta de episode_000040. No instala ni ejecuta ENTRY/recovery,
no crea publicador físico y detiene ambos contenedores tras cada repetición.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_vla_task0_entry_recovery_e6_1b.json"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_task0_p14_shadow_e6_1b.json"
readonly PROFILE_NAME="$(basename -- "$PROFILE")"
readonly DATASET_REPORT="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260904T094803_E6.0Z/dataset-entry-states.json"
readonly AUDIT="$SCRIPT_DIR/audit_vla_task_entry_recovery_e6_1b.sh"
readonly CHECKER="$SCRIPT_DIR/check_vla_task0_entry_e6_1b.py"
readonly NORMALIZER="$SCRIPT_DIR/normalize_vla_joint_state_e6_1b.py"
readonly SUMMARIZER="$SCRIPT_DIR/summarize_vla_task0_shadow_e6_1b.py"
readonly SMOKE="$SCRIPT_DIR/run_vla_shadow_smoke.sh"
readonly SHADOW="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly NEW_EVIDENCE="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly ROS_CONTAINER="walker-motion.manipulation_robot_app-1"
readonly CONFIRMATION_TEXT="SUPPORTED_LOW FIJO, B0 VACIA Y ESTABLE, ENTRY EPISODE 000040 MEDIDA, ROBOT INMOVIL Y PERSONA JUNTO AL E-STOP"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == 1 ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE=check
FIXTURE_MANIFEST=""
while (($#)); do
  case "$1" in
    --check) MODE=check; shift ;;
    --run) MODE=run; shift ;;
    --fixture-manifest)
      (($# >= 2)) || { printf 'ERROR: falta FILE.json\n' >&2; exit 2; }
      FIXTURE_MANIFEST="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in awk basename cp date dirname find jq mkdir mktemp python3 readlink rm \
  setsid sha256sum sort ssh tee timeout xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta herramienta: %s\n' "$tool" >&2; exit 1; }
done
for source in "$CONTRACT" "$PROFILE" "$DATASET_REPORT" "$AUDIT" "$CHECKER" \
  "$NORMALIZER" "$SUMMARIZER" "$SMOKE" "$SHADOW" "$NEW_EVIDENCE"; do
  test -s "$source" || { printf 'ERROR: falta artefacto E6.1B: %s\n' "$source" >&2; exit 1; }
done

"$AUDIT" --check
if [[ "$MODE" == check ]]; then
  printf 'E6.1B_FIVE_SHADOW_CHECK_OK=offline-only,run-interface:fail-closed,repetitions:5\n'
  printf 'E6.1B_LIVE_REQUIREMENTS=measured-fixture,fresh-exact-entry,remote-profile-hash,human-confirmation\n'
  printf 'E6.1B_MOVEMENT_PATH=absent\n'
  exit 0
fi

[[ -n "$FIXTURE_MANIFEST" ]] || { printf 'ERROR: --run requiere --fixture-manifest.\n' >&2; exit 2; }
FIXTURE_MANIFEST="$(readlink -f -- "$FIXTURE_MANIFEST")"
test -s "$FIXTURE_MANIFEST" || { printf 'ERROR: manifiesto de fixture inexistente.\n' >&2; exit 2; }

confirmation="${E6_1B_SHADOW_CONFIRMATION:-}"
if [[ -z "$confirmation" && -t 0 ]]; then
  printf '\nEscriba exactamente:\n%s\n' "$CONFIRMATION_TEXT"
  IFS= read -r confirmation
fi
[[ "$confirmation" == "$CONFIRMATION_TEXT" ]] || {
  printf 'ERROR: confirmación E6.1B ausente; no se accedió al robot.\n' >&2
  exit 2
}

# Qualify the immutable fixture before the first network access. This check
# cannot authorize motion and deliberately succeeds only on fixture facts.
fixture_gate_tmp="$(mktemp)"
trap 'rm -f -- "$fixture_gate_tmp"' EXIT
PYTHONDONTWRITEBYTECODE=1 python3 "$CHECKER" \
  --contract "$CONTRACT" --dataset-report "$DATASET_REPORT" \
  --fixture-manifest "$FIXTURE_MANIFEST" --output "$fixture_gate_tmp" >/dev/null
jq -e '.fixture_qualified == true and .physical_execution_authorized == false' \
  "$fixture_gate_tmp" >/dev/null

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
  run_ssh "docker exec '$ROS_CONTAINER' bash -lc '
    set +u
    source /opt/walker/setup.bash
    set -u
    export ROS2CLI_DISABLE_DAEMON=1
    timeout 8 rosa topic echo --once --no-daemon /mc/whole_joint_states
  '"
}

RUN_DIR="$($NEW_EVIDENCE --experiment E6.1B-SHADOW5)"
START_TIME="$(date --iso-8601=seconds)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
cp -- "$FIXTURE_MANIFEST" "$RUN_DIR/fixture-manifest-source.json"
cp -- "$CONTRACT" "$PROFILE" "$RUN_DIR/"
cp -- "$fixture_gate_tmp" "$RUN_DIR/fixture-gate.json"
mkdir -p "$RUN_DIR/fixture-evidence"
fixture_parent="$(dirname -- "$FIXTURE_MANIFEST")"
while IFS=$'\t' read -r evidence_index evidence_path expected_hash; do
  if [[ "$evidence_path" = /* ]]; then
    evidence_source="$evidence_path"
  else
    evidence_source="$fixture_parent/$evidence_path"
  fi
  actual_hash="$(sha256sum "$evidence_source" | awk '{print $1}')"
  [[ "$actual_hash" == "$expected_hash" ]] || {
    printf 'ERROR: cambió evidencia física del fixture: %s\n' "$evidence_source" >&2
    exit 2
  }
  cp -- "$evidence_source" \
    "$RUN_DIR/fixture-evidence/$(printf '%02d' "$evidence_index")-$(basename -- "$evidence_source")"
done < <(jq -r '.evidence_files | to_entries[] | [.key, .value.path, .value.sha256] | @tsv' "$FIXTURE_MANIFEST")
rm -f -- "$fixture_gate_tmp"

cleanup_required=0
cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  rm -f -- "$fixture_gate_tmp"
  if ((cleanup_required)); then
    "$SHADOW" --stop >"$RUN_DIR/99_cleanup_stop.log" 2>&1 || true
  fi
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat >"$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.1B-SHADOW5
status: FAIL_CLOSED
physical_publishers_created: 0
physical_movement_commanded: false
physical_execution_authorized: false
EOF
    (
      cd "$RUN_DIR"
      find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
    ) >"$RUN_DIR/evidence.sha256"
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

run_args=()
for repetition in 1 2 3 4 5; do
  label="$(printf '%02d' "$repetition")"
  raw_state="$RUN_DIR/state-$label.raw.yaml"
  state_json="$RUN_DIR/state-$label.json"
  gate_json="$RUN_DIR/entry-gate-$label.json"
  printf 'E6.1B_REPETITION=%s/5; CAPTURING_READ_ONLY_STATE\n' "$repetition"
  capture_state >"$raw_state"
  PYTHONDONTWRITEBYTECODE=1 python3 "$NORMALIZER" \
    --contract "$CONTRACT" --input "$raw_state" --output "$state_json"
  PYTHONDONTWRITEBYTECODE=1 python3 "$CHECKER" \
    --contract "$CONTRACT" --dataset-report "$DATASET_REPORT" \
    --fixture-manifest "$FIXTURE_MANIFEST" --state-json "$state_json" \
    --require-fresh-state --output "$gate_json" >/dev/null
  jq -e '.qualified_for_five_shadow == true and .physical_execution_authorized == false' \
    "$gate_json" >/dev/null

  repetition_dir="$RUN_DIR/repetition-$label"
  cleanup_required=1
  "$SMOKE" --task-id 0 --experiment-id "E6.1B-$label" \
    --shadow-profile "$PROFILE_NAME" --output-dir "$repetition_dir"
  cleanup_required=0
  PYTHONDONTWRITEBYTECODE=1 python3 "$SUMMARIZER" \
    --contract "$CONTRACT" --profile "$PROFILE" --run-dir "$repetition_dir" \
    --output "$RUN_DIR/repetition-$label-summary.json"
  run_args+=(--run-dir "$repetition_dir")
done

PYTHONDONTWRITEBYTECODE=1 python3 "$SUMMARIZER" \
  --contract "$CONTRACT" --profile "$PROFILE" "${run_args[@]}" \
  --output "$RUN_DIR/five-shadow-summary.json"
jq -e '.status == "PASS_FIVE_LIVE_SHADOW" and .repetitions_validated == 5
  and .physical_command_publishers_created == 0
  and .physical_movement_commanded == false
  and .physical_execution_authorized == false' "$RUN_DIR/five-shadow-summary.json" >/dev/null

cat >"$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E6.1B-SHADOW5
run_id: $(basename -- "$RUN_DIR")
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_FIVE_LIVE_SHADOW
task_id: 0
scenario: SUPPORTED_LOW
candidate: episode_000040/frame_0
repetitions: 5
profile: $PROFILE_NAME
entry_motion_executed: false
recovery_motion_executed: false
physical_publishers_created: 0
physical_movement_commanded: false
physical_execution_authorized: false
next_gate: SEPARATE_REVIEW_OF_PHYSICAL_SUCCESSOR_REQUIRED
EOF
(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) >"$RUN_DIR/evidence.sha256"
(cd "$RUN_DIR" && sha256sum -c evidence.sha256 >/dev/null)
printf 'E6.1B_FIVE_SHADOW_EVIDENCE_OK=%s\n' "$RUN_DIR"
