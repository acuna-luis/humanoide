#!/usr/bin/env bash
# Configure only ADB reverse for XR; never send START or robot commands.
set -Eeuo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
serial="${PICO_SERIAL:-PA94Y0MGKB070822G}"
mode="${1:---check}"
case "$mode" in
  --help|-h)
    printf 'Uso: bash %s --check|--configure|--remove\n' "$0"
    printf 'XR por USB: PICO PC service IP=127.0.0.1, puerto63901. No inicia movimiento.\n'
    exit 0 ;;
  --check|--configure|--remove) ;;
  *) printf 'Modo inválido\n' >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || exit 2
command -v adb >/dev/null
devices="$(timeout 5 adb devices -l)"
device_line="$(awk -v serial="$serial" '$1==serial && $2=="device" {print}' <<<"$devices")"
[[ "$device_line" == *usb:* ]] || {
  printf 'PICO físico no disponible por USB: %s\n' "$serial" >&2; exit 2;
}
identity="$(timeout 5 adb -s "$serial" shell getprop ro.serialno | tr -d '\r')"
[[ "$identity" == "$serial" ]] || exit 2
# Read the established passive helper; do not open a backend WebSocket, which
# can start its publisher in 4.7.0 merely by connecting while PICO is online.
python3 - "$script_dir/cruzr_pico_teleop_pc.sh" <<'PY'
import json
from pathlib import Path
import subprocess
import sys

source = Path(sys.argv[1]).read_text()
function = 'backend_passive_state_json() {' + source.split(
    'backend_passive_state_json() {', 1)[1].split('\ncheck_pc() {', 1)[0]
setup = ('command_timeout_seconds=5\nbackend_unit=ubt-controller.service\n'
         'backend_log=/opt/ubt/ubt_controller/logs/ubt_controller.log\n')
r = subprocess.run(['bash', '-c', setup + function + '\nbackend_passive_state_json'],
                   capture_output=True, text=True, timeout=7)
if r.returncode or json.loads(r.stdout)['content']['operation_type'] != 1:
    sys.exit('XR_USB_BLOCKED: STOP del backend no confirmado; no se modifica transporte')
print('BACKEND_STOP_CONFIRMED=1; source=passive-log')
PY
if [[ "$mode" == --remove ]]; then
  timeout 5 adb -s "$serial" reverse --remove tcp:63901
  printf 'XR_USB_REVERSE_REMOVED=1\n'
  exit 0
fi
listeners="$(ss -Hltn '( sport = :63901 )')"
[[ -n "$listeners" ]] || { printf 'Servicio XR no escucha63901\n' >&2; exit 2; }
if [[ "$mode" == --configure ]]; then
  timeout 5 adb -s "$serial" reverse tcp:63901 tcp:63901
fi
reverse="$(timeout 5 adb -s "$serial" reverse --list)"
awk '$2=="tcp:63901" && $3=="tcp:63901" {found=1} END {exit !found}' <<<"$reverse"
printf 'XR_USB_REVERSE_OK=1\nPICO_PC_SERVICE_IP=127.0.0.1\n'
printf 'Este check verifica el túnel; comprobar flujo/tracking con probar_pico.sh --check.\n'
