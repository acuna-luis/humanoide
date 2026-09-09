#!/usr/bin/env bash

set -Eeuo pipefail

# Transferencia del contenedor azul desde la mesa 1 hasta la mesa 2:
# detector workbin -> agarre -> MESA2_PRE -> AprilTag 113 -> depósito -> home.

readonly MAP_WAYPOINT="MESA2_PRE"
readonly CARRY_SCRIPT_NAME="cruzr_blue_workbin_carry_back.sh"
readonly CYCLE_SCRIPT_NAME="cruzr_blue_workbin_cycle.sh"
readonly MAP_SCRIPT_NAME="cruzr_blue_workbin_map_route.sh"
readonly ALIGN_SCRIPT_NAME="cruzr_apriltag_mesa2_align.sh"
readonly RECOVERY_SCRIPT_NAME="cruzr_recover_to_home.sh"
readonly CARGO_PROFILE_SCRIPT_NAME="cruzr_cargo_perception_profile.sh"
readonly MESA2_NAV_TIMEOUT_SECONDS="120"
# En la disposición instrumentada, la inflación comenzaba a 0,974 m de
# MESA2_PRE. Se conserva el destino 1,08 m detrás; no es una garantía geométrica
# para mesas nuevas. La aproximación restante se mide mediante AprilTag.
readonly MESA2_CARGO_BACKOFF_METERS="1.08"

SCRIPT_PATH="$(readlink -f -- "$0")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly SCRIPT_PATH SCRIPT_DIR
readonly CARRY_SCRIPT="$SCRIPT_DIR/$CARRY_SCRIPT_NAME"
readonly CYCLE_SCRIPT="$SCRIPT_DIR/$CYCLE_SCRIPT_NAME"
readonly MAP_SCRIPT="$SCRIPT_DIR/$MAP_SCRIPT_NAME"
readonly ALIGN_SCRIPT="$SCRIPT_DIR/$ALIGN_SCRIPT_NAME"
readonly RECOVERY_SCRIPT="$SCRIPT_DIR/$RECOVERY_SCRIPT_NAME"
readonly CARGO_PROFILE_SCRIPT="$SCRIPT_DIR/$CARGO_PROFILE_SCRIPT_NAME"

