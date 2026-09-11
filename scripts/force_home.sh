#!/usr/bin/env bash
set -Eeuo pipefail

readonly MOTION_HOST="192.168.11.2"
readonly WIFI_GATEWAY="192.168.42.2"

readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"

# SSH ejecuta este mismo archivo para obtener la contraseña.
# Debe ir antes del procesamiento de argumentos.
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
    printf '%s\n' "$DEFAULT_PASSWORD"
    exit 0
fi

readonly SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"

trap 'printf "Error en la línea %s (código %s)\n" "$LINENO" "$?" >&2' ERR

case "${1:-}" in
    "")     MOTION_SSH_HOST="$MOTION_HOST" ;;
    --wifi) MOTION_SSH_HOST="$WIFI_GATEWAY" ;;
    *)
        printf 'Uso: %s [--wifi]\n' "$0" >&2
        exit 2
        ;;
esac
readonly MOTION_SSH_HOST

if [[ ! -x "$SCRIPT_PATH" ]]; then
    printf 'El script necesita permiso de ejecución:\nchmod +x "%s"\n' \
        "$SCRIPT_PATH" >&2
    exit 1
fi

ssh_motion() {
    CRUZR_INTERNAL_ASKPASS=1 \
    SSH_ASKPASS="$SCRIPT_PATH" \
    SSH_ASKPASS_REQUIRE=force \
    DISPLAY="${DISPLAY:-:0}" \
    setsid -w ssh -T \
        -o ConnectTimeout=8 \
        -o ConnectionAttempts=1 \
        -o ServerAliveInterval=5 \
        -o ServerAliveCountMax=3 \
        -o PreferredAuthentications=password \
        -o PubkeyAuthentication=no \
        -o NumberOfPasswordPrompts=2 \
        -o StrictHostKeyChecking=accept-new \
        "${ROBOT_USER}@${MOTION_SSH_HOST}" "$@"
}

ssh_motion bash -se <<'REMOTE'
set -Eeuo pipefail

readonly CONTAINER="walker-motion.manipulation_robot_app-1"

echo "Conectado al robot: $(hostname)"

docker exec -i "$CONTAINER" bash -lc '
    set -eo pipefail

    source /opt/walker/setup.bash
    export ROS2CLI_DISABLE_DAEMON=1

    rosa action send_goal \
        /mc/manipulation/action \
        mc_task_msgs/action/ArmTask \
        "{\"task_name\":\"cruzr/home\",\"yaml_args\":\"{}\"}"
'

echo "Comando finalizado."
REMOTE