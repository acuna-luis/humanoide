#!/usr/bin/env bash

set -Eeuo pipefail

# Instala de forma aislada el paquete VLA suministrado para Cruzr S2.
# Los contenedores se crean DETENIDOS y sin política de reinicio. Este script
# no inicia inferencia, no publica /mc/sdk/robot_command y no mueve el robot.

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly PACK_ROOT="$REPO_ROOT/cruzrss2_vla_pack-002"
VISION_HOST="${CRUZR_VISION_HOST:-}"
MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly REMOTE_ROOT="/home/walker/cruzr-vla"
readonly VISION_ADDITIONAL="$PACK_ROOT/codes-S2/vision/rosa_vla_additional"
readonly MOTION_ADDITIONAL="$PACK_ROOT/codes-S2/motion/rosa_vla_additional"
readonly CHECKPOINT="$PACK_ROOT/weight/checkpoint-40000"
readonly INFERENCE_TAR="$PACK_ROOT/docker_images/vla_inference_node_sdk.tar"
readonly CONTROL_TAR="$PACK_ROOT/docker_images/vla_control_node_sdk.tar"
readonly INFERENCE_IMAGE="vla_inference_node_sdk:latest"
readonly CONTROL_IMAGE="vla_control_node_sdk:latest"
readonly INFERENCE_CONTAINER="cruzr-vla-inference"
readonly CONTROL_CONTAINER="cruzr-vla-control"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD

if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE="check"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/install_ubtech_vla.sh --check
  ./scripts/vla/install_ubtech_vla.sh --stage
  ./scripts/vla/install_ubtech_vla.sh --load-images
  ./scripts/vla/install_ubtech_vla.sh --create-containers
  ./scripts/vla/install_ubtech_vla.sh --verify
  ./scripts/vla/install_ubtech_vla.sh --install

Modos:
  --check              Comprueba paquete, hosts, arquitecturas, disco e imágenes.
  --stage              Sincroniza código y pesos; permite reanudar transferencias.
  --load-images        Sincroniza y carga las imágenes Docker en la placa correcta.
  --create-containers  Crea ambos contenedores detenidos y sin autoarranque.
  --verify             Verifica instalación, montajes y dependencias sin movimiento.
  --install            Ejecuta stage, load-images, create-containers y verify.

La instalación NO habilita ni ejecuta el VLA. Activarlo exige primero corregir y
validar el ejecutor de movimiento suministrado y realizar ensayos en shadow mode.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

