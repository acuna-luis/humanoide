#!/usr/bin/env bash

set -Eeuo pipefail

# Gestiona una validación VLA sin movimiento. El contenedor de control sólo
# ejecuta el validador read-only; nunca se inicia el ejecutor entregado por el
# proveedor y cualquier publicador en /mc/sdk/robot_command aborta la sesión.

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly RUNTIME_LOCAL="$SCRIPT_DIR/runtime"
readonly GROOT_OVERLAY_LOCAL="$REPO_ROOT/cruzrss2_vla_pack-002/codes-S2/vision/docker_files/gr00t_model/gr00t"
readonly DATA_CONFIG_SHA256="94c53e7b4a306903812104fd503642f8c0e68051bb257ff2388ae5ff8855ef38"
readonly EAGLE_BACKBONE_SHA256="553d642fe1b5f7fca0b4d09a719a8df76ee21cca864d6292336c7656c5bc0b50"
readonly GROOT_N1_SHA256="1b4a9653f3818f7417f2e99aa558be0abf19dc1cd05e3d026a987dde294f8138"
readonly POLICY_SHA256="458eef19a9da229190c730b9d1c0d2e0c2fa851b949f661ed9c1e5e6bdbe2c1f"
readonly METADATA_LOCAL="$REPO_ROOT/cruzrss2_vla_pack-002/weight/checkpoint-40000/experiment_cfg/metadata.json"
readonly METADATA_CYF_LOCAL="$REPO_ROOT/cruzrss2_vla_pack-002/weight/checkpoint-40000/experiment_cfg/metadata_cyf.json"
readonly METADATA_SHA256="46287335b211cd24a12991481e0f1121e74b4dd3c49b9a25d6fc62ce7de9a572"
readonly METADATA_CYF_SHA256="07b3c1010d24218482aefc817f7456ab077aa89ff6bce03826ea4902bfb3958b"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly REMOTE_ROOT="/home/walker/cruzr-vla"
readonly RUNTIME_REMOTE="$REMOTE_ROOT/additional/safe-runtime"
readonly CONTROL_CONTAINER="cruzr-vla-control"
readonly INFERENCE_CONTAINER="cruzr-vla-inference"
readonly CONTROL_IMAGE="vla_control_node_sdk:latest"
readonly INFERENCE_IMAGE="vla_inference_node_sdk:latest"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD

if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE="status"
SHADOW_DURATION=180
TASK_ID=0
INFERENCE_DURATION=8
EXPORT_DIR=""
PROFILE_NAME="cruzr_s2_vla_profile.json"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_ubtech_vla_shadow.sh --deploy
  ./scripts/vla/run_ubtech_vla_shadow.sh --check [--profile PROFILE.json]
  ./scripts/vla/run_ubtech_vla_shadow.sh --start-shadow [--shadow-duration 180] [--profile PROFILE.json]
  ./scripts/vla/run_ubtech_vla_shadow.sh --start-inference
  ./scripts/vla/run_ubtech_vla_shadow.sh --trigger [--task-id 0] [--inference-duration 8]
  ./scripts/vla/run_ubtech_vla_shadow.sh --status
  ./scripts/vla/run_ubtech_vla_shadow.sh --stop
  ./scripts/vla/run_ubtech_vla_shadow.sh --export-evidence DIR

--trigger sólo solicita inferencia si el validador shadow está activo y el
canal /mc/sdk/robot_command tiene cero publicadores. No mueve el robot.
--export-evidence recupera logs de los contenedores, incluso detenidos, sin
arrancarlos ni conectarlos a una ruta de mando.
--profile sólo acepta el nombre de un JSON versionado dentro de
scripts/vla/runtime; su hash local y remoto debe coincidir.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

