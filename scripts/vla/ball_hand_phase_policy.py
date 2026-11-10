#!/usr/bin/env python3
"""Máquina de fases simbólica para la pelota; no controla el robot.

Las señales son declaraciones externas sin validar: no se infiere alcance,
contacto, altura, apoyo, frescura de sensores ni estado real de la mano. El
resultado no contiene posiciones, fuerzas, mensajes ROS ni órdenes físicas.
El escalar del modelo no se convierte en órdenes ni en una probabilidad.
"""

from dataclasses import dataclass, field
from typing import Mapping


SIGNALS = frozenset({
    'at_grasp', 'close_requested', 'closed_confirmed', 'lift_complete',
    'lower_complete', 'release_requested', 'supported_confirmed', 'open_confirmed',
})


@dataclass
class BallHandPhasePolicy:
    """Un intento, sin rearme ni ejecución: cada llamada avanza como máximo una fase."""

    _phase: str = field(default='approach', init=False)
    _last_sequence: int = field(default=-1, init=False)

    def update(self, sequence: int, signals: Mapping[str, bool]) -> dict:
        """Devuelve un objetivo simbólico según señales externas no verificadas.

        La secuencia debe avanzar. Una señal omitida equivale a no confirmada;
        un valor que no sea booleano o una señal desconocida rechaza la llamada.
        La secuencia no verifica antigüedad física ni identidad del sensor.
        """
        if type(sequence) is not int or sequence < 0 or sequence <= self._last_sequence:
            raise ValueError('sequence debe ser un entero creciente no negativo')
        if not isinstance(signals, Mapping) or set(signals) - SIGNALS:
            raise ValueError('señales desconocidas o formato inválido')
        if any(type(value) is not bool for value in signals.values()):
            raise ValueError('todas las señales presentes deben ser booleanas')

        phase = self._phase
        if phase == 'approach':
            if signals.get('at_grasp', False) and signals.get('close_requested', False):
                phase = 'closing'
        elif phase == 'closing':
            if signals.get('closed_confirmed', False):
                phase = 'grasped'
        elif phase == 'grasped':
            if signals.get('lift_complete', False):
                phase = 'lifted'
        elif phase == 'lifted':
            if signals.get('lower_complete', False):
                phase = 'lowered'
        elif phase == 'lowered':
            if signals.get('release_requested', False) and signals.get('supported_confirmed', False):
                phase = 'opening'
        elif phase == 'opening':
            if signals.get('open_confirmed', False):
                phase = 'complete'
        elif phase != 'complete':
            raise RuntimeError('fase interna inválida')

        self._phase = phase
        self._last_sequence = sequence
        symbolic_goal = 'closed' if phase in ('closing', 'grasped', 'lifted', 'lowered') else 'open'
        return {
            'schema': 'cruzr_ball_hand_phase_simulation_v1',
            'sequence': sequence,
            'phase': phase,
            'symbolic_hand_goal': symbolic_goal,
            'physical_control_qualified': False,
            'physical_commands_generated': 0,
            'limitations': [
                'all phase and support signals are supplied externally and are not verified',
                'no finger targets, torque, current, motor mode or ROS message is generated',
                'no calibration of the SmolVLA hand score or signal freshness is performed',
                'this output cannot be used to authorize physical movement',
            ],
        }
