#!/usr/bin/env bash
# Passive recording only: no publishers, mode switches, START or replay.
set -Eeuo pipefail
mode="${1:---check}"
name="${2:-prueba_v4}"
host="walker@192.168.11.2"
container="walker-ros.ros2-1"
topics=(
  /mc/head/joint_command /mc/left_arm/joint_command /mc/right_arm/joint_command
  /mc/whole_joint_states /mc/head/joint_states
  /mc/left_hand/command /mc/right_hand/command
  /mc/left_hand/joint_states /mc/right_hand/joint_states
  /ecat/left_hand/cmd /ecat/right_hand/cmd
  /ecat/left_hand/state /ecat/right_hand/state
)
case "$mode" in
  --help|-h)
    printf '%s\n' 'Uso desde PC: bash scripts/teleoperation/record_pico_v4_complete.sh --check' \
      '              bash scripts/teleoperation/record_pico_v4_complete.sh --record NOMBRE' \
      'Graba ROS bag complementario al .motion. Ctrl+C sólo detiene este grabador.' \
      'Conserva estados medidos y órdenes completas de manos. No reproduce.'
    exit 0 ;;
  --check|--record) ;;
  *) printf 'Opción no admitida: %s\n' "$mode" >&2; exit 2 ;;
esac
(( $# <= 2 )) || exit 2
[[ "$name" =~ ^[A-Za-z0-9_-]+$ ]] || { printf 'Nombre: sólo letras, números, _ y -.\n' >&2; exit 2; }
command -v ssh >/dev/null
[[ "$mode" != --record || -t 0 && -t 1 ]] || {
  printf 'Ejecutad --record en una terminal interactiva del PC.\n' >&2; exit 2;
}
remote() { ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=yes "$host" "$@"; }
[[ "$(remote "docker inspect --format '{{.State.Running}}' $container")" == true ]] || exit 3
remote "docker exec $container bash -lc 'source /opt/ros/humble/setup.bash && export ROS2CLI_DISABLE_DAEMON=1 && timeout 8 ros2 bag record --help >/dev/null'"
inventory="$(remote "docker exec $container bash -lc 'source /opt/ros/humble/setup.bash && export ROS2CLI_DISABLE_DAEMON=1 && timeout 8 ros2 topic list -t'")"
for side in left right; do
  grep -Fxq "/mc/${side}_hand/joint_states [sensor_msgs/msg/JointState]" <<<"$inventory" || {
    printf 'Falta el canal medido de la mano %s.\n' "$side" >&2; exit 4;
  }
  grep -Fxq "/mc/${side}_hand/command [mc_task_msgs/msg/JointCommand]" <<<"$inventory" || {
    printf 'Falta el canal de órdenes de la mano %s.\n' "$side" >&2; exit 4;
  }
done
printf 'V4_CAPTURE_TOOLS_OK=1; sin START ni movimiento\n'
[[ "$mode" == --record ]] || exit 0

session="${name}_$(date -u +%Y%m%dT%H%M%SZ)_$$"
root="/tmp/pico_v4_capture_$session"
destination="/home/walker/grabaciones_v4_completas/$session"
# New directory only; no previous recording is overwritten.
remote "docker exec $container bash -lc 'test ! -e $root && mkdir $root'"
qos=''
for topic in "${topics[@]}"; do
  qos+="$topic:"$'\n''  history: keep_last'$'\n''  depth: 2000'$'\n''  reliability: best_effort'$'\n''  durability: volatile'$'\n'
done
printf '%s' "$qos" | remote "docker exec -i $container bash -lc 'cat > $root/qos.yaml'"
printf '\nGrabación pasiva. Esperad a los avisos Subscribed antes de demostrar.\n'
printf 'Ctrl+C aquí guarda este bag; NO detiene la teleoperación.\n\n'
record="source /opt/ros/humble/setup.bash && export ROS2CLI_DISABLE_DAEMON=1 && exec ros2 bag record -s sqlite3 --max-cache-size 16777216 --qos-profile-overrides-path $root/qos.yaml --include-unpublished-topics -o $root/rosbag ${topics[*]}"
printf -v quoted '%q' "$record"
rc=0
ssh -tt -o ConnectTimeout=5 -o StrictHostKeyChecking=yes "$host" \
  "docker exec -it $container bash -lc $quoted" || rc=$?
printf '\nGrabador terminó (rc=%s). Conservando captura en Motion...\n' "$rc"
remote "mkdir -p /home/walker/grabaciones_v4_completas && test ! -e $destination && mkdir $destination && docker cp $container:$root/. $destination/" || {
  printf 'Copia pendiente; original permanece en %s:%s\n' "$container" "$root" >&2; exit 5;
}
printf 'CAPTURA_EN_MOTION=%s\n' "$destination"
remote "docker exec $container bash -lc 'source /opt/ros/humble/setup.bash && export ROS2CLI_DISABLE_DAEMON=1 && timeout 10 ros2 bag info $root/rosbag'"
printf '\nRevisar recuentos y movimiento de dedos antes de declarar la toma válida.\n'
printf 'No se ha iniciado ni programado ninguna reproducción.\n'
((rc == 0 || rc == 130)) || exit "$rc"
