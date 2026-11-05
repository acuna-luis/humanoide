#!/usr/bin/env bash
# CVAT Community installation helper. Run ON the selected server, never robot.
set -euo pipefail
umask 077

readonly CVAT_RELEASE=v2.79.0
readonly CVAT_COMMIT=9176834830e2e931a8d3a6857dcf43c6cc0ee927
readonly ARCHIVE_SHA256=dd269cb19c73f841c7bcd029c92fd1876eadd5a212fb4b55a2c7594511dd8c14
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage: bash cvat.sh COMMAND [INSTALL_DIR]
Default INSTALL_DIR: $HOME/app2/cvat (source/config only; Docker stores data).
  --prepare     Download and verify pinned upstream source; no Docker changes.
  --check       Check effective Compose, free SSD space and port; read only.
  --lock        Resolve all image digests into INSTALL_DIR/images.lock.yml.
  --pull        Download images using the existing digest lock.
  --up          Start only project app2-cvat, using the existing digest lock.
  --admin       Interactive createsuperuser; password stays in the terminal.
  --status      Show only this project's containers and local UI/API status.
  --config      Print effective Compose JSON (does not contain admin password).
  --down        Stop/remove this project's containers/network; KEEP volumes.
No apt, driver changes, GPU allocation, cloud uploads, or volume deletion.
EOF
}

COMMAND=${1:---help}
if [[ "$COMMAND" == --help || "$COMMAND" == -h ]]; then usage; exit 0; fi
readonly INSTALL_DIR=${2:-"$HOME/app2/cvat"}
readonly UPSTREAM="$INSTALL_DIR/upstream"
readonly LOCK="$INSTALL_DIR/images.lock.yml"
readonly OVERRIDE="$SCRIPT_DIR/compose.app2.yml"

case "$COMMAND" in
  --prepare|--check|--lock|--pull|--up|--admin|--status|--config|--down) ;;
  *) usage >&2; exit 2 ;;
esac

if [[ "$COMMAND" == --prepare ]]; then
  for dep in curl tar sha256sum python3; do command -v "$dep" >/dev/null; done
  if [[ -e "$UPSTREAM" ]]; then
    [[ -f "$INSTALL_DIR/SOURCE_COMMIT" && "$(cat "$INSTALL_DIR/SOURCE_COMMIT")" == "$CVAT_COMMIT" ]] || {
      echo 'Existing upstream has no matching source receipt; refusing overwrite.' >&2; exit 1;
    }
    echo "Pinned source already prepared: $UPSTREAM"
    exit 0
  fi
  mkdir -p -- "$INSTALL_DIR"
  tmp_dir=$(mktemp -d "$INSTALL_DIR/.prepare.XXXXXX")
  trap 'rm -rf -- "$tmp_dir"' EXIT
  curl --fail --location --retry 3 --connect-timeout 20 --max-time 600 \
    "https://codeload.github.com/cvat-ai/cvat/tar.gz/$CVAT_COMMIT" -o "$tmp_dir/upstream.tar.gz"
  printf '%s  %s\n' "$ARCHIVE_SHA256" "$tmp_dir/upstream.tar.gz" | sha256sum --check -
  mkdir -- "$tmp_dir/source"
  # This pinned, checksum-verified vendor archive contains read-only bind
  # mounts consumed by UID1000 (Vector) and UID472 (Grafana). Preserve its
  # source modes even with our private receipt/lock umask; otherwise a
  # non-root tar extraction can make those mounts unreadable to containers.
  tar --extract --gzip --same-permissions --file "$tmp_dir/upstream.tar.gz" \
    --strip-components=1 --directory "$tmp_dir/source"
  mv -- "$tmp_dir/source" "$UPSTREAM"
  printf '%s\n' "$CVAT_COMMIT" > "$INSTALL_DIR/SOURCE_COMMIT"
  printf '%s\n' "$ARCHIVE_SHA256" > "$INSTALL_DIR/SOURCE_ARCHIVE_SHA256"
  echo "Prepared $CVAT_RELEASE ($CVAT_COMMIT); no containers created."
  exit 0
fi

command -v docker >/dev/null
command -v python3 >/dev/null
[[ -f "$UPSTREAM/docker-compose.yml" && -f "$INSTALL_DIR/SOURCE_COMMIT" ]] || {
  echo 'Run --prepare first.' >&2; exit 1;
}
[[ "$(cat "$INSTALL_DIR/SOURCE_COMMIT")" == "$CVAT_COMMIT" ]] || {
  echo 'Source commit mismatch.' >&2; exit 1;
}