MODE="check"
YES=0
FAST=0
FLUID=0
STAGE="inicio"
BOX_HELD=0
BOX_RELEASED=0
CARGO_PROFILE_ACTIVE=0
GRASP_ATTEMPTED=0
DEPOSIT_ATTEMPTED=0
MODE_SELECTED=""
LOG_DIR=""
TRANSFER_STARTED_AT="$SECONDS"
WITHOUT_APRILTAG=0
MESA2_PROFILE="${CRUZR_MESA2_PROFILE:-$SCRIPT_DIR/../config/cruzr_mesa2_drop.json}"
PROFILE_OPTION_SET=0
TEACH_APPROACH_DISTANCE=""
OVERWRITE_MESA2=0
MAP_STAGE_POSE=""
MAP_DROP_POSE=""
MAP_POSITION_TOLERANCE=""
MAP_YAW_TOLERANCE=""
MAP_APPROACH_PLAN=""
readonly DROP_PROFILE_HELPER="$SCRIPT_DIR/lib/cruzr_table_drop_profile.py"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/cruzr_blue_workbin_table_transfer.sh --teach-mesa2 --approach-distance METROS [--mesa2-profile ARCHIVO]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --without-apriltag --check [--mesa2-profile ARCHIVO]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --without-apriltag --run [--fast] [--mesa2-profile ARCHIVO]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --check [--fast]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --stage-held [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --resume-held-from-mesa1 [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --resume-held-navigation [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --resume-held [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --run [--yes] [--fast|--fluid]

Modos:
  --check       Comprueba el mapa YA activo, waypoint, manipulación y servicio
                AprilTag. No carga mapas ni relocaliza. No demuestra visibilidad
                del tag o apoyo de la caja; se miden en sus etapas respectivas.
  --stage-held  Coge la caja en mesa 1, se retira y navega a 1,08 m detrás de
                MESA2_PRE. Allí comprueba que el tag 113 continúa visible. Termina sujetando
                la caja; no alinea, deposita ni ejecuta home.
  --resume-held-from-mesa1
                Reanuda después de que el agarre en mesa 1 haya terminado:
                verifica que la caja sigue sujeta, retrocede, navega a
                MESA2_PRE, alinea, deposita y termina en home. No vuelve a
                detectar ni a agarrar la caja.
  --resume-held-navigation
                Reanuda cuando la retirada de mesa 1 ya se realizó y una
                navegación anterior quedó bloqueada por la propia caja. No
                retrocede otra vez: verifica agarre, conserva LiDAR pero
                excluye temporalmente las nubes RGB-D/estéreo del costmap,
                navega a MESA2_PRE, deposita y hace home.
  --resume-held-approach Sólo sin tags: reanuda una aproximación interrumpida
                dentro del corredor enseñado, midiendo la distancia restante.
  --resume-held Desde MESA2_PRE y con la caja ya sujeta, alinea con el tag 113,
                deposita en mesa 2, retrocede y termina en home.
  --run         Recoge, traslada, aproxima, alinea, deposita y vuelve a HOME.

Opciones sin AprilTags:
  --without-apriltag
                Usa pose de depósito enseñada en el mapa, sin llamar al detector
                AprilTag. Compatible con --check, --run y todos los modos de
                reanudación. --stage-held se detiene en la premesa enseñada.
  --teach-mesa2 --approach-distance METROS
                Con el robot ya colocado en la pose de depósito de mesa 2, lee
                la pose y crea un perfil local; no mueve. La distancia elegida
                sitúa la premesa detrás, entre 0,10 y 1,20 m. Hay que comprobar
                ese recorrido. No sobrescribe salvo con --overwrite-mesa2.
  --overwrite-mesa2
                Sólo con --teach-mesa2: sustituye la referencia tras una captura
                válida y conserva una copia .bak.* de la anterior. No mueve.
  --mesa2-profile ARCHIVO
                Por defecto config/cruzr_mesa2_drop.json o CRUZR_MESA2_PROFILE.
                Contiene mapa, huella, posición X/Y (m), yaw (rad) y distancia.
                Sin perfil registrado se bloquea antes de conectar.
                Esta variante admite --fast; --fluid sigue reservado a tags.

Opciones:
  CRUZR_MAP_NAME selecciona el mapa existente (por defecto test_route_01).
                Ejemplo:
                CRUZR_MAP_NAME=mesas_20260909 ./scripts/cruzr_blue_workbin_table_transfer.sh --check
  CRUZR_MAP_TYPE=uslam exige la preparación previa de localización LiDAR;
                fusion exige la preparación visual y auto no exige un tipo.
                Este script no carga ni cambia el tipo del mapa.
  --fast        Reduce auditorías repetidas; conserva comprobaciones frescas
                de salud y el resultado de cada acción.
  --fluid       Perfil opcional para el ciclo completo: implica --fast,
                acepta el depósito dentro de 50 mm, reduce muestras y evita
                auditorías duplicadas. Conserva paros, cargador, agarre,
                odometría y el resultado de todas las acciones físicas.
                Cada invocación hace un preflight fresco, también con --fluid.

Durante toda navegación con la caja se mantienen LiDAR, mapa, localización,
odometría, bumpers y paros. Las tres nubes RGB-D/estéreo se excluyen
temporalmente del costmap para evitar que la propia carga bloquee el plan. La
configuración original se restaura antes del depósito y también ante error o
Ctrl+C. Use este perfil únicamente con una ruta controlada y despejada.

La primera puesta en servicio debe usar --stage-held. Ejecute --resume-held
solo después de comprobar visualmente que la caja sigue estable y que la mesa
2 está libre. Si falla cualquier etapa anterior al depósito, el script no abre
los cogedores. Un agarre o depósito interrumpido puede dejar la caja en un
estado incierto: no repita automáticamente ni el ciclo ni HOME.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

# Sólo temporiza ejecutables o with_fast (un único ejecutable), nunca funciones
# de varias etapas: una condición Bash puede desactivar errexit dentro de ellas.
timed() {
  local label="$1" started="$SECONDS" status=0
  shift
  if "$@" 2>&1 | tee "$LOG_DIR/${label}.log"; then
    status=0
  else
    status=$?
  fi
  info "TIMING_${label}=$((SECONDS - started))s STATUS=$status"
  return "$status"
}

while (($#)); do
  case "$1" in
    --check|--stage-held|--resume-held-from-mesa1|--resume-held-navigation|--resume-held|--resume-held-approach|--run|--teach-mesa2)
      [[ -z "$MODE_SELECTED" || "$MODE_SELECTED" == "$1" ]] ||
        die "Seleccione un solo modo; no combine $MODE_SELECTED con $1."
      MODE_SELECTED="$1"
      MODE="${1#--}"
      ;;
    --without-apriltag)
      WITHOUT_APRILTAG=1
      ;;
    --overwrite-mesa2)
      OVERWRITE_MESA2=1
      ;;
    --mesa2-profile)
      (($# >= 2)) || die "--mesa2-profile necesita un archivo"
      MESA2_PROFILE="$2"
      PROFILE_OPTION_SET=1
      shift
      ;;
    --approach-distance)
      (($# >= 2)) || die "--approach-distance necesita metros"
      TEACH_APPROACH_DISTANCE="$2"
      shift
      ;;
    --yes)
      YES=1
      ;;
    --fast)
      FAST=1
      ;;
    --fluid)
      FLUID=1
      FAST=1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "Opción desconocida: $1"
      ;;
  esac
  shift
done

[[ "$MODE" != resume-held-approach || "$WITHOUT_APRILTAG" == 1 ]] || die "--resume-held-approach necesita --without-apriltag."
[[ "$MODE" != teach-mesa2 ]] || WITHOUT_APRILTAG=1
[[ "$MODE" == teach-mesa2 || "$OVERWRITE_MESA2" == 0 ]] ||
  die "--overwrite-mesa2 sólo se usa con --teach-mesa2."
if ((WITHOUT_APRILTAG == 1)); then
  ((FLUID == 0)) || die "La variante sin tags admite --fast, no --fluid."
  export CRUZR_MAP_TYPE="${CRUZR_MAP_TYPE:-uslam}"
else
  ((PROFILE_OPTION_SET == 0)) || die "--mesa2-profile necesita --without-apriltag."
fi
[[ "$MODE" == teach-mesa2 || -z "$TEACH_APPROACH_DISTANCE" ]] ||
  die "--approach-distance sólo se usa al enseñar mesa 2."
export CRUZR_FLUID_MODE="$FLUID"
# Estas marcas heredadas no demuestran el estado de esta ejecución.
unset CRUZR_TRANSFER_PREFLIGHT_DONE CRUZR_DRIVE_PREFLIGHT_DONE CRUZR_AFTER_DEPOSIT CRUZR_EXPECTED_MAP_FINGERPRINT
export CRUZR_ROUTE_CONTEXT="table-transfer"

require_scripts() {
  local path command_name
  for command_name in readlink flock mktemp tee grep python3 cp; do
    command -v "$command_name" >/dev/null 2>&1 || die "Falta '$command_name'."
  done
  local -a dependencies=("$CARRY_SCRIPT" "$CYCLE_SCRIPT" "$MAP_SCRIPT" "$RECOVERY_SCRIPT" "$CARGO_PROFILE_SCRIPT")
  if ((WITHOUT_APRILTAG == 0)); then
    dependencies+=("$ALIGN_SCRIPT")
  else
    [[ -r "$DROP_PROFILE_HELPER" ]] || die "Falta $DROP_PROFILE_HELPER"
  fi
  for path in "${dependencies[@]}"; do
    [[ -x "$path" ]] || die "No existe o no es ejecutable: $path"
  done
}

with_fast() {
  local script="$1"
  shift
  local -a args=("$@")
  if ((FAST == 1)) && [[ "$1" != --check ]]; then
    args+=(--fast)
  fi
  "$script" "${args[@]}" || return $?
}

confirm_once() {
  ((YES == 1)) && return 0
  if ((WITHOUT_APRILTAG == 1)); then
    local answer
    info "TRANSFERENCIA SIN TAGS — modo $MODE"
    info "Premesa: $MAP_STAGE_POSE; depósito: $MAP_DROP_POSE (X/Y metros, yaw radianes)."
    info "Límites de pose: $MAP_POSITION_TOLERANCE m y $MAP_YAW_TOLERANCE rad."
    info "Confirma mesa 2 fija y libre, misma postura de caja/abrazaderas que al enseñar, apoyo completo con margen para esos errores, recorrido libre y caja vacía. Sin cargador/Ethernet ni otros mandos; persona junto al paro."
    case "$MODE" in
      stage-held) info "Recoge, retrocede de mesa 1 y navega a premesa; termina con caja sujeta, sin avanzar hacia el depósito." ;;
      resume-held-approach) info "Reanuda dentro del corredor enseñado; mide el avance pendiente, deposita y vuelve a HOME." ;;
      resume-held) info "Debe estar ya en la premesa enseñada con caja sujeta. Avanza los tramos guardados, deposita y vuelve a HOME." ;;
      resume-held-navigation) info "Debe estar separado de mesa 1 con caja sujeta. No repite retirada; navega, aproxima, deposita y vuelve a HOME." ;;
      resume-held-from-mesa1) info "Debe estar en mesa 1 con caja ya sujeta. Retrocede, navega, aproxima, deposita y vuelve a HOME." ;;
      run) info "Recoge en mesa 1, retrocede, navega, aproxima, deposita y vuelve a HOME." ;;
    esac
    info "Escribe TRANSFERIR SIN TAGS para continuar:"
    read -r answer
    [[ "$answer" == 'TRANSFERIR SIN TAGS' ]] || die "Transferencia cancelada."
    return 0
  fi
  case "$MODE" in
    stage-held)
      cat <<'EOF'

