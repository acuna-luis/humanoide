#!/usr/bin/env bash
set -Eeuo pipefail

# Únicamente inferencia de observaciones por stdin; stdout JSONL, logs stderr.
# No monta el robot, ROS, sockets ni red; nunca publica comandos de actuador.
IMAGE='cruzr-smolvla-ball:0.5.1-1396b9fa'
IMAGE_ID='sha256:4d15e9e6c5a1071bfe522a5258a8db07b448bc29f698c4a48c43c252754f36fa'
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
usage() {
  cat <<'EOF'
Uso: bash shadow_live_inference.sh TRAIN_DIR MODEL_VOLUME CHECKPOINT_DIR DEVICE SEED MAX_SAMPLES
Entrada: JSONL de observaciones por stdin. Salida: eventos ready/prediction/done por stdout.
El proceso termina en EOF, al máximo (1..1000 muestras) o al límite de 300 s.
Ejecuta modelo verificado en Docker sin red ni ROS; sin acciones físicas.
EOF
}
if [[ $# == 1 && ( $1 == '--help' || $1 == '-h' ) ]]; then usage; exit 0; fi
[[ $# == 6 ]] || { usage >&2; exit 2; }
train="$(realpath -e -- "$1")"
volume="$2"
checkpoint="$(realpath -e -- "$3")"
[[ -d "$train" && -d "$checkpoint" ]] || exit 2
[[ "$volume" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || exit 2
[[ "$4" == cpu || "$4" == cuda ]] || exit 2
[[ "$5" =~ ^[0-9]{1,10}$ ]] && (( 10#$5 <= 2147483647 )) || exit 2
[[ "$6" =~ ^[0-9]{1,4}$ ]] && (( 10#$6 >= 1 && 10#$6 <= 1000 )) || exit 2
[[ "$(docker image inspect --format '{{.Id}}' "$IMAGE")" == "$IMAGE_ID" ]] || {
  printf 'La imagen no coincide con el hash verificado.\n' >&2; exit 1;
}
docker volume inspect "$volume" >/dev/null
token="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
name="cruzr-ball-live-shadow-$token"
cleanup() {
  local owner
  owner="$(timeout 5 docker inspect --format '{{index .Config.Labels "cruzr.shadow.owner"}}' "$name" 2>/dev/null || true)"
  if [[ "$owner" == "$token" ]]; then
    timeout 10 docker stop --time 3 "$name" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
gpu_args=()
if [[ "$4" == cuda ]]; then gpu_args=(--gpus device=0); fi
timeout --signal=TERM --kill-after=10 300 \
  docker run -i --rm --init --name "$name" --label "cruzr.shadow.owner=$token" \
  --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=4g \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 512 --memory 32g --cpus 4 \
  --shm-size 1g "${gpu_args[@]}" --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e HF_HUB_DISABLE_TELEMETRY=1 \
  -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1 -e WANDB_DISABLED=true -e TOKENIZERS_PARALLELISM=false \
  --mount "type=bind,src=$train,dst=/train,readonly" \
  --mount "type=bind,src=$checkpoint,dst=/checkpoint,readonly" \
  --mount "type=volume,src=$volume,dst=/models,readonly" \
  --mount "type=bind,src=$SCRIPT_DIR/shadow_live_inference.py,dst=/opt/cruzr/shadow_live_inference.py,readonly" \
  --mount "type=bind,src=$SCRIPT_DIR/evaluate_failed_offline.py,dst=/opt/cruzr/evaluate_failed_offline.py,readonly" \
  --mount "type=bind,src=$SCRIPT_DIR/evaluate_train_offline.py,dst=/opt/cruzr/evaluate_train_offline.py,readonly" \
  --mount "type=bind,src=$SCRIPT_DIR/train_offline.py,dst=/opt/cruzr/train_offline.py,readonly" \
  "$IMAGE" python -u -B /opt/cruzr/shadow_live_inference.py \
  --train /train --checkpoint /checkpoint --vlm /models/smolvlm2_500m_video \
  --device "$4" --seed "$5" --max-samples "$6"
