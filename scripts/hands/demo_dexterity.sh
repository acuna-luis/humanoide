#!/usr/bin/env bash

set -Eeuo pipefail
source "$(dirname -- "$(readlink -f -- "$0")")/_common.sh"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/hands/demo_dexterity.sh --check [--model auto|v3|v4]
  ./scripts/hands/demo_dexterity.sh --run [--model auto|v3|v4] [--yes]

Mueve solamente los efectores: apertura bimanual, secuencia de dedos izquierda
y derecha, cierre bimanual y apertura final. No mueve brazos, cabeza ni base.
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
    v3hand/dual_hand_open
    s2/basic_motion/v3hand_left_sequence_motion
    s2/basic_motion/v3hand_right_sequence_motion
    v3hand/dual_hand_close
    v3hand/dual_hand_open
  )
else
  tasks=(
    v4hand/dual_hand_open
    s2/basic_motion/v4hand_left_sequence_motion
    s2/basic_motion/v4hand_right_sequence_motion
    v4hand/dual_hand_close
    v4hand/dual_hand_open
  )
fi

hands_validate_tasks "${tasks[@]}"
if [[ "$HANDS_MODE" == "check" ]]; then
  hands_info "DEXTERITY_CHECK_OK=model:$HANDS_DETECTED_MODEL,movement:none"
  exit 0
fi

hands_lock
hands_confirm_empty_demo "DESTREZA DE DEDOS"
for task in "${tasks[@]}"; do
  hands_run_task "$task"
  sleep 0.4
done
hands_info "DEXTERITY_DEMO_COMPLETED=model:$HANDS_DETECTED_MODEL,hands:open"

