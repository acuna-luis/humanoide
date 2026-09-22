#!/usr/bin/env python3
"""ROS2-container helper: load/localize utars_nav_map; sends no navigation goal.

Uses only the existing navigation manager commands. Does not edit saved points,
move arms, publish velocities, switch controllers or retry a failed command.
"""
import json
import re
import time


def main():
    import rclpy
    from rclpy.action import ActionClient
    from unav_task_msgs.action import Task
    from rosidl_runtime_py.convert import message_to_ordereddict
    rclpy.init(); node = rclpy.create_node('front_map_preparation')
    client = ActionClient(node, Task, '/vnav/task/command')

    def wait(future, seconds):
        end = time.monotonic()+seconds
        while not future.done() and time.monotonic()<end:
            rclpy.spin_once(node, timeout_sec=.05)
        if not future.done():
            raise TimeoutError('Navigation-manager completion unknown; no retry')
        return future.result()

    def command(name, arg=None, limit=12):
        request = Task.Goal(command=name, arg_json=json.dumps(arg or {}))
        handle = wait(client.send_goal_async(request), 5)
        if not handle.accepted:
            raise RuntimeError('Rejected '+name)
        print(json.dumps(dict(command=name, goal_id=bytes(handle.goal_id.uuid).hex())), flush=True)
        response = wait(handle.get_result_async(), limit)
        result = message_to_ordereddict(response.result)
        print(json.dumps(dict(command=name, status=response.status, result=result)), flush=True)
        if response.status != 4:
            raise RuntimeError('Failed '+name)
        if name in ('get_map_name', 'map_set', 'relocation_start'):
            allowed = {'SUCCESS', 'SUCCEED', 'VSLAM_LOAD_MAP_FINISHED', 'NAVIGATION_READY'}
            if result['state']['desc'] not in allowed:
                raise RuntimeError('Unexpected result '+name)
        return result

    def state():
        found = re.findall(r'\bFSM_[A-Z_]+\b', command('check_state')['dmsg'])
        if len(found) != 1:
            raise RuntimeError('Ambiguous navigation state')
        return found[0]

    try:
        if not client.wait_for_server(timeout_sec=5):
            raise RuntimeError('Navigation manager absent')
        current = json.loads(command('get_map_name')['result_json'])['map_name']
        initial = state()
        if initial not in ('FSM_WAITSETMAP', 'FSM_WAITRELOCATE', 'FSM_WAITNAVIGATE'):
            raise RuntimeError('Navigation busy or unknown')
        if current != 'utars_nav_map' or initial == 'FSM_WAITSETMAP':
            command('map_set', {'map_name':'utars_nav_map'}, 90)
            initial = 'FSM_WAITRELOCATE'
        if initial == 'FSM_WAITRELOCATE':
            command('relocation_start', {'map_name':'utars_nav_map', 'target_point':{'mode':'global'}}, 90)
        if (json.loads(command('get_map_name')['result_json'])['map_name'] != 'utars_nav_map'
                or state() != 'FSM_WAITNAVIGATE'):
            raise RuntimeError('Map/localization not ready')
        print('MAP_READY_NO_NAVIGATION_SENT', flush=True)
    finally:
        client.destroy(); node.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    main()
