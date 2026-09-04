#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/run_vla_canary_physical_e6_0y.sh --check
  ./scripts/vla/run_vla_canary_physical_e6_0y.sh --ready
  ./scripts/vla/run_vla_canary_physical_e6_0y.sh --one-point
  ./scripts/vla/run_vla_canary_physical_e6_0y.sh --recover
  ./scripts/vla/run_vla_canary_physical_e6_0y.sh --stop

E6.0Y separa cada movimiento. --ready mueve de HOME a READY. --one-point
arranca sólo el adaptador de inferencia y el ejecutor acotado del proyecto,
consume el punto 0 de un único chunk task 0 y destruye el publicador al
terminar o fallar. --recover sólo acepta READY medido y vuelve a HOME.

Cada modo de movimiento exige preflight fresco y confirmación exacta propia.
No se arranca el ejecutor físico entregado por UBTECH. El STOP software no
equivale al E-stop; una persona debe permanecer junto al E-stop principal.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly RUNTIME_DIR="$SCRIPT_DIR/runtime"
readonly LIVE_PREFLIGHT="$SCRIPT_DIR/audit_vla_live_preflight_e6_0g.sh"
readonly SHADOW="$SCRIPT_DIR/run_ubtech_vla_shadow.sh"
readonly NEW_EVIDENCE="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly MANIPULATION_CHECK="$REPO_ROOT/scripts/cruzr_blue_workbin_cycle.sh"
readonly HOME_GATE="$REPO_ROOT/scripts/lib/cruzr_home_posture_gate.py"
readonly READY_GATE="$RUNTIME_DIR/cruzr_s2_vla_ready_state_gate.py"
readonly GRANT_BUILDER="$RUNTIME_DIR/create_cruzr_s2_vla_activation_grant_e6_0y.py"
readonly ACTIVATION_TEMPLATE="$RUNTIME_DIR/cruzr_s2_vla_canary_activation_template_e6_0w.json"
readonly OWNER_ACCEPTANCE="$RUNTIME_DIR/cruzr_s2_vla_owner_acceptance_e6_0x.json"
readonly LIMITS="$RUNTIME_DIR/cruzr_s2_vla_canary_engineering_limits_e6_0s.json"
readonly MONITOR="$RUNTIME_DIR/cruzr_s2_vla_measured_state_monitor.py"
readonly MONITOR_CONTRACT="$RUNTIME_DIR/cruzr_s2_vla_measured_state_monitor_contract_e6_0u.json"
readonly TRANSPORT="$RUNTIME_DIR/cruzr_s2_vla_sdk_transport.py"
readonly TRANSPORT_CONTRACT="$RUNTIME_DIR/cruzr_s2_vla_sdk_transport_contract_e6_0r.json"
readonly PROFILE="$RUNTIME_DIR/cruzr_s2_vla_profile.json"
readonly CORE="$RUNTIME_DIR/cruzr_s2_vla_one_point_runtime.py"
readonly ROS_PROCESS="$RUNTIME_DIR/cruzr_s2_vla_ros_one_point_process.py"
readonly ROS_BACKEND="$RUNTIME_DIR/cruzr_s2_vla_ros_sdk_backend.py"
readonly MOTION_HOST="${CRUZR_MOTION_HOST:-192.168.11.2}"
readonly VISION_HOST="${CRUZR_VISION_HOST:-192.168.11.3}"
readonly ROBOT_USER="walker"
readonly DEFAULT_PASSWORD="aa"
readonly MOTION_CONTAINER="walker-motion.manipulation_robot_app-1"
readonly CONTROL_CONTAINER="cruzr-vla-control"
readonly INFERENCE_CONTAINER="cruzr-vla-inference"
readonly REMOTE_RUNTIME="/home/walker/cruzr-vla/additional/safe-runtime"
readonly CONTAINER_RUNTIME="/home/ubt/additional/safe-runtime"
readonly READY_TASK="s2_bio_vla/s2_vla_pick_large_teleop_ready"
readonly RECOVERY_TASK="s2_bio_vla/s2_vla_e6_0_exact_recovery"
readonly READY_CONFIRMATION="AUTORIZO READY E6.0 SIN CAJA: HOME MEDIDO, CLAMPS VACIOS, ZONA 1.5 M VACIA, DOS PERSONAS Y MANO EN E-STOP"
readonly POINT_CONFIRMATION="AUTORIZO E6.0 UN PUNTO VLA SIN CAJA: READY MEDIDO, CLAMPS VACIOS, ZONA 1.5 M VACIA, DOS PERSONAS Y MANO EN E-STOP"
readonly RECOVERY_CONFIRMATION="AUTORIZO RECOVERY E6.0 A HOME: READY MEDIDO, CLAMPS VACIOS, ZONA 1.5 M VACIA, DOS PERSONAS Y MANO EN E-STOP"

