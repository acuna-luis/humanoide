#!/usr/bin/env bash
# Manual release using the reviewed factory BYD primitive.
set -Eeuo pipefail
script_dir="$(dirname -- "$(readlink -f -- "$0")")"
mode="--check-open-only"
if (($# > 1)); then
  echo 'ERROR: use sólo --check, --run o --help.' >&2
  exit 2
fi
case "${1:---check}" in
  --check) ;;
  --run) mode="--open-only" ;;
  --help|-h)
    cat <<'EOF'
Uso:
  ./scripts/cruzr_blue_workbin_open_only.sh --check
  ./scripts/cruzr_blue_workbin_open_only.sh --run

Sin argumentos equivale a --check: no instala ni mueve.
--run comprueba el robot y pide escribir ABRIR ABRAZADERAS.
Separa cada abrazadera 5 cm hacia fuera en unos 2 segundos, sin descenso
previo, transporte ni HOME. La caja puede caer o bascular.
Uso manual desde el agarre frontal workbin, incluso si terminó imperfecto.
No sirve desde PICO ni desde cualquier postura. Comprueba ambos recorridos,
zona de caída libre y persona junto al paro, con otros mandos detenidos.
No admite --yes/--fast ni repite una apertura ya intentada.
EOF
    exit 0 ;;
  *) echo 'ERROR: opción no permitida; use --help.' >&2; exit 2 ;;
esac
exec "$script_dir/cruzr_blue_workbin_cycle.sh" "$mode"