CONFIRMACIÓN — TRASLADO HASTA MESA2_PRE
El robot cogerá la caja, retrocederá 0,50 m y navegará hasta MESA2_PRE.
Terminará a 1,08 m detrás de ese punto, sujetando la caja. Confirma que Ethernet y cargador están
desconectados, toda la ruta admite la anchura de la caja y el paro está listo.

Escribe LLEVAR CAJA A MESA2 para continuar:
EOF
      local answer
      read -r answer
      [[ "$answer" == "LLEVAR CAJA A MESA2" ]] || die "Traslado cancelado."
      ;;
    resume-held)
      cat <<'EOF'

CONFIRMACIÓN — ALINEAR Y DEPOSITAR EN MESA 2
El robot debe estar en la zona de espera anterior a MESA2_PRE con la caja sujeta. Corregirá su pose con
el tag 113, bajará hasta contacto, abrirá, retrocederá y terminará en home.
Confirma que la mesa está libre y estable, el tag visible, la envolvente
despejada y otra persona mantiene preparado el paro.

Escribe DEPOSITAR EN MESA2 para continuar:
EOF
      local answer
      read -r answer
      [[ "$answer" == "DEPOSITAR EN MESA2" ]] || die "Depósito cancelado."
      ;;
    resume-held-from-mesa1)
      cat <<'EOF'

