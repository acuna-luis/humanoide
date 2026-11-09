#!/usr/bin/env bash
set -euo pipefail

IMAGE='cruzr-smolvla-ball:0.5.1-1396b9fa'
VOLUME='cruzr-smolvla-ball-public-models-20261109'
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Uso: fetch_models.sh --help | --fetch

--fetch crea un volumen NUEVO y descarga solamente dos modelos públicos fijados.
No incluye datos del robot ni credenciales y no inicia entrenamiento.
Docker bridge NO limita los destinos de red; véase README antes de ejecutarlo.
Si falla, conserva el volumen parcial para inspección; no sobrescribe ni reanuda.
EOF
}

[[ $# == 1 ]] || { usage >&2; exit 2; }
case "$1" in
  --help|-h) usage ;;
  --fetch)
    docker image inspect "$IMAGE" >/dev/null
    if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
      printf 'Volumen %s ya existe; no se sobrescribe ni reanuda.\n' "$VOLUME" >&2
      exit 1
    fi
    docker volume create --label 'org.cruzr.project=smolvla-ball-public-models' "$VOLUME"
    docker run --rm --network bridge --read-only --tmpfs /tmp:rw,nosuid,nodev,noexec \
      --cap-drop ALL --security-opt no-new-privileges --memory 8g --cpus 4 \
      --env HF_HUB_OFFLINE=0 --env HF_HUB_DISABLE_TELEMETRY=1 \
      --env HF_HUB_DISABLE_IMPLICIT_TOKEN=1 --env HF_HUB_DISABLE_XET=1 \
      --env HF_TOKEN= --env HUGGING_FACE_HUB_TOKEN= \
      --env HF_HOME=/models/.hf-cache --env HOME=/tmp \
      --mount "type=volume,src=$VOLUME,dst=/models" \
      --mount "type=bind,src=$SCRIPT_DIR,dst=/recipe,readonly" \
      "$IMAGE" python -B /recipe/fetch_models.py
    ;;
  *) usage >&2; exit 2 ;;
esac
