#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ $# == 1 && ( $1 == '--help' || $1 == '-h' ) ]]; then
  printf 'Uso: evaluate_current_only.sh OBSERVACIONES TRAIN MODEL_VOLUME CHECKPOINT OUTPUT_NUEVO DEVICE SEED TEST_MANIFEST_SHA256\nInferencia sin red ni robot sobre captura sin revisar; no demuestra éxito.\n'
  exit 0
fi
exec bash "$SCRIPT_DIR/evaluate_failed_only.sh" --current "$@"
