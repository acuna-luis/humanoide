#!/usr/bin/env bash
set -Eeuo pipefail

readonly MOTION_HOST="192.168.11.2"
readonly WIFI_GATEWAY="192.168.42.2"

readonly ROBOT_USER="walker"

# SSH ejecuta este mismo archivo para obtener la contraseña.
# Debe ir antes del procesamiento de argumentos.
if [[ "${CRUZR_INTERNAL_ASKPASS:-0}" == "1" ]]; then
    exec bash "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")/cruzr_recover_to_home.sh"
fi

readonly SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"

trap 'printf "Error en la línea %s (código %s)\n" "$LINENO" "$?" >&2' ERR

MODE=run
SSH_ROUTE=()
for argument in "$@"; do
    case "$argument" in
        --wifi) SSH_ROUTE=(-J "${ROBOT_USER}@${WIFI_GATEWAY}") ;;
        --check) MODE=check ;;
        --help|-h)
            printf 'Uso: %s [--wifi] [--check]\n' "$0"
            printf '%s\n' \
                'Sin --check: preparar mapa/localización → get1 → visión → separate_right → retroceso 20 cm → put1 → depósito → HOME.' \
                'Mapa de la tarea: utars_nav_map; carga y localización global automáticas si hacen falta.' \
                'Iniciar sin caja sujeta, desde la disposición de recogida del proveedor.' \
                '--check sólo consulta mapa/destino; no valida el montaje físico del depósito.' \
                'No reejecutar desde el inicio después de un fallo con caja sujeta.'
            exit 0 ;;
        *) printf 'Argumento desconocido: %s; use --help.\n' "$argument" >&2; exit 2 ;;
    esac
done
readonly MODE

# Tareas anteriores a SPS; no requiere ni arranca el adaptador frontal.
if [[ "$MODE" == run ]]; then
    if [[ ! -t 0 ]]; then
        printf 'Ejecute desde un terminal junto al robot.\n' >&2
        exit 78
    fi
    printf '%s\n' \
        'Ciclo original: get1 → Singapore/separate_right_cruzr → retroceso 20 cm → put1 → depósito → cruzr/originalhome.' \
        'La selección original puede elegir una caja lateral. No conserva la posición actual: navega a get1.' \
        'Compruebe abrazaderas vacías, postura estable, caja apoyada y recorridos libres,' \
        'destino preparado, cargador desconectado, paros liberados, ruedas en navegación,' \
        'modo automático, ningún otro mando activo y una persona junto al paro.'
    bash "$(dirname -- "$SCRIPT_PATH")/cruzr_blue_workbin_cycle.sh" --check
fi

if [[ ! -x "$SCRIPT_PATH" ]]; then
    printf 'El script necesita permiso de ejecución:\nchmod +x "%s"\n' \
        "$SCRIPT_PATH" >&2
    exit 1
fi

ssh_motion() {
    CRUZR_INTERNAL_ASKPASS=1 \
    SSH_ASKPASS="$SCRIPT_PATH" \
    SSH_ASKPASS_REQUIRE=force \
    DISPLAY="${DISPLAY:-:0}" \
    setsid -w ssh -T \
        -o ConnectTimeout=8 \
        -o ConnectionAttempts=1 \
        -o ServerAliveInterval=5 \
        -o ServerAliveCountMax=3 \
        -o PreferredAuthentications=password \
        -o PubkeyAuthentication=no \
        -o NumberOfPasswordPrompts=2 \
        -o StrictHostKeyChecking=accept-new \
        "${SSH_ROUTE[@]}" "${ROBOT_USER}@${MOTION_HOST}" "$@"
}

ssh_motion bash -se -- "$MODE" <<'REMOTE'
set -Eeuo pipefail

readonly CONTAINER="walker-motion.manipulation_robot_app-1"

echo "Conectado al robot: $(hostname)"

docker exec -i "$CONTAINER" bash -s -- "$1" <<'INNER'
set -Eeo pipefail

# El setup del proveedor consulta variables opcionales como COLCON_TRACE.
# Cárguelo sin nounset y vuelva a activar nounset para el ejecutor.
set +u
source /opt/walker/setup.bash
set -u
export ROS2CLI_DISABLE_DAEMON=1

readonly MODE="$1"
STAGE=preflight
NAVIGATION_ACTIVE=0

