#!/usr/bin/env bash
# Initialise only the public app2 cache; never mount a host directory/dataset.
set -euo pipefail
readonly CACHE_VOLUME=app2_training_cache
purpose=$(docker volume inspect "$CACHE_VOLUME" --format '{{index .Labels "app2.purpose"}}')
[[ "$purpose" == public-model-and-library-cache ]] || {
  echo 'Unexpected cache volume; refusing ownership changes.' >&2
  exit 1
}
docker run --rm --network none --read-only --user 0:0 \
  --cap-drop ALL --cap-add CHOWN --cap-add DAC_OVERRIDE \
  --security-opt no-new-privileges --pids-limit 64 --memory 256m --cpus 1 \
  --mount "type=volume,source=$CACHE_VOLUME,target=/cache" \
  --entrypoint /bin/sh app2-rfdetr:1.11.2-torch2.10.0-cu128 -c '
    mkdir -p /cache/xdg/torch/kernels
    chown -R 10001:10001 /cache/xdg
  '
echo 'APP2_PUBLIC_KERNEL_CACHE_READY=1'
