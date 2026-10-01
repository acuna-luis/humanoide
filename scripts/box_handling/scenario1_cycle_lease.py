"""Transient SPS runners with a session lease renewed only between cycles.

The installed, hashed adapter files remain untouched. Only their outer lifetime
condition changes; perception timeouts, cancellation and stop checks do not.
"""
from textwrap import dedent


_RUNNER = dedent('''\
def _scenario1_run_cycle_adapter(path, session):
    import ast
    import json
    import math
    from pathlib import Path
    import sys
    import time

    source_path = Path(path)
    session_path = Path(session)
    source = source_path.read_text()
    predicate = 'time.monotonic() < deadline'
    if source.count(predicate) != 1:
        raise RuntimeError('SPS_CYCLE_ADAPTER_SOURCE_CHANGED: expected one lease condition')
    tree = ast.parse(source, filename=str(source_path))
    expected = ast.dump(ast.parse(predicate, mode='eval').body)
    matches = [node for node in ast.walk(tree)
               if isinstance(node, ast.Compare) and ast.dump(node) == expected]
    if len(matches) != 1 or not any(
            any(node is matches[0] for node in ast.walk(loop.test))
            for loop in ast.walk(tree) if isinstance(loop, ast.While)):
        raise RuntimeError('SPS_CYCLE_ADAPTER_SOURCE_CHANGED: lease is not a while condition')

    rejected = False

    def current_lease_valid():
        nonlocal rejected
        if rejected or (session_path/'stop').exists():
            rejected = True
            return False
        try:
            lease = json.loads((session_path/'lease.json').read_text())
            if not isinstance(lease, dict) or set(lease) != {'deadline'}:
                raise ValueError('Unexpected lease fields')
            deadline = lease['deadline']
            now = time.monotonic()
            if (isinstance(deadline, bool) or not isinstance(deadline, (int, float))
                    or not math.isfinite(deadline) or deadline - now > 900.5):
                raise ValueError('Invalid lease deadline')
        except (OSError, ValueError, TypeError, OverflowError) as exc:
            rejected = True
            raise RuntimeError('SPS_SESSION_LEASE_INVALID') from exc
        if deadline <= now:
            rejected = True
            return False
        return True

    changed = source.replace(predicate, '_scenario1_cycle_lease_valid()', 1)
    # Existing wrapper monkeypatches survive because imports use sys.modules;
    # argv is left exactly as prepared by that wrapper.
    parent = str(source_path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    namespace = dict(__name__='__main__', __file__=str(source_path),
                     __package__=None, __spec__=None, __cached__=None,
                     _scenario1_cycle_lease_valid=current_lease_valid)
    exec(compile(changed, str(source_path), 'exec'), namespace)

''')


def adapter_runner_source(path, session):
    """Return standalone Python appended after wrapper imports and ``sys.argv``.

    A renewed deadline is read each outer-loop iteration. A missing, malformed,
    nonfinite or excessive lease fails closed; expiry/stop ends the original
    loop and runs its existing cleanup. An expired lease cannot be revived in
    this process. The original action and capture deadlines are not patched.
    """
    return (_RUNNER + '\n_scenario1_run_cycle_adapter('
            + repr(str(path)) + ', ' + repr(str(session)) + ')\n')
