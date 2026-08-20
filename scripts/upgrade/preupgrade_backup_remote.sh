#!/usr/bin/env bash

set -Eeuo pipefail

stamp="${1:-}"
if [[ ! "$stamp" =~ ^[0-9]{8}-[0-9]{6}$ ]]; then
  printf 'Uso: %s YYYYMMDD-HHMMSS\n' "$0" >&2
  exit 2
fi

if [[ "$(id -u)" -ne 0 ]]; then
  printf 'Este script debe ejecutarse como root mediante sudo.\n' >&2
  exit 3
fi

owner="walker"
backup_dir="/home/walker/preupgrade-v0.2.0-$stamp"
if [[ -e "$backup_dir" ]]; then
  printf 'El respaldo ya existe: %s\n' "$backup_dir" >&2
  exit 4
fi

install -d -m 0750 -o "$owner" -g "$owner" "$backup_dir"

hostname >"$backup_dir/hostname.txt"
uname -a >"$backup_dir/uname.txt"
cat /etc/walker/system/soft_version >"$backup_dir/soft_version.txt" 2>/dev/null || true
udoke --version >"$backup_dir/udoke-version.txt" 2>&1 || true
uptime >"$backup_dir/uptime.txt"
df -h / /home/walker >"$backup_dir/filesystems.txt"
ip -br address >"$backup_dir/ip-addresses.txt"
ip route >"$backup_dir/ip-routes.txt"
docker ps -a --no-trunc >"$backup_dir/docker-ps-a.txt"
docker image ls --no-trunc >"$backup_dir/docker-images.txt"

mapfile -t container_ids < <(docker ps -aq)
if ((${#container_ids[@]})); then
  docker inspect "${container_ids[@]}" >"$backup_dir/docker-inspect.json"
else
  printf '[]\n' >"$backup_dir/docker-inspect.json"
fi

paths=(
  /home/walker/.config/udoke/walker
  /etc/walker/system
  /etc/walker/calibration
  /etc/walker/map
  /etc/walker/task
  /etc/walker/vision
  /etc/walker/llm
)

existing_paths=()
for path in "${paths[@]}"; do
  [[ -e "$path" ]] && existing_paths+=("$path")
done

if ((${#existing_paths[@]})); then
  tar -czf "$backup_dir/configuration.tar.gz" \
    --warning=no-file-changed \
    "${existing_paths[@]}" \
    2>"$backup_dir/tar-warnings.txt"
else
  printf 'No se encontraron rutas de configuración.\n' >&2
  exit 5
fi

sha256sum "$backup_dir/configuration.tar.gz" >"$backup_dir/SHA256SUMS"
chown -R "$owner:$owner" "$backup_dir"
chmod -R u=rwX,go= "$backup_dir"

printf 'REMOTE_BACKUP=%s\n' "$backup_dir"
du -sh "$backup_dir"
