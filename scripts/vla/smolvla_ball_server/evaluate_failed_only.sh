#!/usr/bin/env bash
set -euo pipefail
IMAGE='cruzr-smolvla-ball:0.5.1-1396b9fa'
IMAGE_ID='sha256:4d15e9e6c5a1071bfe522a5258a8db07b448bc29f698c4a48c43c252754f36fa'
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
usage() {
  cat <<'EOF'
Uso: evaluate_failed_only.sh TEST TRAIN MODEL_VOLUME CHECKPOINT OUTPUT_NUEVO DEVICE SEED TEST_MANIFEST_SHA256
Evalúa observaciones fallidas de otra captura; sin red, robot, entrenamiento ni publicación.
El modelo utiliza la normalización del entrenamiento; test contiene sólo observaciones.
EOF
}
if [[ $# == 1 && ( $1 == '--help' || $1 == '-h' ) ]]; then usage; exit 0; fi
runner='evaluate_failed_offline.py'
ack='--failed-test-only'
if [[ ${1:-} == '--current' ]]; then
  shift
  runner='evaluate_current_offline.py'
  ack='--current-only'
fi
[[ $# == 8 ]] || { usage >&2; exit 2; }
test_dir="$(realpath -e -- "$1")"
train_dir="$(realpath -e -- "$2")"
volume="$3"
checkpoint="$(realpath -e -- "$4")"
out_parent="$(realpath -e -- "$(dirname -- "$5")")"
out_name="$(basename -- "$5")"
[[ "$out_name" != '.' && "$out_name" != '..' && "$out_name" != '/' ]] || exit 2
out="$out_parent/$out_name"
[[ "$volume" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || exit 2
[[ "$6" == cpu || "$6" == cuda ]] || exit 2
[[ "$7" =~ ^[0-9]+$ ]] && (( 10#$7 <= 2147483647 )) || exit 2
[[ "$8" =~ ^[0-9a-f]{64}$ ]] || exit 2
[[ ! -e "$out" && ! -L "$out" ]] || { printf 'Salida ya existe: %s\n' "$out" >&2; exit 1; }
for p in "$test_dir" "$train_dir" "$checkpoint"; do
  [[ -d "$p" ]] || exit 2
  case "$out/" in "$p/"*) printf 'Salida dentro de entrada prohibida\n' >&2; exit 1;; esac
  case "$p/" in "$out/"*) printf 'Salida contiene una entrada\n' >&2; exit 1;; esac
done
[[ "$(docker image inspect --format '{{.Id}}' "$IMAGE")" == "$IMAGE_ID" ]] || {
  printf 'La imagen del entorno no coincide con el hash verificado\n' >&2; exit 1;
}
docker volume inspect "$volume" >/dev/null
gpu_args=()
if [[ "$6" == cuda ]]; then gpu_args=(--gpus device=0); fi
mkdir -- "$out"
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=4g \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 512 --memory 32g --cpus 4 \
  --shm-size 1g "${gpu_args[@]}" --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e HF_HUB_DISABLE_TELEMETRY=1 \
  -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1 -e WANDB_DISABLED=true -e TOKENIZERS_PARALLELISM=false \
  --mount "type=bind,src=$test_dir,dst=/test,readonly" \
  --mount "type=bind,src=$train_dir,dst=/train,readonly" \
  --mount "type=bind,src=$checkpoint,dst=/checkpoint,readonly" \
  --mount "type=volume,src=$volume,dst=/models,readonly" \
  --mount "type=bind,src=$SCRIPT_DIR/evaluate_failed_offline.py,dst=/opt/cruzr/evaluate_failed_offline.py,readonly" \
  --mount "type=bind,src=$SCRIPT_DIR/evaluate_current_offline.py,dst=/opt/cruzr/evaluate_current_offline.py,readonly" \
  --mount "type=bind,src=$SCRIPT_DIR/evaluate_train_offline.py,dst=/opt/cruzr/evaluate_train_offline.py,readonly" \
  --mount "type=bind,src=$SCRIPT_DIR/train_offline.py,dst=/opt/cruzr/train_offline.py,readonly" \
  --mount "type=bind,src=$out,dst=/out" \
  "$IMAGE" python -B "/opt/cruzr/$runner" --test /test --train /train --checkpoint /checkpoint \
    --vlm /models/smolvlm2_500m_video --output /out --device "$6" --seed "$7" --test-sha256 "$8" "$ack"