on_exit() {
    local status=$?
    trap - EXIT
    if (( NAVIGATION_ACTIVE )); then
        printf 'Solicitando parada de navegación tras interrupción...\n' >&2
        timeout 10 rosa action send_goal /vnav/task/command unav_task_msgs/action/Task \
            '{"command":"navigation_stop","arg_json":"{}"}' >&2 || true
    fi
    if (( status != 0 )); then
        printf 'FLUJO_INTERRUMPIDO etapa=%s código=%s. Sin reintento, apertura ni HOME automático.\n' \
            "$STAGE" "$status" >&2
        printf 'Un timeout del cliente no demuestra parada física; compruebe el robot antes de otra orden.\n' >&2
    fi
    exit "$status"
}
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP

validate_result() {
    python3 - "$1" "$2" <<'PY_RESULT'
import ast, json, re, sys
kind, output = sys.argv[1:]
try:
    matches = re.findall(r"^Result: result=(.*), status=(\d+)\s*$", output, re.M)
    if len(matches) != 1 or matches[0][1] != '4':
        raise ValueError('Falta un único resultado final exitoso status=4')
    result = ast.literal_eval(matches[0][0])
    desc = result['state']['desc']
    auxiliary_lost = (kind == 'navigation' and desc == 'VSLAM_LOCATION_LOST'
                      and result.get('dmsg','').startswith('navigation_start SUCCEEDED'))
    if not isinstance(desc, str) or (re.search(r'ERROR|FAIL|ABORT|CANCEL|LOST|OBSTACLE', desc, re.I) and not auxiliary_lost):
        raise ValueError('Estado de error: ' + str(desc))
    if kind == 'motion' and (desc != 'SUCCEED' or result['state']['state'] != 1101001):
        raise ValueError('Motion no informó SUCCEED/1101001')
    if kind == 'map_value':
        value = json.loads(result['result_json'])['map_name']
        if not isinstance(value, str): raise ValueError('Nombre de mapa inválido')
        print(value)
    if kind == 'state_value':
        values = re.findall(r'\bFSM_[A-Z_]+\b', result.get('dmsg', ''))
        if len(values) != 1: raise ValueError('Estado de navegación desconocido')
        print(values[0])
    if kind in ('map_set', 'relocation_start'):
        expected = 'VSLAM_LOAD_MAP_FINISHED' if kind == 'map_set' else 'NAVIGATION_READY'
        if desc not in (expected, 'SUCCESS', 'SUCCEED'):
            raise ValueError('Preparación no confirmada: ' + desc)
    if kind == 'map' and json.loads(result['result_json'])['map_name'] != 'utars_nav_map':
        raise ValueError('El mapa activo no es utars_nav_map')
    if kind == 'state' and not re.search(r'\bFSM_WAITNAVIGATE\b', result.get('dmsg', '')):
        raise ValueError('Navegación no está localizada y disponible')
    if kind == 'navigation' and not (
        desc in ('SUCCESS', 'SUCCEED') or result.get('dmsg', '').startswith('navigation_start SUCCEEDED')
    ):
        raise ValueError('El servidor no confirmó llegada al punto')
except (ValueError, SyntaxError, KeyError, TypeError) as exc:
    raise SystemExit('RESULTADO_RECHAZADO: ' + str(exc))
PY_RESULT
}

nav_query() {
    local command="$1" args="$2" limit="$3" goal
    goal="$(python3 -c 'import json,sys; print(json.dumps({"command":sys.argv[1],"arg_json":sys.argv[2]}))' "$command" "$args")"
    NAV_OUTPUT="$(timeout "$limit" rosa action send_goal /vnav/task/command unav_task_msgs/action/Task "$goal" 2>&1)" || {
        printf '%s\n' "$NAV_OUTPUT" >&2; return 52;
    }
    printf '%s\n' "$NAV_OUTPUT"
}

check_map_and_destination() {
    local current_map current_state
    nav_query get_map_name '{}' 12
    current_map="$(validate_result map_value "$NAV_OUTPUT")"
    nav_query check_state '{}' 12
    current_state="$(validate_result state_value "$NAV_OUTPUT")"
    # No cambiar mapa ni relocalizar mientras navega, mapea o está en un estado desconocido.
    case "$current_state" in
        FSM_WAITNAVIGATE|FSM_WAITRELOCATE|FSM_WAITSETMAP) ;;
        *) printf 'Navegación ocupada o estado no admitido: %s\n' "$current_state" >&2; return 54 ;;
    esac
    POINT_TARGETS="$(python3 - <<'PY_POINT'