CRUZR_SSH_PASSWORD="${CRUZR_SSH_PASSWORD:-$DEFAULT_PASSWORD}"
export CRUZR_SSH_PASSWORD
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == 1 ]]; then
  printf '%s\n' "$CRUZR_SSH_PASSWORD"
  exit 0
fi

MODE=""
while (($#)); do
  case "$1" in
    --check|--ready|--one-point|--recover|--stop)
      [[ -z "$MODE" ]] || { printf 'ERROR: indique un solo modo\n' >&2; exit 2; }
      MODE="$1"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ -n "$MODE" ]] || { printf 'ERROR: falta modo\n' >&2; usage >&2; exit 2; }

for tool in awk date find grep jq nc python3 readlink scp seq setsid sha256sum sleep sort ssh tee timeout xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta %s\n' "$tool" >&2; exit 1; }
done
for required in "$LIVE_PREFLIGHT" "$SHADOW" "$NEW_EVIDENCE" \
  "$MANIPULATION_CHECK" "$HOME_GATE" "$READY_GATE" "$GRANT_BUILDER" \
  "$ACTIVATION_TEMPLATE" "$OWNER_ACCEPTANCE" "$LIMITS" "$MONITOR" \
  "$MONITOR_CONTRACT" "$TRANSPORT" "$TRANSPORT_CONTRACT" "$PROFILE" \
  "$CORE" "$ROS_PROCESS" "$ROS_BACKEND"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done

ssh_options=(
  -o ConnectTimeout=10
  -o ConnectionAttempts=1
  -o ServerAliveInterval=10
  -o ServerAliveCountMax=2
  -o PreferredAuthentications=password
  -o PubkeyAuthentication=no
  -o NumberOfPasswordPrompts=1
  -o StrictHostKeyChecking=accept-new
)

run_ssh() {
  local host="$1"
  shift
  CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
    DISPLAY="${DISPLAY:-:0}" setsid -w ssh "${ssh_options[@]}" \
    "$ROBOT_USER@$host" "$@"
}

run_scp_motion() {
  CRUZR_INTERNAL_ASKPASS=1 SSH_ASKPASS="$SCRIPT_PATH" SSH_ASKPASS_REQUIRE=force \
    DISPLAY="${DISPLAY:-:0}" setsid -w scp "${ssh_options[@]}" \
    "$1" "$ROBOT_USER@$MOTION_HOST:$2"
}

capture_actuator_json() {
  run_ssh "$MOTION_HOST" \
    "docker exec '$MOTION_CONTAINER' bash -lc 'set +u; source /opt/walker/setup.bash; set -u; timeout 8 rosa topic echo --once --no-daemon /mc/actuator_state'"
}

capture_whole_joint_json() {
  run_ssh "$MOTION_HOST" \
    "docker exec '$MOTION_CONTAINER' bash -lc 'set +u; source /opt/walker/setup.bash; set -u; timeout 8 rosa topic echo --once --no-daemon /mc/whole_joint_states'"
}

