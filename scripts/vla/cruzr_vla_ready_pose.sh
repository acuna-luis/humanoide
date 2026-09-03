#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso disponible ahora:
  ./scripts/vla/cruzr_vla_ready_pose.sh --check
  ./scripts/vla/cruzr_vla_ready_pose.sh --dry-plan

Modos reservados, todavía bloqueados:
  --install | --run-ready | --run-recover | --stop

--check y --dry-plan son exclusivamente locales: no conectan al robot, no
instalan, no recargan, no usan ROS y no mueven. Los modos activos permanecen
bloqueados hasta validar físicamente la recuperación y definir un límite de
aceleración aprobado para el canary.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly VENDOR_READY="$REPO_ROOT/cruzrss2_vla_pack-002/codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml"
readonly RECOVERY_XML="$SCRIPT_DIR/runtime/tasks/s2_vla_e6_0_exact_recovery.xml"
readonly RECOVERY_YAML="$SCRIPT_DIR/runtime/meta_move/clamp_s2_vla_e6_0_exact_recovery.yaml"
readonly EXPECTED_VENDOR_READY_SHA256="f4025124491eba995ec824db3e3be91875f781a4b4e98928654bde9a021d8323"

MODE=""
while (($#)); do
  case "$1" in
    --check|--dry-plan|--install|--run-ready|--run-recover|--stop)
      [[ -z "$MODE" ]] || { printf 'ERROR: indique un solo modo\n' >&2; exit 2; }
      MODE="$1"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$MODE" ]] || { printf 'ERROR: falta modo\n' >&2; usage >&2; exit 2; }
for required in "$VENDOR_READY" "$RECOVERY_XML" "$RECOVERY_YAML"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done
actual_ready_sha="$(sha256sum "$VENDOR_READY" | awk '{print $1}')"
[[ "$actual_ready_sha" == "$EXPECTED_VENDOR_READY_SHA256" ]] || {
  printf 'ERROR: cambió el XML ready del proveedor: %s\n' "$actual_ready_sha" >&2
  exit 1
}

if [[ "$MODE" != --check && "$MODE" != --dry-plan ]]; then
  printf 'E6.0_READY_RECOVERY_PHYSICAL_AUTHORIZED=0\n' >&2
  printf 'ERROR: %s reservado; no se conectó, instaló, recargó ni movió el robot.\n' "$MODE" >&2
  exit 3
fi

printf 'E6.0_READY_SOURCE_SHA256=%s\n' "$actual_ready_sha"
printf 'E6.0_RECOVERY_XML_SHA256=%s\n' "$(sha256sum "$RECOVERY_XML" | awk '{print $1}')"
printf 'E6.0_RECOVERY_META_MOVE_SHA256=%s\n' "$(sha256sum "$RECOVERY_YAML" | awk '{print $1}')"
printf 'E6.0_READY_RECOVERY_COMMAND_PATH=local-only,no-robot,no-ros,no-movement\n'
if [[ "$MODE" == --dry-plan ]]; then
  cat <<'EOF'
E6.0_READY_PLAN=measured-home -> vendor staging -> waypoint A -> ready B
E6.0_RECOVERY_PLAN=ready B -> waypoint A -> vendor staging -> numeric home
E6.0_ACTIVE_MODES=blocked-pending-supervised-physical-validation
EOF
fi
printf 'E6.0_READY_RECOVERY_PHYSICAL_AUTHORIZED=0\n'
