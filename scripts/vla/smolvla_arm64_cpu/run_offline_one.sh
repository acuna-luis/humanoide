#!/usr/bin/env bash
set -Eeuo pipefail

# Offline-only inference on a single recorded observation. Does not connect to
# ROS, mount actuators or create a control publisher. The environment remains
# mounted at the same /env path and base image used to create the virtualenv.
BASE='sha256:4703adf8fdd93b1441114e4f87ce2c62f7373fc5f88bda6a546c551625bcc71c'
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
SOURCE="$HERE/../smolvla_ball_server"
usage() {
  printf '%s\n' 'Usage: bash run_offline_one.sh --check|--run ENV_DIR TRAIN_DIR CHECKPOINT_DIR VLM_DIR OBS_JSONL OBS_SHA256'
  printf '%s\n' 'Single historical sample; isolated CPU inference only, no ROS or movement.'
}
if [[ $# == 1 && ( $1 == --help || $1 == -h ) ]]; then usage; exit 0; fi
[[ $# == 7 && ( $1 == --check || $1 == --run ) ]] || { usage >&2; exit 2; }
mode=$1
for path in "$2" "$3" "$4" "$5" "$6"; do [[ ! -L $path ]] || exit 1; done
env_dir=$(realpath -e -- "$2")
train=$(realpath -e -- "$3")
checkpoint=$(realpath -e -- "$4")
vlm=$(realpath -e -- "$5")
input=$(realpath -e -- "$6")
[[ -d $env_dir && -f $env_dir/venv/pyvenv.cfg && -d $train && -d $checkpoint && -d $vlm && -f $input ]] || exit 1
[[ $7 =~ ^[0-9a-f]{64}$ ]] || exit 2
[[ $(sha256sum "$input" | cut -d' ' -f1) == "$7" ]] || { printf 'Recorded observation hash mismatch\n' >&2; exit 1; }
[[ $(stat -c %s "$input") -le 8388608 && $(wc -l < "$input") == 1 ]] || {
  printf 'Input must contain precisely one bounded JSONL record\n' >&2; exit 1;
}
python3 -B - "$input" <<'PY'
import json, sys
with open(sys.argv[1], 'rb') as stream:
    raw = stream.read(8388609)
if len(raw) > 8388608 or not raw.endswith(b'\n'):
    raise SystemExit('Input must be one newline-terminated JSON record')
try:
    row = json.loads(raw)
except (ValueError, UnicodeError) as exc:
    raise SystemExit('Invalid JSON input: ' + str(exc))
if (not isinstance(row, dict) or row.get('schema') != 'cruzr_ball_live_observation_v1' or
        row.get('source_status') != 'historical_recording_not_live' or
        row.get('physical_control_qualified') is not False or 'pc_received_monotonic_ns' in row):
    raise SystemExit('Input is not explicitly unqualified historical evidence')
PY
check_pin() {
  [[ -f "$SOURCE/$1" && ! -L "$SOURCE/$1" && $(sha256sum "$SOURCE/$1" | cut -d' ' -f1) == "$2" ]] || {
    printf 'Pinned inference source differs: %s\n' "$1" >&2; return 1;
  }
}
check_pin shadow_live_inference.py 1a21a9a7069e06aab11c8f5eaa79ca7ea481d03f017f6f1ea22698efa051c2f5
check_pin evaluate_failed_offline.py 03a30ae8808e9091a24f3f1c4dd31f00bdd5e1f84d556e7aa07f9397ab10f837
check_pin evaluate_train_offline.py 82b3c7e6d3595cd121d0b9f63d0cb40121b7dce35cb7814afd965dd15146b787
check_pin train_offline.py 05b88daae838753891afbdb77097154d21508830d5de5f9341b7f311f9a84eff
[[ $(uname -m) == aarch64 && $(docker image inspect --format '{{.Id}}|{{.Architecture}}' "$BASE") == "$BASE|arm64" ]] || {
  printf 'Pinned ARM64 base image unavailable\n' >&2; exit 1;
}
if [[ $mode == --check ]]; then
  printf '%s\n' 'Inputs/source/base checked; venv integrity and model load not verified. Physical control disabled.'
  exit 0
fi
token=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
name="cruzr-smolvla-arm64-offline-$token"
cleanup() {
  local owner
  owner=$(timeout 5 docker inspect --format '{{index .Config.Labels "cruzr.smolvla.owner"}}' "$name" 2>/dev/null || true)
  if [[ $owner == "$token" ]]; then timeout 10 docker stop --time 3 "$name" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
printf 'Temporary container: %s\n' "$name" >&2
timeout --signal=TERM --kill-after=10 600 docker run --rm -i --init --name "$name" \
  --label "cruzr.smolvla.owner=$token" --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 256 --memory 4g --memory-swap 4g --cpus 2 \
  --user "$(id -u):$(id -g)" --tmpfs /tmp:rw,nosuid,nodev,size=1g \
  --mount "type=bind,src=$env_dir,dst=/env,readonly" \
  --mount "type=bind,src=$train,dst=/train,readonly" \
  --mount "type=bind,src=$checkpoint,dst=/checkpoint,readonly" \
  --mount "type=bind,src=$vlm,dst=/models/smolvlm2_500m_video,readonly" \
  --mount "type=bind,src=$SOURCE/shadow_live_inference.py,dst=/opt/cruzr/shadow_live_inference.py,readonly" \
  --mount "type=bind,src=$SOURCE/evaluate_failed_offline.py,dst=/opt/cruzr/evaluate_failed_offline.py,readonly" \
  --mount "type=bind,src=$SOURCE/evaluate_train_offline.py,dst=/opt/cruzr/evaluate_train_offline.py,readonly" \
  --mount "type=bind,src=$SOURCE/train_offline.py,dst=/opt/cruzr/train_offline.py,readonly" \
  -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e HF_HUB_DISABLE_TELEMETRY=1 \
  -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1 -e WANDB_DISABLED=true -e TOKENIZERS_PARALLELISM=false \
  -e PYTHONDONTWRITEBYTECODE=1 -e CUDA_VISIBLE_DEVICES='' "$BASE" \
  /env/venv/bin/python -B -u /opt/cruzr/shadow_live_inference.py \
  --train /train --checkpoint /checkpoint --vlm /models/smolvlm2_500m_video --device cpu --seed 20261109 --max-samples 1 < "$input"
