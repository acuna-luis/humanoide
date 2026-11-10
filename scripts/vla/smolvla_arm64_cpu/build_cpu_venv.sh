#!/usr/bin/env bash
set -Eeuo pipefail
BASE='sha256:4703adf8fdd93b1441114e4f87ce2c62f7373fc5f88bda6a546c551625bcc71c'
MANIFEST_SHA='a92db7e630c79b22f5b36f5eabf6f136a36b51db40bf314b456bc39258daed4f'
CONSTRAINTS_SHA='43f61aa31b210761b8b77847e6cac3334a1419dfe59e612d34d5ab9bec04a7b5'
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
usage() { printf '%s\n' 'Usage: bash build_cpu_venv.sh --check WHEELHOUSE CONSTRAINTS | --run WHEELHOUSE CONSTRAINTS NEW_OUTPUT'; }
if [[ $# == 1 && ( $1 == --help || $1 == -h ) ]]; then usage; exit 0; fi
[[ $# -ge 3 ]] || { usage >&2; exit 2; }
mode=$1
[[ $mode == --check && $# == 3 || $mode == --run && $# == 4 ]] || { usage >&2; exit 2; }
[[ ! -L $2 && ! -L $3 ]] || exit 1
wheels=$(realpath -e -- "$2")
constraints=$(realpath -e -- "$3")
[[ -d $wheels && -f $constraints && ! -L "$wheels/SHA256SUMS" ]] || exit 1
[[ $(sha256sum "$wheels/SHA256SUMS" | cut -d' ' -f1) == "$MANIFEST_SHA" ]] || { printf 'Manifest pin mismatch\n' >&2; exit 1; }
[[ $(sha256sum "$constraints" | cut -d' ' -f1) == "$CONSTRAINTS_SHA" ]] || { printf 'Constraints pin mismatch\n' >&2; exit 1; }
python3 -B "$HERE/check_wheelhouse_manifest.py" "$wheels"
[[ $(uname -m) == aarch64 && $(docker image inspect --format '{{.Id}}|{{.Architecture}}' "$BASE") == "$BASE|arm64" ]] || {
  printf 'ARM64 host or pinned base missing\n' >&2; exit 1;
}
if [[ $mode == --check ]]; then printf 'Inputs verified; environment not built or qualified.\n'; exit 0; fi
parent=$(realpath -e -- "$(dirname -- "$4")")
out="$parent/$(basename -- "$4")"
[[ ! -e $out && ! -L $out && $out != "$wheels" && $out != "$wheels/"* && $wheels != "$out/"* ]] || {
  printf 'Output must be new and separate\n' >&2; exit 1;
}
mkdir -m 700 -- "$out"
token=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
name="cruzr-smolvla-arm64-build-$token"
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
timeout --signal=TERM --kill-after=10 600 docker run --rm -i --name "$name" \
  --label "cruzr.smolvla.owner=$token" --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 256 --memory 4g --memory-swap 4g --cpus 2 \
  --user "$(id -u):$(id -g)" --tmpfs /tmp:rw,nosuid,nodev,exec,size=1g \
  --mount "type=bind,src=$wheels,dst=/wheelhouse,readonly" \
  --mount "type=bind,src=$constraints,dst=/constraints.txt,readonly" \
  --mount "type=bind,src=$out,dst=/env" \
  -e HOME=/tmp -e PIP_NO_CACHE_DIR=1 -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_DISABLE_TELEMETRY=1 -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1 -e WANDB_DISABLED=true \
  -e PYTHONDONTWRITEBYTECODE=1 -e CUDA_VISIBLE_DEVICES='' "$BASE" /bin/sh -eu <<'SH'
python -m venv /env/venv
/env/venv/bin/python -m pip install --no-index --only-binary=:all: --find-links=/wheelhouse -c /constraints.txt \
  'lerobot[smolvla]==0.5.1' 'torch==2.7.1' 'torchvision==0.22.1'
/env/venv/bin/python -m pip check
/env/venv/bin/python -c 'import platform,sys,importlib.metadata,torch,torchvision; from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy; assert platform.machine()=="aarch64" and sys.version_info >= (3,12); assert importlib.metadata.version("lerobot")=="0.5.1"; assert torch.__version__.split("+")[0]=="2.7.1" and torchvision.__version__.split("+")[0]=="0.22.1" and torch.version.cuda is None; print("SMOLVLA_IMPORT_OK CPU aarch64; model and control not tested")'
SH
printf 'Candidate environment built; inference and hardware control remain unqualified.\n'