CONFIRMACIÓN — REANUDAR CON LA CAJA SUJETA EN MESA 1
El robot verificará el agarre existente, retrocederá 0,50 m, navegará hasta
MESA2_PRE, se alineará con el tag 113, depositará y terminará en home. No
volverá a detectar ni a agarrar la caja. Confirma que la caja sigue estable,
Ethernet y cargador están desconectados, la ruta está libre y el paro listo.

Escribe REANUDAR DESDE MESA1 para continuar:
EOF
      local answer
      read -r answer
      [[ "$answer" == "REANUDAR DESDE MESA1" ]] || die "Reanudación cancelada."
      ;;
    resume-held-navigation)
      cat <<'EOF'

CONFIRMACIÓN — REANUDAR DIRECTAMENTE LA NAVEGACIÓN CON CARGA
La caja ya debe estar sujeta y el robot separado de mesa 1. No retrocederá
otra vez. Conservará LiDAR, mapa, bumpers y paros, pero excluirá temporalmente
las nubes RGB-D/estéreo del costmap. Navegará a MESA2_PRE, depositará y hará
home. Confirma que toda la ruta está libre y el paro preparado.

Escribe CONTINUAR NAVEGACION CON CAJA para continuar:
EOF
      local answer
      read -r answer
      [[ "$answer" == "CONTINUAR NAVEGACION CON CAJA" ]] || die "Reanudación cancelada."
      ;;
    run)
      cat <<'EOF'

CONFIRMACIÓN — TRANSFERENCIA COMPLETA ENTRE MESAS
El robot cogerá la caja en mesa 1, navegará a MESA2_PRE, se alineará con el
tag 113, depositará en mesa 2, retrocederá y terminará en home. Confirma que
ambas mesas y toda la ruta están preparadas, Ethernet y cargador desconectados,
la caja está vacía y otra persona mantiene el paro durante todo el ciclo.

Escribe TRANSFERIR CAJA A MESA2 para continuar:
EOF
      local answer
      read -r answer
      [[ "$answer" == "TRANSFERIR CAJA A MESA2" ]] || die "Transferencia cancelada."
      ;;
  esac
}

