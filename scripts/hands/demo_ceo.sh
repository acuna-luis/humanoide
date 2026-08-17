#!/usr/bin/env bash

set -Eeuo pipefail
source "$(dirname -- "$(readlink -f -- "$0")")/_common.sh"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/hands/demo_ceo.sh --check [--model auto|v3|v4]
  ./scripts/hands/demo_ceo.sh --run [--model auto|v3|v4] [--yes]

Coreografía sin objetos:
  1. gesto del brazo derecho y retorno;
  2. apertura y secuencia individual de la mano derecha;
  3. selección breve de pinzas de precisión (sólo v4);
  4. cierre/apertura bimanual;

No incluye bandeja ni mando. Esas pruebas se ejecutan separadamente mediante
demo_functional.sh después de calibrarlas. Las demostraciones de destreza y
precisión separadas recorren ambas manos y todas las pinzas disponibles.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
hands_parse_common_args "$@"
hands_preflight "$HANDS_REQUESTED_MODEL"

if [[ "$HANDS_DETECTED_MODEL" == "v3" ]]; then
  tasks=(
    production_movie/cheer_up_s2_v3hand
    production_movie/cheer_down_s2_v3hand
    v3hand/dual_hand_open
    s2/basic_motion/v3hand_right_sequence_motion
    v3hand/dual_hand_close
    v3hand/dual_hand_open
  )
else
  # Las tareas factory cheer_up/cheer_down V4 exigen 1.12 rad en
  # right_thumb_pip. Esta unidad se queda aproximadamente 0.14 rad por debajo
  # y el árbol aborta antes del retorno. fist_up_s2 ya fue probado en este
  # robot, no ordena posiciones de dedos y devuelve el brazo a cero.
  tasks=(
    fist_up_s2
    v4hand/dual_hand_open
    s2/basic_motion/v4hand_right_sequence_motion
    v4hand/thumb_index_tip_left
    v4hand/thumb_index_tip_right
    v4hand/thumb_middle_tip_right
    v4hand/dual_hand_close
    v4hand/dual_hand_open
  )
fi
hands_validate_tasks "${tasks[@]}"

if [[ "$HANDS_MODE" == "check" ]]; then
  hands_info "CEO_DEMO_CHECK_OK=model:$HANDS_DETECTED_MODEL,tasks:${#tasks[@]},movement:none"
  exit 0
fi

hands_lock
hands_confirm_empty_demo "COREOGRAFÍA PARA VÍDEO CEO"
started="$SECONDS"
for task in "${tasks[@]}"; do
  hands_run_task "$task"
  sleep 0.45
done
hands_info "CEO_DEMO_COMPLETED=model:$HANDS_DETECTED_MODEL,duration:$((SECONDS-started))s,pose:zero,hands:open"
