#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso: ./scripts/vla/run_vla_shadow_matrix.sh \
  --scenario SUPPORTED_LOW|HELD_LOW|SUPPORTED_MIDDLE|HELD_MIDDLE \
  --task-id 0|1|2|3 --axis-profile PERFIL --repetitions 5 --output DIR \
  [--source-campaign DIR]

Construye una celda E5.1 con cinco inferencias C0 congeladas de E3.0 y aplica
el perfil como máscara posterior. Es replay shadow local: no usa red, ROS,
estado vivo, publicadores ni movimiento del robot.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly BUILDER="$SCRIPT_DIR/build_vla_shadow_matrix_e5_1.py"
readonly PROFILE="$SCRIPT_DIR/runtime/cruzr_s2_vla_profile.json"
readonly SINK="$SCRIPT_DIR/runtime/vla_executor_sink.py"
DEFAULT_SOURCE="/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260828T114346_E3.0"

SCENARIO=""
TASK_ID=""
AXIS_PROFILE=""
REPETITIONS=""
OUTPUT=""
SOURCE_CAMPAIGN="$DEFAULT_SOURCE"
while (($#)); do
  case "$1" in
    --scenario) SCENARIO="${2:?Falta escenario}"; shift 2 ;;
    --task-id) TASK_ID="${2:?Falta task ID}"; shift 2 ;;
    --axis-profile) AXIS_PROFILE="${2:?Falta perfil}"; shift 2 ;;
    --repetitions) REPETITIONS="${2:?Faltan repeticiones}"; shift 2 ;;
    --output) OUTPUT="${2:?Falta salida}"; shift 2 ;;
    --source-campaign) SOURCE_CAMPAIGN="${2:?Falta campaña fuente}"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$SCENARIO" && -n "$TASK_ID" && -n "$AXIS_PROFILE" && -n "$REPETITIONS" && -n "$OUTPUT" ]] || {
  echo "ERROR: faltan argumentos obligatorios" >&2
  usage >&2
  exit 2
}
for required in "$BUILDER" "$PROFILE" "$SINK" "$SOURCE_CAMPAIGN/evidence.sha256"; do
  test -s "$required" || { echo "ERROR: falta $required" >&2; exit 1; }
done
for tool in cmp python3 sha256sum; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta herramienta: $tool" >&2; exit 1; }
done
(
  cd "$SOURCE_CAMPAIGN"
  sha256sum -c evidence.sha256 >/dev/null
)
cmp -s "$SOURCE_CAMPAIGN/checkpoint_before.sha256" "$SOURCE_CAMPAIGN/checkpoint_after.sha256"

PYTHONDONTWRITEBYTECODE=1 python3 "$BUILDER" \
  --source-campaign "$SOURCE_CAMPAIGN" \
  --scenario "$SCENARIO" \
  --task-id "$TASK_ID" \
  --axis-profile "$AXIS_PROFILE" \
  --repetitions "$REPETITIONS" \
  --profile "$PROFILE" \
  --sink "$SINK" \
  --output "$OUTPUT"
