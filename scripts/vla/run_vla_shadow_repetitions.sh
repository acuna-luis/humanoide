#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso: ./scripts/vla/run_vla_shadow_repetitions.sh --task-id 0|2
       [--repetitions N] [--output-dir DIR]

Ejecuta E2.3 como runs shadow independientes. Cada repetición crea su propio
directorio, carga una sesión limpia y confirma STOP antes de continuar. Es más
conservador que compartir contenedores y evita mezclar chunks o logs.
EOF
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
SMOKE_SCRIPT="$SCRIPT_DIR/run_vla_shadow_smoke.sh"
SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
TASK_ID=""
REPETITIONS=5
RUN_DIR=""

while (($#)); do
  case "$1" in
    --task-id)
      (($# >= 2)) || { echo "ERROR: --task-id requiere 0 o 2" >&2; exit 2; }
      TASK_ID="$2"
      shift 2
      ;;
    --repetitions)
      (($# >= 2)) || { echo "ERROR: --repetitions requiere N" >&2; exit 2; }
      REPETITIONS="$2"
      shift 2
      ;;
    --output-dir)
      (($# >= 2)) || { echo "ERROR: --output-dir requiere DIR" >&2; exit 2; }
      RUN_DIR="$2"
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
  0) TASK_TEXT="Pick up the large box from the lowest level of shelf" ;;
  2) TASK_TEXT="Pick up the large box from the middle level of shelf" ;;
  *) echo "ERROR: --task-id debe ser 0 o 2" >&2; exit 2 ;;
esac
[[ "$REPETITIONS" =~ ^[1-9][0-9]*$ ]] && ((REPETITIONS <= 10)) || {
  echo "ERROR: --repetitions debe estar entre 1 y 10" >&2
  exit 2
}

for tool in date jq seq sha256sum tee; do
  command -v "$tool" >/dev/null || {
    echo "ERROR: falta herramienta local: $tool" >&2
    exit 1
  }
done
test -x "$EVIDENCE_SCRIPT"
test -x "$SMOKE_SCRIPT"
test -x "$SHADOW_SCRIPT"
cd "$REPO_ROOT"

EXPERIMENT_ID="E2.3-task${TASK_ID}"
if [[ -n "$RUN_DIR" ]]; then
  RUN_DIR="$("$EVIDENCE_SCRIPT" --experiment "$EXPERIMENT_ID" --output-dir "$RUN_DIR")"
else
  RUN_DIR="$("$EVIDENCE_SCRIPT" --experiment "$EXPERIMENT_ID")"
fi
START_TIME="$(date --iso-8601=seconds)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
printf 'E2.3_MODE=independent-shadow-runs,no-robot-command,no-movement\n'

for repetition in $(seq 1 "$REPETITIONS"); do
  printf -v repetition_padded '%02d' "$repetition"
  child_dir="$RUN_DIR/rep_${repetition_padded}"
  child_experiment="E2.3-task${TASK_ID}-rep${repetition_padded}"
  "$SMOKE_SCRIPT" \
    --task-id "$TASK_ID" \
    --experiment-id "$child_experiment" \
    --output-dir "$child_dir" \
    2>&1 | tee "$RUN_DIR/rep_${repetition_padded}.console.log"

  jq -ce \
    --argjson repetition "$repetition" \
    --arg run_dir "rep_${repetition_padded}" \
    '. + {repetition: $repetition, run_dir: $run_dir}' \
    "$child_dir/shadow_summary.json" \
    >> "$RUN_DIR/repetitions.jsonl"
done

"$SHADOW_SCRIPT" --status \
  2>&1 | tee "$RUN_DIR/final_status.log"
grep -Fq 'INFERENCE_CONTAINER=exited' "$RUN_DIR/final_status.log"
grep -Fq 'CONTROL_CONTAINER=exited' "$RUN_DIR/final_status.log"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' "$RUN_DIR/final_status.log"

jq -s \
  --arg task_text "$TASK_TEXT" \
  --argjson expected_repetitions "$REPETITIONS" \
  '{
    task_text: $task_text,
    expected_repetitions: $expected_repetitions,
    completed_repetitions: length,
    total_chunks: (map(.chunks) | add),
    accepted_chunks: (map(.accepted) | add),
    rejected_chunks: (map(.rejected) | add),
    runs: .
  }' "$RUN_DIR/repetitions.jsonl" > "$RUN_DIR/repetitions_summary.json"

[[ "$(jq -r '.completed_repetitions' "$RUN_DIR/repetitions_summary.json")" -eq "$REPETITIONS" ]]

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E2.3
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS_SHADOW_REPETITIONS_ONLY
scenario_id: LIVE_CURRENT_SCENE_OOD_SHADOW_UNCHANGED
task_id: $TASK_ID
task_text: $TASK_TEXT
actual_observations:
  requested_repetitions: $REPETITIONS
  completed_repetitions: $(jq -r '.completed_repetitions' "$RUN_DIR/repetitions_summary.json")
  total_chunks: $(jq -r '.total_chunks' "$RUN_DIR/repetitions_summary.json")
  accepted_chunks: $(jq -r '.accepted_chunks' "$RUN_DIR/repetitions_summary.json")
  rejected_chunks: $(jq -r '.rejected_chunks' "$RUN_DIR/repetitions_summary.json")
  inference_container_final: exited
  control_container_final: exited
  command_publishers_final: 0
  physical_movement_commanded: false
recovery_or_stop: STOP_CONFIRMED_AFTER_EACH_REPETITION
next_experiment_authorized: false
next_requirement: REVIEW_REPETITIONS_AND_PLAN_GATES
EOF

(
  cd "$RUN_DIR"
  sha256sum \
    rep_*.console.log \
    rep_*/evidence.sha256 \
    repetitions.jsonl \
    repetitions_summary.json \
    final_status.log \
    actual_result.yaml
) > "$RUN_DIR/evidence.sha256"

printf 'E2.3_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E2.3_RESULT=PASS_SHADOW_REPETITIONS_NOT_TASK_SUCCESS\n'
