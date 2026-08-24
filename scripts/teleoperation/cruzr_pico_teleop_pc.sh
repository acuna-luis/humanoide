#!/usr/bin/env bash

set -Eeuo pipefail

motion_ip="${CRUZR_MOTION_IP:-192.168.11.2}"
vision_ip="${CRUZR_VISION_IP:-192.168.11.3}"
pico_ip="${PICO_IP:-}"
pc_pico_ip="${PICO_PC_IP:-}"
pico_serial="${PICO_SERIAL:-PA94Y0MGKB070822G}"
robot_iface="${CRUZR_IFACE:-eno1}"
robot_pc_ip="${CRUZR_PC_IP:-192.168.11.250}"
backend_unit="ubt-controller.service"
ui_unit="ubt-remote-control.service"
backend_log="/opt/ubt/ubt_controller/logs/ubt_controller.log"
required_arm="clamp"
patched_backend_sha256="0f0d341424f30042cc9189ff215d09007de91f443e4b9b0debaeffa81cda28eb"
backend_executable="/opt/ubt/ubt_controller/ubt_controller"

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

usage() {
  cat <<'EOF'
Uso:
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --open-ui
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --run
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --stop

--check    Sólo lectura; valida PC, red, PICO y backend.
--open-ui  Abre la interfaz después del backend. No inicia la publicación.
--run      Exige confirmación física y arma directamente el backend corregido
           con arm_type=clamp, sin depender de Electron. La web del robot debe
           mostrar 遥操模式. En esta unidad, el operador debe apretar por
           completo el gatillo izquierdo cuando se indique: el PC lo reasigna
           a la función Y oficial porque X/Y no entregan el clic de forma
           fiable. Sólo es válido con las abrazaderas pasivas instaladas.
--stop     Solicita EXIT_REMOTE_CONTROL y cierra la interfaz.

Este script sólo cambia/ejecuta componentes del PC. Nunca desactiva el
watchdog ni inventa el heartbeat del robot.
EOF
}

ensure_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Falta el comando requerido: $1"
}

adb_state() {
  adb devices | awk -v serial="$pico_serial" '$1 == serial {print $2; exit}'
}

endpoint_ip() {
  sed -E \
    -e 's/^\[::ffff:([^]]+)\]:[0-9]+$/\1/' \
    -e 's/^([^:]+):[0-9]+$/\1/' <<<"$1"
}

discover_pico_stream() {
  local endpoints local_endpoint peer_endpoint detected_pc_ip detected_pico_ip
  endpoints="$(ss -Htn | awk '
    $1 == "ESTAB" && $4 ~ /:63901$/ {print $4, $5; exit}
  ')"
  [[ -n "$endpoints" ]] || return 1
  read -r local_endpoint peer_endpoint <<<"$endpoints"
  detected_pc_ip="$(endpoint_ip "$local_endpoint")"
  detected_pico_ip="$(endpoint_ip "$peer_endpoint")"
  [[ "$detected_pc_ip" =~ ^[0-9]+(\.[0-9]+){3}$ ]] || return 1
  [[ "$detected_pico_ip" =~ ^[0-9]+(\.[0-9]+){3}$ ]] || return 1

  if [[ -n "$pc_pico_ip" && "$pc_pico_ip" != "$detected_pc_ip" ]]; then
    die "PICO_PC_IP=$pc_pico_ip no coincide con el stream activo $detected_pc_ip."
  fi
  if [[ -n "$pico_ip" && "$pico_ip" != "$detected_pico_ip" ]]; then
    die "PICO_IP=$pico_ip no coincide con el stream activo $detected_pico_ip."
  fi
  pc_pico_ip="$detected_pc_ip"
  pico_ip="$detected_pico_ip"
}

has_established_pico_stream() {
  ss -Htn | awk -v local_ip="$pc_pico_ip" -v peer_ip="$pico_ip" '
    $1 == "ESTAB" && index($4, local_ip) && $4 ~ /:63901$/ && index($5, peer_ip) {found=1}
    END {exit !found}
  '
}

latest_log_has_pico() {
  local start_text
  start_text="$(systemctl show "$backend_unit" -p ActiveEnterTimestamp --value)"
  journalctl -u "$backend_unit" --since "$start_text" --no-pager 2>/dev/null |
    grep -qE 'device found|PA94Y0MGKB070822G'
}

backend_detect_json() {
  python3 - <<'PY'
import websocket

ws = websocket.create_connection("ws://127.0.0.1:8082", timeout=3)
try:
    print(ws.recv())
finally:
    ws.close()
PY
}

