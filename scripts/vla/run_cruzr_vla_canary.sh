#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso disponible ahora:
  ./scripts/vla/run_cruzr_vla_canary.sh --check \
    --task-id 0 --axis-profile P14_A --scenario NO_BOX_READY

Flujo físico E6.0Y, siempre por etapas y con confirmación propia:
  --ready | --one-point | --recover | --stop

Modos que siguen reservados:
  --one-chunk | --window

El modo --check sólo audita evidencia local. No conecta al robot ni publica.
El proceso ROS de un punto existe y está probado offline. La plantilla
versionada continúa desactivada; --one-point sólo genera un grant efímero tras
preflight READY fresco y confirmación física exacta de esa corrida.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly AUDITOR="$SCRIPT_DIR/audit_vla_canary_readiness_e6_0.sh"
readonly PHYSICAL_RUNNER="$SCRIPT_DIR/run_vla_canary_physical_e6_0y.sh"

MODE=""
TASK_ID=""
AXIS_PROFILE=""
SCENARIO=""
while (($#)); do
  case "$1" in
    --check|--ready|--one-point|--one-chunk|--window|--recover|--stop)
      [[ -z "$MODE" ]] || { echo "ERROR: indique un solo modo" >&2; exit 2; }
      MODE="$1"
      shift
      ;;
    --task-id)
      (($# >= 2)) || { echo "ERROR: --task-id requiere valor" >&2; exit 2; }
      TASK_ID="$2"; shift 2
      ;;
    --axis-profile)
      (($# >= 2)) || { echo "ERROR: --axis-profile requiere valor" >&2; exit 2; }
      AXIS_PROFILE="$2"; shift 2
      ;;
    --scenario)
      (($# >= 2)) || { echo "ERROR: --scenario requiere valor" >&2; exit 2; }
      SCENARIO="$2"; shift 2
      ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$MODE" ]] || { echo "ERROR: falta modo" >&2; usage >&2; exit 2; }
test -x "$AUDITOR" || { echo "ERROR: auditor no ejecutable: $AUDITOR" >&2; exit 1; }

if [[ "$MODE" == --ready || "$MODE" == --one-point || "$MODE" == --recover || "$MODE" == --stop ]]; then
  test -x "$PHYSICAL_RUNNER" || {
    echo "ERROR: runner E6.0Y no ejecutable: $PHYSICAL_RUNNER" >&2
    exit 1
  }
  if [[ "$MODE" == --one-point ]]; then
    [[ -z "$TASK_ID" || "$TASK_ID" == 0 ]] || { echo 'ERROR: sólo task 0' >&2; exit 2; }
    [[ -z "$AXIS_PROFILE" || "$AXIS_PROFILE" == P14_A ]] || { echo 'ERROR: sólo P14_A' >&2; exit 2; }
    [[ -z "$SCENARIO" || "$SCENARIO" == NO_BOX_READY ]] || { echo 'ERROR: sólo NO_BOX_READY' >&2; exit 2; }
  elif [[ -n "$TASK_ID" || -n "$AXIS_PROFILE" || -n "$SCENARIO" ]]; then
    echo "ERROR: $MODE no admite selectores de checkpoint" >&2
    exit 2
  fi
  exec "$PHYSICAL_RUNNER" "$MODE"
fi

if [[ "$MODE" != "--check" ]]; then
  printf 'E6.0_PHYSICAL_AUTHORIZED=0\n' >&2
  printf 'CANARY_RUNTIME_PROCESS_IMPLEMENTED=1\n' >&2
  printf 'CANARY_ACTIVE_LAUNCHER_ENABLED=guarded-one-point-only\n' >&2
  printf 'ERROR: %s sigue reservado. No se conectó al robot ni se publicó movimiento.\n' "$MODE" >&2
  exit 3
fi

[[ "$TASK_ID" == "0" ]] || { echo "ERROR: E6.0-CHECK sólo admite --task-id 0" >&2; exit 2; }
[[ "$AXIS_PROFILE" == "P14_A" ]] || { echo "ERROR: E6.0-CHECK sólo admite --axis-profile P14_A" >&2; exit 2; }
[[ "$SCENARIO" == "NO_BOX_READY" ]] || { echo "ERROR: E6.0-CHECK sólo admite --scenario NO_BOX_READY" >&2; exit 2; }

"$AUDITOR" --check
printf 'CANARY_RUNTIME_PROCESS_IMPLEMENTED=1\n'
printf 'CANARY_ACTIVE_LAUNCHER_ENABLED=0\n'
printf 'CANARY_COMMAND_PATH=implemented-offline,fail-closed-before-robot-access\n'