on_exit() {
  local status="$?" restore_status=0
  trap - EXIT INT TERM HUP
  set +e
  if ((CARGO_PROFILE_ACTIVE == 1)); then
    "$CARGO_PROFILE_SCRIPT" --restore >&2
    restore_status=$?
    if ((restore_status == 0)); then
      CARGO_PROFILE_ACTIVE=0
    else
      printf 'AVISO: restauración de percepción pendiente. Use cruzr_cargo_perception_profile.sh --restore antes de reanudar.\n' >&2
      ((status != 0)) || status="$restore_status"
    fi
  fi
  if ((status != 0)); then
    printf '\nTRANSFERENCIA_INTERRUMPIDA etapa=%s estado=%s\n' "$STAGE" "$status" >&2
    printf 'TIMING_TOTAL_INTERRUPTED=%ss\n' "$((SECONDS - TRANSFER_STARTED_AT))" >&2
    if ((DEPOSIT_ATTEMPTED == 1 && BOX_RELEASED == 0)); then
      info "Depósito interrumpido: la caja puede estar sujeta, parcialmente apoyada o liberada. No repita depósito ni HOME; compruebe el resultado físico y Motion." >&2
    elif ((BOX_RELEASED == 1)); then
      info "Liberación confirmada por Motion. Si empezó la recuperación, puede haber retrocedido ya; no repita el ciclo ni el retroceso. Revise su registro y use primero recuperador --check." >&2
    elif ((BOX_HELD == 1 || GRASP_ATTEMPTED == 1)); then
      info "La caja puede estar sujeta o parcialmente apoyada, incluso si el agarre falló. No reinicie el ciclo ni ejecute HOME. Compruebe apoyo, contacto y registro antes de elegir recuperación." >&2
    fi
  fi
  [[ -z "$LOG_DIR" ]] || printf 'TRANSFER_LOG_DIR=%s\n' "$LOG_DIR" >&2
  exit "$status"
}

profile_args() {
  python3 "$DROP_PROFILE_HELPER" "$@" \
    --map-name "${CRUZR_MAP_NAME:-test_route_01}" --map-type "${CRUZR_MAP_TYPE:-uslam}"
}

