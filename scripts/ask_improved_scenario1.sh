#!/usr/bin/env bash
# Interactive scenario 1, preserving operator confirmations.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
exec python3 -B -c 'import sys; sys.path.insert(0, sys.argv.pop(1)); from scenario1_cli import entrypoint; raise SystemExit(entrypoint(policy="ask"))' "$SCRIPT_DIR/box_handling" "$@"
