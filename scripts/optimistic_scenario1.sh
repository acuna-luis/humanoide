#!/usr/bin/env bash
# No prompts. Reuse continuously monitored health instead of reacquiring it
# between stages; preserve faults, stationary transitions and measured HOME.
# --cycle repeats in one session. Ctrl+C finishes the current stage and pauses;
# the printed --resume command continues at the following stage.
# A confirmed HOME MoveToGoalFailed allows one retry after fresh health/rest;
# its allowance is persisted before dispatch and retained when resuming.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
exec python3 -B -c 'import sys; sys.path.insert(0, sys.argv.pop(1)); from scenario1_cli import entrypoint; raise SystemExit(entrypoint(policy="assume", execution_profile="optimistic_v1"))' "$SCRIPT_DIR/box_handling" "$@"
