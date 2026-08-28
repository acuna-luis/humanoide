#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso: ./scripts/vla/audit_vla_experiment_e1_1.sh [--output-dir DIR]

Ejecuta el baseline E1.1 sin inferencia ni movimiento. Crea un directorio de
evidencia exclusivo, exige que ambos contenedores ya estén detenidos, confirma
cero publicadores y conserva logs, resultado y hashes relativos.
EOF
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
INSTALL_SCRIPT="$SCRIPT_DIR/install_ubtech_vla.sh"
SHADOW_SCRIPT="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
RUN_DIR=""

while (($#)); do
  case "$1" in
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

for tool in date grep sha256sum tee; do
  command -v "$tool" >/dev/null || {
    echo "ERROR: falta herramienta local: $tool" >&2
    exit 1
  }
done
test -x "$EVIDENCE_SCRIPT"
test -x "$INSTALL_SCRIPT"
test -x "$SHADOW_SCRIPT"
cd "$REPO_ROOT"

if [[ -n "$RUN_DIR" ]]; then
  RUN_DIR="$("$EVIDENCE_SCRIPT" --experiment E1.1 --output-dir "$RUN_DIR")"
else
  RUN_DIR="$("$EVIDENCE_SCRIPT" --experiment E1.1)"
fi
START_TIME="$(date --iso-8601=seconds)"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
printf 'E1.1_MODE=read-only-baseline,no-inference,no-movement\n'

"$INSTALL_SCRIPT" --check \
  2>&1 | tee "$RUN_DIR/01_install_check.log"
"$INSTALL_SCRIPT" --verify \
  2>&1 | tee "$RUN_DIR/02_install_verify.log"
"$SHADOW_SCRIPT" --check \
  2>&1 | tee "$RUN_DIR/03_shadow_check.log"
"$SHADOW_SCRIPT" --status \
  2>&1 | tee "$RUN_DIR/04_shadow_status.log"

if ! grep -Fq 'INFERENCE_CONTAINER=exited' "$RUN_DIR/04_shadow_status.log" ||
   ! grep -Fq 'CONTROL_CONTAINER=exited' "$RUN_DIR/04_shadow_status.log" ||
   ! grep -Fq 'COMMAND_PATH_SAFE=publishers:0' "$RUN_DIR/04_shadow_status.log"; then
  echo "ERROR: E1.1 exige ambos contenedores detenidos y cero publicadores; no se alteró la sesión activa." >&2
  exit 1
fi

"$SHADOW_SCRIPT" --stop \
  2>&1 | tee "$RUN_DIR/05_shadow_stop.log"
grep -Fq 'SHADOW_SESSION_STOPPED=yes' "$RUN_DIR/05_shadow_stop.log"
grep -Fq 'COMMAND_PATH_SAFE=publishers:0' "$RUN_DIR/05_shadow_stop.log"

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E1.1
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PASS
scenario_id: PC_VLA_BASELINE_NO_INFERENCE
actual_observations:
  inference_container: exited
  control_container: exited
  command_publishers: 0
  inference_started: false
  physical_movement_commanded: false
files:
  - 01_install_check.log
  - 02_install_verify.log
  - 03_shadow_check.log
  - 04_shadow_status.log
  - 05_shadow_stop.log
failure_reason: null
recovery_or_stop: SHADOW_SESSION_STOPPED=yes
next_experiment_authorized: E1.2_READ_ONLY
EOF

(
  cd "$RUN_DIR"
  sha256sum 0*.log actual_result.yaml
) > "$RUN_DIR/evidence.sha256"

printf 'E1.1_EVIDENCE_OK=%s\n' "$RUN_DIR"
printf 'E1.1_STATUS=PASS\n'
