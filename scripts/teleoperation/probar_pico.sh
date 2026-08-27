#!/usr/bin/env bash

set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
gate_script="$script_dir/cruzr_pico_teleop_pc.sh"
mode="${1:---check}"

usage() {
  cat <<EOF
Uso:
  $0 --check
  $0 --check-arms-only
  $0 --check-reload-ready
  $0 --check-motion-ready
  $0 --teleoperate
  $0 --move-left-arm
  $0 --move-right-arm
  $0 --all-controls
  $0 --gate-only

Sin opción ejecuta --check, que es de sólo lectura. El PC tiene actualmente la
combinación oficial robot v0.2.0 + controller 4.7.0 + UI 4.1.0. Los modos que
usan el gate antiguo permanecen bloqueados. --teleoperate sólo permite brazos
y exige demostrar que la tarea Motion clamp viva cargó waist_mode=0 y
leg_mode=0. Permite uno o ambos brazos; PICO_ALLOW_BIMANUAL=0 restaura el
bloqueo estricto de solapamiento. Los modos --move-*-arm, --all-controls y
--gate-only todavía dependen de enable_control de 5.3.0.
EOF
}

if (($# > 1)); then
  usage >&2
  exit 2
fi

case "$mode" in
  --check|--check-arms-only|--check-reload-ready|--check-motion-ready|--teleoperate|--move-left-arm|--move-right-arm|--all-controls)
    ;;
  --gate-only)
    mode="--gate-local"
    ;;
  --help|-h)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

[[ -x "$gate_script" ]] || {
  printf 'ERROR: no se puede ejecutar el gate canónico: %s\n' "$gate_script" >&2
  exit 1
}

case "$mode" in
  --check)
    printf '\nDIAGNÓSTICO 4.7.0 DE SÓLO LECTURA — NO ENVÍA START\n\n'
    ;;
  --check-motion-ready)
    printf '\nPREFLIGHT 4.7.0 DE SÓLO LECTURA — NO ENVÍA START NI MOVIMIENTO\n\n'
    ;;
  --check-arms-only)
    printf '\nVERIFICACIÓN DEL PERFIL MOTION ARMS-ONLY — NO ENVÍA START NI MOVIMIENTO\n\n'
    ;;
  --check-reload-ready)
    printf '\nSEGURIDAD MOTION PARA RECARGA — NO CAMBIA DE MODO NI ENVÍA MOVIMIENTO\n\n'
    ;;
  --teleoperate)
    printf '\nTELEOPERACIÓN OFICIAL 4.7.0 CON PREFLIGHT Y STOP AUTOMÁTICO\n\n'
    ;;
  *)
    [[ -t 0 && -t 1 ]] || {
      printf 'ERROR: ejecute los modos físicos directamente en un terminal local del PC.\n' >&2
      exit 1
    }
    cat <<'EOF'

MOVIMIENTO BLOQUEADO EN EL BASELINE OFICIAL 4.7.0

Se retiraron los parches de 5.3.0 (CLAMP forzado, gatillo izquierdo como Y y
watchdog de 300 s). En la prueba oficial 4.7.0 del 26-08, Y produjo enable=1,
el grip llegó al backend y pico_control dejó operation_type=1 al terminar. El
rearme observado después fue causado por un segundo cliente diagnóstico que
permaneció conectado tras STOP, no por pico_control. Este gate solicitará STOP
y terminará sin START hasta migrar su monitor al protocolo oficial 4.7.0.

EOF
    ;;
esac

exec "$gate_script" "$mode"
