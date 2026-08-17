#!/usr/bin/env bash

set -Eeuo pipefail
source "$(dirname -- "$(readlink -f -- "$0")")/_common.sh"

readonly HEART_TASK="cruzr/heart_v4_fingers_v6"
readonly HEART_TEMPLATE="$HANDS_DIR/../custom_tasks/heart_v4_fingers.xml"
readonly HEART_TEMPLATE_SHA="0f144af9974849298d3345dec15910d20976b087f71cfd663517d716eb045f8f"
readonly HEART_DESTINATION="$HANDS_CONFIG_ROOT/$HEART_TASK.xml"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/hands/demo_heart_v4.sh --check
  ./scripts/hands/demo_heart_v4.sh --run [--yes]

Abre ambas manos V4, forma un corazón con brazos y dedos durante tres segundos,
mantiene los pulgares separados del torso durante la retirada, baja los brazos
y sólo entonces abre completamente las manos. No mueve cabeza ni base.
EOF
}

validate_local_template() {
  [[ -r "$HEART_TEMPLATE" ]] || hands_die "No se encuentra $HEART_TEMPLATE"
  local actual
  actual="$(sha256sum "$HEART_TEMPLATE" | awk '{print $1}')"
  [[ "$actual" == "$HEART_TEMPLATE_SHA" ]] || \
    hands_die "La plantilla del corazón fue modificada: $actual"
  python3 - "$HEART_TEMPLATE" <<'PY'
import sys
import xml.etree.ElementTree as ET
ET.parse(sys.argv[1])
PY
  hands_info "HEART_TEMPLATE_OK=$HEART_TEMPLATE_SHA"
}

check_remote_destination() {
  hands_ssh_motion bash -s -- "$HANDS_MOTION_CONTAINER" \
    "$HEART_DESTINATION" "$HEART_TEMPLATE_SHA" <<'REMOTE'
set -Eeuo pipefail
container="$1"
destination="$2"
expected="$3"
if docker exec "$container" test -e "$destination"; then
  actual="$(docker exec "$container" sha256sum "$destination" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || {
    echo "HEART_TASK_CONFLICT=$actual" >&2
    exit 40
  }
  echo "HEART_TASK_STATE=installed:$actual"
else
  echo "HEART_TASK_STATE=ready_to_install"
fi
REMOTE
}

install_heart_task() {
  local staged="/tmp/cruzr_heart_v4_fingers_v6_${$}.xml"
  hands_scp_motion "$HEART_TEMPLATE" \
    "$HANDS_ROBOT_USER@$HANDS_MOTION_HOST:$staged" >/dev/null

  hands_ssh_motion bash -s -- "$HANDS_MOTION_CONTAINER" "$staged" \
    "$HEART_DESTINATION" "$HEART_TEMPLATE_SHA" <<'REMOTE'
set -Eeuo pipefail
container="$1"
staged="$2"
destination="$3"
expected="$4"
candidate="${destination}.installing.$$"

cleanup() {
  rm -f -- "$staged"
  docker exec "$container" rm -f -- "$candidate" >/dev/null 2>&1 || true
}
trap cleanup EXIT

[[ "$(sha256sum "$staged" | awk '{print $1}')" == "$expected" ]]
if docker exec "$container" test -e "$destination"; then
  actual="$(docker exec "$container" sha256sum "$destination" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || {
    echo "HEART_TASK_CONFLICT=$actual" >&2
    exit 41
  }
  echo "HEART_TASK_INSTALLED=already_present:$actual"
  exit 0
fi

docker exec "$container" mkdir -p "$(dirname -- "$destination")"
docker cp "$staged" "$container:$candidate" >/dev/null
docker exec "$container" python3 -c \
  'import sys, xml.etree.ElementTree as ET; ET.parse(sys.argv[1])' "$candidate"
docker exec "$container" chmod 0644 "$candidate"
docker exec "$container" ln "$candidate" "$destination"
actual="$(docker exec "$container" sha256sum "$destination" | awk '{print $1}')"
[[ "$actual" == "$expected" ]]
echo "HEART_TASK_INSTALLED=new:$actual"
REMOTE

  HANDS_VALIDATED_TASKS["$HEART_TASK"]=1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

hands_parse_common_args "$@"
hands_preflight "$HANDS_REQUESTED_MODEL"
[[ "$HANDS_DETECTED_MODEL" == "v4" ]] || \
  hands_die "La demostración de corazón sólo está validada para manos V4."

validate_local_template
hands_validate_tasks v4hand/dual_hand_open
check_remote_destination

if [[ "$HANDS_MODE" == "check" ]]; then
  hands_info "HEART_DEMO_CHECK_OK=model:v4,movement:none"
  exit 0
fi

hands_lock
hands_confirm_empty_demo "CORAZÓN BIMANUAL V4"
install_heart_task

heart_started=0
heart_completed=0
on_exit() {
  local status=$?
  if ((status != 0 && heart_started == 1 && heart_completed == 0)); then
    hands_warn "La trayectoria del corazón no terminó. No la repita ni envíe home sin revisar la postura."
  fi
}
trap on_exit EXIT

hands_run_task v4hand/dual_hand_open
heart_started=1
hands_run_task "$HEART_TASK"
heart_completed=1
hands_run_task v4hand/dual_hand_open
hands_info "HEART_DEMO_COMPLETED=model:v4,fingers:love-v4-v6,hold:3s,pose:zero,hands:open"
