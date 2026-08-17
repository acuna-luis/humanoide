#!/usr/bin/env bash

set -Eeuo pipefail
source "$(dirname -- "$(readlink -f -- "$0")")/_common.sh"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/hands/check_factory_tasks.sh

Comprueba en el robot todos los XML y primitivas incluidos en los manifiestos
locales. No requiere que las manos estén instaladas y no produce movimiento.
EOF
}

if (($#)); then
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *) hands_die "Este comando no acepta opciones." ;;
  esac
fi

hands_select_connection
mapfile -t tasks < <(awk '{sub(/\.xml$/, "", $2); print $2}' "$HANDS_MANIFEST")
((${#tasks[@]} > 0)) || hands_die "El manifiesto de tareas está vacío."
hands_validate_tasks "${tasks[@]}"
hands_info "FACTORY_TASKS_CHECK_OK=tasks:${#tasks[@]},movement:none"

