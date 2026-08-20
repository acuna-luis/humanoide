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
# MESA2_PRE está dentro de la inflación dinámica de la propia mesa. El tránsito
# va directamente a una pose 1,08 m detrás, sin pasar por PASO1; después la
# aproximación adaptativa mediante AprilTag cubre solo la distancia restante.
# La franja inscribed comenzaba a 0,974 m del waypoint en el log instrumentado.
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
readonly FLUID_PREFLIGHT_CACHE="/tmp/cruzr_table_transfer_fluid_preflight"
readonly FLUID_PREFLIGHT_TTL_SECONDS="180"

MODE="check"
YES=0
FAST=0
FLUID=0
STAGE="inicio"
BOX_HELD=0
BOX_RELEASED=0
CARGO_PROFILE_ACTIVE=0
MESA2_COARSE_READY=0
TRANSFER_STARTED_AT="$SECONDS"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/cruzr_blue_workbin_table_transfer.sh --check [--fast]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --stage-held [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --resume-held-from-mesa1 [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --resume-held-navigation [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --resume-held [--yes] [--fast]
  ./scripts/cruzr_blue_workbin_table_transfer.sh --run [--yes] [--fast|--fluid]

Modos:
  --check       Comprueba mapa, waypoint, manipulación y AprilTag. No mueve.
  --stage-held  Coge la caja en mesa 1, se retira, navega a MESA2_PRE y solo
                comprueba que el tag 113 continúa visible. Termina sujetando
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
  --resume-held Desde MESA2_PRE y con la caja ya sujeta, alinea con el tag 113,
                deposita en mesa 2, retrocede y termina en home.
  --run         Ejecuta de una vez --stage-held seguido de --resume-held.

Opciones:
  --fluid       Modo de producción para el ciclo completo: implica --fast,
                acepta el depósito dentro de 50 mm, reduce muestras y evita
                auditorías duplicadas. Conserva paros, cargador, agarre,
                odometría y el resultado de todas las acciones físicas.
                Un --check --fluid se reutiliza durante 180 s.

Durante toda navegación con la caja se mantienen LiDAR, mapa, localización,
odometría, bumpers y paros. Las tres nubes RGB-D/estéreo se excluyen
temporalmente del costmap para evitar que la propia carga bloquee el plan. La
configuración original se restaura antes del depósito y también ante error o
Ctrl+C. Use este perfil únicamente con una ruta controlada y despejada.

La primera puesta en servicio debe usar --stage-held. Ejecute --resume-held
solo después de comprobar visualmente que la caja sigue estable y que la mesa
2 está libre. Si falla cualquier etapa anterior al depósito, el script no abre
los cogedores y la caja permanece sujeta.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

timed() {
  local label="$1"
  shift
  local started="$SECONDS"
  local status=0
  "$@" || status=$?
  info "TIMING_${label}=$((SECONDS - started))s"
  return "$status"
}

while (($#)); do
  case "$1" in
    --check|--stage-held|--resume-held-from-mesa1|--resume-held-navigation|--resume-held|--run)
      MODE="${1#--}"
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

export CRUZR_FLUID_MODE="$FLUID"

require_scripts() {
  local path
  for path in "$CARRY_SCRIPT" "$CYCLE_SCRIPT" "$MAP_SCRIPT" \
    "$ALIGN_SCRIPT" "$RECOVERY_SCRIPT" "$CARGO_PROFILE_SCRIPT"; do
    [[ -x "$path" ]] || die "No existe o no es ejecutable: $path"
  done
}

with_fast() {
  local script="$1"
  shift
  local -a args=("$@")
  ((FAST == 1)) && args+=(--fast)
  "$script" "${args[@]}"
}

confirm_once() {
  ((YES == 1)) && return 0
  case "$MODE" in
    stage-held)
      cat <<'EOF'

CONFIRMACIÓN — TRASLADO HASTA MESA2_PRE
El robot cogerá la caja, retrocederá 0,50 m y navegará hasta MESA2_PRE.
Terminará allí sujetando la caja. Confirma que Ethernet y cargador están
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
El robot ya debe estar en MESA2_PRE sujetando la caja. Corregirá su pose con
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
  local status="$?"
  local restore_status=0
  if ((CARGO_PROFILE_ACTIVE == 1)); then
    set +e
    "$CARGO_PROFILE_SCRIPT" --restore >&2
    restore_status=$?
    set -e
    if ((restore_status == 0)); then
      CARGO_PROFILE_ACTIVE=0
    else
      printf 'AVISO: no se pudo restaurar automáticamente el perfil de percepción de carga.\n' >&2
      ((status != 0)) || status="$restore_status"
    fi
  fi
  ((status != 0)) || return 0
  printf '\nTRANSFERENCIA_INTERRUMPIDA etapa=%s estado=%s\n' "$STAGE" "$status" >&2
  printf 'TIMING_TOTAL_INTERRUPTED=%ss\n' "$((SECONDS - TRANSFER_STARTED_AT))" >&2
  if ((BOX_HELD == 1 && BOX_RELEASED == 0)); then
    cat >&2 <<'EOF'
La caja puede continuar sujeta. No reinicie el ciclo completo ni ejecute home.
Mantenga la zona despejada y diagnostique el estado antes de liberar o reanudar.
EOF
  elif [[ "$STAGE" == "agarre-mesa1" ]]; then
    cat >&2 <<'EOF'
El agarre no llegó a confirmarse. Los brazos pueden no haberse movido; no use
--resume-held. Compruebe visualmente la postura antes de repetir el ciclo.
EOF
  elif ((BOX_RELEASED == 1)); then
    cat >&2 <<'EOF'
La caja ya fue liberada. Si la recuperación no terminó, use
cruzr_recover_to_home.sh después de confirmar que la zona frontal está libre.
EOF
  fi
  return "$status"
}

preflight() {
  STAGE="preflight-mapa"
  export CRUZR_ROUTE_CONTEXT="table-transfer"
  timed PREFLIGHT_MAP with_fast "$MAP_SCRIPT" --check
  unset CRUZR_ROUTE_CONTEXT
  STAGE="preflight-apriltag"
  timed PREFLIGHT_APRILTAG "$ALIGN_SCRIPT" --check
  STAGE="preflight-perfil-carga"
  timed PREFLIGHT_CARGO "$CARGO_PROFILE_SCRIPT" --check
  export CRUZR_TRANSFER_PREFLIGHT_DONE=1
  if ((FLUID == 1)); then
    (umask 077; printf '%s\n' "$(date +%s)" >"$FLUID_PREFLIGHT_CACHE")
    info "FLUID_PREFLIGHT_PRIMED=${FLUID_PREFLIGHT_TTL_SECONDS}s"
  fi
  info "TABLE_TRANSFER_CHECK_OK: mapa, $MAP_WAYPOINT, agarre y AprilTag disponibles."
}

enable_cargo_profile() {
  ((CARGO_PROFILE_ACTIVE == 0)) || return 0
  # Se marca antes de iniciar la transacción para que el trap de EXIT pueda
  # recuperar también una instalación interrumpida por Ctrl+C.
  CARGO_PROFILE_ACTIVE=1
  with_fast "$CARGO_PROFILE_SCRIPT" --enable
}

restore_cargo_profile() {
  ((CARGO_PROFILE_ACTIVE == 1)) || return 0
  "$CARGO_PROFILE_SCRIPT" --restore
  CARGO_PROFILE_ACTIVE=0
}

preflight_for_motion() {
  local primed_at=""
  local now
  local age

  if ((FLUID == 1)) && [[ -f "$FLUID_PREFLIGHT_CACHE" && -O "$FLUID_PREFLIGHT_CACHE" ]]; then
    read -r primed_at <"$FLUID_PREFLIGHT_CACHE" || primed_at=""
    now="$(date +%s)"
    if [[ "$primed_at" =~ ^[0-9]+$ ]]; then
      age=$((now - primed_at))
      if ((age >= 0 && age <= FLUID_PREFLIGHT_TTL_SECONDS)); then
        STAGE="preflight-reutilizado"
        export CRUZR_TRANSFER_PREFLIGHT_DONE=1
        info "FLUID_PREFLIGHT_REUSED=age:${age}s,ttl:${FLUID_PREFLIGHT_TTL_SECONDS}s"
        info "Los controles críticos se revalidarán antes de cada movimiento."
        return 0
      fi
    fi
  fi
  preflight
}

navigate_mesa2_with_clearance_retry() {
  local output
  local status
  local restore_status
  local started="$SECONDS"

  info "CARGO_NAVIGATION_PROFILE: tránsito temporal con LiDAR; nubes RGB-D/estéreo fuera del costmap..."
  enable_cargo_profile
  set +e
  output="$(
    export CRUZR_NAV_TIMEOUT_SECONDS="$MESA2_NAV_TIMEOUT_SECONDS"
    with_fast "$MAP_SCRIPT" --navigate-waypoint-backoff "$MAP_WAYPOINT" \
      "$MESA2_CARGO_BACKOFF_METERS" --yes 2>&1
  )"
  status=$?
  set -e
  printf '%s\n' "$output"

  restore_status=0
  restore_cargo_profile || restore_status=$?
  ((restore_status == 0)) || \
    die "La navegación terminó, pero no se pudo restaurar la percepción original (estado $restore_status)."

  if ((status == 0)); then
    STAGE="aproximacion-gruesa-mesa2"
    info "MESA2_CARGO_STAGING_OK: fuera de la inflación de la mesa."
    with_fast "$CYCLE_SCRIPT" --verify-grasp
    "$ALIGN_SCRIPT" --check-visible
    info "Aproximación gruesa adaptativa mediante AprilTag antes de la alineación fina..."
    timed COARSE_APPROACH_MESA2 with_fast "$ALIGN_SCRIPT" --coarse-held --yes
    MESA2_COARSE_READY=1
    with_fast "$CYCLE_SCRIPT" --verify-grasp
    info "TIMING_NAVIGATE_MESA2=$((SECONDS - started))s"
    return 0
  fi

  if ! grep -Eq 'START_ONOBSTACLE|7218011|起点有静态障碍物' <<<"$output"; then
    if grep -q 'NAV_FAILURE_CLASS=DYNAMIC_OBSTACLE' <<<"$output"; then
      die "El costmap siguió bloqueado aun sin las nubes RGB-D/estéreo. El obstáculo procede de LiDAR, bumper o del mapa; no se desactivará esa protección."
    fi
    if grep -q 'NAV_FAILURE_CLASS=LOCALIZATION_LOST' <<<"$output"; then
      die "La navegación perdió la localización LiDAR antes de alcanzar $MAP_WAYPOINT."
    fi
    die "La navegación a $MAP_WAYPOINT falló sin indicar un obstáculo estático en el inicio."
  fi

  if [[ "$MODE" == "resume-held-navigation" ]]; then
    die "El inicio sigue bloqueado. Este modo no añadirá otro retroceso automático; la caja permanece sujeta."
  fi

  info "START_CLEARANCE_RECOVERY: la aproximación dejó la base dentro de la inflación estática."
  info "Verificando el agarre y aumentando una sola vez la separación de mesa 1 en 0,50 m..."
  with_fast "$CYCLE_SCRIPT" --verify-grasp
  timed EXTRA_CLEARANCE_MESA1 with_fast "$CARRY_SCRIPT" --retreat-only --yes
  export CRUZR_DRIVE_PREFLIGHT_DONE=1
  with_fast "$CYCLE_SCRIPT" --verify-grasp

  info "Reintentando una vez la navegación a $MAP_WAYPOINT..."
  enable_cargo_profile
  export CRUZR_NAV_TIMEOUT_SECONDS="$MESA2_NAV_TIMEOUT_SECONDS"
  set +e
  timed NAVIGATE_MESA2_RETRY with_fast \
    "$MAP_SCRIPT" --navigate-waypoint "$MAP_WAYPOINT" --yes
  status=$?
  set -e
  unset CRUZR_NAV_TIMEOUT_SECONDS
  restore_status=0
  restore_cargo_profile || restore_status=$?
  ((restore_status == 0)) || \
    die "No se pudo restaurar la percepción original tras el reintento."
  ((status == 0)) || die "El reintento de navegación a $MAP_WAYPOINT falló."
  info "TIMING_NAVIGATE_MESA2=$((SECONDS - started))s"
}

stage_box_at_mesa2() {
  STAGE="agarre-mesa1"
  info "[1/5] Centrando, sujetando y elevando la caja en mesa 1..."
  timed GRASP_MESA1 with_fast "$CARRY_SCRIPT" --grasp-only --yes
  BOX_HELD=1
  export CRUZR_DRIVE_PREFLIGHT_DONE=1

  STAGE="retirada-mesa1"
  info "[2/5] Separándose 0,50 m de mesa 1..."
  timed RETREAT_MESA1 with_fast "$CARRY_SCRIPT" --retreat-only --yes

  STAGE="navegacion-mesa2-pre"
  info "[3/5] Navegando con la caja hasta $MAP_WAYPOINT..."
  navigate_mesa2_with_clearance_retry

  STAGE="verificacion-agarre-mesa2"
  info "[4/5] Confirmando que el agarre continúa vigente..."
  if ((FLUID == 0)) || [[ "$MODE" == "stage-held" ]]; then
    with_fast "$CYCLE_SCRIPT" --verify-grasp
  else
    info "FLUID_MODE: --align-held verificará el agarre; se omite la lectura duplicada."
  fi

  STAGE="visibilidad-tag-con-caja"
  info "[5/5] Comprobando el tag 113 con la caja sujeta; no se moverá la base..."
  if [[ "$MODE" == "stage-held" || "$FLUID" == "0" ]]; then
    "$ALIGN_SCRIPT" --check-visible
  else
    info "FLUID_MODE: la alineación inmediata comprobará el tag; se omite la medición duplicada."
  fi

  if [[ "$MODE" == "stage-held" ]]; then
    cat <<'EOF'

MESA2_STAGE_HELD_OK
El robot está en MESA2_PRE, la caja continúa sujeta y el tag 113 fue medido.
No se ejecutó alineación ni depósito. Para continuar después de comprobar la
estabilidad de la caja y despejar mesa 2, use --resume-held.
EOF
  else
    info "MESA2_STAGE_HELD_OK: tag visible y agarre vigente; continuando con la alineación."
  fi
}

resume_held_from_mesa1() {
  BOX_HELD=1
  STAGE="verificacion-agarre-mesa1"
  info "[REANUDACIÓN 1/4] Confirmando el agarre ya existente en mesa 1..."
  with_fast "$CYCLE_SCRIPT" --verify-grasp

  STAGE="retirada-mesa1"
  info "[REANUDACIÓN 2/4] Separándose 0,50 m de mesa 1..."
  timed RETREAT_MESA1 with_fast "$CARRY_SCRIPT" --retreat-only --yes
  export CRUZR_DRIVE_PREFLIGHT_DONE=1

  STAGE="navegacion-mesa2-pre"
  info "[REANUDACIÓN 3/4] Navegando con la caja hasta $MAP_WAYPOINT..."
  navigate_mesa2_with_clearance_retry

  STAGE="verificacion-mesa2-pre"
  info "[REANUDACIÓN 4/4] Confirmando agarre y visibilidad del tag 113..."
  with_fast "$CYCLE_SCRIPT" --verify-grasp
  "$ALIGN_SCRIPT" --check-visible
  info "MESA2_STAGE_HELD_OK: caja sujeta y tag visible; continuando con el depósito."
}

resume_held_navigation() {
  BOX_HELD=1
  STAGE="verificacion-agarre-reanudacion-navegacion"
  info "[REANUDACIÓN DIRECTA 1/3] Confirmando la caja ya sujeta..."
  with_fast "$CYCLE_SCRIPT" --verify-grasp

  STAGE="navegacion-mesa2-pre"
  info "[REANUDACIÓN DIRECTA 2/3] Navegando sin repetir el retroceso a $MAP_WAYPOINT..."
  navigate_mesa2_with_clearance_retry

  STAGE="verificacion-mesa2-pre"
  info "[REANUDACIÓN DIRECTA 3/3] Confirmando agarre y visibilidad del tag 113..."
  with_fast "$CYCLE_SCRIPT" --verify-grasp
  "$ALIGN_SCRIPT" --check-visible
  info "MESA2_STAGE_HELD_OK: caja sujeta y tag visible; continuando con el depósito."
}

align_deposit_and_home() {
  BOX_HELD=1
  STAGE="verificacion-inicial-agarre"
  if ((FLUID == 0)); then
    with_fast "$CYCLE_SCRIPT" --verify-grasp
  else
    info "FLUID_MODE: --align-held verificará el agarre antes de mover."
  fi

  if ((MESA2_COARSE_READY == 0)); then
    STAGE="aproximacion-gruesa-mesa2"
    info "[DEPÓSITO 0/3] Acercándose de forma adaptativa al rango de alineación fina..."
    timed COARSE_APPROACH_MESA2 with_fast "$ALIGN_SCRIPT" --coarse-held --yes
    MESA2_COARSE_READY=1
  else
    info "[DEPÓSITO 0/3] Aproximación gruesa ya validada durante la navegación."
  fi

  STAGE="alineacion-apriltag-mesa2"
  info "[DEPÓSITO 1/3] Alineando el chasis con MESA2_DROP_TARGET..."
  export CRUZR_APRILTAG_EXTENDED=1
  timed ALIGN_MESA2 with_fast "$ALIGN_SCRIPT" --align-held --yes
  unset CRUZR_APRILTAG_EXTENDED

  STAGE="deposito-mesa2"
  info "[DEPÓSITO 2/3] Verificando agarre y depositando por contacto..."
  timed DEPOSIT_MESA2 with_fast "$CYCLE_SCRIPT" --deposit-held --yes
  BOX_RELEASED=1
  BOX_HELD=0

  STAGE="recuperacion-home"
  info "[DEPÓSITO 3/3] Retirándose de mesa 2 y ejecutando cruzr/home..."
  export CRUZR_AFTER_DEPOSIT=1
  timed RECOVERY_HOME with_fast "$RECOVERY_SCRIPT" --run --yes
  STAGE="completado"
  info "TABLE_TRANSFER_COMPLETED=mesa1->MESA2_PRE->mesa2->home"
  info "TIMING_TOTAL=$((SECONDS - TRANSFER_STARTED_AT))s"
}

main() {
  require_scripts
  exec 9>"/tmp/cruzr_blue_workbin_table_transfer.lock"
  flock -n 9 || die "Ya hay otra transferencia entre mesas en ejecución."
  trap on_exit EXIT

  if ((FLUID == 1)); then
    info "FLUID_PROFILE=deposit_tolerance:0.050m,apriltag_swing:3.5deg,apriltag_step:0.18m,apriltag_samples:3,apriltag_iterations:4,approach_speed:0.12mps,retreat_speed:0.08mps,start_clearance_retry:0.50m"
  fi

  case "$MODE" in
    check)
      preflight
      ;;
    stage-held)
      preflight_for_motion
      confirm_once
      stage_box_at_mesa2
      ;;
    resume-held-from-mesa1)
      BOX_HELD=1
      preflight_for_motion
      confirm_once
      resume_held_from_mesa1
      align_deposit_and_home
      ;;
    resume-held-navigation)
      BOX_HELD=1
      preflight_for_motion
      confirm_once
      resume_held_navigation
      align_deposit_and_home
      ;;
    resume-held)
      BOX_HELD=1
      preflight_for_motion
      confirm_once
      align_deposit_and_home
      ;;
    run)
      preflight_for_motion
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
