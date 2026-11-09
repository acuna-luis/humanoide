#!/usr/bin/env bash
set -euo pipefail

IMAGE='cruzr-smolvla-ball:0.5.1-1396b9fa'
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Uso: server.sh --help | --check | --build | --gpu-check

--check      Inspecciona Docker, GPU y la etiqueta local; no instala ni inicia.
--build      Construye una imagen nueva sin sobrescribir una etiqueta existente.
--gpu-check  Ejecuta una consulta CUDA temporal aislada, sin red ni datos.

Ninguna opción entrena ni publica datos o comandos. --build requiere Internet.
--gpu-check requiere que la imagen exista y el runtime NVIDIA esté disponible.
EOF
}

[[ $# == 1 ]] || { usage >&2; exit 2; }
case "$1" in
  --help|-h) usage ;;
  --check)
    command -v docker >/dev/null
    command -v nvidia-smi >/dev/null
    docker info --format 'Docker={{.ServerVersion}}' >/dev/null
    nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv,noheader
    if docker image inspect "$IMAGE" >/dev/null 2>&1; then
      docker image inspect --format 'Imagen={{.Id}}' "$IMAGE"
    else
      printf 'Imagen ausente: %s\n' "$IMAGE"
    fi
    ;;
  --build)
    if docker image inspect "$IMAGE" >/dev/null 2>&1; then
      printf 'La etiqueta %s ya existe; no se sobrescribe.\n' "$IMAGE" >&2
      exit 1
    fi
    docker build --pull --tag "$IMAGE" "$SCRIPT_DIR"
    docker image inspect --format 'Imagen={{.Id}}' "$IMAGE"
    ;;
  --gpu-check)
    docker image inspect "$IMAGE" >/dev/null
    docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,noexec \
      --cap-drop ALL --security-opt no-new-privileges --memory 16g --cpus 4 \
      --gpus all "$IMAGE" python -B -c \
      'import torch; print("torch:",torch.__version__); print("CUDA runtime:",torch.version.cuda); assert torch.cuda.is_available(), "CUDA no disponible"; print("GPU:",torch.cuda.get_device_name(0))'
    ;;
  *) usage >&2; exit 2 ;;
esac
