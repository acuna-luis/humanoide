"""PC-only presentation of supervisor events; never used for control decisions."""
import json
import math
import re
import time


STAGE_LABELS = {
    'navigate_get1': 'Ir a get1',
    'enable_vision': 'Activar visión',
    'grasp': 'Recoger y separar la caja',
    'verify_held': 'Registrar sujeción',
    'retreat': 'Retroceder',
    'navigate_put1': 'Ir a put1',
    'deposit': 'Depositar la caja',
    'verify_released': 'Registrar liberación',
    'home': 'Volver a HOME',
    'verify_home': 'Comprobar HOME',
}
ALERT = re.compile(r'LOST|FAIL|ERROR|FAULT|ABORT|COLLISION|OBSTACLE|STOP|TIMEOUT|BLOCK|PAUS|UNKNOWN|REJECT|CANCEL', re.I)


def mapping(value):
    return value if isinstance(value, dict) else {}


def clean(value):
    """Keep provider messages on one line, without terminal control characters."""
    return ' '.join(''.join(c if c.isprintable() else ' ' for c in str(value or '')).split())


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return float(value) if math.isfinite(value) else None
    except OverflowError:
        return None


def decimal(value, places=1):
    return format(value, '.'+str(places)+'f').replace('.', ',')


def seconds(value):
    value = number(value)
    return decimal(value)+' s' if value is not None and value >= 0 else 'tiempo no disponible'


def stage_label(stage):
    return STAGE_LABELS.get(clean(stage), clean(stage))


def residual(rows):
    rows = rows if isinstance(rows, list) else [rows]
    distances = [number(mapping(row).get('distance_m')) for row in rows]
    angles = [number(mapping(row).get('yaw_error_deg')) for row in rows]
    distances = [abs(value)*1000 for value in distances if value is not None]
    angles = [abs(value) for value in angles if value is not None]
    if not distances or not angles:
        return 'medida no disponible'
    return decimal(max(distances))+' mm / '+decimal(max(angles), 2)+'°'


