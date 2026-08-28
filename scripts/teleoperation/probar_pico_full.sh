#!/usr/bin/env bash

set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
gate_script="$script_dir/cruzr_pico_teleop_pc.sh"
profile_script="$script_dir/install_cruzr_pico_arms_only.sh"
mode="${1:---check}"

usage() {
  cat <<EOF
Uso:
  $0 --check
  $0 --check-reload-ready
  $0 --check-motion-ready
  $0 --prepare-full
  $0 --teleoperate
  $0 --restore-arms-only
  $0 --stop

Lanzador separado de cuerpo completo para el baseline oficial robot v0.2.0,
controller 4.7.0 y UI 4.1.0. No modifica probar_pico.sh.

--check
    Sólo lectura. Exige el YAML vendor exacto y evidencia de que la tarea viva
    cargó clamp, waist_mode=1 y leg_mode=2.
--prepare-full
    Con PC en STOP y preflight Motion aprobado, restaura el YAML vendor exacto.
    No reinicia ni mueve: después hay que recargar de forma controlada
    TeleopMode (teleop -> auto_task -> teleop) y ejecutar --check.
--teleoperate
    Habilita cabeza, brazos, cintura, elevador/torso y chasis durante 120 s por
    defecto. PICO_OFFICIAL_TELEOP_SECONDS admite 120..300. Exige Wi-Fi Cruzr y
    que Ethernet/cargador estén físicamente retirados. Los clicks de joystick
    permanecen prohibidos porque conmutan la protección de fuerza.
--restore-arms-only
    Reinstala el overlay clamp, waist_mode=0, leg_mode=0. No reinicia ni mueve;
    también requiere recargar TeleopMode antes de volver a probar_pico.sh.
--stop
    Solicita STOP mediante el gate canónico.
EOF
}

if (($# > 1)); then
  usage >&2
  exit 2
fi

for required in "$gate_script" "$profile_script"; do
  [[ -x "$required" ]] || {
    printf 'ERROR: no se puede ejecutar el componente requerido: %s\n' "$required" >&2
    exit 1
  }
done

case "$mode" in
  --check)
    printf '\nVERIFICACIÓN FULL-BODY MOTION — SÓLO LECTURA, SIN START\n\n'
    exec "$gate_script" --check-full-body
    ;;
  --check-reload-ready|--check-motion-ready|--stop)
    exec "$gate_script" "$mode"
    ;;
  --prepare-full)
    [[ -t 0 && -t 1 ]] || {
      printf 'ERROR: prepare-full debe ejecutarse en un terminal local.\n' >&2
      exit 1
    }
    cat <<'EOF'

PREPARAR PERFIL VENDOR DE CUERPO COMPLETO — NO MUEVE POR SÍ SOLO

Se comprobará Motion y después se restaurará exactamente el YAML vendor
clamp, waist_mode=1, leg_mode=2. La tarea viva no cambia hasta recargar
TeleopMode. Esa recarga puede inicializar el cuerpo y debe hacerse después,
como operación física separada, con home verificado y zona despejada.

Escriba exactamente: PREPARAR PERFIL FULL SIN RECARGAR NI MOVER
EOF
    read -r confirmation
    [[ "$confirmation" == "PREPARAR PERFIL FULL SIN RECARGAR NI MOVER" ]] || {
      printf 'ERROR: confirmación incorrecta; no se cambió la configuración.\n' >&2
      exit 1
    }
    "$gate_script" --check-reload-ready
    "$profile_script" --rollback
    cat <<'EOF'

FULL_BODY_CONFIG_RESTORED=1
MOVEMENT_SENT=0
RELOAD_REQUIRED=teleop->auto_task->teleop

No ejecute --teleoperate todavía. Con un nuevo preflight físico, recargue
TeleopMode y después ejecute:
  ./scripts/teleoperation/probar_pico_full.sh --check
EOF
    ;;
  --teleoperate)
    export PICO_OFFICIAL_TELEOP_SECONDS="${PICO_OFFICIAL_TELEOP_SECONDS:-120}"
    exec "$gate_script" --teleoperate-full
    ;;
  --restore-arms-only)
    [[ -t 0 && -t 1 ]] || {
      printf 'ERROR: restore-arms-only debe ejecutarse en un terminal local.\n' >&2
      exit 1
    }
    cat <<'EOF'

RESTAURAR PERFIL ARMS-ONLY — NO MUEVE POR SÍ SOLO

Escriba exactamente: RESTAURAR ARMS ONLY SIN RECARGAR NI MOVER
EOF
    read -r confirmation
    [[ "$confirmation" == "RESTAURAR ARMS ONLY SIN RECARGAR NI MOVER" ]] || {
      printf 'ERROR: confirmación incorrecta; no se cambió la configuración.\n' >&2
      exit 1
    }
    "$gate_script" --check-reload-ready
    "$profile_script" --install
    cat <<'EOF'

ARMS_ONLY_CONFIG_RESTORED=1
MOVEMENT_SENT=0
RELOAD_REQUIRED=teleop->auto_task->teleop
EOF
    ;;
  --help|-h)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
