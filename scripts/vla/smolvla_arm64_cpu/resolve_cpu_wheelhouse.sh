#!/usr/bin/env bash
set -Eeuo pipefail

# Reproduce the PC-side, cross-platform candidate; it does not contact Vision.
# The marker adjustment uses pip 24.0 internals and is not a native ARM64 test.
FREEZE_SHA='1011c64be675704b6e95c3e9df9e250d2c82986fb91af50aa2b58aef56575f8e'
DOCOPT_SHA='924cfbf4d2654b5494650ee50ffb3d15b522cdff45eef3f1a2a948108e0c9ffd'
EVDEV_SHA='608caec9870027cc36b7c1b552b849b096e5fa001fb3264da49e2efb698f98bb'
CONSTRAINTS_SHA='43f61aa31b210761b8b77847e6cac3334a1419dfe59e612d34d5ab9bec04a7b5'
MANIFEST_SHA='a92db7e630c79b22f5b36f5eabf6f136a36b51db40bf314b456bc39258daed4f'
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
usage() {
  printf '%s\n' 'Usage: bash resolve_cpu_wheelhouse.sh --check FREEZE BUILT_WHEELS'
  printf '%s\n' '       bash resolve_cpu_wheelhouse.sh --download FREEZE BUILT_WHEELS NEW_OUTPUT'
  printf '%s\n' 'The download requires Internet. It creates a candidate only; no robot or installation.'
}
if [[ $# == 1 && ( $1 == --help || $1 == -h ) ]]; then usage; exit 0; fi
[[ $# -ge 3 ]] || { usage >&2; exit 2; }
mode=$1
[[ $mode == --check && $# == 3 || $mode == --download && $# == 4 ]] || { usage >&2; exit 2; }
[[ ! -L $2 && ! -L $3 ]] || { printf 'Inputs must not be symlinks\n' >&2; exit 1; }
freeze=$(realpath -e -- "$2")
built=$(realpath -e -- "$3")
[[ -f $freeze && -d $built ]] || exit 1
hash_is() {
  local path=$1 expected=$2
  [[ -f $path && ! -L $path && $(sha256sum "$path" | cut -d' ' -f1) == "$expected" ]] || {
    printf 'Missing or changed input: %s\n' "$path" >&2; exit 1;
  }
}
hash_is "$freeze" "$FREEZE_SHA"
hash_is "$built/docopt-0.6.2-py2.py3-none-any.whl" "$DOCOPT_SHA"
hash_is "$built/evdev-2.0.0-cp312-cp312-linux_aarch64.whl" "$EVDEV_SHA"
python3 -B -c 'import platform,sys,pip; assert platform.machine()=="x86_64" and sys.version_info[:2]==(3,12) and pip.__version__=="24.0", "requires checked x86_64 Python 3.12 and pip 24.0"'
if [[ $mode == --check ]]; then printf 'Inputs match; no network, output, or installation.\n'; exit 0; fi

parent=$(realpath -e -- "$(dirname -- "$4")")
out="$parent/$(basename -- "$4")"
[[ ! -e $out && ! -L $out && $out != "$built" && $out != "$built/"* && $built != "$out/"* ]] || {
  printf 'Output must be new and separate\n' >&2; exit 1;
}
mkdir -m 700 -- "$out"
mkdir -m 700 -- "$out/wheelhouse"
python3 -B - "$freeze" "$out/constraints-arm64-from-ada.txt" <<'PY'
from pathlib import Path
import sys
rows = Path(sys.argv[1]).read_text(encoding='utf-8').splitlines()
skip = ('nvidia-', 'triton==', 'torchcodec==', 'torch==', 'torchvision==', 'lerobot @')
keep = [row for row in rows if not row.startswith(skip)]
keep += ['torch==2.7.1', 'torchvision==0.22.1', 'lerobot==0.5.1']
with Path(sys.argv[2]).open('x', encoding='utf-8') as out:
    out.write('\n'.join(keep) + '\n')
PY
hash_is "$out/constraints-arm64-from-ada.txt" "$CONSTRAINTS_SHA"
# The target-marker override reflects the prior exploration. It does not prove
# native dependency resolution. Keep network bounded and never write to host
# package locations. Pip's files are limited individually to 1 GiB.
ulimit -f 1048576
PIP_NO_CACHE_DIR=1 PIP_CONFIG_FILE=/dev/null timeout --signal=TERM --kill-after=10 300 \
  python3 -B -c 'import sys; import pip._vendor.packaging.markers as m; orig=m.default_environment; m.default_environment=lambda: dict(orig(),platform_machine="aarch64",sys_platform="linux",platform_system="Linux"); from pip._internal.cli.main import main; sys.exit(main(sys.argv[1:]))' \
  download --timeout 30 --index-url https://pypi.org/simple --only-binary=:all: \
  --find-links "$built" -c "$out/constraints-arm64-from-ada.txt" \
  --platform manylinux_2_28_aarch64 --platform manylinux_2_17_aarch64 \
  --platform manylinux2014_aarch64 --platform linux_aarch64 --python-version 3.12 \
  --implementation cp --abi cp312 --dest "$out/wheelhouse" \
  'lerobot[smolvla]==0.5.1' 'torch==2.7.1' 'torchvision==0.22.1' \
  > "$out/resolver.log" 2>&1
(
  cd "$out/wheelhouse"
  export LC_ALL=C
  shopt -s nullglob
  wheels=(*.whl)
  (( ${#wheels[@]} > 0 )) || exit 1
  sha256sum -- "${wheels[@]}" > SHA256SUMS
)
hash_is "$out/wheelhouse/SHA256SUMS" "$MANIFEST_SHA"
python3 -B "$HERE/check_wheelhouse_manifest.py" "$out/wheelhouse"
printf 'Candidate verified against recorded hashes; native installation and inference remain pending.\n'
