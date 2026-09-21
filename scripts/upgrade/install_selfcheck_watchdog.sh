#!/usr/bin/env bash
# BOOT-04: install the self-check watchdog on Vision. Enables it for the NEXT
# boot only; does not start it, restart containers or send any command.
set -Eeuo pipefail

readonly HERE="$(dirname -- "$(readlink -f -- "$0")")"
readonly ROOT="$(readlink -f -- "$HERE/../..")"
readonly VISION="${CRUZR_VISION_HOST:-192.168.11.3}"
readonly ASKPASS="$ROOT/scripts/lib/cruzr_ssh_askpass.py"
readonly FILES=(cruzr_selfcheck_watchdog.py cruzr-selfcheck-watchdog.service)
readonly DEPS=(
  "a76e57caed7555de1b476ad4eb717f1a5fe80a135c1b43890ebbdd539d8d136e  /etc/walker/boot/cruzr_boot_voice.py"
  "19f06f68effc7ce6f41ba8294ed01b8d7ea3caf5cc53033d159b4a5f0852011b  /etc/walker/boot/cruzr_cc_start_when_ready.py"
)

if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == 1 ]]; then exec python3 "$ASKPASS"; fi
opts=(-o ConnectTimeout=10 -o PreferredAuthentications=password
      -o PubkeyAuthentication=no -o StrictHostKeyChecking=accept-new)
env_ssh=(env CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$(readlink -f -- "$0")"
         SSH_ASKPASS_REQUIRE=force DISPLAY="${DISPLAY:-:0}" setsid -w)

(cd "$HERE" && python3 -m unittest -q test_cruzr_selfcheck_watchdog.py)
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
stage="/tmp/selfcheck-watchdog-$stamp"
"${env_ssh[@]}" ssh "${opts[@]}" "walker@$VISION" "mkdir -p '$stage'"
for f in "${FILES[@]}"; do
  "${env_ssh[@]}" scp "${opts[@]}" "$HERE/$f" "walker@$VISION:$stage/$f"
done
printf '%s\n' "${DEPS[@]}" | "${env_ssh[@]}" ssh "${opts[@]}" "walker@$VISION" "sha256sum -c -"

# walker has passwordless sudo on Vision; -n fails instead of prompting.
"${env_ssh[@]}" ssh "${opts[@]}" "walker@$VISION" \
  "sudo -n bash -s -- '$stage' '$stamp'" <<'REMOTE'
set -Eeuo pipefail
stage="$1"; stamp="$2"
test "$(hostname)" = vision
backup="/etc/walker/boot/backups/${stamp}_BOOT-04"
install -d -m 755 "$backup"
for f in /etc/walker/boot/cruzr_selfcheck_watchdog.py /etc/systemd/system/cruzr-selfcheck-watchdog.service; do
  [[ -e "$f" ]] && cp -a "$f" "$backup/" || echo "absent $f" >>"$backup/absent.txt"
done
install -o walker -g walker -m 644 "$stage/cruzr_selfcheck_watchdog.py" /etc/walker/boot/
install -o root -g root -m 644 "$stage/cruzr-selfcheck-watchdog.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable cruzr-selfcheck-watchdog.service
sha256sum /etc/walker/boot/cruzr_selfcheck_watchdog.py /etc/systemd/system/cruzr-selfcheck-watchdog.service
echo "BACKUP=$backup"
echo "ENABLED=$(systemctl is-enabled cruzr-selfcheck-watchdog.service); ACTIVE=$(systemctl is-active cruzr-selfcheck-watchdog.service || true)"
echo "STARTED_NOW=0; RESTARTS=0; MOVEMENT_COMMANDS=0"
REMOTE
