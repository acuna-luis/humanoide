#!/usr/bin/env bash

set -Eeuo pipefail

# Ejecuta el TTS ingles del Cruzr S2 desde este PC mediante SSH.
# La contrasena se entrega con SSH_ASKPASS y no aparece en la linea de procesos.

readonly VISION_HOST="192.168.11.3"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly TTS_CONTAINER="walker-voice.speech_service-1"
readonly TTS_ACTION="/sys/speech/tts"
readonly TTS_TYPE="sys_task_msgs/action/Tts"
readonly DEFAULT_TEXT="Hello, I am Cruzr S2."

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD

# ssh invoca este mismo archivo para obtener la contrasena.
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

SCRIPT_PATH="$(readlink -f -- "$0")"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/cruzr_say_english.sh
  ./scripts/cruzr_say_english.sh "Welcome to our factory."
  ./scripts/cruzr_say_english.sh --check
  ./scripts/cruzr_say_english.sh --help

Sin texto utiliza: "Hello, I am Cruzr S2."
--check comprueba la conexion y el servicio TTS sin reproducir audio.

Para usar otra contrasena sin modificar el archivo:
  CRUZR_SSH_PASSWORD='otra' ./scripts/cruzr_say_english.sh "Hello."
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

ssh_vision() {
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w ssh \
    -o ConnectTimeout=6 \
    -o ConnectionAttempts=1 \
    -o ServerAliveInterval=5 \
    -o ServerAliveCountMax=2 \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -o NumberOfPasswordPrompts=1 \
    -o StrictHostKeyChecking=accept-new \
    "$ROBOT_USER@$VISION_HOST" "$@"
}

build_goal() {
  local text="$1"

  python3 - "$text" <<'PY'
import base64
import json
import sys
import unicodedata

text = unicodedata.normalize("NFC", sys.argv[1]).strip()
if not text:
    raise SystemExit("El texto esta vacio.")
if len(text) > 500:
    raise SystemExit("El texto supera el limite de 500 caracteres.")
if any(ord(char) < 32 and char not in "\t" for char in text):
    raise SystemExit("El texto contiene caracteres de control.")

goal = {
    "type": 1,
    "is_break": True,
    "file_path": "",
    "text": text,
    "speaker": "",
    "speed": 50,
    "volume": 100,
    "pitch": 50,
    "language": "en",
    "format": "wav",
    "need_save": True,
}
encoded = base64.b64encode(
    json.dumps(goal, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
)
print(encoded.decode("ascii"))
PY
}

main() {
  local mode="say"
  local text="$DEFAULT_TEXT"
  # El marcador evita que SSH elimine un ultimo argumento vacio en --check.
  local goal_b64="-"

  case "${1:-}" in
    --help|-h)
      usage
      exit 0
      ;;
    --check)
      [[ $# -eq 1 ]] || die "--check no acepta texto."
      mode="check"
      ;;
    --*)
      usage >&2
      die "Opcion desconocida: $1"
      ;;
    "")
      ;;
    *)
      text="$*"
      ;;
  esac

  command -v ssh >/dev/null 2>&1 || die "No esta instalado el cliente ssh."
  command -v setsid >/dev/null 2>&1 || die "No esta instalado setsid."
  command -v python3 >/dev/null 2>&1 || die "No esta instalado python3."

  if [[ "$mode" == "say" ]]; then
    goal_b64="$(build_goal "$text")" || die "El texto no es valido."
    printf 'Enviando al Cruzr S2: %s\n' "$text"
  else
    printf 'Comprobando el TTS del Cruzr S2 sin reproducir audio...\n'
  fi

  ssh_vision bash -s -- \
    "$mode" "$TTS_CONTAINER" "$TTS_ACTION" "$TTS_TYPE" "$goal_b64" <<'REMOTE'
set -Eeuo pipefail

mode="$1"
container="$2"
action_name="$3"
action_type="$4"
goal_b64="$5"

[[ "$(hostname)" == "vision" ]] || {
  printf 'ERROR: el host remoto no es vision: %s\n' "$(hostname)" >&2
  exit 20
}

[[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == "true" ]] || {
  printf 'ERROR: el contenedor %s no esta activo.\n' "$container" >&2
  exit 21
}

action_info="$(docker exec "$container" bash -lc \
  'source /opt/walker/setup.bash && rosa action info /sys/speech/tts')" || {
  printf 'ERROR: no fue posible consultar el servicio TTS.\n' >&2
  exit 22
}
printf '%s\n' "$action_info"
grep -q 'Action: sys_task_msgs/action/Tts' <<<"$action_info" || {
  printf 'ERROR: el tipo de la accion TTS no coincide.\n' >&2
  exit 23
}
grep -q 'Action server count: 1' <<<"$action_info" || {
  printf 'ERROR: no hay exactamente un servidor TTS disponible.\n' >&2
  exit 24
}

if [[ "$mode" == "check" ]]; then
  printf 'TTS_CHECK_OK: conexion, contenedor y servidor disponibles.\n'
  exit 0
fi

goal="$(printf '%s' "$goal_b64" | base64 --decode)" || {
  printf 'ERROR: no se pudo decodificar la peticion TTS.\n' >&2
  exit 25
}

result="$(docker exec "$container" bash -lc '
  source /opt/walker/setup.bash
  timeout 60 rosa action send_goal "$1" "$2" "$3"
' _ "$action_name" "$action_type" "$goal")" || {
  printf 'ERROR: la accion TTS fallo. No se repetira automaticamente.\n' >&2
  exit 26
}

printf '%s\n' "$result"
grep -q "desc.*SUCCEED" <<<"$result" && grep -q 'status=4' <<<"$result" || {
  printf 'ERROR: TTS no devolvio SUCCEED/status=4.\n' >&2
  exit 27
}
printf 'TTS_OK: frase inglesa reproducida correctamente.\n'
REMOTE
}

main "$@"