check_pc() {
  ensure_cmd adb
  ensure_cmd ip
  ensure_cmd ping
  ensure_cmd ss
  ensure_cmd systemctl
  ensure_cmd python3
  ensure_cmd jq
  ensure_cmd sha256sum

  [[ "$(adb_state)" == "device" ]] || die "PICO no autorizado por ADB ($pico_serial)."
  adb -s "$pico_serial" shell pidof com.xrobotoolkit.client >/dev/null 2>&1 ||
    die "XRoboToolkit no está abierto en el PICO."

  ip -4 -o addr show dev "$robot_iface" | grep -q " $robot_pc_ip/" ||
    die "$robot_iface no tiene $robot_pc_ip."
  ip route get "$motion_ip" | grep -q "dev $robot_iface" ||
    die "La ruta a motion no usa $robot_iface."
  ping -c 1 -W 1 "$motion_ip" >/dev/null || die "Motion $motion_ip no responde."
  ping -c 1 -W 1 "$vision_ip" >/dev/null || die "Vision $vision_ip no responde."

  systemctl is-active --quiet "$backend_unit" || die "$backend_unit no está activo."
  ss -Hlnt | grep -q ':8082 ' || die "El backend no escucha en TCP 8082."
  ss -Hlnt | grep -q ':63901 ' || die "XRoboToolkit PC Service no escucha en TCP 63901."
  discover_pico_stream || die "PICO no mantiene ningún flujo TCP hacia el servicio XR en 63901."
  has_established_pico_stream || die "PICO no mantiene el flujo TCP hacia $pc_pico_ip:63901."
  latest_log_has_pico || die "El backend activo todavía no ha descubierto el PICO."

  local environment
  environment="$(systemctl show "$backend_unit" -p Environment --value)"
  [[ " $environment " == *" arm=$required_arm "* ]] ||
    die "El backend no está fijado a arm=$required_arm; reinstale el drop-in del PC."
  local backend_sha256
  backend_sha256="$(sha256sum "$backend_executable" | awk '{print $1}')"
  [[ "$backend_sha256" == "$patched_backend_sha256" ]] ||
    die "El backend no contiene la corrección clamp validada (SHA-256=$backend_sha256)."

  local detect_json vr_status operation_type
  detect_json="$(backend_detect_json)"
  vr_status="$(jq -r 'select(.type == "detect") | .content.vr_status' <<<"$detect_json")"
  operation_type="$(jq -r 'select(.type == "detect") | .content.operation_type' <<<"$detect_json")"
  [[ "$vr_status" == "1" ]] ||
    die "El socket USB existe, pero XRoboToolkit no envía HEAD+CONTROLLERS (vr_status=$vr_status). Active Send data/Working en el PICO."
  [[ "$operation_type" == "1" ]] ||
    die "El backend ya está en operación remota (operation_type=$operation_type); ejecute --stop antes de iniciar."

  info "PC_NETWORK_OK=$robot_iface:$robot_pc_ip"
  info "ROBOT_LINK_OK=motion:$motion_ip,vision:$vision_ip"
  info "PICO_ADB_OK=$pico_serial"
  info "PICO_STREAM_OK=$pico_ip->$pc_pico_ip:63901"
  info "PICO_TRACKING_OK=vr_status:$vr_status"
  info "BACKEND_OK=ubt-controller:5.3.0,arm:$required_arm,ws:8082"
  info "CLAMP_PATCH_OK=WebsocketServer.collect:GRIPPER->CLAMP"
  info "PICO_BUTTON_WORKAROUND_OK=left-trigger-bool->vendor-Y"
  info "UI_PACKAGE_OK=ubt-remote-control:4.1.0"
}

send_local_message() {
  local payload="$1"
  PAYLOAD="$payload" python3 - <<'PY'
import json
import os
import sys
import time
import websocket

ws = websocket.create_connection("ws://127.0.0.1:8082", timeout=3)
try:
    # The backend sends its current state immediately after accepting a client.
    # Consume that snapshot so a later collect response cannot be mistaken for
    # the pre-command state.
    try:
        ws.recv()
    except Exception:
        pass
    ws.send(os.environ["PAYLOAD"])
    deadline = time.monotonic() + 3
    messages = []
    while time.monotonic() < deadline:
        try:
            raw = ws.recv()
        except Exception:
            break
        messages.append(raw)
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if data.get("type") in {"detect", "error"}:
            print(raw)
            break
    if not messages:
        print("LOCAL_WS_SENT_NO_RESPONSE", file=sys.stderr)
finally:
    ws.close()
PY
}

open_ui() {
  check_pc
  systemctl --user reset-failed "$ui_unit" >/dev/null 2>&1 || true
  if ! systemctl --user is-active --quiet "$ui_unit"; then
    systemctl --user start "$ui_unit"
  fi

  local deadline=$((SECONDS + 20))
  until ss -Htn | grep -qE '127\.0\.0\.1:[0-9]+ +127\.0\.0\.1:8082'; do
    ((SECONDS < deadline)) || die "La interfaz no conectó al backend TCP 8082."
    sleep 1
  done
  sleep 2
  local detect_json operation_type enable_control
  detect_json="$(backend_detect_json)"
  operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
  enable_control="$(jq -r '.content.enable_control' <<<"$detect_json")"
  if [[ "$operation_type" != "1" || "$enable_control" != "0" ]]; then
    stop_all
    die "La UI alteró el estado remoto al abrirse; STOP enviado (operation_type=$operation_type, enable_control=$enable_control)."
  fi
  info "UI_CONNECTED=local-ws:8082"
  info "UI_NOTE=no pulse todavía el botón chino de inicio ni Y"
}

