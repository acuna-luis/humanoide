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
        self.shown_box_measurements = set()
        self.shown_box_rejections = set()

    def rejected_box_measurement(self, detail):
        """Display the rejected gate input, without reselecting or authorizing it.

        None requests the existing generic warning; an empty list means this
        exact diagnostic was already shown. A missing axis never hides others.
        """
        if detail.get('frame_id') != 'base_link':
            return None
        identity = None
        stamp = detail.get('time_ns')
        if type(stamp) is int and stamp > 0:
            try:
                identity = json.dumps(detail, sort_keys=True, separators=(',', ':'))
            except (TypeError, ValueError):
                pass  # Malformed diagnostics still must not hide the rejection.
        if identity is not None and identity in self.shown_box_rejections:
            return []
        position, bounds = mapping(detail.get('position')), mapping(detail.get('bounds_m'))
        lines = ['  AVISO: Caja seleccionada en base_link — rechazada por posición '
                 '(Z no es altura al suelo):']
        for axis in 'xyz':
            prefix = '    '+axis.upper()+': '
            limits = bounds.get(axis)
            if not isinstance(limits, (tuple, list)) or len(limits) != 2:
                lines.append(prefix+'dato no disponible')
                continue
            value, low, high = number(position.get(axis)), number(limits[0]), number(limits[1])
            if None in (value, low, high) or low > high:
                lines.append(prefix+'dato no disponible')
                continue
            if value < low:
                label, distance = 'falta hasta mínimo', low-value
            elif value > high:
                label, distance = 'exceso sobre máximo', value-high
            elif value-low <= high-value:
                label, distance = 'margen al mínimo', value-low
            else:
                label, distance = 'margen al máximo', high-value
            cm, low_cm, high_cm, distance_mm = value*100, low*100, high*100, distance*1000
            if any(number(item) is None for item in (cm, low_cm, high_cm, distance_mm)):
                lines.append(prefix+'dato no disponible')
                continue
            lines.append(prefix+decimal(cm, 2)+' cm ['+decimal(low_cm, 2)+' a '+
                         decimal(high_cm, 2)+' cm]; '+label+': '+decimal(distance_mm)+' mm')
        if identity is not None:
            self.shown_box_rejections.add(identity)
        return lines

    def box_measurement(self, detail):
        """Show the already-validated final capture; never decide robot control."""
        if detail.get('event') not in ('detected', 'selected'):
            return []
        selection = mapping(detail.get('selection'))
        gate = mapping(selection.get('position_gate'))
        if gate.get('passed') is not True or gate.get('frame_id') != 'base_link':
            return []
        stamp, index = detail.get('stamp_ns'), selection.get('selected_index')
        if type(stamp) is not int or stamp <= 0 or type(index) is not int or index < 0:
            return []
        position = mapping(mapping(selection.get('selected_pose')).get('position'))
        bounds = mapping(gate.get('bounds_m'))
        measured = []
        lines = ['  Caja seleccionada en base_link — dentro del rango XYZ (Z no es altura al suelo):']
        for axis in 'xyz':
            limits = bounds.get(axis)
            if not isinstance(limits, (tuple, list)) or len(limits) != 2:
                return []
            value, low, high = number(position.get(axis)), number(limits[0]), number(limits[1])
            if None in (value, low, high) or not low <= value <= high:
                return []
            lower_gap, upper_gap = value-low, high-value
            face = 'mínimo' if lower_gap <= upper_gap else 'máximo'
            cm, low_cm, high_cm, margin_mm = value*100, low*100, high*100, min(lower_gap, upper_gap)*1000
            if any(number(item) is None for item in (cm, low_cm, high_cm, margin_mm)):
                return []
            measured.append((axis, value, low, high))
            lines.append('    '+axis.upper()+': '+decimal(cm, 2)+' cm ['+
                         decimal(low_cm, 2)+' a '+decimal(high_cm, 2)+' cm]; margen al '+face+
                         ': '+decimal(margin_mm)+' mm')
        identity = (stamp, index, tuple(measured))
        if identity in self.shown_box_measurements:
            return []
        self.shown_box_measurements.add(identity)
        return lines

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
        if name == 'box_alignment':
            phase = event.get('phase')
            if phase == 'prepare_head':
                return ['  Preparando cabeza para medir la caja antes del agarre']
            if phase == 'in_flight':
                delta = mapping(event.get('displacement_base_m'))
                axes = ', '.join(axis.upper()+': '+decimal(delta.get(axis, 0)*1000, 1)+' mm'
                                 for axis in 'xy' if delta.get(axis))
                return ['  Ajuste visual de caja '+clean(event.get('attempt'))+': '+axes]
            if phase == 'ready':
                return ['  Caja dentro del rango; ajustes visuales: '+clean(event.get('attempts'))+
                        '. Se vuelve a validar en el agarre.']
            return []
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
            if name == 'perception':
                if detail.get('event') == 'position_rejected':
                    rejected = self.rejected_box_measurement(detail)
                    if rejected is not None:
                        return rejected
                measured = self.box_measurement(detail)
                if measured:
                    return measured
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
            'perception_log_warning': 'AVISO de registro de percepción',
        }
        if name in labels:
            if name == 'cancel_response':
                code = mapping(event.get('response')).get('return_code')
                if code is not None:
                    reason = 'código '+clean(str(code))
            return ['  '+labels[name]+(': '+reason if reason else '')]
        if name == 'accepted' and event.get('accepted') is False:
            return ['  Orden no aceptada'+(': '+reason if reason else '')]
        if name in ('request_complete', 'worker_closed') and event.get('returncode') not in (None, 0):
            return ['  ERROR: ejecutor terminó con código '+clean(event.get('returncode'))]
        if ALERT.search(name):
            return ['  AVISO: '+name+(': '+reason if reason else '')]
        return []
