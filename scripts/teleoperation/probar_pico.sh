#!/usr/bin/env bash

set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
gate_script="$script_dir/cruzr_pico_teleop_pc.sh"

if (($# != 0)); then
  printf 'Uso: %s\n' "$0" >&2
  exit 2
fi

if [[ ! -t 0 || ! -t 1 ]]; then
  printf 'ERROR: ejecute este lanzador directamente en un terminal local del PC.\n' >&2
  exit 1
fi

if [[ ! -x "$gate_script" ]]; then
  printf 'ERROR: no se puede ejecutar el gate canónico: %s\n' "$gate_script" >&2
  exit 1
fi

cat <<'EOF'

PRUEBA GUIADA PICO -> PC -> CRUZR S2

Siga únicamente las órdenes que aparezcan en este terminal.
No toque ningún gatillo hasta ver el aviso grande «TOQUE AHORA».
Cuando aparezca, haga UN toque completo de menos de 0,5 segundos y suéltelo.
No mantenga ni repita el toque. Ctrl+C solicita STOP si necesita abortar.

Es un gate de habilitación y heartbeat, no una prueba de maniobras. Habilitar la
teleoperación sí puede mover el robot: mantenga los mandos completamente neutros.
El terminal muestra progreso durante 60 segundos y después envía STOP. Si
cualquier gate falla, también envía STOP.

EOF

exec "$gate_script" --gate-local