class ConsoleReporter:
    def __init__(self, verbose=False, clock=None):
        self.verbose = verbose
        self.clock = clock or time.monotonic
        self.last_feedback = {}
        self.confirmations = {}

    def render(self, event):
        if self.verbose:
            return [json.dumps(event, ensure_ascii=False)]
        event = mapping(event)
        name = clean(event.get('event'))
        if name == 'checkpoint':
            self.confirmations = mapping(mapping(event.get('checkpoint')).get('confirmations'))
            return []
        if name in ('action', 'health_worker'):
            return self.detail(mapping(event.get('detail')), clean(event.get('kind') or name))
        if name == 'arrival':
            return ['  Llegada '+clean(event.get('point'))+': '+residual(event.get('measurement'))]
        if name == 'get1_correction':
            measured = residual(event.get('measurements'))
            if event.get('phase') == 'blocked_before_dispatch':
                return ['  Ajuste get1 no enviado: '+clean(mapping(event.get('qualification')).get('reason'))+
                        '; llegada medida '+measured+'. Agarre no iniciado.']
            phase = 'inicio' if event.get('phase') == 'start' else 'resultado medido'
            return ['  Ajuste get1 '+clean(event.get('attempt'))+': '+phase+'; '+measured]
        if name == 'resume_checked':
            return ['  Entrada comprobada: '+stage_label(event.get('stage'))+'; caja declarada/asumida: '+
                    clean(mapping(event.get('requirements')).get('box_state'))+'.']
        if name == 'resume_arrival':
            return ['  Posición de entrada '+clean(event.get('point'))+': '+residual(event.get('measurements'))]
        if name == 'resume_prerequisite':
            return ['  Preparación de la entrada: '+clean(event.get('task'))]
        if name == 'sensor_check':
            return ['  Telemetría FT/articular recibida; referencias: '+clean(event.get('qualification'))]
        if name == 'sensor_verification':
            state = {'held': 'caja sujeta', 'released': 'caja liberada'}.get(clean(event.get('state')), clean(event.get('state')))
            return ['  FT/postura compatibles con '+state]
        if name == 'timing' and event.get('operation') == 'health':
            return ['  Comprobación de estado técnico: '+seconds(event.get('elapsed_s'))]
        if name == 'stage_complete':
            record = mapping(self.confirmations.get(clean(event.get('stage'))))
            assumed = event.get('logical_assumption') or record.get('source') == 'assumed'
            suffix = '; estado de caja asumido' if assumed else ''
            return ['  Etapa completada: '+seconds(event.get('elapsed_s'))+suffix]
        if name == 'check_benchmark':
            return ['  Lectura '+clean(event.get('iteration'))+': '+seconds(event.get('elapsed_s'))+' en total']
        if name in ('native_log', 'perception'):
            detail = mapping(event.get('detail'))
            message = clean(event.get('text') or detail.get('reason') or detail.get('event'))
            return ['  AVISO: '+message] if ALERT.search(message) else []
        return self.detail(event, '')

    def detail(self, event, kind):
        name = clean(event.get('event'))
        reason = clean(event.get('reason'))
        if name == 'feedback':
            feedback = mapping(event.get('feedback'))
            state = mapping(feedback.get('state'))
            desc = clean(state.get('desc'))
            message = clean(feedback.get('dmsg'))
            alert = bool(ALERT.search(desc+' '+message))
            key = (kind, clean(event.get('goal_id') or event.get('request_id')))
            signature = (desc, clean(state.get('state')))
            now = self.clock()
            previous = self.last_feedback.get(key)
            if not alert and previous and previous[0] == signature and now-previous[1] < 1.0:
                return []
            self.last_feedback[key] = (signature, now)
            label = {'RUNNING': 'En curso', '': 'En curso', 'FINISH': 'FINISH (pendiente de resultado)',
                     'READY': 'READY (pendiente de resultado)'}.get(desc, desc)
            current = number(feedback.get('current_time'))
            total = number(feedback.get('total_time'))
            if current is not None and current >= 0:
                label += ' — '+seconds(current)
                if total is not None and total > 0:
                    label += ' / '+seconds(total)
            if alert and message:
                label += '; '+message
            return ['  '+('AVISO: ' if alert else '')+label]
        if name == 'result':
            result = mapping(event.get('result'))
            desc = clean(mapping(result.get('state')).get('desc'))
            message = clean(result.get('dmsg'))
            status = event.get('status')
            alert = bool(ALERT.search(desc+' '+message)) or status != 4
            label = desc or 'sin descripción'
            if status != 4:
                label += '; estado de acción '+clean(status)
            if alert and message:
                label += '; '+message
            # Transport success does not prove stage completion or localization.
            return ['  '+('AVISO: ' if alert else '')+'Resultado recibido: '+label]
        labels = {
            'error': 'ERROR', 'rejected': 'Orden rechazada',
            'cancel_requested': 'Cancelación solicitada',
            'cancel_response': 'Respuesta a cancelación recibida (parada física no confirmada)',
            'terminal_unknown': 'Estado final desconocido; parada física no confirmada',
            'interrupted_terminal': 'Acción interrumpida; estado físico por comprobar',
            'worker_exit_unconfirmed': 'Salida del ejecutor sin confirmar; parada física no confirmada',
            'adapter_exit_unconfirmed': 'Salida del adaptador sin confirmar',
            'sensor_profile_pending': 'Referencias de sensores pendientes',
        }
        if name in labels:
            if name == 'cancel_response':
                code = mapping(event.get('response')).get('return_code')
                if code is not None:
                    reason = 'código '+clean(code)
            return ['  '+labels[name]+(': '+reason if reason else '')]
        if name == 'accepted' and event.get('accepted') is False:
            return ['  Orden no aceptada'+(': '+reason if reason else '')]
        if name in ('request_complete', 'worker_closed') and event.get('returncode') not in (None, 0):
            return ['  ERROR: ejecutor terminó con código '+clean(event.get('returncode'))]
        if ALERT.search(name):
            return ['  AVISO: '+name+(': '+reason if reason else '')]
        return []