capture_ready() {
  local actuator_health named_ready
  # Raw actuator data is authoritative for faults, enable state, velocity and
  # latent command delta, but not for checkpoint joint signs.  The home gate
  # performs those health checks even when MEASURED_HOME=0 in READY.
  actuator_health="$(capture_actuator_json | python3 "$HOME_GATE")"
  named_ready="$(capture_whole_joint_json | python3 "$READY_GATE" --contract "$TRANSPORT_CONTRACT")"
  printf 'READY_ACTUATOR_HEALTH=passed\n%s\n%s\n' "$actuator_health" "$named_ready"
}

capture_home() {
  capture_actuator_json | python3 "$HOME_GATE"
}

read_confirmation() {
  local expected="$1" variable_name="$2" confirmation
  confirmation="${!variable_name:-}"
  if [[ -z "$confirmation" && -t 0 ]]; then
    printf '\nEscriba exactamente:\n%s\n' "$expected"
    IFS= read -r confirmation
  fi
  [[ "$confirmation" == "$expected" ]] || {
    printf 'ERROR: confirmación exacta ausente; no se envió movimiento.\n' >&2
    return 2
  }
}

released_preflight() {
  "$LIVE_PREFLIGHT" --check --expect-released
}

run_motion_task() {
  local task="$1" limit="$2"
  run_ssh "$MOTION_HOST" bash -s -- "$MOTION_CONTAINER" "$task" "$limit" <<'REMOTE'
set -Eeuo pipefail
container="$1"
task="$2"
limit="$3"
output="$(docker exec -i "$container" bash -s -- "$task" "$limit" <<'INNER'
set -Eeo pipefail
set +u
source /opt/walker/setup.bash
set -u
task="$1"
limit="$2"
timeout "$limit" rosa action send_goal /mc/manipulation/action \
  mc_task_msgs/action/ArmTask \
  "{\"task_name\":\"$task\",\"yaml_args\":\"{}\"}"
INNER
)"
printf '%s\n' "$output"
grep -q "'desc': 'SUCCEED'" <<<"$output"
grep -q 'status=4' <<<"$output"
REMOTE
}

publisher_count() {
  run_ssh "$MOTION_HOST" "docker exec walker-ros.ros2-1 bash -lc '
    source /opt/ros/humble/setup.bash
    export ROS2CLI_DISABLE_DAEMON=1
    output=\$(timeout 8 ros2 topic info /mc/sdk/robot_command 2>&1) || true
    awk '\''/Publisher count:/ {print \$3; found=1} END {if (!found) print 0}'\'' <<<\"\$output\"
  '"
}

assert_runtime_sources() {
  python3 -m py_compile "$READY_GATE" "$GRANT_BUILDER" "$CORE" "$ROS_PROCESS" "$ROS_BACKEND"
  jq -e '.owner_accepted == true and .acceptance_is_movement_authorization == false' \
    "$OWNER_ACCEPTANCE" >/dev/null
  jq -e '.manufacturer_certified == false and .owner_accepted == false and .physical_execution_authorized == false' \
    "$LIMITS" >/dev/null
  jq -e '.active_launcher_enabled == false and .physical_execution_authorized == false' \
    "$ACTIVATION_TEMPLATE" >/dev/null
  python3 "$ROS_PROCESS" --check \
    --activation "$ACTIVATION_TEMPLATE" --runtime "$CORE" --monitor "$MONITOR" \
    --transport "$TRANSPORT" --ros-backend "$ROS_BACKEND" \
    --monitor-contract "$MONITOR_CONTRACT" --transport-contract "$TRANSPORT_CONTRACT" \
    --limits "$LIMITS" --profile "$PROFILE"
  printf 'E6.0Y_CHECK_OK=local-only,no-robot,no-ros,no-publisher,no-movement\n'
}

