#!/usr/bin/env bash
# Mantiene los túneles ADB del PICO por USB mientras se teleopera:
#   reverse tcp:63901 (control XR, PICO -> PC 127.0.0.1)
#   forward tcp:12345 (vídeo, PC 127.0.0.1 -> listener del PICO)
# El PICO 4 Ultra se re-enumera por USB (reposo, ponerse/quitarse el visor) y
# ADB borra ambas reglas. Este bucle sólo las recrea; no envía órdenes al robot
# ni toca el backend. Una sesión de teleoperación ya caída no se reanuda sola.
# Uso: bash scripts/teleoperation/pico_usb_tunnel_keepalive.sh   (Ctrl+C para salir)
set -uo pipefail
serial="${PICO_SERIAL:-PA94Y0MGKB070822G}"
interval="${PICO_KEEPALIVE_INTERVAL:-2}"
video="${PICO_KEEPALIVE_VIDEO:-1}"   # 0 = sólo control
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

log "Vigilando PICO $serial: control 63901, vídeo 12345=$([[ $video == 1 ]] && echo sí || echo no). Ctrl+C para salir."
present_before=""
while true; do
  state="$(timeout 5 adb devices 2>/dev/null | awk -v s="$serial" '$1==s{print $2}')"
  if [[ "$state" != "device" ]]; then
    [[ "$present_before" == 0 ]] || log "PICO no disponible por USB (estado='${state:-ausente}'); esperando…"
    present_before=0
  else
    [[ "$present_before" == 1 ]] || log "PICO presente por USB."
    present_before=1
    if ! timeout 5 adb -s "$serial" reverse --list 2>/dev/null | grep -q 'tcp:63901 tcp:63901'; then
      if timeout 5 adb -s "$serial" reverse tcp:63901 tcp:63901 >/dev/null 2>&1; then
        log "REVERSE_RESTORED tcp:63901 -> reconecte en el visor si la app muestra error."
      else
        log "No se pudo crear reverse 63901; reintentando."
      fi
    fi
    if [[ "$video" == 1 ]] && ! timeout 5 adb forward --list 2>/dev/null | grep -q "^$serial tcp:12345 tcp:12345"; then
      if timeout 5 adb -s "$serial" forward tcp:12345 tcp:12345 >/dev/null 2>&1; then
        log "FORWARD_RESTORED tcp:12345 (vídeo)."
      else
        log "No se pudo crear forward 12345; reintentando."
      fi
    fi
  fi
  sleep "$interval"
done
