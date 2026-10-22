"""Recorded table74 recipe; assumptions never become current observations.

Pure validation is also sent to the existing remote phase runtime. No robot IO
or input is performed here. The successful source is provenance, not a resume
checkpoint and not a sensor measuring a future box.
"""
import copy
import hashlib
import json
from pathlib import Path
import time


RECORDED_RECIPE = {
    'version': 1,
    'id': 'table74-recorded-20261022-v1',
    'source_evidence': '20261022T142922Z_TABLE74_SUPERVISED_CYCLE_1198976',
    'source_cycle_sha256': '7dc8c5a047d7aacb80ab9db67176babfd3ddda4fd3dd219aad23db4bfe222b7c',
    'robot_serial': 'WAE001UBT60000669',
    'surface_height_cm': 74.,
    'effector': 'clamp',
    'box_dimensions_m': [.603, .397, .22],
    'sequence': ['approach', 'precontact', 'support', 'pin_relief', 'lateral_open', 'home'],
    'facts': {
        'gap_after_approach_cm': 19.,
        'gap_after_precontact_cm': 5.,
        'support_assumed': True,
        'tool_clearance_before_relief_cm': 8.,
        'required_pin_exit_cm': 2.,
        'tool_clearance_after_relief_cm': 5.,
        'pins_free_assumed': True,
        'lateral_path_assumed_clear': True,
        'empty_tools_after_open_assumed': True,
    },
    'physical_state_of_new_cycle_measured': False,
    'automatic_settle': False,
    'automatic_retry': False,
}
TOKENS = frozenset(('CONTINUAR74', 'APROXIMAR74', 'BAJAR74', 'LIBERAR74',
    'HOME74', 'HUECO19', 'HUECO5', 'APOYADA', 'PINES_LIBRES', 'DESPEJADO10', 'LIBRE'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _record():
    return dict(kind='recorded_recipe_assumption', recipe_id=RECORDED_RECIPE['id'],
        recipe_sha256=hashlib.sha256(canonical(RECORDED_RECIPE).encode()).hexdigest(),
        source_evidence=RECORDED_RECIPE['source_evidence'], current_physical_measurement=False,
        recipe=copy.deepcopy(RECORDED_RECIPE))


def validate_record(record):
    # Canonical comparison distinguishes JSON booleans and integers too.
    if not isinstance(record, dict) or canonical(record) != canonical(_record()):
        raise ValueError('TABLE74_RECIPE_CHANGED: unsupported recipe or provenance')
    return copy.deepcopy(record)


def assert_policy(policy):
    if type(policy) is not RecipePolicy:
        raise ValueError('An authenticated table74 RecipePolicy is required')
    validate_record(policy.as_dict())
    return policy


class RecipePolicy:
    def __init__(self, record):
        self._record = validate_record(record)

    @classmethod
    def from_default(cls):
        return cls(_record())

    def as_dict(self):
        return validate_record(self._record)

    def facts(self):
        return self.as_dict()['recipe']['facts']

    def authorize(self, token, evidence):
        if token not in TOKENS:
            raise ValueError('TABLE74_RECIPE_TOKEN_NOT_ALLOWED: '+str(token))
        record = self.as_dict()
        receipt = dict(authorization_kind='recorded_recipe_assumption', token=token,
            current_physical_measurement=False, recorded_ns=time.time_ns(), record=record)
        path = Path(evidence)/('recipe-'+token+'.json')
        # Repeated guards get separate receipts; none overwrites an observation.
        if path.exists():
            path = path.with_name(path.stem+'-'+str(time.time_ns())+'.json')
        with path.open('x') as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        return receipt

    def validate_completion(self, after, evidence):
        """Bind the successful action to an honest, possibly inconclusive log audit.

        Feria uses the native terminal plus live guards. An unavailable Docker
        log is a diagnostic limitation, not a contradictory robot outcome.
        Positive force/IK evidence still fails in the runtime before success.
        """
        self.as_dict()
        events = Path(after)/'events.jsonl'
        if events.stat().st_size > 16*1024*1024:
            raise ValueError('TABLE74_RECIPE_EVENTS_UNBOUNDED')
        rows = [json.loads(line) for line in events.read_text().splitlines() if line.strip()]
        checks = [row for row in rows if row.get('event') == 'table74_native_completion']
        if len(checks) != 1:
            raise RuntimeError('TABLE74_RECIPE_NATIVE_COMPLETION_UNCONFIRMED')
        journal = json.loads((Path(after)/'trial.json').read_text())
        check = checks[0]
        complete = check.get('verified') is True
        inconclusive = (check.get('verified') is False and
            check.get('guard_policy') == 'feria_native_terminal_v1' and
            check.get('diagnostic_status') in ('inconclusive', 'unavailable') and
            check.get('critical_fault_observed') is False and
            check.get('execution_result_validated') is True)
        if not (complete or inconclusive):
            raise RuntimeError('TABLE74_RECIPE_NATIVE_COMPLETION_UNCONFIRMED')
        if (journal.get('phase') != 'succeeded' or check.get('goal_id') != journal.get('result', {}).get('goal_id')
                or check.get('bundle_id') != journal.get('bundle_id')):
            raise RuntimeError('TABLE74_RECIPE_COMPLETION_IDENTITY_CHANGED')
        if inconclusive:
            if __package__:
                from .scenario1_contract import validate_motion_result
            else:
                from scenario1_contract import validate_motion_result
            validate_motion_result(journal['result'])
        return check
