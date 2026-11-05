#!/usr/bin/env bash
# Run on the app2 x86_64 training server, never on the robot.
set -euo pipefail
umask 077
readonly HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly APP2_DIR="$HOME/app2"

usage() {
  cat <<'EOF'
Usage: bash install_server.sh --check|--install|--status
--check    Read-only tools, GPU, disk and existing service inventory.
--install  Prepare/start isolated CVAT and validate RF-DETR with synthetic data.
--status   Report CVAT, local training image, and app2 volumes.
No host packages/drivers, robot commands, global cleanup, or volume deletion.
EOF
}

training() {
  docker compose --env-file /dev/null --project-name app2-training \
    --project-directory "$HERE/training" -f "$HERE/training/compose.yaml" "$@"
}

check() {
  [[ "$(uname -m)" == x86_64 ]] || { echo 'Expected x86_64 training server.' >&2; return 1; }
  for tool in docker python3 curl tar nvidia-smi; do command -v "$tool" >/dev/null; done
  docker compose version
  nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv,noheader
  [[ "$(docker info --format '{{.DockerRootDir}}')" == /var/lib/docker ]]
  df -h /home /var/lib/docker
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
}

case "${1:---help}" in
  --check) check ;;
  --status)
    bash "$HERE/cvat/cvat.sh" --status "$APP2_DIR/cvat"
    docker image inspect app2-rfdetr:1.11.2-torch2.10.0-cu128 --format '{{.Id}}'
    docker volume ls --filter name=app2
    ;;
  --install)
    check
    mkdir -p "$APP2_DIR/receipts"
    bash "$HERE/cvat/cvat.sh" --prepare "$APP2_DIR/cvat"
    bash "$HERE/cvat/cvat.sh" --check "$APP2_DIR/cvat"
    if [[ ! -s "$APP2_DIR/cvat/images.lock.yml" ]]; then
      if [[ -s "$HERE/cvat/images.lock.yml" ]]; then
        cp -- "$HERE/cvat/images.lock.yml" "$APP2_DIR/cvat/images.lock.yml"
      else
        bash "$HERE/cvat/cvat.sh" --lock "$APP2_DIR/cvat"
      fi
    fi
    bash "$HERE/cvat/cvat.sh" --pull "$APP2_DIR/cvat"
    bash "$HERE/cvat/cvat.sh" --up "$APP2_DIR/cvat"
    python3 - <<'PY'
import time, urllib.request
for attempt in range(120):
    try:
        with urllib.request.urlopen('http://localhost:18080/api/server/about', timeout=5) as r:
            assert r.status == 200
        break
    except Exception:
        if attempt % 15 == 0:
            print('Waiting for CVAT migrations/API...', flush=True)
        time.sleep(2)
else:
    raise SystemExit('CVAT readiness timeout; preserve evidence and inspect app2 logs')
PY
    container=$(docker ps -q --filter label=com.docker.compose.project=app2-cvat \
      --filter label=com.docker.compose.service=cvat_server)
    [[ -n "$container" && "$container" != *$'\n'* ]]
    # /about alone can be ready before OPA has loaded its authorization bundle.
    docker exec "$container" python -c '
import time, urllib.request
for attempt in range(90):
    try:
        with urllib.request.urlopen("http://opa:8181/health?bundles", timeout=3) as r:
            assert r.status == 200
        print("APP2_CVAT_AUTHORIZATION_READY=1")
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit("OPA bundle readiness timed out; inspect app2 configuration")
'
    python3 "$HERE/create_cvat_admin.py" --container "$container"
    python3 "$HERE/cvat/verify_annotation.py" --output-dir "$APP2_DIR/receipts/cvat-smoke"
    training build training
    training --profile online run --rm --no-deps precache
    bash "$HERE/training/init_cache.sh"
    training run --rm --no-deps training python smoke.py gpu
    training run --rm --no-deps training python smoke.py train
    training run --rm --no-deps training python smoke.py export
    bash "$HERE/cvat/cvat.sh" --status "$APP2_DIR/cvat"
    echo 'APP2_INSTALLATION_VERIFIED=1 (synthetic data only; no app2 model trained)'
    ;;
  --help|-h) usage ;;
  *) usage >&2; exit 2 ;;
esac