load_map_drop_profile() {
  local fields snapshot="$LOG_DIR/mesa2-profile.json"
  cp -- "$MESA2_PROFILE" "$snapshot" || die "Falta referencia de mesa 2. Use --teach-mesa2 cuando esté colocado en la pose de depósito."
  fields="$(profile_args fields "$snapshot")" || die "Perfil de mesa 2 inválido; no se conectó al robot."
  local -a values=()
  mapfile -t values <<<"$fields"
  ((${#values[@]} == 5)) || die "Perfil incompleto."
  MAP_STAGE_POSE="${values[0]}"
  MAP_DROP_POSE="${values[1]}"
  MAP_POSITION_TOLERANCE="${values[2]}"
  MAP_YAW_TOLERANCE="${values[3]}"
  export CRUZR_EXPECTED_MAP_FINGERPRINT="${values[4]}"
  MAP_APPROACH_PLAN="$(profile_args plan "$snapshot")" || die "No se calculó una aproximación válida."
  info "MESA2_MODE=map-only; premesa=$MAP_STAGE_POSE; depósito=$MAP_DROP_POSE"
  info "MESA2_APPROACH_PLAN=$MAP_APPROACH_PLAN"
}

teach_mesa2() {
  # Comprobar argumentos y destino local antes de cualquier lectura remota.
  [[ ! -L "$MESA2_PROFILE" ]] || die "El perfil es un enlace simbólico; indique un archivo normal."
  [[ ! -e "$MESA2_PROFILE" || "$OVERWRITE_MESA2" == 1 ]] || die "El perfil ya existe; use --overwrite-mesa2 para sustituirlo con copia, o elija otro --mesa2-profile."
  [[ ! -e "$MESA2_PROFILE" || -f "$MESA2_PROFILE" ]] || die "El perfil no es un archivo normal."
  local -a record_options=()
  ((OVERWRITE_MESA2 == 0)) || record_options+=(--overwrite)
  python3 - "$TEACH_APPROACH_DISTANCE" "${CRUZR_MAP_TYPE:-uslam}" <<'PY_TEACH'
import math, sys
try:
    distance = float(sys.argv[1])
except ValueError:
    raise SystemExit("Indique --approach-distance: distancia de premesa a depósito, en metros")
if not math.isfinite(distance) or not .10 <= distance <= 1.20:
    raise SystemExit("La distancia debe estar entre 0,10 y 1,20 m")
if sys.argv[2] not in ("uslam", "fusion"):
    raise SystemExit("Fije CRUZR_MAP_TYPE=uslam o fusion antes de enseñar")
PY_TEACH
  STAGE="registro-referencia-mesa2"
  info "Registrando la pose actual de base como depósito de mesa 2. Debe haber sido colocada allí por el operador; este comando no la posiciona."
  timed TEACH_MESA2 "$MAP_SCRIPT" --measure-map-reference
  profile_args record "$MESA2_PROFILE" --report "$LOG_DIR/TEACH_MESA2.log" \
    --approach-distance "$TEACH_APPROACH_DISTANCE" "${record_options[@]}"
}

check_taught_pose() {
  local label="$1" target="$2"
  timed "$label" "$MAP_SCRIPT" --check-map-pose "$target" \
    --position-tolerance "$MAP_POSITION_TOLERANCE" --yaw-tolerance "$MAP_YAW_TOLERANCE"
}

read_pose_marker() {
  python3 - "$1" "$2" <<'PY_POSE_MARKER'
import pathlib, re, sys
values = re.findall(r'^'+re.escape(sys.argv[2])+r'=(.*)$', pathlib.Path(sys.argv[1]).read_text(), re.M)
if len(values) != 1:
    raise SystemExit('Falta una lectura de pose única: '+sys.argv[2])
print(values[0])
PY_POSE_MARKER
}

approach_taught_mesa2() {
  local distance target current index=0
  local -a current_values target_values
  STAGE="verificacion-premesa-sin-tags"
  if [[ "$MODE" == resume-held-approach ]]; then
    current="$(read_pose_marker "$LOG_DIR/PREFLIGHT_MAP.log" MAP_POSE_REFERENCE)"
    check_taught_pose MAP_STAGING_CHECK "$current"
  else
    check_taught_pose MAP_STAGING_CHECK "$MAP_STAGE_POSE"
  fi
  current="$(read_pose_marker "$LOG_DIR/MAP_STAGING_CHECK.log" TAUGHT_MAP_POSE_VERIFIED)"
  if [[ "$MODE" == resume-held-approach ]]; then
    read -r -a current_values <<<"$current"
    MAP_APPROACH_PLAN="$(profile_args remaining-plan "$LOG_DIR/mesa2-profile.json" --current-pose "${current_values[@]}")"
    info "MESA2_REMAINING_PLAN=$MAP_APPROACH_PLAN"
  fi
  while IFS='|' read -r distance target; do
    ((index += 1))
    read -r -a current_values <<<"$current"
    read -r -a target_values <<<"$target"
    distance="$(profile_args forward-distance "$LOG_DIR/mesa2-profile.json" --current-pose "${current_values[@]}" --target-pose "${target_values[@]}")"
    info "MESA2_NEXT_ADVANCE_M=$distance; destino=$target"
    STAGE="aproximacion-sin-tags-$index"
    timed "MAP_APPROACH_$index" with_fast "$CARRY_SCRIPT" --advance-held-distance "$distance" --yes
    STAGE="verificacion-aproximacion-sin-tags-$index"
    check_taught_pose "MAP_APPROACH_CHECK_$index" "$target"
    current="$(read_pose_marker "$LOG_DIR/MAP_APPROACH_CHECK_$index.log" TAUGHT_MAP_POSE_VERIFIED)"
  done <<<"$MAP_APPROACH_PLAN"
  info "MESA2_TAUGHT_DROP_READY=$MAP_DROP_POSE"
}

preflight() {
  STAGE="preflight-mapa"
  # El contexto table-transfer impide que map_route cargue/relocalice un mapa.
  if ((WITHOUT_APRILTAG == 1)); then
    timed PREFLIGHT_MAP "$MAP_SCRIPT" --measure-map-reference
  else
    timed PREFLIGHT_MAP with_fast "$MAP_SCRIPT" --check
    STAGE="preflight-apriltag"
    timed PREFLIGHT_APRILTAG "$ALIGN_SCRIPT" --check
  fi
  STAGE="preflight-perfil-carga"
  timed PREFLIGHT_CARGO "$CARGO_PROFILE_SCRIPT" --check
  grep -qx 'CARGO_PERCEPTION_PROFILE=disabled' "$LOG_DIR/PREFLIGHT_CARGO.log" ||
    die "Hay una transacción de percepción anterior. Ejecute cruzr_cargo_perception_profile.sh --restore y repita --check."
  if ((WITHOUT_APRILTAG == 1)); then
    info "TABLE_TRANSFER_CHECK_OK: referencia enseñada y mapa coinciden; no se usaron AprilTags. Geometría física pendiente de confirmación del operador."
  else
    info "TABLE_TRANSFER_CHECK_OK: mapa activo, $MAP_WAYPOINT, manipulación y servicio AprilTag disponibles; visibilidad/apoyo pendientes de su etapa."
  fi
}

enable_cargo_profile() {
  ((CARGO_PROFILE_ACTIVE == 0)) || return 0
  # Se marca antes de iniciar la transacción para que el trap de EXIT pueda
  # recuperar también una instalación interrumpida por Ctrl+C.
  CARGO_PROFILE_ACTIVE=1
  timed CARGO_ENABLE with_fast "$CARGO_PROFILE_SCRIPT" --enable
}

restore_cargo_profile() {
  ((CARGO_PROFILE_ACTIVE == 1)) || return 0
  timed CARGO_RESTORE "$CARGO_PROFILE_SCRIPT" --restore || return $?
  CARGO_PROFILE_ACTIVE=0
}

navigate_mesa2() {
  local status=0 restore_status=0
  info "CARGO_NAVIGATION_PROFILE: tránsito con LiDAR; cámaras fuera del costmap temporalmente."
  enable_cargo_profile
  # Alcance local: ni el timeout ni el resultado se filtran a otra etapa.
  local -a nav_args=(--navigate-waypoint-backoff "$MAP_WAYPOINT" "$MESA2_CARGO_BACKOFF_METERS" --yes)
  if ((WITHOUT_APRILTAG == 1)); then
    nav_args=(--navigate-map-pose "$MAP_STAGE_POSE" --position-tolerance "$MAP_POSITION_TOLERANCE" --yaw-tolerance "$MAP_YAW_TOLERANCE" --yes)
  fi
  if CRUZR_NAV_TIMEOUT_SECONDS="$MESA2_NAV_TIMEOUT_SECONDS" timed NAVIGATE_MESA2 \
      with_fast "$MAP_SCRIPT" "${nav_args[@]}"; then
    status=0
  else
    status=$?
  fi
  restore_cargo_profile || restore_status=$?
  ((restore_status == 0)) || die "No se restauró la percepción original (estado $restore_status); no se aproximará ni depositará."
  if ((status != 0)); then
    if grep -Eq 'START_ONOBSTACLE|7218011|起点有静态障碍物' "$LOG_DIR/NAVIGATE_MESA2.log"; then
      info "Inicio bloqueado: no se añade otro retroceso automático ni se cambia el destino. Revise posición y recorrido antes de reanudar." >&2
    elif grep -q 'NAV_FAILURE_CLASS=LOCALIZATION_LOST' "$LOG_DIR/NAVIGATE_MESA2.log"; then
      info "Localización perdida: se necesita recuperar la pose antes de reanudar." >&2
    elif grep -q 'NAV_FAILURE_CLASS=DYNAMIC_OBSTACLE' "$LOG_DIR/NAVIGATE_MESA2.log"; then
      info "La navegación sigue bloqueada con LiDAR activo. Revise el obstáculo; no se desactiva esa protección." >&2
    fi
    return "$status"
  fi
  if ((WITHOUT_APRILTAG == 1)); then
    info "MESA2_CARGO_STAGING_OK: premesa enseñada $MAP_STAGE_POSE."
    return 0
  fi
  info "MESA2_CARGO_STAGING_OK: destino a ${MESA2_CARGO_BACKOFF_METERS} m detrás de $MAP_WAYPOINT; no demuestra el margen físico de una disposición nueva."
}

stage_box_at_mesa2() {
  STAGE="agarre-mesa1"
  info "[1/5] Centrando, sujetando y elevando la caja en mesa 1..."
  GRASP_ATTEMPTED=1
  timed GRASP_MESA1 with_fast "$CARRY_SCRIPT" --grasp-only --yes
  BOX_HELD=1

  STAGE="retirada-mesa1"
  info "[2/5] Separándose 0,50 m de mesa 1..."
  timed RETREAT_MESA1 with_fast "$CARRY_SCRIPT" --retreat-only --yes

  STAGE="navegacion-mesa2-pre"
  info "[3/5] Navegando con la caja hasta $MAP_WAYPOINT..."
  navigate_mesa2

  if [[ "$MODE" == "stage-held" ]]; then
    STAGE="verificacion-agarre-mesa2"
    timed VERIFY_STAGE_GRASP with_fast "$CYCLE_SCRIPT" --verify-grasp
    if ((WITHOUT_APRILTAG == 1)); then
      STAGE="verificacion-premesa-sin-tags"
      check_taught_pose MAP_STAGE_HELD_CHECK "$MAP_STAGE_POSE"
      info "MESA2_STAGE_HELD_OK: premesa enseñada y agarre comprobados; sin aproximación, depósito ni HOME. Para continuar, conserve --without-apriltag y el mismo perfil."
      return 0
    fi
    STAGE="visibilidad-tag-con-caja"
    timed CHECK_STAGE_TAG "$ALIGN_SCRIPT" --check-visible
    info "MESA2_STAGE_HELD_OK: caja sujeta y tag medido, a ${MESA2_CARGO_BACKOFF_METERS} m detrás de $MAP_WAYPOINT; sin aproximación, alineación, depósito ni HOME. Use --resume-held tras comprobar caja estable y mesa libre."
  fi
}

resume_held_from_mesa1() {
  BOX_HELD=1
  STAGE="verificacion-agarre-mesa1"
  info "[REANUDACIÓN 1/3] Confirmando el agarre ya existente en mesa 1..."
  timed VERIFY_RESUME_GRASP with_fast "$CYCLE_SCRIPT" --verify-grasp

  STAGE="retirada-mesa1"
  info "[REANUDACIÓN 2/3] Separándose 0,50 m de mesa 1..."
  timed RETREAT_MESA1 with_fast "$CARRY_SCRIPT" --retreat-only --yes

  STAGE="navegacion-mesa2-pre"
  info "[REANUDACIÓN 3/3] Navegando con la caja hasta $MAP_WAYPOINT..."
  navigate_mesa2
}

resume_held_navigation() {
  BOX_HELD=1
  STAGE="verificacion-agarre-reanudacion-navegacion"
  info "[REANUDACIÓN DIRECTA 1/2] Confirmando la caja ya sujeta..."
  timed VERIFY_RESUME_GRASP with_fast "$CYCLE_SCRIPT" --verify-grasp

  STAGE="navegacion-mesa2-pre"
  info "[REANUDACIÓN DIRECTA 2/2] Navegando sin repetir el retroceso a $MAP_WAYPOINT..."
  navigate_mesa2
}

align_deposit_and_home() {
  BOX_HELD=1
  if ((WITHOUT_APRILTAG == 1)); then
    approach_taught_mesa2
  else
    STAGE="aproximacion-gruesa-mesa2"
    info "[DEPÓSITO 0/3] Acercándose al rango de alineación fina; el alineador comprueba agarre y tag antes de avanzar."
    timed COARSE_APPROACH_MESA2 with_fast "$ALIGN_SCRIPT" --coarse-held --yes

    STAGE="alineacion-apriltag-mesa2"
    info "[DEPÓSITO 1/3] Alineando el chasis con MESA2_DROP_TARGET..."
    CRUZR_APRILTAG_EXTENDED=1 timed ALIGN_MESA2 with_fast "$ALIGN_SCRIPT" --align-held --yes
  fi

  STAGE="deposito-mesa2"
  info "[DEPÓSITO 2/3] Verificando agarre y depositando por contacto..."
  DEPOSIT_ATTEMPTED=1
  # El depósito conserva el preflight canónico completo incluso con --fast.
  timed DEPOSIT_MESA2 "$CYCLE_SCRIPT" --deposit-held --yes
  BOX_RELEASED=1
  BOX_HELD=0

  STAGE="recuperacion-home"
  info "[DEPÓSITO 3/3] Retirándose de mesa 2 y ejecutando cruzr/home..."
  timed RECOVERY_HOME with_fast "$RECOVERY_SCRIPT" --run --yes
  STAGE="completado"
  info "TABLE_TRANSFER_COMPLETED=mesa1->MESA2_PRE->mesa2->home"
  info "TIMING_TOTAL=$((SECONDS - TRANSFER_STARTED_AT))s"
}

main() {
  require_scripts
  exec 9>"/tmp/cruzr_blue_workbin_table_transfer.lock"
  flock -n 9 || die "Ya hay otra transferencia entre mesas en ejecución."
  LOG_DIR="$(umask 077; mktemp -d "${TMPDIR:-/tmp}/cruzr-table-transfer.XXXXXXXX")"
  info "TRANSFER_LOG_DIR=$LOG_DIR"
  trap on_exit EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  trap 'exit 129' HUP

  if ((WITHOUT_APRILTAG == 1)) && [[ "$MODE" != teach-mesa2 ]]; then
    load_map_drop_profile
  fi
  if ((FLUID == 1)); then
    info "FLUID_PROFILE=deposit_tolerance:0.050m,apriltag_swing:3.5deg,apriltag_step:0.18m,apriltag_samples:3,apriltag_iterations:4,approach_speed:0.12mps,retreat_speed:0.08mps,automatic_navigation_retries:0"
  fi

  case "$MODE" in
    teach-mesa2)
      teach_mesa2
      ;;
    check)
      preflight
      ;;
    stage-held)
      preflight
      confirm_once
      stage_box_at_mesa2
      ;;
    resume-held-from-mesa1)
      BOX_HELD=1
      preflight
      confirm_once
      resume_held_from_mesa1
      align_deposit_and_home
      ;;
    resume-held-navigation)
      BOX_HELD=1
      preflight
      confirm_once
      resume_held_navigation
      align_deposit_and_home
      ;;
    resume-held|resume-held-approach)
      BOX_HELD=1
      preflight
      confirm_once
      align_deposit_and_home
      ;;
    run)
      preflight
      confirm_once
      stage_box_at_mesa2
      align_deposit_and_home
      ;;
    *)
      die "Modo interno desconocido: $MODE"
      ;;
  esac
}

main
