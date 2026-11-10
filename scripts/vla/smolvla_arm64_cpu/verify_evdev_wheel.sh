#!/usr/bin/env bash
set -Eeuo pipefail
BASE='sha256:4703adf8fdd93b1441114e4f87ce2c62f7373fc5f88bda6a546c551625bcc71c'
if [[ $# == 1 && ( $1 == --help || $1 == -h ) ]]; then
  printf '%s\n' 'Usage: bash verify_evdev_wheel.sh --check|--verify WHEEL SHA256'
  exit 0
fi
[[ $# == 3 && ( $1 == --check || $1 == --verify ) && $3 =~ ^[0-9a-f]{64}$ ]] || exit 2
mode=$1
[[ ! -L $2 ]] || { printf 'wheel symlink not allowed\n' >&2; exit 1; }
wheel=$(realpath -e -- "$2")
[[ $(basename -- "$wheel") == evdev-2.0.0-cp312-cp312-linux_aarch64.whl && -f $wheel ]] || exit 1
[[ $(sha256sum "$wheel" | cut -d' ' -f1) == "$3" ]] || { printf 'wheel hash mismatch\n' >&2; exit 1; }
[[ $(uname -m) == aarch64 && $(docker image inspect --format '{{.Id}}|{{.Architecture}}' "$BASE") == "$BASE|arm64" ]] || exit 1
if [[ $mode == --check ]]; then printf 'Inputs valid; no import tested.\n'; exit 0; fi
token=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
name="cruzr-evdev-arm64-verify-$token"
cleanup() {
  local owner
  owner=$(timeout 5 docker inspect --format '{{index .Config.Labels "cruzr.evdev.owner"}}' "$name" 2>/dev/null || true)
  if [[ $owner == "$token" ]]; then timeout 10 docker stop --time 3 "$name" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
printf 'Temporary container: %s\n' "$name" >&2
timeout --signal=TERM --kill-after=10 120 docker run --rm -i --name "$name" \
  --label "cruzr.evdev.owner=$token" --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 64 --memory 512m --memory-swap 512m --cpus 1 \
  --user "$(id -u):$(id -g)" --tmpfs /tmp:rw,nosuid,nodev,exec,size=256m \
  --mount "type=bind,src=$wheel,dst=/input/evdev-2.0.0-cp312-cp312-linux_aarch64.whl,readonly" \
  -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 "$BASE" /bin/sh -eu <<'SH'
python -m venv /tmp/venv
awk '$2=="/tmp" {print "TMP_MOUNT=" $4}' /proc/mounts
/tmp/venv/bin/python -m pip install --no-index --no-deps /input/evdev-2.0.0-cp312-cp312-linux_aarch64.whl
/tmp/venv/bin/python -c 'import importlib.metadata, platform, evdev, evdev._input, evdev._uinput, evdev._ecodes; print("ARCH=" + platform.machine()); print("EVDEV=" + importlib.metadata.version("evdev")); print("EXTENSIONS_IMPORTED=3")'
SH