# Explicit files/env avoid ambient .env / COMPOSE_FILE affecting deployment.
compose_base() {
  env -u COMPOSE_FILE -u COMPOSE_PROFILES CVAT_VERSION="$CVAT_RELEASE" CVAT_HOST=localhost \
    docker compose --project-name app2-cvat --project-directory "$UPSTREAM" \
      --env-file /dev/null -f "$UPSTREAM/docker-compose.yml" -f "$OVERRIDE" "$@"
}
compose_locked() {
  [[ -s "$LOCK" ]] || { echo 'Run --lock first; image digests are required.' >&2; return 1; }
  compose_base -f "$LOCK" "$@"
}

check_config() {
  compose_base config --format json | python3 -c '
import json, sys
c = json.load(sys.stdin)
assert c["name"] == "app2-cvat"
assert all(not s.get("container_name") for s in c["services"].values())
ports = [(n,p) for n,s in c["services"].items() for p in s.get("ports", [])]
assert len(ports) == 1, ports
n,p = ports[0]
assert (n,p["host_ip"],str(p["published"]),p["target"]) == ("traefik","127.0.0.1","18080",8080), ports
assert c["networks"]["cvat"]["name"] == "app2-cvat_cvat"
assert all(v["name"].startswith("app2-cvat_") and not v.get("external") for v in c["volumes"].values())
e=c["services"]["traefik"]["environment"]
assert e["TRAEFIK_PROVIDERS_DOCKER_NETWORK"] == "app2-cvat_cvat"
assert e["TRAEFIK_PROVIDERS_DOCKER_CONSTRAINTS"] == "Label(`com.docker.compose.project`,`app2-cvat`)"
print("COMPOSE_ISOLATION_OK=1; 18 services, one loopback port, project-scoped named volumes")'
}

case "$COMMAND" in
  --config) compose_base config --format json ;;
  --check)
    check_config
    docker compose version
    docker_root=$(docker info --format '{{.DockerRootDir}}')
    [[ "$docker_root" == /var/lib/docker ]] || { echo "Unexpected DockerRootDir: $docker_root" >&2; exit 1; }
    findmnt -T "$docker_root" -o SOURCE,TARGET,FSTYPE
    df -h -- "$docker_root" "$INSTALL_DIR"
    python3 - "$docker_root" <<'PY'
import os, sys
s = os.statvfs(sys.argv[1])
available = s.f_bavail * s.f_frsize
assert available >= 200 * 1024**3, f"Less than 200 GiB free in DockerRootDir: {available} bytes"
print(f"DOCKER_DISK_OK=1; available_GiB={available / 1024**3:.2f}; no quota applied")
PY
    existing=$(docker ps -aq --filter label=com.docker.compose.project=app2-cvat)
    if [[ -z "$existing" ]] && [[ -n "$(ss -H -ltn 'sport = :18080')" ]]; then
      echo 'Port 18080 already used outside this deployment; refusing.' >&2; exit 1
    fi
    docker ps -a --filter label=com.docker.compose.project=app2-cvat --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
    ;;
  --lock)
    check_config
    [[ ! -e "$LOCK" ]] || { echo 'Digest lock exists; preserve it. No automatic refresh.' >&2; exit 1; }
    tmp_lock=$(mktemp "$INSTALL_DIR/.images.lock.XXXXXX")
    trap 'rm -f -- "$tmp_lock"' EXIT
    compose_base config --lock-image-digests --output "$tmp_lock"
    mv -- "$tmp_lock" "$LOCK"
    sha256sum -- "$LOCK"
    ;;
  --pull) compose_locked pull ;;
  --up)
    bash "$SCRIPT_DIR/cvat.sh" --check "$INSTALL_DIR"
    compose_locked up -d --no-build
    ;;
  --admin) compose_locked exec cvat_server python3 /opt/cvat/manage.py createsuperuser ;;
  --status)
    compose_locked ps -a
    curl --fail --silent --show-error --max-time 20 http://localhost:18080/api/server/about
    printf '\n'
    curl --fail --silent --show-error --max-time 20 --output /dev/null \
      --write-out 'UI_HTTP_STATUS=%{http_code}\n' http://localhost:18080/
    ;;
  --down) compose_locked down ;;
esac
