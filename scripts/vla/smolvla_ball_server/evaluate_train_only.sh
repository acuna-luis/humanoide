#!/usr/bin/env bash
set -euo pipefail
IMAGE='cruzr-smolvla-ball:0.5.1-1396b9fa'
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
usage() {
  cat <<'EOF'
Uso: evaluate_train_only.sh DATASET_BUNDLE MODEL_VOLUME CHECKPOINT OUTPUT_NUEVO DEVICE SEED [LIMIT]

Evalúa SÓLO muestras de entrenamiento, sin red, robot ni publicación.
DEVICE es cpu o cuda; LIMIT por defecto 60, máximo 60. Salida nueva obligatoria.
EOF
}
if [[ $# == 1 && ( $1 == '--help' || $1 == '-h' ) ]]; then usage; exit 0; fi
[[ $# == 6 || $# == 7 ]] || { usage >&2; exit 2; }
dataset="$(realpath -e -- "$1")"
volume="$2"
checkpoint="$(realpath -e -- "$3")"
out_parent="$(realpath -e -- "$(dirname -- "$4")")"
out_name="$(basename -- "$4")"
[[ "$out_name" != '.' && "$out_name" != '..' && "$out_name" != '/' ]] || exit 2
out="$out_parent/$out_name"
[[ "$volume" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || { printf 'Volumen inválido\n' >&2; exit 2; }
[[ "$5" == cpu || "$5" == cuda ]] || { printf 'DEVICE inválido\n' >&2; exit 2; }
[[ "$6" =~ ^[0-9]+$ && "${7:-60}" =~ ^[0-9]+$ ]] || { printf 'SEED/LIMIT inválido\n' >&2; exit 2; }
(( 10#$6 <= 2147483647 && 10#${7:-60} >= 1 && 10#${7:-60} <= 60 )) || exit 2
[[ ! -e "$out" && ! -L "$out" ]] || { printf 'Salida ya existe: %s\n' "$out" >&2; exit 1; }
for p in "$dataset" "$checkpoint"; do
  [[ -d "$p" ]] || { printf 'Entrada ausente: %s\n' "$p" >&2; exit 1; }
  case "$out/" in "$p/"*) printf 'Salida dentro de entrada prohibida\n' >&2; exit 1;; esac
  case "$p/" in "$out/"*) printf 'Salida contiene una entrada\n' >&2; exit 1;; esac
done
docker image inspect "$IMAGE" >/dev/null
docker volume inspect "$volume" >/dev/null
gpu_args=()
if [[ "$5" == cuda ]]; then gpu_args=(--gpus device=0); fi
mkdir -- "$out"
printf 'Salida exclusiva: %s\n' "$out"
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=4g \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 512 --memory 32g --cpus 4 \
  --shm-size 1g "${gpu_args[@]}" --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e HF_HUB_DISABLE_TELEMETRY=1 \
  -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1 -e WANDB_DISABLED=true -e TOKENIZERS_PARALLELISM=false \
  --mount "type=bind,src=$dataset,dst=/data,readonly" \
  --mount "type=bind,src=$checkpoint,dst=/checkpoint,readonly" \
  --mount "type=volume,src=$volume,dst=/models,readonly" \
  --mount "type=bind,src=$SCRIPT_DIR/evaluate_train_offline.py,dst=/opt/cruzr/evaluate_train_offline.py,readonly" \
  --mount "type=bind,src=$SCRIPT_DIR/train_offline.py,dst=/opt/cruzr/train_offline.py,readonly" \
  --mount "type=bind,src=$out,dst=/out" \
  "$IMAGE" python -B /opt/cruzr/evaluate_train_offline.py --dataset /data --checkpoint /checkpoint \
    --vlm /models/smolvlm2_500m_video --output /out --device "$5" --seed "$6" \
    --limit "${7:-60}" --train-only
