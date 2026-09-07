#!/usr/bin/env bash
# Local quarantine, not a robot-side safety controller. Deliberately no unlock
# flag/environment override. Removal requires reviewed replacement gates.
set -eu
printf 'CONTACT_INCIDENT_LOCK=2026-09-04\n' >&2
printf 'MOTION_DENIED_ROUTE=%s\n' "${1:-unspecified}" >&2
printf 'ERROR: montaje/trayectoria/arranque pendientes de recalificación; no se conecta ni se mueve.\n' >&2
printf 'SCOPE=local-caller-only;vendor-boot-and-external-clients-not-intercepted\n' >&2
exit 78