finalize_evidence() {
  local run_dir="$1"
  (
    cd "$run_dir"
    find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
  ) > "$run_dir/evidence.sha256"
  (cd "$run_dir" && sha256sum -c evidence.sha256 >/dev/null)
}

case "$MODE" in
  --check)
    assert_runtime_sources
    exit 0
    ;;
  --stop)
    "$SHADOW" --stop
    [[ "$(publisher_count)" == 0 ]] || {
      printf 'ERROR: aún existe un publicador de mando; accione E-stop.\n' >&2
      exit 1
    }
    printf 'E6.0Y_STOPPED=containers-exited,publishers-0\n'
    exit 0
    ;;
esac

nc -z -w3 "$MOTION_HOST" 22 || { printf 'ERROR: Motion no responde.\n' >&2; exit 1; }
nc -z -w3 "$VISION_HOST" 22 || { printf 'ERROR: Vision no responde.\n' >&2; exit 1; }
assert_runtime_sources

case "$MODE" in
  --ready)
    preflight="$(released_preflight)"
    home="$(capture_home)"
    grep -Fq 'MEASURED_HOME=1' <<<"$home"
    printf '%s\n%s\n' "$preflight" "$home"
    read_confirmation "$READY_CONFIRMATION" E6_0Y_READY_CONFIRMATION
    run_dir="$("$NEW_EVIDENCE" --experiment E6.0Y-READY)"
    printf '%s\n' "$preflight" > "$run_dir/preflight-before.log"
    printf '%s\n' "$home" > "$run_dir/home-before.log"
    if ! run_motion_task "$READY_TASK" 120 | tee "$run_dir/ready-action.log"; then
      printf 'ERROR: READY falló; no repita. Mantenga el robot estable y use diagnóstico.\n' >&2
      exit 1
    fi
    ready="$(capture_ready)"
    printf '%s\n' "$ready" | tee "$run_dir/ready-after.log"
    grep -Fq 'MEASURED_READY=1' <<<"$ready"
    cat > "$run_dir/actual_result.yaml" <<EOF
experiment_id: E6.0Y-READY
run_id: $(basename -- "$run_dir")
status: PASS_HOME_TO_READY_MEASURED
physical_movement_commanded: true
task: $READY_TASK
measured_ready: true
next_gate: OPERATOR_VISUAL_READY_CONFIRMATION_THEN_ONE_POINT
EOF
    finalize_evidence "$run_dir"
    printf 'E6.0Y_READY_EVIDENCE_OK=%s\n' "$run_dir"
    ;;
  --recover)
    preflight="$(released_preflight)"
    ready="$(capture_ready)"
    grep -Fq 'MEASURED_READY=1' <<<"$ready" || {
      printf '%s\nERROR: recovery E6.0 sólo admite READY medido; no se movió.\n' "$ready" >&2
      exit 1
    }
    printf '%s\n%s\n' "$preflight" "$ready"
    read_confirmation "$RECOVERY_CONFIRMATION" E6_0Y_RECOVERY_CONFIRMATION
    run_dir="$("$NEW_EVIDENCE" --experiment E6.0Y-RECOVERY)"
    printf '%s\n' "$preflight" > "$run_dir/preflight-before.log"
    printf '%s\n' "$ready" > "$run_dir/ready-before.log"
    if ! run_motion_task "$RECOVERY_TASK" 120 | tee "$run_dir/recovery-action.log"; then
      printf 'ERROR: recovery falló; no repita y accione E-stop ante contacto.\n' >&2
      exit 1
    fi
    home="$(capture_home)"
    printf '%s\n' "$home" | tee "$run_dir/home-after.log"
    grep -Fq 'MEASURED_HOME=1' <<<"$home"
    cat > "$run_dir/actual_result.yaml" <<EOF