import json, math, urllib.request, sys
request = urllib.request.Request(
    'http://192.168.11.3:30023/map/get/utars_nav_map', data=b'{}',
    headers={'Content-Type': 'application/json'}, method='POST')
response = json.loads(urllib.request.urlopen(request, timeout=8).read())
if response.get('code') != 200:
    raise SystemExit('No se pudo consultar el mapa: ' + str(response.get('code')))
points = json.loads(response['message'])['umap']['target_points']
targets = {}
for name in ('get1', 'put1'):
    selected = [p for p in points if p.get('id') == name]
    if len(selected) != 1:
        raise SystemExit('Falta un ' + name + ' único en utars_nav_map. Guárdelo antes del agarre.')
    p = selected[0]
    marker = p.get('type') == 'mapping_marker' and p.get('mode') == ''
    if p.get('mode') != 'logo_nav' and not marker:
        raise SystemExit(name + ' modo/tipo no permitido: ' + repr((p.get('mode'),p.get('type'))))
    if not all(type(p.get(k)) in (int, float) and math.isfinite(p[k])
               for k in ('point_x', 'point_y', 'point_yaw')):
        raise SystemExit(name + ' tiene coordenadas/orientación inválidas')
    print(name.upper() + '_DISPONIBLE=' + json.dumps({k: p[k] for k in ('point_x', 'point_y', 'point_yaw')}), file=sys.stderr)
    target = {'map_name':'utars_nav_map', 'mode':'logo_nav', 'id':name}
    if marker:
        target = dict(map_name='utars_nav_map', mode='free_nav', level=1,
                      **{k:p[k] for k in ('point_x','point_y','point_yaw')},
                      speed={'linear':{'x':0.18,'y':0.01,'z':0.0},
                             'angular':{'x':0.0,'y':0.0,'z':0.20}})
    target['_expected_pose'] = {k:p[k] for k in ('point_x','point_y','point_yaw')}
    targets[name] = target
print(json.dumps(targets))
PY_POINT
)" || return
    if [[ "$MODE" == check ]]; then
        [[ "$current_map" == utars_nav_map && "$current_state" == FSM_WAITNAVIGATE ]] || {
            printf 'PREPARACION_REQUERIDA: al ejecutar se cargará utars_nav_map y/o se localizará. --check no cambia estado.\n' >&2
            return 55
        }
        return 0
    fi
    if [[ "$current_map" != utars_nav_map || "$current_state" == FSM_WAITSETMAP ]]; then
        STAGE=map_set
        nav_query map_set '{"map_name":"utars_nav_map"}' 90
        validate_result map_set "$NAV_OUTPUT"
        current_state=FSM_WAITRELOCATE
    fi
    if [[ "$current_state" == FSM_WAITRELOCATE ]]; then
        STAGE=relocation_start
        nav_query relocation_start '{"map_name":"utars_nav_map","target_point":{"mode":"global"}}' 90
        validate_result relocation_start "$NAV_OUTPUT"
    fi
    # Confirmación posterior independiente: una respuesta de acción no basta.
    STAGE=verify_map_localization
    nav_query get_map_name '{}' 12
    validate_result map "$NAV_OUTPUT"
    nav_query check_state '{}' 12
    validate_result state "$NAV_OUTPUT"
    printf 'MAPA_Y_LOCALIZACION_LISTOS=utars_nav_map\n'
}

run_task_once() {
    local task_name="$1"
    local timeout_seconds="$2"
    local output

    STAGE="$task_name"
    printf '\nEjecutando acción: %s\n' "$task_name"
    output="$(timeout "$timeout_seconds" rosa action send_goal \
        /mc/manipulation/action \
        mc_task_msgs/action/ArmTask \
        "{\"task_name\":\"${task_name}\",\"yaml_args\":\"{}\"}" 2>&1)" || {
        printf '%s\n' "$output" >&2
        return 50
    }
    printf '%s\n' "$output"

    validate_result motion "$output"

    printf 'Acción finalizada correctamente: %s\n' "$task_name"
}

