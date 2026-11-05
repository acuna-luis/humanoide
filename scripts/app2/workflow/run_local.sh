#!/usr/bin/env bash
# Run on the existing GPU server. No robot/PLC addresses or control interfaces.
set -euo pipefail
umask 077
APP2_WORKFLOW_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP2_WORKFLOW_IMAGE=app2-workflow:1.0-rfdetr1.11.2
APP2_PARENT_IMAGE=app2-rfdetr:1.11.2-torch2.10.0-cu128
APP2_PARENT_ID=sha256:af168d95cd04b99fc107652ec11834d69f5dfdf75f98e5bf568cf758eb928ba0
APP2_COMPOSE=(docker compose --env-file /dev/null --project-name app2-workflow --project-directory "$APP2_WORKFLOW_DIR" -f "$APP2_WORKFLOW_DIR/compose.yaml")

check_volumes() {
  docker volume inspect app2_datasets app2_training_cache app2_checkpoints >/dev/null
  test "$(docker image inspect "$APP2_PARENT_IMAGE" --format '{{.Id}}')" = "$APP2_PARENT_ID" || {
    echo 'Parent image differs from the tested baseline; inspect before building.' >&2; exit 1;
  }
}

case "${1:---help}" in
  --help)
    cat <<'EOF'
Run on the app2 GPU server:
  bash run_local.sh --check                 Read-only installation inventory
  bash run_local.sh --install               Build isolated extension; keep parent/services
  bash run_local.sh --test                  CPU tests and real QR/no-read checks
  bash run_local.sh --verify                CVAT synthetic roundtrip -> COCO -> train/save/reload -> demo
  bash run_local.sh --prepare [arguments]   coco_prepare.py (CPU, writable dataset volume)
  bash run_local.sh --demo [arguments]      demo.py (GPU, datasets read-only)
  bash run_local.sh --checkpoint-smoke ...  One measured synthetic training step (GPU)
EOF
    ;;
  --check)
    check_volumes
    docker image inspect "$APP2_WORKFLOW_IMAGE" --format '{{.Id}}'
    docker ps --filter label=com.docker.compose.project=app2-cvat
    docker ps --filter label=com.docker.compose.project=app2-workflow
    nvidia-smi --query-gpu=index,name,memory.total,memory.used,driver_version --format=csv
    ;;
  --install)
    check_volumes
    docker build --tag "$APP2_WORKFLOW_IMAGE" "$APP2_WORKFLOW_DIR"
    ;;
  --test)
    check_volumes
    "${APP2_COMPOSE[@]}" run --rm --no-deps tools python -m unittest discover -s tests -p 'test_*.py' -v
    "${APP2_COMPOSE[@]}" run --rm --no-deps tools python code_smoke.py --output-dir "/checkpoints/code-smoke/$(date -u +%Y%m%dT%H%M%SZ)-$$"
    ;;
  --prepare|--demo|--checkpoint-smoke)
    APP2_MODE="$1"; shift
    check_volumes
    case "$APP2_MODE" in
      --prepare) "${APP2_COMPOSE[@]}" run --rm --no-deps tools python coco_prepare.py "$@" ;;
      --demo) "${APP2_COMPOSE[@]}" run --rm --no-deps gpu python demo.py "$@" ;;
      --checkpoint-smoke) "${APP2_COMPOSE[@]}" run --rm --no-deps gpu python checkpoint_smoke.py "$@" ;;
    esac
    ;;
  --verify)
    check_volumes
    APP2_RUN="infra-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    APP2_RECEIPT="$HOME/app2/receipts/$APP2_RUN"
    mkdir -p "$APP2_RECEIPT"
    printf '%s\n' "$APP2_RUN" > "$APP2_RECEIPT/run-id.txt"
    # Host stdlib API client reads the existing private credentials. No cloud/robot.
    PYTHONPATH="$HOME/app2/setup/cvat" python3 "$APP2_WORKFLOW_DIR/cvat_demo.py" \
      --output-dir "$APP2_RECEIPT/cvat" --run-id "$APP2_RUN"
    # Stream only the synthetic export into the existing results volume as UID10001.
    tar -C "$APP2_RECEIPT/cvat" -cf - cvat-export.zip split-manifest.json |
      "${APP2_COMPOSE[@]}" run --rm --no-deps -T tools sh -c \
        'umask 077; mkdir "/checkpoints/$1"; tar --no-same-owner --no-same-permissions -xf - -C "/checkpoints/$1"' sh "$APP2_RUN"
    "${APP2_COMPOSE[@]}" run --rm --no-deps tools python coco_prepare.py \
      --cvat-zip "/checkpoints/$APP2_RUN/cvat-export.zip" \
      --split-manifest "/checkpoints/$APP2_RUN/split-manifest.json" \
      --output "/datasets/$APP2_RUN"
    "${APP2_COMPOSE[@]}" run --rm --no-deps gpu python verify_pipeline.py \
      --dataset "/datasets/$APP2_RUN" --output-dir "/checkpoints/$APP2_RUN/verification"
    printf 'WORKFLOW_RUN=%s\nHOST_RECEIPTS=%s\nVOLUME_RESULTS=/checkpoints/%s\n' "$APP2_RUN" "$APP2_RECEIPT" "$APP2_RUN"
    ;;
  *) echo 'Unknown command; use --help' >&2; exit 2 ;;
esac
