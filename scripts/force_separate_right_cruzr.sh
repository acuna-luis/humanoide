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

docker exec -i "$CONTAINER" bash -s <<'INNER'
set -Eeo pipefail

# El setup del proveedor consulta variables opcionales como COLCON_TRACE.
# Cárguelo sin nounset y vuelva a activar nounset para el ejecutor.
set +u
source /opt/walker/setup.bash
set -u
export ROS2CLI_DISABLE_DAEMON=1

run_task_once() {
    local task_name="$1"
    local timeout_seconds="$2"
    local output

    printf '\nEjecutando acción: %s\n' "$task_name"
    output="$(timeout "$timeout_seconds" rosa action send_goal \
        /mc/manipulation/action \
        mc_task_msgs/action/ArmTask \
        "{\"task_name\":\"${task_name}\",\"yaml_args\":\"{}\"}")"
    printf '%s\n' "$output"

    if ! grep -q "'desc': 'SUCCEED'" <<<"$output"; then
        printf 'ERROR: Motion no informó SUCCEED para %s. No se reintentará.\n' \
            "$task_name" >&2
        return 50
    fi
    if ! grep -q 'status=4' <<<"$output"; then
        printf 'ERROR: la acción %s no terminó con status=4. No se reintentará.\n' \
            "$task_name" >&2
        return 51
    fi

    printf 'Acción finalizada correctamente: %s\n' "$task_name"
}

# El árbol completo del escenario 1 habilita este modo después de navegar.
# Una llamada directa al agarre debe reproducir ese prerrequisito.
run_task_once "vision/enable_transport_vision_switch" 20
sleep 1
run_task_once "Singapore/separate_right_cruzr" 45
INNER

echo "La visión de transporte y la separación derecha han finalizado correctamente."
REMOTE
