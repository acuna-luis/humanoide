#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso: ./scripts/vla/new_vla_evidence_run.sh --experiment ID [--output-dir DIR]

Crea de forma exclusiva un directorio vacío para la evidencia de un
experimento VLA y muestra únicamente su ruta absoluta. Rechaza `/`, rutas ya
existentes e identificadores ambiguos; nunca reutiliza una variable de otro
shell ni sobrescribe un run anterior.
EOF
}

EVIDENCE_ROOT="${VLA_EVIDENCE_ROOT:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence}"
EXPERIMENT_ID=""
OUTPUT_DIR=""

while (($#)); do
  case "$1" in
    --experiment)
      (($# >= 2)) || { echo "ERROR: --experiment requiere ID" >&2; exit 2; }
      EXPERIMENT_ID="$2"
      shift 2
      ;;
    --output-dir)
      (($# >= 2)) || { echo "ERROR: --output-dir requiere DIR" >&2; exit 2; }
      OUTPUT_DIR="$2"
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

[[ "$EXPERIMENT_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || {
  echo "ERROR: ID de experimento inválido: $EXPERIMENT_ID" >&2
  exit 2
}

for tool in date dirname mkdir readlink; do
  command -v "$tool" >/dev/null || {
    echo "ERROR: falta herramienta local: $tool" >&2
    exit 1
  }
done

if [[ -z "$OUTPUT_DIR" ]]; then
  EVIDENCE_ROOT="$(readlink -m -- "$EVIDENCE_ROOT")"
  [[ "$EVIDENCE_ROOT" != "/" ]] || {
    echo "ERROR: la raíz de evidencia no puede ser /" >&2
    exit 1
  }
  mkdir -p -- "$EVIDENCE_ROOT"
  [[ -d "$EVIDENCE_ROOT" && -w "$EVIDENCE_ROOT" ]] || {
    echo "ERROR: raíz de evidencia no escribible: $EVIDENCE_ROOT" >&2
    exit 1
  }
  OUTPUT_DIR="$EVIDENCE_ROOT/$(date +%Y%m%dT%H%M%S)_${EXPERIMENT_ID}"
else
  OUTPUT_DIR="$(readlink -m -- "$OUTPUT_DIR")"
  PARENT_DIR="$(dirname -- "$OUTPUT_DIR")"
  [[ "$OUTPUT_DIR" != "/" ]] || {
    echo "ERROR: el directorio de evidencia no puede ser /" >&2
    exit 1
  }
  [[ -d "$PARENT_DIR" && -w "$PARENT_DIR" ]] || {
    echo "ERROR: el directorio padre no existe o no permite escritura: $PARENT_DIR" >&2
    exit 1
  }
fi

if ! mkdir -m 0750 -- "$OUTPUT_DIR" 2>/dev/null; then
  echo "ERROR: no se creará ni reutilizará el run: $OUTPUT_DIR" >&2
  exit 1
fi

printf '%s\n' "$OUTPUT_DIR"
