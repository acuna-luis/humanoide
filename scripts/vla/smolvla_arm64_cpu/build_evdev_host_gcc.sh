#!/usr/bin/env bash
set -Eeuo pipefail

# Experimental build-only helper. It does not publish, access ROS, configure
# the host, or change network settings. Never treats a wheel as qualified.
BASE='sha256:4703adf8fdd93b1441114e4f87ce2c62f7373fc5f88bda6a546c551625bcc71c'
usage() {
  printf '%s\n' 'Usage: bash build_evdev_host_gcc.sh --check INPUTS | --build INPUTS NEW_OUTPUT'
  printf '%s\n' 'Experimental, not yet run. Needs ARM64 GCC 11.4 and isolated Python base.'
}
if [[ $# == 1 && ( $1 == --help || $1 == -h ) ]]; then usage; exit 0; fi
[[ $# -ge 2 ]] || { usage >&2; exit 2; }
mode=$1
[[ $mode == --check && $# == 2 || $mode == --build && $# == 3 ]] || { usage >&2; exit 2; }
inputs=$(realpath -e -- "$2")
[[ -d $inputs && ! -L $2 ]] || { printf 'Invalid inputs\n' >&2; exit 1; }
[[ $(uname -m) == aarch64 && $(gcc -dumpmachine) == aarch64-linux-gnu && $(gcc -dumpfullversion) == 11.4.0 ]] || {
  printf 'Requires inspected ARM64 GCC 11.4.0; no build attempted\n' >&2; exit 1;
}
[[ $(docker image inspect --format '{{.Id}}|{{.Architecture}}' "$BASE") == "$BASE|arm64" ]] || {
  printf 'Expected local ARM64 image ID absent\n' >&2; exit 1;
}
for dir in /usr/bin /usr/lib/gcc/aarch64-linux-gnu/11 /usr/include /usr/lib/aarch64-linux-gnu; do
  [[ -d $dir ]] || { printf 'Missing toolchain directory: %s\n' "$dir" >&2; exit 1; }
done
for file in /usr/bin/aarch64-linux-gnu-gcc-11 /usr/bin/aarch64-linux-gnu-as \
            /usr/bin/aarch64-linux-gnu-ld.bfd /usr/lib/gcc/aarch64-linux-gnu/11/cc1 \
            /usr/include/linux/input.h /usr/include/aarch64-linux-gnu/gnu/stubs.h \
            /usr/lib/aarch64-linux-gnu/crti.o /usr/lib/aarch64-linux-gnu/crtn.o \
            /usr/lib/aarch64-linux-gnu/libc.so /usr/lib/aarch64-linux-gnu/libc_nonshared.a; do
  [[ -f $file ]] || { printf 'Missing toolchain file: %s\n' "$file" >&2; exit 1; }
done
check_file() {
  local name=$1 expected=$2
  [[ -f "$inputs/$name" && ! -L "$inputs/$name" ]] || { printf 'Missing input %s\n' "$name" >&2; exit 1; }
  [[ $(sha256sum "$inputs/$name" | cut -d' ' -f1) == "$expected" ]] || { printf 'Invalid hash: %s\n' "$name" >&2; exit 1; }
}
check_file evdev-2.0.0.tar.gz 442fb3f4c8dfc9e61e901133c356220c02d663eca8f34722e0cecdd637eba504
check_file setuptools-78.1.0-py3-none-any.whl 3e386e96793c8702ae83d17b853fb93d3e09ef82ec62722e61da5cd22376dcd8
check_file wheel-0.45.1-py3-none-any.whl 708e7481cc80179af0e556bbf0cc00b8444c7321e2700b8d8580231d13017248
if [[ $mode == --check ]]; then
  printf 'Inputs present; build and wheel compatibility remain unverified.\n'
  exit 0
fi
out_parent=$(realpath -e -- "$(dirname -- "$3")")
out="$out_parent/$(basename -- "$3")"
[[ ! -e $out && ! -L $out && $out != "$inputs" && $out != "$inputs/"* ]] || { printf 'Output must be new and separate\n' >&2; exit 1; }
mkdir -m 700 -- "$out"
token=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
container_name="cruzr-evdev-arm64-build-$token"
cleanup() {
  local owner
  owner=$(timeout 5 docker inspect --format '{{index .Config.Labels "cruzr.evdev.owner"}}' "$container_name" 2>/dev/null || true)
  if [[ $owner == "$token" ]]; then
    timeout 10 docker stop --time 3 "$container_name" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
printf 'Temporary container: %s\n' "$container_name" >&2

# Host toolchain paths are mounted below /host, leaving container /usr intact.
# These mounts are read-only; no ROS, docker socket, devices, network or host
# control paths are exposed. If libraries differ, fail rather than substitute.
timeout --signal=TERM --kill-after=10 300 docker run --rm -i --name "$container_name" \
  --label "cruzr.evdev.owner=$token" --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 128 --memory 2g --memory-swap 2g --cpus 2 \
  --user "$(id -u):$(id -g)" --tmpfs /tmp:rw,nosuid,nodev,size=1g \
  --mount "type=bind,src=$inputs,dst=/input,readonly" --mount "type=bind,src=$out,dst=/output" \
  --mount type=bind,src=/usr/bin,dst=/host/usr/bin,readonly \
  --mount type=bind,src=/usr/lib/gcc/aarch64-linux-gnu/11,dst=/host/gcc,readonly \
  --mount type=bind,src=/usr/include,dst=/host/usr/include,readonly \
  --mount type=bind,src=/usr/lib/aarch64-linux-gnu,dst=/host/usr/lib/aarch64-linux-gnu,readonly \
  -e HOME=/tmp -e PIP_NO_CACHE_DIR=1 -e PYTHONDONTWRITEBYTECODE=1 \
  "$BASE" /bin/sh -eu <<'SH'
mkdir /tmp/compiler-libs
for lib in libisl.so.23 libmpc.so.3 libmpfr.so.6 libgmp.so.10 libzstd.so.1 \
           libopcodes-2.38-system.so libbfd-2.38-system.so libctf.so.0; do
  test -f "/host/usr/lib/aarch64-linux-gnu/$lib"
  ln -s "/host/usr/lib/aarch64-linux-gnu/$lib" "/tmp/compiler-libs/$lib"
done
export LD_LIBRARY_PATH=/tmp/compiler-libs
export PATH=/host/usr/bin:/usr/local/bin:/usr/bin:/bin
export CC=/host/usr/bin/aarch64-linux-gnu-gcc-11
export C_INCLUDE_PATH=/host/usr/include:/host/usr/include/aarch64-linux-gnu
export CFLAGS='-B/host/gcc/ -B/host/usr/bin/ -B/host/usr/lib/aarch64-linux-gnu/ -isystem /host/usr/include -isystem /host/usr/include/aarch64-linux-gnu'
# The host linker script refers to a host-only absolute static archive path.
# Rewrite only that reference in a tmpfs copy; leave the container's dynamic
# libc in use. ABI still requires a clean independent wheel-import test.
mkdir /tmp/linker-libs
sed 's@/usr/lib/aarch64-linux-gnu/libc_nonshared.a@/host/usr/lib/aarch64-linux-gnu/libc_nonshared.a@g' /host/usr/lib/aarch64-linux-gnu/libc.so > /tmp/linker-libs/libc.so
export LDFLAGS='-L/tmp/linker-libs -L/host/usr/lib/aarch64-linux-gnu'
/usr/local/bin/python -m venv /tmp/build-venv
/tmp/build-venv/bin/python -m pip install --no-index --no-deps --find-links=/input setuptools==78.1.0 wheel==0.45.1
/tmp/build-venv/bin/python -m pip wheel --no-build-isolation --no-deps --no-index --wheel-dir /output /input/evdev-2.0.0.tar.gz
SH
expected_wheel="$out/evdev-2.0.0-cp312-cp312-linux_aarch64.whl"
[[ -f $expected_wheel && ! -L $expected_wheel ]] || { printf 'Wheel expected but not found\n' >&2; exit 1; }
sha256sum "$expected_wheel"
printf 'Candidate wheel created; validate its ABI and import separately before use.\n'
