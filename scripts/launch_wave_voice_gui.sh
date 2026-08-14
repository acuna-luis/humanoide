#!/usr/bin/env bash

set -u
umask 077

SCRIPT_DIR="$(dirname -- "$(readlink -f -- "$0")")"
readonly SCRIPT_DIR
readonly CONTROL_SCRIPT="$SCRIPT_DIR/install_wave_both_arms.sh"
readonly STATE_DIR="${XDG_STATE_HOME:-/home/lacuna/.local/state}/cruzr-s2"

mkdir -p "$STATE_DIR"
exec 9>"$STATE_DIR/voice-wave.lock"

if ! flock -n 9; then
  zenity --warning \
    --title="Cruzr S2" \
    --text="Ya hay una sesión de voz para los brazos en ejecución."
  exit 1
fi

log_file="$STATE_DIR/voice-wave-$(date +%Y%m%d-%H%M%S).log"
notify-send "Cruzr S2" "Iniciando el control de voz de un solo uso..." || true

if "$CONTROL_SCRIPT" --voice-gui >>"$log_file" 2>&1; then
  zenity --info \
    --title="Cruzr S2" \
    --text="Movimiento completado. El control de voz se ha desarmado."
  exit 0
else
  status=$?
fi

zenity --error \
  --title="Cruzr S2: no se realizó el movimiento" \
  --width=520 \
  --text="La sesión terminó o fue cancelada sin mover el robot.\n\nRegistro: $log_file"
exit "$status"
