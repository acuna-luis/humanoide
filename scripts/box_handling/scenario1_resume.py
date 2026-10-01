"""Pure, explicit resume planning; an acknowledgement never authorizes motion.

The caller archives the source checkpoint and validates fresh physical/runtime
requirements before arming. A resumed checkpoint records only its new segment.
Origin skipped/repeated lists describe an ordered jump, not proof of past work.
"""
import copy
import hashlib
import json

if __package__:
    from . import scenario1_contract as contract
else:
    import scenario1_contract as contract


def plan_resume(checkpoint, profile, *, stage=None, box_state=None,
                recovery_confirmed=False, stop_after='verify_home', policy='assume',
                execution_profile='standard_v1'):
    source = contract.validate_checkpoint(checkpoint, profile)
    contract.validate_profile(profile, stop_after=stop_after)
    if type(recovery_confirmed) is not bool:
        raise ValueError('Recovery confirmation must be a boolean')
    if type(policy) is not str or policy not in contract.CONFIRMATION_POLICIES:
        raise ValueError('Unknown confirmation policy')
    if source.get('policy', 'ask') != policy:
        raise ValueError('Resume cannot change the checkpoint confirmation policy')
    requested_execution = contract.execution_profile(
        {'policy': policy, 'execution_profile': execution_profile})
    if contract.execution_profile(source) != requested_execution:
        raise ValueError('Resume cannot change the checkpoint execution profile')
    if stage is not None and (type(stage) is not str or stage not in contract.STAGES):
        raise ValueError('Unknown resume stage')
    index = contract.progress_index(source)
    following = contract.STAGES[index] if index < len(contract.STAGES) else None
    selected = following if stage is None else stage
    if selected is None:
        raise ValueError('Cycle already complete; an explicit recovery stage is required')
    if contract.STAGES.index(selected) > contract.STAGES.index(stop_after):
        raise ValueError('Resume entry is after stop_after')
    expected = contract.ENTRY_BOX_STATES[selected]
    if box_state is not None and (type(box_state) is not str or box_state != expected):
        raise ValueError('Explicit box state does not match the selected stage')
    needs_recovery = (source['failure'] is not None or source['in_flight'] is not None or
                      source['box_state'] == 'unknown' or selected != following)
    if needs_recovery and not (recovery_confirmed and box_state is not None):
        raise ValueError('Recovery requires explicit box state and recovery confirmation')
    if not needs_recovery and box_state is None and source['box_state'] != expected:
        raise ValueError('Checkpoint box state cannot be inferred for this stage')
    source_sha256 = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(',', ':'),
                                             allow_nan=False).encode()).hexdigest()
    selected_index = contract.STAGES.index(selected)
    origin = {
        'source_sha256': source_sha256,
        'source_next_stage': following,
        'source_failure': copy.deepcopy(source['failure']),
        'source_in_flight': source['in_flight'],
        'requested_stage': stage,
        'explicit_state': box_state is not None,
        'recovery_confirmed': recovery_confirmed,
        'skipped_stages': list(contract.STAGES[index:selected_index]) if selected_index > index else [],
        'repeated_stages': list(contract.STAGES[selected_index:index]) if selected_index < index else [],
    }
    cp = contract.new_resume_checkpoint(profile, entry_stage=selected, entry_box_state=expected,
        origin=origin, stop_after=stop_after, policy=policy, execution_profile=execution_profile)
    if 'home_retry' in source:
        # An explicit recovery segment must not manufacture another automatic
        # retry, including when a crash followed reservation but not dispatch.
        cp['home_retry'] = copy.deepcopy(source['home_retry'])
    uncertain_home_budget = (source['in_flight'] == 'home' or
                             source['failure'] is not None and source['failure']['stage'] == 'home')
    if (source.get('home_retry_blocked', False) or
            requested_execution == 'optimistic_v1' and 'home_retry' not in source
            and uncertain_home_budget):
        # The remote reservation can be durable before its event reaches the
        # PC checkpoint. Absence there does not prove that the budget is free.
        # Preserve uncertainty without inventing a failed UUID or native result.
        cp['home_retry_blocked'] = True
    cp = contract.validate_checkpoint(cp, profile)
    waypoint = ('get1' if selected in ('enable_vision', 'grasp', 'verify_held', 'retreat') else
                'put1' if selected == 'deposit' else None)
    return {'checkpoint': cp, 'stage': selected, 'source_sha256': source_sha256,
            'requirements': {'box_state': expected,
                             'home': selected in ('navigate_get1', 'enable_vision', 'grasp', 'verify_home'),
                             'waypoint': waypoint, 'vision_prep': selected == 'grasp'}}
