#!/usr/bin/env bash

set -Eeuo pipefail
source "$(dirname -- "$(readlink -f -- "$0")")/_common.sh"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/hands/demo_precision_v4.sh --check
  ./scripts/hands/demo_precision_v4.sh --run [--yes]

Sólo para manos v4. Ejecuta pinzas pulgar-índice, pulgar-medio y pulgar-anular
en ambos lados. Las manos empiezan y terminan abiertas; no mueve los brazos.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
hands_parse_common_args "$@"
[[ "$HANDS_REQUESTED_MODEL" == "auto" || "$HANDS_REQUESTED_MODEL" == "v4" ]] || \
  hands_die "La demostración de precisión sólo es compatible con v4."
hands_preflight v4

tasks=(
  v4hand/dual_hand_open
  v4hand/thumb_index_tip_left
  v4hand/thumb_index_tip_right
  v4hand/thumb_middle_tip_left
  v4hand/thumb_middle_tip_right
  v4hand/thumb_ring_tip_left
  v4hand/thumb_ring_tip_right
  v4hand/dual_hand_open
)
hands_validate_tasks "${tasks[@]}"

if [[ "$HANDS_MODE" == "check" ]]; then
  hands_info "PRECISION_CHECK_OK=model:v4,movement:none"
  exit 0
fi

hands_lock
hands_confirm_empty_demo "PINZAS DE PRECISIÓN V4"
for task in "${tasks[@]}"; do
  hands_run_task "$task"
  sleep 0.35
done
hands_info "PRECISION_DEMO_COMPLETED=model:v4,hands:open"

