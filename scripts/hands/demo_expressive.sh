#!/usr/bin/env bash

set -Eeuo pipefail
source "$(dirname -- "$(readlink -f -- "$0")")/_common.sh"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/hands/demo_expressive.sh --check [--model auto|v3|v4]
  ./scripts/hands/demo_expressive.sh --run [--model auto|v3|v4] [--yes]

Mueve el brazo derecho y termina en cero. Para V4 usa fist_up_s2, porque la
pareja factory cheer_up/cheer_down contiene una posición de pulgar que esta
unidad no alcanza dentro de tolerancia.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
hands_parse_common_args "$@"
hands_preflight "$HANDS_REQUESTED_MODEL"

if [[ "$HANDS_DETECTED_MODEL" == "v3" ]]; then
  tasks=(production_movie/cheer_up_s2_v3hand production_movie/cheer_down_s2_v3hand)
else
  tasks=(fist_up_s2)
fi
hands_validate_tasks "${tasks[@]}"

if [[ "$HANDS_MODE" == "check" ]]; then
  hands_info "EXPRESSIVE_CHECK_OK=model:$HANDS_DETECTED_MODEL,movement:none"
  exit 0
fi

hands_lock
hands_confirm_empty_demo "GESTO EXPRESIVO CHEER"
for task in "${tasks[@]}"; do
  hands_run_task "$task"
  sleep 0.4
done
hands_info "EXPRESSIVE_DEMO_COMPLETED=model:$HANDS_DETECTED_MODEL,pose:zero"