while (($#)); do
  case "$1" in
    --deploy|--check|--start-shadow|--start-inference|--trigger|--status|--stop)
      MODE="${1#--}"
      ;;
    --export-evidence)
      shift
      EXPORT_DIR="${1:?Falta directorio de exportación}"
      MODE="export-evidence"
      ;;
    --shadow-duration)
      shift
      SHADOW_DURATION="${1:?Falta duración shadow}"
      ;;
    --task-id)
      shift
      TASK_ID="${1:?Falta task ID}"
      ;;
    --inference-duration)
      shift
      INFERENCE_DURATION="${1:?Falta duración de inferencia}"
      ;;
    --profile)
      shift
      PROFILE_NAME="${1:?Falta nombre de perfil}"
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "Opción desconocida: $1"
      ;;
  esac
  shift
done

[[ "$TASK_ID" =~ ^[0-3]$ ]] || die "task-id debe estar entre 0 y 3."
[[ "$SHADOW_DURATION" =~ ^[0-9]+([.][0-9]+)?$ ]] || die "Duración shadow inválida."
[[ "$INFERENCE_DURATION" =~ ^[0-9]+([.][0-9]+)?$ ]] || die "Duración de inferencia inválida."
[[ "$PROFILE_NAME" =~ ^[A-Za-z0-9._-]+[.]json$ ]] || die "--profile debe ser un basename JSON seguro."
readonly PROFILE_LOCAL="$RUNTIME_LOCAL/$PROFILE_NAME"
[[ -s "$PROFILE_LOCAL" ]] || die "No existe el perfil local: $PROFILE_LOCAL"

for command_name in find grep nc readlink rsync setsid sha256sum ssh tar; do
  command -v "$command_name" >/dev/null 2>&1 || die "Falta '$command_name'."
done
readonly PROFILE_SHA256="$(sha256sum "$PROFILE_LOCAL" | awk '{print $1}')"

ssh_options=(
  -o ConnectTimeout=10
  -o ConnectionAttempts=1
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
  -o PreferredAuthentications=password
  -o PubkeyAuthentication=no
  -o NumberOfPasswordPrompts=2
  -o StrictHostKeyChecking=accept-new
)

run_ssh() {
  local host="$1"
  shift
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w ssh "${ssh_options[@]}" "$ROBOT_USER@$host" "$@"
}

run_rsync() {
  local source_path="$1"
  local host="$2"
  local destination_path="$3"
  shift 3
  local ssh_command="ssh"
  local option
  for option in "${ssh_options[@]}"; do
    printf -v ssh_command '%s %q' "$ssh_command" "$option"
  done
  CRUZR_INTERNAL_ASKPASS=1 \
  SSH_ASKPASS="$SCRIPT_PATH" \
  SSH_ASKPASS_REQUIRE=force \
  DISPLAY="${DISPLAY:-:0}" \
  setsid -w rsync --archive --exclude='__pycache__/' --exclude='*.swp' -e "$ssh_command" \
    "$@" "$source_path" "$ROBOT_USER@$host:$destination_path"
}

resolve_vision_host() {
  if [[ -n "${CRUZR_VISION_HOST:-}" ]]; then
    printf '%s\n' "$CRUZR_VISION_HOST"
  elif nc -z -w2 192.168.11.3 22; then
    printf '%s\n' 192.168.11.3
  elif nc -z -w2 192.168.42.2 22; then
    printf '%s\n' 192.168.42.2
  else
    die "No se alcanza vision por Ethernet ni por Wi-Fi."
  fi
}

VISION_HOST="$(resolve_vision_host)"
readonly VISION_HOST

