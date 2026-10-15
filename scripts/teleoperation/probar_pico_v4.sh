#!/usr/bin/env bash
set -Eeuo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mode="${1:---check}"
(($# <= 1)) || { printf 'Sólo se admite una opción.\n' >&2; exit 2; }
case "$mode" in
  --check) mode=--check-motion-ready ;;
  --check-arms-only|--teleoperate|--stop) ;;
  --help|-h)
    printf '%s\n' \
      'Uso: bash scripts/teleoperation/probar_pico_v4.sh [--check|--check-arms-only|--teleoperate|--stop]' \
      'Por defecto sólo comprueba. --teleoperate exige perfil v4 sólo brazos cargado,' \
      'estados frescos de siete articulaciones por mano y confirmación física.' \
      'Grips: brazos. Gatillos: apertura/cierre según perfil vendor; ensayo v4 pendiente.' \
      'No habilita seguimiento óptico de dedos, cintura, elevador ni chasis.'
    exit 0 ;;
  *) printf 'Opción v4 no admitida: %s\n' "$mode" >&2; exit 2 ;;
esac
export PICO_EFFECTOR=v4
exec bash "$script_dir/cruzr_pico_teleop_pc.sh" "$mode"
