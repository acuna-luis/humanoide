#!/usr/bin/env bash

set -Eeuo pipefail
source "$(dirname -- "$(readlink -f -- "$0")")/_common.sh"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/hands/recover_hands_home.sh --check [--model auto|v3|v4]
  ./scripts/hands/recover_hands_home.sh --run [--model auto|v3|v4] [--yes]

Abre ambas manos y ejecuta la tarea oficial cruzr/home. Sólo debe utilizarse
cuando no hay ningún objeto entre los dedos ni dentro de la trayectoria de los
brazos. No cancela una acción que todavía esté en curso.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
hands_parse_common_args "$@"
hands_preflight "$HANDS_REQUESTED_MODEL"

if [[ "$HANDS_DETECTED_MODEL" == "v3" ]]; then
  tasks=(v3hand/dual_hand_open cruzr/home)
else
  tasks=(v4hand/dual_hand_open cruzr/home)
fi
hands_validate_tasks "${tasks[@]}"

if [[ "$HANDS_MODE" == "check" ]]; then
  hands_info "HANDS_HOME_CHECK_OK=model:$HANDS_DETECTED_MODEL,movement:none"
  exit 0
fi

hands_lock
if [[ "${CRUZR_HANDS_CONFIRMED:-0}" != "1" ]]; then
  [[ -t 0 ]] || hands_die "La recuperación requiere una terminal interactiva."
  cat <<EOF

CONFIRMACIÓN — ABRIR MANOS Y VOLVER A HOME
  - Las dos manos están completamente vacías.
  - No hay mesa, soporte, objeto ni persona dentro del recorrido de brazos.
  - El robot no está ejecutando otra tarea.
  - Otra persona mantiene preparado el paro físico.

Escribe MANOS VACIAS HOME para continuar:
EOF
  read -r answer
  [[ "$answer" == "MANOS VACIAS HOME" ]] || hands_die "Recuperación cancelada."
fi

hands_run_task "${tasks[0]}"
hands_run_task "${tasks[1]}"
hands_info "HANDS_HOME_COMPLETED=model:$HANDS_DETECTED_MODEL,pose:home,hands:open"

