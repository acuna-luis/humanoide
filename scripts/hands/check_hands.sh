#!/usr/bin/env bash

set -Eeuo pipefail
source "$(dirname -- "$(readlink -f -- "$0")")/_common.sh"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/hands/check_hands.sh [--model auto|v3|v4]

Sólo lectura: identifica las manos, comprueba publicación de estado, batería,
paros, cargador, servidor de manipulación y hashes de las tareas de fábrica.
No mueve ni instala nada.
EOF
}

model="auto"
while (($#)); do
  case "$1" in
    --model)
      shift
      (($#)) || hands_die "--model requiere un valor."
      model="$1"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      hands_die "Opción desconocida: $1"
      ;;
  esac
  shift
done

hands_preflight "$model"

if [[ "$HANDS_DETECTED_MODEL" == "v3" ]]; then
  tasks=(
    v3hand/dual_hand_open
    v3hand/dual_hand_close
    s2/basic_motion/v3hand_left_sequence_motion
    s2/basic_motion/v3hand_right_sequence_motion
    production_movie/cheer_up_s2_v3hand
    production_movie/cheer_down_s2_v3hand
    qyh/hold_plate_v3hand
    qyh/hold_plate_back_v3hand
    cruzr/home
  )
else
  tasks=(
    v4hand/dual_hand_open
    v4hand/dual_hand_close
    s2/basic_motion/v4hand_left_sequence_motion
    s2/basic_motion/v4hand_right_sequence_motion
    v4hand/thumb_index_tip_left
    v4hand/thumb_index_tip_right
    v4hand/thumb_middle_tip_left
    v4hand/thumb_middle_tip_right
    v4hand/thumb_ring_tip_left
    v4hand/thumb_ring_tip_right
    production_movie/cheer_up_s2_v4hand
    production_movie/cheer_down_s2_v4hand
    qyh/hold_plate_v4hand
    production_movie/grasp_the_remote_control_ready
    production_movie/press_the_remote_control
    production_movie/press_the_remote_control_down
    cruzr/home
  )
fi

hands_validate_tasks "${tasks[@]}"
hands_info "CHECK_OK=model:$HANDS_DETECTED_MODEL,tasks:${#tasks[@]},movement:none"