experiment_id: E6.0Y-RECOVERY
run_id: $(basename -- "$run_dir")
status: PASS_READY_TO_HOME_MEASURED
physical_movement_commanded: true
task: $RECOVERY_TASK
measured_home: true
EOF
    finalize_evidence "$run_dir"
    printf 'E6.0Y_RECOVERY_EVIDENCE_OK=%s\n' "$run_dir"
    ;;
  --one-point)
    preflight_before="$(released_preflight)"
    ready_before="$(capture_ready)"
    grep -Fq 'MEASURED_READY=1' <<<"$ready_before" || {
      printf '%s\nERROR: el canary sólo puede armarse desde READY medido.\n' "$ready_before" >&2
      exit 1
    }
    printf '%s\n%s\n' "$preflight_before" "$ready_before"
    printf 'E6.0Y_PREPARING_INFERENCE_ONLY=1; todavía no se publicará movimiento\n'
    "$SHADOW" --deploy
    cleanup_required=1
    cleanup() {
      local exit_code=$?
      trap - EXIT INT TERM
      if [[ "${cleanup_required:-0}" == 1 ]]; then
        set +e
        "$SHADOW" --stop
        set -e
      fi
      if ((exit_code != 0)) && [[ -n "${run_dir:-}" && ! -e "$run_dir/actual_result.yaml" ]]; then
        cat > "$run_dir/actual_result.yaml" <<EOF
experiment_id: E6.0Y
run_id: $(basename -- "$run_dir")
status: FAIL_CLOSED_BEFORE_CONFIRMED_COMPLETION
physical_movement_commanded: unknown
physical_command_publisher_after_cleanup: 0
vla_containers_after_cleanup: exited
automatic_retry_executed: false
EOF
        finalize_evidence "$run_dir"
      fi
      exit "$exit_code"
    }
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    "$SHADOW" --start-inference

    inference_ready=0
    for _ in $(seq 1 90); do
      if run_ssh "$VISION_HOST" \
        "docker exec '$INFERENCE_CONTAINER' grep -Fq INFERENCE_STATE_READY /home/ubt/additional/safe-runtime-logs/inference-process.log" \
        2>/dev/null; then
        inference_ready=1
        break
      fi
      sleep 1
    done
    ((inference_ready == 1)) || {
      run_ssh "$VISION_HOST" "docker exec '$INFERENCE_CONTAINER' tail -n 80 /home/ubt/additional/safe-runtime-logs/inference-process.log" || true
      printf 'ERROR: inferencia no quedó lista; no se creó publicador.\n' >&2
      exit 1
    }
    [[ "$(publisher_count)" == 0 ]] || { printf 'ERROR: publicador inesperado.\n' >&2; exit 1; }
    safety="$("$MANIPULATION_CHECK" --check)"
    grep -Fq 'ACTUATORS_OPERATION_ENABLED=1' <<<"$safety"
    grep -Fq 'ESTOPS=0,0' <<<"$safety"
    grep -Fq 'CHARGER=disconnected' <<<"$safety"
    grep -Fq 'ACTIONS=ready' <<<"$safety"
    ready_fresh="$(capture_ready)"
    grep -Fq 'MEASURED_READY=1' <<<"$ready_fresh"
    printf '%s\n%s\nINFERENCE_READY=1\nCOMMAND_PATH_SAFE=publishers:0\n' "$safety" "$ready_fresh"

    read_confirmation "$POINT_CONFIRMATION" E6_0Y_POINT_CONFIRMATION
    run_dir="$("$NEW_EVIDENCE" --experiment E6.0Y)"
    run_id="$(basename -- "$run_dir")"
    printf '%s\n' "$preflight_before" > "$run_dir/preflight-before.log"
    printf '%s\n' "$ready_before" > "$run_dir/ready-before.log"
    printf '%s\n' "$safety" > "$run_dir/preflight-immediate.log"
    printf '%s\n' "$ready_fresh" > "$run_dir/ready-immediate.log"
    motion_epoch="$(run_ssh "$MOTION_HOST" 'date +%s')"
    [[ "$motion_epoch" =~ ^[0-9]{10}$ ]] || {
      printf 'ERROR: reloj de Motion no válido; no se creó grant.\n' >&2
      exit 1
    }
    pc_epoch="$(date +%s)"
    clock_skew_seconds=$((pc_epoch - motion_epoch))
    clock_skew_abs="${clock_skew_seconds#-}"
    ((clock_skew_abs <= 60)) || {
      printf 'ERROR: desfase PC/Motion=%ss; no se creó grant.\n' "$clock_skew_seconds" >&2
      exit 1
    }
    printf 'GRANT_CLOCK_SOURCE=motion-host-epoch\nPC_MOTION_CLOCK_SKEW_SECONDS=%s\n' \
      "$clock_skew_seconds" | tee "$run_dir/clock.log"
    python3 "$GRANT_BUILDER" --template "$ACTIVATION_TEMPLATE" \
      --acceptance "$OWNER_ACCEPTANCE" --limits "$LIMITS" \
      --preflight "$run_dir/preflight-before.log" --ready "$run_dir/ready-immediate.log" \
      --run-id "$run_id" --output "$run_dir/activation-grant.json" \
      --reference-epoch "$motion_epoch" \
      | tee "$run_dir/grant.log"
    grant_sha="$(sha256sum "$run_dir/activation-grant.json" | awk '{print $1}')"
    remote_grant="$REMOTE_RUNTIME/grants/${run_id}.json"
    run_ssh "$MOTION_HOST" "install -d '$REMOTE_RUNTIME/grants'"
    run_scp_motion "$run_dir/activation-grant.json" "$remote_grant"
    run_ssh "$MOTION_HOST" "test \"\$(sha256sum '$remote_grant' | awk '{print \$1}')\" = '$grant_sha'"

    if ! run_ssh "$MOTION_HOST" bash -s -- "$CONTROL_CONTAINER" "$CONTAINER_RUNTIME" \
      "$run_id" "$grant_sha" <<'REMOTE'
