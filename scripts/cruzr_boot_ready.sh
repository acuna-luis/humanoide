#!/usr/bin/env bash
# Comprobación de arranque desde el PC. No inicia/reinicia procesos del robot.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${1:---check}" in
  --help|-h)
    cat <<'HELP'
Uso: ./scripts/cruzr_boot_ready.sh --check

Espera hasta 7 minutos a Motion y las seis cámaras. Comprueba que Control Center
está en el arranque inicial, el E-stop principal pulsado, el secundario liberado
y el cargador desconectado. No mueve, rearma ni reinicia el robot.

Uso habitual: encender con brazos abajo y vacíos, zona libre y E-stop pulsado;
esperar la frase del robot "Ready to release the emergency stop".
Este comando es la alternativa si no se oye la voz. No sirve para recuperar
una detención durante PICO o una trayectoria.
HELP
    exit 0 ;;
  --check) [[ $# -le 1 ]] || exit 2 ;;
  *) printf 'Opción desconocida. Use --help.\n' >&2; exit 2 ;;
esac
printf 'ESPERA: comprobando arranque. Mantén el E-stop pulsado.\n'
export CRUZR_INTERNAL_ASKPASS=1
export SSH_ASKPASS="$SCRIPT_DIR/cruzr_recover_to_home.sh"
export SSH_ASKPASS_REQUIRE=force
export DISPLAY="${DISPLAY:-:0}"
if ! timeout 445 setsid -w ssh -o StrictHostKeyChecking=yes -o ConnectTimeout=5 \
    -o ServerAliveInterval=5 -o ServerAliveCountMax=2 \
    -o PreferredAuthentications=password -o PubkeyAuthentication=no \
    -o NumberOfPasswordPrompts=1 walker@192.168.11.3 \
    'timeout 435 python3 /etc/walker/boot/cruzr_boot_voice.py --check'; then
  printf 'NO LISTO: no se ha demostrado el estado de arranque. Mantén el paro pulsado.\n' >&2
  exit 1
fi
printf '\a\nLISTO PARA LIBERAR EL E-STOP (comprobación técnica del arranque).\n'
printf 'Con brazos abajo/vacíos, zona libre y persona junto al paro, puedes liberarlo.\n'
printf 'Puede comenzar el HOME interno. Espera después el autodiagnóstico y el fin del arranque.\n'
