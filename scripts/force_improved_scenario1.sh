#!/usr/bin/env bash
# Scenario 1 with explicit execution, checkpoints and supervised transitions.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
exec python3 -B "$SCRIPT_DIR/box_handling/scenario1_cli.py" "$@"
