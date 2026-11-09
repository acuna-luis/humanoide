#!/usr/bin/env bash
set -euo pipefail

IMAGE='cruzr-smolvla-ball:0.5.1-1396b9fa'
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
usage() {
  cat <<'EOF'
Uso: run_offline.sh DATASET_BUNDLE MODEL_VOLUME OUTPUT_NUEVO PASOS BATCH CHUNK

Ejecuta un experimento aislado sin red, con entradas sólo lectura y salida nueva.
PASOS 1..20000, BATCH 1..64 y CHUNK 1..8. No contacta ni controla el robot.
Las acciones son hipótesis sin cualificar: el modelo sólo sirve para análisis.
MODEL_VOLUME debe contener smolvla_base y smolvlm2_500m_video y se monta sólo lectura.
EOF
}
if [[ $# == 1 && ( $1 == '--help' || $1 == '-h' ) ]]; then usage; exit 0; fi
[[ $# == 6 ]] || { usage >&2; exit 2; }
dataset="$(realpath -e -- "$1")"
model_volume="$2"
[[ "$model_volume" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || { printf 'Nombre de volumen inválido\n' >&2; exit 2; }
out_parent="$(realpath -e -- "$(dirname -- "$3")")"
out_name="$(basename -- "$3")"
[[ "$out_name" != '.' && "$out_name" != '..' && "$out_name" != '/' ]] || exit 2
out="$out_parent/$out_name"
[[ ! -e "$out" && ! -L "$out" ]] || { printf 'Salida ya existe: %s\n' "$out" >&2; exit 1; }
for p in "$dataset"; do
  [[ -d "$p" ]] || { printf 'Entrada ausente: %s\n' "$p" >&2; exit 1; }
  case "$out/" in "$p/"*) printf 'Salida dentro de entrada prohibida\n' >&2; exit 1;; esac
  case "$p/" in "$out/"*) printf 'Salida contiene una entrada\n' >&2; exit 1;; esac
done
[[ $4 =~ ^[0-9]+$ && $5 =~ ^[0-9]+$ && $6 =~ ^[0-9]+$ ]] || { printf 'Parámetros numéricos inválidos\n' >&2; exit 2; }
(( 10#$4 >= 1 && 10#$4 <= 20000 && 10#$5 >= 1 && 10#$5 <= 64 && 10#$6 >= 1 && 10#$6 <= 8 )) || exit 2
docker image inspect "$IMAGE" >/dev/null
docker volume inspect "$model_volume" >/dev/null
mkdir -- "$out"
printf 'Salida exclusiva: %s\n' "$out"
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=4g \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 512 --memory 64g --cpus 8 \
  --shm-size 1g --gpus device=0 --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e HF_HUB_DISABLE_TELEMETRY=1 \
  -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1 -e WANDB_DISABLED=true -e TOKENIZERS_PARALLELISM=false \
  --mount "type=bind,src=$dataset,dst=/data,readonly" \
  --mount "type=volume,src=$model_volume,dst=/models,readonly" \
  --mount "type=bind,src=$SCRIPT_DIR/train_offline.py,dst=/opt/cruzr/train_offline.py,readonly" \
  --mount "type=bind,src=$out,dst=/out" \
  "$IMAGE" python -B /opt/cruzr/train_offline.py --dataset /data --model /models/smolvla_base \
    --vlm /models/smolvlm2_500m_video --output /out --steps "$4" --batch-size "$5" \
    --chunk-size "$6" --offline-experiment