set -Eeuo pipefail
container="$1"
runtime="$2"
run_id="$3"
grant_sha="$4"
test "$(docker inspect "$container" --format '{{.State.Status}}')" = exited
docker start "$container" >/dev/null
docker exec "$container" bash -lc "
  pkill -f '[c]ruzr_s2_shadow_validator.py|[c]ruzr_s2_vla_ros_one_point_process.py' 2>/dev/null || true
  install -d '$runtime/logs'
  : > '$runtime/logs/one-point-process.log'
"
docker exec -d "$container" bash -lc "
  set +u
  source /home/ubt/additional/vla-motionx86/install/setup.bash
  set -u
  export ROS2CLI_DISABLE_DAEMON=1
  exec python3 '$runtime/cruzr_s2_vla_ros_one_point_process.py' --run \\
    --activation '$runtime/grants/$run_id.json' \\
    --expected-activation-sha256 '$grant_sha' \\
    --runtime '$runtime/cruzr_s2_vla_one_point_runtime.py' \\
    --monitor '$runtime/cruzr_s2_vla_measured_state_monitor.py' \\
    --transport '$runtime/cruzr_s2_vla_sdk_transport.py' \\
    --ros-backend '$runtime/cruzr_s2_vla_ros_sdk_backend.py' \\
    --monitor-contract '$runtime/cruzr_s2_vla_measured_state_monitor_contract_e6_0u.json' \\
    --transport-contract '$runtime/cruzr_s2_vla_sdk_transport_contract_e6_0r.json' \\
    --limits '$runtime/cruzr_s2_vla_canary_engineering_limits_e6_0s.json' \\
    --profile '$runtime/cruzr_s2_vla_profile.json' \\
    > '$runtime/logs/one-point-process.log' 2>&1
