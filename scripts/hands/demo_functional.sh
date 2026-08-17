#!/usr/bin/env bash

set -Eeuo pipefail
source "$(dirname -- "$(readlink -f -- "$0")")/_common.sh"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/hands/demo_functional.sh --check --demo plate [--model auto|v3|v4]
  ./scripts/hands/demo_functional.sh --run   --demo plate [--model auto|v3|v4]
  ./scripts/hands/demo_functional.sh --check --demo remote
  ./scripts/hands/demo_functional.sh --run   --demo remote

plate:
  Usa la postura oficial de sujeción de bandeja. Requiere una bandeja vacía,
  ligera, rígida y previamente ensayada. Siempre pide confirmar que está
  apoyada antes de abrir y regresar a home.

remote:
  Sólo v4. Prepara la mano izquierda, espera la colocación manual de un mando
  ligero, ejecuta la acción oficial de pulsación y pide sujetarlo antes de
  abrir y volver a home. La pose del objeto debe calibrarse primero en vacío.

--yes no omite las confirmaciones de apoyo de los objetos.
EOF
}

mode="check"
model="auto"
demo=""
yes=0
while (($#)); do
  case "$1" in
    --check) mode="check" ;;
    --run) mode="run" ;;
    --model)
      shift
      (($#)) || hands_die "--model requiere un valor."
      model="$1"
      ;;
    --demo)
      shift
      (($#)) || hands_die "--demo requiere plate o remote."
      demo="$1"
      ;;
    --yes) yes=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) hands_die "Opción desconocida: $1" ;;
  esac
  shift
done
[[ "$demo" == "plate" || "$demo" == "remote" ]] || hands_die "Selecciona --demo plate o --demo remote."
((yes == 0)) || export CRUZR_HANDS_CONFIRMED=1

if [[ "$demo" == "remote" ]]; then
  [[ "$model" == "auto" || "$model" == "v4" ]] || hands_die "remote sólo es compatible con v4."
  hands_preflight v4
  tasks=(
    production_movie/grasp_the_remote_control_ready
    production_movie/press_the_remote_control
    production_movie/press_the_remote_control_down
    v4hand/dual_hand_open
    cruzr/home
  )
else
  hands_preflight "$model"
  if [[ "$HANDS_DETECTED_MODEL" == "v3" ]]; then
    tasks=(qyh/hold_plate_v3hand qyh/hold_plate_back_v3hand)
  else
    tasks=(qyh/hold_plate_v4hand v4hand/dual_hand_open cruzr/home)
  fi
fi
hands_validate_tasks "${tasks[@]}"

if [[ "$mode" == "check" ]]; then
  hands_info "FUNCTIONAL_CHECK_OK=demo:$demo,model:$HANDS_DETECTED_MODEL,movement:none"
  exit 0
fi

[[ -t 0 ]] || hands_die "La demostración con objetos requiere una terminal interactiva."
hands_lock
cat <<EOF

CONFIRMACIÓN — DEMOSTRACIÓN FUNCIONAL: $demo
  - Manos $HANDS_DETECTED_MODEL homed; robot inicialmente en home.
  - El objeto es ligero, vacío, rígido y no puede atrapar los dedos.
  - La pose se validó antes sin objeto y el entorno está despejado.
  - Una segunda persona sostiene el paro físico.

Escribe OBJETO PREPARADO para continuar:
EOF
read -r answer
[[ "$answer" == "OBJETO PREPARADO" ]] || hands_die "Demostración cancelada."

if [[ "$demo" == "plate" ]]; then
  hands_run_task "${tasks[0]}"
  hands_info "PLATE_HOLDING=ready_for_video"
  printf '\nApoya y sujeta firmemente la bandeja. Escribe BANDEJA APOYADA para liberar:\n'
  read -r answer
  [[ "$answer" == "BANDEJA APOYADA" ]] || hands_die "La bandeja permanece sujeta; no se ordenará apertura/home."
  for ((index=1; index<${#tasks[@]}; index++)); do
    hands_run_task "${tasks[index]}"
  done
else
  hands_run_task "${tasks[0]}"
  printf '\nColoca el mando en la mano izquierda. Escribe MANDO COLOCADO para pulsar:\n'
  read -r answer
  [[ "$answer" == "MANDO COLOCADO" ]] || hands_die "No se iniciará la pulsación."
  hands_run_task "${tasks[1]}"
  sleep 2
  hands_run_task "${tasks[2]}"
  printf '\nSujeta el mando. Escribe MANDO SUJETO para abrir y volver a home:\n'
  read -r answer
  [[ "$answer" == "MANDO SUJETO" ]] || hands_die "El mando permanece agarrado; no se ordenará apertura/home."
  hands_run_task "${tasks[3]}"
  hands_run_task "${tasks[4]}"
fi
hands_info "FUNCTIONAL_DEMO_COMPLETED=demo:$demo,model:$HANDS_DETECTED_MODEL,pose:home"

