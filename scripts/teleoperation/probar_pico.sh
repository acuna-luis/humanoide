#!/usr/bin/env bash

set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
gate_script="$script_dir/cruzr_pico_teleop_pc.sh"

mode="--move-right-arm"
if (($# > 1)); then
  printf 'Uso: %s [--move-left-arm|--move-right-arm|--all-controls|--gate-only]\n' "$0" >&2
  exit 2
fi
case "${1:-}" in
  "")
    ;;
  --move-left-arm|--move-right-arm|--all-controls)
    mode="$1"
    ;;
  --gate-only)
    mode="--gate-local"
    ;;
  --help|-h)
    cat <<EOF
Uso:
  $0
  $0 --move-left-arm
  $0 --move-right-arm
  $0 --all-controls
  $0 --gate-only

Sin opción ejecuta la prueba física real recomendada del brazo derecho. Los
modos --move-*-arm prueban un solo brazo y siempre envían STOP al soltar el
grip o ante cualquier fallo. --all-controls añade 60 s neutros y después una
ventana física integral de 120 s. --gate-only conserva el diagnóstico sin
maniobra.
EOF
    exit 0
    ;;
  *)
    printf 'Uso: %s [--move-left-arm|--move-right-arm|--all-controls|--gate-only]\n' "$0" >&2
    exit 2
    ;;
esac

if [[ ! -t 0 || ! -t 1 ]]; then
  printf 'ERROR: ejecute este lanzador directamente en un terminal local del PC.\n' >&2
  exit 1
fi

if [[ ! -x "$gate_script" ]]; then
  printf 'ERROR: no se puede ejecutar el gate canónico: %s\n' "$gate_script" >&2
  exit 1
fi

if [[ "$mode" == "--gate-local" ]]; then
  cat <<'EOF'

PRUEBA GUIADA PICO -> PC -> CRUZR S2

Siga únicamente las órdenes que aparezcan en este terminal.
No toque ningún gatillo hasta ver el aviso grande «TOQUE AHORA».
Cuando aparezca, apriete UNA vez el gatillo izquierdo y suéltelo. El backend
publica sólo el flanco inicial y el script confirma la liberación. No repita el
toque. Ctrl+C solicita STOP si necesita abortar.

Es una ventana diagnóstica de habilitación, no una prueba de maniobras ni una
validación de heartbeat. Por autorización del propietario, el watchdog de
heartbeat del backend se amplía temporalmente a 300 segundos; la ventana dura
60 segundos y después envía STOP. Habilitar la teleoperación sí puede mover el
robot: mantenga los mandos completamente neutros. Si cualquier gate restante
falla, también envía STOP.

El preflight muestra CHECK 1/7 ... CHECK 7/7 con timestamps. Si necesita una
traza Bash completa, aborte antes de armar y vuelva a ejecutar:
  CRUZR_TELEOP_DEBUG=1 ./scripts/teleoperation/probar_pico.sh

EOF
elif [[ "$mode" == "--all-controls" ]]; then
  cat <<'EOF'

TELEOPERACIÓN FÍSICA INTEGRAL PICO -> PC -> CRUZR S2

Este modo exige preflight PC/PICO/Motion, 60 segundos completamente neutros y
después permite durante 120 segundos los controles documentados del headset:
brazos, cintura, elevador, cabeza, modo móvil, chasis, reset y captura.

X y B son conmutadores: deben pulsarse por pares para volver a modo en sitio y
cerrar la captura. Los clicks de joystick conmutan protección de fuerza: si se
prueban, deben hacerse dos clicks separados para restaurarla. El gatillo
izquierdo ya actúa como enable/Y en esta build y no debe repetirse.
El mapeo publica sólo el flanco inicial y mantenerlo apretado no puede volver a
conmutar enable; el script exige además comprobar que quede liberado.

La prueba siempre solicita STOP al terminar, con Ctrl+C o ante cualquier
fallo. Requiere envolvente de brazos y suelo 360° despejados, una persona junto
al paro y otra atendiendo el terminal. El resumen final indica qué entradas se
observaron; una entrada ausente no autoriza una repetición inmediata.

EOF
else
  arm_name="izquierdo"
  [[ "$mode" == "--move-right-arm" ]] && arm_name="derecho"
  cat <<EOF

TELEOPERACIÓN FÍSICA PICO -> PC -> CRUZR S2 — BRAZO ${arm_name^^}

Este modo sí puede mover físicamente el robot. Ejecutará:

1. preflight PC/PICO y preflight Motion de paros, batería, cargador, efector,
   tarea PICO y velocidad articular;
2. START con arm_type=clamp y un único toque corto del gatillo izquierdo;
3. 60 segundos obligatorios con cabeza, mandos y grips quietos;
4. un solo gesto de 2-3 cm con el grip $arm_name, durante 5 s como máximo;
5. STOP inmediato al soltar el grip, con Ctrl+C o ante cualquier fallo.

No pulse el grip hasta el aviso «MUEVA SÓLO EL BRAZO». No toque el gatillo
otra vez después de habilitar. Deben participar una persona con el visor, otra
en el terminal y una persona situada junto al paro físico (pueden ser las dos
últimas la misma si mantiene acceso inmediato a ambos).

El brazo derecho es la primera prueba recomendada: después del toque de
habilitación, el mando izquierdo puede quedar completamente neutro.

El preflight actual bloqueará hasta que XRoboToolkit vuelva a mostrar
Head + Controllers / Send data / Working y el backend indique vr_status=1.

EOF
fi

exec "$gate_script" "$mode"