"
sleep 2
pgrep_output="$(docker exec "$container" pgrep -af '[c]ruzr_s2_vla_ros_one_point_process.py')" || {
  docker exec "$container" cat "$runtime/logs/one-point-process.log" >&2 || true
  exit 1
}
printf '%s\n' "$pgrep_output"
REMOTE
    then
      printf 'ERROR: el proceso de un punto no arrancó; no se enviará trigger.\n' >&2
      exit 1
    fi
    [[ "$(publisher_count)" == 0 ]] || { printf 'ERROR: publicador apareció antes del chunk.\n' >&2; exit 1; }

    printf '\nE6.0Y_LIVE=1: el siguiente trigger puede mover ambos brazos <=0.1 rad durante <=2 s.\n'
    run_ssh "$VISION_HOST" "docker exec '$INFERENCE_CONTAINER' bash -lc '
      set +u
      source /home/ubt/additional/vla-onboard/install/setup.bash
      set -u
      export ROS2CLI_DISABLE_DAEMON=1
      timeout 30 ros2 action send_goal /gr00t/trigger_inference mc_task_msgs/action/InferenceTask \
        \"{task_id: 0, max_inference_duration: 15.0, end_threshold: 0.1}\" --feedback
    '" | tee "$run_dir/inference-trigger.log"

    process_done=0
    for _ in $(seq 1 35); do
      if ! run_ssh "$MOTION_HOST" \
        "docker exec '$CONTROL_CONTAINER' pgrep -f '[c]ruzr_s2_vla_ros_one_point_process.py' >/dev/null"; then
        process_done=1
        break
      fi
      sleep 1
    done
    ((process_done == 1)) || { printf 'ERROR: runtime excedió plazo; se detendrá.\n' >&2; exit 1; }
    run_ssh "$MOTION_HOST" \
      "docker exec '$CONTROL_CONTAINER' cat '$CONTAINER_RUNTIME/logs/one-point-process.log'" \
      | tee "$run_dir/one-point-process.log"
    grep -Fq 'E6.0W_FINAL_STATE=COMPLETED' "$run_dir/one-point-process.log"

    "$SHADOW" --stop | tee "$run_dir/stop.log"
    cleanup_required=0
    [[ "$(publisher_count)" == 0 ]]
    preflight_after="$(released_preflight)"
    ready_after="$(capture_ready)"
    printf '%s\n' "$preflight_after" > "$run_dir/preflight-after.log"
    printf '%s\n' "$ready_after" > "$run_dir/posture-after.log"
    frames="$(awk -F'\"frames_published\": ' '/frames_published/ {split($2,a,","); value=a[1]} END {print value+0}' "$run_dir/one-point-process.log")"
    cat > "$run_dir/actual_result.yaml" <<EOF
experiment_id: E6.0Y
run_id: $run_id
status: PASS_ONE_CHECKPOINT_SOURCE_POINT_PHYSICALLY_DISPATCHED
scenario: NO_BOX_READY
task_id: 0
axis_profile: P14_A
source_point_index: 0
activation_grant_sha256: $grant_sha
transport_frames_published: $frames
maximum_target_delta_rad: 0.1
maximum_velocity_rad_s: 0.15
maximum_acceleration_rad_s2: 0.5
vla_containers_after: exited
physical_publishers_after: 0
automatic_recovery_executed: false
next_gate: OPERATOR_VISUAL_INSPECTION_BEFORE_ANY_RECOVERY
EOF
    cp -- "$SCRIPT_PATH" "$READY_GATE" "$GRANT_BUILDER" "$run_dir/"
    finalize_evidence "$run_dir"
    printf 'E6.0Y_ONE_POINT_EVIDENCE_OK=%s\n' "$run_dir"
    printf 'E6.0Y_AUTOMATIC_RECOVERY=0; inspeccione antes de cualquier otro movimiento.\n'
    ;;
esac
