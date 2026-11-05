#!/usr/bin/env bash
# V4 full-body profile: explicit operator actions, no automatic reload or HOME.
set -Eeuo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
gate_script="$script_dir/cruzr_pico_teleop_pc.sh"
profile_script="$script_dir/install_cruzr_pico_arms_only.sh"
mode="${1:---check}"
export PICO_EFFECTOR=v4

usage() {
  cat <<'HELP'
Uso: bash scripts/teleoperation/probar_pico_v4_full.sh [--check|--prepare-full|--teleoperate|--restore-arms-only|--stop]

--check             Sólo lectura: comprueba hash y modos de la tarea v4 full viva.
--prepare-full      Comprueba gates y STOP, restaura YAML vendor v4; no recarga.
--teleoperate       Permite cuerpo completo y, mediante X, chasis. Exige perfil
                    v4 full cargado, Wi-Fi, sin cables, preflight y supervisión.
--restore-arms-only Restaura overlay v4 sin recargar ni mover.
--stop              Solicita STOP canónico.

ALCANCE: preparación de software; funcionamiento v4 full NO probado físicamente.
Cambiar el YAML no recarga la tarea. La recarga tiene init_reset y puede mover;
requiere revisión separada de HOME y trayectorias. No envía HOME automático.
No pulse clicks de joystick: conmutan la protección de fuerza.
HELP
}

(($# <= 1)) || { usage >&2; exit 2; }
case "$mode" in
  --help|-h) usage ;;
  --check) exec bash "$gate_script" --check-v4-full ;;
  --stop) exec bash "$gate_script" --stop ;;
  --teleoperate) exec bash "$gate_script" --teleoperate-v4-full ;;
  --prepare-full|--restore-arms-only)
    [[ -t 0 && -t 1 ]] || { echo 'ERROR: operación requiere terminal local.' >&2; exit 2; }
    if [[ "$mode" == --prepare-full ]]; then
      echo 'Se restaurará el YAML vendor v4, con cintura, elevador y posibilidad de chasis.'
      echo 'No se recargará el modo ni se enviará movimiento.'
      echo 'Escriba exactamente: PREPARAR V4 FULL SIN RECARGAR NI MOVER'
      read -r confirmation
      [[ "$confirmation" == 'PREPARAR V4 FULL SIN RECARGAR NI MOVER' ]] || { echo 'ERROR: confirmación incorrecta.' >&2; exit 1; }
      bash "$gate_script" --check-v4-control-available
      bash "$gate_script" --check-motion-ready
      bash "$gate_script" --check-v4-control-available
      bash "$profile_script" --rollback
      echo 'V4_FULL_CONFIG_RESTORED=1; MOVEMENT_SENT=0; RELOAD_REQUIRED=1'
      echo 'No se ha cargado el perfil. La recarga requiere revisión y autorización física separadas.'
    else
      echo 'Se restaurará el YAML v4 arms-only, sin recargar el modo ni mover.'
      echo 'Escriba exactamente: RESTAURAR V4 ARMS ONLY SIN RECARGAR NI MOVER'
      read -r confirmation
      [[ "$confirmation" == 'RESTAURAR V4 ARMS ONLY SIN RECARGAR NI MOVER' ]] || { echo 'ERROR: confirmación incorrecta.' >&2; exit 1; }
      bash "$gate_script" --check-v4-control-available
      bash "$gate_script" --check-reload-ready
      bash "$gate_script" --check-v4-control-available
      bash "$profile_script" --install
      echo 'V4_ARMS_ONLY_CONFIG_RESTORED=1; MOVEMENT_SENT=0; RELOAD_REQUIRED=1'
    fi
    ;;
  *) usage >&2; exit 2 ;;
esac