verify_arrival() {
    python3 - "$POINT_TARGETS" "$1" <<'PY_ARRIVAL'
import json, math, os, subprocess, sys, time
expected = json.loads(sys.argv[1])[sys.argv[2]]['_expected_pose']
previous = None
for sample in range(2):
    started = time.time()
    try:
        r = subprocess.run(['rosa','topic','echo','--once','--no-daemon',
                            '--qos-durability','volatile','/nav/robot_pose'],
                           capture_output=True,text=True,timeout=7,
                           env=dict(os.environ, ROSA_LOG_LEVEL='ERROR'))
        if r.returncode: raise ValueError('No se recibió pose actual')
        pose = json.loads(r.stdout)
        stamp = pose['header']['stamp']
        sec, ns = stamp['sec'], stamp['nanosec']
        if type(sec) is not int or type(ns) is not int or not 0 <= ns < 1000000000:
            raise ValueError('Marca temporal inválida')
        timestamp = sec + ns/1e9
        now = time.time()
        if not started - 0.1 <= timestamp <= now + 0.5 or now-timestamp > 2:
            raise ValueError('Pose antigua o reloj incoherente')
        if previous is not None and timestamp <= previous:
            raise ValueError('La marca temporal no avanza')
        previous = timestamp
        if pose['header']['frame_id'] != 'map': raise ValueError('Marco distinto de map')
        p,q = pose['pose']['position'],pose['pose']['orientation']
        values = [p[k] for k in ('x','y','z')] + [q[k] for k in ('x','y','z','w')]
        if not all(type(v) in (int,float) and math.isfinite(v) for v in values):
            raise ValueError('Pose no finita')
        norm = math.sqrt(sum(q[k]**2 for k in ('x','y','z','w')))
        if abs(norm-1) > 0.01: raise ValueError('Cuaternión inválido')
        q = {k:v/norm for k,v in q.items()}
        yaw = math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
        distance = math.hypot(p['x']-expected['point_x'],p['y']-expected['point_y'])
        angle = abs(math.atan2(math.sin(yaw-expected['point_yaw']),math.cos(yaw-expected['point_yaw'])))
        if distance > 0.05 or angle > math.radians(3):
            raise ValueError('Fuera del destino: %.4fm / %.3fgrados' % (distance,math.degrees(angle)))
        print('LLEGADA_%s_MUESTRA_%d=%.4fm,%.3fgrados; stamp=%.9f' %
              (sys.argv[2],sample+1,distance,math.degrees(angle),timestamp))
    except (ValueError,KeyError,TypeError,subprocess.TimeoutExpired) as exc:
        raise SystemExit('LLEGADA_NO_VERIFICADA: '+str(exc))
print('LLEGADA_VERIFICADA='+sys.argv[2])
PY_ARRIVAL
}

navigate_point() {
    local point="$1" output goal
    STAGE="navigation_$point"
    goal="$(python3 - "$POINT_TARGETS" "$point" <<'PY_GOAL'
import json,sys
target=json.loads(sys.argv[1])[sys.argv[2]]
target.pop('_expected_pose')
print(json.dumps({'command':'navigation_start','arg_json':json.dumps({'target_point':target})}))
PY_GOAL
)"
    NAVIGATION_ACTIVE=1
    printf '\nNavegando a %s en utars_nav_map...\n' "$point"
    output="$(timeout 180 rosa action send_goal /vnav/task/command unav_task_msgs/action/Task "$goal" 2>&1)" || {
        printf '%s\n' "$output" >&2; return 53;
    }
    printf '%s\n' "$output"
    validate_result navigation "$output"
    STAGE="verify_arrival_$point"
    nav_query get_map_name '{}' 12
    validate_result map "$NAV_OUTPUT"
    nav_query check_state '{}' 12
    validate_result state "$NAV_OUTPUT"
    verify_arrival "$point"
    NAVIGATION_ACTIVE=0
}

navigate_get1() { navigate_point get1; }
navigate_put1() { navigate_point put1; }

check_map_and_destination
if [[ "$MODE" == check ]]; then
    printf 'CHECK_OK: mapa localizado y get1/put1 disponibles; no se envió movimiento.\n'
    exit 0
fi

# El árbol completo del escenario 1 habilita este modo después de navegar.
# Una llamada directa al agarre debe reproducir ese prerrequisito.
navigate_get1
sleep 1
run_task_once "vision/enable_transport_vision_switch" 20
sleep 1
run_task_once "Singapore/separate_right_cruzr" 45
run_task_once "cruzr/mobot_back_20" 30
navigate_put1
run_task_once "wrc_cruzr/put_cruzr_wrc_low" 120
run_task_once "cruzr/originalhome" 60
printf 'CICLO_GET1_PUT1_HOME_COMPLETADO\n'
INNER

echo "Comando finalizado."
REMOTE
