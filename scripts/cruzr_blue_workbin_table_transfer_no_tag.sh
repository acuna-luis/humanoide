#!/usr/bin/env bash
set -Eeuo pipefail
# Conserva el mismo orquestador, locks, preflight y recuperación. Sin argumentos
# sólo comprueba. Ningún modo de este wrapper utiliza el alineador AprilTag.
script_dir="$(dirname -- "$(readlink -f -- "$0")")"
exec "$script_dir/cruzr_blue_workbin_table_transfer.sh" --without-apriltag "$@"