while (($#)); do
  case "$1" in
    --check|--stage|--load-images|--create-containers|--verify|--install)
      MODE="${1#--}"
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

for command_name in ssh rsync setsid nc readlink stat; do
  command -v "$command_name" >/dev/null 2>&1 || die "Falta '$command_name'."
done

ssh_options=(
  -o ConnectTimeout=10
  -o ConnectionAttempts=1
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=4
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
  setsid -w rsync \
    --archive \
    --human-readable \
    --partial \
    --append-verify \
    --info=progress2 \
    "$@" \
    -e "$ssh_command" \
    "$source_path" "$ROBOT_USER@$host:$destination_path"
}

assert_local_package() {
  [[ -d "$VISION_ADDITIONAL/vla-onboard" ]] || die "Falta vla-onboard."
  [[ -d "$MOTION_ADDITIONAL/vla-motionx86" ]] || die "Falta vla-motionx86."
  [[ -s "$CHECKPOINT/config.json" ]] || die "Falta config.json del checkpoint."
  [[ -s "$CHECKPOINT/model-00001-of-00002.safetensors" ]] || die "Falta el shard 1."
  [[ -s "$CHECKPOINT/model-00002-of-00002.safetensors" ]] || die "Falta el shard 2."
  [[ -s "$CHECKPOINT/model.safetensors.index.json" ]] || die "Falta el índice de shards."
  [[ -s "$CHECKPOINT/experiment_cfg/metadata.json" ]] || die "Falta metadata.json del checkpoint."
  [[ -s "$CHECKPOINT/experiment_cfg/metadata_cyf.json" ]] || die "Falta metadata_cyf.json del checkpoint."
  [[ -s "$INFERENCE_TAR" ]] || die "Falta la imagen de inferencia."
  [[ -s "$CONTROL_TAR" ]] || die "Falta la imagen de control."
}

assert_hosts() {
  if [[ -z "$VISION_HOST" ]]; then
    if nc -z -w2 192.168.11.3 22; then
      VISION_HOST="192.168.11.3"
    elif nc -z -w2 192.168.42.2 22; then
      VISION_HOST="192.168.42.2"
    else
      die "No se alcanza vision ni por Ethernet (192.168.11.3) ni por Wi-Fi (192.168.42.2)."
    fi
  fi
  nc -z -w3 "$VISION_HOST" 22 || die "No se alcanza vision en $VISION_HOST:22."
  nc -z -w3 "$MOTION_HOST" 22 || die "No se alcanza motion en $MOTION_HOST:22."
  info "CONTROL_HOSTS=vision:$VISION_HOST,motion:$MOTION_HOST"
}

check_remote() {
  local host="$1"
  local expected_arch="$2"
  local minimum_kib="$3"
  local actual_arch available_kib

  actual_arch="$(run_ssh "$host" 'uname -m')"
  [[ "$actual_arch" == "$expected_arch" ]] || \
    die "$host tiene arquitectura $actual_arch; se esperaba $expected_arch."
  available_kib="$(run_ssh "$host" "df -Pk /home/walker | awk 'NR==2 {print \$4}'")"
  [[ "$available_kib" =~ ^[0-9]+$ ]] || die "No se pudo leer el disco de $host."
  ((available_kib >= minimum_kib)) || \
    die "$host no tiene espacio suficiente: ${available_kib} KiB libres."
  info "REMOTE_OK=$host arch:$actual_arch free_kib:$available_kib"
}

check_all() {
  local hw_type_count
  assert_local_package
  assert_hosts
  # Incluye margen para tar temporal + imagen cargada + código/pesos.
  check_remote "$VISION_HOST" aarch64 100000000
  check_remote "$MOTION_HOST" x86_64 50000000
  hw_type_count="$(run_ssh "$MOTION_HOST" \
    'for c in walker-motion.hw-1 walker-motion.t800_mc_server-1 walker-motion.manipulation_robot_app-1; do docker inspect --format "{{range .Config.Env}}{{println .}}{{end}}" "$c"; done' |
    grep -c '^HW_TYPE=cruzr_s2_v1$')"
  [[ "$hw_type_count" == "3" ]] || die "HW_TYPE no corresponde a las abrazaderas Cruzr S2."
  info "PACKAGE_OK=code:codes-S2,checkpoint:checkpoint-40000,effectors:clamps"
}

prepare_remote_directories() {
  local host
  for host in "$VISION_HOST" "$MOTION_HOST"; do
    run_ssh "$host" "install -d '$REMOTE_ROOT/additional' '$REMOTE_ROOT/images' '$REMOTE_ROOT/manifests'"
  done
}

stage_payload() {
  check_all
  prepare_remote_directories

  info "[1/3] Sincronizando workspace de inferencia con vision..."
  run_rsync "$VISION_ADDITIONAL/" "$VISION_HOST" "$REMOTE_ROOT/additional/"

  info "[2/3] Sincronizando pesos de inferencia con vision..."
  run_rsync "$CHECKPOINT/" "$VISION_HOST" "$REMOTE_ROOT/additional/checkpoint-40000/" \
    --include='/config.json' \
    --include='/model-00001-of-00002.safetensors' \
    --include='/model-00002-of-00002.safetensors' \
    --include='/model.safetensors.index.json' \
    --include='/experiment_cfg/' \
    --include='/experiment_cfg/metadata.json' \
    --include='/experiment_cfg/metadata_cyf.json' \
    --exclude='*'

  info "[3/3] Sincronizando workspace de control con motion..."
  run_rsync "$MOTION_ADDITIONAL/" "$MOTION_HOST" "$REMOTE_ROOT/additional/"
  info "STAGE_OK"
}

sync_and_load_image() {
  local source_tar="$1"
  local host="$2"
  local image="$3"
  local remote_tar="$REMOTE_ROOT/images/$(basename -- "$source_tar")"

  if run_ssh "$host" "docker image inspect '$image' >/dev/null 2>&1"; then
    info "IMAGE_ALREADY_LOADED=$host:$image"
    return
  fi

  info "Sincronizando $(basename -- "$source_tar") con $host; la copia es reanudable..."
  run_rsync "$source_tar" "$host" "$remote_tar"
  info "Cargando $image en $host..."
  run_ssh "$host" "docker load --input '$remote_tar'"
  run_ssh "$host" "docker image inspect '$image' --format 'IMAGE_OK={{.RepoTags}} arch={{.Architecture}} id={{.Id}} size={{.Size}}'"
}

