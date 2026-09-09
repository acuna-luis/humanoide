#!/usr/bin/env python3
"""Referencia local de depósito sin tags. Geometría plana; no publica comandos."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile


def number(value, name, low=None, high=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(name + ': se requiere un número finito')
    if (low is not None and value < low) or (high is not None and value > high):
        raise ValueError('%s: fuera de [%s, %s]' % (name, low, high))
    return float(value)


def pose(value):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError('drop_pose_m_rad: escribir [X metros, Y metros, yaw radianes]')
    return [number(value[0], 'X'), number(value[1], 'Y'),
            number(value[2], 'yaw radianes', -math.pi, math.pi)]


def validate(data, map_name, map_type):
    if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1:
        raise ValueError('Se requiere perfil version=1')
    if data.get('capture_method') != 'volatile-stamped-v2':
        raise ValueError('Referencia anterior sin comprobar frescura: volver a enseñar mesa 2 con --overwrite-mesa2; no editar sus coordenadas ni añadir esta marca a mano')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}', map_name):
        raise ValueError('Nombre de mapa inválido')
    if map_type not in ('uslam', 'fusion'):
        raise ValueError('Sin tags debe fijarse CRUZR_MAP_TYPE=uslam o fusion, no auto')
    if data.get('map_name') != map_name or data.get('map_type') != map_type:
        raise ValueError('El perfil no corresponde al mapa/tipo solicitado')
    if not isinstance(data.get('map_fingerprint'), str) or not re.fullmatch(r'[0-9a-f]{64}', data['map_fingerprint']):
        raise ValueError('Falta huella del mapa; registrar con --teach-mesa2')
    target = pose(data.get('drop_pose_m_rad'))
    distance = number(data.get('approach_distance_m'), 'approach_distance_m', .10, 1.20)
    pos_tol = number(data.get('position_tolerance_m'), 'position_tolerance_m', .005, .12)
    yaw_tol = number(data.get('yaw_tolerance_rad'), 'yaw_tolerance_rad', .005, .14)
    recorded = data.get('recorded_at_utc')
    if not isinstance(recorded, str) or not recorded.strip():
        raise ValueError('Falta recorded_at_utc')
    return dict(data, drop_pose_m_rad=target, approach_distance_m=distance,
                position_tolerance_m=pos_tol, yaw_tolerance_rad=yaw_tol)


def offset(target, backoff):
    x, y, yaw = target
    return [x - backoff * math.cos(yaw), y - backoff * math.sin(yaw), yaw]


def approach_steps(data):
    distance = data['approach_distance_m']
    # Primitiva existente admite 0,10–0,65 m. Usar tramos iguales <=0,60 m.
    count = math.ceil(distance / .60)
    step = distance / count
    return [(step, offset(data['drop_pose_m_rad'], distance - step * (i+1)))
            for i in range(count)]


def triplet(values):
    return ' '.join(format(value, '.12g') for value in values)


def corridor_remaining(data, current):
    current = pose(current)
    x, y, yaw = data['drop_pose_m_rad']
    dx, dy = x-current[0], y-current[1]
    remaining = dx*math.cos(yaw) + dy*math.sin(yaw)
    lateral = -dx*math.sin(yaw) + dy*math.cos(yaw)
    angle = math.atan2(math.sin(current[2]-yaw), math.cos(current[2]-yaw))
    if not 0 <= remaining <= data['approach_distance_m']:
        raise ValueError('La base no está dentro del tramo enseñado de aproximación')
    if abs(lateral) > data['position_tolerance_m'] or abs(angle) > data['yaw_tolerance_rad']:
        raise ValueError('Fuera del corredor o de su orientación permitida')
    # Un avance recto con la orientación actual debe terminar dentro del margen.
    if abs(lateral-remaining*math.tan(angle)) > data['position_tolerance_m']:
        raise ValueError('La orientación actual llevaría fuera del corredor')
    return remaining


def remaining_steps(data, current):
    remaining = corridor_remaining(data, current)
    if remaining < .10:
        raise ValueError('Menos de 0,10 m: verificar depósito por separado; no repetir aproximación')
    count = math.ceil(remaining/.55)
    return [(remaining/count, offset(data['drop_pose_m_rad'], remaining*(1-(i+1)/count)))
            for i in range(count)]


def forward_distance(data, current, target):
    current, target = pose(current), pose(target)
    # Se conserva la orientación de la base; comprobar el punto realmente alcanzable.
    dx, dy = target[0]-current[0], target[1]-current[1]
    angle = math.atan2(math.sin(current[2]-target[2]), math.cos(current[2]-target[2]))
    distance = dx*math.cos(current[2]) + dy*math.sin(current[2])
    cross = -dx*math.sin(current[2]) + dy*math.cos(current[2])
    if abs(angle) > data['yaw_tolerance_rad'] or abs(cross) > data['position_tolerance_m']:
        raise ValueError('El avance recto no alcanza el siguiente punto con el margen permitido')
    return number(distance, 'Avance restante', .10, .65)


def record(report, map_name, map_type, distance):
    def one(key):
        values = re.findall(r'^' + key + r'=(.*)$', report, re.M)
        if len(values) != 1:
            raise ValueError('Informe incompleto o ambiguo: ' + key)
        return values[0]
    data = dict(version=1, capture_method=one('MAP_POSE_FRESHNESS'), map_name=map_name, map_type=map_type,
                map_fingerprint=one('MAP_FINGERPRINT'),
                drop_pose_m_rad=list(map(float, one('MAP_POSE_REFERENCE').split())),
                approach_distance_m=distance, position_tolerance_m=.05,
                yaw_tolerance_rad=.05,
                recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                reference_description='Pose de base enseñada en mesa 2; confirmar montaje, postura de caja, apoyo y mesas inmóviles antes de ejecutar.')
    return validate(data, map_name, map_type)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['fields', 'plan', 'record', 'remaining-plan', 'forward-distance'])
    parser.add_argument('path', type=Path)
    parser.add_argument('--map-name', required=True)
    parser.add_argument('--map-type', required=True)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--approach-distance', type=float)
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--current-pose', nargs=3, type=float)
    parser.add_argument('--target-pose', nargs=3, type=float)
    args = parser.parse_args()
    try:
        if args.overwrite and args.mode != 'record':
            raise ValueError('--overwrite sólo se usa con record')
        if args.mode == 'record':
            if args.report is None or args.approach_distance is None:
                raise ValueError('record necesita --report y --approach-distance')
            data = record(args.report.read_text(), args.map_name, args.map_type, args.approach_distance)
            args.path.parent.mkdir(parents=True, exist_ok=True)
            save_profile(args.path, data, args.overwrite)
            print('MESA2_PROFILE_RECORDED=' + str(args.path))
            print('REFERENCIA_REGISTRADA: pendiente comprobar la geometría física y ensayar por etapas.')
            return 0
        data = validate(json.loads(args.path.read_text()), args.map_name, args.map_type)
        if args.mode == 'fields':
            print(triplet(offset(data['drop_pose_m_rad'], data['approach_distance_m'])))
            print(triplet(data['drop_pose_m_rad']))
            print(format(data['position_tolerance_m'], '.12g'))
            print(format(data['yaw_tolerance_rad'], '.12g'))
            print(data['map_fingerprint'])
        elif args.mode == 'forward-distance':
            print(format(forward_distance(data, args.current_pose, args.target_pose), '.12g'))
        else:
            steps = remaining_steps(data, args.current_pose) if args.mode == 'remaining-plan' else approach_steps(data)
            for distance, target in steps:
                print(format(distance, '.12g') + '|' + triplet(target))
    except (OSError, ValueError, TypeError) as exc:
        print('MESA2_PROFILE_ERROR: ' + str(exc), file=sys.stderr)
        return 2
    return 0


def save_profile(path, data, overwrite=False):
    payload = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if not overwrite:
        with path.open('x', encoding='utf-8') as stream:
            stream.write(payload)
        return
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('El perfil debe ser un archivo normal, no un enlace')
    # Preparar la sustitución completa antes de modificar el perfil actual.
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.new.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            original = path.read_bytes()
            backup_fd, backup = tempfile.mkstemp(prefix=path.name + '.bak.', dir=path.parent)
            with os.fdopen(backup_fd, 'wb') as stream:
                stream.write(original)
                stream.flush()
                os.fsync(stream.fileno())
            print('MESA2_PROFILE_BACKUP=' + backup)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == '__main__':
    raise SystemExit(main())