command_publisher_count() {
  run_ssh "$MOTION_HOST" "docker exec walker-ros.ros2-1 bash -lc '
    source /opt/ros/humble/setup.bash
    export ROS2CLI_DISABLE_DAEMON=1
    output=\$(timeout 8 ros2 topic info /mc/sdk/robot_command 2>&1) && rc=0 || rc=\$?
    if count=\$(awk '\''/Publisher count:/ {print \$3; found=1} END {exit !found}'\'' <<<\"\$output\"); then
      printf '\''%s\\n'\'' \"\$count\"
    elif grep -Fq '\''Unknown topic'\'' <<<\"\$output\"; then
      # Un topic ausente no puede tener publicadores. Es un estado seguro y
      # normal con los contenedores VLA detenidos, no un fallo de transporte.
      printf '\''0\\n'\''
    else
      printf '\''%s\\n'\'' \"\$output\" >&2
      exit \"\${rc:-1}\"
    fi
  '"
}

assert_command_path_absent() {
  local count
  count="$(command_publisher_count)"
  [[ "$count" == "0" ]] || die "El canal de movimiento tiene publicadores: $count. Se aborta."
  printf 'COMMAND_PATH_SAFE=publishers:0\n'
}

assert_containers() {
  run_ssh "$MOTION_HOST" "docker image inspect '$CONTROL_IMAGE' >/dev/null; docker container inspect '$CONTROL_CONTAINER' >/dev/null"
  run_ssh "$VISION_HOST" "docker image inspect '$INFERENCE_IMAGE' >/dev/null; docker container inspect '$INFERENCE_CONTAINER' >/dev/null"
}

deploy_runtime() {
  [[ -s "$RUNTIME_LOCAL/cruzr_s2_shadow_validator.py" ]] || die "Falta el validador local."
  [[ -d "$GROOT_OVERLAY_LOCAL" ]] || die "Falta el overlay GR00T suministrado por UBTECH."
  [[ "$(sha256sum "$GROOT_OVERLAY_LOCAL/experiment/data_config.py" | awk '{print $1}')" == "$DATA_CONFIG_SHA256" ]] || die "data_config.py no coincide."
  [[ "$(sha256sum "$GROOT_OVERLAY_LOCAL/model/backbone/eagle_backbone.py" | awk '{print $1}')" == "$EAGLE_BACKBONE_SHA256" ]] || die "eagle_backbone.py no coincide."
  [[ "$(sha256sum "$GROOT_OVERLAY_LOCAL/model/gr00t_n1.py" | awk '{print $1}')" == "$GROOT_N1_SHA256" ]] || die "gr00t_n1.py no coincide."
  [[ "$(sha256sum "$GROOT_OVERLAY_LOCAL/model/policy.py" | awk '{print $1}')" == "$POLICY_SHA256" ]] || die "policy.py no coincide."
  [[ "$(sha256sum "$METADATA_LOCAL" | awk '{print $1}')" == "$METADATA_SHA256" ]] || die "metadata.json no coincide."
  [[ "$(sha256sum "$METADATA_CYF_LOCAL" | awk '{print $1}')" == "$METADATA_CYF_SHA256" ]] || die "metadata_cyf.json no coincide."
  python3 "$RUNTIME_LOCAL/test_cruzr_s2_shadow_validator.py"
  run_ssh "$MOTION_HOST" "install -d '$RUNTIME_REMOTE'"
  run_rsync "$RUNTIME_LOCAL/" "$MOTION_HOST" "$RUNTIME_REMOTE/"
  run_ssh "$VISION_HOST" "install -d '$RUNTIME_REMOTE'"
  run_rsync "$RUNTIME_LOCAL/" "$VISION_HOST" "$RUNTIME_REMOTE/"
  run_ssh "$VISION_HOST" "install -d '$RUNTIME_REMOTE/vendor-overrides'"
  run_rsync "$GROOT_OVERLAY_LOCAL/" "$VISION_HOST" "$RUNTIME_REMOTE/vendor-overrides/gr00t/" --delete
  run_ssh "$VISION_HOST" "
    test \"\$(sha256sum '$RUNTIME_REMOTE/vendor-overrides/gr00t/experiment/data_config.py' | awk '{print \$1}')\" = '$DATA_CONFIG_SHA256'
    test \"\$(sha256sum '$RUNTIME_REMOTE/vendor-overrides/gr00t/model/backbone/eagle_backbone.py' | awk '{print \$1}')\" = '$EAGLE_BACKBONE_SHA256'
    test \"\$(sha256sum '$RUNTIME_REMOTE/vendor-overrides/gr00t/model/gr00t_n1.py' | awk '{print \$1}')\" = '$GROOT_N1_SHA256'
    test \"\$(sha256sum '$RUNTIME_REMOTE/vendor-overrides/gr00t/model/policy.py' | awk '{print \$1}')\" = '$POLICY_SHA256'
    install -d '$REMOTE_ROOT/additional/checkpoint-40000/experiment_cfg'
  "
  run_rsync "$METADATA_LOCAL" "$VISION_HOST" "$REMOTE_ROOT/additional/checkpoint-40000/experiment_cfg/metadata.json"
  run_rsync "$METADATA_CYF_LOCAL" "$VISION_HOST" "$REMOTE_ROOT/additional/checkpoint-40000/experiment_cfg/metadata_cyf.json"
  run_ssh "$VISION_HOST" "test \"\$(sha256sum '$REMOTE_ROOT/additional/checkpoint-40000/experiment_cfg/metadata.json' | awk '{print \$1}')\" = '$METADATA_SHA256'; test \"\$(sha256sum '$REMOTE_ROOT/additional/checkpoint-40000/experiment_cfg/metadata_cyf.json' | awk '{print \$1}')\" = '$METADATA_CYF_SHA256'"
  run_ssh "$MOTION_HOST" "docker run --rm --network none --entrypoint bash \
    -v '$REMOTE_ROOT/additional:/home/ubt/additional:ro' '$CONTROL_IMAGE' -lc '
      set -e
      source /home/ubt/additional/vla-motionx86/install/setup.bash
      export PYTHONDONTWRITEBYTECODE=1
      export PYTHONPYCACHEPREFIX=/tmp/cruzr-vla-pycache
      python3 -m py_compile /home/ubt/additional/safe-runtime/cruzr_s2_shadow_validator.py
      python3 -m py_compile /home/ubt/additional/safe-runtime/cruzr_s2_inference_shadow.py
      python3 /home/ubt/additional/safe-runtime/test_cruzr_s2_shadow_validator.py
    '"
  run_ssh "$VISION_HOST" "docker run --rm --network none --entrypoint bash \
    -v '$REMOTE_ROOT/additional:/home/ubt/additional:ro' '$INFERENCE_IMAGE' -lc '
      set -e
      source /home/ubt/additional/vla-onboard/install/setup.bash
      export PYTHONPYCACHEPREFIX=/tmp/cruzr-vla-pycache
      python3 -m py_compile /home/ubt/additional/safe-runtime/cruzr_s2_inference_shadow.py
    '"
  printf 'SHADOW_RUNTIME_DEPLOYED=vision:%s,motion:%s\n' "$VISION_HOST" "$MOTION_HOST"
}

check_installation() {
  assert_containers
  assert_command_path_absent
  run_ssh "$MOTION_HOST" "test -s '$RUNTIME_REMOTE/cruzr_s2_shadow_validator.py'; test -s '$RUNTIME_REMOTE/$PROFILE_NAME'; test \"\$(sha256sum '$RUNTIME_REMOTE/$PROFILE_NAME' | awk '{print \$1}')\" = '$PROFILE_SHA256'" || \
    die "El perfil remoto $PROFILE_NAME falta o no coincide (ejecute --deploy de forma separada)."
  run_ssh "$VISION_HOST" "test -s '$REMOTE_ROOT/additional/checkpoint-40000/config.json'; test -s '$REMOTE_ROOT/additional/vla-onboard/src/gr00t_control/gr00t_inference.py'; test \"\$(sha256sum '$RUNTIME_REMOTE/vendor-overrides/gr00t/experiment/data_config.py' | awk '{print \$1}')\" = '$DATA_CONFIG_SHA256'; test \"\$(sha256sum '$RUNTIME_REMOTE/vendor-overrides/gr00t/model/backbone/eagle_backbone.py' | awk '{print \$1}')\" = '$EAGLE_BACKBONE_SHA256'; test \"\$(sha256sum '$REMOTE_ROOT/additional/checkpoint-40000/experiment_cfg/metadata.json' | awk '{print \$1}')\" = '$METADATA_SHA256'"
  printf 'SHADOW_PROFILE_OK=%s,sha256:%s\n' "$PROFILE_NAME" "$PROFILE_SHA256"
  printf 'SHADOW_CHECK_OK=vision:%s,motion:%s,movement:none\n' "$VISION_HOST" "$MOTION_HOST"
}

start_shadow() {
  check_installation
  run_ssh "$MOTION_HOST" "
    state=\$(docker inspect '$CONTROL_CONTAINER' --format '{{.State.Status}}')
    if [ \"\$state\" != running ]; then docker start '$CONTROL_CONTAINER' >/dev/null; fi
    docker exec '$CONTROL_CONTAINER' bash -lc '
      pkill -f \"[c]ruzr_s2_shadow_validator.py\" 2>/dev/null || true
      install -d /home/ubt/additional/safe-runtime/logs
      : > /home/ubt/additional/safe-runtime/logs/shadow-process.log
      rm -f /home/ubt/additional/safe-runtime/logs/shadow.jsonl
    '
    docker exec -d '$CONTROL_CONTAINER' bash -lc '
      source /home/ubt/additional/vla-motionx86/install/setup.bash
      export ROS2CLI_DISABLE_DAEMON=1
      exec python3 /home/ubt/additional/safe-runtime/cruzr_s2_shadow_validator.py \
        --profile /home/ubt/additional/safe-runtime/$PROFILE_NAME \
        --duration $SHADOW_DURATION \
        --log /home/ubt/additional/safe-runtime/logs/shadow.jsonl \
        > /home/ubt/additional/safe-runtime/logs/shadow-process.log 2>&1
    '
    sleep 2
    docker exec '$CONTROL_CONTAINER' pgrep -af '[c]ruzr_s2_shadow_validator.py'
    docker exec '$CONTROL_CONTAINER' tail -n 20 /home/ubt/additional/safe-runtime/logs/shadow-process.log
  "
  assert_command_path_absent
  printf 'SHADOW_STARTED=duration:%ss,publisher:none\n' "$SHADOW_DURATION"
}

start_inference() {
  check_installation
  run_ssh "$VISION_HOST" "
    state=\$(docker inspect '$INFERENCE_CONTAINER' --format '{{.State.Status}}')
    if [ \"\$state\" != running ]; then docker start '$INFERENCE_CONTAINER' >/dev/null; fi
    docker exec '$INFERENCE_CONTAINER' bash -lc '
      pkill -f \"[c]ruzr_s2_inference_shadow.py\" 2>/dev/null || true
      install -d /home/ubt/additional/safe-runtime-logs
      install -d /home/ubt/additional/safe-runtime-logs/shadow-inputs
      : > /home/ubt/additional/safe-runtime-logs/inference-process.log
      find /home/ubt/additional/safe-runtime-logs/shadow-inputs \\
        -mindepth 1 -maxdepth 1 -type f -delete
    '
    docker exec -d '$INFERENCE_CONTAINER' bash -lc '
      source /home/ubt/additional/vla-onboard/install/setup.bash
      export ROS2CLI_DISABLE_DAEMON=1
      export CRUZR_SHADOW_INPUT_DIR=/home/ubt/additional/safe-runtime-logs/shadow-inputs
      cd /home/ubt/additional/vla-onboard/src/gr00t_control
      exec python3 /home/ubt/additional/safe-runtime/cruzr_s2_inference_shadow.py \
        > /home/ubt/additional/safe-runtime-logs/inference-process.log 2>&1
    '
  "
  assert_command_path_absent
  printf 'INFERENCE_START_REQUESTED=vision:%s,movement:none\n' "$VISION_HOST"
}

assert_shadow_running() {
  run_ssh "$MOTION_HOST" "test \"\$(docker inspect '$CONTROL_CONTAINER' --format '{{.State.Status}}')\" = running; docker exec '$CONTROL_CONTAINER' pgrep -f '[c]ruzr_s2_shadow_validator.py' >/dev/null" || \
    die "El validador shadow no está activo."
}

assert_inference_running() {
  run_ssh "$VISION_HOST" "test \"\$(docker inspect '$INFERENCE_CONTAINER' --format '{{.State.Status}}')\" = running; docker exec '$INFERENCE_CONTAINER' pgrep -f '[c]ruzr_s2_inference_shadow.py' >/dev/null" || \
    die "La inferencia no está activa."
}

trigger_inference() {
  assert_shadow_running
  assert_inference_running
  assert_command_path_absent
  run_ssh "$VISION_HOST" "docker exec '$INFERENCE_CONTAINER' bash -lc '
    source /home/ubt/additional/vla-onboard/install/setup.bash
    export ROS2CLI_DISABLE_DAEMON=1
    ros2 action send_goal /gr00t/trigger_inference mc_task_msgs/action/InferenceTask \
      \"{task_id: $TASK_ID, max_inference_duration: $INFERENCE_DURATION, end_threshold: 0.1}\" --feedback
  '"
  assert_command_path_absent
  run_ssh "$MOTION_HOST" "docker exec '$CONTROL_CONTAINER' tail -n 80 /home/ubt/additional/safe-runtime/logs/shadow-process.log"
  printf 'INFERENCE_SHADOW_TRIGGER_COMPLETED=task:%s,duration:%ss,movement:none\n' "$TASK_ID" "$INFERENCE_DURATION"
}

show_status() {
  assert_containers
  printf 'VISION_HOST=%s\nMOTION_HOST=%s\n' "$VISION_HOST" "$MOTION_HOST"
  run_ssh "$VISION_HOST" "docker inspect '$INFERENCE_CONTAINER' --format 'INFERENCE_CONTAINER={{.State.Status}}'; if [ \"\$(docker inspect '$INFERENCE_CONTAINER' --format '{{.State.Status}}')\" = running ]; then docker exec '$INFERENCE_CONTAINER' pgrep -af '[c]ruzr_s2_inference_shadow.py' || true; docker exec '$INFERENCE_CONTAINER' tail -n 15 /home/ubt/additional/safe-runtime-logs/inference-process.log 2>/dev/null || true; fi"
  run_ssh "$MOTION_HOST" "docker inspect '$CONTROL_CONTAINER' --format 'CONTROL_CONTAINER={{.State.Status}}'; if [ \"\$(docker inspect '$CONTROL_CONTAINER' --format '{{.State.Status}}')\" = running ]; then docker exec '$CONTROL_CONTAINER' pgrep -af '[c]ruzr_s2_shadow_validator.py' || true; docker exec '$CONTROL_CONTAINER' tail -n 20 /home/ubt/additional/safe-runtime/logs/shadow-process.log 2>/dev/null || true; fi"
  assert_command_path_absent
}

stop_session() {
  run_ssh "$VISION_HOST" "state=\$(docker inspect '$INFERENCE_CONTAINER' --format '{{.State.Status}}'); if [ \"\$state\" = running ]; then docker stop --time 20 '$INFERENCE_CONTAINER' >/dev/null; fi; docker inspect '$INFERENCE_CONTAINER' --format 'INFERENCE_CONTAINER={{.State.Status}}'"
  run_ssh "$MOTION_HOST" "state=\$(docker inspect '$CONTROL_CONTAINER' --format '{{.State.Status}}'); if [ \"\$state\" = running ]; then docker stop --time 5 '$CONTROL_CONTAINER' >/dev/null; fi; docker inspect '$CONTROL_CONTAINER' --format 'CONTROL_CONTAINER={{.State.Status}}'"
  assert_command_path_absent
  printf 'SHADOW_SESSION_STOPPED=yes\n'
}

export_container_file() {
  local host="$1"
  local container="$2"
  local source_path="$3"
  local destination_path="$4"

  run_ssh "$host" "docker cp '$container:$source_path' - | tar -xOf -" \
    > "$destination_path"
  [[ -s "$destination_path" ]] || die "No se recuperó $source_path desde $container."
}

export_evidence() {
  [[ -n "$EXPORT_DIR" ]] || die "Falta directorio de exportación."
  EXPORT_DIR="$(readlink -m -- "$EXPORT_DIR")"
  [[ "$EXPORT_DIR" != "/" ]] || die "El directorio de exportación no puede ser /."
  [[ ! -e "$EXPORT_DIR" || -d "$EXPORT_DIR" ]] || \
    die "La ruta de exportación existe y no es un directorio: $EXPORT_DIR"
  if [[ -d "$EXPORT_DIR" ]] &&
     find "$EXPORT_DIR" -mindepth 1 -print -quit | grep -q .; then
    die "El directorio de exportación debe estar vacío: $EXPORT_DIR"
  fi
  mkdir -p "$EXPORT_DIR"
  [[ -d "$EXPORT_DIR" && -w "$EXPORT_DIR" ]] || \
    die "El directorio no existe o no permite escritura: $EXPORT_DIR"
  local evidence_name
  for evidence_name in \
    shadow.jsonl shadow-process.log inference-process.log \
    status_after_export.log exported_logs.sha256; do
    [[ ! -e "$EXPORT_DIR/$evidence_name" ]] || \
      die "No se sobrescribirá evidencia existente: $EXPORT_DIR/$evidence_name"
  done

  assert_containers
  export_container_file "$MOTION_HOST" "$CONTROL_CONTAINER" \
    /home/ubt/additional/safe-runtime/logs/shadow.jsonl \
    "$EXPORT_DIR/shadow.jsonl"
  export_container_file "$MOTION_HOST" "$CONTROL_CONTAINER" \
    /home/ubt/additional/safe-runtime/logs/shadow-process.log \
    "$EXPORT_DIR/shadow-process.log"
  export_container_file "$VISION_HOST" "$INFERENCE_CONTAINER" \
    /home/ubt/additional/safe-runtime-logs/inference-process.log \
    "$EXPORT_DIR/inference-process.log"
  mkdir -p "$EXPORT_DIR/inputs"
  if run_ssh "$VISION_HOST" \
      "docker cp '$INFERENCE_CONTAINER:/home/ubt/additional/safe-runtime-logs/shadow-inputs/.' -" \
      | tar -xf - -C "$EXPORT_DIR/inputs"; then
    printf 'SHADOW_INPUT_EVIDENCE_EXPORTED=%s\n' "$EXPORT_DIR/inputs"
  else
    rmdir "$EXPORT_DIR/inputs" 2>/dev/null || true
    printf 'SHADOW_INPUT_EVIDENCE_UNAVAILABLE=1\n'
  fi
  show_status > "$EXPORT_DIR/status_after_export.log"
  (
    cd "$EXPORT_DIR"
    find . -type f ! -name exported_logs.sha256 -print0 \
      | sort -z \
      | xargs -0 sha256sum
  ) > "$EXPORT_DIR/exported_logs.sha256"
  printf 'SHADOW_EVIDENCE_EXPORTED=%s\n' "$EXPORT_DIR"
  printf 'SHADOW_EVIDENCE_MODE=read-only,containers-not-started\n'
}

case "$MODE" in
  deploy) deploy_runtime ;;
  check) check_installation ;;
  start-shadow) start_shadow ;;
  start-inference) start_inference ;;
  trigger) trigger_inference ;;
  status) show_status ;;
  stop) stop_session ;;
  export-evidence) export_evidence ;;
esac
