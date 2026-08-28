#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso: ./scripts/vla/run_vla_shadow_smoke.sh --task-id 0|2
       [--experiment-id ID] [--output-dir DIR]

Ejecuta un único smoke test VLA en shadow y crea evidencia autocontenida.
Task 0 corresponde a E2.0 y task 2 a E2.1. No publica RobotCommand ni mueve
el robot. Un trap solicita STOP si el bloque falla o recibe una señal.
EOF
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
TASK_ID=""
EXPERIMENT_ID=""
RUN_DIR=""

while (($#)); do
  case "$1" in
    --task-id)
      (($# >= 2)) || { echo "ERROR: --task-id requiere 0 o 2" >&2; exit 2; }
      TASK_ID="$2"
      shift 2
      ;;
    --output-dir)
      (($# >= 2)) || { echo "ERROR: --output-dir requiere DIR" >&2; exit 2; }
      RUN_DIR="$2"
      shift 2
      ;;
    --experiment-id)
      (($# >= 2)) || { echo "ERROR: --experiment-id requiere ID" >&2; exit 2; }
      EXPERIMENT_ID="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: argumento desconocido: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$TASK_ID" in
  0)
    [[ -n "$EXPERIMENT_ID" ]] || EXPERIMENT_ID="E2.0"
    TASK_TEXT="Pick up the large box from the lowest level of shelf"
    ;;
  2)
    [[ -n "$EXPERIMENT_ID" ]] || EXPERIMENT_ID="E2.1"
    TASK_TEXT="Pick up the large box from the middle level of shelf"
    ;;
  *) echo "ERROR: --task-id debe ser 0 o 2" >&2; exit 2 ;;
esac

for tool in find grep jq sha256sum tee wc; do
  command -v "$tool" >/dev/null || {
    echo "ERROR: falta herramienta local: $tool" >&2
    exit 1
  }
done
test -x "$SHADOW_SCRIPT"
test -x "$EVIDENCE_SCRIPT"
cd "$REPO_ROOT"

if [[ -n "$RUN_DIR" ]]; then
  RUN_DIR="$("$EVIDENCE_SCRIPT" --experiment "$EXPERIMENT_ID" --output-dir "$RUN_DIR")"
else
  RUN_DIR="$("$EVIDENCE_SCRIPT" --experiment "$EXPERIMENT_ID")"
fi
START_TIME="$(date --iso-8601=seconds)"
test -d "$RUN_DIR"
test -w "$RUN_DIR"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
printf '%s_MODE=shadow,no-robot-command,no-movement\n' "$EXPERIMENT_ID"

cleanup_required=0
cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((cleanup_required)); then
    "$SHADOW_SCRIPT" --stop \
      > >(tee "$RUN_DIR/99_cleanup_stop.log") \
      2> >(tee "$RUN_DIR/99_cleanup_stop.stderr.log" >&2) || true
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

"$SHADOW_SCRIPT" --check \
  2>&1 | tee "$RUN_DIR/01_check.log"
cleanup_required=1
"$SHADOW_SCRIPT" --start-shadow --shadow-duration 180 \
  2>&1 | tee "$RUN_DIR/02_start_shadow.log"
"$SHADOW_SCRIPT" --start-inference \
  2>&1 | tee "$RUN_DIR/03_start_inference.log"
"$SHADOW_SCRIPT" --trigger --task-id "$TASK_ID" --inference-duration 8 \
  2>&1 | tee "$RUN_DIR/04_task${TASK_ID}.log"
"$SHADOW_SCRIPT" --status \
  2>&1 | tee "$RUN_DIR/05_status.log"
"$SHADOW_SCRIPT" --stop \
  2>&1 | tee "$RUN_DIR/06_stop.log"
cleanup_required=0

"$SHADOW_SCRIPT" --export-evidence "$RUN_DIR/exported" \
  2>&1 | tee "$RUN_DIR/07_export.log"

test "$(find "$RUN_DIR" -maxdepth 1 -type f -name '*.log' -size +0c | wc -l)" -eq 7
grep -Fq 'Goal finished with status: SUCCEEDED' "$RUN_DIR/04_task${TASK_ID}.log"
grep -Fq 'SHADOW_SESSION_STOPPED=yes' "$RUN_DIR/06_stop.log"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' "$RUN_DIR/06_stop.log"
grep -Fq 'INFERENCE_CONTAINER=exited' "$RUN_DIR/exported/status_after_export.log"
grep -Fq 'CONTROL_CONTAINER=exited' "$RUN_DIR/exported/status_after_export.log"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' "$RUN_DIR/exported/status_after_export.log"

ACTUAL_DURATION_LINE="$(grep -m1 '^actual_duration:' "$RUN_DIR/04_task${TASK_ID}.log")"
ACTUAL_DURATION_SEC="${ACTUAL_DURATION_LINE#actual_duration: }"
[[ "$ACTUAL_DURATION_SEC" =~ ^[0-9]+([.][0-9]+)?$ ]] || {
  echo "ERROR: duración real ausente o inválida: $ACTUAL_DURATION_SEC" >&2
  exit 1
}

jq -s \
  --argjson requested_duration_sec 8 \
  --argjson actual_duration_sec "$ACTUAL_DURATION_SEC" \
  --arg task_text "$TASK_TEXT" \
  '{
  task_text: $task_text,
  requested_duration_sec: $requested_duration_sec,
  actual_duration_sec: $actual_duration_sec,
  duration_overrun_sec: ($actual_duration_sec - $requested_duration_sec),
  chunks: length,
  accepted: (map(select(.accepted == true)) | length),
  rejected: (map(select(.accepted == false)) | length),
  chunk_ids: map(.chunk_id),
  reasons: map(.reasons),
  inference_time_sec: map(.metrics.inference_time_sec),
  max_first_point_delta_by_chunk: map(
    ((.metrics.first_point_delta // {}) | to_entries | max_by(.value)) // null
  ),
  first_point_delta_violation_examples: map(
    .metrics.first_point_delta_violation_examples // []
  )
}' "$RUN_DIR/exported/shadow.jsonl" > "$RUN_DIR/shadow_summary.json"

CHUNK_COUNT="$(jq -r '.chunks' "$RUN_DIR/shadow_summary.json")"
((CHUNK_COUNT >= 1)) || {
  echo "ERROR: no se recibió ningún chunk con verdict" >&2
  exit 1
}

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: $EXPERIMENT_ID
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_SHADOW_SAFETY_ONLY
scenario_id: LIVE_CURRENT_SCENE_OOD_SHADOW
task_id: $TASK_ID
task_text: $TASK_TEXT
task_outcome: SHADOW_VERDICT_ONLY_NOT_PHYSICAL_TASK_SUCCESS
actual_observations:
  requested_duration_sec: 8
  actual_duration_sec: $ACTUAL_DURATION_SEC
  duration_overrun_sec: $(jq -r '.duration_overrun_sec' "$RUN_DIR/shadow_summary.json")
  chunks: $CHUNK_COUNT
  accepted: $(jq -r '.accepted' "$RUN_DIR/shadow_summary.json")
  rejected: $(jq -r '.rejected' "$RUN_DIR/shadow_summary.json")
  reasons: $(jq -c '.reasons' "$RUN_DIR/shadow_summary.json")
  inference_container: exited
  control_container: exited
  command_publishers: 0
  physical_movement_commanded: false
files:
  - 01_check.log
  - 02_start_shadow.log
  - 03_start_inference.log
  - 04_task${TASK_ID}.log
  - 05_status.log
  - 06_stop.log
  - 07_export.log
  - exported/shadow.jsonl
  - exported/shadow-process.log
  - exported/inference-process.log
  - exported/status_after_export.log
  - shadow_summary.json
  - evidence.sha256
failure_reason: null
recovery_or_stop: SHADOW_SESSION_STOPPED=yes
next_experiment_authorized: false
next_requirement: REVIEW_RESULT_AND_PLAN_GATES
EOF

(
  cd "$RUN_DIR"
  sha256sum \
    0*.log \
    actual_result.yaml \
    shadow_summary.json \
    exported/exported_logs.sha256
) > "$RUN_DIR/evidence.sha256"

printf '%s_EVIDENCE_OK=%s\n' "$EXPERIMENT_ID" "$RUN_DIR"
printf '%s_RESULT=PASS_SHADOW_SAFETY_NOT_TASK_SUCCESS\n' "$EXPERIMENT_ID"
