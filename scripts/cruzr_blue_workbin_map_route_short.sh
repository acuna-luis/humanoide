#!/usr/bin/env bash

set -Eeuo pipefail

# Variante corta: START -> PASO1 . Desde PASO1 vuelve directamente
# a la mesa; el script principal mantiene el agarre, depósito y home.

SCRIPT_DIR="$(dirname -- "$(readlink -f -- "$0")")"
exec "$SCRIPT_DIR/cruzr_blue_workbin_map_route.sh" --short "$@"
