"""Candidato de despacho de cabeza PICO: bloqueo físico incondicional.

La estructura reproduce el cliente y seguimiento del ensayo de cabeza HOME.
NO se ha cualificado para PICO/v4. La barrera inicial impide incluso crear el
ActionClient; esta pieza no es un método de parada física ni un ejecutor listo.
La espera de aceptación no supervisa checked() continuamente; sin un goal handle
una aceptación tardía no puede cancelarse. La cancelación no demuestra frenado.
"""
import time

from metamove_head_probe import check_envelope


def dispatch_after_qualification(node, checked, names, rclpy, emit):
    """Borrador revisable; sólo una futura modificación puede habilitarlo."""
    raise RuntimeError('PICO_HEAD_PHYSICAL_CONTROL_BLOCKED: geometry, mode and stopping not qualified')

    # Código de integración deliberadamente inalcanzable. No eliminar la barrera
    # sin un procedimiento revisado, protección de la escena y parada efectiva.
    from rclpy.action import ActionClient
    from mc_task_msgs.action import ArmTask
    from rosidl_runtime_py.convert import message_to_ordereddict

    initial, _ = checked()
    client = ActionClient(node, ArmTask, '/mc/manipulation/action')
    if not client.wait_for_server(timeout_sec=2):
        raise RuntimeError('Action server absent')
    checked()
    request = ArmTask.Goal()
    request.task_name = 'cruzr/move_head_lower'
    request.yaml_args = '{}'
    emit(kind='dispatch', task=request.task_name)
    future = client.send_goal_async(request)
    deadline = time.monotonic() + 5
    while not future.done() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.02)
    if not future.done():
        raise RuntimeError('Acceptance unknown: no retry; operator intervention required')
    goal = future.result()
    if not goal.accepted:
        raise RuntimeError('Goal rejected')
    try:
        # Cover every exception from the moment an accepted goal is known.
        emit(kind='accepted', goal_id=list(map(int, goal.goal_id.uuid)))
        result = goal.get_result_async()
        deadline = time.monotonic() + 10
        since = None
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.01)
            q, v = checked()
            check_envelope(q, initial, names)
            if result.done():
                response = result.result()
                if response.status != 4 or response.result.state.desc != 'SUCCEED':
                    raise RuntimeError('Motion did not succeed')
                stable = abs(q['head_pitch_joint'] + .43) <= .02 and all(abs(v[n]) <= .01 for n in names)
                since = (since or time.monotonic()) if stable else None
                if since and time.monotonic() - since >= 1:
                    emit(status='HEAD_COMPLETED', physical_stop_qualified=False)
                    return
        raise RuntimeError('Head trial deadline exceeded')
    except BaseException:
        cancelled = goal.cancel_goal_async()
        deadline = time.monotonic() + 2
        while not cancelled.done() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.02)
        emit(kind='cancel_request', response_received=cancelled.done(),
             response=message_to_ordereddict(cancelled.result()) if cancelled.done() else None,
             physical_stop_demonstrated=False)
        raise
