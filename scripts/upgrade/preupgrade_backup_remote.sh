#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then
  printf 'Uso: sudo bash %s YYYYMMDD-HHMMSS\n' "$0"
  printf 'Copia privada selectiva en Motion o Vision; no reinicia ni mueve.\n'
  printf 'No incluye imágenes/pesos, workspace VLA completo, PC ni PICO. Revisar cobertura.\n'
  exit 0
fi

stamp="${1:-}"
if [[ ! "$stamp" =~ ^[0-9]{8}-[0-9]{6}$ || $# -ne 1 ]]; then
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

install -d -m 0700 -o "$owner" -g "$owner" "$backup_dir"
printf 'IN_PROGRESS\n' >"$backup_dir/STATUS"
date -u +%FT%TZ >"$backup_dir/captured-at-utc.txt"
: >"$backup_dir/failures.txt"

hostname >"$backup_dir/hostname.txt"
uname -a >"$backup_dir/uname.txt"
cat /etc/walker/system/soft_version >"$backup_dir/soft_version.txt" 2>/dev/null || true
timeout 10 udoke --version >"$backup_dir/udoke-version.txt" 2>&1 || true
uptime >"$backup_dir/uptime.txt"
df -h / /home/walker >"$backup_dir/filesystems.txt"
ip -br address >"$backup_dir/ip-addresses.txt"
ip route >"$backup_dir/ip-routes.txt"
timeout 30 docker ps -a --no-trunc >"$backup_dir/docker-ps-a.txt"
timeout 30 docker image ls --no-trunc >"$backup_dir/docker-images.txt"

timeout 30 docker ps -aq >"$backup_dir/container-ids.txt"
mapfile -t container_ids <"$backup_dir/container-ids.txt"
if ((${#container_ids[@]})); then
  timeout 30 docker inspect "${container_ids[@]}" >"$backup_dir/docker-inspect.json"
else
  printf '[]\n' >"$backup_dir/docker-inspect.json"
fi
timeout 15 systemctl list-unit-files --no-pager >"$backup_dir/systemd-unit-files.txt" 2>&1 || true
timeout 15 systemctl list-units --all --no-pager >"$backup_dir/systemd-units.txt" 2>&1 || true
timeout 15 dpkg-query -W >"$backup_dir/packages.txt" 2>&1 || true

paths=(
  /home/walker/.config/udoke/walker
  /etc/walker/system
  /etc/walker/calibration
  /etc/walker/map
  /etc/walker/task
  /etc/walker/vision
  /etc/walker/llm
  /etc/walker/boot
  /etc/walker/trajectory-overlays
  /etc/systemd/system
  /etc/NetworkManager/system-connections
  /usr/local/sbin/cruzr-v020-boot-guard
  /home/walker/.config/udoke/cruzr-cargo-perception-profile
  /home/walker/.local/share/cruzr-pico-arms-only
  /home/walker/cruzr-owner-backups
  /home/walker/cruzr-vla/backups
  /home/walker/cruzr-vla/manifests
  /home/walker/.AppImages/kiosk-session.sh
)

existing_paths=()
: >"$backup_dir/host-paths.tsv"
for path in "${paths[@]}"; do
  if [[ -e "$path" || -L "$path" ]]; then
    existing_paths+=("${path#/}")
    printf 'INCLUDED\t%s\n' "$path" >>"$backup_dir/host-paths.tsv"
  else
    printf 'ABSENT\t%s\n' "$path" >>"$backup_dir/host-paths.tsv"
  fi
done

if ((${#existing_paths[@]})); then
  tar -czf "$backup_dir/configuration.tar.gz" \
    -C / -- "${existing_paths[@]}" \
    2>"$backup_dir/tar-warnings.txt"
else
  printf 'No se encontraron rutas de configuración.\n' >&2
  exit 5
fi

# Selective writable-layer capture, even for stopped containers. No docker exec.
mkdir -p "$backup_dir/container-configs" "$backup_dir/container-diff"
timeout 30 docker ps -a --format '{{.ID}}\t{{.Names}}' >"$backup_dir/container-list.tsv"
: >"$backup_dir/container-paths.tsv"
known_count=0
while IFS=$'\t' read -r id name; do
  [[ -n "$id" ]] || continue
  if [[ ! "$id" =~ ^[a-f0-9]+$ || ! "$name" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]*$ ]]; then
    printf 'unrecognized_container_identity\n' >>"$backup_dir/failures.txt"
    continue
  fi
  if ! timeout 60 docker diff "$id" >"$backup_dir/container-diff/$name.txt" \
    2>"$backup_dir/container-diff/$name.errors.txt"; then
    printf 'docker_diff_failed\t%s\n' "$name" >>"$backup_dir/failures.txt"
  fi
  paths=()
  case "$name" in
    *motion.manipulation_robot_app*)
      paths=(
        /opt/walker/manipulation_task_manager/share/manipulation_task_manager/config
        /opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config
      ) ;;
    *web.web-expression*)
      paths=(/usr/share/nginx/html/index.html)
      if [[ -f /etc/walker/boot/cruzr-boot-ready.js ]]; then
        paths+=(/usr/share/nginx/html/cruzr-boot-ready.js)
      fi ;;
    *nav.vnav_perception*)
      paths=(/opt/walker/nav_perception2d_config_utars/share/nav_perception2d_config_utars/config) ;;
    *nav.freepnc_task*)
      paths=(/opt/walker/nav_freepnc_config_utars/share/nav_freepnc_config_utars/config) ;;
  esac
  if ((${#paths[@]} == 0)); then
    printf 'INVENTORY_ONLY\t%s\t-\t-\n' "$name" >>"$backup_dir/container-paths.tsv"
    continue
  fi
  known_count=$((known_count + 1))
  slot=0
  for path in "${paths[@]}"; do
    slot=$((slot + 1))
    target="container-configs/$name/$slot"
    mkdir -p "$backup_dir/container-configs/$name"
    if timeout 60 docker cp "$id:$path" "$backup_dir/$target" \
      >"$backup_dir/$target.stdout.txt" 2>"$backup_dir/$target.errors.txt"; then
      printf 'COPIED\t%s\t%s\t%s\n' "$name" "$path" "$target" >>"$backup_dir/container-paths.tsv"
    else
      rc=$?
      printf 'FAILED\t%s\t%s\t%s\n' "$name" "$path" "$target" >>"$backup_dir/container-paths.tsv"
      printf 'container_copy_failed\t%s\t%s\trc=%s\n' "$name" "$path" "$rc" >>"$backup_dir/failures.txt"
    fi
  done
done <"$backup_dir/container-list.tsv"
if ((known_count == 0)); then
  printf 'no_known_configuration_containers_review_names\n' >>"$backup_dir/failures.txt"
fi
# Archive preserves symlinks as data, not as files to follow while checksumming.
tar -czf "$backup_dir/container-configs.tar.gz" -C "$backup_dir" container-configs
cat >"$backup_dir/RESTORE-NOTES.txt" <<'NOTES'
Private selective capture, not a restore script or a complete system image.
Review ABSENT/INVENTORY_ONLY/FAILED entries and every docker diff against the registry.
No images, weights, complete VLA workspace, robot logs, PC or PICO backup.
Stop teaching maps/changing configuration while taking the snapshot.
Do not extract archives onto a live system. Restore reviewed, selected files only.
Boot IDs, display permissions, transient units and enabled states are evidence,
not permission to reactivate them. Keep the retired boot guard disabled.
The directory prefix preupgrade-v0.2.0 is historical; soft_version.txt records reality.
NOTES
if [[ -s "$backup_dir/failures.txt" ]]; then
  printf 'PARTIAL\n' >"$backup_dir/STATUS"
else
  printf 'CAPTURED_REVIEW_COVERAGE\n' >"$backup_dir/STATUS"
fi
(
  cd "$backup_dir"
  find . -type f ! -name SHA256SUMS -print0 | LC_ALL=C sort -z | xargs -0 -r sha256sum >SHA256SUMS
)
chown -R "$owner:$owner" "$backup_dir"
chmod -R u=rwX,go= "$backup_dir"

printf 'REMOTE_BACKUP=%s\n' "$backup_dir"
printf 'BACKUP_STATUS=%s\n' "$(cat "$backup_dir/STATUS")"
du -sh "$backup_dir"
[[ ! -s "$backup_dir/failures.txt" ]] || exit 6
