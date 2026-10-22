"""Select reviewed deposit contracts without sharing physical qualification."""
if __package__:
    from . import scenario1_table90 as table90
    from . import scenario1_table695 as table695
else:
    import scenario1_table90 as table90
    import scenario1_table695 as table695


def select(profile):
    task = profile.get('deposit', {}).get('task')
    for module in (table90, table695):
        if task == module.TASK_NAME:
            return module
    return None


def validate_trial(profile, stop_after, deposit_trial):
    if type(deposit_trial) is not bool:
        raise ValueError('DEPOSIT_TRIAL_INVALID: expected a boolean')
    module = select(profile)
    if deposit_trial and (module is not table695 or stop_after != 'deposit'):
        raise ValueError('DEPOSIT_TRIAL_INVALID: requiere mesa 69,5 cm y --stop-after deposit')


def require_motion_ready(profile, stop_after, entry_stage='navigate_get1', *, deposit_trial=False):
    validate_trial(profile, stop_after, deposit_trial)
    module = select(profile)
    if module is table695:
        module.require_motion_ready(profile, stop_after, entry_stage, deposit_trial=deposit_trial)
    elif module is not None:
        module.require_motion_ready(profile, stop_after, entry_stage)
