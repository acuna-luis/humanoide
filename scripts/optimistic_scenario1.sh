#!/usr/bin/env bash
# No prompts. Reuse continuously monitored health instead of reacquiring it
# between stages; preserve faults, stationary transitions and measured HOME.
# This branch defaults to table90, tested in a supervised cycle on 2026-10-01.
# Preserve the tested geometry, native model/HOME pins and live safety checks.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
exec python3 -B -c 'import sys; sys.path.insert(0, sys.argv.pop(1)); from scenario1_cli import entrypoint; raise SystemExit(entrypoint(policy="assume", execution_profile="optimistic_v1"))' "$SCRIPT_DIR/box_handling" "$@"