load_images() {
  check_all
  prepare_remote_directories
  sync_and_load_image "$INFERENCE_TAR" "$VISION_HOST" "$INFERENCE_IMAGE"
  sync_and_load_image "$CONTROL_TAR" "$MOTION_HOST" "$CONTROL_IMAGE"
  info "IMAGES_OK"
}

create_stopped_container() {
  local host="$1"
  local name="$2"
  local image="$3"
  local runtime_args="$4"

  run_ssh "$host" "
    if docker container inspect '$name' >/dev/null 2>&1; then
      state=\$(docker inspect '$name' --format '{{.State.Status}}')
      [ \"\$state\" != running ] || { echo '$name está activo inesperadamente' >&2; exit 1; }
      docker rm '$name' >/dev/null
    fi
    docker create \
      --name '$name' \
      --network host \
      --restart no \
      $runtime_args \
      -e ROS_DOMAIN_ID=0 \
      -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
      -v '$REMOTE_ROOT/additional:/home/ubt/additional:rw' \
      -v '/dev/shm:/dev/shm:rw' \
      -v '/tmp:/tmp:rw' \
      '$image' bash -lc 'exec sleep infinity' >/dev/null
    docker inspect '$name' --format 'CONTAINER_OK={{.Name}} state={{.State.Status}} restart={{.HostConfig.RestartPolicy.Name}} image={{.Config.Image}}'
  "
}

create_containers() {
  check_all
  run_ssh "$VISION_HOST" "docker image inspect '$INFERENCE_IMAGE' >/dev/null" || \
    die "La imagen de inferencia todavía no está cargada."
  run_ssh "$MOTION_HOST" "docker image inspect '$CONTROL_IMAGE' >/dev/null" || \
    die "La imagen de control todavía no está cargada."

  create_stopped_container "$VISION_HOST" "$INFERENCE_CONTAINER" "$INFERENCE_IMAGE" '--runtime nvidia'
  create_stopped_container "$MOTION_HOST" "$CONTROL_CONTAINER" "$CONTROL_IMAGE" ''
  info "CONTAINERS_CREATED_STOPPED=yes"
}

verify_installation() {
  check_all
  run_ssh "$VISION_HOST" "
    test -s '$REMOTE_ROOT/additional/checkpoint-40000/config.json'
    test -s '$REMOTE_ROOT/additional/checkpoint-40000/model-00001-of-00002.safetensors'
    test -s '$REMOTE_ROOT/additional/checkpoint-40000/model-00002-of-00002.safetensors'
    test -s '$REMOTE_ROOT/additional/checkpoint-40000/experiment_cfg/metadata.json'
    test -s '$REMOTE_ROOT/additional/checkpoint-40000/experiment_cfg/metadata_cyf.json'
    test -s '$REMOTE_ROOT/additional/vla-onboard/install/setup.bash'
    docker image inspect '$INFERENCE_IMAGE' >/dev/null
    test \"\$(docker inspect '$INFERENCE_CONTAINER' --format '{{.State.Status}}')\" != running
    test \"\$(docker inspect '$INFERENCE_CONTAINER' --format '{{.HostConfig.RestartPolicy.Name}}')\" = no
    echo 'VISION_VLA_OK=files,image,container-stopped'
  "
  run_ssh "$MOTION_HOST" "
    test -s '$REMOTE_ROOT/additional/vla-motionx86/install/setup.bash'
    docker image inspect '$CONTROL_IMAGE' >/dev/null
    test \"\$(docker inspect '$CONTROL_CONTAINER' --format '{{.State.Status}}')\" != running
    test \"\$(docker inspect '$CONTROL_CONTAINER' --format '{{.HostConfig.RestartPolicy.Name}}')\" = no
    echo 'MOTION_VLA_OK=files,image,container-stopped'
  "
  info "VLA_INSTALLED_DISABLED=yes"
  info "MOVEMENT_COMMANDS_PUBLISHED=0"
}

case "$MODE" in
  check)
    check_all
    info "CHECK_OK: no se transfirió, cargó, creó ni ejecutó nada."
    ;;
  stage)
    stage_payload
    ;;
  load-images)
    load_images
    ;;
  create-containers)
    create_containers
    ;;
  verify)
    verify_installation
    ;;
  install)
    stage_payload
    load_images
    create_containers
    verify_installation
    ;;
esac