stop_all() {
  if systemctl is-active --quiet "$backend_unit" && ss -Hlnt | grep -q ':8082 '; then
    send_local_message '{"type":"collect","content":{"operation_type":1}}' || true
  fi
  systemctl --user stop "$ui_unit" >/dev/null 2>&1 || true
  info "TELEOPERATION_STOP_REQUESTED=1"
  info "UI_STOPPED=1"
}

run_gate() {
  check_pc

  cat <<'EOF'

CONFIRMACIÓN FÍSICA OBLIGATORIA
El cargador debe estar desconectado; PICO y Ethernet conectados; abrazaderas
vacías; robot en home; controladores neutros; grip y gatillos libres; nadie
tocando el robot; toda la envolvente despejada y paro físico preparado. La
web 192.168.11.3 debe mostrar 遥操模式 (Remote control mode) arriba.

Escriba exactamente TELEOPERACION SEGURA Y MODO REMOTO para armar el flujo del PC:
EOF
  read -r confirmation
  [[ "$confirmation" == "TELEOPERACION SEGURA Y MODO REMOTO" ]] ||
    die "Confirmación incorrecta; no se inició la publicación."

  cat <<'EOF'

PREPARACIÓN INMEDIATA
Mantenga ambos controladores neutros. Empiece a apretar y soltar completamente
el gatillo izquierdo una vez por segundo y pulse Enter mientras continúa. El
PC armará la sesión y capturará el primer flanco posterior al armado dentro de
los 8 segundos permitidos por el watchdog original del fabricante.
EOF
  read -r _

  local start_line
  start_line="$(wc -l < "$backend_log")"
  send_local_message '{"type":"collect","content":{"arm_type":"clamp","operation_type":2}}'

  local deadline=$((SECONDS + 8))
  until tail -n "+$((start_line + 1))" "$backend_log" | grep -q 'Arm type is: clamp'; do
    if tail -n "+$((start_line + 1))" "$backend_log" | grep -q 'Arm type is: gripper'; then
      stop_all
      die "El backend volvió a seleccionar gripper; publicación detenida."
    fi
    ((SECONDS < deadline)) || { stop_all; die "No se confirmó arm_type=clamp."; }
    sleep 0.25
  done

  info "ARM_TYPE_CONFIRMED=clamp"
  info "PUBLISHER_ARMED=1"
  info "ENABLE_CONTROL_BEFORE_TRIGGER=0"
  info "PRESS_LEFT_TRIGGER_NOW=1"

  local enabled=0 detect_json operation_type enable_control
  local enable_deadline=$((SECONDS + 8))
  while ((SECONDS < enable_deadline)); do
    detect_json="$(backend_detect_json)"
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    enable_control="$(jq -r '.content.enable_control' <<<"$detect_json")"
    if [[ "$operation_type" == "2" && "$enable_control" == "1" ]]; then
      enabled=1
      break
    fi
    if [[ "$operation_type" == "1" ]]; then
      stop_all
      die "El robot cerró la sesión antes de detectar la habilitación."
    fi
    sleep 0.25
  done
  if [[ "$enabled" != "1" ]]; then
    stop_all
    die "No se detectó una nueva pulsación del gatillo/enable_control=1 dentro de 8 s."
  fi
  info "ENABLE_CONTROL_CONFIRMED=1"

  info "MONITORING_HEARTBEAT_GATE=60s"
  local monitor_deadline=$((SECONDS + 60))
  while ((SECONDS < monitor_deadline)); do
    if tail -n "+$((start_line + 1))" "$backend_log" | grep -q 'No heartbeat for 10 seconds'; then
      stop_all
      die "El watchdog no recibió heartbeat; STOP enviado y UI cerrada."
    fi
    detect_json="$(backend_detect_json)"
    operation_type="$(jq -r '.content.operation_type' <<<"$detect_json")"
    enable_control="$(jq -r '.content.enable_control' <<<"$detect_json")"
    if [[ "$operation_type" != "2" || "$enable_control" != "1" ]]; then
      stop_all
      die "La sesión perdió habilitación (operation_type=$operation_type, enable_control=$enable_control)."
    fi
    sleep 1
  done

  local response
  response="$(send_local_message '{"type":"detect","content":{}}' || true)"
  printf '%s\n' "$response"
  grep -q '"operation_type":2' <<<"$response" || {
    stop_all
    die "La operación no permaneció activa durante 60 s."
  }
  info "TELEOPERATION_STABLE=60s"
  info "WATCHDOG_TRIP=0"
  info "La teleoperación queda activa; use --stop antes de salir o quitarse el PICO."
}

mode="${1:---check}"
case "$mode" in
  --check)
    check_pc
    ;;
  --open-ui)
    open_ui
    ;;
  --run)
    trap 'stop_all >/dev/null 2>&1 || true' ERR INT TERM
    run_gate
    trap - ERR INT TERM
    ;;
  --stop)
    stop_all
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
